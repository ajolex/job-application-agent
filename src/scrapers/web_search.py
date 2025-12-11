"""
Web Search Scraper

Uses web search to find job postings across the entire internet.
More flexible than site-specific scrapers and doesn't break when sites change.
"""

import logging
import re
import urllib.parse
from typing import List, Optional
from bs4 import BeautifulSoup, Tag

from src.scrapers.base_scraper import BaseScraper, ScraperConfig
from src.database.db_manager import Job

logger = logging.getLogger(__name__)


class WebSearchScraper(BaseScraper):
    """
    Scraper that uses web search engines to find jobs across the internet.
    
    Uses DuckDuckGo HTML search (no API key required) to find job postings
    matching keywords, then extracts job details from the results.
    """
    
    def __init__(self, config: ScraperConfig):
        super().__init__(config)
        self.search_url = "https://html.duckduckgo.com/html/"
        
        # Get extra settings from search_params if available
        extra = config.search_params if hasattr(config, 'search_params') else {}
        self.max_results_per_keyword = extra.get("max_results_per_keyword", 30)
        
        # Sites to prioritize in search
        self.priority_sites = extra.get("priority_sites", [
            "careers.un.org",
            "jobs.undp.org", 
            "worldbank.org/careers",
            "devex.com/jobs",
            "reliefweb.int/jobs",
            "impactpool.org",
            "econjobmarket.org",
            "80000hours.org/job-board",
            "indeed.com",
            "linkedin.com/jobs",
            "idealist.org",
            "devnetjobs.org",
            "unjobs.org",
        ])
    
    def scrape(self, keywords: List[str], max_pages: int = 3) -> List[Job]:
        """
        Search the web for jobs matching keywords.
        
        Args:
            keywords: List of job-related keywords to search
            max_pages: Maximum pages of search results per keyword
            
        Returns:
            List of Job objects found
        """
        logger.info(f"Searching web for jobs with keywords: {keywords[:5]}...")
        
        all_jobs = []
        seen_urls: set[str] = set()
        
        for keyword in keywords[:5]:  # Limit keywords to avoid too many searches
            try:
                jobs = self._search_keyword(keyword, max_pages)
                
                # Deduplicate
                for job in jobs:
                    if job.url not in seen_urls:
                        seen_urls.add(job.url)
                        all_jobs.append(job)
                
                self._rate_limit()
                
            except Exception as e:
                logger.warning(f"Error searching for '{keyword}': {e}")
                continue
        
        logger.info(f"Found {len(all_jobs)} unique jobs from web search")
        return all_jobs
    
    def _search_keyword(self, keyword: str, max_pages: int) -> List[Job]:
        """Search for a single keyword."""
        jobs: List[Job] = []
        
        # Build search query with job-related terms
        search_query = f"{keyword} job OR career OR position OR vacancy 2024 OR 2025"
        
        for page in range(max_pages):
            try:
                page_jobs = self._search_page(search_query, page)
                if not page_jobs:
                    break
                jobs.extend(page_jobs)
                self._rate_limit()
            except Exception as e:
                logger.warning(f"Error on page {page} for '{keyword}': {e}")
                break
        
        return jobs
    
    def _search_page(self, query: str, page: int = 0) -> List[Job]:
        """Execute search and parse results page."""
        jobs: List[Job] = []
        
        # DuckDuckGo HTML search parameters
        params = {
            "q": query,
            "b": str(page * 30),  # Offset for pagination
            "kl": "wt-wt",  # No region filter
        }
        
        try:
            response = self.session.post(
                self.search_url,
                data=params,
                timeout=self.config.timeout_seconds
            )
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, "lxml")
            
            # Find search results
            results = soup.select(".result")
            
            for result in results:
                job = self._parse_search_result(result)
                if job:
                    jobs.append(job)
            
            logger.debug(f"Found {len(jobs)} results on page {page}")
            
        except Exception as e:
            logger.warning(f"Search request failed: {e}")
        
        return jobs
    
    def _parse_search_result(self, result: Tag) -> Optional[Job]:
        """Parse a search result into a Job object."""
        try:
            # Extract URL
            link = result.select_one(".result__a")
            if not link:
                return None
            
            url_attr = link.get("href", "")
            url = str(url_attr) if url_attr else ""
            if not url:
                return None
            
            # Clean DuckDuckGo redirect URL
            if "duckduckgo.com" in url:
                parsed = urllib.parse.urlparse(url)
                params = urllib.parse.parse_qs(parsed.query)
                url = params.get("uddg", [url])[0]
            
            # Skip non-job URLs
            if not self._is_likely_job_url(url):
                return None
            
            # Extract title
            title = link.get_text(strip=True)
            if not title:
                return None
            
            # Extract snippet/description
            snippet_elem = result.select_one(".result__snippet")
            description = snippet_elem.get_text(strip=True) if snippet_elem else ""
            
            # Extract source domain as organization
            domain_elem = result.select_one(".result__url")
            domain = domain_elem.get_text(strip=True) if domain_elem else ""
            organization = self._extract_org_from_domain(domain)
            
            return self.create_job(
                url=url,
                title=self._clean_title(title),
                organization=organization,
                description=description,
                location="See posting"
            )
            
        except Exception as e:
            logger.debug(f"Failed to parse search result: {e}")
            return None
    
    def _is_likely_job_url(self, url: str) -> bool:
        """Check if URL is likely a job posting."""
        url_lower = url.lower()
        
        # Positive indicators
        job_indicators = [
            "/job", "/career", "/position", "/vacancy", "/opening",
            "/jobs/", "/careers/", "/opportunities/", "/work-with-us",
            "/join-us", "/hiring", "jobid=", "job_id=", "positionid=",
            "econjobmarket.org", "devex.com", "reliefweb.int",
            "impactpool.org", "unjobs.org", "idealist.org",
            "linkedin.com/jobs", "indeed.com", "80000hours.org"
        ]
        
        # Negative indicators (not job postings)
        non_job_indicators = [
            "linkedin.com/in/",  # Profile pages
            "linkedin.com/company/",  # Company pages
            "/article", "/blog", "/news", "/press",
            "wikipedia.org", "youtube.com", "facebook.com",
            "twitter.com", ".pdf", ".doc"
        ]
        
        # Check negative indicators first
        for indicator in non_job_indicators:
            if indicator in url_lower:
                return False
        
        # Check positive indicators
        for indicator in job_indicators:
            if indicator in url_lower:
                return True
        
        return False
    
    def _extract_org_from_domain(self, domain: str) -> str:
        """Extract organization name from domain."""
        if not domain:
            return "Unknown"
        
        # Remove www. and common TLDs
        domain = re.sub(r'^(www\.)?', '', domain)
        domain = re.sub(r'\.(com|org|int|net|gov|edu|io).*$', '', domain)
        
        # Map known domains to proper names
        domain_map = {
            "worldbank": "World Bank",
            "undp": "UNDP",
            "unicef": "UNICEF",
            "who": "WHO",
            "unfpa": "UNFPA",
            "unhcr": "UNHCR",
            "wfp": "WFP",
            "devex": "DevEx",
            "reliefweb": "ReliefWeb",
            "impactpool": "ImpactPool",
            "econjobmarket": "EconJobMarket",
            "80000hours": "80,000 Hours",
            "linkedin": "LinkedIn",
            "indeed": "Indeed",
            "idealist": "Idealist",
        }
        
        for key, name in domain_map.items():
            if key in domain.lower():
                return name
        
        # Capitalize and return
        return domain.replace("-", " ").replace("_", " ").title()
    
    def _clean_title(self, title: str) -> str:
        """Clean up job title from search results."""
        # Remove common suffixes
        title = re.sub(r'\s*[-–|]\s*(LinkedIn|Indeed|Glassdoor|Apply Now).*$', '', title, flags=re.IGNORECASE)
        title = re.sub(r'\s*\|\s*.*$', '', title)  # Remove everything after |
        
        # Trim whitespace
        return title.strip()
    
    def parse_job_listing(self, element: Tag) -> Optional[Job]:
        """Required by base class but not used in web search."""
        return self._parse_search_result(element)
