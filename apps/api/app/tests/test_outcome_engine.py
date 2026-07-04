"""Tests for the outcome engine — resolution_score + direction-aware status + closure."""

from __future__ import annotations

from app.services.outcome_engine import (
    build_outcome_contract,
    clamp01,
    closure_level,
    measure_outcome,
    outcome_direction,
    outcome_status,
    resolution_score,
)


class TestClamp01:
    def test_clamps_below_zero(self) -> None:
        assert clamp01(-0.5) == 0.0

    def test_clamps_above_one(self) -> None:
        assert clamp01(1.5) == 1.0

    def test_passes_through_valid_range(self) -> None:
        assert clamp01(0.3) == 0.3
        assert clamp01(0.0) == 0.0
        assert clamp01(1.0) == 1.0


class TestOutcomeDirection:
    def test_increase_when_target_above_baseline(self) -> None:
        assert outcome_direction(baseline=10, target=20) == "increase"

    def test_decrease_when_target_below_baseline(self) -> None:
        assert outcome_direction(baseline=50, target=10) == "decrease"

    def test_increase_when_equal(self) -> None:
        assert outcome_direction(baseline=10, target=10) == "increase"


class TestOutcomeStatus:
    def test_not_measured_when_none(self) -> None:
        assert outcome_status(baseline=10, target=20, measured=None) == "not_measured"

    def test_target_met_increase(self) -> None:
        assert outcome_status(baseline=10, target=20, measured=25) == "target_met"

    def test_improving_increase(self) -> None:
        assert outcome_status(baseline=10, target=20, measured=15) == "improving"

    def test_not_improved_increase(self) -> None:
        assert outcome_status(baseline=10, target=20, measured=8) == "not_improved"

    def test_target_met_decrease(self) -> None:
        # Complaint rate: baseline 50, target 5, measured 3 -> target met
        assert outcome_status(baseline=50, target=5, measured=3) == "target_met"

    def test_improving_decrease(self) -> None:
        # Complaint rate: baseline 50, target 5, measured 30 -> improving
        assert outcome_status(baseline=50, target=5, measured=30) == "improving"

    def test_not_improved_decrease(self) -> None:
        # Complaint rate: baseline 50, target 5, measured 60 -> not improved
        assert outcome_status(baseline=50, target=5, measured=60) == "not_improved"

    def test_explicit_direction_wins_over_derivation_for_zero_baseline(self) -> None:
        # target(0) >= baseline(0) derives "increase", which would report ANY
        # recurrence as target_met; the explicit contract direction must win.
        assert outcome_status(baseline=0, target=0, measured=2, direction="decrease") == "not_improved"
        assert outcome_status(baseline=0, target=0, measured=0, direction="decrease") == "target_met"


class TestResolutionScore:
    def test_decrease_full_resolution(self) -> None:
        # Complaints dropped to 0: score = 1 - 0/50 = 1.0
        assert resolution_score(baseline=50, measured=0, direction="decrease") == 1.0

    def test_decrease_half_resolution(self) -> None:
        # Complaints halved: score = 1 - 25/50 = 0.5
        assert resolution_score(baseline=50, measured=25, direction="decrease") == 0.5

    def test_decrease_no_improvement(self) -> None:
        # Complaints unchanged: score = 1 - 50/50 = 0.0
        assert resolution_score(baseline=50, measured=50, direction="decrease") == 0.0

    def test_decrease_worse_than_baseline(self) -> None:
        # Complaints increased: score clamped to 0
        assert resolution_score(baseline=50, measured=80, direction="decrease") == 0.0

    def test_decrease_zero_baseline_no_recurrence(self) -> None:
        assert resolution_score(baseline=0, measured=0, direction="decrease") == 1.0

    def test_decrease_zero_baseline_with_recurrence(self) -> None:
        assert resolution_score(baseline=0, measured=5, direction="decrease") == 0.5

    def test_increase_full_target(self) -> None:
        # Adoption: baseline 10, measured 20 -> score = 20/10 = 1.0 (clamped)
        assert resolution_score(baseline=10, measured=20, direction="increase") == 1.0

    def test_increase_partial(self) -> None:
        # Adoption: baseline 10, measured 15 -> score = 15/10 = 0.5 (wait, that's 1.5 clamped)
        # Actually: 15/10 = 1.5, clamped to 1.0. Let's test 12/10 = 1.2 clamped to 1.0
        # For a partial, we need measured < baseline in increase mode... that doesn't make sense.
        # The increase formula is measured/baseline, so measured=12, baseline=10 -> 1.2 -> clamped 1.0
        # measured=5, baseline=10 -> 0.5
        assert resolution_score(baseline=10, measured=5, direction="increase") == 0.5

    def test_increase_zero_baseline_positive_measured(self) -> None:
        assert resolution_score(baseline=0, measured=5, direction="increase") == 1.0


