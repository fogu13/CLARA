"""Emerging-problem report — corroboration-gated, burst-tested surfacing.

Two layers decide the "action" tier:

1. The additive presence score + corroboration floor (original design): the
   score is volume-dominated, so acting additionally requires multi-source
   evidence or several distinct identified customers.
2. A burst statistic (science review R5): the score measured PRESENCE, not
   emergence — a theme that always produces five signals a week scored like a
   genuinely new spike, the 7d/30d trend ratio flipped on 3-vs-2 noise, and
   testing every candidate every report build is a multiplicity problem. Each
   candidate now gets an exact two-window rate test (recent 7 days vs the prior
   28), and the p-values are Benjamini-Hochberg adjusted ACROSS the report so
   "action" carries a controlled false-alarm rate. Candidates whose evidence
   has no usable timestamps keep the legacy behaviour and say so in a driver.

The exact test: under equal rates, the recent count conditioned on the total is
Binomial(k1+k2, w1/(w1+w2)) — the standard conditional comparison of two
Poisson rates. One-sided (bursts up), exact via comb(), stdlib only.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from math import comb

from app.domain.models import (
    CandidateReviewStatus,
    EmergingProblemReport,
    EmergingProblemSignal,
    ProblemCandidate,
    SignalRecord,
)
from app.services.signals import utc_now

ACTION_THRESHOLD = 0.68
WATCH_THRESHOLD = 0.48
# Corroboration floor for "action": the score is volume-dominated, so a burst
# from one source (or one identifier-less CSV) could page someone on its own.
# Acting additionally requires multi-source evidence or several distinct
# identified customers; otherwise the candidate is held at "watch".
MIN_ACTION_SOURCES = 2
MIN_ACTION_CUSTOMERS = 3

RECENT_WINDOW_DAYS = 7
BASELINE_WINDOW_DAYS = 28
# BH false-discovery ceiling for the "action" tier: at most ~10% of flagged
# bursts are expected to be noise. Watch-tier surfacing is not gated on it.
BURST_FDR_Q = 0.10


def _binom_sf(k: int, n: int, p: float) -> float:
    """P(X >= k) for X ~ Binomial(n, p) — exact, stdlib."""
    if k <= 0:
        return 1.0
    if k > n:
        return 0.0
    q = 1.0 - p
    return min(1.0, sum(comb(n, i) * (p**i) * (q ** (n - i)) for i in range(k, n + 1)))


def burst_p_value(recent_count: int, baseline_count: int) -> float:
    """One-sided exact test that the recent rate exceeds the baseline rate.

    Conditional two-Poisson comparison: recent | total ~ Binomial(total, w1/(w1+w2)).
    """
    total = recent_count + baseline_count
    if total == 0:
        return 1.0
    expected_share = RECENT_WINDOW_DAYS / (RECENT_WINDOW_DAYS + BASELINE_WINDOW_DAYS)
    return _binom_sf(recent_count, total, expected_share)


def benjamini_hochberg(p_values: list[float]) -> list[float]:
    """BH-adjusted q-values, preserving input order."""
    m = len(p_values)
    if m == 0:
        return []
    order = sorted(range(m), key=lambda i: p_values[i])
    q = [0.0] * m
    running = 1.0
    for rank_from_end, idx in enumerate(reversed(order)):
        rank = m - rank_from_end
        running = min(running, p_values[idx] * m / rank)
        q[idx] = round(min(1.0, running), 4)
    return q


def _parse_ts(value: str) -> datetime | None:
    try:
        parsed = datetime.fromisoformat((value or "").replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def _candidate_burst(
    candidate: ProblemCandidate,
    signals_by_id: dict[str, SignalRecord],
    now: datetime,
) -> tuple[float | None, float | None, float | None]:
    """(recent_rate, baseline_rate, p_value) from the candidate's own evidence."""
    stamps = []
    for evidence in candidate.evidence:
        signal = signals_by_id.get(evidence.signal_id)
        if signal is None:
            continue
        ts = _parse_ts(signal.timestamp)
        if ts is not None:
            stamps.append(ts)
    if not stamps:
        return None, None, None
    recent_start = now - timedelta(days=RECENT_WINDOW_DAYS)
    baseline_start = recent_start - timedelta(days=BASELINE_WINDOW_DAYS)
    recent = sum(1 for ts in stamps if ts >= recent_start)
    baseline = sum(1 for ts in stamps if baseline_start <= ts < recent_start)
    return (
        round(recent / RECENT_WINDOW_DAYS, 4),
        round(baseline / BASELINE_WINDOW_DAYS, 4),
        burst_p_value(recent, baseline),
    )


