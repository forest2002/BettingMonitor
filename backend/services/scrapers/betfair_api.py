import os
import asyncio
from typing import List, Optional
from datetime import datetime, timedelta
from decimal import Decimal
import betfairlightweight
from betfairlightweight import APIClient
from betfairlightweight.filters import market_filter, streaming_market_filter
from betfairlightweight.resources import MarketBook, RunnerBook
from models.schemas import OddsData
from services.scrapers.base import BookmakerScraper
import logging

logger = logging.getLogger(__name__)


class BetfairAPIClient(BookmakerScraper):
    """Betfair API client using official Betfair API via betfairlightweight"""

    def __init__(self):
        super().__init__("betfair_api")
        self.client: Optional[APIClient] = None
        self.username = os.getenv("BETFAIR_USERNAME")
        self.password = os.getenv("BETFAIR_PASSWORD")
        self.app_key = os.getenv("BETFAIR_APP_KEY")
        self.cert_path = os.getenv("BETFAIR_CERT_PATH")  # Optional: for cert-based auth

        # Validate credentials
        if not all([self.username, self.password, self.app_key]):
            raise ValueError(
                "Missing Betfair API credentials. Required: BETFAIR_USERNAME, "
                "BETFAIR_PASSWORD, BETFAIR_APP_KEY"
            )

    async def initialize(self):
        """Initialize Betfair API client and login"""
        self.logger.info("Initializing Betfair API client...")

        try:
            # Create API client with lightweight_login (interactive login without certs)
            self.client = betfairlightweight.APIClient(
                username=self.username,
                password=self.password,
                app_key=self.app_key,
                lightweight=True,  # Use lightweight mode (no certs required)
            )

            # Login to Betfair using interactive login
            self.client.login_interactive()
            self.logger.info("Successfully logged in to Betfair API (interactive mode)")

            # Keep session alive
            self.client.keep_alive()

            self.is_running = True
            self.logger.info("Betfair API client initialized successfully")

        except Exception as e:
            self.logger.error(f"Failed to initialize Betfair API client: {e}", exc_info=True)
            await self.cleanup()
            raise

    async def scrape(self) -> List[OddsData]:
        """Fetch odds from Betfair API for upcoming horse races (WIN and PLACE markets for each-way calculator)"""
        if not self.client:
            self.logger.error("API client not initialized")
            return []

        odds_data_list = []

        try:
            # Keep session alive
            self.client.keep_alive()

            time_filter = {
                'from': datetime.utcnow().isoformat(),
                'to': (datetime.utcnow() + timedelta(hours=24)).isoformat()
            }

            # Fetch both WIN and PLACE markets (both needed for each-way calculator)
            win_filter = market_filter(
                event_type_ids=['7'],
                market_countries=['GB', 'IE'],
                market_type_codes=['WIN'],
                market_start_time=time_filter
            )
            place_filter = market_filter(
                event_type_ids=['7'],
                market_countries=['GB', 'IE'],
                market_type_codes=['PLACE'],
                market_start_time=time_filter
            )

            projection = [
                'COMPETITION', 'EVENT', 'EVENT_TYPE',
                'MARKET_START_TIME', 'MARKET_DESCRIPTION',
                'RUNNER_DESCRIPTION', 'RUNNER_METADATA'
            ]

            win_catalogues = self.client.betting.list_market_catalogue(
                filter=win_filter, max_results=200, market_projection=projection
            )
            place_catalogues = self.client.betting.list_market_catalogue(
                filter=place_filter, max_results=200, market_projection=projection
            )

            self.logger.info(
                f"Found {len(win_catalogues)} WIN and {len(place_catalogues)} PLACE markets from Betfair API"
            )

            # Build catalogue lookup by market ID and collect all market IDs
            catalogue_map = {}
            market_ids = []
            market_type_map = {}

            for market in win_catalogues:
                mid = market.get('marketId') if isinstance(market, dict) else market.market_id
                if mid:
                    catalogue_map[mid] = market
                    market_ids.append(mid)
                    market_type_map[mid] = 'WIN'

            for market in place_catalogues:
                mid = market.get('marketId') if isinstance(market, dict) else market.market_id
                if mid:
                    catalogue_map[mid] = market
                    market_ids.append(mid)
                    market_type_map[mid] = 'PLACE'

            if not market_ids:
                self.logger.info("No horse racing markets found")
                return []

            # Fetch live market books in batches (API allows up to 40 per call)
            all_market_books = []
            for i in range(0, len(market_ids), 40):
                batch_ids = market_ids[i:i + 40]
                books = self.client.betting.list_market_book(
                    market_ids=batch_ids,
                    price_projection={
                        'priceData': ['EX_BEST_OFFERS'],
                    }
                )
                all_market_books.extend(books)

            self.logger.info(f"Got {len(all_market_books)} market books for {len(market_ids)} markets")

            # Process each market book, matching to its catalogue by market ID
            for idx, market_book in enumerate(all_market_books):
                # Get market ID from book
                if isinstance(market_book, dict):
                    book_market_id = market_book.get('marketId', '')
                else:
                    book_market_id = market_book.market_id

                catalogue = catalogue_map.get(book_market_id)
                if not catalogue:
                    self.logger.warning(f"No catalogue found for market book {book_market_id}")
                    continue

                mkt_type = market_type_map.get(book_market_id, 'WIN')

                try:
                    self.logger.info(f"Processing {mkt_type} market {idx+1}/{len(all_market_books)}: {book_market_id}")

                    # Handle both dict and object responses
                    if isinstance(catalogue, dict):
                        event_name = catalogue.get('event', {}).get('name')
                        venue = catalogue.get('event', {}).get('venue')
                        scheduled_time = datetime.fromisoformat(catalogue.get('marketStartTime', '').replace('Z', '+00:00'))
                        market_id = catalogue.get('marketId', '')
                        runners = catalogue.get('runners', [])
                        race_type = catalogue.get('description', {}).get('raceType')
                        market_name = catalogue.get('marketName', '')

                        if not event_name:
                            self.logger.warning(f"Skipping market with missing event name: {market_id}")
                            continue

                        runner_map = {
                            r.get('selectionId'): r.get('runnerName')
                            for r in runners
                        }
                    else:
                        event_name = catalogue.event.name if catalogue.event else None
                        venue = catalogue.event.venue if catalogue.event else None
                        race_type = catalogue.description.race_type if catalogue.description else None
                        market_name = catalogue.market_name if catalogue.market_name else ''

                        if not event_name:
                            self.logger.warning(f"Skipping market with missing event name")
                            continue
                        scheduled_time = catalogue.market_start_time
                        market_id = catalogue.market_id

                        runner_map = {
                            runner.selection_id: runner.runner_name
                            for runner in catalogue.runners
                        }

                    # Process each runner (horse)
                    if isinstance(market_book, dict):
                        runners_list = market_book.get('runners', [])
                    else:
                        runners_list = market_book.runners

                    self.logger.info(f"{mkt_type} market {market_id} has {len(runners_list)} runners, runner_map has {len(runner_map)} entries")

                    # Count only ACTIVE runners (exclude REMOVED/non-runners)
                    active_runners = 0
                    for runner in runners_list:
                        if isinstance(runner, dict):
                            status = runner.get('status', 'ACTIVE')
                        else:
                            status = runner.status if hasattr(runner, 'status') else 'ACTIVE'

                        if status == 'ACTIVE':
                            active_runners += 1

                    # Calculate place terms based on ACTIVE runners only
                    # Standard UK/Irish racing rules:
                    # 5-7 runners: 2 places, 1/5 odds
                    # 8-15 runners: 3 places, 1/5 odds
                    # 16+ runners: 4 places, 1/5 odds
                    if active_runners >= 16:
                        place_terms = "1/5 1-2-3-4"
                    elif active_runners >= 8:
                        place_terms = "1/5 1-2-3"
                    elif active_runners >= 5:
                        place_terms = "1/5 1-2"
                    else:
                        place_terms = None  # No each-way betting for races with less than 5 runners

                    self.logger.info(f"{mkt_type} market {market_id}: {len(runners_list)} total runners, {active_runners} active, place terms: {place_terms}")

                    if runners_list and len(odds_data_list) < 5:
                        self.logger.info(f"Sample runner: {runners_list[0] if isinstance(runners_list[0], dict) else 'object'}")

                    for runner_idx, runner in enumerate(runners_list):
                        try:
                            if isinstance(runner, dict):
                                selection_id = runner.get('selectionId')
                                horse_name = runner_map.get(selection_id)
                                if not horse_name:
                                    self.logger.debug(f"Skipping runner with no name (selection_id: {selection_id})")
                                    continue

                                ex_data = runner.get('ex', {})
                                available_to_back = ex_data.get('availableToBack', [])

                                if runner_idx == 0 and len(odds_data_list) < 3:
                                    self.logger.info(f"Sample runner for {horse_name}: has ex={bool(ex_data)}, availableToBack={len(available_to_back)} items")

                                if not available_to_back:
                                    continue

                                back_price = Decimal(str(available_to_back[0].get('price', 0)))
                                if back_price == 0:
                                    self.logger.debug(f"Zero back price for {horse_name}")
                                    continue

                                lay_price = None
                                available_to_lay = ex_data.get('availableToLay', [])
                                if available_to_lay:
                                    lay_price = Decimal(str(available_to_lay[0].get('price', 0)))
                            else:
                                selection_id = runner.selection_id
                                horse_name = runner_map.get(selection_id)
                                if not horse_name:
                                    self.logger.debug(f"Skipping runner with no name (selection_id: {selection_id})")
                                    continue

                                if runner.ex and runner.ex.available_to_back:
                                    best_back = runner.ex.available_to_back[0]
                                    back_price = Decimal(str(best_back.price))
                                else:
                                    continue

                                lay_price = None
                                if runner.ex and runner.ex.available_to_lay:
                                    best_lay = runner.ex.available_to_lay[0]
                                    lay_price = Decimal(str(best_lay.price))

                            runner_status = runner.get('status', 'ACTIVE') if isinstance(runner, dict) else runner.status

                            # Use different bookmaker names for WIN vs PLACE (needed for calculator)
                            if mkt_type == 'PLACE':
                                bk_name = "Betfair Exchange Place"
                                meta = {
                                    "market_id": market_id,
                                    "selection_id": selection_id,
                                    "source": "betfair_api",
                                    "status": runner_status,
                                    "market_type": "PLACE",
                                    "race_type": race_type,
                                    "market_name": market_name,
                                }
                            else:
                                bk_name = "Betfair Exchange"
                                meta = {
                                    "market_id": market_id,
                                    "selection_id": selection_id,
                                    "source": "betfair_api",
                                    "status": runner_status,
                                    "market_type": "WIN",
                                    "race_type": race_type,
                                    "market_name": market_name,
                                }

                            odds_data = OddsData(
                                event_name=event_name,
                                venue=venue,
                                scheduled_time=scheduled_time,
                                selection_name=horse_name,
                                odds_decimal=back_price,
                                place_odds=lay_price,
                                place_terms=place_terms,
                                bookmaker_name=bk_name,
                                event_type="horse_racing",
                                metadata=meta
                            )

                            odds_data_list.append(odds_data)
                            self.logger.debug(
                                f"API ({mkt_type}): {horse_name} @ {back_price} (back) / {lay_price} (lay)"
                            )

                        except Exception as e:
                            self.logger.debug(f"Error processing runner: {e}")
                            continue

                except Exception as e:
                    self.logger.error(f"Error processing market: {e}", exc_info=True)
                    continue

            win_count = sum(1 for o in odds_data_list if o.bookmaker_name == "Betfair Exchange")
            place_count = sum(1 for o in odds_data_list if o.bookmaker_name == "Betfair Exchange Place")
            self.logger.info(f"Scraped {len(odds_data_list)} odds from Betfair API ({win_count} WIN, {place_count} PLACE)")

        except Exception as e:
            self.logger.error(f"Error during Betfair API scrape: {e}", exc_info=True)

        return odds_data_list

    async def cleanup(self):
        """Logout and cleanup"""
        self.logger.info("Cleaning up Betfair API client...")
        if self.client:
            try:
                self.client.logout()
            except Exception as e:
                self.logger.error(f"Error during logout: {e}")
        self.is_running = False
        self.logger.info("Betfair API client cleanup complete")

    def health_check(self) -> bool:
        """Check if API client is healthy"""
        if not self.is_running or not self.client:
            return False

        try:
            # Try to keep alive - if this fails, we're not logged in
            self.client.keep_alive()
            return True
        except Exception as e:
            self.logger.error(f"Health check failed: {e}")
            return False
