"""Dispatch authorisation: a push (first or retried) sends exactly the action
revision the approval in force signed, for the execution that approval created.

Invariants under test (never the old unsafe behaviour):
  - an approved action cannot be edited in place (PATCH -> 409);
  - a retry after an out-of-band edit, a rejection, or a newer approval run is
    refused with a named reason and the connector is NOT called;
  - an unchanged retry still succeeds and names the authorising decision;
  - four-eyes runs need two distinct reviewers on the same revision;
  - concurrent retries create at most one external record;
  - SQLite persists the approval -> execution binding, legacy rows still load
    (created_at fallback), and rows without a snapshot fail closed.
"""

from __future__ import annotations

import json
import sqlite3
import tempfile
import threading
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.connectors import DESTINATIONS
from app.connectors.base import ConnectorError
from app.connectors.config_store import ConnectorConfigStore
from app.domain.models import (
    ActionProposalUpdateRequest,
    ApprovalRecord,
    ExecutionRecord,
    ExecutionStatus,
)
from app.main import create_app
from app.services.contexts import CustomerContextStore
from app.services.measurement_scheduler import SQLiteMeasurementPlanStore
from app.services.problems import ProblemStore
from app.services.seed import load_seed_problems
from app.services.signals import SignalStore
from app.services.workflow import (
    SQLiteWorkflowStore,
    WorkflowStore,
    action_snapshot,
    authorize_dispatch,
    find_action,
)
from app.services.workspace import SQLiteWorkspaceStore

JIRA_CONFIG = {
    "base_url": "https://example.atlassian.net",
    "email": "a@b.c",
    "api_token": "t",
    "project_key": "PAY",
}


def _iso(moment: datetime) -> str:
    return moment.isoformat().replace("+00:00", "Z")


class _FakeJira:
    """Records every payload; fails on the call numbers in `fail_calls`."""

    connector_type = "jira"

    def __init__(self, *, fail_calls: set[int] | None = None, delay: float = 0.0) -> None:
        self.calls: list[dict] = []
        self.fail_calls = {1} if fail_calls is None else fail_calls
        self.delay = delay
        self._lock = threading.Lock()

    def push(self, action, config):
        with self._lock:
            self.calls.append({"action": action, "config": config})
            number = len(self.calls)
        if number in self.fail_calls:
            raise ConnectorError("Jira returned 500", connector="jira", status=500)
        if self.delay:
            time.sleep(self.delay)
        return {"external_id": f"PAY-{number}", "status": "pushed", "audit": {}}


def _client(
    problem_store: ProblemStore | None = None,
    workflows: WorkflowStore | SQLiteWorkflowStore | None = None,
) -> TestClient:
    # Own plan, connector and workspace stores per app: the default SQLite
    # files are shared by every test in the process, so a four-eyes flag or a
    # Jira config left by one test would leak into the next.
    scratch = Path(tempfile.mkdtemp(prefix="clara-dispatch-"))
    return TestClient(
        create_app(
            problem_store=problem_store or ProblemStore([]),
            workflows=workflows or WorkflowStore(),
            signals=SignalStore(),
            contexts=CustomerContextStore(),
            connector_configs=ConnectorConfigStore(),
            measurement_plans=SQLiteMeasurementPlanStore(scratch / "plans.db"),
            workspace=SQLiteWorkspaceStore(scratch / "workspace.db"),
        )
    )


def _promote_checkout_problem(client: TestClient) -> tuple[str, str]:
    """Import two payment signals, accept the checkout candidate, configure
    Jira; returns (problem_id, structural action id)."""
    now = datetime.now(UTC)
    rows = [
        {
            "signal_id": f"sig-{i}",
            "feedback_text": f"Checkout crashed when I paid, attempt {i}",
            "source": "app_store",
            "customer_id": f"C-{i}",
            "account_id": f"A-{i}",
            "timestamp": _iso(now - timedelta(hours=2) + timedelta(minutes=30) * i),
            "journey": "checkout",
            "journey_stage": "payment",
        }
        for i in range(2)
    ]
    assert client.post("/signals/import", json={"signals": rows}).status_code == 200
    accepted = client.post("/problem-candidates/CAND-CHECKOUT-PAYMENT/accept", json={"reviewer": "r"})
    assert accepted.status_code == 200, accepted.text
    problem_id = accepted.json()["problem_id"]
    assert client.put("/connectors/jira", json=JIRA_CONFIG).status_code == 200
    transition = client.post(
        f"/problems/{problem_id}/transitions",
        json={"target_status": "approval_needed", "actor": "tester", "note": "reviewed"},
    )
    assert transition.status_code == 200, transition.text
    return problem_id, f"ACT-{problem_id}-STRUCTURAL"


