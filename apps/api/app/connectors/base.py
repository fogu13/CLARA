"""Connector interface — sources (pull) and destinations (push).

First connectors to prove the brief's headline
("connects to sources ... pushes insights to other platforms"):
  - Zendesk source (pull): tickets/search -> signals via field map
  - Jira destination (push): create issue behind governance gate
  - Slack destination (push): chat.postMessage notify action

Reuses Elvis's api_poll field-mapping design
(reference/elvis/supabase/functions/sync-source/index.ts:79-160)
and replaces CLARA_2's local-only JiraIssueDraft
(apps/api/app/services/workflow.py:125-142).
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class SourceConnector(Protocol):
    """Pulls customer signals from an external system into the signal store."""

    connector_type: str  # e.g. "zendesk"

    def pull(self, config: dict[str, Any]) -> list[dict[str, Any]]:
        """Fetch new items and map them to canonical signal dicts.

        Returns a list of signal dicts aligned with SignalRecord fields
        (signal_id, customer_id, account_id, source, journey, journey_stage,
        feedback_text, language, timestamp) plus a metadata block for
        deduplication (external_id, source_id).
        """
        ...


@runtime_checkable
class DestinationConnector(Protocol):
    """Pushes an approved action to an external system (close the loop)."""

    connector_type: str  # e.g. "jira", "slack"

    def push(self, action: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
        """Execute the action externally and return a result record:
        {external_id, status, raw, audit}.
        Called only after governance approval.
        """
        ...


class ConnectorError(RuntimeError):
    """Base error for connector failures. Non-fatal — logged, not raised."""

    def __init__(self, message: str, connector: str = "", status: int | None = None) -> None:
        super().__init__(message)
        self.connector = connector
        self.status = status
