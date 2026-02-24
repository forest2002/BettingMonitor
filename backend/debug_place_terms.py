#!/usr/bin/env python3
"""Debug script to check Oddschecker place terms display.

Picks the first available UK race dynamically rather than requiring a
specific venue/time to be hardcoded.
"""

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
import re
import time

UK_VENUES = {
    'ascot', 'bath', 'brighton', 'carlisle', 'catterick', 'chelmsford',
    'cheltenham', 'chester', 'chepstow', 'doncaster', 'epsom', 'exeter',
    'fakenham', 'ffos-las', 'goodwood', 'hamilton', 'haydock', 'hereford',
    'huntingdon', 'kempton', 'leicester', 'lingfield', 'ludlow', 'market-rasen',
    'musselburgh', 'newbury', 'newcastle', 'newton-abbot', 'nottingham',
    'perth', 'plumpton', 'pontefract', 'redcar', 'ripon', 'salisbury',
    'sandown', 'sedgefield', 'southwell', 'stratford', 'taunton', 'thirsk',
    'uttoxeter', 'warwick', 'wetherby', 'wincanton', 'windsor', 'wolverhampton',
    'worcester', 'yarmouth', 'york', 'bangor-on-dee',
}


def make_chrome_options():
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
    return chrome_options


def is_uk_race(href: str) -> bool:
    """Return True if the race URL is for a UK venue."""
    match = re.search(r'/horse-racing/(?:\d{4}-\d{2}-\d{2}-)?([^/]+)/\d{2}:\d{2}', href)
    if not match:
        return False
    venue = match.group(1).lower()
    # Strip leading date prefix if present (e.g. "2026-02-24-newbury" -> "newbury")
    venue = re.sub(r'^\d{4}-\d{2}-\d{2}-', '', venue)
    return venue in UK_VENUES


print("Loading Oddschecker horse racing page...")
service = Service()
driver = webdriver.Chrome(service=service, options=make_chrome_options())

try:
    driver.get("https://www.oddschecker.com/horse-racing")
    time.sleep(5)

    # Find all race winner links
    link_elements = driver.find_elements(By.CSS_SELECTOR, 'a[href*="/horse-racing/"]')

    # Collect all unique UK race URLs
    uk_races = []
    seen = set()
    for elem in link_elements:
        href = elem.get_attribute('href')
        if href and '/winner' in href and href not in seen and is_uk_race(href):
            uk_races.append(href)
            seen.add(href)

    if not uk_races:
        print("ERROR: No UK races found on the page.")
        # List everything we did find so it's easy to diagnose
        print("\nAll races found:")
        seen_all = set()
        for elem in link_elements:
            href = elem.get_attribute('href')
            if href and '/winner' in href and href not in seen_all:
                m = re.search(r'/horse-racing/(?:\d{4}-\d{2}-\d{2}-)?([^/]+)/(\d{2}:\d{2})/winner', href)
                if m:
                    print(f"  {m.group(1)} {m.group(2)}")
                    seen_all.add(href)
        driver.quit()
        exit(1)

    # Use the first available UK race
    race_url = uk_races[0]
    m = re.search(r'/horse-racing/(?:\d{4}-\d{2}-\d{2}-)?([^/]+)/(\d{2}:\d{2})/winner', race_url)
    label = f"{m.group(1)} {m.group(2)}" if m else race_url

    print(f"\nUsing race: {label}")
    print(f"URL: {race_url}")
    print(f"(Found {len(uk_races)} UK races total)\n")

    # Load the race page
    print("Loading race page...")
    driver.get(race_url)
    time.sleep(5)

    print("\n" + "=" * 80)
    print("SEARCHING FOR EACH-WAY TERMS")
    print("=" * 80)

    # --- Strategy 0: data-ew-denom / data-ew-places attributes (most reliable) ---
    print("\n0. Checking data-ew-denom / data-ew-places attributes:")
    cells = driver.find_elements(By.CSS_SELECTOR, 'td[data-ew-denom][data-ew-places]')
    if cells:
        cell = cells[0]
        denom = cell.get_attribute('data-ew-denom')
        num_places = cell.get_attribute('data-ew-places')
        places = '-'.join(str(i) for i in range(1, int(num_places) + 1))
        print(f"  FOUND: 1/{denom} {places}  (from {len(cells)} cells)")
    else:
        print("  Not found.")

    # --- Strategy 1: CSS selectors for explicit each-way elements ---
    selectors = [
        '.each-way', '.ew-terms', '[class*="eachWay"]', '[class*="each-way"]',
        '.market-info', '.race-info', '[class*="marketInfo"]',
        '[class*="raceInfo"]', '.extra-places', '[class*="place"]',
    ]
    print("\n1. Checking CSS selectors for each-way terms:")
    found_any = False
    for selector in selectors:
        try:
            elems = driver.find_elements(By.CSS_SELECTOR, selector)
            for elem in elems[:3]:
                text = elem.text.strip()
                if text and len(text) < 200 and any(t in text.lower() for t in ['1/4', '1/5', 'each way', 'places']):
                    print(f"  [{selector}] {text}")
                    found_any = True
        except Exception:
            pass
    if not found_any:
        print("  Nothing matching found.")

    # --- Strategy 2: Page source keyword scan ---
    print("\n2. Searching page source for each-way patterns:")
    page_source = driver.page_source.lower()
    lines_with_ew = []
    for line in page_source.split('\n'):
        if any(term in line for term in ['each way', 'each-way', '1/4', '1/5', 'places']):
            clean_line = re.sub(r'<[^>]+>', ' ', line)
            clean_line = ' '.join(clean_line.split())
            if clean_line and len(clean_line) < 300:
                lines_with_ew.append(clean_line)
    unique_lines = list(dict.fromkeys(lines_with_ew))[:10]
    for line in unique_lines:
        if '1/' in line:
            print(f"  {line[:200]}")
    if not unique_lines:
        print("  Nothing found.")

    # --- Strategy 3: Runner count (current production method) ---
    print("\n3. Runner count (current production fallback):")
    runner_rows = driver.find_elements(By.CSS_SELECTOR, 'tr[data-bname]')
    num_runners = len(runner_rows)
    if num_runners >= 16:
        fallback_terms = "1/5 1-2-3-4"
    elif num_runners >= 8:
        fallback_terms = "1/5 1-2-3"
    elif num_runners >= 5:
        fallback_terms = "1/5 1-2"
    else:
        fallback_terms = None
    print(f"  {num_runners} runner rows found → place terms: {fallback_terms}")

    # --- Strategy 4: Regex on page source ---
    print("\n4. Pattern matching in page source:")
    patterns = [
        (r'(1/[45])\s*(?:odds?)?\s*(\d)\s*(?:places?)', 'Format: "1/4 odds 3 places"'),
        (r'(1/[45])\s*(?:odds?)?\s*(\d+[\-,]\d+)', 'Format: "1/4 1-2-3"'),
        (r'each\s*way[:\s]+(1/[45])', 'Format: "Each Way: 1/4"'),
    ]
    found_pattern = False
    for pattern, description in patterns:
        matches = re.findall(pattern, page_source, re.IGNORECASE)
        if matches:
            print(f"  {description}")
            print(f"    Found: {matches[:5]}")
            found_pattern = True
    if not found_pattern:
        print("  No patterns matched.")

    print("\n" + "=" * 80)

finally:
    driver.quit()

print("\nDone!")
