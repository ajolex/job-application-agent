"""
80,000 Hours Job Board Scraper

Scrapes job postings from 80,000 Hours job board.
"""

import logging
from typing import List, Optional, Any

from src.scrapers.base_scraper import APIScraper, ScraperConfig
from src.database.db_manager import Job

logger = logging.getLogger(__name__)


class EightyThousandHoursScraper(APIScraper):
    """Scraper for 80,000 Hours job board."""
    
    def __init__(self, config: ScraperConfig):
        super().__init__(config)
        self.api_url = config.extra_headers.get(
            "api_url",
            "https://jobs.80000hours.org/api/jobs"
        )
    
    def scrape(self, keywords: List[str], max_pages: int = 5) -> List[Job]:
        """Scrape jobs from 80,000 Hours."""
        jobs = []
        
        logger.info(f"Scraping 80,000 Hours with keywords: {keywords}")
        
        try:
            # Try API first
            try:
                response = self.get_json(self.api_url)
                
                if isinstance(response, list):
                    for item in response:
                        job = self._parse_api_job(item, keywords)
                        if job:
                            jobs.append(job)
                elif isinstance(response, dict) and "jobs" in response:
                    for item in response["jobs"]:
                        job = self._parse_api_job(item, keywords)
                        if job:
                            jobs.append(job)
                
            except Exception as e:
                logger.warning(f"API request failed, falling back to HTML scraping: {e}")
                # Fall back to HTML scraping
                jobs = self._scrape_html(keywords, max_pages)
            
            logger.info(f"Found {len(jobs)} jobs on 80,000 Hours")
            
        except Exception as e:
            logger.error(f"Error scraping 80,000 Hours: {e}", exc_info=True)
        
        return jobs
    
    def _parse_api_job(self, item: dict, keywords: List[str]) -> Optional[Job]:
        """Parse a job from API response."""
        try:
            title = item.get("title", "")
            
            # Filter by keywords
            title_lower = title.lower()
            if not any(kw.lower() in title_lower for kw in keywords):
                # Also check description
                description = item.get("description", "")
                if not any(kw.lower() in description.lower() for kw in keywords):
                    return None
            
            url = item.get("url", "") or item.get("link", "")
            organization = item.get("company", "") or item.get("organization", "")
            location = item.get("location", "Remote")
            description = item.get("description", "")
            posted_date = item.get("posted_date", "") or item.get("published", "")
            deadline = item.get("deadline", "") or item.get("expires", "")
            
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
            logger.warning(f"Failed to parse 80,000 Hours job: {e}")
            return None
    
    def _scrape_html(self, keywords: List[str], max_pages: int) -> List[Job]:
        """Fall back to HTML scraping if API unavailable."""
        jobs = []
        
        try:
            for page in range(1, max_pages + 1):
                url = f"{self.config.base_url}/?page={page}"
                soup = self.get_soup(url)
                
                # Find job listings
                job_elements = soup.select("div.job, article.vacancy, .job-listing")
                
                if not job_elements:
                    break
                
                for element in job_elements:
                    job = self.parse_job_listing(element)
                    if job:
                        jobs.append(job)
        
        except Exception as e:
            logger.error(f"HTML scraping failed: {e}")
        
        return jobs
    
    def parse_job_listing(self, element: Any) -> Optional[Job]:
        """Parse a job listing from HTML."""
        try:
            # Title and URL
            title_elem = element.select_one("h3 a, h2 a, .job-title a")
            if not title_elem:
                return None
            
            title = self.extract_text(title_elem)
            url = self.make_absolute_url(self.extract_attribute(title_elem, "href"))
            
            # Organization
            org_elem = element.select_one(".company, .organization, .employer")
            organization = self.extract_text(org_elem, "Unknown")
            
            # Location
            location_elem = element.select_one(".location, .place")
            location = self.extract_text(location_elem, "Remote")
            
            # Description
            desc_elem = element.select_one(".description, .summary")
            description = self.extract_text(desc_elem, "")
            
            return self.create_job(
                url=url,
                title=title,
                organization=organization,
                location=location,
                description=description
            )
            
        except Exception as e:
            logger.warning(f"Failed to parse job listing: {e}")
            return None
