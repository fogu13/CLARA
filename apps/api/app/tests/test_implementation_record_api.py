"""The implementation-recording flow the web form drives (13 September 2026
review): authorised editors record the instant a fix landed; viewers are
refused (403); malformed, future and pre-dispatch instants are refused (422)
and record nothing; a created ticket never counts as an implementation; the
outbound preview is readable by viewers.
"""

from __future__ import annotations

import tempfile
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.connectors import DESTINATIONS
from app.services.measurement_scheduler import SQLiteMeasurementPlanStore
from app.services.problems import ProblemStore
from app.services.seed import load_seed_problems
from app.services.signals import SignalStore
from app.services.telemetry import SQLiteTelemetryStore
from app.services.workflow import WorkflowStore
from app.tests.test_api_rbac import (  # noqa: F401 — the autouse fixture resets auth after each test
    SECRET,
    _reset_auth_modules_after_each_test,
)
from app.tests.test_dispatch_authorization_gaps import _FakeJira, _promote_checkout_problem


def _iso(moment: datetime) -> str:
    return moment.isoformat().replace("+00:00", "Z")


def _auth_client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("SUPABASE_JWT_SECRET", SECRET)
    import importlib

    import app.auth as auth_mod
    import app.main as main_mod
    import app.rbac as rbac_mod

    importlib.reload(auth_mod)
    importlib.reload(rbac_mod)
    importlib.reload(main_mod)
    from app.connectors.config_store import ConnectorConfigStore

    scratch = Path(tempfile.mkdtemp(prefix="clara-impl-"))
    return TestClient(
        main_mod.create_app(
            problem_store=ProblemStore(load_seed_problems()),
            signals=SignalStore(),
            workflows=WorkflowStore(),
            connector_configs=ConnectorConfigStore(),
            telemetry=SQLiteTelemetryStore(scratch / "telemetry.db"),
            measurement_plans=SQLiteMeasurementPlanStore(scratch / "plans.db"),
        )
    )


def _header(role: str) -> dict[str, str]:
    from app.tests.test_api_rbac import token

    return {"Authorization": f"Bearer {token(role)}"}


def _approved_execution(client: TestClient, headers: dict[str, str]) -> dict:
    response = client.post(
        "/problems/PRB-108/approvals",
        json={"action_id": "ACT-501", "decision": "approved", "reviewer": "ignored", "accept_proposed_contract": False},
        headers=headers,
    )
    assert response.status_code == 200, response.text
    return next(e for e in client.get("/executions", headers=headers).json() if e["action_id"] == "ACT-501")


