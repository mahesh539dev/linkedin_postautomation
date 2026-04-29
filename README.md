# LinkedIn Post Automation

Automated LinkedIn content pipeline for Mahesh Annapureddy's AI Infrastructure Engineer transition. Every week it turns raw learning notes into 6 scored, reviewed, and scheduled LinkedIn posts — driven by a 3-email flow and a multi-model AI pipeline with zero manual scheduling.

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
│   auto_run.py  ──►  Email 1: "Which week are you on?"              │
│                      Buttons for weeks 2–12                         │
│                      Each links to /select-week/<week>             │
│                      (Resend API / SMTP fallback)                   │
└─────────────────────────────────────────────────────────────────────┘
                                │
                  You click your current week
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    RAILWAY FLASK SERVER                             │
│                                                                     │
│   GET  /select-week/<week>                                         │
│          │  DeepSeek generates 5 questions from roadmap.py         │
│          │  Questions stored in memory (pending_questions)         │
│          ▼                                                          │
│   Email 2: "Your Week N learning questions"                        │
│             5 specific questions + link to answer form             │
│                                                                     │
│   GET  /input/<week>   ──►  Answer form with dynamic questions     │
│   POST /input/<week>   ──►  Submit notes → background thread       │
│                                    │                               │
│                    ┌───────────────▼───────────────┐               │
│                    │    GENERATION PIPELINE        │               │
│                    │                               │               │
│                    │  trend_fetcher.py             │               │
│                    │  HN Algolia + SerpAPI (opt.)  │               │
│                    │  Raises if no trends found    │               │
│                    │          │                    │               │
│                    │          ▼                    │               │
│                    │  research_agent.py            │               │
│                    │  DeepSeek (OpenRouter)        │               │
│                    │  Ranks headlines → top 6      │               │
│                    │  Topics must come from HN     │               │
│                    │          │                    │               │
│                    │          ▼                    │               │
│                    │  generate_posts.py            │               │
│                    │  Kimi (OpenRouter)            │               │
│                    │  N posts from notes + topics  │               │
│                    │  + day normalisation pass     │               │
│                    │          │                    │               │
│                    │          ▼                    │               │
│                    │  refinement.py                │               │
│                    │  Claude Haiku                 │               │
│                    │  Polish + brand voice         │               │
│                    │          │                    │               │
│                    │          ▼                    │               │
│                    │  post_variants.py             │               │
│                    │  Claude Sonnet  → V2 rewrite  │               │
│                    │  GPT-4o         → V3 rewrite  │               │
│                    │  GPT-4o scores all 3 versions │               │
│                    └───────────────────────────────┘               │
│                                    │                               │
│                                    ▼                               │
│   Token stored in memory (48 hr expiry)                            │
│          │                                                          │
│          ▼                                                          │
│   Email 3: "Posts ready for review"                                │
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
│                              Scheduled Mon–Sat                     │
└─────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         LINKEDIN                                    │
│                                                                     │
│   Monday    10:00 EST  — Industry News                             │
│   Tuesday   17:00 EST  — Bridge (Backend→AI analogy)              │
│   Wednesday 10:00 EST  — Industry Trend                            │
│   Thursday  17:00 EST  — Model Comparison (trending models)        │
│   Friday    10:00 EST  — Opinion / Hot take                        │
│   Saturday  10:00 EST  — Learning Checkpoint (personal notes)      │
└─────────────────────────────────────────────────────────────────────┘
```

**Cost per weekly run: ~$0.026**

| Step | Model | Cost |
|---|---|---|
| Trend fetching | HN Algolia (free) | $0.000 |
| Question generation | DeepSeek via OpenRouter | ~$0.001 |
| Topic ranking | DeepSeek via OpenRouter | ~$0.003 |
| Post generation (V1) | Kimi via OpenRouter | ~$0.012 |
| Refinement | Claude Haiku | ~$0.010 |
| V2 rewrite + scoring | Claude Sonnet | ~$0.020 |
| V3 rewrite | GPT-4o | ~$0.015 |

---

## Project Structure

```
linkedin_postautomation/
├── src/
│   ├── config.py               # Env vars and constants
│   ├── llm_client.py           # OpenRouter gateway (DeepSeek / Kimi / fallback)
│   ├── trend_fetcher.py        # HN Algolia + optional SerpAPI (3 hr cache)
│   ├── research_agent.py       # Topic ranking via DeepSeek (no hardcoded fallbacks)
│   ├── roadmap.py              # 12-week learning plan + dynamic question generation
│   ├── generate_posts.py       # Post generation + dynamic scheduling + day normalisation
│   ├── linkedin_guidelines.py  # Scoring rubric + personalised system prompt
│   ├── post_variants.py        # Claude Sonnet V2 + GPT-4o V3 + scoring
│   ├── refinement.py           # Claude Haiku polish pass
│   ├── email_utils.py          # Resend API (Railway) / SMTP fallback (GH Actions)
│   ├── approval_server.py      # Flask: 3-email flow + review UI + Buffer scheduling
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
| `NOTIFY_EMAIL` | Where all three emails are sent | Yes |
| `APPROVAL_SECRET` | Any random string | Yes |
| `BASE_URL` | Your Railway URL (no trailing slash) | Yes |
| `JOURNEY_START_DATE` | e.g. `2025-01-06` | Yes |
| `SMTP_EMAIL` | Your Gmail address | Fallback only |
| `SMTP_PASSWORD` | Gmail App Password (16 chars, 2FA required) | Fallback only |
| `SERPAPI_KEY` | serpapi.com (free tier 100/mo) | Optional |

