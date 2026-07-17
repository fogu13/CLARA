from app.domain.models import OutcomeContract, OutcomeMeasurement
from app.services.seed import load_seed_problems
from app.services.workflow import WorkflowStore


def test_outcome_snapshot_zero_baseline_signal_rate_is_never_target_met() -> None:
    # signal_rate contracts are decrease-style even at baseline 0. Deriving the
    # direction from target >= baseline used to flip them to "increase" and
    # report a recurrence — or literally nothing ("0.0/day from 0 signals") —
    # as "Target met" on the outcome board.
    problem = load_seed_problems()[0].model_copy(
        update={
            "outcome_contract": OutcomeContract(
                primary_metric="signal_rate_per_day:checkout",
                baseline=0.0,
                success_threshold=0.0,
                measurement_window_days=30,
                comparison_method="its_v1",
                guardrail_metrics=[],
                responsible_owner="cx_lead",
            )
        }
    )
    store = WorkflowStore()

    snapshot = store.outcome_snapshot(problem)
    assert snapshot.improvement_direction == "decrease"
    assert snapshot.status == "not_measured"

    store.record_outcome(
        problem=problem,
        measurement=OutcomeMeasurement(
            problem_id=problem.problem_id,
            metric=problem.outcome_contract.primary_metric,
            observed_value=0.0,
            measured_at="2026-07-01T00:00:00Z",
        ),
    )
    assert store.outcome_snapshot(problem).status == "not_measured"

    store.record_outcome(
        problem=problem,
        measurement=OutcomeMeasurement(
            problem_id=problem.problem_id,
            metric=problem.outcome_contract.primary_metric,
            observed_value=3.0,
            measured_at="2026-07-02T00:00:00Z",
        ),
    )
    assert store.outcome_snapshot(problem).status == "not_improved"


def test_outcome_snapshot_status_variants_for_increase_metric() -> None:
    problem = load_seed_problems()[0]
    store = WorkflowStore()

    assert store.outcome_snapshot(problem).status == "not_measured"
    assert store.outcome_snapshot(problem).improvement_direction == "increase"

    store.record_outcome(
        problem=problem,
        measurement=OutcomeMeasurement(
            problem_id=problem.problem_id,
            metric=problem.outcome_contract.primary_metric,
            observed_value=problem.outcome_contract.baseline,
            measured_at="2026-07-01T00:00:00Z",
        ),
    )
    assert store.outcome_snapshot(problem).status == "not_improved"

    store.record_outcome(
        problem=problem,
        measurement=OutcomeMeasurement(
            problem_id=problem.problem_id,
            metric=problem.outcome_contract.primary_metric,
            observed_value=problem.outcome_contract.baseline + 0.01,
            measured_at="2026-07-02T00:00:00Z",
        ),
    )
    assert store.outcome_snapshot(problem).status == "improving"

    store.record_outcome(
        problem=problem,
        measurement=OutcomeMeasurement(
            problem_id=problem.problem_id,
            metric=problem.outcome_contract.primary_metric,
            observed_value=problem.outcome_contract.success_threshold,
            measured_at="2026-07-03T00:00:00Z",
        ),
    )
    assert store.outcome_snapshot(problem).status == "target_met"


def test_outcome_snapshot_status_variants_for_decrease_metric() -> None:
    problem = load_seed_problems()[1]
    store = WorkflowStore()

    assert store.outcome_snapshot(problem).status == "not_measured"
    assert store.outcome_snapshot(problem).improvement_direction == "decrease"

    store.record_outcome(
        problem=problem,
        measurement=OutcomeMeasurement(
            problem_id=problem.problem_id,
            metric=problem.outcome_contract.primary_metric,
            observed_value=problem.outcome_contract.baseline,
            measured_at="2026-07-01T00:00:00Z",
        ),
    )
    assert store.outcome_snapshot(problem).status == "not_improved"

    store.record_outcome(
        problem=problem,
        measurement=OutcomeMeasurement(
            problem_id=problem.problem_id,
            metric=problem.outcome_contract.primary_metric,
            observed_value=problem.outcome_contract.baseline - 0.01,
            measured_at="2026-07-02T00:00:00Z",
        ),
    )
    assert store.outcome_snapshot(problem).status == "improving"

    store.record_outcome(
        problem=problem,
        measurement=OutcomeMeasurement(
            problem_id=problem.problem_id,
            metric=problem.outcome_contract.primary_metric,
            observed_value=problem.outcome_contract.success_threshold,
            measured_at="2026-07-03T00:00:00Z",
        ),
    )
    assert store.outcome_snapshot(problem).status == "target_met"
