from pathlib import Path

from app import main
from app.domain.models import (
    ApprovalDecision,
    LearningConclusionRecord,
    LearningConclusionRequest,
    OutcomeMeasurement,
)
from app.services.postgres import SCHEMA_SQL, PostgresWorkflowStore, _model_payload, normalize_database_url
from app.services.seed import load_seed_problems
from app.services.workflow import WorkflowStore, action_snapshot


class DummyPostgresStore:
    def __init__(self, *args):
        self.args = args


class FakePostgresConnection:
    def __init__(self, rows):
        self.rows = rows

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return None

    def execute(self, *_args, **_kwargs):
        return self

    def fetchall(self):
        return self.rows


def test_postgres_url_normalization_accepts_supabase_postgres_scheme() -> None:
    assert normalize_database_url("postgres://user:pass@host:5432/postgres") == (
        "postgresql://user:pass@host:5432/postgres"
    )
    assert normalize_database_url("postgresql://user:pass@host:5432/postgres") == (
        "postgresql://user:pass@host:5432/postgres"
    )


def test_postgres_schema_contains_production_tables() -> None:
    assert "clara_problems" in SCHEMA_SQL
    assert "clara_signals" in SCHEMA_SQL
    assert "clara_candidate_decisions" in SCHEMA_SQL
    assert "clara_customer_context" in SCHEMA_SQL
    assert "clara_workflow_records" in SCHEMA_SQL
    assert "tenant_id TEXT NOT NULL DEFAULT 'legacy'" in SCHEMA_SQL
    assert "retention_expires_at TIMESTAMPTZ" in SCHEMA_SQL
    assert "clara_taxonomy_catalogs" in SCHEMA_SQL
    assert "clara_terminology_dictionary" in SCHEMA_SQL


def test_workflow_tenant_retention_migration_enables_rls() -> None:
    migration = Path("migrations/002_workflow_tenant_retention.sql").read_text()

    assert "tenant_id TEXT NOT NULL DEFAULT 'legacy'" in migration
    assert "retention_expires_at TIMESTAMPTZ" in migration
    assert "ENABLE ROW LEVEL SECURITY" in migration
    assert "clara_workflow_records_tenant_isolation" in migration


def test_pgvector_taxonomy_migration_is_self_contained() -> None:
    migration = Path("migrations/003_pgvector_taxonomy.sql").read_text()

    taxonomy_table_index = migration.index("CREATE TABLE IF NOT EXISTS public.taxonomy_nodes")
    assert migration.index("CREATE TABLE IF NOT EXISTS public.workspaces") < taxonomy_table_index
    assert migration.index("CREATE OR REPLACE FUNCTION public.is_current_workspace") < taxonomy_table_index
    assert migration.index("CREATE OR REPLACE FUNCTION public.update_updated_at_column") < taxonomy_table_index


