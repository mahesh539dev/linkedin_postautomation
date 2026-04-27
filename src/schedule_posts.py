"""
schedule_posts.py
─────────────────
Sends generated posts from a JSON file to Buffer API for scheduling.
Buffer posts them to LinkedIn automatically at the right times.
"""

import json
import os
import sys
import requests
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

BUFFER_API_BASE = "https://api.bufferapp.com/1"


def get_credentials():
    token = os.getenv("BUFFER_ACCESS_TOKEN")
    profile_id = os.getenv("BUFFER_PROFILE_ID")
    if not token:
        raise ValueError("BUFFER_ACCESS_TOKEN not set in .env")
    if not profile_id:
        raise ValueError("BUFFER_PROFILE_ID not set in .env")
    return token, profile_id


def test_connection():
    """Verify Buffer credentials work."""
    token, profile_id = get_credentials()
    url = f"{BUFFER_API_BASE}/profiles/{profile_id}.json"
    response = requests.get(url, params={"access_token": token})
    if response.status_code == 200:
        data = response.json()
        print(f"  ✅ Buffer connected — Profile: {data.get('formatted_username', 'Unknown')}")
        return True
    else:
        print(f"  ❌ Buffer connection failed: {response.status_code}")
        print(f"     {response.text[:200]}")
        return False


def parse_scheduled_time(scheduled_datetime: str) -> int:
    """Convert 'YYYY-MM-DD HH:MM:SS' to Unix timestamp."""
    dt = datetime.strptime(scheduled_datetime, "%Y-%m-%d %H:%M:%S")
    return int(dt.timestamp())


def schedule_post(content: str, scheduled_datetime: str) -> dict:
    """Schedule a single post to Buffer."""
    token, profile_id = get_credentials()
    url = f"{BUFFER_API_BASE}/updates/create.json"
    scheduled_at = parse_scheduled_time(scheduled_datetime)
    payload = {
        "access_token": token,
        "profile_ids[]": profile_id,
        "text": content,
        "scheduled_at": scheduled_at,
        "now": False,
        "shorten": False,
    }
    response = requests.post(url, data=payload)
    if response.status_code == 200:
        data = response.json()
        if data.get("success"):
            return {"success": True, "update_id": data.get("updates", [{}])[0].get("id")}
        return {"success": False, "error": data.get("message", "Unknown error")}
    return {"success": False, "error": f"HTTP {response.status_code}: {response.text[:200]}"}


def schedule_all_posts(posts_file: str, dry_run: bool = False) -> list:
    """Load posts from JSON file and schedule all to Buffer."""
    if not os.path.exists(posts_file):
        raise FileNotFoundError(f"Posts file not found: {posts_file}")

    with open(posts_file) as f:
        data = json.load(f)

    posts = data.get("posts", [])
    week = data.get("week", "?")

    print(f"\n  📤 Scheduling {len(posts)} posts for Week {week}...")
    if dry_run:
        print("     [DRY RUN — not sending to Buffer]\n")

    results = []
    for i, post in enumerate(posts, 1):
        title = post.get("title", f"Post {i}")
        day = post.get("schedule_day", "?")
        time = post.get("schedule_time", "?")
        scheduled_dt = post.get("scheduled_datetime", "")
        content = post.get("content", "")

        print(f"     [{i}/5] {day} {time} — {title}")

        if dry_run:
            print(f"            Would schedule for {scheduled_dt}")
            results.append({"post": title, "success": True, "dry_run": True})
            continue

        if not scheduled_dt:
            print(f"            ⚠️  No scheduled_datetime — skipping")
            results.append({"post": title, "success": False, "error": "No scheduled_datetime"})
            continue

        result = schedule_post(content, scheduled_dt)
        if result["success"]:
            print(f"            ✅ Scheduled (ID: {result.get('update_id', '?')})")
        else:
            print(f"            ❌ Failed: {result.get('error', 'Unknown')}")
        results.append({"post": title, "day": day, **result})

    success_count = sum(1 for r in results if r.get("success"))
    print(f"\n  Results: {success_count}/{len(posts)} scheduled successfully")
    if success_count < len(posts):
        failed = [r["post"] for r in results if not r.get("success")]
        print(f"  Failed: {', '.join(failed)}")
        print(f"  Schedule these manually at publish.buffer.com")

    return results


def get_queued_posts() -> list:
    """List all pending posts in Buffer queue."""
    token, profile_id = get_credentials()
    url = f"{BUFFER_API_BASE}/profiles/{profile_id}/updates/pending.json"
    response = requests.get(url, params={"access_token": token})
    if response.status_code != 200:
        print(f"❌ Could not fetch queue: {response.status_code}")
        return []
    data = response.json()
    updates = data.get("updates", [])
    if not updates:
        print("  Queue is empty.")
        return []
    print(f"\n  📋 Buffer Queue ({len(updates)} posts):\n")
    for u in updates:
        scheduled = u.get("scheduled_at", 0)
        dt = datetime.fromtimestamp(scheduled).strftime("%a %b %d at %I:%M %p") if scheduled else "?"
        preview = u.get("text", "")[:60] + "..."
        print(f"  • {dt}: {preview}")
    return updates


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Schedule posts to Buffer")
    parser.add_argument("--file", type=str)
    parser.add_argument("--week", type=int)
    parser.add_argument("--test", action="store_true", help="Test connection only")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--queue", action="store_true")
    args = parser.parse_args()

    if args.test:
        test_connection()
        sys.exit(0)
    if args.queue:
        get_queued_posts()
        sys.exit(0)

    posts_file = args.file or (f"posts/week_{args.week}.json" if args.week else None)
    if not posts_file:
        print("❌ Specify --file or --week")
        sys.exit(1)

    if not test_connection():
        sys.exit(1)

    schedule_all_posts(posts_file, dry_run=args.dry_run)
