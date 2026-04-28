# Quick Start Guide

## ✓ System is Ready!

All modules are configured and working. Here's how to run the app.

## 🚀 Run the Flask Server

```bash
python src/approval_server.py
```

You'll see:
```
Approval server on port 5000 | http://localhost:5000
 * Running on http://127.0.0.1:5000
```

## 📝 Generate Your First Posts

Open your browser to: **http://localhost:5000/input/2**

(Replace `2` with your current week number if different)

### The Input Form
You'll see 5 learning questions for your week. Answer them with:
- What you learned
- What surprised you
- What you built
- Specific numbers, tool names, patterns you recognized

**Be specific** — Claude uses your exact words to make authentic posts.

Click **"Generate My Posts →"**

The page will show: "Claude is researching topics + writing your 5 posts. Check your email in 3-5 minutes."

## 📧 Approve Your Posts

**Check your email** (`NOTIFY_EMAIL` from `.env`)

You'll receive an approval link. Click it to:
- **Review** all 5 generated posts
- **Edit** any content directly
- **Approve** the ones you like
- **Reject** the ones you don't

Only approved posts go to Buffer.

### Post Types
1. **Industry News** — Sharp backend take on latest AI/infra news
2. **Bridge** — Connect your backend expertise to AI concept
3. **Industry Trend** — Broader AI infrastructure trend/tool update
4. **Learning** — What YOU learned or built this week
5. **Opinion** — Bold, polarizing hot take

## 🔗 Approved Posts → Buffer → LinkedIn

After approval, posts automatically schedule to Buffer:
- **Monday 10:00** — Industry News
- **Tuesday 17:00** — Bridge analogy
- **Wednesday 10:00** — Industry Trend
- **Thursday 17:00** — Learning
- **Friday 10:00** — Opinion

Check [publish.buffer.com](https://publish.buffer.com) to confirm posts scheduled.

## 🧪 Test Buffer Connection

Before generating posts, verify your Buffer credentials work:

```bash
python src/schedule_posts.py --test
```

You should see:
```
  OK Buffer connected — Profile: your_linkedin_handle
```

## 🔧 Common Issues

### "I didn't get an approval email"
- Check `NOTIFY_EMAIL` in `.env` (should be your Gmail)
- Check spam folder
- Verify `SMTP_EMAIL` and `SMTP_PASSWORD` are correct
- Gmail needs app-specific password, not regular password

### "Flask server won't start"
- Port 5000 might be in use
- Try: `PORT=8000 python src/approval_server.py`
- Or kill whatever's using port 5000

### "Posts aren't scheduling to Buffer"
- Run: `python src/schedule_posts.py --test`
- Check `BUFFER_ACCESS_TOKEN` and `BUFFER_PROFILE_ID` in `.env`
- Visit [buffer.com/developers](https://buffer.com/developers) to regenerate token if needed

### "Claude API errors"
- Verify `ANTHROPIC_API_KEY` is valid (starts with `sk-ant-`)
- Check you have API credits at [console.anthropic.com](https://console.anthropic.com)
- Verify internet connection

## 📊 Your Current Journey

- **Journey Start:** 2026-04-27 (from `.env`)
- **Current Week:** 1
- **Configured Weeks:** 2-9 with themes and questions in `src/config.py`

### Week Schedule
```
Week 2: Python Foundations
Week 3: Embeddings and Vectors
Week 4: Vector DBs and RAG
Week 5: FastAPI and Kafka AI Pipelines
Week 6: LangChain and LangGraph
Week 7: LLM Inference and vLLM
Week 8: Observability and MLflow
Week 9: Production AI and Hiring Push
```

## 🤖 Customize Learning Questions

Edit `src/config.py` to change questions for your journey:

```python
LEARNING_QUESTIONS = {
    2: [
        "What surprised you?",
        "What did you build?",
        # Add your own questions
    ],
}
```

## 🎯 Full Weekly Workflow

1. **Sunday/Monday**: Open `http://localhost:5000/input/2`
2. **Answer questions** about your week's learning
3. **Click "Generate"** and wait for email (3-5 min)
4. **Check email** for approval link
5. **Review and edit** posts in browser
6. **Approve** your favorites
7. **Posts schedule** to Buffer automatically
8. **Check Buffer** that posts are queued
9. **Posts publish** automatically Mon-Fri

## 📱 Deploy to Production (Optional)

To make your approval form accessible anywhere:

### Railway (Recommended)
```bash
# 1. Push code to GitHub
# 2. Go to railway.app, create new project
# 3. Connect your GitHub repo
# 4. Set environment variables from .env
# 5. Deploy — Railway builds and runs automatically
```

### Or use Heroku, AWS, or Docker

See full README.md for deployment details.

## ⚡ Automated Sunday Generation (Optional)

GitHub Actions can automatically generate posts every Sunday.

Set up: `.github/workflows/sunday-automation.yml`

Then weekly posts auto-generate and email you for approval — no manual `/input` form needed.

## 💡 Tips

- **Post quality** depends on learning notes quality — be specific
- **Research takes time** — first run may take 3-5 minutes
- **Edit before approval** — the edit box lets you refine Claude's output
- **Buffer queue** — see all pending posts at publish.buffer.com/buffer/social/queue
- **Timezone** — schedule times are in your local timezone

## 🎓 Learning Journey Milestones

```
Week 1-2:  Foundations (Python, NumPy)
Week 3-4:  Vectors & RAG (embeddings, vector DBs)
Week 5-6:  Systems (FastAPI, LangChain agents)
Week 7-8:  Production (vLLM, observability)
Week 9:    AI Infrastructure Engineer ready
```

---

**All set!** Start with:

```bash
python src/approval_server.py
# Then open http://localhost:5000/input/2
```

Questions? Check `/health` endpoint or review `.env` setup.
