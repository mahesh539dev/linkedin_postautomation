"""
research_agent.py
─────────────────
Uses Claude API to research trending topics in AI infrastructure,
MLOps, Kafka, LLMs, and backend engineering each week.

Finds 5 post-worthy topics with angles specific to Mahesh's transition story.
"""

import anthropic
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

Be specific. Not "AI is growing fast" but "vLLM 0.7 released with 40%
throughput improvement on A100s — here's what changed in the batching logic"
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
    Use Claude with web search to find this week's best LinkedIn topics.
    Returns dict with ranked topics and recommendations.
    """
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY not set in .env")

    client = anthropic.Anthropic(api_key=api_key)

    today = datetime.now().strftime("%A, %B %d %Y")

    print(f"\n🔍 Researching trending topics for Week {week_number}...")
    print(f"   Date: {today}")
    print(f"   Searching AI infrastructure, MLOps, Kafka, LLMs, K8s...")

    message = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=4096,
        system=RESEARCH_SYSTEM_PROMPT,
        tools=[{
            "type": "web_search_20250305",
            "name": "web_search"
        }],
        messages=[
            {
                "role": "user",
                "content": RESEARCH_USER_PROMPT.format(
                    context=ENGINEER_CONTEXT,
                    date=today
                )
            }
        ]
    )

    # Extract final text response (after any tool use)
    raw = ""
    for block in message.content:
        if block.type == "text":
            raw += block.text

    # Strip markdown if present
    if "```json" in raw:
        raw = raw.split("```json")[1].split("```")[0]
    elif "```" in raw:
        raw = raw.split("```")[1].split("```")[0]
    raw = raw.strip()

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        # Try to extract JSON if wrapped in text
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


# ── Fallback topics (when API unavailable) ────────────────────────────────────

FALLBACK_TOPICS = {
    "week_theme": "AI Infrastructure Evolution",
    "topics": [
        {
            "rank": 1,
            "category": "LLM Infrastructure",
            "headline": "vLLM continuous batching cuts inference latency by 30-40% vs naive approaches",
            "source": "vLLM docs + community benchmarks",
            "why_it_matters": "Throughput optimization is the #1 cost driver in production LLM systems. Understanding batching is critical for any AI infra engineer.",
            "backend_angle": "Kafka engineers already think about batch.size vs linger.ms tradeoffs. vLLM batching is the same optimization, different domain.",
            "linkedin_hook": "The same batching trade-off I tune in Kafka every day is what makes vLLM 40% faster than naive LLM serving.",
            "suggested_post_type": "bridge",
            "freshness": "evergreen"
        },
        {
            "rank": 2,
            "category": "MLOps",
            "headline": "LangSmith now supports distributed tracing across multi-agent LangGraph workflows",
            "source": "LangChain blog",
            "why_it_matters": "Observability in multi-agent systems is the hardest unsolved problem in AI infrastructure today.",
            "backend_angle": "Same as distributed tracing in microservices — but LLM calls are non-deterministic, making root cause analysis much harder.",
            "linkedin_hook": "Debugging a multi-agent LangGraph system without LangSmith is like debugging a Kafka consumer with no monitoring. Here's why.",
            "suggested_post_type": "industry_news",
            "freshness": "recent"
        },
        {
            "rank": 3,
            "category": "Industry Trend",
            "headline": "Enterprise RAG adoption hitting a wall: retrieval quality, not LLMs, is the bottleneck",
            "source": "Multiple engineering blogs + LinkedIn discussions",
            "why_it_matters": "Most companies find their RAG systems hallucinate because of bad retrieval, not bad generation. The solution is better data pipelines.",
            "backend_angle": "Backend engineers understand data pipeline quality better than most AI teams. Kafka + data quality = the missing piece.",
            "linkedin_hook": "Unpopular opinion: 80% of failed RAG systems aren't LLM problems. They're data pipeline problems.",
            "suggested_post_type": "opinion",
            "freshness": "trending"
        },
        {
            "rank": 4,
            "category": "Vector DB",
            "headline": "pgvector vs Pinecone at scale: PostgreSQL wins on cost, loses on query latency above 10M vectors",
            "source": "Community benchmarks",
            "why_it_matters": "Choosing the wrong vector store is expensive to undo. Backend engineers need the tradeoff map.",
            "backend_angle": "Same as Oracle vs MySQL vs MongoDB decisions — choose based on your scale and access patterns, not hype.",
            "linkedin_hook": "pgvector vs Pinecone: I ran the benchmarks so you don't have to. Here's the honest tradeoff.",
            "suggested_post_type": "industry_trend",
            "freshness": "evergreen"
        },
        {
            "rank": 5,
            "category": "Streaming+AI",
            "headline": "Real-time AI pipelines: Kafka + Flink + LLM inference becoming standard pattern in fintech",
            "source": "Confluent blog + Flink community",
            "why_it_matters": "Event-driven AI is the future of intelligent financial systems. Kafka engineers are perfectly positioned for this.",
            "backend_angle": "7 years of Kafka expertise becomes your AI infrastructure superpower when you add LLM inference to the pipeline.",
            "linkedin_hook": "Kafka + LLM inference = the fintech AI pipeline nobody is talking about. Here's the architecture.",
            "suggested_post_type": "industry_trend",
            "freshness": "recent"
        },
        {
            "rank": 6,
            "category": "Backend+AI",
            "headline": "Spring AI 1.0 milestone: Java developers can now build RAG systems without leaving their ecosystem",
            "source": "Spring blog",
            "why_it_matters": "Java shops no longer need Python AI teams. Backend engineers can own the full AI pipeline.",
            "backend_angle": "Spring AI bridges the Java/Python gap — exactly the transition path backend engineers need.",
            "linkedin_hook": "Spring AI 1.0 just eliminated the main reason Java engineers couldn't do AI. Here's what changed.",
            "suggested_post_type": "industry_news",
            "freshness": "recent"
        }
    ],
    "recommended_post_order": [2, "bridge from your expertise", 3, "your learning this week", 5]
}


def get_fallback_topics(week_number: int) -> dict:
    """Return curated fallback topics if API search fails."""
    data = FALLBACK_TOPICS.copy()
    data["week"] = week_number
    data["research_date"] = datetime.now().strftime("%A, %B %d %Y")
    data["note"] = "Fallback topics — Claude web search unavailable"
    return data

# Alias for backwards compatibility
get_fallback = get_fallback_topics


# ── CLI ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Research trending LinkedIn topics using Claude")
    parser.add_argument("--week", type=int, required=True, help="Week number (2-9)")
    parser.add_argument("--fallback", action="store_true", help="Use curated fallback topics (no API)")
    parser.add_argument("--no-save", action="store_true", help="Don't save to file")
    args = parser.parse_args()

    if args.fallback:
        data = get_fallback_topics(args.week)
        print("Using fallback curated topics...")
    else:
        try:
            data = research_weekly_topics(args.week, save=not args.no_save)
        except Exception as e:
            print(f"⚠️  Research failed ({e}), using fallback topics...")
            data = get_fallback_topics(args.week)

    display_research(data)
