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


# --- Closed-set routing (science review R3/F9) ------------------------------
#
# The thesis eval measured free-form journey/owner generation intersecting the
# gold vocabulary at ~15%/~1%, while the closed-inventory condition reached
# 0.59/0.40 — yet production kept running the free-form condition. When a
# journey-stage inventory is passed (and ENRICH_ROUTING_CLOSED_SET is on),
# enrichment offers the workspace's own stages as an enum and the model must
# choose from them or abstain; abstention routes to human review and the model
# never invents a stage. Off by default: enabling it is an eval-improve
# iteration, and published_metrics.json describes the flag-off configuration.
# Owner routing joins when an owner registry exists — an enum of invented
# owners would be theater, not routing.

ROUTING_ABSTAIN = "abstain"


def routing_closed_set_enabled() -> bool:
    return os.getenv("ENRICH_ROUTING_CLOSED_SET", "0").lower() not in ("0", "false", "no", "")


def _with_routing(stages: list[str]) -> tuple[str, dict[str, Any]]:
    """(system prompt, tool schema) extended with the closed-set stage field."""
    prompt = SYSTEM_PROMPT + (
        "\n- journey_stage: the ONE stage from this workspace inventory that the"
        ' feedback belongs to, or exactly "abstain" when none fits or you are'
        " unsure. Never invent a stage. Inventory: " + " | ".join(stages)
    )
    tool = deepcopy(ENRICHMENT_TOOL)
    item = tool["function"]["parameters"]["properties"]["enrichments"]["items"]
    item["properties"]["journey_stage"] = {
        "type": "string",
        "enum": [*stages, ROUTING_ABSTAIN],
    }
    item["required"].append("journey_stage")
    return prompt, tool


def enrich_signals(
    signals: list[dict[str, Any]],
    *,
    batch_size: int = 25,
    exemplars: list[dict[str, Any]] | None = None,
    journey_stage_inventory: list[str] | None = None,
) -> list[dict[str, Any]]:
    """Enrich a list of qualitative signal dicts with LLM-extracted metadata.

    Each signal dict must have 'id' (string) and 'text' (string).
    Returns a list of enrichment dicts:
    {id, sentiment, sentiment_score, urgency, tags}.

    When ``exemplars`` (labelled few-shot examples) are passed, they are prepended
    to the prompt to pin the model to the project's tag vocabulary and urgency
    calibration. Exemplars are plain text, so this stays model-agnostic.

    When ``journey_stage_inventory`` is passed and ENRICH_ROUTING_CLOSED_SET is
    on, each enrichment also carries journey_stage — chosen from the inventory
    or "abstain", never invented (closed-set routing, science review R3).

    Signals are batched to stay within context windows. Errors on individual
    batches are logged and skipped (partial enrichment is better than none).
    """
    if not signals:
        return []

    system_prompt, tool = SYSTEM_PROMPT, ENRICHMENT_TOOL
    if journey_stage_inventory and routing_closed_set_enabled():
        system_prompt, tool = _with_routing(sorted(set(journey_stage_inventory)))

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
                system=system_prompt,
                user=fewshot + "Enrich these feedback items:\n\n" + json.dumps(items, indent=2),
                tool=tool,
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

    merged = {
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

    # Closed-set routing (R3): the suggestion fills journey_stage only when the
    # source did not provide one — connector/CSV-provided stages are ground
    # truth the model must not overwrite. Abstention is recorded for the human
    # review queue instead of being silently dropped.
    suggested_stage = enrichment.get("journey_stage")
    if suggested_stage:
        current = str(signal.get("journey_stage") or "").strip()
        stage_unknown = current in ("", "unknown_stage")
        if suggested_stage == "abstain":
            if stage_unknown:
                merged["routing_review"] = "stage_abstained"
        elif stage_unknown:
            merged["journey_stage"] = suggested_stage
            merged["routing_source"] = "closed_set_llm"
    return merged
