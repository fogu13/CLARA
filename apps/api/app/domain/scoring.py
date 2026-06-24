from __future__ import annotations

import os
from collections.abc import Mapping

_DEFAULT_WEIGHTS: dict[str, float] = {
    "customer_reach": 1.0,
    "severity": 1.25,
    "recurrence": 1.0,
    "journey_criticality": 1.2,
    "account_exposure": 0.9,
    "financial_exposure": 0.9,
    "regulatory_risk": 1.1,
    "evidence_confidence": 1.0,
}

_IMPACT_WEIGHTS: dict[str, float] | None = None


def _load_weights() -> dict[str, float]:
    """Load impact weights from env vars, falling back to defaults.

    Env vars: SCORING_WEIGHT_CUSTOMER_REACH, SCORING_WEIGHT_SEVERITY, etc.
    Weights are loaded once and cached; call reload_weights() to refresh.
    """
    weights: dict[str, float] = {}
    for key, default in _DEFAULT_WEIGHTS.items():
        env_key = f"SCORING_WEIGHT_{key.upper()}"
        val = os.getenv(env_key)
        if val is not None:
            try:
                weights[key] = float(val)
            except ValueError:
                weights[key] = default
        else:
            weights[key] = default
    return weights


def reload_weights() -> None:
    """Force reload of weights from env vars (useful for tests)."""
    global _IMPACT_WEIGHTS
    _IMPACT_WEIGHTS = None


def get_impact_weights() -> dict[str, float]:
    """Get the current impact weights (cached after first load)."""
    global _IMPACT_WEIGHTS
    if _IMPACT_WEIGHTS is None:
        _IMPACT_WEIGHTS = _load_weights()
    return _IMPACT_WEIGHTS


def clamp(value: float, minimum: float = 0.0, maximum: float = 1.0) -> float:
    return max(minimum, min(maximum, value))


def normalized_impact_score(factors: Mapping[str, float]) -> float:
    """Return a weighted impact score between 0 and 1."""
    weights = get_impact_weights()
    total_weight = sum(weights.values())
    weighted_score = 0.0

    for factor, weight in weights.items():
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
