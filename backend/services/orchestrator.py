import asyncio
import logging
import os
import signal
from datetime import datetime
from dotenv import load_dotenv
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from collections import defaultdict
from services.scrapers.betfair_factory import get_betfair_client
from services.scrapers.oddschecker import OddscheckerScraper
from services.data_processor import data_processor
from db.database import db
from db.redis_client import redis_client

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=os.getenv('LOG_LEVEL', 'INFO'),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ScraperOrchestrator:
    """Orchestrates multiple scrapers with scheduling"""

    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.scrapers = {}
        self.is_running = False

    async def initialize(self):
        """Initialize database connections and scrapers"""
        logger.info("Initializing Scraper Orchestrator...")

        try:
            # Connect to database and Redis
            await db.connect()
            await redis_client.connect()
            logger.info("Database connections established")

            # Initialize Betfair REST API client (simple polling, no streaming complexity)
            logger.info("Initializing Betfair REST API client...")
            from services.scrapers.betfair_api import BetfairAPIClient
            betfair_api = BetfairAPIClient()
            await betfair_api.initialize()
            self.scrapers['betfair'] = betfair_api
            logger.info(f"Betfair API initialized: {betfair_api.bookmaker_name}")

            # Initialize Oddschecker scraper (replaces individual PP/Bet365 scrapers)
            logger.info("Initializing Oddschecker scraper...")
            oddschecker_scraper = OddscheckerScraper()
            await oddschecker_scraper.initialize()
            self.scrapers['oddschecker'] = oddschecker_scraper
            logger.info("Oddschecker scraper initialized")

            # Schedule scraper jobs
            self._schedule_jobs()

            self.is_running = True
            logger.info("Scraper Orchestrator initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize orchestrator: {e}", exc_info=True)
            await self.cleanup()
            raise

    def _schedule_jobs(self):
        """Schedule scraper jobs"""
        # Betfair REST API: every 2 seconds (very fast polling)
        self.scheduler.add_job(
            self._run_scraper,
            'interval',
            seconds=2,
            args=['betfair'],
            id='betfair_job',
            replace_existing=True
        )
        logger.info("Scheduled Betfair REST API polling every 2 seconds")

        # Oddschecker: every 60 seconds (scrapes 5 key bookmakers only)
        self.scheduler.add_job(
            self._run_scraper,
            'interval',
            seconds=60,
            args=['oddschecker'],
            id='oddschecker_job',
            replace_existing=True
        )
        logger.info("Scheduled Oddschecker scraper every 60 seconds")

        # Cleanup: remove finished races every 2 minutes
        self.scheduler.add_job(
            self._cleanup_old_events,
            'interval',
            minutes=2,
            id='cleanup_job',
            replace_existing=True
        )
        logger.info("Scheduled event cleanup every 2 minutes")

        # Daily cleanup: clear all data at 9:45pm, before scrapers stop at 10pm
        self.scheduler.add_job(
            self._daily_cleanup,
            'cron',
            hour=21,
            minute=45,
            id='daily_cleanup_job',
            replace_existing=True
        )
        logger.info("Scheduled daily cleanup at 9:45 PM")

    async def _cleanup_old_events(self):
        """Delete events (and their selections/odds) that have finished.

        A race is considered finished if:
        1. Its scheduled_time was over 2 hours ago, OR
        2. It is still 'upcoming' but has had no fresh odds in the last
           30 minutes (stale / wrongly-dated event)

        Note: We keep events for 2 hours after their scheduled time to ensure
        the frontend has time to display results and handle any timing edge cases.
        """
        try:
            # First, mark stale events as completed — these are events still
            # flagged 'upcoming' but with no recent odds, which means the race
            # has already run (common when the stored scheduled_time is wrong).
            mark_stale = """
                UPDATE events SET status = 'completed'
                WHERE status = 'upcoming'
                AND id NOT IN (
                    SELECT DISTINCT e.id
                    FROM events e
                    JOIN selections s ON s.event_id = e.id
                    JOIN odds_history oh ON oh.selection_id = s.id
                    WHERE oh.scraped_at > NOW() - INTERVAL '30 minutes'
                )
                AND created_at < NOW() - INTERVAL '30 minutes'
            """
            await db.execute(mark_stale)

            # Delete odds for events that finished over 2 hours ago
            delete_odds = """
                DELETE FROM odds_history
                WHERE selection_id IN (
                    SELECT s.id FROM selections s
                    JOIN events e ON s.event_id = e.id
                    WHERE e.scheduled_time < NOW() - INTERVAL '2 hours'
                       OR (e.status = 'completed' AND e.scheduled_time < NOW() - INTERVAL '2 hours')
                )
            """
            await db.execute(delete_odds)

            # Delete selections for events that finished over 2 hours ago
            delete_selections = """
                DELETE FROM selections
                WHERE event_id IN (
                    SELECT id FROM events
                    WHERE scheduled_time < NOW() - INTERVAL '2 hours'
                       OR (status = 'completed' AND scheduled_time < NOW() - INTERVAL '2 hours')
                )
            """
            await db.execute(delete_selections)

            # Delete events that finished over 2 hours ago
            delete_events = """
                DELETE FROM events
                WHERE scheduled_time < NOW() - INTERVAL '2 hours'
                   OR (status = 'completed' AND scheduled_time < NOW() - INTERVAL '2 hours')
            """
            await db.execute(delete_events)

            logger.info("Cleaned up finished and stale events")

        except Exception as e:
            logger.error(f"Error cleaning up old events: {e}", exc_info=True)

    async def _daily_cleanup(self):
        """Daily cleanup at 9:45pm: clear all data before scrapers stop at 10pm"""
        try:
            logger.info("Starting daily cleanup at 9:45pm...")

            # Delete all odds history
            await db.execute("DELETE FROM odds_history")
            logger.info("Cleared all odds history")

            # Delete all selections
            await db.execute("DELETE FROM selections")
            logger.info("Cleared all selections")

            # Delete all events
            await db.execute("DELETE FROM events")
            logger.info("Cleared all events")

            # Clear Redis cache if needed
            await redis_client.flushdb()
            logger.info("Cleared Redis cache")

            logger.info("Daily cleanup completed successfully")

        except Exception as e:
            logger.error(f"Error during daily cleanup: {e}", exc_info=True)

    async def _run_scraper(self, scraper_name: str):
        """Run a single scraper (only between 6am-10pm)"""
        # Check if we're within operating hours (6am-10pm)
        current_hour = datetime.now().hour
        if current_hour < 6 or current_hour >= 22:
            logger.debug(f"Skipping {scraper_name} scraper - outside operating hours (6am-10pm)")
            return

        if scraper_name not in self.scrapers:
            logger.error(f"Scraper '{scraper_name}' not found")
            return

        scraper = self.scrapers[scraper_name]
        logger.info(f"Running {scraper_name} scraper...")

        try:
            # Scrape data
            odds_data_list = await scraper.scrape()

            # Process and store data
            if odds_data_list:
                # Group by bookmaker_name so the data processor creates the
                # correct bookmaker record for each entry.  The Oddschecker
                # scraper returns entries for multiple bookmakers in one batch.
                grouped = defaultdict(list)
                for entry in odds_data_list:
                    grouped[entry.bookmaker_name].append(entry)

                total_stored = 0
                for bookmaker_name, entries in grouped.items():
                    stored_count = await data_processor.process_odds_data(
                        entries, bookmaker_name
                    )
                    total_stored += stored_count

                logger.info(
                    f"{scraper_name} scrape complete: "
                    f"{len(odds_data_list)} scraped, {total_stored} stored "
                    f"across {len(grouped)} bookmakers"
                )
            else:
                logger.info(f"{scraper_name} scrape complete: no data found")

        except Exception as e:
            logger.error(f"Error running {scraper_name} scraper: {e}", exc_info=True)

    def start(self):
        """Start the scheduler"""
        if not self.is_running:
            logger.error("Orchestrator not initialized")
            return

        logger.info("Starting scheduler...")
        self.scheduler.start()
        logger.info("Scheduler started. Scrapers are running.")

    async def cleanup(self):
        """Cleanup all resources"""
        logger.info("Cleaning up Scraper Orchestrator...")

        # Stop scheduler
        if self.scheduler.running:
            self.scheduler.shutdown(wait=True)

        # Cleanup all scrapers
        for name, scraper in self.scrapers.items():
            try:
                logger.info(f"Cleaning up {name} scraper...")
                await scraper.cleanup()
            except Exception as e:
                logger.error(f"Error cleaning up {name} scraper: {e}")

        # Close database connections
        await db.disconnect()
        await redis_client.disconnect()

        self.is_running = False
        logger.info("Scraper Orchestrator cleanup complete")

async def main():
    """Main entry point"""
    orchestrator = ScraperOrchestrator()

    # Setup signal handlers for graceful shutdown
    def signal_handler(sig, frame):
        logger.info("Shutdown signal received")
        orchestrator.is_running = False

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        # Initialize and start
        await orchestrator.initialize()
        orchestrator.start()

        # Keep running
        logger.info("Orchestrator is running. Press Ctrl+C to stop.")
        while orchestrator.is_running:
            await asyncio.sleep(1)

    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
    finally:
        await orchestrator.cleanup()

if __name__ == "__main__":
    asyncio.run(main())
