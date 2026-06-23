"""Provider-agnostic AI client — Python port of reference/elvis/supabase/functions/_shared/ai.ts.

Phase 0 target. Works with any OpenAI-compatible Chat Completions endpoint:
  - OpenAI:        AI_BASE_URL=https://api.openai.com/v1            AI_MODEL=gpt-4o-mini
  - Google Gemini: AI_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai
  - Groq / OpenRouter / Together: set their base URL + model
  - Local (Ollama): AI_BASE_URL=http://localhost:11434/v1           AI_MODEL=llama3.1  (AI_API_KEY optional)
  - Local (vLLM):   AI_BASE_URL=http://localhost:8000/v1            AI_MODEL=<served-model>

Local-first is a hard requirement (EU data-residency moat): keyless operation with
Ollama/vLLM must keep working. Tool-calling is used for structured-output extraction,
not for the model to choose actions at runtime (governed, deterministic orchestration).

TODO(Phase 0):
  - implement call_tool(system, user, tool_schema, tool_name) -> dict using httpx
  - implement embed(input: str | list[str]) -> list[list[float]]
  - wire Langfuse tracing around every call
  - map HTTP 429 -> RateLimitError, 402 -> QuotaError
  - to_vector_literal(v) -> "[0.1,0.2,...]" for pgvector
"""

from __future__ import annotations

import os
from typing import Any

# --- Configuration (read once at import; mirror _shared/ai.ts) ---
AI_BASE_URL = (os.getenv("AI_BASE_URL") or "https://api.openai.com/v1").rstrip("/")
AI_API_KEY = os.getenv("AI_API_KEY") or ""
AI_MODEL = os.getenv("AI_MODEL") or "gpt-4o-mini"
AI_EMBED_MODEL = os.getenv("AI_EMBED_MODEL") or "gemini-embedding-001"
# Must match the pgvector column dimension (taxonomy_nodes.embedding vector(768)).
AI_EMBED_DIM = int(os.getenv("AI_EMBED_DIM") or "768")


class AIProviderError(RuntimeError):
    """Raised on AI provider HTTP failure. Carries .status."""

    def __init__(self, message: str, status: int | None = None) -> None:
        super().__init__(message)
        self.status = status


class RateLimitError(AIProviderError):
    pass


class QuotaError(AIProviderError):
    pass


def _headers() -> dict[str, str]:
    h = {"Content-Type": "application/json"}
    # Local servers (Ollama/vLLM) usually need no key; only send one if configured.
    if AI_API_KEY:
        h["Authorization"] = f"Bearer {AI_API_KEY}"
    return h


def call_tool(*, system: str, user: str, tool: dict[str, Any], tool_name: str) -> dict[str, Any]:
    """Single-tool structured call against an OpenAI-compatible endpoint.

    Returns the parsed tool-call arguments. Raises AIProviderError on HTTP failure.

    TODO(Phase 0): implement with httpx.AsyncClient; wrap with Langfuse trace.
    """
    raise NotImplementedError("Phase 0: port call_tool from reference/elvis/supabase/functions/_shared/ai.ts")


def embed(input: str | list[str]) -> list[list[float]]:
    """Embed one or more strings via the OpenAI-compatible /embeddings endpoint.

    TODO(Phase 0): implement with httpx; request {model, input, dimensions: AI_EMBED_DIM}.
    """
    raise NotImplementedError("Phase 0: port embed from reference/elvis/supabase/functions/_shared/ai.ts")


def to_vector_literal(v: list[float]) -> str:
    """pgvector accepts a string like '[0.1,0.2,...]'."""
    return "[" + ",".join(str(x) for x in v) + "]"
