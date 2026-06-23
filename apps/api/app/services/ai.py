"""Provider-agnostic AI client — Python port of reference/elvis/supabase/functions/_shared/ai.ts.

Works with any OpenAI-compatible Chat Completions endpoint:
  - OpenAI:        AI_BASE_URL=https://api.openai.com/v1            AI_MODEL=gpt-4o-mini
  - Google Gemini: AI_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai
  - Groq / OpenRouter / Together: set their base URL + model
  - Local (Ollama): AI_BASE_URL=http://localhost:11434/v1   AI_MODEL=llama3.1
                    (AI_API_KEY optional)
  - Local (vLLM):   AI_BASE_URL=http://localhost:8000/v1    AI_MODEL=<served-model>

Local-first is a hard requirement (EU data-residency moat): keyless operation with
Ollama/vLLM must keep working. Tool-calling is used for structured-output extraction,
not for the model to choose actions at runtime (governed, deterministic orchestration).

Langfuse tracing is optional: if LANGFUSE_PUBLIC_KEY/LANGFUSE_SECRET_KEY are unset,
calls proceed without tracing (graceful degradation for local dev / offline).
"""

from __future__ import annotations

import json
import logging
import os
from collections.abc import Sequence
from typing import Any

import httpx

logger = logging.getLogger(__name__)

# --- Configuration (read once at import; mirror _shared/ai.ts) ---
AI_BASE_URL = (os.getenv("AI_BASE_URL") or "https://api.openai.com/v1").rstrip("/")
AI_API_KEY = os.getenv("AI_API_KEY") or ""
AI_MODEL = os.getenv("AI_MODEL") or "gpt-4o-mini"
AI_EMBED_MODEL = os.getenv("AI_EMBED_MODEL") or "gemini-embedding-001"
# Must match the pgvector column dimension (taxonomy_nodes.embedding vector(768)).
# gemini-embedding-001 defaults to 3072; request 768. Cosine distance is scale-invariant
# so the reduced (un-normalised) vectors are fine for nearest-neighbour matching.
AI_EMBED_DIM = int(os.getenv("AI_EMBED_DIM") or "768")

# --- Langfuse (optional tracing + evals) ---
_LANGFUSE_PUBLIC_KEY = os.getenv("LANGFUSE_PUBLIC_KEY") or ""
_LANGFUSE_SECRET_KEY = os.getenv("LANGFUSE_SECRET_KEY") or ""
_LANGFUSE_BASE_URL = os.getenv("LANGFUSE_BASE_URL") or "http://localhost:3000"

_langfuse_client: Any = None


def _get_langfuse() -> Any | None:
    """Return a Langfuse client if configured, else None (graceful degradation)."""
    global _langfuse_client
    if _langfuse_client is not None:
        return _langfuse_client
    if not _LANGFUSE_PUBLIC_KEY or not _LANGFUSE_SECRET_KEY:
        return None
    try:
        from langfuse import Langfuse

        _langfuse_client = Langfuse(
            public_key=_LANGFUSE_PUBLIC_KEY,
            secret_key=_LANGFUSE_SECRET_KEY,
            host=_LANGFUSE_BASE_URL,
        )
        return _langfuse_client
    except Exception:
        logger.warning(
            "Langfuse configured but client init failed; tracing disabled",
            exc_info=True,
        )
        return None


class AIProviderError(RuntimeError):
    """Raised on AI provider HTTP failure. Carries .status."""

    def __init__(self, message: str, status: int | None = None) -> None:
        super().__init__(message)
        self.status = status


class RateLimitError(AIProviderError):
    pass


class QuotaError(AIProviderError):
    pass


class NoStructuredResponseError(AIProviderError):
    pass


def _headers() -> dict[str, str]:
    h = {"Content-Type": "application/json"}
    # Local servers (Ollama/vLLM) usually need no key; only send one if configured.
    if AI_API_KEY:
        h["Authorization"] = f"Bearer {AI_API_KEY}"
    return h


def _map_http_error(status: int, detail: str) -> AIProviderError:
    if status == 429:
        return RateLimitError("Rate limit exceeded. Please try again shortly.", status)
    if status == 402:
        return QuotaError("Usage credits/quota required for the configured AI provider.", status)
    return AIProviderError(f"AI provider error {status}: {detail[:200]}", status)


