# LinkedIn Post Automation — AI Infrastructure Learning Journey

Automated LinkedIn content pipeline for Mahesh Annapureddy's 90-day AI Infrastructure Engineer transition. Converts weekly learning notes into 5 polished posts using a multi-model AI pipeline, with email-based approval and Buffer scheduling.

---

## How It Works

```
Sunday 9 AM (GitHub Actions)
        ↓
Email 1: "What did you learn this week?" → form link
        ↓
You fill form (3-5 min)
        ↓
Railway server (background):
  1. Fetch trends  — HN Algolia (free) + optional SerpAPI
  2. Rank topics   — DeepSeek via OpenRouter  (~$0.003)
  3. Generate posts — Kimi via OpenRouter      (~$0.011)
  4. Refine         — Claude Haiku             (~$0.010)
        ↓
Email 2: approval link with review UI
        ↓
You read, edit, approve (10-15 min)
        ↓
Buffer schedules 5 posts: Mon–Fri to LinkedIn
```

**Cost per weekly run: ~$0.024** (vs ~$0.47+ with Claude-only)

---

## Project Structure

```
linkedin_postautomation/
├── src/
│   ├── config.py               # All env vars and constants
│   ├── llm_client.py           # OpenRouter gateway (DeepSeek / Kimi / MiniMax)
│   ├── trend_fetcher.py        # HN Algolia + optional SerpAPI (3-hr cache)
│   ├── research_agent.py       # Topic ranking via DeepSeek
│   ├── generate_posts.py       # Post generation via Kimi
│   ├── refinement.py           # Final polish via Claude Haiku
│   ├── approval_server.py      # Flask server (input form + review UI)
│   ├── schedule_posts.py       # Buffer API scheduling
│   ├── auto_run.py             # GitHub Actions entry point
│   └── __init__.py
├── posts/                      # Generated post JSON (gitignored)
├── research/                   # Research topic JSON (gitignored)
├── .github/workflows/
│   └── linkedin_sunday.yml     # Sunday 9 AM Toronto cron
├── .env.template               # Copy to .env and fill in keys
├── requirements.txt
├── Procfile                    # Railway/Heroku startup
└── railway.toml                # Railway config
```

---

## API Keys You Need

| Key | Where to get | Used for |
|---|---|---|
| `ANTHROPIC_API_KEY` | console.anthropic.com → API Keys | Claude Haiku refinement |
| `OPENROUTER_API_KEY` | openrouter.ai/keys → Create Key | DeepSeek ranking + Kimi generation |
| `BUFFER_ACCESS_TOKEN` | buffer.com/developers/apps → Create App | Schedule posts to LinkedIn |
| `BUFFER_PROFILE_ID` | buffer.com/manage → LinkedIn channel → copy ID from URL | Target LinkedIn profile |
| `SMTP_PASSWORD` | myaccount.google.com → Security → App passwords (16 chars) | Send approval emails |
| `SERPAPI_KEY` | serpapi.com (optional, free tier 100/mo) | Enhanced Google News trends |

---

## Setup

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.template .env
# Edit .env with your keys
```

Required `.env` values:

```env
ANTHROPIC_API_KEY=sk-ant-...
OPENROUTER_API_KEY=sk-or-...
BUFFER_ACCESS_TOKEN=...
BUFFER_PROFILE_ID=...
APPROVAL_SECRET=mahesh2025linkedin99
SMTP_EMAIL=mahesh.annapureddy5@gmail.com
SMTP_PASSWORD=xxxx xxxx xxxx xxxx
NOTIFY_EMAIL=mahesh.annapureddy5@gmail.com
BASE_URL=https://your-app.up.railway.app
FLASK_ENV=production
JOURNEY_START_DATE=2025-01-06
TUESDAY_START_THIS_WEEK=false
USE_WEB_RESEARCH=true
SERPAPI_KEY=                          # leave blank to use HN API only
```

### 3. Test locally

```bash
# Start server
python -m src.approval_server

# Open form in browser
open http://localhost:5000/input/2

# Health check
curl http://localhost:5000/health
```

---

## Deploy to Railway

```bash
# Install Railway CLI
npm install -g @railway/cli
railway login
railway init      # name it: linkedin-automation
railway up

# Copy the URL from:
railway domain

# Set all variables
railway variables set ANTHROPIC_API_KEY="sk-ant-..."
railway variables set OPENROUTER_API_KEY="sk-or-..."
railway variables set BUFFER_ACCESS_TOKEN="..."
railway variables set BUFFER_PROFILE_ID="..."
railway variables set APPROVAL_SECRET="mahesh2025linkedin99"
railway variables set SMTP_EMAIL="mahesh.annapureddy5@gmail.com"
railway variables set SMTP_PASSWORD="your-16-char-app-password"
railway variables set NOTIFY_EMAIL="mahesh.annapureddy5@gmail.com"
railway variables set BASE_URL="https://your-actual-url.up.railway.app"
railway variables set FLASK_ENV="production"
railway variables set JOURNEY_START_DATE="2025-01-06"
railway variables set TUESDAY_START_THIS_WEEK="false"
railway variables set USE_WEB_RESEARCH="true"
railway up

