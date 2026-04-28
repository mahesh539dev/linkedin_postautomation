"""
approval_server.py
──────────────────
Flask web server for the LinkedIn automation pipeline.
Serves learning input form, triggers post generation, and handles approval UI.
"""

import os
import json
import uuid
import hmac
import smtplib
import threading
import time
import requests
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask import Flask, request, jsonify, render_template_string, redirect
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

SECRET_KEY      = os.getenv("APPROVAL_SECRET", "change-me")
BUFFER_API_BASE = "https://api.bufferapp.com/1"

def get_base_url():
    """Get BASE_URL from environment at runtime. On Railway, uses BASE_URL from .env.
    Fallback to localhost:5000 only if BASE_URL not set (for local development)."""
    return os.getenv("BASE_URL", "http://localhost:5000").rstrip('/')

# In-memory store: token → {data, expires_at}
pending_reviews = {}


# ── Buffer ────────────────────────────────────────────────────────────────────

def schedule_to_buffer(content: str, scheduled_datetime: str) -> dict:
    token      = os.getenv("BUFFER_ACCESS_TOKEN")
    profile_id = os.getenv("BUFFER_PROFILE_ID")
    dt = datetime.strptime(scheduled_datetime, "%Y-%m-%d %H:%M:%S")
    payload = {
        "access_token":  token,
        "profile_ids[]": profile_id,
        "text":          content,
        "scheduled_at":  int(dt.timestamp()),
        "now":           False,
        "shorten":       False,
    }
    r = requests.post(f"{BUFFER_API_BASE}/updates/create.json", data=payload)
    if r.status_code == 200:
        data = r.json()
        if data.get("success"):
            return {"success": True, "id": data.get("updates", [{}])[0].get("id")}
    return {"success": False, "error": r.text[:200]}


# ── Email ─────────────────────────────────────────────────────────────────────

def send_review_email(to_email: str, review_token: str, week: int, posts: list) -> bool:
    smtp_email    = os.getenv("SMTP_EMAIL")
    smtp_password = os.getenv("SMTP_PASSWORD")
    if not smtp_email or not smtp_password:
        print("SMTP not configured — skipping email")
        return False

    review_url = f"{get_base_url()}/review/{review_token}"
    type_icons = {"industry_news": "📰", "bridge": "🌉",
                  "industry_trend": "📈", "learning": "🎓", "opinion": "💡"}
    previews = "".join(
        f"\n  {type_icons.get(p.get('type',''),'📌')} "
        f"{p.get('schedule_day')} {p.get('schedule_time')} — {p.get('type','').upper()}\n"
        f"  \"{p.get('content','')[:100]}...\"\n"
        for p in posts
    )

    html = f"""<html><body style="font-family:sans-serif;max-width:600px;margin:0 auto;padding:20px">
<h2 style="color:#3b82f6">LinkedIn Week {week} — Review Ready</h2>
<p>5 posts generated. Your approval needed before they go to Buffer.</p>
<pre style="background:#f1f5f9;padding:16px;border-radius:8px;font-size:13px">{previews}</pre>
<div style="text-align:center;margin:28px 0">
  <a href="{review_url}" style="background:#3b82f6;color:white;padding:14px 36px;
     border-radius:8px;text-decoration:none;font-size:15px;font-weight:700">
    Review &amp; Approve Posts →
  </a>
</div>
<p style="color:#64748b;font-size:12px">Link expires in 48 hours.</p>
</body></html>"""

    msg = MIMEMultipart("alternative")
    msg["From"]    = smtp_email
    msg["To"]      = to_email
    msg["Subject"] = f"✍️ LinkedIn Week {week}: posts ready for review"
    msg.attach(MIMEText(html, "html"))
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as s:
            s.login(smtp_email, smtp_password)
            s.send_message(msg)
        print(f"Review email sent to {to_email}")
        return True
    except Exception as e:
        print(f"Email failed: {e}")
        return False


# ── Background generation ─────────────────────────────────────────────────────

