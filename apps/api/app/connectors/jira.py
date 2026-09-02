"""Jira destination connector (push).

Creates Jira issues from approved actions via the Jira Cloud REST API v3.
Replaces CLARA_2's local-only JiraIssueDraft (workflow.py:125-142, which
hardcoded project_key="ODR") with a real POST /rest/api/3/issue call.

Auth: config = {
    "base_url": "https://company.atlassian.net",
    "email": "user@company.com",
    "api_token": "...",
    "project_key": "PROJ",
}

Called only after governance approval — the action node passes approved
insight + action dicts. Returns {external_id, status, raw, audit}.
"""

from __future__ import annotations

import base64
import logging
from typing import Any

import httpx

from app.connectors.base import ConnectorError, validate_external_url

logger = logging.getLogger(__name__)


class JiraDestinationConnector:
    """Pushes approved actions to Jira as issues."""

    connector_type = "jira"

    def push(self, action: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
        """Create a Jira issue from an approved action.

        Args:
            action: {type, title, description, priority, insight_title,
                     insight_summary, insight_severity, ...}
            config: {base_url, email, api_token, project_key}

        Returns: {external_id: <Jira key>, status, raw, audit}
        Raises ConnectorError on failure.
        """
        base_url = config.get("base_url", "").rstrip("/")
        email = config.get("email", "")
        api_token = config.get("api_token", "")
        project_key = config.get("project_key", "")

        if not base_url or not email or not api_token or not project_key:
            raise ConnectorError(
                "Missing Jira config (base_url, email, api_token, project_key required)",
                connector="jira",
            )
        validate_external_url(base_url, connector="jira")  # SSRF guard on user-supplied URL

        # Build the issue payload from the action + insight context
        payload = self._build_issue_payload(action, project_key)

        # Jira Cloud uses basic auth with email/api_token
        auth_str = f"{email}:{api_token}"
        auth_b64 = base64.b64encode(auth_str.encode()).decode()
        headers = {
            "Authorization": f"Basic {auth_b64}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

        url = f"{base_url}/rest/api/3/issue"

        try:
            with httpx.Client(timeout=30.0) as client:
                resp = client.post(url, headers=headers, json=payload)
        except httpx.RequestError as exc:
            raise ConnectorError(
                f"Jira API unreachable: {exc}",
                connector="jira",
            ) from exc

        if resp.status_code == 401:
            raise ConnectorError(
                "Jira auth failed — check email and api_token",
                connector="jira",
                status=401,
            )
        if resp.status_code == 429:
            raise ConnectorError(
                "Jira rate limit exceeded — retry later",
                connector="jira",
                status=429,
            )
        if resp.status_code not in (200, 201):
            raise ConnectorError(
                f"Jira API error {resp.status_code}: {resp.text[:300]}",
                connector="jira",
                status=resp.status_code,
            )

        data = resp.json()
        issue_key = data.get("key", "")
        issue_id = data.get("id", "")

        return {
            "external_id": issue_key,
            "status": "pushed",
            "raw": {
                "jira_id": issue_id,
                "jira_key": issue_key,
                "self": data.get("self", ""),
            },
            "audit": {
                "connector": "jira",
                "endpoint": url,
                "project_key": project_key,
                "limitations": [],
            },
        }

    def _build_issue_payload(self, action: dict[str, Any], project_key: str) -> dict[str, Any]:
        """Build the Jira REST API v3 issue creation payload.

        Maps action priority (1-3) to Jira priority (Highest/High/Medium/Low).
        Includes insight context in the description for traceability.
        """
        priority_map = {1: "Highest", 2: "High", 3: "Medium"}
        action_priority = action.get("priority", 3)
        jira_priority = priority_map.get(action_priority, "Medium")

        insight_title = action.get("insight_title", "")
        insight_summary = action.get("insight_summary", "")
        insight_severity = action.get("insight_severity", "")
        signal_ids = action.get("insight_signal_ids", [])

        # Build description with insight context for traceability
        description_lines = [
            action.get("description", ""),
            "",
            "---",
            f"*Insight:* {insight_title}" if insight_title else "",
            f"*Summary:* {insight_summary}" if insight_summary else "",
            f"*Severity:* {insight_severity}" if insight_severity else "",
        ]
        if signal_ids:
            description_lines.append(f"*Signals:* {', '.join(signal_ids[:10])}")
        if action.get("problem_id"):
            description_lines.append(f"*CLARA problem:* {action['problem_id']}")
        if action.get("clara_url"):
            description_lines.append(f"*Open in CLARA:* {action['clara_url']}")
        description = "\n".join(line for line in description_lines if line)

        return {
            "fields": {
                "project": {"key": project_key},
                "summary": action.get("title", "Customer feedback action"),
                "description": {
                    "type": "doc",
                    "version": 1,
                    "content": [
                        {
                            "type": "paragraph",
                            "content": [
                                {"type": "text", "text": description},
                            ],
                        }
                    ],
                },
                "issuetype": {"name": "Task"},
                "priority": {"name": jira_priority},
                "labels": ["clara", "customer-feedback"],
            }
        }
