"""
ImpactPool Jobs Scraper

Scrapes job postings from ImpactPool.org
"""

import logging
from typing import List, Optional, Any

from src.scrapers.base_scraper import BaseScraper, ScraperConfig
from src.database.db_manager import Job

logger = logging.getLogger(__name__)


class ImpactPoolScraper(BaseScraper):
    """Scraper for ImpactPool jobs."""
    
    def scrape(self, keywords: List[str], max_pages: int = 5) -> List[Job]:
        """Scrape jobs from ImpactPool."""
        jobs = []
        
        logger.info(f"Scraping ImpactPool with keywords: {keywords}")
        
        try:
            for page in range(1, max_pages + 1):
                logger.debug(f"Fetching page {page}/{max_pages}")
                
                # Build search URL
                query = "+".join(keywords)
                url = f"{self.config.base_url}/jobs?q={query}&page={page}"
                
                # Fetch page
                soup = self.get_soup(url)
                
                # Find job listings
                job_elements = soup.select("div.job-listing, article.job, .job-item, .vacancy-item")
                
                if not job_elements:
                    logger.debug(f"No job listings found on page {page}")
                    break
                
                for element in job_elements:
                    job = self.parse_job_listing(element)
                    if job:
                        jobs.append(job)
            
            logger.info(f"Found {len(jobs)} jobs on ImpactPool")
            
        except Exception as e:
            logger.error(f"Error scraping ImpactPool: {e}", exc_info=True)
        
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
            
            # Organization
            org_elem = element.select_one(".organization, .company, .employer")
            organization = self.extract_text(org_elem, "Unknown")
            
            # Location
            location_elem = element.select_one(".location, .place, .country")
            location = self.extract_text(location_elem, "Global")
            
            # Description
            desc_elem = element.select_one(".description, .summary, .excerpt")
            description = self.extract_text(desc_elem, "")
            
            # Dates
            date_elem = element.select_one(".posted-date, .date")
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
            logger.warning(f"Failed to parse ImpactPool job listing: {e}")
            return None
