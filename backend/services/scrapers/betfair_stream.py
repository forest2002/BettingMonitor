"""
Betfair Stream API client for real-time push data.
Uses Betfair's streaming API for instant price updates with Interactive Login.
"""
import os
import asyncio
import threading
import json
from typing import List, Optional, Dict
from datetime import datetime
from decimal import Decimal
import logging
import time

import betfairlightweight
from betfairlightweight import StreamListener
from betfairlightweight.filters import streaming_market_filter
from models.schemas import OddsData
from services.scrapers.base import BookmakerScraper

logger = logging.getLogger(__name__)


class BetfairStreamListener(StreamListener):
    """Custom stream listener that processes streaming data"""

    def __init__(self, parent):
        super().__init__()
        self.parent = parent
        self.update_count = 0

    def on_data(self, raw_data):
        """Called when stream data arrives - parse JSON ourselves"""
        try:
            self.update_count += 1

            # raw_data is a JSON string - parse it
            try:
                data = json.loads(raw_data)
            except Exception as e:
                if self.update_count <= 5:
                    self.parent.logger.error(f"JSON parse error: {e}")
                return

            # Check if this is market change message
            if not isinstance(data, dict):
                return

            # Log all message types for debugging
            if self.update_count <= 10 or self.update_count % 100 == 0:
                self.parent.logger.info(f"📨 Stream message #{self.update_count}: op={data.get('op')}, keys={list(data.keys())}")

            # Betfair stream sends various message types
            # We're looking for 'mc' (market change) messages
            if data.get('op') == 'mcm' and 'mc' in data:
                # Market change message
                market_changes = data['mc']

                # Log every 20 messages to debug stale prices
                if self.update_count % 20 == 0:
                    self.parent.logger.info(f"📊 MCM #{self.update_count}: Processing {len(market_changes)} market changes")

                # Periodically log a sample market change for debugging
                if self.update_count == 100 and len(market_changes) > 0:
                    sample_mc = market_changes[0]
                    self.parent.logger.info(f"📋 Sample market change structure: {json.dumps(sample_mc, indent=2)[:500]}")

                for mc in market_changes:
                    market_id = mc.get('id')
                    if not market_id:
                        continue

                    # Parse market definition
                    market_def = mc.get('marketDefinition', {})

                    if not market_def:
                        if self.update_count <= 3:
                            self.parent.logger.debug(f"Market {market_id} has no marketDefinition")
                        continue

                    # Get event details - use fallbacks if not available
                    event_name = market_def.get('eventName')
                    if not event_name:
                        # Use eventId as fallback
                        event_id = market_def.get('eventId')
                        event_name = f"Event {event_id}" if event_id else "Unknown Event"

                    venue = market_def.get('venue') or "Unknown Venue"
                    market_time_str = market_def.get('marketTime')
                    market_type = market_def.get('marketType', 'WIN')

                    # Parse market time
                    market_time = None
                    if market_time_str:
                        try:
                            market_time = datetime.fromisoformat(market_time_str.replace('Z', '+00:00'))
                        except:
                            pass

                    # If no market_time, use current time
                    if not market_time:
                        market_time = datetime.now()

                    # Get runner definitions for names
                    runners_def = market_def.get('runners', [])
                    # Only include runners that have both id and name
                    runner_names = {r.get('id'): r.get('name') for r in runners_def if r.get('id') and r.get('name')}

                    # If no runner names in stream data, fetch from API cache
                    if not runner_names:
                        with self.parent.runner_cache_lock:
                            # Check if we have cached runner names for this market
                            if market_id not in self.parent.runner_names_cache:
                                # Fetch runner names from API (this is synchronous, runs in stream thread)
                                try:
                                    fetched = self.parent._fetch_runner_names([market_id])
                                    if market_id in fetched:
                                        self.parent.runner_names_cache[market_id] = fetched[market_id]
                                        runner_names = fetched[market_id]
                                        if self.update_count <= 5:
                                            self.parent.logger.info(f"✅ Fetched {len(runner_names)} runner names for market {market_id}")
                                except Exception as e:
                                    if self.update_count <= 3:
                                        self.parent.logger.error(f"Failed to fetch runner names for {market_id}: {e}")
                            else:
                                # Use cached runner names
                                runner_names = self.parent.runner_names_cache[market_id]

                    # Parse runner changes (price updates)
                    # 'rc' = runner changes (updates), 'img' = image (full snapshot)
                    # NOTE: Messages can have BOTH img=true AND rc data!
                    runner_changes = mc.get('rc', [])
                    has_img = mc.get('img', False)

                    # Log Punchestown 13:40 market every time to debug
                    if market_id == '1.254139974':
                        runner_ids = [rc.get('id') for rc in runner_changes if rc.get('id')]
                        self.parent.logger.info(f"📊 Punchestown: img={has_img}, rc_count={len(runner_changes)}, runner_ids={runner_ids[:5]}...")
                    elif self.update_count % 50 == 0:
                        self.parent.logger.info(f"📊 Market {market_id}: img={has_img}, rc_count={len(runner_changes)}")

                    # Process runner changes if available (even if img=true)
                    if not runner_changes:
                        # No price updates in this message
                        if self.update_count <= 10:
                            self.parent.logger.debug(f"Market {market_id} has no rc - skipping")
                        continue

                    # Debug: Log first runner change structure
                    if self.update_count == 50 and len(runner_changes) > 0:
                        sample_rc = runner_changes[0]
                        self.parent.logger.info(f"📋 Sample runner change keys: {list(sample_rc.keys())}")
                        if 'batb' in sample_rc:
                            self.parent.logger.info(f"📋 Sample batb structure: {sample_rc['batb']}")
                        if 'batl' in sample_rc:
                            self.parent.logger.info(f"📋 Sample batl structure: {sample_rc['batl']}")

                    for rc in runner_changes:
                        selection_id = rc.get('id')

                        if not selection_id:
                            continue

                        # Get runner name with fallback
                        runner_name = runner_names.get(selection_id)
                        if not runner_name:
                            # Use selection_id as fallback if name not available
                            runner_name = f"Runner {selection_id}"

                        # Get best available back price (batb = best available to back)
                        # Try both 'batb' (best) and 'atb' (all) for backwards compatibility
                        batb = rc.get('batb', [])
                        if not batb:
                            batb = rc.get('atb', [])

                        back_price = None
                        if batb and len(batb) > 0:
                            # DEBUG: Log raw batb for Straight John and Bulgaden
                            if runner_name in ["Straight John", "Bulgaden Castle"] and self.update_count % 10 == 0:
                                self.parent.logger.info(f"🔍 {runner_name} batb: {batb}")

                            # batb format: [[position, price, size], ...]
                            # Take first non-zero price entry
                            for entry in batb:
                                if len(entry) >= 3 and entry[1] > 0:
                                    back_price = Decimal(str(entry[1]))
                                    break

                            # Debug: Log first few prices to verify they're correct
                            if self.update_count % 50 == 0 and len(self.parent.market_cache) < 5:
                                first_entry = batb[0] if batb else None
                                if first_entry and len(first_entry) >= 3:
                                    self.parent.logger.info(f"💰 {runner_name}: batb[0]=[pos={first_entry[0]}, price={first_entry[1]}, size={first_entry[2]}] → extracted={back_price}")

                        # Allow processing even without back_price - might have lay_price or cached data
                        # if not back_price:
                        #     continue

                        # Get lay price (batl = best available to lay)
                        # Try both 'batl' (best) and 'atl' (all) for backwards compatibility
                        batl = rc.get('batl', [])
                        if not batl:
                            batl = rc.get('atl', [])

                        lay_price = None
                        if batl and len(batl) > 0:
                            # batl format: [[position, price, size], ...]
                            # Take first non-zero price entry
                            for entry in batl:
                                if len(entry) >= 3 and entry[1] > 0:
                                    lay_price = Decimal(str(entry[1]))
                                    break

                        # Skip only if we have NEITHER back nor lay price
                        if not back_price and not lay_price:
                            continue

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
                                'market_id': market_id,
                                'selection_id': selection_id,
                                'source': 'betfair_stream',
                                'market_type': market_type,
                            }
                        )

                        # Cache it
                        with self.parent.cache_lock:
                            cache_key = f"{market_id}_{selection_id}"
                            self.parent.market_cache[cache_key] = odds_data
                            self.parent.last_update = time.time()

                            if self.update_count <= 5 or len(self.parent.market_cache) <= 3:
                                self.parent.logger.info(f"✅ Cached: {runner_name} @ {back_price} ({bk_name}) - cache size: {len(self.parent.market_cache)}")

                    if self.update_count % 100 == 0:
                        self.parent.logger.info(f"✅ Stream cache: {len(self.parent.market_cache)} odds entries")

            # betfairlightweight automatically parses stream data
            # Market books should be in self.stream._caches or similar
            if hasattr(self, 'stream') and self.stream:
                # Try different ways to access market data
                market_books = None

                # Try _caches attribute
                if hasattr(self.stream, '_caches'):
                    market_books = list(self.stream._caches.values()) if self.stream._caches else None
                    if self.update_count == 1:
                        self.parent.logger.info(f"Stream has _caches: {self.stream._caches is not None}, books: {len(market_books) if market_books else 0}")
                elif self.update_count == 1:
                    self.parent.logger.info("Stream does NOT have _caches attribute")

                # If that didn't work, raw_data might be the market books
                if not market_books and raw_data:
                    if isinstance(raw_data, list):
                        market_books = raw_data
                        if self.update_count == 1:
                            self.parent.logger.info(f"Using raw_data as market_books - list with {len(raw_data)} items")

                # Cache the market books
                if market_books:
                    cached_count = 0
                    with self.parent.cache_lock:
                        for market_book in market_books:
                            if hasattr(market_book, 'market_id'):
                                self.parent.market_cache[market_book.market_id] = market_book
                                cached_count += 1
                        self.parent.last_update = time.time()

                    if self.update_count <= 2 or self.update_count % 100 == 0:
                        self.parent.logger.info(f"✅ Cached {cached_count} markets, total cache size: {len(self.parent.market_cache)} (update #{self.update_count})")
                elif self.update_count == 1:
                    self.parent.logger.warning("No market_books found to cache!")

        except Exception as e:
            logger.error(f"Error in on_data: {e}", exc_info=True)

    def on_error(self, error):
        """Called when stream encounters an error"""
        self.parent.logger.error(f"🔴 Stream error received: {error}", exc_info=True)


