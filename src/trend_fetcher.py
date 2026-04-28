"""
trend_fetcher.py
────────────────
Fetches trending AI/MLOps/Kafka stories from free sources.
Primary: Hacker News Algolia API (no key required).
Optional: SerpAPI Google News (if SERPAPI_KEY is set).
Results are cached in-memory for 3 hours.
"""

import os
import time
import requests
from src.config import SERPAPI_KEY

_CACHE_TTL = 3 * 3600  # 3 hours
_cache: dict = {"data": None, "fetched_at": 0.0}

_HN_QUERIES = [
    "AI infrastructure LLM",
    "MLOps LangChain vLLM inference",
    "Kafka streaming AI pipeline",
]
_HN_BASE = "https://hn.algolia.com/api/v1/search"


def _fetch_hn() -> list[dict]:
    items = []
    seen = set()
    for query in _HN_QUERIES:
        try:
            resp = requests.get(
                _HN_BASE,
                params={"query": query, "tags": "story", "hitsPerPage": 10},
                headers={"User-Agent": "linkedin-automation/1.0"},
                timeout=10,
            )
            resp.raise_for_status()
            for hit in resp.json().get("hits", []):
                oid = hit.get("objectID")
                title = hit.get("title") or hit.get("story_title")
                url = hit.get("url") or hit.get("story_url")
                if oid and oid not in seen and title and url:
                    seen.add(oid)
                    items.append({
                        "title":   title,
                        "url":     url,
                        "points":  hit.get("points", 0),
                        "source":  "HackerNews",
                    })
        except Exception as e:
            print(f"trend_fetcher: HN query '{query}' failed — {e}")
    return items


def _fetch_serpapi() -> list[dict]:
    key = SERPAPI_KEY or os.getenv("SERPAPI_KEY", "")
    if not key:
        return []
    items = []
    try:
        resp = requests.get(
            "https://serpapi.com/search.json",
            params={"q": "AI infrastructure MLOps news", "tbm": "nws", "num": 10, "api_key": key},
            timeout=15,
        )
        resp.raise_for_status()
        for r in resp.json().get("news_results", []):
            title = r.get("title")
            url   = r.get("link")
            if title and url:
                items.append({"title": title, "url": url, "points": 0, "source": "GoogleNews"})
    except Exception as e:
        print(f"trend_fetcher: SerpAPI failed — {e}")
    return items


def fetch_trends() -> list[dict]:
    """
    Return up to 25 normalised trend items.
    Uses in-memory cache with 3-hour TTL.
    Never raises — returns partial data on failure.
    """
    now = time.time()
    if _cache["data"] is not None and (now - _cache["fetched_at"]) < _CACHE_TTL:
        return _cache["data"]

    items = _fetch_hn() + _fetch_serpapi()

    # Deduplicate by URL, cap at 25
    seen_urls: set = set()
    unique = []
    for item in items:
        if item["url"] not in seen_urls:
            seen_urls.add(item["url"])
            unique.append(item)
        if len(unique) >= 25:
            break

    _cache["data"] = unique
    _cache["fetched_at"] = now
    print(f"trend_fetcher: fetched {len(unique)} trends ({len(_fetch_hn.__doc__ or '')} sources)")
    return unique