### GitHub Actions secrets (for Sunday email trigger only)

| Secret | Value |
|---|---|
| `SMTP_EMAIL` | Your Gmail |
| `SMTP_PASSWORD` | Gmail App Password |
| `NOTIFY_EMAIL` | Your email |
| `BASE_URL` | Your Railway URL |
| `JOURNEY_START_DATE` | Same as Railway |

> GitHub Actions only sends Email 1 (week selection). All LLM generation happens on Railway after you submit the answer form.

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

# Set all required variables
railway variables set ANTHROPIC_API_KEY="sk-ant-..."
railway variables set OPENROUTER_API_KEY="sk-or-..."
railway variables set OPENAI_API_KEY="sk-..."
railway variables set BUFFER_ACCESS_TOKEN="..."
railway variables set BUFFER_PROFILE_ID="..."
railway variables set RESEND_API_KEY="re_..."
railway variables set NOTIFY_EMAIL="you@gmail.com"
railway variables set APPROVAL_SECRET="your-secret"
railway variables set BASE_URL="https://your-app.up.railway.app"
railway variables set JOURNEY_START_DATE="2025-01-06"
```

### 4. Add GitHub Actions secrets

Repo → Settings → Secrets → Actions → New repository secret. Add the secrets from the GitHub Actions table above.

> **Scheduled runs only trigger from the default branch.** Merge to `main` before relying on the Sunday cron. Manual `workflow_dispatch` runs work on any branch.

---

## Weekly Workflow

### Automated (full setup)

```
Sunday 9 AM  →  Email 1: "Which week are you on?" (buttons for weeks 2–12)
You          →  Click your current week
~30 seconds  →  Email 2: 5 dynamic learning questions for that week
You          →  Click the form link, answer questions (3–5 min), submit
~3 min later →  Email 3: "Posts ready for review" (approval link)
You          →  Review 3 versions per post, pick best, click Approve
Mon–Sat      →  Buffer posts to LinkedIn automatically
```

### Manual trigger (any day)

```bash
# Trigger week selection email directly
python -m src.auto_run --week 5

# Open input form directly (skip email flow)
open https://your-app.up.railway.app/input/5

# Or trigger GitHub Action with optional week override
gh workflow run linkedin_sunday.yml --field week_override=5

# Test Buffer connection
python -m src.schedule_posts --test

