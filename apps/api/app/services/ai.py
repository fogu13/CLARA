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
import time
from collections.abc import Sequence
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import httpx
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# Auto-load apps/api/.env so the API + eval scripts pick up AI_* config without a
# manual `source`. override=False so real exported env vars (and test monkeypatches)
# always win over the file. ai.py is the single module that reads AI_* at import,
# so loading here covers every entrypoint.
load_dotenv(Path(__file__).resolve().parents[2] / ".env", override=False)

# --- Configuration (read once at import; mirror _shared/ai.ts) ---
AI_BASE_URL = (os.getenv("AI_BASE_URL") or "https://api.openai.com/v1").rstrip("/")
AI_API_KEY = os.getenv("AI_API_KEY") or ""
AI_MODEL = os.getenv("AI_MODEL") or "gpt-4o-mini"
AI_EMBED_MODEL = os.getenv("AI_EMBED_MODEL") or "gemini-embedding-001"
# Must match the pgvector column dimension (taxonomy_nodes.embedding vector(768)).
# gemini-embedding-001 defaults to 3072; request 768. Cosine distance is scale-invariant
# so the reduced (un-normalised) vectors are fine for nearest-neighbour matching.
AI_EMBED_DIM = int(os.getenv("AI_EMBED_DIM") or "768")

# --- Runtime override (set from the Settings GUI via main.py) ---
# None field = fall back to the env value above. ponytail: a dict, not a
# config framework; the store persists it, this is just the hot copy.
_RUNTIME_OVERRIDE: dict[str, str] = {}


def set_runtime_config(
    *,
    base_url: str | None = None,
    model: str | None = None,
    api_key: str | None = None,
    embed_model: str | None = None,
) -> None:
    for key, value in (
        ("base_url", base_url),
        ("model", model),
        ("api_key", api_key),
        ("embed_model", embed_model),
    ):
        if value:
            _RUNTIME_OVERRIDE[key] = value.rstrip("/") if key == "base_url" else value
        else:
            _RUNTIME_OVERRIDE.pop(key, None)


def effective_base_url() -> str:
    # Override -> live env -> import-time default. Live env keeps test
    # monkeypatching and container env changes working without a reimport.
    return (_RUNTIME_OVERRIDE.get("base_url") or os.getenv("AI_BASE_URL") or AI_BASE_URL).rstrip("/")


def effective_model() -> str:
    return _RUNTIME_OVERRIDE.get("model") or os.getenv("AI_MODEL") or AI_MODEL


def effective_api_key() -> str:
    return _RUNTIME_OVERRIDE.get("api_key") or os.getenv("AI_API_KEY") or AI_API_KEY


def effective_embed_model() -> str:
    return _RUNTIME_OVERRIDE.get("embed_model") or os.getenv("AI_EMBED_MODEL") or AI_EMBED_MODEL

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


def provider_error_detail(exc: AIProviderError) -> str:
    """An actionable sentence for an AI failure, safe to show a signed-in user.

    Names the knob to check rather than echoing the provider's raw body. The
    4xx case matters most: a model name the configured provider doesn't serve
    (e.g. the default embed model `gemini-embedding-001` against a Mistral
    AI_BASE_URL) is a config error that read as "provider unavailable" and sent
    people looking at the provider's status page instead of their own env.
    """
    host = urlparse(effective_base_url()).hostname or effective_base_url()
    if isinstance(exc, QuotaError):
        return f"AI provider ({host}) is out of credits — top up the account for AI_API_KEY."
    if isinstance(exc, RateLimitError):
        return f"AI provider ({host}) rate limit hit — try again shortly."
    if isinstance(exc, NoStructuredResponseError):
        return f"AI model '{effective_model()}' did not return a structured answer."
    if exc.status in (401, 403):
        return f"AI provider ({host}) rejected the API key — check AI_API_KEY."
    if exc.status is not None and 400 <= exc.status < 500:
        return (
            f"AI provider ({host}) rejected the request ({exc.status}) — check that"
            f" AI_MODEL ('{effective_model()}') and AI_EMBED_MODEL"
            f" ('{effective_embed_model()}') are served by AI_BASE_URL."
        )
    if exc.status is None:
        return f"AI provider ({host}) unreachable."
    return f"AI provider ({host}) error {exc.status}."


def _headers() -> dict[str, str]:
    h = {"Content-Type": "application/json"}
    # Local servers (Ollama/vLLM) usually need no key; only send one if configured.
    if effective_api_key():
        h["Authorization"] = f"Bearer {effective_api_key()}"
    return h


