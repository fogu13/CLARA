"""Measurement semantics — the gaps a second independent probe found after C2-C4
landed (spec B1-B14). Each test states the DESIRED invariant:

  B1  client-supplied provenance on POST /outcomes is dropped: the store stamps
      the problem's contract, a forged snapshot cannot re-score the reading;
  B2  the evidence grade follows the method the reading was taken under;
  B3  a certified reading keeps the clock it was taken on, whatever anchor a
      later implementation record creates;
  B4  dispatched_at is never invented on a non-dispatch update; a legacy
      pushed row anchors on created_at;
  B5  implementation records supersede EVERY live plan, require an authorised
      execution, and cannot precede the dispatch;
  B6  a real push after a draft-only approval moves the clock to dispatch;
  B7  a window amendment does not rewrite what the follow-up reads;
  B8  learning conclusions score under the measured baseline;
  B9  the amended flag tracks scoring terms; revision falls back to the snapshot;
  B10 the approval-path auto-proposal is audited as contract_amended;
  B11 a note-only PATCH is a 422;
  B12 stamp_contract_provenance keeps snapshot and revision consistent;
  B13 a 0/0/0 reading counts as a measurement in the PATCH guard;
  B14 the outcomes CSV carries measurement_source, checkpoint_kind, loop_verdict.
"""

from __future__ import annotations

import csv
import io
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.connectors import DESTINATIONS
from app.connectors.config_store import ConnectorConfig, ConnectorConfigStore
from app.domain.models import (
    ExecutionRecord,
    ExecutionStatus,
    OutcomeMeasurement,
    SignalRecord,
)
from app.main import create_app
from app.services.measurement_scheduler import (
    SQLiteMeasurementPlanStore,
    followup_window_start,
    schedule_measurements,
)
from app.services.outcome_engine import intervention_anchor
from app.services.problems import ProblemStore
from app.services.seed import load_seed_problems
from app.services.signals import SQLiteSignalStore, build_candidates, promote_candidate
from app.services.telemetry import SQLiteTelemetryStore
from app.services.workflow import (
    SQLiteWorkflowStore,
    WorkflowStore,
    build_outcome_snapshot,
    stamp_contract_provenance,
)

NOW = datetime.now(UTC).replace(microsecond=0)
JIRA_CONFIG = ConnectorConfig(
    connector_type="jira",
    config={
        "base_url": "https://clara-demo.atlassian.net",
        "email": "bot@clara.eu",
        "api_token": "secret",
        "project_key": "CLARA",
    },
    is_active=True,
)


def _iso(moment: datetime) -> str:
    return moment.isoformat().replace("+00:00", "Z")