# Dry-run scheduling
python -m src.schedule_posts --file posts/week_5.json --dry-run
```

---

## Post Schedule

All times are **EST/EDT (Toronto)**. The server converts to UTC automatically before sending to Buffer.

| Day | Time (EST) | Type | Focus |
|---|---|---|---|
| Monday | 10:00 | Industry News | Biggest AI/infra story of the week — sharp backend take |
| Tuesday | 17:00 | Bridge | Your backend expertise (Kafka/K8s) mapped to an AI concept |
| Wednesday | 10:00 | Industry Trend | Broader AI/MLOps pattern — what it means in 6–12 months |
| Thursday | 17:00 | Model Comparison | 2–3 trending models compared on hard infra metrics (latency, cost, context window) — clear production verdict |
| Friday | 10:00 | Opinion | Bold, polarising take — start with the claim, then back it up |
| Saturday | 10:00 | Learning | Weekly checkpoint — what you studied, built, or discovered this week |

### Dynamic post count

Posts are scheduled starting from the **next day** when you submit. Count is based on what day you run the pipeline:

| Run day | Posts generated | Days covered |
|---|---|---|
| Monday | 5 | Tue–Sat |
| Tuesday | 4 | Wed–Sat |
| Wednesday | 3 | Thu–Sat |
| Thursday | 2 | Fri–Sat |
| Friday | 1 | Sat |
| Saturday or Sunday | 6 | Mon–Sat next week |

---

## Review UI

Each post shows 3 AI-generated versions:

- **V1 · Kimi** — original generation, refined by Claude Haiku
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
| Engagement | 10 | Question or call to action at end |
| Format | 5 | Word count 150–220, ≤2 emojis, hashtags at end only |

The best-scoring version is auto-selected (gold border on tab). Switch tabs, edit the text, then approve.

---

## API Endpoints

```
GET  /health                    →  {"status": "ok", "time": "..."}
GET  /select-week/<week>        →  Generate questions + send Email 2 + confirmation page
GET  /input/<week>              →  Answer form with dynamic questions
POST /input/<week>              →  Submit notes, trigger background generation
GET  /review/<token>            →  Post review + approval UI (48 hr expiry)
POST /approve/<token>           →  Schedule approved posts to Buffer
GET  /reviews?secret=<secret>   →  List all pending review tokens
```

---

## Customise for Your Journey

### Engineer profile

Edit `ENGINEER_CONTEXT` in `src/research_agent.py` and `src/generate_posts.py`:

```python
ENGINEER_CONTEXT = """
Name: Your Name
Role: Current role → Target role
Background: Your years of experience, key technologies
Learning now: Tools you're learning
Unique angle: What makes your perspective different
Target audience: Who you're writing for
"""
```

### Learning roadmap

Edit `src/roadmap.py` — `WEEK_CONTENT` maps each week number to what you're studying. DeepSeek uses this to generate the 5 dynamic questions sent in Email 2:

```python
WEEK_CONTENT = {
    1: "Python for data science: NumPy, Pandas, basic ML concepts",
    2: "Embeddings and semantic search: sentence-transformers, ...",
    # ... add your own weeks
}
```

---

## Troubleshooting

**Email not sending from Railway**
Railway blocks all SMTP ports. Add `RESEND_API_KEY` from resend.com (free, 3,000 emails/month). GitHub Actions uses SMTP directly and works fine without Resend.

**No questions in Email 2 / select-week returns 500**
DeepSeek question generation failed. Check `OPENROUTER_API_KEY` and credit balance at openrouter.ai. Railway logs show the full traceback.

**Research returns error / no trends**
`trend_fetcher.py` raises `RuntimeError` if HN Algolia returns nothing. Check network connectivity from Railway. Adding `SERPAPI_KEY` gives a second source as backup.

**Buffer error: OIDC tokens not accepted**
The token in Railway is a web session token, not a personal API key. Get it from: publish.buffer.com → Settings → API → Generate API Key.

**Buffer error: channel not found**
Run the channels `curl` command in Setup step 2, copy the correct `id`, update `BUFFER_PROFILE_ID` in Railway.

**Posts at wrong time (UTC instead of EST)**
Verify `BASE_URL` is set to your Railway URL. The server uses `America/Toronto` timezone for all datetime conversions.

**Wrong number of posts / posts on wrong days**
After generation, Railway logs print `Posts after normalisation: N (Day, Day, ...)` showing the corrected schedule. If the LLM assigns multiple posts to the same day, the normalisation pass fixes it automatically.

**Review link expired**
Tokens last 48 hours. Resubmit the form at `/input/<week>` to regenerate.

**Kimi generation fails**
`llm_client.py` has a fallback chain: Kimi → MiniMax → DeepSeek. If all OpenRouter models fail, check `OPENROUTER_API_KEY` and credit balance at openrouter.ai.

**GitHub Actions cron not firing**
The `schedule` trigger only fires from the default branch. Merge your branch to `main`.
