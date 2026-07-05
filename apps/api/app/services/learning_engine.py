"""Learning engine — confidence decay + relevant-learnings retrieval.

Port of reference/elvis/src/lib/learnings.ts. Merges Elvis's AbLearning
confidence-decay model with CLARA_2's structured LearningConclusion verdicts.

Design decision #2 (Elvis): a learning's stored confidence erodes exponentially
from last_validated_at with a configurable half-life. Fresher/stronger learnings
surface first.

Design decision #4 (Elvis): "relevant past learnings" retrieval ranks learnings
by token overlap with the query, weighted by decayed confidence. A pgvector
semantic ranking can replace the scorer without changing callers.

CLARA_2 contributes structured verdicts: worked | partially_worked |
did_not_work | inconclusive | measurement_invalid (LearningStatus enum).
"""

from __future__ import annotations

import logging
import re
from datetime import UTC, datetime
from typing import Any

logger = logging.getLogger(__name__)

DAY_SECONDS = 86_400
DEFAULT_HALF_LIFE_DAYS = 180


def decayed_confidence(
    learning: dict[str, Any],
    *,
    now: float | None = None,
) -> float:
    """Confidence decay — port of Elvis's decayedConfidence (learnings.ts:10-17).

    A learning's stored confidence erodes exponentially from last_validated_at
    with a configurable half-life. Returns a 0-1 value.

    base * 0.5^(age_days / half_life_days)
    """
    if now is None:
        now = datetime.now(UTC).timestamp()

    base = float(
        learning.get("base_confidence",
                     learning.get("evidence", {}).get("confidence", 0))
    )

    ref_str = (
        learning.get("last_validated_at")
        or learning.get("reviewed_at")
        or learning.get("created_at")
    )
    if not ref_str:
        return base

    try:
        ref_dt = datetime.fromisoformat(ref_str.replace("Z", "+00:00"))
        ref_ts = ref_dt.timestamp()
    except (ValueError, TypeError):
        return base

    age_days = max(0, (now - ref_ts) / DAY_SECONDS)
    half_life = float(learning.get("half_life_days", DEFAULT_HALF_LIFE_DAYS))
    if half_life <= 0:
        half_life = DEFAULT_HALF_LIFE_DAYS

    return base * (0.5 ** (age_days / half_life))


def is_stale(
    learning: dict[str, Any],
    *,
    now: float | None = None,
) -> bool:
    """A learning is stale once confidence has decayed below half its original.

    Port of Elvis's isStale (learnings.ts:20-23).
    """
    base = float(learning.get("base_confidence", learning.get("evidence", {}).get("confidence", 0)))
    return base > 0 and decayed_confidence(learning, now=now) < base * 0.5


def learning_freshness(
    learning: dict[str, Any],
    *,
    now: float | None = None,
) -> str:
    """Classify a learning as VALIDATED, EMERGING, or STALE.

    Matches Elvis's Learnings.tsx UI badges:
      - VALIDATED: decayed confidence >= 0.5 * base (within half-life)
      - EMERGING: decayed confidence >= 0.25 * base (within 2x half-life)
      - STALE: decayed confidence < 0.25 * base
    """
    base = float(learning.get("base_confidence", 0))
    if base <= 0:
        return "STALE"

    decayed = decayed_confidence(learning, now=now)
    if decayed >= base * 0.5:
        return "VALIDATED"
    if decayed >= base * 0.25:
        return "EMERGING"
    return "STALE"


def _tokenize(s: str) -> list[str]:
    """Tokenize a string for relevance matching — port of Elvis's tokenize."""
    return [t for t in re.split(r"[^a-z0-9]+", s.lower()) if len(t) > 2]


def track_record(learning: dict[str, Any]) -> float:
    """Proven-outcome weight in [0, 1] — port of Elvis's recScore track-record term.

    Elvis (RelevantLearnings.tsx:13-17) ranks by
    ``similarity × decayed_confidence × (1 + avg_resolution)`` so a play that actually
    closed loops outranks a merely-similar untested one. This returns that
    ``avg_resolution``: an explicit re-application average once the apply -> outcome edge
    is tracked, else the originating outcome's resolution_score, else 0 (neutral: the
    ``1 + track_record`` factor stays 1.0, so unproven learnings are never penalised).
    """
    res = learning.get("avg_resolution")
    if res is None:
        res = learning.get("evidence", {}).get("resolution_score", 0)
    try:
        return max(0.0, min(1.0, float(res)))
    except (TypeError, ValueError):
        return 0.0


