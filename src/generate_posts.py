"""
generate_posts.py  (v2)
───────────────────────
Generates 5 LinkedIn posts per week mixing:
  - 3 industry/trend posts (from Claude research)
  - 1 bridge post (from your backend expertise)
  - 1 learning post (from your weekly notes)

This gives you industry reach + personal credibility.
"""

import json
import os
import time
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

SYSTEM_INFRA_CONTEXT = """
You are writing for an engineer who BUILDS AI systems — not one who reads about them.

This engineer has built:
- Multi-model LLM orchestration: DeepSeek for research ranking, Kimi for generation,
  Claude Haiku for refinement, Claude Sonnet + GPT-4o for rewrites and scoring
- Cost optimisation pipelines comparing models across latency, quality, and price
- Automated content pipeline: HN trend ingestion → DeepSeek ranking → Kimi generation
  → Claude refinement → 3-way scoring → Buffer scheduling
- Production Kafka systems processing 500K+ events/day in financial payment infrastructure

Write like a production engineer:
- Include system-level thinking and architecture decisions
- Name specific tradeoffs (latency vs cost, throughput vs memory, consistency vs availability)
- Reference model selection reasoning where it fits naturally (why pick Kimi over GPT for generation?)
- Assume the reader builds these systems too — no generic AI explanations

Target audience:
- AI infrastructure recruiters evaluating system design depth
- Backend engineers transitioning to AI who see themselves in this story
- MLOps engineers who care about production tradeoffs
"""

SYSTEM_PROMPT = """You are a LinkedIn content writer for a senior backend engineer
building real AI infrastructure systems. Write like a sharp, opinionated production
engineer — not a marketer, student, or influencer.

Post modes:
1. INDUSTRY (industry_news, industry_trend): React to real news with a backend/infra
   angle. What does this mean for production systems? What tradeoff does it expose?

2. ANALYSIS (bridge, model_comparison): Bridge posts map a distributed systems concept
   (Kafka, K8s, Spring Boot) to an AI equivalent. Model comparison posts compare 2-3
   models on hard metrics — tok/s, cost/million tokens, context window, VRAM, deployment
   complexity — and give a clear production verdict.

3. OPINION: Start with the claim, back it up with data or a real experience.
   Polarising is fine. Vague is not.

4. LEARNING (learning, build_in_public): Learning posts show honest weekly reflection
   — what clicked, what broke, one concrete number or result. Build-in-public posts
   show a real system: architecture diagram in text, tradeoffs made, cost/latency
   results, and what you'd do differently.

Writing rules:
- First line MUST contain a number (latency, cost, throughput), a comparison (X vs Y),
  or a strong engineering claim. Never starts with "I".
- Each post MUST include at least one: system design insight, infra tradeoff,
  real-world engineering decision, or known limitation / failure case.
- No phrases: "Excited to share", "Game-changer", "Thrilled", "Dive into",
  "Revolutionising", "AI is changing everything"
- Numbers beat adjectives: "120 tok/s" not "blazing fast", "4x memory" not "much more"
- Max 2 emojis — only if genuinely fitting
- Hashtags at END only, never in body
- 150–220 words per post
""" + SYSTEM_INFRA_CONTEXT

# ── Schedule ──────────────────────────────────────────────────────────────────

POST_SCHEDULE = [
    ("Monday",    "10:00", "industry_news",    "Biggest AI/infra news of the week — engineering breakdown, not summary"),
    ("Tuesday",   "17:00", "bridge",           "Map one backend concept (Kafka/K8s/Spring) to its AI infrastructure equivalent"),
    ("Wednesday", "10:00", "industry_trend",   "Broader AI/infra trend — what it means for production systems in 6-12 months"),
    ("Thursday",  "17:00", "model_comparison", "Compare 2-3 trending models on hard infra metrics — give a production verdict"),
    ("Friday",    "10:00", "opinion",          "Data-backed hot take — start with the claim, then the evidence"),
    ("Saturday",  "10:00", "learning",         "Weekly learning checkpoint — one concrete insight, result, or failure from your notes"),
    ("Sunday",    "10:00", "build_in_public",  "Show a real system you built: architecture, tradeoffs, results, and what you'd change"),
]

# Ordered list of all post days in the weekly cycle (Mon–Sun)
_ALL_POST_DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

