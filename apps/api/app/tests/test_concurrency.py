"""Regression: SQLite stores must survive FastAPI's threadpool concurrency.

Before SerializedConnection, all stores shared one sqlite3 connection with
check_same_thread=False and no locking. Parallel requests (the dashboard fires
~8 at once) interleaved cursor state and crashed with IndexError inside row
mapping. Reproduced live on /outcome-board; this test recreates the pattern.
"""

from __future__ import annotations

import concurrent.futures
from pathlib import Path

from fastapi.testclient import TestClient

from app.connectors.config_store import ConnectorConfigStore
from app.main import create_app
from app.services.contexts import SQLiteCustomerContextStore, parse_context_csv
from app.services.problems import ProblemStore
from app.services.seed import load_seed_problems
from app.services.signals import SQLiteSignalStore
from app.services.telemetry import SQLiteTelemetryStore
from app.services.workflow import WorkflowStore

CONTEXT_CSV = "customer_id,account_id,account_value,consent_status\n" + "\n".join(
    f"C-{i},A-{i % 5},{1000 + i},granted" for i in range(40)
)


def test_parallel_requests_do_not_corrupt_sqlite_cursors(tmp_path: Path) -> None:
    context_store = SQLiteCustomerContextStore(tmp_path / "ctx.db")
    context_store.import_context(parse_context_csv(CONTEXT_CSV))
    client = TestClient(
        create_app(
            problem_store=ProblemStore(load_seed_problems()),
            workflows=WorkflowStore(),
            signals=SQLiteSignalStore(tmp_path / "signals.db"),
            contexts=context_store,
            connector_configs=ConnectorConfigStore(),
            telemetry=SQLiteTelemetryStore(tmp_path / "t.db"),
        )
    )

    endpoints = [
        "/problems", "/outcome-board", "/approvals", "/executions",
        "/signals", "/customer-context", "/emerging-problems", "/measurements",
    ]

    def hit(path: str) -> int:
        return client.get(path).status_code

    with concurrent.futures.ThreadPoolExecutor(max_workers=12) as pool:
        statuses = list(pool.map(hit, [ep for _ in range(15) for ep in endpoints]))

    assert statuses.count(200) == len(statuses), (
        f"non-200 under parallel load: { {s: statuses.count(s) for s in set(statuses)} }"
    )


def test_store_level_parallel_reads_and_writes(tmp_path: Path) -> None:
    store = SQLiteTelemetryStore(tmp_path / "t.db")

    def work(i: int) -> int:
        store.record(f"event_{i % 4}", metadata={"i": i})
        return len(store.list_events(limit=50))

    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as pool:
        results = list(pool.map(work, range(200)))

    assert len(results) == 200
    assert store.counts_by_type()  # store intact, no corruption
