"""Tests for the Slack destination connector — chat.postMessage."""

from __future__ import annotations

import json
from typing import Any

import pytest


def _slack_success_response(channel: str = "C123456", ts: str = "1690000000.000200") -> dict[str, Any]:
    return {
        "ok": True,
        "channel": channel,
        "ts": ts,
        "message": {
            "text": "test",
            "type": "message",
        },
    }


def _make_action(
    *,
    action_type: str = "notify",
    title: str = "High-severity checkout issue detected",
    description: str = "3 users reported checkout crashes in the last hour.",
    insight_title: str = "Checkout failure cluster",
    insight_summary: str = "Multiple users report crashes during payment.",
    insight_severity: str = "high",
) -> dict[str, Any]:
    return {
        "type": action_type,
        "title": title,
        "description": description,
        "priority": 1,
        "insight_title": insight_title,
        "insight_summary": insight_summary,
        "insight_severity": insight_severity,
        "insight_signal_ids": ["sig-1", "sig-2", "sig-3"],
    }


class TestSlackPush:
    def test_posts_message_and_returns_external_id(self, httpx_mock: Any) -> None:
        from app.connectors.slack import SlackDestinationConnector

        httpx_mock.add_response(
            url="https://slack.com/api/chat.postMessage",
            method="POST",
            json=_slack_success_response("C999", "1690000000.000500"),
        )

        connector = SlackDestinationConnector()
        result = connector.push(
            _make_action(),
            {"bot_token": "xoxb-123", "channel": "#customer-feedback"},
        )

        assert result["external_id"] == "C999/1690000000.000500"
        assert result["status"] == "pushed"
        assert result["raw"]["channel"] == "C999"

    def test_uses_bearer_auth(self, httpx_mock: Any) -> None:
        from app.connectors.slack import SlackDestinationConnector

        httpx_mock.add_response(
            url="https://slack.com/api/chat.postMessage",
            method="POST",
            json=_slack_success_response(),
        )

        connector = SlackDestinationConnector()
        connector.push(
            _make_action(),
            {"bot_token": "xoxb-secret-token", "channel": "C123"},
        )

        request = httpx_mock.get_requests()[-1]
        assert request.headers.get("authorization") == "Bearer xoxb-secret-token"

    def test_sends_to_correct_channel(self, httpx_mock: Any) -> None:
        from app.connectors.slack import SlackDestinationConnector

        httpx_mock.add_response(
            url="https://slack.com/api/chat.postMessage",
            method="POST",
            json=_slack_success_response(),
        )

        connector = SlackDestinationConnector()
        connector.push(
            _make_action(),
            {"bot_token": "xoxb-123", "channel": "#alerts"},
        )

        body = json.loads(httpx_mock.get_requests()[-1].read())
        assert body["channel"] == "#alerts"

    def test_includes_insight_context_in_blocks(self, httpx_mock: Any) -> None:
        from app.connectors.slack import SlackDestinationConnector

        httpx_mock.add_response(
            url="https://slack.com/api/chat.postMessage",
            method="POST",
            json=_slack_success_response(),
        )

        connector = SlackDestinationConnector()
        connector.push(
            _make_action(
                insight_title="Checkout crash",
                insight_summary="500 users affected",
                insight_severity="critical",
            ),
            {"bot_token": "xoxb-123", "channel": "#alerts"},
        )

        body = json.loads(httpx_mock.get_requests()[-1].read())
        blocks_text = json.dumps(body["blocks"])
        assert "Checkout crash" in blocks_text
        assert "500 users affected" in blocks_text
        assert "critical" in blocks_text

    def test_includes_severity_emoji(self, httpx_mock: Any) -> None:
        from app.connectors.slack import SlackDestinationConnector

        httpx_mock.add_response(
            url="https://slack.com/api/chat.postMessage",
            method="POST",
            json=_slack_success_response(),
        )

        connector = SlackDestinationConnector()
        connector.push(
            _make_action(insight_severity="critical"),
            {"bot_token": "xoxb-123", "channel": "#alerts"},
        )

        body = json.loads(httpx_mock.get_requests()[-1].read())
        header_block = body["blocks"][0]
        assert "🔴" in header_block["text"]["text"]

    def test_raises_on_missing_token(self) -> None:
        from app.connectors.base import ConnectorError
        from app.connectors.slack import SlackDestinationConnector

        connector = SlackDestinationConnector()
        with pytest.raises(ConnectorError) as exc_info:
            connector.push(_make_action(), {"channel": "#alerts"})

        assert "Missing Slack bot_token" in str(exc_info.value)

    def test_raises_on_missing_channel(self) -> None:
        from app.connectors.base import ConnectorError
        from app.connectors.slack import SlackDestinationConnector

        connector = SlackDestinationConnector()
        with pytest.raises(ConnectorError) as exc_info:
            connector.push(_make_action(), {"bot_token": "xoxb-123"})

        assert "Missing Slack channel" in str(exc_info.value)

    def test_raises_on_slack_api_error(self, httpx_mock: Any) -> None:
        from app.connectors.base import ConnectorError
        from app.connectors.slack import SlackDestinationConnector

        httpx_mock.add_response(
            url="https://slack.com/api/chat.postMessage",
            method="POST",
            json={"ok": False, "error": "channel_not_found"},
        )

        connector = SlackDestinationConnector()
        with pytest.raises(ConnectorError) as exc_info:
            connector.push(
                _make_action(),
                {"bot_token": "xoxb-123", "channel": "#nonexistent"},
            )

        assert "channel_not_found" in str(exc_info.value)

    def test_raises_on_http_error(self, httpx_mock: Any) -> None:
        from app.connectors.base import ConnectorError
        from app.connectors.slack import SlackDestinationConnector

        httpx_mock.add_response(
            url="https://slack.com/api/chat.postMessage",
            method="POST",
            status_code=500,
            text="Server error",
        )

        connector = SlackDestinationConnector()
        with pytest.raises(ConnectorError) as exc_info:
            connector.push(
                _make_action(),
                {"bot_token": "xoxb-123", "channel": "#alerts"},
            )

        assert "500" in str(exc_info.value)
