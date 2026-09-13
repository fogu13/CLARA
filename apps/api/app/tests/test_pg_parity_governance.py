"""Postgres parity for dispatch governance (13 September 2026 review, F1).

Skipped unless CLARA_TEST_DATABASE_URL points at a PostgreSQL database with
migrations 001-017 applied (conftest keeps DATABASE_URL="" so no app store
touches it by accident; the stores here are built with the explicit URL).

Two store INSTANCES stand in for two API workers sharing one database:

  - a rejection committed by worker B refuses a dispatch authorised on worker
    A's cached snapshot (the cache is never the authority);
  - the dispatch claim is a database compare-and-set: two instances cannot
    both win, a finished execution is not claimable, an expired claim is
    taken over;
  - the approval insert and a governed problem edit take the same advisory
    lock: an edit committed while a decision waited makes the decision a 409
    (it would have signed text the reviewer never read), and a decision
    recorded first makes the edit's guard refuse;
  - the outbound snapshot round-trips through the JSONB payload.
"""

from __future__ import annotations

import os
import threading
import time
from datetime import UTC, datetime, timedelta

import pytest
from fastapi import HTTPException

from app.domain.models import ApprovalDecision, ExecutionStatus, ProblemUpdateRequest
from app.services.action_push import DispatchNotAuthorized, push_approved_action
from app.services.outbound import build_outbound_content, outbound_sha256
from app.services.signals import build_candidates, promote_candidate
from app.services.workflow import DISPATCH_CLAIM_TTL_SECONDS, find_action
from app.tests.test_pg_parity_measurement import PRE_SIGNALS, TABLES, _rows

