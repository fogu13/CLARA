from __future__ import annotations

from app.domain.models import (
    CandidateReviewStatus,
    EmergingProblemReport,
    EmergingProblemSignal,
    ProblemCandidate,
)
from app.services.signals import utc_now

ACTION_THRESHOLD = 0.68
WATCH_THRESHOLD = 0.48


def build_emerging_problem_report(
    candidates: list[ProblemCandidate],
) -> EmergingProblemReport:
    signals = [
        signal
        for candidate in candidates
        if (signal := emerging_signal_for_candidate(candidate)) is not None
    ]
    signals = sorted(signals, key=lambda signal: signal.emerging_score, reverse=True)
    return EmergingProblemReport(
        generated_at=utc_now(),
        candidate_count=len(candidates),
        watch_count=sum(signal.trend_label == "watch" for signal in signals),
        action_count=sum(signal.trend_label == "action" for signal in signals),
        signals=signals,
    )


def emerging_signal_for_candidate(
    candidate: ProblemCandidate,
) -> EmergingProblemSignal | None:
    score = candidate.emerging_problem_score
    if score < WATCH_THRESHOLD:
        return None

    trend_label = "action" if score >= ACTION_THRESHOLD else "watch"
    taxonomy_labels = [classification.label for classification in candidate.classifications[:3]]
    drivers = emerging_drivers(candidate)
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
