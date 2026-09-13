"""Upgrade path for the measurement schema (13 September 2026 review, WP5):
a database at the pre-fix schema and plpgsql function -> the new API boots
on it -> migration 017 -> a safe rerun, with the readiness diagnostics and
the database function verified at every step.

Skipped unless CLARA_TEST_DATABASE_URL points at a PostgreSQL server. The
test CREATEs its own database on that server (the role needs CREATEDB; the
CI service role and a scratch server's owner have it) and drops it at the
end, so the shared parity database is never left in a pre-017 state.
scripts/apply_migrations.py applies the files in the documented order.

Steps and what each proves:

  A. 001-016 (with the API boot DDL between 008 and 009) and the three 017
     plan columns dropped again — the state of a database the 017-aware API
     never booted on. Readiness: function version None, three columns
     missing, verdict "incompatible" naming 017. The 016 function reads a
     legacy window plan from its clock origin to the processing instant:
     the reading carries no observation interval.
  B. The new API boots (its DDL self-heals the columns) and schedules
     checkpoints with frozen terms and fixed intervals. Readiness: columns
     present, function still None -> still "incompatible": the OLD function
     reads those plans and ignores both (open-ended reading, no
     observation_end) — the exact mismatch the diagnostics exist to expose.
  C. 017 applied: version 17, verdict "compatible", and the tick reads the
     remaining follow-up over its fixed interval under the frozen terms.
  D. 017 applied again: no error, version still 17, readings and plans
     untouched, a tick with nothing due measures nothing.
"""

from __future__ import annotations

import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit
from uuid import uuid4

import pytest

from app.routers.system import measurement_compatibility
from app.services.measurement_scheduler import schedule_measurements
from app.services.signals import build_candidates, promote_candidate
from app.tests.test_pg_parity_measurement import DISPATCHED_AT, NOW, POST_SIGNALS, PRE_SIGNALS, _iso

