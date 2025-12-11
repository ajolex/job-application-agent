# Job Application Agent

**Your personal assistant for finding Development Economics and Research jobs.**

This tool automatically searches multiple job websites every day, finds positions that match your background, writes personalized cover letters, and emails you a summary of the best opportunities.

---

## What Does This Do?

1. **Reads your CV/resume** to understand your skills, experience, and qualifications
2. **Searches Google Jobs, LinkedIn, Indeed, Glassdoor** and many more via smart job APIs
3. **Uses AI to match jobs to your profile** and scores how well each job fits you (0-100)
4. **Writes draft cover letters** tailored to each matched position
5. **Sends you a daily email** with your top job matches and ready-to-use cover letters
6. **Remembers which jobs you've seen** so you never get duplicates

---

## How Job Search Works

Unlike simple web scrapers that often break, this agent uses **professional job aggregator APIs**:

| Service | What It Does | Cost |
|---------|--------------|------|
| **SerpApi** (recommended) | Searches Google Jobs - aggregates LinkedIn, Indeed, Glassdoor, ZipRecruiter, and 50+ job boards | Free tier: 100 searches/month |
| **JSearch** | RapidAPI aggregator - great for indie projects | Free tier: 500 searches/month |

These APIs are the same tools used by professional job search AI agents because:
- ✅ Google already aggregates jobs from everywhere
- ✅ No website blocking or CAPTCHA issues
- ✅ Clean, structured data (not broken HTML)
- ✅ Much more reliable than direct scraping

---

## Getting Started

### Prerequisites

- **Python 3.11 or higher** installed on your computer
  - [Download Python](https://www.python.org/downloads/)
  - During installation, check "Add Python to PATH"

### Installation

1. **Download this project** (or clone with Git)

2. **Open a terminal/command prompt** in the project folder

3. **Create a virtual environment** (recommended):
   ```
   python -m venv venv
   ```

4. **Activate the virtual environment**:
   - Windows: `venv\Scripts\activate`
   - Mac/Linux: `source venv/bin/activate`

5. **Install required packages**:
   ```
   pip install -r requirements.txt
   ```

---

### Step 1: Get the Required API Keys

You'll need these API keys:

1. **Google Gemini API Key** (free tier - for AI matching)
   - Go to [Google AI Studio](https://makersuite.google.com/app/apikey)
   - Sign in with your Google account
   - Click "Create API Key"
   - Copy the key somewhere safe

2. **SerpApi Key** (free tier: 100 searches/month - for job search)
   - Go to [SerpApi](https://serpapi.com/)
   - Create a free account
   - Copy your API key from the dashboard

   **OR** use JSearch instead (free tier: 500 searches/month):
   - Go to [JSearch on RapidAPI](https://rapidapi.com/letscrape-6bRBa3QguO5/api/jsearch)
   - Subscribe to the free plan
   - Copy your RapidAPI key

3. **Gmail Account** (for receiving job notifications)
   - Use your existing Gmail or create a new one
   - You'll set up permissions later to let the tool send you emails

### Step 2: Download and Set Up

1. Download this project to your computer
2. Find the file called `.env.example` and rename it to `.env`
3. Open `.env` in any text editor and fill in:
   - `GEMINI_API_KEY` - Your Gemini API key
   - `SERPAPI_API_KEY` - Your SerpApi key (or `RAPIDAPI_KEY` for JSearch)
   - `EMAIL_ADDRESS` - Your email address

### Step 3: Add Your Resume

Save your CV/resume as an HTML file named `index.html` in the project folder. The tool will read this to understand your background.

### Step 4: Set Up Gmail Permissions

This allows the tool to send you email notifications:

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project (call it anything you like)
3. Enable the "Gmail API"
4. Create credentials (choose "Desktop application")
5. Download the credentials file and save it as `credentials.json` in the project folder
6. Run the tool once – it will open a browser window asking you to grant permission

### Step 5: Run It!

Open a terminal in the project folder and run:

```
# Make sure virtual environment is activated first!
venv\Scripts\activate  # Windows
# or: source venv/bin/activate  # Mac/Linux

# Run the agent
python -m src.main
```

**Other useful commands:**

```
# Test run (won't send emails)
python -m src.main --dry-run

# See detailed output
python -m src.main --dry-run -v

# Check database statistics
python -m src.main --stats

# Skip scraping (use existing data)
python -m src.main --skip-scraping
```

The tool will:

- Search all job boards via APIs
- Match jobs to your profile (filtering out visa-restricted positions)
- Generate cover letters saved as `.md` files in `output/cover_letters/`
- Email you a compact summary with job links

---

## How It Works (Non-Technical)

**Daily Process:**
1. ☀️ Every morning, the tool wakes up automatically
2. 🔍 It visits each job website and searches for relevant positions
3. 🤖 AI reads each job description and compares it to your resume
4. 📊 Jobs are scored from 0-100 based on how well they match
5. ✉️ Anything scoring 70+ gets a cover letter draft saved locally
6. 📧 You receive a summary email with job links

**What You Get:**
- A daily email summary with job opportunities and links
- Ready-to-customize cover letters saved as `.md` files (editable Markdown)
- Direct links to apply
- No duplicate listings – it remembers what you've seen

---

## Customization

### Change What Jobs to Search For

Open `config/config.yaml` and modify the keywords list to match your interests:

```
keywords:
  - "development economics"
  - "impact evaluation"
  - "research associate"
  - "policy analyst"
```

### Change the Match Threshold

By default, you only get notified about jobs that score 70 or higher. Change this in the same file:

```
match_threshold: 70  # Lower = more jobs, Higher = stricter matching
```

---

## Automatic Daily Runs (Optional)

If you host this on GitHub, it can run automatically every day at 8 AM without you doing anything. See the technical documentation for setup instructions.

---

## Questions?

**Q: Is this free to use?**
A: Yes! Google Gemini has a free tier that's more than enough for daily job searching.

**Q: Will this apply to jobs for me?**
A: No – it finds and prepares applications, but you review and submit them yourself.

**Q: How accurate is the matching?**
A: The AI does a good job, but always review matches yourself. Think of it as a smart filter, not a replacement for your judgment.

**Q: Can I add more job boards?**
A: Yes, the system is designed to be extended. See the technical documentation.

---

## Privacy & Data

- Your resume stays on your computer (or your private GitHub repository)
- Job data is stored locally in a small database file
- The AI processes your data through Google's Gemini API (subject to their privacy policy)
- No data is shared with third parties

---

*Built to help Development Economics researchers find their next opportunity.*
