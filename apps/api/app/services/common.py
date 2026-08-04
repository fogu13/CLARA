"""Small shared helpers used across services (consolidated from byte-identical copies)."""

from __future__ import annotations

from datetime import UTC, datetime

from app.domain.models import ActionProposal, ActionProposalSnapshot


def utc_now() -> str:
    """Current UTC time as an ISO-8601 string with a 'Z' suffix."""
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def normalize_timestamp(value: object) -> tuple[str, bool]:
    """Parse an ISO-8601 timestamp to UTC. Returns (timestamp, was_defaulted).

    Missing or unparseable values fall back to ingestion time, never to a
    fabricated epoch date. `1970-01-01` is worse than useless here: outcome
    measurement buckets by calendar day, so an epoch-stamped signal silently
    drops out of every pre/post window instead of erroring, and it corrupts
    first_seen/last_seen, which order by string compare.

    Callers persist the flag so a defaulted timestamp stays auditable rather
    than becoming indistinguishable from a real one.
    """
    text = str(value).strip() if value is not None else ""
    if text:
        try:
            parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        except ValueError:
            pass  # fall through to the flagged default
        else:
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=UTC)
            return parsed.astimezone(UTC).isoformat().replace("+00:00", "Z"), False
    return utc_now(), True


def action_snapshot(action: ActionProposal) -> ActionProposalSnapshot:
    """Immutable by-alias snapshot of an action proposal (for audit records)."""
    return ActionProposalSnapshot.model_validate(action.model_dump(by_alias=True))


class _FetchedCursor:
    """Cursor stand-in with results already materialized under the lock."""

    def __init__(self, rows: list, lastrowid: int | None, rowcount: int) -> None:
        self._rows = rows
        self.lastrowid = lastrowid
        self.rowcount = rowcount

    def fetchall(self) -> list:
        return self._rows

    def fetchone(self):
        return self._rows[0] if self._rows else None

    def __iter__(self):
        return iter(self._rows)


class SerializedConnection:
    """sqlite3 connection that is actually safe under FastAPI's threadpool.

    Every SQLite store used check_same_thread=False with a SHARED connection,
    but sqlite3 connections are not safe for concurrent use: parallel requests
    (the dashboard fires ~8 at once) interleave cursor state and blow up with
    IndexError/ProgrammingError mid-fetch (reproduced live on /outcome-board).

    One RLock serializes execute+fetch as a unit; results are materialized
    before the lock is released, so no cursor ever crosses a thread boundary.
    ponytail: a lock, not a pool. Postgres stores are the scale path.
    """

    def __init__(self, path) -> None:
        import sqlite3
        import threading

        self._conn = sqlite3.connect(path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._lock = threading.RLock()

    def execute(self, sql: str, params=()) -> _FetchedCursor:
        with self._lock:
            cursor = self._conn.execute(sql, params)
            rows = cursor.fetchall() if cursor.description is not None else []
            return _FetchedCursor(rows, cursor.lastrowid, cursor.rowcount)

    def executescript(self, script: str) -> None:
        with self._lock:
            self._conn.executescript(script)

    def commit(self) -> None:
        with self._lock:
            self._conn.commit()
