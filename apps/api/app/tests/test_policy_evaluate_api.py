"""Tests for POST /policy/evaluate — the side-effect-free per-call decision seam."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from app.main import create_app
from app.services.problems import ProblemStore
from app.services.seed import load_seed_problems
from app.services.telemetry import SQLiteTelemetryStore
from app.services.workflow import WorkflowStore


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


def test_workflow_shaped_envelope_blocks_on_missing_checks(tmp_path: Path) -> None:
    client, _ = _client(tmp_path)

    response = client.post(
        "/policy/evaluate",
        json={
            "source": "api",
            "destination": "zendesk",
            "governance_checks": [],
            "reference": "PRB-TEST/ACT-TEST",
        },
    )

    assert response.status_code == 200
    decision = response.json()
    assert decision["decision"] == "block"
    assert set(decision["applicable_rule_ids"]) == {
        "customer_contact_requires_consent_review",
        "customer_contact_requires_valid_consent",
        "sensitive_attribute_inference_prohibited",
    }
    assert decision["engine_version"]


def test_triage_shaped_envelope_blocks_on_compliance_category(tmp_path: Path) -> None:
    client, _ = _client(tmp_path)

    response = client.post(
        "/policy/evaluate",
        json={
            "source": "external_agent",
            "actor_type": "agent",
            "tool_name": "create_ticket",
            "data_categories": ["compliance_concern"],
        },
    )

    assert response.status_code == 200
    decision = response.json()
    assert decision["decision"] == "block"
    assert decision["blocking_rule_ids"] == ["compliance_concern_requires_review"]


def test_clean_envelope_allows_and_records_audit_event(tmp_path: Path) -> None:
    client, telemetry = _client(tmp_path)

    response = client.post(
        "/policy/evaluate",
        json={
            "source": "mcp",
            "actor_type": "agent",
            "tool_name": "list_problems",
            "reference": "demo-tool-call",
        },
    )

    assert response.status_code == 200
    assert response.json()["decision"] == "allow"
    events = [e for e in telemetry.list_events() if e["event_type"] == "policy_decision"]
    assert len(events) == 1
    assert events[0]["entity_id"] == "demo-tool-call"
    assert events[0]["metadata"]["source"] == "mcp"
    assert events[0]["metadata"]["actor_type"] == "agent"


def test_evaluate_mutates_no_workflow_state(tmp_path: Path) -> None:
    client, _ = _client(tmp_path)

    client.post(
        "/policy/evaluate",
        json={"source": "api", "destination": "zendesk", "governance_checks": []},
    )

    assert client.get("/approvals").json() == []
    assert client.get("/executions").json() == []


def test_evaluate_rejects_unknown_source(tmp_path: Path) -> None:
    client, _ = _client(tmp_path)

    response = client.post("/policy/evaluate", json={"source": "not_a_source"})

    assert response.status_code == 422
