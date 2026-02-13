from fastapi import APIRouter, HTTPException
from typing import List
from datetime import datetime, timedelta
from models.schemas import ScraperStatusSchema
from db.database import db
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/status", tags=["status"])

@router.get("/scrapers", response_model=List[ScraperStatusSchema])
async def get_scraper_status():
    """Get status of all scrapers"""
    try:
        query = """
            SELECT
                ss.bookmaker_id,
                b.display_name as bookmaker_name,
                ss.last_scrape_at,
                ss.last_success_at,
                ss.last_error,
                ss.total_scrapes,
                ss.total_errors,
                CASE
                    WHEN ss.last_success_at IS NULL THEN false
                    WHEN ss.last_success_at > NOW() - INTERVAL '5 minutes' THEN true
                    ELSE false
                END as is_healthy
            FROM scraper_status ss
            JOIN bookmakers b ON ss.bookmaker_id = b.id
            WHERE b.enabled = true
            ORDER BY b.display_name
        """

        rows = await db.fetch_all(query)
        return [ScraperStatusSchema(**dict(row)) for row in rows]

    except Exception as e:
        logger.error(f"Error fetching scraper status: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch scraper status")

@router.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Check database connection
        await db.fetch_one("SELECT 1")

        # Check if any scrapers are active
        query = """
            SELECT COUNT(*) as active_scrapers
            FROM scraper_status
            WHERE last_success_at > NOW() - INTERVAL '10 minutes'
        """
        result = await db.fetch_one(query)
        active_scrapers = result['active_scrapers']

        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "database": "connected",
            "active_scrapers": active_scrapers
        }

    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail="Service unhealthy")
