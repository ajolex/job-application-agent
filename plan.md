# Job Application Agent - Build Plan

## Overview
Build a comprehensive Job Application Agent that automates job searching, matching, and application preparation for Development Economics Research positions.

### User Profile
- **Profile/CV source:** "G:\job-application-agent\index.html"
- **Field:** Development Economics Research
- The agent should extract skills, experience, qualifications, and research interests

## Technical Requirements

### Tech Stack
- **Language:** Python 3.11+
- **LLM:** Google Gemini API (user has API key)
- **Email:** Gmail API
- **Scheduling:** GitHub Actions (daily cron job)
- **Database:** SQLite (to track processed jobs and skip duplicates)

### Job Sources to Scrape/Query
1. EconJobMarket (econjobmarket.org)
2. DevEx (devex.com)
3. ReliefWeb (reliefweb.int/jobs)
4. ImpactPool (impactpool.org)
5. UNJobs (unjobs.org)
6. World Bank Jobs (worldbank.org/en/about/careers)
7. SSRN Jobs
8. IDEAs/RePEc (ideas.repec.org)
9. 80,000 Hours Job Board (https://jobs.80000hours.org/)
10. Any other relevant job boards for Development Economics Research

## Core Features

### 1. Profile Parser (src/profile/parser.py)
Scrape user's html profile/CV from "G:\job-application-agent\index.html"
Extract key metadata:
- Skills and competencies
- Work experience
- Education and qualifications
- Research interests
- Publications (if any)
- Cache the profile data locally

### 2. Job Scrapers (src/scrapers/)
Create individual scraper modules for each job board
Extract job metadata:
- Job title
- Organization
- Location
- Posted date
- Due date/deadline
- Job description
- Required qualifications
- Application URL
- Application requirements (cover letter, questions, etc.)
- Handle pagination and rate limiting
- Implement robust error handling

### 3. Job Matcher (src/matching/matcher.py)
Use Google Gemini to analyze job descriptions against user profile
Score relevance (0-100) based on:
- Skills match
- Experience match
- Research area alignment
- Qualification requirements
- Filter jobs above a configurable threshold (default: 70)

### 4. Cover Letter Generator (src/generator/cover_letter.py)
Use Gemini to generate personalized cover letters
- Use a customizable template structure, user to upload
- Incorporate:
  - User's relevant experience
  - Skills matching job requirements
  - Research interests alignment
  - Specific organization/role details

### 5. Question Answerer (src/generator/question_answerer.py)
For jobs with application questions
- Use Gemini to generate personalized answers based on:
  - User profile
  - Job requirements
  - Question context

### 6. Email Notifier (src/notifications/email_sender.py)
Use Gmail API to send daily summary emails for matched jobs
Email should include:
- Job summary (title, org, location, dates)
- Match score and reasoning
- Application instructions
- Attachments: personalized cover letter (PDF), CV
- Support HTML email templates

### 7. Database Manager (src/database/db_manager.py)
SQLite database to track:
- Processed jobs (job_id, url, title, org, processed_date)
- Application status
- Generated cover letters
- Skip jobs that have already been processed

### 8. GitHub Actions Workflow (.github/workflows/job_search.yml)
Run daily on schedule (configurable cron)
Use GitHub Secrets for sensitive data:
- GEMINI_API_KEY
- GMAIL_CREDENTIALS
- EMAIL_ADDRESS
- Cache dependencies for faster runs
- Upload artifacts (generated cover letters, logs)

## Project Structure

```
job-application-agent/
├── .github/
│   └── workflows/
│       └── job_search.yml
├── config/
│   └── config.yaml
├── src/
│   ├── __init__.py
│   ├── main.py
│   ├── profile/
│   │   ├── __init__.py
│   │   └── parser.py
│   ├── scrapers/
│   │   ├── __init__.py
│   │   ├── base_scraper.py
│   │   ├── econjobmarket.py
│   │   ├── devex.py
│   │   ├── reliefweb.py
│   │   ├── impactpool.py
│   │   ├── unjobs.py
│   │   ├── worldbank.py
│   │   ├── ssrn.py
│   │   └── ideas_repec.py
│   ├── matching/
│   │   ├── __init__.py
│   │   └── matcher.py
│   ├── generator/
│   │   ├── __init__.py
│   │   ├── cover_letter.py
│   │   └── question_answerer.py
│   ├── notifications/
│   │   ├── __init__.py
│   │   └── email_sender.py
│   └── database/
│       ├── __init__.py
│       └── db_manager.py
├── templates/
│   ├── cover_letter_template.md
│   └── email_template.html
├── data/
│   ├── .gitkeep
│   └── cv.pdf (placeholder)
├── tests/
│   └── __init__.py
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

## Configuration (config/config.yaml)

```yaml
profile:
  url: "https://ajolex.github.io/"
  cache_duration_hours: 24

job_search:
  keywords:
    - "development economics"
    - "research associate"
    - "predoctoral fellow"
    - "development researcher"
    - "research analyst"
    - "research manager"
    - "associate research manager"
    - "junior economist"
    - "researche assistant"
    - "economist"
    - "data analyst"
    - "impact evaluation"
    - "policy research"
  locations:
    - "Remote"
    - "Global"
  match_threshold: 70

scrapers:
  enabled:
    - econjobmarket
    - devex
    - reliefweb
    - impactpool
    - unjobs
    - worldbank
    - 80000hours
    - ssrn
  rate_limit_seconds: 2

email:
  recipient: "${EMAIL_ADDRESS}"
  send_summary: true
  attach_cover_letter: true
  attach_cv: true
```

## Implementation Steps

### Step 1: Initialize Project Structure
- Create all directories
- Initialize Git repository
- Create .gitignore
- Create requirements.txt with base dependencies
- Create module scaffolding (__init__.py files)

### Step 2: Build Configuration System
- Create config/config.yaml with job keywords, locations, API endpoints
- Implement configuration loader
- Create src/database/db_manager.py for SQLite job tracking

### Step 3: Implement Profile Parser
- Create src/profile/parser.py to scrape ajolex.github.io
- Extract skills, experience, education, research interests
- Implement local caching with timestamp validation
- Create profile data structures

### Step 4: Build Base Scraper Framework
- Create src/scrapers/base_scraper.py with common patterns
- Implement rate limiting, error handling, pagination logic
- Add retry mechanisms with exponential backoff
- Create standardized job data model

### Step 5: Implement 8 Job Board Scrapers
- Create individual modules in src/scrapers/ for each board:
  - econjobmarket.py
  - devex.py
  - reliefweb.py
  - impactpool.py
  - unjobs.py
  - worldbank.py
  - ssrn.py
  - ideas_repec.py
  - eighty_thousand_hours.py
- Use requests + BeautifulSoup for HTML parsing
- Handle board-specific HTML structures and pagination
- Implement error handling and logging for each scraper

### Step 6: Build Job Matching Engine
- Create src/matching/matcher.py using Gemini API
- Score jobs (0-100) based on:
  - Skills match
  - Experience alignment
  - Research area overlap
  - Qualification fit
- Filter jobs above configured threshold
- Cache matching results

### Step 7: Create Content Generators
- Build src/generator/cover_letter.py using Gemini
- Build src/generator/question_answerer.py using Gemini
- Personalize responses based on job/profile match
- Implement template system for customization
- Add quality checks and content validation

### Step 8: Implement Email Notification System
- Create src/notifications/email_sender.py using Gmail API
- Support both individual and summary emails
- Generate PDF cover letters
- Attach CV and cover letters
- Use HTML email templates
- Implement error handling and delivery confirmation

### Step 9: Assemble Main Orchestrator
- Create src/main.py to coordinate all modules:
  1. Fetch and cache user profile
  2. Scrape jobs from all enabled sources
  3. Match jobs against profile
  4. Generate personalized content
  5. Send emails
  6. Update database with processed jobs
- Implement logging and progress tracking
- Add error recovery mechanisms

### Step 10: Build GitHub Actions Workflow
- Create .github/workflows/job_search.yml
- Configure daily cron trigger (configurable schedule)
- Manage secrets: GEMINI_API_KEY, GMAIL_CREDENTIALS, EMAIL_ADDRESS
- Cache Python dependencies for faster runs
- Upload artifacts (logs, generated cover letters)
- Set up failure notifications

### Step 11: Add Testing & Documentation
- Create unit tests in tests/
- Create README.md with:
  - Setup instructions
  - Configuration guide
  - Usage examples
  - Troubleshooting
- Create .env.example template
- Add inline code documentation
- Create API documentation for each module

## Key Design Decisions

### Question 1: Scraping Strategy for Complex Boards
Some job boards (DevEx, ReliefWeb) may require browser automation (Selenium/Playwright) vs. simple HTTP requests. Start with static scraping and upgrade to browser automation only if needed.

**Recommended Approach:**
- Start with `requests` + `BeautifulSoup` for static HTML
- Fall back to Selenium for JavaScript-heavy sites if needed
- Use Playwright as premium option if Selenium proves unreliable
- Document scraper method in code comments

### Question 2: Gemini API Cost Management
Cover letter generation could be expensive at scale. Consider:
- Caching similar job responses (same job title, company, requirements)
- Implementing batch processing for efficiency
- Rate limiting API calls
- Storing generated content in database

**Recommended Approach:**
- Cache cover letters by hash of (job_id + user_profile_hash)
- Batch process 5-10 jobs per API call if possible
- Implement token-based rate limiting
- Log all API usage for cost tracking

### Question 3: Email Delivery Robustness
Consider:
- Failed email retry mechanism
- Email queue for manual review
- Support both individual emails and daily summaries
- Delivery confirmation and bounce handling

**Recommended Approach:**
- Individual emails per matched job (as specified in feature #6)
- Optional daily summary email toggle (config-based)
- Retry failed emails up to 3 times with exponential backoff
- Log all email delivery attempts
- Queue failed emails for manual intervention

### Question 4: Testing & Credentials
For development:
- Mock Gemini API calls with sample responses
- Mock Gmail API with file-based email capture
- Use environment-specific configuration (dev/prod)
- Provide fixture data for scrapers

**Recommended Approach:**
- Create tests/fixtures/ directory with sample job data
- Use `unittest.mock` for API mocking
- Separate dev/prod configs via environment variable
- Implement integration tests that can run against real APIs with limited scope

## Dependencies Summary

### Core Libraries
- `requests` - HTTP requests for scraping
- `beautifulsoup4` - HTML parsing
- `google-generativeai` - Gemini API
- `google-auth-oauthlib` - Gmail API authentication
- `pyyaml` - Configuration management
- `python-dotenv` - Environment variable management

### Optional (for enhanced scraping)
- `selenium` or `playwright` - Browser automation if needed
- `reportlab` - PDF generation for cover letters
- `jinja2` - Template rendering

### Development
- `pytest` - Testing framework
- `black` - Code formatting
- `pylint` - Linting
- `python-dotenv` - Development environment config

## Success Criteria

1. ✅ Profile parser successfully extracts and caches user data
2. ✅ All 8 job board scrapers retrieve jobs without rate limiting violations
3. ✅ Job matcher scores jobs with 70+ relevance threshold accuracy
4. ✅ Cover letter generator produces personalized, contextual content
5. ✅ Email system reliably delivers matched jobs with attachments
6. ✅ Database prevents duplicate processing of same jobs
7. ✅ GitHub Actions workflow runs daily without manual intervention
8. ✅ System handles errors gracefully with detailed logging
9. ✅ No sensitive credentials exposed in public repositories
10. ✅ Documentation enables easy reproduction and customization

## Timeline Estimate

- **Phase 1 (Setup & Config):** 30 min
- **Phase 2 (Profile Parser):** 45 min
- **Phase 3 (Base Scraper + 1 sample board):** 1.5 hours
- **Phase 4 (Remaining 7 scrapers):** 2 hours
- **Phase 5 (Matching Engine):** 1 hour
- **Phase 6 (Content Generators):** 1.5 hours
- **Phase 7 (Email System):** 1 hour
- **Phase 8 (Main Orchestrator):** 1 hour
- **Phase 9 (GitHub Actions):** 45 min
- **Phase 10 (Testing & Docs):** 1.5 hours

**Total Estimated Time:** ~12 hours for complete implementation

**Recommended Approach:** Build iteratively with GitHub commits after each major component, starting with core functionality and enhancing with optional features (browser automation, advanced caching, comprehensive testing) as time permits.
