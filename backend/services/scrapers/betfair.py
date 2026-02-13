import os
import asyncio
from typing import List
from datetime import datetime, timedelta
from decimal import Decimal
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from models.schemas import OddsData
from services.scrapers.base import BookmakerScraper
import logging

logger = logging.getLogger(__name__)

class BetfairScraper(BookmakerScraper):
    """Scraper for Betfair Exchange - the baseline for odds comparison"""

    def __init__(self):
        super().__init__("betfair")
        self.driver = None
        self.url = "https://www.betfair.com/exchange/plus/horse-racing"

    async def initialize(self):
        """Initialize Chrome driver"""
        self.logger.info("Initializing Betfair Exchange scraper...")

        try:
            # Setup Chrome options for Chromium
            chrome_options = Options()
            chrome_options.add_argument('--headless=new')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-blink-features=AutomationControlled')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--window-size=1920,1080')
            chrome_options.binary_location = '/usr/bin/chromium'

            # Use the installed chromedriver
            service = Service('/usr/bin/chromedriver')

            # Initialize driver
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            self.driver.get(self.url)

            # Wait for page load
            await asyncio.sleep(5)

            self.is_running = True
            self.logger.info("Betfair Exchange scraper initialized successfully")

        except Exception as e:
            self.logger.error(f"Failed to initialize scraper: {e}", exc_info=True)
            await self.cleanup()
            raise

    async def scrape(self) -> List[OddsData]:
        """Scrape Betfair Exchange odds for upcoming horse races"""
        if not self.driver:
            self.logger.error("Driver not initialized")
            return []

        odds_data_list = []

        try:
            # Refresh page to get latest data
            self.driver.refresh()
            await asyncio.sleep(3)

            # Find race cards (this is an example structure - actual selectors need to be discovered)
            # Betfair typically has race cards with market links
            races = self.driver.find_elements(By.CSS_SELECTOR, '[data-test-id="race-card"], .race-card, .event-item')

            if not races:
                self.logger.info("No races found on Betfair Exchange")
                return []

            self.logger.info(f"Found {len(races)} potential races on Betfair")

            # Process up to 5 races to avoid overload
            for race in races[:5]:
                try:
                    # Extract race details (these selectors are estimates and may need adjustment)
                    race_name = race.find_element(By.CSS_SELECTOR, '.event-name, .race-name, h3, h4').text
                    race_time_elem = race.find_elements(By.CSS_SELECTOR, '.event-time, .race-time, time')

                    if race_time_elem:
                        race_time_text = race_time_elem[0].text
                    else:
                        race_time_text = ""

                    # Try to extract venue
                    venue_elem = race.find_elements(By.CSS_SELECTOR, '.venue, .course-name')
                    venue = venue_elem[0].text if venue_elem else "Unknown"

                    # Parse time - estimate scheduled time
                    scheduled_time = self._parse_race_time(race_time_text)

                    # Click to see runners (if needed)
                    # For now, try to find runners in the current view
                    runners = race.find_elements(By.CSS_SELECTOR, '.runner-name, .selection-name, [data-test-id="runner"]')

                    if not runners:
                        self.logger.debug(f"No runners found for race: {race_name}")
                        continue

                    # Extract odds for each runner
                    for runner in runners[:10]:  # Limit to 10 horses per race
                        try:
                            horse_name = runner.text.strip()
                            if not horse_name:
                                continue

                            # Find back odds (lay odds are different)
                            odds_elem = runner.find_element(By.XPATH, './following-sibling::*[contains(@class, "back")]//span[@class="odds"]')
                            odds_text = odds_elem.text.strip()

                            # Betfair shows odds as decimal
                            odds_decimal = Decimal(odds_text)

                            odds_data = OddsData(
                                event_name=race_name,
                                venue=venue,
                                scheduled_time=scheduled_time,
                                selection_name=horse_name,
                                odds_decimal=odds_decimal,
                                place_odds=None,  # Betfair Exchange doesn't have each-way
                                place_terms=None,
                                bookmaker_name="Betfair Exchange",
                                event_type="horse_racing",
                                metadata={
                                    "race_time": race_time_text,
                                    "source": "betfair_exchange"
                                }
                            )

                            odds_data_list.append(odds_data)
                            self.logger.info(f"Scraped: {horse_name} @ {odds_decimal} (Betfair)")

                        except Exception as e:
                            self.logger.debug(f"Error processing runner: {e}")
                            continue

                except Exception as e:
                    self.logger.error(f"Error processing race: {e}", exc_info=True)
                    continue

        except Exception as e:
            self.logger.error(f"Error during scrape: {e}", exc_info=True)

        return odds_data_list

    def _parse_race_time(self, time_text: str) -> datetime:
        """Parse race time text to datetime"""
        try:
            # Try to parse time like "14:30" or "2:30pm"
            # For now, assume it's today
            from datetime import datetime
            import re

            # Extract time pattern
            match = re.search(r'(\d{1,2}):(\d{2})', time_text)
            if match:
                hour = int(match.group(1))
                minute = int(match.group(2))

                # Assume PM if hour < 12 and text contains 'pm'
                if 'pm' in time_text.lower() and hour < 12:
                    hour += 12

                # Create datetime for today
                now = datetime.now()
                scheduled = datetime(now.year, now.month, now.day, hour, minute)

                # If time has passed, assume tomorrow
                if scheduled < now:
                    scheduled += timedelta(days=1)

                return scheduled

        except Exception as e:
            self.logger.warning(f"Failed to parse race time '{time_text}': {e}")

        # Default: 1 hour from now
        return datetime.now() + timedelta(hours=1)

    async def cleanup(self):
        """Close browser and cleanup"""
        self.logger.info("Cleaning up Betfair scraper...")
        if self.driver:
            try:
                self.driver.quit()
            except Exception as e:
                self.logger.error(f"Error closing driver: {e}")
        self.is_running = False
        self.logger.info("Betfair scraper cleanup complete")
