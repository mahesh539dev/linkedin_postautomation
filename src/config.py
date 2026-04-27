"""Central config — all env vars and constants."""
import os
from dotenv import load_dotenv
load_dotenv()

ANTHROPIC_API_KEY   = os.getenv("ANTHROPIC_API_KEY", "")
BUFFER_ACCESS_TOKEN = os.getenv("BUFFER_ACCESS_TOKEN", "")
BUFFER_PROFILE_ID   = os.getenv("BUFFER_PROFILE_ID", "")
APPROVAL_SECRET     = os.getenv("APPROVAL_SECRET", "change-me")
SMTP_EMAIL          = os.getenv("SMTP_EMAIL", "")
SMTP_PASSWORD       = os.getenv("SMTP_PASSWORD", "")
NOTIFY_EMAIL        = os.getenv("NOTIFY_EMAIL", "mahesh.annapureddy5@gmail.com")
BASE_URL            = os.getenv("BASE_URL", "http://localhost:5000")
PORT                = int(os.getenv("PORT", 5000))
JOURNEY_START_DATE  = os.getenv("JOURNEY_START_DATE", "2025-01-06")
TUESDAY_START_THIS_WEEK = os.getenv("TUESDAY_START_THIS_WEEK", "false").lower() == "true"
CLAUDE_MODEL        = "claude-sonnet-4-20250514"
BUFFER_API_BASE     = "https://api.bufferapp.com/1"

ENGINEER_CONTEXT = """
Name: Mahesh Annapureddy
Role: Senior Consultant at Capgemini, transitioning to AI Infrastructure Engineer
Background: 7 years Java/Spring Boot/Apache Kafka (500K+ events/day),
            Kubernetes, Docker, OpenShift, PCI-DSS, financial systems, Toronto Canada
Learning: Python, NumPy, Pandas, FastAPI, Embeddings, Pinecone, ChromaDB,
          LangChain, LangGraph, HuggingFace, vLLM, MLflow, LangSmith, Arize AI
Unique edge: Distributed systems thinker mapping Kafka/K8s expertise to AI infrastructure
Goal: AI Infrastructure Engineer role by Week 9 of 90-day learning plan
"""

WEEK_THEMES = {
    2: "Python Foundations",
    3: "Embeddings and Vectors",
    4: "Vector DBs and RAG",
    5: "FastAPI and Kafka AI Pipelines",
    6: "LangChain and LangGraph",
    7: "LLM Inference and vLLM",
    8: "Observability and MLflow",
    9: "Production AI and Hiring Push",
}

FULL_SCHEDULE = [
    ("Monday",    "10:00", "industry_news",  "Biggest AI/infra news — sharp backend take"),
    ("Tuesday",   "17:00", "bridge",         "Backend to AI concept analogy from your expertise"),
    ("Wednesday", "10:00", "industry_trend", "Broader AI infrastructure trend or tool update"),
    ("Thursday",  "17:00", "learning",       "What YOU learned or built this week"),
    ("Friday",    "10:00", "opinion",        "Bold hot take — polarising and memorable"),
]

TUESDAY_START_SCHEDULE = [
    ("Tuesday",   "17:00", "bridge",         "Backend to AI concept analogy from your expertise"),
    ("Wednesday", "10:00", "industry_trend", "Broader AI infrastructure trend or tool update"),
    ("Thursday",  "17:00", "learning",       "What YOU learned or built this week"),
    ("Friday",    "10:00", "opinion",        "Bold hot take — polarising and memorable"),
]

LEARNING_QUESTIONS = {
    2: ["What Python concept surprised you most coming from Java?",
        "What did NumPy teach you about performance?",
        "Did you build anything this week? Describe it in one sentence.",
        "What backend concept showed up unexpectedly in Python?",
        "What confused you at first that later clicked?"],
    3: ["How would you explain embeddings to a Java engineer in one sentence?",
        "What clicked about vector math or semantic similarity?",
        "Did you set up a vector DB? What surprised you?",
        "Any latency or performance numbers worth sharing?",
        "What confused you that later made sense?"],
    4: ["Did you build a RAG prototype? What did it do?",
        "What surprised you about retrieval quality?",
        "How does vector search feel compared to SQL?",
        "What was the biggest technical challenge?",
        "What would you do differently now?"],
    5: ["How does FastAPI compare to Spring Boot?",
        "Did you connect Kafka to any AI component?",
        "What was harder or easier than expected?",
        "Any interesting benchmark numbers?",
        "What Spring pattern did you recognise in AI?"],
    6: ["What was your first working LangChain chain or agent?",
        "What debugging challenge came up?",
        "How does LangGraph feel vs what you know from Spring?",
        "What did the agent get wrong that required fixing?",
        "What use case excites you most with agents?"],
    7: ["What inference engine did you try? Any numbers?",
        "What optimization had the biggest impact on speed or cost?",
        "How does LLM throughput tuning compare to Kafka tuning?",
        "What trade-offs surprised you?",
        "What would you benchmark differently next time?"],
    8: ["What did MLflow or LangSmith reveal that surprised you?",
        "What does good AI observability look like vs Kafka monitoring?",
        "What metric would you definitely alert on in production?",
        "How does tracing change your architecture thinking?",
        "What would you monitor that most teams miss?"],
    9: ["What does your complete AI system architecture look like?",
        "Biggest technical insight from 9 weeks?",
        "What would you tell a backend engineer starting this journey today?",
        "What are you most confident about for interviews?",
        "What gap do you still want to close?"],
}

AUTO_LEARNING_NOTES = {
    2: "Python OOP, NumPy arrays. Vectorization equals Kafka batch processing — same throughput vs latency tradeoff. Built CLI task manager with JSON persistence.",
    3: "Embeddings are coordinates in semantic space. king minus man plus woman equals queen. Set up Pinecone. 15 to 50ms query for 500K vectors.",
    4: "RAG prototype with Claude API plus Pinecone plus FastAPI. Retrieval quality matters more than generation quality. Bad vector search equals bad RAG.",
    5: "FastAPI type hints replace Spring Boot annotations. Connected Kafka consumer to embedding pipeline.",
    6: "LangChain chains equal Spring Integration pipelines. LangGraph equals Spring State Machine. Built research agent.",
    7: "vLLM continuous batching equals Kafka linger.ms. 120 tokens per second vs 45 naive. 4-bit quantization gives 3x memory reduction with 2 percent quality drop.",
    8: "LangSmith traces LLM chains like distributed tracing. MLflow equals Git for experiments. Arize monitors drift like consumer lag alerting.",
    9: "Complete system: Kafka to embeddings to Pinecone to RAG to vLLM to LangSmith. Backend engineers solve AI infra faster because we think in systems.",
}
