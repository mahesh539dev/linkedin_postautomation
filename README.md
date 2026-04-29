# LinkedIn Post Automation 

Automated LinkedIn content pipeline for Mahesh Annapureddy's AI Infrastructure Engineer transition. Every week it turns raw learning notes into 5 scored, reviewed, and scheduled LinkedIn posts — with a full multi-model AI pipeline and zero manual scheduling.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        WEEKLY TRIGGER                               │
│                                                                     │
│   GitHub Actions cron                                               │
│   Every Sunday 9 AM Toronto (2 PM UTC)                             │
│          │                                                          │
│          ▼                                                          │
│   auto_run.py  ──►  Email 1: "What did you learn?"                 │
│                      (Resend API / SMTP fallback)                   │
└─────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    RAILWAY FLASK SERVER                             │
│                                                                     │
│   GET  /input/<week>   ──►  Learning notes form (dark UI)          │
│   POST /input/<week>   ──►  Submit notes → background thread       │
│                                    │                               │
│                    ┌───────────────▼───────────────┐               │
│                    │    GENERATION PIPELINE        │               │
│                    │                               │               │
│                    │  trend_fetcher.py             │               │
│                    │  HN Algolia + SerpAPI (opt.)  │               │
│                    │          │                    │               │
│                    │          ▼                    │               │
│                    │  research_agent.py            │               │
│                    │  DeepSeek (OpenRouter)        │               │
│                    │  Ranks 21 topics → top 5      │               │
│                    │          │                    │               │
│                    │          ▼                    │               │
│                    │  generate_posts.py            │               │
│                    │  Kimi (OpenRouter)            │               │
│                    │  5 posts from notes + topics  │               │
│                    │          │                    │               │
│                    │          ▼                    │               │
│                    │  refinement.py                │               │
│                    │  Claude Haiku                 │               │
│                    │  Polish + brand voice         │               │
│                    │          │                    │               │
│                    │          ▼                    │               │
│                    │  post_variants.py             │               │
│                    │  Claude Sonnet → V2 rewrite   │               │
│                    │  GPT-4o        → V3 rewrite   │               │
│                    │  GPT-4o scores all 3 versions │               │
│                    └───────────────────────────────┘               │
│                                    │                               │
│                                    ▼                               │
│   Token stored in memory (48hr expiry)                             │
│          │                                                          │
│          ▼                                                          │
│   Email 2: "Posts ready for review"                                │
│   (Resend API / SMTP fallback)                                     │
│                                                                     │
│   GET  /review/<token>  ──►  Review UI: 3 tabs per post            │
│                              V1·Kimi / V2·Claude / V3·OpenAI       │
│                              Score badges + breakdown              │
│                              Best version auto-selected            │
│                                                                     │
│   POST /approve/<token> ──►  Buffer GraphQL API                    │
│                              createPost mutation                   │
│                              EST→UTC conversion                    │
│                              Scheduled Mon–Fri                     │
└─────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         LINKEDIN                                    │
│                                                                     │
│   Monday    10:00 EST  — Industry News                             │
│   Tuesday   17:00 EST  — Bridge (Backend→AI analogy)              │
│   Wednesday 10:00 EST  — Industry Trend                            │
│   Thursday  17:00 EST  — Learning (personal)                       │
│   Friday    10:00 EST  — Opinion / Hot take                        │
└─────────────────────────────────────────────────────────────────────┘
```

**Cost per weekly run: ~$0.024**

| Step | Model | Cost |
|---|---|---|
| Trend fetching | HN Algolia (free) | $0.000 |
| Topic ranking | DeepSeek V3 via OpenRouter | ~$0.003 |
| Post generation (V1) | Kimi via OpenRouter | ~$0.011 |
| Refinement | Claude Haiku | ~$0.010 |
| V2 rewrite + scoring | Claude Sonnet | ~$0.020 |
| V3 rewrite | GPT-4o | ~$0.015 |

---

## Project Structure

```
linkedin_postautomation/
├── src/
│   ├── config.py               # Env vars, week themes, learning questions
│   ├── llm_client.py           # OpenRouter gateway (DeepSeek / Kimi / fallback)
│   ├── trend_fetcher.py        # HN Algolia + optional SerpAPI (3hr cache)
│   ├── research_agent.py       # Topic ranking via DeepSeek
│   ├── generate_posts.py       # Post generation + dynamic scheduling
│   ├── linkedin_guidelines.py  # Scoring rubric + personalised system prompt
│   ├── post_variants.py        # Claude Sonnet V2 + GPT-4o V3 + scoring
│   ├── refinement.py           # Claude Haiku polish pass
│   ├── email_utils.py          # Resend API (Railway) / SMTP fallback (GH Actions)
│   ├── approval_server.py      # Flask: input form + review UI + Buffer scheduling
│   ├── schedule_posts.py       # CLI: Buffer GraphQL API
│   ├── auto_run.py             # GitHub Actions entry point (sends Email 1)
│   └── __init__.py
├── posts/                      # Generated post JSON (gitignored)
├── research/                   # Research topic JSON (gitignored)
├── .github/workflows/
│   └── linkedin_sunday.yml     # Sunday 9 AM Toronto cron
├── .env.template               # Copy to .env and fill in keys
├── requirements.txt
├── Procfile                    # gunicorn startup for Railway
└── railway.toml                # Railway config
```

---

## Environment Variables

### Railway (server + generation)

| Variable | Where to get | Required |
|---|---|---|
| `ANTHROPIC_API_KEY` | console.anthropic.com → API Keys | Yes |
| `OPENROUTER_API_KEY` | openrouter.ai/keys | Yes |
| `OPENAI_API_KEY` | platform.openai.com/api-keys | Yes |
| `BUFFER_ACCESS_TOKEN` | publish.buffer.com/settings/api → Generate API Key | Yes |
| `BUFFER_PROFILE_ID` | LinkedIn channel ID from Buffer channels query | Yes |
| `RESEND_API_KEY` | resend.com → API Keys | Yes (Railway blocks SMTP) |
| `SMTP_EMAIL` | Your Gmail address | Yes |
| `SMTP_PASSWORD` | Gmail App Password (16 chars, 2FA required) | Fallback only |
| `NOTIFY_EMAIL` | Where approval emails are sent | Yes |
| `APPROVAL_SECRET` | Any random string | Yes |
| `BASE_URL` | Your Railway URL (no trailing slash) | Yes |
| `JOURNEY_START_DATE` | e.g. `2025-01-06` | Yes |
| `USE_WEB_RESEARCH` | `true` to use live HN/SerpAPI, `false` for curated | Optional |
| `SERPAPI_KEY` | serpapi.com (free tier 100/mo) | Optional |

### GitHub Actions secrets (for Sunday email trigger only)

| Secret | Value |
|---|---|
| `ANTHROPIC_API_KEY` | Same as Railway |
| `SMTP_EMAIL` | Your Gmail |
| `SMTP_PASSWORD` | Gmail App Password |
| `NOTIFY_EMAIL` | Your email |
| `APPROVAL_SECRET` | Same as Railway |
| `APPROVAL_SERVER_URL` | Your Railway URL |
| `BUFFER_ACCESS_TOKEN` | Same as Railway |
| `BUFFER_PROFILE_ID` | Same as Railway |
| `JOURNEY_START_DATE` | Same as Railway |

> GitHub Actions only sends Email 1. All LLM generation happens on Railway when you submit the form.

---

## Setup

### 1. Clone and install

```bash
git clone https://github.com/mahesh539dev/linkedin_postautomation
cd linkedin_postautomation
pip install -r requirements.txt
cp .env.template .env
# Edit .env with your keys
```

### 2. Get your Buffer channel ID

```bash
curl -X POST https://api.buffer.com/graphql \
  -H "Authorization: Bearer YOUR_BUFFER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query":"{ channels { id name serviceType } }"}'
