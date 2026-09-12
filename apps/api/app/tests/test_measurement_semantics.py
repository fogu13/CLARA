"""Measurement semantics — C2 (verdict bound to the observation), C3 (contract
revisions do not reinterpret recorded observations) and C4 (the measurement
clock starts at dispatch / implementation, never on a failed push).

Each test states the invariant the independent review found violated, as the
DESIRED behaviour. SQLite and in-memory stores; Postgres parity lives in
test_pg_parity_measurement.py.
"""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.connectors import DESTINATIONS
from app.connectors.base import ConnectorError
from app.connectors.config_store import ConnectorConfig, ConnectorConfigStore
from app.domain.models import (
    ApprovalDecision,
    ExecutionStatus,
    OutcomeContract,
    OutcomeMeasurement,
    SignalRecord,
)
from app.main import create_app
from app.services.measurement_scheduler import (
    SQLiteMeasurementPlanStore,
    schedule_measurements,
)
from app.services.outcome_engine import intervention_anchor, loop_verdict
from app.services.problems import ProblemStore
from app.services.seed import load_seed_problems
from app.services.signals import SQLiteSignalStore, build_candidates, promote_candidate
from app.services.telemetry import SQLiteTelemetryStore
from app.services.workflow import SQLiteWorkflowStore, WorkflowStore

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


class _FakeJira:
    connector_type = "jira"

    def __init__(self, *, fail_first: int = 0) -> None:
        self.fail_first = fail_first
        self.calls = 0

    def push(self, action, config):
        self.calls += 1
        if self.calls <= self.fail_first:
            raise ConnectorError("Jira returned 500", connector="jira", status=500)
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
        "signals": signal_store,
        "plans": plan_store,
        "telemetry": telemetry,
        "workflows": workflows,
    }


def _jira_action(problem):
    return next(action for action in problem.action_proposals if action.destination == "jira")


def _approve(client: TestClient, problem) -> dict:
    response = client.post(
        f"/problems/{problem.problem_id}/approvals",
        json={
            "action_id": _jira_action(problem).action_id,
            "decision": "approved",
            "reviewer": "tester",
            "accept_proposed_contract": False,
        },
    )
    assert response.status_code == 200, response.text
    return response.json()


def _execution(client: TestClient, problem_id: str) -> dict:
    return next(e for e in client.get("/executions").json() if e["problem_id"] == problem_id)


def _plans(store: SQLiteMeasurementPlanStore, problem_id: str) -> list[dict]:
    return [plan for plan in store.list_plans() if plan["problem_id"] == problem_id]


def _events(telemetry: SQLiteTelemetryStore, event_type: str) -> list[dict]:
    return [e for e in telemetry.list_events() if e["event_type"] == event_type]


# ---------------------------------------------------------------------------
# C2 — the verdict is bound to the observation a closing checkpoint produced
# ---------------------------------------------------------------------------


