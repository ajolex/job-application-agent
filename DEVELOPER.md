# Developer Documentation

Technical documentation for developers who want to understand, modify, or extend the Job Application Agent.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         main.py                                  │
│                    (CLI Orchestrator)                           │
└─────────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        ▼                     ▼                     ▼
┌───────────────┐    ┌───────────────┐    ┌───────────────┐
│ ProfileParser │    │  Scrapers     │    │  Matcher      │
│ (profile/)    │    │  (scrapers/)  │    │  (matching/)  │
└───────────────┘    └───────────────┘    └───────────────┘
        │                     │                     │
        │                     ▼                     │
        │            ┌───────────────┐              │
        │            │ DatabaseMgr   │◄─────────────┘
        │            │ (database/)   │
        │            └───────────────┘
        │                     │
        ▼                     ▼
┌───────────────┐    ┌───────────────┐
│  Generator    │    │ EmailSender   │
│ (generator/)  │    │(notifications)│
└───────────────┘    └───────────────┘
```

## Tech Stack

| Component | Technology | Purpose |
|-----------|------------|---------|
| Runtime | Python 3.11+ | Core language |
| AI/LLM | Google Gemini (gemini-1.5-flash) | Job matching, cover letter generation |
| Database | SQLite | Job tracking, deduplication |
| Web Scraping | BeautifulSoup4, lxml, requests | HTML parsing |
| HTTP | requests, fake-useragent | Web requests with rotation |
| Email | Gmail API (google-api-python-client) | Notifications |
| PDF | ReportLab | Cover letter PDF generation |
| Config | PyYAML, python-dotenv | Configuration management |
| Retry Logic | tenacity | Exponential backoff |
| CI/CD | GitHub Actions | Daily automation |

## Project Structure

```
job-application-agent/
├── .github/
│   └── workflows/
│       └── job_search.yml      # GitHub Actions workflow
├── config/
│   └── config.yaml             # Main configuration file
├── src/
│   ├── __init__.py
│   ├── main.py                 # CLI entry point & orchestrator
│   ├── config.py               # Configuration loader & dataclasses
│   ├── profile/
│   │   ├── __init__.py
│   │   └── parser.py           # HTML CV/profile parser
│   ├── scrapers/
│   │   ├── __init__.py
│   │   ├── base_scraper.py     # Abstract base scraper class
│   │   ├── scraper_factory.py  # Factory for scraper instantiation
│   │   ├── reliefweb.py        # ReliefWeb API scraper
│   │   ├── devex.py            # DevEx scraper
│   │   ├── impactpool.py       # ImpactPool scraper
│   │   ├── unjobs.py           # UN Jobs scraper
│   │   ├── worldbank.py        # World Bank scraper
│   │   ├── eighty_thousand_hours.py  # 80,000 Hours scraper
│   │   └── econjobmarket.py    # EconJobMarket scraper
│   ├── matching/
│   │   ├── __init__.py
│   │   └── matcher.py          # Gemini-based job matching
│   ├── generator/
│   │   ├── __init__.py
│   │   ├── cover_letter.py     # Cover letter generation
│   │   └── question_answerer.py # Application Q&A generation
│   ├── notifications/
│   │   ├── __init__.py
│   │   └── email_sender.py     # Gmail API integration
│   └── database/
│       ├── __init__.py
│       └── db_manager.py       # SQLite database manager
├── templates/
│   ├── cover_letter_template.md
│   └── email_template.html     # Jinja2 email template
├── tests/
│   ├── __init__.py
│   ├── conftest.py             # pytest configuration
│   ├── test_config.py
│   ├── test_database.py
│   ├── test_profile_parser.py
│   └── test_matcher.py
├── data/                       # Runtime data (gitignored)
│   └── .gitkeep
├── .env.example
├── .gitignore
├── requirements.txt
├── README.md                   # User documentation
└── DEVELOPER.md               # This file
```

## Core Components

### 1. Configuration (`src/config.py`)

Loads configuration from YAML and environment variables:

```python
from src.config import load_config

config = load_config("config/config.yaml")
print(config.job_search.keywords)
print(config.matching.threshold)
```

**Key dataclasses:**
- `ProfileConfig` - Profile/CV settings
- `JobSearchConfig` - Keywords, thresholds
- `ScraperConfig` - Rate limits, enabled scrapers
- `MatchingConfig` - AI model settings
- `EmailConfig` - Notification settings
- `DatabaseConfig` - SQLite path

### 2. Profile Parser (`src/profile/parser.py`)

Extracts structured data from HTML CV:

```python
from src.profile.parser import ProfileParser

