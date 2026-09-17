"""Dispatch is bound to the reviewed outbound content (13 September 2026 review,
finding F1). Each test states the DESIRED invariant:

  - the connector never receives a title, statement, severity or evidence
    list that no approval record signed: an approval freezes the outbound
    content (`outbound_snapshot`, SHA-256) and dispatch sends exactly that
    content, or refuses with `problem_changed_since_approval` and no
    connector call when the problem drifted (however that drift happened);
  - a governed edit and an approval of the same problem are serialised: an
    edit whose check passed cannot be persisted after the approval;
  - a reviewer can bind a decision to the content hash the UI displayed
    (`expected_outbound_sha256`): a stale hash is refused, nothing recorded;
  - four-eyes reviewers must have signed the same outbound content;
  - approvals recorded before the binding existed cannot dispatch (fail
    closed, fresh approval) but still cover the implementation attestation;
  - a dispatch claim is a store-level compare-and-set: a live claim held by
    another worker refuses the retry without a connector call, an expired
    claim is taken over, and the claim is cleared when the attempt ends;
  - a decision recorded while the connector was writing is annotated on the
    execution and emitted as telemetry (the record cannot be recalled).
"""

from __future__ import annotations

import tempfile
import threading
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.connectors import DESTINATIONS
from app.connectors.config_store import ConnectorConfigStore
from app.domain.models import (
    ApprovalDecision,
    ExecutionStatus,
    ProblemUpdateRequest,
)
from app.main import create_app
from app.services.action_push import _build_push_payload
from app.services.contexts import CustomerContextStore
from app.services.measurement_scheduler import SQLiteMeasurementPlanStore
from app.services.outbound import build_outbound_content, outbound_sha256
from app.services.problems import ProblemStore, SQLiteProblemStore
from app.services.seed import load_seed_problems
from app.services.signals import SignalStore
from app.services.telemetry import SQLiteTelemetryStore
from app.services.workflow import (
    DISPATCH_CLAIM_TTL_SECONDS,
    SQLiteWorkflowStore,
    WorkflowStore,
    action_snapshot,
    authorize_dispatch,
    find_action,
)
from app.services.workspace import SQLiteWorkspaceStore
from app.tests.test_dispatch_authorization_gaps import (
    _decide,
    _events,
    _executions,
    _FakeJira,
    _promote_checkout_problem,
)


def _iso(moment: datetime) -> str:
    return moment.isoformat().replace("+00:00", "Z")


def _stores(kind: str):
    scratch = Path(tempfile.mkdtemp(prefix=f"clara-binding-{kind}-"))
    if kind == "sqlite":
        return SQLiteProblemStore(scratch / "problems.db", []), SQLiteWorkflowStore(scratch / "wf.db"), scratch
    return ProblemStore([]), WorkflowStore(), scratch


def _client(problem_store, workflows, scratch: Path) -> TestClient:
    return TestClient(
        create_app(
            problem_store=problem_store,
            workflows=workflows,
            signals=SignalStore(),
            contexts=CustomerContextStore(),
            connector_configs=ConnectorConfigStore(),
            telemetry=SQLiteTelemetryStore(scratch / "telemetry.db"),
            measurement_plans=SQLiteMeasurementPlanStore(scratch / "plans.db"),
            workspace=SQLiteWorkspaceStore(scratch / "workspace.db"),
        )
    )


def _rename_behind_the_api(problem_store, problem_id: str, title: str) -> None:
    """The race outcome (or a direct database edit): the title changes
    without the route's guard ever running."""
    assert problem_store.update_problem(problem_id, ProblemUpdateRequest(title=title)) is not None


def _approvals(client: TestClient, problem_id: str) -> list[dict]:
    return [a for a in client.get("/approvals").json() if a["problem_id"] == problem_id]


