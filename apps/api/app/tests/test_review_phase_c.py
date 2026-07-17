"""Regressions for the external-review data-integrity fixes:
enrichment persistence, unknown-identity cohort counts, outcome provenance."""

from app.domain.models import OutcomeMeasurement, SignalRecord
from app.services.seed import load_seed_problems
from app.services.signals import SignalStore, SQLiteSignalStore, build_candidates
from app.services.workflow import SQLiteWorkflowStore, WorkflowStore


def _signal(sid: str, customer: str = "unknown_customer") -> SignalRecord:
    return SignalRecord(
        signal_id=sid,
        feedback_text="checkout keeps failing",
        customer_id=customer,
        account_id="unknown_account",
        journey="purchase",
        journey_stage="checkout",
        timestamp="2026-07-01T00:00:00Z",
    )


def test_enrichment_persists_in_memory_and_sqlite(tmp_path) -> None:
    for store in (SignalStore(), SQLiteSignalStore(tmp_path / "signals.db")):
        store.import_signals([_signal("s-1")])
        assert store.list_signals()[0].enriched is False

        store.update_enrichment("s-1", sentiment="negative", urgency="high")

        record = store.list_signals()[0]
        assert record.enriched is True
        assert record.sentiment == "negative"
        assert record.urgency == "high"


def test_unknown_identities_do_not_count_as_customers() -> None:
    signals = [_signal(f"s-{i}") for i in range(5)] + [_signal("s-real", customer="cust-42")]
    candidate = build_candidates(signals)[0]
    # 5 identifier-less signals used to reconcile to "1 customer"; only the
    # genuinely identified customer counts now.
    assert candidate.customer_count == 1
    assert candidate.account_count == 0
    assert candidate.signal_count == 6


def test_outcome_measurement_provenance(tmp_path) -> None:
    problem = load_seed_problems()[0]
    for store in (WorkflowStore(), SQLiteWorkflowStore(tmp_path / "wf.db")):
        measurement = OutcomeMeasurement(
            problem_id=problem.problem_id,
            metric=problem.outcome_contract.primary_metric,
            observed_value=problem.outcome_contract.baseline,
            measured_at="2026-07-01T00:00:00Z",
        )
        assert measurement.measurement_source == "manual"  # the default
        store.record_outcome(problem=problem, measurement=measurement)
        assert store.outcome_snapshot(problem).measurement_source == "manual"

        store.record_outcome(
            problem=problem,
            measurement=measurement.model_copy(
                update={
                    "measurement_source": "instrumented",
                    "measured_at": "2026-07-02T00:00:00Z",
                }
            ),
        )
        assert store.outcome_snapshot(problem).measurement_source == "instrumented"