def rank_learnings(
    learnings: list[dict[str, Any]],
    query: str,
    *,
    k: int = 3,
    now: float | None = None,
) -> list[dict[str, Any]]:
    """Relevant-learnings retrieval — port of Elvis's rankLearnings (learnings.ts:33-47).

    Ranks learnings by token overlap with the query, weighted by decayed
    confidence *and* proven track record, so fresher/stronger plays that actually
    closed loops surface first: overlap × (0.5 + 0.5·decayed) × (1 + track_record).

    A pgvector semantic ranking can replace the overlap term without changing callers.
    """
    q_tokens = list(set(_tokenize(query)))
    if not q_tokens:
        return []

    scored: list[tuple[float, dict[str, Any]]] = []
    for learning in learnings:
        hay = " ".join([
            learning.get("topic", ""),
            learning.get("pattern", ""),
            " ".join(learning.get("winning_examples", [])),
            " ".join(learning.get("losing_examples", [])),
            learning.get("summary", ""),
        ]).lower()

        overlap = sum(1 for t in q_tokens if t in hay)
        if overlap == 0:
            continue

        decayed = decayed_confidence(learning, now=now)
        score = overlap * (0.5 + 0.5 * decayed) * (1.0 + track_record(learning))
        scored.append((score, learning))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [learning for _, learning in scored[:k]]


def build_learning_from_conclusion(
    *,
    conclusion: dict[str, Any],
    insight: dict[str, Any],
    outcome: dict[str, Any],
) -> dict[str, Any]:
    """Build a learning record from a human conclusion + outcome measurement.

    Merges CLARA_2's structured LearningConclusion (worked/partially_worked/
    did_not_work/inconclusive/measurement_invalid) with Elvis's AbLearning
    pattern (topic, evidence, confidence, half_life_days).

    The base_confidence is derived from the outcome's resolution_score:
      - worked + high score -> high confidence
      - did_not_work -> low confidence (still valuable as a negative learning)
      - inconclusive -> medium-low confidence
    """
    status = conclusion.get("learning_status", "inconclusive")
    score_raw = outcome.get("resolution_score", 0)
    score = float(score_raw) if score_raw is not None else 0.0

    # Confidence mapping: combine human verdict + measured score
    if status == "worked":
        base_confidence = max(0.6, score)  # at least 0.6 if human says worked
    elif status == "partially_worked":
        base_confidence = max(0.4, score * 0.8)
    elif status == "did_not_work":
        base_confidence = 0.3  # negative learnings are valuable but lower confidence
    elif status == "measurement_invalid":
        base_confidence = 0.1
    else:  # inconclusive
        base_confidence = 0.2

    tag = insight.get("tag", "")
    topic = tag or insight.get("category", "general")
    pattern = f"{insight.get('title', '')} -> {conclusion.get('summary', '')}"

    return {
        "topic": topic,
        "pattern": pattern,
        "learning_status": status,
        "summary": conclusion.get("summary", ""),
        "limitations": conclusion.get("limitations", ""),
        "next_step": conclusion.get("next_step"),
        "base_confidence": round(base_confidence, 2),
        "half_life_days": DEFAULT_HALF_LIFE_DAYS,
        "last_validated_at": datetime.now(UTC).isoformat(),
        "evidence": {
            "confidence": base_confidence,
            "outcome_metric": outcome.get("metric"),
            "resolution_score": score,
            "outcome_status": outcome.get("status"),
            "insight_title": insight.get("title"),
            "insight_severity": insight.get("severity"),
        },
        "winning_examples": [] if status != "worked" else [insight.get("title", "")],
        "losing_examples": [] if status != "did_not_work" else [insight.get("title", "")],
        "reviewer": conclusion.get("reviewer", "system"),
    }
