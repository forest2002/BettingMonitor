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

# Track which opportunities have already been appended (selection+event only, no duplicates)
_appended_keys: Set[str] = set()


def _opp_key(opp: Dict) -> str:
    """Generate unique key for horse (no bookmaker, prevents duplicates)"""
    return f"{opp['selection_name']}::{opp['event_name']}"


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

    # Filter to only new opportunities (deduplicate within batch AND across session)
    new_opps = []
    seen_in_batch = set()
    for opp in opportunities:
        key = _opp_key(opp)
        if key not in _appended_keys and key not in seen_in_batch:
            new_opps.append(opp)
            seen_in_batch.add(key)

    if not new_opps:
        return

    client = _get_client()
    if client is None:
        return

    try:
        spreadsheet = client.open(SPREADSHEET_NAME)
        sheet = spreadsheet.sheet1

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

        # Mark as appended only after successful write
        for opp in new_opps:
            _appended_keys.add(_opp_key(opp))

        logger.info(f"Appended {len(rows)} new rows to Google Sheet '{SPREADSHEET_NAME}'")

    except Exception as e:
        logger.error(f"Failed to append to Google Sheet: {e}", exc_info=True)
