"""Readiness and version diagnostics (13 September 2026 review, WP5).

GET /health and GET /ready carry the build identity (CLARA_BUILD_COMMIT,
baked into the image by the Dockerfile); /ready adds one word for the
measurement schema and never fails on it (a pending migration is a release
step, not an outage); /ready/details names the expected and found function
versions, the missing plan columns, the tick in use and the action to take.

The probe outcomes are simulated here: an old plpgsql function under a new
app, a database that predates 016/017, no plpgsql tick at all (Python
fallback), a database failure, a compatible database and SQLite. The same
states are produced by a real database in test_pg_migration_upgrade.py.
"""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.routers.system import build_identity, build_router, measurement_compatibility
from app.services.postgres import (
    EXPECTED_MEASUREMENT_FUNCTION_VERSION,
    MEASUREMENT_PLAN_COLUMNS,
    measurement_schema_state,
)

COMPATIBLE = {
    "function_version": EXPECTED_MEASUREMENT_FUNCTION_VERSION,
    "tick_function_present": True,
    "columns_missing": [],
    "backend_tick": "plpgsql",
}
# Migration 017 not applied: the 016 (or 013/011) function has no version marker.
OLD_FUNCTION = {**COMPATIBLE, "function_version": None}
# A database the 017-aware API never booted on (no self-healed plan columns).
PRE_017_DATABASE = {**OLD_FUNCTION, "columns_missing": ["contract_snapshot", "observation_start", "observation_end"]}
# No plpgsql tick at all: the API runs its Python tick.
NO_TICK = {"function_version": None, "tick_function_present": False, "columns_missing": [], "backend_tick": "python"}
SQLITE = {"function_version": None, "columns_missing": [], "backend_tick": "python"}


def _pg(measurement: dict) -> dict:
    return {"ok": True, "backend": "postgres", "measurement": measurement}


@pytest.mark.parametrize(
    ("database", "state", "action_names"),
    [
        (_pg(COMPATIBLE), "compatible", None),
        (_pg(OLD_FUNCTION), "incompatible", "017_measurement_intervals.sql"),
        (_pg(PRE_017_DATABASE), "incompatible", "017_measurement_intervals.sql"),
        (_pg({**COMPATIBLE, "function_version": 16}), "incompatible", "017_measurement_intervals.sql"),
        (_pg(NO_TICK), "fallback", "017_measurement_intervals.sql"),
        ({"ok": True, "backend": "sqlite", "measurement": SQLITE}, "compatible", None),
        ({"ok": True, "backend": "memory", "measurement": SQLITE}, "compatible", None),
        ({"ok": False, "error": "OperationalError"}, "unknown", "DATABASE_URL"),
        (None, "unknown", "DATABASE_URL"),
        (_pg({}), "incompatible", "017_measurement_intervals.sql"),  # a probe that names no version
    ],
)
def test_compatibility_verdicts(database: dict | None, state: str, action_names: str | None) -> None:
    verdict = measurement_compatibility(database)
    assert verdict["state"] == state, verdict
    assert verdict["expected_function_version"] == EXPECTED_MEASUREMENT_FUNCTION_VERSION
    if action_names is None:
        assert verdict["action"] is None, verdict
    else:
        assert action_names in verdict["action"], verdict


