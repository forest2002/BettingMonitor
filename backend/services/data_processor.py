import logging
import json
from typing import List
from datetime import datetime
from models.schemas import OddsData
from db.database import db
from db.redis_client import redis_client

logger = logging.getLogger(__name__)

class DataProcessor:
    """Process scraped odds data and store in database"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    async def process_odds_data(self, odds_data_list: List[OddsData], bookmaker_name: str) -> int:
        """
        Process and store odds data

        Args:
            odds_data_list: List of scraped odds data
            bookmaker_name: Name of the bookmaker

        Returns:
            int: Number of odds records stored
        """
        if not odds_data_list:
            self.logger.info(f"No data to process for {bookmaker_name}")
            return 0

        stored_count = 0

        try:
            # Get bookmaker ID
            bookmaker = await self._get_or_create_bookmaker(bookmaker_name)
            bookmaker_id = bookmaker['id']

            for odds_data in odds_data_list:
                try:
                    # Get or create event
                    event = await self._get_or_create_event(odds_data)
                    event_id = event['id']

                    # Get or create selection
                    selection = await self._get_or_create_selection(event_id, odds_data.selection_name)
                    selection_id = selection['id']

                    # Check for duplicate (same selection, bookmaker, and similar odds in last 2 minutes)
                    if await self._is_duplicate(selection_id, bookmaker_id, odds_data.odds_decimal):
                        self.logger.debug(
                            f"Duplicate odds for {odds_data.selection_name} @ {odds_data.odds_decimal}"
                        )
                        continue

                    # Store odds
                    await self._store_odds(selection_id, bookmaker_id, odds_data)
                    stored_count += 1

                    # Update Redis cache
                    await self._update_cache(event_id, selection_id, bookmaker_id, odds_data)

                    self.logger.info(
                        f"Stored odds: {odds_data.selection_name} @ {odds_data.odds_decimal} "
                        f"from {bookmaker_name}"
                    )

                except Exception as e:
                    self.logger.error(f"Error processing odds data: {e}", exc_info=True)
                    continue

            # Update scraper status
            await self._update_scraper_status(bookmaker_id, stored_count > 0)

        except Exception as e:
            self.logger.error(f"Error in process_odds_data: {e}", exc_info=True)
            await self._update_scraper_status_error(bookmaker_name, str(e))

        return stored_count

    async def _get_or_create_bookmaker(self, bookmaker_name: str) -> dict:
        """Get or create bookmaker record"""
        # Check if exists
        query = "SELECT id, name, display_name FROM bookmakers WHERE name = $1"
        bookmaker = await db.fetch_one(query, bookmaker_name)

        if bookmaker:
            return dict(bookmaker)

        # Create new bookmaker
        insert_query = """
            INSERT INTO bookmakers (name, display_name, enabled)
            VALUES ($1, $2, true)
            RETURNING id, name, display_name
        """
        display_name = bookmaker_name.replace('_', ' ').title()
        bookmaker = await db.fetch_one(insert_query, bookmaker_name, display_name)
        return dict(bookmaker)

    async def _get_or_create_event(self, odds_data: OddsData) -> dict:
        """Get or create event record"""
        # Get event type ID
        event_type_query = "SELECT id FROM event_types WHERE name = $1"
        event_type = await db.fetch_one(event_type_query, odds_data.event_type)

        if not event_type:
            raise ValueError(f"Event type '{odds_data.event_type}' not found")

        event_type_id = event_type['id']

        # Check if event exists (same name, venue, and scheduled time within 5 minutes)
        if odds_data.venue:
            query = """
                SELECT id, event_type_id, name, venue, scheduled_time, status, metadata
                FROM events
                WHERE name = $1
                AND venue = $2
                AND ABS(EXTRACT(EPOCH FROM (scheduled_time - $3))) < 300
                ORDER BY created_at DESC
                LIMIT 1
            """
            event = await db.fetch_one(query, odds_data.event_name, odds_data.venue, odds_data.scheduled_time)
        else:
            query = """
                SELECT id, event_type_id, name, venue, scheduled_time, status, metadata
                FROM events
                WHERE name = $1
                AND venue IS NULL
                AND ABS(EXTRACT(EPOCH FROM (scheduled_time - $3))) < 300
                ORDER BY created_at DESC
                LIMIT 1
            """
            event = await db.fetch_one(query, odds_data.event_name, odds_data.scheduled_time)

        if event:
            return dict(event)

        # Create new event
        insert_query = """
            INSERT INTO events (event_type_id, name, venue, scheduled_time, status, metadata)
            VALUES ($1, $2, $3, $4, 'upcoming', $5)
            RETURNING id, event_type_id, name, venue, scheduled_time, status, metadata
        """
        event = await db.fetch_one(
            insert_query,
            event_type_id,
            odds_data.event_name,
            odds_data.venue,
            odds_data.scheduled_time,
            json.dumps(odds_data.metadata) if odds_data.metadata else None
        )
        return dict(event)

    async def _get_or_create_selection(self, event_id: int, selection_name: str) -> dict:
        """Get or create selection record"""
        query = "SELECT id, event_id, name FROM selections WHERE event_id = $1 AND name = $2"
        selection = await db.fetch_one(query, event_id, selection_name)

        if selection:
            return dict(selection)

        # Create new selection
        insert_query = """
            INSERT INTO selections (event_id, name)
            VALUES ($1, $2)
            RETURNING id, event_id, name
        """
        selection = await db.fetch_one(insert_query, event_id, selection_name)
        return dict(selection)

    async def _is_duplicate(self, selection_id: int, bookmaker_id: int, odds_decimal: float) -> bool:
        """Check if this is a duplicate odds entry"""
        query = """
            SELECT COUNT(*) as count
            FROM odds_history
            WHERE selection_id = $1
            AND bookmaker_id = $2
            AND odds_decimal = $3
            AND scraped_at > NOW() - '2 minutes'::interval
        """
        result = await db.fetch_one(query, selection_id, bookmaker_id, float(odds_decimal))
        return result['count'] > 0

    async def _store_odds(self, selection_id: int, bookmaker_id: int, odds_data: OddsData):
        """Store odds in database"""
        query = """
            INSERT INTO odds_history (
                selection_id, bookmaker_id, odds_decimal,
                place_odds, place_terms, scraped_at, metadata
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7)
        """
        await db.execute(
            query,
            selection_id,
            bookmaker_id,
            float(odds_data.odds_decimal),
            float(odds_data.place_odds) if odds_data.place_odds else None,
            odds_data.place_terms,
            datetime.now(),
            json.dumps(odds_data.metadata) if odds_data.metadata else None
        )

    async def _update_cache(
        self, event_id: int, selection_id: int, bookmaker_id: int, odds_data: OddsData
    ):
        """Update Redis cache with latest odds"""
        cache_key = f"odds:event:{event_id}:selection:{selection_id}:bookmaker:{bookmaker_id}"
        cache_data = {
            "odds_decimal": float(odds_data.odds_decimal),
            "place_odds": float(odds_data.place_odds) if odds_data.place_odds else None,
            "place_terms": odds_data.place_terms,
            "scraped_at": datetime.now().isoformat()
        }
        await redis_client.set(cache_key, cache_data, expiry=300)

    async def _update_scraper_status(self, bookmaker_id: int, success: bool):
        """Update scraper status after scrape attempt"""
        query = """
            UPDATE scraper_status
            SET last_scrape_at = NOW(),
                last_success_at = CASE WHEN $2 THEN NOW() ELSE last_success_at END,
                total_scrapes = total_scrapes + 1,
                last_error = CASE WHEN $2 THEN NULL ELSE last_error END
            WHERE bookmaker_id = $1
        """
        await db.execute(query, bookmaker_id, success)

    async def _update_scraper_status_error(self, bookmaker_name: str, error: str):
        """Update scraper status after error"""
        query = """
            UPDATE scraper_status
            SET last_scrape_at = NOW(),
                last_error = $2,
                total_errors = total_errors + 1
            FROM bookmakers
            WHERE scraper_status.bookmaker_id = bookmakers.id
            AND bookmakers.name = $1
        """
        await db.execute(query, bookmaker_name, error)

# Global instance
data_processor = DataProcessor()
