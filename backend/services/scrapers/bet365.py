import os
import asyncio
from typing import List
from datetime import datetime, timedelta
from decimal import Decimal
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from models.schemas import OddsData
from services.scrapers.base import BookmakerScraper
import logging

logger = logging.getLogger(__name__)

class Bet365Scraper(BookmakerScraper):
    """Scraper for Bet365 odds"""

    def __init__(self):
        super().__init__("bet365")
        self.driver = None
        self.url = "https://www.bet365.com/#/HO/"  # Horse racing section

    async def initialize(self):
        """Initialize Chrome driver"""
        self.logger.info("Initializing Bet365 scraper...")

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

            # Bet365 is heavily JavaScript-based, needs more wait time
            await asyncio.sleep(8)

            # Handle cookie consent
            try:
                cookie_buttons = self.driver.find_elements(By.CSS_SELECTOR,
                    '.ccm-CookieConsentPopup_Accept, button[class*="accept"]')
                if cookie_buttons:
                    cookie_buttons[0].click()
                    await asyncio.sleep(2)
            except:
                pass

            self.is_running = True
            self.logger.info("Bet365 scraper initialized successfully")

        except Exception as e:
            self.logger.error(f"Failed to initialize scraper: {e}", exc_info=True)
            await self.cleanup()
            raise

    async def scrape(self) -> List[OddsData]:
        """Scrape Bet365 odds"""
        if not self.driver:
            self.logger.error("Driver not initialized")
            return []

        odds_data_list = []

        try:
            # Bet365 uses heavy JavaScript, so we need to wait for content
            await asyncio.sleep(5)

            # Find race sections (Bet365 has unique class names that change)
            races = self.driver.find_elements(By.CSS_SELECTOR,
                '[class*="RaceCard"], [class*="racecard"], [class*="meeting-event"]')

            if not races:
                self.logger.info("No races found on Bet365")
                return []

            self.logger.info(f"Found {len(races)} races on Bet365")

            for race in races[:5]:
                try:
                    # Bet365 uses complex nested structures
                    race_name_elem = race.find_elements(By.CSS_SELECTOR,
                        '[class*="RaceHeader"], [class*="event-header"], span, div')
                    race_name = None
                    for elem in race_name_elem:
                        text = elem.text.strip()
                        if text and len(text) > 5:
                            race_name = text
                            break

                    if not race_name:
                        self.logger.debug("Skipping race with no name on Bet365")
                        continue

                    # Extract time
                    time_elem = race.find_elements(By.CSS_SELECTOR,
                        '[class*="Time"], [class*="time"], span')
                    race_time = ""
                    for elem in time_elem:
                        text = elem.text.strip()
                        if ':' in text:
                            race_time = text
                            break

                    scheduled_time = self._parse_race_time(race_time)

                    # Find runners (Bet365 has complex selectors)
                    runners = race.find_elements(By.CSS_SELECTOR,
                        '[class*="Runner"], [class*="runner"], [class*="Participant"]')

                    if not runners:
                        # Try alternative selector
                        runners = race.find_elements(By.CSS_SELECTOR, 'div[class*="gl-"]')

                    for runner in runners[:10]:
                        try:
                            # Extract horse name
                            name_elem = runner.find_elements(By.CSS_SELECTOR,
                                'span, div[class*="name"], [class*="Runner"]')
                            horse_name = ""
                            for elem in name_elem:
                                text = elem.text.strip()
                                if text and len(text) > 2:
                                    horse_name = text
                                    break

                            if not horse_name:
                                continue

                            # Extract odds
                            odds_elem = runner.find_elements(By.CSS_SELECTOR,
                                '[class*="Odds"], [class*="odds"], span[class*="gl-"]')

                            odds_text = ""
                            for elem in odds_elem:
                                text = elem.text.strip()
                                if text and ('/' in text or text.replace('.', '').isdigit()):
                                    odds_text = text
                                    break

                            if not odds_text:
                                continue

                            odds_decimal = self._parse_odds(odds_text)

                            odds_data = OddsData(
                                event_name=race_name,
                                venue=None,  # Bet365 venue extraction needs custom selectors
                                scheduled_time=scheduled_time,
                                selection_name=horse_name,
                                odds_decimal=odds_decimal,
                                place_odds=None,
                                place_terms=None,
                                bookmaker_name="Bet365",
                                event_type="horse_racing",
                                metadata={
                                    "race_time": race_time,
                                    "source": "bet365"
                                }
                            )

                            odds_data_list.append(odds_data)
                            self.logger.info(f"Scraped: {horse_name} @ {odds_decimal} (Bet365)")

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
        """Convert odds to decimal"""
        try:
            odds_text = odds_text.strip()

            # Fractional odds
            if '/' in odds_text:
                parts = odds_text.split('/')
                numerator = float(parts[0])
                denominator = float(parts[1])
                decimal = (numerator / denominator) + 1
                return Decimal(str(round(decimal, 2)))

            # Decimal odds
            return Decimal(odds_text)

        except Exception as e:
            self.logger.warning(f"Failed to parse odds '{odds_text}': {e}")
            return Decimal("2.0")

    def _parse_race_time(self, time_text: str) -> datetime:
        """Parse race time"""
        try:
            import re
            match = re.search(r'(\d{1,2}):(\d{2})', time_text)
            if match:
                hour = int(match.group(1))
                minute = int(match.group(2))

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
        self.logger.info("Cleaning up Bet365 scraper...")
        if self.driver:
            try:
                self.driver.quit()
            except Exception as e:
                self.logger.error(f"Error closing driver: {e}")
        self.is_running = False
        self.logger.info("Bet365 scraper cleanup complete")
