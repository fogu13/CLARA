import time

from app.services.postgres import _WORKFLOW_REFRESH_TTL_SECONDS, PostgresWorkflowStore
from app.services.seed import load_seed_problems
from app.services.workflow import WorkflowStore


class CountingConnection:
    """Counts full clara_workflow_records loads; returns no rows."""

    def __init__(self, counter: dict[str, int]):
        self.counter = counter

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return None

    def execute(self, sql, *args, **kwargs):
        if "FROM clara_workflow_records" in str(sql):
            self.counter["loads"] += 1
        return self

    def fetchall(self):
        return []


def make_store(counter: dict[str, int]) -> PostgresWorkflowStore:
    store = PostgresWorkflowStore.__new__(PostgresWorkflowStore)
    WorkflowStore.__init__(store)
    store._connect = lambda: CountingConnection(counter)
    return store


def test_outcome_board_shaped_read_burst_loads_once() -> None:
    # The 16 Jul production incident: build_outcome_board calls
    # outcome_snapshot + latest_learning_conclusion per problem, which
    # re-SELECTed the whole workflow table 2xN times per dashboard load.
    counter = {"loads": 0}
    store = make_store(counter)
    problems = load_seed_problems()[:5]

    store.list_approvals()
    store.list_executions()
    for problem in problems:
        store.outcome_snapshot(problem)
        store.latest_learning_conclusion(problem)

    assert counter["loads"] == 1


def test_reads_refresh_after_ttl_expiry() -> None:
    counter = {"loads": 0}
    store = make_store(counter)

    store.list_approvals()
    assert counter["loads"] == 1

    store._records_loaded_at = time.monotonic() - (_WORKFLOW_REFRESH_TTL_SECONDS + 0.1)
    store.list_approvals()
    assert counter["loads"] == 2


def test_force_refresh_bypasses_ttl() -> None:
    counter = {"loads": 0}
    store = make_store(counter)

    store.list_approvals()
    store._load_records(force=True)

    assert counter["loads"] == 2