parser = ProfileParser(local_path="index.html")
profile = parser.parse()

# Returns dict with:
# - skills: List[str]
# - experience: List[dict]
# - education: List[dict]
# - research_interests: List[str]
# - publications: List[str]
```

**Extraction patterns:**
- Looks for semantic HTML sections (`<section id="skills">`)
- Falls back to heading-based extraction (`<h2>Skills</h2>`)
- Extracts list items, paragraphs, and structured content

### 3. Scrapers (`src/scrapers/`)

#### Base Scraper

All scrapers inherit from `BaseScraper`:

```python
from src.scrapers.base_scraper import BaseScraper
from src.database.db_manager import Job

class MyScraper(BaseScraper):
    def __init__(self, config: dict):
        super().__init__(config)
        self.base_url = config.get("base_url", "https://example.com")
    
    def scrape(self, keywords: List[str], max_pages: int = 5) -> List[Job]:
        """Main scraping method."""
        jobs = []
        for keyword in keywords:
            jobs.extend(self._search_keyword(keyword, max_pages))
        return jobs
    
    def parse_job_listing(self, element) -> Optional[Job]:
        """Parse a single job listing element."""
        return self.create_job(
            url=self._extract_url(element),
            title=self._extract_text(element, ".job-title"),
            organization=self._extract_text(element, ".company"),
            location=self._extract_text(element, ".location"),
            description=self._extract_text(element, ".description"),
            source="myscraper"
        )
```

**Built-in features:**
- Rate limiting with configurable delay
- Automatic retries with exponential backoff
- User-agent rotation
- Session management
- BeautifulSoup helpers

#### Scraper Factory

```python
from src.scrapers.scraper_factory import create_scrapers

scrapers = create_scrapers(config)
for scraper in scrapers:
    jobs = scraper.scrape(keywords)
```

### 4. Job Matcher (`src/matching/matcher.py`)

AI-powered job matching using Gemini:

```python
from src.matching.matcher import JobMatcher, MatchScore

matcher = JobMatcher(api_key="your_key")
score: MatchScore = matcher.match_job(job, profile)

# MatchScore dataclass:
# - overall_score: float (0-100)
# - skills_match: float
# - experience_match: float
# - research_match: float
# - qualifications_match: float
# - reasoning: str
# - highlights: List[str]
# - concerns: List[str]
```

**Matching prompt template:**
- Sends profile summary + job description to Gemini
- Requests JSON response with scores and reasoning
- Handles rate limiting and API errors

### 5. Content Generator (`src/generator/`)

#### Cover Letter Generator

```python
from src.generator.cover_letter import CoverLetterGenerator

generator = CoverLetterGenerator(api_key="your_key")
letter = generator.generate(job, profile, match_score)
pdf_path = generator.save_as_pdf(letter, "output/cover_letter.pdf")
```

#### Question Answerer

```python
from src.generator.question_answerer import QuestionAnswerer

qa = QuestionAnswerer(api_key="your_key")
answers = qa.answer_questions(
    questions=["Why are you interested in this role?"],
    job=job,
    profile=profile
)
```

### 6. Database Manager (`src/database/db_manager.py`)

SQLite-based job tracking:

```python
from src.database.db_manager import DatabaseManager, Job

db = DatabaseManager("data/jobs.db")

# Add jobs
job = Job(url="...", title="...", organization="...", source="devex")
job_id = db.add_job(job)

# Check if processed
if not db.is_job_processed(job.url):
    # Process job...
    db.mark_job_processed(job.url, content_hash)

# Get unprocessed jobs
jobs = db.get_unprocessed_jobs()

# Store match results
db.add_match_result(match_result)

# Statistics
stats = db.get_statistics()
```

**Database schema:**
```sql
-- jobs: All discovered jobs
CREATE TABLE jobs (
    id INTEGER PRIMARY KEY,
    url TEXT UNIQUE,
    title TEXT,
    organization TEXT,
    location TEXT,
    description TEXT,
    posted_date TEXT,
    deadline TEXT,
    salary TEXT,
    job_type TEXT,
    source TEXT,
    created_at TIMESTAMP
);

-- processed_jobs: Tracking which jobs have been processed
CREATE TABLE processed_jobs (
    id INTEGER PRIMARY KEY,
    job_url TEXT UNIQUE,
    content_hash TEXT,
    processed_at TIMESTAMP
);