URL = os.getenv("CLARA_TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(not URL, reason="CLARA_TEST_DATABASE_URL not set")


def _iso(moment: datetime) -> str:
    return moment.isoformat().replace("+00:00", "Z")


class _Configs:
    def get_config(self, connector_type):
        return type("Cfg", (), {"config": {"base_url": "https://x", "project_key": "PAY"}, "is_active": True})()


class _FakeJira:
    connector_type = "jira"

    def __init__(self) -> None:
        self.calls: list[dict] = []

    def push(self, action, config):
        self.calls.append(action)
        return {"external_id": f"PAY-{len(self.calls)}", "status": "pushed", "audit": {}}


@pytest.fixture()
def stores():
    import psycopg

    from app.services.postgres import PostgresProblemStore, PostgresWorkflowStore

    with psycopg.connect(URL) as conn:
        conn.execute(f"TRUNCATE {', '.join(TABLES)}")
    problem = promote_candidate(build_candidates(PRE_SIGNALS)[0])
    problems = PostgresProblemStore(URL, [])
    problems.upsert_problem(problem)
    return {
        "problem": problem,
        "problems": problems,
        "a": PostgresWorkflowStore(URL),
        "b": PostgresWorkflowStore(URL),
    }


def _jira_action(problem):
    return next(action for action in problem.action_proposals if action.destination == "jira")


def _approve(store, problem, *, reviewer="alice"):
    return store.record_approval(
        problem=problem,
        decision=ApprovalDecision(action_id=_jira_action(problem).action_id, decision="approved", reviewer=reviewer),
    )


def test_rejection_committed_elsewhere_refuses_a_dispatch_on_a_cached_snapshot(stores, monkeypatch) -> None:
    problem, a, b = stores["problem"], stores["a"], stores["b"]
    approval = _approve(a, problem)
    execution = next(e for e in a.list_executions() if e.execution_id == approval.execution_id)
    assert a.list_approvals()[-1].decision.value == "approved"  # A's snapshot: approved
    b.record_approval(
        problem=problem,
        decision=ApprovalDecision(action_id=_jira_action(problem).action_id, decision="rejected", reviewer="bob"),
    )
    jira = _FakeJira()
    monkeypatch.setitem(__import__("app.connectors", fromlist=["DESTINATIONS"]).DESTINATIONS, "jira", jira)
    with pytest.raises(DispatchNotAuthorized) as refused:
        push_approved_action(
            problem=problem, action=_jira_action(problem), execution=execution,
            config_store=_Configs(), workflow_store=a,
        )
    assert refused.value.reason == "approval_revoked"
    assert jira.calls == []
    persisted = [row["payload"] for row in _rows(
        "SELECT payload FROM clara_workflow_records WHERE record_type = 'execution' AND record_id = %s",
        (execution.execution_id,),
    )]
    assert persisted[0]["status"] == "draft_created"
    assert "approval_revoked" in persisted[0]["detail"]
    assert persisted[0].get("dispatch_claimed_at") is None  # the refused attempt released its claim


def test_dispatch_claim_is_a_database_compare_and_set(stores) -> None:
    problem, a, b = stores["problem"], stores["a"], stores["b"]
    approval = _approve(a, problem)
    execution_id = approval.execution_id
    now = datetime.now(UTC)
    won = a.claim_dispatch(execution_id, worker="worker-a", now=_iso(now))
    assert won is not None and won.dispatch_claimed_by == "worker-a"
    assert b.claim_dispatch(execution_id, worker="worker-b", now=_iso(now + timedelta(seconds=1))) is None
    # The claim is in the shared row, not in A's memory.
    row = _rows("SELECT payload FROM clara_workflow_records WHERE record_type = 'execution' AND record_id = %s", (execution_id,))[0]["payload"]
    assert row["dispatch_claimed_by"] == "worker-a"
    # Expired -> taken over by the other instance.
    expired = _iso(now + timedelta(seconds=DISPATCH_CLAIM_TTL_SECONDS + 1))
    taken = b.claim_dispatch(execution_id, worker="worker-b", now=expired)
    assert taken is not None and taken.dispatch_claimed_by == "worker-b"
    # A status write clears the claim; a finished execution is not claimable.
    b.update_execution(execution_id, status=ExecutionStatus.pushed, external_ref="PAY-1", detail="done")
    row = _rows("SELECT payload FROM clara_workflow_records WHERE record_type = 'execution' AND record_id = %s", (execution_id,))[0]["payload"]
    assert row["status"] == "pushed" and row.get("dispatch_claimed_at") is None
    assert a.claim_dispatch(execution_id, worker="worker-a", now=_iso(now + timedelta(days=1))) is None
    assert a.claim_dispatch("EXE-NOPE", worker="worker-a") is None


def test_edit_committed_while_a_decision_waited_makes_the_decision_a_409(stores) -> None:
    """Worker A edits the title under the advisory lock with a slow guard;
    worker B, holding the problem as it read it before the edit, tries to
    approve. B waits for A's transaction, then sees that the stored content
    no longer matches what its reviewer read, and refuses."""
    problem, problems, b = stores["problem"], stores["problems"], stores["b"]
    entered = threading.Event()
    timeline: dict[str, float] = {}

    def slow_guard() -> None:
        entered.set()
        time.sleep(1.0)

    def edit() -> None:
        problems.update_problem(problem.problem_id, ProblemUpdateRequest(title="Edited by worker A"), guard=slow_guard)
        timeline["edit_done"] = time.monotonic()

    def approve() -> None:
        try:
            _approve(b, problem, reviewer="bob")
            timeline["approve_outcome"] = "recorded"
        except HTTPException as exc:
            timeline["approve_outcome"] = exc.status_code
        timeline["approve_done"] = time.monotonic()

    editor = threading.Thread(target=edit)
    editor.start()
    assert entered.wait(5)
    approver = threading.Thread(target=approve)
    approver.start()
    editor.join(10)
    approver.join(10)
    assert timeline["approve_done"] >= timeline["edit_done"]  # the insert waited for the lock
    assert timeline["approve_outcome"] == 409
    assert b.list_approvals() == []
    assert problems.get_problem(problem.problem_id).title == "Edited by worker A"
    # Deciding on the current text works and freezes the edited title.
    fresh = problems.get_problem(problem.problem_id)
    approval = _approve(b, fresh, reviewer="bob")
    assert approval.outbound_snapshot.insight_title == "Edited by worker A"


def test_decision_recorded_first_makes_the_edit_guard_refuse(stores) -> None:
    problem, problems, a, b = stores["problem"], stores["problems"], stores["a"], stores["b"]
    _approve(a, problem)

    def guard() -> None:
        # The router's guard: a fresh read of the approvals on the OTHER instance.
        b.refresh()
        if any(ap.decision.value == "approved" for ap in b.list_approvals() if ap.problem_id == problem.problem_id):
            raise HTTPException(status_code=409, detail="frozen")

    with pytest.raises(HTTPException):
        problems.update_problem(problem.problem_id, ProblemUpdateRequest(title="Should not land"), guard=guard)
    assert problems.get_problem(problem.problem_id).title == problem.title


def test_outbound_snapshot_round_trips_through_jsonb(stores) -> None:
    problem, a, b = stores["problem"], stores["a"], stores["b"]
    approval = _approve(a, problem)
    expected = build_outbound_content(problem, _jira_action(problem))
    assert approval.outbound_snapshot == expected
    assert approval.outbound_sha256 == outbound_sha256(expected)
    b.refresh()
    reloaded = next(ap for ap in b.list_approvals() if ap.decision_id == approval.decision_id)
    assert reloaded.outbound_snapshot == expected and reloaded.outbound_sha256 == approval.outbound_sha256
    payload = _rows("SELECT payload FROM clara_workflow_records WHERE record_type = 'approval'")[0]["payload"]
    assert payload["outbound_sha256"] == approval.outbound_sha256
    assert payload["outbound_snapshot"]["insight_summary"] == problem.statement
    assert find_action(problem, approval.action_id) is not None
