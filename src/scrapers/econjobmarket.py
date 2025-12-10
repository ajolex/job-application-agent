"""
EconJobMarket Scraper

Scrapes job postings from EconJobMarket.org
"""

import logging
from typing import List, Optional, Any

from src.scrapers.base_scraper import BaseScraper, ScraperConfig
from src.database.db_manager import Job

logger = logging.getLogger(__name__)


class EconJobMarketScraper(BaseScraper):
    """Scraper for EconJobMarket.org."""
    
    def scrape(self, keywords: List[str], max_pages: int = 5) -> List[Job]:
        """Scrape jobs from EconJobMarket."""
        jobs = []
        
        logger.info(f"Scraping EconJobMarket with keywords: {keywords}")
        
        try:
            # EconJobMarket typically shows positions on a main page
            url = f"{self.config.base_url}/positions"
            
            for page in range(1, max_pages + 1):
                logger.debug(f"Fetching page {page}/{max_pages}")
                
                page_url = f"{url}?page={page}" if page > 1 else url
                
                # Fetch page
                soup = self.get_soup(page_url)
                
                # Find job listings
                job_elements = soup.select("tr.position-row, div.position, article.job, .listing-row")
                
                if not job_elements:
                    logger.debug(f"No job listings found on page {page}")
                    break
                
                for element in job_elements:
                    job = self.parse_job_listing(element)
                    if job:
                        # Filter by keywords
                        title_desc = f"{job.title} {job.description}".lower()
                        if any(kw.lower() in title_desc for kw in keywords):
                            jobs.append(job)
            
            logger.info(f"Found {len(jobs)} jobs on EconJobMarket")
            
        except Exception as e:
            logger.error(f"Error scraping EconJobMarket: {e}", exc_info=True)
        
        return jobs
    
    def parse_job_listing(self, element: Any) -> Optional[Job]:
        """Parse a job listing from search results."""
        try:
            # Title and URL
            title_elem = element.select_one("a.position-title, td.title a, .job-title a")
            if not title_elem:
                return None
            
            title = self.extract_text(title_elem)
            url = self.make_absolute_url(self.extract_attribute(title_elem, "href"))
            
            # Organization
            org_elem = element.select_one(".institution, td.institution, .organization")
            organization = self.extract_text(org_elem, "Unknown Institution")
            
            # Location
            location_elem = element.select_one(".location, td.location")
            location = self.extract_text(location_elem, "")
            
            # Deadline
            deadline_elem = element.select_one(".deadline, td.deadline, .due-date")
            deadline = self.extract_text(deadline_elem, "")
            
            # Field/area
            field_elem = element.select_one(".field, td.field, .area")
            field = self.extract_text(field_elem, "")
            
            requirements = f"Field: {field}" if field else ""
            
            return self.create_job(
                url=url,
                title=title,
                organization=organization,
                location=location,
                deadline=deadline,
                requirements=requirements
            )
            
        except Exception as e:
            logger.warning(f"Failed to parse EconJobMarket listing: {e}")
            return None
