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
    PostgresJourneyEventStore,
    PostgresMeasurementPlanStore,
    PostgresProblemStore,
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

    # --- #18: problem-store contract parity (insert-only upsert + seed guard) ---
    from app.domain.models import ApprovalDecision, JourneyEventRecord, ProblemUpdateRequest
    from app.services.seed import load_seed_problems

    problems_store = PostgresProblemStore(URL, [])
    smoke_problem = load_seed_problems()[0].model_copy(
        update={"problem_id": "SMOKE-PRB-18", "title": "smoke original"}
    )
    problems_store.upsert_problem(smoke_problem)
    returned = problems_store.upsert_problem(
        smoke_problem.model_copy(update={"title": "OVERWRITTEN"})
    )
    stored_title = problems_store.get_problem("SMOKE-PRB-18").title
    check("problem upsert is insert-only", returned.title == "smoke original" and stored_title == "smoke original")
    updated = problems_store.update_problem("SMOKE-PRB-18", ProblemUpdateRequest(title="edited"))
    check("problem update works on non-seed", updated is not None and updated.title == "edited")
    seeded_store = PostgresProblemStore(URL, [smoke_problem])
    check(
        "seed problems are read-only",
        seeded_store.update_problem("SMOKE-PRB-18", ProblemUpdateRequest(title="nope")) is None
        and seeded_store.transition_problem_status("SMOKE-PRB-18", smoke_problem.status) is None,
    )

    # --- #23: cross-instance workflow freshness (local dev + Render share one DB) ---
    wf_reader = PostgresWorkflowStore(URL)  # constructed BEFORE the write
    wf_writer = PostgresWorkflowStore(URL)
    before = {a.decision_id for a in wf_reader.list_approvals()}
    wf_writer.record_approval(
        problem=smoke_problem,
        decision=ApprovalDecision(
            action_id=smoke_problem.action_proposals[0].action_id,
            decision="rejected",  # rejection skips governance gating + mints no execution
            reviewer="smoke",
        ),
    )
    after = {a.decision_id for a in wf_reader.list_approvals()}
    check("workflow reads are cross-instance fresh", len(after - before) == 1)

    # --- #29/#34: in-batch duplicate counting ---
    dup = SignalRecord(
        signal_id="SMOKE-DUP-1", customer_id="SMOKE-CUST-9", account_id="SMOKE-ACC",
        source="smoke", journey="smoke", journey_stage="smoke",
        campaign_exposure=[], product_events=[],
        feedback_text="dupe batch", language="en", timestamp="2026-07-04T10:00:00Z",
    )
    result = signals.import_signals([dup, dup])
    check("in-batch signal dupes counted as skipped", result.imported == 1 and result.skipped_duplicates == 1)
    events_store = PostgresJourneyEventStore(URL)
    evt = JourneyEventRecord(
        event_id="SMOKE-EVT-1", customer_id="SMOKE-CUST-9", account_id="SMOKE-ACC",
        journey="smoke", journey_stage="smoke", event_name="smoke", timestamp="2026-07-04T10:00:00Z",
    )
    eresult = events_store.import_events([evt, evt])
    check("in-batch event dupes counted as skipped", eresult.imported == 1 and eresult.skipped_duplicates == 1)

    # --- migration 011: FORCE RLS + pg_cron actually in effect ---
    from app.auth import set_current_tenant

    clara_tables = {
        "clara_problems", "clara_signals", "clara_candidate_decisions",
        "clara_customer_context", "clara_workflow_records",
        "clara_taxonomy_catalogs", "clara_terminology_dictionary",
        "clara_telemetry", "clara_measurement_plans", "clara_connector_configs",
        "clara_journey_events", "clara_feedback_rules",
        "clara_workspace_settings", "clara_api_keys",
    }
    with telemetry._connect() as conn:
        forced = {
            row["relname"]
            for row in conn.execute(
                "SELECT relname FROM pg_class WHERE relforcerowsecurity"
            ).fetchall()
        }
    check(
        "FORCE RLS on every clara_ table",
        clara_tables <= forced,
        f"missing: {sorted(clara_tables - forced)}" if not clara_tables <= forced else "",
    )

    # Hard check — migration 003's silent exception swallow hid a pg_cron
    # enable failure for months; never trust a WARNING alone.
    try:
        with telemetry._connect() as conn:
            jobs = {
                row["jobname"]
                for row in conn.execute("SELECT jobname FROM cron.job").fetchall()
            }
    except Exception as exc:  # noqa: BLE001 — undefined cron schema = not installed
        jobs = set()
        print(f"      (cron.job unreadable: {exc})")
    check("pg_cron measurement job scheduled", "clara-measurements-due" in jobs, f"jobs={sorted(jobs)}")
    check("pg_cron taxonomy job re-healed", "taxonomy-governance-daily" in jobs)

    # --- tenant isolation: a second workspace can neither see nor be seen ---
    with telemetry._connect() as conn:
        smoke_ws = conn.execute(
            "INSERT INTO public.workspaces (name, slug) VALUES ('SMOKE workspace', 'smoke-tenant')"
            " ON CONFLICT (slug) DO UPDATE SET name = excluded.name RETURNING id"
        ).fetchone()["id"]

    iso_signal = record.model_copy(
        update={"signal_id": "SMOKE-ISO-1", "customer_id": "SMOKE-CUST-ISO"}
    )
    set_current_tenant(str(smoke_ws))
    signals.import_signals([iso_signal])
    with signals._connect() as conn:
        stamped = conn.execute(
            "SELECT workspace_id FROM clara_signals WHERE signal_id = 'SMOKE-ISO-1'"
        ).fetchone()
    check(
        "insert inherits the session workspace via GUC default",
        stamped is not None and stamped["workspace_id"] == smoke_ws,
        f"workspace_id={stamped['workspace_id'] if stamped else None} expected {smoke_ws}",
    )
    check("own-tenant read sees the row", "SMOKE-ISO-1" in signals.existing_signal_ids())
    iso_execution = execution.model_copy(
        update={"execution_id": "SMOKE-ISO-EXE", "problem_id": "SMOKE-ISO-PRB"}
    )
    workflow._save_workflow_record(
        "execution", "SMOKE-ISO-EXE", "SMOKE-ISO-PRB", iso_execution, str(smoke_ws)
    )

    set_current_tenant("1")
    check("cross-tenant store read hides the row", "SMOKE-ISO-1" not in signals.existing_signal_ids())
    with signals._connect() as conn:
        visible = conn.execute(
            "SELECT count(*) AS n FROM clara_signals WHERE signal_id = 'SMOKE-ISO-1'"
        ).fetchone()["n"]
    check("raw select as owner is RLS-filtered too (FORCE)", visible == 0)
    iso_workflow = PostgresWorkflowStore(URL)
    check(
        "cross-tenant workflow records invisible",
        not any(e.execution_id == "SMOKE-ISO-EXE" for e in iso_workflow._executions),
    )
    # Pin the documented ceiling: entity ids are global PKs, so a cross-tenant
    # same-id import silently no-ops (isolation holds; usability of a second
    # workspace is gated on composite keys — see migration 011 header).
    ceiling = signals.import_signals([iso_signal])
    check("global-PK ceiling: cross-tenant same-id import no-ops", ceiling.imported == 0)

    # --- clara_run_due_measurements: the DB-side measurement tick, end to end ---
    from datetime import UTC, datetime, timedelta

    def iso_z(dt: datetime) -> str:
        return dt.isoformat().replace("+00:00", "Z")

    now = datetime.now(UTC)
    cron_contract = smoke_problem.outcome_contract.model_copy(
        update={"primary_metric": "signal_rate_per_day:smoke journey/smoke stage"}
    )
    cron_problem = smoke_problem.model_copy(
        update={"problem_id": "SMOKE-CRON-PRB", "outcome_contract": cron_contract}
    )
    problems_store.upsert_problem(cron_problem)
    signals.import_signals(
        [
            record.model_copy(
                update={
                    "signal_id": f"SMOKE-CRON-SIG-{i}",
                    "customer_id": "SMOKE-CUST-CRON",
                    "timestamp": iso_z(now - timedelta(days=1)),
                }
            )
            for i in (1, 2)
        ]
    )
    plans.schedule(
        problem_id="SMOKE-CRON-PRB",
        execution_id="SMOKE-CRON-EXE",
        executed_at=iso_z(now - timedelta(days=2)),
        due_at=iso_z(now - timedelta(hours=1)),
        kind="t7",
    )
    with plans._connect() as conn:
        conn.execute("SELECT public.clara_run_due_measurements(1)")
    cron_plan = next(p for p in plans.list_plans() if p["problem_id"] == "SMOKE-CRON-PRB")
    check(
        "cron function measures the due plan from real signals",
        cron_plan["status"] == "done" and "2 signals" in (cron_plan["note"] or ""),
        f"status={cron_plan['status']} note={cron_plan['note']}",
    )
    from app.domain.models import OutcomeMeasurement

    with plans._connect() as conn:
        outcome_rows = conn.execute(
            "SELECT payload FROM clara_workflow_records"
            " WHERE record_type = 'outcome' AND problem_id = 'SMOKE-CRON-PRB'"
        ).fetchall()
    check("cron outcome row written", len(outcome_rows) == 1)
    outcome = OutcomeMeasurement.model_validate(outcome_rows[0]["payload"])
    check(
        "cron outcome payload parses with a real rate",
        outcome.metric == cron_contract.primary_metric and 0 < outcome.observed_value <= 2,
        f"observed={outcome.observed_value}",
    )
    check(
        "cron run recorded honest telemetry",
        telemetry.has_event("outcome_recorded", "SMOKE-CRON-PRB"),
    )
    # Idempotency + the API-side wrapper share one implementation.
    rerun = plans.run_due()
    with plans._connect() as conn:
        recount = conn.execute(
            "SELECT count(*) AS n FROM clara_workflow_records"
            " WHERE record_type = 'outcome' AND problem_id = 'SMOKE-CRON-PRB'"
        ).fetchone()["n"]
    check(
        "second pass is a no-op (plan already done)",
        isinstance(rerun, dict) and recount == 1,
        f"rerun={rerun} outcomes={recount}",
    )

    # --- cleanup (per tenant: RLS scopes DELETEs to the active GUC) ---
    with telemetry._connect() as conn:
        conn.execute("DELETE FROM clara_telemetry WHERE event_type = 'SMOKE_event'")
        conn.execute("DELETE FROM clara_telemetry WHERE entity_id LIKE 'SMOKE-%'")
        conn.execute("DELETE FROM clara_measurement_plans WHERE problem_id LIKE 'SMOKE-%'")
        conn.execute(
            "DELETE FROM clara_workflow_records WHERE record_id LIKE 'SMOKE-%' OR problem_id LIKE 'SMOKE-%'"
        )
        conn.execute("DELETE FROM clara_problems WHERE problem_id LIKE 'SMOKE-%'")
        conn.execute("DELETE FROM clara_signals WHERE signal_id LIKE 'SMOKE-%'")
        conn.execute("DELETE FROM clara_journey_events WHERE event_id LIKE 'SMOKE-%'")
    set_current_tenant(str(smoke_ws))
    with telemetry._connect() as conn:
        conn.execute("DELETE FROM clara_signals WHERE signal_id LIKE 'SMOKE-%'")
        conn.execute(
            "DELETE FROM clara_workflow_records WHERE record_id LIKE 'SMOKE-%' OR problem_id LIKE 'SMOKE-%'"
        )
    set_current_tenant("1")
    with telemetry._connect() as conn:
        conn.execute("DELETE FROM public.workspaces WHERE slug = 'smoke-tenant'")
    print(f"\nAll {len(PASS)} parity checks passed against the live DB; smoke rows cleaned up.")


if __name__ == "__main__":
    main()
