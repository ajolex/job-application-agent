"""
Base Scraper for Job Application Agent.

Provides common functionality for all job board scrapers including:
- Rate limiting
- Retry logic with exponential backoff
- User agent rotation
- Session management
- Error handling
"""

import logging
import random
import time
from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from fake_useragent import UserAgent

from src.database.db_manager import Job

logger = logging.getLogger(__name__)


# Common user agents as fallback
FALLBACK_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
]


@dataclass
class ScraperConfig:
    """Configuration for a scraper."""
    name: str
    base_url: str
    rate_limit_seconds: float = 2.0
    timeout_seconds: int = 30
    max_retries: int = 3
    rotate_user_agent: bool = True
    extra_headers: Dict[str, str] = field(default_factory=dict)
    search_params: Dict[str, Any] = field(default_factory=dict)


class BaseScraper(ABC):
    """
    Abstract base class for job board scrapers.
    
    Provides common functionality for making HTTP requests,
    parsing HTML, and handling errors.
    
    Subclasses must implement:
    - scrape(): Main scraping logic
    - parse_job_listing(): Parse individual job listings
    - parse_job_details(): Parse full job details page
    """
    
    def __init__(self, config: ScraperConfig):
        """
        Initialize base scraper.
        
        Args:
            config: Scraper configuration
        """
        self.config = config
        self.session = requests.Session()
        self._last_request_time = 0.0
        self._request_count = 0
        
        # Initialize user agent
        try:
            self._ua = UserAgent()
        except Exception:
            self._ua = None
            logger.warning("Failed to initialize UserAgent, using fallback")
        
        # Set up session headers
        self._setup_session()
    
    def _setup_session(self) -> None:
        """Configure session with default headers."""
        headers = {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
        }
        headers.update(self.config.extra_headers)
        self.session.headers.update(headers)
        self._rotate_user_agent()
    
    def _rotate_user_agent(self) -> None:
        """Rotate to a new user agent."""
        if self.config.rotate_user_agent:
            if self._ua:
                try:
                    ua = self._ua.random
                except Exception:
                    ua = random.choice(FALLBACK_USER_AGENTS)
            else:
                ua = random.choice(FALLBACK_USER_AGENTS)
            self.session.headers["User-Agent"] = ua
    
    def _rate_limit(self) -> None:
        """Enforce rate limiting between requests."""
        elapsed = time.time() - self._last_request_time
        if elapsed < self.config.rate_limit_seconds:
            sleep_time = self.config.rate_limit_seconds - elapsed
            logger.debug(f"Rate limiting: sleeping {sleep_time:.2f}s")
            time.sleep(sleep_time)
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        retry=retry_if_exception_type((requests.RequestException, ConnectionError)),
        before_sleep=lambda retry_state: logger.warning(
            f"Request failed, retrying ({retry_state.attempt_number}/3)..."
        )
    )
    def _make_request(
        self,
        url: str,
        method: str = "GET",
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> requests.Response:
        """
        Make an HTTP request with rate limiting and retries.
        
        Args:
            url: URL to request
            method: HTTP method (GET, POST, etc.)
            params: Query parameters
            data: Form data
            json_data: JSON body
            headers: Additional headers
            
        Returns:
            Response object
            
        Raises:
            requests.RequestException: If request fails after retries
        """
        self._rate_limit()
        
        # Rotate user agent periodically
        if self._request_count % 10 == 0:
            self._rotate_user_agent()
        
        self._request_count += 1
        
        try:
            response = self.session.request(
                method=method,
                url=url,
                params=params,
                data=data,
                json=json_data,
                headers=headers,
                timeout=self.config.timeout_seconds,
            )
            
            self._last_request_time = time.time()
            
            # Check for common error responses
            if response.status_code == 403:
                logger.warning(f"Access forbidden (403) for {url}")
                raise requests.HTTPError("Access forbidden - possible bot detection")
            elif response.status_code == 429:
                logger.warning(f"Rate limited (429) for {url}")
                # Increase rate limit and retry
                self.config.rate_limit_seconds *= 2
                raise requests.HTTPError("Rate limited - backing off")
            
            response.raise_for_status()
            
            logger.debug(f"Successfully fetched {url} ({response.status_code})")
            return response
            
        except requests.RequestException as e:
            logger.error(f"Request failed for {url}: {e}")
            raise
    
    def get(self, url: str, **kwargs) -> requests.Response:
        """Make a GET request."""
        return self._make_request(url, method="GET", **kwargs)
    
    def post(self, url: str, **kwargs) -> requests.Response:
        """Make a POST request."""
        return self._make_request(url, method="POST", **kwargs)
    
    def get_soup(self, url: str, **kwargs) -> BeautifulSoup:
        """
        Fetch a URL and return parsed BeautifulSoup object.
        
        Args:
            url: URL to fetch
            **kwargs: Additional arguments for request
            
        Returns:
            BeautifulSoup object
        """
        response = self.get(url, **kwargs)
        return BeautifulSoup(response.content, "lxml")
    
    def make_absolute_url(self, url: str) -> str:
        """Convert relative URL to absolute URL."""
        if url.startswith(("http://", "https://")):
            return url
        return urljoin(self.config.base_url, url)
    
    def extract_text(self, element: Any, default: str = "") -> str:
        """Safely extract text from a BeautifulSoup element."""
        if element:
            return element.get_text(strip=True)
        return default
    
    def extract_attribute(self, element: Any, attr: str, default: str = "") -> str:
        """Safely extract an attribute from a BeautifulSoup element."""
        if element and element.get(attr):
            return element[attr]
        return default
    
    def create_job(
        self,
        url: str,
        title: str,
        organization: str,
        location: str = "",
        description: str = "",
        posted_date: str = "",
        deadline: str = "",
        requirements: str = "",
        application_url: str = "",
        raw_data: str = ""
    ) -> Job:
        """
        Create a Job object with auto-generated ID.
        
        Args:
            url: Job posting URL
            title: Job title
            organization: Hiring organization
            location: Job location
            description: Full job description
            posted_date: When job was posted
            deadline: Application deadline
            requirements: Job requirements
            application_url: Direct application URL
            raw_data: Raw scraped data for reference
            
        Returns:
            Job object
        """
        job_id = Job.generate_id(url, title, organization)
        
        return Job(
            job_id=job_id,
            url=url,
            title=title,
            organization=organization,
            location=location,
            description=description,
            posted_date=posted_date,
            deadline=deadline,
            requirements=requirements,
            application_url=application_url or url,
            source=self.config.name,
            raw_data=raw_data
        )
    
    @abstractmethod
    def scrape(self, keywords: List[str], max_pages: int = 5) -> List[Job]:
        """
        Scrape job listings from the board.
        
        Args:
            keywords: Search keywords
            max_pages: Maximum number of pages to scrape
            
        Returns:
            List of Job objects
        """
        pass
    
    @abstractmethod
    def parse_job_listing(self, element: Any) -> Optional[Job]:
        """
        Parse a job listing element from search results.
        
        Args:
            element: BeautifulSoup element containing job listing
            
        Returns:
            Job object or None if parsing fails
        """
        pass
    
    def parse_job_details(self, job: Job) -> Job:
        """
        Fetch and parse full job details page.
        
        Override in subclass if additional details need to be fetched.
        
        Args:
            job: Job object with URL
            
        Returns:
            Updated Job object with full details
        """
        return job
    
    def search_url(self, keywords: List[str], page: int = 1) -> str:
        """
        Build search URL for keywords.
        
        Override in subclass for site-specific URL structure.
        
        Args:
            keywords: Search keywords
            page: Page number
            
        Returns:
            Search URL string
        """
        query = " ".join(keywords)
        params = {"q": query, "page": page}
        params.update(self.config.search_params)
        
        base = urljoin(self.config.base_url, "/search")
        param_str = "&".join(f"{k}={v}" for k, v in params.items())
        return f"{base}?{param_str}"
    
    def get_name(self) -> str:
        """Get scraper name."""
        return self.config.name
    
    def close(self) -> None:
        """Close the session."""
        self.session.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


class APIScraper(BaseScraper):
    """
    Base class for scrapers that use an API instead of HTML parsing.
    
    Many job boards provide JSON APIs that are easier to work with.
    """
    
    def __init__(self, config: ScraperConfig):
        super().__init__(config)
        # Set JSON accept header
        self.session.headers["Accept"] = "application/json"
    
    def get_json(self, url: str, **kwargs) -> Dict[str, Any]:
        """
        Fetch a URL and return JSON response.
        
        Args:
            url: URL to fetch
            **kwargs: Additional arguments for request
            
        Returns:
            Parsed JSON response
        """
        response = self.get(url, **kwargs)
        return response.json()
    
    def post_json(self, url: str, json_data: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """
        Make POST request and return JSON response.
        
        Args:
            url: URL to post to
            json_data: JSON body
            **kwargs: Additional arguments
            
        Returns:
            Parsed JSON response
        """
        response = self.post(url, json_data=json_data, **kwargs)
        return response.json()
