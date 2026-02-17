from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from datetime import datetime, timedelta
from models.schemas import EventWithSelectionsSchema, EventSchema
from db.database import db
import logging
import json

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/events", tags=["events"])

@router.get("/", response_model=List[EventWithSelectionsSchema])
async def get_events(
    event_type: Optional[str] = None,
    hours_ahead: int = Query(default=24, ge=1, le=168),
    status: str = Query(default="upcoming")
):
    """
    Get upcoming events with their selections

    Args:
        event_type: Filter by event type (horse_racing, football, etc.)
        hours_ahead: Get events in the next N hours (default 24)
        status: Event status (upcoming, in_progress, completed)
    """
    try:
        time_limit = datetime.now() + timedelta(hours=hours_ahead)

        query = """
            SELECT
                e.id, e.event_type_id, e.name, e.venue,
                e.scheduled_time, e.status, e.metadata,
                e.created_at, e.updated_at,
                et.name as event_type_name
            FROM events e
            JOIN event_types et ON e.event_type_id = et.id
            WHERE e.scheduled_time > NOW()
            AND e.scheduled_time <= $1
            AND e.status = $2
        """
        params = [time_limit, status]

        if event_type:
            query += " AND et.name = $3"
            params.append(event_type)

        query += " ORDER BY e.scheduled_time ASC"

        events_rows = await db.fetch_all(query, *params)

        events = []
        for row in events_rows:
            event_dict = dict(row)

            # Parse metadata JSON string to dict
            if event_dict.get('metadata') and isinstance(event_dict['metadata'], str):
                event_dict['metadata'] = json.loads(event_dict['metadata'])

            # Get selections for this event
            selections_query = """
                SELECT id, event_id, name, metadata
                FROM selections
                WHERE event_id = $1
                ORDER BY name
            """
            selections_rows = await db.fetch_all(selections_query, row['id'])

            # Parse selection metadata JSON strings to dicts
            selections = []
            for sel in selections_rows:
                sel_dict = dict(sel)
                if sel_dict.get('metadata') and isinstance(sel_dict['metadata'], str):
                    sel_dict['metadata'] = json.loads(sel_dict['metadata'])
                selections.append(sel_dict)

            event_dict['selections'] = selections

            events.append(EventWithSelectionsSchema(**event_dict))

        return events

    except Exception as e:
        logger.error(f"Error fetching events: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch events")

@router.get("/{event_id}", response_model=EventWithSelectionsSchema)
async def get_event(event_id: int):
    """Get a specific event by ID with its selections"""
    try:
        query = """
            SELECT
                e.id, e.event_type_id, e.name, e.venue,
                e.scheduled_time, e.status, e.metadata,
                e.created_at, e.updated_at,
                et.name as event_type_name
            FROM events e
            JOIN event_types et ON e.event_type_id = et.id
            WHERE e.id = $1
        """
        event_row = await db.fetch_one(query, event_id)

        if not event_row:
            raise HTTPException(status_code=404, detail="Event not found")

        event_dict = dict(event_row)

        # Parse metadata JSON string to dict
        if event_dict.get('metadata') and isinstance(event_dict['metadata'], str):
            event_dict['metadata'] = json.loads(event_dict['metadata'])

        # Get selections
        selections_query = """
            SELECT id, event_id, name, metadata
            FROM selections
            WHERE event_id = $1
            ORDER BY name
        """
        selections_rows = await db.fetch_all(selections_query, event_id)

        # Parse selection metadata JSON strings to dicts
        selections = []
        for sel in selections_rows:
            sel_dict = dict(sel)
            if sel_dict.get('metadata') and isinstance(sel_dict['metadata'], str):
                sel_dict['metadata'] = json.loads(sel_dict['metadata'])
            selections.append(sel_dict)

        event_dict['selections'] = selections

        return EventWithSelectionsSchema(**event_dict)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching event {event_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch event")
