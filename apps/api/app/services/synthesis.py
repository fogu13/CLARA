"""LLM synthesis — port of reference/elvis/supabase/functions/synthesize-insights/index.ts.

Clusters enriched signals, computes deterministic severity, and calls the LLM
to synthesize an actionable insight per cluster.

Improvements over the original:
  - Multi-tag Jaccard clustering (replaces first-tag-only grouping)
  - Optional semantic fallback via embeddings
  - 8-factor severity using CLARA_2's impact scoring (when context available)
  - Time-decayed frequency with trend labels (replaces raw volume count)
  - Source corroboration factor
  - Configurable thresholds via env vars

Design decision #3 (from Elvis): severity is computed deterministically —
the LLM is explicitly told NOT to set it.
"""

from __future__ import annotations

import json
import logging
import os
from collections import Counter, defaultdict
from typing import Any

from app.services.ai import AIProviderError, call_tool

logger = logging.getLogger(__name__)

URGENCY_RANK: dict[str, int] = {"low": 1, "medium": 2, "high": 3, "critical": 4}

# Configurable thresholds
CLUSTER_JACCARD_THRESHOLD = float(os.getenv("CLUSTER_JACCARD_THRESHOLD", "0.34"))
CLUSTER_SEMANTIC_THRESHOLD = float(os.getenv("CLUSTER_SEMANTIC_THRESHOLD", "0.70"))
CLUSTER_MIN_SIZE = int(os.getenv("CLUSTER_MIN_SIZE", "3"))
CLUSTER_MIN_SOURCES = int(os.getenv("CLUSTER_MIN_SOURCES", "1"))

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


# ============================================================
# Multi-tag clustering with union-find
# ============================================================


class _UnionFind:
    """Union-find data structure for transitive clustering."""

    def __init__(self, n: int) -> None:
        self.parent = list(range(n))
        self.rank = [0] * n

    def find(self, x: int) -> int:
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]
            x = self.parent[x]
        return x

    def union(self, x: int, y: int) -> None:
        px, py = self.find(x), self.find(y)
        if px == py:
            return
        if self.rank[px] < self.rank[py]:
            px, py = py, px
        self.parent[py] = px
        if self.rank[px] == self.rank[py]:
            self.rank[px] += 1


def _jaccard_similarity(set_a: set[str], set_b: set[str]) -> float:
    """Jaccard similarity between two tag sets."""
    if not set_a and not set_b:
        return 0.0
    intersection = set_a & set_b
    union = set_a | set_b
    return len(intersection) / len(union) if union else 0.0


def cluster_signals(
    signals: list[dict[str, Any]],
    *,
    jaccard_threshold: float = CLUSTER_JACCARD_THRESHOLD,
    semantic_threshold: float = CLUSTER_SEMANTIC_THRESHOLD,
    embeddings: list[list[float]] | None = None,
) -> list[tuple[str, list[dict[str, Any]]]]:
    """Cluster signals by multi-tag Jaccard similarity + optional semantic fallback.

    Replaces the old cluster_by_tag() which only used tags[0].
    Two signals with ["checkout_failure", "payment_error"] and
    ["payment_error", "checkout_failure"] now end up in the same cluster.

    If embeddings are provided, signals with no tag overlap but high cosine
    similarity (>= semantic_threshold) are also grouped.

    Returns a list of (cluster_label, signals) tuples, where cluster_label
    is the most common tag across member signals.
    """
    if not signals:
        return []

    n = len(signals)
    uf = _UnionFind(n)

    tag_sets = [set(s.get("tags", [])) for s in signals]

    # Phase 1: Jaccard similarity on tag sets
    for i in range(n):
        for j in range(i + 1, n):
            if _jaccard_similarity(tag_sets[i], tag_sets[j]) >= jaccard_threshold:
                uf.union(i, j)

    # Phase 2: Semantic fallback (if embeddings provided)
    if embeddings and len(embeddings) == n:
        for i in range(n):
            for j in range(i + 1, n):
                if uf.find(i) == uf.find(j):
                    continue  # already grouped
                sim = _cosine_sim(embeddings[i], embeddings[j])
                if sim >= semantic_threshold:
                    uf.union(i, j)

    # Collect clusters
    groups: dict[int, list[int]] = defaultdict(list)
    for i in range(n):
        groups[uf.find(i)].append(i)

    # Build output with labels
    result: list[tuple[str, list[dict[str, Any]]]] = []
    for indices in groups.values():
        cluster_signals = [signals[i] for i in indices]
        # Label = most common tag across all signals in the cluster
        all_tags: Counter[str] = Counter()
        for s in cluster_signals:
            for t in s.get("tags", []):
                all_tags[t] += 1
        label = all_tags.most_common(1)[0][0] if all_tags else "unknown"
        result.append((label, cluster_signals))

    return result


def _cosine_sim(a: list[float], b: list[float]) -> float:
    """Cosine similarity between two vectors."""
    dot = sum(x * y for x, y in zip(a, b, strict=False))
    import math

    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


# ============================================================
# Severity computation — 8-factor when context available, simple fallback
# ============================================================


