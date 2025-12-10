"""
DevEx Jobs Scraper

Scrapes job postings from Devex.com
Note: DevEx may require JavaScript rendering for full functionality.
"""

import logging
import re
from typing import List, Optional, Any
from datetime import datetime

from src.scrapers.base_scraper import BaseScraper, ScraperConfig
from src.database.db_manager import Job

logger = logging.getLogger(__name__)


class DevExScraper(BaseScraper):
    """
    Scraper for DevEx jobs.
    
    DevEx is a platform for international development jobs.
    """
    
    def scrape(self, keywords: List[str], max_pages: int = 5) -> List[Job]:
        """
        Scrape jobs from DevEx.
        
        Args:
            keywords: Search keywords
            max_pages: Maximum number of pages to scrape
            
        Returns:
            List of Job objects
        """
        jobs = []
        
        logger.info(f"Scraping DevEx with keywords: {keywords}")
        
        try:
            for page in range(1, max_pages + 1):
                logger.debug(f"Fetching page {page}/{max_pages}")
                
                # Build search URL
                query = "+".join(keywords)
                url = f"{self.config.base_url}/jobs/search?search={query}&page={page}"
                
                # Fetch page
                soup = self.get_soup(url)
                
                # Find job listings
                job_elements = soup.select("div.job-card, article.job-listing, div.job-item, .search-result-item")
                
                if not job_elements:
                    logger.debug(f"No job listings found on page {page}")
                    break
                
                for element in job_elements:
                    job = self.parse_job_listing(element)
                    if job:
                        jobs.append(job)
                
                # Check for next page
                next_button = soup.select_one("a.next-page, a[rel='next'], .pagination a:contains('Next')")
                if not next_button:
                    break
            
            logger.info(f"Found {len(jobs)} jobs on DevEx")
            
        except Exception as e:
            logger.error(f"Error scraping DevEx: {e}", exc_info=True)
        
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
            org_elem = element.select_one(".company-name, .organization, .employer, .org-name")
            organization = self.extract_text(org_elem, "Unknown")
            
            # Location
            location_elem = element.select_one(".location, .job-location, .place")
            location = self.extract_text(location_elem, "Global")
            
            # Description (summary from listing page)
            desc_elem = element.select_one(".job-description, .description, .summary, .excerpt")
            description = self.extract_text(desc_elem, "")
            
            # Posted date
            date_elem = element.select_one(".posted-date, .date, time")
            posted_date = self.extract_text(date_elem, "")
            if date_elem and date_elem.get("datetime"):
                posted_date = date_elem["datetime"]
            
            # Deadline
            deadline_elem = element.select_one(".deadline, .closing-date, .expires")
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
            logger.warning(f"Failed to parse DevEx job listing: {e}")
            return None
    
    def parse_job_details(self, job: Job) -> Job:
        """Fetch full job details from the job page."""
        try:
            soup = self.get_soup(job.url)
            
            # Full description
            desc_elem = soup.select_one(".job-description, #job-description, .description-content")
            if desc_elem:
                job.description = self.extract_text(desc_elem)
            
            # Requirements
            req_elem = soup.select_one(".requirements, .qualifications, #requirements")
            if req_elem:
                job.requirements = self.extract_text(req_elem)
            
            # Application URL
            apply_elem = soup.select_one("a.apply-button, a[href*='apply'], .apply-link")
            if apply_elem:
                job.application_url = self.make_absolute_url(self.extract_attribute(apply_elem, "href"))
            
        except Exception as e:
            logger.warning(f"Failed to fetch DevEx job details: {e}")
        
        return job
