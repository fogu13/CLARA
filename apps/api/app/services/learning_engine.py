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


def rank_learnings(
    learnings: list[dict[str, Any]],
    query: str,
    *,
    k: int = 3,
    now: float | None = None,
) -> list[dict[str, Any]]:
    """Relevant-learnings retrieval — port of Elvis's rankLearnings (learnings.ts:33-47).

    Ranks learnings by token overlap with the query, weighted by decayed
    confidence so fresher/stronger learnings surface first.

    Only HUMAN-validated conclusions are retrieval-eligible (science review F7):
    learn_node auto-derives "worked" from the outcome status with
    reviewer="system", and those outcomes are peak-selected and
    volume-confounded — feeding them back into synthesis prompts would launder
    an unvalidated causal claim into future recommendations. Auto-derived
    learnings stay visible as pending; they just never steer the model.

    A pgvector semantic ranking can replace this scorer without changing callers.
    """
    q_tokens = list(set(_tokenize(query)))
    if not q_tokens:
        return []

    scored: list[tuple[float, dict[str, Any]]] = []
    for learning in learnings:
        # Records without the field (legacy stores, probe fixtures) pass — only
        # the auto-derived path labels itself, and it is the one being gated.
        if learning.get("reviewer") == "system":
            continue
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
        score = overlap * (0.5 + 0.5 * decayed)
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


def learning_from_problem_conclusion(
    *,
    problem: Any,
    conclusion: Any,
    outcome_status: str,
    resolution_score: float | None = None,
    resolution_actions: list[str] | None = None,
) -> dict[str, Any]:
    """Learning-memory record for a HUMAN conclusion recorded on an Action Queue problem.

    This is the production bridge the thesis harness never needed: a reviewer's
    ``LearningConclusionRecord`` (append-only audit record) becomes a retrievable
    learning that ``rank_learnings`` can hand to the next synthesis run — so the
    model learns which resolutions actually changed customer behaviour, per the
    product promise. Keyed by the conclusion id so re-recording upserts.

    ``resolution_actions`` are the approved action proposals' text: that is the
    WHAT-was-done half of the learning, without which "worked" is not reusable.
    """
    theme = getattr(problem, "theme_tag", None) or problem.journey_stage
    insight = {
        "title": problem.title,
        "tag": theme,
        "category": problem.journey,
        "severity": problem.impact_band or "",
    }
    outcome = {
        "metric": problem.outcome_contract.primary_metric,
        "status": outcome_status,
        "resolution_score": resolution_score,
    }
    payload = {
        "learning_status": conclusion.learning_status.value
        if hasattr(conclusion.learning_status, "value")
        else str(conclusion.learning_status),
        "summary": conclusion.summary,
        "limitations": conclusion.limitations,
        "next_step": conclusion.next_step,
        "reviewer": conclusion.reviewer,
    }
    learning = build_learning_from_conclusion(conclusion=payload, insight=insight, outcome=outcome)
    actions = [text for text in (resolution_actions or []) if text]
    if actions:
        learning["pattern"] = f"{problem.title} -> {'; '.join(actions)} -> {conclusion.summary}"
        if learning["learning_status"] == "worked":
            learning["winning_examples"] = actions
        elif learning["learning_status"] == "did_not_work":
            learning["losing_examples"] = actions
    learning.update(
        {
            "conclusion_id": conclusion.conclusion_id,
            "problem_id": problem.problem_id,
            "owner": problem.owner,
            "journey": problem.journey,
            "journey_stage": problem.journey_stage,
            "theme_tag": getattr(problem, "theme_tag", None),
            "resolution_actions": actions,
            "created_at": conclusion.reviewed_at,
            "last_validated_at": conclusion.reviewed_at,
            "retention_expires_at": conclusion.retention_expires_at,
            "source": "action_queue_conclusion",
        }
    )
    return learning


def with_decay(learning: dict[str, Any], *, now: float | None = None) -> dict[str, Any]:
    """Read-side copy carrying the current decayed confidence and freshness badge."""
    return {
        **learning,
        "decayed_confidence": round(decayed_confidence(learning, now=now), 4),
        "freshness": learning_freshness(learning, now=now),
        "retrieval_eligible": learning.get("reviewer") != "system",
    }
