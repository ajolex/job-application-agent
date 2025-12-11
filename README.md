# Job Application Agent

**Your personal assistant for finding Development Economics and Research jobs.**

This tool automatically searches multiple job websites every day, finds positions that match your background, writes personalized cover letters, and emails you a summary of the best opportunities.

---

## What Does This Do?

1. **Reads your CV/resume** to understand your skills, experience, and qualifications
2. **Searches 8+ job websites** including World Bank, UN Jobs, DevEx, ReliefWeb, and academic job boards
3. **Uses AI to match jobs to your profile** and scores how well each job fits you (0-100)
4. **Writes draft cover letters** tailored to each matched position
5. **Sends you a daily email** with your top job matches and ready-to-use cover letters
6. **Remembers which jobs you've seen** so you never get duplicates

---

## Job Boards Searched

- **ReliefWeb** – Humanitarian and development jobs worldwide
- **DevEx** – International development careers
- **ImpactPool** – Social impact and sustainability roles
- **UN Jobs** – United Nations positions
- **World Bank** – World Bank Group opportunities
- **80,000 Hours** – High-impact career opportunities
- **EconJobMarket** – Academic economics positions

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

### Step 1: Get the Required Accounts (Free)

You'll need two things:

1. **Google Gemini API Key** (free tier available)
   - Go to [Google AI Studio](https://makersuite.google.com/app/apikey)
   - Sign in with your Google account
   - Click "Create API Key"
   - Copy the key somewhere safe

2. **Gmail Account** (for receiving job notifications)
   - Use your existing Gmail or create a new one
   - You'll set up permissions later to let the tool send you emails

### Step 2: Download and Set Up

1. Download this project to your computer
2. Find the file called `.env.example` and rename it to `.env`
3. Open `.env` in any text editor and fill in:
   - Your Gemini API key
   - Your email address

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

- Search all job boards
- Match jobs to your profile
- Generate cover letters for good matches
- Email you the results

---

## How It Works (Non-Technical)

**Daily Process:**
1. ☀️ Every morning, the tool wakes up automatically
2. 🔍 It visits each job website and searches for relevant positions
3. 🤖 AI reads each job description and compares it to your resume
4. 📊 Jobs are scored from 0-100 based on how well they match
5. ✉️ Anything scoring 70+ gets a cover letter draft
6. 📧 You receive an email with all matched jobs and cover letters

**What You Get:**
- A daily email with job opportunities ranked by fit
- Ready-to-customize cover letters for each position
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
