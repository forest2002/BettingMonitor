import asyncio
import re
import random
from typing import List, Optional
from datetime import datetime, timedelta
from decimal import Decimal
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from models.schemas import OddsData
from services.scrapers.base import BookmakerScraper
import logging

logger = logging.getLogger(__name__)

# Oddschecker bookmaker codes -> display names
TARGET_BOOKMAKERS = {
    "PP": "Paddy Power",
    "B3": "Bet365",
    "BF": "Betfair Sportsbook",
    "WH": "William Hill",
    "SK": "Sky Bet",
    "LD": "Ladbrokes",
    "CE": "Coral",
    "BY": "Boylesports",
    "UN": "Unibet",
    "BD": "Betfred",
    "FR": "Betfred",
    "OE": "10Bet",
}


# UK and Irish racecourses (slug form as they appear in Oddschecker URLs)
UK_IRISH_VENUES = {
    'aintree', 'ascot', 'ayr', 'bangor-on-dee', 'bath', 'beverley',
    'brighton', 'carlisle', 'cartmel', 'catterick', 'chelmsford-city',
    'cheltenham', 'chepstow', 'chester', 'cork', 'curragh', 'doncaster',
    'down-royal', 'downpatrick', 'dundalk', 'epsom', 'exeter',
    'fairyhouse', 'fakenham', 'ffos-las', 'fontwell', 'galway',
    'goodwood', 'gowran-park', 'hamilton', 'haydock', 'hereford',
    'hexham', 'huntingdon', 'kelso', 'kempton', 'kilbeggan',
    'killarney', 'laytown', 'leicester', 'leopardstown', 'limerick',
    'lingfield', 'listowel', 'ludlow', 'market-rasen', 'musselburgh',
    'naas', 'navan', 'newbury', 'newcastle', 'newmarket', 'newton-abbot',
    'nottingham', 'perth', 'plumpton', 'pontefract', 'punchestown',
    'redcar', 'ripon', 'roscommon', 'salisbury', 'sandown',
    'sedgefield', 'sligo', 'southwell', 'stratford', 'taunton',
    'thirsk', 'thurles', 'tipperary', 'towcester', 'tramore',
    'uttoxeter', 'warwick', 'wetherby', 'wexford', 'wincanton',
    'winchester', 'windsor', 'wolverhampton', 'worcester', 'yarmouth',
    'york',
}


