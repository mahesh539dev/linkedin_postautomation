"""
auto_run.py
-----------
Step 1 of weekly pipeline: send week-selection email.
GitHub Actions runs this every Sunday 9 AM Toronto time.

Flow:
  1. Calculate current week from JOURNEY_START_DATE
  2. Send Email 1: "Which week are you on?" with clickable week buttons
  3. User clicks their week → /select-week/<week> on Railway
  4. Railway generates dynamic questions via DeepSeek + roadmap doc
  5. Sends Email 2: questions + link to answer form
  6. User answers → generation pipeline runs
  7. Sends Email 3: approval link with 3-version review UI
"""

import os
import sys
import logging
import argparse
from datetime import datetime, date
from src.config import JOURNEY_START_DATE, NOTIFY_EMAIL
from src.email_utils import send_email

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
log = logging.getLogger(__name__)


def get_base_url() -> str:
    return os.getenv("BASE_URL", "http://localhost:5000").rstrip("/")


def calculate_week() -> int:
    try:
        start = date.fromisoformat(JOURNEY_START_DATE)
    except ValueError:
        return 2
    elapsed = (date.today() - start).days
    return max(2, min(12, (elapsed // 7) + 1))


def send_week_selection_email(suggested_week: int) -> bool:
    """
    Email 1: Ask which week the user is on.
    Each week button links to /select-week/<week> which generates
    dynamic questions and sends Email 2.
    """
    base = get_base_url()

    week_buttons = ""
    for w in range(2, 13):
        is_suggested = w == suggested_week
        bg = "background:linear-gradient(135deg,#3b82f6,#06d6a0)" if is_suggested else "background:#1e293b"
        border = "border:2px solid #3b82f6" if is_suggested else "border:1px solid #1e3a5f"
        label = f"Week {w}" + (" ← suggested" if is_suggested else "")
        week_buttons += (
            f'<a href="{base}/select-week/{w}" '
            f'style="{bg};{border};color:white;padding:10px 18px;border-radius:8px;'
            f'text-decoration:none;font-size:13px;font-weight:600;display:inline-block;margin:4px">'
            f"{label}</a>"
        )

    html = f"""<html><body style="font-family:-apple-system,sans-serif;max-width:600px;
margin:0 auto;padding:20px;background:#0a0f1e;color:#e2e8f0">

<div style="background:linear-gradient(135deg,#0f2044,#0a1628);padding:28px;
border-radius:12px;margin-bottom:20px;border:1px solid #1e3a5f">
  <h1 style="color:#60a5fa;margin:0 0 6px;font-size:20px">📅 Which week are you on?</h1>
  <p style="color:#64748b;margin:0;font-size:13px;font-family:monospace">
    {datetime.now().strftime('%A, %B %d')} · LinkedIn Post Automation
  </p>
</div>

<p style="color:#94a3b8;font-size:14px;line-height:1.7;margin-bottom:24px">
  Click your current learning week. We'll generate tailored questions based on
  your roadmap for that week, then send them to you in a follow-up email.
</p>

<div style="text-align:center;margin-bottom:28px;line-height:2">
  {week_buttons}
</div>

<p style="color:#475569;font-size:12px;line-height:1.7;border-top:1px solid #1e293b;padding-top:14px">
  After you click:<br>
  1. DeepSeek generates 5 questions specific to that week's content<br>
  2. You get a second email with the questions + answer form link<br>
  3. Answer them (3–5 min) → posts are generated → approval email follows
</p>
</body></html>"""

    ok = send_email(NOTIFY_EMAIL, "📅 LinkedIn posts — which week are you on?", html)
    if ok:
        log.info(f"Week-selection email sent to {NOTIFY_EMAIL} (suggested week {suggested_week})")
    else:
        log.error("Email failed — check RESEND_API_KEY (Railway) or SMTP_EMAIL/SMTP_PASSWORD")
    return ok


def run(week: int = None, dry_run: bool = False):
    log.info("=" * 55)
    log.info("STEP 1: SEND WEEK SELECTION EMAIL")
    log.info(datetime.now().strftime("%A %B %d %Y %I:%M %p"))
    log.info("=" * 55)

    suggested = week if week is not None else calculate_week()
    log.info(f"Suggested week: {suggested}")

    if dry_run:
        log.info(f"[DRY RUN] Would send week-selection email (suggested week {suggested})")
        return

    sent = send_week_selection_email(suggested)
    if sent:
        log.info("Week-selection email sent. Waiting for user to click a week.")
    else:
        log.error("Email failed — open manually:")
        for w in range(2, 13):
            log.info(f"  Week {w}: {get_base_url()}/select-week/{w}")

    log.info("=" * 55)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Send week-selection email")
    parser.add_argument("--week", type=int, help="Override suggested week")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    run(args.week, args.dry_run)
