"""
auto_run.py
-----------
Step 1 of weekly pipeline: send learning input email.
GitHub Actions runs this every Sunday 9 AM Toronto time.

Flow:
  1. Calculate which week we are on (from JOURNEY_START_DATE)
  2. Send Email 1: "What did you learn this week?" with form link
  3. Mahesh fills form (3-5 min)
  4. approval_server receives notes, triggers Steps 2-3 in background:
     - DeepSeek ranks trending topics
     - Kimi generates posts from notes + research
     - Claude Haiku refines, Claude Sonnet + GPT-4o create variants + scores
     - Sends Email 2: approval link with 3-version review UI
"""

import os
import sys
import logging
import argparse
from datetime import datetime, date
from src.config import (
    JOURNEY_START_DATE, WEEK_THEMES, LEARNING_QUESTIONS,
    NOTIFY_EMAIL,
)
from src.email_utils import send_email

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("auto_run.log", mode="a")
    ]
)
log = logging.getLogger(__name__)


def get_base_url() -> str:
    return os.getenv("BASE_URL", "http://localhost:5000").rstrip('/')


def calculate_week() -> int:
    try:
        start = date.fromisoformat(JOURNEY_START_DATE)
    except ValueError:
        return 2
    elapsed = (date.today() - start).days
    return max(2, min(9, (elapsed // 7) + 1))


def send_learning_input_email(week: int) -> bool:
    """Send Email 1: What did you learn this week? Contains the form link."""
    theme = WEEK_THEMES.get(week, f"Week {week}")
    questions = LEARNING_QUESTIONS.get(week, [
        "What did you learn this week?",
        "What clicked or surprised you?",
        "What did you build or ship?",
    ])
    input_url = f"{get_base_url()}/input/{week}"

    questions_html = "".join(
        f'<div style="background:#1e293b;border-left:3px solid #3b82f6;'
        f'padding:12px 16px;margin-bottom:10px;border-radius:0 6px 6px 0;">'
        f'<p style="color:#94a3b8;font-size:12px;margin:0 0 4px;font-family:monospace">Q{i}</p>'
        f'<p style="color:#e2e8f0;font-size:14px;margin:0">{q}</p></div>'
        for i, q in enumerate(questions, 1)
    )

    html = f"""
<html><body style="font-family:-apple-system,sans-serif;max-width:600px;
margin:0 auto;padding:20px;background:#0a0f1e;color:#e2e8f0;">

<div style="background:linear-gradient(135deg,#0f2044,#0a1628);padding:28px;
border-radius:12px;margin-bottom:20px;border:1px solid #1e3a5f;">
  <h1 style="color:#60a5fa;margin:0 0 6px;font-size:20px;">
    📚 Week {week}: What did you learn?
  </h1>
  <p style="color:#64748b;margin:0;font-size:13px;font-family:monospace">
    {theme} · {datetime.now().strftime('%A, %B %d')}
  </p>
</div>

<p style="color:#94a3b8;font-size:14px;line-height:1.7;margin-bottom:20px;">
  Before generating your LinkedIn posts, share what you learned this week.
  Your specific answers make the posts authentic. Takes 3-5 minutes.
</p>

<div style="margin-bottom:24px;">
  {questions_html}
</div>

<div style="text-align:center;margin:28px 0;">
  <a href="{input_url}"
     style="background:linear-gradient(135deg,#3b82f6,#06d6a0);color:white;
     padding:15px 38px;border-radius:8px;text-decoration:none;font-size:15px;
     font-weight:700;display:inline-block;">
    ✍️ Share What You Learned →
  </a>
</div>

<p style="color:#475569;font-size:12px;line-height:1.6;">
  After you submit:<br>
  1. DeepSeek ranks trending AI/infra topics<br>
  2. Kimi generates posts from your notes + research<br>
  3. Claude Sonnet + GPT-4o create 3 versions + scores per post<br>
  4. Emails you an approval link (3-5 minutes)
</p>

<p style="color:#334155;font-size:12px;border-top:1px solid #1e293b;
padding-top:14px;margin-top:16px;">
  Link expires in 12 hours. Miss it? Trigger manually from GitHub Actions.
</p>
</body></html>
"""

    ok = send_email(NOTIFY_EMAIL, f"📚 Week {week} LinkedIn — What did you learn this week?", html)
    if ok:
        log.info(f"Learning input email sent to {NOTIFY_EMAIL}")
    else:
        log.error("Email failed — check RESEND_API_KEY (Railway) or SMTP_EMAIL/SMTP_PASSWORD")
    return ok


def run(week: int = None, dry_run: bool = False):
    log.info("=" * 55)
    log.info("STEP 1: SEND LEARNING INPUT EMAIL")
    log.info(datetime.now().strftime("%A %B %d %Y %I:%M %p"))
    log.info("=" * 55)

    if week is None:
        week = calculate_week()

    log.info(f"Week {week}: {WEEK_THEMES.get(week, '')}")

    if dry_run:
        log.info(f"[DRY RUN] Would send email. Form: {get_base_url()}/input/{week}")
        return

    sent = send_learning_input_email(week)

    if sent:
        log.info("Email sent successfully")
        log.info(f"Learning form: {get_base_url()}/input/{week}")
        log.info("Once you submit notes, posts are generated and approval email follows.")
    else:
        log.error("Email failed — check RESEND_API_KEY (Railway) or SMTP_EMAIL/SMTP_PASSWORD")
        log.info(f"Open the form manually: {get_base_url()}/input/{week}")

    log.info("=" * 55)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Send learning input email")
    parser.add_argument("--week", type=int)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    run(args.week, args.dry_run)
