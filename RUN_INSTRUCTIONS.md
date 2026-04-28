# How to Run the LinkedIn Post Automation System

**Status: ✓ All systems verified and working**

## Prerequisites ✓

- [x] Python 3.9+ (installed)
- [x] Dependencies installed (`pip install -r requirements.txt`)
- [x] `.env` configured with all credentials
- [x] All modules import successfully
- [x] Flask server tested and working

## 🎯 Simple 3-Step Workflow

### Step 1: Start the Flask Server

```bash
python src/approval_server.py
```

**Expected output:**
```
Approval server on port 5000 | http://localhost:5000
 * Running on http://127.0.0.1:5000
```

The server runs in foreground. Keep this terminal open while you use the app.

**To stop:** Press `Ctrl+C`

---

### Step 2: Open the Learning Input Form

In your browser, go to:

```
http://localhost:5000/input/2
```

Replace `2` with your current week number (1-9).

You'll see a dark-themed form with 5 learning questions for that week.

**Fill in your answers:**
- What did you learn?
- What surprised you?
- What did you build?
- What clicked?
- Any mistakes that taught you something?

**Be specific** — include numbers, tool names, patterns you recognized. Claude uses your exact words.

Click: **"Generate My Posts →"**

The page shows: *"Claude is researching topics + writing your 5 posts. Check your email in 3–5 minutes."*

---

### Step 3: Review & Approve Posts

**Check your email** (the address in `NOTIFY_EMAIL` from `.env`)

You'll get: **"Week 2 LinkedIn — posts ready for review"**

**Click the link** to open the review UI in your browser.

You'll see 5 posts with:
- Post type (industry news, bridge, trend, learning, opinion)
- Scheduled day and time
- Full content in an editable text area
- Character count

