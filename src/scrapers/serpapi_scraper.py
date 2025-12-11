"""
SerpApi Google Jobs Scraper

The industry standard for job search AI agents.
Google Jobs aggregates listings from LinkedIn, Glassdoor, Indeed, ZipRecruiter,
and thousands of company career pages into one place.

SerpApi provides clean JSON data from Google's job widget.
"""

import logging
import hashlib
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import re

import requests

from src.scrapers.base_scraper import BaseScraper, ScraperConfig
from src.database.db_manager import Job

logger = logging.getLogger(__name__)


class SerpApiScraper(BaseScraper):
    """
    Scraper using SerpApi's Google Jobs API.
    
    This is the most reliable way to get job listings because:
    - Google already aggregates from 50+ job boards
    - No need to maintain separate scrapers for each site
    - Clean, structured JSON responses
    - Handles anti-bot measures automatically
    
    Requires SERPAPI_API_KEY environment variable or config setting.
    """
    
    def __init__(self, config: ScraperConfig):
        super().__init__(config)
        self.api_url = "https://serpapi.com/search"
        
        # Get API key from config or environment
        import os
        params = config.search_params if hasattr(config, 'search_params') else {}
        self.api_key = params.get("api_key") or os.environ.get("SERPAPI_API_KEY", "")
        
        if not self.api_key:
            logger.warning("SERPAPI_API_KEY not set - SerpApi scraper will be disabled")
        
        # Configuration options
        self.results_per_query = params.get("results_per_query", 40)
        self.location = params.get("location", "")  # e.g., "United States" or "Remote"
    
    def scrape(self, keywords: List[str], max_pages: int = 3) -> List[Job]:
        """
        Search Google Jobs via SerpApi for matching positions.
        
        Args:
            keywords: List of job-related keywords to search
            max_pages: Maximum result pages per keyword (10 results per page)
            
        Returns:
            List of Job objects found
        """
        if not self.api_key:
            logger.warning("SerpApi scraper disabled - no API key configured")
            return []
        
        all_jobs = []
        seen_ids = set()
        
        for keyword in keywords:
            try:
                jobs = self._search_keyword(keyword, max_pages)
                
                # Deduplicate
                for job in jobs:
                    if job.job_id not in seen_ids:
                        seen_ids.add(job.job_id)
                        all_jobs.append(job)
                        
            except Exception as e:
                logger.error(f"Error searching for '{keyword}': {e}")
                continue
        
        logger.info(f"SerpApi found {len(all_jobs)} unique jobs")
        return all_jobs
    
    def _search_keyword(self, keyword: str, max_pages: int) -> List[Job]:
        """Search for a single keyword across multiple pages using next_page_token."""
        jobs = []
        next_page_token = None
        
        for page in range(max_pages):
            params = {
                "engine": "google_jobs",
                "q": keyword,
                "api_key": self.api_key,
            }
            
            # Use next_page_token for pagination (start parameter deprecated)
            if next_page_token:
                params["next_page_token"] = next_page_token
            
            # Add location if specified
            if self.location:
                params["location"] = self.location
            
            try:
                self._rate_limit()
                
                response = requests.get(
                    self.api_url,
                    params=params,
                    timeout=self.config.timeout_seconds
                )
                
                if response.status_code == 401:
                    logger.error("SerpApi authentication failed - check API key")
                    break
                elif response.status_code == 400:
                    # Log the error details for debugging
                    try:
                        error_data = response.json()
                        logger.warning(f"SerpApi returned 400: {error_data.get('error', 'Unknown error')}")
                    except Exception:
                        logger.warning("SerpApi returned status 400")
                    break  # Don't continue on 400 errors
                elif response.status_code == 429:
                    logger.warning("SerpApi rate limit hit - stopping")
                    break
                elif response.status_code != 200:
                    logger.warning(f"SerpApi returned status {response.status_code}")
                    continue
                
                data = response.json()
                
                # Parse job results
                job_results = data.get("jobs_results", [])
                
                if not job_results:
                    logger.debug(f"No more results for '{keyword}' at page {page}")
                    break
                
                for job_data in job_results:
                    job = self._parse_job(job_data, keyword)
                    if job:
                        jobs.append(job)
                
                logger.debug(f"Found {len(job_results)} jobs for '{keyword}' page {page}")
                
                # Get next page token for pagination
                serpapi_pagination = data.get("serpapi_pagination", {})
                next_page_token = serpapi_pagination.get("next_page_token")
                
                if not next_page_token:
                    logger.debug(f"No more pages for '{keyword}'")
                    break
                
            except requests.RequestException as e:
                logger.error(f"SerpApi request failed: {e}")
                break
        
        return jobs
    
    def _parse_job(self, data: Dict[str, Any], search_keyword: str) -> Optional[Job]:
        """Parse a SerpApi job result into a Job object."""
        try:
            title = data.get("title", "")
            company = data.get("company_name", "")
            
            if not title or not company:
                return None
            
            # Generate unique ID from title + company
            id_string = f"serpapi_{company}_{title}".lower()
            job_id = hashlib.md5(id_string.encode()).hexdigest()[:16]
            
            # Extract location
            location = data.get("location", "")
            
            # Build description from available fields
            description_parts = []
            
            if data.get("description"):
                description_parts.append(data["description"])
            
            # Add highlights if available
            highlights = data.get("job_highlights", [])
            for highlight in highlights:
                section_title = highlight.get("title", "")
                items = highlight.get("items", [])
                if section_title and items:
                    description_parts.append(f"\n{section_title}:")
                    for item in items:
                        description_parts.append(f"  • {item}")
            
            description = "\n".join(description_parts) if description_parts else "No description available"
            
            # Get application URL
            apply_options = data.get("apply_options", [])
            url = ""
            if apply_options:
                # Prefer direct company link
                for option in apply_options:
                    if "company" in option.get("title", "").lower():
                        url = option.get("link", "")
                        break
                if not url:
                    url = apply_options[0].get("link", "")
            
            # Fallback to related links
            if not url:
                related = data.get("related_links", [])
                if related:
                    url = related[0].get("link", "")
            
            # Parse posted date
            posted_at = data.get("detected_extensions", {}).get("posted_at", "")
            date_posted = self._parse_relative_date(posted_at)
            
            # Check for remote work
            extensions = data.get("detected_extensions", {})
            work_type = extensions.get("work_from_home", False)
            schedule = extensions.get("schedule_type", "")
            
            # Add to description
            if work_type or "remote" in location.lower():
                description = f"🏠 Remote Work Available\n\n{description}"
            if schedule:
                description = f"📅 {schedule}\n{description}"
            
            # Determine source from apply options
            source = "Google Jobs"
            if apply_options:
                source_name = apply_options[0].get("title", "Google Jobs")
                source = f"Google Jobs ({source_name})"
            
            return Job(
                job_id=job_id,
                url=url,
                title=title,
                organization=company,
                location=location,
                description=description,
                posted_date=date_posted.isoformat() if date_posted else None,
                source=source,
            )
            
        except Exception as e:
            logger.error(f"Error parsing SerpApi job: {e}")
            return None
    
    def _parse_relative_date(self, date_string: str) -> Optional[datetime]:
        """Parse relative date strings like '3 days ago' into datetime."""
        if not date_string:
            return None
        
        date_string = date_string.lower().strip()
        now = datetime.now()
        
        try:
            if "just posted" in date_string or "today" in date_string:
                return now
            elif "hour" in date_string:
                hours = int(re.search(r'(\d+)', date_string).group(1))
                return now - timedelta(hours=hours)
            elif "day" in date_string:
                days = int(re.search(r'(\d+)', date_string).group(1))
                return now - timedelta(days=days)
            elif "week" in date_string:
                weeks = int(re.search(r'(\d+)', date_string).group(1))
                return now - timedelta(weeks=weeks)
            elif "month" in date_string:
                months = int(re.search(r'(\d+)', date_string).group(1))
                return now - timedelta(days=months * 30)
        except:
            pass
        
        return None
    
    def parse_job_listing(self, element) -> Optional[Job]:
        """Not used for API-based scraper. See _parse_job instead."""
        return None
    
    def get_job_details(self, job_id: str) -> Optional[Job]:
        """SerpApi doesn't support fetching individual job details."""
        return None
