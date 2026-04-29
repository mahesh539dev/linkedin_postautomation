"""
schedule_posts.py
─────────────────
Sends generated posts from a JSON file to Buffer API for scheduling.
Buffer posts them to LinkedIn automatically at the right times.

Auth: personal API key from Buffer → Settings → API
      Set BUFFER_ACCESS_TOKEN in Railway / .env
      Set BUFFER_PROFILE_ID  in Railway / .env  (your LinkedIn profile ID in Buffer)
"""

import json
import os
import sys
import requests
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

BUFFER_GRAPHQL = "https://api.buffer.com/graphql"


def _headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def _gql(token: str, query: str, variables: dict = None) -> requests.Response:
    body = {"query": query}
    if variables:
        body["variables"] = variables
    return requests.post(BUFFER_GRAPHQL, headers=_headers(token), json=body, timeout=15)


def get_credentials():
    token = os.getenv("BUFFER_ACCESS_TOKEN")
    profile_id = os.getenv("BUFFER_PROFILE_ID")
    if not token:
        raise ValueError("BUFFER_ACCESS_TOKEN not set in .env")
    if not profile_id:
        raise ValueError("BUFFER_PROFILE_ID not set in .env")
    return token, profile_id


def test_connection():
    """Verify Buffer credentials and list channels (use id as BUFFER_PROFILE_ID)."""
    token, _ = get_credentials()
    r = _gql(token, "{ channels { id name serviceType } }")
    try:
        data = r.json()
    except Exception:
        print(f"  ❌ Buffer response not JSON: {r.text[:200]}")
        return False
    if r.status_code != 200 or data.get("errors"):
        errs = data.get("errors", [])
        msg  = "; ".join(e.get("message", str(e)) for e in errs) if errs else r.text[:200]
        print(f"  ❌ Buffer connection failed: {msg}")
        return False
    channels = (data.get("data") or {}).get("channels", [])
    for c in channels:
        print(f"  Channel: {c.get('name','?')} — ID: {c.get('id','?')} — type: {c.get('serviceType','?')}")
    print(f"  ✅ Buffer connected ({len(channels)} channels) — use the LinkedIn channel ID as BUFFER_PROFILE_ID")
    return True


def schedule_post(content: str, scheduled_datetime: str) -> dict:
    token, channel_id = get_credentials()
    dt     = datetime.strptime(scheduled_datetime, "%Y-%m-%d %H:%M:%S")
    due_at = dt.strftime("%Y-%m-%dT%H:%M:%S.000Z")

    mutation = """
    mutation CreatePost($input: CreatePostInput!) {
      createPost(input: $input) {
        ... on PostActionSuccess { post { id dueAt } }
        ... on MutationError { message }
      }
    }
    """
    r = _gql(token, mutation, {
        "input": {
            "text":           content,
            "channelId":      channel_id,
            "schedulingType": "automatic",
            "mode":           "customScheduled",
            "dueAt":          due_at,
        }
    })
    try:
        data = r.json()
    except Exception:
        return {"success": False, "error": f"HTTP {r.status_code}: {r.text[:300]}"}

    if data.get("errors"):
        msg = "; ".join(e.get("message", str(e)) for e in data["errors"])
        return {"success": False, "error": msg}

    result = (data.get("data") or {}).get("createPost", {})
    if "post" in result:
        return {"success": True, "update_id": result["post"].get("id")}
    if "message" in result:
        return {"success": False, "error": result["message"]}
    return {"success": False, "error": f"Unexpected response: {str(data)[:300]}"}


def schedule_all_posts(posts_file: str, dry_run: bool = False) -> list:
    if not os.path.exists(posts_file):
        raise FileNotFoundError(f"Posts file not found: {posts_file}")

    with open(posts_file) as f:
        data = json.load(f)

    posts = data.get("posts", [])
    week  = data.get("week", "?")

    print(f"\n  📤 Scheduling {len(posts)} posts for Week {week}...")
    if dry_run:
        print("     [DRY RUN — not sending to Buffer]\n")

    results = []
    for i, post in enumerate(posts, 1):
        title        = post.get("title", f"Post {i}")
        day          = post.get("schedule_day", "?")
        time         = post.get("schedule_time", "?")
        scheduled_dt = post.get("scheduled_datetime", "")
        content      = post.get("content", "")

        print(f"     [{i}/{len(posts)}] {day} {time} — {title}")

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
    token, profile_id = get_credentials()
    response = requests.get(
        f"{BUFFER_API_BASE}/profiles/{profile_id}/updates/pending.json",
        headers=_headers(token),
    )
    if response.status_code != 200:
        print(f"❌ Could not fetch queue: {response.status_code}: {response.text[:200]}")
        return []
    data    = response.json()
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
    parser.add_argument("--file",    type=str)
    parser.add_argument("--week",    type=int)
    parser.add_argument("--test",    action="store_true", help="Test connection + list profiles")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--queue",   action="store_true")
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
