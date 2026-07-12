"""EU AI Act Art. 50(4) editorial-review productisation (W2).

Approved executions carry a first-class human-review stamp and push verbatim
(Art. 50(4) exemption); anything pushed without that stamp gets the workspace's
AI-disclosure line appended and `disclosure_applied` recorded; /article50-status
aggregates both for the compliance page.
"""

from __future__ import annotations

import json
import sqlite3
from typing import Any

from fastapi.testclient import TestClient

from app.connectors.config_store import ConnectorConfig, ConnectorConfigStore
from app.domain.models import ExecutionRecord, ExecutionStatus, WorkspaceSettings
from app.main import create_app
from app.services.action_push import push_approved_action
from app.services.problems import ProblemStore
from app.services.seed import load_seed_problems
from app.services.workflow import WorkflowStore, find_action
from app.services.workspace import SQLiteWorkspaceStore

DEFAULT_DISCLOSURE = WorkspaceSettings().ai_disclosure_template

JIRA_URL = "https://clara-demo.atlassian.net/rest/api/3/issue"

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
    "note": "Reviewed and released.",
}


def _client(tmp_path, workflows: WorkflowStore | None = None) -> TestClient:
    return TestClient(
        create_app(
            problem_store=ProblemStore(load_seed_problems()),
            workflows=workflows or WorkflowStore(),
            connector_configs=ConnectorConfigStore([JIRA_CONFIG]),
            workspace=SQLiteWorkspaceStore(tmp_path / "workspace.db"),
        )
    )


def _jira_description(httpx_mock: Any) -> str:
    body = json.loads(httpx_mock.get_requests()[-1].read())
    return body["fields"]["description"]["content"][0]["content"][0]["text"]


def _action_text(jira_description: str) -> str:
    """The CLARA-authored text: the Jira connector appends an insight-context
    trailer ('---', Insight/Summary/Severity) after the pushed description."""
    return jira_description.split("\n---")[0].rstrip("\n")


def _auto_execution(problem_id: str = "PRB-109", action_id: str = "ACT-511") -> ExecutionRecord:
    """An execution that never went through the approval gate (no review stamp)."""
    return ExecutionRecord(
        execution_id="EXE-9001",
        problem_id=problem_id,
        action_id=action_id,
        destination="jira",
        status=ExecutionStatus.draft_created,
        owner="automation",
        summary="Auto-published draft (no human review).",
        created_at="2026-07-12T09:00:00+00:00",
    )


class TestHumanReviewStamp:
    def test_approved_push_carries_stamp_and_no_disclosure(self, tmp_path, httpx_mock: Any) -> None:
        httpx_mock.add_response(
            url=JIRA_URL, method="POST", json={"id": "10001", "key": "CLARA-42"}, status_code=201
        )

        client = _client(tmp_path)
        approval = client.post("/problems/PRB-108/approvals", json=APPROVAL_BODY)
        assert approval.status_code == 200

        execution = next(
            e for e in client.get("/executions").json() if e["action_id"] == "ACT-501"
        )
        assert execution["status"] == "pushed"
        assert execution["human_reviewed"] is True
        assert execution["reviewed_by"] == "test_product_owner"
        assert execution["reviewed_at"] == approval.json()["created_at"]
        assert execution["disclosure_applied"] is False
        # Art. 50(4) exemption: reviewed content leaves without the AI label.
        assert DEFAULT_DISCLOSURE not in _jira_description(httpx_mock)

    def test_sqlite_stamp_survives_reopen(self, tmp_path) -> None:
        from app.domain.models import ApprovalDecision
        from app.services.workflow import SQLiteWorkflowStore

        store = SQLiteWorkflowStore(tmp_path / "wf.db")
        store.record_approval(
            problem=load_seed_problems()[0],
            decision=ApprovalDecision(action_id="ACT-501", decision="approved", reviewer="tester"),
        )
        execution = store.list_executions()[0]
        assert execution.human_reviewed is True
        assert execution.reviewed_by == "tester"
        assert execution.reviewed_at == execution.created_at

        store.update_execution(
            execution.execution_id,
            status=ExecutionStatus.pushed,
            external_ref="CLARA-7",
            disclosure_applied=True,
        )

        reopened = SQLiteWorkflowStore(tmp_path / "wf.db")
        persisted = reopened.list_executions()[0]
        assert persisted.human_reviewed is True
        assert persisted.reviewed_by == "tester"
        assert persisted.disclosure_applied is True

    def test_sqlite_ensure_column_upgrades_existing_db(self, tmp_path) -> None:
        from app.services.workflow import SQLiteWorkflowStore

        # A database written before W2: executions table without the Art. 50 columns.
        db_path = tmp_path / "wf.db"
        with sqlite3.connect(db_path) as conn:
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
                " VALUES ('PRB-108', 'ACT-501', 'jira', 'draft_created', 'own', 'sum',"
                " '2026-07-01T00:00:00+00:00')"
            )

        store = SQLiteWorkflowStore(db_path)
        legacy = store.list_executions()[0]
        assert legacy.human_reviewed is False
        assert legacy.reviewed_by is None
        assert legacy.disclosure_applied is False

        updated = store.update_execution(
            legacy.execution_id, status=ExecutionStatus.pushed, disclosure_applied=True
        )
        assert updated.disclosure_applied is True