def _make_chrome_options() -> Options:
    """Create standard Chrome options for Oddschecker"""
    chrome_options = Options()
    chrome_options.add_argument('--headless=new')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-blink-features=AutomationControlled')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--window-size=1920,1080')
    chrome_options.add_argument(
        '--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
        'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    )
    chrome_options.binary_location = '/usr/bin/chromium'
    return chrome_options


def _new_driver() -> webdriver.Chrome:
    """Create a fresh Chrome driver instance"""
    service = Service('/usr/bin/chromedriver')
    driver = webdriver.Chrome(service=service, options=_make_chrome_options())
    driver.set_page_load_timeout(30)
    return driver


class OddscheckerScraper(BookmakerScraper):
    """Scraper that extracts odds from multiple bookmakers via Oddschecker.

    Uses a fresh browser session per page to avoid Cloudflare's
    per-session bot detection on subsequent navigations.
    """

    def __init__(self):
        super().__init__("oddschecker")
        self.base_url = "https://www.oddschecker.com/horse-racing"
        self.max_races = 60

    async def initialize(self):
        """Validate that Chrome driver can launch"""
        self.logger.info("Initializing Oddschecker scraper...")
        try:
            driver = _new_driver()
            driver.quit()
            self.is_running = True
            self.logger.info("Oddschecker scraper initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize scraper: {e}", exc_info=True)
            raise

    async def scrape(self) -> List[OddsData]:
        """Scrape odds from Oddschecker for multiple bookmakers"""
        odds_data_list = []

        try:
            # Step 1: get list of race URLs from the landing page
            race_links = await self._fetch_race_links()

            if not race_links:
                self.logger.info("No race links found on Oddschecker")
                return []

            self.logger.info(f"Found {len(race_links)} race links on Oddschecker")
            race_links = race_links[:self.max_races]

            # Step 2: scrape each race with a fresh driver
            for race_url in race_links:
                try:
                    race_odds = await self._scrape_race(race_url)
                    odds_data_list.extend(race_odds)
                    await asyncio.sleep(random.uniform(1.0, 2.5))
                except Exception as e:
                    self.logger.error(f"Error scraping race {race_url}: {e}")
                    continue

        except Exception as e:
            self.logger.error(f"Error during Oddschecker scrape: {e}", exc_info=True)

        self.logger.info(
            f"Oddschecker scrape complete: {len(odds_data_list)} total odds entries"
        )
        return odds_data_list

    async def _fetch_race_links(self) -> List[str]:
        """Load the landing page in a fresh driver and extract race URLs"""
        driver = _new_driver()
        try:
            driver.get(self.base_url)
            await asyncio.sleep(5)

            link_elements = driver.find_elements(
                By.CSS_SELECTOR, 'a[href*="/horse-racing/"]'
            )

            race_links = []
            for elem in link_elements:
                href = elem.get_attribute('href')
                if not href:
                    continue
                match = re.search(
                    r'/horse-racing/(?:\d{4}-\d{2}-\d{2}-)?([^/]+)/\d{2}:\d{2}/winner$',
                    href,
                )
                if match:
                    venue_slug = match.group(1)
                    if venue_slug in UK_IRISH_VENUES and href not in race_links:
                        race_links.append(href)

            return race_links
        except Exception as e:
            self.logger.error(f"Error fetching race links: {e}")
            return []
        finally:
            driver.quit()

    async def _scrape_race(self, race_url: str) -> List[OddsData]:
        """Scrape a single race page using a fresh driver"""
        odds_data_list = []
        driver = _new_driver()

        try:
            driver.get(race_url)
            await asyncio.sleep(3)

            # Check we didn't hit Cloudflare
            if 'Attention Required' in driver.title:
                self.logger.warning(f"Cloudflare blocked: {race_url}")
                return []

            try:
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located(
                        (By.CSS_SELECTOR, 'table.eventTable')
                    )
                )
            except TimeoutException:
                self.logger.debug(f"Timeout waiting for odds table on {race_url}")
                return []

            # Race metadata
            venue, race_time = self._parse_race_url(race_url)
            race_name = self._get_race_name(driver)
            scheduled_time = self._parse_race_time(race_time)
            event_name = race_name or f"{venue} {race_time}"

            place_terms = self._extract_each_way_terms(driver)

            # Runner rows
            runner_rows = driver.find_elements(By.CSS_SELECTOR, 'tr.diff-row')
            if not runner_rows:
                self.logger.debug(f"No runner rows for {race_url}")
                return []

            bookmakers_found = set()

            for row in runner_rows:
                try:
                    horse_name = (row.get_attribute('data-bname') or '').strip()
                    if not horse_name:
                        continue

                    cells = row.find_elements(By.CSS_SELECTOR, 'td[data-bk]')

                    for cell in cells:
                        bk_code = cell.get_attribute('data-bk')
                        if not bk_code or bk_code not in TARGET_BOOKMAKERS:
                            continue

                        bookmaker_name = TARGET_BOOKMAKERS[bk_code]

                        odig = cell.get_attribute('data-odig')
                        if not odig:
                            continue

                        odds_decimal = self._parse_odds(odig)
                        if odds_decimal is None:
                            continue

                        place_odds = None
                        if place_terms:
                            place_odds = self._calculate_place_odds(
                                odds_decimal, place_terms
                            )

                        odds_data_list.append(OddsData(
                            event_name=event_name,
                            venue=venue,
                            scheduled_time=scheduled_time,
                            selection_name=horse_name,
                            odds_decimal=odds_decimal,
                            place_odds=place_odds,
                            place_terms=place_terms,
                            bookmaker_name=bookmaker_name,
                            event_type="horse_racing",
                            metadata={
                                "race_time": race_time,
                                "source": "oddschecker",
                                "race_url": race_url,
                            }
                        ))
                        bookmakers_found.add(bookmaker_name)

                except Exception as e:
                    self.logger.debug(f"Error processing runner row: {e}")
                    continue

            self.logger.info(
                f"Scraped {len(odds_data_list)} odds from {event_name} "
                f"({', '.join(sorted(bookmakers_found))})"
            )

        except Exception as e:
            self.logger.error(f"Error scraping race {race_url}: {e}", exc_info=True)
        finally:
            driver.quit()

        return odds_data_list

    # --- helpers ---

    def _parse_race_url(self, url: str) -> tuple:
        venue = None
        race_time = ""
        match = re.search(r'/horse-racing/([^/]+)/(\d{2}:\d{2})', url)
        if match:
            raw_venue = match.group(1)
            # Strip date prefixes like "2026-02-14-" from venue slugs
            raw_venue = re.sub(r'^\d{4}-\d{2}-\d{2}-', '', raw_venue)
            venue = raw_venue.replace('-', ' ').title()
            race_time = match.group(2)
        return venue, race_time

    def _get_race_name(self, driver) -> Optional[str]:
        try:
            elems = driver.find_elements(By.CSS_SELECTOR, 'h1, .beta-title')
            if elems:
                text = elems[0].text.strip()
                if text:
                    return text
        except Exception:
            pass
        return None

    def _parse_race_time(self, time_text: str) -> datetime:
        try:
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

    def _extract_each_way_terms(self, driver) -> Optional[str]:
        try:
            elems = driver.find_elements(
                By.CSS_SELECTOR,
                '.each-way, .ew-terms, [class*="eachWay"], '
                '[class*="each-way"], .market-info'
            )
            for elem in elems:
                text = elem.text.strip()
                if re.search(r'\d+/\d+\s+[\d,\-]+', text):
                    return text
        except Exception:
            pass
        return None

    def _parse_odds(self, odds_text: str) -> Optional[Decimal]:
        try:
            odds_text = odds_text.strip()
            if not odds_text or odds_text in ('-', 'N/A', 'SP', 'NR', 'SUSP'):
                return None
            if odds_text == 'EVS':
                return Decimal("2.0")
            if '/' in odds_text:
                parts = odds_text.split('/')
                num = float(parts[0])
                den = float(parts[1])
                if den == 0:
                    return None
                return Decimal(str(round((num / den) + 1, 2)))
            val = float(odds_text.replace(',', ''))
            if val >= 1.01:
                return Decimal(str(round(val, 2)))
        except (ValueError, IndexError, ArithmeticError) as e:
            self.logger.debug(f"Failed to parse odds '{odds_text}': {e}")
        return None

    def _calculate_place_odds(
        self, odds_decimal: Decimal, place_terms: str
    ) -> Optional[Decimal]:
        try:
            match = re.search(r'(\d+)/(\d+)', place_terms)
            if match:
                fraction = Decimal(match.group(1)) / Decimal(match.group(2))
                place_odds = (odds_decimal - 1) * fraction + 1
                return Decimal(str(round(float(place_odds), 2)))
        except Exception:
            pass
        return None

    async def cleanup(self):
        """Nothing persistent to clean up — drivers are per-request"""
        self.is_running = False
        self.logger.info("Oddschecker scraper cleanup complete")