def _map_http_error(status: int, detail: str) -> AIProviderError:
    if status == 429:
        return RateLimitError("Rate limit exceeded. Please try again shortly.", status)
    if status == 402:
        return QuotaError("Usage credits/quota required for the configured AI provider.", status)
    return AIProviderError(f"AI provider error {status}: {detail[:200]}", status)


_MAX_ATTEMPTS = 3


def _retry_delay(resp: httpx.Response | None, attempt: int) -> float:
    if resp is not None:
        retry_after = resp.headers.get("retry-after")
        if retry_after:
            try:
                return min(float(retry_after), 10.0)
            except ValueError:
                pass
    return 0.5 * (2**attempt)


def _post_with_retry(path: str, body: dict[str, Any], timeout: float) -> httpx.Response:
    """POST with a bounded retry (3 attempts, exponential backoff, honors
    Retry-After) on 429/5xx/network errors. Other 4xx stay fail-fast.

    The pipeline fires sequential burst batches, so a single throttle event is
    the most likely failure — without retry it silently drops a whole
    enrichment batch or cluster.
    """
    last_exc: httpx.RequestError | None = None
    resp: httpx.Response | None = None
    for attempt in range(_MAX_ATTEMPTS):
        if attempt:
            time.sleep(_retry_delay(resp, attempt - 1))
        try:
            with httpx.Client(timeout=timeout) as client:
                resp = client.post(f"{effective_base_url()}{path}", headers=_headers(), json=body)
        except httpx.RequestError as exc:
            last_exc = exc
            resp = None
            continue
        if resp.status_code == 429 or resp.status_code >= 500:
            continue
        return resp
    if resp is not None:
        return resp  # retries exhausted — caller maps the HTTP error
    raise AIProviderError(f"AI provider unreachable: {last_exc}") from last_exc


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
        "model": effective_model(),
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "tools": [tool],
        "tool_choice": {"type": "function", "function": {"name": tool_name}},
    }
    # Pin sampling when AI_TEMPERATURE is set (eval determinism). Unset = provider
    # default, so normal runtime behaviour is unchanged.
    _temp = os.getenv("AI_TEMPERATURE")
    if _temp:
        try:
            body["temperature"] = float(_temp)
        except ValueError:
            logger.warning("Ignoring non-numeric AI_TEMPERATURE=%r", _temp)

    lf = _get_langfuse()
    obs = None
    if lf is not None:
        obs = lf.start_observation(
            name=trace_name or f"call_tool:{tool_name}",
            as_type="generation",
            model=effective_model(),
            input={"system": system, "user": user, "tool": tool},
        )

    try:
        resp = _post_with_retry("/chat/completions", body, timeout)
    except AIProviderError as err:
        if obs is not None:
            obs.end(level="ERROR", status_message=str(err), usage_details={})
        raise

    if resp.status_code != 200:
        detail = resp.text
        if resp.status_code not in (429, 402):
            logger.error("AI provider error: %s %s", resp.status_code, detail[:500])
        err = _map_http_error(resp.status_code, detail)
        if obs is not None:
            obs.end(level="ERROR", status_message=str(err), usage_details={})
        raise err

    data = resp.json()
    # `or [{}]`: an empty choices list must raise NoStructuredResponseError, not IndexError.
    tool_calls = (data.get("choices") or [{}])[0].get("message", {}).get("tool_calls", [])
    if not tool_calls:
        err = NoStructuredResponseError("No structured response returned from AI")
        if obs is not None:
            obs.end(level="ERROR", status_message=str(err), usage_details={})
        raise err

    try:
        arguments = tool_calls[0]["function"]["arguments"]
        parsed = json.loads(arguments)
    except (KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
        err = NoStructuredResponseError(f"Malformed tool-call arguments from AI: {exc}")
        if obs is not None:
            obs.end(level="ERROR", status_message=str(err), usage_details={})
        raise err from exc

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

    body: dict[str, Any] = {"model": effective_embed_model(), "input": input_list}
    # Some providers don't support the `dimensions` param (Mistral 422s on it);
    # send it only for the env-configured model, where the operator controls
    # both knobs. A GUI-selected embed model gets the provider's default dims.
    if AI_EMBED_DIM and "embed_model" not in _RUNTIME_OVERRIDE:
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
        resp = _post_with_retry("/embeddings", body, timeout)
    except AIProviderError as err:
        if obs is not None:
            obs.end(level="ERROR", status_message=str(err), usage_details={})
        raise

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