class TestDisclosureLine:
    def test_non_reviewed_push_gets_disclosure_and_flag(self, httpx_mock: Any) -> None:
        httpx_mock.add_response(
            url=JIRA_URL, method="POST", json={"id": "10002", "key": "CLARA-43"}, status_code=201
        )

        store = WorkflowStore()
        execution = _auto_execution()
        store._executions.append(execution)
        problem = next(p for p in load_seed_problems() if p.problem_id == "PRB-109")

        pushed = push_approved_action(
            problem=problem,
            action=find_action(problem, "ACT-511"),
            execution=execution,
            config_store=ConnectorConfigStore([JIRA_CONFIG]),
            workflow_store=store,
            disclosure_template=DEFAULT_DISCLOSURE,
        )

        assert pushed.status == ExecutionStatus.pushed
        assert pushed.disclosure_applied is True
        assert store.list_executions()[0].disclosure_applied is True
        assert _action_text(_jira_description(httpx_mock)).endswith(DEFAULT_DISCLOSURE)

    def test_connector_test_push_carries_default_disclosure(self, tmp_path, httpx_mock: Any) -> None:
        httpx_mock.add_response(
            url=JIRA_URL, method="POST", json={"id": "10003", "key": "CLARA-44"}, status_code=201
        )

        client = _client(tmp_path)
        response = client.post("/connectors/test/jira", json=JIRA_CONFIG.config)
        assert response.json()["status"] == "ok"
        assert _action_text(_jira_description(httpx_mock)).endswith(DEFAULT_DISCLOSURE)

    def test_connector_test_slack_carries_disclosure(self, tmp_path, httpx_mock: Any) -> None:
        httpx_mock.add_response(
            url="https://slack.com/api/chat.postMessage",
            method="POST",
            json={"ok": True, "channel": "C1", "ts": "1726000000.1"},
        )

        client = _client(tmp_path)
        response = client.post(
            "/connectors/test/slack", json={"bot_token": "xoxb-1", "channel": "#alerts"}
        )
        assert response.json()["status"] == "ok"

        body = json.loads(httpx_mock.get_requests()[-1].read())
        section_text = body["blocks"][1]["text"]["text"]
        assert section_text.endswith(DEFAULT_DISCLOSURE)

    def test_custom_template_from_workspace_settings(self, tmp_path, httpx_mock: Any) -> None:
        httpx_mock.add_response(
            url=JIRA_URL, method="POST", json={"id": "10004", "key": "CLARA-45"}, status_code=201
        )

        client = _client(tmp_path)
        settings = client.get("/workspace").json()
        settings["ai_disclosure_template"] = "Custom AI note (Art. 50)."
        assert client.put("/workspace", json=settings).status_code == 200

        client.post("/connectors/test/jira", json=JIRA_CONFIG.config)
        description = _jira_description(httpx_mock)
        assert _action_text(description).endswith("Custom AI note (Art. 50).")
        assert DEFAULT_DISCLOSURE not in description


class TestArticle50Status:
    def test_counts_after_one_reviewed_and_one_auto_push(self, tmp_path, httpx_mock: Any) -> None:
        httpx_mock.add_response(
            url=JIRA_URL, method="POST", json={"id": "10005", "key": "CLARA-46"}, status_code=201
        )
        httpx_mock.add_response(
            url=JIRA_URL, method="POST", json={"id": "10006", "key": "CLARA-47"}, status_code=201
        )

        store = WorkflowStore()
        client = _client(tmp_path, workflows=store)
        assert client.post("/problems/PRB-108/approvals", json=APPROVAL_BODY).status_code == 200

        execution = _auto_execution()
        store._executions.append(execution)
        problem = next(p for p in load_seed_problems() if p.problem_id == "PRB-109")
        push_approved_action(
            problem=problem,
            action=find_action(problem, "ACT-511"),
            execution=execution,
            config_store=ConnectorConfigStore([JIRA_CONFIG]),
            workflow_store=store,
            disclosure_template=DEFAULT_DISCLOSURE,
        )

        status = client.get("/article50-status").json()
        assert status["human_reviewed"]["count"] == 1
        assert status["human_reviewed"]["latest_at"] is not None
        assert status["auto_published"] == {
            "count": 1,
            "disclosed_count": 1,
            "latest_at": execution.created_at,
        }
        assert status["by_destination"] == [
            {"destination": "jira", "human_reviewed": 1, "disclosed": 1}
        ]
        assert status["generated_at"]

    def test_empty_store_returns_zero_counts(self, tmp_path) -> None:
        status = _client(tmp_path).get("/article50-status").json()
        assert status["human_reviewed"] == {"count": 0, "latest_at": None}
        assert status["auto_published"] == {"count": 0, "disclosed_count": 0, "latest_at": None}
        assert status["by_destination"] == []