def test_viewer_is_refused_and_editor_records_the_implementation(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _auth_client(monkeypatch)
    editor, viewer = _header("editor"), _header("viewer")
    execution = _approved_execution(client, editor)
    assert execution["status"] == "draft_created"  # no connector: the draft is the deliverable
    assert execution["implemented_at"] is None
    url = f"/problems/PRB-108/executions/{execution['execution_id']}/implementation"
    at = _iso(datetime.now(UTC))

    refused = client.post(url, json={"implemented_at": at, "note": "landed"}, headers=viewer)
    assert refused.status_code == 403, refused.text
    assert next(e for e in client.get("/executions", headers=viewer).json() if e["execution_id"] == execution["execution_id"])["implemented_at"] is None

    recorded = client.post(url, json={"implemented_at": at, "note": "landed"}, headers=editor)
    assert recorded.status_code == 200, recorded.text
    assert recorded.json()["implemented_at"] == at
    assert recorded.json()["implementation_note"] == "landed"
    assert recorded.json()["status"] == "draft_created"  # an attestation, not a push
    plans = client.get("/measurements", headers=viewer).json()
    assert {p["origin"] for p in plans if p["status"] == "pending"} == {"implementation"}
    assert all(p["observation_start"] and p["observation_end"] for p in plans if p["status"] == "pending")

    # The preview is a read: viewers may look at what a decision would sign.
    preview = client.get("/problems/PRB-108/actions/ACT-501/outbound-preview", headers=viewer)
    assert preview.status_code == 200 and len(preview.json()["sha256"]) == 64


@pytest.mark.parametrize(
    ("body", "detail"),
    [
        ({"implemented_at": "not-a-date"}, "ISO 8601"),
        ({"implemented_at": _iso(datetime.now(UTC) + timedelta(days=1))}, "future"),
        ({"implemented_at": "2020-01-01T00:00:00Z"}, "precede the execution's approval"),
    ],
)
def test_invalid_instants_are_refused_and_record_nothing(monkeypatch: pytest.MonkeyPatch, body: dict, detail: str) -> None:
    client = _auth_client(monkeypatch)
    editor = _header("editor")
    execution = _approved_execution(client, editor)
    url = f"/problems/PRB-108/executions/{execution['execution_id']}/implementation"
    refused = client.post(url, json=body, headers=editor)
    assert refused.status_code == 422, refused.text
    assert detail in refused.json()["detail"]
    row = next(e for e in client.get("/executions", headers=editor).json() if e["execution_id"] == execution["execution_id"])
    assert row["implemented_at"] is None
    assert all(p["origin"] != "implementation" for p in client.get("/measurements", headers=editor).json())


def test_an_instant_before_the_dispatch_is_refused_and_a_created_ticket_never_counts(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CLARA_SEED_DEMO_DATA", "0")
    jira = _FakeJira(fail_calls=set())
    monkeypatch.setitem(DESTINATIONS, "jira", jira)
    scratch = Path(tempfile.mkdtemp(prefix="clara-impl-"))
    from app.connectors.config_store import ConnectorConfigStore
    from app.main import create_app
    from app.services.contexts import CustomerContextStore
    from app.services.workspace import SQLiteWorkspaceStore

    client = TestClient(
        create_app(
            problem_store=ProblemStore([]), workflows=WorkflowStore(), signals=SignalStore(), contexts=CustomerContextStore(),
            connector_configs=ConnectorConfigStore(), telemetry=SQLiteTelemetryStore(scratch / "t.db"),
            measurement_plans=SQLiteMeasurementPlanStore(scratch / "p.db"), workspace=SQLiteWorkspaceStore(scratch / "w.db"),
        )
    )
    problem_id, action_id = _promote_checkout_problem(client)
    approved = client.post(f"/problems/{problem_id}/approvals", json={"action_id": action_id, "decision": "approved", "reviewer": "r", "accept_proposed_contract": False})
    assert approved.status_code == 200, approved.text
    [execution] = [e for e in client.get("/executions").json() if e["problem_id"] == problem_id]
    assert execution["status"] == "pushed" and execution["dispatched_at"] is not None
    # Ticket creation stamps the dispatch only; nothing is "implemented".
    assert execution["implemented_at"] is None
    plans = [p for p in client.get("/measurements").json() if p["problem_id"] == problem_id]
    assert {p["origin"] for p in plans} == {"dispatch"}

    dispatched_at = datetime.fromisoformat(execution["dispatched_at"].replace("Z", "+00:00"))
    early = client.post(
        f"/problems/{problem_id}/executions/{execution['execution_id']}/implementation",
        json={"implemented_at": _iso(dispatched_at - timedelta(minutes=1))},
    )
    # Refused as an instant before the record left CLARA: the approval and the
    # dispatch stamps are one request apart, so either bound may name the refusal.
    assert early.status_code == 422 and "cannot precede the execution's" in early.json()["detail"]
    ok = client.post(
        f"/problems/{problem_id}/executions/{execution['execution_id']}/implementation",
        json={"implemented_at": _iso(dispatched_at + timedelta(minutes=1)), "note": "deployed"},
    )
    assert ok.status_code == 200, ok.text
    assert ok.json()["implemented_at"] == _iso(dispatched_at + timedelta(minutes=1))
    plans = [p for p in client.get("/measurements").json() if p["problem_id"] == problem_id]
    assert {p["status"] for p in plans if p["origin"] == "dispatch"} == {"superseded"}
    assert {p["origin"] for p in plans if p["status"] == "pending"} == {"implementation"}
