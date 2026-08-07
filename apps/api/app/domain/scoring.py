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
# Public, read-only view for industry_profiles to merge overrides onto.
DEFAULT_IMPACT_WEIGHTS: dict[str, float] = dict(_DEFAULT_WEIGHTS)

_IMPACT_WEIGHTS: dict[str, float] | None = None


def _load_weights() -> dict[str, float]:
    """Resolve impact weights: industry-profile baseline, then env overrides.

    Precedence (lowest to highest): default weights -> active INDUSTRY_PROFILE
    overrides -> explicit SCORING_WEIGHT_* env vars. Loaded once and cached;
    call reload_weights() to refresh (e.g. after changing the profile).
    """
    # Lazy import avoids a module-load cycle (industry_profiles imports scoring).
    from app.domain.industry_profiles import resolve_profile_name, weights_for_profile

    weights = dict(weights_for_profile(resolve_profile_name()))
    for key in _DEFAULT_WEIGHTS:
        val = os.getenv(f"SCORING_WEIGHT_{key.upper()}")
        if val is not None:
            try:
                weights[key] = float(val)
            except ValueError:
                pass  # invalid env -> keep the profile/default value
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


def normalized_impact_score(
    factors: Mapping[str, float],
    *,
    weights: Mapping[str, float] | None = None,
) -> float:
    """Return a weighted impact score between 0 and 1.

    ``weights`` overrides the active (profile + env) weights for one call — used
    to score a signal under a specific industry profile without changing the
    global selection (e.g. weights_for_profile("fintech")).
    """
    weights = weights if weights is not None else get_impact_weights()
    total_weight = sum(weights.values())
    weighted_score = 0.0

    for factor, weight in weights.items():
        weighted_score += clamp(float(factors.get(factor, 0.0))) * weight

    return round(weighted_score / total_weight, 3)


def impact_drivers(
    factors: Mapping[str, float],
    *,
    weights: Mapping[str, float] | None = None,
    top_n: int = 3,
) -> list[tuple[str, float]]:
    """Return the factors that produced the impact score, ranked by contribution.

    This is an exact decomposition of ``normalized_impact_score``, not a second
    heuristic: each factor's share is its own weighted term over the total
    weighted score, so the shares of all eight factors sum to 1.0 and the same
    ``weights`` argument yields a decomposition of the same number.

    Why this exists: the approver sees a single score, and a single score cannot
    be argued with. Naming the two or three factors that drove it is what makes
    the priority contestable — and it matters more than it looks, because
    industry profiles re-weight the factors, so an identical score means
    different things in fintech and in manufacturing.

    Returns ``[]`` when every factor is zero — there is nothing to attribute,
    and inventing a ranking from zeros would be a lie with a decimal point.
    """
    weights = weights if weights is not None else get_impact_weights()

    contributions = {
        factor: clamp(float(factors.get(factor, 0.0))) * weight
        for factor, weight in weights.items()
    }
    total = sum(contributions.values())
    if total <= 0.0:
        return []

    ranked = sorted(contributions.items(), key=lambda item: item[1], reverse=True)
    return [
        (factor, round(contribution / total, 3))
        for factor, contribution in ranked[:top_n]
        if contribution > 0.0
    ]


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
