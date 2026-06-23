"""LLM synthesis — port of reference/elvis/supabase/functions/synthesize-insights/index.ts.

Clusters enriched signals by primary tag, computes deterministic cross-signal
severity, and calls the LLM to synthesize an actionable insight per cluster.

Design decision #3 (from Elvis): severity is computed deterministically from
urgency + volume + negativity — the LLM is explicitly told NOT to set it.
"""

from __future__ import annotations

import json
import logging
from collections import defaultdict
from typing import Any

from app.services.ai import AIProviderError, call_tool

logger = logging.getLogger(__name__)

URGENCY_RANK: dict[str, int] = {"low": 1, "medium": 2, "high": 3, "critical": 4}

SYSTEM_PROMPT = (
    "You are a customer-insight synthesist. Given a cluster of related "
    "customer signals (all about the same theme), produce a single "
    "actionable insight:\n"
    "- title: short, specific\n"
    "- summary: 1-2 sentences citing the evidence\n"
    "- category: one of content_clarity | product_issue | churn_risk | "
    "campaign_performance | ux_friction | sentiment_shift | engagement_drop "
    "| positive_trend | compliance_concern\n"
    "- impact_score: 0-10\n"
    "- confidence: 0-1\n"
    "- target_team: one of marketing | product | cx | sales | engineering\n"
    "- suggested_actions: up to 2 items, each with type, title, description, "
    "priority\n"
    "Do NOT set severity — it is computed separately."
)

SYNTHESIS_TOOL = {
    "type": "function",
    "function": {
        "name": "submit_insight",
        "parameters": {
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "summary": {"type": "string"},
                "category": {"type": "string"},
                "impact_score": {"type": "number"},
                "confidence": {"type": "number"},
                "target_team": {"type": "string"},
                "suggested_actions": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "type": {"type": "string"},
                            "title": {"type": "string"},
                            "description": {"type": "string"},
                            "priority": {"type": "integer"},
                        },
                        "required": ["type", "title", "description", "priority"],
                    },
                },
            },
            "required": [
                "title",
                "summary",
                "category",
                "impact_score",
                "confidence",
                "target_team",
                "suggested_actions",
            ],
        },
    },
}


def cross_signal_severity(signals: list[dict[str, Any]]) -> str:
    """Deterministic cross-signal severity — port of Elvis's synthesize-insights:26-36.

    Composite of the strongest urgency among member signals, the volume of
    corroborating signals, and how negative the cluster is.
    """
    if not signals:
        return "low"

    max_urgency = max(
        (URGENCY_RANK.get(s.get("urgency", "medium"), 2) for s in signals),
        default=1,
    )
    volume = len(signals)
    score = max_urgency + min(3, volume // 2)

    neg_frac = sum(1 for s in signals if s.get("sentiment") == "negative") / volume
    if neg_frac >= 0.6:
        score += 1

    if score >= 6:
        return "critical"
    if score >= 4:
        return "high"
    if score >= 2:
        return "medium"
    return "low"


def cluster_by_tag(signals: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    """Cluster enriched signals by their first (primary) tag."""
    clusters: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for s in signals:
        tags = s.get("tags", [])
        if not tags:
            continue
        clusters[tags[0]].append(s)
    return dict(clusters)


def synthesize_cluster(tag: str, signals: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Call the LLM to synthesize a single insight from a cluster of signals.

    Returns the LLM-generated insight dict, or None on failure.
    """
    evidence = [s.get("text", "") for s in signals if s.get("text")]
    if not evidence:
        return None

    try:
        result = call_tool(
            system=SYSTEM_PROMPT,
            user=f"Theme: {tag}\nSignals ({len(signals)}):\n" + json.dumps(evidence, indent=2),
            tool=SYNTHESIS_TOOL,
            tool_name="submit_insight",
            trace_name=f"synthesize:{tag}",
        )
        return result
    except AIProviderError:
        logger.warning("Synthesis failed for tag '%s', skipping", tag, exc_info=True)
        return None


def synthesize_insights(
    enriched_signals: list[dict[str, Any]],
    *,
    min_cluster_size: int = 2,
) -> list[dict[str, Any]]:
    """Cluster enriched signals by tag and synthesize an insight per cluster.

    Requires min_cluster_size signals for corroboration (Elvis default: 2).
    Severity is computed deterministically; the LLM is told NOT to set it.

    Each insight dict carries:
      - title, summary, category, impact_score, confidence, target_team,
        suggested_actions (from LLM)
      - severity (deterministic, from cross_signal_severity)
      - signal_ids, qual_count, quant_count, affected_contacts (computed)
      - max_urgency (computed)
      - audit block (model, source, limitations)
    """
    from app.services.ai import AI_MODEL

    clusters = cluster_by_tag(enriched_signals)
    insights: list[dict[str, Any]] = []

    for tag, sigs in clusters.items():
        if len(sigs) < min_cluster_size:
            continue

        severity = cross_signal_severity(sigs)
        generated = synthesize_cluster(tag, sigs)
        if generated is None:
            continue

        qual_count = sum(1 for s in sigs if s.get("signal_type") == "qualitative")
        quant_count = len(sigs) - qual_count
        affected = sum(s.get("contact_count", 1) for s in sigs)
        max_urgency = max(
            sigs,
            key=lambda s: URGENCY_RANK.get(s.get("urgency", "medium"), 2),
        ).get("urgency", "low")

        insight = {
            "title": generated.get("title", ""),
            "summary": generated.get("summary", ""),
            "category": generated.get("category", ""),
            "impact_score": generated.get("impact_score", 0),
            "confidence": generated.get("confidence", 0),
            "target_team": generated.get("target_team", ""),
            "suggested_actions": generated.get("suggested_actions", []),
            "severity": severity,
            "signal_ids": [s["id"] for s in sigs],
            "qual_signal_count": qual_count,
            "quant_signal_count": quant_count,
            "affected_contacts": affected,
            "max_urgency": max_urgency,
            "tag": tag,
            "status": "new",
            "audit": {
                "model": AI_MODEL,
                "source": "llm_synthesis",
                "severity_source": "deterministic_cross_signal",
                "limitations": [
                    "LLM-synthesized; not human-validated",
                    "Severity is deterministic; LLM was instructed not to set it",
                ],
            },
        }
        insights.append(insight)

    return insights
