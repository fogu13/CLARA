import pytest

from app.domain.scoring import (
    DEFAULT_IMPACT_WEIGHTS,
    approval_pressure,
    impact_band,
    impact_drivers,
    normalized_impact_score,
)

FACTORS = {
    "customer_reach": 0.7,
    "severity": 0.9,
    "recurrence": 0.8,
    "journey_criticality": 1.0,
    "account_exposure": 0.5,
    "financial_exposure": 0.4,
    "regulatory_risk": 0.2,
    "evidence_confidence": 0.9,
}


def test_normalized_impact_score_weights_core_factors() -> None:
    score = normalized_impact_score(
        {
            "customer_reach": 0.7,
            "severity": 0.9,
            "recurrence": 0.8,
            "journey_criticality": 1.0,
            "account_exposure": 0.5,
            "financial_exposure": 0.4,
            "regulatory_risk": 0.2,
            "evidence_confidence": 0.9,
        }
    )

    assert 0.65 <= score <= 0.75


def test_impact_band_thresholds() -> None:
    assert impact_band(0.8) == "critical"
    assert impact_band(0.6) == "high"
    assert impact_band(0.4) == "medium"
    assert impact_band(0.2) == "low"


def test_impact_drivers_shares_sum_to_one() -> None:
    """The decomposition must account for the whole score, or it explains nothing."""
    all_drivers = impact_drivers(FACTORS, top_n=len(DEFAULT_IMPACT_WEIGHTS))

    assert len(all_drivers) == len(DEFAULT_IMPACT_WEIGHTS)
    assert sum(share for _, share in all_drivers) == pytest.approx(1.0, abs=0.005)


def test_impact_drivers_rank_by_weighted_contribution_not_raw_value() -> None:
    """journey_criticality (1.0 x 1.2) must outrank severity (0.9 x 1.25 = 1.125)."""
    top = impact_drivers(FACTORS, top_n=2)

    assert [factor for factor, _ in top] == ["journey_criticality", "severity"]
    assert top[0][1] > top[1][1]


def test_impact_drivers_follow_profile_weights() -> None:
    """Re-weighting must change the explanation, not just the score.

    This is the reason the drivers are derived rather than stored: the same
    factors under a regulatory-heavy profile are driven by a different factor.
    """
    regulatory_heavy = dict(DEFAULT_IMPACT_WEIGHTS, regulatory_risk=20.0)

    top = impact_drivers(FACTORS, weights=regulatory_heavy, top_n=1)

    assert top[0][0] == "regulatory_risk"


def test_impact_drivers_empty_when_nothing_to_attribute() -> None:
    """All-zero factors must yield no ranking rather than an arbitrary one."""
    assert impact_drivers(dict.fromkeys(DEFAULT_IMPACT_WEIGHTS, 0.0)) == []
    assert impact_drivers({}) == []


def test_impact_drivers_skip_zero_contributors() -> None:
    only_severity = dict.fromkeys(DEFAULT_IMPACT_WEIGHTS, 0.0) | {"severity": 0.8}

    assert impact_drivers(only_severity) == [("severity", 1.0)]


def test_impact_drivers_survive_the_jsonb_round_trip() -> None:
    """Records persist as jsonb via model_dump -> model_validate (postgres.py).

    A computed field is serialised on dump but is not a validation input, so the
    round trip must neither fail nor leave the drivers empty. Uses the real seed
    problems so the shapes are the ones actually stored.
    """
    from app.domain.models import ProblemRecord
    from app.services.seed import load_seed_problems

    problem = load_seed_problems()[0]
    assert problem.impact_drivers, "seed problem should attribute a non-zero score"

    payload = problem.model_dump(mode="json", by_alias=True)
    assert "impact_drivers" in payload

    restored = ProblemRecord.model_validate(payload)
    assert restored.impact_drivers == problem.impact_drivers


def test_approval_pressure_blocks_policy_failures() -> None:
    assert approval_pressure("approval_needed", 0) == "needs_review"
    assert approval_pressure("validation_required", 0) == "needs_review"
    assert approval_pressure("blocked_by_policy", 0) == "blocked"
    assert approval_pressure("approval_needed", 1) == "blocked"
