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

RESEARCH_SYSTEM_PROMPT = """You are a LinkedIn content researcher for a senior backend engineer
transitioning to AI infrastructure. Your job is to find the most engaging,
timely topics from the past 7 days in AI infrastructure, MLOps, LLMs, Kafka,
Kubernetes, and backend engineering.

You have access to web search. Use it to find:
- Real news, releases, benchmarks from the past week
- Trending discussions on LinkedIn/Twitter/Hacker News in AI/MLOps space
- New tool releases (vLLM updates, LangChain releases, new vector DBs, etc.)
- Research papers getting traction
- Industry moves (companies adopting AI infra, new funding, acquisitions)

For each topic you find, provide:
1. The actual news/trend (with source)
2. Why it matters to AI infrastructure engineers
3. The angle a backend engineer (Kafka/Spring Boot) would uniquely bring
4. A hook sentence that would stop scrolling on LinkedIn

Be specific. Style example (do NOT use this as a topic — find real news):
"vLLM v0.X.Y released with N% throughput improvement — here's the actual change"
That level of specificity is the target. The actual topics must come from the
provided trending headlines, not from this example.
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

IMPORTANT: You MUST select topics exclusively from the provided trending headlines
above. Do NOT invent topics, reuse examples from this prompt, or pick generic
evergreen content. Every topic must trace back to a specific headline in the list.

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
      "linkedin_hook": "one sentence that would stop scrolling — specific, bold, surprising",
      "suggested_post_type": "industry_news|industry_trend|opinion|bridge|quick_tip",
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
        print(f"     Headline: {topic['headline']}")
        print(f"     Source:   {topic.get('source', 'N/A')}")
        print(f"     Fresh:    {topic.get('freshness', 'N/A')}")
        print(f"     Hook:     \"{topic['linkedin_hook']}\"")
        print(f"     Type:     {topic['suggested_post_type']}")
        print(f"     Backend angle: {topic['backend_angle'][:80]}...")

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
