"""Slack destination connector (push).

Posts notifications to Slack channels via the Web API chat.postMessage method.
Implements the `notify` action type. Replaces Elvis's simulated notify
(evaluate-rules/index.ts:142-153, which returned {delivered: true} without
calling any API).

Auth: config = {
    "bot_token": "xoxb-...",
    "channel": "#customer-feedback"  (or channel ID)
}

Returns {external_id: "<channel>/<ts>", status, raw, audit}.
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

from app.connectors.base import ConnectorError

logger = logging.getLogger(__name__)


class SlackDestinationConnector:
    """Pushes notifications to Slack channels."""

    connector_type = "slack"

    def push(self, action: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
        """Post a Slack message about an approved action.

        Args:
            action: {type, title, description, insight_title, insight_summary,
                     insight_severity, ...}
            config: {bot_token, channel}

        Returns: {external_id: "<channel>/<ts>", status, raw, audit}
        Raises ConnectorError on failure.
        """
        bot_token = config.get("bot_token", "")
        channel = config.get("channel", "")

        if not bot_token:
            raise ConnectorError(
                "Missing Slack bot_token",
                connector="slack",
            )
        if not channel:
            raise ConnectorError(
                "Missing Slack channel (channel name or ID required)",
                connector="slack",
            )

        # Build the message from the action + insight context
        message = self._build_message(action, channel)

        headers = {
            "Authorization": f"Bearer {bot_token}",
            "Content-Type": "application/json",
        }

        url = "https://slack.com/api/chat.postMessage"

        try:
            with httpx.Client(timeout=30.0) as client:
                resp = client.post(url, headers=headers, json=message)
        except httpx.RequestError as exc:
            raise ConnectorError(
                f"Slack API unreachable: {exc}",
                connector="slack",
            ) from exc

        if resp.status_code != 200:
            raise ConnectorError(
                f"Slack API HTTP error {resp.status_code}: {resp.text[:200]}",
                connector="slack",
                status=resp.status_code,
            )

        data = resp.json()
        if not data.get("ok", False):
            error = data.get("error", "unknown_error")
            raise ConnectorError(
                f"Slack API returned error: {error}",
                connector="slack",
            )

        channel_id = data.get("channel", "")
        ts = data.get("ts", "")
        external_id = f"{channel_id}/{ts}"

        return {
            "external_id": external_id,
            "status": "pushed",
            "raw": {
                "channel": channel_id,
                "ts": ts,
                "message_ts": ts,
            },
            "audit": {
                "connector": "slack",
                "endpoint": url,
                "channel": channel,
                "limitations": [],
            },
        }

    def _build_message(self, action: dict[str, Any], channel: str) -> dict[str, Any]:
        """Build the Slack chat.postMessage payload.

        Uses Block Kit for a rich, actionable notification that includes
        the insight context and the proposed action.
        """
        insight_title = action.get("insight_title", "")
        insight_summary = action.get("insight_summary", "")
        insight_severity = action.get("insight_severity", "")
        action_title = action.get("title", "")
        action_description = action.get("description", "")

        # Severity emoji mapping
        severity_emoji = {
            "critical": "🔴",
            "high": "🟠",
            "medium": "🟡",
            "low": "🟢",
        }
        emoji = severity_emoji.get(insight_severity, "⚪")

        # Build Block Kit blocks
        blocks: list[dict[str, Any]] = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"{emoji} Customer Feedback Action",
                },
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": (
                        f"*{action_title}*\n{action_description}"
                        if action_description
                        else f"*{action_title}*"
                    ),
                },
            },
        ]

        # Add insight context if available
        if insight_title or insight_summary:
            context_lines: list[str] = []
            if insight_title:
                context_lines.append(f"📊 *Insight:* {insight_title}")
            if insight_summary:
                context_lines.append(f"📝 {insight_summary}")
            if insight_severity:
                context_lines.append(f"⚡ *Severity:* {insight_severity}")

            blocks.append({
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": "\n".join(context_lines),
                    }
                ],
            })

        # Add footer with provenance
        blocks.append({
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": "🤖 Sent by CLARA Feedback-to-Action Platform",
                }
            ],
        })

        return {
            "channel": channel,
            "blocks": blocks,
            "text": f"Customer feedback action: {action_title}",
        }