# ---------------------------------------------------------------------------
# The approval freezes the content; dispatch sends it or refuses on drift
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("kind", ["memory", "sqlite"])
def test_title_changed_behind_the_api_after_approval_refuses_the_retry(
    monkeypatch: pytest.MonkeyPatch, kind: str
) -> None:
    monkeypatch.setenv("CLARA_SEED_DEMO_DATA", "0")
    jira = _FakeJira(fail_calls={1})
    monkeypatch.setitem(DESTINATIONS, "jira", jira)
    problem_store, workflows, scratch = _stores(kind)
    client = _client(problem_store, workflows, scratch)
    problem_id, action_id = _promote_checkout_problem(client)
    original_title = client.get(f"/problems/{problem_id}").json()["title"]

    assert _decide(client, problem_id, action_id, "approved").status_code == 200
    [approval] = _approvals(client, problem_id)
    assert approval["outbound_snapshot"]["insight_title"] == original_title
    assert approval["outbound_snapshot"]["title"] == f"{original_title} [structural]"
    assert len(approval["outbound_sha256"]) == 64
    [execution] = _executions(client, problem_id)
    assert execution["status"] == "push_failed"

    _rename_behind_the_api(problem_store, problem_id, "UNREVIEWED replacement title")
    retried = client.post(f"/problems/{problem_id}/executions/{execution['execution_id']}/retry")
    assert retried.status_code == 409, retried.text
    assert retried.json()["detail"].startswith("problem_changed_since_approval")
    assert "title" in retried.json()["detail"] and "insight_title" in retried.json()["detail"]
    assert len(jira.calls) == 1  # the failed first push only; nothing unreviewed left CLARA
    assert all("UNREVIEWED" not in call["action"]["title"] for call in jira.calls)
    [row] = _executions(client, problem_id)
    assert row["status"] == "push_failed" and row["external_ref"] is None
    assert "problem_changed_since_approval" in row["detail"]
    assert row["dispatch_claimed_at"] is None  # the refused attempt released its claim
    [refused] = _events(client, "action_push_refused")
    assert refused["metadata"]["reason"] == "problem_changed_since_approval"

    # Rejection, re-approval of the current text: the new approval signs the
    # new title and the retry of the NEW execution sends exactly it.
    assert _decide(client, problem_id, action_id, "rejected").status_code == 200
    assert _decide(client, problem_id, action_id, "approved").status_code == 200
    latest = _approvals(client, problem_id)[-1]
    assert latest["outbound_snapshot"]["insight_title"] == "UNREVIEWED replacement title"
    pushed = next(e for e in _executions(client, problem_id) if e["status"] == "pushed")
    assert jira.calls[-1]["action"]["title"] == latest["outbound_snapshot"]["title"]
    assert jira.calls[-1]["action"]["insight_summary"] == latest["outbound_snapshot"]["insight_summary"]
    assert pushed["dispatch_claimed_at"] is None


@pytest.mark.parametrize("kind", ["memory", "sqlite"])
def test_edit_and_approval_of_one_problem_are_serialised(monkeypatch: pytest.MonkeyPatch, kind: str) -> None:
    """The 13 Sep race: a title PATCH that passed the approval check is paused
    before its write; an approval must not be recorded in that window. Under
    the governance lock the approval waits, and whichever order results, the
    connector only ever receives a title an approval record signed."""
    monkeypatch.setenv("CLARA_SEED_DEMO_DATA", "0")
    jira = _FakeJira(fail_calls={1})
    monkeypatch.setitem(DESTINATIONS, "jira", jira)
    problem_store, workflows, scratch = _stores(kind)
    client = _client(problem_store, workflows, scratch)
    problem_id, action_id = _promote_checkout_problem(client)

    entered, gate = threading.Event(), threading.Event()
    original_update = problem_store.update_problem

    def paused_update(pid, update, *, guard=None):
        # The store-level guard runs first (the route's check passed too);
        # the write itself is delayed while the approval request arrives.
        if guard is not None:
            guard()
        entered.set()
        assert gate.wait(timeout=10)
        return original_update(pid, update, guard=None)

    monkeypatch.setattr(problem_store, "update_problem", paused_update)
    results: dict[str, object] = {}

    def patch() -> None:
        results["patch"] = client.patch(f"/problems/{problem_id}", json={"title": "Edited before approval"})

    def approve() -> None:
        results["approve"] = _decide(client, problem_id, action_id, "approved")

    patcher = threading.Thread(target=patch)
    patcher.start()
    assert entered.wait(5)
    approver = threading.Thread(target=approve)
    approver.start()
    time.sleep(0.5)
    assert approver.is_alive()  # blocked on the problem lock while the edit is in flight
    assert _approvals(client, problem_id) == []
    gate.set()
    patcher.join(10)
    approver.join(10)
    assert results["patch"].status_code == 200, results["patch"].text  # type: ignore[union-attr]
    assert results["approve"].status_code == 200, results["approve"].text  # type: ignore[union-attr]

    [approval] = _approvals(client, problem_id)
    assert approval["outbound_snapshot"]["insight_title"] == "Edited before approval"
    [execution] = _executions(client, problem_id)
    assert execution["status"] == "push_failed"
    retried = client.post(f"/problems/{problem_id}/executions/{execution['execution_id']}/retry")
    assert retried.status_code == 200, retried.text
    assert jira.calls[-1]["action"]["title"] == approval["outbound_snapshot"]["title"]
    assert jira.calls[-1]["action"]["insight_title"] == "Edited before approval"
    # Once approved, the title is frozen again.
    assert client.patch(f"/problems/{problem_id}", json={"title": "Edited after approval"}).status_code == 409


