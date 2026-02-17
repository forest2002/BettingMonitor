"""
Betfair Stream API client for real-time push data.
Uses Betfair's streaming API for instant price updates.
"""
import os
import asyncio
import queue
from typing import List, Optional, Dict
from datetime import datetime
from decimal import Decimal
import logging

from betfairlightweight import StreamListener, APIClient
from betfairlightweight.streaming import StreamingMarketFilter
from models.schemas import OddsData
from services.scrapers.base import BookmakerScraper

logger = logging.getLogger(__name__)


class BetfairStreamListener(StreamListener):
    """Custom stream listener for processing Betfair market updates"""

    def __init__(self, callback):
        super().__init__()
        self.callback = callback
        self.market_cache = {}

    def on_data(self, data):
        """Called when new data arrives"""
        try:
            # Process market changes
            market_changes = data.get('mc', [])
            for market_change in market_changes:
                market_id = market_change.get('id')
                if not market_id:
                    continue

                # Update cache and trigger callback
                self.market_cache[market_id] = market_change
                self.callback(market_change)

        except Exception as e:
            logger.error(f"Error processing stream data: {e}", exc_info=True)


class BetfairStreamClient(BookmakerScraper):
    """Betfair Streaming API client for real-time push updates"""

    def __init__(self):
        super().__init__("betfair_stream")
        self.client: Optional[APIClient] = None
        self.stream = None
        self.listener = None
        self.odds_queue = asyncio.Queue()

        # Credentials
        self.username = os.getenv("BETFAIR_USERNAME")
        self.password = os.getenv("BETFAIR_PASSWORD")
        self.app_key = os.getenv("BETFAIR_APP_KEY")
        self.cert_path = os.getenv("BETFAIR_CERT_PATH")
        self.key_path = os.getenv("BETFAIR_KEY_PATH")  # Private key path

        if not all([self.username, self.password, self.app_key]):
            raise ValueError(
                "Missing Betfair credentials. Required: BETFAIR_USERNAME, "
                "BETFAIR_PASSWORD, BETFAIR_APP_KEY"
            )

        if not self.cert_path:
            raise ValueError(
                "BETFAIR_CERT_PATH required for streaming. "
                "Generate certificates with generate_betfair_certs.sh"
            )

    async def initialize(self):
        """Initialize streaming client and start stream"""
        self.logger.info("Initializing Betfair Stream API client...")

        try:
            # Create API client with certificate auth
            self.client = APIClient(
                username=self.username,
                password=self.password,
                app_key=self.app_key,
                certs=(self.cert_path, self.key_path) if self.key_path else self.cert_path,
            )

            # Login
            self.client.login()
            self.logger.info("Successfully logged in to Betfair (certificate mode)")

            # Create listener
            self.listener = BetfairStreamListener(self._on_market_update)

            # Create stream
            self.stream = self.client.streaming.create_stream(
                listener=self.listener
            )

            # Subscribe to horse racing markets
            market_filter = StreamingMarketFilter(
                event_type_ids=['7'],  # Horse racing
                country_codes=['GB', 'IE'],
                market_types=['WIN', 'PLACE']
            )

            # Start streaming in a separate thread
            import threading
            self.stream_thread = threading.Thread(
                target=self._run_stream,
                args=(market_filter,),
                daemon=True
            )
            self.stream_thread.start()

            self.is_running = True
            self.logger.info("Betfair Stream API client initialized - receiving real-time updates")

        except Exception as e:
            self.logger.error(f"Failed to initialize streaming client: {e}", exc_info=True)
            await self.cleanup()
            raise

    def _run_stream(self, market_filter):
        """Run stream in thread"""
        try:
            self.stream.subscribe_to_markets(
                market_filter=market_filter,
                market_data_filter={'fields': ['EX_BEST_OFFERS']},
                conflate_ms=100  # Update every 100ms
            )
            self.stream.start()
        except Exception as e:
            self.logger.error(f"Stream error: {e}", exc_info=True)

    def _on_market_update(self, market_change: Dict):
        """Called when market prices change"""
        try:
            # Extract market info
            market_id = market_change.get('id')
            market_definition = market_change.get('marketDefinition', {})

            # Process runner changes
            runner_changes = market_change.get('rc', [])
            for runner_change in runner_changes:
                selection_id = runner_change.get('id')

                # Get best back/lay prices
                ex = runner_change.get('ex', {})
                available_to_back = ex.get('atb', [])
                available_to_lay = ex.get('atl', [])

                if not available_to_back:
                    continue

                # Create odds data
                back_price = Decimal(str(available_to_back[0][0]))
                lay_price = Decimal(str(available_to_lay[0][0])) if available_to_lay else None

                # Determine bookmaker name based on market type
                market_type = market_definition.get('marketType', 'WIN')
                bk_name = "Betfair Exchange Place" if market_type == "PLACE" else "Betfair Exchange"

                # Queue for async processing
                odds_data = {
                    'market_id': market_id,
                    'selection_id': selection_id,
                    'back_price': back_price,
                    'lay_price': lay_price,
                    'bookmaker_name': bk_name,
                    'market_type': market_type,
                    'timestamp': datetime.utcnow()
                }

                # Add to queue (non-blocking)
                try:
                    asyncio.run_coroutine_threadsafe(
                        self.odds_queue.put(odds_data),
                        asyncio.get_event_loop()
                    )
                except:
                    pass  # Queue full or event loop not available

        except Exception as e:
            self.logger.debug(f"Error processing market update: {e}")

    async def scrape(self) -> List[OddsData]:
        """
        Get accumulated odds updates from stream.
        Called periodically to batch process streaming updates.
        """
        odds_list = []

        try:
            # Get all queued updates (non-blocking)
            while not self.odds_queue.empty():
                try:
                    odds = await asyncio.wait_for(self.odds_queue.get(), timeout=0.1)

                    # TODO: Convert to OddsData format
                    # For now, just count updates
                    odds_list.append(odds)

                except asyncio.TimeoutError:
                    break

            if odds_list:
                self.logger.info(f"Processed {len(odds_list)} real-time price updates from stream")

        except Exception as e:
            self.logger.error(f"Error in scrape: {e}", exc_info=True)

        return []  # Return empty for now, needs full implementation

    async def cleanup(self):
        """Stop stream and logout"""
        self.logger.info("Cleaning up Betfair Stream client...")
        if self.stream:
            try:
                self.stream.stop()
            except:
                pass
        if self.client:
            try:
                self.client.logout()
            except:
                pass
        self.is_running = False

    def health_check(self) -> bool:
        """Check if stream is healthy"""
        return self.is_running and self.stream is not None
