"""
Betfair Stream API client for real-time push data.
Uses Betfair's streaming API for instant price updates with Interactive Login.
"""
import os
import asyncio
import threading
from typing import List, Optional, Dict
from datetime import datetime
from decimal import Decimal
import logging

import betfairlightweight
from betfairlightweight import StreamListener
from betfairlightweight.filters import streaming_market_filter
from models.schemas import OddsData
from services.scrapers.base import BookmakerScraper

logger = logging.getLogger(__name__)


class BetfairStreamListener(StreamListener):
    """Custom stream listener for processing Betfair market updates"""

    def __init__(self, parent):
        super().__init__()
        self.parent = parent
        self.market_definitions = {}  # Cache market definitions

    def on_data(self, raw_data):
        """Called when new data arrives from stream"""
        try:
            # Update market definitions from stream
            for market_change in raw_data:
                if hasattr(market_change, 'market_definition'):
                    if market_change.market_definition:
                        self.market_definitions[market_change.market_id] = market_change.market_definition

                # Process runner changes
                if hasattr(market_change, 'runners'):
                    for runner in market_change.runners:
                        self.parent._process_runner_update(market_change, runner)

        except Exception as e:
            logger.error(f"Error processing stream data: {e}", exc_info=True)


class BetfairStreamClient(BookmakerScraper):
    """Betfair Streaming API client for real-time push updates"""

    def __init__(self):
        super().__init__("betfair_stream")
        self.client = None
        self.stream = None
        self.listener = None
        self.update_buffer = []
        self.buffer_lock = threading.Lock()

        # Credentials
        self.username = os.getenv("BETFAIR_USERNAME")
        self.password = os.getenv("BETFAIR_PASSWORD")
        self.app_key = os.getenv("BETFAIR_APP_KEY")

        if not all([self.username, self.password, self.app_key]):
            raise ValueError(
                "Missing Betfair credentials. Required: BETFAIR_USERNAME, "
                "BETFAIR_PASSWORD, BETFAIR_APP_KEY"
            )

    async def initialize(self):
        """Initialize streaming client and start stream"""
        self.logger.info("Initializing Betfair Stream API client (Interactive Login)...")

        try:
            # Create API client with interactive login (no certificates needed!)
            self.client = betfairlightweight.APIClient(
                username=self.username,
                password=self.password,
                app_key=self.app_key,
                lightweight=True  # Interactive login
            )

            # Login
            self.client.login_interactive()
            self.logger.info("Successfully logged in to Betfair (interactive mode)")

            # Keep alive
            self.client.keep_alive()

            # Create listener
            self.listener = BetfairStreamListener(self)

            # Create stream
            self.stream = self.client.streaming.create_stream(
                listener=self.listener
            )

            # Subscribe to horse racing markets
            market_filter = streaming_market_filter(
                event_type_ids=['7'],  # Horse racing
                country_codes=['GB', 'IE'],
                market_types=['WIN', 'PLACE']
            )

            # Start streaming in a separate thread
            self.stream_thread = threading.Thread(
                target=self._run_stream,
                args=(market_filter,),
                daemon=True
            )
            self.stream_thread.start()

            self.is_running = True
            self.logger.info("🚀 Betfair Stream API active - receiving REAL-TIME price updates!")

        except Exception as e:
            self.logger.error(f"Failed to initialize streaming client: {e}", exc_info=True)
            await self.cleanup()
            raise

    def _run_stream(self, market_filter):
        """Run stream in thread"""
        try:
            self.logger.info("Starting market stream subscription...")
            self.stream.subscribe_to_markets(
                market_filter=market_filter,
                market_data_filter={'fields': ['EX_BEST_OFFERS', 'EX_MARKET_DEF']},
                conflate_ms=0  # No conflation - instant updates!
            )
            self.stream.start()
        except Exception as e:
            self.logger.error(f"Stream error: {e}", exc_info=True)

    def _process_runner_update(self, market_change, runner):
        """Process individual runner price update"""
        try:
            if not hasattr(runner, 'ex'):
                return

            # Get market definition
            market_def = None
            if hasattr(market_change, 'market_definition'):
                market_def = market_change.market_definition
            elif market_change.market_id in self.listener.market_definitions:
                market_def = self.listener.market_definitions[market_change.market_id]

            if not market_def:
                return

            # Get runner name
            runner_name = None
            if hasattr(market_def, 'runners'):
                for r in market_def.runners:
                    if r.id == runner.id:
                        runner_name = r.name
                        break

            if not runner_name:
                return

            # Extract prices
            ex = runner.ex
            back_price = None
            lay_price = None

            if hasattr(ex, 'available_to_back') and ex.available_to_back:
                back_price = Decimal(str(ex.available_to_back[0].price))

            if hasattr(ex, 'available_to_lay') and ex.available_to_lay:
                lay_price = Decimal(str(ex.available_to_lay[0].price))

            if not back_price:
                return

            # Get event info
            event_name = market_def.event_name if hasattr(market_def, 'event_name') else None
            venue = market_def.venue if hasattr(market_def, 'venue') else None
            market_time = market_def.market_time if hasattr(market_def, 'market_time') else None
            market_type = market_def.market_type if hasattr(market_def, 'market_type') else 'WIN'

            # Determine bookmaker name
            bk_name = "Betfair Exchange Place" if market_type == "PLACE" else "Betfair Exchange"

            # Create odds data
            odds_data = OddsData(
                event_name=event_name,
                venue=venue,
                scheduled_time=market_time,
                selection_name=runner_name,
                odds_decimal=back_price,
                place_odds=lay_price,
                place_terms=None,
                bookmaker_name=bk_name,
                event_type="horse_racing",
                metadata={
                    'market_id': market_change.market_id,
                    'selection_id': runner.id,
                    'source': 'betfair_stream',
                    'market_type': market_type,
                }
            )

            # Buffer the update
            with self.buffer_lock:
                self.update_buffer.append(odds_data)

        except Exception as e:
            self.logger.debug(f"Error processing runner update: {e}")

    async def scrape(self) -> List[OddsData]:
        """
        Get accumulated odds updates from stream.
        Called periodically to batch process streaming updates.
        """
        odds_list = []

        try:
            # Keep session alive
            if self.client:
                try:
                    self.client.keep_alive()
                except:
                    pass

            # Get buffered updates
            with self.buffer_lock:
                odds_list = self.update_buffer.copy()
                self.update_buffer.clear()

            if odds_list:
                win_count = sum(1 for o in odds_list if o.bookmaker_name == "Betfair Exchange")
                place_count = sum(1 for o in odds_list if o.bookmaker_name == "Betfair Exchange Place")
                self.logger.info(
                    f"📊 Processed {len(odds_list)} real-time updates from stream "
                    f"({win_count} WIN, {place_count} PLACE)"
                )

        except Exception as e:
            self.logger.error(f"Error in scrape: {e}", exc_info=True)

        return odds_list

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
