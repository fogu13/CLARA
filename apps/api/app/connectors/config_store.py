"""Connector configuration store + Pydantic models.

Stores integration configs (credentials, field maps, project keys) keyed by
connector_type. SQLiteConnectorConfigStore persists them (a pilot's Jira config
must survive an API restart); the in-memory ConnectorConfigStore remains for
tests. ponytail: single-workspace keying for now; move to a workspace-scoped
Postgres `integrations` table when multi-tenant config matters.
"""

from __future__ import annotations

import json
import logging
import os
import sqlite3

from app.services.common import SerializedConnection
from pathlib import Path
from typing import Any

from pydantic import BaseModel

logger = logging.getLogger(__name__)

# --------------------------------------------------------------------------- #
# At-rest encryption for connector secrets (external-review item 20).
#
# CLARA_CONFIG_SECRET_KEY: a Fernet key — generate with
#   python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
# Unset -> plaintext storage (local dev) with a one-time warning. Sealed values
# carry the "enc:v1:" marker, so legacy plaintext rows keep loading and the
# next upsert re-seals them. cryptography ships via PyJWT[crypto] — no new dep.
# --------------------------------------------------------------------------- #
_ENC_PREFIX = "enc:v1:"
_warned_plaintext = False


def _fernet():
    key = os.getenv("CLARA_CONFIG_SECRET_KEY")
    if not key:
        return None
    from cryptography.fernet import Fernet

    return Fernet(key.encode())


def seal_config(config: dict[str, Any]) -> str:
    """Serialize a config dict for storage — encrypted when the key is set."""
    global _warned_plaintext
    raw = json.dumps(config)
    fernet = _fernet()
    if fernet is None:
        if not _warned_plaintext:
            logger.warning(
                "CLARA_CONFIG_SECRET_KEY is unset: connector secrets are stored in "
                "PLAINTEXT. Set the key in any real deployment."
            )
            _warned_plaintext = True
        return raw
    return _ENC_PREFIX + fernet.encrypt(raw.encode()).decode()


def unseal_config(stored: str | dict[str, Any]) -> dict[str, Any]:
    """Inverse of seal_config; also accepts legacy plaintext (str json or dict)."""
    if isinstance(stored, dict):
        return stored  # legacy Postgres payloads stored the dict directly
    if stored.startswith(_ENC_PREFIX):
        fernet = _fernet()
        if fernet is None:
            # Fail closed and loud: silently returning {} would look like a
            # deleted config and invite re-entry of secrets.
            raise RuntimeError(
                "Connector config is encrypted but CLARA_CONFIG_SECRET_KEY is unset"
            )
        return json.loads(fernet.decrypt(stored[len(_ENC_PREFIX):].encode()))
    return json.loads(stored)


class ConnectorConfig(BaseModel):
    """A stored connector configuration (credentials + settings)."""

    connector_type: str  # "zendesk", "jira", "slack", "webhook"
    config: dict[str, Any]  # connector-specific: subdomain, base_url, bot_token, etc.
    display_name: str = ""
    is_active: bool = True


class ConnectorConfigStore:
    """In-memory store for connector configurations (tests / ephemeral use)."""

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


class SQLiteConnectorConfigStore:
    """Persistent connector-config store — same interface as the in-memory one.

    Credentials live in the same local SQLite file as the rest of the workspace
    data (local-first: secrets never leave the deployment).
    """

    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._connection = SerializedConnection(self.path)
        self._connection.execute(
            """
            CREATE TABLE IF NOT EXISTS connector_configs (
                connector_type TEXT PRIMARY KEY,
                config TEXT NOT NULL,
                display_name TEXT NOT NULL DEFAULT '',
                is_active INTEGER NOT NULL DEFAULT 1
            )
            """
        )
        self._connection.commit()

    @staticmethod
    def _from_row(row: sqlite3.Row) -> ConnectorConfig:
        return ConnectorConfig(
            connector_type=row["connector_type"],
            config=unseal_config(row["config"]),
            display_name=row["display_name"],
            is_active=bool(row["is_active"]),
        )

    def list_configs(self) -> list[ConnectorConfig]:
        rows = self._connection.execute(
            "SELECT * FROM connector_configs ORDER BY connector_type"
        ).fetchall()
        return [self._from_row(row) for row in rows]

    def get_config(self, connector_type: str) -> ConnectorConfig | None:
        row = self._connection.execute(
            "SELECT * FROM connector_configs WHERE connector_type = ?", (connector_type,)
        ).fetchone()
        return self._from_row(row) if row else None

    def upsert_config(self, config: ConnectorConfig) -> ConnectorConfig:
        self._connection.execute(
            """
            INSERT INTO connector_configs (connector_type, config, display_name, is_active)
            VALUES (?, ?, ?, ?)
            ON CONFLICT (connector_type) DO UPDATE SET
                config = excluded.config,
                display_name = excluded.display_name,
                is_active = excluded.is_active
            """,
            (
                config.connector_type,
                seal_config(config.config),
                config.display_name,
                int(config.is_active),
            ),
        )
        self._connection.commit()
        return config

    def delete_config(self, connector_type: str) -> bool:
        cursor = self._connection.execute(
            "DELETE FROM connector_configs WHERE connector_type = ?", (connector_type,)
        )
        self._connection.commit()
        return cursor.rowcount > 0


def default_connector_config_store() -> ConnectorConfigStore:
    """Default empty in-memory store — kept for tests and ephemeral runs."""
    return ConnectorConfigStore()
