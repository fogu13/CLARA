"""Provider-agnostic AI client — Python port of reference/elvis/supabase/functions/_shared/ai.ts.

Works with any OpenAI-compatible Chat Completions endpoint. EU-first defaults:
  - Mistral (FR, default): AI_BASE_URL=https://api.mistral.ai/v1  AI_MODEL=mistral-small-latest
                           AI_EMBED_MODEL=mistral-embed  AI_EMBED_DIM=0
  - Local (Ollama): AI_BASE_URL=http://localhost:11434/v1   AI_MODEL=llama3.1
                    (AI_API_KEY optional)
  - Local (vLLM):   AI_BASE_URL=http://localhost:8000/v1    AI_MODEL=<served-model>
  - Any other OpenAI-compatible host works technically, but see provider_residency():
    with CLARA_AI_REQUIRE_EU=1 a non-EU provider is refused at boot and in Settings.

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
# Defaults are the EU provider production runs on (render.yaml / DEPLOY.md). The
# earlier defaults (api.openai.com + gpt-4o-mini + gemini-embedding-001) put a
# US provider one missing env var away from receiving customer feedback, which
# contradicts the product's residency promise.
AI_BASE_URL = (os.getenv("AI_BASE_URL") or "https://api.mistral.ai/v1").rstrip("/")
AI_API_KEY = os.getenv("AI_API_KEY") or ""
AI_MODEL = os.getenv("AI_MODEL") or "mistral-small-latest"
AI_EMBED_MODEL = os.getenv("AI_EMBED_MODEL") or "mistral-embed"
# Must match the pgvector column dimension of taxonomy_nodes.embedding — vector(768)
# from migration 003, or vector(1024) once 012 has been applied for mistral-embed.
# 0 = do not send the `dimensions` parameter (mistral-embed rejects it and is a
# fixed 1024). Models that accept it (gemini-embedding-001 defaults to 3072)
# should request the column width explicitly.
AI_EMBED_DIM = int(os.getenv("AI_EMBED_DIM") or "0")
# Embeddings may live on a different provider than chat. Unset = same host and key
# as chat, which is every existing deployment and the keyless Ollama path. Needed
# because chat-only gateways exist: OpenCode Zen serves 61 chat models and 404s on
# /embeddings, so no AI_EMBED_MODEL value can make embeddings work there.
AI_EMBED_BASE_URL = (os.getenv("AI_EMBED_BASE_URL") or "").rstrip("/")
AI_EMBED_API_KEY = os.getenv("AI_EMBED_API_KEY") or ""

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


def effective_embed_base_url() -> str:
    # Falls back to the chat host, so an unset AI_EMBED_BASE_URL behaves exactly
    # as before the split. No runtime override: this is deployment topology, not
    # a Settings-GUI knob.
    return (os.getenv("AI_EMBED_BASE_URL") or AI_EMBED_BASE_URL).rstrip("/") or effective_base_url()


def effective_embed_api_key() -> str:
    # Only falls back to the chat key when the embed host is the chat host —
    # sending the chat provider's key to a different provider is a credential
    # leak, so a split host with no AI_EMBED_API_KEY sends no key at all.
    explicit = os.getenv("AI_EMBED_API_KEY") or AI_EMBED_API_KEY
    if explicit:
        return explicit
    return effective_api_key() if effective_embed_base_url() == effective_base_url() else ""


# --- Data residency ---------------------------------------------------------
# The pitch: feedback never leaves the EU and never passes through US or Chinese
# providers. This module is the one place every AI call goes through, so the
# classification lives here and is surfaced in /system-config and the Settings
# page. Enforcement is opt-in (CLARA_AI_REQUIRE_EU=1) so local dev can use any
# endpoint, and fail-closed once on: a non-EU host refuses to boot, mirroring
# CLARA_REQUIRE_AUTH.
#
# Host suffixes are matched on the hostname only (no path/scheme games). The
# lists are deliberately conservative: an unrecognised host is "unknown", which
# the EU-only mode also refuses unless the operator allowlists it explicitly
# via CLARA_AI_EU_HOSTS (e.g. a private EU vLLM gateway on a public hostname).
EU_PROVIDER_HOST_SUFFIXES: tuple[str, ...] = (
    "mistral.ai",
    "aleph-alpha.com",
    "ionos.com",
    "ionos.de",
    "scaleway.com",
    "scw.cloud",
    "ovh.net",
    "ovhcloud.com",
    "stackit.cloud",
    "stackit.de",
    "t-systems.com",
    "telekom.de",
    "infomaniak.com",
    "exoscale.com",
    "hetzner.cloud",
    "cloud.langfuse.com",
)
NON_EU_PROVIDER_HOST_SUFFIXES: tuple[str, ...] = (
    "openai.com",
    "anthropic.com",
    "googleapis.com",
    "google.com",
    "groq.com",
    "together.xyz",
    "together.ai",
    "openrouter.ai",
    "perplexity.ai",
    "cohere.ai",
    "cohere.com",
    "x.ai",
    "fireworks.ai",
    "cerebras.ai",
    "deepinfra.com",
    "replicate.com",
    "huggingface.co",
    "amazonaws.com",
    "azure.com",
    "microsoft.com",
    "us.cloud.langfuse.com",
    "deepseek.com",
    "aliyuncs.com",
    "moonshot.cn",
    "baidubce.com",
    "volces.com",
    "bigmodel.cn",
    "minimax.chat",
)
_SELF_HOSTED_HOSTS = frozenset({"localhost", "127.0.0.1", "0.0.0.0", "::1", "host.docker.internal"})
RESIDENCY_EU = "eu"
RESIDENCY_SELF_HOSTED = "self_hosted"
RESIDENCY_NON_EU = "non_eu"
RESIDENCY_UNKNOWN = "unknown"


def _is_private_host(host: str) -> bool:
    if host in _SELF_HOSTED_HOSTS or "." not in host:
        return True
    if host.endswith((".local", ".internal", ".lan", ".home.arpa")):
        return True
    parts = host.split(".")
    if len(parts) == 4 and all(part.isdigit() for part in parts):
        first, second = int(parts[0]), int(parts[1])
        return (
            first == 10
            or (first == 172 and 16 <= second <= 31)
            or (first == 192 and second == 168)
            or first == 127
        )
    return False


def provider_residency(base_url: str | None) -> str:
    """Classify where a provider URL sends data: eu | self_hosted | non_eu | unknown."""
    if not base_url:
        return RESIDENCY_UNKNOWN
    try:
        host = (urlparse(base_url).hostname or "").lower()
    except ValueError:
        return RESIDENCY_UNKNOWN
    if not host:
        return RESIDENCY_UNKNOWN
    if _is_private_host(host):
        return RESIDENCY_SELF_HOSTED
    # Longest-suffix-wins so "us.cloud.langfuse.com" beats "cloud.langfuse.com".
    best: tuple[int, str] | None = None
    for suffix, verdict in (
        *((suffix, RESIDENCY_EU) for suffix in EU_PROVIDER_HOST_SUFFIXES),
        *((suffix, RESIDENCY_NON_EU) for suffix in NON_EU_PROVIDER_HOST_SUFFIXES),
    ):
        if host == suffix or host.endswith("." + suffix):
            if best is None or len(suffix) > best[0]:
                best = (len(suffix), verdict)
    return best[1] if best else RESIDENCY_UNKNOWN


def _truthy(value: str | None) -> bool:
    return (value or "").strip().lower() in {"1", "true", "yes", "on"}


AI_REQUIRE_EU = _truthy(os.getenv("CLARA_AI_REQUIRE_EU"))
AI_EU_EXTRA_HOSTS = frozenset(
    host.strip().lower()
    for host in (os.getenv("CLARA_AI_EU_HOSTS") or "").split(",")
    if host.strip()
)


class ResidencyViolation(RuntimeError):
    """A provider outside the EU (or unknown) was configured while EU-only mode is on."""


def residency_allowed(base_url: str | None) -> bool:
    residency = provider_residency(base_url)
    if residency in (RESIDENCY_EU, RESIDENCY_SELF_HOSTED):
        return True
    try:
        host = (urlparse(base_url or "").hostname or "").lower()
    except ValueError:
        host = ""
    return bool(host) and host in AI_EU_EXTRA_HOSTS


def assert_residency_allowed(base_url: str | None, *, purpose: str) -> None:
    """Raise ResidencyViolation when EU-only mode is on and the host is not EU/self-hosted."""
    if not AI_REQUIRE_EU or residency_allowed(base_url):
        return
    raise ResidencyViolation(
        f"{purpose} points at {urlparse(base_url or '').hostname or base_url!r}, classified as "
        f"'{provider_residency(base_url)}'. CLARA_AI_REQUIRE_EU=1 refuses providers outside the "
        "EU; use an EU-hosted or self-hosted endpoint, or allowlist a private EU host via "
        "CLARA_AI_EU_HOSTS."
    )


def eu_only_enforced() -> bool:
    return AI_REQUIRE_EU

# --- Langfuse (optional tracing + evals) ---
_LANGFUSE_PUBLIC_KEY = os.getenv("LANGFUSE_PUBLIC_KEY") or ""
_LANGFUSE_SECRET_KEY = os.getenv("LANGFUSE_SECRET_KEY") or ""
_LANGFUSE_BASE_URL = os.getenv("LANGFUSE_BASE_URL") or "http://localhost:3000"

# Boot-time residency gate (fail closed, like CLARA_REQUIRE_AUTH): traces carry
# feedback text too, so a configured Langfuse host is checked as well.
if AI_REQUIRE_EU:
    assert_residency_allowed(effective_base_url(), purpose="AI_BASE_URL")
    assert_residency_allowed(effective_embed_base_url(), purpose="AI_EMBED_BASE_URL")
    if _LANGFUSE_PUBLIC_KEY and _LANGFUSE_SECRET_KEY:
        assert_residency_allowed(_LANGFUSE_BASE_URL, purpose="LANGFUSE_BASE_URL")

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
    """Raised on AI provider HTTP failure.

    Carries .status, the .host it came from, and which .endpoint was called —
    "chat" or "embeddings". The endpoint is recorded at the raise site rather
    than inferred later from host equality: when both providers point at the
    same host, inference cannot tell the two calls apart and names the wrong
    env var, which is exactly how a chat misconfiguration once got reported as
    an embeddings key problem.
    """

    def __init__(
        self,
        message: str,
        status: int | None = None,
        host: str | None = None,
        endpoint: str | None = None,
    ) -> None:
        super().__init__(message)
        self.status = status
        self.host = host
        self.endpoint = endpoint


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
    # Which call failed decides which knobs to name, and it is read from the
    # error, not inferred from host equality — with both providers on one host
    # the two calls are indistinguishable and inference names the wrong var.
    base = exc.host or effective_base_url()
    host = urlparse(base).hostname or base
    is_embed = exc.endpoint == "embeddings"
    # AI_EMBED_API_KEY only exists as a distinct knob when a split is configured;
    # otherwise embeddings authenticate with the chat key and that is the one to fix.
    split = effective_embed_base_url() != effective_base_url()
    key_var = "AI_EMBED_API_KEY" if (is_embed and split) else "AI_API_KEY"

    if isinstance(exc, QuotaError):
        message = f"AI provider ({host}) is out of credits — top up the account for {key_var}."
    elif isinstance(exc, RateLimitError):
        message = f"AI provider ({host}) rate limit hit — try again shortly."
    elif isinstance(exc, NoStructuredResponseError):
        message = f"AI model '{effective_model()}' did not return a structured answer."
    elif exc.status in (401, 403):
        message = f"AI provider ({host}) rejected the API key — check {key_var}."
    elif exc.status is not None and 400 <= exc.status < 500:
        if is_embed:
            message = (
                f"Embedding provider ({host}) rejected the request ({exc.status}) — check that"
                f" AI_EMBED_MODEL ('{effective_embed_model()}') is served by AI_EMBED_BASE_URL."
                " A 404 usually means the host has no /embeddings endpoint at all."
            )
        else:
            message = (
                f"AI provider ({host}) rejected the request ({exc.status}) — check that"
                f" AI_MODEL ('{effective_model()}') and AI_EMBED_MODEL"
                f" ('{effective_embed_model()}') are served by AI_BASE_URL."
            )
    elif exc.status is None:
        message = f"AI provider ({host}) unreachable."
    else:
        message = f"AI provider ({host}) error {exc.status}."

    return message + _settings_override_note(is_embed)


def _settings_override_note(is_embed: bool) -> str:
    """Say so when the Settings GUI, not the env, is in control.

    A base URL saved in Settings is persisted as an "ai" connector config and
    re-applied on every boot, so it silently beats .env and survives a restart.
    Telling someone to "check AI_BASE_URL" while that override is active sends
    them to edit a file that has no effect — which is exactly how a demo-eve
    debugging session went. Embedding config is env-only, so a pure embeddings
    failure gets no note.
    """
    if is_embed:
        return ""
    active = sorted(k for k in ("base_url", "model", "api_key") if k in _RUNTIME_OVERRIDE)
    if not active:
        return ""
    return (
        f" Note: {', '.join(active)} currently come from the Settings page,"
        " which overrides the server env — change it there, not in .env."
    )


def _headers(api_key: str | None = None) -> dict[str, str]:
    h = {"Content-Type": "application/json"}
    # Local servers (Ollama/vLLM) usually need no key; only send one if configured.
    key = effective_api_key() if api_key is None else api_key
    if key:
        h["Authorization"] = f"Bearer {key}"
    return h


def _map_http_error(
    status: int, detail: str, host: str | None = None, endpoint: str | None = None
) -> AIProviderError:
    if status == 429:
        return RateLimitError("Rate limit exceeded. Please try again shortly.", status, host, endpoint)
    if status == 402:
        return QuotaError(
            "Usage credits/quota required for the configured AI provider.", status, host, endpoint
        )
    return AIProviderError(f"AI provider error {status}: {detail[:200]}", status, host, endpoint)


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


def _post_with_retry(
    path: str,
    body: dict[str, Any],
    timeout: float,
    *,
    base_url: str | None = None,
    api_key: str | None = None,
    endpoint: str = "chat",
) -> httpx.Response:
    """POST with a bounded retry (3 attempts, exponential backoff, honors
    Retry-After) on 429/5xx/network errors. Other 4xx stay fail-fast.

    The pipeline fires sequential burst batches, so a single throttle event is
    the most likely failure — without retry it silently drops a whole
    enrichment batch or cluster.

    base_url/api_key default to the chat provider; /embeddings passes its own.
    """
    host = base_url or effective_base_url()
    last_exc: httpx.RequestError | None = None
    resp: httpx.Response | None = None
    for attempt in range(_MAX_ATTEMPTS):
        if attempt:
            time.sleep(_retry_delay(resp, attempt - 1))
        try:
            with httpx.Client(timeout=timeout) as client:
                resp = client.post(f"{host}{path}", headers=_headers(api_key), json=body)
        except httpx.RequestError as exc:
            last_exc = exc
            resp = None
            continue
        if resp.status_code == 429 or resp.status_code >= 500:
            continue
        return resp
    if resp is not None:
        return resp  # retries exhausted — caller maps the HTTP error
    raise AIProviderError(
        f"AI provider unreachable: {last_exc}", None, host, endpoint
    ) from last_exc


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
        resp = _post_with_retry("/chat/completions", body, timeout, endpoint="chat")
    except AIProviderError as err:
        if obs is not None:
            obs.end(level="ERROR", status_message=str(err), usage_details={})
        raise

    if resp.status_code != 200:
        detail = resp.text
        if resp.status_code not in (429, 402):
            logger.error("AI provider error: %s %s", resp.status_code, detail[:500])
        err = _map_http_error(resp.status_code, detail, effective_base_url(), "chat")
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


# Providers cap embedding requests on two axes: input count and total tokens.
# Measured against Mistral (Aug 2026): 256 inputs is the hard count cap (257
# rejects), and ~64 max-length (2000-char) signals pass while 96 fail on
# tokens. Both limits halved for margin; the chunker respects whichever bites
# first. /ask embeds up to 501 texts in one call, so without this any
# workspace beyond ~256 signals lost search outright with a 400.
EMBED_MAX_INPUTS = 128
EMBED_MAX_CHARS = 100_000


def _embed_chunks(input_list: list[str]) -> list[list[str]]:
    """Split inputs greedily under both request caps, preserving order.

    A single text longer than EMBED_MAX_CHARS still goes out (alone) — the
    provider's per-input limit is its own to enforce, and dropping the text
    would silently skew retrieval.
    """
    chunks: list[list[str]] = []
    current: list[str] = []
    current_chars = 0
    for text in input_list:
        if current and (
            len(current) >= EMBED_MAX_INPUTS or current_chars + len(text) > EMBED_MAX_CHARS
        ):
            chunks.append(current)
            current, current_chars = [], 0
        current.append(text)
        current_chars += len(text)
    if current:
        chunks.append(current)
    return chunks


def embed(
    input: str | Sequence[str],
    timeout: float = 60.0,
    trace_name: str | None = None,
) -> list[list[float]]:
    """Embed one or more strings via the OpenAI-compatible /embeddings endpoint.

    Returns a list of embedding vectors (one per input string). For a single string,
    returns a list with one vector. Large batches are transparently split into
    multiple requests (see EMBED_MAX_INPUTS/EMBED_MAX_CHARS); order is preserved.
    """
    if isinstance(input, str):
        input_list = [input]
    else:
        input_list = list(input)

    # Some providers don't support the `dimensions` param (Mistral 422s on it);
    # send it only for the env-configured model, where the operator controls
    # both knobs. A GUI-selected embed model gets the provider's default dims.
    send_dimensions = bool(AI_EMBED_DIM) and "embed_model" not in _RUNTIME_OVERRIDE

    lf = _get_langfuse()
    obs = None
    if lf is not None:
        obs = lf.start_observation(
            name=trace_name or "embed",
            as_type="embedding",
            model=AI_EMBED_MODEL,
            input={"input_count": len(input_list)},
        )

    embed_host = effective_embed_base_url()
    embeddings: list[list[float]] = []
    usage_input = 0
    usage_total = 0
    for chunk in _embed_chunks(input_list):
        body: dict[str, Any] = {"model": effective_embed_model(), "input": chunk}
        if send_dimensions:
            body["dimensions"] = AI_EMBED_DIM
        try:
            resp = _post_with_retry(
                "/embeddings",
                body,
                timeout,
                base_url=embed_host,
                api_key=effective_embed_api_key(),
                endpoint="embeddings",
            )
        except AIProviderError as err:
            if obs is not None:
                obs.end(level="ERROR", status_message=str(err), usage_details={})
            raise

        if resp.status_code != 200:
            detail = resp.text
            err = _map_http_error(resp.status_code, detail, embed_host, "embeddings")
            if obs is not None:
                obs.end(level="ERROR", status_message=str(err), usage_details={})
            raise err

        data = resp.json()
        # Sort by index within the chunk: the spec orders the array, but a
        # misordered response would silently pair vectors with wrong texts.
        items = sorted(data.get("data", []), key=lambda item: item.get("index", 0))
        embeddings.extend(item["embedding"] for item in items)
        usage = data.get("usage", {})
        usage_input += usage.get("prompt_tokens", 0)
        usage_total += usage.get("total_tokens", 0)

    if obs is not None:
        obs.end(
            output={"embedding_count": len(embeddings)},
            usage_details={"input": usage_input, "total": usage_total},
        )

    return embeddings


def to_vector_literal(v: list[float]) -> str:
    """pgvector accepts a string like '[0.1,0.2,...]'."""
    return "[" + ",".join(str(x) for x in v) + "]"
