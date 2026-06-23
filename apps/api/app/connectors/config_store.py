"""Connector configuration store + Pydantic models.

Stores integration configs (credentials, field maps, project keys) keyed by
connector_type. In-memory for the prototype; Postgres-backed in production
(via the integrations table pattern from Elvis).
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class ConnectorConfig(BaseModel):
    """A stored connector configuration (credentials + settings)."""

    connector_type: str  # "zendesk", "jira", "slack"
    config: dict[str, Any]  # connector-specific: subdomain, base_url, bot_token, etc.
    display_name: str = ""
    is_active: bool = True


class ConnectorConfigStore:
    """In-memory store for connector configurations.

    Keyed by connector_type. In production, backed by an `integrations` table
    (workspace_id-scoped, RLS-protected) like Elvis's Integrations page.
    """

    def __init__(self, configs: list[ConnectorConfig] | None = None) -> None:
        self._configs: dict[str, ConnectorConfig] = {}
        if configs:
            for c in configs:
                self._configs[c.connector_type] = c

    def list_configs(self) -> list[ConnectorConfig]:
        return list(self._configs.values())

    def get_config(self, connector_type: str) -> ConnectorConfig | None:
        return self._configs.get(connector_type)

    def upsert_config(self, config: ConnectorConfig) -> ConnectorConfig:
        self._configs[config.connector_type] = config
        return config

    def delete_config(self, connector_type: str) -> bool:
        if connector_type in self._configs:
            del self._configs[connector_type]
            return True
        return False


def default_connector_config_store() -> ConnectorConfigStore:
    """Default empty store — connectors are configured at runtime."""
    return ConnectorConfigStore()
