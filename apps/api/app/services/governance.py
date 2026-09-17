"""Process-wide governance locks.

A reviewer's approval and an editor's change to the reviewed content of the
same problem must not interleave: the approval route records the decision
(freezing the outbound content) and the edit routes check the approvals and
write the problem under ONE per-problem lock, so a check that passed cannot
be persisted after an approval was recorded in between (the title race of
the 13 September 2026 review).

The lock is process-local. Across processes (a multi-worker Postgres
deployment) the Postgres stores add a transaction-level advisory lock on the
same key and re-run the guard inside the write transaction
(``PostgresProblemStore.update_problem(..., guard=...)``,
``PostgresWorkflowStore.record_approval``), so the two writes are serialised
by the database as well.
"""

from __future__ import annotations

import threading

_LOCKS: dict[str, threading.RLock] = {}
_GUARD = threading.Lock()


def problem_lock(problem_id: str) -> threading.RLock:
    """The lock serialising governed writes for one problem."""
    with _GUARD:
        return _LOCKS.setdefault(problem_id, threading.RLock())


def advisory_lock_key(problem_id: str) -> str:
    """The advisory-lock key both Postgres stores hash (`hashtext`)."""
    return f"clara:problem:{problem_id}"
