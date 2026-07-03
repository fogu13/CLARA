"""Product telemetry — append-only event log powering the pilot/VC metrics.

Records the events needed for: time-to-first-insight, approval-cycle time,
% auto-triaged, outcome-contract completion, learning-reuse rate. Local-first
SQLite here; the Postgres side already exists as `public.events` (migration 005,
RLS'd) and a Postgres store can adopt it later with the same interface.

Named "telemetry" (not product_events) to avoid colliding with the existing
`product_events` field on SignalRecord, which means product *usage* events.

No external analytics vendor by design: events stay in the customer's database
(EU residency — an empty subprocessor register is part of the sales story).
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from app.services.common import utc_now


class SQLiteTelemetryStore:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._connection = sqlite3.connect(self.path, check_same_thread=False)
        self._connection.row_factory = sqlite3.Row
        self._connection.execute(
            """
            CREATE TABLE IF NOT EXISTS telemetry_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                workspace_id INTEGER NOT NULL DEFAULT 1,
                event_type TEXT NOT NULL,
                entity_id TEXT,
                metadata TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL
            )
            """
        )
        self._connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_telemetry_type_time"
            " ON telemetry_events (event_type, created_at)"
        )
        self._connection.commit()

    def record(
        self,
        event_type: str,
        *,
        entity_id: str | None = None,
        metadata: dict[str, Any] | None = None,
        workspace_id: int = 1,
    ) -> None:
        """Append one event. Never raises — telemetry must not break a request."""
        try:
            self._connection.execute(
                "INSERT INTO telemetry_events"
                " (workspace_id, event_type, entity_id, metadata, created_at)"
                " VALUES (?, ?, ?, ?, ?)",
                (
                    workspace_id,
                    event_type,
                    entity_id,
                    json.dumps(metadata or {}),
                    utc_now(),
                ),
            )
            self._connection.commit()
        except sqlite3.Error:  # ponytail: swallow — metrics never break the product
            pass

    def list_events(self, *, limit: int = 500) -> list[dict[str, Any]]:
        rows = self._connection.execute(
            "SELECT * FROM telemetry_events ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
        return [
            {
                "id": row["id"],
                "workspace_id": row["workspace_id"],
                "event_type": row["event_type"],
                "entity_id": row["entity_id"],
                "metadata": json.loads(row["metadata"]),
                "created_at": row["created_at"],
            }
            for row in rows
        ]

    def counts_by_type(self) -> dict[str, int]:
        rows = self._connection.execute(
            "SELECT event_type, COUNT(*) AS n FROM telemetry_events GROUP BY event_type"
        ).fetchall()
        return {row["event_type"]: row["n"] for row in rows}