```

Copy the `id` of your LinkedIn channel → set as `BUFFER_PROFILE_ID`.

### 3. Deploy to Railway

```bash
npm install -g @railway/cli
railway login
railway init      # name: linkedin-automation
railway up
railway domain    # copy the URL → set as BASE_URL

# Set all variables
railway variables set ANTHROPIC_API_KEY="sk-ant-..."
railway variables set OPENROUTER_API_KEY="sk-or-..."
railway variables set OPENAI_API_KEY="sk-..."
railway variables set BUFFER_ACCESS_TOKEN="..."
railway variables set BUFFER_PROFILE_ID="..."
railway variables set RESEND_API_KEY="re_..."
railway variables set SMTP_EMAIL="you@gmail.com"
railway variables set SMTP_PASSWORD="xxxx xxxx xxxx xxxx"
railway variables set NOTIFY_EMAIL="you@gmail.com"
railway variables set APPROVAL_SECRET="your-secret"
railway variables set BASE_URL="https://your-app.up.railway.app"
railway variables set JOURNEY_START_DATE="2025-01-06"
railway variables set USE_WEB_RESEARCH="true"
```

### 4. Add GitHub Actions secrets

Repo → Settings → Secrets → Actions → New repository secret. Add all secrets from the table above.

> **Scheduled runs only trigger from the default branch.** Merge to `main` before relying on the Sunday cron. Manual `workflow_dispatch` runs work on any branch.

---

## Weekly Workflow

### Automated (full setup)

```
Sunday 9 AM  →  Email 1 arrives: "What did you learn this week?"
You          →  Click link, fill form (3–5 min), submit
~3 min later →  Email 2 arrives: approval link
You          →  Review posts, pick best version, click Approve
Mon–Fri      →  Buffer posts to LinkedIn automatically
```

### Manual trigger (any day)

```bash
# Open input form directly
open https://your-app.up.railway.app/input/2