**For each post:**
- **Approve** — green button
- **Reject** — red button (if you don't like it)
- **Edit** — change the text before approving
- **Undo** — revert your approval/rejection decision

Only approved posts go to Buffer.

Click: **"Approve All & Schedule →"**

You'll see: *"✅ Posts Sent to Buffer"*

---

## 🔍 Verify Everything Works First

Before your first run, check that all systems are ready:

```bash
python verify_setup.py
```

Output should show all 5 checks passing:
```
[1/5] Testing module imports...      OK
[2/5] Checking configuration...      OK
[3/5] Checking Flask app...          OK
[4/5] Checking week configuration... OK
[5/5] Checking journey dates...      OK

OK: SYSTEM READY
```

---

## 🧪 Individual Tests (Optional)

### Test Buffer Connection

Verify your Buffer API credentials work:

```bash
python src/schedule_posts.py --test
```

Should show:
```
OK Buffer connected — Profile: your_linkedin_handle
```

### Check Buffer Queue

See all posts scheduled in Buffer:

```bash
python src/schedule_posts.py --queue
```

Shows list of pending posts with scheduled times.

### Test Flask Health Endpoint

```bash
curl http://localhost:5000/health
```

Should return:
```json
{"status": "ok", "time": "2026-04-27T..."}
```

### Dry-Run Post Generation

Generate posts without scheduling to Buffer:

```bash
python -c "
from src.research_agent import research_weekly_topics
from src.generate_posts import generate_posts

week = 2
notes = 'This week I learned FastAPI type hints. Built a task API.'
research = research_weekly_topics(week, save=True)
posts = generate_posts(week, research, notes, save=True)
print(f'Generated {len(posts[\"posts\"])} posts')
"
```

---

## 📂 File Locations

After generation, posts are saved to:
```
posts/week_2.json      # Week 2 generated posts
posts/week_2_research.json  # Week 2 research data
```

Generated posts include:
- Full content
- Type (industry_news, bridge, etc.)
- Schedule day and time
- Title and source topic

---

## 🚨 Troubleshooting

### Flask won't start: "Address already in use"

Port 5000 is taken by another process.

**Fix 1: Kill the process**
```bash
# Windows PowerShell
netstat -ano | findstr :5000
taskkill /PID <PID> /F

# macOS/Linux
lsof -i :5000
kill -9 <PID>
```

**Fix 2: Use different port**
```bash
PORT=8000 python src/approval_server.py
# Then visit: http://localhost:8000/input/2
```

---

### "I didn't receive the approval email"

Check these in order:

1. **Email address is correct** — verify `NOTIFY_EMAIL` in `.env`
2. **Check spam folder** — Gmail may filter it
3. **SMTP credentials are right** — test with:
   ```bash
   python -c "
   import smtplib
   from dotenv import load_dotenv
   import os
   load_dotenv()
   email = os.getenv('SMTP_EMAIL')
   password = os.getenv('SMTP_PASSWORD')
   try:
       with smtplib.SMTP_SSL('smtp.gmail.com', 465) as s:
           s.login(email, password)
       print('SMTP login OK')
   except Exception as e:
       print(f'SMTP failed: {e}')
   "
   ```

4. **Gmail app password** — make sure you're using app-specific password, NOT your Gmail password
   - Go to [myaccount.google.com/security](https://myaccount.google.com/security)
   - Click "App passwords" (requires 2FA enabled)
   - Select "Mail" and "Windows Computer"
   - Copy the 16-char password
   - Paste in `.env` as `SMTP_PASSWORD=xxxx xxxx xxxx xxxx` (spaces are part of it)

---

### "Buffer API error when approving posts"

Test connection:
```bash
python src/schedule_posts.py --test
```

If it fails:

1. **Check token** — go to [buffer.com/developers](https://buffer.com/developers)
   - Regenerate Access Token
   - Update `.env` with new `BUFFER_ACCESS_TOKEN`

2. **Check profile ID** — go to [publish.buffer.com](https://publish.buffer.com)
   - Click your LinkedIn channel
   - Copy the profile ID from the URL: `...profile=69efe0b45c4c051afae74765`
   - Update `.env` with `BUFFER_PROFILE_ID`

3. **Rate limits** — if posting many at once, Buffer may rate-limit
   - Wait 1 minute and retry
   - Or schedule posts manually at publish.buffer.com

---

### "Claude API error"

Check:

1. **API key is valid** — test with:
   ```bash
   python -c "
   import anthropic
   import os
   from dotenv import load_dotenv
   load_dotenv()
   
   api_key = os.getenv('ANTHROPIC_API_KEY')
   if not api_key.startswith('sk-ant-'):
       print('ERROR: Invalid API key format')
   else:
       client = anthropic.Anthropic(api_key=api_key)
       msg = client.messages.create(
           model='claude-sonnet-4-20250514',
           max_tokens=100,
           messages=[{'role': 'user', 'content': 'Hi'}]
       )
       print('Claude API working')
   "
   ```

2. **You have API credits** — check [console.anthropic.com/account/billing](https://console.anthropic.com/account/billing)

3. **No internet connection** — check your network

---

## 📊 Post Types Explained

Your 5 weekly posts mix personal + industry content:

1. **Industry News** (Monday 10am)
   - Biggest AI/infrastructure news from the week
   - Your sharp take as a backend engineer
   - Example: "Llama 2 released with 4-bit quantization. Here's why this breaks the cost/quality tradeoff..."

2. **Bridge** (Tuesday 5pm)
   - Connect your backend expertise to AI infrastructure
   - "How Kafka throughput tuning teaches you LLM batching..."
   - Shows your unique angle

3. **Industry Trend** (Wednesday 10am)
   - Broader pattern in AI/MLOps/LLM space
   - New tools, released benchmarks, company moves
   - "Everyone's building vector search. Here's what actually matters..."

4. **Learning** (Thursday 5pm)
   - What YOU learned or built this week
   - Most authentic, personal post
   - "Built my first RAG system. Spent 3 hours tuning retrieval. Here's what worked..."

5. **Opinion** (Friday 10am)
   - Bold, sometimes polarizing take
   - Memorable and shareable
   - "MLOps engineers are solving the wrong problem. Here's why..."

---

## 📅 Your Journey Timeline

Your `JOURNEY_START_DATE` is: **2026-04-27**

This means:
- Week 1: Apr 27 – May 3 (current week)
- Week 2: May 4 – May 10
- Week 3: May 11 – May 17
- ...
- Week 9: Jun 22 – Jun 28 (final week)

Current week is auto-calculated. To generate for a specific week, replace `2` in the URL with your week number.

---

## 🎓 Customizing Questions

Edit `src/config.py` to change learning questions for your journey:

```python
LEARNING_QUESTIONS = {
    2: [
        "What surprised you?",
        "What did you build?",
        "How does X compare to your backend knowledge?",
        # Add your own
    ],
    3: [
        # Customize per week
    ],
}
```

Also customize:
- `WEEK_THEMES` — the week title
- `ENGINEER_CONTEXT` — your background/story
- `AUTO_LEARNING_NOTES` — auto-filled notes (if not doing manual input)

---

## 🚀 Deploy to Production (Skip for Now)

Once you're happy locally, deploy to the cloud so you can access from anywhere:

### Option 1: Railway (Easiest)
```bash
# Push to GitHub
git push origin main

# At railway.app:
# 1. Create new project
# 2. Connect GitHub repo
# 3. Set environment variables from .env
# 4. Railway auto-deploys
```

Then use your Railway URL instead of `http://localhost:5000` in `.env` as `BASE_URL`.

### Option 2: Heroku
```bash
heroku create linkedin-automation
heroku config:set ANTHROPIC_API_KEY=sk-ant-...
git push heroku main
```

### Option 3: Docker
```bash
docker build -t linkedin-automation .
docker run -p 5000:5000 --env-file .env linkedin-automation
```

---

## 💡 Pro Tips

1. **First run takes longer** — 3–5 minutes because Claude researches fresh topics. Subsequent runs are faster.

2. **Edit before approving** — the text area is fully editable. Refine Claude's posts before they go to Buffer.

3. **Approve subset** — you don't have to approve all 5. Approve only the ones you like, reject the rest. Only approved posts schedule.

4. **Check Buffer** — after approving, go to [publish.buffer.com](https://publish.buffer.com) to confirm posts queued. You can reschedule or delete there if needed.

5. **Manual scheduling** — if something goes wrong with Buffer integration, you can schedule posts manually at publish.buffer.com.

6. **Dry-run testing** — test the full flow with:
   ```bash
   python src/schedule_posts.py --file posts/week_2.json --dry-run
   ```

---

## 🎯 Next Steps

**Right now:**
1. ✓ Verify setup: `python verify_setup.py`
2. ✓ Start server: `python src/approval_server.py`
3. ✓ Open form: `http://localhost:5000/input/2`
4. ✓ Submit learning notes
5. ✓ Check email in 3–5 minutes
6. ✓ Review and approve posts
7. ✓ Check Buffer for scheduled posts

**This week:**
- Generate posts for your current week
- Refine the learning questions in `src/config.py` for your journey
- Test Buffer posting
- Adjust post timing in `src/config.py` if needed

**Next week:**
- Automate with GitHub Actions (see `.github/workflows/sunday-automation.yml`)
- Deploy to production (Railway/Heroku)
- Set up recurring weekly generation

---

**Questions?** Check the [README.md](README.md) for full documentation or [QUICKSTART.md](QUICKSTART.md) for common workflows.

**All set! Start with:**
```bash
python src/approval_server.py
```

Then open: `http://localhost:5000/input/2`