class TestVerdictBinding:
    def test_manual_reading_with_old_done_window_plan_is_not_certified(self, tmp_path: Path) -> None:
        """The review's probe: target_met + manual latest reading + a done window
        plan used to read loop_closed "on real signals"."""
        app = _app(tmp_path)
        client, problem, plans = app["client"], app["problem"], app["plans"]
        plans.schedule(
            problem_id=problem.problem_id,
            execution_id="EXE-0001",
            executed_at=_iso(NOW - timedelta(days=40)),
            due_at=_iso(NOW - timedelta(days=12)),
            kind="window",
            origin="dispatch",
        )
        plans.mark(_plans(plans, problem.problem_id)[0]["id"], status="done", note="observed 0.1/day from 3 signals")

        manual = client.post(
            f"/problems/{problem.problem_id}/outcomes",
            json={
                "problem_id": problem.problem_id,
                "metric": problem.outcome_contract.primary_metric,
                "observed_value": 0.0,
                "measured_at": _iso(NOW),
            },
        )
        assert manual.status_code == 200, manual.text

        snapshot = client.get(f"/problems/{problem.problem_id}/outcome").json()
        assert snapshot["status"] == "target_met"
        assert snapshot["measurement_source"] == "manual"
        assert snapshot["checkpoint_kind"] is None
        assert snapshot["loop_verdict"] == "on_track"
        assert "manual reading" in snapshot["loop_note"]
        assert "not certified" in snapshot["loop_note"]
        assert "real signals" not in snapshot["loop_note"]
        board = next(i for i in client.get("/outcome-board").json()["items"] if i["problem_id"] == problem.problem_id)
        assert board["loop_verdict"] == "on_track"

    def test_instrumented_window_read_certifies_with_binding_fields(self, tmp_path: Path) -> None:
        app = _app(tmp_path)
        client, problem, plans, workflows = app["client"], app["problem"], app["plans"], app["workflows"]
        _approve(client, problem)  # no connector -> approval-origin clock
        execution = _execution(client, problem.problem_id)
        executed = _parse(_plans(plans, problem.problem_id)[0]["executed_at"])
        window_days = problem.outcome_contract.measurement_window_days
        app["signals"].import_signals([_signal("post-1", days_ago=-3)])

        at_window = _iso(executed + timedelta(days=window_days, hours=1))
        result = client.post("/measurements/run-due", json={"now": at_window}).json()
        assert result["measured"] == 2 and result["loop_closed"] == 1

        recorded = workflows._outcomes[problem.problem_id]
        assert recorded.measurement_source == "instrumented"
        assert recorded.checkpoint_kind == "window"
        assert recorded.execution_id == execution["execution_id"]
        window_plan = next(p for p in _plans(plans, problem.problem_id) if p["kind"] == "window")
        assert recorded.plan_id == window_plan["id"]
        assert recorded.contract_revision == problem.outcome_contract.revision
        assert recorded.contract_snapshot == problem.outcome_contract
        assert "since approval (" in (recorded.notes or "")
        assert window_plan["status"] == "done" and "observed" in window_plan["note"]

        snapshot = client.get(f"/problems/{problem.problem_id}/outcome").json()
        assert snapshot["status"] == "target_met"
        assert snapshot["checkpoint_kind"] == "window"
        assert snapshot["loop_verdict"] == "loop_closed"
        assert "window checkpoint" in snapshot["loop_note"]
        assert "instrumented read" in snapshot["loop_note"]
        assert "clock from approval" in snapshot["loop_note"]
        assert "may predate the fix" in snapshot["loop_note"]  # approval-origin caveat
        assert "loop worked" not in snapshot["loop_note"]
        assert snapshot["measurement_origin"] == "approval"
        assert snapshot["measurement_origin_at"] == execution["created_at"]

    def test_manual_reading_after_instrumented_read_follows_the_manual_value_uncertified(
        self, tmp_path: Path
    ) -> None:
        app = _app(tmp_path)
        client, problem, plans = app["client"], app["problem"], app["plans"]
        schedule_measurements(
            plans,
            problem=problem,
            execution_id="EXE-0001",
            executed_at=_iso(NOW - timedelta(days=40)),
            origin="dispatch",
        )
        certified = client.post("/measurements/run-due", json={"now": _iso(NOW - timedelta(hours=1))}).json()
        assert certified["loop_closed"] == 1  # zero post-dispatch inflow at the window read
        assert client.get(f"/problems/{problem.problem_id}/outcome").json()["loop_verdict"] == "loop_closed"

        def _manual(value: float, at: datetime) -> dict:
            response = client.post(
                f"/problems/{problem.problem_id}/outcomes",
                json={
                    "problem_id": problem.problem_id,
                    "metric": problem.outcome_contract.primary_metric,
                    "observed_value": value,
                    "measured_at": _iso(at),
                },
            )
            assert response.status_code == 200, response.text
            return client.get(f"/problems/{problem.problem_id}/outcome").json()

        worse = _manual(problem.outcome_contract.baseline * 2, NOW - timedelta(minutes=30))
        assert worse["status"] == "not_improved"
        assert worse["loop_verdict"] == "measuring"  # never fix_did_not_land on a manual read
        assert worse["checkpoint_kind"] is None

        better = _manual(0.0, NOW)
        assert better["status"] == "target_met"
        assert better["loop_verdict"] == "on_track"
        assert "not certified" in better["loop_note"]
        # The done window plan is still there; it no longer certifies anything.
        assert any(p["kind"] == "window" and p["status"] == "done" for p in _plans(plans, problem.problem_id))


