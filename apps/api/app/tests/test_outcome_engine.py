"""Tests for the outcome engine — resolution_score + direction-aware status + closure,
plus W4: auto-proposed outcome contracts + honest ITS (segmented regression) scoring."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.domain.models import SignalRecord
from app.services.outcome_engine import (
    INSUFFICIENT_DATA_LABEL,
    ITS_COMPARISON_METHOD,
    build_outcome_contract,
    clamp01,
    closure_level,
    its_effect,
    its_outcome_for_problem,
    measure_outcome,
    outcome_direction,
    outcome_status,
    propose_outcome_contract,
    resolution_score,
)
from app.services.seed import load_seed_problems
from app.services.signals import build_candidates, promote_candidate

NOW = datetime.now(UTC).replace(hour=12, minute=0, second=0, microsecond=0)


def _iso(dt: datetime) -> str:
    return dt.isoformat().replace("+00:00", "Z")


def _signal(signal_id: str, *, days_ago: float) -> SignalRecord:
    return SignalRecord(
        signal_id=signal_id,
        customer_id=f"C-{signal_id}",
        account_id="A-1",
        source="webhook",
        journey="checkout",
        journey_stage="payment",
        campaign_exposure=[],
        product_events=[],
        feedback_text=f"Payment problem report {signal_id}",
        language="en",
        timestamp=_iso(NOW - timedelta(days=days_ago)),
    )


def _promoted_problem(signals: list[SignalRecord]):
    return promote_candidate(build_candidates(signals)[0])


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

    def test_zero_degenerate_contract_is_not_measured(self) -> None:
        # "0.0/day from 0 signals · Target met" was meaningless: with nothing
        # observed against a zero baseline and zero target, report not_measured.
        assert outcome_status(baseline=0, target=0, measured=0) == "not_measured"
        assert (
            outcome_status(baseline=0, target=0, measured=0, direction="decrease")
            == "not_measured"
        )

    def test_zero_baseline_recurrence_with_decrease_direction(self) -> None:
        # Explicit decrease direction: a recurrence after a zero baseline is a
        # regression, not target_met (the derived direction would flip here).
        assert (
            outcome_status(baseline=0, target=0, measured=5, direction="decrease")
            == "not_improved"
        )

    def test_explicit_direction_wins_over_derivation_for_zero_baseline(self) -> None:
        # target(0) >= baseline(0) derives "increase", which would report ANY
        # recurrence as target_met; the explicit contract direction must win.
        assert outcome_status(baseline=0, target=0, measured=2, direction="decrease") == "not_improved"
        # measured 0 against baseline 0 / target 0 used to read "target_met";
        # nothing was ever observed, so it is now reported as not_measured (F14).
        assert outcome_status(baseline=0, target=0, measured=0, direction="decrease") == "not_measured"


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


class TestItsEffect:
    def test_exact_recovery_on_noiseless_data(self) -> None:
        # y = 2 + 0.1t pre; level change -3 and slope change -0.05 at t=25.
        series = [
            2 + 0.1 * t + ((-3 - 0.05 * (t - 25)) if t >= 25 else 0.0)
            for t in range(40)
        ]
        result = its_effect(series, 25)

        assert result["method"] == "its"
        assert result["level_change"] == -3.0
        assert result["slope_change"] == -0.05
        assert result["effect"] == round(-3 + (39 - 25) * -0.05, 4)  # -3.7
        # Perfect fit: residual variance 0, so the CI collapses to the point.
        assert result["ci_low"] == result["effect"] == result["ci_high"]
        assert result["n_pre"] == 25 and result["n_post"] == 15

    def test_level_drop_ci_excludes_zero(self) -> None:
        # ~30-day series: pre rate alternates 5/7 (mean 6), post 1/3 (mean 2).
        pre = [7.0 if t % 2 == 0 else 5.0 for t in range(28)]
        post = [3.0 if t % 2 == 0 else 1.0 for t in range(15)]
        result = its_effect(pre + post, 28)

        assert result["method"] == "its"
        assert result["effect"] < 0
        assert result["ci_high"] < 0  # 95% CI excludes 0
        assert result["ci_low"] < result["ci_high"]

    def test_zero_variance_series_yields_zero_effect_and_ci(self) -> None:
        result = its_effect([5.0] * 30, 20)

        assert result["method"] == "its"
        assert result["effect"] == 0.0
        assert result["ci_low"] == 0.0 and result["ci_high"] == 0.0

    def test_all_zero_series(self) -> None:
        result = its_effect([0.0] * 20, 12)

        assert result["method"] == "its"
        assert result["effect"] == 0.0
        assert result["ci_low"] == 0.0 and result["ci_high"] == 0.0

    def test_sparse_pre_period_falls_back_to_labelled_delta(self) -> None:
        result = its_effect([4.0] * 3 + [1.0] * 10, 3)

        assert result["method"] == "delta_insufficient_data"
        assert result["label"] == INSUFFICIENT_DATA_LABEL
        assert result["delta"] == -3.0
        assert result["n_pre"] == 3 and result["n_post"] == 10
        assert "ci_low" not in result  # never a fake CI

    def test_sparse_post_period_falls_back_to_labelled_delta(self) -> None:
        result = its_effect([4.0] * 20 + [1.0] * 3, 20)

        assert result["method"] == "delta_insufficient_data"
        assert result["label"] == INSUFFICIENT_DATA_LABEL


class TestProposeOutcomeContract:
    def test_proposes_observed_span_baseline_and_its_window(self) -> None:
        # 14 signals over 14 observed days -> 1.0/day; dividing by a fixed 28
        # would fabricate zero-days and dilute the baseline to 0.5.
        signals = [_signal(f"s{i}", days_ago=1 + i) for i in range(14)]
        problem = _promoted_problem(signals)

        proposal = propose_outcome_contract(problem, signals, now=_iso(NOW))

        assert proposal is not None
        assert proposal.primary_metric == problem.outcome_contract.primary_metric
        assert proposal.baseline == round(14 / 14.0, 4)
        assert proposal.success_threshold == round(proposal.baseline * 0.5, 4)
        assert proposal.measurement_window_days == 30
        assert proposal.comparison_method == ITS_COMPARISON_METHOD
        assert proposal.guardrail_metrics == problem.outcome_contract.guardrail_metrics
        assert proposal.responsible_owner == problem.outcome_contract.responsible_owner

    def test_span_caps_at_trailing_28d_for_mature_workspaces(self) -> None:
        signals = [
            _signal(f"s{day}-{i}", days_ago=day)
            for day in range(1, 29)
            for i in range(2)
        ]
        problem = _promoted_problem(signals)

        proposal = propose_outcome_contract(problem, signals, now=_iso(NOW))

        assert proposal is not None
        assert proposal.baseline == round(56 / 28.0, 4)

    def test_signals_outside_trailing_window_are_excluded(self) -> None:
        recent = [_signal(f"r{i}", days_ago=1 + i) for i in range(7)]
        stale = [_signal(f"o{i}", days_ago=40 + i) for i in range(5)]
        problem = _promoted_problem(recent + stale)

        proposal = propose_outcome_contract(problem, recent + stale, now=_iso(NOW))

        assert proposal is not None
        assert proposal.baseline == round(7 / 7.0, 4)

    def test_business_metric_contract_is_left_alone(self) -> None:
        seed_problem = load_seed_problems()[0]
        assert not seed_problem.outcome_contract.primary_metric.startswith(
            "signal_rate_per_day:"
        )

        assert propose_outcome_contract(seed_problem, [], now=_iso(NOW)) is None

    def test_zero_signal_trailing_window_proposes_nothing(self) -> None:
        # baseline 0.0 would make threshold == baseline and flip the inferred
        # direction to 'increase' — any recurrence would read as target_met.
        signals = [_signal(f"s{i}", days_ago=40 + i) for i in range(5)]
        problem = _promoted_problem(signals)

        assert propose_outcome_contract(problem, [], now=_iso(NOW)) is None
        assert propose_outcome_contract(problem, signals, now=_iso(NOW)) is None


class TestItsOutcomeForProblem:
    def test_level_drop_detected_with_ci(self) -> None:
        executed = NOW - timedelta(days=15)
        signals: list[SignalRecord] = []
        # Pre: 28 days before execution, alternating 5/7 reports per day.
        for day in range(1, 29):
            count = 7 if day % 2 == 0 else 5
            for i in range(count):
                signals.append(_signal(f"pre-{day}-{i}", days_ago=15 + day))
        # Post: execution day onward, alternating 1/3 reports per day.
        for day in range(15):
            count = 3 if day % 2 == 0 else 1
            for i in range(count):
                signals.append(_signal(f"post-{day}-{i}", days_ago=15 - day - 0.1))
        problem = _promoted_problem(signals)

        result = its_outcome_for_problem(
            problem, signals, executed_at=_iso(executed), now=_iso(NOW)
        )

        assert result is not None
        assert result["method"] == "its"
        assert result["n_pre"] >= 27 and result["n_post"] >= 14
        assert result["effect"] < 0
        assert result["ci_high"] < 0  # the drop is significant, CI excludes 0

    def test_steady_rate_mid_day_read_reports_no_effect(self) -> None:
        # Regression: the partial bucket for the read day used to enter the
        # fit at full-day scale, dragging every mid-window read toward a
        # phantom improvement. With complete-days-only, a steady rate with
        # no true effect must not produce a significant negative effect.
        executed = NOW - timedelta(days=15)
        signals = [
            _signal(f"d{day}-{i}", days_ago=float(day))
            for day in range(1, 44)
            for i in range(10)
        ]
        problem = _promoted_problem(signals)

        # Read mid-day: `now` is 03:00 into the current UTC day.
        read_at = NOW - timedelta(hours=9)
        result = its_outcome_for_problem(
            problem, signals, executed_at=_iso(executed), now=_iso(read_at)
        )

        assert result is not None
        assert result["method"] == "its"
        assert abs(result["effect"]) < 1.0
        assert result["ci_low"] <= 0.0 <= result["ci_high"]

    def test_execution_day_excluded_from_fit(self) -> None:
        # Regression: the execution day mixes pre and post signals; keeping
        # it in the post segment understated the level change and invented a
        # post slope. An instant, complete stop must fit as a clean level
        # drop with no slope artifact.
        executed = NOW - timedelta(days=15)
        signals = [
            _signal(f"pre{day}-{i}", days_ago=float(day))
            for day in range(15, 44)
            for i in range(10)
        ]
        problem = _promoted_problem(signals)

        result = its_outcome_for_problem(
            problem, signals, executed_at=_iso(executed), now=_iso(NOW)
        )

        assert result is not None
        assert result["method"] == "its"
        assert abs(result["level_change"] + 10.0) < 0.5
        assert abs(result["slope_change"]) < 0.2

    def test_sparse_post_period_returns_labelled_delta(self) -> None:
        executed = NOW - timedelta(days=1)
        signals = [_signal(f"s{i}", days_ago=2 + i) for i in range(20)]
        problem = _promoted_problem(signals)

        result = its_outcome_for_problem(
            problem, signals, executed_at=_iso(executed), now=_iso(NOW)
        )

        assert result is not None
        assert result["method"] == "delta_insufficient_data"
        assert result["label"] == INSUFFICIENT_DATA_LABEL

    def test_non_signal_metric_returns_none(self) -> None:
        seed_problem = load_seed_problems()[0]

        result = its_outcome_for_problem(
            seed_problem, [], executed_at=_iso(NOW - timedelta(days=10)), now=_iso(NOW)
        )

        assert result is None

    def test_no_matching_signals_returns_labelled_delta(self) -> None:
        signals = [_signal(f"s{i}", days_ago=1 + i) for i in range(5)]
        problem = _promoted_problem(signals)

        result = its_outcome_for_problem(
            problem, [], executed_at=_iso(NOW - timedelta(days=10)), now=_iso(NOW)
        )

        assert result is not None
        assert result["method"] == "delta_insufficient_data"
        assert result["delta"] == 0.0
        assert result["n_pre"] == 0 and result["n_post"] == 0