# Verify
curl https://your-app.up.railway.app/health
```

---

## GitHub Actions (Sunday Automation)

Workflow: `.github/workflows/linkedin_sunday.yml`
Schedule: Every Sunday 9 AM Toronto time (2 PM UTC)

### GitHub Secrets to add

Go to: GitHub repo → Settings → Secrets → Actions → New repository secret

| Secret | Value |
|---|---|
| `ANTHROPIC_API_KEY` | Your Claude key |
| `BUFFER_ACCESS_TOKEN` | Your Buffer token |
| `BUFFER_PROFILE_ID` | Your LinkedIn channel ID |
| `APPROVAL_SECRET` | `mahesh2025linkedin99` |
| `APPROVAL_SERVER_URL` | Your Railway URL |
| `SMTP_EMAIL` | `mahesh.annapureddy5@gmail.com` |
| `SMTP_PASSWORD` | Your 16-char app password |
| `NOTIFY_EMAIL` | `mahesh.annapureddy5@gmail.com` |
| `JOURNEY_START_DATE` | `2025-01-06` |

> **Note:** `OPENROUTER_API_KEY` is NOT needed as a GitHub Secret — the Sunday cron only sends an email. All LLM calls happen on Railway when you submit the form.

### Trigger manually

```bash
# From GitHub Actions tab: LinkedIn Sunday Automation → Run workflow
# Or with gh CLI:
gh workflow run linkedin_sunday.yml --field week_override=2 --field tuesday_start=true
```

---

## Weekly Workflow

### Automated (after full setup)

1. **Sunday 9 AM** — Email 1 arrives with "What did you learn?" form link
2. **You** — Click link, fill form (3-5 min), submit
3. **~3 min later** — Email 2 arrives with approval link
4. **You** — Review/edit posts, click "Approve All & Schedule"
5. **Mon–Fri** — Buffer posts to LinkedIn automatically

### Manual run (any time)

```bash
# Option A: Open form in browser directly
open https://your-app.up.railway.app/input/2

# Option B: Trigger GitHub Action manually
gh workflow run linkedin_sunday.yml --field week_override=2

# Option C: Test Buffer connection
python -m src.schedule_posts --test

# Option D: Dry-run scheduling (no actual Buffer posts)
python -m src.schedule_posts --file posts/week_2.json --dry-run
```

---

## Post Schedule

| Day | Time | Type | Content |
|---|---|---|---|
| Monday | 10:00 | Industry News | Biggest AI/infra news — sharp backend take |
| Tuesday | 17:00 | Bridge | Backend → AI concept analogy from your expertise |
| Wednesday | 10:00 | Industry Trend | Broader AI infrastructure trend or tool update |
| Thursday | 17:00 | Learning | What YOU learned or built this week |
| Friday | 10:00 | Opinion | Bold hot take — polarising and memorable |

Tuesday-start weeks (first week only): Tue–Fri, 4 posts.

---

## API Endpoints

```
GET  /health              → {"status": "ok", "time": "..."}
GET  /input/<week>        → Learning notes form
POST /input/<week>        → Submit notes, triggers background generation
GET  /review/<token>      → Post review and approval UI (48hr expiry)
POST /approve/<token>     → Schedule approved posts to Buffer
POST /submit-posts        → Direct post submission (X-Secret header required)
```

---

## Cost Reference

| Model | Used for | Rate | Cost/run |
|---|---|---|---|
| HN Algolia API | Trend fetching | Free | $0.000 |
| SerpAPI | Google News (optional) | Free ≤100/mo | $0.000 |
| DeepSeek V3 via OpenRouter | Topic ranking | $0.27/$1.10 per MTok | ~$0.003 |
| Kimi moonshot-v1-8k via OpenRouter | Post generation | ~$0.33/$3.30 per MTok | ~$0.011 |
| Claude Haiku 4.5 | Refinement polish | $0.80/$4.00 per MTok | ~$0.010 |
| **Total** | | | **~$0.024/week** |

Load ~$5 on OpenRouter → covers ~200 weekly runs.

To disable live research (use curated fallback topics, $0 cost):
```env
USE_WEB_RESEARCH=false
```

---

## Troubleshooting

**Background generation failed: 429**
- Old issue (Claude rate limits). Fixed — now uses OpenRouter models with no rate limit problem.

**Buffer posting fails**
- Run: `python -m src.schedule_posts --test`
- Verify `BUFFER_ACCESS_TOKEN` and `BUFFER_PROFILE_ID` in Railway env vars

**Email not sending**
- Use Gmail App Password (16 chars), NOT your Gmail password
- Enable 2FA first at myaccount.google.com → Security → App passwords

**Review link expired**
- Tokens expire in 48 hours
- Open the form again at `https://your-app.up.railway.app/input/<week>` and resubmit

**Server not responding**
- Check Railway deployment: `railway logs`
- Verify `BASE_URL` is set to your actual Railway URL (no trailing slash)

**OpenRouter errors**
- Verify `OPENROUTER_API_KEY` is set on Railway
- Add credit at openrouter.ai (minimum ~$5)
- Model fallback chain: Kimi → MiniMax → DeepSeek auto-activates on failure

---

## Customize for Your Journey

Edit `src/config.py`:

```python
ENGINEER_CONTEXT = """
Name: Your Name
Role: Your current role → target role
Background: Your experience
...
"""

WEEK_THEMES = {
    2: "Your Week 2 Theme",
    ...
}

LEARNING_QUESTIONS = {
    2: ["Question 1?", "Question 2?", ...],
    ...
}
```

---

Built for Mahesh Annapureddy's AI Infrastructure Engineer transition journey.
Customize freely for your own 90-day learning sprint.
