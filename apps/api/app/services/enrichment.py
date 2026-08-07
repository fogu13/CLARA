"""LLM enrichment — port of reference/elvis/supabase/functions/enrich-signal/index.ts.

Extracts sentiment, sentiment_score, urgency, and tags from qualitative customer
feedback signals via a single LLM call_tool with forced structured output.

Every enrichment carries evidence/confidence/limitations/audit per CLARA_2's
governed-AI model (apps/api/app/domain/models.py).
"""

from __future__ import annotations

import json
import logging
import os
from copy import deepcopy
from typing import Any

from app.services.ai import AIProviderError, call_tool
from app.services.exemplar_store import format_fewshot

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a customer-feedback analyst. For each feedback item you receive, extract:
- sentiment: one of positive | neutral | negative | mixed
- sentiment_score: number from -1 (very negative) to 1 (very positive)
- urgency: one of low | medium | high | critical. Judge by impact and time-sensitivity:
  - critical: data loss, a security or compliance breach, a full outage, or explicit cancellation/churn intent
  - high: a broken core flow (checkout, login, payment) or a strongly negative experience needing prompt action
  - medium: a notable problem that has a workaround, or friction that is annoying but not blocking
  - low: praise, a general question, or a minor/cosmetic issue
- tags: exactly 2 concise snake_case theme tags naming the specific problem or topic
  (e.g. checkout_failure, payment_error). Add a 3rd only if it is a clearly distinct theme.
  Do not pad with a tag that merely restates the sentiment (e.g. positive_feedback,
  customer_satisfaction) or a generic catch-all.
