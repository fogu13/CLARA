"""Tests for connector integration in the LangGraph action node.

Verifies that the action node:
  - Calls real Jira/Slack connectors when configured
  - Gracefully handles missing connector configs (no_config)
  - Gracefully handles unregistered action types (no_connector)
  - Records connector failures as non-fatal (failed status + error message)
"""

from __future__ import annotations

from typing import Any
from unittest.mock import patch

import pytest
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command


@pytest.fixture
def _mock_ai_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AI_BASE_URL", "http://test-ai.local/v1")
    monkeypatch.setenv("AI_API_KEY", "")
    monkeypatch.setenv("AI_MODEL", "test-model")
    monkeypatch.delenv("LANGFUSE_PUBLIC_KEY", raising=False)
    monkeypatch.delenv("LANGFUSE_SECRET_KEY", raising=False)
    import importlib

    import app.agents.triage_graph as graph_mod
    import app.services.ai as ai_mod
    import app.services.enrichment as enr_mod
    import app.services.synthesis as syn_mod

    importlib.reload(ai_mod)
    importlib.reload(enr_mod)
    importlib.reload(syn_mod)
    importlib.reload(graph_mod)


def _mock_enrich(signals: list[dict]) -> list[dict]:
    return [
        {
            "id": s["id"],
            "sentiment": "negative",
            "sentiment_score": -0.7,
            "urgency": "high",
            "tags": ["checkout_failure"],
        }
        for s in signals
    ]


def _mock_synthesize(enriched: list[dict], **kw: Any) -> list[dict]:
    return [
        {
            "title": "Checkout failure",
            "summary": "Users report crashes",
            "category": "ux_friction",
            "impact_score": 8.0,
            "confidence": 0.9,
            "target_team": "engineering",
            "suggested_actions": [
                {
                    "type": "create_ticket",
                    "title": "Fix checkout",
                    "description": "Investigate crash",
                    "priority": 1,
                },
                {
                    "type": "notify",
                    "title": "Alert team",
                    "description": "Notify engineering",
                    "priority": 1,
                },
            ],
            "severity": "high",
            "signal_ids": [s["id"] for s in enriched],
            "qual_signal_count": len(enriched),
            "quant_signal_count": 0,
            "affected_contacts": len(enriched),
            "max_urgency": "high",
            "tag": "checkout_failure",
            "status": "new",
            "audit": {"model": "test", "source": "llm_synthesis"},
        }
    ]


def _make_signals(n: int = 3) -> list[dict]:
    return [
        {"signal_id": f"sig-{i}", "feedback_text": f"Checkout crashed {i}", "signal_type": "qualitative"}
        for i in range(n)
    ]