@pytest.mark.parametrize(
    ("status", "source", "kind", "plans", "expected"),
    [
        ("not_measured", None, None, [], "not_measured"),
        ("not_measured", None, None, [{"kind": "t7", "status": "pending"}], "measuring"),
        ("not_measured", None, None, [{"kind": "window", "status": "manual_required"}], "manual_required"),
        # Instrumented closing reads certify either way.
        ("target_met", "instrumented", "window", [], "loop_closed"),
        ("target_met", "instrumented", "followup", [], "loop_closed"),
        ("not_improved", "instrumented", "window", [], "fix_did_not_land"),
        ("not_improved", "instrumented", "followup", [], "fix_did_not_land"),
        # An instrumented early read is not proof, whatever the plans say.
        ("target_met", "instrumented", "t7", [{"kind": "window", "status": "done"}], "on_track"),
        ("not_improved", "instrumented", "t7", [{"kind": "window", "status": "done"}], "measuring"),
        # A manual reading never certifies, even next to a done closing plan.
        ("target_met", "manual", None, [{"kind": "window", "status": "done"}], "on_track"),
        ("not_improved", "manual", None, [{"kind": "followup", "status": "done"}], "measuring"),
        ("improving", "manual", None, [{"kind": "window", "status": "done"}], "on_track"),
        # Legacy instrumented readings (no checkpoint kind) fall back to the plans.
        ("target_met", "instrumented", None, [{"kind": "window", "status": "done"}], "loop_closed"),
        ("target_met", "instrumented", None, [{"kind": "t7", "status": "done"}], "on_track"),
        ("not_improved", "instrumented", None, [{"kind": "window", "status": "done"}], "fix_did_not_land"),
        ("not_improved", "instrumented", None, [{"kind": "t7", "status": "pending"}], "measuring"),
        ("improving", "instrumented", "window", [], "on_track"),
    ],
)
def test_loop_verdict_certifies_only_instrumented_closing_reads(status, source, kind, plans, expected) -> None:
    verdict, _ = loop_verdict(
        outcome_status=status, plans=plans, measurement_source=source, checkpoint_kind=kind
    )
    assert verdict == expected


def test_loop_verdict_note_words_target_attainment_not_causation() -> None:
    _, note = loop_verdict(
        outcome_status="target_met",
        plans=[],
        measurement_source="instrumented",
        checkpoint_kind="window",
        measurement_origin="dispatch",
        measurement_origin_at="2026-09-01T10:00:00Z",
    )
    assert "Inflow met the target at the window checkpoint" in note
    assert "clock from dispatch on 2026-09-01" in note
    assert "causal attribution rests on the comparison method" in note
    assert "predate the fix" not in note
    _, approval_note = loop_verdict(
        outcome_status="target_met",
        plans=[],
        measurement_source="instrumented",
        checkpoint_kind="followup",
        measurement_origin="approval",
    )
    assert "follow-up checkpoint" in approval_note
    assert "no dispatch or implementation was recorded" in approval_note.lower()


# ---------------------------------------------------------------------------
# C3 — contract amendments are revisions; observations keep their revision
# ---------------------------------------------------------------------------


def _amendable_problem():
    return _draft_problem(
        baseline=100.0,
        success_threshold=50.0,
        comparison_method="its_segmented_regression",
    )


