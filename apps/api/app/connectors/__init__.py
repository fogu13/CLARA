"""Connector registry — source and destination connectors.

Phase 2: real Zendesk (in), Jira + Slack (out) connectors.
The registry maps connector_type strings to connector instances so the
LangGraph action node and FastAPI routes can look up the right connector
for a given integration config.
"""

from __future__ import annotations

from app.connectors.base import ConnectorError, DestinationConnector, SourceConnector
from app.connectors.jira import JiraDestinationConnector
from app.connectors.slack import SlackDestinationConnector
from app.connectors.app_store import AppStoreSourceConnector
from app.connectors.google_play import GooglePlaySourceConnector
from app.connectors.trustpilot import TrustpilotSourceConnector
from app.connectors.zendesk import ZendeskSourceConnector

# Registry: connector_type -> instance
SOURCES: dict[str, SourceConnector] = {
    "zendesk": ZendeskSourceConnector(),
    "app_store": AppStoreSourceConnector(),
    "trustpilot": TrustpilotSourceConnector(),
    "google_play": GooglePlaySourceConnector(),
}

DESTINATIONS: dict[str, DestinationConnector] = {
    "jira": JiraDestinationConnector(),
    "slack": SlackDestinationConnector(),
}


def get_source(connector_type: str) -> SourceConnector | None:
    """Look up a source connector by type."""
    return SOURCES.get(connector_type)


def get_destination(connector_type: str) -> DestinationConnector | None:
    """Look up a destination connector by type.

    Destination connectors are keyed by action type:
      - create_ticket -> jira
      - notify -> slack
      - create_segment -> (Phase 3: HubSpot/CDP)
      - draft_email -> (Phase 3: email platform)
    """
    return DESTINATIONS.get(connector_type)


# Action type -> destination connector type mapping
ACTION_TYPE_TO_DESTINATION: dict[str, str] = {
    "create_ticket": "jira",
    "notify": "slack",
    # Phase 3: "create_segment" -> "hubspot", "draft_email" -> "email"
}


def get_destination_for_action(action_type: str) -> DestinationConnector | None:
    """Look up the destination connector for a given action type."""
    dest_type = ACTION_TYPE_TO_DESTINATION.get(action_type)
    if not dest_type:
        return None
    return DESTINATIONS.get(dest_type)


__all__ = [
    "ConnectorError",
    "DestinationConnector",
    "SourceConnector",
    "ZendeskSourceConnector",
    "AppStoreSourceConnector",
    "TrustpilotSourceConnector",
    "GooglePlaySourceConnector",
    "JiraDestinationConnector",
    "SlackDestinationConnector",
    "SOURCES",
    "DESTINATIONS",
    "get_source",
    "get_destination",
    "get_destination_for_action",
    "ACTION_TYPE_TO_DESTINATION",
]
