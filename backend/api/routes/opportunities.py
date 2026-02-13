from fastapi import APIRouter, HTTPException, Query
from typing import List
from datetime import datetime, timedelta
from db.database import db
from services.calculators.each_way_calculator import EachWayCalculator
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/opportunities", tags=["opportunities"])

@router.get("/each-way")
async def get_each_way_opportunities(
    min_rating: int = Query(default=0, description="Minimum opportunity rating"),
    hours_ahead: int = Query(default=24, ge=1, le=168)
):
    """
    Get each-way arbitrage opportunities

    Finds horses where bookmaker place odds > Betfair Exchange lay place odds
    """
    try:
        time_limit = datetime.now() + timedelta(hours=hours_ahead)

        # Get all selections with odds from upcoming events
        query = """
            SELECT
                s.id as selection_id,
                s.name as selection_name,
                e.id as event_id,
                e.name as event_name,
                e.venue,
                e.scheduled_time,
                oh.bookmaker_id,
                b.display_name as bookmaker_name,
                oh.odds_decimal,
                oh.place_odds,
                oh.place_terms
            FROM selections s
            JOIN events e ON s.event_id = e.id
            LEFT JOIN LATERAL (
                SELECT DISTINCT ON (bookmaker_id)
                    bookmaker_id, odds_decimal, place_odds, place_terms
                FROM odds_history
                WHERE selection_id = s.id
                AND scraped_at > NOW() - INTERVAL '10 minutes'
                ORDER BY bookmaker_id, scraped_at DESC
            ) oh ON true
            JOIN bookmakers b ON oh.bookmaker_id = b.id
            WHERE e.scheduled_time > NOW()
            AND e.scheduled_time <= $1
            AND e.status = 'upcoming'
            ORDER BY e.scheduled_time, s.name, b.display_name
        """

        rows = await db.fetch_all(query, time_limit)

        # Group by selection
        selections_map = {}
        for row in rows:
            sel_id = row['selection_id']
            if sel_id not in selections_map:
                selections_map[sel_id] = {
                    'selection_id': sel_id,
                    'name': row['selection_name'],
                    'event_id': row['event_id'],
                    'event_name': row['event_name'],
                    'venue': row['venue'],
                    'scheduled_time': row['scheduled_time'],
                    'odds': []
                }

            selections_map[sel_id]['odds'].append({
                'bookmaker_name': row['bookmaker_name'],
                'odds_decimal': float(row['odds_decimal']),
                'place_odds': float(row['place_odds']) if row['place_odds'] else None,
                'place_terms': row['place_terms']
            })

        # Calculate opportunities
        calculator = EachWayCalculator()
        opportunities = calculator.find_opportunities(list(selections_map.values()))

        # Filter by minimum rating
        opportunities = [opp for opp in opportunities if opp['rating'] >= min_rating]

        # Format for response
        result = []
        for opp in opportunities:
            result.append({
                'selection_name': opp['selection_name'],
                'event_name': opp['event_name'],
                'bookmaker': opp['bookmaker'],
                'bookmaker_place_odds': float(opp['bookmaker_place_odds']),
                'betfair_lay_odds': float(opp['betfair_lay_odds']),
                'rating': opp['rating'],
                'edge': opp['edge'],
                'expected_value': float(opp['expected_value']),
                'profit_if_places': float(opp['profit_if_places']),
                'profit_if_wins': float(opp['profit_if_wins']),
                'profit_if_loses': float(opp['profit_if_loses']),
                'num_places': opp['num_places']
            })

        return {
            'count': len(result),
            'opportunities': result
        }

    except Exception as e:
        logger.error(f"Error fetching each-way opportunities: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch opportunities")

@router.get("/summary")
async def get_opportunities_summary():
    """Get summary of current opportunities"""
    try:
        # Get total events and selections
        events_query = """
            SELECT COUNT(*) as count
            FROM events
            WHERE scheduled_time > NOW()
            AND status = 'upcoming'
        """
        events_count = await db.fetch_one(events_query)

        # Get selections with odds
        selections_query = """
            SELECT COUNT(DISTINCT s.id) as count
            FROM selections s
            JOIN events e ON s.event_id = e.id
            WHERE e.scheduled_time > NOW()
            AND e.status = 'upcoming'
        """
        selections_count = await db.fetch_one(selections_query)

        return {
            'upcoming_events': events_count['count'],
            'total_selections': selections_count['count'],
            'timestamp': datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"Error fetching summary: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch summary")
