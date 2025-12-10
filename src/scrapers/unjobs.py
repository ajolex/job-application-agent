"""
UNJobs Scraper

Scrapes job postings from UNJobs.org
"""

import logging
from typing import List, Optional, Any

from src.scrapers.base_scraper import BaseScraper, ScraperConfig
from src.database.db_manager import Job

logger = logging.getLogger(__name__)


class UNJobsScraper(BaseScraper):
    """Scraper for UNJobs.org."""
    
    def scrape(self, keywords: List[str], max_pages: int = 5) -> List[Job]:
        """Scrape jobs from UNJobs."""
        jobs = []
        
        logger.info(f"Scraping UNJobs with keywords: {keywords}")
        
        try:
            for page in range(1, max_pages + 1):
                logger.debug(f"Fetching page {page}/{max_pages}")
                
                # Build search URL
                query = "+".join(keywords)
                url = f"{self.config.base_url}/search?q={query}&page={page}"
                
                # Fetch page
                soup = self.get_soup(url)
                
                # Find job listings
                job_elements = soup.select("tr.job-row, div.job-listing, article.job, .vacancy")
                
                if not job_elements:
                    logger.debug(f"No job listings found on page {page}")
                    break
                
                for element in job_elements:
                    job = self.parse_job_listing(element)
                    if job:
                        jobs.append(job)
            
            logger.info(f"Found {len(jobs)} jobs on UNJobs")
            
        except Exception as e:
            logger.error(f"Error scraping UNJobs: {e}", exc_info=True)
        
        return jobs
    
    def parse_job_listing(self, element: Any) -> Optional[Job]:
        """Parse a job listing from search results."""
        try:
            # Title and URL
            title_elem = element.select_one("a.job-title, td.title a, h3 a, .title a")
            if not title_elem:
                return None
            
            title = self.extract_text(title_elem)
            url = self.make_absolute_url(self.extract_attribute(title_elem, "href"))
            
            # Organization
            org_elem = element.select_one(".organization, td.org, .company")
            organization = self.extract_text(org_elem, "UN Organization")
            
            # Location
            location_elem = element.select_one(".location, td.location, .duty-station")
            location = self.extract_text(location_elem, "Various")
            
            # Deadline
            deadline_elem = element.select_one(".deadline, td.deadline, .closing-date")
            deadline = self.extract_text(deadline_elem, "")
            
            return self.create_job(
                url=url,
                title=title,
                organization=organization,
                location=location,
                deadline=deadline
            )
            
        except Exception as e:
            logger.warning(f"Failed to parse UNJobs listing: {e}")
            return None
