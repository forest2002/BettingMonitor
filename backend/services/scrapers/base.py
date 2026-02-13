from abc import ABC, abstractmethod
from typing import List, Optional
from models.schemas import OddsData
import logging

logger = logging.getLogger(__name__)

class BookmakerScraper(ABC):
    """Abstract base class for all bookmaker scrapers"""

    def __init__(self, bookmaker_name: str):
        self.bookmaker_name = bookmaker_name
        self.is_running = False
        self.logger = logging.getLogger(f"{__name__}.{bookmaker_name}")

    @abstractmethod
    async def initialize(self):
        """
        Initialize the scraper (setup browser, login, etc.)
        Called once before scraping starts
        """
        pass

    @abstractmethod
    async def scrape(self) -> List[OddsData]:
        """
        Perform one scrape cycle and return standardized odds data
        Should be idempotent and handle errors gracefully

        Returns:
            List[OddsData]: List of scraped odds in standardized format
        """
        pass

    @abstractmethod
    async def cleanup(self):
        """
        Cleanup resources (close browser, logout, etc.)
        Called when scraper is stopped
        """
        pass

    def health_check(self) -> bool:
        """
        Check if scraper is healthy
        Override if custom health checks needed

        Returns:
            bool: True if healthy, False otherwise
        """
        return self.is_running

    async def safe_scrape(self) -> List[OddsData]:
        """
        Wrapper around scrape() with error handling

        Returns:
            List[OddsData]: Scraped data or empty list on error
        """
        try:
            return await self.scrape()
        except Exception as e:
            self.logger.error(f"Error during scrape: {e}", exc_info=True)
            return []
