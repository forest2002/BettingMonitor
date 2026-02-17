"""
Factory for creating Betfair scraper/API client based on configuration.
This allows easy switching between web scraping and official API.
"""

import os
from enum import Enum
from typing import Union
from services.scrapers.base import BookmakerScraper
from services.scrapers.betfair import BetfairScraper
from services.scrapers.betfair_api import BetfairAPIClient
from services.scrapers.betfair_stream import BetfairStreamClient
import logging

logger = logging.getLogger(__name__)


class BetfairMode(Enum):
    """Betfair data source mode"""
    SCRAPER = "scraper"  # Web scraping (free but fragile)
    API = "api"  # Official REST API (polling every 60s)
    STREAM = "stream"  # Streaming API (real-time push updates)


class BetfairFactory:
    """Factory for creating appropriate Betfair client based on mode"""

    @staticmethod
    def create(mode: str = None) -> BookmakerScraper:
        """
        Create Betfair scraper or API client based on mode

        Args:
            mode: "scraper" or "api". If None, reads from BETFAIR_MODE env var

        Returns:
            BookmakerScraper: Either BetfairScraper or BetfairAPIClient

        Raises:
            ValueError: If mode is invalid
        """
        # Get mode from env if not provided
        if mode is None:
            mode = os.getenv("BETFAIR_MODE", "scraper")

        mode = mode.lower()
        logger.info(f"Creating Betfair client in '{mode}' mode")

        try:
            betfair_mode = BetfairMode(mode)
        except ValueError:
            raise ValueError(
                f"Invalid BETFAIR_MODE: {mode}. Must be 'scraper', 'api', or 'stream'"
            )

        if betfair_mode == BetfairMode.STREAM:
            logger.info("Using Betfair Stream API (real-time push)")
            return BetfairStreamClient()
        elif betfair_mode == BetfairMode.API:
            logger.info("Using Betfair REST API (polling)")
            return BetfairAPIClient()
        else:
            logger.info("Using Betfair web scraper")
            return BetfairScraper()


# Convenience function
def get_betfair_client() -> BookmakerScraper:
    """Get configured Betfair client based on environment"""
    return BetfairFactory.create()
