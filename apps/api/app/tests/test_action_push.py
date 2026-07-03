"""Tests for the real action push on approval (Sprint-0 N2).

Approving an action with a configured destination connector must fire the real
external write and record the result on the execution; failures must be recorded
without failing the approval; unconfigured destinations stay drafts.
"""

from __future__ import annotations

from typing import Any

from fastapi.testclient import TestClient

from app.connectors.config_store import ConnectorConfig, ConnectorConfigStore
from app.main import create_app
from app.services.problems import ProblemStore
from app.services.seed import load_seed_problems
from app.services.workflow import WorkflowStore

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

APPROVAL_BODY = {
    "action_id": "ACT-501",  # seed action with destination=jira
    "decision": "approved",
    "reviewer": "test_product_owner",
    "note": "Push it for real.",
}


def _client(configs: list[ConnectorConfig] | None = None) -> TestClient:
    return TestClient(
        create_app(
            problem_store=ProblemStore(load_seed_problems()),
            workflows=WorkflowStore(),
            connector_configs=ConnectorConfigStore(configs or []),
        )
    )


def _jira_execution(client: TestClient) -> dict[str, Any]:
    executions = client.get("/executions").json()
    return next(e for e in executions if e["action_id"] == "ACT-501")


class TestRealActionPush:
    def test_approval_pushes_real_jira_issue(self, httpx_mock: Any) -> None:
        httpx_mock.add_response(
            url="https://clara-demo.atlassian.net/rest/api/3/issue",
            method="POST",
            json={"id": "10001", "key": "CLARA-42", "self": "https://clara-demo/10001"},
            status_code=201,
        )

        client = _client([JIRA_CONFIG])
        response = client.post("/problems/PRB-108/approvals", json=APPROVAL_BODY)
        assert response.status_code == 200

        execution = _jira_execution(client)
        assert execution["status"] == "pushed"
        assert execution["external_ref"] == "CLARA-42"
        assert "CLARA-42" in execution["detail"]

    def test_connector_failure_recorded_but_approval_succeeds(self, httpx_mock: Any) -> None:
        httpx_mock.add_response(
            url="https://clara-demo.atlassian.net/rest/api/3/issue",
            method="POST",
            status_code=500,
            text="boom",
        )

        client = _client([JIRA_CONFIG])
        response = client.post("/problems/PRB-108/approvals", json=APPROVAL_BODY)
        assert response.status_code == 200  # approval never fails on push errors

        execution = _jira_execution(client)
        assert execution["status"] == "push_failed"
        assert execution["external_ref"] is None
        assert "500" in execution["detail"]

    def test_no_config_leaves_draft_with_note(self) -> None:
        client = _client([])  # no connectors configured
        response = client.post("/problems/PRB-108/approvals", json=APPROVAL_BODY)
        assert response.status_code == 200

        execution = _jira_execution(client)
        assert execution["status"] == "draft_created"
        assert "No active jira connector" in execution["detail"]

    def test_inactive_config_leaves_draft(self) -> None:
        inactive = JIRA_CONFIG.model_copy(update={"is_active": False})
        client = _client([inactive])
        client.post("/problems/PRB-108/approvals", json=APPROVAL_BODY)

        execution = _jira_execution(client)
        assert execution["status"] == "draft_created"

    def test_rejection_does_not_push(self, httpx_mock: Any) -> None:
        # httpx_mock would raise on any unexpected request; none must happen.
        client = _client([JIRA_CONFIG])
        response = client.post(
            "/problems/PRB-108/approvals",
            json={**APPROVAL_BODY, "decision": "rejected"},
        )
        assert response.status_code == 200
        assert client.get("/executions").json() == []


class TestSQLiteExecutionColumns:
    def test_update_execution_round_trip(self, tmp_path: Any) -> None:
        from app.domain.models import ApprovalDecision, ExecutionStatus
        from app.services.workflow import SQLiteWorkflowStore

        store = SQLiteWorkflowStore(tmp_path / "wf.db")
        problem = load_seed_problems()[0]
        store.record_approval(
            problem=problem,
            decision=ApprovalDecision(
                action_id="ACT-501", decision="approved", reviewer="tester"
            ),
        )
        execution = store.list_executions()[0]

        updated = store.update_execution(
            execution.execution_id,
            status=ExecutionStatus.pushed,
            external_ref="CLARA-7",
            detail="jira record created: CLARA-7",
        )
        assert updated.status == ExecutionStatus.pushed
        assert updated.external_ref == "CLARA-7"

        # Re-open the DB: the columns survive a restart (schema migration guard).
        reopened = SQLiteWorkflowStore(tmp_path / "wf.db")
        persisted = reopened.list_executions()[0]
        assert persisted.external_ref == "CLARA-7"
        assert persisted.status == ExecutionStatus.pushed