-- match_results: AI matching scores
CREATE TABLE match_results (
    id INTEGER PRIMARY KEY,
    job_id INTEGER,
    overall_score REAL,
    skills_score REAL,
    experience_score REAL,
    research_score REAL,
    reasoning TEXT,
    created_at TIMESTAMP
);

-- cover_letters: Generated cover letters
CREATE TABLE cover_letters (
    id INTEGER PRIMARY KEY,
    job_id INTEGER,
    content TEXT,
    pdf_path TEXT,
    created_at TIMESTAMP
);
```

### 7. Email Sender (`src/notifications/email_sender.py`)

Gmail API integration:

```python
from src.notifications.email_sender import EmailSender

sender = EmailSender(
    credentials_path="credentials.json",
    token_path="token.json"
)

sender.send_daily_summary(
    to_email="user@example.com",
    matched_jobs=jobs_with_scores,
    attachments=["output/cover_letter.pdf"]
)
```

**OAuth flow:**
1. First run opens browser for authentication
2. Saves token to `token.json` for future use
3. Automatically refreshes expired tokens

## CLI Reference

```bash
python -m src.main [OPTIONS]

Options:
  -c, --config PATH       Config file path (default: config/config.yaml)
  -v, --verbose           Enable debug logging
  --dry-run               Run without sending emails
  --skip-scraping         Use existing database, skip scraping
  --skip-matching         Skip AI matching step
  --skip-cover-letters    Skip cover letter generation
  --skip-email            Skip email notification
  --stats                 Show database statistics and exit
  -h, --help              Show help message
```

## Adding a New Scraper

1. **Create scraper file** (`src/scrapers/myboard.py`):

```python
"""Scraper for MyBoard job site."""
import logging
from typing import List, Optional
from bs4 import Tag

from src.scrapers.base_scraper import BaseScraper
from src.database.db_manager import Job

logger = logging.getLogger(__name__)


class MyBoardScraper(BaseScraper):
    """Scraper for MyBoard job listings."""
    
    def __init__(self, config: dict):
        super().__init__(config)
        self.base_url = config.get("base_url", "https://myboard.com")
        self.search_url = f"{self.base_url}/jobs/search"
    
    def scrape(self, keywords: List[str], max_pages: int = 5) -> List[Job]:
        """Scrape jobs matching keywords."""
        jobs = []
        
        for keyword in keywords:
            logger.info(f"Searching MyBoard for: {keyword}")
            
            for page in range(1, max_pages + 1):
                page_jobs = self._scrape_page(keyword, page)
                if not page_jobs:
                    break
                jobs.extend(page_jobs)
                self._rate_limit()
        
        return self._deduplicate(jobs)
    
    def _scrape_page(self, keyword: str, page: int) -> List[Job]:
        """Scrape a single page of results."""
        params = {"q": keyword, "page": page}
        soup = self._get_soup(self.search_url, params=params)
        
        if not soup:
            return []
        
        listings = soup.select(".job-listing")
        return [
            job for listing in listings
            if (job := self.parse_job_listing(listing))
        ]
    
    def parse_job_listing(self, element: Tag) -> Optional[Job]:
        """Parse a job listing element into a Job object."""
        try:
            url = self._extract_url(element, "a.job-link")
            if not url:
                return None
            
            return self.create_job(
                url=self._make_absolute_url(url),
                title=self._extract_text(element, ".job-title"),
                organization=self._extract_text(element, ".company-name"),
                location=self._extract_text(element, ".location"),
                description=self._extract_text(element, ".description"),
                posted_date=self._extract_text(element, ".posted-date"),
                deadline=self._extract_text(element, ".deadline"),
                source="myboard"
            )
        except Exception as e:
            logger.warning(f"Failed to parse listing: {e}")
            return None
```

2. **Register in factory** (`src/scrapers/scraper_factory.py`):

```python
from src.scrapers.myboard import MyBoardScraper

SCRAPER_CLASSES = {
    "reliefweb": ReliefWebScraper,
    "devex": DevExScraper,
    # ... other scrapers
    "myboard": MyBoardScraper,  # Add this line
}
```

3. **Add configuration** (`config/config.yaml`):

```yaml
scrapers:
  enabled:
    - myboard  # Add to enabled list
    
scraper_configs:
  myboard:
    base_url: "https://myboard.com"
    rate_limit_seconds: 2