def _decide(client: TestClient, problem_id: str, action_id: str, decision: str, reviewer: str = "reviewer"):
    return client.post(
        f"/problems/{problem_id}/approvals",
        json={
            "action_id": action_id,
            "decision": decision,
            "reviewer": reviewer,
            "accept_proposed_contract": False,
        },
    )


def _executions(client: TestClient, problem_id: str) -> list[dict]:
    return [e for e in client.get("/executions").json() if e["problem_id"] == problem_id]


def _action(client: TestClient, problem_id: str, action_id: str) -> dict:
    problem = client.get(f"/problems/{problem_id}").json()
    return next(a for a in problem["action_proposals"] if a["action_id"] == action_id)


def _approve_and_fail_push(client: TestClient, monkeypatch: pytest.MonkeyPatch, **jira_kwargs):
    """approve -> connector fails -> one push_failed execution."""
    jira = _FakeJira(**jira_kwargs)
    monkeypatch.setitem(DESTINATIONS, "jira", jira)
    problem_id, action_id = _promote_checkout_problem(client)
    assert _decide(client, problem_id, action_id, "approved").status_code == 200
    executions = _executions(client, problem_id)
    assert len(executions) == 1 and executions[0]["status"] == "push_failed"
    assert len(jira.calls) == 1
    return jira, problem_id, action_id, executions[0]


# ---------------------------------------------------------------------------
# 1-5: API-level invariants on the retry / edit / revoke sequence
# ---------------------------------------------------------------------------


