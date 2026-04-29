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
import threading
import requests
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from flask import Flask, request, jsonify, render_template_string, redirect
from dotenv import load_dotenv
from src.email_utils import send_email

load_dotenv()

app = Flask(__name__)

SECRET_KEY      = os.getenv("APPROVAL_SECRET", "change-me")
BUFFER_GRAPHQL  = "https://api.buffer.com/graphql"

# week → dynamically generated questions (populated by /select-week/<week>)
pending_questions: dict[int, list[str]] = {}

def get_base_url():
    return os.getenv("BASE_URL", "http://localhost:5000").rstrip('/')

# In-memory store: token → {data, expires_at}
pending_reviews = {}


# ── Buffer ────────────────────────────────────────────────────────────────────

def _buffer_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def _buffer_gql(token: str, query: str, variables: dict = None) -> requests.Response:
    body = {"query": query}
    if variables:
        body["variables"] = variables
    return requests.post(BUFFER_GRAPHQL, headers=_buffer_headers(token), json=body, timeout=15)


def schedule_to_buffer(content: str, scheduled_datetime: str) -> dict:
    token      = os.getenv("BUFFER_ACCESS_TOKEN")
    channel_id = os.getenv("BUFFER_PROFILE_ID")
    if not token or not channel_id:
        return {"success": False, "error": "BUFFER_ACCESS_TOKEN or BUFFER_PROFILE_ID not set in Railway env vars"}

    # scheduled_datetime is in America/Toronto (EST/EDT); convert to UTC for Buffer
    dt_local = datetime.strptime(scheduled_datetime, "%Y-%m-%d %H:%M:%S").replace(
        tzinfo=ZoneInfo("America/Toronto")
    )
    due_at = dt_local.astimezone(ZoneInfo("UTC")).strftime("%Y-%m-%dT%H:%M:%S.000Z")

    mutation = """
    mutation CreatePost($input: CreatePostInput!) {
      createPost(input: $input) {
        ... on PostActionSuccess { post { id dueAt } }
        ... on MutationError { message }
      }
    }
    """
    variables = {
        "input": {
            "text":           content,
            "channelId":      channel_id,
            "schedulingType": "automatic",
            "mode":           "customScheduled",
            "dueAt":          due_at,
        }
    }

    try:
        r = _buffer_gql(token, mutation, variables)
    except Exception as e:
        return {"success": False, "error": str(e)}

    try:
        data = r.json()
    except Exception:
        return {"success": False, "error": f"HTTP {r.status_code}: {r.text[:300]}"}

    gql_errors = data.get("errors")
    if gql_errors:
        msg = "; ".join(e.get("message", str(e)) for e in gql_errors)
        return {"success": False, "error": msg}

    result = (data.get("data") or {}).get("createPost", {})
    if "post" in result:
        return {"success": True, "id": result["post"].get("id")}
    if "message" in result:
        return {"success": False, "error": result["message"]}
    return {"success": False, "error": f"Unexpected response: {str(data)[:300]}"}


# ── Email ─────────────────────────────────────────────────────────────────────

def send_review_email(to_email: str, review_token: str, week: int, posts: list) -> bool:
    review_url = f"{get_base_url()}/review/{review_token}"
    type_icons = {"industry_news": "📰", "bridge": "🌉", "industry_trend": "📈",
                  "model_comparison": "⚖️", "opinion": "💡",
                  "learning": "🎓", "build_in_public": "🏗️"}

    previews = ""
    for p in posts:
        versions = p.get("versions", [])
        if versions:
            best = max(versions, key=lambda v: v.get("score", 0))
            content   = best.get("content", p.get("content", ""))
            score     = best.get("score", 0)
            score_str = f" [{score}/100]" if score > 0 else ""
            ver_str   = f" · {best.get('label', 'V1')}"
        else:
            content   = p.get("content", "")
            score_str = ""
            ver_str   = ""
        previews += (
            f"\n  {type_icons.get(p.get('type',''),'📌')} "
            f"{p.get('schedule_day')} {p.get('schedule_time')} — {p.get('type','').upper()}{ver_str}{score_str}\n"
            f"  \"{content[:100]}...\"\n"
        )

    html = f"""<html><body style="font-family:sans-serif;max-width:600px;margin:0 auto;padding:20px">
<h2 style="color:#3b82f6">LinkedIn Week {week} — Review Ready</h2>
<p>{len(posts)} posts generated in 3 versions each (Kimi, Claude, OpenAI) with scores. Your approval needed before they go to Buffer.</p>
<pre style="background:#f1f5f9;padding:16px;border-radius:8px;font-size:13px">{previews}</pre>
<div style="text-align:center;margin:28px 0">
  <a href="{review_url}" style="background:#3b82f6;color:white;padding:14px 36px;
     border-radius:8px;text-decoration:none;font-size:15px;font-weight:700">
    Review &amp; Approve Posts →
  </a>
</div>
<p style="color:#64748b;font-size:12px">Link expires in 48 hours.</p>
</body></html>"""

    return send_email(to_email, f"✍️ LinkedIn Week {week}: posts ready for review", html)


