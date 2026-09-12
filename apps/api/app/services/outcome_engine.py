"""Outcome engine — close-the-loop measurement.

Merges Elvis's outcome-contract + resolution_score (measure-outcomes edge fn)
with CLARA_2's direction-aware outcome_status (workflow.py:63-87).

Elvis: resolution_score = clamp01(1 - measured/baseline) for "lower is better"
metrics (e.g. complaint recurrence). CLARA_2: direction-aware status handles
both "higher is better" and "lower is better" metrics correctly.

The hybrid engine:
  1. Captures the outcome contract at action time (metric, baseline, target,
     measurement_window_days).
  2. After the measurement window, recomputes the metric from new signals.
  3. Computes resolution_score (Elvis's formula, generalized for direction).
  4. Reports direction-aware status (CLARA_2's outcome_status).
  5. Assigns a closure_level (Elvis's chips: operational/customer/outcome).
"""

from __future__ import annotations

import logging
import math
from datetime import date, datetime, time, timedelta, timezone
from typing import Any

from app.domain.models import OutcomeContract, ProblemRecord

# Shared with the scheduler so proposal, ITS scoring and scheduled
# re-measurement all match/bucket signals identically.
from app.services.measurement_scheduler import (
    LOOP_CHECKPOINT_KINDS,
    SIGNAL_METRIC_PREFIX,
    _parse_ts,
    signal_matches_scope,
)

logger = logging.getLogger(__name__)


def clamp01(n: float) -> float:
    """Clamp a value to [0, 1] — port of Elvis's measure-outcomes:9."""
    return max(0.0, min(1.0, n))


def detectability_note(
    *, baseline_rate: float, window_days: int, pre_days: int = 28
) -> str | None:
    """Honest heuristic MDE for a signal-rate contract, or None when meaningless.

    Two-sample Poisson rate comparison, normal approximation, two-sided
    alpha=.05 at 80% power: relative MDE ~= 2.8 * sqrt((1/W1 + 1/W2) / rate).
    Deliberately labelled a heuristic — it flags underpowered windows before
    approval; it is NOT a formal power analysis.
    """
    if baseline_rate <= 0 or window_days <= 0:
        return None
    relative = 2.8 * math.sqrt((1 / pre_days + 1 / window_days) / baseline_rate)
    if relative >= 1:
        return (
            f"Detectability: at ~{baseline_rate:.1f} signals/day, even a 100% change may "
            f"not reach significance within {window_days} days — treat the readout as "
            "directional (80%-power Poisson heuristic)."
        )
    return (
        f"Detectability: at ~{baseline_rate:.1f} signals/day over {window_days} days, "
        f"changes smaller than ~{round(relative * 100)}% likely won't reach significance "
        "(80%-power Poisson heuristic, not a formal power analysis)."
    )


def evidence_grade(
    *,
    comparison_method: str,
    measurement_source: str | None,
    realised_method: str | None = None,
) -> str:
    """A–E design grade for an outcome readout (external-review evidence scale).

    A  randomized holdout / control group, instrumented measurement
    B  controlled quasi-experiment (diff-in-diff, matched control) — reserved,
       CLARA does not produce this design yet
    C  interrupted time series (segmented regression)
    D  uncontrolled before/after, instrumented
    E  manual assertion or nothing measured yet (descriptive only)

    Grades the design from fields available on every snapshot. The board
    grades the contracted design; the problem detail, which runs the ITS,
    also passes the fit it actually obtained (``realised_method``): when the
    contract promised an ITS but the series was too sparse and the engine
    fell back to a labelled plain delta, the readout IS an uncontrolled
    before/after and is graded D, not C — the grade follows the evidence
    that exists, not the evidence that was planned.
    """
    if measurement_source is None or measurement_source == "manual":
        return "E"
    method = comparison_method.lower()
    if "holdout" in method or "control" in method:
        return "A"
    if "its" in method:
        if realised_method is not None and realised_method != "its":
            return "D"
        return "C"
    return "D"


