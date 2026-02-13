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

class PaddyPowerScraper(BookmakerScraper):
    """Scraper for Paddy Power odds"""

    def __init__(self):
        super().__init__("paddy_power")
        self.driver = None
        self.url = "https://www.paddypower.com/horse-racing"

    async def initialize(self):
        """Initialize Chrome driver"""
        self.logger.info("Initializing Paddy Power scraper...")

        try:
            chrome_options = Options()
            chrome_options.add_argument('--headless=new')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-blink-features=AutomationControlled')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--window-size=1920,1080')
            chrome_options.binary_location = '/usr/bin/chromium'

            service = Service('/usr/bin/chromedriver')
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            self.driver.get(self.url)

            # Wait for page load and handle cookie consent
            await asyncio.sleep(5)

            # Try to accept cookies if present
            try:
                cookie_button = self.driver.find_elements(By.CSS_SELECTOR,
                    'button[class*="accept"], button[id*="accept"], button[class*="cookie"]')
                if cookie_button:
                    cookie_button[0].click()
                    await asyncio.sleep(1)
            except:
                pass

            self.is_running = True
            self.logger.info("Paddy Power scraper initialized successfully")

        except Exception as e:
            self.logger.error(f"Failed to initialize scraper: {e}", exc_info=True)
            await self.cleanup()
            raise

    async def scrape(self) -> List[OddsData]:
        """Scrape Paddy Power odds"""
        if not self.driver:
            self.logger.error("Driver not initialized")
            return []

        odds_data_list = []

        try:
            self.driver.refresh()
            await asyncio.sleep(3)

            # Find race cards (selectors are estimates)
            races = self.driver.find_elements(By.CSS_SELECTOR,
                '[class*="race-card"], [class*="event-card"], [data-testid*="race"]')

            if not races:
                self.logger.info("No races found on Paddy Power")
                return []

            self.logger.info(f"Found {len(races)} races on Paddy Power")

            for race in races[:5]:
                try:
                    # Extract race details
                    race_name_elem = race.find_elements(By.CSS_SELECTOR,
                        '[class*="race-name"], [class*="event-name"], h3, h4')
                    race_name = race_name_elem[0].text if race_name_elem else None
                    if not race_name:
                        self.logger.debug("Skipping race with no name")
                        continue

                    time_elem = race.find_elements(By.CSS_SELECTOR,
                        '[class*="time"], time, [class*="race-time"]')
                    race_time = time_elem[0].text if time_elem else ""

                    venue_elem = race.find_elements(By.CSS_SELECTOR,
                        '[class*="venue"], [class*="course"]')
                    venue = venue_elem[0].text if venue_elem else None

                    scheduled_time = self._parse_race_time(race_time)

                    # Find runners
                    runners = race.find_elements(By.CSS_SELECTOR,
                        '[class*="runner"], [class*="selection"], [data-testid*="runner"]')

                    for runner in runners[:10]:
                        try:
                            # Extract horse name
                            name_elem = runner.find_elements(By.CSS_SELECTOR,
                                '[class*="runner-name"], [class*="selection-name"], span, strong')
                            horse_name = name_elem[0].text.strip() if name_elem else ""

                            if not horse_name:
                                continue

                            # Extract odds - Paddy Power uses fractional or decimal
                            odds_elem = runner.find_elements(By.CSS_SELECTOR,
                                '[class*="odds"], [class*="price"], button[class*="odds"]')

                            if not odds_elem:
                                continue

                            odds_text = odds_elem[0].text.strip()

                            # Convert to decimal
                            odds_decimal = self._parse_odds(odds_text)

                            # Try to find each-way terms
                            ew_elem = runner.find_elements(By.CSS_SELECTOR,
                                '[class*="each-way"], [class*="ew"]')
                            place_terms = ew_elem[0].text if ew_elem else None

                            odds_data = OddsData(
                                event_name=race_name,
                                venue=venue,
                                scheduled_time=scheduled_time,
                                selection_name=horse_name,
                                odds_decimal=odds_decimal,
                                place_odds=None,  # Can be calculated from terms
                                place_terms=place_terms,
                                bookmaker_name="Paddy Power",
                                event_type="horse_racing",
                                metadata={
                                    "race_time": race_time,
                                    "source": "paddypower"
                                }
                            )

                            odds_data_list.append(odds_data)
                            self.logger.info(f"Scraped: {horse_name} @ {odds_decimal} (Paddy Power)")

                        except Exception as e:
                            self.logger.debug(f"Error processing runner: {e}")
                            continue

                except Exception as e:
                    self.logger.error(f"Error processing race: {e}", exc_info=True)
                    continue

        except Exception as e:
            self.logger.error(f"Error during scrape: {e}", exc_info=True)

        return odds_data_list

    def _parse_odds(self, odds_text: str) -> Decimal:
        """Convert fractional or decimal odds to decimal"""
        try:
            # Remove whitespace and currency symbols
            odds_text = odds_text.strip().replace('£', '').replace('€', '')

            # Check if fractional (e.g., "5/1", "11/4")
            if '/' in odds_text:
                parts = odds_text.split('/')
                numerator = float(parts[0])
                denominator = float(parts[1])
                decimal = (numerator / denominator) + 1
                return Decimal(str(round(decimal, 2)))

            # Otherwise assume decimal
            return Decimal(odds_text)

        except Exception as e:
            self.logger.warning(f"Failed to parse odds '{odds_text}': {e}")
            return Decimal("2.0")  # Default

    def _parse_race_time(self, time_text: str) -> datetime:
        """Parse race time to datetime"""
        try:
            import re
            match = re.search(r'(\d{1,2}):(\d{2})', time_text)
            if match:
                hour = int(match.group(1))
                minute = int(match.group(2))

                if 'pm' in time_text.lower() and hour < 12:
                    hour += 12

                now = datetime.now()
                scheduled = datetime(now.year, now.month, now.day, hour, minute)

                if scheduled < now:
                    scheduled += timedelta(days=1)

                return scheduled

        except Exception as e:
            self.logger.warning(f"Failed to parse time '{time_text}': {e}")

        return datetime.now() + timedelta(hours=1)

    async def cleanup(self):
        """Close browser"""
        self.logger.info("Cleaning up Paddy Power scraper...")
        if self.driver:
            try:
                self.driver.quit()
            except Exception as e:
                self.logger.error(f"Error closing driver: {e}")
        self.is_running = False
        self.logger.info("Paddy Power scraper cleanup complete")
