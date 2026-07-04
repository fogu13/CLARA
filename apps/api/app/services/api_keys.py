"""API keys: machine-to-machine access without borrowing a browser session.

Key format: clara_sk_<32 hex>. Only the SHA-256 hash is stored; the plaintext
is returned exactly once at creation. Keys carry a role (viewer/editor/admin)
and act through the same require_role gates as JWT users, so nothing about
the authorization model changes — an API key is just another identity.
"""

from __future__ import annotations

import hashlib
import secrets
from pathlib import Path
from typing import Any

from app.services.common import SerializedConnection, utc_now

KEY_PREFIX = "clara_sk_"
VALID_ROLES = ("viewer", "editor", "admin")


def _hash(plaintext: str) -> str:
    return hashlib.sha256(plaintext.encode("utf-8")).hexdigest()


def generate_plaintext() -> str:
    return KEY_PREFIX + secrets.token_hex(16)


class SQLiteApiKeyStore:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._connection = SerializedConnection(self.path)
        self._connection.execute(
            """
            CREATE TABLE IF NOT EXISTS api_keys (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                role TEXT NOT NULL,
                key_hash TEXT NOT NULL UNIQUE,
                key_prefix TEXT NOT NULL,
                created_at TEXT NOT NULL,
                revoked_at TEXT
            )
            """
        )
        self._connection.commit()

    def create_key(self, *, name: str, role: str) -> tuple[dict[str, Any], str]:
        if role not in VALID_ROLES:
            raise ValueError(f"role must be one of {VALID_ROLES}")
        plaintext = generate_plaintext()
        created_at = utc_now()
        cursor = self._connection.execute(
            "INSERT INTO api_keys (name, role, key_hash, key_prefix, created_at)"
            " VALUES (?, ?, ?, ?, ?)",
            (name.strip() or "unnamed", role, _hash(plaintext), plaintext[:14], created_at),
        )
        self._connection.commit()
        record = {
            "id": cursor.lastrowid,
            "name": name.strip() or "unnamed",
            "role": role,
            "key_prefix": plaintext[:14],
            "created_at": created_at,
            "revoked_at": None,
        }
        return record, plaintext

    def list_keys(self) -> list[dict[str, Any]]:
        rows = self._connection.execute(
            "SELECT id, name, role, key_prefix, created_at, revoked_at"
            " FROM api_keys ORDER BY id DESC"
        ).fetchall()
        return [dict(row) for row in rows]

    def revoke(self, key_id: int) -> bool:
        cursor = self._connection.execute(
            "UPDATE api_keys SET revoked_at = ? WHERE id = ? AND revoked_at IS NULL",
            (utc_now(), key_id),
        )
        self._connection.commit()
        return cursor.rowcount > 0

    def verify(self, plaintext: str) -> dict[str, Any] | None:
        if not plaintext.startswith(KEY_PREFIX):
            return None
        row = self._connection.execute(
            "SELECT id, name, role FROM api_keys"
            " WHERE key_hash = ? AND revoked_at IS NULL",
            (_hash(plaintext),),
        ).fetchone()
        return dict(row) if row else None
