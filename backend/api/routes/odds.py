from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from datetime import datetime, timedelta
from models.schemas import OddsWithDetailsSchema
from db.database import db
from db.redis_client import redis_client
import logging
import json

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/odds", tags=["odds"])

@router.get("/events/{event_id}", response_model=List[OddsWithDetailsSchema])
async def get_event_odds(
    event_id: int,
    bookmaker_ids: Optional[str] = Query(None, description="Comma-separated bookmaker IDs")
):
    """
    Get current odds for all selections in an event

    Args:
        event_id: The event ID
        bookmaker_ids: Filter by bookmaker IDs (e.g., "1,2,3")
    """
    try:
        # Try cache first
        cache_key = f"odds:event:{event_id}"
        if bookmaker_ids:
            cache_key += f":{bookmaker_ids}"

        cached_data = await redis_client.get(cache_key)
        if cached_data:
            logger.info(f"Cache hit for event {event_id} odds")
            return [OddsWithDetailsSchema(**item) for item in cached_data]

        # Build query
        query = """
            SELECT
                oh.id, oh.selection_id, oh.bookmaker_id,
                oh.odds_decimal, oh.place_odds, oh.place_terms,
                oh.scraped_at, oh.metadata,
                s.name as selection_name,
                b.display_name as bookmaker_name,
                e.name as event_name,
                e.id as event_id,
                e.scheduled_time,
                e.venue
            FROM odds_history oh
            JOIN selections s ON oh.selection_id = s.id
            JOIN events e ON s.event_id = e.id
            JOIN bookmakers b ON oh.bookmaker_id = b.id
            WHERE e.id = $1
            AND oh.scraped_at > NOW() - INTERVAL '5 minutes'
        """
        params = [event_id]

        if bookmaker_ids:
            bookmaker_id_list = [int(x.strip()) for x in bookmaker_ids.split(',')]
            placeholders = ','.join(f'${i+2}' for i in range(len(bookmaker_id_list)))
            query += f" AND oh.bookmaker_id IN ({placeholders})"
            params.extend(bookmaker_id_list)

        query += """
            ORDER BY s.name, oh.scraped_at DESC
        """

        rows = await db.fetch_all(query, *params)

        # Get latest odds per selection-bookmaker combination
        odds_dict = {}
        for row in rows:
            key = (row['selection_id'], row['bookmaker_id'])
            if key not in odds_dict:
                odds_dict[key] = dict(row)

        odds_list = list(odds_dict.values())

        # Cache for 30 seconds
        await redis_client.set(cache_key, odds_list, expiry=30)

        return [OddsWithDetailsSchema(**item) for item in odds_list]

    except Exception as e:
        logger.error(f"Error fetching odds for event {event_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch odds")

@router.get("/selections/{selection_id}/history")
async def get_selection_odds_history(
    selection_id: int,
    hours: int = Query(default=1, ge=1, le=168),
    bookmaker_ids: Optional[str] = Query(None)
):
    """
    Get historical odds for a selection

    Args:
        selection_id: The selection ID
        hours: Number of hours of history (default 1)
        bookmaker_ids: Filter by bookmaker IDs
    """
    try:
        time_limit = datetime.now() - timedelta(hours=hours)

        query = """
            SELECT
                oh.scraped_at,
                oh.odds_decimal,
                oh.place_odds,
                b.display_name as bookmaker_name,
                b.id as bookmaker_id
            FROM odds_history oh
            JOIN bookmakers b ON oh.bookmaker_id = b.id
            WHERE oh.selection_id = $1
            AND oh.scraped_at >= $2
        """
        params = [selection_id, time_limit]

        if bookmaker_ids:
            bookmaker_id_list = [int(x.strip()) for x in bookmaker_ids.split(',')]
            placeholders = ','.join(f'${i+3}' for i in range(len(bookmaker_id_list)))
            query += f" AND oh.bookmaker_id IN ({placeholders})"
            params.extend(bookmaker_id_list)

        query += " ORDER BY oh.scraped_at ASC"

        rows = await db.fetch_all(query, *params)

        # Format for charting
        history = {
            "selection_id": selection_id,
            "data_points": [
                {
                    "timestamp": row['scraped_at'].isoformat(),
                    "odds_decimal": float(row['odds_decimal']),
                    "place_odds": float(row['place_odds']) if row['place_odds'] else None,
                    "bookmaker_name": row['bookmaker_name'],
                    "bookmaker_id": row['bookmaker_id']
                }
                for row in rows
            ]
        }

        return history

    except Exception as e:
        logger.error(f"Error fetching odds history for selection {selection_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch odds history")

@router.get("/best")
async def get_best_odds(
    event_type: Optional[str] = None,
    hours_ahead: int = Query(default=24, ge=1, le=168)
):
    """Get best odds across all bookmakers for upcoming events"""
    try:
        time_limit = datetime.now() + timedelta(hours=hours_ahead)

        query = """
            SELECT * FROM best_odds
            WHERE scheduled_time <= $1
        """
        params = [time_limit]

        if event_type:
            # Would need to join with events table to filter by event_type
            # For now, return all
            pass

        query += " ORDER BY scheduled_time ASC"

        rows = await db.fetch_all(query, *params)
        return [dict(row) for row in rows]

    except Exception as e:
        logger.error(f"Error fetching best odds: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch best odds")