# ── Background generation ─────────────────────────────────────────────────────

def generate_and_store(week: int, notes: str):
    """Run research → generation → variants → store token → email user."""
    try:
        from src.research_agent import research_weekly_topics
        from src.generate_posts import generate_posts

        print(f"[Week {week}] Starting web research...")
        research = research_weekly_topics(week, save=True)
        print(f"[Week {week}] Research complete — {len(research.get('topics', []))} topics")

        data = generate_posts(week, research, notes, save=True)

        try:
            from src.refinement import refine_posts
            data["posts"] = refine_posts(data["posts"])
        except Exception as e:
            print(f"ERROR: Refinement step failed — {e}")
            print("Continuing with unrefined posts")

        try:
            from src.post_variants import create_variants
            data["posts"] = create_variants(data["posts"])
        except Exception as e:
            print(f"ERROR: Variant generation failed — {e}")
            print("Continuing with single version — check ANTHROPIC_API_KEY and OPENAI_API_KEY")

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
            print("Check RESEND_API_KEY (Railway) or SMTP_EMAIL/SMTP_PASSWORD")
        print("=" * 60)

    except Exception as e:
        import traceback
        print("=" * 60)
        print(f"GENERATION FAILED — Week {week}: {e}")
        print(traceback.format_exc())
        print("=" * 60)


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

  <div>{% for q in questions %}
    <div class="q"><p>Q{{ loop.index }}</p><span>{{ q }}</span></div>
  {% endfor %}</div>

  <form id="form">
    <textarea id="notes" placeholder="Answer the questions above in any order. Be specific — numbers, tool names, what surprised you, what you built."></textarea>
    <button type="submit" id="btn">✍️ Generate My Posts →</button>
  </form>

  <div class="done" id="done">
    <h2>Generating your posts...</h2>
    <p>DeepSeek is researching topics · Kimi is writing posts · Claude + OpenAI are creating variants.<br>
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
        body: JSON.stringify({notes})
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
    .container{max-width:860px;margin:0 auto;padding:32px 20px}
    .card{background:#111827;border:1px solid #1e3a5f;border-radius:12px;
          margin-bottom:22px;overflow:hidden;transition:border-color .2s}
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
    .type-model_comparison{background:rgba(16,185,129,.2);color:#34d399;border:1px solid rgba(16,185,129,.3)}
    .type-build_in_public{background:rgba(249,115,22,.2);color:#fb923c;border:1px solid rgba(249,115,22,.3)}
    .type-learning{background:rgba(245,158,11,.2);color:#fbbf24;border:1px solid rgba(245,158,11,.3)}
    .type-opinion{background:rgba(239,68,68,.2);color:#f87171;border:1px solid rgba(239,68,68,.3)}
    .sched{margin-left:auto;font-family:monospace;font-size:12px;color:#64748b}
    .st{font-size:12px;font-weight:600;padding:4px 12px;border-radius:10px}
    .st-pending{background:rgba(100,116,139,.2);color:#64748b}
    .st-approved{background:rgba(6,214,160,.2);color:#06d6a0}
    .st-rejected{background:rgba(239,68,68,.2);color:#ef4444}
    /* Version tabs */
    .ver-tabs{display:flex;gap:3px;padding:10px 18px 0;background:#0d1a2d;
              border-bottom:1px solid #1e3a5f;flex-wrap:wrap}
    .ver-tab{padding:7px 14px;border-radius:8px 8px 0 0;font-size:12px;font-weight:600;
             cursor:pointer;border:1px solid #1e3a5f;border-bottom:none;
             background:#1a2234;color:#64748b;font-family:inherit;
             display:inline-flex;align-items:center;gap:6px;transition:all .15s}
    .ver-tab:hover{color:#94a3b8;background:#1e293b}
    .ver-tab.active{background:#111827;color:#e2e8f0;border-color:#3b82f6}
    .ver-tab.best-ver{border-color:#fbbf24 !important}
    .vscore{font-family:monospace;font-size:11px;padding:2px 7px;border-radius:10px;
            background:rgba(255,255,255,.08);font-weight:700}
    .s-good{color:#06d6a0}
    .s-ok{color:#fbbf24}
    .s-bad{color:#ef4444}
    .s-none{color:#64748b}
    .breakdown-row{padding:7px 18px;background:#0d1a2d;min-height:26px;
                   border-bottom:1px solid #1e3a5f;line-height:1.8;font-size:11px}
    .card-body{padding:18px}
    .post-title{font-size:13px;color:#94a3b8;margin-bottom:10px;font-style:italic}
    textarea{width:100%;min-height:160px;background:rgba(0,0,0,.35);
             border:1px solid #1e3a5f;border-radius:8px;padding:12px 14px;
             color:#e2e8f0;font-size:14px;line-height:1.7;resize:vertical;outline:none}
    textarea:focus{border-color:#3b82f6}
    .chars{font-family:monospace;font-size:11px;color:#64748b;text-align:right;margin-top:4px}
    .card-actions{padding:12px 18px;border-top:1px solid #1e3a5f;display:flex;gap:8px;align-items:center;flex-wrap:wrap}
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
    ⚡ Each post has 3 AI versions — tabs show scores. Best version is pre-selected.
    Edit directly · approve the version you like · reject the rest.
  </div>

{% for post in posts %}
{% set pi = loop.index0 %}
  <div class="card" id="card-{{ pi }}">
    <div class="card-head">
      <span class="num">Post {{ loop.index }}</span>
      <span class="type type-{{ post.type }}">{{ post.type.replace('_',' ') }}</span>
      <span class="sched">{{ post.schedule_day }} · {{ post.schedule_time }}</span>
      <span class="st st-pending" id="st-{{ pi }}">Pending</span>
    </div>

    {% if post.versions %}
    <div class="ver-tabs" id="tabs-{{ pi }}">
      {% for v in post.versions %}
      {% set vi = loop.index0 %}
      <button class="ver-tab{% if vi == 0 %} active{% endif %}"
              id="vtab-{{ pi }}-{{ vi }}"
              onclick="switchVer({{ pi }}, {{ vi }})">
        {{ v.label }}
        {% if v.score and v.score > 0 %}
        <span class="vscore {% if v.score >= 80 %}s-good{% elif v.score >= 60 %}s-ok{% else %}s-bad{% endif %}">{{ v.score }}</span>
        {% endif %}
      </button>
      {% endfor %}
    </div>
    <div class="breakdown-row" id="bd-{{ pi }}"></div>
    {% endif %}

    <div class="card-body">
      <div class="post-title">{{ post.title }}</div>
      <textarea id="tx-{{ pi }}" oninput="cc({{ pi }})">{{ post.content }}</textarea>
      <div class="chars" id="ch-{{ pi }}"></div>
    </div>
    <div class="card-actions">
      <button class="btn btn-a" onclick="approve({{ pi }})">✓ Approve</button>
      <button class="btn btn-r" onclick="reject({{ pi }})">✗ Reject</button>
      <button class="btn btn-u" id="undo-{{ pi }}" onclick="undo({{ pi }})">↩ Undo</button>
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
const verData = {{ versions_js | safe }};
const s = new Array(N).fill('pending');
const activeVer = new Array(N).fill(0);
const approvedVer = new Array(N).fill('V1');

const BREAKDOWN_MAX = {hook:20, specificity:20, insight:20, voice:15, backend:10, engagement:10, format:5};
const BREAKDOWN_LABEL = {hook:'Hook', specificity:'Spec', insight:'Insight', voice:'Voice', backend:'Backend', engagement:'Engage', format:'Format'};

function scoreColor(score) {
  if (!score || score <= 0) return '#64748b';
  if (score >= 80) return '#06d6a0';
  if (score >= 60) return '#fbbf24';
  return '#ef4444';
}

function updateBreakdown(pi, vi) {
  const el = document.getElementById('bd-' + pi);
  if (!el) return;
  const ver = verData[pi] && verData[pi][vi];
  if (!ver || !ver.breakdown || !Object.keys(ver.breakdown).length) {
    el.innerHTML = '';
    return;
  }
  const parts = Object.entries(ver.breakdown).map(([k, val]) => {
    const max = BREAKDOWN_MAX[k] || 10;
    const color = scoreColor(Math.round((val / max) * 100));
    return `<span style="color:${color}">${BREAKDOWN_LABEL[k]||k}:${val}/${max}</span>`;
  });
  el.innerHTML = parts.join('<span style="color:#1e3a5f"> · </span>');
}

function switchVer(pi, vi) {
  const versions = verData[pi];
  if (!versions || !versions[vi]) return;
  activeVer[pi] = vi;
  approvedVer[pi] = versions[vi].label || ('V' + (vi + 1));
  document.getElementById('tx-' + pi).value = versions[vi].content;
  cc(pi);
  const tabsEl = document.getElementById('tabs-' + pi);
  if (tabsEl) {
    tabsEl.querySelectorAll('.ver-tab').forEach((tab, j) => {
      tab.classList.toggle('active', j === vi);
    });
  }
  updateBreakdown(pi, vi);
}

function cc(i) {
  const l = document.getElementById('tx-' + i).value.length;
  document.getElementById('ch-' + i).textContent = l + ' chars';
}

function badge() {
  const a = s.filter(x => x === 'approved').length;
  document.getElementById('cnt').textContent = a + ' / ' + N + ' approved';
  document.getElementById('info').textContent =
    a === 0 ? 'Approve posts above, then submit' : a + ' post' + (a > 1 ? 's' : '') + ' ready to schedule';
}

function approve(i) {
  const verLabel = verData[i] && verData[i][activeVer[i]] ? verData[i][activeVer[i]].label : 'V1';
  approvedVer[i] = verLabel;
  s[i] = 'approved';
  document.getElementById('card-' + i).className = 'card approved';
  const st = document.getElementById('st-' + i);
  st.className = 'st st-approved';
  st.textContent = '✓ ' + verLabel;
  document.getElementById('undo-' + i).style.display = 'inline-block';
  badge();
}

function reject(i) {
  s[i] = 'rejected';
  document.getElementById('card-' + i).className = 'card rejected';
  const st = document.getElementById('st-' + i);
  st.className = 'st st-rejected';
  st.textContent = '✗ Rejected';
  document.getElementById('undo-' + i).style.display = 'inline-block';
  badge();
}

function undo(i) {
  s[i] = 'pending';
  document.getElementById('card-' + i).className = 'card';
  const st = document.getElementById('st-' + i);
  st.className = 'st st-pending';
  st.textContent = 'Pending';
  document.getElementById('undo-' + i).style.display = 'none';
  badge();
}

async function submitAll() {
  const approved = s.map((v, i) => v === 'approved' ? i : -1).filter(i => i >= 0);
  if (!approved.length) { alert('Approve at least one post first.'); return; }
  const btn = document.querySelector('.submit-btn');
  btn.textContent = 'Sending to Buffer...';
  btn.disabled = true;
  const payload = approved.map(i => ({
    index: i,
    content: document.getElementById('tx-' + i).value,
    version_label: approvedVer[i] || 'V1'
  }));
  try {
    const r = await fetch('/approve/' + token, {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({approved_posts: payload})
    });
    const d = await r.json();
    if (d.success) {
      document.getElementById('success').style.display = 'block';
      document.getElementById('success').scrollIntoView({behavior: 'smooth'});
      btn.textContent = '✅ ' + d.scheduled + ' posts scheduled!';
      btn.style.background = '#06d6a0';
    } else {
      btn.textContent = 'Error — try again';
      btn.disabled = false;
      alert('Error: ' + (d.error || 'unknown'));
    }
  } catch(e) {
    btn.textContent = 'Error — try again';
    btn.disabled = false;
    alert('Network error: ' + e.message);
  }
}

// Mark best-scoring tab with gold border
function markBestTab(pi) {
  const versions = verData[pi];
  if (!versions || versions.length < 2) return;
  let best = 0;
  for (let j = 1; j < versions.length; j++) {
    if ((versions[j].score || 0) > (versions[best].score || 0)) best = j;
  }
  const tab = document.getElementById('vtab-' + pi + '-' + best);
  if (tab) tab.classList.add('best-ver');
  return best;
}

// Initialize: switch each post to its best-scoring version
for (let i = 0; i < N; i++) {
  cc(i);
  if (!verData[i] || verData[i].length === 0) continue;
  const best = markBestTab(i);
  if (best > 0) {
    switchVer(i, best);
  } else {
    updateBreakdown(i, 0);
  }
}
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
    items = []
    for token, stored in pending_reviews.items():
        data = stored["data"]
        items.append({
            "week":       data.get("week"),
            "theme":      data.get("week_theme", ""),
            "posts":      len(data.get("posts", [])),
            "review_url": f"{get_base_url()}/review/{token}",
            "expires_at": stored.get("expires_at", ""),
        })
    return jsonify({"pending": len(items), "reviews": items})


@app.route("/select-week/<int:week>")
def select_week(week):
    """
    Called when user clicks a week button in Email 1.
    Generates dynamic questions via OpenRouter, stores them, sends Email 2,
    and shows a confirmation page.
    """
    from src.roadmap import generate_questions, WEEK_CONTENT
    to_email = os.getenv("NOTIFY_EMAIL", "")
    topic    = WEEK_CONTENT.get(week, f"Week {week}")

    try:
        print(f"[Week {week}] Generating questions via DeepSeek...")
        questions = generate_questions(week)
        pending_questions[week] = questions
        print(f"[Week {week}] Generated {len(questions)} questions")
    except Exception as e:
        import traceback
        print(f"ERROR: Question generation failed for week {week} — {e}")
        print(traceback.format_exc())
        return f"<h2 style='font-family:sans-serif;padding:40px;color:#ef4444'>" \
               f"Question generation failed: {e}<br>Check Railway logs.</h2>", 500

    # Send Email 2 — questions email
    form_url  = f"{get_base_url()}/input/{week}"
    q_html    = "".join(
        f'<div style="background:#1e293b;border-left:3px solid #3b82f6;padding:12px 16px;'
        f'margin-bottom:10px;border-radius:0 6px 6px 0">'
        f'<p style="color:#94a3b8;font-size:12px;margin:0 0 4px;font-family:monospace">Q{i}</p>'
        f'<p style="color:#e2e8f0;font-size:14px;margin:0">{q}</p></div>'
        for i, q in enumerate(questions, 1)
    )
    html = f"""<html><body style="font-family:-apple-system,sans-serif;max-width:600px;
margin:0 auto;padding:20px;background:#0a0f1e;color:#e2e8f0">
<div style="background:linear-gradient(135deg,#0f2044,#0a1628);padding:28px;
border-radius:12px;margin-bottom:20px;border:1px solid #1e3a5f">
  <h1 style="color:#60a5fa;margin:0 0 6px;font-size:20px">📚 Week {week} Questions</h1>
  <p style="color:#64748b;margin:0;font-size:13px;font-family:monospace">{topic[:80]}</p>
</div>
<p style="color:#94a3b8;font-size:14px;line-height:1.7;margin-bottom:20px">
  Answer these in the form — be specific with numbers, tool names, and what actually happened.
</p>
{q_html}
<div style="text-align:center;margin:28px 0">
  <a href="{form_url}" style="background:linear-gradient(135deg,#3b82f6,#06d6a0);color:white;
  padding:15px 38px;border-radius:8px;text-decoration:none;font-size:15px;font-weight:700;
  display:inline-block">✍️ Answer These Questions →</a>
</div>
<p style="color:#334155;font-size:12px;border-top:1px solid #1e293b;padding-top:14px;margin-top:16px">
  Takes 3–5 minutes. Your notes drive the post quality — be specific.
</p>
</body></html>"""

    sent = send_email(to_email, f"📚 Week {week} — Your learning questions", html)
    if not sent:
        print(f"ERROR: Questions email failed to send for week {week}")

    return f"""<html><body style="font-family:-apple-system,sans-serif;max-width:500px;
margin:80px auto;padding:20px;background:#0a0f1e;color:#e2e8f0;text-align:center">
<h2 style="color:#06d6a0">✓ Questions sent to your email</h2>
<p style="color:#94a3b8">Check <strong>{to_email}</strong> for Week {week} questions.<br>
Click the link in the email to open the answer form.</p>
<p style="margin-top:30px"><a href="{form_url}"
style="color:#60a5fa;font-size:13px">Or open the form directly →</a></p>
</body></html>"""


@app.route("/input/<int:week>", methods=["GET"])
def input_form(week):
    from src.roadmap import WEEK_CONTENT
    theme     = WEEK_CONTENT.get(week, f"Week {week}")
    questions = pending_questions.get(week) or [
        "What specific tools or concepts did you work with this week?",
        "What surprised you or didn't work as expected?",
        "What did you build or implement — and what were the results?",
        "How does what you learned connect to your backend engineering experience?",
        "What's one thing you'd do differently based on this week?",
    ]
    today = datetime.now().strftime("%A, %B %d")
    return render_template_string(
        INPUT_HTML,
        week=week, theme=theme, questions=questions, today=today,
    )


@app.route("/input/<int:week>", methods=["POST"])
def input_submit(week):
    body  = request.get_json()
    notes = (body or {}).get("notes", "").strip()
    if not notes:
        return jsonify({"error": "No notes provided"}), 400
    t = threading.Thread(target=generate_and_store, args=(week, notes), daemon=True)
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
    posts  = data.get("posts", [])
    versions_js = json.dumps([post.get("versions", []) for post in posts])
    return render_template_string(
        REVIEW_HTML,
        posts        = posts,
        week         = data.get("week", "?"),
        theme        = data.get("week_theme", "AI Infrastructure"),
        generated_at = data.get("generated_at", "")[:10],
        token        = token,
        versions_js  = versions_js,
    )


@app.route("/approve/<token>", methods=["POST"])
def approve_posts(token):
    if token not in pending_reviews:
        return jsonify({"error": "Link expired or invalid"}), 404
    body     = request.get_json()
    approved = body.get("approved_posts", [])
    if not approved:
        return jsonify({"error": "No posts approved"}), 400

    all_posts = pending_reviews[token]["data"].get("posts", [])
    scheduled, errors = 0, []

    for item in approved:
        try:
            idx           = item["index"]
            content       = item["content"]
            version_label = item.get("version_label", "V1")
            if idx >= len(all_posts):
                continue
            sdt = all_posts[idx].get("scheduled_datetime", "")
            if not sdt:
                errors.append(f"Post {idx+1}: no scheduled_datetime")
                continue
            result = schedule_to_buffer(content, sdt)
            if result["success"]:
                scheduled += 1
                print(f"  Scheduled post {idx+1} ({version_label}): {sdt}")
            else:
                err = result.get("error", "Buffer API error")
                errors.append(f"Post {idx+1}: {err}")
                print(f"  Buffer error for post {idx+1}: {err}")
        except Exception as e:
            errors.append(f"Post {idx+1}: {e}")
            print(f"  Unexpected error for post {idx+1}: {e}")

    if scheduled > 0:
        del pending_reviews[token]

    error_summary = "; ".join(errors) if errors else None
    return jsonify({
        "success":   scheduled > 0,
        "scheduled": scheduled,
        "errors":    errors,
        "error":     error_summary,
    })


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    port  = int(os.getenv("PORT", 5000))
    debug = os.getenv("FLASK_ENV") == "development"
    print(f"Approval server on port {port} | {get_base_url()}")
    app.run(host="0.0.0.0", port=port, debug=debug)
