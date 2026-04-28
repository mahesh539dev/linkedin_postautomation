"""
post_variants.py
────────────────
Creates 3 versions of each post and scores them.
  V1: Kimi original (refined by Claude Haiku) — no API call
  V2: Claude Sonnet rewrite using Mahesh's personalized voice prompt
  V3: OpenAI GPT-4o rewrite using the same prompt
  Scoring: OpenAI GPT-4o scores all versions in a single call.

On any failure: skips that version gracefully. Always returns at least V1.
"""

import json
import re
import anthropic
from src.config import (
    ANTHROPIC_API_KEY, CLAUDE_REWRITE_MODEL,
    OPENAI_API_KEY, OPENAI_MODEL,
)
from src.linkedin_guidelines import SCORING_GUIDELINES, MAHESH_SYSTEM_PROMPT

try:
    from openai import OpenAI as _OpenAI
    _OPENAI_AVAILABLE = True
except ImportError:
    _OPENAI_AVAILABLE = False

_REWRITE_PROMPT = """Rewrite these {n} LinkedIn posts. Follow the system prompt guidelines exactly.

Each rewrite must:
- Open with a punchier, more specific first line (never the same as the original)
- Keep the same core message but sharpen the argument
- Sound like a real engineer thinking out loud, not a polished press release
- Preserve any real numbers or specific tool names from the original

{posts_text}

Return ONLY valid JSON array (no markdown fences):
[{{"index": 0, "content": "rewritten post here"}}, ...]"""

_SCORE_PROMPT = """Score these LinkedIn posts using the rubric below. Return ALL {total} entries.

{guidelines}

POSTS TO SCORE:
{posts_block}

Return ONLY valid JSON array (no markdown fences):
[{{"post": 0, "version": "V1 · Kimi", "score": 82, "breakdown": {{"hook": 16, "specificity": 18, "insight": 15, "voice": 12, "backend": 8, "engagement": 8, "format": 5}}}}, ...]"""


def _extract_json_array(raw: str) -> list:
    if "```json" in raw:
        raw = raw.split("```json")[1].split("```")[0]
    elif "```" in raw:
        raw = raw.split("```")[1].split("```")[0]
    raw = raw.strip()
    if not raw.startswith("["):
        m = re.search(r'\[.*\]', raw, re.DOTALL)
        raw = m.group() if m else raw
    return json.loads(raw.strip())


def _posts_text(posts: list[dict]) -> str:
    return "\n\n".join(
        f"Post {i} (type: {p.get('type', '')}, day: {p.get('schedule_day', '')}):\n{p.get('content', '')}"
        for i, p in enumerate(posts)
    )


def _rewrite_with_claude(posts: list[dict]) -> dict:
    if not ANTHROPIC_API_KEY:
        print("post_variants: ANTHROPIC_API_KEY not set — skipping V2")
        return {}
    try:
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        user_msg = _REWRITE_PROMPT.format(n=len(posts), posts_text=_posts_text(posts))
        msg = client.messages.create(
            model=CLAUDE_REWRITE_MODEL,
            max_tokens=5000,
            system=MAHESH_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_msg}],
        )
        items = _extract_json_array(msg.content[0].text)
        result = {item["index"]: item["content"].strip()
                  for item in items if item.get("index") is not None and item.get("content")}
        print(f"post_variants: V2 (Claude) rewrote {len(result)}/{len(posts)} posts")
        return result
    except Exception as e:
        print(f"post_variants: Claude rewrite failed ({e}) — skipping V2")
        return {}


def _rewrite_with_openai(posts: list[dict]) -> dict:
    if not _OPENAI_AVAILABLE:
        print("post_variants: openai package not installed — skipping V3")
        return {}
    if not OPENAI_API_KEY:
        print("post_variants: OPENAI_API_KEY not set — skipping V3")
        return {}
    try:
        client = _OpenAI(api_key=OPENAI_API_KEY)
        user_msg = _REWRITE_PROMPT.format(n=len(posts), posts_text=_posts_text(posts))
        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            max_tokens=5000,
            messages=[
                {"role": "system", "content": MAHESH_SYSTEM_PROMPT},
                {"role": "user", "content": user_msg},
            ],
        )
        items = _extract_json_array(response.choices[0].message.content)
        result = {item["index"]: item["content"].strip()
                  for item in items if item.get("index") is not None and item.get("content")}
        print(f"post_variants: V3 (OpenAI) rewrote {len(result)}/{len(posts)} posts")
        return result
    except Exception as e:
        print(f"post_variants: OpenAI rewrite failed ({e}) — skipping V3")
        return {}


def _score_versions(all_versions: list[list[dict]]) -> list[list[dict]]:
    """Single OpenAI call to score every version of every post."""
    if not _OPENAI_AVAILABLE or not OPENAI_API_KEY:
        return all_versions

    posts_block = ""
    for pi, versions in enumerate(all_versions):
        for v in versions:
            posts_block += f"\nPost {pi} {v['label']}:\n{v['content']}\n"

    total = sum(len(vs) for vs in all_versions)
    prompt = _SCORE_PROMPT.format(
        total=total,
        guidelines=SCORING_GUIDELINES,
        posts_block=posts_block,
    )

    try:
        client = _OpenAI(api_key=OPENAI_API_KEY)
        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            max_tokens=3000,
            messages=[{"role": "user", "content": prompt}],
        )
        items = _extract_json_array(response.choices[0].message.content)

        score_map = {(item.get("post"), item.get("version", "").strip()): item
                     for item in items}

        for pi, versions in enumerate(all_versions):
            for v in versions:
                entry = score_map.get((pi, v["label"]))
                if entry:
                    v["score"] = int(entry.get("score", 0))
                    v["breakdown"] = entry.get("breakdown", {})

        print(f"post_variants: scored {len(items)} versions across {len(all_versions)} posts")
        return all_versions

    except Exception as e:
        print(f"post_variants: scoring failed ({e}) — scores set to 0")
        return all_versions


def create_variants(posts: list[dict]) -> list[dict]:
    """
    Add versions=[V1, V2, V3] with scores to each post.
    Gracefully skips V2/V3 if API keys are missing or calls fail.
    Always returns at least V1 in each post's versions list.
    """
    if not posts:
        return posts

    v2_map = _rewrite_with_claude(posts)
    v3_map = _rewrite_with_openai(posts)

    all_versions: list[list[dict]] = []
    for i, post in enumerate(posts):
        versions = [{"label": "V1 · Kimi", "content": post.get("content", ""), "score": 0, "breakdown": {}}]
        if v2_map.get(i):
            versions.append({"label": "V2 · Claude", "content": v2_map[i], "score": 0, "breakdown": {}})
        if v3_map.get(i):
            versions.append({"label": "V3 · OpenAI", "content": v3_map[i], "score": 0, "breakdown": {}})
        all_versions.append(versions)

    all_versions = _score_versions(all_versions)

    result = [p.copy() for p in posts]
    for i, post in enumerate(result):
        post["versions"] = all_versions[i]

    ver_count = len(all_versions[0]) if all_versions else 0
    print(f"post_variants: {len(posts)} posts × {ver_count} versions each")
    return result
