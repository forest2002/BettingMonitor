#!/usr/bin/env python3
"""
Add test data to demonstrate the each-way tracker system

WARNING: This script inserts FAKE test data into the database.
Only run this in development/testing environments.
"""
import asyncio
import os
import sys
from datetime import datetime, timedelta
from decimal import Decimal
sys.path.append('/app')

from db.database import db


def _confirm_test_environment():
    """Prevent accidental execution in production"""
    env = os.getenv("ENVIRONMENT", "").lower()
    if env == "production":
        print("ERROR: Cannot run test data scripts in production environment.")
        print("Set ENVIRONMENT to 'development' or 'test' to use this script.")
        sys.exit(1)
    if env not in ("development", "test", "dev"):
        response = input("WARNING: ENVIRONMENT is not set. Are you sure you want to add test data? (yes/no): ")
        if response.strip().lower() != "yes":
            print("Aborted.")
            sys.exit(0)


async def add_test_data():
    """Add sample horse racing data with odds from multiple bookmakers"""

    await db.connect()

    try:
        # Get bookmaker IDs
        bookmakers_query = "SELECT id, name FROM bookmakers"
        bookmakers = await db.fetch_all(bookmakers_query)
        bookmaker_map = {b['name']: b['id'] for b in bookmakers}

        # Get event type ID for horse racing
        event_type_query = "SELECT id FROM event_types WHERE name = 'horse_racing'"
        event_type = await db.fetch_one(event_type_query)
        event_type_id = event_type['id']

        # Create test races
        races = [
            {
                'name': 'Cheltenham 15:30',
                'venue': 'Cheltenham',
                'time': datetime.now() + timedelta(hours=1, minutes=30),
                'horses': [
                    ('Tiger Roll', {'betfair': 4.5, 'paddy_power': 4.8, 'bet365': 4.2}),
                    ('Delta Work', {'betfair': 3.2, 'paddy_power': 3.5, 'bet365': 3.0}),
                    ('Minella Times', {'betfair': 6.0, 'paddy_power': 6.5, 'bet365': 5.8}),
                    ('Any Second Now', {'betfair': 8.0, 'paddy_power': 7.5, 'bet365': 8.5}),
                    ('Galvin', {'betfair': 5.5, 'paddy_power': 6.0, 'bet365': 5.2}),
                ]
            },
            {
                'name': 'Newmarket 16:00',
                'venue': 'Newmarket',
                'time': datetime.now() + timedelta(hours=2),
                'horses': [
                    ('Stradivarius', {'betfair': 2.5, 'paddy_power': 2.8, 'bet365': 2.4}),
                    ('Enable', {'betfair': 3.5, 'paddy_power': 3.2, 'bet365': 3.8}),
                    ('Ghaiyyath', {'betfair': 5.0, 'paddy_power': 5.5, 'bet365': 4.8}),
                    ('Lord North', {'betfair': 7.5, 'paddy_power': 7.0, 'bet365': 8.0}),
                    ('Japan', {'betfair': 6.5, 'paddy_power': 7.0, 'bet365': 6.0}),
                    ('Magical', {'betfair': 9.0, 'paddy_power': 9.5, 'bet365': 8.5}),
                ]
            },
            {
                'name': 'Ascot 16:30',
                'venue': 'Ascot',
                'time': datetime.now() + timedelta(hours=2, minutes=30),
                'horses': [
                    ('Palace Pier', {'betfair': 2.2, 'paddy_power': 2.4, 'bet365': 2.1}),
                    ('Baaeed', {'betfair': 4.0, 'paddy_power': 4.2, 'bet365': 3.8}),
                    ('Inspiral', {'betfair': 5.5, 'paddy_power': 6.0, 'bet365': 5.2}),
                    ('Coroebus', {'betfair': 7.0, 'paddy_power': 6.5, 'bet365': 7.5}),
                ]
            },
            {
                'name': 'Aintree 17:00',
                'venue': 'Aintree',
                'time': datetime.now() + timedelta(hours=3),
                'horses': [
                    ('Noble Yeats', {'betfair': 3.8, 'paddy_power': 4.0, 'bet365': 3.5}),
                    ('Snow Leopardess', {'betfair': 5.2, 'paddy_power': 5.5, 'bet365': 5.0}),
                    ('Santini', {'betfair': 6.5, 'paddy_power': 7.0, 'bet365': 6.2}),
                    ('Conflated', {'betfair': 8.5, 'paddy_power': 8.0, 'bet365': 9.0}),
                    ('Run Wild Fred', {'betfair': 10.0, 'paddy_power': 11.0, 'bet365': 9.5}),
                ]
            }
        ]

        print("Adding test races and odds...")

        for race in races:
            # Create event
            event_query = """
                INSERT INTO events (event_type_id, name, venue, scheduled_time, status)
                VALUES ($1, $2, $3, $4, 'upcoming')
                RETURNING id
            """
            event = await db.fetch_one(
                event_query,
                event_type_id,
                race['name'],
                race['venue'],
                race['time']
            )
            event_id = event['id']

            print(f"Created race: {race['name']} at {race['venue']}")

            # Add horses and odds
            for horse_name, odds in race['horses']:
                # Create selection
                selection_query = """
                    INSERT INTO selections (event_id, name)
                    VALUES ($1, $2)
                    RETURNING id
                """
                selection = await db.fetch_one(selection_query, event_id, horse_name)
                selection_id = selection['id']

                # Add odds from each bookmaker
                for bookmaker, odds_value in odds.items():
                    if bookmaker in bookmaker_map:
                        odds_query = """
                            INSERT INTO odds_history
                            (selection_id, bookmaker_id, odds_decimal, scraped_at)
                            VALUES ($1, $2, $3, $4)
                        """
                        await db.execute(
                            odds_query,
                            selection_id,
                            bookmaker_map[bookmaker],
                            Decimal(str(odds_value)),
                            datetime.now()
                        )

                print(f"  Added {horse_name}: Betfair {odds['betfair']}, "
                      f"Paddy Power {odds['paddy_power']}, Bet365 {odds['bet365']}")

        print("\n✅ Test data added successfully!")
        print(f"Added {len(races)} races with multiple horses and odds")
        print("\nNow open http://localhost:3000 to see the data!")

    except Exception as e:
        print(f"Error adding test data: {e}")
        raise
    finally:
        await db.disconnect()

if __name__ == "__main__":
    _confirm_test_environment()
    asyncio.run(add_test_data())
