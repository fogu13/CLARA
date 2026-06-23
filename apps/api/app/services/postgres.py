from __future__ import annotations

import json
import os
import re
from itertools import count
from typing import Any
from uuid import uuid4

from app.domain.models import (
    ApprovalRecord,
    CandidateDecisionRecord,
    CandidateDecisionStatus,
    CustomerContextImportResult,
    CustomerContextRecord,
    ExecutionRecord,
    JiraIssueDraft,
    LearningConclusionRecord,
    OutcomeMeasurement,
    ProblemRecord,
    ProblemStatus,
    ProblemTransitionRecord,
    SignalImportResult,
    SignalRecord,
    TaxonomyCatalog,
    TerminologyDictionaryEntry,
)
from app.services.contexts import CustomerContextStore
from app.services.problems import (
    apply_action_proposal_update,
    apply_problem_status,
    apply_problem_update,
)
from app.services.signals import build_candidates
from app.services.taxonomies import (
    TaxonomyStore,
    TerminologyStore,
    load_seed_taxonomies,
    load_seed_terminology,
)
from app.services.workflow import WorkflowStore

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS odradek_problems (
    problem_id TEXT PRIMARY KEY,
    payload JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS odradek_signals (
    signal_id TEXT PRIMARY KEY,
    payload JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS odradek_candidate_decisions (
    candidate_id TEXT PRIMARY KEY,
    payload JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS odradek_customer_context (
    customer_id TEXT PRIMARY KEY,
    account_id TEXT,
    payload JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS odradek_workflow_records (
    record_type TEXT NOT NULL,
    record_id TEXT NOT NULL,
    problem_id TEXT NOT NULL,
    tenant_id TEXT NOT NULL DEFAULT 'legacy',
    payload JSONB NOT NULL,
    retention_expires_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (record_type, record_id)
);

CREATE INDEX IF NOT EXISTS odradek_workflow_problem_idx
    ON odradek_workflow_records (problem_id, record_type);

CREATE TABLE IF NOT EXISTS odradek_taxonomy_catalogs (
    taxonomy_type TEXT PRIMARY KEY,
    payload JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS odradek_terminology_dictionary (
    term_id TEXT PRIMARY KEY,
    payload JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
"""


def database_url() -> str | None:
    return os.getenv("DATABASE_URL")


def normalize_database_url(url: str) -> str:
    if url.startswith("postgres://"):
        return "postgresql://" + url.removeprefix("postgres://")
    return url


def _load_psycopg():
    try:
        import psycopg
        from psycopg.rows import dict_row
        from psycopg.types.json import Jsonb
    except ImportError as exc:
        raise RuntimeError(
            "DATABASE_URL is set, but psycopg is not installed. "
            "Install API dependencies with `pip install -e apps/api` or install `psycopg[binary]`."
        ) from exc
    return psycopg, dict_row, Jsonb


def _payload(value: Any) -> dict[str, Any]:
    if isinstance(value, str):
        return json.loads(value)
    return dict(value)


def _model_payload(model: Any) -> dict[str, Any]:
    return model.model_dump(mode="json")


class PostgresConnectionMixin:
    def __init__(self, url: str) -> None:
        self.url = normalize_database_url(url)
        self._ensure_schema()

    def _connect(self):
        psycopg, dict_row, _ = _load_psycopg()
        return psycopg.connect(self.url, row_factory=dict_row)

    def _ensure_schema(self) -> None:
        with self._connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute(SCHEMA_SQL)
                cursor.execute(
                    """
                    ALTER TABLE odradek_workflow_records
                    ADD COLUMN IF NOT EXISTS tenant_id TEXT NOT NULL DEFAULT 'legacy'
                    """
                )
                cursor.execute(
                    """
                    ALTER TABLE odradek_workflow_records
                    ADD COLUMN IF NOT EXISTS retention_expires_at TIMESTAMPTZ
                    """
                )
                cursor.execute(
                    """
                    CREATE INDEX IF NOT EXISTS odradek_workflow_tenant_problem_idx
                    ON odradek_workflow_records (tenant_id, problem_id, record_type)
                    """
                )
                cursor.execute("ALTER TABLE odradek_workflow_records ENABLE ROW LEVEL SECURITY")
                cursor.execute(
                    """
                    DROP POLICY IF EXISTS odradek_workflow_records_tenant_isolation
                    ON odradek_workflow_records
                    """
                )
                cursor.execute(
                    """
                    CREATE POLICY odradek_workflow_records_tenant_isolation
                    ON odradek_workflow_records
                    USING (
                        tenant_id = current_setting('app.tenant_id', true)
                        OR tenant_id = (
                            NULLIF(current_setting('request.jwt.claims', true), '')::jsonb
                            ->> 'tenant_id'
                        )
                    )
                    WITH CHECK (
                        tenant_id = current_setting('app.tenant_id', true)
                        OR tenant_id = (
                            NULLIF(current_setting('request.jwt.claims', true), '')::jsonb
                            ->> 'tenant_id'
                        )
                    )
                    """
                )

    def _jsonb(self, payload: dict[str, Any]):
        _, _, Jsonb = _load_psycopg()
        return Jsonb(payload)


class PostgresProblemStore(PostgresConnectionMixin):
    def __init__(self, url: str, seed_problems: list[ProblemRecord]) -> None:
        super().__init__(url)
        if not self.list_problems():
            for problem in seed_problems:
                self.upsert_problem(problem)

    def list_problems(self) -> list[ProblemRecord]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT payload FROM odradek_problems ORDER BY problem_id"
            ).fetchall()
        return [ProblemRecord.model_validate(_payload(row["payload"])) for row in rows]

    def get_problem(self, problem_id: str) -> ProblemRecord | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT payload FROM odradek_problems WHERE problem_id = %s",
                (problem_id,),
            ).fetchone()
        if row is None:
            return None
        return ProblemRecord.model_validate(_payload(row["payload"]))

    def upsert_problem(self, problem: ProblemRecord) -> ProblemRecord:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO odradek_problems (problem_id, payload)
                VALUES (%s, %s)
                ON CONFLICT (problem_id) DO UPDATE
                SET payload = excluded.payload, updated_at = now()
                """,
                (problem.problem_id, self._jsonb(_model_payload(problem))),
            )
        return problem

    def update_problem(self, problem_id: str, update) -> ProblemRecord | None:
        existing = self.get_problem(problem_id)
        if existing is None:
            return None
        updated = apply_problem_update(existing, update)
        return self.upsert_problem(updated)

    def update_action_proposal(self, problem_id: str, action_id: str, update):
        existing = self.get_problem(problem_id)
        if existing is None:
            return None
        updated = apply_action_proposal_update(existing, action_id, update)
        if updated is None:
            return None
        return self.upsert_problem(updated)

    def transition_problem_status(
        self,
        problem_id: str,
        status: ProblemStatus,
    ) -> ProblemRecord | None:
        existing = self.get_problem(problem_id)
        if existing is None:
            return None
        updated = apply_problem_status(existing, status)
        return self.upsert_problem(updated)


class PostgresSignalStore(PostgresConnectionMixin):
    def list_signals(self) -> list[SignalRecord]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT payload FROM odradek_signals ORDER BY signal_id"
            ).fetchall()
        return [SignalRecord.model_validate(_payload(row["payload"])) for row in rows]

    def import_signals(self, signals: list[SignalRecord]) -> SignalImportResult:
        existing_ids = self.existing_signal_ids()
        imported = 0
        with self._connect() as conn:
            for signal in signals:
                if signal.signal_id in existing_ids:
                    continue
                conn.execute(
                    """
                    INSERT INTO odradek_signals (signal_id, payload)
                    VALUES (%s, %s)
                    ON CONFLICT (signal_id) DO NOTHING
                    """,
                    (signal.signal_id, self._jsonb(_model_payload(signal))),
                )
                imported += 1
        return SignalImportResult(
            imported=imported,
            skipped_duplicates=len(signals) - imported,
            total_signals=len(self.list_signals()),
        )

    def candidates(self):
        return build_candidates(self.list_signals())

    def get_candidate_decision(self, candidate_id: str) -> CandidateDecisionRecord | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT payload FROM odradek_candidate_decisions WHERE candidate_id = %s",
                (candidate_id,),
            ).fetchone()
        if row is None:
            return None
        return CandidateDecisionRecord.model_validate(_payload(row["payload"]))

    def record_candidate_decision(
        self,
        *,
        candidate_id: str,
        decision: CandidateDecisionStatus,
        reviewer: str,
        note: str | None = None,
    ) -> CandidateDecisionRecord:
        from app.services.signals import utc_now

        record = CandidateDecisionRecord(
            candidate_id=candidate_id,
            decision=decision,
            reviewer=reviewer,
            note=note,
            created_at=utc_now(),
        )
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO odradek_candidate_decisions (candidate_id, payload)
                VALUES (%s, %s)
                ON CONFLICT (candidate_id) DO UPDATE
                SET payload = excluded.payload, updated_at = now()
                """,
                (candidate_id, self._jsonb(_model_payload(record))),
            )
        return record

    def existing_signal_ids(self) -> set[str]:
        with self._connect() as conn:
            rows = conn.execute("SELECT signal_id FROM odradek_signals").fetchall()
        return {row["signal_id"] for row in rows}


class PostgresCustomerContextStore(PostgresConnectionMixin, CustomerContextStore):
    def list_context(self) -> list[CustomerContextRecord]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT payload FROM odradek_customer_context ORDER BY customer_id"
            ).fetchall()
        return [CustomerContextRecord.model_validate(_payload(row["payload"])) for row in rows]

    def import_context(
        self,
        records: list[CustomerContextRecord],
    ) -> CustomerContextImportResult:
        existing_ids = self.existing_customer_ids()
        imported = 0
        updated = 0
        with self._connect() as conn:
            for record in records:
                if record.customer_id in existing_ids:
                    updated += 1
                else:
                    imported += 1
                conn.execute(
                    """
                    INSERT INTO odradek_customer_context (customer_id, account_id, payload)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (customer_id) DO UPDATE
                    SET account_id = excluded.account_id,
                        payload = excluded.payload,
                        updated_at = now()
                    """,
                    (
                        record.customer_id,
                        record.account_id,
                        self._jsonb(_model_payload(record)),
                    ),
                )
        return CustomerContextImportResult(
            imported=imported,
            updated=updated,
            total_context_records=len(self.list_context()),
        )

    def existing_customer_ids(self) -> set[str]:
        with self._connect() as conn:
            rows = conn.execute("SELECT customer_id FROM odradek_customer_context").fetchall()
        return {row["customer_id"] for row in rows}


class PostgresWorkflowStore(PostgresConnectionMixin, WorkflowStore):
    def __init__(self, url: str) -> None:
        PostgresConnectionMixin.__init__(self, url)
        WorkflowStore.__init__(self)
        self._load_records()

    def _load_records(self) -> None:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT record_type, payload
                FROM odradek_workflow_records
                ORDER BY created_at, record_id
                """
            ).fetchall()

        approvals: list[ApprovalRecord] = []
        executions: list[ExecutionRecord] = []
        jira_drafts: list[JiraIssueDraft] = []
        transitions: list[ProblemTransitionRecord] = []
        outcomes: dict[str, OutcomeMeasurement] = {}
        learning_conclusions: list[LearningConclusionRecord] = []

        for row in rows:
            payload = _payload(row["payload"])
            record_type = row["record_type"]
            if record_type == "approval":
                approvals.append(ApprovalRecord.model_validate(payload))
            elif record_type == "execution":
                executions.append(ExecutionRecord.model_validate(payload))
            elif record_type == "jira_draft":
                jira_drafts.append(JiraIssueDraft.model_validate(payload))
            elif record_type == "transition":
                transitions.append(ProblemTransitionRecord.model_validate(payload))
            elif record_type == "outcome":
                measurement = OutcomeMeasurement.model_validate(payload)
                outcomes[measurement.problem_id] = measurement
            elif record_type == "learning_conclusion":
                learning_conclusions.append(LearningConclusionRecord.model_validate(payload))

        self._approvals = approvals
        self._executions = executions
        self._jira_issue_drafts = jira_drafts
        self._transitions = transitions
        self._outcomes = outcomes
        self._learning_conclusions = learning_conclusions
        self._approval_ids = count(_next_id(approvals, "decision_id", "DEC") + 1)
        self._execution_ids = count(_next_id(executions, "execution_id", "EXE") + 1)
        self._jira_draft_ids = count(_next_id(jira_drafts, "draft_id", "JIRA") + 1)
        self._transition_ids = count(_next_id(transitions, "transition_id", "TRN") + 1)

    def _save_workflow_record(
        self,
        record_type: str,
        record_id: str,
        problem_id: str,
        record: Any,
        tenant_id: str = "legacy",
        retention_expires_at: str | None = None,
    ) -> None:
        with self._connect() as conn:
            conn.execute("SELECT set_config('app.tenant_id', %s, true)", (tenant_id,))
            conn.execute(
                """
                INSERT INTO odradek_workflow_records (
                    record_type,
                    record_id,
                    problem_id,
                    tenant_id,
                    payload,
                    retention_expires_at
                )
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (record_type, record_id) DO UPDATE
                SET problem_id = excluded.problem_id,
                    tenant_id = excluded.tenant_id,
                    payload = excluded.payload,
                    retention_expires_at = excluded.retention_expires_at,
                    updated_at = now()
                """,
                (
                    record_type,
                    record_id,
                    problem_id,
                    tenant_id,
                    self._jsonb(_model_payload(record)),
                    retention_expires_at,
                ),
            )

    def record_transition(self, *args: Any, **kwargs: Any):
        transition = WorkflowStore.record_transition(self, *args, **kwargs)
        self._save_workflow_record(
            "transition",
            transition.transition_id,
            transition.problem_id,
            transition,
        )
        return transition

    def record_approval(self, *args: Any, **kwargs: Any):
        before_executions = {execution.execution_id for execution in self._executions}
        before_drafts = {draft.draft_id for draft in self._jira_issue_drafts}
        approval = WorkflowStore.record_approval(self, *args, **kwargs)
        self._save_workflow_record(
            "approval",
            approval.decision_id,
            approval.problem_id,
            approval,
        )
        for execution in self._executions:
            if execution.execution_id not in before_executions:
                self._save_workflow_record(
                    "execution",
                    execution.execution_id,
                    execution.problem_id,
                    execution,
                )
        for draft in self._jira_issue_drafts:
            if draft.draft_id not in before_drafts:
                self._save_workflow_record(
                    "jira_draft",
                    draft.draft_id,
                    draft.problem_id,
                    draft,
                )
        return approval

    def record_outcome(self, *args: Any, **kwargs: Any):
        measurement = WorkflowStore.record_outcome(self, *args, **kwargs)
        record_id = (
            f"{measurement.problem_id}:{measurement.metric}:"
            f"{measurement.measured_at}:{uuid4().hex}"
        )
        self._save_workflow_record(
            "outcome",
            record_id,
            measurement.problem_id,
            measurement,
        )
        return measurement

    def record_learning_conclusion(self, *args: Any, **kwargs: Any):
        conclusion = WorkflowStore.record_learning_conclusion(self, *args, **kwargs)
        # ponytail: workflow_records has no tenant_id yet; future RLS milestone adds DB tenant boundaries.
        self._save_workflow_record(
            "learning_conclusion",
            conclusion.conclusion_id,
            conclusion.problem_id,
            conclusion,
            conclusion.tenant_id,
            conclusion.retention_expires_at,
        )
        return conclusion


def _next_id(records: list[Any], field_name: str, prefix: str) -> int:
    pattern = re.compile(rf"^{re.escape(prefix)}-(\d+)$")
    maximum = 0
    for record in records:
        match = pattern.match(getattr(record, field_name))
        if match:
            maximum = max(maximum, int(match.group(1)))
    return maximum


class PostgresTaxonomyStore(PostgresConnectionMixin, TaxonomyStore):
    def __init__(self, url: str) -> None:
        PostgresConnectionMixin.__init__(self, url)
        if not self._load_catalogs():
            for catalog in load_seed_taxonomies():
                self._save_catalog(catalog)
        TaxonomyStore.__init__(self, self._load_catalogs())

    def _load_catalogs(self) -> list[TaxonomyCatalog]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT payload FROM odradek_taxonomy_catalogs ORDER BY taxonomy_type"
            ).fetchall()
        return [TaxonomyCatalog.model_validate(_payload(row["payload"])) for row in rows]

    def _save_catalog(self, catalog: TaxonomyCatalog) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO odradek_taxonomy_catalogs (taxonomy_type, payload)
                VALUES (%s, %s)
                ON CONFLICT (taxonomy_type) DO UPDATE
                SET payload = excluded.payload, updated_at = now()
                """,
                (catalog.taxonomy_type.value, self._jsonb(_model_payload(catalog))),
            )

    def rename_category(self, *args: Any, **kwargs: Any) -> TaxonomyCatalog:
        catalog = TaxonomyStore.rename_category(self, *args, **kwargs)
        self._save_catalog(catalog)
        return catalog

    def lock_category(self, *args: Any, **kwargs: Any) -> TaxonomyCatalog:
        catalog = TaxonomyStore.lock_category(self, *args, **kwargs)
        self._save_catalog(catalog)
        return catalog

    def merge_categories(self, *args: Any, **kwargs: Any) -> TaxonomyCatalog:
        catalog = TaxonomyStore.merge_categories(self, *args, **kwargs)
        self._save_catalog(catalog)
        return catalog

    def split_category(self, *args: Any, **kwargs: Any) -> TaxonomyCatalog:
        catalog = TaxonomyStore.split_category(self, *args, **kwargs)
        self._save_catalog(catalog)
        return catalog


class PostgresTerminologyStore(PostgresConnectionMixin, TerminologyStore):
    def __init__(self, url: str) -> None:
        PostgresConnectionMixin.__init__(self, url)
        if not self._load_entries():
            for entry in load_seed_terminology():
                self._save_entry(entry)
        TerminologyStore.__init__(self, self._load_entries())

    def _load_entries(self) -> list[TerminologyDictionaryEntry]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT payload FROM odradek_terminology_dictionary ORDER BY term_id"
            ).fetchall()
        return [
            TerminologyDictionaryEntry.model_validate(_payload(row["payload"]))
            for row in rows
        ]

    def _save_entry(self, entry: TerminologyDictionaryEntry) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO odradek_terminology_dictionary (term_id, payload)
                VALUES (%s, %s)
                ON CONFLICT (term_id) DO UPDATE
                SET payload = excluded.payload, updated_at = now()
                """,
                (entry.term_id, self._jsonb(_model_payload(entry))),
            )
