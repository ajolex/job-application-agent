"""
ReliefWeb Jobs Scraper

Scrapes job postings from ReliefWeb using their public API.
API Documentation: https://reliefweb.int/help/api
"""

import logging
from typing import List, Optional, Any
from datetime import datetime

from src.scrapers.base_scraper import APIScraper, ScraperConfig
from src.database.db_manager import Job

logger = logging.getLogger(__name__)


class ReliefWebScraper(APIScraper):
    """
    Scraper for ReliefWeb jobs.
    
    ReliefWeb provides a public REST API that's easy to work with.
    """
    
    def __init__(self, config: ScraperConfig):
        super().__init__(config)
        self.api_url = config.extra_headers.get("api_url", "https://api.reliefweb.int/v1/jobs")
    
    def scrape(self, keywords: List[str], max_pages: int = 5) -> List[Job]:
        """
        Scrape jobs from ReliefWeb API.
        
        Args:
            keywords: Search keywords
            max_pages: Maximum number of pages (each page has ~20 results)
            
        Returns:
            List of Job objects
        """
        jobs = []
        offset = 0
        limit = 20
        
        logger.info(f"Scraping ReliefWeb with keywords: {keywords}")
        
        try:
            for page in range(max_pages):
                logger.debug(f"Fetching page {page + 1}/{max_pages}")
                
                # Build query
                query = {
                    "query": {
                        "value": " OR ".join(keywords),
                        "operator": "OR"
                    },
                    "limit": limit,
                    "offset": offset,
                    "fields": {
                        "include": [
                            "id", "title", "url", "source.name",
                            "date.created", "date.closing",
                            "body", "how_to_apply", "country.name",
                            "theme.name", "career_categories.name"
                        ]
                    },
                    "sort": ["date.created:desc"]
                }
                
                # Make API request
                response = self.post_json(
                    self.api_url,
                    json_data=query
                )
                
                # Parse results
                if "data" in response:
                    for item in response["data"]:
                        job = self._parse_job_item(item)
                        if job:
                            jobs.append(job)
                
                # Check if there are more results
                total = response.get("totalCount", 0)
                if offset + limit >= total:
                    break
                
                offset += limit
            
            logger.info(f"Found {len(jobs)} jobs on ReliefWeb")
            
        except Exception as e:
            logger.error(f"Error scraping ReliefWeb: {e}", exc_info=True)
        
        return jobs
    
    def _parse_job_item(self, item: dict) -> Optional[Job]:
        """Parse a job item from API response."""
        try:
            fields = item.get("fields", {})
            
            job_id = str(item.get("id", ""))
            title = fields.get("title", "")
            url = fields.get("url", "")
            
            # Organization
            source = fields.get("source", [])
            organization = source[0].get("name", "") if source else "Unknown"
            
            # Location
            countries = fields.get("country", [])
            location = ", ".join(c.get("name", "") for c in countries) if countries else "Global"
            
            # Description
            body = fields.get("body", "")
            how_to_apply = fields.get("how_to_apply", "")
            description = f"{body}\n\nHow to Apply:\n{how_to_apply}" if how_to_apply else body
            
            # Dates
            posted_date = fields.get("date", {}).get("created", "")
            deadline = fields.get("date", {}).get("closing", "")
            
            # Categories/themes
            themes = fields.get("theme", [])
            categories = fields.get("career_categories", [])
            theme_names = [t.get("name", "") for t in themes]
            category_names = [c.get("name", "") for c in categories]
            requirements = f"Themes: {', '.join(theme_names)}\nCategories: {', '.join(category_names)}"
            
            return self.create_job(
                url=url,
                title=title,
                organization=organization,
                location=location,
                description=description,
                posted_date=posted_date,
                deadline=deadline,
                requirements=requirements,
                application_url=url
            )
            
        except Exception as e:
            logger.warning(f"Failed to parse job item: {e}")
            return None
    
    def parse_job_listing(self, element: Any) -> Optional[Job]:
        """Not used for API scraper."""
        return None
