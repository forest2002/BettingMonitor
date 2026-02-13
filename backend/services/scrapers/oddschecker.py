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
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from models.schemas import OddsData
from services.scrapers.base import BookmakerScraper
import logging

logger = logging.getLogger(__name__)

# Bookmakers we care about extracting from Oddschecker
TARGET_BOOKMAKERS = {
    "PP": "Paddy Power",
    "B3": "Bet365",
    "FB": "Betfair Sportsbook",
    "WH": "William Hill",
    "SK": "Sky Bet",
    "LD": "Ladbrokes",
    "CE": "Coral",
    "BY": "Boylesports",
    "UN": "Unibet",
    "BD": "Betfred",
    "RB": "188Bet",
    "OE": "10Bet",
}


class OddscheckerScraper(BookmakerScraper):
    """Scraper that extracts odds from multiple bookmakers via Oddschecker"""

    def __init__(self):
        super().__init__("oddschecker")
        self.driver = None
        self.base_url = "https://www.oddschecker.com/horse-racing"
        self.max_races = 15

    async def initialize(self):
        """Initialize Chrome driver"""
        self.logger.info("Initializing Oddschecker scraper...")

        try:
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

            service = Service('/usr/bin/chromedriver')
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            self.driver.set_page_load_timeout(30)

            self.driver.get(self.base_url)
            await asyncio.sleep(5)

            # Handle cookie consent
            try:
                cookie_buttons = self.driver.find_elements(
                    By.CSS_SELECTOR,
                    'button[id*="accept"], button[class*="accept"], '
                    '.cookie-consent-accept, #onetrust-accept-btn-handler'
                )
                if cookie_buttons:
                    cookie_buttons[0].click()
                    await asyncio.sleep(1)
            except Exception:
                pass

            self.is_running = True
            self.logger.info("Oddschecker scraper initialized successfully")

        except Exception as e:
            self.logger.error(f"Failed to initialize scraper: {e}", exc_info=True)
            await self.cleanup()
            raise

    async def scrape(self) -> List[OddsData]:
        """Scrape odds from Oddschecker for multiple bookmakers"""
        if not self.driver:
            self.logger.error("Driver not initialized")
            return []

        odds_data_list = []

        try:
            # Navigate to horse racing page
            self.driver.get(self.base_url)
            await asyncio.sleep(3)

            # Find race links
            race_links = self._find_race_links()

            if not race_links:
                self.logger.info("No race links found on Oddschecker")
                return []

            self.logger.info(f"Found {len(race_links)} race links on Oddschecker")

            # Limit races to avoid overload
            race_links = race_links[:self.max_races]

            for race_url in race_links:
                try:
                    race_odds = await self._scrape_race(race_url)
                    odds_data_list.extend(race_odds)

                    # Random delay between pages to avoid detection
                    await asyncio.sleep(random.uniform(1.5, 3.0))

                except Exception as e:
                    self.logger.error(f"Error scraping race {race_url}: {e}")
                    continue

        except Exception as e:
            self.logger.error(f"Error during Oddschecker scrape: {e}", exc_info=True)

        self.logger.info(
            f"Oddschecker scrape complete: {len(odds_data_list)} total odds entries"
        )
        return odds_data_list

    def _find_race_links(self) -> List[str]:
        """Find links to individual race pages"""
        race_links = []

        try:
            # Oddschecker race links follow pattern: /horse-racing/{venue}/{time}/winner
            link_elements = self.driver.find_elements(
                By.CSS_SELECTOR,
                'a[href*="/horse-racing/"][href*="/winner"]'
            )

            for elem in link_elements:
                href = elem.get_attribute('href')
                if href and '/winner' in href and href not in race_links:
                    race_links.append(href)

            # Fallback: look for race card links
            if not race_links:
                link_elements = self.driver.find_elements(
                    By.CSS_SELECTOR,
                    'a[href*="/horse-racing/"]'
                )
                for elem in link_elements:
                    href = elem.get_attribute('href')
                    if href and re.search(r'/horse-racing/[^/]+/\d{2}:\d{2}', href):
                        if href not in race_links:
                            race_links.append(href)

        except Exception as e:
            self.logger.error(f"Error finding race links: {e}")

        return race_links

    async def _scrape_race(self, race_url: str) -> List[OddsData]:
        """Scrape a single race page for all bookmaker odds"""
        odds_data_list = []

        self.driver.get(race_url)
        await asyncio.sleep(2)

        try:
            # Wait for odds table to load
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'table.eventTable, .odds-table, [class*="BettingTable"]'))
            )
        except TimeoutException:
            self.logger.debug(f"Timeout waiting for odds table on {race_url}")
            return []

        # Extract race metadata from URL and page
        venue, race_time = self._parse_race_url(race_url)
        race_name = self._get_race_name()
        scheduled_time = self._parse_race_time(race_time)
        event_name = race_name or f"{venue} {race_time}"

        # Extract each-way terms
        place_terms = self._extract_each_way_terms()

        # Build bookmaker column mapping
        bookmaker_columns = self._map_bookmaker_columns()

        if not bookmaker_columns:
            self.logger.debug(f"No bookmaker columns found for {race_url}")
            return []

        self.logger.info(
            f"Race: {event_name} — found columns for: "
            f"{', '.join(bookmaker_columns.values())}"
        )

        # Extract runner rows
        runner_rows = self.driver.find_elements(
            By.CSS_SELECTOR,
            'tr.diff-row, tr[class*="runner"], tbody tr[data-bname]'
        )

        for row in runner_rows:
            try:
                # Get horse name
                horse_name = self._extract_horse_name(row)
                if not horse_name:
                    continue

                # Get odds for each bookmaker column
                cells = row.find_elements(By.CSS_SELECTOR, 'td')

                for col_index, bookmaker_name in bookmaker_columns.items():
                    if col_index >= len(cells):
                        continue

                    odds_text = cells[col_index].get_attribute('data-odig') or cells[col_index].text.strip()

                    if not odds_text or odds_text in ('', '-', 'N/A', 'SP', 'NR', 'SUSP'):
                        continue

                    odds_decimal = self._parse_odds(odds_text)
                    if odds_decimal is None:
                        continue

                    # Calculate place odds if we have each-way terms
                    place_odds = None
                    if place_terms and odds_decimal:
                        place_odds = self._calculate_place_odds(odds_decimal, place_terms)

                    odds_data = OddsData(
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
                    )
                    odds_data_list.append(odds_data)

            except Exception as e:
                self.logger.debug(f"Error processing runner row: {e}")
                continue

        self.logger.info(
            f"Scraped {len(odds_data_list)} odds entries from {event_name}"
        )
        return odds_data_list

    def _map_bookmaker_columns(self) -> dict:
        """Map column indices to bookmaker names from the table header"""
        bookmaker_columns = {}

        try:
            # Try header cells with data-bk attribute (Oddschecker's format)
            header_cells = self.driver.find_elements(
                By.CSS_SELECTOR,
                'td[data-bk], th[data-bk], .bk-logo-click[data-bk]'
            )

            if header_cells:
                for cell in header_cells:
                    bk_code = cell.get_attribute('data-bk')
                    if bk_code and bk_code in TARGET_BOOKMAKERS:
                        # Find column index by counting preceding sibling cells
                        col_index = self._get_column_index(cell)
                        if col_index is not None:
                            bookmaker_columns[col_index] = TARGET_BOOKMAKERS[bk_code]
                return bookmaker_columns

            # Fallback: look for header cells with title attributes
            header_cells = self.driver.find_elements(
                By.CSS_SELECTOR,
                'thead td[title], thead th[title], .bk-logo-click[title]'
            )

            for cell in header_cells:
                title = cell.get_attribute('title') or ''
                for bk_code, bk_name in TARGET_BOOKMAKERS.items():
                    if bk_name.lower() in title.lower():
                        col_index = self._get_column_index(cell)
                        if col_index is not None:
                            bookmaker_columns[col_index] = bk_name
                        break

        except Exception as e:
            self.logger.error(f"Error mapping bookmaker columns: {e}")

        return bookmaker_columns

    def _get_column_index(self, cell) -> Optional[int]:
        """Get the column index of a table cell"""
        try:
            # Use JavaScript to get cellIndex
            index = self.driver.execute_script(
                "return arguments[0].cellIndex;", cell
            )
            return index
        except Exception:
            return None

    def _extract_horse_name(self, row) -> Optional[str]:
        """Extract horse name from a runner row"""
        try:
            # Try data-bname attribute first
            bname = row.get_attribute('data-bname')
            if bname:
                return bname.strip()

            # Try common selectors for horse name
            name_elem = row.find_elements(
                By.CSS_SELECTOR,
                '.popup a[data-name], .selTxt, a[class*="runner"], '
                'td.sel span, .nm span, [class*="horse-name"]'
            )
            if name_elem:
                return name_elem[0].text.strip()

            # Try first cell with text content
            first_cell = row.find_elements(By.CSS_SELECTOR, 'td.sel, td:first-child')
            if first_cell:
                text = first_cell[0].text.strip()
                # Remove jockey/trainer info (usually after newline)
                if text:
                    return text.split('\n')[0].strip()

        except Exception:
            pass

        return None

    def _parse_race_url(self, url: str) -> tuple:
        """Extract venue and time from race URL"""
        venue = None
        race_time = ""

        try:
            # URL pattern: /horse-racing/{venue}/{time}/winner
            match = re.search(r'/horse-racing/([^/]+)/(\d{2}:\d{2})', url)
            if match:
                venue = match.group(1).replace('-', ' ').title()
                race_time = match.group(2)
        except Exception:
            pass

        return venue, race_time

    def _get_race_name(self) -> Optional[str]:
        """Extract race name from the page"""
        try:
            name_elem = self.driver.find_elements(
                By.CSS_SELECTOR,
                'h1.racing-header, .page-description h1, '
                'h1[class*="race"], .race-details h1'
            )
            if name_elem:
                return name_elem[0].text.strip()
        except Exception:
            pass
        return None

    def _parse_race_time(self, time_text: str) -> datetime:
        """Parse race time to datetime"""
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

    def _extract_each_way_terms(self) -> Optional[str]:
        """Extract each-way terms from the race page"""
        try:
            ew_elems = self.driver.find_elements(
                By.CSS_SELECTOR,
                '.each-way, .ew-terms, [class*="eachWay"], '
                '[class*="each-way"], .market-info'
            )
            for elem in ew_elems:
                text = elem.text.strip()
                # Match patterns like "Each Way: 1/5 1,2,3" or "EW 1/4 1-2-3"
                if re.search(r'\d+/\d+\s+[\d,\-]+', text):
                    return text
        except Exception:
            pass
        return None

    def _parse_odds(self, odds_text: str) -> Optional[Decimal]:
        """Convert fractional or decimal odds text to decimal value"""
        try:
            odds_text = odds_text.strip()

            if not odds_text or odds_text in ('-', 'N/A', 'SP', 'NR', 'SUSP', 'EVS'):
                if odds_text == 'EVS':
                    return Decimal("2.0")
                return None

            # Fractional odds (e.g., "5/1", "11/4")
            if '/' in odds_text:
                parts = odds_text.split('/')
                numerator = float(parts[0])
                denominator = float(parts[1])
                if denominator == 0:
                    return None
                decimal_val = (numerator / denominator) + 1
                return Decimal(str(round(decimal_val, 2)))

            # Decimal odds
            cleaned = odds_text.replace(',', '')
            if cleaned.replace('.', '').isdigit():
                return Decimal(cleaned)

        except Exception as e:
            self.logger.debug(f"Failed to parse odds '{odds_text}': {e}")

        return None

    def _calculate_place_odds(self, odds_decimal: Decimal, place_terms: str) -> Optional[Decimal]:
        """Calculate place odds from win odds and each-way terms"""
        try:
            # Extract fraction from terms like "Each Way: 1/5 1,2,3"
            match = re.search(r'(\d+)/(\d+)', place_terms)
            if match:
                numerator = int(match.group(1))
                denominator = int(match.group(2))
                fraction = Decimal(str(numerator)) / Decimal(str(denominator))
                # Place odds = (win odds - 1) * fraction + 1
                place_odds = (odds_decimal - 1) * fraction + 1
                return Decimal(str(round(float(place_odds), 2)))
        except Exception:
            pass
        return None

    async def cleanup(self):
        """Close browser"""
        self.logger.info("Cleaning up Oddschecker scraper...")
        if self.driver:
            try:
                self.driver.quit()
            except Exception as e:
                self.logger.error(f"Error closing driver: {e}")
        self.is_running = False
        self.logger.info("Oddschecker scraper cleanup complete")
