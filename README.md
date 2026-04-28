# LinkedIn Learning Journey Post Automation

An intelligent content generation pipeline that transforms weekly learning reflections into 5 polished LinkedIn posts using Claude AI, with email-based approval workflow and Buffer integration for scheduling.

## 🎯 Overview

This system automates the LinkedIn content creation workflow for AI infrastructure engineers on a 90-day learning journey:

1. **Input**: Weekly learning notes via Flask web form
2. **Research**: Claude API researches trending AI/MLOps topics
3. **Generation**: Creates 5 diverse posts (news, bridge analogy, trend, learning, opinion)
4. **Approval**: Email-based review UI for editing and approving posts
5. **Scheduling**: Approved posts go to Buffer for automatic LinkedIn posting

## 🏗️ Project Structure

```
.
├── src/
│   ├── approval_server.py      # Flask web server (forms, review UI)
│   ├── research_agent.py       # Claude API topic research
│   ├── generate_posts.py       # Claude API post generation
│   ├── schedule_posts.py       # Buffer API scheduling
│   ├── auto_run.py             # GitHub Actions automation
│   ├── config.py               # Config & environment
│   └── __init__.py
├── .env                        # Environment variables (see .env.example)
├── requirements.txt            # Python dependencies
└── README.md                   # This file
```

## 📋 Requirements

- Python 3.9+
- Anthropic Claude API key (for research & generation)
- Buffer API access (for LinkedIn scheduling)
- Gmail SMTP credentials (for approval emails)
- Optional: GitHub Actions (for automation)

## 🚀 Quick Start

### 1. Setup

```bash
# Clone and navigate to project
cd linkedin_postautomation

# Install dependencies
pip install -r requirements.txt

# Copy and configure environment
cp .env.example .env
# Edit .env with your credentials
```

### 2. Configure `.env`