def test_approved_action_cannot_be_edited_and_retry_sends_the_approved_text(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("CLARA_SEED_DEMO_DATA", "0")
    client = _client()
    jira, problem_id, action_id, execution = _approve_and_fail_push(client, monkeypatch)
    approved_text = _action(client, problem_id, action_id)["proposal"]

    edited = client.patch(
        f"/problems/{problem_id}/actions/{action_id}",
        json={"proposal": "Text nobody approved."},
    )
    assert edited.status_code == 409, edited.text
    assert "rejection first" in edited.json()["detail"]
    assert _action(client, problem_id, action_id)["proposal"] == approved_text

    retried = client.post(f"/problems/{problem_id}/executions/{execution['execution_id']}/retry")
    assert retried.status_code == 200, retried.text
    assert retried.json()["status"] == "pushed"
    assert len(jira.calls) == 2
    # Human-reviewed dispatch: the approved text, verbatim, no disclosure line.
    assert jira.calls[-1]["action"]["description"] == approved_text


def test_retry_refuses_when_the_action_changed_behind_the_api(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CLARA_SEED_DEMO_DATA", "0")
    problem_store = ProblemStore([])
    client = _client(problem_store)
    jira, problem_id, action_id, execution = _approve_and_fail_push(client, monkeypatch)

    # A path that bypasses the router's guard (bug, script, future endpoint).
    assert problem_store.update_action_proposal(
        problem_id, action_id, ActionProposalUpdateRequest(proposal="Text nobody approved.")
    ) is not None

    retried = client.post(f"/problems/{problem_id}/executions/{execution['execution_id']}/retry")
    assert retried.status_code == 409, retried.text
    assert retried.json()["detail"].startswith("action_changed_since_approval")
    assert "proposal" in retried.json()["detail"]
    assert len(jira.calls) == 1  # no second outbound write
    after = _executions(client, problem_id)[0]
    assert after["status"] == "push_failed"
    assert after["external_ref"] is None
    assert "Dispatch refused (action_changed_since_approval)" in after["detail"]
    refused = [
        e for e in client.get("/telemetry").json()["events"] if e["event_type"] == "action_push_refused"
    ]
    assert len(refused) == 1
    assert refused[0]["metadata"] == {"problem_id": problem_id, "reason": "action_changed_since_approval"}


def test_retry_refuses_after_a_rejection(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CLARA_SEED_DEMO_DATA", "0")
    client = _client()
    jira, problem_id, action_id, execution = _approve_and_fail_push(client, monkeypatch)

    assert _decide(client, problem_id, action_id, "rejected").status_code == 200
    retried = client.post(f"/problems/{problem_id}/executions/{execution['execution_id']}/retry")
    assert retried.status_code == 409, retried.text
    assert retried.json()["detail"].startswith("approval_revoked")
    assert len(jira.calls) == 1
    assert _executions(client, problem_id)[0]["status"] == "push_failed"


def test_unchanged_retry_succeeds_and_names_the_decision(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CLARA_SEED_DEMO_DATA", "0")
    client = _client()
    jira, problem_id, action_id, execution = _approve_and_fail_push(client, monkeypatch)
    decision_id = client.get(f"/problems/{problem_id}/workflow").json()["approvals"][0]["decision_id"]

    retried = client.post(f"/problems/{problem_id}/executions/{execution['execution_id']}/retry")
    assert retried.status_code == 200, retried.text
    body = retried.json()
    assert body["status"] == "pushed"
    assert body["external_ref"] == "PAY-2"
    assert f"authorized by {decision_id}" in body["detail"]
    assert len(jira.calls) == 2


def test_stale_execution_is_superseded_by_a_new_approval_run(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CLARA_SEED_DEMO_DATA", "0")
    client = _client()
    jira, problem_id, action_id, old_execution = _approve_and_fail_push(client, monkeypatch)

    assert _decide(client, problem_id, action_id, "rejected").status_code == 200
    # Editing is allowed again once the approval is revoked.
    edited = client.patch(
        f"/problems/{problem_id}/actions/{action_id}", json={"proposal": "Revised proposal."}
    )
    assert edited.status_code == 200, edited.text
    assert _decide(client, problem_id, action_id, "approved").status_code == 200

    executions = _executions(client, problem_id)
    assert len(executions) == 2
    new_execution = next(e for e in executions if e["execution_id"] != old_execution["execution_id"])
    assert new_execution["status"] == "pushed"
    assert jira.calls[-1]["action"]["description"] == "Revised proposal."

    retried = client.post(f"/problems/{problem_id}/executions/{old_execution['execution_id']}/retry")
    assert retried.status_code == 409, retried.text
    assert retried.json()["detail"].startswith("execution_superseded")
    assert len(jira.calls) == 2
    stale = next(e for e in _executions(client, problem_id) if e["execution_id"] == old_execution["execution_id"])
    assert stale["status"] == "push_failed"
    assert "execution_superseded" in stale["detail"]


# ---------------------------------------------------------------------------
# 6: four-eyes
# ---------------------------------------------------------------------------


def test_four_eyes_retry_needs_two_reviewers_and_stops_after_a_rejection(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("CLARA_SEED_DEMO_DATA", "0")
    client = _client()
    assert client.put("/workspace", json={"four_eyes_approval": True}).status_code == 200
    assert client.get("/workspace").json()["four_eyes_approval"] is True
    jira = _FakeJira(fail_calls={1, 2})
    monkeypatch.setitem(DESTINATIONS, "jira", jira)
    problem_id, action_id = _promote_checkout_problem(client)

    assert _decide(client, problem_id, action_id, "approved", reviewer="alice").status_code == 200
    assert _executions(client, problem_id) == []  # first approval holds
    assert _decide(client, problem_id, action_id, "approved", reviewer="bob").status_code == 200
    executions = _executions(client, problem_id)
    assert len(executions) == 1 and executions[0]["status"] == "push_failed"
    execution_id = executions[0]["execution_id"]
    approvals = client.get(f"/problems/{problem_id}/workflow").json()["approvals"]
    assert approvals[0]["execution_id"] is None
    assert approvals[1]["execution_id"] == execution_id

    # Retry under an intact two-reviewer run is authorised (connector fails again).
    retried = client.post(f"/problems/{problem_id}/executions/{execution_id}/retry")
    assert retried.status_code == 200, retried.text
    assert retried.json()["status"] == "push_failed"
    assert len(jira.calls) == 2

    # A rejection by either reviewer revokes the run.
    assert _decide(client, problem_id, action_id, "rejected", reviewer="alice").status_code == 200
    refused = client.post(f"/problems/{problem_id}/executions/{execution_id}/retry")
    assert refused.status_code == 409, refused.text
    assert refused.json()["detail"].startswith("approval_revoked")
    assert len(jira.calls) == 2


def test_four_eyes_retry_succeeds_when_both_reviewers_signed_the_same_revision(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("CLARA_SEED_DEMO_DATA", "0")
    client = _client()
    assert client.put("/workspace", json={"four_eyes_approval": True}).status_code == 200
    jira = _FakeJira()
    monkeypatch.setitem(DESTINATIONS, "jira", jira)
    problem_id, action_id = _promote_checkout_problem(client)
    assert _decide(client, problem_id, action_id, "approved", reviewer="alice").status_code == 200
    assert _decide(client, problem_id, action_id, "approved", reviewer="bob").status_code == 200
    execution = _executions(client, problem_id)[0]
    assert execution["status"] == "push_failed"

    retried = client.post(f"/problems/{problem_id}/executions/{execution['execution_id']}/retry")
    assert retried.status_code == 200, retried.text
    assert retried.json()["status"] == "pushed"
    approvals = client.get(f"/problems/{problem_id}/workflow").json()["approvals"]
    assert f"authorized by {approvals[0]['decision_id']}, {approvals[1]['decision_id']}" in retried.json()["detail"]


# ---------------------------------------------------------------------------
# 7: concurrency — one external record, whatever the interleaving
# ---------------------------------------------------------------------------


def test_concurrent_retries_create_exactly_one_external_record(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CLARA_SEED_DEMO_DATA", "0")
    client = _client()
    jira, problem_id, action_id, execution = _approve_and_fail_push(client, monkeypatch, delay=0.2)
    url = f"/problems/{problem_id}/executions/{execution['execution_id']}/retry"

    results: list[tuple[int, dict]] = []
    barrier = threading.Barrier(2)

    def retry() -> None:
        barrier.wait()
        response = client.post(url)
        results.append((response.status_code, response.json()))

    threads = [threading.Thread(target=retry) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=10)

    assert len(results) == 2
    assert len(jira.calls) == 2  # the original failure + exactly one successful push
    assert {status for status, _ in results} <= {200, 409}
    assert any(status == 200 for status, _ in results)
    external_refs = {body["external_ref"] for status, body in results if status == 200}
    assert external_refs == {"PAY-2"}
    final = _executions(client, problem_id)[0]
    assert final["status"] == "pushed"
    assert final["external_ref"] == "PAY-2"


# ---------------------------------------------------------------------------
# 8: SQLite persistence and legacy rows
# ---------------------------------------------------------------------------


def test_sqlite_persists_the_approval_execution_binding(tmp_path: Path) -> None:
    from app.domain.models import ApprovalDecision

    problem = next(p for p in load_seed_problems() if p.problem_id == "PRB-108")
    store = SQLiteWorkflowStore(tmp_path / "wf.db")
    record = store.record_approval(
        problem=problem,
        decision=ApprovalDecision(action_id="ACT-501", decision="approved", reviewer="owner"),
    )
    assert record.execution_id == store.list_executions()[0].execution_id

    reopened = SQLiteWorkflowStore(tmp_path / "wf.db")
    approval = reopened.list_approvals()[0]
    assert approval.execution_id == reopened.list_executions()[0].execution_id


def _legacy_workflow_db(path: Path, *, with_snapshot: bool) -> None:
    """An approvals table written before execution_id existed (and, optionally,
    before action_snapshot did), plus the push_failed execution it created."""
    problem = next(p for p in load_seed_problems() if p.problem_id == "PRB-108")
    snapshot = json.dumps(
        action_snapshot(find_action(problem, "ACT-501")).model_dump(mode="json", by_alias=True)
    )
    stamp = "2026-07-01T00:00:00+00:00"
    with sqlite3.connect(path) as conn:
        conn.execute(
            """
            CREATE TABLE approvals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                problem_id TEXT NOT NULL,
                action_id TEXT NOT NULL,
                decision TEXT NOT NULL,
                reviewer TEXT NOT NULL,
                note TEXT,
                created_at TEXT NOT NULL,
                action_snapshot TEXT
            )
            """
        )
        conn.execute(
            "INSERT INTO approvals (problem_id, action_id, decision, reviewer, created_at, action_snapshot)"
            " VALUES ('PRB-108', 'ACT-501', 'approved', 'owner', ?, ?)",
            (stamp, snapshot if with_snapshot else None),
        )
        conn.execute(
            """
            CREATE TABLE executions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                problem_id TEXT NOT NULL,
                action_id TEXT NOT NULL,
                destination TEXT NOT NULL,
                status TEXT NOT NULL,
                owner TEXT NOT NULL,
                summary TEXT NOT NULL,
                created_at TEXT NOT NULL,
                external_ref TEXT,
                detail TEXT,
                human_reviewed INTEGER NOT NULL DEFAULT 0
            )
            """
        )
        conn.execute(
            "INSERT INTO executions"
            " (problem_id, action_id, destination, status, owner, summary, created_at, human_reviewed)"
            " VALUES ('PRB-108', 'ACT-501', 'jira', 'push_failed', 'own', 'sum', ?, 1)",
            (stamp,),
        )


def test_legacy_approval_without_execution_id_authorises_by_created_at(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    db_path = tmp_path / "legacy.db"
    _legacy_workflow_db(db_path, with_snapshot=True)
    store = SQLiteWorkflowStore(db_path)
    approval = store.list_approvals()[0]
    assert approval.execution_id is None and approval.action_snapshot is not None

    client = _client(ProblemStore(load_seed_problems()), workflows=store)
    assert client.put("/connectors/jira", json=JIRA_CONFIG).status_code == 200
    jira = _FakeJira(fail_calls=set())
    monkeypatch.setitem(DESTINATIONS, "jira", jira)
    execution_id = store.list_executions()[0].execution_id
    retried = client.post(f"/problems/PRB-108/executions/{execution_id}/retry")
    assert retried.status_code == 200, retried.text
    assert retried.json()["status"] == "pushed"
    assert "authorized by DEC-0001" in retried.json()["detail"]
    assert len(jira.calls) == 1


def test_legacy_approval_without_snapshot_fails_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    db_path = tmp_path / "legacy.db"
    _legacy_workflow_db(db_path, with_snapshot=False)
    store = SQLiteWorkflowStore(db_path)
    client = _client(ProblemStore(load_seed_problems()), workflows=store)
    assert client.put("/connectors/jira", json=JIRA_CONFIG).status_code == 200
    jira = _FakeJira(fail_calls=set())
    monkeypatch.setitem(DESTINATIONS, "jira", jira)
    execution_id = store.list_executions()[0].execution_id
    retried = client.post(f"/problems/PRB-108/executions/{execution_id}/retry")
    assert retried.status_code == 409, retried.text
    assert retried.json()["detail"].startswith("approval_unverifiable")
    assert jira.calls == []
    persisted = SQLiteWorkflowStore(db_path).list_executions()[0]
    assert persisted.status == ExecutionStatus.push_failed
    assert "approval_unverifiable" in (persisted.detail or "")


# ---------------------------------------------------------------------------
# 9: helper-level unit tests, one per reason code
# ---------------------------------------------------------------------------

T1 = "2026-07-01T00:00:00+00:00"
T2 = "2026-07-02T00:00:00+00:00"
T3 = "2026-07-03T00:00:00+00:00"
T4 = "2026-07-04T00:00:00+00:00"


@pytest.fixture
def seed_action():
    problem = next(p for p in load_seed_problems() if p.problem_id == "PRB-108")
    return problem, find_action(problem, "ACT-501")


def _approval(
    decision_id: str,
    *,
    decision: str = "approved",
    reviewer: str = "alice",
    created_at: str = T1,
    snapshot=None,
    execution_id: str | None = None,
    problem_id: str = "PRB-108",
    action_id: str = "ACT-501",
) -> ApprovalRecord:
    return ApprovalRecord(
        decision_id=decision_id,
        problem_id=problem_id,
        action_id=action_id,
        decision=decision,
        reviewer=reviewer,
        created_at=created_at,
        action_snapshot=snapshot,
        execution_id=execution_id,
    )


def _execution(execution_id: str = "EXE-0001", *, created_at: str = T1, destination: str = "jira") -> ExecutionRecord:
    return ExecutionRecord(
        execution_id=execution_id,
        problem_id="PRB-108",
        action_id="ACT-501",
        destination=destination,
        status=ExecutionStatus.push_failed,
        owner="own",
        summary="sum",
        created_at=created_at,
        human_reviewed=True,
    )


def test_helper_approval_missing(seed_action) -> None:
    problem, action = seed_action
    result = authorize_dispatch(problem=problem, action=action, execution=_execution(), approvals=[], four_eyes=False)
    assert (result.authorized, result.reason, result.decision_ids) == (False, "approval_missing", [])
    # Decisions for other actions/problems do not count.
    other = _approval("DEC-0001", snapshot=action_snapshot(action), action_id="ACT-502", execution_id="EXE-0001")
    assert authorize_dispatch(problem=problem, action=action, execution=_execution(), approvals=[other], four_eyes=False).reason == "approval_missing"


def test_helper_approval_revoked(seed_action) -> None:
    problem, action = seed_action
    snap = action_snapshot(action)
    approvals = [
        _approval("DEC-0001", snapshot=snap, execution_id="EXE-0001"),
        _approval("DEC-0002", decision="rejected", created_at=T2, snapshot=snap),
    ]
    result = authorize_dispatch(problem=problem, action=action, execution=_execution(), approvals=approvals, four_eyes=False)
    assert result.reason == "approval_revoked"
    assert "DEC-0002" in result.detail
    # Ordering is by created_at, not list position.
    assert authorize_dispatch(problem=problem, action=action, execution=_execution(), approvals=list(reversed(approvals)), four_eyes=False).reason == "approval_revoked"
    needs_more = [_approval("DEC-0001", snapshot=snap, execution_id="EXE-0001"), _approval("DEC-0002", decision="needs_more_evidence", created_at=T2, snapshot=snap)]
    assert authorize_dispatch(problem=problem, action=action, execution=_execution(), approvals=needs_more, four_eyes=False).reason == "approval_revoked"


def test_helper_approval_incomplete_under_four_eyes(seed_action) -> None:
    problem, action = seed_action
    snap = action_snapshot(action)
    single = [_approval("DEC-0001", snapshot=snap)]
    assert authorize_dispatch(problem=problem, action=action, execution=_execution(), approvals=single, four_eyes=True).reason == "approval_incomplete"
    same_reviewer_twice = [
        _approval("DEC-0001", snapshot=snap),
        _approval("DEC-0002", snapshot=snap, created_at=T2, reviewer="alice"),
    ]
    assert authorize_dispatch(problem=problem, action=action, execution=_execution(), approvals=same_reviewer_twice, four_eyes=True).reason == "approval_incomplete"
    # Without four-eyes one reviewer suffices.
    assert authorize_dispatch(problem=problem, action=action, execution=_execution(), approvals=single, four_eyes=False).authorized is True


def test_helper_execution_superseded(seed_action) -> None:
    problem, action = seed_action
    snap = action_snapshot(action)
    bound_elsewhere = [_approval("DEC-0001", snapshot=snap, execution_id="EXE-0002")]
    result = authorize_dispatch(problem=problem, action=action, execution=_execution("EXE-0001"), approvals=bound_elsewhere, four_eyes=False)
    assert result.reason == "execution_superseded"
    # A rejection resets the run: the old execution belongs to a dead run.
    history = [
        _approval("DEC-0001", snapshot=snap, execution_id="EXE-0001"),
        _approval("DEC-0002", decision="rejected", created_at=T2),
        _approval("DEC-0003", snapshot=snap, created_at=T3, execution_id="EXE-0002"),
    ]
    assert authorize_dispatch(problem=problem, action=action, execution=_execution("EXE-0001"), approvals=history, four_eyes=False).reason == "execution_superseded"
    fresh = authorize_dispatch(problem=problem, action=action, execution=_execution("EXE-0002", created_at=T3), approvals=history, four_eyes=False)
    assert fresh.authorized is True and fresh.decision_ids == ["DEC-0003"]


def test_helper_legacy_created_at_fallback(seed_action) -> None:
    problem, action = seed_action
    snap = action_snapshot(action)
    legacy = [_approval("DEC-0001", snapshot=snap, created_at=T1)]
    assert authorize_dispatch(problem=problem, action=action, execution=_execution(created_at=T1), approvals=legacy, four_eyes=False).authorized is True
    assert authorize_dispatch(problem=problem, action=action, execution=_execution(created_at=T2), approvals=legacy, four_eyes=False).reason == "execution_superseded"


def test_helper_approval_unverifiable(seed_action) -> None:
    problem, action = seed_action
    no_snapshot = [_approval("DEC-0001", snapshot=None, execution_id="EXE-0001")]
    result = authorize_dispatch(problem=problem, action=action, execution=_execution(), approvals=no_snapshot, four_eyes=False)
    assert result.reason == "approval_unverifiable"
    assert "DEC-0001" in result.detail


def test_helper_action_changed_since_approval(seed_action) -> None:
    problem, action = seed_action
    approved = [_approval("DEC-0001", snapshot=action_snapshot(action), execution_id="EXE-0001")]
    edited = action.model_copy(update={"proposal": "Different text.", "owner": "someone_else"})
    result = authorize_dispatch(problem=problem, action=edited, execution=_execution(), approvals=approved, four_eyes=False)
    assert result.reason == "action_changed_since_approval"
    assert result.changed_fields == ["owner", "proposal"]
    # approval_state is a UI label: changing it does not invalidate the approval.
    relabelled = action.model_copy(update={"approval_state": "ready_for_product_review"})
    assert authorize_dispatch(problem=problem, action=relabelled, execution=_execution(), approvals=approved, four_eyes=False).authorized is True


def test_helper_approval_revision_mismatch(seed_action) -> None:
    problem, action = seed_action
    earlier = action.model_copy(update={"proposal": "First revision."})
    approvals = [
        _approval("DEC-0001", snapshot=action_snapshot(earlier), reviewer="alice"),
        _approval("DEC-0002", snapshot=action_snapshot(action), reviewer="bob", created_at=T2, execution_id="EXE-0001"),
    ]
    result = authorize_dispatch(problem=problem, action=action, execution=_execution(), approvals=approvals, four_eyes=True)
    assert result.reason == "approval_revision_mismatch"
    assert result.changed_fields == ["proposal"]
    assert "DEC-0001" in result.detail and "DEC-0002" in result.detail


def test_helper_destination_changed(seed_action) -> None:
    problem, action = seed_action
    approved = [_approval("DEC-0001", snapshot=action_snapshot(action), execution_id="EXE-0001")]
    result = authorize_dispatch(problem=problem, action=action, execution=_execution(destination="slack"), approvals=approved, four_eyes=False)
    assert result.reason == "destination_changed"


def test_helper_authorized_names_the_whole_run(seed_action) -> None:
    problem, action = seed_action
    snap = action_snapshot(action)
    history = [
        _approval("DEC-0001", snapshot=snap, reviewer="alice"),
        _approval("DEC-0002", decision="rejected", created_at=T2, reviewer="bob"),
        _approval("DEC-0003", snapshot=snap, reviewer="alice", created_at=T3),
        _approval("DEC-0004", snapshot=snap, reviewer="bob", created_at=T4, execution_id="EXE-0002"),
    ]
    result = authorize_dispatch(problem=problem, action=action, execution=_execution("EXE-0002", created_at=T4), approvals=history, four_eyes=True)
    assert result.authorized is True
    assert result.reason is None
    assert result.decision_ids == ["DEC-0003", "DEC-0004"]
    assert result.changed_fields == []
    assert "DEC-0003, DEC-0004" in result.detail
