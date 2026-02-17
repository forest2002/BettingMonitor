"""
Google Sheets integration for logging opportunities to EachWay Tracker.

Imports gspread lazily so the app still starts if the package isn't installed.
"""
import os
import logging
from typing import List, Dict, Set

logger = logging.getLogger(__name__)

SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive',
]

SPREADSHEET_NAME = 'EachWay Tracker'

_client = None
_spreadsheet_url: str | None = None

def _opp_key(opp: Dict) -> str:
    """Generate unique key for horse (no bookmaker, prevents duplicates)"""
    return f"{opp['selection_name']}::{opp['event_name']}"


def _get_existing_horses(sheet) -> Set[str]:
    """Get set of horses already in the sheet (column B)"""
    try:
        all_values = sheet.get_all_values()
        # Column B (index 1) contains selection names
        existing = {row[1] for row in all_values if len(row) > 1 and row[1]}
        logger.info(f"Found {len(existing)} existing horses in sheet")
        return existing
    except Exception as e:
        logger.warning(f"Could not read existing horses from sheet: {e}")
        return set()


def _get_client():
    global _client
    if _client is not None:
        return _client

    try:
        import gspread
        from google.oauth2.service_account import Credentials
    except ImportError:
        logger.warning("gspread or google-auth not installed, Google Sheets integration disabled")
        return None

    key_path = os.getenv(
        'GOOGLE_SERVICE_ACCOUNT_KEY_PATH',
        '/etc/gsheets/creds.json',
    )

    if not os.path.exists(key_path):
        logger.warning(f"Google service account key not found at {key_path}")
        return None

    try:
        creds = Credentials.from_service_account_file(key_path, scopes=SCOPES)
        _client = gspread.authorize(creds)
        return _client
    except Exception as e:
        logger.error(f"Failed to authorize Google Sheets client: {e}", exc_info=True)
        return None


def get_spreadsheet_url() -> str | None:
    """Return the URL of the EachWay Tracker spreadsheet, or None."""
    global _spreadsheet_url
    if _spreadsheet_url is not None:
        return _spreadsheet_url

    client = _get_client()
    if client is None:
        return None

    try:
        spreadsheet = client.open(SPREADSHEET_NAME)
        _spreadsheet_url = spreadsheet.url
        return _spreadsheet_url
    except Exception as e:
        logger.error(f"Failed to get spreadsheet URL: {e}", exc_info=True)
        return None


def append_opportunities(opportunities: List[Dict]) -> None:
    """
    Append NEW opportunity rows to the EachWay Tracker spreadsheet.
    Skips opportunities that have already been appended this session.

    Columns:
        A - Provider name (always 'EachWayTracker')
        B - Selection name (horse name)
        C - MarketType (always 'Win')
        D - Price (bookmaker win odds)
        E - Rating (percentage rating)
    """
    if not opportunities:
        return

    logger.info(f"append_opportunities called with {len(opportunities)} opportunities")

    client = _get_client()
    if client is None:
        return

    try:
        spreadsheet = client.open(SPREADSHEET_NAME)
        sheet = spreadsheet.sheet1

        # Get existing horses from sheet (persistent deduplication)
        existing_horses = _get_existing_horses(sheet)

        # Filter to only new opportunities (deduplicate within batch AND against sheet)
        new_opps = []
        seen_in_batch = set()
        for opp in opportunities:
            horse_name = opp['selection_name']

            if horse_name in existing_horses:
                logger.debug(f"Already in sheet: {horse_name}")
            elif horse_name in seen_in_batch:
                logger.debug(f"Duplicate in batch: {horse_name}")
            else:
                new_opps.append(opp)
                seen_in_batch.add(horse_name)
                logger.debug(f"New opportunity: {horse_name}")

        if not new_opps:
            logger.info("No new opportunities to append")
            return

        rows = []
        for opp in new_opps:
            rows.append([
                'EachWayTracker',
                opp['selection_name'],
                'Win',
                opp['bookmaker_win_odds'],
                opp['rating'],
            ])

        sheet.append_rows(rows, value_input_option='USER_ENTERED')
        logger.info(f"Appended {len(rows)} new rows to Google Sheet '{SPREADSHEET_NAME}'")

    except Exception as e:
        logger.error(f"Failed to append to Google Sheet: {e}", exc_info=True)
