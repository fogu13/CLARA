"""Learning store — persist + load confidence-decayed learnings per workspace.

Closes the outcome -> learning -> retrieval loop: the outcome simulation
harness (and, in production, the measure/learn flow) persist learnings here;
synthesis retrieves the relevant ones via
``learning_engine.rank_learnings`` to inform future insights.

Local-first: SQLite by default (mirrors ``SQLiteWorkspaceStore``), keyed by
workspace_id. The Supabase/Postgres ``learning_conclusions`` table
(migration 005) is the production counterpart; this store is the local/offline
equivalent the thesis demo runs against.
"""

from __future__ import annotations

import json

from app.services.common import SerializedConnection
import uuid
from pathlib import Path
from typing import Any


class SQLiteLearningStore:
    """Learnings persisted as JSON blobs keyed by (workspace_id, conclusion_id)."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._connection = SerializedConnection(self.path)
        self._connection.execute(
            """
            CREATE TABLE IF NOT EXISTS learnings (
                workspace_id INTEGER NOT NULL,
                conclusion_id TEXT NOT NULL,
                topic TEXT,
                payload TEXT NOT NULL,
                PRIMARY KEY (workspace_id, conclusion_id)
            )
            """
        )
        self._connection.commit()

    def load(self, workspace_id: int = 1) -> list[dict[str, Any]]:
        rows = self._connection.execute(
            "SELECT payload FROM learnings WHERE workspace_id = ?",
            (workspace_id,),
        ).fetchall()
        return [json.loads(r["payload"]) for r in rows]

    def persist(
        self,
        learning: dict[str, Any],
        *,
        workspace_id: int = 1,
    ) -> dict[str, Any]:
        cid = learning.get("conclusion_id") or str(uuid.uuid4())
        stored = {**learning, "conclusion_id": cid}
        self._connection.execute(
            """
            INSERT INTO learnings (workspace_id, conclusion_id, topic, payload)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(workspace_id, conclusion_id) DO UPDATE SET
                topic = excluded.topic, payload = excluded.payload
            """,
            (workspace_id, cid, stored.get("topic", ""), json.dumps(stored)),
        )
        self._connection.commit()
        return stored

    def clear(self, workspace_id: int = 1) -> None:
        """Remove a workspace's learnings (the sim harness uses this for clean A/B)."""
        self._connection.execute(
            "DELETE FROM learnings WHERE workspace_id = ?", (workspace_id,)
        )
        self._connection.commit()