class TestActionNodeWithConnectors:
    def test_jira_push_on_approval(self, _mock_ai_env: None, httpx_mock: Any) -> None:
        from app.agents.triage_graph import build_triage_graph

        graph = build_triage_graph(checkpointer=MemorySaver())
        config = {"configurable": {"thread_id": "test-jira-push"}}

        # Mock Jira API: issue creation
        httpx_mock.add_response(
            url="https://test.atlassian.net/rest/api/3/issue",
            method="POST",
            status_code=201,
            json={"id": "10001", "key": "PROJ-42", "self": "..."},
        )

        with (
            patch("app.agents.triage_graph.enrich_signals", side_effect=_mock_enrich),
            patch("app.agents.triage_graph.synthesize_insights", side_effect=_mock_synthesize),
        ):
            graph.invoke(
                {
                    "signals": _make_signals(3),
                    "connector_configs": {
                        "jira": {
                            "base_url": "https://test.atlassian.net",
                            "email": "u@c.com",
                            "api_token": "tok",
                            "project_key": "PROJ",
                        }
                    },
                },
                config=config,
            )
            result = graph.invoke(Command(resume="approved"), config=config)

        actions = result.get("action_results", [])
        jira_actions = [a for a in actions if a["action_type"] == "create_ticket"]
        assert len(jira_actions) == 1
        assert jira_actions[0]["external_id"] == "PROJ-42"
        assert jira_actions[0]["status"] == "pushed"

    def test_slack_push_on_approval(self, _mock_ai_env: None, httpx_mock: Any) -> None:
        from app.agents.triage_graph import build_triage_graph

        graph = build_triage_graph(checkpointer=MemorySaver())
        config = {"configurable": {"thread_id": "test-slack-push"}}

        httpx_mock.add_response(
            url="https://slack.com/api/chat.postMessage",
            method="POST",
            json={"ok": True, "channel": "C999", "ts": "1690000000.000500"},
        )

        with (
            patch("app.agents.triage_graph.enrich_signals", side_effect=_mock_enrich),
            patch("app.agents.triage_graph.synthesize_insights", side_effect=_mock_synthesize),
        ):
            graph.invoke(
                {
                    "signals": _make_signals(3),
                    "connector_configs": {
                        "slack": {"bot_token": "xoxb-test", "channel": "#alerts"}
                    },
                },
                config=config,
            )
            result = graph.invoke(Command(resume="approved"), config=config)

        actions = result.get("action_results", [])
        slack_actions = [a for a in actions if a["action_type"] == "notify"]
        assert len(slack_actions) == 1
        assert slack_actions[0]["status"] == "pushed"
        assert "C999" in slack_actions[0]["external_id"]

    def test_no_config_records_no_config_status(self, _mock_ai_env: None) -> None:
        from app.agents.triage_graph import build_triage_graph

        graph = build_triage_graph(checkpointer=MemorySaver())
        config = {"configurable": {"thread_id": "test-no-config"}}

        with (
            patch("app.agents.triage_graph.enrich_signals", side_effect=_mock_enrich),
            patch("app.agents.triage_graph.synthesize_insights", side_effect=_mock_synthesize),
        ):
            graph.invoke({"signals": _make_signals(3)}, config=config)
            result = graph.invoke(Command(resume="approved"), config=config)

        actions = result.get("action_results", [])
        assert all(a["status"] == "no_config" for a in actions)
        assert all(a["external_id"] is None for a in actions)

    def test_connector_failure_is_non_fatal(self, _mock_ai_env: None, httpx_mock: Any) -> None:
        from app.agents.triage_graph import build_triage_graph

        graph = build_triage_graph(checkpointer=MemorySaver())
        config = {"configurable": {"thread_id": "test-conn-fail"}}

        # Mock Jira returning 500
        httpx_mock.add_response(
            url="https://test.atlassian.net/rest/api/3/issue",
            method="POST",
            status_code=500,
            text="Internal server error",
        )

        with (
            patch("app.agents.triage_graph.enrich_signals", side_effect=_mock_enrich),
            patch("app.agents.triage_graph.synthesize_insights", side_effect=_mock_synthesize),
        ):
            graph.invoke(
                {
                    "signals": _make_signals(3),
                    "connector_configs": {
                        "jira": {
                            "base_url": "https://test.atlassian.net",
                            "email": "u@c.com",
                            "api_token": "tok",
                            "project_key": "PROJ",
                        }
                    },
                },
                config=config,
            )
            result = graph.invoke(Command(resume="approved"), config=config)

        actions = result.get("action_results", [])
        jira_actions = [a for a in actions if a["action_type"] == "create_ticket"]
        assert len(jira_actions) == 1
        assert jira_actions[0]["status"] == "failed"
        assert jira_actions[0]["external_id"] is None
        assert "error" in jira_actions[0]["audit"]

        # Graph should still complete (non-fatal)
        assert result["status"] == "learned"

        # Error should be accumulated
        errors = result.get("errors", [])
        assert any("jira" in e.lower() or "connector" in e.lower() for e in errors)

    def test_both_jira_and_slack_push(self, _mock_ai_env: None, httpx_mock: Any) -> None:
        from app.agents.triage_graph import build_triage_graph

        graph = build_triage_graph(checkpointer=MemorySaver())
        config = {"configurable": {"thread_id": "test-both-push"}}

        httpx_mock.add_response(
            url="https://test.atlassian.net/rest/api/3/issue",
            method="POST",
            status_code=201,
            json={"id": "1", "key": "PROJ-1", "self": ""},
        )
        httpx_mock.add_response(
            url="https://slack.com/api/chat.postMessage",
            method="POST",
            json={"ok": True, "channel": "C1", "ts": "123.456"},
        )

        with (
            patch("app.agents.triage_graph.enrich_signals", side_effect=_mock_enrich),
            patch("app.agents.triage_graph.synthesize_insights", side_effect=_mock_synthesize),
        ):
            graph.invoke(
                {
                    "signals": _make_signals(3),
                    "connector_configs": {
                        "jira": {
                            "base_url": "https://test.atlassian.net",
                            "email": "u@c.com",
                            "api_token": "tok",
                            "project_key": "PROJ",
                        },
                        "slack": {"bot_token": "xoxb-test", "channel": "#alerts"},
                    },
                },
                config=config,
            )
            result = graph.invoke(Command(resume="approved"), config=config)

        actions = result.get("action_results", [])
        assert len(actions) == 2
        statuses = {a["action_type"]: a["status"] for a in actions}
        assert statuses["create_ticket"] == "pushed"
        assert statuses["notify"] == "pushed"


class TestConnectorRegistry:
    def test_get_destination_for_create_ticket(self) -> None:
        from app.connectors import get_destination_for_action

        dest = get_destination_for_action("create_ticket")
        assert dest is not None
        assert dest.connector_type == "jira"

    def test_get_destination_for_notify(self) -> None:
        from app.connectors import get_destination_for_action

        dest = get_destination_for_action("notify")
        assert dest is not None
        assert dest.connector_type == "slack"

    def test_get_destination_for_unknown_action(self) -> None:
        from app.connectors import get_destination_for_action

        assert get_destination_for_action("unknown_type") is None

    def test_get_source_zendesk(self) -> None:
        from app.connectors import get_source

        src = get_source("zendesk")
        assert src is not None
        assert src.connector_type == "zendesk"


class TestConnectorConfigStore:
    def test_upsert_and_get(self) -> None:
        from app.connectors.config_store import ConnectorConfig, ConnectorConfigStore

        store = ConnectorConfigStore()
        cfg = ConnectorConfig(
            connector_type="jira",
            config={"base_url": "https://test.atlassian.net", "project_key": "PROJ"},
        )
        store.upsert_config(cfg)

        retrieved = store.get_config("jira")
        assert retrieved is not None
        assert retrieved.config["project_key"] == "PROJ"

    def test_delete(self) -> None:
        from app.connectors.config_store import ConnectorConfig, ConnectorConfigStore

        store = ConnectorConfigStore()
        store.upsert_config(ConnectorConfig(connector_type="slack", config={"bot_token": "xoxb"}))
        assert store.delete_config("slack") is True
        assert store.get_config("slack") is None

    def test_list_configs(self) -> None:
        from app.connectors.config_store import ConnectorConfig, ConnectorConfigStore

        store = ConnectorConfigStore([
            ConnectorConfig(connector_type="jira", config={}),
            ConnectorConfig(connector_type="slack", config={}),
        ])
        configs = store.list_configs()
        assert len(configs) == 2
