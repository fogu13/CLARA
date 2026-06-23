"""Connector interface — sources (pull) and destinations (push).

Phase 2 target. First connectors to prove the brief's headline
("connects to sources ... pushes insights to other platforms"):
  - Zendesk source (pull): tickets/search -> signals via field map
  - Jira destination (push): create issue behind governance gate
  - Slack destination (push): chat.postMessage notify action

Reuses Elvis's api_poll field-mapping design
(reference/elvis/supabase/functions/sync-source/index.ts:79-160)
and replaces Odradek_2's local-only JiraIssueDraft
(apps/api/app/services/workflow.py:125-142).
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class SourceConnector(Protocol):
    """Pulls customer signals from an external system into the signal store."""

    connector_type: str  # e.g. "zendesk"

    def pull(self, config: dict[str, Any]) -> list[dict[str, Any]]:
        """Fetch new items and map them to canonical signal records.

        TODO(Phase 2): define the canonical signal dict shape (align with
        apps/api/app/domain/models.py SignalRecord).
        """
        ...


@runtime_checkable
class DestinationConnector(Protocol):
    """Pushes an approved action to an external system (close the loop)."""

    connector_type: str  # e.g. "jira", "slack"

    def push(self, action: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
        """Execute the action externally and return a result record with at
        minimum {external_id, status, raw}. Called only after governance approval.

        TODO(Phase 2): agree result schema with workflow.execute_action.
        """
        ...
