"""Outcome engine — close-the-loop measurement.

Merges Elvis's outcome-contract + resolution_score (measure-outcomes edge fn)
with Odradek_2's direction-aware outcome_status (workflow.py:63-87).

Elvis: resolution_score = clamp01(1 - measured/baseline) for "lower is better"
metrics (e.g. complaint recurrence). Odradek_2: direction-aware status handles
both "higher is better" and "lower is better" metrics correctly.

The hybrid engine:
  1. Captures the outcome contract at action time (metric, baseline, target,
     measurement_window_days).
  2. After the measurement window, recomputes the metric from new signals.
  3. Computes resolution_score (Elvis's formula, generalized for direction).
  4. Reports direction-aware status (Odradek_2's outcome_status).
  5. Assigns a closure_level (Elvis's chips: operational/customer/outcome).
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def clamp01(n: float) -> float:
    """Clamp a value to [0, 1] — port of Elvis's measure-outcomes:9."""
    return max(0.0, min(1.0, n))


def outcome_direction(*, baseline: float, target: float) -> str:
    """Determine if higher or lower values are better.

    Port of Odradek_2's outcome_direction (workflow.py:64-65).
    """
    return "increase" if target >= baseline else "decrease"


def outcome_status(
    *,
    baseline: float,
    target: float,
    measured: float | None,
) -> str:
    """Direction-aware outcome status.

    Port of Odradek_2's outcome_status (workflow.py:68-88). Handles both
    "higher is better" (success_threshold >= baseline) and "lower is better"
    (success_threshold < baseline) metrics correctly, so complaint-rate metrics
    are not misread as completion-rate metrics.

    Returns: not_measured | not_improved | improving | target_met
    """
    if measured is None:
        return "not_measured"

    if outcome_direction(baseline=baseline, target=target) == "increase":
        if measured >= target:
            return "target_met"
        if measured > baseline:
            return "improving"
        return "not_improved"

    # Lower is better
    if measured <= target:
        return "target_met"
    if measured < baseline:
        return "improving"
    return "not_improved"


def resolution_score(
    *,
    baseline: float,
    measured: float,
    direction: str | None = None,
) -> float:
    """Compute resolution_score — generalized from Elvis's formula.

    Elvis's original (measure-outcomes:41): for "lower is better" metrics
    (complaint recurrence), score = clamp01(1 - measured/baseline).
    A score of 1 means the issue is fully resolved (measured dropped to 0).

    Generalized for both directions:
      - decrease (lower is better): clamp01(1 - measured/baseline)
      - increase (higher is better): clamp01(measured/baseline) if baseline > 0,
        else 1.0 if measured > 0 else 0.5

    Returns a 0-1 value where 1 = fully resolved / target met.
    """
    if direction is None:
        direction = "decrease"  # default: complaint-style metrics

    if direction == "increase":
        if baseline <= 0:
            return 1.0 if measured > 0 else 0.5
        return clamp01(measured / baseline)

    # decrease (lower is better) — Elvis's original formula
    if baseline > 0:
        return clamp01(1 - measured / baseline)
    return 1.0 if measured == 0 else 0.5


def closure_level(
    *,
    action_results: list[dict[str, Any]],
    measured: float | None,
    score: float | None,
) -> str:
    """Determine the closure level — port of Elvis's closure chips.

    Three levels (from Elvis's InsightDetail.tsx:657-660):
      - 'operational': an action was taken (ticket created, notification sent)
      - 'customer': the affected customer was contacted / loop closed with them
      - 'outcome': the outcome metric was measured and shows improvement

    Returns the highest level achieved.
    """
    if measured is not None and score is not None:
        if score >= 0.5:  # meaningful improvement
            return "outcome"
        return "operational"  # measured but no improvement

    if action_results:
        # Check if any action was taken (pushed, no_config, no_connector —
        # anything that isn't a failure represents an approved action)
        acted = [
            a for a in action_results
            if a.get("status") not in ("failed", None)
        ]
        if acted:
            return "operational"

    return "none"


def build_outcome_contract(
    *,
    insight: dict[str, Any],
    measurement_window_days: int = 14,
) -> dict[str, Any]:
    """Build an outcome contract from an insight at action time.

    Port of Elvis's evaluate-rules outcome contract capture (evaluate-rules:317-355).
    Default metric: affected_contacts. Prefer recurrence of the insight's
    dominant signal tag (tag:<tag>) — this measures whether the same theme
    keeps appearing after the action.

    Returns: {metric, baseline, target, measurement_window_days, direction}
    """
    metric = "affected_contacts"
    baseline = float(insight.get("affected_contacts", 0))

    # Prefer tag recurrence if signal tags are available
    signal_ids = insight.get("signal_ids", [])
    tag = insight.get("tag", "")
    if tag:
        metric = f"tag:{tag}"
        # Baseline = count of signals with this tag (from the insight)
        baseline = float(insight.get("qual_signal_count", len(signal_ids)))

    # Target: for decrease metrics, target = 0 (no recurrence).
    # For increase metrics, target = baseline * 1.5 (50% improvement).
    direction = "decrease"
    target = 0.0

    return {
        "metric": metric,
        "baseline": baseline,
        "target": target,
        "measurement_window_days": measurement_window_days,
        "direction": direction,
    }


def measure_outcome(
    *,
    contract: dict[str, Any],
    measured_value: float,
    action_results: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Measure an outcome against its contract.

    Combines:
      - resolution_score (Elvis's formula, generalized)
      - outcome_status (Odradek_2's direction-aware status)
      - closure_level (Elvis's chips)

    Returns: {
        metric, baseline, measured, target, resolution_score,
        status, closure_level, summary
    }
    """
    baseline = float(contract.get("baseline", 0))
    target = float(contract.get("target", 0))
    metric = contract.get("metric", "affected_contacts")
    direction = contract.get("direction", "decrease")

    score = resolution_score(
        baseline=baseline,
        measured=measured_value,
        direction=direction,
    )
    status = outcome_status(
        baseline=baseline,
        target=target,
        measured=measured_value,
    )
    level = closure_level(
        action_results=action_results or [],
        measured=measured_value,
        score=score,
    )

    summary = _build_summary(metric, baseline, measured_value, score, status)

    return {
        "metric": metric,
        "baseline": baseline,
        "measured": measured_value,
        "target": target,
        "resolution_score": round(score, 4),
        "status": status,
        "closure_level": level,
        "summary": summary,
    }


def _build_summary(
    metric: str,
    baseline: float,
    measured: float,
    score: float,
    status: str,
) -> str:
    """Build a human-readable outcome summary — port of Elvis's measure-outcomes:35-38."""
    if metric.startswith("tag:"):
        tag = metric[4:]
        return (
            f'Recurrence of "{tag}" after action: {measured} new signal(s) '
            f"vs baseline of {baseline}. Resolution score: {score:.2f} ({status})."
        )
    return (
        f"Metric {metric}: baseline {baseline}, measured {measured}. "
        f"Resolution score: {score:.2f} ({status})."
    )
