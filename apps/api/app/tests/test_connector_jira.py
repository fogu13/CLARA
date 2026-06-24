"""Tests for the Jira destination connector — issue creation."""

from __future__ import annotations

import base64
import json
from typing import Any

import pytest


def _jira_create_response(key: str = "PROJ-123") -> dict[str, Any]:
    return {
        "id": "10001",
        "key": key,
        "self": "https://company.atlassian.net/rest/api/3/issue/10001",
    }


def _make_action(
    *,
    action_type: str = "create_ticket",
    title: str = "Fix checkout crash",
    description: str = "Users report the checkout page crashes on payment step.",
    priority: int = 1,
    insight_title: str = "Checkout failure affecting 500 users",
    insight_summary: str = "Multiple users report checkout crashes.",
    insight_severity: str = "high",
    insight_signal_ids: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "type": action_type,
        "title": title,
        "description": description,
        "priority": priority,
        "insight_title": insight_title,
        "insight_summary": insight_summary,
        "insight_severity": insight_severity,
        "insight_signal_ids": insight_signal_ids or ["sig-1", "sig-2"],
    }


class TestJiraPush:
    def test_creates_issue_and_returns_key(self, httpx_mock: Any) -> None:
        from app.connectors.jira import JiraDestinationConnector

        httpx_mock.add_response(
            url="https://company.atlassian.net/rest/api/3/issue",
            method="POST",
            status_code=201,
            json=_jira_create_response("PROJ-42"),
        )

        connector = JiraDestinationConnector()
        result = connector.push(
            _make_action(),
            {
                "base_url": "https://company.atlassian.net",
                "email": "user@company.com",
                "api_token": "token",
                "project_key": "PROJ",
            },
        )

        assert result["external_id"] == "PROJ-42"
        assert result["status"] == "pushed"
        assert result["raw"]["jira_key"] == "PROJ-42"

    def test_uses_basic_auth(self, httpx_mock: Any) -> None:
        from app.connectors.jira import JiraDestinationConnector

        httpx_mock.add_response(
            url="https://company.atlassian.net/rest/api/3/issue",
            method="POST",
            status_code=201,
            json=_jira_create_response(),
        )

        connector = JiraDestinationConnector()
        connector.push(
            _make_action(),
            {
                "base_url": "https://company.atlassian.net",
                "email": "user@company.com",
                "api_token": "secret-token",
                "project_key": "PROJ",
            },
        )

        request = httpx_mock.get_requests()[-1]
        auth = request.headers.get("authorization", "")
        assert auth.startswith("Basic ")
        decoded = base64.b64decode(auth.removeprefix("Basic ")).decode()
        assert decoded == "user@company.com:secret-token"

    def test_sends_correct_project_key(self, httpx_mock: Any) -> None:
        from app.connectors.jira import JiraDestinationConnector

        httpx_mock.add_response(
            url="https://company.atlassian.net/rest/api/3/issue",
            method="POST",
            status_code=201,
            json=_jira_create_response(),
        )

        connector = JiraDestinationConnector()
        connector.push(
            _make_action(),
            {
                "base_url": "https://company.atlassian.net",
                "email": "u@c.com",
                "api_token": "t",
                "project_key": "FEEDBACK",
            },
        )

        body = json.loads(httpx_mock.get_requests()[-1].read())
        assert body["fields"]["project"]["key"] == "FEEDBACK"
        assert body["fields"]["issuetype"]["name"] == "Task"

    def test_maps_priority_correctly(self, httpx_mock: Any) -> None:
        from app.connectors.jira import JiraDestinationConnector

        httpx_mock.add_response(
            url="https://company.atlassian.net/rest/api/3/issue",
            method="POST",
            status_code=201,
            json=_jira_create_response(),
        )

        connector = JiraDestinationConnector()
        connector.push(
            _make_action(priority=1),
            {
                "base_url": "https://company.atlassian.net",
                "email": "u@c.com",
                "api_token": "t",
                "project_key": "PROJ",
            },
        )

        body = json.loads(httpx_mock.get_requests()[-1].read())
        assert body["fields"]["priority"]["name"] == "Highest"

    def test_includes_insight_context_in_description(self, httpx_mock: Any) -> None:
        from app.connectors.jira import JiraDestinationConnector

        httpx_mock.add_response(
            url="https://company.atlassian.net/rest/api/3/issue",
            method="POST",
            status_code=201,
            json=_jira_create_response(),
        )

        connector = JiraDestinationConnector()
        connector.push(
            _make_action(
                insight_title="Checkout crash",
                insight_summary="500 users affected",
                insight_severity="critical",
            ),
            {
                "base_url": "https://company.atlassian.net",
                "email": "u@c.com",
                "api_token": "t",
                "project_key": "PROJ",
            },
        )

        body = json.loads(httpx_mock.get_requests()[-1].read())
        desc_text = body["fields"]["description"]["content"][0]["content"][0]["text"]
        assert "Checkout crash" in desc_text
        assert "500 users affected" in desc_text
        assert "critical" in desc_text

    def test_raises_on_missing_config(self) -> None:
        from app.connectors.base import ConnectorError
        from app.connectors.jira import JiraDestinationConnector

        connector = JiraDestinationConnector()
        with pytest.raises(ConnectorError) as exc_info:
            connector.push(_make_action(), {"base_url": "https://x.atlassian.net"})

        assert "Missing Jira config" in str(exc_info.value)

    def test_raises_on_auth_failure(self, httpx_mock: Any) -> None:
        from app.connectors.base import ConnectorError
        from app.connectors.jira import JiraDestinationConnector

        httpx_mock.add_response(
            url="https://company.atlassian.net/rest/api/3/issue",
            method="POST",
            status_code=401,
            text="Unauthorized",
        )

        connector = JiraDestinationConnector()
        with pytest.raises(ConnectorError) as exc_info:
            connector.push(
                _make_action(),
                {
                    "base_url": "https://company.atlassian.net",
                    "email": "u@c.com",
                    "api_token": "wrong",
                    "project_key": "PROJ",
                },
            )

        assert "auth failed" in str(exc_info.value).lower()

    def test_includes_clara_labels(self, httpx_mock: Any) -> None:
        from app.connectors.jira import JiraDestinationConnector

        httpx_mock.add_response(
            url="https://company.atlassian.net/rest/api/3/issue",
            method="POST",
            status_code=201,
            json=_jira_create_response(),
        )

        connector = JiraDestinationConnector()
        connector.push(
            _make_action(),
            {
                "base_url": "https://company.atlassian.net",
                "email": "u@c.com",
                "api_token": "t",
                "project_key": "PROJ",
            },
        )

        body = json.loads(httpx_mock.get_requests()[-1].read())
        assert "clara" in body["fields"]["labels"]
        assert "customer-feedback" in body["fields"]["labels"]
