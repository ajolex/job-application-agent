"""
JSearch RapidAPI Scraper

Popular choice for indie developers and smaller projects.
Aggregates jobs from LinkedIn, Indeed, Glassdoor, and other major boards.

Requires a RapidAPI key with JSearch subscription.
"""

import logging
import hashlib
from typing import List, Optional, Dict, Any
from datetime import datetime
import re

import requests

from src.scrapers.base_scraper import BaseScraper, ScraperConfig
from src.database.db_manager import Job

logger = logging.getLogger(__name__)


class JSearchScraper(BaseScraper):
    """
    Scraper using JSearch API via RapidAPI.
    
    JSearch is a massive job aggregator that scrapes listings from:
    - LinkedIn
    - Indeed
    - Glassdoor
    - ZipRecruiter
    - And many more
    
    It's cheaper than SerpApi and great for side projects.
    Requires RAPIDAPI_KEY environment variable or config setting.
    """
    
    def __init__(self, config: ScraperConfig):
        super().__init__(config)
        self.api_url = "https://jsearch.p.rapidapi.com/search"
        
        # Get API key from config or environment
        import os
        params = config.search_params if hasattr(config, 'search_params') else {}
        self.api_key = params.get("api_key") or os.environ.get("RAPIDAPI_KEY", "")
        
        if not self.api_key:
            logger.warning("RAPIDAPI_KEY not set - JSearch scraper will be disabled")
        
        # Configuration options
        self.results_per_page = params.get("results_per_page", 20)
        self.country = params.get("country", "us")
        self.date_posted = params.get("date_posted", "week")  # all, today, 3days, week, month
        self.remote_only = params.get("remote_only", False)
    
    def scrape(self, keywords: List[str], max_pages: int = 3) -> List[Job]:
        """
        Search JSearch API for matching positions.
        
        Args:
            keywords: List of job-related keywords to search
            max_pages: Maximum result pages per keyword
            
        Returns:
            List of Job objects found
        """
        if not self.api_key:
            logger.warning("JSearch scraper disabled - no API key configured")
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
                logger.error(f"Error searching JSearch for '{keyword}': {e}")
                continue
        
        logger.info(f"JSearch found {len(all_jobs)} unique jobs")
        return all_jobs
    
    def _search_keyword(self, keyword: str, max_pages: int) -> List[Job]:
        """Search for a single keyword across multiple pages."""
        jobs = []
        
        headers = {
            "X-RapidAPI-Key": self.api_key,
            "X-RapidAPI-Host": "jsearch.p.rapidapi.com"
        }
        
        for page in range(1, max_pages + 1):
            params = {
                "query": keyword,
                "page": str(page),
                "num_pages": "1",
                "date_posted": self.date_posted,
                "country": self.country,
            }
            
            # Add remote filter if enabled
            if self.remote_only:
                params["remote_jobs_only"] = "true"
            
            try:
                self._rate_limit()
                
                response = requests.get(
                    self.api_url,
                    headers=headers,
                    params=params,
                    timeout=self.config.timeout_seconds
                )
                
                if response.status_code == 401:
                    logger.error("JSearch authentication failed - check API key")
                    break
                elif response.status_code == 403:
                    logger.error("JSearch API forbidden - check subscription")
                    break
                elif response.status_code == 429:
                    logger.warning("JSearch rate limit hit - stopping")
                    break
                elif response.status_code != 200:
                    logger.warning(f"JSearch returned status {response.status_code}")
                    continue
                
                data = response.json()
                
                # Check for API errors
                if data.get("status") == "ERROR":
                    logger.error(f"JSearch API error: {data.get('message', 'Unknown error')}")
                    break
                
                # Parse job results
                job_results = data.get("data", [])
                
                if not job_results:
                    logger.debug(f"No more results for '{keyword}' at page {page}")
                    break
                
                for job_data in job_results:
                    job = self._parse_job(job_data, keyword)
                    if job:
                        jobs.append(job)
                
                logger.debug(f"Found {len(job_results)} jobs for '{keyword}' page {page}")
                
            except requests.RequestException as e:
                logger.error(f"JSearch request failed: {e}")
                break
        
        return jobs
    
    def _parse_job(self, data: Dict[str, Any], search_keyword: str) -> Optional[Job]:
        """Parse a JSearch job result into a Job object."""
        try:
            title = data.get("job_title", "")
            company = data.get("employer_name", "")
            
            if not title or not company:
                return None
            
            # Use JSearch's job_id or generate one
            job_id = data.get("job_id", "")
            if not job_id:
                id_string = f"jsearch_{company}_{title}".lower()
                job_id = hashlib.md5(id_string.encode()).hexdigest()[:16]
            else:
                # Shorten the very long JSearch IDs
                job_id = f"js_{hashlib.md5(job_id.encode()).hexdigest()[:12]}"
            
            # Location
            city = data.get("job_city", "")
            state = data.get("job_state", "")
            country = data.get("job_country", "")
            location_parts = [p for p in [city, state, country] if p]
            location = ", ".join(location_parts) if location_parts else "Not specified"
            
            # Description
            description = data.get("job_description", "No description available")
            
            # Add job highlights if available
            highlights = data.get("job_highlights", {})
            if highlights:
                qualifications = highlights.get("Qualifications", [])
                responsibilities = highlights.get("Responsibilities", [])
                benefits = highlights.get("Benefits", [])
                
                extras = []
                if qualifications:
                    extras.append("\n📋 Qualifications:")
                    for q in qualifications[:5]:  # Limit to 5
                        extras.append(f"  • {q}")
                if responsibilities:
                    extras.append("\n📝 Responsibilities:")
                    for r in responsibilities[:5]:
                        extras.append(f"  • {r}")
                if benefits:
                    extras.append("\n🎁 Benefits:")
                    for b in benefits[:5]:
                        extras.append(f"  • {b}")
                
                if extras:
                    description = description + "\n" + "\n".join(extras)
            
            # URL
            url = data.get("job_apply_link", "") or data.get("job_google_link", "")
            
            # Source
            publisher = data.get("job_publisher", "JSearch")
            source = f"JSearch ({publisher})"
            
            # Date posted
            date_posted = None
            posted_str = data.get("job_posted_at_datetime_utc", "")
            if posted_str:
                try:
                    # ISO format: 2024-01-15T10:30:00.000Z
                    date_posted = datetime.fromisoformat(posted_str.replace("Z", "+00:00"))
                except:
                    pass
            
            # Salary
            salary_min = data.get("job_min_salary")
            salary_max = data.get("job_max_salary")
            salary_currency = data.get("job_salary_currency", "USD")
            salary_period = data.get("job_salary_period", "")
            
            salary = ""
            if salary_min or salary_max:
                if salary_min and salary_max:
                    salary = f"{salary_currency} {salary_min:,.0f} - {salary_max:,.0f}"
                elif salary_min:
                    salary = f"{salary_currency} {salary_min:,.0f}+"
                elif salary_max:
                    salary = f"Up to {salary_currency} {salary_max:,.0f}"
                if salary_period:
                    salary += f" ({salary_period})"
            
            # Job type
            job_type = data.get("job_employment_type", "")
            if job_type:
                job_type = job_type.replace("_", " ").title()
            
            # Remote
            is_remote = data.get("job_is_remote", False)
            
            # Experience level (try to extract from requirements)
            experience_level = ""
            required_exp = data.get("job_required_experience", {})
            if required_exp:
                exp_in_months = required_exp.get("required_experience_in_months")
                if exp_in_months:
                    years = exp_in_months / 12
                    if years < 2:
                        experience_level = "Entry Level"
                    elif years < 5:
                        experience_level = "Mid Level"
                    else:
                        experience_level = "Senior Level"
            
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
            logger.error(f"Error parsing JSearch job: {e}")
            return None
    
    def parse_job_listing(self, element) -> Optional[Job]:
        """Not used for API-based scraper. See _parse_job instead."""
        return None
    
    def get_job_details(self, job_id: str) -> Optional[Job]:
        """
        Get detailed information about a specific job.
        
        JSearch has a job-details endpoint for this.
        """
        if not self.api_key:
            return None
        
        headers = {
            "X-RapidAPI-Key": self.api_key,
            "X-RapidAPI-Host": "jsearch.p.rapidapi.com"
        }
        
        try:
            self._rate_limit()
            
            response = requests.get(
                "https://jsearch.p.rapidapi.com/job-details",
                headers=headers,
                params={"job_id": job_id},
                timeout=self.config.timeout_seconds
            )
            
            if response.status_code == 200:
                data = response.json()
                job_data = data.get("data", [])
                if job_data:
                    return self._parse_job(job_data[0], "")
            
        except Exception as e:
            logger.error(f"Error fetching job details: {e}")
        
        return None