def build_emerging_problem_report(
    candidates: list[ProblemCandidate],
    signals: list[SignalRecord] | None = None,
) -> EmergingProblemReport:
    now = _parse_ts(utc_now()) or datetime.now(timezone.utc)
    signals_by_id = {s.signal_id: s for s in (signals or [])}

    enriched: list[tuple[ProblemCandidate, float | None, float | None, float | None]] = []
    for candidate in candidates:
        if candidate.emerging_problem_score < WATCH_THRESHOLD:
            continue
        recent_rate, baseline_rate, p_value = (
            _candidate_burst(candidate, signals_by_id, now)
            if signals_by_id
            else (None, None, None)
        )
        enriched.append((candidate, recent_rate, baseline_rate, p_value))

    tested = [item for item in enriched if item[3] is not None]
    q_values = benjamini_hochberg([item[3] for item in tested if item[3] is not None])
    q_by_candidate = {item[0].candidate_id: q for item, q in zip(tested, q_values)}

    report_signals = []
    for candidate, recent_rate, baseline_rate, _p in enriched:
        signal = emerging_signal_for_candidate(
            candidate,
            recent_rate=recent_rate,
            baseline_rate=baseline_rate,
            burst_q=q_by_candidate.get(candidate.candidate_id),
        )
        if signal is not None:
            report_signals.append(signal)

    report_signals = sorted(
        report_signals, key=lambda signal: signal.emerging_score, reverse=True
    )
    return EmergingProblemReport(
        generated_at=utc_now(),
        candidate_count=len(candidates),
        watch_count=sum(signal.trend_label == "watch" for signal in report_signals),
        action_count=sum(signal.trend_label == "action" for signal in report_signals),
        signals=report_signals,
    )


def emerging_signal_for_candidate(
    candidate: ProblemCandidate,
    *,
    recent_rate: float | None = None,
    baseline_rate: float | None = None,
    burst_q: float | None = None,
) -> EmergingProblemSignal | None:
    score = candidate.emerging_problem_score
    if score < WATCH_THRESHOLD:
        return None

    corroborated = (
        len(candidate.sources) >= MIN_ACTION_SOURCES
        or candidate.customer_count >= MIN_ACTION_CUSTOMERS
    )
    # A missing burst test (no timestamps / no signals passed) does not veto —
    # the legacy behaviour is preserved and disclosed in a driver instead.
    burst_confirmed = burst_q is None or burst_q <= BURST_FDR_Q
    trend_label = (
        "action" if score >= ACTION_THRESHOLD and corroborated and burst_confirmed else "watch"
    )
    taxonomy_labels = [classification.label for classification in candidate.classifications[:3]]
    drivers = emerging_drivers(candidate)
    if score >= ACTION_THRESHOLD and not corroborated:
        drivers.insert(
            0, "Held at watch: single-source evidence with few identified customers"
        )
    if burst_q is not None:
        if burst_q <= BURST_FDR_Q:
            drivers.insert(
                0,
                f"Burst confirmed: {recent_rate}/day recent vs {baseline_rate}/day baseline"
                f" (q={burst_q}, FDR-adjusted across this report)",
            )
        else:
            drivers.insert(
                0,
                f"No burst above baseline: {recent_rate}/day recent vs {baseline_rate}/day"
                f" (q={burst_q}) — presence, not emergence; held at watch",
            )
    elif recent_rate is None and burst_q is None:
        drivers.append("Burst test unavailable: no usable evidence timestamps")
    drivers = drivers[:5]
    return EmergingProblemSignal(
        candidate_id=candidate.candidate_id,
        title=candidate.title,
        journey=candidate.journey,
        journey_stage=candidate.journey_stage,
        emerging_score=score,
        trend_label=trend_label,
        signal_count=candidate.signal_count,
        source_count=len(candidate.sources),
        customer_count=candidate.customer_count,
        account_count=candidate.account_count,
        first_seen=candidate.first_seen,
        last_seen=candidate.last_seen,
        taxonomy_labels=taxonomy_labels,
        drivers=drivers,
        recommended_next_step=recommended_next_step(candidate, trend_label),
        recent_rate=recent_rate,
        baseline_rate=baseline_rate,
        burst_q=burst_q,
    )


def emerging_drivers(candidate: ProblemCandidate) -> list[str]:
    drivers: list[str] = []
    if candidate.signal_count >= 5:
        drivers.append(f"{candidate.signal_count} signals in one journey stage")
    elif candidate.signal_count >= 3:
        drivers.append(f"{candidate.signal_count} early signals in one journey stage")

    if len(candidate.sources) >= 2:
        drivers.append(f"Evidence spans {len(candidate.sources)} sources")

    if candidate.review_status == CandidateReviewStatus.pending:
        drivers.append("Candidate is still pending review")

    if candidate.classifications:
        top = candidate.classifications[0]
        drivers.append(f"{top.label} classified at {round(top.confidence * 100)}% confidence")

    if candidate.terminology_hits:
        drivers.append(f"Terminology hits: {', '.join(candidate.terminology_hits[:3])}")

    if candidate.contradictory_evidence:
        drivers.append("Contradictory evidence needs validation")

    return drivers[:5]


def recommended_next_step(candidate: ProblemCandidate, trend_label: str) -> str:
    if trend_label == "action":
        return (
            f"Review {candidate.journey_stage} evidence, confirm the root-cause analysis, "
            "then accept or route the candidate."
        )
    return (
        f"Monitor {candidate.journey_stage} for more signals and validate taxonomy matches "
        "before promotion."
    )
