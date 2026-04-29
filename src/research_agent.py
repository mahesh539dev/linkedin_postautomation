"""
research_agent.py
─────────────────
Uses Claude API to research trending topics in AI infrastructure,
MLOps, Kafka, LLMs, and backend engineering each week.

Finds 5 post-worthy topics with angles specific to Mahesh's transition story.
"""

import json
import os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

CLAUDE_MODEL = "claude-sonnet-4-20250514"

# ── Engineer context (same as before) ────────────────────────────────────────

ENGINEER_CONTEXT = """
Name: Mahesh Annapureddy
Role: Senior Consultant at Capgemini → transitioning to AI Infrastructure Engineer
Background: 7 years Java/Spring Boot/Apache Kafka (500K+ events/day), Kubernetes,
            Docker, PCI-DSS, financial payment systems, Toronto Canada
Learning now: Python, NumPy, Pandas, FastAPI, Embeddings, Pinecone/ChromaDB,
              LangChain, LangGraph, vLLM, Ollama, MLflow, LangSmith, Arize AI
Unique angle: Backend/distributed systems engineer who understands AI infra deeply
Target audience: AI infrastructure recruiters, backend engineers pivoting to AI,
                 MLOps engineers, Toronto tech community
"""

# ── Research prompt ───────────────────────────────────────────────────────────

RESEARCH_SYSTEM_PROMPT = """You are a senior AI infrastructure engineer analyzing weekly trends.

Your job is NOT to summarize news.
Your job is to extract engineering insights from real-world AI infrastructure developments.

For each topic:
1. What actually happened (fact-based, from the provided headlines)
2. Why it matters for AI infrastructure engineers
3. Backend/system design angle (Kafka, distributed systems, APIs, distributed inference)
4. A strong LinkedIn hook with a specific number, comparison, or engineering claim
5. The concrete infrastructure tradeoff involved (latency vs cost, throughput vs memory, etc.)
6. A real-world production use case where an engineer would encounter this
7. Why AI infrastructure recruiters would care about this topic

Avoid generic summaries. Think like someone reviewing production architecture decisions.

Style target — do NOT use as a topic, this is only a specificity example:
"vLLM v0.X.Y: N% throughput gain at the cost of 2x memory — here's the batching tradeoff"
Every topic must be that specific. Source it from the provided headlines.
"""

RESEARCH_USER_PROMPT = """
Engineer context:
{context}

Today's date: {date}

Search the web for the most relevant and timely topics from the PAST 7 DAYS in:

1. LLM/AI infrastructure news (new model releases, inference optimizations, benchmarks)
2. MLOps tooling updates (LangChain, LangSmith, MLflow, vLLM, Ollama, Arize, W&B)
3. Vector database news (Pinecone, Weaviate, Qdrant, pgvector updates)
4. Kafka/streaming + AI integration news
5. Kubernetes/cloud AI deployment patterns
6. Backend engineering + AI intersection (any language)
7. RAG, agents, or LLM deployment patterns getting traction

RULES — a topic is REJECTED if:
- It has no concrete infrastructure tradeoff (not "it's faster" but "latency drops X% at cost of Y")
- It has no real production use case
- The hook is generic (e.g. "AI is changing everything", "the future is here")

IMPORTANT: Select topics exclusively from the provided trending headlines.
Do NOT invent topics, reuse prompt examples, or pick generic evergreen content.
Every topic must trace back to a specific headline in the list.

Find 6 topics total. Return as JSON:
{{
  "research_date": "{date}",
  "topics": [
    {{
      "rank": 1,
      "category": "LLM Infrastructure|MLOps|Vector DB|Streaming+AI|K8s+AI|Backend+AI|Industry Trend",
      "headline": "What actually happened (specific, factual)",
      "source": "where you found this",
      "why_it_matters": "2-3 sentences on why AI infra engineers care",
      "backend_angle": "the unique perspective a Kafka/Spring Boot engineer brings",
      "linkedin_hook": "one sentence — must contain a number, comparison, or engineering claim",
      "infra_tradeoff": "specific tradeoff involved (e.g. latency vs throughput, cost vs quality)",
      "real_world_use": "concrete production scenario where an engineer encounters this",
      "why_recruiters_care": "what skill signal this sends to AI infra recruiters",
      "suggested_post_type": "industry_news|industry_trend|opinion|bridge|model_comparison",
      "freshness": "how old is this news (hours/days)"
    }}
  ],
  "recommended_post_order": [
    "topic rank for Monday",
    "topic rank for Tuesday (bridge - pick from your own expertise)",
    "topic rank for Wednesday",
    "topic rank for Thursday (learning post from user's notes)",
    "topic rank for Friday (opinion/hot take)"
  ],
  "week_theme": "one overarching theme tying this week's posts together"
}}
"""

# ── Main function ─────────────────────────────────────────────────────────────

