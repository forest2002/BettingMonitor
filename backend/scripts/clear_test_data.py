#!/usr/bin/env python3
"""
Clear test data from the database.

This removes known test events (Tiger Roll, Stradivarius, etc.)
and any events with "Unknown" venues/names that were created by
failed scraper runs.
"""
import asyncio
import sys
sys.path.append('/app')

from db.database import db

# Known test horse names from add_test_data.py and add_ew_test_data.py
TEST_HORSE_NAMES = [
    'Tiger Roll', 'Delta Work', 'Minella Times', 'Any Second Now', 'Galvin',
    'Stradivarius', 'Enable', 'Ghaiyyath', 'Lord North', 'Japan', 'Magical',
    'Palace Pier', 'Baaeed', 'Inspiral', 'Coroebus',
    'Noble Yeats', 'Snow Leopardess', 'Santini', 'Conflated', 'Run Wild Fred',
]

# Known test event names
TEST_EVENT_NAMES = [
    'Cheltenham 15:30', 'Newmarket 16:00', 'Ascot 16:30', 'Aintree 17:00',
]


async def clear_test_data():
    """Remove test data from the database"""
    await db.connect()

    try:
        # Find events matching known test names
        placeholders = ', '.join(f'${i+1}' for i in range(len(TEST_EVENT_NAMES)))
        events_query = f"""
            SELECT id, name FROM events
            WHERE name IN ({placeholders})
        """
        test_events = await db.fetch_all(events_query, *TEST_EVENT_NAMES)

        if not test_events:
            print("No test events found in the database.")
            await db.disconnect()
            return

        event_ids = [e['id'] for e in test_events]
        print(f"Found {len(event_ids)} test events to remove:")
        for e in test_events:
            print(f"  - {e['name']} (id: {e['id']})")

        # Delete in order: odds_history -> selections -> events
        for event_id in event_ids:
            await db.execute(
                "DELETE FROM odds_history WHERE selection_id IN (SELECT id FROM selections WHERE event_id = $1)",
                event_id
            )
            await db.execute("DELETE FROM selections WHERE event_id = $1", event_id)
            await db.execute("DELETE FROM events WHERE id = $1", event_id)

        print(f"\nRemoved {len(event_ids)} test events and their associated data.")

        # Also clean up any selections with "Unknown_" prefix (from failed scraper runs)
        unknown_result = await db.fetch_all(
            "SELECT id, name FROM selections WHERE name LIKE 'Unknown_%'"
        )
        if unknown_result:
            print(f"\nFound {len(unknown_result)} 'Unknown_*' selections to clean up:")
            for s in unknown_result:
                print(f"  - {s['name']} (id: {s['id']})")
                await db.execute("DELETE FROM odds_history WHERE selection_id = $1", s['id'])
                await db.execute("DELETE FROM selections WHERE id = $1", s['id'])
            print(f"Cleaned up {len(unknown_result)} unknown selections.")

        print("\nTest data cleared successfully!")

    except Exception as e:
        print(f"Error clearing test data: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await db.disconnect()


if __name__ == "__main__":
    asyncio.run(clear_test_data())