def _parse(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


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


# 10 signals over the 5 days before "now" -> promoted baseline ~2/day, target ~1/day.
PRE_SIGNALS = [_signal(f"pre-{i}", days_ago=5 - i * 0.5) for i in range(10)]


def _draft_problem(**contract_overrides: Any):
    problem = promote_candidate(build_candidates(PRE_SIGNALS)[0])
    if contract_overrides:
        problem = problem.model_copy(
            update={"outcome_contract": problem.outcome_contract.model_copy(update=contract_overrides)}
        )
    return problem


def _amendable_problem():
    return _draft_problem(
        baseline=100.0,
        success_threshold=50.0,
        comparison_method="its_segmented_regression",
    )


class _FakeJira:
    connector_type = "jira"

    def __init__(self) -> None:
        self.calls = 0

    def push(self, action, config):
        self.calls += 1
        return {"external_id": f"CLARA-{self.calls}", "status": "pushed", "audit": {}}


def _app(tmp_path: Path, *, problem=None, connectors: list[ConnectorConfig] | None = None, sqlite_workflows: bool = False):
    problem = problem or _draft_problem()
    signal_store = SQLiteSignalStore(tmp_path / "signals.db")
    signal_store.import_signals(PRE_SIGNALS)
    plan_store = SQLiteMeasurementPlanStore(tmp_path / "plans.db")
    telemetry = SQLiteTelemetryStore(tmp_path / "telemetry.db")
    workflows = SQLiteWorkflowStore(tmp_path / "wf.db") if sqlite_workflows else WorkflowStore()
    problems = ProblemStore(load_seed_problems())
    problems.upsert_problem(problem)  # a DRAFT: contract edits are allowed
    client = TestClient(
        create_app(
            problem_store=problems,
            workflows=workflows,
            signals=signal_store,
            connector_configs=ConnectorConfigStore(connectors or []),
            telemetry=telemetry,
            measurement_plans=plan_store,
        )
    )
    return {
        "client": client,
        "problem": problem,
        "problems": problems,
        "signals": signal_store,
        "plans": plan_store,
        "telemetry": telemetry,
        "workflows": workflows,
    }


def _action(problem, destination: str):
    return next(action for action in problem.action_proposals if action.destination == destination)


def _approve(client: TestClient, problem, destination: str = "jira") -> dict:
    response = client.post(
        f"/problems/{problem.problem_id}/approvals",
        json={
            "action_id": _action(problem, destination).action_id,
            "decision": "approved",
            "reviewer": "tester",
            "accept_proposed_contract": False,
        },
    )
    assert response.status_code == 200, response.text
    return response.json()


def _execution(client: TestClient, problem_id: str, execution_id: str | None = None) -> dict:
    return next(
        e
        for e in client.get("/executions").json()
        if e["problem_id"] == problem_id and (execution_id is None or e["execution_id"] == execution_id)
    )


def _plans(store: SQLiteMeasurementPlanStore, problem_id: str) -> list[dict]:
    return [plan for plan in store.list_plans() if plan["problem_id"] == problem_id]


def _events(telemetry: SQLiteTelemetryStore, event_type: str) -> list[dict]:
    """Matching events, oldest first (the store lists newest first)."""
    return sorted((e for e in telemetry.list_events() if e["event_type"] == event_type), key=lambda e: e["id"])


def _record_manual(client: TestClient, problem, value: float, **extra) -> dict:
    response = client.post(
        f"/problems/{problem.problem_id}/outcomes",
        json={
            "problem_id": problem.problem_id,
            "metric": problem.outcome_contract.primary_metric,
            "observed_value": value,
            "measured_at": _iso(NOW - timedelta(hours=1)),
            **extra,
        },
    )
    assert response.status_code == 200, response.text
    return response.json()


def _implement(client: TestClient, problem_id: str, execution_id: str, at: str):
    return client.post(
        f"/problems/{problem_id}/executions/{execution_id}/implementation",
        json={"implemented_at": at, "note": "Fix deployed."},
    )


# ---------------------------------------------------------------------------
# B1 — client-supplied provenance is dropped
# ---------------------------------------------------------------------------


def test_forged_snapshot_on_a_manual_reading_cannot_rescore_it(tmp_path: Path) -> None:
    app = _app(tmp_path, problem=_amendable_problem(), sqlite_workflows=True)
    client, problem = app["client"], app["problem"]
    forged = problem.outcome_contract.model_copy(update={"success_threshold": 90.0, "revision": 7})
    recorded = _record_manual(
        client,
        problem,
        80.0,
        measurement_source="instrumented",
        contract_snapshot=forged.model_dump(),
        contract_revision=7,
        checkpoint_kind="window",
        plan_id=3,
        execution_id="EXE-0009",
        clock_origin="dispatch",
        clock_origin_at=_iso(NOW - timedelta(days=40)),
    )
    assert recorded["measurement_source"] == "manual"
    assert recorded["contract_revision"] == 1
    assert recorded["contract_snapshot"]["success_threshold"] == 50.0
    assert recorded["checkpoint_kind"] is None and recorded["plan_id"] is None
    assert recorded["execution_id"] is None
    assert recorded["clock_origin"] is None and recorded["clock_origin_at"] is None

    stored = app["workflows"].latest_outcome(problem.problem_id)
    assert stored.contract_snapshot == problem.outcome_contract
    assert stored.contract_revision == 1
    assert stored.checkpoint_kind is None and stored.plan_id is None and stored.execution_id is None

    snapshot = client.get(f"/problems/{problem.problem_id}/outcome").json()
    assert snapshot["status"] == "improving"  # 80 vs the REAL threshold 50, not the forged 90
    assert snapshot["loop_verdict"] == "on_track"
    assert snapshot["measured_under_revision"] == 1
    board = next(i for i in client.get("/outcome-board").json()["items"] if i["problem_id"] == problem.problem_id)
    assert board["outcome_status"] == "improving"
    assert board["loop_verdict"] == "on_track"


# ---------------------------------------------------------------------------
# B2 — the grade follows the measured method
# ---------------------------------------------------------------------------


def test_evidence_grade_stays_with_the_method_the_reading_was_taken_under(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    app = _app(tmp_path)  # promotion default: pre_post_signal_rate
    client, problem, plans = app["client"], app["problem"], app["plans"]
    pid = problem.problem_id
    schedule_measurements(plans, problem=problem, execution_id="EXE-0001", executed_at=_iso(NOW - timedelta(days=40)), origin="dispatch")
    assert client.post("/measurements/run-due", json={"now": _iso(NOW - timedelta(hours=1))}).json()["measured"] == 2
    before = client.get(f"/problems/{pid}/outcome").json()
    assert before["measurement_source"] == "instrumented"
    assert before["evidence_grade"] == "D"
    assert before["measured_comparison_method"] == "pre_post_signal_rate"

    # Whatever the read-time ITS realises, the reading was a before/after.
    import app.routers.problems as problems_router

    monkeypatch.setattr(
        problems_router,
        "its_outcome_for_problem",
        lambda *args, **kwargs: {"method": "its", "effect": -1.0, "ci_low": -2.0, "ci_high": 0.0},
    )
    upgraded = client.patch(f"/problems/{pid}/outcome-contract", json={"comparison_method": "its_segmented_regression"})
    assert upgraded.status_code == 200, upgraded.text
    after = client.get(f"/problems/{pid}/outcome").json()
    assert after["comparison_method"] == "its_segmented_regression"
    assert after["measured_comparison_method"] == "pre_post_signal_rate"
    assert after["evidence_grade"] == "D"
    board = next(i for i in client.get("/outcome-board").json()["items"] if i["problem_id"] == pid)
    assert board["evidence_grade"] == "D"
    assert board["comparison_method"] == "its_segmented_regression"


# ---------------------------------------------------------------------------
# B3 — a certified reading keeps the clock it was taken on
# ---------------------------------------------------------------------------


def test_certified_reading_keeps_its_clock_after_a_later_implementation(tmp_path: Path) -> None:
    app = _app(tmp_path, sqlite_workflows=True)  # no connector -> approval clock
    client, problem, plans, workflows = app["client"], app["problem"], app["plans"], app["workflows"]
    pid = problem.problem_id
    _approve(client, problem)
    execution = _execution(client, pid)
    executed = _parse(_plans(plans, pid)[0]["executed_at"])
    at_window = _iso(executed + timedelta(days=problem.outcome_contract.measurement_window_days, hours=1))
    assert client.post("/measurements/run-due", json={"now": at_window}).json()["loop_closed"] == 1
    recorded = workflows.latest_outcome(pid)
    assert recorded.clock_origin == "approval"
    assert recorded.clock_origin_at == execution["created_at"]
    certified = client.get(f"/problems/{pid}/outcome").json()
    assert certified["loop_verdict"] == "loop_closed"
    assert "clock from approval" in certified["loop_note"]

    implemented_at = _iso(_parse(execution["created_at"]) + timedelta(minutes=2))
    assert _implement(client, pid, execution["execution_id"], implemented_at).status_code == 200

    after = client.get(f"/problems/{pid}/outcome").json()
    assert after["loop_verdict"] == "loop_closed"
    assert "clock from approval" in after["loop_note"]
    assert "may predate the fix" in after["loop_note"]
    assert "clock from implementation" not in after["loop_note"]
    assert after["measurement_origin"] == "approval"
    assert after["measurement_origin_at"] == execution["created_at"]
    # The reading persisted its clock across a reopen too.
    reopened = SQLiteWorkflowStore(tmp_path / "wf.db").latest_outcome(pid)
    assert (reopened.clock_origin, reopened.clock_origin_at) == ("approval", execution["created_at"])


def test_manual_and_legacy_readings_fall_back_to_the_intervention_anchor(tmp_path: Path) -> None:
    app = _app(tmp_path)
    client, problem = app["client"], app["problem"]
    _approve(client, problem)
    execution = _execution(client, problem.problem_id)
    recorded = _record_manual(client, problem, 0.0)
    assert recorded["clock_origin"] is None
    snapshot = client.get(f"/problems/{problem.problem_id}/outcome").json()
    assert snapshot["measurement_origin"] == "approval"
    assert snapshot["measurement_origin_at"] == execution["created_at"]


# ---------------------------------------------------------------------------
# B4 — dispatched_at is never invented
# ---------------------------------------------------------------------------


def test_implementation_on_a_legacy_pushed_row_leaves_dispatched_at_none(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setitem(DESTINATIONS, "jira", _FakeJira())
    app = _app(tmp_path, connectors=[JIRA_CONFIG], sqlite_workflows=True)
    client, problem, workflows = app["client"], app["problem"], app["workflows"]
    pid = problem.problem_id
    _approve(client, problem)
    execution = _execution(client, pid)
    assert execution["status"] == "pushed" and execution["dispatched_at"] is not None
    # A row pushed before migration 016 stamped the dispatch instant.
    workflows._connection.execute("UPDATE executions SET dispatched_at = NULL")
    workflows._connection.commit()
    assert _execution(client, pid)["dispatched_at"] is None

    implemented_at = _iso(_parse(execution["created_at"]) + timedelta(minutes=1))
    response = _implement(client, pid, execution["execution_id"], implemented_at)
    assert response.status_code == 200, response.text
    assert response.json()["dispatched_at"] is None
    assert response.json()["implemented_at"] == implemented_at
    assert SQLiteWorkflowStore(tmp_path / "wf.db").list_executions()[0].dispatched_at is None


def test_intervention_anchor_uses_created_at_for_a_legacy_pushed_row() -> None:
    def _exe(execution_id: str, status: str, created_at: str = "2026-09-01T00:00:00Z", **extra) -> ExecutionRecord:
        return ExecutionRecord(
            execution_id=execution_id, problem_id="P", action_id="A", destination="jira", status=status,
            owner="o", summary="s", created_at=created_at, **extra,
        )

    legacy = _exe("EXE-1", "pushed")  # pre-016: pushed inside the approval request
    assert intervention_anchor([legacy]) == ("dispatch", "2026-09-01T00:00:00Z")
    stamped = _exe("EXE-2", "pushed", dispatched_at="2026-08-30T00:00:00Z")
    assert intervention_anchor([legacy, stamped]) == ("dispatch", "2026-08-30T00:00:00Z")
    draft = _exe("EXE-3", "draft_created", created_at="2026-08-01T00:00:00Z")
    assert intervention_anchor([draft, legacy]) == ("dispatch", "2026-09-01T00:00:00Z")


# ---------------------------------------------------------------------------
# B5 — implementation records
# ---------------------------------------------------------------------------


class TestImplementationRecords:
    def test_second_record_corrects_the_date_and_moves_every_live_plan(self, tmp_path: Path) -> None:
        app = _app(tmp_path)
        client, problem, plans, telemetry = app["client"], app["problem"], app["plans"], app["telemetry"]
        pid = problem.problem_id
        _approve(client, problem)
        execution = _execution(client, pid)
        first_at = _iso(_parse(execution["created_at"]) + timedelta(minutes=1))
        assert _implement(client, pid, execution["execution_id"], first_at).status_code == 200
        first_plans = [p for p in _plans(plans, pid) if p["status"] == "pending"]
        assert {p["origin"] for p in first_plans} == {"implementation"}

        second_at = _iso(_parse(execution["created_at"]) + timedelta(minutes=2))
        response = _implement(client, pid, execution["execution_id"], second_at)
        assert response.status_code == 200, response.text
        after = _plans(plans, pid)
        superseded = {p["id"] for p in after if p["status"] == "superseded"}
        assert {p["id"] for p in first_plans} <= superseded
        live = [p for p in after if p["status"] == "pending"]
        assert {p["kind"] for p in live} == {"t7", "window", "followup"}
        assert {p["executed_at"] for p in live} == {second_at}
        last = _events(telemetry, "implementation_recorded")[-1]
        assert last["metadata"]["implemented_at"] == second_at
        assert last["metadata"]["superseded_plans"] == 3
        assert sorted(last["metadata"]["kinds"]) == ["followup", "t7", "window"]
        assert client.get(f"/problems/{pid}/outcome").json()["measurement_origin_at"] == second_at

    def test_manual_required_plans_are_superseded_too(self, tmp_path: Path) -> None:
        business = _draft_problem(primary_metric="checkout_completion_7d", baseline=0.7, success_threshold=0.8)
        app = _app(tmp_path, problem=business)
        client, plans, telemetry = app["client"], app["plans"], app["telemetry"]
        pid = business.problem_id
        _approve(client, business)
        execution = _execution(client, pid)
        far = _iso(NOW + timedelta(days=business.outcome_contract.measurement_window_days + 31))
        assert client.post("/measurements/run-due", json={"now": far}).json()["manual_required"] == 3
        assert {p["status"] for p in _plans(plans, pid)} == {"manual_required"}

        implemented_at = _iso(_parse(execution["created_at"]) + timedelta(minutes=1))
        response = _implement(client, pid, execution["execution_id"], implemented_at)
        assert response.status_code == 200, response.text
        after = _plans(plans, pid)
        assert len([p for p in after if p["status"] == "superseded" and p["origin"] == "approval"]) == 3
        fresh = [p for p in after if p["status"] == "pending"]
        assert {p["origin"] for p in fresh} == {"implementation"}
        assert {p["executed_at"] for p in fresh} == {implemented_at}
        [event] = _events(telemetry, "implementation_recorded")
        assert event["metadata"]["superseded_plans"] == 3
        assert sorted(event["metadata"]["kinds"]) == ["followup", "t7", "window"]

    def test_requires_an_execution_whose_dispatch_is_still_authorised(self, tmp_path: Path) -> None:
        app = _app(tmp_path)
        client, problem, plans = app["client"], app["problem"], app["plans"]
        pid = problem.problem_id
        _approve(client, problem)
        execution = _execution(client, pid)
        action_id = _action(problem, "jira").action_id
        rejected = client.post(
            f"/problems/{pid}/approvals",
            json={"action_id": action_id, "decision": "rejected", "reviewer": "tester"},
        )
        assert rejected.status_code == 200, rejected.text

        implemented_at = _iso(_parse(execution["created_at"]) + timedelta(minutes=1))
        refused = _implement(client, pid, execution["execution_id"], implemented_at)
        assert refused.status_code == 409, refused.text
        assert refused.json()["detail"].startswith("approval_revoked")
        assert _execution(client, pid)["implemented_at"] is None
        assert {p["status"] for p in _plans(plans, pid)} == {"pending"}
        assert {p["origin"] for p in _plans(plans, pid)} == {"approval"}

    def test_requires_an_approval_created_execution_that_is_not_blocked(self, tmp_path: Path) -> None:
        app = _app(tmp_path)
        client, problem, workflows, plans = app["client"], app["problem"], app["workflows"], app["plans"]
        pid = problem.problem_id
        jira_action = _action(problem, "jira")

        def _orphan(status: ExecutionStatus, human_reviewed: bool) -> str:
            return workflows.add_execution(
                ExecutionRecord(
                    execution_id="EXE-XXXX", problem_id=pid, action_id=jira_action.action_id, destination="jira",
                    status=status, owner="own", summary="sum", created_at=_iso(NOW - timedelta(hours=1)),
                    human_reviewed=human_reviewed,
                )
            ).execution_id

        at = _iso(NOW)
        no_approval = _implement(client, pid, _orphan(ExecutionStatus.push_failed, False), at)
        assert no_approval.status_code == 409
        assert no_approval.json()["detail"] == "Only approval-created executions can record an implementation"
        blocked = _implement(client, pid, _orphan(ExecutionStatus.blocked, True), at)
        assert blocked.status_code == 409
        assert "blocked" in blocked.json()["detail"]
        not_started = _implement(client, pid, _orphan(ExecutionStatus.not_started, True), at)
        assert not_started.status_code == 409
        assert _plans(plans, pid) == []

    def test_cannot_precede_the_dispatch(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setitem(DESTINATIONS, "jira", _FakeJira())
        app = _app(tmp_path, connectors=[JIRA_CONFIG])
        client, problem, workflows = app["client"], app["problem"], app["workflows"]
        pid = problem.problem_id
        _approve(client, problem)
        execution = _execution(client, pid)
        assert execution["status"] == "pushed"
        created = _parse(execution["created_at"])
        dispatched_at = _iso(created + timedelta(minutes=2))
        workflows._executions[0] = workflows._executions[0].model_copy(update={"dispatched_at": dispatched_at})

        early = _implement(client, pid, execution["execution_id"], _iso(created + timedelta(minutes=1)))
        assert early.status_code == 422, early.text
        assert early.json()["detail"] == "implemented_at cannot precede the execution's dispatch"
        assert _execution(client, pid)["implemented_at"] is None
        exact = _implement(client, pid, execution["execution_id"], dispatched_at)
        assert exact.status_code == 200, exact.text
        assert exact.json()["implemented_at"] == dispatched_at


# ---------------------------------------------------------------------------
# B6 — origin precedence in scheduling
# ---------------------------------------------------------------------------


def test_real_push_after_a_draft_only_approval_moves_the_clock_to_dispatch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setitem(DESTINATIONS, "jira", _FakeJira())
    app = _app(tmp_path, connectors=[JIRA_CONFIG])
    client, problem, plans, telemetry = app["client"], app["problem"], app["plans"], app["telemetry"]
    pid = problem.problem_id
    # A research action has no connector: the draft is the deliverable.
    _approve(client, problem, destination="research_panel")
    draft = _execution(client, pid)
    assert draft["status"] == "draft_created"
    assert {p["origin"] for p in _plans(plans, pid)} == {"approval"}

    _approve(client, problem, destination="jira")
    pushed = next(e for e in client.get("/executions").json() if e["problem_id"] == pid and e["status"] == "pushed")
    after = _plans(plans, pid)
    superseded = [p for p in after if p["status"] == "superseded"]
    assert {p["origin"] for p in superseded} == {"approval"} and len(superseded) == 3
    assert all(p["note"] == f"superseded by dispatch clock ({pushed['execution_id']})" for p in superseded)
    live = [p for p in after if p["status"] == "pending"]
    assert {p["kind"] for p in live} == {"t7", "window", "followup"}
    assert {p["origin"] for p in live} == {"dispatch"}
    assert {p["executed_at"] for p in live} == {pushed["dispatched_at"]}
    scheduled = _events(telemetry, "measurement_scheduled")
    assert [e["metadata"]["origin"] for e in scheduled] == ["approval", "dispatch"]
    assert sorted(scheduled[-1]["metadata"]["kinds"]) == ["followup", "t7", "window"]
    snapshot = client.get(f"/problems/{pid}/outcome").json()
    assert snapshot["measurement_origin"] == "dispatch"

    # A same-or-lower clock keeps the dispatch plans (dedupe, no restart).
    kinds = schedule_measurements(plans, problem=problem, execution_id="EXE-0009", executed_at=_iso(NOW), origin="approval")
    assert kinds == []
    assert {p["executed_at"] for p in _plans(plans, pid) if p["status"] == "pending"} == {pushed["dispatched_at"]}


def test_supersede_pending_by_origin_and_live_status(tmp_path: Path) -> None:
    store = SQLiteMeasurementPlanStore(tmp_path / "plans.db")
    for origin in ("approval", "dispatch", "implementation"):
        store.schedule(problem_id="P", execution_id="E", executed_at="2026-09-01T00:00:00Z", due_at=f"2026-09-0{ORIGIN_DAY[origin]}T00:00:00Z", kind=origin, origin=origin)
    store.mark(next(p["id"] for p in store.list_plans() if p["origin"] == "dispatch"), status="manual_required", note="human")
    assert store.supersede_pending("P", note="lower clocks", origins={"approval", "dispatch"}) == 2
    by_origin = {p["origin"]: p["status"] for p in store.list_plans()}
    assert by_origin == {"approval": "superseded", "dispatch": "superseded", "implementation": "pending"}
    assert store.supersede_pending("P", note="none", origins=set()) == 0
    assert store.supersede_pending("P", note="everything") == 1


ORIGIN_DAY = {"approval": 1, "dispatch": 2, "implementation": 3}


# ---------------------------------------------------------------------------
# B7 — a window amendment does not rewrite the follow-up read
# ---------------------------------------------------------------------------


def test_followup_reads_its_own_scheduled_window_after_an_amendment(tmp_path: Path) -> None:
    problem = _draft_problem(measurement_window_days=30, comparison_method="pre_post_signal_rate")
    app = _app(tmp_path, problem=problem)
    client, plans, workflows = app["client"], app["plans"], app["workflows"]
    pid = problem.problem_id
    executed = NOW - timedelta(days=61)
    schedule_measurements(plans, problem=problem, execution_id="EXE-0001", executed_at=_iso(executed), origin="dispatch")
    followup = next(p for p in _plans(plans, pid) if p["kind"] == "followup")
    assert followup["due_at"] == _iso(executed + timedelta(days=60))

    amended = client.patch(f"/problems/{pid}/outcome-contract", json={"measurement_window_days": 60, "comparison_method": "pre_post_signal_rate"})
    assert amended.status_code == 200, amended.text

    result = client.post("/measurements/run-due", json={"now": _iso(NOW)}).json()
    assert result["measured"] == 3
    recorded = workflows.latest_outcome(pid)
    assert recorded.checkpoint_kind == "followup"
    # The month after the window the plan was scheduled with: [T+30, T+60],
    # which holds every pre-signal; the amended window would have read only
    # [T+60, now] and seen one.
    assert "10 matching signals" in (recorded.notes or "")
    assert recorded.observed_value == pytest.approx(10 / 31, abs=1e-4)


def test_followup_window_start_derives_from_due_at() -> None:
    assert followup_window_start("2026-09-30T00:00:00Z") == "2026-08-31T00:00:00Z"
    assert followup_window_start("2026-09-30T00:00:00+00:00", gap_days=10) == "2026-09-20T00:00:00Z"


# ---------------------------------------------------------------------------
# B8 — learning conclusions score under the measured baseline
# ---------------------------------------------------------------------------


def test_learning_conclusion_scores_under_the_measured_baseline(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    app = _app(tmp_path, problem=_amendable_problem())
    client, problem = app["client"], app["problem"]
    pid = problem.problem_id
    _record_manual(client, problem, 80.0)
    assert client.patch(f"/problems/{pid}/outcome-contract", json={"baseline": 1000.0}).status_code == 200
    snapshot = client.get(f"/problems/{pid}/outcome").json()
    assert snapshot["baseline"] == 1000.0
    assert snapshot["measured_baseline"] == 100.0 and snapshot["measured_success_threshold"] == 50.0

    import app.routers.problems as problems_router

    captured: dict[str, Any] = {}
    real_score = problems_router.resolution_score

    def _capture(*, baseline, measured, direction=None):
        captured.update({"baseline": baseline, "measured": measured})
        return real_score(baseline=baseline, measured=measured, direction=direction)

    monkeypatch.setattr(problems_router, "resolution_score", _capture)
    response = client.post(
        f"/problems/{pid}/learning-conclusions",
        json={"learning_status": "partially_worked", "summary": "Down a fifth.", "limitations": "One reading."},
    )
    assert response.status_code == 200, response.text
    assert captured == {"baseline": 100.0, "measured": 80.0}


# ---------------------------------------------------------------------------
# B9 — amended flag and revision fallbacks
# ---------------------------------------------------------------------------


def test_amended_flag_tracks_scoring_terms_not_the_revision_number(tmp_path: Path) -> None:
    app = _app(tmp_path, problem=_amendable_problem())
    client, problem = app["client"], app["problem"]
    pid = problem.problem_id
    _record_manual(client, problem, 80.0)
    guardrails = client.patch(
        f"/problems/{pid}/outcome-contract",
        json={"guardrail_metrics": ["repeat_signal_rate"], "comparison_method": "its_segmented_regression"},
    )
    assert guardrails.status_code == 200, guardrails.text
    assert guardrails.json()["outcome_contract"]["revision"] == 2
    snapshot = client.get(f"/problems/{pid}/outcome").json()
    assert snapshot["contract_revision"] == 2 and snapshot["measured_under_revision"] == 1
    assert snapshot["contract_amended_after_measurement"] is False  # no scoring term changed

    assert client.patch(f"/problems/{pid}/outcome-contract", json={"success_threshold": 90.0}).status_code == 200
    flagged = client.get(f"/problems/{pid}/outcome").json()
    assert flagged["contract_revision"] == 3
    assert flagged["contract_amended_after_measurement"] is True
    assert flagged["status"] == "improving"


def test_measured_revision_falls_back_to_the_snapshot() -> None:
    problem = _amendable_problem()
    frozen = problem.outcome_contract.model_copy(update={"revision": 3, "success_threshold": 85.0})
    measurement = OutcomeMeasurement(
        problem_id=problem.problem_id, metric=frozen.primary_metric, observed_value=80.0,
        measured_at="2026-09-01T00:00:00Z", contract_snapshot=frozen, contract_revision=None,
    )
    snapshot = build_outcome_snapshot(problem, measurement, [])
    assert snapshot.measured_under_revision == 3
    assert snapshot.status == "target_met"  # scored under the frozen threshold 85
    assert snapshot.contract_amended_after_measurement is True
    same_terms = build_outcome_snapshot(
        problem, measurement.model_copy(update={"contract_snapshot": problem.outcome_contract.model_copy(update={"revision": 9})}), []
    )
    assert same_terms.measured_under_revision == 9
    assert same_terms.contract_amended_after_measurement is False


# ---------------------------------------------------------------------------
# B10 / B11 / B13 — contract PATCH and approval-path auditing
# ---------------------------------------------------------------------------


def test_approval_auto_proposal_emits_contract_amended(tmp_path: Path) -> None:
    app = _app(tmp_path)  # promotion default -> the proposal applies
    client, problem, telemetry = app["client"], app["problem"], app["telemetry"]
    pid = problem.problem_id
    response = client.post(
        f"/problems/{pid}/approvals",
        json={"action_id": _action(problem, "jira").action_id, "decision": "approved", "reviewer": "tester"},
    )
    assert response.status_code == 200, response.text
    contract = client.get(f"/problems/{pid}").json()["outcome_contract"]
    assert contract["revision"] == 2
    assert len(_events(telemetry, "contract_proposed")) == 1
    [amended] = _events(telemetry, "contract_amended")
    assert amended["entity_id"] == pid
    assert amended["metadata"]["problem_id"] == pid
    assert amended["metadata"]["revision"] == 2
    assert amended["metadata"]["actor"] == "tester"
    assert amended["metadata"]["note"] == "auto-proposed contract accepted at approval"
    assert amended["metadata"]["had_measurement"] is False
    assert amended["metadata"]["changed"]["comparison_method"]["after"] == "its_segmented_regression"
    assert amended["metadata"]["changed"]["baseline"]["after"] == contract["baseline"]


def test_note_only_patch_is_rejected(tmp_path: Path) -> None:
    app = _app(tmp_path, problem=_amendable_problem())
    client, problem, telemetry = app["client"], app["problem"], app["telemetry"]
    pid = problem.problem_id
    response = client.patch(f"/problems/{pid}/outcome-contract", json={"amendment_note": "just a note"})
    assert response.status_code == 422, response.text
    assert response.json()["detail"] == "no contract term changed"
    contract = client.get(f"/problems/{pid}").json()["outcome_contract"]
    assert contract["revision"] == 1 and contract["revision_note"] is None
    assert not _events(telemetry, "contract_amended")


def test_zero_reading_counts_as_a_measurement_in_the_patch_guard(tmp_path: Path) -> None:
    degenerate = _draft_problem(baseline=0.0, success_threshold=0.0, comparison_method="its_segmented_regression")
    app = _app(tmp_path, problem=degenerate)
    client, telemetry = app["client"], app["telemetry"]
    pid = degenerate.problem_id
    _record_manual(client, degenerate, 0.0)
    assert client.get(f"/problems/{pid}/outcome").json()["status"] == "not_measured"

    rejected = client.patch(f"/problems/{pid}/outcome-contract", json={"primary_metric": "signal_rate_per_day:checkout/refunds"})
    assert rejected.status_code == 409, rejected.text
    assert client.get(f"/problems/{pid}").json()["outcome_contract"]["primary_metric"] == degenerate.outcome_contract.primary_metric
    assert client.patch(f"/problems/{pid}/outcome-contract", json={"success_threshold": 1.0}).status_code == 200
    [event] = _events(telemetry, "contract_amended")
    assert event["metadata"]["had_measurement"] is True


# ---------------------------------------------------------------------------
# B12 — stamp_contract_provenance consistency
# ---------------------------------------------------------------------------


def test_stamp_contract_provenance_keeps_snapshot_and_revision_consistent() -> None:
    problem = _amendable_problem().model_copy()
    problem = problem.model_copy(update={"outcome_contract": problem.outcome_contract.model_copy(update={"revision": 4})})
    metric = problem.outcome_contract.primary_metric
    stale_revision = OutcomeMeasurement(problem_id=problem.problem_id, metric=metric, observed_value=1.0, measured_at="2026-09-01T00:00:00Z", contract_revision=7)
    stamped = stamp_contract_provenance(problem, stale_revision)
    assert stamped.contract_snapshot == problem.outcome_contract
    assert stamped.contract_revision == 4  # never revision 7 paired with the revision-4 snapshot

    frozen = problem.outcome_contract.model_copy(update={"revision": 2, "success_threshold": 10.0})
    with_snapshot = OutcomeMeasurement(problem_id=problem.problem_id, metric=metric, observed_value=1.0, measured_at="2026-09-01T00:00:00Z", contract_snapshot=frozen)
    stamped = stamp_contract_provenance(problem, with_snapshot)
    assert stamped.contract_snapshot == frozen and stamped.contract_revision == 2
    complete = with_snapshot.model_copy(update={"contract_revision": 2})
    assert stamp_contract_provenance(problem, complete) == complete


# ---------------------------------------------------------------------------
# B14 — CSV export
# ---------------------------------------------------------------------------


def test_outcomes_csv_carries_measurement_provenance(tmp_path: Path) -> None:
    app = _app(tmp_path)
    client, problem, plans = app["client"], app["problem"], app["plans"]
    pid = problem.problem_id
    schedule_measurements(plans, problem=problem, execution_id="EXE-0001", executed_at=_iso(NOW - timedelta(days=40)), origin="dispatch")
    assert client.post("/measurements/run-due", json={"now": _iso(NOW - timedelta(hours=1))}).json()["loop_closed"] == 1

    response = client.get("/export/outcomes.csv")
    assert response.status_code == 200, response.text
    rows = list(csv.DictReader(io.StringIO(response.text)))
    header = list(rows[0].keys())
    assert header[:12] == [
        "problem_id", "title", "owner", "problem_status", "metric", "baseline", "success_threshold",
        "latest_value", "outcome_status", "improvement_direction", "measurement_window_days",
        "latest_learning_status",
    ]
    assert header[12:] == ["measurement_source", "checkpoint_kind", "loop_verdict"]
    row = next(r for r in rows if r["problem_id"] == pid)
    assert (row["measurement_source"], row["checkpoint_kind"], row["loop_verdict"]) == ("instrumented", "window", "loop_closed")
    unmeasured = next(r for r in rows if r["problem_id"] != pid)
    assert (unmeasured["measurement_source"], unmeasured["checkpoint_kind"]) == ("", "")
    assert unmeasured["loop_verdict"] == "not_measured"


def test_outcomes_csv_without_provenance_keeps_the_legacy_columns() -> None:
    from types import SimpleNamespace

    from app.services.exports import outcomes_csv

    item = SimpleNamespace(
        problem_id="P", title="T", owner="o", problem_status=SimpleNamespace(value="open"), metric="m",
        baseline=1.0, success_threshold=0.5, latest_value=None, outcome_status="not_measured",
        improvement_direction="decrease", measurement_window_days=28, latest_learning_status=None,
    )
    header = outcomes_csv(SimpleNamespace(items=[item])).splitlines()[0]
    assert header.endswith("latest_learning_status")
    assert "loop_verdict" not in header
