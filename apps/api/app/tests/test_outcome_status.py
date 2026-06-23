from app.domain.models import OutcomeMeasurement
from app.services.seed import load_seed_problems
from app.services.workflow import WorkflowStore


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