def generate_and_store(week: int, notes: str, tuesday_start: bool):
    """Run research + generation then store token and email user."""
    try:
        from src.research_agent import get_fallback_topics
        from src.generate_posts import generate_posts

        # Use curated fallback topics — avoids expensive web search API calls.
        # Set USE_WEB_RESEARCH=true in Railway env to enable live search once
        # your Anthropic account is on a paid plan with higher rate limits.
        use_web = os.getenv("USE_WEB_RESEARCH", "false").lower() == "true"
        if use_web:
            from src.research_agent import research_weekly_topics
            try:
                research = research_weekly_topics(week, save=True)
            except Exception as e:
                print(f"Web research failed ({e}), falling back to curated topics")
                research = get_fallback_topics(week)
        else:
            print("Using curated fallback topics (web research disabled)")
            research = get_fallback_topics(week)

        data = generate_posts(week, research, notes, save=True)

        try:
            from src.refinement import refine_posts
            data["posts"] = refine_posts(data["posts"])
        except Exception as e:
            print(f"Refinement step failed ({e}), continuing with unrefined posts")

        token      = str(uuid.uuid4()).replace("-", "")[:24]
        expires_at = datetime.now() + timedelta(hours=48)
        pending_reviews[token] = {
            "data":       data,
            "expires_at": expires_at.isoformat(),
        }

        review_url = f"{get_base_url()}/review/{token}"
        to_email   = os.getenv("NOTIFY_EMAIL", "mahesh.annapureddy5@gmail.com")
        sent       = send_review_email(to_email, token, week, data.get("posts", []))

        print("=" * 60)
        print(f"GENERATION COMPLETE — Week {week}")
        print(f"Review URL: {review_url}")
        if sent:
            print(f"Approval email sent to {to_email}")
        else:
            print(f"EMAIL FAILED — open this URL manually: {review_url}")
            print(f"Check SMTP_EMAIL / SMTP_PASSWORD in Railway env vars")
        print("=" * 60)

    except Exception as e:
        print(f"Background generation failed: {e}")


# ── Input form HTML ───────────────────────────────────────────────────────────

