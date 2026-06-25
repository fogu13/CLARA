from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from app.domain.models import WorkspaceSettings


class SQLiteWorkspaceStore:
    """Per-workspace settings persisted as a JSON blob keyed by workspace_id."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._connection = sqlite3.connect(self.path, check_same_thread=False)
        self._connection.row_factory = sqlite3.Row
        self._connection.execute(
            """
            CREATE TABLE IF NOT EXISTS workspace_settings (
                workspace_id INTEGER PRIMARY KEY,
                payload TEXT NOT NULL
            )
            """
        )
        self._connection.commit()

    def get(self, workspace_id: int) -> WorkspaceSettings:
        row = self._connection.execute(
            "SELECT payload FROM workspace_settings WHERE workspace_id = ?",
            (workspace_id,),
        ).fetchone()
        if row is None:
            return WorkspaceSettings()
        return WorkspaceSettings.model_validate(json.loads(row["payload"]))

    def put(self, workspace_id: int, settings: WorkspaceSettings) -> WorkspaceSettings:
        self._connection.execute(
            """
            INSERT INTO workspace_settings (workspace_id, payload)
            VALUES (?, ?)
            ON CONFLICT(workspace_id) DO UPDATE SET payload = excluded.payload
            """,
            (workspace_id, json.dumps(settings.model_dump())),
        )
        self._connection.commit()
        return settings