class TestContractRevisions:
    def test_amendment_does_not_reinterpret_the_recorded_observation(self, tmp_path: Path) -> None:
        app = _app(tmp_path, problem=_amendable_problem())
        client, problem, telemetry = app["client"], app["problem"], app["telemetry"]
        pid = problem.problem_id
        assert problem.outcome_contract.revision == 1

        recorded = client.post(
            f"/problems/{pid}/outcomes",
            json={
                "problem_id": pid,
                "metric": problem.outcome_contract.primary_metric,
                "observed_value": 80.0,
                "measured_at": _iso(NOW - timedelta(hours=1)),
            },
        )
        assert recorded.status_code == 200, recorded.text
        assert recorded.json()["contract_revision"] == 1
        assert recorded.json()["contract_snapshot"]["success_threshold"] == 50.0
        before = client.get(f"/problems/{pid}/outcome").json()
        assert before["status"] == "improving"
        assert before["contract_revision"] == 1 and before["measured_under_revision"] == 1
        assert before["contract_amended_after_measurement"] is False

        patched = client.patch(
            f"/problems/{pid}/outcome-contract",
            json={"success_threshold": 90.0, "amendment_note": "loosen the target"},
        )
        assert patched.status_code == 200, patched.text
        contract = patched.json()["outcome_contract"]
        assert contract["revision"] == 2
        assert contract["revised_by"] == "dev-user"
        assert contract["revision_note"] == "loosen the target"
        assert contract["revised_at"] is not None
        assert contract["success_threshold"] == 90.0
        assert "amendment_note" not in contract

        after = client.get(f"/problems/{pid}/outcome").json()
        assert after["status"] == "improving"  # 80 is NOT re-labelled target_met under 90
        assert after["success_threshold"] == 90.0  # the UI shows the current terms
        assert after["contract_revision"] == 2
        assert after["measured_under_revision"] == 1
        assert after["contract_amended_after_measurement"] is True
        board = next(i for i in client.get("/outcome-board").json()["items"] if i["problem_id"] == pid)
        assert board["outcome_status"] == "improving"

        [event] = _events(telemetry, "contract_amended")
        assert event["entity_id"] == pid
        assert event["metadata"]["revision"] == 2
        assert event["metadata"]["actor"] == "dev-user"
        assert event["metadata"]["note"] == "loosen the target"
        assert event["metadata"]["had_measurement"] is True
        assert event["metadata"]["changed"] == {"success_threshold": {"before": 50.0, "after": 90.0}}

        # A new instrumented read is evaluated under revision 2.
        revised_problem = problem.model_copy(
            update={"outcome_contract": OutcomeContract.model_validate(contract)}
        )
        schedule_measurements(
            app["plans"],
            problem=revised_problem,
            execution_id="EXE-0001",
            executed_at=_iso(NOW - timedelta(days=30)),
            origin="dispatch",
        )
        assert {p["contract_revision"] for p in _plans(app["plans"], pid)} == {2}
        result = client.post("/measurements/run-due", json={}).json()
        assert result["measured"] == 2
        fresh = client.get(f"/problems/{pid}/outcome").json()
        assert fresh["measurement_source"] == "instrumented"
        assert fresh["measured_under_revision"] == 2
        assert fresh["contract_amended_after_measurement"] is False
        assert fresh["status"] == "target_met"  # zero post-dispatch inflow vs threshold 90

    def test_metric_change_after_measurement_is_still_rejected(self, tmp_path: Path) -> None:
        app = _app(tmp_path, problem=_amendable_problem())
        client, problem = app["client"], app["problem"]
        pid = problem.problem_id
        client.post(
            f"/problems/{pid}/outcomes",
            json={
                "problem_id": pid,
                "metric": problem.outcome_contract.primary_metric,
                "observed_value": 80.0,
                "measured_at": _iso(NOW - timedelta(hours=1)),
            },
        )
        rejected = client.patch(
            f"/problems/{pid}/outcome-contract", json={"primary_metric": "signal_rate_per_day:checkout/refunds"}
        )
        assert rejected.status_code == 409
        assert client.get(f"/problems/{pid}").json()["outcome_contract"]["revision"] == 1
        assert not _events(app["telemetry"], "contract_amended")

    def test_noop_amendment_does_not_bump_the_revision(self, tmp_path: Path) -> None:
        app = _app(tmp_path, problem=_amendable_problem())
        client, problem, telemetry = app["client"], app["problem"], app["telemetry"]
        pid = problem.problem_id
        same = client.patch(
            f"/problems/{pid}/outcome-contract",
            json={"success_threshold": 50.0, "comparison_method": "its_segmented_regression"},
        )
        assert same.status_code == 200, same.text
        contract = same.json()["outcome_contract"]
        assert contract["revision"] == 1
        assert contract["revised_at"] is None and contract["revised_by"] is None
        assert not _events(telemetry, "contract_amended")

        real = client.patch(f"/problems/{pid}/outcome-contract", json={"measurement_window_days": 45})
        assert real.json()["outcome_contract"]["revision"] == 2
        again = client.patch(f"/problems/{pid}/outcome-contract", json={"measurement_window_days": 45})
        assert again.json()["outcome_contract"]["revision"] == 2
        assert len(_events(telemetry, "contract_amended")) == 1

    def test_approval_auto_proposal_is_an_audited_revision(self, tmp_path: Path) -> None:
        app = _app(tmp_path)  # promotion default: pre_post_signal_rate -> proposal applies
        client, problem = app["client"], app["problem"]
        response = client.post(
            f"/problems/{problem.problem_id}/approvals",
            json={"action_id": _jira_action(problem).action_id, "decision": "approved", "reviewer": "tester"},
        )
        assert response.status_code == 200, response.text
        contract = client.get(f"/problems/{problem.problem_id}").json()["outcome_contract"]
        assert contract["comparison_method"] == "its_segmented_regression"
        assert contract["revision"] == 2
        assert contract["revised_by"] == "tester"
        assert contract["revision_note"] == "auto-proposed contract accepted at approval"
        assert {p["contract_revision"] for p in _plans(app["plans"], problem.problem_id)} == {2}


# ---------------------------------------------------------------------------
# C4 — the clock starts at dispatch / implementation, never on a failed push
# ---------------------------------------------------------------------------


