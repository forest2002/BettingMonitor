import os
import time
import asyncio
from typing import List
from datetime import datetime
from decimal import Decimal
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from models.schemas import OddsData
from services.scrapers.base import BookmakerScraper
import logging

logger = logging.getLogger(__name__)

class ProfitMaximiserScraper(BookmakerScraper):
    """Scraper for ProfitMaximiser EachWay Sniper tool"""

    def __init__(self):
        super().__init__("profit_maximiser")
        self.driver = None
        self.email = os.getenv('PROFIT_MAXIMISER_EMAIL')
        self.password = os.getenv('PROFIT_MAXIMISER_PASSWORD')
        self.url = "https://profitmaximiser.co.uk/mastermind/eachwaysniper/user/software2"

        if not self.email or not self.password:
            raise ValueError("PROFIT_MAXIMISER_EMAIL and PROFIT_MAXIMISER_PASSWORD must be set")

    async def initialize(self):
        """Initialize Chrome driver and login"""
        self.logger.info("Initializing ProfitMaximiser scraper...")

        try:
            # Setup Chrome options for Chromium
            chrome_options = Options()
            chrome_options.add_argument('--headless=new')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-blink-features=AutomationControlled')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.binary_location = '/usr/bin/chromium'

            # Use the installed chromedriver
            service = Service('/usr/bin/chromedriver')

            # Initialize driver
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            self.driver.get(self.url)

            # Wait for page load
            await asyncio.sleep(3)

            # Login
            self.logger.info("Logging in...")
            email_field = self.driver.find_element(By.NAME, "email")
            email_field.send_keys(self.email)

            password_field = self.driver.find_element(By.NAME, "password")
            password_field.send_keys(self.password)
            password_field.send_keys(Keys.RETURN)

            # Wait for login
            await asyncio.sleep(5)

            # Apply filters (Rating >= 97, EPV Rating >= 102, Min Odds >= 2)
            self.logger.info("Applying filters...")
            filter_btn = self.driver.find_element(
                By.CSS_SELECTOR,
                ".filter_btn > .win-command:nth-child(1) > .win-label"
            )
            filter_btn.click()
            await asyncio.sleep(1)

            # Set minimum rating
            min_rating_box = self.driver.find_element(By.ID, "minRating")
            min_rating_box.clear()
            min_rating_box.send_keys("97")

            # Set minimum EPV rating
            min_epv_rating_box = self.driver.find_element(By.ID, "minEPVRating")
            min_epv_rating_box.clear()
            min_epv_rating_box.send_keys("102")

            # Set minimum odds
            min_odds_box = self.driver.find_element(By.ID, "minOdds")
            min_odds_box.clear()
            min_odds_box.send_keys("2")

            # Apply filters
            apply_btn = self.driver.find_element(By.ID, "apply")
            apply_btn.click()

            # Close modal
            close_btn = self.driver.find_element(By.CSS_SELECTOR, "#basicModal .close")
            close_btn.click()
            await asyncio.sleep(1)

            # Click additional filter (if needed)
            extra_filter = self.driver.find_element(
                By.CSS_SELECTOR,
                ".win-command:nth-child(4) > .win-label"
            )
            extra_filter.click()

            self.is_running = True
            self.logger.info("ProfitMaximiser scraper initialized successfully")

        except Exception as e:
            self.logger.error(f"Failed to initialize scraper: {e}", exc_info=True)
            await self.cleanup()
            raise

    async def scrape(self) -> List[OddsData]:
        """Scrape current horse racing data"""
        if not self.driver:
            self.logger.error("Driver not initialized")
            return []

        odds_data_list = []

        try:
            # Find all horse selections
            horse_selections = self.driver.find_elements(By.NAME, 'tableUI')

            if not horse_selections:
                self.logger.info("No horse selections found")
                return []

            self.logger.info(f"Found {len(horse_selections)} horse selections")

            for horse_selection in horse_selections:
                try:
                    # Extract data using XPath (same as original)
                    horse_name = horse_selection.find_element(
                        By.XPATH, './/*[@id="data_body"]/tr[1]/td[3]'
                    ).text

                    price_text = horse_selection.find_element(
                        By.XPATH, './/*[@id="data_body"]/tr[1]/td[6]'
                    ).text

                    race_details = horse_selection.find_element(
                        By.XPATH, './/*[@id="data_body"]/tr[1]/td[2]'
                    ).text

                    bookie_image = horse_selection.find_element(
                        By.XPATH, './/*[@id="data_body"]/tr[1]/td[5]/img'
                    )
                    bookie_name = bookie_image.get_attribute('alt')

                    rating = horse_selection.find_element(
                        By.XPATH, './/*[@id="data_body"]/tr[1]/td[1]/span'
                    ).text

                    places_text = horse_selection.find_element(
                        By.XPATH, './/*[@id="data_body"]/tr[1]/td[9]'
                    ).text

                    # Parse place odds and terms
                    places_split = places_text.split('\n')
                    place_odds_text = places_split[0] if len(places_split) > 0 else None
                    place_terms = places_split[2] if len(places_split) > 2 else None

                    # Parse race details
                    race_details_split = race_details.split('\n')
                    venue = race_details_split[0] if len(race_details_split) > 0 else "Unknown"
                    date_of_race = race_details_split[1] if len(race_details_split) > 1 else ""
                    time_of_race = race_details_split[2] if len(race_details_split) > 2 else ""

                    # Parse scheduled time
                    try:
                        # Combine date and time
                        datetime_str = f"{date_of_race} {time_of_race}"
                        scheduled_time = datetime.strptime(datetime_str, "%d/%m/%Y %H:%M")
                        # Set to current year if parsing fails
                        if scheduled_time.year < datetime.now().year:
                            scheduled_time = scheduled_time.replace(year=datetime.now().year)
                    except Exception as e:
                        self.logger.warning(f"Failed to parse datetime '{datetime_str}': {e}")
                        # Default to 1 hour from now
                        scheduled_time = datetime.now()

                    # Convert odds to decimal
                    try:
                        odds_decimal = Decimal(str(price_text))
                        place_odds_decimal = Decimal(str(place_odds_text)) if place_odds_text else None
                    except Exception as e:
                        self.logger.warning(f"Failed to parse odds for {horse_name}: {e}")
                        continue

                    # Create event name
                    event_name = f"{venue} {time_of_race}"

                    # Create OddsData object
                    odds_data = OddsData(
                        event_name=event_name,
                        venue=venue,
                        scheduled_time=scheduled_time,
                        selection_name=horse_name,
                        odds_decimal=odds_decimal,
                        place_odds=place_odds_decimal,
                        place_terms=place_terms,
                        bookmaker_name=bookie_name,
                        event_type="horse_racing",
                        metadata={
                            "rating": rating,
                            "date_of_race": date_of_race,
                            "time_of_race": time_of_race
                        }
                    )

                    odds_data_list.append(odds_data)
                    self.logger.info(f"Scraped: {horse_name} @ {odds_decimal} from {bookie_name}")

                    # Delete the entry from the webpage (like original scraper)
                    await asyncio.sleep(0.5)
                    delete_button = horse_selection.find_element(
                        By.CSS_SELECTOR, "tr:nth-child(1) .icon-del-horse"
                    )
                    self.driver.execute_script("arguments[0].click();", delete_button)

                except Exception as e:
                    self.logger.error(f"Error processing horse selection: {e}", exc_info=True)
                    continue

        except Exception as e:
            self.logger.error(f"Error during scrape: {e}", exc_info=True)

        return odds_data_list

    async def cleanup(self):
        """Close browser and cleanup"""
        self.logger.info("Cleaning up ProfitMaximiser scraper...")
        if self.driver:
            try:
                self.driver.quit()
            except Exception as e:
                self.logger.error(f"Error closing driver: {e}")
        self.is_running = False
        self.logger.info("ProfitMaximiser scraper cleanup complete")
