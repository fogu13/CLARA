"""Postgres parity for measurement provenance (migration 016).

Skipped unless CLARA_TEST_DATABASE_URL points at a PostgreSQL database with
migrations 001-016 applied. conftest keeps DATABASE_URL="" (auth stays
disabled, no app store touches the DB by accident); the stores here are built
with the explicit URL.

Proves that the plpgsql tick (clara_run_due_measurements) and the Python tick
(measurement_scheduler.run_due_measurements) write the same outcome payload
keys, that the Postgres workflow store scores and certifies exactly like the
SQLite/memory stores, and that plan origin/contract_revision round-trip.
"""

from __future__ import annotations

import os
from datetime import UTC, datetime, timedelta

import pytest

from app.domain.models import OutcomeMeasurement, SignalRecord
from app.services.measurement_scheduler import run_due_measurements, schedule_measurements
from app.services.outcome_engine import loop_verdict
from app.services.signals import build_candidates, promote_candidate

URL = os.getenv("CLARA_TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(not URL, reason="CLARA_TEST_DATABASE_URL not set")

TABLES = (
    "clara_measurement_plans",
    "clara_workflow_records",
    "clara_problems",
    "clara_signals",
    "clara_telemetry",
)
NOW = datetime.now(UTC).replace(microsecond=0)
OUTCOME_KEYS = {
    "problem_id",
    "metric",
    "observed_value",
    "measured_at",
    "notes",
    "measurement_source",
    "checkpoint_kind",
    "plan_id",
    "execution_id",
    "contract_revision",
    "contract_snapshot",
}


def _iso(moment: datetime) -> str:
    return moment.isoformat().replace("+00:00", "Z")


def _signal(signal_id: str, *, days_ago: float) -> SignalRecord:
    return SignalRecord(
        signal_id=signal_id,
        customer_id=f"C-{signal_id}",
        account_id="A-1",
        source="webhook",
        journey="checkout",
        journey_stage="payment",
        feedback_text=f"Payment problem report {signal_id}",
        language="en",
        timestamp=_iso(NOW - timedelta(days=days_ago)),
    )


# 10 pre-signals in the five days before the (backdated) dispatch -> ~2/day.
DISPATCHED_AT = NOW - timedelta(days=31)
PRE_SIGNALS = [_signal(f"pre-{i}", days_ago=36 - i * 0.5) for i in range(10)]
POST_SIGNALS = [_signal("post-1", days_ago=20)]  # one complaint in 31 days


def _rows(sql: str, params: tuple = ()) -> list[dict]:
    import psycopg
    from psycopg.rows import dict_row

    with psycopg.connect(URL, row_factory=dict_row) as conn:
        conn.execute("SELECT set_config('app.tenant_id', '1', false), set_config('app.workspace_id', '1', false)")
        return conn.execute(sql, params).fetchall()


@pytest.fixture()
def stores():
    import psycopg

    from app.services.postgres import (
        PostgresMeasurementPlanStore,
        PostgresProblemStore,
        PostgresSignalStore,
        PostgresTelemetryStore,
        PostgresWorkflowStore,
    )

    with psycopg.connect(URL) as conn:
        conn.execute(f"TRUNCATE {', '.join(TABLES)}")
    problem = promote_candidate(build_candidates(PRE_SIGNALS)[0])
    problems = PostgresProblemStore(URL, [])
    problems.upsert_problem(problem)
    signals = PostgresSignalStore(URL)
    signals.import_signals([*PRE_SIGNALS, *POST_SIGNALS])
    return {
        "problem": problem,
        "problems": problems,
        "signals": signals,
        "workflows": PostgresWorkflowStore(URL),
        "plans": PostgresMeasurementPlanStore(URL),
        "telemetry": PostgresTelemetryStore(URL),
        "fresh_workflows": lambda: PostgresWorkflowStore(URL),
    }


def _outcome_payloads(problem_id: str) -> list[dict]:
    return [
        row["payload"]
        for row in _rows(
            "SELECT payload FROM clara_workflow_records"
            " WHERE record_type = 'outcome' AND problem_id = %s ORDER BY created_at, record_id",
            (problem_id,),
        )
    ]


def test_schedule_round_trips_origin_and_contract_revision(stores) -> None:
    problem = stores["problem"]
    kinds = schedule_measurements(
        stores["plans"],
        problem=problem,
        execution_id="EXE-0001",
        executed_at=_iso(DISPATCHED_AT),
        origin="dispatch",
    )
    assert set(kinds) == {"t7", "window", "followup"}
    plans = stores["plans"].list_plans()
    assert {plan["origin"] for plan in plans} == {"dispatch"}
    assert {plan["contract_revision"] for plan in plans} == {problem.outcome_contract.revision}
    assert {plan["executed_at"] for plan in plans} == {_iso(DISPATCHED_AT)}
    # Superseding marks only non-implementation pending plans.
    assert stores["plans"].supersede_pending(problem.problem_id, note="superseded by implementation record EXE-0001") == 3
    assert {plan["status"] for plan in stores["plans"].list_plans()} == {"superseded"}


def test_plpgsql_tick_binds_reading_and_certifies_like_sqlite(stores) -> None:
    problem = stores["problem"]
    schedule_measurements(
        stores["plans"],
        problem=problem,
        execution_id="EXE-0001",
        executed_at=_iso(DISPATCHED_AT),
        origin="dispatch",
    )
    # Two ticks, as in operation (T+7 read, then the window read). Readings
    # written by ONE plpgsql tick share measured_at and created_at, so the
    # "latest outcome" among them is not ordered — a pre-existing Postgres
    # quirk this file does not paper over.
    assert stores["plans"].run_due(_iso(DISPATCHED_AT + timedelta(days=8)))["measured"] == 1
    result = stores["plans"].run_due(_iso(NOW))
    assert result["measured"] == 1  # the window read; followup still pending
    assert result["loop_closed"] == 1

    payloads = _outcome_payloads(problem.problem_id)
    window_payload = next(p for p in payloads if p["checkpoint_kind"] == "window")
    assert set(window_payload) == OUTCOME_KEYS
    assert window_payload["execution_id"] == "EXE-0001"
    assert window_payload["contract_revision"] == problem.outcome_contract.revision
    assert window_payload["contract_snapshot"]["success_threshold"] == problem.outcome_contract.success_threshold
    assert "since dispatch (" in window_payload["notes"]
    window_plan = next(p for p in stores["plans"].list_plans() if p["kind"] == "window")
    assert window_payload["plan_id"] == window_plan["id"]
    assert window_plan["status"] == "done"

    snapshot = stores["fresh_workflows"]().outcome_snapshot(problem)
    assert snapshot.status == "target_met"
    assert snapshot.measurement_source == "instrumented"
    assert snapshot.checkpoint_kind == "window"
    assert snapshot.measured_under_revision == problem.outcome_contract.revision
    assert snapshot.contract_amended_after_measurement is False
    verdict, note = loop_verdict(
        outcome_status=snapshot.status,
        plans=stores["plans"].list_plans(),
        measurement_source=snapshot.measurement_source,
        checkpoint_kind=snapshot.checkpoint_kind,
        measurement_origin="dispatch",
        measurement_origin_at=_iso(DISPATCHED_AT),
    )
    assert verdict == "loop_closed"
    assert "instrumented read" in note and "clock from dispatch" in note


def test_manual_reading_after_certified_read_is_not_certified_on_postgres(stores) -> None:
    problem = stores["problem"]
    schedule_measurements(
        stores["plans"],
        problem=problem,
        execution_id="EXE-0001",
        executed_at=_iso(DISPATCHED_AT),
        origin="dispatch",
    )
    assert stores["plans"].run_due(_iso(DISPATCHED_AT + timedelta(days=8)))["measured"] == 1
    assert stores["plans"].run_due(_iso(NOW))["loop_closed"] == 1

    workflows = stores["fresh_workflows"]()
    workflows.record_outcome(
        problem=problem,
        measurement=OutcomeMeasurement(
            problem_id=problem.problem_id,
            metric=problem.outcome_contract.primary_metric,
            observed_value=0.0,
            measured_at=_iso(NOW + timedelta(seconds=1)),
            notes="manual read",
        ),
    )
    snapshot = stores["fresh_workflows"]().outcome_snapshot(problem)
    assert snapshot.status == "target_met"
    assert snapshot.measurement_source == "manual"
    assert snapshot.checkpoint_kind is None
    assert snapshot.measured_under_revision == problem.outcome_contract.revision
    verdict, note = loop_verdict(
        outcome_status=snapshot.status,
        plans=stores["plans"].list_plans(),  # the window plan is still "done"
        measurement_source=snapshot.measurement_source,
        checkpoint_kind=snapshot.checkpoint_kind,
        measurement_origin="dispatch",
    )
    assert verdict == "on_track"
    assert "manual reading" in note and "not certified" in note
    # The manual record carries the same provenance keys the tick writes.
    assert set(_outcome_payloads(problem.problem_id)[-1]) == OUTCOME_KEYS


def test_python_tick_writes_the_same_payload_keys_as_plpgsql(stores) -> None:
    problem = stores["problem"]
    schedule_measurements(
        stores["plans"],
        problem=problem,
        execution_id="EXE-0001",
        executed_at=_iso(DISPATCHED_AT),
        origin="dispatch",
    )
    # plpgsql processes the T+7 read; the Python tick processes the window read.
    t7_due = _iso(DISPATCHED_AT + timedelta(days=8))
    assert stores["plans"].run_due(t7_due)["measured"] == 1
    result = run_due_measurements(
        plan_store=stores["plans"],
        problem_lookup=stores["problems"].get_problem,
        signal_store=stores["signals"],
        workflow_store=stores["fresh_workflows"](),
        telemetry=stores["telemetry"],
        now=_iso(NOW),
    )
    assert result["measured"] == 1
    assert result["loop_closed"] == 1

    payloads = _outcome_payloads(problem.problem_id)
    by_kind = {payload["checkpoint_kind"]: payload for payload in payloads}
    assert set(by_kind) == {"t7", "window"}
    assert set(by_kind["t7"]) == set(by_kind["window"]) == OUTCOME_KEYS
    assert by_kind["t7"]["measurement_source"] == by_kind["window"]["measurement_source"] == "instrumented"
    assert by_kind["t7"]["execution_id"] == by_kind["window"]["execution_id"] == "EXE-0001"
    assert by_kind["t7"]["contract_revision"] == by_kind["window"]["contract_revision"]
    assert set(by_kind["t7"]["contract_snapshot"]) == set(by_kind["window"]["contract_snapshot"])
    assert "since dispatch (" in by_kind["t7"]["notes"]
    assert "since dispatch (" in by_kind["window"]["notes"]
    plans = {plan["kind"]: plan for plan in stores["plans"].list_plans()}
    assert by_kind["t7"]["plan_id"] == plans["t7"]["id"]
    assert by_kind["window"]["plan_id"] == plans["window"]["id"]