```

## Testing

```bash
# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_database.py -v

# Run with coverage
pytest tests/ --cov=src --cov-report=html
```

**Test structure:**
- `test_config.py` - Configuration loading tests
- `test_database.py` - Database operations tests
- `test_profile_parser.py` - Profile extraction tests
- `test_matcher.py` - Matching logic tests

## GitHub Actions Workflow

The workflow (`.github/workflows/job_search.yml`) runs daily:

```yaml
on:
  schedule:
    - cron: '0 8 * * *'  # 8:00 AM UTC daily
  workflow_dispatch:      # Manual trigger

jobs:
  search:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
      - run: pip install -r requirements.txt
      - run: python -m src.main
        env:
          GEMINI_API_KEY: ${{ secrets.GEMINI_API_KEY }}
          EMAIL_ADDRESS: ${{ secrets.EMAIL_ADDRESS }}
```

**Required secrets:**
| Secret | Description |
|--------|-------------|
| `GEMINI_API_KEY` | Google Gemini API key |
| `EMAIL_ADDRESS` | Notification recipient |
| `GMAIL_CREDENTIALS` | OAuth credentials JSON |
| `GMAIL_TOKEN` | OAuth token JSON |

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `GEMINI_API_KEY` | Yes | Google Gemini API key |
| `EMAIL_ADDRESS` | Yes | Email for notifications |
| `CONFIG_PATH` | No | Override config file path |
| `LOG_LEVEL` | No | DEBUG, INFO, WARNING, ERROR |

## Error Handling

The system uses structured error handling:

```python
# Scraper errors - logged, continues with next
try:
    jobs = scraper.scrape(keywords)
except ScraperError as e:
    logger.error(f"Scraper failed: {e}")
    continue

# API errors - retry with backoff
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(min=1, max=10)
)
def call_gemini_api(self, prompt):
    ...

# Critical errors - fail fast
if not config.gemini_api_key:
    raise ValueError("GEMINI_API_KEY not configured")
```

## Performance Considerations

1. **Rate limiting**: Configurable delay between requests (default 2s)
2. **Pagination limits**: Max pages per keyword to avoid excessive scraping
3. **Database indexing**: URLs are indexed for fast deduplication
4. **Caching**: Profile parsing results are cached
5. **Batch processing**: Jobs are processed in batches for email

## Security Notes

- API keys stored in environment variables, never in code
- OAuth tokens stored locally, gitignored
- No sensitive data logged
- HTTPS for all external requests
- Database contains no authentication data

## Extending the System

### Custom Matching Criteria

Modify `src/matching/matcher.py`:

```python
def _build_prompt(self, job: Job, profile: dict) -> str:
    return f"""
    Evaluate this job match with emphasis on:
    1. Research methodology alignment (weight: 30%)
    2. Geographic experience (weight: 20%)
    3. Technical skills (weight: 25%)
    4. Education requirements (weight: 25%)
    
    {self._format_profile(profile)}
    
    {self._format_job(job)}
    """
```

### Custom Email Templates

Modify `templates/email_template.html` (Jinja2):

```html
{% for job in jobs %}
<div class="job-card">
  <h3>{{ job.title }}</h3>
  <p>Score: {{ job.score }}/100</p>
  <!-- Customize layout -->
</div>
{% endfor %}
```

### Alternative AI Providers

Replace Gemini with OpenAI in `matcher.py`:

```python
from openai import OpenAI

class JobMatcher:
    def __init__(self, api_key: str):
        self.client = OpenAI(api_key=api_key)
    
    def _call_api(self, prompt: str) -> str:
        response = self.client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content
```

## Troubleshooting

### Debug Mode

```bash
python -m src.main -v --dry-run
```

### Check Database

```python
from src.database.db_manager import DatabaseManager
db = DatabaseManager("data/jobs.db")
print(db.get_statistics())
```

### Test Individual Scraper

```python
from src.scrapers.devex import DevExScraper
scraper = DevExScraper({"base_url": "https://devex.com"})
jobs = scraper.scrape(["economist"], max_pages=1)
print(f"Found {len(jobs)} jobs")
```

### Validate Gmail Auth

```python
from src.notifications.email_sender import EmailSender
sender = EmailSender("credentials.json", "token.json")
# Will prompt for auth if needed
```

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/my-feature`)
3. Write tests for new functionality
4. Ensure all tests pass (`pytest tests/ -v`)
5. Submit a pull request

## License

MIT License - see LICENSE file.