class BetfairStreamClient(BookmakerScraper):
    """Betfair Streaming API client for real-time push updates"""

    def __init__(self):
        super().__init__("betfair_stream")
        self.client = None
        self.stream = None
        self.listener = None

        # Market cache
        self.market_cache = {}
        self.cache_lock = threading.Lock()
        self.last_update = 0

        # Runner names cache: {market_id: {selection_id: runner_name}}
        self.runner_names_cache = {}
        self.runner_cache_lock = threading.Lock()

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
            # Create API client (NOT using lightweight mode for better stream support)
            self.client = betfairlightweight.APIClient(
                username=self.username,
                password=self.password,
                app_key=self.app_key,
                lightweight=False
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

            # Give listener access to stream
            self.listener.stream = self.stream

            # Subscribe to horse racing markets (WIN only - not PLACE)
            market_filter = streaming_market_filter(
                event_type_ids=['7'],
                country_codes=['GB', 'IE'],
                market_types=['WIN']  # Only WIN markets for accurate each-way tracking
            )

            # Subscribe with explicit fields for live updates
            # conflate_ms=0 = fastest possible updates (no delay/batching)
            self.stream.subscribe_to_markets(
                market_filter=market_filter,
                market_data_filter={
                    'fields': ['EX_BEST_OFFERS', 'EX_MARKET_DEF'],
                    'ladderLevels': 3  # Just top 3 levels for speed
                },
                conflate_ms=0,  # No conflation = instant updates
                heartbeat_ms=5000  # Heartbeat every 5s
            )

            # Set is_running before starting thread to avoid race condition
            self.is_running = True

            # Start streaming in a separate thread
            self.stream_thread = threading.Thread(
                target=self._run_stream,
                daemon=True
            )
            self.stream_thread.start()

            self.logger.info("🚀 Betfair Stream API active - receiving REAL-TIME price updates!")

        except Exception as e:
            self.logger.error(f"Failed to initialize streaming client: {e}", exc_info=True)
            await self.cleanup()
            raise

    def _fetch_runner_names(self, market_ids: List[str]) -> Dict[str, Dict[int, str]]:
        """Fetch runner names from Betfair API for given market IDs"""
        try:
            if not market_ids:
                return {}

            # Remove duplicates
            market_ids = list(set(market_ids))

            # Call Betfair API to get market catalogue
            market_filter = {
                'marketIds': market_ids
            }

            market_catalogues = self.client.betting.list_market_catalogue(
                filter=market_filter,
                max_results=100,
                market_projection=['RUNNER_METADATA']
            )

            # Build runner names dictionary
            result = {}
            for catalogue in market_catalogues:
                # Access as dict if that's what we get
                if isinstance(catalogue, dict):
                    market_id = catalogue.get('marketId')
                    runners_list = catalogue.get('runners', [])
                else:
                    market_id = catalogue.market_id
                    runners_list = catalogue.runners if hasattr(catalogue, 'runners') else []

                runners = {}
                if runners_list:
                    for runner in runners_list:
                        if isinstance(runner, dict):
                            selection_id = runner.get('selectionId')
                            runner_name = runner.get('runnerName')
                        else:
                            selection_id = runner.selection_id if hasattr(runner, 'selection_id') else None
                            runner_name = runner.runner_name if hasattr(runner, 'runner_name') else None

                        if selection_id and runner_name:
                            runners[selection_id] = runner_name

                if market_id and runners:
                    result[market_id] = runners
                    self.logger.info(f"✅ Fetched {len(runners)} runner names for market {market_id}")

            return result

        except Exception as e:
            self.logger.error(f"Error fetching runner names: {e}", exc_info=True)
            return {}

    def _run_stream(self):
        """Run stream with auto-reconnect on failure"""
        while self.is_running:
            try:
                self.logger.info("Starting stream.start() - will process data via listener callbacks...")
                # start() blocks and continuously calls listener callbacks
                self.stream.start()
                # If we get here, stream stopped normally
                self.logger.warning("Stream stopped unexpectedly")
            except Exception as e:
                self.logger.error(f"Stream error: {e}", exc_info=True)

            # If still supposed to be running, attempt reconnect after delay
            if self.is_running:
                self.logger.info("Stream disconnected - will attempt reconnect in 10 seconds...")
                time.sleep(10)
                try:
                    # Recreate stream
                    self.logger.info("Attempting to reconnect stream...")
                    self.client.keep_alive()
                    self.stream = self.client.streaming.create_stream(
                        listener=self.listener
                    )
                    self.listener.stream = self.stream

                    # Re-subscribe to markets
                    from betfairlightweight.filters import streaming_market_filter
                    market_filter = streaming_market_filter(
                        event_type_ids=['7'],
                        country_codes=['GB', 'IE'],
                        market_types=['WIN', 'PLACE']
                    )
                    self.stream.subscribe_to_markets(
                        market_filter=market_filter,
                        market_data_filter={'fields': ['EX_BEST_OFFERS', 'EX_MARKET_DEF']},
                        conflate_ms=0
                    )
                    self.logger.info("✅ Stream reconnected successfully")
                except Exception as reconnect_error:
                    self.logger.error(f"Reconnection failed: {reconnect_error}", exc_info=True)

    async def scrape(self) -> List[OddsData]:
        """Get current market data from stream cache"""
        odds_list = []

        try:
            # Keep session alive
            if self.client:
                try:
                    self.client.keep_alive()
                except:
                    pass

            # Check if stream has _caches (after it's been running for a while)
            if self.stream and hasattr(self.stream, '_caches'):
                self.logger.info(f"🎯 Stream._caches found with {len(self.stream._caches) if self.stream._caches else 0} markets")
                if self.stream._caches:
                    # Copy stream's cache to our cache
                    with self.cache_lock:
                        for market_id, market_book in self.stream._caches.items():
                            self.market_cache[market_id] = market_book
                        self.last_update = time.time()
            else:
                self.logger.debug("Stream has no _caches attribute yet")

            # Get odds from cache (already parsed as OddsData)
            with self.cache_lock:
                if not self.market_cache:
                    age = int(time.time() - self.last_update) if self.last_update > 0 else 0
                    self.logger.debug(f"No odds in cache (last update {age}s ago, listener updates: {self.listener.update_count if self.listener else 0})")
                    return []

                odds_list = list(self.market_cache.values())
                cache_age = int(time.time() - self.last_update)

                # Warn if cache is stale (no updates in 5+ minutes)
                if cache_age > 300:
                    self.logger.warning(
                        f"⚠️ Stream cache is STALE! Last update was {cache_age}s ago. "
                        f"Stream may have disconnected. Check stream thread health."
                    )

            if odds_list:
                win_count = sum(1 for o in odds_list if o.bookmaker_name == "Betfair Exchange")
                place_count = sum(1 for o in odds_list if o.bookmaker_name == "Betfair Exchange Place")
                self.logger.info(
                    f"📊 Processed {len(odds_list)} real-time prices from stream "
                    f"({win_count} WIN, {place_count} PLACE) - cache age: {cache_age}s"
                )

        except Exception as e:
            self.logger.error(f"Error in scrape: {e}", exc_info=True)

        return odds_list

    def _process_market_book_to_list(self, market_book, odds_list):
        """Process a market book and add odds to the provided list"""
        try:
            # Get market definition
            market_def = market_book.market_definition if hasattr(market_book, 'market_definition') else None

            if not market_def:
                return

            # Get event info
            event_name = market_def.event_name if hasattr(market_def, 'event_name') else None
            venue = market_def.venue if hasattr(market_def, 'venue') else None
            market_time = market_def.market_time if hasattr(market_def, 'market_time') else None
            market_type = market_def.market_type if hasattr(market_def, 'market_type') else 'WIN'

            # Process each runner
            if hasattr(market_book, 'runners'):
                for runner in market_book.runners:
                    try:
                        # Get runner name from market definition
                        runner_name = None
                        if hasattr(market_def, 'runners'):
                            for r in market_def.runners:
                                if r.id == runner.selection_id:
                                    runner_name = r.name
                                    break

                        if not runner_name:
                            continue

                        # Get best back price
                        back_price = None
                        if hasattr(runner, 'ex') and hasattr(runner.ex, 'available_to_back'):
                            if runner.ex.available_to_back:
                                back_price = Decimal(str(runner.ex.available_to_back[0]['price']))

                        if not back_price:
                            continue

                        # Get lay price for place markets
                        lay_price = None
                        if hasattr(runner, 'ex') and hasattr(runner.ex, 'available_to_lay'):
                            if runner.ex.available_to_lay:
                                lay_price = Decimal(str(runner.ex.available_to_lay[0]['price']))

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
                                'market_id': market_book.market_id,
                                'selection_id': runner.selection_id,
                                'source': 'betfair_stream',
                                'market_type': market_type,
                            }
                        )

                        odds_list.append(odds_data)

                    except Exception as e:
                        self.logger.debug(f"Error processing runner: {e}")

        except Exception as e:
            self.logger.debug(f"Error processing market book: {e}")

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
