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

            # Initialize Betfair client (API or scraper based on config)
            logger.info("Initializing Betfair client...")
            betfair_client = get_betfair_client()
            await betfair_client.initialize()
            self.scrapers['betfair'] = betfair_client
            logger.info(f"Betfair client initialized: {betfair_client.bookmaker_name}")

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
        # Betfair Exchange: every 30 seconds (baseline odds)
        self.scheduler.add_job(
            self._run_scraper,
            'interval',
            seconds=30,
            args=['betfair'],
            id='betfair_job',
            replace_existing=True
        )
        logger.info("Scheduled Betfair Exchange scraper every 30 seconds")

        # Oddschecker: every 90 seconds (scrapes multiple race pages)
        self.scheduler.add_job(
            self._run_scraper,
            'interval',
            seconds=90,
            args=['oddschecker'],
            id='oddschecker_job',
            replace_existing=True
        )
        logger.info("Scheduled Oddschecker scraper every 90 seconds")

    async def _run_scraper(self, scraper_name: str):
        """Run a single scraper"""
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
            self.scheduler.shutdown(wait=False)

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
        asyncio.create_task(orchestrator.cleanup())

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