HASHTAG_SETS = {
    "industry_news":    ["#AIInfrastructure", "#MLOps", "#LLMs", "#AI", "#MachineLearning"],
    "bridge":           ["#Kafka", "#BackendToAI", "#SystemDesign", "#AIInfrastructure", "#DistributedSystems"],
    "industry_trend":   ["#MLOps", "#AIInfrastructure", "#RAG", "#LLMs", "#VectorDB"],
    "model_comparison": ["#LLMs", "#AIInfrastructure", "#ModelBenchmark", "#MLOps", "#AI"],
    "opinion":          ["#AIInfrastructure", "#MLOps", "#TechOpinion", "#BackendEngineering", "#AI"],
    "learning":         ["#100DaysOfAI", "#LearningInPublic", "#BackendToAI", "#Python", "#AIInfrastructure"],
    "build_in_public":  ["#BuildInPublic", "#AIInfrastructure", "#SystemDesign", "#MLOps", "#100DaysOfAI"],
}

_DAY_INSTRUCTIONS = {
    "Monday":    "Pick the most timely research topic. Give the engineering breakdown — what changed in the system, what tradeoff it exposes, what it means for production. Your distributed systems angle must be visible.",
    "Tuesday":   "Use YOUR expertise (Kafka/Spring Boot/K8s). Find one precise mapping: pick a backend concept and show its direct AI infrastructure equivalent. Concrete analogy, real numbers, clear conclusion.",
    "Wednesday": "Pick a different research topic. Zoom out: what does this mean for the industry in 6-12 months? What architecture decision should engineers make now?",
    "Thursday":  "Compare 2-3 trending models from the research on hard infra metrics: tok/s throughput, cost per million tokens, context window, VRAM requirement, quantization options, cold-start latency. Give a clear production verdict with numbers — which would you deploy and why.",
    "Friday":    "Data-backed opinion. Start with the engineering claim, then back it up with a specific result, benchmark, or failure case. Not aggressive — just confident and specific.",
    "Saturday":  "Use the personal learning notes. One specific insight, confusion, or breakthrough. Show the actual learning curve: what you tried, what broke, what the number was.",
    "Sunday":    "Show a real system you built this week. Include: what it does, the architecture (describe it in text), why you made the key tradeoffs, latency/cost/accuracy results, and one thing you'd redesign. This is your strongest hiring signal — be specific about the engineering decisions.",
}


def get_dynamic_schedule() -> list[tuple]:
    """Return POST_SCHEDULE entries for remaining days in the posting cycle.

    Cycle is Mon–Sun (7 posts). Always starts from the NEXT post day:
      Mon → 6 posts (Tue–Sun)
      Tue → 5 posts (Wed–Sun)
      Wed → 4 posts (Thu–Sun)
      Thu → 3 posts (Fri–Sun)
      Fri → 2 posts (Sat–Sun)
      Sat → 1 post  (Sun)
      Sun → 7 posts (Mon–Sun next week)
    """
    wd = datetime.now().weekday()  # 0=Mon … 5=Sat, 6=Sun

    if wd <= 5:     # Mon(0)–Sat(5): schedule from tomorrow through Sunday
        remaining = set(_ALL_POST_DAYS[wd + 1:])
    else:           # Sun(6): full next week Mon–Sun
        remaining = set(_ALL_POST_DAYS)
    return [e for e in POST_SCHEDULE if e[0] in remaining]


