"""
llm_client.py
─────────────
Unified OpenRouter gateway. Resolves logical model keys to model IDs,
calls the OpenAI-compatible API, and falls back across models on failure.
"""

import os
import requests
from src.config import OPENROUTER_API_KEY, DEEPSEEK_MODEL, KIMI_MODEL, MINIMAX_MODEL

_OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

_MODEL_MAP = {
    "deepseek": DEEPSEEK_MODEL,
    "kimi":     KIMI_MODEL,
    "minimax":  MINIMAX_MODEL,
}

# Fallback order when a model call fails
_FALLBACK_CHAIN = ["kimi", "minimax", "deepseek"]


def _call_model(model_id: str, messages: list, max_tokens: int) -> str:
    """Single attempt to call one model via OpenRouter. Raises on failure."""
    api_key = OPENROUTER_API_KEY or os.getenv("OPENROUTER_API_KEY", "")
    if not api_key:
        raise ValueError("OPENROUTER_API_KEY not set")

    resp = requests.post(
        _OPENROUTER_URL,
        headers={
            "Authorization": f"Bearer {api_key}",
            "HTTP-Referer": "linkedin-automation",
            "Content-Type": "application/json",
        },
        json={
            "model":      model_id,
            "messages":   messages,
            "max_tokens": max_tokens,
        },
        timeout=120,
    )
    resp.raise_for_status()
    data = resp.json()
    return data["choices"][0]["message"]["content"]


def call_llm(model_key: str, prompt: str, system: str = "", max_tokens: int = 2000) -> str:
    """
    Call an LLM via OpenRouter with automatic fallback.

    model_key: "deepseek" | "kimi" | "minimax"
    Returns the response text. Raises RuntimeError if all models fail.
    """
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    # Build attempt order: requested model first, then remaining fallbacks
    chain = [model_key] + [m for m in _FALLBACK_CHAIN if m != model_key]
    errors = []

    for key in chain:
        model_id = _MODEL_MAP.get(key, key)
        try:
            result = _call_model(model_id, messages, max_tokens)
            if key != model_key:
                print(f"llm_client: fell back to {key} ({model_id})")
            return result
        except Exception as e:
            errors.append(f"{key}: {e}")
            print(f"llm_client: {key} failed — {e}")

    raise RuntimeError(f"All models failed: {'; '.join(errors)}")
