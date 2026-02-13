#!/usr/bin/env python3
"""
Add test data with each-way opportunities
"""
import asyncio
import sys
from datetime import datetime, timedelta
from decimal import Decimal
sys.path.append('/app')

from db.database import db

async def clear_existing_data():
    """Clear existing test data"""
    await db.execute("DELETE FROM odds_history")
    await db.execute("DELETE FROM selections")
    await db.execute("DELETE FROM events WHERE status = 'upcoming'")
    print("Cleared existing test data")

async def add_each_way_test_data():
    """Add test data with each-way arbitrage opportunities"""

    await db.connect()

    try:
        await clear_existing_data()

        # Get bookmaker IDs
        bookmakers_query = "SELECT id, name FROM bookmakers"
        bookmakers = await db.fetch_all(bookmakers_query)
        bookmaker_map = {b['name']: b['id'] for b in bookmakers}

        # Get event type ID
        event_type_query = "SELECT id FROM event_types WHERE name = 'horse_racing'"
        event_type = await db.fetch_one(event_type_query)
        event_type_id = event_type['id']

        # Create races with each-way opportunities
        races = [
            {
                'name': 'Cheltenham 15:30',
                'venue': 'Cheltenham',
                'time': datetime.now() + timedelta(hours=1, minutes=30),
                'horses': [
                    {
                        'name': 'Tiger Roll',
                        'odds': {
                            'betfair': {'win': 4.5, 'place': 1.8, 'place_terms': None},  # Betfair place lay odds
                            'paddy_power': {'win': 5.0, 'place': None, 'place_terms': '1/4 1-2-3'},  # PP place: 2.0
                            'bet365': {'win': 4.8, 'place': None, 'place_terms': '1/5 1-2-3-4'},  # Bet365 place: 1.96
                        }
                    },
                    {
                        'name': 'Delta Work',
                        'odds': {
                            'betfair': {'win': 3.2, 'place': 1.5, 'place_terms': None},
                            'paddy_power': {'win': 3.5, 'place': None, 'place_terms': '1/4 1-2-3'},  # PP place: 1.625 - NO OPPORTUNITY
                            'bet365': {'win': 3.0, 'place': None, 'place_terms': '1/5 1-2-3-4'},
                        }
                    },
                    {
                        'name': 'Minella Times',
                        'odds': {
                            'betfair': {'win': 6.0, 'place': 2.0, 'place_terms': None},
                            'paddy_power': {'win': 7.0, 'place': None, 'place_terms': '1/4 1-2-3'},  # PP place: 2.5 - GOOD OPPORTUNITY!
                            'bet365': {'win': 6.5, 'place': None, 'place_terms': '1/5 1-2-3-4'},  # Bet365 place: 2.1 - OPPORTUNITY!
                        }
                    },
                    {
                        'name': 'Any Second Now',
                        'odds': {
                            'betfair': {'win': 8.0, 'place': 2.2, 'place_terms': None},
                            'paddy_power': {'win': 9.0, 'place': None, 'place_terms': '1/4 1-2-3'},  # PP place: 3.0 - GREAT OPPORTUNITY!
                            'bet365': {'win': 8.5, 'place': None, 'place_terms': '1/5 1-2-3-4'},
                        }
                    },
                ]
            },
            {
                'name': 'Newmarket 16:00',
                'venue': 'Newmarket',
                'time': datetime.now() + timedelta(hours=2),
                'horses': [
                    {
                        'name': 'Stradivarius',
                        'odds': {
                            'betfair': {'win': 2.5, 'place': 1.3, 'place_terms': None},
                            'paddy_power': {'win': 2.8, 'place': None, 'place_terms': '1/5 1-2-3-4'},  # PP place: 1.36 - SMALL OPPORTUNITY
                            'bet365': {'win': 2.6, 'place': None, 'place_terms': '1/5 1-2-3-4'},
                        }
                    },
                    {
                        'name': 'Enable',
                        'odds': {
                            'betfair': {'win': 3.5, 'place': 1.6, 'place_terms': None},
                            'paddy_power': {'win': 4.0, 'place': None, 'place_terms': '1/4 1-2-3'},  # PP place: 1.75 - OPPORTUNITY!
                            'bet365': {'win': 3.8, 'place': None, 'place_terms': '1/5 1-2-3-4'},
                        }
                    },
                    {
                        'name': 'Ghaiyyath',
                        'odds': {
                            'betfair': {'win': 5.0, 'place': 1.9, 'place_terms': None},
                            'paddy_power': {'win': 6.0, 'place': None, 'place_terms': '1/4 1-2-3'},  # PP place: 2.25 - OPPORTUNITY!
                            'bet365': {'win': 5.5, 'place': None, 'place_terms': '1/5 1-2-3-4'},
                        }
                    },
                ]
            }
        ]

        print("Adding races with each-way opportunities...")
        print("")

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

            print(f"📍 {race['name']} at {race['venue']}")
            print("")

            # Add horses and odds
            for horse in race['horses']:
                # Create selection
                selection_query = """
                    INSERT INTO selections (event_id, name)
                    VALUES ($1, $2)
                    RETURNING id
                """
                selection = await db.fetch_one(selection_query, event_id, horse['name'])
                selection_id = selection['id']

                # Add odds from each bookmaker
                for bookmaker_name, odds_info in horse['odds'].items():
                    if bookmaker_name in bookmaker_map:
                        odds_query = """
                            INSERT INTO odds_history
                            (selection_id, bookmaker_id, odds_decimal, place_odds, place_terms, scraped_at)
                            VALUES ($1, $2, $3, $4, $5, $6)
                        """
                        await db.execute(
                            odds_query,
                            selection_id,
                            bookmaker_map[bookmaker_name],
                            Decimal(str(odds_info['win'])),
                            Decimal(str(odds_info['place'])) if odds_info['place'] else None,
                            odds_info['place_terms'],
                            datetime.now()
                        )

                print(f"  🏇 {horse['name']}")
                for bm, odds_info in horse['odds'].items():
                    bm_display = bm.replace('_', ' ').title()
                    if odds_info['place_terms']:
                        print(f"    - {bm_display}: {odds_info['win']} (EW: {odds_info['place_terms']})")
                    else:
                        print(f"    - {bm_display}: Win {odds_info['win']}, Place Lay {odds_info['place']}")

            print("")

        print("✅ Each-way test data added successfully!")
        print("")
        print("🎯 Expected Opportunities:")
        print("  1. Minella Times - Paddy Power (place 2.5 vs Betfair lay 2.0)")
        print("  2. Any Second Now - Paddy Power (place 3.0 vs Betfair lay 2.2)")
        print("  3. Enable - Paddy Power (place 1.75 vs Betfair lay 1.6)")
        print("  4. Ghaiyyath - Paddy Power (place 2.25 vs Betfair lay 1.9)")
        print("")
        print("🌐 Check the opportunities at:")
        print("   http://localhost:8000/opportunities/each-way")
        print("   http://localhost:3000")

    except Exception as e:
        print(f"Error adding test data: {e}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        await db.disconnect()

if __name__ == "__main__":
    asyncio.run(add_each_way_test_data())