def build_generation_prompt(
    week_number: int,
    research_topics: list[dict],
    learning_notes: str,
    schedule: list[tuple]
) -> str:

    topics_text = ""
    for t in research_topics[:6]:
        topics_text += f"""
Topic #{t['rank']}: {t['headline']}
  Category:        {t['category']}
  Why it matters:  {t['why_it_matters']}
  Infra tradeoff:  {t.get('infra_tradeoff', 'N/A')}
  Real-world use:  {t.get('real_world_use', 'N/A')}
  Backend angle:   {t['backend_angle']}
  Hook suggestion: {t['linkedin_hook']}
  Suggested type:  {t['suggested_post_type']}
"""

    instructions = "\n".join(
        f"- {day} ({type_}): {_DAY_INSTRUCTIONS.get(day, desc)}"
        for day, time, type_, desc in schedule
    )

    n = len(schedule)
    return f"""
Week {week_number} — Generate {n} LinkedIn post{'s' if n != 1 else ''}.

ENGINEER PROFILE:
{ENGINEER_CONTEXT}

THIS WEEK'S RESEARCH TOPICS (from web search):
{topics_text}

THIS WEEK'S PERSONAL LEARNING NOTES:
{learning_notes}

POST SCHEDULE TO FILL:
{chr(10).join(f"  {day} {time}: {type_} — {desc}" for day, time, type_, desc in schedule)}

INSTRUCTIONS:
{instructions}

Return ONLY valid JSON (no markdown):
{{
  "week": {week_number},
  "generated_at": "{datetime.now().isoformat()}",
  "week_theme": "one phrase tying all posts together",
  "posts": [
    {{
      "title": "short internal title",
      "type": "industry_news|bridge|industry_trend|model_comparison|opinion|learning|build_in_public",
      "schedule_day": "Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday",
      "schedule_time": "10:00|17:00",
      "content": "full post text — no hashtags in body — must include one infra tradeoff or system insight",
      "hashtags": ["#Tag1", "#Tag2", "#Tag3", "#Tag4"],
      "source_topic": "which research topic this draws from (or 'personal')",
      "infra_signal": "one sentence on the system design / engineering depth in this post",
      "why_this_post": "one sentence on why this post signals AI infra engineering skill"
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
    """Generate LinkedIn posts for the remaining days this week."""
    from src.llm_client import call_llm

    research_topics = research_data.get("topics", [])
    if not research_topics:
        raise ValueError("No research topics found — run research_agent.py first")

    schedule = get_dynamic_schedule()
    print(f"\n✍️  Generating {len(schedule)} posts for Week {week_number}...")
    print(f"   Days: {', '.join(d for d, *_ in schedule)}")
    print(f"   Using {len(research_topics)} research topics + your learning notes")

    prompt = build_generation_prompt(
        week_number,
        research_topics,
        learning_notes,
        schedule,
    )

    t0 = time.time()
    raw = call_llm("kimi", prompt, system=SYSTEM_PROMPT, max_tokens=5000)
    gen_latency = round(time.time() - t0, 1)

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

    # Correct schedule_day / schedule_time regardless of what the LLM wrote.
    # Kimi often assigns multiple posts to the same day or uses wrong day names.
    # Strategy: match each post to a schedule slot by type; fill remaining slots
    # by position for any post whose type didn't appear in the schedule.
    slot_by_type = {stype: (day, t) for day, t, stype, _ in schedule}
    matched, unmatched, used_types = [], [], set()

    for post in data.get("posts", []):
        ptype = post.get("type", "")
        if ptype in slot_by_type and ptype not in used_types:
            post["schedule_day"]  = slot_by_type[ptype][0]
            post["schedule_time"] = slot_by_type[ptype][1]
            used_types.add(ptype)
            matched.append(post)
        else:
            unmatched.append(post)

    # Fill unfilled schedule slots from leftover posts (type mismatch)
    for day, t, stype, _ in schedule:
        if stype not in used_types and unmatched:
            post = unmatched.pop(0)
            post["schedule_day"]  = day
            post["schedule_time"] = t
            post["type"]          = stype
            used_types.add(stype)
            matched.append(post)

    data["posts"] = matched[:len(schedule)]
    print(f"   Posts after normalisation: {len(data['posts'])} "
          f"({', '.join(p['schedule_day'] for p in data['posts'])})")

    # Add pipeline metadata (logged + usable in build_in_public posts)
    data["meta"] = {
        "pipeline":        "multi-model orchestration",
        "models_used":     ["deepseek", "kimi", "claude-haiku", "claude-sonnet", "gpt-4o"],
        "generation_model": "kimi",
        "gen_latency_s":   gen_latency,
        "post_count":      len(data["posts"]),
        "estimated_cost_usd": "~$0.026",
        "week":            week_number,
        "generated_at":    datetime.now().isoformat(),
    }
    print(f"   Generation latency: {gen_latency}s")

    # Assign actual calendar dates. Mirrors get_dynamic_schedule logic exactly.
    today = datetime.now()
    wd    = today.weekday()

    if wd <= 5:     # Mon(0)–Sat(5): base is tomorrow
        remaining = _ALL_POST_DAYS[wd + 1:]
        base_date = today + timedelta(days=1)
    else:           # Sun(6): base is next Monday
        remaining = _ALL_POST_DAYS
        base_date = today + timedelta(days=1)

    day_offsets = {day: i for i, day in enumerate(remaining)}

    for post in data.get("posts", []):
        day = post.get("schedule_day", "")
        offset = day_offsets.get(day, 0)
        scheduled_date = base_date + timedelta(days=offset)
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
        "industry_news":    "📰",
        "bridge":           "🌉",
        "industry_trend":   "📈",
        "model_comparison": "⚖️",
        "opinion":          "💡",
        "learning":         "🎓",
        "build_in_public":  "🏗️",
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
