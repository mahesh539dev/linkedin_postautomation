"""
email_utils.py
--------------
Send email via Resend HTTP API (Railway-safe) or SMTP fallback (GitHub Actions).

Railway blocks all outgoing SMTP ports, so RESEND_API_KEY must be set there.
SMTP works fine from GitHub Actions or local.
"""

import os
import smtplib
import requests
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


def send_email(to: str, subject: str, html: str, from_name: str = "LinkedIn Bot") -> bool:
    resend_key = os.getenv("RESEND_API_KEY")
    if resend_key:
        return _send_via_resend(resend_key, to, subject, html, from_name)
    return _send_via_smtp(to, subject, html)


def _send_via_resend(api_key: str, to: str, subject: str, html: str, from_name: str) -> bool:
    smtp_email = os.getenv("SMTP_EMAIL", "")
    resend_from = os.getenv("RESEND_FROM_EMAIL", f"{from_name} <onboarding@resend.dev>")
    if smtp_email and "@" in smtp_email:
        domain = smtp_email.split("@")[1]
        # Use your own domain sender if RESEND_FROM_EMAIL is set, else default
        if not os.getenv("RESEND_FROM_EMAIL"):
            resend_from = f"{from_name} <onboarding@resend.dev>"

    try:
        r = requests.post(
            "https://api.resend.com/emails",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={"from": resend_from, "to": [to], "subject": subject, "html": html},
            timeout=15,
        )
        if r.status_code in (200, 201):
            print(f"Email sent via Resend to {to}")
            return True
        print(f"Resend error {r.status_code}: {r.text[:200]}")
        return False
    except Exception as e:
        print(f"Resend request failed: {e}")
        return False


def _send_via_smtp(to: str, subject: str, html: str) -> bool:
    smtp_email    = os.getenv("SMTP_EMAIL")
    smtp_password = os.getenv("SMTP_PASSWORD")
    if not smtp_email or not smtp_password:
        print("No email credentials configured (RESEND_API_KEY or SMTP_EMAIL+SMTP_PASSWORD)")
        return False

    msg = MIMEMultipart("alternative")
    msg["From"]    = smtp_email
    msg["To"]      = to
    msg["Subject"] = subject
    msg.attach(MIMEText(html, "html"))

    # Try port 587 (STARTTLS) first, then 465 (SSL)
    for port, use_ssl in [(587, False), (465, True)]:
        try:
            if use_ssl:
                with smtplib.SMTP_SSL("smtp.gmail.com", port) as s:
                    s.login(smtp_email, smtp_password)
                    s.send_message(msg)
            else:
                with smtplib.SMTP("smtp.gmail.com", port) as s:
                    s.starttls()
                    s.login(smtp_email, smtp_password)
                    s.send_message(msg)
            print(f"Email sent via SMTP:{port} to {to}")
            return True
        except OSError as e:
            if "Network is unreachable" in str(e) or "Connect" in str(e):
                print(f"SMTP port {port} unreachable, trying next...")
                continue
            print(f"SMTP error on port {port}: {e}")
            return False
        except Exception as e:
            print(f"SMTP error on port {port}: {e}")
            return False

    print("All SMTP ports blocked — set RESEND_API_KEY in Railway env vars")
    return False