def outcome_direction(*, baseline: float, target: float) -> str:
    """Determine if higher or lower values are better.

    Port of CLARA_2's outcome_direction (workflow.py:64-65).
    """
    return "increase" if target >= baseline else "decrease"


def outcome_status(
    *,
    baseline: float,
    target: float,
    measured: float | None,
    direction: str | None = None,
) -> str:
    """Direction-aware outcome status.

    Port of CLARA_2's outcome_status (workflow.py:68-88). Handles both
    "higher is better" (success_threshold >= baseline) and "lower is better"
    (success_threshold < baseline) metrics correctly, so complaint-rate metrics
    are not misread as completion-rate metrics.

    An explicit contract `direction` wins over derivation: with the standard
    decrease contract (target=0) and a zero baseline, `target >= baseline`
    would flip the derived direction to "increase" and report any recurrence
    as target_met.

    Returns: not_measured | not_improved | improving | target_met
    """
    if measured is None:
        return "not_measured"

    # Degenerate contract: zero baseline, zero target, zero measured means
    # nothing was ever observed — reporting "target_met" there (Learnings card
    # "0.0/day from 0 signals · Target met") is meaningless, not a success.
    if baseline == 0 and target == 0 and measured == 0:
        return "not_measured"

    if direction is None:
        direction = outcome_direction(baseline=baseline, target=target)

    if direction == "increase":
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
      - outcome_status (CLARA_2's direction-aware status)
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
        direction=direction,
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


# ---------------------------------------------------------------------------
# W4 — auto-proposed outcome contracts + honest ITS (interrupted time series)
# scoring. Pure stdlib, deterministic (precedent: evals/harness.py).
# ---------------------------------------------------------------------------

ITS_COMPARISON_METHOD = "its_segmented_regression"
PROPOSED_WINDOW_DAYS = 30
TRAILING_BASELINE_DAYS = 28
MIN_PRE_DAYS = 10
MIN_POST_DAYS = 5
INSUFFICIENT_DATA_LABEL = "insufficient data for ITS"

# Two-sided 95% critical values of Student's t for df 1..30; beyond 30 the
# Cornish-Fisher expansion in _t_crit_95 is accurate to ~1e-3.
_T_95 = [
    12.706, 4.303, 3.182, 2.776, 2.571, 2.447, 2.365, 2.306, 2.262, 2.228,
    2.201, 2.179, 2.160, 2.145, 2.131, 2.120, 2.110, 2.101, 2.093, 2.086,
    2.080, 2.074, 2.069, 2.064, 2.060, 2.056, 2.052, 2.048, 2.045, 2.042,
]


def _t_crit_95(df: int) -> float:
    if df <= 0:
        return 0.0
    if df <= 30:
        return _T_95[df - 1]
    z = 1.959964
    return z + (z**3 + z) / (4 * df) + (5 * z**5 + 16 * z**3 + 3 * z) / (96 * df**2)


def _solve_gaussian(
    matrix: list[list[float]],
    rhs_list: list[list[float]],
) -> list[list[float]] | None:
    """Solve matrix @ x = rhs for several right-hand sides at once via
    Gauss-Jordan elimination with partial pivoting. Returns None when the
    matrix is singular (collinear design)."""
    n = len(matrix)
    augmented = [list(matrix[i]) + [rhs[i] for rhs in rhs_list] for i in range(n)]
    for col in range(n):
        pivot = max(range(col, n), key=lambda row: abs(augmented[row][col]))
        if abs(augmented[pivot][col]) < 1e-12:
            return None
        augmented[col], augmented[pivot] = augmented[pivot], augmented[col]
        divisor = augmented[col][col]
        augmented[col] = [value / divisor for value in augmented[col]]
        for row in range(n):
            if row == col or augmented[row][col] == 0.0:
                continue
            factor = augmented[row][col]
            augmented[row] = [
                value - factor * lead for value, lead in zip(augmented[row], augmented[col])
            ]
    return [[augmented[i][n + k] for i in range(n)] for k in range(len(rhs_list))]


def _insufficient_delta(*, delta: float, n_pre: int, n_post: int) -> dict[str, Any]:
    """Honest sparse fallback: a labelled plain delta, never a fake CI."""
    return {
        "method": "delta_insufficient_data",
        "label": INSUFFICIENT_DATA_LABEL,
        "delta": round(delta, 4),
        "n_pre": n_pre,
        "n_post": n_post,
    }


def its_effect(
    daily_counts: list[float],
    action_index: int,
    *,
    times: list[float] | None = None,
) -> dict[str, Any]:
    """Segmented regression (interrupted time series) on a daily-rate series.

    Model: y = b0 + b1*t + b2*post + b3*(t - action_index)*post — the classic
    level-change (b2) + slope-change (b3) ITS parameterisation. `effect` is
    the model-implied difference at the end of the series between the fitted
    post trend and the pre-trend counterfactual: b2 + b3*(t_end - action_index).

    `times` gives each observation's day offset on the real time axis
    (default 0..n-1); callers use it to drop buckets (e.g. the mixed
    pre/post execution day) without compressing the timeline.

    Honesty rule: with fewer than MIN_PRE_DAYS pre or MIN_POST_DAYS post daily
    buckets the regression is not credible — return the labelled plain delta.
    """
    n = len(daily_counts)
    if times is None:
        times = [float(i) for i in range(n)]
    n_pre = sum(1 for t in times if t < action_index)
    n_post = n - n_pre

    def _delta_fallback() -> dict[str, Any]:
        pre = [y for t, y in zip(times, daily_counts) if t < action_index]
        post = [y for t, y in zip(times, daily_counts) if t >= action_index]
        pre_mean = sum(pre) / len(pre) if pre else 0.0
        post_mean = sum(post) / len(post) if post else 0.0
        return _insufficient_delta(delta=post_mean - pre_mean, n_pre=n_pre, n_post=n_post)

    if n_pre < MIN_PRE_DAYS or n_post < MIN_POST_DAYS:
        return _delta_fallback()

    design_rows: list[tuple[float, float, float, float]] = []
    xtx = [[0.0] * 4 for _ in range(4)]
    xty = [0.0] * 4
    for t, y in zip(times, daily_counts):
        post = 1.0 if t >= action_index else 0.0
        x = (1.0, float(t), post, (t - action_index) * post)
        design_rows.append(x)
        for i in range(4):
            xty[i] += x[i] * y
            for j in range(4):
                xtx[i][j] += x[i] * x[j]

    solved = _solve_gaussian(xtx, [xty, [0, 0, 1, 0], [0, 0, 0, 1]])
    if solved is None:  # collinear design — cannot fit credibly
        return _delta_fallback()
    beta, inv_col2, inv_col3 = solved

    residual_ss = sum(
        (y - sum(b * xi for b, xi in zip(beta, x))) ** 2
        for x, y in zip(design_rows, daily_counts)
    )
    degrees = n - 4
    sigma2 = residual_ss / degrees if degrees > 0 else 0.0

    horizon = times[-1] - action_index
    effect = beta[2] + horizon * beta[3]
    # Var(b2 + h*b3) from the (X'X)^-1 block, scaled by residual variance.
    # ponytail: plain-OLS standard errors; Newey-West (HAC) errors are the
    # upgrade path if residual autocorrelation in daily rates matters.
    variance = sigma2 * (
        inv_col2[2] + horizon * horizon * inv_col3[3] + 2 * horizon * inv_col2[3]
    )
    standard_error = math.sqrt(max(variance, 0.0))
    t_crit = _t_crit_95(degrees)
    return {
        "method": "its",
        "level_change": round(beta[2], 4),
        "slope_change": round(beta[3], 4),
        "effect": round(effect, 4),
        "ci_low": round(effect - t_crit * standard_error, 4),
        "ci_high": round(effect + t_crit * standard_error, 4),
        "n_pre": n_pre,
        "n_post": n_post,
    }


def _utc_date(ts: datetime) -> date:
    """Calendar day in UTC — a stamp's own offset must not shift its bucket."""
    return ts.astimezone(timezone.utc).date()


def _metric_journey_stage(metric: str) -> tuple[str, str] | None:
    if not metric.startswith(SIGNAL_METRIC_PREFIX):
        return None
    journey, _, stage = metric.removeprefix(SIGNAL_METRIC_PREFIX).partition("/")
    return journey.replace("_", " "), stage.replace("_", " ")


def _matching_timestamps(
    signals: list[Any],
    *,
    journey: str,
    journey_stage: str,
) -> list:
    stamps = []
    for signal in signals:
        if not signal_matches_scope(signal, journey=journey, journey_stage=journey_stage):
            continue
        try:
            stamps.append(_parse_ts(signal.timestamp))
        except ValueError:
            continue
    return sorted(stamps)


# --- Loop verdict ---------------------------------------------------------
# The pitch's proof step in one word: did the fix land? Derived at read time
# from the contract status plus the scheduled checkpoints, never stored, so it
# always reflects the latest real-signal measurement.
LOOP_VERDICTS = (
    "not_measured",
    "measuring",
    "manual_required",
    "on_track",
    "loop_closed",
    "fix_did_not_land",
)


def intervention_anchor(executions: list[Any]) -> tuple[str, str] | None:
    """(origin, at) of the intervention the measurement clock runs from.

    Earliest human-recorded ``implemented_at`` wins (the fix landed); else the
    earliest ``dispatched_at`` of a pushed execution (the ticket/message left
    CLARA); else the earliest ``created_at`` of a draft-only execution, where
    the approval itself is the deliverable. Executions that only ever failed
    to push give no anchor: nothing happened that inflow could react to.
    """
    implemented = sorted(
        execution.implemented_at for execution in executions if execution.implemented_at
    )
    if implemented:
        return "implementation", implemented[0]
    dispatched = sorted(
        execution.dispatched_at
        for execution in executions
        if execution.dispatched_at and _status_name(execution.status) == "pushed"
    )
    if dispatched:
        return "dispatch", dispatched[0]
    drafts = sorted(
        execution.created_at
        for execution in executions
        if _status_name(execution.status) == "draft_created"
    )
    if drafts:
        return "approval", drafts[0]
    return None


def _status_name(status: Any) -> str:
    return str(getattr(status, "value", status))


def loop_verdict(
    *,
    outcome_status: str,
    plans: list[dict[str, Any]],
    measurement_source: str | None = None,
    checkpoint_kind: str | None = None,
    measurement_origin: str | None = None,
    measurement_origin_at: str | None = None,
) -> tuple[str, str]:
    """(verdict, note) for one problem.

    - not_measured: no approved action has started the clock.
    - measuring: checkpoints are scheduled but the closing read is not in yet.
    - manual_required: CLARA cannot observe the metric; a human must record it.
    - on_track: an early read (T+7, or a manual read) looks good — not proof yet.
    - loop_closed: the latest reading is an instrumented window or follow-up
      checkpoint read that met the target. Certified target attainment on
      real inflow; causal attribution rests on the comparison method.
    - fix_did_not_land: that same closing read shows no improvement.

    Certification is bound to the observation itself: only an instrumented
    reading produced by a closing checkpoint (``checkpoint_kind``) certifies.
    Legacy readings without a checkpoint kind fall back to "a closing plan is
    done". A manual reading never certifies, whatever the plans say.
    """
    done_closing = {
        plan["kind"] for plan in plans if plan.get("status") == "done" and plan.get("kind") in LOOP_CHECKPOINT_KINDS
    }
    pending = any(plan.get("status") == "pending" for plan in plans)
    manual = any(plan.get("status") == "manual_required" for plan in plans)

    if outcome_status == "not_measured":
        if manual:
            return "manual_required", "CLARA cannot observe this metric; record the measurement by hand."
        if pending:
            return "measuring", "Checkpoints are scheduled; the closing read is not in yet."
        return "not_measured", "No approved action has started the measurement clock."

    instrumented = measurement_source == "instrumented"
    if checkpoint_kind is not None:
        certified = instrumented and checkpoint_kind in LOOP_CHECKPOINT_KINDS
        closing_label = "follow-up" if checkpoint_kind == "followup" else "window"
    else:
        certified = instrumented and bool(done_closing)
        closing_label = "follow-up" if "followup" in done_closing else "window"

    clock = ""
    if measurement_origin:
        clock = f"; clock from {measurement_origin}"
        if measurement_origin_at:
            clock += f" on {str(measurement_origin_at)[:10]}"
    caveat = (
        " No dispatch or implementation was recorded, so this read may predate the fix."
        if measurement_origin == "approval"
        else ""
    )

    if outcome_status == "target_met":
        if certified:
            return "loop_closed", (
                f"Inflow met the target at the {closing_label} checkpoint (instrumented read{clock})."
                " Target attained; causal attribution rests on the comparison method"
                f" (see evidence grade).{caveat}"
            )
        if not instrumented:
            return "on_track", (
                "A manual reading met the target; it is not certified on signal inflow"
                " — the next scheduled read will."
            )
        return "on_track", "The early read met the target; the window checkpoint will confirm it."
    if outcome_status == "improving":
        return "on_track", "Inflow is moving the right way but has not reached the target yet."
    if outcome_status == "not_improved":
        if certified:
            return "fix_did_not_land", (
                f"The {closing_label} checkpoint shows no improvement (instrumented read{clock}):"
                f" the fix did not land.{caveat}"
            )
        if not instrumented:
            return "measuring", (
                "A manual reading shows no improvement; the next scheduled read decides."
            )
        return "measuring", "The early read shows no improvement yet; the window checkpoint decides."
    return "measuring", "Measurement in progress."


def propose_outcome_contract(
    problem: ProblemRecord,
    signals: list[Any],
    now: str,
) -> OutcomeContract | None:
    """Auto-proposed contract at approval time (W4): keep the promotion metric,
    re-anchor the baseline on the trailing 28 days of REAL signal inflow, and
    upgrade the comparison to ITS segmented regression over a 30-day window.

    Returns None for metrics CLARA cannot observe (seed problems' business
    metrics) — those keep their manually authored contracts — and for a
    zero-signal trailing window: a baseline of 0.0 makes the halving
    convention degenerate (threshold == baseline flips the inferred
    direction, so any recurrence would read as target_met).
    """
    contract = problem.outcome_contract
    parsed = _metric_journey_stage(contract.primary_metric)
    if parsed is None:
        return None
    journey, stage = parsed
    end = _parse_ts(now)
    start = end - timedelta(days=TRAILING_BASELINE_DAYS)
    window_stamps = [
        ts
        for ts in _matching_timestamps(signals, journey=journey, journey_stage=stage)
        if start <= ts < end
    ]
    if not window_stamps:
        return None
    # Rate over the OBSERVED span, not a fixed 28d: dividing a young
    # workspace's count by fabricated zero-days dilutes the baseline up to
    # 4x and turns real improvements into reported failures.
    span_days = min(
        float(TRAILING_BASELINE_DAYS),
        max((end - window_stamps[0]).total_seconds() / 86400.0, 1.0),
    )
    baseline = round(len(window_stamps) / span_days, 4)
    return OutcomeContract(
        primary_metric=contract.primary_metric,
        baseline=baseline,
        success_threshold=round(baseline * 0.5, 4),
        measurement_window_days=PROPOSED_WINDOW_DAYS,
        comparison_method=ITS_COMPARISON_METHOD,
        guardrail_metrics=list(contract.guardrail_metrics),
        responsible_owner=contract.responsible_owner,
    )


def its_outcome_for_problem(
    problem: ProblemRecord,
    signals: list[Any],
    *,
    executed_at: str,
    now: str,
) -> dict[str, Any] | None:
    """Read-time ITS scoring for a problem's approved+executed action.

    Builds the daily count series for the contract's journey/stage over
    [executed_at - 28d, min(now, executed_at + window)], bucketed by UTC day
    with zero-signal days included, and runs segmented regression. The series
    comes from raw signals only — simulated data never writes signals, so it
    is real-source by construction. Returns None for non-signal metrics.
    """
    parsed = _metric_journey_stage(problem.outcome_contract.primary_metric)
    if parsed is None:
        return None
    journey, stage = parsed

    executed = _parse_ts(executed_at)
    window_days = problem.outcome_contract.measurement_window_days
    end = min(_parse_ts(now), executed + timedelta(days=window_days))
    start = executed - timedelta(days=TRAILING_BASELINE_DAYS)

    stamps = [
        ts
        for ts in _matching_timestamps(signals, journey=journey, journey_stage=stage)
        if start <= ts <= end
    ]
    if not stamps:
        return _insufficient_delta(delta=0.0, n_pre=0, n_post=0)

    # Complete UTC days only. The bucket for `end`'s own day is partial on
    # every mid-window read and would enter the regression at full-day scale
    # with maximum leverage on the effect estimate; same for `start`'s day.
    if stamps[0] > start:
        # Honest pre-window: never fabricate observation days before data
        # existed. The first signal's day is a complete observation (zero
        # signals before it that day is real data, not a window artifact).
        start_date = _utc_date(stamps[0])
    else:
        start_utc = start.astimezone(timezone.utc)
        start_date = start_utc.date()
        if start_utc.time() != time.min:
            start_date += timedelta(days=1)
    end_date = _utc_date(end) - timedelta(days=1)
    exec_day = _utc_date(executed)
    if end_date < start_date:
        return _insufficient_delta(delta=0.0, n_pre=0, n_post=0)

    total_days = (end_date - start_date).days + 1
    raw = [0.0] * total_days
    for ts in stamps:
        index = (_utc_date(ts) - start_date).days
        if 0 <= index < total_days:
            raw[index] += 1.0

    # The execution day mixes pre- and post-intervention signals — drop it
    # from the fit (standard ITS practice) and keep the real time axis.
    times: list[float] = []
    counts: list[float] = []
    for offset in range(total_days):
        if start_date + timedelta(days=offset) == exec_day:
            continue
        times.append(float(offset))
        counts.append(raw[offset])
    if not counts:
        return _insufficient_delta(delta=0.0, n_pre=0, n_post=0)

    action_index = max((exec_day - start_date).days + 1, 0)
    result = its_effect(counts, action_index, times=times)

    # --- Volume-adjusted readout (science review R6/F6) -------------------
    # The raw metric is a COUNT: if total feedback inflow drops platform-wide
    # (seasonality, a connector outage, a feed going dark), every open
    # contract "improves". The share series — matched signals over ALL
    # signals that day — is immune to that confound; when the two readouts
    # disagree, the share is the one to believe.
    total_raw = [0.0] * total_days
    for signal in signals:
        try:
            ts = _parse_ts(signal.timestamp)
        except ValueError:
            continue
        index = (_utc_date(ts) - start_date).days
        if 0 <= index < total_days:
            total_raw[index] += 1.0
    shares: list[float] = []
    for offset_f, matched in zip(times, counts):
        total = total_raw[int(offset_f)]
        shares.append(matched / total if total > 0 else 0.0)
    result["volume_adjusted"] = its_effect(shares, action_index, times=times)

    # --- Placebo check (science review R6/F6) -----------------------------
    # Refit with a pseudo-intervention inside the pre-window. A "significant"
    # effect at a date where nothing happened means the series is too noisy or
    # trended to attribute anything to the real action — regression to the
    # mean's calling card, since actions trigger on peaks.
    pre_times = [t for t in times if t < action_index]
    if len(pre_times) >= MIN_PRE_DAYS + MIN_POST_DAYS:
        placebo_index = pre_times[-MIN_POST_DAYS]
        pre_counts = [y for t, y in zip(times, counts) if t < action_index]
        placebo = its_effect(pre_counts, placebo_index, times=pre_times)
        if placebo.get("method") == "its":
            placebo["excludes_zero"] = not (
                placebo["ci_low"] <= 0.0 <= placebo["ci_high"]
            )
            if placebo["excludes_zero"]:
                placebo["warning"] = (
                    "A pseudo-intervention inside the pre-window shows a"
                    " 'significant' effect where nothing happened — this series"
                    " is too noisy or trended to attribute the real change to"
                    " the action."
                )
        result["placebo"] = placebo

    return result