def call_tool(
    *,
    system: str,
    user: str,
    tool: dict[str, Any],
    tool_name: str,
    timeout: float = 120.0,
    trace_name: str | None = None,
) -> dict[str, Any]:
    """Single-tool structured call against an OpenAI-compatible endpoint.

    Returns the parsed tool-call arguments. Raises AIProviderError on HTTP failure,
    NoStructuredResponseError if the model returns no tool call.

    Tool-calling is used purely for structured-output extraction (forced tool_choice),
    never for the model to invoke external tools at runtime — preserving governed,
    deterministic orchestration.
    """
    body = {
        "model": AI_MODEL,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "tools": [tool],
        "tool_choice": {"type": "function", "function": {"name": tool_name}},
    }

    lf = _get_langfuse()
    obs = None
    if lf is not None:
        obs = lf.start_observation(
            name=trace_name or f"call_tool:{tool_name}",
            as_type="generation",
            model=AI_MODEL,
            input={"system": system, "user": user, "tool": tool},
        )

    try:
        with httpx.Client(timeout=timeout) as client:
            resp = client.post(f"{AI_BASE_URL}/chat/completions", headers=_headers(), json=body)
    except httpx.RequestError as exc:
        err = AIProviderError(f"AI provider unreachable: {exc}")
        if obs is not None:
            obs.end(level="ERROR", status_message=str(err), usage_details={})
        raise err from exc

    if resp.status_code != 200:
        detail = resp.text
        if resp.status_code not in (429, 402):
            logger.error("AI provider error: %s %s", resp.status_code, detail[:500])
        err = _map_http_error(resp.status_code, detail)
        if obs is not None:
            obs.end(level="ERROR", status_message=str(err), usage_details={})
        raise err

    data = resp.json()
    tool_calls = data.get("choices", [{}])[0].get("message", {}).get("tool_calls", [])
    if not tool_calls:
        err = NoStructuredResponseError("No structured response returned from AI")
        if obs is not None:
            obs.end(level="ERROR", status_message=str(err), usage_details={})
        raise err

    arguments = tool_calls[0]["function"]["arguments"]
    parsed = json.loads(arguments)

    if obs is not None:
        usage = data.get("usage", {})
        obs.end(
            output=parsed,
            usage_details={
                "input": usage.get("prompt_tokens", 0),
                "output": usage.get("completion_tokens", 0),
                "total": usage.get("total_tokens", 0),
            },
        )

    return parsed


def embed(
    input: str | Sequence[str],
    timeout: float = 60.0,
    trace_name: str | None = None,
) -> list[list[float]]:
    """Embed one or more strings via the OpenAI-compatible /embeddings endpoint.

    Returns a list of embedding vectors (one per input string). For a single string,
    returns a list with one vector.
    """
    if isinstance(input, str):
        input_list = [input]
    else:
        input_list = list(input)

    body: dict[str, Any] = {"model": AI_EMBED_MODEL, "input": input_list}
    # Some providers don't support the `dimensions` param; send it when configured.
    if AI_EMBED_DIM:
        body["dimensions"] = AI_EMBED_DIM

    lf = _get_langfuse()
    obs = None
    if lf is not None:
        obs = lf.start_observation(
            name=trace_name or "embed",
            as_type="embedding",
            model=AI_EMBED_MODEL,
            input={"input_count": len(input_list)},
        )

    try:
        with httpx.Client(timeout=timeout) as client:
            resp = client.post(f"{AI_BASE_URL}/embeddings", headers=_headers(), json=body)
    except httpx.RequestError as exc:
        err = AIProviderError(f"AI provider unreachable: {exc}")
        if obs is not None:
            obs.end(level="ERROR", status_message=str(err), usage_details={})
        raise err from exc

    if resp.status_code != 200:
        detail = resp.text
        err = _map_http_error(resp.status_code, detail)
        if obs is not None:
            obs.end(level="ERROR", status_message=str(err), usage_details={})
        raise err

    data = resp.json()
    embeddings = [item["embedding"] for item in data.get("data", [])]

    if obs is not None:
        usage = data.get("usage", {})
        obs.end(
            output={"embedding_count": len(embeddings)},
            usage_details={
                "input": usage.get("prompt_tokens", 0),
                "total": usage.get("total_tokens", 0),
            },
        )

    return embeddings


def to_vector_literal(v: list[float]) -> str:
    """pgvector accepts a string like '[0.1,0.2,...]'."""
    return "[" + ",".join(str(x) for x in v) + "]"
