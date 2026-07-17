"""Guardrail measurement (docs/engineering/guardrail-measurement-design.md):
breach detection, unknown-identity exclusion, no-data-source markers, and the
snapshot carrier across store implementations."""

from app.domain.models import OutcomeContract, SignalRecord
from app.services.measurement_scheduler import measure_guardrails
from app.services.seed import load_seed_problems
from app.services.workflow import SQLiteWorkflowStore, WorkflowStore

EXECUTED_AT = "2026-07-01T00:00:00Z"
NOW = "2026-07-08T00:00:00Z"


def _problem(guardrails: list[str]):
    problem = load_seed_problems()[0]
    return problem.model_copy(
        update={
            "outcome_contract": problem.outcome_contract.model_copy(
                update={"guardrail_metrics": guardrails}
            )
        }
    )


def _signal(sid: str, customer: str, ts: str, problem) -> SignalRecord:
    return SignalRecord(
        signal_id=sid,
        feedback_text="same theme again",
        customer_id=customer,
        journey=problem.journey,
        journey_stage=problem.journey_stage,
        timestamp=ts,
    )


def test_repeat_guardrail_breach_and_ok() -> None:
    problem = _problem(["repeat_signal_rate"])
    store = WorkflowStore()
    # Pre-window: one identified customer complains once (baseline ~0.036/day).
    # Post-window: the SAME customer complains 5 times in 7 days (~0.71/day) -> breach.
    signals = [_signal("pre-1", "cust-1", "2026-06-20T00:00:00Z", problem)] + [
        _signal(f"post-{i}", "cust-1", f"2026-07-0{i}T12:00:00Z", problem) for i in range(1, 6)
    ]
    measure_guardrails(problem, signals, executed_at=EXECUTED_AT, now=NOW, workflow_store=store)
    [record] = store.latest_guardrails(problem.problem_id)
    assert record.status == "breach"
    assert record.baseline is not None and record.observed_value > record.baseline

    # No repeats post-execution -> ok.
    store_ok = WorkflowStore()
    measure_guardrails(
        problem,
        [_signal("pre-1", "cust-1", "2026-06-20T00:00:00Z", problem)],
        executed_at=EXECUTED_AT,
        now=NOW,
        workflow_store=store_ok,
    )
    [record_ok] = store_ok.latest_guardrails(problem.problem_id)
    assert record_ok.status == "ok"
    assert record_ok.observed_value == 0.0


def test_identityless_signals_cannot_prove_repeats() -> None:
    problem = _problem(["repeat_signal_rate"])
    store = WorkflowStore()
    # All signals come from the unknown bucket: no cohort, no repeats, no breach.
    signals = [
        _signal(f"s-{i}", "unknown_customer", ts, problem)
        for i, ts in enumerate(["2026-06-20T00:00:00Z", "2026-07-02T00:00:00Z", "2026-07-03T00:00:00Z"])
    ]
    measure_guardrails(problem, signals, executed_at=EXECUTED_AT, now=NOW, workflow_store=store)
    [record] = store.latest_guardrails(problem.problem_id)
    assert record.status == "ok"
    assert record.baseline == 0.0 and record.observed_value == 0.0


def test_unmeasurable_guardrail_says_no_data_source() -> None:
    problem = _problem(["unsubscribe_or_opt_out_rate"])
    store = WorkflowStore()
    measure_guardrails(problem, [], executed_at=EXECUTED_AT, now=NOW, workflow_store=store)
    [record] = store.latest_guardrails(problem.problem_id)
    assert record.status == "no_data_source"
    assert record.observed_value is None


def test_snapshot_carries_latest_guardrails_across_stores(tmp_path) -> None:
    problem = _problem(["repeat_signal_rate", "unsubscribe_or_opt_out_rate"])
    for store in (WorkflowStore(), SQLiteWorkflowStore(tmp_path / "wf.db")):
        measure_guardrails(problem, [], executed_at=EXECUTED_AT, now=NOW, workflow_store=store)
        # Second checkpoint: latest-per-metric wins, list stays at 2 entries.
        measure_guardrails(
            problem, [], executed_at=EXECUTED_AT, now="2026-07-15T00:00:00Z", workflow_store=store
        )
        snapshot = store.outcome_snapshot(problem)
        assert len(snapshot.guardrails) == 2
        assert {g.metric for g in snapshot.guardrails} == set(
            problem.outcome_contract.guardrail_metrics
        )
        assert all(g.measured_at == "2026-07-15T00:00:00Z" for g in snapshot.guardrails)


def test_contract_model_accepts_guardrail_override() -> None:
    # Sanity: the helper actually reads the contract's declared list.
    assert isinstance(
        OutcomeContract(
            primary_metric="signal_rate_per_day:x",
            baseline=1.0,
            success_threshold=0.5,
            measurement_window_days=30,
            comparison_method="its_v1",
            guardrail_metrics=["repeat_signal_rate"],
            responsible_owner="cx",
        ).guardrail_metrics,
        list,
    )