# Or trigger GitHub Action (with optional week override)
gh workflow run linkedin_sunday.yml --field week_override=3

# Test Buffer connection
python -m src.schedule_posts --test

# Dry-run scheduling
python -m src.schedule_posts --file posts/week_2.json --dry-run
```

**Smart same-day scheduling:**
- Triggered **before 2 PM** on a weekday → today's 5 PM slot is included
- Triggered **after 2 PM** → posts start from next weekday
- **Weekend** → posts schedule Mon–Fri next week

---

## Post Schedule

All times are **EST/EDT (Toronto)**. The server converts to UTC automatically before sending to Buffer.

| Day | Time (EST) | Type | Focus |
|---|---|---|---|
| Monday | 10:00 | Industry News | Biggest AI/infra story — sharp backend take |
| Tuesday | 17:00 | Bridge | Your backend expertise mapped to an AI concept |
| Wednesday | 10:00 | Industry Trend | Broader AI/MLOps pattern or tool shift |
| Thursday | 17:00 | Learning | One specific thing you learned or built |
| Friday | 10:00 | Opinion | Bold, polarising take — confident, not aggressive |

---

## Review UI

Each post shows 3 AI-generated versions:

- **V1 · Kimi** — original generation
- **V2 · Claude** — Sonnet rewrite with your brand voice
- **V3 · OpenAI** — GPT-4o rewrite

Each version is scored out of 100 across 7 dimensions:

| Dimension | Max | What it checks |
|---|---|---|
| Hook | 20 | First line stops the scroll |
| Specificity | 20 | Numbers, tool names, real examples |
| Insight | 20 | Non-obvious, teaches something |
| Voice | 15 | Matches your direct/confident tone |
| Backend angle | 10 | Connects to your systems background |
| Engagement | 10 | Question or call to action |
| Format | 5 | Whitespace, line breaks, length |

The best-scoring version is auto-selected (gold border on tab). You can switch tabs, edit the text, then approve.

---

## API Endpoints

```
GET  /health              →  {"status": "ok", "time": "..."}
GET  /input/<week>        →  Learning notes form
POST /input/<week>        →  Submit notes, trigger background generation
GET  /review/<token>      →  Post review + approval UI (48hr expiry)
POST /approve/<token>     →  Schedule approved posts to Buffer
GET  /reviews?secret=...  →  List all pending review tokens
```

---

## Customise for Your Journey

Edit `src/config.py`:

```python
# Your background — used in every generation prompt
ENGINEER_CONTEXT = """
Name: Your Name
Role: Current role → Target role
Background: Your years of experience, key technologies
...
"""

# Per-week themes and learning questions
WEEK_THEMES = {
    2: "Your Week 2 Theme",
    3: "Your Week 3 Theme",
    ...
}

LEARNING_QUESTIONS = {
    2: ["What surprised you?", "What did you build?", ...],
    ...
}
```

---

## Troubleshooting

**Email not sending from Railway**
Railway blocks all SMTP ports. Add `RESEND_API_KEY` from resend.com (free, 3,000/month). GitHub Actions uses SMTP and works fine.

**Buffer error: OIDC tokens not accepted**
The token in Railway is a web session token. Get a personal API key: publish.buffer.com/settings/api → Generate API Key.

**Buffer error: channel not found**
Run the channels curl command in Setup step 2, copy the correct `id`, update `BUFFER_PROFILE_ID` in Railway.

**Posts at wrong time**
Verify `BASE_URL` in Railway points to your actual Railway URL, not localhost. The server uses `America/Toronto` timezone automatically.

**Review link expired**
Tokens last 48 hours. Resubmit the form at `/input/<week>` to regenerate.

**Kimi generation fails**
llm_client.py has a fallback chain: Kimi → MiniMax → DeepSeek. If all OpenRouter models fail, check your `OPENROUTER_API_KEY` and credit balance at openrouter.ai.

**GitHub Actions cron not firing**
The `schedule` trigger only fires from the default branch. Merge your branch to `main`.
