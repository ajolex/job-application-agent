# Job Application Agent

Automated job searching, matching, and application preparation for Development Economics Research positions.

## Features

- **Profile Parsing**: Extracts skills, experience, and qualifications from your HTML CV/profile
- **Multi-source Job Scraping**: Searches 8+ job boards automatically
- **AI-Powered Matching**: Uses Google Gemini to score job relevance (0-100)
- **Cover Letter Generation**: Creates personalized cover letters for matched positions
- **Email Notifications**: Sends daily summaries with matched jobs and attachments
- **Duplicate Prevention**: SQLite database tracks processed jobs
- **GitHub Actions**: Runs automatically on schedule

## Supported Job Boards

1. **ReliefWeb** - API-based scraping
2. **DevEx** - International development jobs
3. **ImpactPool** - Impact sector positions
4. **UNJobs** - United Nations opportunities
5. **World Bank** - World Bank Group careers
6. **80,000 Hours** - High-impact career opportunities
7. **EconJobMarket** - Academic economics positions
8. More can be added by extending the scraper framework

## Quick Start

### 1. Clone and Install

```bash
git clone <your-repo-url>
cd job-application-agent
pip install -r requirements.txt
```

### 2. Configure

Copy the example environment file and add your credentials:

```bash
cp .env.example .env
```

Edit `.env`:
```
GEMINI_API_KEY=your_gemini_api_key_here
EMAIL_ADDRESS=your_email@gmail.com
```

### 3. Add Your Profile

Place your HTML CV/profile at `index.html` in the project root, or update `config/config.yaml`:

```yaml
profile:
  local_path: "path/to/your/profile.html"
```

### 4. Set Up Gmail API (for email notifications)

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing
3. Enable Gmail API
4. Create OAuth 2.0 credentials (Desktop application)
5. Download `credentials.json` to project root
6. Run the agent once locally to authenticate and generate `token.json`

### 5. Run Locally

```bash
# Full run
python -m src.main

# Dry run (no emails sent)
python -m src.main --dry-run

# Skip scraping (use existing database)
python -m src.main --skip-scraping

# Show statistics
python -m src.main --stats

# Verbose output
python -m src.main -v
```

## Configuration

Edit `config/config.yaml` to customize:

```yaml
job_search:
  keywords:
    - "development economics"
    - "research associate"
    - "impact evaluation"
  match_threshold: 70  # Minimum match score (0-100)
  max_jobs_per_run: 50

scrapers:
  enabled:
    - reliefweb
    - devex
    - impactpool
  rate_limit_seconds: 2

email:
  send_summary: true
  attach_cover_letter: true
  attach_cv: true
```

## GitHub Actions Setup

### Required Secrets

Add these secrets to your repository (Settings → Secrets and variables → Actions):

| Secret | Description |
|--------|-------------|
| `GEMINI_API_KEY` | Google Gemini API key |
| `EMAIL_ADDRESS` | Your email address for notifications |
| `GMAIL_CREDENTIALS` | Contents of `credentials.json` |
| `GMAIL_TOKEN` | Contents of `token.json` (after initial auth) |

### Schedule

The workflow runs daily at 8:00 AM UTC. Modify `.github/workflows/job_search.yml` to change:

```yaml
on:
  schedule:
    - cron: '0 8 * * *'  # Change time here
```

### Manual Trigger

Go to Actions → Daily Job Search → Run workflow to trigger manually.

## Project Structure

```
job-application-agent/
├── .github/workflows/     # GitHub Actions
├── config/
│   └── config.yaml        # Main configuration
├── src/
│   ├── main.py            # Main orchestrator
│   ├── config.py          # Configuration loader
│   ├── profile/           # Profile parsing
│   ├── scrapers/          # Job board scrapers
│   ├── matching/          # AI job matching
│   ├── generator/         # Content generation
│   ├── notifications/     # Email sending
│   └── database/          # SQLite management
├── templates/             # Email/cover letter templates
├── data/                  # Database and cache files
├── output/                # Generated cover letters
└── logs/                  # Application logs
```

## Adding New Job Boards

1. Create a new scraper in `src/scrapers/`:

```python
from src.scrapers.base_scraper import BaseScraper
from src.database.db_manager import Job

class NewBoardScraper(BaseScraper):
    def scrape(self, keywords, max_pages=5):
        jobs = []
        # Your scraping logic here
        return jobs
    
    def parse_job_listing(self, element):
        # Parse individual job listing
        return self.create_job(
            url="...",
            title="...",
            organization="...",
            # ...
        )
```

2. Register in `src/scrapers/scraper_factory.py`:

```python
from src.scrapers.newboard import NewBoardScraper

SCRAPER_CLASSES = {
    # ...
    "newboard": NewBoardScraper,
}
```

3. Add configuration in `config/config.yaml`:

```yaml
scrapers:
  enabled:
    - newboard
    
scraper_configs:
  newboard:
    base_url: "https://newboard.com"
```

## CLI Options

```
usage: python -m src.main [-h] [--config CONFIG] [--dry-run]
                          [--skip-scraping] [--skip-matching]
                          [--skip-cover-letters] [--skip-email]
                          [--stats] [--verbose]

Options:
  --config, -c       Path to configuration file
  --dry-run          Run without sending emails
  --skip-scraping    Skip job scraping step
  --skip-matching    Skip job matching step
  --skip-cover-letters  Skip cover letter generation
  --skip-email       Skip sending email
  --stats            Show database statistics and exit
  --verbose, -v      Enable verbose logging
```

## Troubleshooting

### "GEMINI_API_KEY not configured"
- Ensure `.env` file exists with valid API key
- Or set environment variable: `export GEMINI_API_KEY=your_key`

### "Gmail credentials not found"
- Download OAuth credentials from Google Cloud Console
- Save as `credentials.json` in project root

### "No jobs found"
- Check if scrapers are enabled in config
- Some boards may have changed their structure
- Try running with `--verbose` for detailed logs

### Rate limiting
- Increase `rate_limit_seconds` in config
- Some boards may block automated access

## License

MIT License - See LICENSE file for details.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Submit a pull request

## Disclaimer

This tool is for personal use. Please respect each job board's terms of service and robots.txt. Use responsibly and avoid excessive scraping.
