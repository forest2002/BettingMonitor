#!/usr/bin/env python3
"""
Remove duplicate horses from EachWay Tracker Google Sheet.
Keeps only the first occurrence of each horse (by selection name).
"""
import os
import sys

try:
    import gspread
    from google.oauth2.service_account import Credentials
except ImportError:
    print("Error: gspread or google-auth not installed")
    sys.exit(1)

SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive',
]

SPREADSHEET_NAME = 'EachWay Tracker'

def clean_duplicates():
    """Remove duplicate horses from the sheet, keeping only first occurrence."""
    key_path = os.getenv(
        'GOOGLE_SERVICE_ACCOUNT_KEY_PATH',
        '/etc/gsheets/creds.json',
    )

    if not os.path.exists(key_path):
        print(f"Error: Google service account key not found at {key_path}")
        sys.exit(1)

    try:
        creds = Credentials.from_service_account_file(key_path, scopes=SCOPES)
        client = gspread.authorize(creds)
        spreadsheet = client.open(SPREADSHEET_NAME)
        sheet = spreadsheet.sheet1

        # Get all rows
        all_rows = sheet.get_all_values()

        if not all_rows:
            print("Sheet is empty")
            return

        print(f"Total rows in sheet: {len(all_rows)}")

        # Track which horses we've seen (column B is selection name)
        seen_horses = set()
        unique_rows = []

        # Deduplicate in memory
        for idx, row in enumerate(all_rows, start=1):
            if len(row) < 2:
                unique_rows.append(row)
                continue

            horse_name = row[1]  # Column B (0-indexed: column 1)

            if horse_name in seen_horses:
                print(f"Row {idx}: Duplicate found - {horse_name} (skipping)")
            else:
                seen_horses.add(horse_name)
                unique_rows.append(row)
                print(f"Row {idx}: First occurrence - {horse_name} (keeping)")

        duplicates_count = len(all_rows) - len(unique_rows)
        print(f"\nFound {duplicates_count} duplicate rows")

        if duplicates_count == 0:
            print("No duplicates found!")
            return

        print(f"\nClearing sheet and writing {len(unique_rows)} unique rows...")

        # Clear entire sheet
        sheet.clear()

        # Write back unique rows in one batch operation
        if unique_rows:
            sheet.update(range_name='A1', values=unique_rows)

        print(f"\n✓ Removed {duplicates_count} duplicate rows")
        print(f"✓ Sheet now has {len(unique_rows)} unique rows")

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    clean_duplicates()
