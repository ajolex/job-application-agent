"""
World Bank Jobs Scraper

Scrapes job postings from World Bank careers site.
Note: World Bank uses a complex careers portal that may require special handling.
"""

import logging
from typing import List, Optional, Any

from src.scrapers.base_scraper import BaseScraper, ScraperConfig
from src.database.db_manager import Job

logger = logging.getLogger(__name__)


class WorldBankScraper(BaseScraper):
    """Scraper for World Bank jobs."""
    
    def scrape(self, keywords: List[str], max_pages: int = 5) -> List[Job]:
        """Scrape jobs from World Bank."""
        jobs = []
        
        logger.info(f"Scraping World Bank with keywords: {keywords}")
        
        try:
            # World Bank careers often use specific URLs
            careers_url = self.config.extra_headers.get(
                "careers_url",
                f"{self.config.base_url}/en/about/careers"
            )
            
            for page in range(1, max_pages + 1):
                logger.debug(f"Fetching page {page}/{max_pages}")
                
                # Build search URL
                query = " ".join(keywords)
                url = f"{careers_url}/search?q={query}&page={page}"
                
                # Fetch page
                soup = self.get_soup(url)
                
                # Find job listings
                job_elements = soup.select("div.job-result, article.job, .career-opportunity, .vacancy")
                
                if not job_elements:
                    logger.debug(f"No job listings found on page {page}")
                    break
                
                for element in job_elements:
                    job = self.parse_job_listing(element)
                    if job:
                        jobs.append(job)
            
            logger.info(f"Found {len(jobs)} jobs at World Bank")
            
        except Exception as e:
            logger.error(f"Error scraping World Bank: {e}", exc_info=True)
        
        return jobs
    
    def parse_job_listing(self, element: Any) -> Optional[Job]:
        """Parse a job listing from search results."""
        try:
            # Title and URL
            title_elem = element.select_one("h3 a, h2 a, .job-title a, a.title")
            if not title_elem:
                return None
            
            title = self.extract_text(title_elem)
            url = self.make_absolute_url(self.extract_attribute(title_elem, "href"))
            
            # Organization (always World Bank or affiliate)
            org_elem = element.select_one(".organization, .unit, .department")
            organization = self.extract_text(org_elem, "World Bank Group")
            
            # Location
            location_elem = element.select_one(".location, .duty-station, .office")
            location = self.extract_text(location_elem, "Washington, DC")
            
            # Description
            desc_elem = element.select_one(".description, .summary, .excerpt")
            description = self.extract_text(desc_elem, "")
            
            # Dates
            date_elem = element.select_one(".posted-date, .publish-date")
            posted_date = self.extract_text(date_elem, "")
            
            deadline_elem = element.select_one(".deadline, .closing-date")
            deadline = self.extract_text(deadline_elem, "")
            
            return self.create_job(
                url=url,
                title=title,
                organization=organization,
                location=location,
                description=description,
                posted_date=posted_date,
                deadline=deadline
            )
            
        except Exception as e:
            logger.warning(f"Failed to parse World Bank job listing: {e}")
            return None
