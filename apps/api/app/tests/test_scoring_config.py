"""Tests for configurable scoring weights via env vars."""

from __future__ import annotations

import pytest

from app.domain.scoring import (
    get_impact_weights,
    normalized_impact_score,
    reload_weights,
)


@pytest.fixture(autouse=True)
def _reset_weights():
    """Ensure weights are reloaded fresh for each test."""
    reload_weights()
    yield
    reload_weights()


class TestConfigurableWeights:
    def test_default_weights(self) -> None:
        reload_weights()
        weights = get_impact_weights()
        assert weights["severity"] == 1.25
        assert weights["journey_criticality"] == 1.2
        assert weights["customer_reach"] == 1.0

    def test_env_override_changes_weight(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("SCORING_WEIGHT_SEVERITY", "2.0")
        reload_weights()
        weights = get_impact_weights()
        assert weights["severity"] == 2.0

    def test_env_invalid_value_falls_back(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("SCORING_WEIGHT_SEVERITY", "not-a-number")
        reload_weights()
        weights = get_impact_weights()
        assert weights["severity"] == 1.25  # default

    def test_multiple_env_overrides(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("SCORING_WEIGHT_CUSTOMER_REACH", "0.5")
        monkeypatch.setenv("SCORING_WEIGHT_REGULATORY_RISK", "2.5")
        reload_weights()
        weights = get_impact_weights()
        assert weights["customer_reach"] == 0.5
        assert weights["regulatory_risk"] == 2.5

    def test_env_override_affects_score(self, monkeypatch: pytest.MonkeyPatch) -> None:
        # With default weights, severity=1.0 should give a moderate score.
        # If we boost severity weight to 10.0, severity=1.0 should dominate.
        factors = {
            "customer_reach": 0.0,
            "severity": 1.0,
            "recurrence": 0.0,
            "journey_criticality": 0.0,
            "account_exposure": 0.0,
            "financial_exposure": 0.0,
            "regulatory_risk": 0.0,
            "evidence_confidence": 0.0,
        }

        reload_weights()
        default_score = normalized_impact_score(factors)

        monkeypatch.setenv("SCORING_WEIGHT_SEVERITY", "10.0")
        reload_weights()
        boosted_score = normalized_impact_score(factors)

        assert boosted_score > default_score

    def test_reload_clears_cache(self) -> None:
        weights1 = get_impact_weights()
        reload_weights()
        weights2 = get_impact_weights()
        # Same values (no env change), but cache was cleared and reloaded
        assert weights1 == weights2