class TestClosureLevel:
    def test_outcome_when_measured_with_good_score(self) -> None:
        level = closure_level(
            action_results=[{"status": "pushed"}],
            measured=5,
            score=0.8,
        )
        assert level == "outcome"

    def test_operational_when_measured_but_no_improvement(self) -> None:
        level = closure_level(
            action_results=[{"status": "pushed"}],
            measured=50,
            score=0.0,
        )
        assert level == "operational"

    def test_operational_when_action_pushed_no_measurement(self) -> None:
        level = closure_level(
            action_results=[{"status": "pushed"}],
            measured=None,
            score=None,
        )
        assert level == "operational"

    def test_none_when_no_action_and_no_measurement(self) -> None:
        level = closure_level(
            action_results=[],
            measured=None,
            score=None,
        )
        assert level == "none"

    def test_none_when_action_failed(self) -> None:
        level = closure_level(
            action_results=[{"status": "failed"}],
            measured=None,
            score=None,
        )
        assert level == "none"


class TestBuildOutcomeContract:
    def test_defaults_to_affected_contacts(self) -> None:
        insight = {"affected_contacts": 42, "signal_ids": ["s1", "s2"]}
        contract = build_outcome_contract(insight=insight)

        assert contract["metric"] == "affected_contacts"
        assert contract["baseline"] == 42
        assert contract["target"] == 0
        assert contract["direction"] == "decrease"

    def test_prefers_tag_recurrence(self) -> None:
        insight = {
            "affected_contacts": 42,
            "signal_ids": ["s1", "s2", "s3"],
            "tag": "checkout_failure",
            "qual_signal_count": 3,
        }
        contract = build_outcome_contract(insight=insight)

        assert contract["metric"] == "tag:checkout_failure"
        assert contract["baseline"] == 3
        assert contract["direction"] == "decrease"

    def test_measurement_window_days(self) -> None:
        contract = build_outcome_contract(
            insight={"affected_contacts": 10},
            measurement_window_days=30,
        )
        assert contract["measurement_window_days"] == 30


class TestMeasureOutcome:
    def test_full_measurement_with_improvement(self) -> None:
        contract = {
            "metric": "tag:checkout_failure",
            "baseline": 10,
            "target": 0,
            "direction": "decrease",
            "measurement_window_days": 14,
        }
        result = measure_outcome(
            contract=contract,
            measured_value=2,
            action_results=[{"status": "pushed"}],
        )

        assert result["measured"] == 2
        assert result["resolution_score"] == 0.8  # 1 - 2/10
        assert result["status"] == "improving"
        assert result["closure_level"] == "outcome"
        assert "checkout_failure" in result["summary"]

    def test_full_measurement_with_full_resolution(self) -> None:
        contract = {
            "metric": "tag:bug_report",
            "baseline": 5,
            "target": 0,
            "direction": "decrease",
        }
        result = measure_outcome(
            contract=contract,
            measured_value=0,
            action_results=[{"status": "pushed"}],
        )

        assert result["resolution_score"] == 1.0
        assert result["status"] == "target_met"
        assert result["closure_level"] == "outcome"

    def test_measurement_with_no_improvement(self) -> None:
        contract = {
            "metric": "affected_contacts",
            "baseline": 50,
            "target": 0,
            "direction": "decrease",
        }
        result = measure_outcome(
            contract=contract,
            measured_value=60,
            action_results=[{"status": "pushed"}],
        )

        assert result["resolution_score"] == 0.0
        assert result["status"] == "not_improved"
        assert result["closure_level"] == "operational"

    def test_zero_baseline_decrease_recurrence_is_not_target_met(self) -> None:
        # A tag cluster of purely quantitative signals yields baseline=0 on the
        # standard decrease contract; recurrence must not read as success.
        contract = {"metric": "tag:x", "baseline": 0, "target": 0, "direction": "decrease"}
        result = measure_outcome(contract=contract, measured_value=2)

        assert result["status"] == "not_improved"
        assert result["resolution_score"] == 0.5

    def test_summary_includes_tag_for_tag_metrics(self) -> None:
        contract = {"metric": "tag:onboarding", "baseline": 8, "target": 0, "direction": "decrease"}
        result = measure_outcome(contract=contract, measured_value=3)

        assert "onboarding" in result["summary"]
        assert "3" in result["summary"]
        assert "8" in result["summary"]
