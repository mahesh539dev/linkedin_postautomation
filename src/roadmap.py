"""
roadmap.py
----------
AI Infrastructure Engineer Learning Plan — structured reference.
Used by generate_questions() to produce dynamic, week-specific
reflection questions via OpenRouter (DeepSeek).
"""

# ── Week content map ──────────────────────────────────────────────────────────

WEEK_CONTENT = {
    1:  "Python for data science: NumPy, Pandas, basic ML concepts, data manipulation",
    2:  "Embeddings and semantic search: sentence-transformers, vector representations, "
        "cosine similarity, building a basic semantic search system",
    3:  "Vector databases: ChromaDB, Weaviate, Pinecone, pgvector — CRUD operations, "
        "similarity search, indexing strategies, querying",
    4:  "AI data pipelines: Apache Kafka → Python processing → Vector DB ingestion, "
        "streaming data for AI workloads",
    5:  "Transformers architecture, HuggingFace ecosystem, LLM APIs — calling hosted "
        "models, tokenization basics, prompt design",
    6:  "Retrieval Augmented Generation (RAG): retrieval strategies, chunking, "
        "context building, grounding LLM answers in documents",
    7:  "LangChain: chains, tools, memory, document loaders, agents — building "
        "composable LLM workflows",
    8:  "LangGraph: stateful agent workflows, multi-agent systems, graph-based "
        "orchestration, complex multi-step reasoning",
    9:  "FastAPI AI microservices + Spring Boot integration: exposing Python AI as "
        "REST APIs, Spring AI, connecting Java backend to LLM services",
    10: "Model serving: vLLM and Ollama — inference optimization, batching, "
        "quantization, latency vs throughput trade-offs",
    11: "AI observability: LangSmith, Arize AI, Weights & Biases, MLflow — "
        "tracing LLM calls, experiment tracking, drift detection",
    12: "Production AI systems: Docker, Kubernetes, workflow orchestration "
        "(Airflow/Prefect), capstone project — full end-to-end deployment",
}

ROADMAP_SUMMARY = """
AI Infrastructure Engineer Learning Plan (3-Month Intensive)

Goal: Transition from Senior Backend Engineer (Java/Spring Boot/Kafka) to
AI Infrastructure Engineer. Focus is production-grade AI systems, not theory.

Core Stack:
  Backend: Java, Spring Boot, Spring AI, Kafka
  AI Layer: Python, FastAPI, LangChain, LangGraph, HuggingFace Transformers
  Data/Retrieval: ChromaDB, Weaviate, Pinecone, pgvector, Embeddings
  Infrastructure: Docker, Kubernetes, MLflow, vLLM, Ollama
  Observability: LangSmith, Arize AI, Weights & Biases

Phase 1 (Weeks 1–4): AI Foundations + Data Pipelines
  Week 1: Python for AI, NumPy, Pandas, ML basics
  Week 2: Embeddings, semantic search, sentence-transformers
  Week 3: Vector databases (ChromaDB, Weaviate, Pinecone, pgvector)
  Week 4: AI data pipelines — Kafka → Python → Vector DB

Phase 2 (Weeks 5–9): LLM Applications and RAG Systems
  Week 5: Transformers, HuggingFace ecosystem, LLM APIs
  Week 6: Retrieval Augmented Generation (RAG), prompt engineering
  Week 7: LangChain — chains, tools, memory, agents
  Week 8: LangGraph — stateful agents, multi-agent workflows
  Week 9: FastAPI AI services + Spring Boot integration, Spring AI

Phase 3 (Weeks 10–12): AI Infrastructure and Production Systems
  Week 10: Model serving — vLLM, Ollama, inference optimization
  Week 11: AI observability — LangSmith, Arize AI, W&B, MLflow
  Week 12: Production deployment, Docker, Kubernetes, capstone

Capstone: AI Social Media Automation Platform
  Trend discovery → Content generation → Autonomous agents → Scheduling
"""


def generate_questions(week: int) -> list[str]:
    """
    Call OpenRouter (DeepSeek) to generate 5 specific learning reflection
    questions for the given week, grounded in the roadmap content.
    Raises RuntimeError if the LLM call or JSON parse fails.
    """
    import json
    from src.llm_client import call_llm

    week_topic = WEEK_CONTENT.get(week, f"Week {week} of the AI Infrastructure learning plan")

    prompt = f"""You are helping Mahesh Annapureddy — a senior backend engineer (7 years Java/Spring Boot/Kafka, \
Kubernetes, financial payment systems) transitioning to AI Infrastructure Engineer — \
reflect on his weekly learning.

This week (Week {week}) he was studying:
{week_topic}

His unique angle: he connects backend/distributed systems expertise (Kafka, K8s, Spring Boot) \
to AI infrastructure challenges. His LinkedIn goal is to get AI Infrastructure Engineer \
interview offers.

Generate exactly 5 specific, concrete weekly learning reflection questions.

Requirements:
- Specific to THIS week's exact tools and concepts — not generic
- Surface concrete experiences: what he built, what broke, what surprised him, numbers
- Connect to his backend background where relevant (e.g. "How does X compare to Kafka Y?")
- Answerable in 2-4 sentences with specific details
- Help produce authentic LinkedIn content — not textbook answers

Return ONLY a valid JSON array of exactly 5 question strings. No markdown, no explanation:
["Question 1?", "Question 2?", "Question 3?", "Question 4?", "Question 5?"]"""

    raw = call_llm("deepseek", prompt, max_tokens=600)

    # Strip markdown fences if present
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("```")[1].lstrip("json").strip()
        if "```" in cleaned:
            cleaned = cleaned.split("```")[0].strip()

    try:
        questions = json.loads(cleaned)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"generate_questions: JSON parse failed — {e}\nRaw: {raw[:300]}")

    if not isinstance(questions, list) or len(questions) < 3:
        raise RuntimeError(f"generate_questions: expected list of 5, got: {questions}")

    return [str(q) for q in questions[:5]]