def test_frozen_content_is_what_dispatch_sends(monkeypatch: pytest.MonkeyPatch) -> None:
    """Unit level: the payload comes from the authorisation's frozen content,
    not from the problem object handed to the push."""
    problem = next(p for p in load_seed_problems() if p.problem_id == "PRB-108")
    action = find_action(problem, "ACT-501")
    frozen = build_outbound_content(problem, action)
    renamed = problem.model_copy(update={"title": "Renamed later", "statement": "Rewritten later."})
    from app.services.workflow import DispatchAuthorization

    authorization = DispatchAuthorization(authorized=True, reason=None, detail="ok", outbound=frozen)
    payload = _build_push_payload(renamed, action, authorization=authorization)
    assert payload["title"] == frozen.title and payload["insight_title"] == problem.title
    assert payload["insight_summary"] == problem.statement
    # Ungated executions (no approval to bind to) are built from the current objects.
    unbound = _build_push_payload(renamed, action, authorization=None)
    assert unbound["insight_title"] == "Renamed later"
    # The disclosure line is appended at dispatch, outside the frozen content.
    disclosed = _build_push_payload(renamed, action, authorization=authorization, disclosure="AI-drafted.")
    assert disclosed["description"].endswith("\n\nAI-drafted.") and frozen.description == action.proposal


# ---------------------------------------------------------------------------
# Approve what you saw: the expected-hash binding and the preview endpoint
# ---------------------------------------------------------------------------


def test_stale_expected_hash_refuses_the_decision_and_records_nothing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CLARA_SEED_DEMO_DATA", "0")
    monkeypatch.setitem(DESTINATIONS, "jira", _FakeJira(fail_calls=set()))
    problem_store, workflows, scratch = _stores("memory")
    client = _client(problem_store, workflows, scratch)
    problem_id, action_id = _promote_checkout_problem(client)

    preview = client.get(f"/problems/{problem_id}/actions/{action_id}/outbound-preview")
    assert preview.status_code == 200, preview.text
    shown = preview.json()
    assert shown["content"]["insight_title"] == client.get(f"/problems/{problem_id}").json()["title"]
    assert shown["sha256"] == outbound_sha256(
        build_outbound_content(problem_store.get_problem(problem_id), find_action(problem_store.get_problem(problem_id), action_id))
    )
    assert client.get(f"/problems/{problem_id}/actions/ACT-NOPE/outbound-preview").status_code == 404

    assert client.patch(f"/problems/{problem_id}", json={"title": "Changed while the reviewer read"}).status_code == 200
    stale = client.post(
        f"/problems/{problem_id}/approvals",
        json={"action_id": action_id, "decision": "approved", "reviewer": "r", "accept_proposed_contract": False, "expected_outbound_sha256": shown["sha256"]},
    )
    assert stale.status_code == 409, stale.text
    assert "changed since it was displayed" in stale.json()["detail"]
    assert _approvals(client, problem_id) == [] and _executions(client, problem_id) == []

    fresh = client.get(f"/problems/{problem_id}/actions/{action_id}/outbound-preview").json()
    assert fresh["sha256"] != shown["sha256"]
    signed = client.post(
        f"/problems/{problem_id}/approvals",
        json={"action_id": action_id, "decision": "approved", "reviewer": "r", "accept_proposed_contract": False, "expected_outbound_sha256": fresh["sha256"]},
    )
    assert signed.status_code == 200, signed.text
    assert signed.json()["outbound_sha256"] == fresh["sha256"]
    assert signed.json()["outbound_snapshot"]["insight_title"] == "Changed while the reviewer read"


# ---------------------------------------------------------------------------
# Four-eyes: both reviewers signed the same outbound content
# ---------------------------------------------------------------------------


