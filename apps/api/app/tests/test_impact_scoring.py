from app.domain.scoring import approval_pressure, impact_band, normalized_impact_score


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


def test_approval_pressure_blocks_policy_failures() -> None:
    assert approval_pressure("approval_needed", 0) == "needs_review"
    assert approval_pressure("validation_required", 0) == "needs_review"
    assert approval_pressure("blocked_by_policy", 0) == "blocked"
    assert approval_pressure("approval_needed", 1) == "blocked"
