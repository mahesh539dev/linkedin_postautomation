"""
refinement.py
─────────────
Final Claude Haiku pass: removes filler phrases, enforces word count,
caps emojis, ensures first line is not "I ...".
Single API call for all 5 posts to minimise cost and latency.
On any failure returns original posts unchanged.
"""

import json
import re
import anthropic
from src.config import ANTHROPIC_API_KEY, CLAUDE_REFINE_MODEL

_SYSTEM = """You are a LinkedIn copyeditor. Refine each post:
- Remove filler phrases: "Excited to share", "Game-changer", "Thrilled", "Dive into", "Delighted"
- If the first line starts with "I ", rewrite it to not start with "I"
- Trim to 150-220 words if over limit (keep hashtags, don't count them)
- Allow max 2 emojis per post total

Return ONLY a JSON array — no markdown, no explanation:
[{"index": 0, "content": "refined post text here"}, ...]"""


def refine_posts(posts: list[dict]) -> list[dict]:
    """
    Refine all posts in a single Claude Haiku call.
    Returns updated list with only `content` fields changed.
    Falls back to original posts on any error.
    """
    if not posts:
        return posts

    api_key = ANTHROPIC_API_KEY
    if not api_key:
        print("refinement: ANTHROPIC_API_KEY not set — skipping refinement")
        return posts

    numbered = "\n\n".join(
        f"Post {i}:\n{p.get('content', '')}"
        for i, p in enumerate(posts)
    )
    user_prompt = f"Refine these {len(posts)} LinkedIn posts:\n\n{numbered}"

    try:
        client = anthropic.Anthropic(api_key=api_key)
        msg = client.messages.create(
            model=CLAUDE_REFINE_MODEL,
            max_tokens=4000,
            system=_SYSTEM,
            messages=[{"role": "user", "content": user_prompt}],
        )
        raw = msg.content[0].text.strip()

        # Strip markdown fences if present
        if "```json" in raw:
            raw = raw.split("```json")[1].split("```")[0]
        elif "```" in raw:
            raw = raw.split("```")[1].split("```")[0]

        # Fallback: extract JSON array if wrapped in text
        if not raw.strip().startswith("["):
            match = re.search(r'\[.*\]', raw, re.DOTALL)
            raw = match.group() if match else raw

        refined = json.loads(raw.strip())
        result = [p.copy() for p in posts]
        for item in refined:
            idx = item.get("index")
            content = item.get("content", "").strip()
            if idx is not None and 0 <= idx < len(result) and content:
                result[idx]["content"] = content

        print(f"refinement: refined {len(refined)} posts via Claude Haiku")
        return result

    except Exception as e:
        print(f"refinement: failed ({e}) — returning original posts")
        return posts
