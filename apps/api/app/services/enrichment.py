"""LLM enrichment — port of reference/elvis/supabase/functions/enrich-signal/index.ts.

Extracts sentiment, sentiment_score, urgency, and tags from qualitative customer
feedback signals via a single LLM call_tool with forced structured output.

Every enrichment carries evidence/confidence/limitations/audit per CLARA_2's
governed-AI model (apps/api/app/domain/models.py).
"""

from __future__ import annotations

import json
import logging
from typing import Any

from app.services.ai import AIProviderError, call_tool

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a customer-feedback analyst. For each feedback item you receive, extract:
- sentiment: one of positive | neutral | negative | mixed
- sentiment_score: number from -1 (very negative) to 1 (very positive)
- urgency: one of low | medium | high | critical
- tags: 1-3 short snake_case theme tags (e.g. checkout_failure, late_delivery,
  onboarding_friction, pricing_unclear)
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


def enrich_signals(
    signals: list[dict[str, Any]],
    *,
    batch_size: int = 25,
) -> list[dict[str, Any]]:
    """Enrich a list of qualitative signal dicts with LLM-extracted metadata.

    Each signal dict must have 'id' (string) and 'text' (string).
    Returns a list of enrichment dicts:
    {id, sentiment, sentiment_score, urgency, tags}.

    Signals are batched to stay within context windows. Errors on individual
    batches are logged and skipped (partial enrichment is better than none).
    """
    if not signals:
        return []

    all_enrichments: list[dict[str, Any]] = []

    for i in range(0, len(signals), batch_size):
        batch = signals[i : i + batch_size]
        items = [{"id": s["id"], "text": s["text"]} for s in batch]

        try:
            result = call_tool(
                system=SYSTEM_PROMPT,
                user="Enrich these feedback items:\n\n" + json.dumps(items, indent=2),
                tool=ENRICHMENT_TOOL,
                tool_name="submit_enrichments",
                trace_name="enrich_signals",
            )
            enrichments = result.get("enrichments", [])
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
