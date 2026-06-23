from __future__ import annotations

from collections.abc import Mapping

IMPACT_WEIGHTS: dict[str, float] = {
    "customer_reach": 1.0,
    "severity": 1.25,
    "recurrence": 1.0,
    "journey_criticality": 1.2,
    "account_exposure": 0.9,
    "financial_exposure": 0.9,
    "regulatory_risk": 1.1,
    "evidence_confidence": 1.0,
}


def clamp(value: float, minimum: float = 0.0, maximum: float = 1.0) -> float:
    return max(minimum, min(maximum, value))


def normalized_impact_score(factors: Mapping[str, float]) -> float:
    """Return a weighted impact score between 0 and 1."""
    total_weight = sum(IMPACT_WEIGHTS.values())
    weighted_score = 0.0

    for factor, weight in IMPACT_WEIGHTS.items():
        weighted_score += clamp(float(factors.get(factor, 0.0))) * weight

    return round(weighted_score / total_weight, 3)


def impact_band(score: float) -> str:
    normalized = clamp(score)

    if normalized >= 0.78:
        return "critical"
    if normalized >= 0.58:
        return "high"
    if normalized >= 0.38:
        return "medium"
    return "low"


def approval_pressure(status: str, governance_failures: int) -> str:
    if governance_failures > 0 or status == "blocked_by_policy":
        return "blocked"
    if status in {"approval_needed", "review_required", "validation_required"}:
        return "needs_review"
    return "ready"