def test_four_eyes_reviewers_must_have_signed_the_same_outbound_content(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CLARA_SEED_DEMO_DATA", "0")
    jira = _FakeJira(fail_calls=set())
    monkeypatch.setitem(DESTINATIONS, "jira", jira)
    problem_store, workflows, scratch = _stores("memory")
    client = _client(problem_store, workflows, scratch)
    assert client.put("/workspace", json={"four_eyes_approval": True}).status_code == 200
    problem_id, action_id = _promote_checkout_problem(client)

    assert _decide(client, problem_id, action_id, "approved", reviewer="alice").status_code == 200
    _rename_behind_the_api(problem_store, problem_id, "Title bob saw, alice did not")
    assert _decide(client, problem_id, action_id, "approved", reviewer="bob").status_code == 200
    alice, bob = _approvals(client, problem_id)
    assert alice["outbound_sha256"] != bob["outbound_sha256"]
    assert jira.calls == []
    [execution] = _executions(client, problem_id)
    assert execution["status"] == "push_failed"
    assert execution["detail"].startswith("Dispatch refused (approval_revision_mismatch)")
    assert "insight_title" in execution["detail"]


# ---------------------------------------------------------------------------
# Approvals recorded before the binding existed
# ---------------------------------------------------------------------------


def test_pre_binding_approval_cannot_dispatch_but_covers_the_attestation() -> None:
    from app.domain.models import ApprovalRecord, ExecutionRecord

    problem = next(p for p in load_seed_problems() if p.problem_id == "PRB-108")
    action = find_action(problem, "ACT-501")
    execution = ExecutionRecord(
        execution_id="EXE-0001", problem_id="PRB-108", action_id="ACT-501", destination="jira",
        status=ExecutionStatus.push_failed, owner="own", summary="sum",
        created_at="2026-07-01T00:00:00Z", human_reviewed=True,
    )
    legacy = ApprovalRecord(
        decision_id="DEC-0001", problem_id="PRB-108", action_id="ACT-501", decision="approved",
        reviewer="alice", created_at="2026-07-01T00:00:00Z", action_snapshot=action_snapshot(action),
        execution_id="EXE-0001",
    )
    refused = authorize_dispatch(problem=problem, action=action, execution=execution, approvals=[legacy], four_eyes=False)
    assert refused.reason == "approval_unverifiable" and "outbound-content" in refused.detail
    attest = authorize_dispatch(
        problem=problem, action=action, execution=execution, approvals=[legacy], four_eyes=False, outbound_binding=False
    )
    assert attest.authorized is True and attest.outbound is None
    # A four-eyes run whose FIRST approval predates the binding is refused too.
    bound = legacy.model_copy(
        update={
            "decision_id": "DEC-0002", "reviewer": "bob", "created_at": "2026-07-01T00:00:01Z",
            "outbound_snapshot": build_outbound_content(problem, action),
            "outbound_sha256": outbound_sha256(build_outbound_content(problem, action)),
        }
    )
    mixed = authorize_dispatch(problem=problem, action=action, execution=execution, approvals=[legacy, bound], four_eyes=True)
    assert mixed.reason == "approval_unverifiable" and "DEC-0001" in mixed.detail


@pytest.mark.parametrize("kind", ["memory", "sqlite"])
def test_stores_persist_the_outbound_snapshot(kind: str) -> None:
    problem = next(p for p in load_seed_problems() if p.problem_id == "PRB-108")
    _, workflows, scratch = _stores(kind)
    record = workflows.record_approval(
        problem=problem,
        decision=ApprovalDecision(action_id="ACT-501", decision="approved", reviewer="alice"),
    )
    expected = build_outbound_content(problem, find_action(problem, "ACT-501"))
    assert record.outbound_snapshot == expected
    assert record.outbound_sha256 == outbound_sha256(expected)
    reloaded = (SQLiteWorkflowStore(scratch / "wf.db") if kind == "sqlite" else workflows).list_approvals()[0]
    assert reloaded.outbound_snapshot == expected and reloaded.outbound_sha256 == record.outbound_sha256


# ---------------------------------------------------------------------------
# Dispatch claims
# ---------------------------------------------------------------------------


def _set_claim(workflows, execution_id: str, *, at: str, by: str) -> None:
    if isinstance(workflows, SQLiteWorkflowStore):
        workflows._connection.execute(
            "UPDATE executions SET dispatch_claimed_at = ?, dispatch_claimed_by = ? WHERE id = ?",
            (at, by, int(execution_id.removeprefix("EXE-"))),
        )
        workflows._connection.commit()
        return
    index = next(i for i, e in enumerate(workflows._executions) if e.execution_id == execution_id)
    workflows._executions[index] = workflows._executions[index].model_copy(
        update={"dispatch_claimed_at": at, "dispatch_claimed_by": by}
    )


@pytest.mark.parametrize("kind", ["memory", "sqlite"])
def test_live_claim_of_another_worker_refuses_the_retry_and_an_expired_one_is_taken_over(
    monkeypatch: pytest.MonkeyPatch, kind: str
) -> None:
    monkeypatch.setenv("CLARA_SEED_DEMO_DATA", "0")
    jira = _FakeJira(fail_calls={1})
    monkeypatch.setitem(DESTINATIONS, "jira", jira)
    problem_store, workflows, scratch = _stores(kind)
    client = _client(problem_store, workflows, scratch)
    problem_id, action_id = _promote_checkout_problem(client)
    assert _decide(client, problem_id, action_id, "approved").status_code == 200
    [execution] = _executions(client, problem_id)
    assert execution["status"] == "push_failed" and execution["dispatch_claimed_at"] is None

    now = datetime.now(UTC)
    _set_claim(workflows, execution["execution_id"], at=_iso(now - timedelta(seconds=5)), by="other-host:99")
    refused = client.post(f"/problems/{problem_id}/executions/{execution['execution_id']}/retry")
    assert refused.status_code == 409, refused.text
    assert refused.json()["detail"].startswith("dispatch_in_progress")
    assert "other-host:99" in refused.json()["detail"]
    assert len(jira.calls) == 1
    [row] = _executions(client, problem_id)
    assert row["dispatch_claimed_by"] == "other-host:99"  # a foreign live claim is left alone

    _set_claim(
        workflows, execution["execution_id"],
        at=_iso(now - timedelta(seconds=DISPATCH_CLAIM_TTL_SECONDS + 1)), by="other-host:99",
    )
    taken_over = client.post(f"/problems/{problem_id}/executions/{execution['execution_id']}/retry")
    assert taken_over.status_code == 200, taken_over.text
    assert taken_over.json()["status"] == "pushed"
    assert taken_over.json()["dispatch_claimed_at"] is None  # cleared by the status write
    assert len(jira.calls) == 2

    # A pushed execution is not claimable at all.
    assert workflows.claim_dispatch(execution["execution_id"], worker="me") is None


def test_claim_is_a_compare_and_set_on_the_store() -> None:
    from app.domain.models import ExecutionRecord

    workflows = WorkflowStore()
    execution = workflows.add_execution(
        ExecutionRecord(
            execution_id="EXE-X", problem_id="PRB-108", action_id="ACT-501", destination="jira",
            status=ExecutionStatus.push_failed, owner="own", summary="sum", created_at="2026-07-01T00:00:00Z",
        )
    )
    first = workflows.claim_dispatch(execution.execution_id, worker="w1", now="2026-07-01T00:00:10Z")
    assert first is not None and first.dispatch_claimed_by == "w1"
    assert workflows.claim_dispatch(execution.execution_id, worker="w2", now="2026-07-01T00:00:20Z") is None
    workflows.release_dispatch(execution.execution_id)
    second = workflows.claim_dispatch(execution.execution_id, worker="w2", now="2026-07-01T00:00:30Z")
    assert second is not None and second.dispatch_claimed_by == "w2"
    assert workflows.claim_dispatch("EXE-NOPE", worker="w3") is None


# ---------------------------------------------------------------------------
# A decision recorded while the connector was writing
# ---------------------------------------------------------------------------


def test_rejection_recorded_during_the_connector_call_is_annotated_and_reported(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("CLARA_SEED_DEMO_DATA", "0")
    problem_store, workflows, scratch = _stores("memory")
    client = _client(problem_store, workflows, scratch)
    problem_id, action_id = _promote_checkout_problem(client)

    class _RejectingJira(_FakeJira):
        def push(self, action, config):
            result = super().push(action, config)
            # The rejection lands while the ticket is being created.
            workflows.record_approval(
                problem=problem_store.get_problem(problem_id),
                decision=ApprovalDecision(action_id=action_id, decision="rejected", reviewer="late"),
            )
            return result

    jira = _RejectingJira(fail_calls=set())
    monkeypatch.setitem(DESTINATIONS, "jira", jira)
    assert _decide(client, problem_id, action_id, "approved").status_code == 200
    [execution] = _executions(client, problem_id)
    assert execution["status"] == "pushed" and execution["external_ref"] == "PAY-1"
    assert "WARNING: approval_revoked recorded during dispatch" in execution["detail"]
    assert "needs manual withdrawal" in execution["detail"]
    [event] = _events(client, "action_pushed_during_revocation")
    assert event["entity_id"] == execution["execution_id"]
    assert event["metadata"]["reason"] == "approval_revoked"
    assert event["metadata"]["external_ref"] == "PAY-1"
    # The latest decision is the rejection: no further dispatch is possible.
    assert _approvals(client, problem_id)[-1]["decision"] == "rejected"