INPUT_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>Week {{ week }} — What did you learn?</title>
  <style>
    body{font-family:-apple-system,sans-serif;background:#0a0f1e;color:#e2e8f0;
         max-width:640px;margin:0 auto;padding:40px 20px}
    h1{color:#60a5fa;font-size:22px;margin-bottom:6px}
    .sub{color:#64748b;font-size:13px;margin-bottom:28px;font-family:monospace}
    .q{background:#1e293b;border-left:3px solid #3b82f6;padding:12px 16px;
       margin-bottom:10px;border-radius:0 6px 6px 0}
    .q p{color:#94a3b8;font-size:12px;margin:0 0 4px;font-family:monospace}
    .q span{color:#e2e8f0;font-size:14px}
    textarea{width:100%;min-height:220px;background:rgba(0,0,0,.4);border:1px solid #1e3a5f;
             border-radius:8px;padding:14px;color:#e2e8f0;font-size:14px;
             line-height:1.7;resize:vertical;outline:none;margin:16px 0}
    textarea:focus{border-color:#3b82f6}
    button{background:linear-gradient(135deg,#3b82f6,#06d6a0);color:white;
           padding:14px 36px;border-radius:8px;border:none;font-size:15px;
           font-weight:700;cursor:pointer;width:100%}
    .done{display:none;background:rgba(6,214,160,.1);border:1px solid #06d6a0;
          border-radius:8px;padding:20px;text-align:center;margin-top:20px}
    .done h2{color:#06d6a0;margin-bottom:6px}
    .done p{color:#94a3b8;font-size:14px}
  </style>
</head>
<body>
  <h1>📚 Week {{ week }}: What did you learn?</h1>
  <p class="sub">{{ theme }} · {{ today }}</p>

  {% if tuesday_start %}
  <div style="background:rgba(245,158,11,.1);border:1px solid rgba(245,158,11,.3);
       border-radius:8px;padding:12px 16px;margin-bottom:20px;color:#fbbf24;font-size:13px">
    📅 <strong>This week only:</strong> Starting Tuesday — posts go Tue–Fri.
  </div>
  {% endif %}

  <div>{% for q in questions %}
    <div class="q"><p>Q{{ loop.index }}</p><span>{{ q }}</span></div>
  {% endfor %}</div>

  <form id="form">
    <textarea id="notes" placeholder="Answer the questions above in any order. Be specific — numbers, tool names, what surprised you, what you built. Claude uses your exact words."></textarea>
    <button type="submit" id="btn">✍️ Generate My Posts →</button>
  </form>

  <div class="done" id="done">
    <h2>Generating your posts...</h2>
    <p>Claude is researching topics + writing your 5 posts.<br>
       Check your email in 3–5 minutes for the approval link.</p>
  </div>

  <script>
    document.getElementById('form').addEventListener('submit', async e => {
      e.preventDefault();
      const notes = document.getElementById('notes').value.trim();
      if (!notes) { alert('Please share what you learned first.'); return; }
      document.getElementById('btn').textContent = 'Generating...';
      document.getElementById('btn').disabled = true;
      const resp = await fetch('/input/{{ week }}', {
        method: 'POST',
        headers: {'Content-Type':'application/json'},
        body: JSON.stringify({notes, tuesday_start: {{ 'true' if tuesday_start else 'false' }}})
      });
      const data = await resp.json();
      if (data.success) {
        document.getElementById('form').style.display = 'none';
        document.getElementById('done').style.display = 'block';
      } else {
        alert('Error: ' + (data.error || 'unknown'));
        document.getElementById('btn').textContent = '✍️ Generate My Posts →';
        document.getElementById('btn').disabled = false;
      }
    });
  </script>
</body>
</html>"""


# ── Review UI HTML ────────────────────────────────────────────────────────────

REVIEW_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>Review — Week {{ week }}</title>
  <style>
    *{box-sizing:border-box;margin:0;padding:0}
    body{font-family:-apple-system,sans-serif;background:#0a0f1e;color:#e2e8f0;
         padding-bottom:100px}
    .header{background:linear-gradient(135deg,#0f2044,#0a1628);border-bottom:1px solid #1e3a5f;
            padding:20px 32px;position:sticky;top:0;z-index:100;
            display:flex;align-items:center;justify-content:space-between}
    .header h1{color:#fff;font-size:20px}
    .header p{color:#64748b;font-size:12px;font-family:monospace;margin-top:3px}
    .badge{font-family:monospace;font-size:12px;padding:5px 14px;border-radius:20px;
           background:rgba(59,130,246,.15);color:#60a5fa;border:1px solid rgba(59,130,246,.3)}
    .container{max-width:820px;margin:0 auto;padding:32px 20px}
    .card{background:#111827;border:1px solid #1e3a5f;border-radius:12px;
          margin-bottom:18px;overflow:hidden;transition:border-color .2s}
    .card.approved{border-color:#06d6a0}
    .card.rejected{border-color:#ef4444;opacity:.55}
    .card-head{padding:14px 18px;background:#1a2234;border-bottom:1px solid #1e3a5f;
               display:flex;align-items:center;gap:10px;flex-wrap:wrap}
    .num{font-family:monospace;font-size:11px;color:#64748b;background:rgba(255,255,255,.05);
         padding:3px 10px;border-radius:10px;border:1px solid #1e3a5f}
    .type{font-size:11px;font-weight:600;padding:4px 12px;border-radius:10px;
          text-transform:uppercase;font-family:monospace}
    .type-industry_news{background:rgba(139,92,246,.2);color:#a78bfa;border:1px solid rgba(139,92,246,.3)}
    .type-bridge{background:rgba(6,214,160,.15);color:#06d6a0;border:1px solid rgba(6,214,160,.3)}
    .type-industry_trend{background:rgba(59,130,246,.2);color:#60a5fa;border:1px solid rgba(59,130,246,.3)}
    .type-learning{background:rgba(245,158,11,.2);color:#fbbf24;border:1px solid rgba(245,158,11,.3)}
    .type-opinion{background:rgba(239,68,68,.2);color:#f87171;border:1px solid rgba(239,68,68,.3)}
    .sched{margin-left:auto;font-family:monospace;font-size:12px;color:#64748b}
    .st{font-size:12px;font-weight:600;padding:4px 12px;border-radius:10px}
    .st-pending{background:rgba(100,116,139,.2);color:#64748b}
    .st-approved{background:rgba(6,214,160,.2);color:#06d6a0}
    .st-rejected{background:rgba(239,68,68,.2);color:#ef4444}
    .card-body{padding:18px}
    .post-title{font-size:13px;color:#94a3b8;margin-bottom:10px;font-style:italic}
    textarea{width:100%;min-height:150px;background:rgba(0,0,0,.35);
             border:1px solid #1e3a5f;border-radius:8px;padding:12px 14px;
             color:#e2e8f0;font-size:14px;line-height:1.7;resize:vertical;outline:none}
    textarea:focus{border-color:#3b82f6}
    .chars{font-family:monospace;font-size:11px;color:#64748b;text-align:right;margin-top:4px}
    .card-actions{padding:12px 18px;border-top:1px solid #1e3a5f;display:flex;gap:8px;align-items:center}
    .btn{padding:8px 18px;border-radius:8px;font-size:13px;font-weight:600;
         cursor:pointer;border:none;font-family:inherit}
    .btn-a{background:#06d6a0;color:#0a1628}
    .btn-r{background:rgba(239,68,68,.15);color:#ef4444;border:1px solid rgba(239,68,68,.3)}
    .btn-u{background:rgba(100,116,139,.2);color:#64748b;border:1px solid #1e3a5f;display:none}
    .src{margin-left:auto;font-family:monospace;font-size:11px;color:#64748b;
         background:rgba(255,255,255,.04);padding:3px 10px;border-radius:6px;border:1px solid #1e3a5f}
    .submit-bar{position:fixed;bottom:0;left:0;right:0;
                background:linear-gradient(0deg,#0a0f1e 70%,transparent);
                padding:18px 32px 22px;display:flex;justify-content:center;
                gap:14px;align-items:center;z-index:200}
    .submit-btn{background:linear-gradient(135deg,#3b82f6,#06d6a0);color:white;
                padding:13px 34px;border-radius:10px;font-size:15px;font-weight:700;
                border:none;cursor:pointer;box-shadow:0 4px 20px rgba(59,130,246,.3)}
    .submit-info{font-family:monospace;font-size:13px;color:#64748b}
    .success{display:none;background:rgba(6,214,160,.1);border:1px solid #06d6a0;
             border-radius:12px;padding:28px;text-align:center;margin-bottom:24px}
    .success h2{color:#06d6a0;font-size:22px;margin-bottom:8px}
    .success p{color:#94a3b8;font-size:14px}
    .instructions{background:rgba(245,158,11,.08);border:1px solid rgba(245,158,11,.25);
                  border-radius:8px;padding:12px 16px;margin-bottom:24px;
                  font-size:13px;color:#fbbf24;line-height:1.6}
  </style>
</head>
<body>
<div class="header">
  <div>
    <h1>LinkedIn Post Review</h1>
    <p>Week {{ week }} · {{ theme }} · {{ generated_at }}</p>
  </div>
  <span class="badge" id="cnt">0 / {{ posts|length }} approved</span>
</div>

<div class="container">
  <div class="success" id="success">
    <h2>✅ Posts Sent to Buffer</h2>
    <p>Your approved posts are now scheduled for the week.<br>
       Check <a href="https://publish.buffer.com" style="color:#3b82f6">publish.buffer.com</a> to confirm.</p>
  </div>

  <div class="instructions">
    ⚡ Read each post · Edit directly if needed · Approve what you like · Reject the rest.
    Only approved posts go to Buffer.
  </div>

{% for post in posts %}
  <div class="card" id="card-{{ loop.index0 }}">
    <div class="card-head">
      <span class="num">Post {{ loop.index }}</span>
      <span class="type type-{{ post.type }}">{{ post.type.replace('_',' ') }}</span>
      <span class="sched">{{ post.schedule_day }} · {{ post.schedule_time }}</span>
      <span class="st st-pending" id="st-{{ loop.index0 }}">Pending</span>
    </div>
    <div class="card-body">
      <div class="post-title">{{ post.title }}</div>
      <textarea id="tx-{{ loop.index0 }}" oninput="cc({{ loop.index0 }})">{{ post.content }}</textarea>
      <div class="chars" id="ch-{{ loop.index0 }}"></div>
    </div>
    <div class="card-actions">
      <button class="btn btn-a" onclick="approve({{ loop.index0 }})">✓ Approve</button>
      <button class="btn btn-r" onclick="reject({{ loop.index0 }})">✗ Reject</button>
      <button class="btn btn-u" id="undo-{{ loop.index0 }}" onclick="undo({{ loop.index0 }})">↩ Undo</button>
      <span class="src">{{ post.source_topic or 'personal' }}</span>
    </div>
  </div>
{% endfor %}
</div>

<div class="submit-bar">
  <span class="submit-info" id="info">Approve posts above, then submit</span>
  <button class="submit-btn" onclick="submitAll()">Approve All &amp; Schedule →</button>
</div>

<script>
const N = {{ posts|length }};
const token = "{{ token }}";
const s = new Array(N).fill('pending');

function cc(i) {
  const l = document.getElementById('tx-'+i).value.length;
  document.getElementById('ch-'+i).textContent = l + ' chars';
}
function badge() {
  const a = s.filter(x=>x==='approved').length;
  document.getElementById('cnt').textContent = a+' / '+N+' approved';
  document.getElementById('info').textContent =
    a===0 ? 'Approve posts above, then submit' : a+' post'+(a>1?'s':'')+' ready to schedule';
}
function approve(i) {
  s[i]='approved';
  document.getElementById('card-'+i).className='card approved';
  const st=document.getElementById('st-'+i);
  st.className='st st-approved'; st.textContent='✓ Approved';
  document.getElementById('undo-'+i).style.display='inline-block';
  badge();
}
function reject(i) {
  s[i]='rejected';
  document.getElementById('card-'+i).className='card rejected';
  const st=document.getElementById('st-'+i);
  st.className='st st-rejected'; st.textContent='✗ Rejected';
  document.getElementById('undo-'+i).style.display='inline-block';
  badge();
}
function undo(i) {
  s[i]='pending';
  document.getElementById('card-'+i).className='card';
  const st=document.getElementById('st-'+i);
  st.className='st st-pending'; st.textContent='Pending';
  document.getElementById('undo-'+i).style.display='none';
  badge();
}
async function submitAll() {
  const approved = s.map((v,i)=>v==='approved'?i:-1).filter(i=>i>=0);
  if (!approved.length) { alert('Approve at least one post first.'); return; }
  const btn = document.querySelector('.submit-btn');
  btn.textContent = 'Sending to Buffer...'; btn.disabled = true;
  const payload = approved.map(i=>({index:i, content:document.getElementById('tx-'+i).value}));
  try {
    const r = await fetch('/approve/'+token, {
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({approved_posts: payload})
    });
    const d = await r.json();
    if (d.success) {
      document.getElementById('success').style.display='block';
      document.getElementById('success').scrollIntoView({behavior:'smooth'});
      btn.textContent = '✅ '+d.scheduled+' posts scheduled!';
      btn.style.background = '#06d6a0';
    } else {
      btn.textContent='Error — try again'; btn.disabled=false;
      alert('Error: '+(d.error||'unknown'));
    }
  } catch(e) {
    btn.textContent='Error — try again'; btn.disabled=false;
    alert('Network error: '+e.message);
  }
}
for(let i=0;i<N;i++) cc(i);
</script>
</body>
</html>"""


# ── Routes ────────────────────────────────────────────────────────────────────

@app.route("/health")
def health():
    return jsonify({"status": "ok", "time": datetime.now().isoformat()})


@app.route("/reviews")
def list_reviews():
    """List all pending review links. Open this if approval email didn't arrive."""
    secret = request.args.get("secret", "")
    if not hmac.compare_digest(secret, SECRET_KEY):
        return jsonify({"error": "Pass ?secret=YOUR_APPROVAL_SECRET"}), 401
    now = datetime.now()
    items = []
    for token, stored in pending_reviews.items():
        data       = stored["data"]
        expires_at = stored.get("expires_at", "")
        items.append({
            "week":       data.get("week"),
            "theme":      data.get("week_theme", ""),
            "posts":      len(data.get("posts", [])),
            "review_url": f"{get_base_url()}/review/{token}",
            "expires_at": expires_at,
        })
    return jsonify({"pending": len(items), "reviews": items})


@app.route("/input/<int:week>", methods=["GET"])
def input_form(week):
    from src.config import WEEK_THEMES, LEARNING_QUESTIONS
    tuesday_start = request.args.get("tuesday_start", "false").lower() == "true"
    theme     = WEEK_THEMES.get(week, f"Week {week}")
    questions = LEARNING_QUESTIONS.get(week, [
        "What did you learn this week?",
        "What clicked or surprised you?",
        "What did you build or ship?",
    ])
    today = datetime.now().strftime("%A, %B %d")
    return render_template_string(
        INPUT_HTML,
        week=week, theme=theme, questions=questions,
        today=today, tuesday_start=tuesday_start
    )


@app.route("/input/<int:week>", methods=["POST"])
def input_submit(week):
    body          = request.get_json()
    notes         = (body or {}).get("notes", "").strip()
    tuesday_start = (body or {}).get("tuesday_start", False)
    if not notes:
        return jsonify({"error": "No notes provided"}), 400
    t = threading.Thread(target=generate_and_store, args=(week, notes, tuesday_start), daemon=True)
    t.start()
    return jsonify({"success": True, "message": "Generating posts — check email in 3-5 min"})


@app.route("/submit-posts", methods=["POST"])
def submit_posts():
    auth = request.headers.get("X-Secret", "")
    if not hmac.compare_digest(auth, SECRET_KEY):
        return jsonify({"error": "Unauthorized"}), 401
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data"}), 400

    token      = str(uuid.uuid4()).replace("-", "")[:24]
    expires_at = datetime.now() + timedelta(hours=48)
    pending_reviews[token] = {"data": data, "expires_at": expires_at.isoformat()}

    week     = data.get("week", "?")
    posts    = data.get("posts", [])
    to_email = os.getenv("NOTIFY_EMAIL", "mahesh.annapureddy5@gmail.com")
    sent     = send_review_email(to_email, token, week, posts)

    return jsonify({
        "success":    True,
        "token":      token,
        "review_url": f"{get_base_url()}/review/{token}",
        "email_sent": sent,
        "expires_at": expires_at.isoformat(),
    })


@app.route("/review/<token>")
def review_page(token):
    if token not in pending_reviews:
        return "<h2 style='font-family:sans-serif;padding:40px'>Link expired or invalid.</h2>", 404
    stored = pending_reviews[token]
    data   = stored["data"]
    return render_template_string(
        REVIEW_HTML,
        posts        = data.get("posts", []),
        week         = data.get("week", "?"),
        theme        = data.get("week_theme", "AI Infrastructure"),
        generated_at = data.get("generated_at", "")[:10],
        token        = token,
    )


@app.route("/approve/<token>", methods=["POST"])
def approve_posts(token):
    if token not in pending_reviews:
        return jsonify({"error": "Link expired or invalid"}), 404
    body       = request.get_json()
    approved   = body.get("approved_posts", [])
    if not approved:
        return jsonify({"error": "No posts approved"}), 400

    all_posts = pending_reviews[token]["data"].get("posts", [])
    scheduled, errors = 0, []

    for item in approved:
        idx     = item["index"]
        content = item["content"]
        if idx >= len(all_posts):
            continue
        sdt = all_posts[idx].get("scheduled_datetime", "")
        if not sdt:
            errors.append(f"Post {idx+1}: no scheduled_datetime")
            continue
        result = schedule_to_buffer(content, sdt)
        if result["success"]:
            scheduled += 1
        else:
            errors.append(f"Post {idx+1}: {result.get('error','unknown')}")

    if scheduled > 0:
        del pending_reviews[token]

    return jsonify({"success": scheduled > 0, "scheduled": scheduled, "errors": errors})


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    port  = int(os.getenv("PORT", 5000))
    debug = os.getenv("FLASK_ENV") == "development"
    print(f"Approval server on port {port} | {get_base_url()}")
    app.run(host="0.0.0.0", port=port, debug=debug)
