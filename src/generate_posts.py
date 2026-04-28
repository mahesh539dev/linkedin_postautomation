"""
generate_posts.py  (v2)
───────────────────────
Generates 5 LinkedIn posts per week mixing:
  - 3 industry/trend posts (from Claude research)
  - 1 bridge post (from your backend expertise)
  - 1 learning post (from your weekly notes)

This gives you industry reach + personal credibility.
"""

import anthropic
import json
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

CLAUDE_MODEL = "claude-sonnet-4-20250514"

ENGINEER_CONTEXT = """
Name: Mahesh Annapureddy
Role: Senior Consultant at Capgemini → AI Infrastructure Engineer
Background: 7 years Java/Spring Boot/Apache Kafka (500K+ events/day),
            Kubernetes, Docker, OpenShift, PCI-DSS, financial payment systems
Location: Toronto, Canada
Learning stack: Python, NumPy, Pandas, FastAPI, Embeddings, Pinecone,
                ChromaDB, LangChain, LangGraph, HuggingFace, vLLM, Ollama,
                MLflow, LangSmith, Arize AI
Unique voice: Backend/distributed systems thinker who connects Kafka/K8s
              expertise to AI infrastructure challenges
LinkedIn goal: Get 2-3 AI infrastructure engineer interview offers by Week 9
"""

SYSTEM_PROMPT = """You are a LinkedIn content strategist for a senior backend engineer
transitioning to AI infrastructure. You write posts that sound like a sharp,
opinionated senior engineer — not a marketer, not a student, not an influencer.

Two modes:
1. INDUSTRY post: React to real news/trends. Add the unique backend engineer
   perspective. Make it useful for anyone in AI/MLOps space.

2. PERSONAL post (bridge or learning): Authentic first-person. Show real thinking,
   including confusion, mistakes, and breakthroughs.

Writing rules:
- First line MUST be a scroll-stopper (specific claim, surprising stat, bold opinion)
- Never start with "I" on the first line
- No phrases: "Excited to share", "Game-changer", "Thrilled to announce", "Dive into"
- Use specific numbers always (40% improvement, 500K events/day, 768 dimensions)
- Industry posts: your take matters more than the news summary
- Max 2 emojis per post — use only if genuinely fitting
- Hashtags at END only, never in body
- 150–220 words per post
- Conversational but technically precise
"""

# ── Schedule ──────────────────────────────────────────────────────────────────

POST_SCHEDULE = [
    ("Monday",    "10:00", "industry_news",    "Biggest AI/infra news of the week — your sharp take"),
    ("Tuesday",   "17:00", "bridge",           "Timeless backend→AI concept analogy (your expertise)"),
    ("Wednesday", "10:00", "industry_trend",   "Broader trend in AI infra — tools, patterns, companies"),
    ("Thursday",  "17:00", "learning",         "What YOU learned or built this week — 1 specific insight"),
    ("Friday",    "10:00", "opinion",          "Hot take or quick tip — polarising, memorable, useful"),
]

HASHTAG_SETS = {
    "industry_news":  ["#AIInfrastructure", "#MLOps", "#LLMs", "#AI", "#MachineLearning"],
    "bridge":         ["#Kafka", "#BackendToAI", "#SystemDesign", "#AIInfrastructure", "#DistributedSystems"],
    "industry_trend": ["#MLOps", "#AIInfrastructure", "#RAG", "#LLMs", "#VectorDB"],
    "learning":       ["#100DaysOfAI", "#LearningInPublic", "#BackendToAI", "#Python", "#AIInfrastructure"],
    "opinion":        ["#AIInfrastructure", "#MLOps", "#TechOpinion", "#BackendEngineering", "#AI"],
}


def build_generation_prompt(
    week_number: int,
    research_topics: list[dict],
    learning_notes: str,
    schedule: list[tuple]
) -> str:

    # Format research topics for the prompt
    topics_text = ""
    for t in research_topics[:5]:
        topics_text += f"""
Topic #{t['rank']}: {t['headline']}
  Category: {t['category']}
  Why it matters: {t['why_it_matters']}
  Backend angle: {t['backend_angle']}
  Hook suggestion: {t['linkedin_hook']}
  Suggested type: {t['suggested_post_type']}
"""

    return f"""
Week {week_number} — Generate 5 LinkedIn posts.

ENGINEER PROFILE:
{ENGINEER_CONTEXT}

THIS WEEK'S RESEARCH TOPICS (from web search):
{topics_text}

THIS WEEK'S PERSONAL LEARNING NOTES:
{learning_notes}

POST SCHEDULE TO FILL:
{chr(10).join(f"  {day} {time}: {type_} — {desc}" for day, time, type_, desc in schedule)}

INSTRUCTIONS:
- Monday (industry_news): Pick the most timely research topic. Write a sharp take,
  not just a summary. Your backend angle must be in the post.

- Tuesday (bridge): Use YOUR expertise (Kafka/Spring Boot/K8s). Find one specific
  mapping from your backend world to an AI concept. Make it concrete.

- Wednesday (industry_trend): Pick a different research topic. Zoom out — what does
  this mean for the industry in 6-12 months? What should engineers do?

- Thursday (learning): Use the personal learning notes. One specific thing that
  clicked or surprised you. Show the learning curve honestly.

- Friday (opinion): Bold, polarising take based on research or your experience.
  Start with the opinion, then back it up. Not aggressive — just confident.

Return ONLY valid JSON (no markdown):
{{
  "week": {week_number},
  "generated_at": "{datetime.now().isoformat()}",
  "week_theme": "one phrase tying all posts together",
  "posts": [
    {{
      "title": "short internal title",
      "type": "industry_news|bridge|industry_trend|learning|opinion",
      "schedule_day": "Monday|Tuesday|Wednesday|Thursday|Friday",
      "schedule_time": "10:00|17:00",
      "content": "full post text here — no hashtags in body",
      "hashtags": ["#Tag1", "#Tag2", "#Tag3", "#Tag4"],
      "source_topic": "which research topic this is based on (or 'personal')",
      "why_this_post": "one sentence on why this post will get engagement"
    }}
  ]
}}
"""


