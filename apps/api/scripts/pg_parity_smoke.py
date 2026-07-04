"""Live Postgres parity smoke — run against the real Supabase DB.

Usage: DATABASE_URL=postgresql://... python scripts/pg_parity_smoke.py

Unit tests are SQLite-only by design (conftest pops DATABASE_URL so test data
can never land in production). THIS script is the Postgres proof: it exercises
every store the hosted deployment relies on, using SMOKE-prefixed synthetic
ids, and removes everything it created at the end.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

URL = os.environ.get("DATABASE_URL")
if not URL:
    sys.exit("Set DATABASE_URL first")

from app.connectors.config_store import ConnectorConfig  # noqa: E402
from app.domain.models import SignalRecord  # noqa: E402
from app.services.postgres import (  # noqa: E402
    PostgresConnectorConfigStore,
    PostgresCustomerContextStore,
    PostgresMeasurementPlanStore,
    PostgresSignalStore,
    PostgresTelemetryStore,
    PostgresWorkflowStore,
)

PASS: list[str] = []


def check(name: str, condition: bool, detail: str = "") -> None:
    status = "PASS" if condition else "FAIL"
    print(f"[{status}] {name}" + (f" — {detail}" if detail else ""))
    if not condition:
        sys.exit(1)
    PASS.append(name)


def main() -> None:
    # --- telemetry ---
    telemetry = PostgresTelemetryStore(URL)
    telemetry.record("SMOKE_event", entity_id="SMOKE-1", metadata={"k": "v"})
    events = [e for e in telemetry.list_events(limit=50) if e["event_type"] == "SMOKE_event"]
    check("telemetry record+list", len(events) >= 1, f"{len(events)} events")
    check("telemetry counts", telemetry.counts_by_type().get("SMOKE_event", 0) >= 1)

    # --- signals: import, dedup, GDPR delete ---
    signals = PostgresSignalStore(URL)
    record = SignalRecord(
        signal_id="SMOKE-SIG-1",
        customer_id="SMOKE-CUST-1",
        account_id="SMOKE-ACC",
        source="smoke",
        journey="smoke journey",
        journey_stage="smoke stage",
        campaign_exposure=[],
        product_events=[],
        feedback_text="Parity smoke: die Verifizierung dauert zu lange.",
        language="de",
        timestamp="2026-07-04T10:00:00Z",
        metadata={"smoke": "true"},
    )
    first = signals.import_signals([record])
    second = signals.import_signals([record])
    check("signal import", first.imported == 1, f"imported={first.imported}")
    check("signal dedup", second.skipped_duplicates == 1)
    check("signal gdpr delete", signals.delete_by_customer("SMOKE-CUST-1") == 1)
    check("signal gone", "SMOKE-SIG-1" not in signals.existing_signal_ids())

    # --- context GDPR ---
    contexts = PostgresCustomerContextStore(URL)
    from app.services.contexts import parse_context_csv

    contexts.import_context(
        parse_context_csv("customer_id,account_id,account_value\nSMOKE-CUST-2,SMOKE-ACC,100")
    )
    check("context gdpr delete", contexts.delete_by_customer("SMOKE-CUST-2") == 1)

    # --- measurement plans ---
    plans = PostgresMeasurementPlanStore(URL)
    plans.schedule(
        problem_id="SMOKE-PRB",
        execution_id="SMOKE-EXE",
        executed_at="2026-07-01T00:00:00Z",
        due_at="2026-07-02T00:00:00Z",
        kind="t7",
    )
    plans.schedule(  # double-schedule guard
        problem_id="SMOKE-PRB",
        execution_id="SMOKE-EXE-2",
        executed_at="2026-07-01T00:00:00Z",
        due_at="2026-07-02T00:00:00Z",
        kind="t7",
    )
    due = [p for p in plans.due("2026-07-03T00:00:00Z") if p["problem_id"] == "SMOKE-PRB"]
    check("plan schedule+guard", len(due) == 1, f"due={len(due)}")
    plans.mark(due[0]["id"], status="skipped", note="smoke cleanup")
    still_due = [p for p in plans.due("2026-07-03T00:00:00Z") if p["problem_id"] == "SMOKE-PRB"]
    check("plan mark", len(still_due) == 0)

    # --- connector configs (the redeploy-survival store) ---
    configs = PostgresConnectorConfigStore(URL)
    configs.upsert_config(
        ConnectorConfig(connector_type="SMOKE-connector", config={"secret": "s"}, is_active=True)
    )
    loaded = configs.get_config("SMOKE-connector")
    check("config upsert+get", loaded is not None and loaded.config["secret"] == "s")
    loaded.config["last_synced_at"] = "2026-07-04T00:00:00Z"
    configs.upsert_config(loaded)
    check(
        "config cursor persist",
        configs.get_config("SMOKE-connector").config["last_synced_at"] == "2026-07-04T00:00:00Z",
    )
    check("config delete", configs.delete_config("SMOKE-connector") is True)

    # --- workflow: execution update persistence + draft scrub ---
    workflow = PostgresWorkflowStore(URL)
    from app.domain.models import ExecutionRecord

    execution = ExecutionRecord(
        execution_id="SMOKE-EXE-9",
        problem_id="SMOKE-PRB",
        action_id="SMOKE-ACT",
        destination="jira",
        status="draft_created",
        summary="smoke",
        owner="smoke-owner",
        created_at="2026-07-04T10:00:00Z",
    )
    workflow._executions.append(execution)
    workflow._save_workflow_record("execution", execution.execution_id, "SMOKE-PRB", execution)
    workflow.update_execution("SMOKE-EXE-9", status="completed", external_ref="SMOKE-77")
    fresh = PostgresWorkflowStore(URL)  # reload from DB — the actual restart test
    reloaded = [e for e in fresh._executions if e.execution_id == "SMOKE-EXE-9"]
    check(
        "execution update survives restart",
        len(reloaded) == 1 and reloaded[0].status == "completed" and reloaded[0].external_ref == "SMOKE-77",
    )

    # --- cleanup ---
    with telemetry._connect() as conn:
        conn.execute("DELETE FROM clara_telemetry WHERE event_type = 'SMOKE_event'")
        conn.execute("DELETE FROM clara_measurement_plans WHERE problem_id = 'SMOKE-PRB'")
        conn.execute(
            "DELETE FROM clara_workflow_records WHERE record_id LIKE 'SMOKE-%' OR problem_id = 'SMOKE-PRB'"
        )
    print(f"\nAll {len(PASS)} parity checks passed against the live DB; smoke rows cleaned up.")


if __name__ == "__main__":
    main()
