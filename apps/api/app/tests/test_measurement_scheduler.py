"""Tests for X1 — scheduled outcome re-measurement (the close-the-loop clock).

Covers: auto-captured signal-rate contracts on promoted problems, checkpoint
scheduling on approval, real-data auto-measurement at T+7, the manual_required
path for unobservable business metrics, and idempotency.
"""

from __future__ import annotations

from datetime import datetime, timedelta, UTC
from pathlib import Path

from fastapi.testclient import TestClient

from app.connectors.config_store import ConnectorConfigStore
from app.domain.models import SignalRecord
from app.main import create_app
from app.services.measurement_scheduler import SQLiteMeasurementPlanStore
from app.services.problems import ProblemStore
from app.services.seed import load_seed_problems
from app.services.signals import (
    SQLiteSignalStore,
    build_candidates,
    promote_candidate,
)
from app.services.telemetry import SQLiteTelemetryStore
from app.services.workflow import WorkflowStore

NOW = datetime(2026, 7, 3, 12, 0, tzinfo=UTC)


def _iso(dt: datetime) -> str:
    return dt.isoformat().replace("+00:00", "Z")


def _signal(signal_id: str, *, days_ago: float, journey: str = "checkout", stage: str = "payment") -> SignalRecord:
    return SignalRecord(
        signal_id=signal_id,
        customer_id=f"C-{signal_id}",
        account_id="A-1",
        source="webhook",
        journey=journey,
        journey_stage=stage,
        campaign_exposure=[],
        product_events=[],
        feedback_text=f"Payment problem report {signal_id}",
        language="en",
        timestamp=_iso(NOW - timedelta(days=days_ago)),
    )


# 10 signals over the 5 days BEFORE execution -> baseline ~2/day.
PRE_SIGNALS = [_signal(f"pre-{i}", days_ago=5 - i * 0.5) for i in range(10)]


def _promoted_problem():
    candidate = build_candidates(PRE_SIGNALS)[0]
    return promote_candidate(candidate)


class TestAutoCapturedContract:
    def test_promoted_contract_is_signal_derived(self) -> None:
        problem = _promoted_problem()
        contract = problem.outcome_contract
        assert contract.primary_metric.startswith("signal_rate_per_day:")
        assert contract.baseline > 0  # auto-captured from the candidate's own signals
        assert contract.success_threshold == round(contract.baseline * 0.5, 4)
        assert contract.comparison_method == "pre_post_signal_rate"


def _app(tmp_path: Path):
    problem = _promoted_problem()
    signal_store = SQLiteSignalStore(tmp_path / "signals.db")
    signal_store.import_signals(PRE_SIGNALS)
    plan_store = SQLiteMeasurementPlanStore(tmp_path / "plans.db")
    telemetry = SQLiteTelemetryStore(tmp_path / "telemetry.db")
    workflows = WorkflowStore()
    client = TestClient(
        create_app(
            problem_store=ProblemStore([*load_seed_problems(), problem]),
            workflows=workflows,
            signals=signal_store,
            connector_configs=ConnectorConfigStore(),
            telemetry=telemetry,
            measurement_plans=plan_store,
        )
    )
    return client, problem, signal_store, plan_store, telemetry


def _approve(client: TestClient, problem) -> None:
    response = client.post(
        f"/problems/{problem.problem_id}/approvals",
        json={
            "action_id": problem.action_proposals[0].action_id,
            "decision": "approved",
            "reviewer": "tester",
        },
    )
    assert response.status_code == 200


class TestSchedulingAndMeasurement:
    def test_approval_schedules_t7_and_window_checkpoints(self, tmp_path: Path) -> None:
        client, problem, _, plan_store, _ = _app(tmp_path)
        _approve(client, problem)

        plans = plan_store.list_plans()
        kinds = {plan["kind"] for plan in plans if plan["problem_id"] == problem.problem_id}
        assert kinds == {"t7", "window"}
        assert all(plan["status"] == "pending" for plan in plans)

        # Re-approving another action must not double-schedule the same checkpoints.
        client.post(
            f"/problems/{problem.problem_id}/approvals",
            json={
                "action_id": problem.action_proposals[0].action_id,
                "decision": "approved",
                "reviewer": "tester2",
            },
        )
        assert len(plan_store.list_plans()) == len(plans)

    def test_due_checkpoint_auto_measures_from_real_signals(self, tmp_path: Path) -> None:
        client, problem, signal_store, plan_store, telemetry = _app(tmp_path)
        _approve(client, problem)

        # After the action: complaints slow to ~0.25/day (2 in 8 days).
        signal_store.import_signals(
            [
                _signal("post-1", days_ago=-3),
                _signal("post-2", days_ago=-7),
            ]
        )

        eight_days_later = _iso(NOW + timedelta(days=8))
        response = client.post("/measurements/run-due", json={"now": eight_days_later})
        assert response.status_code == 200
        assert response.json()["measured"] >= 1

        snapshot = client.get(f"/problems/{problem.problem_id}/outcome").json()
        assert snapshot["latest_value"] is not None
        assert snapshot["latest_value"] < problem.outcome_contract.baseline  # rate dropped
        assert snapshot["status"] in ("improving", "target_met")

        done = [p for p in plan_store.list_plans() if p["status"] == "done"]
        assert len(done) == 1 and done[0]["kind"] == "t7"
        # window checkpoint (day 28) still pending
        assert any(p["status"] == "pending" and p["kind"] == "window" for p in plan_store.list_plans())

        events = [e for e in telemetry.list_events() if e["event_type"] == "outcome_recorded"]
        assert events and events[0]["metadata"]["real_data_source"] is True
        assert events[0]["metadata"]["source"] == "scheduler"

    def test_second_run_is_idempotent(self, tmp_path: Path) -> None:
        client, problem, _, _, _ = _app(tmp_path)
        _approve(client, problem)

        later = _iso(NOW + timedelta(days=8))
        first = client.post("/measurements/run-due", json={"now": later}).json()
        second = client.post("/measurements/run-due", json={"now": later}).json()
        assert first["measured"] >= 1
        assert second == {"measured": 0, "manual_required": 0, "skipped": 0}

    def test_business_metric_contract_becomes_manual_task(self, tmp_path: Path) -> None:
        client, _, _, plan_store, telemetry = _app(tmp_path)
        # Approve a SEED problem action — its contract metric (verification_completion_7d)
        # is not observable by CLARA and must never be auto-fabricated.
        response = client.post(
            "/problems/PRB-108/approvals",
            json={"action_id": "ACT-501", "decision": "approved", "reviewer": "tester"},
        )
        assert response.status_code == 200

        later = _iso(NOW + timedelta(days=40))
        result = client.post("/measurements/run-due", json={"now": later}).json()
        assert result["manual_required"] >= 1
        assert result["measured"] == 0

        manual = [p for p in plan_store.list_plans() if p["status"] == "manual_required"]
        assert manual and "human-recorded" in (manual[0]["note"] or "")
        assert any(e["event_type"] == "measurement_due" for e in telemetry.list_events())

        # And the outcome snapshot stays unmeasured — no invented data.
        snapshot = client.get("/problems/PRB-108/outcome").json()
        assert snapshot["latest_value"] is None

    def test_measurements_endpoint_lists_plans(self, tmp_path: Path) -> None:
        client, problem, _, _, _ = _app(tmp_path)
        _approve(client, problem)
        plans = client.get("/measurements").json()
        assert any(p["problem_id"] == problem.problem_id and p["kind"] == "t7" for p in plans)