URL = os.getenv("CLARA_TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(not URL, reason="CLARA_TEST_DATABASE_URL not set")

SCRIPTS_DIR = Path(__file__).resolve().parents[4] / "scripts"
COLUMNS_017 = ("contract_snapshot", "observation_start", "observation_end")


def _apply_migrations():
    if str(SCRIPTS_DIR) not in sys.path:
        sys.path.insert(0, str(SCRIPTS_DIR))
    import apply_migrations

    return apply_migrations


def _with_database(url: str, name: str) -> str:
    parts = urlsplit(url)
    return urlunsplit((parts.scheme, parts.netloc, f"/{name}", parts.query, parts.fragment))


@pytest.fixture(scope="module")
def upgrade_url():
    import psycopg

    from app.services.postgres import _POOLS, _SCHEMA_ENSURED

    name = f"clara_upgrade_{uuid4().hex[:8]}"
    admin = psycopg.connect(URL, autocommit=True)
    if not _apply_migrations().pgvector_available(URL):
        pytest.skip("the server has no vector extension (003 needs it); CI uses pgvector/pgvector:pg16")
    admin.execute(f'CREATE DATABASE "{name}"')
    url = _with_database(URL, name)
    try:
        yield url
    finally:
        pool = _POOLS.pop(url, None)
        if pool is not None:
            pool.close()
        _SCHEMA_ENSURED.discard(url)
        admin.execute(f'DROP DATABASE "{name}" WITH (FORCE)')
        admin.close()


def _rows(url: str, sql: str, params: tuple = ()) -> list[dict]:
    import psycopg
    from psycopg.rows import dict_row

    with psycopg.connect(url, row_factory=dict_row) as conn:
        conn.execute("SELECT set_config('app.tenant_id', '1', false), set_config('app.workspace_id', '1', false)")
        return conn.execute(sql, params).fetchall()


def _exec(url: str, sql: str, params: tuple = ()) -> None:
    import psycopg

    with psycopg.connect(url) as conn:
        conn.execute(sql, params)


def _tick(url: str, now: datetime) -> dict:
    return _rows(url, "SELECT clara_run_due_measurements(1, %s) AS r", (now,))[0]["r"]


def _readiness(url: str) -> dict:
    """What GET /ready/details would report for this database."""
    import psycopg
    from psycopg.rows import dict_row

    from app.services.postgres import measurement_schema_state

    with psycopg.connect(url, row_factory=dict_row) as conn:
        state = measurement_schema_state(conn)
    return {"state": state, "verdict": measurement_compatibility({"ok": True, "backend": "postgres", "measurement": state})}


def _outcomes(url: str, problem_id: str) -> list[dict]:
    return [
        r["payload"]
        for r in _rows(
            url,
            "SELECT payload FROM clara_workflow_records WHERE record_type = 'outcome' AND problem_id = %s"
            " ORDER BY created_at, record_id",
            (problem_id,),
        )
    ]


def _plans(url: str) -> list[dict]:
    return _rows(url, "SELECT * FROM clara_measurement_plans ORDER BY due_at, id")


def test_upgrade_from_the_pre_017_schema_and_function(upgrade_url: str) -> None:
    from app.services.postgres import (
        _SCHEMA_ENSURED,
        PostgresMeasurementPlanStore,
        PostgresProblemStore,
        PostgresSignalStore,
    )

    migrate = _apply_migrations()

    # ---- A. the pre-fix database ------------------------------------------
    applied = migrate.apply(upgrade_url, skip=["017"])
    assert [p.name[:3] for p in applied][-3:] == ["015", "016", "012"]
    _exec(
        upgrade_url,
        "ALTER TABLE clara_measurement_plans " + ", ".join(f"DROP COLUMN IF EXISTS {c}" for c in COLUMNS_017),
    )
    before = _readiness(upgrade_url)
    assert before["state"]["function_version"] is None
    assert before["state"]["tick_function_present"] is True and before["state"]["backend_tick"] == "plpgsql"
    assert before["state"]["columns_missing"] == list(COLUMNS_017)
    assert before["verdict"]["state"] == "incompatible"
    assert "017_measurement_intervals.sql" in before["verdict"]["action"]

    # Problem + signals as the (old or new) API writes them: payload rows only.
    problem = promote_candidate(build_candidates(PRE_SIGNALS)[0])
    PostgresProblemStore(upgrade_url, []).upsert_problem(problem)
    PostgresSignalStore(upgrade_url).import_signals([*PRE_SIGNALS, *POST_SIGNALS])
    window_days = problem.outcome_contract.measurement_window_days
    # A window plan as the pre-017 API scheduled it: no frozen terms, no interval.
    _exec(
        upgrade_url,
        "INSERT INTO clara_measurement_plans (workspace_id, problem_id, execution_id, executed_at, due_at, kind,"
        " status, origin, contract_revision) VALUES (1, %s, 'EXE-OLD', %s, %s, 'window', 'pending', 'dispatch', %s)",
        (problem.problem_id, _iso(DISPATCHED_AT), _iso(DISPATCHED_AT + timedelta(days=window_days)), problem.outcome_contract.revision),
    )
    old_result = _tick(upgrade_url, NOW)
    assert old_result["measured"] == 1, old_result
    [legacy] = _outcomes(upgrade_url, problem.problem_id)
    assert legacy["checkpoint_kind"] == "window" and legacy["execution_id"] == "EXE-OLD"
    assert "observation_end" not in legacy and "observation_start" not in legacy  # 016 payload: no interval
    assert legacy["notes"].startswith("Auto-measured by the scheduler (window)") and "since dispatch" in legacy["notes"]
    assert {p["status"] for p in _plans(upgrade_url)} == {"done"}

    # ---- B. the new API boots on the old function -------------------------
    _SCHEMA_ENSURED.discard(upgrade_url)  # a fresh process: the boot DDL runs again
    plans = PostgresMeasurementPlanStore(upgrade_url)
    booted = _readiness(upgrade_url)
    assert booted["state"]["columns_missing"] == []  # self-healed by the boot DDL
    assert booted["state"]["function_version"] is None
    assert booted["verdict"]["state"] == "incompatible", booted  # old function under the new app

    kinds = schedule_measurements(plans, problem=problem, execution_id="EXE-NEW", executed_at=_iso(DISPATCHED_AT), origin="dispatch")
    assert set(kinds) == {"t7", "window", "followup"}
    new_plans = {p["kind"]: p for p in plans.list_plans() if p["execution_id"] == "EXE-NEW"}
    assert all(p["contract_snapshot"] and p["observation_start"] and p["observation_end"] for p in new_plans.values())
    # The old function reads the due t7 and window plans: frozen terms and
    # fixed intervals ignored, open-ended readings without an interval.
    mixed = _tick(upgrade_url, NOW)
    assert mixed["measured"] == 2, mixed
    read_under_old = [o for o in _outcomes(upgrade_url, problem.problem_id) if o["execution_id"] == "EXE-NEW"]
    assert {o["checkpoint_kind"] for o in read_under_old} == {"t7", "window"}
    assert all("observation_end" not in o and "since dispatch" in o["notes"] for o in read_under_old)
    assert all(item.get("observation_end") is None for item in mixed["processed"])

    # ---- C. migration 017 -------------------------------------------------
    assert [p.name[:3] for p in migrate.apply(upgrade_url, only=["017"])] == ["017"]
    after = _readiness(upgrade_url)
    assert after["state"]["function_version"] == 17 and after["state"]["columns_missing"] == []
    assert after["verdict"]["state"] == "compatible" and after["verdict"]["action"] is None
    followup = new_plans["followup"]
    fixed = _tick(upgrade_url, datetime.fromisoformat(followup["due_at"].replace("Z", "+00:00")) + timedelta(hours=1))
    assert fixed["measured"] == 1, fixed
    reading = next(o for o in _outcomes(upgrade_url, problem.problem_id) if o["checkpoint_kind"] == "followup")
    assert reading["plan_id"] == followup["id"] and reading["execution_id"] == "EXE-NEW"
    assert (reading["observation_start"], reading["observation_end"]) == (followup["observation_start"], followup["observation_end"])
    assert reading["contract_snapshot"] == followup["contract_snapshot"]
    assert "in the fixed interval" in reading["notes"] and "clock from dispatch" in reading["notes"]
    assert [item["observation_end"] for item in fixed["processed"]] == [followup["observation_end"]]
    # Readings written under the old function are history, not rewritten.
    assert len([o for o in _outcomes(upgrade_url, problem.problem_id) if "observation_end" not in o]) == 3

    # ---- D. safe rerun ----------------------------------------------------
    outcomes_before = _outcomes(upgrade_url, problem.problem_id)
    plans_before = _plans(upgrade_url)
    assert [p.name[:3] for p in migrate.apply(upgrade_url, only=["017"])] == ["017"]
    assert _readiness(upgrade_url)["verdict"]["state"] == "compatible"
    assert _rows(upgrade_url, "SELECT clara_measurement_function_version() AS v")[0]["v"] == 17
    assert _outcomes(upgrade_url, problem.problem_id) == outcomes_before
    assert _plans(upgrade_url) == plans_before
    assert _tick(upgrade_url, NOW + timedelta(days=365))["measured"] == 0  # nothing pending: nothing re-read
    assert {p["status"] for p in plans_before} == {"done"}


def test_apply_script_plans_the_documented_order_and_refuses_unknown_files(tmp_path: Path) -> None:
    migrate = _apply_migrations()
    plan = migrate.plan()
    labels = [migrate._label(step) for step in plan]
    assert labels == ["001", "002", "004", "003", "005", "006", "007", "008", "API boot DDL",
                      "009", "010", "011", "013", "014", "015", "016", "017", "012"]
    assert [migrate._label(s) for s in migrate.plan(only=["017"])] == ["017"]
    assert [migrate._label(s) for s in migrate.plan(skip=["012", "003"], api_ddl=False)][-2:] == ["016", "017"]
    # A file the ORDER does not list stops the script before anything runs.
    stray = migrate.MIGRATIONS_DIR / "999_stray.sql"
    stray.write_text("SELECT 1;", encoding="utf-8")
    try:
        with pytest.raises(SystemExit, match="999"):
            migrate.plan()
    finally:
        stray.unlink()