def test_build_identity_is_the_baked_commit_never_the_checkout(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CLARA_BUILD_COMMIT", raising=False)
    monkeypatch.delenv("CLARA_VERSION", raising=False)
    assert build_identity() is None
    monkeypatch.setenv("CLARA_VERSION", "0.1.0")
    assert build_identity() == "0.1.0"
    monkeypatch.setenv("CLARA_BUILD_COMMIT", "3e86f66")
    assert build_identity() == "3e86f66"
    monkeypatch.setenv("CLARA_BUILD_COMMIT", "")  # the Dockerfile's default: unknown, not guessed
    assert build_identity() == "0.1.0"


def _client(readiness_check) -> TestClient:
    """The system router alone: /health, /ready and /ready/details need only
    the readiness probe (the stores are touched by other routes at call time)."""
    api = FastAPI()
    api.include_router(
        build_router(
            signal_store=None,
            active_problem_store=None,
            workflow_store=None,
            workspace_store=None,
            api_key_store=None,
            telemetry_store=None,
            connector_config_store=None,
            enrich_problem_for_response=None,
            readiness_check=readiness_check,
        )
    )
    return TestClient(api)


def test_health_and_ready_carry_the_build_identity(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CLARA_BUILD_COMMIT", raising=False)
    monkeypatch.delenv("CLARA_VERSION", raising=False)
    client = _client(lambda: _pg(COMPATIBLE))
    assert client.get("/health").json() == {"status": "ok", "version": None}

    monkeypatch.setenv("CLARA_BUILD_COMMIT", "3e86f66")
    assert client.get("/health").json() == {"status": "ok", "version": "3e86f66"}
    ready = client.get("/ready")
    assert ready.status_code == 200
    # Public and minimal: three fields, no backend type, no error class, no versions.
    assert ready.json() == {"status": "ok", "version": "3e86f66", "measurement_schema": "compatible"}

    details = client.get("/ready/details")
    assert details.status_code == 200
    checks = details.json()["checks"]
    assert checks["database"] == _pg(COMPATIBLE)
    assert checks["build"] == {"version": "3e86f66"}
    assert checks["measurement"] == {
        "state": "compatible",
        "expected_function_version": EXPECTED_MEASUREMENT_FUNCTION_VERSION,
        "found_function_version": EXPECTED_MEASUREMENT_FUNCTION_VERSION,
        "columns_missing": [],
        "backend_tick": "plpgsql",
        "action": None,
    }


def test_old_function_under_a_new_app_is_reported_not_taken_out_of_rotation() -> None:
    client = _client(lambda: _pg(OLD_FUNCTION))
    ready = client.get("/ready")
    assert ready.status_code == 200  # the instance serves; the schema gap is a release step
    assert ready.json()["status"] == "ok"
    assert ready.json()["measurement_schema"] == "incompatible"
    measurement = client.get("/ready/details").json()["checks"]["measurement"]
    assert measurement["state"] == "incompatible"
    assert measurement["found_function_version"] is None
    assert measurement["expected_function_version"] == EXPECTED_MEASUREMENT_FUNCTION_VERSION
    assert "017_measurement_intervals.sql" in measurement["action"]

    pre_017 = _client(lambda: _pg(PRE_017_DATABASE)).get("/ready/details").json()["checks"]["measurement"]
    assert pre_017["state"] == "incompatible"
    assert pre_017["columns_missing"] == ["contract_snapshot", "observation_start", "observation_end"]


def test_python_fallback_is_named_on_postgres_and_compatible_on_sqlite() -> None:
    fallback = _client(lambda: _pg(NO_TICK)).get("/ready/details").json()["checks"]["measurement"]
    assert fallback["state"] == "fallback" and fallback["backend_tick"] == "python"
    assert "017_measurement_intervals.sql" in fallback["action"]
    sqlite = _client(lambda: {"ok": True, "backend": "sqlite", "measurement": SQLITE})
    assert sqlite.get("/ready").json()["measurement_schema"] == "compatible"


def test_database_failure_is_a_503_with_an_unknown_schema(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CLARA_BUILD_COMMIT", raising=False)
    monkeypatch.delenv("CLARA_VERSION", raising=False)

    def broken() -> dict:
        raise ConnectionError("connection refused")

    client = _client(broken)
    ready = client.get("/ready")
    assert ready.status_code == 503
    assert ready.json() == {"status": "degraded", "version": None, "measurement_schema": "unknown"}
    details = client.get("/ready/details")
    assert details.status_code == 503
    checks = details.json()["checks"]
    assert checks["database"] == {"ok": False, "error": "ConnectionError"}  # the class, never the DSN
    assert checks["measurement"]["state"] == "unknown"
    assert "DATABASE_URL" in checks["measurement"]["action"]


class _CatalogueConnection:
    """A connection answering the four catalogue queries measurement_schema_state runs."""

    def __init__(self, *, version_function: bool, version: int | None, tick: bool, columns: list[str]) -> None:
        self.answers = {
            "clara_measurement_function_version()')": {"present": version_function},
            "public.clara_measurement_function_version() AS v": {"v": version},
            "clara_run_due_measurements(integer, timestamptz)')": {"present": tick},
        }
        self.columns = columns
        self.sql = ""
        self.queries: list[str] = []

    def execute(self, sql: str, *_args):
        self.sql = sql
        self.queries.append(sql)
        return self

    def fetchone(self):
        for needle, row in self.answers.items():
            if needle in self.sql:
                return row
        raise AssertionError(f"unexpected query: {self.sql}")

    def fetchall(self):
        assert "information_schema.columns" in self.sql
        return [{"column_name": c} for c in self.columns]


ALL_COLUMNS = ["id", "workspace_id", "problem_id", "kind", "status", *MEASUREMENT_PLAN_COLUMNS]


def test_measurement_schema_state_reads_the_catalogue() -> None:
    current = _CatalogueConnection(version_function=True, version=17, tick=True, columns=ALL_COLUMNS)
    assert measurement_schema_state(current) == COMPATIBLE

    old = _CatalogueConnection(version_function=False, version=None, tick=True, columns=ALL_COLUMNS)
    assert measurement_schema_state(old) == OLD_FUNCTION
    # No version function: its value is never queried (the call would raise on a real server).
    assert not any("AS v" in q for q in old.queries)

    pre_017 = _CatalogueConnection(
        version_function=False, version=None, tick=True, columns=[c for c in ALL_COLUMNS if c not in PRE_017_DATABASE["columns_missing"]]
    )
    assert measurement_schema_state(pre_017) == PRE_017_DATABASE

    no_tick = _CatalogueConnection(version_function=False, version=None, tick=False, columns=ALL_COLUMNS)
    assert measurement_schema_state(no_tick) == NO_TICK
