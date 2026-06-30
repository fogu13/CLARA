"""Industry profiles: profile resolution + that they retune impact prioritisation."""

from __future__ import annotations

import pytest

from app.domain.industry_profiles import (
    DEFAULT_IMPACT_WEIGHTS,
    get_profile,
    resolve_profile_name,
    weights_for_profile,
)
from app.domain.scoring import (
    get_impact_weights,
    normalized_impact_score,
    reload_weights,
)


@pytest.fixture(autouse=True)
def _isolate_weights():
    """Reset the cached global weights around each test."""
    reload_weights()
    yield
    reload_weights()


class TestProfileResolution:
    def test_default_profile_is_unchanged_defaults(self) -> None:
        assert weights_for_profile("default") == DEFAULT_IMPACT_WEIGHTS

    def test_unknown_profile_falls_back_to_default(self) -> None:
        assert get_profile("does_not_exist").name == "default"

    def test_overrides_merge_onto_defaults(self) -> None:
        w = weights_for_profile("fintech")
        assert w["regulatory_risk"] == 1.6 and w["financial_exposure"] == 1.5
        # an unspecified factor keeps its default
        assert w["recurrence"] == DEFAULT_IMPACT_WEIGHTS["recurrence"]

    def test_resolve_reads_env(self, monkeypatch) -> None:
        monkeypatch.delenv("INDUSTRY_PROFILE", raising=False)
        assert resolve_profile_name() == "default"
        monkeypatch.setenv("INDUSTRY_PROFILE", "fintech")
        assert resolve_profile_name() == "fintech"


class TestPrioritisationShifts:
    REG_FIN = {"regulatory_risk": 1.0, "financial_exposure": 1.0}
    REACH = {"customer_reach": 1.0}

    def test_fintech_ranks_regulatory_higher_than_default(self) -> None:
        default = normalized_impact_score(self.REG_FIN, weights=weights_for_profile("default"))
        fintech = normalized_impact_score(self.REG_FIN, weights=weights_for_profile("fintech"))
        assert fintech > default

    def test_food_delivery_ranks_reach_higher_than_default(self) -> None:
        default = normalized_impact_score(self.REACH, weights=weights_for_profile("default"))
        delivery = normalized_impact_score(self.REACH, weights=weights_for_profile("food_delivery"))
        assert delivery > default

    def test_same_signal_ranked_differently_across_industries(self) -> None:
        # a compliance/money issue matters more to fintech than to food_delivery
        fintech = normalized_impact_score(self.REG_FIN, weights=weights_for_profile("fintech"))
        delivery = normalized_impact_score(self.REG_FIN, weights=weights_for_profile("food_delivery"))
        assert fintech > delivery


class TestEnvActivation:
    def test_env_profile_drives_global_weights(self, monkeypatch) -> None:
        monkeypatch.setenv("INDUSTRY_PROFILE", "fintech")
        reload_weights()
        assert get_impact_weights()["regulatory_risk"] == 1.6

    def test_scoring_weight_env_overrides_profile(self, monkeypatch) -> None:
        monkeypatch.setenv("INDUSTRY_PROFILE", "fintech")
        monkeypatch.setenv("SCORING_WEIGHT_REGULATORY_RISK", "2.0")
        reload_weights()
        assert get_impact_weights()["regulatory_risk"] == 2.0  # explicit env wins