Required variables:
- `ANTHROPIC_API_KEY` — Claude API key from [console.anthropic.com](https://console.anthropic.com)
- `BUFFER_ACCESS_TOKEN` — Buffer API token from [buffer.com/developers](https://buffer.com/developers/apps)
- `BUFFER_PROFILE_ID` — Your LinkedIn profile ID (copy from Buffer URL)
- `APPROVAL_SECRET` — Random string for API security (e.g., `mahesh2025linkedin99`)
- `SMTP_EMAIL` — Gmail address for sending approval emails
- `SMTP_PASSWORD` — Gmail app-specific password (NOT Gmail password)
- `NOTIFY_EMAIL` — Email to receive approval links
- `JOURNEY_START_DATE` — First Monday of your learning journey (format: `YYYY-MM-DD`)
- `BASE_URL` — Your Flask server URL (local: `http://localhost:5000`, production: your Railway/Heroku URL)
- `FLASK_ENV` — `development` (local) or `production` (deploy)

**Example `.env`:**
```env
ANTHROPIC_API_KEY=sk-ant-...
BUFFER_ACCESS_TOKEN=spGuoe...
BUFFER_PROFILE_ID=69efe0...
APPROVAL_SECRET=mysecret123
SMTP_EMAIL=you@gmail.com
SMTP_PASSWORD=xxxx xxxx xxxx xxxx
NOTIFY_EMAIL=you@gmail.com
JOURNEY_START_DATE=2025-01-06
BASE_URL=http://localhost:5000
FLASK_ENV=development
TUESDAY_START_THIS_WEEK=false
```

### 3. Run Locally

```bash
# Start the Flask approval server
python src/approval_server.py
```

Open browser: `http://localhost:5000/input/2` (replace `2` with your week number)

## 📖 Workflows

### Manual Weekly Workflow

```bash
# 1. Open input form in browser
open http://localhost:5000/input/2

# 2. Fill in: "What did you learn this week?"
# → Flask triggers background post generation
# → Research agent runs, generates posts
# → Email arrives with approval link

# 3. Click email link to review posts
# → Edit content as needed
# → Approve 5 posts or select subset

# 4. Posts scheduled to Buffer
# → Check publish.buffer.com to confirm
```

### Command-Line Scheduling (if posts already generated)

```bash
# Generate posts directly
python -c "
from src.research_agent import research_weekly_topics
from src.generate_posts import generate_posts

week = 2
notes = 'Your learning notes here...'
research = research_weekly_topics(week, save=True)
posts = generate_posts(week, research, notes, save=True)
print('Posts saved to posts/week_' + str(week) + '.json')
"

# Schedule to Buffer
python src/schedule_posts.py --file posts/week_2.json

# Or dry-run first
python src/schedule_posts.py --file posts/week_2.json --dry-run

# Check Buffer queue
python src/schedule_posts.py --queue

# Test Buffer connection
python src/schedule_posts.py --test
```

### GitHub Actions (Sunday Automation)

The `.github/workflows/sunday-automation.yml` runs every Sunday:

```yaml
# Automatically:
# 1. Calculates current week from JOURNEY_START_DATE
# 2. Pulls last week's learning notes from tracked file
# 3. Generates posts
# 4. Sends approval email
```

Configure in `.env`:
```env
TUESDAY_START_THIS_WEEK=true   # If this week starts Tuesday instead of Monday
```

## 🔧 API Endpoints

### Input Form
```
GET /input/<week>
  → Renders input form for week

POST /input/<week>
  Body: {"notes": "...", "tuesday_start": true/false}
  → Triggers background generation, sends email
```

### Review & Approval
```
GET /review/<token>
  → Renders review UI (48-hour token expiry)

POST /approve/<token>
  Body: {"approved_posts": [{"index": 0, "content": "..."}]}
  → Schedules to Buffer, deletes token
```

### Health Check
```
GET /health
  → Returns {"status": "ok", "time": "..."}
```

### External Submission (for pipelines)
```
POST /submit-posts
  Header: X-Secret: <APPROVAL_SECRET>
  Body: {"week": 2, "posts": [...]}
  → Creates review token, sends email
```

## 🧪 Testing

### Check All Imports
```bash
python -c "
from src.config import WEEK_THEMES, LEARNING_QUESTIONS
from src.approval_server import app
from src.research_agent import research_weekly_topics
from src.generate_posts import generate_posts
from src.schedule_posts import schedule_all_posts, test_connection
print('OK: All modules import successfully')
"
```

### Test Buffer Connection
```bash
python src/schedule_posts.py --test
```

### Test Flask Startup
```bash
timeout 5 python src/approval_server.py || true
```

## 📊 Configuration Reference

### Week Themes & Questions

Edit `src/config.py` to customize:

```python
WEEK_THEMES = {
    2: "Python Foundations",
    3: "Embeddings and Vectors",
    4: "Vector DBs and RAG",
    # ... customize for your journey
}

LEARNING_QUESTIONS = {
    2: [
        "What Python concept surprised you most?",
        "What did NumPy teach you?",
        # ... customize per week
    ]
}
```

### Post Schedule

Default schedule (Mon-Fri):
```
Monday 10:00     → Industry News
Tuesday 17:00    → Bridge (backend → AI analogy)
Wednesday 10:00  → Industry Trend
Thursday 17:00   → Learning (what you built)
Friday 10:00     → Opinion (hot take)
```

For Tuesday start weeks:
```
Tuesday 17:00    → Bridge
Wednesday 10:00  → Industry Trend
Thursday 17:00   → Learning
Friday 10:00     → Opinion
```

## 🛠️ Deployment

### Railway (Recommended)

```bash
# 1. Push to GitHub
git push origin main

# 2. Connect repo at railway.app
# 3. Set environment variables in Railway dashboard
# 4. Deploy (auto-builds from main branch)
```

### Heroku

```bash
# 1. Create Heroku app
heroku create linkedin-automation

# 2. Set environment variables
heroku config:set ANTHROPIC_API_KEY=sk-ant-...

# 3. Deploy
git push heroku main
```

### Docker

```bash
docker build -t linkedin-automation .
docker run -p 5000:5000 --env-file .env linkedin-automation
```

## 📧 Email Integration

### Gmail Setup

1. Enable 2-factor authentication
2. Go to [Google Account → Security → App passwords](https://myaccount.google.com/apppasswords)
3. Select "Mail" and "Windows Computer"
4. Copy the 16-character password
5. Add to `.env`:
   ```env
   SMTP_PASSWORD=xxxx xxxx xxxx xxxx
   ```

**Note:** The password has spaces — that's correct.

## 🔒 Security

- `APPROVAL_SECRET`: Protects `/submit-posts` endpoint
- Review tokens: 48-hour expiry, random 24-char strings
- In-memory token storage (production: use Redis)
- Environment variables: Never commit `.env`

## 📝 Common Commands

```bash
# Start Flask server
python src/approval_server.py

# Research topics for week 2
python -c "from src.research_agent import research_weekly_topics; import json; r = research_weekly_topics(2); print(json.dumps(r, indent=2))"

# Generate posts
python -c "from src.generate_posts import generate_posts; from src.research_agent import research_weekly_topics; posts = generate_posts(2, research_weekly_topics(2), 'My notes', save=True); print(f'Generated {len(posts[\"posts\"])} posts')"

# Check current week from journey start date
python -c "from src.auto_run import get_current_week; print(f'Current week: {get_current_week()}')"
```

## 🐛 Troubleshooting

### Flask won't start
```bash
# Check port isn't in use
netstat -tlnp | grep 5000

# Try different port
PORT=8000 python src/approval_server.py
```

### Email not sending
- Gmail app password (not account password)
- Check SMTP credentials in `.env`
- Try: `python src/schedule_posts.py --test` (tests email config)

### Buffer posting fails
- Verify `BUFFER_ACCESS_TOKEN` and `BUFFER_PROFILE_ID` in `.env`
- Run: `python src/schedule_posts.py --test`
- Check [Buffer API status](https://status.buffer.com)

### Claude API errors
- Check `ANTHROPIC_API_KEY` is valid
- Ensure you have Claude API credits
- Verify internet connection

### Review link expired
- Tokens expire in 48 hours
- Re-run week generation to get new token
- Check `/health` endpoint that server is running

## 📚 Learning Journey Dates

Your journey: Week 1 starts on `JOURNEY_START_DATE` (Monday)
- Week 1: Jan 6-12
- Week 2: Jan 13-19
- Week 3: Jan 20-26
- ... continues for 9 weeks

Current week calculated as: `(today - journey_start) // 7 + 1`

## 🤝 Contributing

To customize for your own journey:

1. Fork/clone this repo
2. Edit `src/config.py`:
   - `ENGINEER_CONTEXT`: Your background
   - `WEEK_THEMES`: Your weekly topics
   - `LEARNING_QUESTIONS`: Questions for each week
3. Update `.env` with your credentials
4. Run and test locally
5. Deploy to your server

## 📄 License

Built for AI infrastructure learning journeys. Customize freely.

## 🚦 Next Steps

1. **Today**: Complete `.env` setup and test Flask startup
2. **This week**: Run `/input/2` form, generate first posts, test approval flow
3. **Next week**: Automate with GitHub Actions
4. **Production**: Deploy to Railway/Heroku, monitor approval workflow

---

**Questions?** Check `/health` endpoint or review `.env` setup. Email approval links are sent to `NOTIFY_EMAIL`.