def research_weekly_topics(week_number: int, save: bool = True) -> dict:
    """
    Fetch trending topics via HN/SerpAPI then rank with DeepSeek.
    Returns dict with ranked topics and recommendations.
    """
    from src.trend_fetcher import fetch_trends
    from src.llm_client import call_llm

    today = datetime.now().strftime("%A, %B %d %Y")

    print(f"\n🔍 Researching trending topics for Week {week_number}...")
    print(f"   Date: {today}")
    print(f"   Fetching from HN Algolia + optional SerpAPI...")

    raw_trends = fetch_trends()
    if not raw_trends:
        raise ValueError("fetch_trends returned no data — check network or use --fallback")

    trends_text = "\n".join(
        f"- [{t['source']}] {t['title']}  ({t['url']})"
        for t in raw_trends
    )

    ranking_prompt = (
        f"Here are today's trending items from the past week:\n{trends_text}\n\n"
        + RESEARCH_USER_PROMPT.format(context=ENGINEER_CONTEXT, date=today)
    )

    print(f"   Ranking {len(raw_trends)} trends with DeepSeek...")
    raw = call_llm("deepseek", ranking_prompt, system=RESEARCH_SYSTEM_PROMPT, max_tokens=3000)

    # Strip markdown if present
    if "```json" in raw:
        raw = raw.split("```json")[1].split("```")[0]
    elif "```" in raw:
        raw = raw.split("```")[1].split("```")[0]
    raw = raw.strip()

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        import re
        match = re.search(r'\{.*\}', raw, re.DOTALL)
        if match:
            data = json.loads(match.group())
        else:
            print("❌ Could not parse research results. Raw response:")
            print(raw[:1000])
            raise

    # Validate topics — drop any that lack infra depth or are too generic
    _GENERIC_PHRASES = [
        "ai is growing", "the future is", "game changer", "game-changer",
        "ai is changing everything", "revolutionary", "unprecedented"
    ]
    valid, dropped = [], []
    for topic in data.get("topics", []):
        hook = topic.get("linkedin_hook", "").lower()
        missing_tradeoff = not topic.get("infra_tradeoff", "").strip()
        missing_use      = not topic.get("real_world_use", "").strip()
        too_generic      = any(p in hook for p in _GENERIC_PHRASES)
        if missing_tradeoff or missing_use or too_generic:
            reason = (
                "missing infra_tradeoff" if missing_tradeoff else
                "missing real_world_use" if missing_use else
                "hook too generic"
            )
            print(f"   ⚠️  Dropping topic #{topic.get('rank')} ({reason}): {topic.get('headline','')[:60]}")
            dropped.append(topic)
        else:
            valid.append(topic)

    if valid:
        for i, t in enumerate(valid, 1):
            t["rank"] = i
        data["topics"] = valid
        if dropped:
            print(f"   Kept {len(valid)} topics, dropped {len(dropped)} for lacking infra depth")
    else:
        print("   ⚠️  All topics failed validation — keeping original set")

    data["week"] = week_number

    if save:
        os.makedirs("research", exist_ok=True)
        filename = f"research/week_{week_number}_topics.json"
        with open(filename, "w") as f:
            json.dump(data, f, indent=2)
        print(f"✅ Research saved to {filename}")

    return data


def display_research(data: dict):
    """Print a readable summary of research results."""
    print(f"\n{'='*65}")
    print(f"  WEEK {data.get('week', '?')} RESEARCH RESULTS")
    print(f"  Theme: {data.get('week_theme', 'AI Infrastructure')}")
    print(f"  Researched: {data.get('research_date', 'today')}")
    print(f"{'='*65}")

    for topic in data.get("topics", []):
        category_icons = {
            "LLM Infrastructure": "🤖",
            "MLOps": "⚙️",
            "Vector DB": "🗄️",
            "Streaming+AI": "🌊",
            "K8s+AI": "☸️",
            "Backend+AI": "🔧",
            "Industry Trend": "📈"
        }
        icon = category_icons.get(topic.get("category", ""), "📌")

        print(f"\n  {icon} Topic #{topic['rank']}: [{topic['category']}]")
        print(f"     Headline:        {topic['headline']}")
        print(f"     Source:          {topic.get('source', 'N/A')}")
        print(f"     Fresh:           {topic.get('freshness', 'N/A')}")
        print(f"     Hook:            \"{topic['linkedin_hook']}\"")
        print(f"     Tradeoff:        {topic.get('infra_tradeoff', 'N/A')[:80]}")
        print(f"     Real-world use:  {topic.get('real_world_use', 'N/A')[:80]}")
        print(f"     Recruiter signal:{topic.get('why_recruiters_care', 'N/A')[:80]}")
        print(f"     Type:            {topic['suggested_post_type']}")

    order = data.get("recommended_post_order", [])
    if order:
        days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
        print(f"\n  📅 RECOMMENDED SCHEDULE:")
        for i, day in enumerate(days):
            topic_rank = order[i] if i < len(order) else "?"
            if str(topic_rank).isdigit():
                topic = next((t for t in data["topics"] if t["rank"] == int(topic_rank)), None)
                if topic:
                    print(f"     {day}: #{topic_rank} — {topic['headline'][:50]}...")
            else:
                print(f"     {day}: {topic_rank}")

    print(f"\n{'='*65}\n")


# ── CLI ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Research trending LinkedIn topics using Claude")
    parser.add_argument("--week", type=int, required=True, help="Week number (2-9)")
    parser.add_argument("--no-save", action="store_true", help="Don't save to file")
    args = parser.parse_args()

    data = research_weekly_topics(args.week, save=not args.no_save)

    display_research(data)