def cross_signal_severity(signals: list[dict[str, Any]]) -> str:
    """Simple severity fallback — urgency + volume + negativity.

    Used when no context data is available. Kept for backward compatibility
    and as the default in tests without context.
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


def compute_severity(
    signals: list[dict[str, Any]],
    *,
    context_data: dict[str, Any] | None = None,
    frequency_data: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Compute severity using the full 8-factor model when context is available.

    Falls back to the simple cross_signal_severity formula when no context data
    is provided (tests, no-DB mode).

    Returns: {score: float, band: str, factors: dict, method: str}
    """
    if not signals:
        return {"score": 0.0, "band": "low", "factors": {}, "method": "empty"}

    # If we have context data, use the full 8-factor impact model
    if context_data is not None:
        from app.domain.scoring import impact_band, normalized_impact_score

        volume = len(signals)
        customers = {s.get("customer_id", s.get("id", "")) for s in signals}
        sources = {s.get("source", "unknown") for s in signals}

        max_urgency_rank = max(
            (URGENCY_RANK.get(s.get("urgency", "medium"), 2) for s in signals),
            default=1,
        )
        urgency_factor = max_urgency_rank / 4.0  # normalize to 0-1

        neg_frac = sum(
            1 for s in signals if s.get("sentiment") == "negative"
        ) / volume

        # Build the 8 factors
        freq = frequency_data or {}
        decayed_freq = freq.get("decayed_frequency", float(volume))

        factors = {
            "customer_reach": min(1.0, len(customers) / 250),
            "severity": max(urgency_factor, neg_frac),
            "recurrence": min(1.0, decayed_freq / 25),
            "journey_criticality": context_data.get("journey_criticality", 0.5),
            "account_exposure": min(
                1.0,
                context_data.get("account_count", len(customers)) / 100,
            ),
            "financial_exposure": context_data.get("financial_exposure", 0.3),
            "regulatory_risk": context_data.get("regulatory_risk", 0.2),
            "evidence_confidence": min(
                1.0,
                (len(sources) * 0.04) + (volume * 0.02),
            ),
        }

        # Apply context adjustments (account value, health, renewal)
        ctx_impact = context_data.get("context_impact")
        if ctx_impact:
            factors["account_exposure"] = max(
                factors["account_exposure"],
                min(1.0, ctx_impact.get("matched_accounts", 0) / 100),
            )
            factors["financial_exposure"] = max(
                factors["financial_exposure"],
                min(1.0, ctx_impact.get("total_account_value", 0) / 250_000),
            )
            if ctx_impact.get("consent_risk_customers", 0) > 0:
                factors["regulatory_risk"] = max(
                    factors["regulatory_risk"],
                    ctx_impact["consent_risk_customers"]
                    / max(ctx_impact.get("matched_customers", 1), 1),
                )

        score = normalized_impact_score(factors)
        band = impact_band(score)

        return {
            "score": score,
            "band": band,
            "factors": factors,
            "method": "8_factor_impact",
        }

    # Fallback: simple formula
    band = cross_signal_severity(signals)
    return {
        "score": URGENCY_RANK.get(band, 1) / 4.0,
        "band": band,
        "factors": {},
        "method": "simple_urgency_volume",
    }


# ============================================================
# Insight synthesis
# ============================================================


def synthesize_cluster(tag: str, signals: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Call the LLM to synthesize a single insight from a cluster of signals."""
    evidence = [
        s.get("text", s.get("feedback_text", ""))
        for s in signals
        if s.get("text") or s.get("feedback_text")
    ]
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
    min_cluster_size: int = CLUSTER_MIN_SIZE,
    min_sources: int = CLUSTER_MIN_SOURCES,
    context_data: dict[str, Any] | None = None,
    embeddings: list[list[float]] | None = None,
) -> list[dict[str, Any]]:
    """Cluster enriched signals and synthesize an insight per cluster.

    Uses multi-tag Jaccard clustering (not first-tag-only). Severity uses the
    full 8-factor model when context_data is provided. Frequency analysis
    provides time-decayed counts and trend labels.

    Each insight dict carries:
      - title, summary, category, impact_score, confidence, target_team,
        suggested_actions (from LLM)
      - severity (deterministic: 8-factor or simple fallback)
      - severity_factors (when 8-factor: the individual factor values)
      - frequency ({raw_count, decayed_frequency, trend, first_seen, last_seen})
      - signal_ids, qual_count, quant_count, affected_contacts
      - source_count, cluster_method
      - audit block
    """
    from app.services.ai import AI_MODEL
    from app.services.frequency import frequency_factors

    clusters = cluster_signals(
        enriched_signals,
        jaccard_threshold=CLUSTER_JACCARD_THRESHOLD,
        semantic_threshold=CLUSTER_SEMANTIC_THRESHOLD,
        embeddings=embeddings,
    )
    insights: list[dict[str, Any]] = []

    for tag, sigs in clusters:
        if len(sigs) < min_cluster_size:
            continue

        sources = {s.get("source", "unknown") for s in sigs}
        if len(sources) < min_sources:
            continue

        # Frequency analysis
        freq = frequency_factors(sigs)

        # Severity (8-factor if context available, simple otherwise)
        sev = compute_severity(sigs, context_data=context_data, frequency_data=freq)

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
            "severity": sev["band"],
            "severity_score": sev["score"],
            "severity_factors": sev["factors"],
            "severity_method": sev["method"],
            "frequency": freq,
            "signal_ids": [s.get("id", s.get("signal_id", "")) for s in sigs],
            "qual_signal_count": qual_count,
            "quant_signal_count": quant_count,
            "affected_contacts": affected,
            "max_urgency": max_urgency,
            "source_count": len(sources),
            "tag": tag,
            "cluster_method": "jaccard" if embeddings is None else "jaccard+semantic",
            "status": "new",
            "audit": {
                "model": AI_MODEL,
                "source": "llm_synthesis",
                "severity_source": sev["method"],
                "limitations": [
                    "LLM-synthesized; not human-validated",
                    "Severity is deterministic; LLM was instructed not to set it",
                ],
            },
        }
        insights.append(insight)

    return insights
