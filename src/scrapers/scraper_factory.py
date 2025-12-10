"""
Scraper Factory

Creates and configures job board scrapers based on configuration.
"""

import logging
from typing import Dict, List, Optional

from src.config import Config
from src.scrapers.base_scraper import BaseScraper, ScraperConfig
from src.scrapers.reliefweb import ReliefWebScraper
from src.scrapers.devex import DevExScraper
from src.scrapers.impactpool import ImpactPoolScraper
from src.scrapers.unjobs import UNJobsScraper
from src.scrapers.worldbank import WorldBankScraper
from src.scrapers.eighty_thousand_hours import EightyThousandHoursScraper
from src.scrapers.econjobmarket import EconJobMarketScraper

logger = logging.getLogger(__name__)


class ScraperFactory:
    """
    Factory for creating and managing job board scrapers.
    
    Handles scraper instantiation, configuration, and lifecycle.
    """
    
    # Map of scraper names to classes
    SCRAPER_CLASSES = {
        "reliefweb": ReliefWebScraper,
        "devex": DevExScraper,
        "impactpool": ImpactPoolScraper,
        "unjobs": UNJobsScraper,
        "worldbank": WorldBankScraper,
        "eighty_thousand_hours": EightyThousandHoursScraper,
        "econjobmarket": EconJobMarketScraper,
    }
    
    def __init__(self, config: Config):
        """
        Initialize scraper factory.
        
        Args:
            config: Application configuration
        """
        self.config = config
        self._scrapers: Dict[str, BaseScraper] = {}
    
    def create_scraper(self, name: str) -> Optional[BaseScraper]:
        """
        Create a scraper instance.
        
        Args:
            name: Scraper name (e.g., 'reliefweb', 'devex')
            
        Returns:
            BaseScraper instance or None if not found
        """
        name = name.lower()
        
        if name not in self.SCRAPER_CLASSES:
            logger.error(f"Unknown scraper: {name}")
            return None
        
        # Get scraper-specific configuration
        scraper_config_dict = self.config.get_scraper_config(name)
        
        # Create scraper configuration
        scraper_config = ScraperConfig(
            name=name,
            base_url=scraper_config_dict.get("base_url", ""),
            rate_limit_seconds=self.config.scrapers.rate_limit_seconds,
            timeout_seconds=self.config.scrapers.timeout_seconds,
            max_retries=self.config.scrapers.max_retries,
            rotate_user_agent=self.config.scrapers.rotate_user_agent,
            extra_headers=scraper_config_dict
        )
        
        # Instantiate scraper
        scraper_class = self.SCRAPER_CLASSES[name]
        scraper = scraper_class(scraper_config)
        
        logger.info(f"Created scraper: {name}")
        return scraper
    
    def get_enabled_scrapers(self) -> List[BaseScraper]:
        """
        Get all enabled scrapers from configuration.
        
        Returns:
            List of scraper instances
        """
        scrapers = []
        
        for name in self.config.scrapers.enabled:
            scraper = self.create_scraper(name)
            if scraper:
                scrapers.append(scraper)
                self._scrapers[name] = scraper
        
        logger.info(f"Loaded {len(scrapers)} enabled scrapers")
        return scrapers
    
    def get_scraper(self, name: str) -> Optional[BaseScraper]:
        """
        Get a scraper by name (cached or create new).
        
        Args:
            name: Scraper name
            
        Returns:
            BaseScraper instance or None
        """
        if name in self._scrapers:
            return self._scrapers[name]
        
        scraper = self.create_scraper(name)
        if scraper:
            self._scrapers[name] = scraper
        
        return scraper
    
    def close_all(self) -> None:
        """Close all active scrapers."""
        for scraper in self._scrapers.values():
            try:
                scraper.close()
            except Exception as e:
                logger.warning(f"Error closing scraper: {e}")
        
        self._scrapers.clear()
        logger.debug("Closed all scrapers")
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close_all()