def test_database_url_switches_default_stores_to_postgres(monkeypatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@host:5432/postgres")
    monkeypatch.setattr(main, "PostgresProblemStore", DummyPostgresStore)
    monkeypatch.setattr(main, "PostgresSignalStore", DummyPostgresStore)
    monkeypatch.setattr(main, "PostgresCustomerContextStore", DummyPostgresStore)
    monkeypatch.setattr(main, "PostgresWorkflowStore", DummyPostgresStore)

    assert isinstance(main.default_problem_store(), DummyPostgresStore)
    assert isinstance(main.default_signal_store(), DummyPostgresStore)
    assert isinstance(main.default_context_store(), DummyPostgresStore)
    assert isinstance(main.default_workflow_store(), DummyPostgresStore)


def test_postgres_workflow_loads_latest_outcome_as_snapshot() -> None:
    problem = load_seed_problems()[1]
    first_measurement = OutcomeMeasurement(
        problem_id=problem.problem_id,
        metric=problem.outcome_contract.primary_metric,
        observed_value=problem.outcome_contract.baseline,
        measured_at="2026-07-01T00:00:00Z",
    )
    latest_measurement = OutcomeMeasurement(
        problem_id=problem.problem_id,
        metric=problem.outcome_contract.primary_metric,
        observed_value=problem.outcome_contract.baseline - 0.001,
        measured_at="2026-07-02T00:00:00Z",
    )
    rows = [
        {"record_type": "outcome", "payload": first_measurement.model_dump(mode="json")},
        {"record_type": "outcome", "payload": latest_measurement.model_dump(mode="json")},
    ]
    store = PostgresWorkflowStore.__new__(PostgresWorkflowStore)
    WorkflowStore.__init__(store)
    store._connect = lambda: FakePostgresConnection(rows)

    store._load_records()
    snapshot = store.outcome_snapshot(problem)

    assert snapshot.latest_value == latest_measurement.observed_value
    assert snapshot.improvement_direction == "decrease"
    assert snapshot.status == "improving"


def test_postgres_workflow_loads_approval_with_action_diff() -> None:
    problem = load_seed_problems()[0]
    action = problem.action_proposals[0]
    edited_action = action.model_copy(
        update={
            "owner": "edited_owner",
            "original_snapshot": action_snapshot(action),
        }
    )
    problem = problem.model_copy(
        update={"action_proposals": [edited_action, *problem.action_proposals[1:]]}
    )

    saved_records = []
    store = PostgresWorkflowStore.__new__(PostgresWorkflowStore)
    WorkflowStore.__init__(store)
    store._save_workflow_record = lambda *record: saved_records.append(record)

    store.record_approval(
        problem=problem,
        decision=ApprovalDecision(
            action_id="ACT-501",
            decision="approved",
            reviewer="test_product_owner",
        ),
    )

    approval_record = next(row[3] for row in saved_records if row[0] == "approval")
    rows = [{"record_type": "approval", "payload": _model_payload(approval_record)}]
    reload_store = PostgresWorkflowStore.__new__(PostgresWorkflowStore)
    WorkflowStore.__init__(reload_store)
    reload_store._connect = lambda: FakePostgresConnection(rows)

    reload_store._load_records()
    approval = reload_store.state_for_problem(problem).approvals[0]

    assert approval.action_snapshot is not None
    assert approval.action_snapshot.class_.value == "structural"
    assert approval.action_snapshot.owner == "edited_owner"
    assert approval.action_diff[0].field == "owner"
    assert approval.action_diff[0].after == "edited_owner"


def test_postgres_workflow_records_outcome_without_list_state() -> None:
    problem = load_seed_problems()[1]
    measurement = OutcomeMeasurement(
        problem_id=problem.problem_id,
        metric=problem.outcome_contract.primary_metric,
        observed_value=problem.outcome_contract.baseline - 0.001,
        measured_at="2026-07-02T00:00:00Z",
    )
    saved_records = []
    store = PostgresWorkflowStore.__new__(PostgresWorkflowStore)
    WorkflowStore.__init__(store)
    store._save_workflow_record = lambda *record: saved_records.append(record)

    store.record_outcome(problem=problem, measurement=measurement)
    snapshot = store.outcome_snapshot(problem)

    assert snapshot.status == "improving"
    assert saved_records[0][0] == "outcome"
    assert saved_records[0][1].startswith(
        f"{measurement.problem_id}:{measurement.metric}:{measurement.measured_at}:"
    )


def test_postgres_workflow_loads_learning_conclusions() -> None:
    problem = load_seed_problems()[0]
    conclusion = LearningConclusionRecord(
        conclusion_id="LRN-test",
        problem_id=problem.problem_id,
        tenant_id="test_tenant",
        learning_status="worked",
        reviewer="test_reviewer",
        reviewed_at="2026-07-21T00:00:00Z",
        retention_expires_at="2028-07-20T00:00:00Z",
        summary="Outcome improved.",
        limitations="Small holdout.",
    )
    rows = [
        {"record_type": "learning_conclusion", "payload": conclusion.model_dump(mode="json")},
    ]
    store = PostgresWorkflowStore.__new__(PostgresWorkflowStore)
    WorkflowStore.__init__(store)
    store._connect = lambda: FakePostgresConnection(rows)

    store._load_records()
    latest = store.latest_learning_conclusion(problem, tenant_id="test_tenant")

    assert latest is not None
    assert latest.conclusion_id == "LRN-test"
    state = store.state_for_problem(problem, tenant_id="test_tenant")
    assert state.learning_conclusions[0].summary == "Outcome improved."


def test_postgres_workflow_records_learning_conclusion() -> None:
    problem = load_seed_problems()[0]
    saved_records = []
    store = PostgresWorkflowStore.__new__(PostgresWorkflowStore)
    WorkflowStore.__init__(store)
    store._save_workflow_record = lambda *record: saved_records.append(record)

    conclusion = store.record_learning_conclusion(
        problem=problem,
        conclusion=LearningConclusionRequest(
            learning_status="worked",
            summary="Outcome improved.",
            limitations="Small holdout.",
        ),
        tenant_id="test_tenant",
        actor="test_reviewer",
    )

    assert saved_records[0][0] == "learning_conclusion"
    assert saved_records[0][1] == conclusion.conclusion_id
    assert saved_records[0][2] == problem.problem_id
    assert saved_records[0][4] == "test_tenant"