Return one enrichment per input item, preserving its id."""

ENRICHMENT_TOOL = {
    "type": "function",
    "function": {
        "name": "submit_enrichments",
        "description": "Submit per-item feedback enrichments",
        "parameters": {
            "type": "object",
            "properties": {
                "enrichments": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "string"},
                            "sentiment": {
                                "type": "string",
                                "enum": ["positive", "neutral", "negative", "mixed"],
                            },
                            "sentiment_score": {"type": "number"},
                            "urgency": {
                                "type": "string",
                                "enum": ["low", "medium", "high", "critical"],
                            },
                            "tags": {"type": "array", "items": {"type": "string"}},
                        },
                        "required": ["id", "sentiment", "sentiment_score", "urgency", "tags"],
                    },
                },
            },
            "required": ["enrichments"],
        },
    },
}


# --- Optional enrichment fields, off by default -----------------------------
#
# published_metrics.json (n=100, 18 Jul) is served at GET /model-card/metrics and
# is cited in the thesis as measured under *the production configuration*. Any
# change to the prompt or the tool schema changes the artifact those numbers
# describe. So both additions below are opt-in, and with the flags unset the
# functions return the module constants unchanged — same objects, not merely
# equal ones. Turning a flag on is then a deliberate eval-improve iteration
# (gap -> intervention -> in-run paired A/B), not silent drift.
#
# Separate flags because the in-run paired McNemar design isolates one
# intervention at a time; a single combined flag could not be A/B-tested.

_BASIS_PROMPT = """
- evidence_basis: one of reported_event | mixed | opinion. Judge what the text is
  grounded in, NOT whether you agree with it:
  - reported_event: describes something that happened and could be checked
    ("the payment failed three times", "support never replied")
  - opinion: expresses a preference or judgement with no checkable event
    ("the app feels clunky", "pricing is unfair")
  - mixed: contains both"""

_TYPE_PROMPT = """
- signal_type: one of bug | feature_request | complaint | praise | question |
  churn_risk | compliance_concern. Pick the single best fit; prefer churn_risk
  over complaint when the customer signals leaving, and compliance_concern over
  bug when the issue is regulatory, legal, or a data-protection matter."""

_BASIS_SCHEMA = {"type": "string", "enum": ["reported_event", "mixed", "opinion"]}
_TYPE_SCHEMA = {
    "type": "string",
    "enum": [
        "bug",
        "feature_request",
        "complaint",
        "praise",
        "question",
        "churn_risk",
        "compliance_concern",
    ],
}


def _flag_on(name: str) -> bool:
    return os.getenv(name, "0").lower() not in ("0", "false", "no", "")


def _optional_fields() -> list[tuple[str, str, dict[str, Any]]]:
    """(field, prompt fragment, schema) for each enabled optional field."""
    enabled = []
    if _flag_on("ENRICH_SIGNAL_BASIS"):
        enabled.append(("evidence_basis", _BASIS_PROMPT, _BASIS_SCHEMA))
    if _flag_on("ENRICH_SIGNAL_TYPE"):
        enabled.append(("signal_type", _TYPE_PROMPT, _TYPE_SCHEMA))
    return enabled


def build_system_prompt() -> str:
    """SYSTEM_PROMPT verbatim when no optional field is enabled."""
    extras = _optional_fields()
    if not extras:
        return SYSTEM_PROMPT
    closing = "\nReturn one enrichment per input item"
    head, _, tail = SYSTEM_PROMPT.rpartition(closing)
    return head + "".join(fragment for _, fragment, _ in extras) + closing + tail


def build_enrichment_tool() -> dict[str, Any]:
    """ENRICHMENT_TOOL verbatim when no optional field is enabled."""
    extras = _optional_fields()
    if not extras:
        return ENRICHMENT_TOOL

    tool = deepcopy(ENRICHMENT_TOOL)
    item = tool["function"]["parameters"]["properties"]["enrichments"]["items"]
    for field, _, schema in extras:
        item["properties"][field] = schema
        item["required"].append(field)
    return tool


def enrich_signals(
    signals: list[dict[str, Any]],
    *,
    batch_size: int = 25,
    exemplars: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """Enrich a list of qualitative signal dicts with LLM-extracted metadata.

    Each signal dict must have 'id' (string) and 'text' (string).
    Returns a list of enrichment dicts:
    {id, sentiment, sentiment_score, urgency, tags}.

    When ``exemplars`` (labelled few-shot examples) are passed, they are prepended
    to the prompt to pin the model to the project's tag vocabulary and urgency
    calibration. Exemplars are plain text, so this stays model-agnostic.

    Signals are batched to stay within context windows. Errors on individual
    batches are logged and skipped (partial enrichment is better than none).
    """
    if not signals:
        return []

    fewshot = format_fewshot(exemplars) + "\n\n" if exemplars else ""
    all_enrichments: list[dict[str, Any]] = []

    # Lexical tag canonicalization (ENRICH_TAG_CANON=0 disables): exemplar
    # tags seed the vocabulary; canonical results accumulate so later batches
    # converge on the names earlier batches used.
    canonicalizer = None
    if os.getenv("ENRICH_TAG_CANON", "1").lower() not in ("0", "false", "no"):
        from app.services.tag_canon import TagCanonicalizer

        seed_tags = [t for ex in (exemplars or []) for t in ex.get("tags", [])]
        canonicalizer = TagCanonicalizer(seed_tags)

    for i in range(0, len(signals), batch_size):
        batch = signals[i : i + batch_size]
        items = [{"id": s["id"], "text": s["text"]} for s in batch]

        try:
            result = call_tool(
                system=build_system_prompt(),
                user=fewshot + "Enrich these feedback items:\n\n" + json.dumps(items, indent=2),
                tool=build_enrichment_tool(),
                tool_name="submit_enrichments",
                trace_name="enrich_signals",
            )
            enrichments = result.get("enrichments", [])
            if canonicalizer is not None:
                for enrichment in enrichments:
                    tags = enrichment.get("tags")
                    if isinstance(tags, list):
                        enrichment["tags"] = canonicalizer.canonicalize_all(
                            [str(t) for t in tags]
                        )
            all_enrichments.extend(enrichments)
        except AIProviderError:
            logger.warning(
                "Enrichment batch %d-%d failed, skipping",
                i, i + len(batch), exc_info=True,
            )

    return all_enrichments


def merge_enrichment_into_signal(
    signal: dict[str, Any],
    enrichment: dict[str, Any],
) -> dict[str, Any]:
    """Merge an LLM enrichment into a signal dict, adding audit metadata.

    Adds the enrichment fields plus an `enriched: True` flag and an `audit`
    block recording the model and enrichment source, per CLARA_2's
    evidence/confidence/limitations/audit model.
    """
    from app.services.ai import AI_MODEL

    return {
        **signal,
        "sentiment": enrichment.get("sentiment"),
        "sentiment_score": enrichment.get("sentiment_score"),
        "urgency": enrichment.get("urgency"),
        "tags": enrichment.get("tags", []),
        "enriched": True,
        "audit": {
            "model": AI_MODEL,
            "source": "llm_enrichment",
            "confidence": "derived",
            "limitations": ["LLM-extracted; not human-validated"],
        },
    }
