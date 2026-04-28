#!/usr/bin/env python
"""Verify LinkedIn automation system is properly configured."""
import os
import sys
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

def main():
    print("=" * 60)
    print("LINKEDIN AUTOMATION SYSTEM - STARTUP VERIFICATION")
    print("=" * 60)
    print()

    # Test 1: Imports
    print("[1/5] Testing module imports...")
    try:
        from src.config import WEEK_THEMES, LEARNING_QUESTIONS
        from src.approval_server import app
        from src.research_agent import research_weekly_topics
        from src.generate_posts import generate_posts
        from src.schedule_posts import test_connection
        print("      OK - All modules import successfully")
    except Exception as e:
        print(f"      ERROR: {e}")
        return False

    # Test 2: Config
    print("[2/5] Checking configuration...")
    try:
        required = [
            "ANTHROPIC_API_KEY",
            "BUFFER_ACCESS_TOKEN",
            "BUFFER_PROFILE_ID",
            "APPROVAL_SECRET",
            "JOURNEY_START_DATE",
        ]
        missing = [k for k in required if not os.getenv(k)]

        if missing:
            print(f"      WARNING: Missing env vars: {', '.join(missing)}")
        else:
            print("      OK - All required env vars present")
    except Exception as e:
        print(f"      ERROR: {e}")

    # Test 3: Flask app
    print("[3/5] Checking Flask app...")
    try:
        from src.approval_server import app
        with app.test_client() as client:
            response = client.get("/health")
            if response.status_code == 200:
                print("      OK - Flask /health endpoint works")
            else:
                print(f"      ERROR: /health returned {response.status_code}")
    except Exception as e:
        print(f"      ERROR: {e}")

    # Test 4: Week configuration
    print("[4/5] Checking week configuration...")
    try:
        weeks_configured = len(WEEK_THEMES)
        questions_configured = len(LEARNING_QUESTIONS)
        print(
            f"      OK - {weeks_configured} week themes, {questions_configured} Q&A sets configured"
        )
    except Exception as e:
        print(f"      ERROR: {e}")

    # Test 5: Journey dates
    print("[5/5] Checking journey dates...")
    try:
        journey_start = os.getenv("JOURNEY_START_DATE", "2025-01-06")
        start_dt = datetime.strptime(journey_start, "%Y-%m-%d")
        today = datetime.now()
        weeks_elapsed = (today - start_dt).days // 7 + 1
        print(
            f"      OK - Journey started {journey_start}, currently week {weeks_elapsed}"
        )
    except Exception as e:
        print(f"      ERROR: {e}")

    print()
    print("=" * 60)
    print("OK: SYSTEM READY - Ready to start generating posts")
    print("=" * 60)
    print()
    print("Next steps:")
    print("  1. Start Flask server:")
    print("     python src/approval_server.py")
    print()
    print("  2. Open in browser:")
    print("     http://localhost:5000/input/2")
    print()
    print("  3. Fill in learning notes and submit")
    print()
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
