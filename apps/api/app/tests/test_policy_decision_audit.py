"""Audit-trail tests: every gated consequential path leaves a policy_decision
telemetry event with rule/entity ids only (no personal data, no free text)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import create_app
from app.services.problems import ProblemStore
from app.services.seed import load_seed_problems
from app.services.telemetry import SQLiteTelemetryStore
from app.services.workflow import WorkflowStore
from app.tests.test_triage_graph import (
    _make_signals,
    _mock_enrich_signals,
    _mock_synthesize_insights,
)


def _client(tmp_path: Path) -> tuple[TestClient, SQLiteTelemetryStore]:
    telemetry = SQLiteTelemetryStore(tmp_path / "telemetry.db")
    client = TestClient(
        create_app(
            problem_store=ProblemStore(load_seed_problems()),
            workflows=WorkflowStore(),
            telemetry=telemetry,
        )
    )
    return client, telemetry


def _policy_events(telemetry: SQLiteTelemetryStore) -> list[dict]:
    return [e for e in telemetry.list_events() if e["event_type"] == "policy_decision"]


def test_approved_action_records_policy_decision_event(tmp_path: Path) -> None:
    client, telemetry = _client(tmp_path)

    response = client.post(
        "/problems/PRB-108/approvals",
        json={"action_id": "ACT-501", "decision": "approved", "reviewer": "tester"},
    )

    assert response.status_code == 200
    events = _policy_events(telemetry)
    assert len(events) == 1
    metadata = events[0]["metadata"]
    assert metadata["source"] == "workflow_approval"
    assert metadata["decision"] in ("allow", "needs_review")
    assert metadata["blocking_rule_ids"] == []
    assert metadata["reference"] == "PRB-108/ACT-501"


def test_blocked_approval_records_block_decision_event(tmp_path: Path) -> None:
    client, telemetry = _client(tmp_path)

    response = client.post(
        "/problems/PRB-108/approvals",
        json={"action_id": "ACT-502", "decision": "approved", "reviewer": "tester"},
    )

    assert response.status_code == 409
    events = _policy_events(telemetry)
    assert len(events) == 1
    metadata = events[0]["metadata"]
    assert metadata["decision"] == "block"
    assert "customer_contact_requires_consent_review" in metadata["blocking_rule_ids"]


def test_non_approved_decision_records_no_policy_event(tmp_path: Path) -> None:
    client, telemetry = _client(tmp_path)

    response = client.post(
        "/problems/PRB-108/approvals",
        json={"action_id": "ACT-501", "decision": "rejected", "reviewer": "tester"},
    )

    assert response.status_code == 200
    assert _policy_events(telemetry) == []


def test_triage_run_records_governance_summary_event(tmp_path: Path) -> None:
    client, telemetry = _client(tmp_path)

    with (
        patch("app.agents.triage_graph.enrich_signals", side_effect=_mock_enrich_signals),
        patch(
            "app.agents.triage_graph.synthesize_insights",
            side_effect=_mock_synthesize_insights,
        ),
    ):
        run = client.post("/triage/run", json={"signals": _make_signals(3)})

    assert run.status_code == 200
    events = _policy_events(telemetry)
    assert len(events) == 1
    metadata = events[0]["metadata"]
    assert metadata["source"] == "triage_graph"
    assert metadata["decision"] == "allow"  # ux_friction matches no seeded blocking rule
    assert metadata["blocking_rule_ids"] == []
    assert metadata["actor_type"] == "system"