def generate_posts(
    week_number: int,
    research_data: dict,
    learning_notes: str,
    save: bool = True
) -> dict:
    """
    Generate 5 LinkedIn posts mixing industry research + personal learning.
    """
    from src.llm_client import call_llm

    research_topics = research_data.get("topics", [])
    if not research_topics:
        raise ValueError("No research topics found — run research_agent.py first")

    print(f"\n✍️  Generating 5 posts for Week {week_number}...")
    print(f"   Using {len(research_topics)} research topics + your learning notes")

    prompt = build_generation_prompt(
        week_number,
        research_topics,
        learning_notes,
        POST_SCHEDULE
    )

    raw = call_llm("kimi", prompt, system=SYSTEM_PROMPT, max_tokens=4000)

    # Clean up markdown if present
    if "```json" in raw:
        raw = raw.split("```json")[1].split("```")[0]
    elif "```" in raw:
        raw = raw.split("```")[1].split("```")[0]
    raw = raw.strip()

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        print(f"❌ JSON parse error: {e}")
        print("Raw:", raw[:500])
        raise

    # Add scheduled dates + append hashtags
    today = datetime.now()
    days_to_monday = (7 - today.weekday()) % 7 or 7
    next_monday = today + timedelta(days=days_to_monday)
    day_offsets = {"Monday": 0, "Tuesday": 1, "Wednesday": 2, "Thursday": 3, "Friday": 4}

    for post in data.get("posts", []):
        offset = day_offsets.get(post.get("schedule_day", "Monday"), 0)
        scheduled_date = next_monday + timedelta(days=offset)
        post["scheduled_datetime"] = f"{scheduled_date.strftime('%Y-%m-%d')} {post.get('schedule_time', '10:00')}:00"

        # Append hashtags if not already in content
        tags = post.get("hashtags", [])
        if tags and not any(t in post["content"] for t in tags):
            post["content"] = post["content"].rstrip() + "\n\n" + " ".join(tags)

    if save:
        os.makedirs("posts", exist_ok=True)
        filename = f"posts/week_{week_number}.json"
        with open(filename, "w") as f:
            json.dump(data, f, indent=2)
        print(f"✅ Posts saved to posts/week_{week_number}.json")

    return data


def preview_posts(data: dict):
    """Print a readable preview of generated posts."""
    type_icons = {
        "industry_news":  "📰",
        "bridge":         "🌉",
        "industry_trend": "📈",
        "learning":       "🎓",
        "opinion":        "💡",
    }

    print(f"\n{'='*65}")
    print(f"  WEEK {data.get('week', '?')} POSTS — {data.get('week_theme', '')}")
    print(f"{'='*65}")

    for i, post in enumerate(data.get("posts", []), 1):
        ptype = post.get("type", "")
        icon = type_icons.get(ptype, "📌")
        print(f"\n{icon} Post {i}: {post.get('schedule_day')} {post.get('schedule_time')}")
        print(f"   Type:    {ptype.upper()}")
        print(f"   Title:   {post.get('title', '')}")
        print(f"   Source:  {post.get('source_topic', 'N/A')}")
        print(f"   Why:     {post.get('why_this_post', '')}")
        print(f"\n   {'─'*55}")
        preview = post["content"][:250]
        for line in preview.split("\n"):
            if line.strip():
                print(f"   {line}")
        if len(post["content"]) > 250:
            print("   ...")
        print(f"   {'─'*55}")

    print(f"\n✅ {len(data.get('posts', []))} posts ready for Week {data.get('week')}")
    print(f"   3 industry posts | 1 bridge | 1 learning\n")


# ── CLI ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse, sys

    parser = argparse.ArgumentParser(description="Generate LinkedIn posts (industry + learning mix)")
    parser.add_argument("--week", type=int, required=True)
    parser.add_argument("--research", type=str, help="Path to research JSON (default: research/week_N_topics.json)")
    parser.add_argument("--notes", type=str, help="Path to learning notes .txt file")
    parser.add_argument("--no-save", action="store_true")
    args = parser.parse_args()

    # Load research
    research_file = args.research or f"research/week_{args.week}_topics.json"
    if not os.path.exists(research_file):
        print(f"❌ Research file not found: {research_file}")
        print(f"   Run: python research_agent.py --week {args.week}")
        sys.exit(1)

    with open(research_file) as f:
        research_data = json.load(f)

    # Get learning notes
    if args.notes:
        with open(args.notes) as f:
            learning_notes = f.read()
    else:
        print("\n📝 Paste your Week learning notes (what you studied/built/discovered).")
        print("   Press Enter twice when done:\n")
        lines = []
        while True:
            line = input()
            if line == "" and lines and lines[-1] == "":
                break
            lines.append(line)
        learning_notes = "\n".join(lines[:-1])

    data = generate_posts(args.week, research_data, learning_notes, save=not args.no_save)
    preview_posts(data)
