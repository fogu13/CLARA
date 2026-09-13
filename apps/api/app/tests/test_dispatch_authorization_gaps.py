"""Dispatch authorisation — the gaps a second independent probe found after the
approval -> execution binding landed (spec A1-A7). Each test states the DESIRED
invariant:

  A1  a re-approved revision gets its OWN external record; the idempotent
      reuse never hands a superseded run's ticket to a new execution;
  A2  a refused FIRST push is recorded (push_failed, telemetry, no clock), not
      swallowed as a 200 that leaves an untouched-looking draft;
  A3  the effective review status gates the push: a legacy row created by an
      approval is gated, a row with no approval at all cannot be retried;
  A4  the problem title/statement that ride in the outbound payload are frozen
      while an action is approved;
  A5  the success detail names the resolved team route;
  A6  a rejection recorded between the first check and the connector call
      still refuses the write;
  A7  decisions are ordered by their numeric suffix, not as strings.
"""

from __future__ import annotations

import tempfile
import threading
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.connectors import DESTINATIONS
from app.connectors.base import ConnectorError
from app.connectors.config_store import ConnectorConfigStore
from app.domain.models import (
    ActionProposalUpdateRequest,
    ApprovalDecision,
    ApprovalRecord,
    ExecutionRecord,
    ExecutionStatus,
)
from app.main import create_app
from app.services.action_push import DispatchNotAuthorized, push_approved_action
from app.services.contexts import CustomerContextStore
from app.services.measurement_scheduler import SQLiteMeasurementPlanStore
from app.services.problems import ProblemStore
from app.services.seed import load_seed_problems
from app.services.signals import SignalStore
from app.services.telemetry import SQLiteTelemetryStore
from app.services.outbound import build_outbound_content, outbound_sha256
from app.services.workflow import (
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


def _seed_outbound():
    """The outbound content of the seed action PRB-108/ACT-501, which every
    hand-built approval below signs (13 Sep 2026, F1: an approval without
    it cannot dispatch)."""
    problem = next(p for p in load_seed_problems() if p.problem_id == "PRB-108")
    content = build_outbound_content(problem, find_action(problem, "ACT-501"))
    return {"outbound_snapshot": content, "outbound_sha256": outbound_sha256(content)}


class _FakeJira:
    """Records every payload; fails on the call numbers in `fail_calls`."""

    connector_type = "jira"

    def __init__(self, *, fail_calls: set[int] | None = None) -> None:
        self.calls: list[dict] = []
        self.fail_calls = set() if fail_calls is None else fail_calls
        self._lock = threading.Lock()

    def push(self, action, config):
        with self._lock:
            self.calls.append({"action": action, "config": config})
            number = len(self.calls)
        if number in self.fail_calls:
            raise ConnectorError("Jira returned 500", connector="jira", status=500)
        return {"external_id": f"PAY-{number}", "status": "pushed", "audit": {}}


def _client(
    problem_store: ProblemStore | None = None,
    workflows: WorkflowStore | None = None,
    connector_configs: ConnectorConfigStore | None = None,
) -> TestClient:
    # Own plan, telemetry, connector and workspace stores per app: the default
    # SQLite files are shared by every test in the process.
    scratch = Path(tempfile.mkdtemp(prefix="clara-dispatch-gaps-"))
    return TestClient(
        create_app(
            problem_store=problem_store or ProblemStore([]),
            workflows=workflows or WorkflowStore(),
            signals=SignalStore(),
            contexts=CustomerContextStore(),
            connector_configs=connector_configs or ConnectorConfigStore(),
            telemetry=SQLiteTelemetryStore(scratch / "telemetry.db"),
            measurement_plans=SQLiteMeasurementPlanStore(scratch / "plans.db"),
            workspace=SQLiteWorkspaceStore(scratch / "workspace.db"),
        )
    )


def _promote_checkout_problem(client: TestClient) -> tuple[str, str]:
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


def _events(client: TestClient, event_type: str) -> list[dict]:
    return [e for e in client.get("/telemetry").json()["events"] if e["event_type"] == event_type]


def _action(client: TestClient, problem_id: str, action_id: str) -> dict:
    problem = client.get(f"/problems/{problem_id}").json()
    return next(a for a in problem["action_proposals"] if a["action_id"] == action_id)


# ---------------------------------------------------------------------------
# A1 — a re-approved revision gets its own external record
# ---------------------------------------------------------------------------


def test_reapproved_revision_is_dispatched_with_its_own_record(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CLARA_SEED_DEMO_DATA", "0")
    jira = _FakeJira()
    monkeypatch.setitem(DESTINATIONS, "jira", jira)
    client = _client()
    problem_id, action_id = _promote_checkout_problem(client)

    assert _decide(client, problem_id, action_id, "approved").status_code == 200
    [first] = _executions(client, problem_id)
    assert first["status"] == "pushed" and first["external_ref"] == "PAY-1"
    assert first["dispatched_at"] is not None

    assert _decide(client, problem_id, action_id, "rejected").status_code == 200
    edited = client.patch(f"/problems/{problem_id}/actions/{action_id}", json={"proposal": "Revised proposal."})
    assert edited.status_code == 200, edited.text
    assert _decide(client, problem_id, action_id, "approved").status_code == 200

    executions = _executions(client, problem_id)
    assert len(executions) == 2
    second = next(e for e in executions if e["execution_id"] != first["execution_id"])
    # The revised text really left CLARA, as a NEW record — never "pushed"
    # by reusing the ticket the superseded run created.
    assert len(jira.calls) == 2
    assert jira.calls[-1]["action"]["description"] == "Revised proposal."
    assert second["status"] == "pushed"
    assert second["external_ref"] == "PAY-2"
    assert "Reused" not in (second["detail"] or "")
    assert second["dispatched_at"] is not None
    untouched = next(e for e in executions if e["execution_id"] == first["execution_id"])
    assert untouched == first


def test_idempotent_reuse_is_limited_to_the_authorising_run_and_copies_its_clock(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Unit level: two executions bound to ONE approval run (the only case
    reuse is legitimate) share the external record and its dispatch instant;
    an execution outside the run is never reused."""
    problem = next(p for p in load_seed_problems() if p.problem_id == "PRB-108")
    action = find_action(problem, "ACT-501")
    jira = _FakeJira()
    monkeypatch.setitem(DESTINATIONS, "jira", jira)
    store = WorkflowStore()

    def _exe(status: ExecutionStatus, **extra) -> ExecutionRecord:
        return store.add_execution(
            ExecutionRecord(
                execution_id="EXE-XXXX",
                problem_id="PRB-108",
                action_id="ACT-501",
                destination="jira",
                status=status,
                owner="own",
                summary="sum",
                created_at="2026-07-01T00:00:00Z",
                human_reviewed=True,
                **extra,
            )
        )

    stale = _exe(ExecutionStatus.pushed, external_ref="OLD-1", dispatched_at="2026-06-01T00:00:00Z")
    earlier = _exe(ExecutionStatus.pushed, external_ref="PAY-7", dispatched_at="2026-07-01T00:00:10Z")
    current = _exe(ExecutionStatus.push_failed)
    snap = action_snapshot(action)
    store._approvals.extend(
        [
            ApprovalRecord(decision_id="DEC-0001", problem_id="PRB-108", action_id="ACT-501", decision="approved", reviewer="a", created_at="2026-07-01T00:00:00Z", action_snapshot=snap, **_seed_outbound(), execution_id=earlier.execution_id),
            ApprovalRecord(decision_id="DEC-0002", problem_id="PRB-108", action_id="ACT-501", decision="approved", reviewer="b", created_at="2026-07-01T00:00:01Z", action_snapshot=snap, **_seed_outbound(), execution_id=current.execution_id),
        ]
    )

    class _Configs:
        def get_config(self, connector_type):
            return type("Cfg", (), {"config": JIRA_CONFIG, "is_active": True})()

    reused = push_approved_action(
        problem=problem, action=action, execution=current, config_store=_Configs(), workflow_store=store
    )
    assert jira.calls == []
    assert reused.status == ExecutionStatus.pushed
    assert reused.external_ref == "PAY-7"  # the run's own record, never the stale OLD-1
    assert reused.dispatched_at == "2026-07-01T00:00:10Z"  # the reused dispatch, not "now"
    assert stale.external_ref == "OLD-1"


# ---------------------------------------------------------------------------
# A2 — a refused first push is recorded, not swallowed
# ---------------------------------------------------------------------------


def test_refused_first_push_is_a_recorded_failure_that_starts_no_clock(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("CLARA_SEED_DEMO_DATA", "0")
    jira = _FakeJira()
    monkeypatch.setitem(DESTINATIONS, "jira", jira)
    problem_store = ProblemStore([])
    client = _client(problem_store)
    assert client.put("/workspace", json={"four_eyes_approval": True}).status_code == 200
    problem_id, action_id = _promote_checkout_problem(client)

    assert _decide(client, problem_id, action_id, "approved", reviewer="alice").status_code == 200
    # Out-of-band edit between the two four-eyes approvals: bob signs a
    # different revision than alice did.
    assert problem_store.update_action_proposal(
        problem_id, action_id, ActionProposalUpdateRequest(proposal="Text only bob saw.")
    ) is not None
    approved = _decide(client, problem_id, action_id, "approved", reviewer="bob")
    assert approved.status_code == 200, approved.text  # the approval itself stands

    assert jira.calls == []  # nothing left CLARA
    [execution] = _executions(client, problem_id)
    assert execution["status"] == "push_failed"  # retryable, not an untouched draft
    assert execution["external_ref"] is None
    assert execution["detail"].startswith("Dispatch refused (approval_revision_mismatch)")
    [refused] = _events(client, "action_push_refused")
    assert refused["entity_id"] == execution["execution_id"]
    assert refused["metadata"] == {"problem_id": problem_id, "reason": "approval_revision_mismatch"}
    assert _events(client, "action_pushed") == []
    assert _events(client, "measurement_scheduled") == []
    [not_scheduled] = _events(client, "measurement_not_scheduled")
    assert not_scheduled["metadata"]["reason"] == "dispatch_refused"
    assert not_scheduled["metadata"]["execution_id"] == execution["execution_id"]
    assert client.get("/measurements").json() == []
    # Not an approval-origin anchor either.
    assert client.get(f"/problems/{problem_id}/outcome").json()["measurement_origin"] is None

    retried = client.post(f"/problems/{problem_id}/executions/{execution['execution_id']}/retry")
    assert retried.status_code == 409
    assert retried.json()["detail"].startswith("approval_revision_mismatch")
    assert jira.calls == []


# ---------------------------------------------------------------------------
# A3 — the EFFECTIVE review status gates the push
# ---------------------------------------------------------------------------


def test_unstamped_execution_created_by_an_approval_is_still_gated(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CLARA_SEED_DEMO_DATA", "0")
    jira = _FakeJira(fail_calls={1})
    monkeypatch.setitem(DESTINATIONS, "jira", jira)
    problem_store = ProblemStore([])
    workflows = WorkflowStore()
    client = _client(problem_store, workflows)
    problem_id, action_id = _promote_checkout_problem(client)
    assert _decide(client, problem_id, action_id, "approved").status_code == 200
    [execution] = _executions(client, problem_id)
    assert execution["status"] == "push_failed"

    # A row written before the Art. 50 stamp existed: no stamp, but the
    # approval that created it is on record.
    index = next(i for i, e in enumerate(workflows._executions) if e.execution_id == execution["execution_id"])
    workflows._executions[index] = workflows._executions[index].model_copy(
        update={"human_reviewed": False, "reviewed_by": None, "reviewed_at": None}
    )

    assert problem_store.update_action_proposal(
        problem_id, action_id, ActionProposalUpdateRequest(proposal="Text nobody approved.")
    ) is not None
    retried = client.post(f"/problems/{problem_id}/executions/{execution['execution_id']}/retry")
    assert retried.status_code == 409, retried.text
    assert retried.json()["detail"].startswith("action_changed_since_approval")
    assert len(jira.calls) == 1

    assert _decide(client, problem_id, action_id, "rejected").status_code == 200
    retried = client.post(f"/problems/{problem_id}/executions/{execution['execution_id']}/retry")
    assert retried.status_code == 409, retried.text
    assert retried.json()["detail"].startswith("approval_revoked")
    assert len(jira.calls) == 1
    [row] = _executions(client, problem_id)
    assert row["status"] == "push_failed" and row["external_ref"] is None


def test_execution_without_any_approval_cannot_be_retried(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CLARA_SEED_DEMO_DATA", "0")
    jira = _FakeJira()
    monkeypatch.setitem(DESTINATIONS, "jira", jira)
    workflows = WorkflowStore()
    client = _client(ProblemStore([]), workflows)
    problem_id, action_id = _promote_checkout_problem(client)

    orphan = workflows.add_execution(
        ExecutionRecord(
            execution_id="EXE-XXXX",
            problem_id=problem_id,
            action_id=action_id,
            destination="jira",
            status=ExecutionStatus.push_failed,
            owner="payments",
            summary="graph push that failed",
            created_at=_iso(datetime.now(UTC)),
            detail="Jira returned 500",
        )
    )
    retried = client.post(f"/problems/{problem_id}/executions/{orphan.execution_id}/retry")
    assert retried.status_code == 409, retried.text
    assert retried.json()["detail"] == "Only approval-created executions can be retried"
    assert jira.calls == []
    assert workflows.list_executions()[0].status == ExecutionStatus.push_failed


# ---------------------------------------------------------------------------
# A4 — problem title/statement are frozen while an action is approved
# ---------------------------------------------------------------------------


def test_problem_title_and_statement_are_frozen_while_an_action_is_approved(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("CLARA_SEED_DEMO_DATA", "0")
    monkeypatch.setitem(DESTINATIONS, "jira", _FakeJira())
    client = _client()
    problem_id, action_id = _promote_checkout_problem(client)
    before = client.get(f"/problems/{problem_id}").json()
    assert _decide(client, problem_id, action_id, "approved").status_code == 200

    expected = "Problem title/statement are frozen while an action is approved; record a rejection first"
    for body in ({"title": "Renamed after approval"}, {"statement": "Rewritten after approval."}):
        refused = client.patch(f"/problems/{problem_id}", json=body)
        assert refused.status_code == 409, refused.text
        assert refused.json()["detail"] == expected
    after = client.get(f"/problems/{problem_id}").json()
    assert (after["title"], after["statement"]) == (before["title"], before["statement"])

    # Unrelated fields — and an unchanged title — still pass.
    allowed = client.patch(
        f"/problems/{problem_id}",
        json={"owner": "cx_operations", "root_cause_hypothesis": "Timeouts on the PSP call.", "title": before["title"]},
    )
    assert allowed.status_code == 200, allowed.text
    assert allowed.json()["owner"] == "cx_operations"
    assert allowed.json()["root_cause_hypothesis"] == "Timeouts on the PSP call."

    # Once the approval is revoked the text is editable again.
    assert _decide(client, problem_id, action_id, "rejected").status_code == 200
    renamed = client.patch(f"/problems/{problem_id}", json={"title": "Renamed after rejection"})
    assert renamed.status_code == 200, renamed.text
    assert renamed.json()["title"] == "Renamed after rejection"


# ---------------------------------------------------------------------------
# A5 — the audit detail names the resolved team route
# ---------------------------------------------------------------------------


def test_success_detail_names_the_resolved_team_route(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CLARA_SEED_DEMO_DATA", "0")
    jira = _FakeJira()
    monkeypatch.setitem(DESTINATIONS, "jira", jira)
    client = _client()
    problem_id, action_id = _promote_checkout_problem(client)
    owner = _action(client, problem_id, action_id)["owner"]
    settings = client.put(
        "/workspace",
        json={"owner_routes": [{"match": "payment", "owner": owner, "jira_project_key": "ELSEWHERE"}]},
    )
    assert settings.status_code == 200, settings.text

    assert _decide(client, problem_id, action_id, "approved").status_code == 200
    [execution] = _executions(client, problem_id)
    assert execution["status"] == "pushed"
    assert jira.calls[-1]["config"]["project_key"] == "ELSEWHERE"
    assert f"via team route '{owner}' → project ELSEWHERE" in execution["detail"]
    assert "authorized by DEC-0001" in execution["detail"]


# ---------------------------------------------------------------------------
# A6 — the check-then-act window
# ---------------------------------------------------------------------------


class _RejectingConfigStore(ConnectorConfigStore):
    """Config lookup that records a rejection on its way back — i.e. between
    the first authorisation check and the connector call."""

    def __init__(self) -> None:
        super().__init__()
        self.hook = None

    def get_config(self, connector_type: str):
        config = super().get_config(connector_type)
        if self.hook is not None:
            hook, self.hook = self.hook, None
            hook()
        return config


def test_rejection_between_the_first_check_and_the_push_refuses_the_write(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("CLARA_SEED_DEMO_DATA", "0")
    jira = _FakeJira(fail_calls={1})
    monkeypatch.setitem(DESTINATIONS, "jira", jira)
    problem_store = ProblemStore([])
    workflows = WorkflowStore()
    configs = _RejectingConfigStore()
    client = _client(problem_store, workflows, configs)
    problem_id, action_id = _promote_checkout_problem(client)
    assert _decide(client, problem_id, action_id, "approved").status_code == 200
    [execution] = _executions(client, problem_id)
    assert execution["status"] == "push_failed"

    def _reject_now() -> None:
        workflows.record_approval(
            problem=problem_store.get_problem(problem_id),
            decision=ApprovalDecision(action_id=action_id, decision="rejected", reviewer="late-reviewer"),
        )

    configs.hook = _reject_now
    retried = client.post(f"/problems/{problem_id}/executions/{execution['execution_id']}/retry")
    assert retried.status_code == 409, retried.text
    assert retried.json()["detail"].startswith("approval_revoked")
    assert "late-reviewer" in retried.json()["detail"]
    assert len(jira.calls) == 1  # no external record was created
    assert configs.hook is None  # the hook did fire, after the first check
    [row] = _executions(client, problem_id)
    assert row["status"] == "push_failed" and row["external_ref"] is None
    assert "Dispatch refused (approval_revoked)" in row["detail"]


def test_recheck_refuses_when_the_store_changes_between_calls(monkeypatch: pytest.MonkeyPatch) -> None:
    """The same window at unit level: list_approvals answers differently on
    the second read."""
    problem = next(p for p in load_seed_problems() if p.problem_id == "PRB-108")
    action = find_action(problem, "ACT-501")
    jira = _FakeJira()
    monkeypatch.setitem(DESTINATIONS, "jira", jira)
    store = WorkflowStore()
    execution = store.add_execution(
        ExecutionRecord(
            execution_id="EXE-XXXX",
            problem_id="PRB-108",
            action_id="ACT-501",
            destination="jira",
            status=ExecutionStatus.push_failed,
            owner="own",
            summary="sum",
            created_at="2026-07-01T00:00:00Z",
            human_reviewed=True,
        )
    )
    approved = ApprovalRecord(
        decision_id="DEC-0001", problem_id="PRB-108", action_id="ACT-501", decision="approved",
        reviewer="alice", created_at="2026-07-01T00:00:00Z", action_snapshot=action_snapshot(action), **_seed_outbound(),
        execution_id=execution.execution_id,
    )
    rejected = ApprovalRecord(
        decision_id="DEC-0002", problem_id="PRB-108", action_id="ACT-501", decision="rejected",
        reviewer="bob", created_at="2026-07-01T00:00:05Z",
    )
    store._approvals.append(approved)
    reads = {"count": 0}
    original = store.list_approvals

    def _changing_list_approvals():
        reads["count"] += 1
        if reads["count"] == 2:  # the re-check sees the late rejection
            store._approvals.append(rejected)
        return original()

    monkeypatch.setattr(store, "list_approvals", _changing_list_approvals)

    class _Configs:
        def get_config(self, connector_type):
            return type("Cfg", (), {"config": JIRA_CONFIG, "is_active": True})()

    with pytest.raises(DispatchNotAuthorized) as refused:
        push_approved_action(
            problem=problem, action=action, execution=execution, config_store=_Configs(), workflow_store=store
        )
    assert refused.value.reason == "approval_revoked"
    assert jira.calls == []
    assert store.list_executions()[0].status == ExecutionStatus.push_failed


# ---------------------------------------------------------------------------
# A7 — numeric decision ordering
# ---------------------------------------------------------------------------


def test_decisions_are_ordered_by_numeric_suffix_not_as_strings() -> None:
    from app.services.workflow import decision_order

    problem = next(p for p in load_seed_problems() if p.problem_id == "PRB-108")
    action = find_action(problem, "ACT-501")
    stamp = "2026-07-01T00:00:00+00:00"
    approved = ApprovalRecord(
        decision_id="DEC-9999", problem_id="PRB-108", action_id="ACT-501", decision="approved",
        reviewer="alice", created_at=stamp, action_snapshot=action_snapshot(action), **_seed_outbound(), execution_id="EXE-0001",
    )
    rejected = ApprovalRecord(
        decision_id="DEC-10000", problem_id="PRB-108", action_id="ACT-501", decision="rejected",
        reviewer="bob", created_at=stamp,
    )
    assert [a.decision_id for a in sorted([rejected, approved], key=decision_order)] == ["DEC-9999", "DEC-10000"]
    execution = ExecutionRecord(
        execution_id="EXE-0001", problem_id="PRB-108", action_id="ACT-501", destination="jira",
        status=ExecutionStatus.push_failed, owner="own", summary="sum", created_at=stamp, human_reviewed=True,
    )
    result = authorize_dispatch(
        problem=problem, action=action, execution=execution, approvals=[rejected, approved], four_eyes=False
    )
    assert result.reason == "approval_revoked"
    assert "DEC-10000" in result.detail


# --------------------------------------------------------------------------- #
# Third-pass probes: ordering under clock skew, fresh reads on the Postgres
# store, and the legacy clock on idempotent reuse.
# --------------------------------------------------------------------------- #


def test_a_later_rejection_with_an_earlier_clock_still_revokes() -> None:
    """A rejection appended after an approval revokes it even when its
    created_at sorts earlier (a worker clock behind, or a whole-second stamp
    that sorts after a fractional one). Append order wins, not the clock."""
    from app.domain.models import ActionProposalSnapshot, ApprovalDecisionStatus, ApprovalRecord
    from app.services.workflow import authorize_dispatch, decision_order, latest_decisions

    problem = ProblemStore(load_seed_problems()).get_problem("PRB-108")
    action = next(a for a in problem.action_proposals if a.action_id == "ACT-501")
    snapshot = ActionProposalSnapshot.model_validate(action.model_dump(by_alias=True))
    execution = ExecutionRecord(
        execution_id="EXE-0001", problem_id="PRB-108", action_id="ACT-501",
        destination=action.destination, status=ExecutionStatus.push_failed, owner=action.owner,
        summary="s", created_at="2026-07-01T00:00:05Z", human_reviewed=True,
    )
    approved = ApprovalRecord(
        decision_id="DEC-0001", problem_id="PRB-108", action_id="ACT-501",
        decision=ApprovalDecisionStatus.approved,
        reviewer="alice", created_at="2026-07-01T00:00:05Z", action_snapshot=snapshot, **_seed_outbound(),
        execution_id="EXE-0001",
    )
    for skewed_at in ("2026-07-01T00:00:03Z", "2026-07-01T00:00:05.500000Z"):
        rejected = approved.model_copy(update={
            "decision_id": "DEC-0002", "decision": ApprovalDecisionStatus.rejected, "created_at": skewed_at,
            "execution_id": None,
        })
        approvals = [rejected, approved]  # arrival order irrelevant: ids decide
        assert [a.decision_id for a in sorted(approvals, key=decision_order)] == ["DEC-0001", "DEC-0002"]
        assert latest_decisions(approvals, "PRB-108")["ACT-501"].decision_id == "DEC-0002"
        verdict = authorize_dispatch(
            problem=problem, action=action, execution=execution, approvals=approvals, four_eyes=False,
        )
        assert not verdict.authorized and verdict.reason == "approval_revoked", (skewed_at, verdict)


def test_postgres_store_refresh_forces_a_reload_inside_the_ttl() -> None:
    """The pre-dispatch checks call refresh(): on the Postgres store that must
    bypass the read cache, or a rejection recorded by another worker inside
    the TTL would be invisible to the re-check."""
    from app.services.postgres import PostgresWorkflowStore
    from app.services.workflow import WorkflowStore

    counter = {"loads": 0}

    class CountingConnection:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

        def execute(self, sql, *args, **kwargs):
            if "FROM clara_workflow_records" in str(sql):
                counter["loads"] += 1
            return self

        def fetchall(self):
            return []

    store = PostgresWorkflowStore.__new__(PostgresWorkflowStore)
    WorkflowStore.__init__(store)
    store._connect = lambda: CountingConnection()
    store.list_approvals()
    store.list_approvals()
    assert counter["loads"] == 1  # cached inside the TTL
    store.refresh()
    assert counter["loads"] == 2  # refresh() always reloads
    store.list_approvals()
    assert counter["loads"] == 2  # and the fresh snapshot is then reused
    assert WorkflowStore().refresh() is None


def test_same_run_reuse_of_a_legacy_record_anchors_on_its_created_at(monkeypatch: pytest.MonkeyPatch) -> None:
    """A reused external record whose execution predates the dispatched_at
    stamp still gives the new execution a real dispatch instant (the legacy
    row's created_at: the push happened inside that approval request)."""
    jira = _FakeJira()
    monkeypatch.setitem(DESTINATIONS, "jira", jira)
    store = WorkflowStore()
    client = _client(workflows=store)
    problem_id, action_id = _promote_checkout_problem(client)
    assert _decide(client, problem_id, action_id, "approved", reviewer="alice").status_code == 200
    exe1 = _executions(client, problem_id)[0]
    assert exe1["status"] == "pushed" and exe1["external_ref"]
    # Simulate a row pushed before the stamp existed.
    store._executions = [
        record.model_copy(update={"dispatched_at": None}) if record.execution_id == exe1["execution_id"] else record
        for record in store._executions
    ]
    assert client.put("/workspace", json={"four_eyes_approval": True}).status_code == 200
    assert _decide(client, problem_id, action_id, "approved", reviewer="bob").status_code == 200
    exe2 = next(e for e in _executions(client, problem_id) if e["execution_id"] != exe1["execution_id"])
    assert exe2["status"] == "pushed" and exe2["external_ref"] == exe1["external_ref"]
    assert exe2["dispatched_at"] == exe1["created_at"]
    assert len(jira.calls) == 1  # the record was reused, not re-created