class TestClockOrigins:
    def test_failed_push_starts_no_clock(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setitem(DESTINATIONS, "jira", _FakeJira(fail_first=99))
        app = _app(tmp_path, connectors=[JIRA_CONFIG])
        client, problem, plans, telemetry = app["client"], app["problem"], app["plans"], app["telemetry"]
        _approve(client, problem)
        execution = _execution(client, problem.problem_id)
        assert execution["status"] == "push_failed"
        assert execution["dispatched_at"] is None
        assert _plans(plans, problem.problem_id) == []
        [event] = _events(telemetry, "measurement_not_scheduled")
        assert event["metadata"] == {
            "problem_id": problem.problem_id,
            "execution_id": execution["execution_id"],
            "reason": "push_failed",
        }
        assert not _events(telemetry, "measurement_scheduled")
        snapshot = client.get(f"/problems/{problem.problem_id}/outcome").json()
        assert snapshot["loop_verdict"] == "not_measured"
        assert snapshot["measurement_origin"] is None and snapshot["its"] is None

    def test_draft_only_execution_runs_from_approval(self, tmp_path: Path) -> None:
        app = _app(tmp_path)  # no jira connector configured -> the draft stands
        client, problem, plans, telemetry = app["client"], app["problem"], app["plans"], app["telemetry"]
        _approve(client, problem)
        execution = _execution(client, problem.problem_id)
        assert execution["status"] == "draft_created"
        scheduled = _plans(plans, problem.problem_id)
        assert {p["kind"] for p in scheduled} == {"t7", "window", "followup"}
        assert {p["origin"] for p in scheduled} == {"approval"}
        assert {p["executed_at"] for p in scheduled} == {execution["created_at"]}
        assert {p["contract_revision"] for p in scheduled} == {problem.outcome_contract.revision}
        [event] = _events(telemetry, "measurement_scheduled")
        assert event["metadata"]["origin"] == "approval"
        snapshot = client.get(f"/problems/{problem.problem_id}/outcome").json()
        assert snapshot["measurement_origin"] == "approval"
        assert snapshot["measurement_origin_at"] == execution["created_at"]

    def test_successful_push_runs_from_dispatch(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setitem(DESTINATIONS, "jira", _FakeJira())
        app = _app(tmp_path, connectors=[JIRA_CONFIG])
        client, problem, plans = app["client"], app["problem"], app["plans"]
        _approve(client, problem)
        execution = _execution(client, problem.problem_id)
        assert execution["status"] == "pushed"
        assert execution["dispatched_at"] is not None
        assert _parse(execution["dispatched_at"]) >= _parse(execution["created_at"])
        scheduled = _plans(plans, problem.problem_id)
        assert {p["origin"] for p in scheduled} == {"dispatch"}
        assert {p["executed_at"] for p in scheduled} == {execution["dispatched_at"]}
        snapshot = client.get(f"/problems/{problem.problem_id}/outcome").json()
        assert snapshot["measurement_origin"] == "dispatch"
        assert snapshot["measurement_origin_at"] == execution["dispatched_at"]

    def test_successful_retry_starts_the_dispatch_clock(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setitem(DESTINATIONS, "jira", _FakeJira(fail_first=1))
        app = _app(tmp_path, connectors=[JIRA_CONFIG])
        client, problem, plans, telemetry = app["client"], app["problem"], app["plans"], app["telemetry"]
        _approve(client, problem)
        execution = _execution(client, problem.problem_id)
        assert execution["status"] == "push_failed"
        assert _plans(plans, problem.problem_id) == []

        retried = client.post(f"/problems/{problem.problem_id}/executions/{execution['execution_id']}/retry")
        assert retried.status_code == 200, retried.text
        assert retried.json()["status"] == "pushed"
        dispatched_at = retried.json()["dispatched_at"]
        assert dispatched_at is not None
        assert _parse(dispatched_at) >= _parse(execution["created_at"])
        scheduled = _plans(plans, problem.problem_id)
        assert {p["kind"] for p in scheduled} == {"t7", "window", "followup"}
        assert {p["origin"] for p in scheduled} == {"dispatch"}
        assert {p["executed_at"] for p in scheduled} == {dispatched_at}
        assert [e["metadata"]["origin"] for e in _events(telemetry, "measurement_scheduled")] == ["dispatch"]

    def test_implementation_record_supersedes_and_restarts_the_clock(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        app = _app(tmp_path)
        client, problem, plans, telemetry = app["client"], app["problem"], app["plans"], app["telemetry"]
        _approve(client, problem)
        execution = _execution(client, problem.problem_id)
        before = _plans(plans, problem.problem_id)
        assert {p["origin"] for p in before} == {"approval"}

        captured: dict[str, Any] = {}
        import app.routers.problems as problems_router

        real_its = problems_router.its_outcome_for_problem

        def _capture(problem_arg, signals, *, executed_at, now):
            captured["executed_at"] = executed_at
            return real_its(problem_arg, signals, executed_at=executed_at, now=now)

        monkeypatch.setattr(problems_router, "its_outcome_for_problem", _capture)

        implemented_at = _iso(_parse(execution["created_at"]) + timedelta(minutes=2))
        response = client.post(
            f"/problems/{problem.problem_id}/executions/{execution['execution_id']}/implementation",
            json={"implemented_at": implemented_at, "note": "Fix deployed to production."},
        )
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["implemented_at"] == implemented_at
        assert body["implementation_note"] == "Fix deployed to production."
        assert body["status"] == "draft_created"  # implementation is a human record, not a push

        after = _plans(plans, problem.problem_id)
        superseded = [p for p in after if p["status"] == "superseded"]
        assert {p["id"] for p in superseded} == {p["id"] for p in before}
        assert all(p["note"] == f"superseded by implementation record {execution['execution_id']}" for p in superseded)
        fresh = [p for p in after if p["status"] == "pending"]
        assert {p["kind"] for p in fresh} == {"t7", "window", "followup"}
        assert {p["origin"] for p in fresh} == {"implementation"}
        assert {p["executed_at"] for p in fresh} == {implemented_at}
        [event] = _events(telemetry, "implementation_recorded")
        assert event["metadata"]["execution_id"] == execution["execution_id"]
        assert event["metadata"]["superseded_plans"] == 3
        assert event["metadata"]["actor"] == "dev-user"

        snapshot = client.get(f"/problems/{problem.problem_id}/outcome").json()
        assert snapshot["measurement_origin"] == "implementation"
        assert snapshot["measurement_origin_at"] == implemented_at
        assert captured["executed_at"] == implemented_at  # ITS anchored on the implementation
        assert snapshot["loop_verdict"] == "measuring"

    def test_implementation_record_rejects_future_and_pre_approval_instants(self, tmp_path: Path) -> None:
        app = _app(tmp_path)
        client, problem = app["client"], app["problem"]
        _approve(client, problem)
        execution = _execution(client, problem.problem_id)
        url = f"/problems/{problem.problem_id}/executions/{execution['execution_id']}/implementation"
        future = client.post(url, json={"implemented_at": _iso(NOW + timedelta(days=1))})
        assert future.status_code == 422
        early = client.post(url, json={"implemented_at": _iso(_parse(execution["created_at"]) - timedelta(days=1))})
        assert early.status_code == 422
        garbage = client.post(url, json={"implemented_at": "yesterday"})
        assert garbage.status_code == 422
        missing = client.post(
            f"/problems/{problem.problem_id}/executions/EXE-9999/implementation",
            json={"implemented_at": _iso(NOW)},
        )
        assert missing.status_code == 404
        assert {p["status"] for p in _plans(app["plans"], problem.problem_id)} == {"pending"}

    def test_run_due_note_names_the_clock_origin(self, tmp_path: Path) -> None:
        app = _app(tmp_path)
        client, problem, plans, workflows = app["client"], app["problem"], app["plans"], app["workflows"]
        schedule_measurements(
            plans,
            problem=problem,
            execution_id="EXE-0007",
            executed_at=_iso(NOW - timedelta(days=70)),
            origin="implementation",
        )
        result = client.post("/measurements/run-due", json={"now": _iso(NOW - timedelta(hours=1))}).json()
        assert result["measured"] == 3
        recorded = workflows._outcomes[problem.problem_id]
        assert recorded.checkpoint_kind == "followup"
        assert recorded.execution_id == "EXE-0007"
        assert recorded.plan_id == next(p["id"] for p in _plans(plans, problem.problem_id) if p["kind"] == "followup")
        assert recorded.contract_snapshot is not None
        assert "clock from implementation " + _iso(NOW - timedelta(days=70))[:10] in (recorded.notes or "")

    def test_intervention_anchor_prefers_implementation_then_dispatch_then_draft(self) -> None:
        from app.domain.models import ExecutionRecord

        def _exe(execution_id: str, status: str, **extra) -> ExecutionRecord:
            return ExecutionRecord(
                execution_id=execution_id,
                problem_id="P",
                action_id="A",
                destination="jira",
                status=status,
                owner="o",
                summary="s",
                created_at="2026-09-01T00:00:00Z",
                **extra,
            )

        failed = _exe("EXE-1", "push_failed")
        assert intervention_anchor([failed]) is None
        assert intervention_anchor([]) is None
        draft = _exe("EXE-2", "draft_created")
        assert intervention_anchor([failed, draft]) == ("approval", "2026-09-01T00:00:00Z")
        pushed = _exe("EXE-3", "pushed", dispatched_at="2026-09-03T00:00:00Z")
        assert intervention_anchor([draft, pushed]) == ("dispatch", "2026-09-03T00:00:00Z")
        implemented = _exe("EXE-4", "pushed", dispatched_at="2026-09-02T00:00:00Z", implemented_at="2026-09-05T00:00:00Z")
        assert intervention_anchor([draft, pushed, implemented]) == ("implementation", "2026-09-05T00:00:00Z")


# ---------------------------------------------------------------------------
# SQLite persistence of the new columns (including pre-existing databases)
# ---------------------------------------------------------------------------


class TestSQLitePersistence:
    def test_plan_columns_survive_reopen_and_upgrade_legacy_db(self, tmp_path: Path) -> None:
        db = tmp_path / "plans.db"
        with sqlite3.connect(db) as conn:
            conn.execute(
                """
                CREATE TABLE measurement_plans (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    problem_id TEXT NOT NULL,
                    execution_id TEXT NOT NULL,
                    executed_at TEXT NOT NULL,
                    due_at TEXT NOT NULL,
                    kind TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'pending',
                    note TEXT,
                    created_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                "INSERT INTO measurement_plans"
                " (problem_id, execution_id, executed_at, due_at, kind, status, created_at)"
                " VALUES ('P', 'EXE-1', '2026-08-01T00:00:00Z', '2026-08-08T00:00:00Z', 't7', 'done', '2026-08-01T00:00:00Z')"
            )
        store = SQLiteMeasurementPlanStore(db)
        [legacy] = store.list_plans()
        assert legacy["origin"] == "approval" and legacy["contract_revision"] is None
        assert store.schedule(
            problem_id="P",
            execution_id="EXE-2",
            executed_at="2026-09-01T00:00:00Z",
            due_at="2026-09-08T00:00:00Z",
            kind="window",
            origin="dispatch",
            contract_revision=3,
        )
        reopened = SQLiteMeasurementPlanStore(db)
        window = next(p for p in reopened.list_plans() if p["kind"] == "window")
        assert window["origin"] == "dispatch" and window["contract_revision"] == 3
        assert reopened.supersede_pending("P", note="superseded by implementation record EXE-2") == 1
        assert next(p for p in reopened.list_plans() if p["kind"] == "window")["status"] == "superseded"
        assert next(p for p in reopened.list_plans() if p["kind"] == "t7")["status"] == "done"

    def test_outcome_columns_survive_reopen_and_upgrade_legacy_db(self, tmp_path: Path) -> None:
        db = tmp_path / "wf.db"
        problem = _amendable_problem()
        with sqlite3.connect(db) as conn:
            conn.execute(
                """
                CREATE TABLE outcomes (
                    problem_id TEXT PRIMARY KEY,
                    metric TEXT NOT NULL,
                    observed_value REAL NOT NULL,
                    measured_at TEXT NOT NULL,
                    notes TEXT,
                    measurement_source TEXT NOT NULL DEFAULT 'manual'
                )
                """
            )
            conn.execute(
                "INSERT INTO outcomes (problem_id, metric, observed_value, measured_at, notes)"
                " VALUES (?, ?, 80.0, '2026-08-01T00:00:00Z', 'legacy')",
                (problem.problem_id, problem.outcome_contract.primary_metric),
            )
        store = SQLiteWorkflowStore(db)
        legacy = store.latest_outcome(problem.problem_id)
        assert legacy is not None
        assert legacy.contract_revision is None and legacy.contract_snapshot is None
        assert legacy.checkpoint_kind is None and legacy.plan_id is None and legacy.execution_id is None
        legacy_snapshot = store.outcome_snapshot(problem)
        assert legacy_snapshot.status == "improving"  # scored under the current contract
        assert legacy_snapshot.measured_under_revision is None
        assert legacy_snapshot.contract_amended_after_measurement is False

        store.record_outcome(
            problem=problem,
            measurement=OutcomeMeasurement(
                problem_id=problem.problem_id,
                metric=problem.outcome_contract.primary_metric,
                observed_value=10.0,
                measured_at="2026-09-01T00:00:00Z",
                measurement_source="instrumented",
                checkpoint_kind="window",
                plan_id=12,
                execution_id="EXE-0003",
            ),
        )
        reopened = SQLiteWorkflowStore(db)
        stored = reopened.latest_outcome(problem.problem_id)
        assert stored is not None
        assert stored.contract_revision == 1
        assert stored.contract_snapshot == problem.outcome_contract
        assert stored.checkpoint_kind == "window"
        assert stored.plan_id == 12
        assert stored.execution_id == "EXE-0003"
        amended = problem.model_copy(
            update={"outcome_contract": problem.outcome_contract.model_copy(update={"success_threshold": 5.0, "revision": 2})}
        )
        snapshot = reopened.outcome_snapshot(amended)
        assert snapshot.status == "target_met"  # 10 <= 50 under the frozen revision 1
        assert snapshot.success_threshold == 5.0  # current terms shown
        assert snapshot.measured_under_revision == 1 and snapshot.contract_revision == 2
        assert snapshot.contract_amended_after_measurement is True
        assert snapshot.checkpoint_kind == "window"

    def test_execution_clock_columns_survive_reopen_and_upgrade_legacy_db(self, tmp_path: Path) -> None:
        db = tmp_path / "wf.db"
        with sqlite3.connect(db) as conn:
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
                    detail TEXT
                )
                """
            )
            conn.execute(
                "INSERT INTO executions"
                " (problem_id, action_id, destination, status, owner, summary, created_at)"
                " VALUES ('PRB-108', 'ACT-501', 'jira', 'draft_created', 'own', 'sum', '2026-07-01T00:00:00Z')"
            )
        store = SQLiteWorkflowStore(db)
        legacy = store.list_executions()[0]
        assert legacy.dispatched_at is None and legacy.implemented_at is None

        # A status update never invents a clock origin: only the push that
        # really left CLARA stamps dispatched_at (action_push passes it).
        pushed = store.update_execution(legacy.execution_id, status=ExecutionStatus.pushed, external_ref="CLARA-1")
        assert pushed.dispatched_at is None
        first_dispatch = "2026-07-02T00:00:00Z"
        stamped = store.update_execution(
            legacy.execution_id, status=ExecutionStatus.pushed, external_ref="CLARA-1", dispatched_at=first_dispatch
        )
        assert stamped.dispatched_at == first_dispatch
        again = store.update_execution(legacy.execution_id, status=ExecutionStatus.pushed, external_ref="CLARA-1")
        assert again.dispatched_at == first_dispatch  # kept, never overwritten by omission
        implemented = store.update_execution(
            legacy.execution_id,
            status=ExecutionStatus.pushed,
            external_ref="CLARA-1",
            implemented_at="2026-07-03T00:00:00Z",
            implementation_note="deployed",
        )
        assert implemented.implemented_at == "2026-07-03T00:00:00Z"

        reopened = SQLiteWorkflowStore(db)
        persisted = reopened.list_executions()[0]
        assert persisted.dispatched_at == first_dispatch
        assert persisted.implemented_at == "2026-07-03T00:00:00Z"
        assert persisted.implementation_note == "deployed"

        # Fresh approvals on the upgraded DB carry the columns through add/insert too.
        store.record_approval(
            problem=load_seed_problems()[0],
            decision=ApprovalDecision(action_id="ACT-501", decision="approved", reviewer="tester"),
        )
        newest = reopened.list_executions()[-1]
        assert newest.dispatched_at is None and newest.implemented_at is None

    def test_memory_store_never_invents_a_dispatch_instant(self) -> None:
        store = WorkflowStore()
        store.record_approval(
            problem=load_seed_problems()[0],
            decision=ApprovalDecision(action_id="ACT-501", decision="approved", reviewer="tester"),
        )
        execution = store.list_executions()[0]
        pushed = store.update_execution(execution.execution_id, status=ExecutionStatus.pushed, external_ref="X")
        assert pushed.dispatched_at is None  # a status flip is not a dispatch
        explicit = store.update_execution(
            execution.execution_id, status=ExecutionStatus.pushed, dispatched_at="2026-01-01T00:00:00Z"
        )
        assert explicit.dispatched_at == "2026-01-01T00:00:00Z"
        again = store.update_execution(execution.execution_id, status=ExecutionStatus.pushed, external_ref="X")
        assert again.dispatched_at == "2026-01-01T00:00:00Z"

    def test_sqlite_workflow_app_round_trips_the_snapshot(self, tmp_path: Path) -> None:
        app = _app(tmp_path, problem=_amendable_problem(), sqlite_workflows=True)
        client, problem = app["client"], app["problem"]
        pid = problem.problem_id
        client.post(
            f"/problems/{pid}/outcomes",
            json={
                "problem_id": pid,
                "metric": problem.outcome_contract.primary_metric,
                "observed_value": 80.0,
                "measured_at": _iso(NOW - timedelta(hours=1)),
            },
        )
        assert client.patch(f"/problems/{pid}/outcome-contract", json={"success_threshold": 90.0}).status_code == 200
        snapshot = client.get(f"/problems/{pid}/outcome").json()
        assert snapshot["status"] == "improving"
        assert snapshot["measured_under_revision"] == 1 and snapshot["contract_revision"] == 2
        assert snapshot["contract_amended_after_measurement"] is True
