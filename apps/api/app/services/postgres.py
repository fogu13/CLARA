from __future__ import annotations

import atexit
import logging
import threading

import json
import os
import re
import time
from contextlib import contextmanager
from itertools import count
from typing import Any
from uuid import uuid4

from fastapi import HTTPException

from app.auth import current_tenant
from app.domain.models import (
    ApprovalRecord,
    CandidateDecisionRecord,
    CandidateDecisionStatus,
    ClosureRecord,
    CustomerContextImportResult,
    CustomerContextRecord,
    ExecutionRecord,
    FeedbackRule,
    FeedbackRuleCreate,
    GuardrailMeasurement,
    JiraIssueDraft,
    JourneyEventImportResult,
    JourneyEventRecord,
    LearningConclusionRecord,
    OutcomeMeasurement,
    ProblemRecord,
    ProblemStatus,
    ProblemTransitionRecord,
    SignalImportResult,
    SignalRecord,
    TaxonomyCatalog,
    TerminologyDictionaryEntry,
    WorkspaceSettings,
)
from app.services.contexts import CustomerContextStore
from app.services.problems import (
    apply_action_proposal_update,
    apply_outcome_contract_update,
    apply_problem_status,
    apply_problem_update,
    scrub_customer_evidence,
)
from app.services.signals import build_candidates
from app.services.taxonomies import (
    TaxonomyStore,
    TerminologyStore,
    load_seed_taxonomies,
    load_seed_terminology,
)
from app.services.common import utc_now
from app.services.governance import advisory_lock_key
from app.services.workflow import DISPATCH_CLAIM_TTL_SECONDS, WorkflowStore, find_action

logger = logging.getLogger(__name__)

SCHEMA_SQL = """
-- Tenant-first keys (migration 014): ids repeat across workspaces (Zendesk
-- ticket 123, PRB-DRAFT-CHECKOUT-PAYMENT), so uniqueness is per workspace.
-- workspace_id defaults read the session GUC set by _connect().
CREATE TABLE IF NOT EXISTS clara_problems (
    workspace_id BIGINT NOT NULL DEFAULT COALESCE(NULLIF(current_setting('app.workspace_id', true), ''), '1')::bigint,
    problem_id TEXT NOT NULL,
    payload JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (workspace_id, problem_id)
);

CREATE TABLE IF NOT EXISTS clara_signals (
    workspace_id BIGINT NOT NULL DEFAULT COALESCE(NULLIF(current_setting('app.workspace_id', true), ''), '1')::bigint,
    signal_id TEXT NOT NULL,
    payload JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (workspace_id, signal_id)
);

CREATE TABLE IF NOT EXISTS clara_candidate_decisions (
    workspace_id BIGINT NOT NULL DEFAULT COALESCE(NULLIF(current_setting('app.workspace_id', true), ''), '1')::bigint,
    candidate_id TEXT NOT NULL,
    payload JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (workspace_id, candidate_id)
);

CREATE TABLE IF NOT EXISTS clara_journey_events (
    workspace_id BIGINT NOT NULL DEFAULT COALESCE(NULLIF(current_setting('app.workspace_id', true), ''), '1')::bigint,
    event_id TEXT NOT NULL,
    payload JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (workspace_id, event_id)
);

CREATE TABLE IF NOT EXISTS clara_customer_context (
    workspace_id BIGINT NOT NULL DEFAULT COALESCE(NULLIF(current_setting('app.workspace_id', true), ''), '1')::bigint,
    customer_id TEXT NOT NULL,
    account_id TEXT,
    payload JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (workspace_id, customer_id)
);

CREATE TABLE IF NOT EXISTS clara_workflow_records (
    record_type TEXT NOT NULL,
    record_id TEXT NOT NULL,
    problem_id TEXT NOT NULL,
    tenant_id TEXT NOT NULL DEFAULT 'legacy',
    payload JSONB NOT NULL,
    retention_expires_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    -- tenant-first PK: record ids (DEC-0001, ...) are minted per tenant view,
    -- so uniqueness must be per tenant or tenant 2's first ids would collide
    -- with tenant 1's rows (invisible under RLS -> 42501 on upsert).
    PRIMARY KEY (tenant_id, record_type, record_id)
);

CREATE INDEX IF NOT EXISTS clara_workflow_problem_idx
    ON clara_workflow_records (problem_id, record_type);

CREATE TABLE IF NOT EXISTS clara_taxonomy_catalogs (
    workspace_id BIGINT NOT NULL DEFAULT COALESCE(NULLIF(current_setting('app.workspace_id', true), ''), '1')::bigint,
    taxonomy_type TEXT NOT NULL,
    payload JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (workspace_id, taxonomy_type)
);

CREATE TABLE IF NOT EXISTS clara_terminology_dictionary (
    workspace_id BIGINT NOT NULL DEFAULT COALESCE(NULLIF(current_setting('app.workspace_id', true), ''), '1')::bigint,
    term_id TEXT NOT NULL,
    payload JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (workspace_id, term_id)
);

CREATE TABLE IF NOT EXISTS clara_workspace_settings (
    workspace_id INTEGER PRIMARY KEY,
    payload JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
-- workspace_id defaults read the session GUC set by _connect(), so inserts
-- inherit the active tenant without any store naming the column (falls back
-- to the default workspace for GUC-less sessions, e.g. SQL-editor DML).
CREATE TABLE IF NOT EXISTS clara_telemetry (
    id BIGSERIAL PRIMARY KEY,
    workspace_id BIGINT NOT NULL DEFAULT COALESCE(NULLIF(current_setting('app.workspace_id', true), ''), '1')::bigint,
    event_type TEXT NOT NULL,
    entity_id TEXT,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS clara_measurement_plans (
    id BIGSERIAL PRIMARY KEY,
    workspace_id BIGINT NOT NULL DEFAULT COALESCE(NULLIF(current_setting('app.workspace_id', true), ''), '1')::bigint,
    problem_id TEXT NOT NULL,
    execution_id TEXT NOT NULL,
    executed_at TEXT NOT NULL,
    due_at TEXT NOT NULL,
    kind TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    note TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    -- Clock origin (approval | dispatch | implementation) and the contract
    -- revision the checkpoints were scheduled under (migration 016).
    origin TEXT NOT NULL DEFAULT 'approval',
    contract_revision INTEGER
);

CREATE TABLE IF NOT EXISTS clara_connector_configs (
    workspace_id BIGINT NOT NULL DEFAULT COALESCE(NULLIF(current_setting('app.workspace_id', true), ''), '1')::bigint,
    connector_type TEXT NOT NULL,
    payload JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (workspace_id, connector_type)
);

CREATE TABLE IF NOT EXISTS clara_api_keys (
    id BIGSERIAL PRIMARY KEY,
    workspace_id BIGINT NOT NULL DEFAULT COALESCE(NULLIF(current_setting('app.workspace_id', true), ''), '1')::bigint,
    name TEXT NOT NULL,
    role TEXT NOT NULL,
    key_hash TEXT NOT NULL UNIQUE,
    key_prefix TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    revoked_at TIMESTAMPTZ
);

-- AI triage themes persisted from POST /triage/run so they surface as problem
-- candidates (origin=ai_theme). One row per (workspace, theme tag); the latest
-- run wins. Migration 013 is the SQL-editor twin of this DDL.
CREATE TABLE IF NOT EXISTS clara_theme_insights (
    workspace_id BIGINT NOT NULL DEFAULT COALESCE(NULLIF(current_setting('app.workspace_id', true), ''), '1')::bigint,
    theme_tag TEXT NOT NULL,
    payload JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (workspace_id, theme_tag)
);

-- Learning memory (retrieval store for synthesis). Human conclusions from the
-- Action Queue and resume-path learnings land here; rank_learnings reads it.
CREATE TABLE IF NOT EXISTS clara_learnings (
    workspace_id BIGINT NOT NULL DEFAULT COALESCE(NULLIF(current_setting('app.workspace_id', true), ''), '1')::bigint,
    conclusion_id TEXT NOT NULL,
    topic TEXT,
    payload JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (workspace_id, conclusion_id)
);
"""


def database_url() -> str | None:
    url = os.getenv("DATABASE_URL")
    return url or None


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


# One pool per DATABASE_URL, shared across all stores in the process. The
# previous connect-per-call pattern opened a fresh session-pooler connection
# for EVERY store method; under burst load Supavisor queues new connects
# indefinitely, which surfaced as multi-minute request hangs, and each stuck
# request parked an "idle in transaction" session that ate another pooler
# slot. A bounded pool with timeouts fails fast instead of hanging.
_POOLS: dict[str, Any] = {}
_POOLS_LOCK = threading.Lock()


def _get_pool(url: str):
    from psycopg_pool import ConnectionPool

    _, dict_row, _ = _load_psycopg()
    with _POOLS_LOCK:
        pool = _POOLS.get(url)
        if pool is None:
            pool = ConnectionPool(
                url,
                kwargs={
                    "row_factory": dict_row,
                    "connect_timeout": 10,
                    # Server-side guard: whatever leaks a transaction (stuck
                    # thread, killed process), Postgres reaps it — stale
                    # "idle in transaction" sessions blocked schema DDL for
                    # hours during the 5 Jul incident.
                    "options": "-c idle_in_transaction_session_timeout=120000",
                },
                min_size=0,
                max_size=5,
                timeout=15,  # bounded wait for a pooled connection, not forever
                open=True,
                name=f"clara-{len(_POOLS)}",
            )
            _POOLS[url] = pool
            atexit.register(pool.close)  # quiet, prompt worker shutdown
    return pool


def _payload(value: Any) -> dict[str, Any]:
    if isinstance(value, str):
        return json.loads(value)
    return dict(value)


def _model_payload(model: Any) -> dict[str, Any]:
    return model.model_dump(mode="json", by_alias=True)


_SCHEMA_ENSURED: set[str] = set()

# (table, natural key) pairs whose primary key must be (workspace_id, key).
TENANT_KEYED_TABLES: tuple[tuple[str, str], ...] = (
    ("clara_problems", "problem_id"),
    ("clara_signals", "signal_id"),
    ("clara_candidate_decisions", "candidate_id"),
    ("clara_journey_events", "event_id"),
    ("clara_customer_context", "customer_id"),
    ("clara_taxonomy_catalogs", "taxonomy_type"),
    ("clara_terminology_dictionary", "term_id"),
    ("clara_connector_configs", "connector_type"),
)


class PostgresConnectionMixin:
    def __init__(self, url: str) -> None:
        self.url = normalize_database_url(url)
        self._ensure_schema()

    @contextmanager
    def _connect(self):
        # Context manager from the shared pool: `with self._connect() as conn`
        # commits on clean exit, rolls back on error, returns the connection.
        # Every checkout pins the transaction to the active tenant (auth.py
        # ContextVar): the FORCEd RLS policies key on these two GUCs, so this
        # single choke point is what tenant-scopes every store. set_config with
        # is_local=true is transaction-scoped — it dies at the checkout's
        # commit/rollback and can never leak across pooled connection reuses.
        with _get_pool(self.url).connection() as conn:
            tenant = current_tenant()
            conn.execute(
                "SELECT set_config('app.tenant_id', %s, true),"
                " set_config('app.workspace_id', %s, true)",
                (tenant, tenant),
            )
            yield conn

    def _ensure_schema(self) -> None:
        # Once per process: create_app builds ~10 stores and each used to
        # re-run the full DDL block. On a live Supabase project that means ten
        # AccessExclusiveLock bursts racing autovacuum/background workers,
        # which deadlocked real boots. One burst, retried once on deadlock.
        if self.url in _SCHEMA_ENSURED:
            return
        psycopg, _, _ = _load_psycopg()
        try:
            self._run_schema_ddl()
        except psycopg.errors.DeadlockDetected:
            import time

            time.sleep(1.0)
            self._run_schema_ddl()
        _SCHEMA_ENSURED.add(self.url)

    def _run_schema_ddl(self) -> None:
        with self._connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute(SCHEMA_SQL)
                cursor.execute(
                    """
                    ALTER TABLE clara_workflow_records
                    ADD COLUMN IF NOT EXISTS tenant_id TEXT NOT NULL DEFAULT 'legacy'
                    """
                )
                cursor.execute(
                    """
                    ALTER TABLE clara_workflow_records
                    ADD COLUMN IF NOT EXISTS retention_expires_at TIMESTAMPTZ
                    """
                )
                cursor.execute(
                    """
                    CREATE INDEX IF NOT EXISTS clara_workflow_tenant_problem_idx
                    ON clara_workflow_records (tenant_id, problem_id, record_type)
                    """
                )
                # Measurement provenance columns (migration 016) self-heal on
                # DBs that predate it; the plpgsql tick itself only lives in
                # the migration file.
                cursor.execute(
                    """
                    ALTER TABLE clara_measurement_plans
                    ADD COLUMN IF NOT EXISTS origin TEXT NOT NULL DEFAULT 'approval',
                    ADD COLUMN IF NOT EXISTS contract_revision INTEGER
                    """
                )
                # Self-heal the tenant-first PK on DBs that predate migration 011.
                # _save_workflow_record's ON CONFLICT names this arbiter, so the
                # swap must happen at boot, before the first write. ~10 rows live;
                # the ACCESS EXCLUSIVE lock is momentary.
                cursor.execute(
                    """
                    DO $$
                    DECLARE
                        pk_cols text;
                    BEGIN
                        SELECT string_agg(a.attname, ',' ORDER BY k.ord) INTO pk_cols
                        FROM pg_constraint c
                        JOIN unnest(c.conkey) WITH ORDINALITY AS k(attnum, ord) ON true
                        JOIN pg_attribute a
                          ON a.attrelid = c.conrelid AND a.attnum = k.attnum
                        WHERE c.conrelid = 'clara_workflow_records'::regclass
                          AND c.contype = 'p';
                        IF pk_cols IS DISTINCT FROM 'tenant_id,record_type,record_id' THEN
                            ALTER TABLE clara_workflow_records
                                DROP CONSTRAINT clara_workflow_records_pkey;
                            ALTER TABLE clara_workflow_records
                                ADD PRIMARY KEY (tenant_id, record_type, record_id);
                        END IF;
                    END $$
                    """
                )
                # Same self-heal for the GUC-based workspace defaults on the ops
                # tables this DDL owns (SCHEMA_SQL creates them correctly on
                # fresh DBs; older DBs carry a literal DEFAULT 1).
                for ops_table in (
                    "clara_telemetry",
                    "clara_measurement_plans",
                    "clara_connector_configs",
                    "clara_api_keys",
                ):
                    cursor.execute(
                        f"""
                        ALTER TABLE {ops_table} ALTER COLUMN workspace_id SET DEFAULT
                        COALESCE(NULLIF(current_setting('app.workspace_id', true), ''), '1')::bigint
                        """
                    )
                # Tenant-first primary keys (migration 014): ids repeat across
                # workspaces, so a single-column PK made every ON CONFLICT
                # collide with a row RLS hides (dropped import / 42501). Swap on
                # boot wherever the table has a workspace_id column; the stores'
                # ON CONFLICT targets name the composite key.
                for table_name, key_col in TENANT_KEYED_TABLES:
                    cursor.execute(
                        """
                        SELECT 1 FROM information_schema.columns
                        WHERE table_schema = current_schema() AND table_name = %s
                          AND column_name = 'workspace_id'
                        """,
                        (table_name,),
                    )
                    if cursor.fetchone() is None:
                        logger.critical(
                            "%s has no workspace_id column (apply migration 004); "
                            "tenant-scoped keys cannot be enforced for it",
                            table_name,
                        )
                        continue
                    cursor.execute(
                        f"""
                        ALTER TABLE {table_name} ALTER COLUMN workspace_id SET DEFAULT
                        COALESCE(NULLIF(current_setting('app.workspace_id', true), ''), '1')::bigint
                        """
                    )
                    cursor.execute(
                        f"""
                        DO $$
                        DECLARE
                            pk_cols text;
                            pk_name text;
                        BEGIN
                            SELECT c.conname, string_agg(a.attname, ',' ORDER BY k.ord)
                              INTO pk_name, pk_cols
                            FROM pg_constraint c
                            JOIN unnest(c.conkey) WITH ORDINALITY AS k(attnum, ord) ON true
                            JOIN pg_attribute a
                              ON a.attrelid = c.conrelid AND a.attnum = k.attnum
                            WHERE c.conrelid = '{table_name}'::regclass
                              AND c.contype = 'p'
                            GROUP BY c.conname;
                            IF pk_cols IS DISTINCT FROM 'workspace_id,{key_col}' THEN
                                IF pk_name IS NOT NULL THEN
                                    EXECUTE format('ALTER TABLE {table_name} DROP CONSTRAINT %I', pk_name);
                                END IF;
                                ALTER TABLE {table_name} ADD PRIMARY KEY (workspace_id, {key_col});
                            END IF;
                        END $$
                        """
                    )
                # api-keys RLS is applied here (not only migration 010) so a boot
                # against a DB that predates the migration self-heals the policy -
                # the 007-era lesson: never leave a clara_ table without RLS.
                cursor.execute("ALTER TABLE clara_api_keys ENABLE ROW LEVEL SECURITY")
                cursor.execute(
                    "DROP POLICY IF EXISTS clara_api_keys_workspace_isolation ON clara_api_keys"
                )
                cursor.execute(
                    """
                    CREATE POLICY clara_api_keys_workspace_isolation ON clara_api_keys
                    USING (
                      workspace_id = COALESCE(NULLIF(current_setting('app.workspace_id', true), ''), '1')::bigint
                      OR current_setting('app.api_key_lookup', true) = 'on'
                    )
                    WITH CHECK (workspace_id = COALESCE(NULLIF(current_setting('app.workspace_id', true), ''), '1')::bigint)
                    """
                )
                # Same self-healed policy for the two loop-closure tables this
                # DDL owns (theme insights + learning memory): a boot against a
                # DB that predates migration 013 must never leave them open.
                for loop_table in ("clara_theme_insights", "clara_learnings"):
                    cursor.execute(f"ALTER TABLE {loop_table} ENABLE ROW LEVEL SECURITY")
                    cursor.execute(
                        f"DROP POLICY IF EXISTS {loop_table}_workspace_isolation ON {loop_table}"
                    )
                    cursor.execute(
                        f"""
                        CREATE POLICY {loop_table}_workspace_isolation ON {loop_table}
                        USING (workspace_id = COALESCE(NULLIF(current_setting('app.workspace_id', true), ''), '1')::bigint)
                        WITH CHECK (workspace_id = COALESCE(NULLIF(current_setting('app.workspace_id', true), ''), '1')::bigint)
                        """
                    )
                    cursor.execute(f"ALTER TABLE {loop_table} FORCE ROW LEVEL SECURITY")
                cursor.execute("ALTER TABLE clara_workflow_records ENABLE ROW LEVEL SECURITY")
                # FORCE = the policies bind the table owner too (the app connects
                # as `postgres`). Without it every policy here is decorative —
                # the core of review finding #25. Migration 011 forces the other
                # clara_ tables; these two are self-healed because this DDL owns
                # their policies.
                cursor.execute("ALTER TABLE clara_api_keys FORCE ROW LEVEL SECURITY")
                cursor.execute("ALTER TABLE clara_workflow_records FORCE ROW LEVEL SECURITY")
                # Defense in depth for the other clara_ tables (audit finding T1):
                # migration 011 FORCEs RLS on all of them, but if 011 was never
                # applied they stay merely ENABLEd and the owner (the app role)
                # bypasses RLS -> cross-workspace reads. Self-heal that here so
                # isolation lives in code, not only in a migration. FORCE only
                # where a policy already exists (else FORCE = deny-all); a table
                # with RLS but no policy is logged loudly instead of bricked.
                cursor.execute(
                    """
                    SELECT c.relname,
                           c.relrowsecurity  AS enabled,
                           c.relforcerowsecurity AS forced,
                           EXISTS (SELECT 1 FROM pg_policy p WHERE p.polrelid = c.oid) AS has_policy
                    FROM pg_class c
                    JOIN pg_namespace n ON n.oid = c.relnamespace
                    WHERE n.nspname = current_schema()
                      AND c.relkind = 'r'
                      AND c.relname LIKE 'clara\\_%'
                    """
                )
                for row in cursor.fetchall():
                    name = row["relname"] if isinstance(row, dict) else row[0]
                    forced = row["forced"] if isinstance(row, dict) else row[2]
                    has_policy = row["has_policy"] if isinstance(row, dict) else row[3]
                    if forced:
                        continue
                    if has_policy:
                        # name is a clara_ table identifier from pg_class, never
                        # user input — safe to interpolate.
                        cursor.execute(  # noqa: S608
                            f"ALTER TABLE {name} FORCE ROW LEVEL SECURITY"
                        )
                    else:
                        logger.critical(
                            "RLS NOT enforced on %s (no policy, not forced) — apply "
                            "migration 011; cross-workspace isolation is not guaranteed "
                            "for this table until then.",
                            name,
                        )
                cursor.execute(
                    """
                    DROP POLICY IF EXISTS clara_workflow_records_tenant_isolation
                    ON clara_workflow_records
                    """
                )
                cursor.execute(
                    """
                    CREATE POLICY clara_workflow_records_tenant_isolation
                    ON clara_workflow_records
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
        # SQLite-contract parity: seed problems are read-only reference content.
        self.seed_problem_ids = {problem.problem_id for problem in seed_problems}
        if not self.list_problems():
            for problem in seed_problems:
                self.upsert_problem(problem)

    def list_problems(self) -> list[ProblemRecord]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT payload FROM clara_problems ORDER BY problem_id"
            ).fetchall()
        return [ProblemRecord.model_validate(_payload(row["payload"])) for row in rows]

    def get_problem(self, problem_id: str) -> ProblemRecord | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT payload FROM clara_problems WHERE problem_id = %s",
                (problem_id,),
            ).fetchone()
        if row is None:
            return None
        return ProblemRecord.model_validate(_payload(row["payload"]))

    def upsert_problem(self, problem: ProblemRecord) -> ProblemRecord:
        # SQLite-contract parity: upsert is INSERT-ONLY — promoting a candidate
        # twice must return the existing problem, never overwrite edits/approvals.
        existing = self.get_problem(problem.problem_id)
        if existing is not None:
            return existing
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO clara_problems (problem_id, payload)
                VALUES (%s, %s)
                ON CONFLICT (workspace_id, problem_id) DO NOTHING
                """,
                (problem.problem_id, self._jsonb(_model_payload(problem))),
            )
        return problem

    def _write_problem(self, problem: ProblemRecord) -> ProblemRecord:
        """Internal overwrite for update paths (the old upsert semantics)."""
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO clara_problems (problem_id, payload)
                VALUES (%s, %s)
                ON CONFLICT (workspace_id, problem_id) DO UPDATE
                SET payload = excluded.payload, updated_at = now()
                """,
                (problem.problem_id, self._jsonb(_model_payload(problem))),
            )
        return problem

    def _guarded_write(self, problem_id: str, mutate, guard) -> ProblemRecord | None:
        """Read, guard and write in ONE transaction under the problem's
        advisory lock, so an approval insert (which takes the same lock,
        PostgresWorkflowStore.record_approval) cannot land between the guard
        and the write on another worker. ``guard`` raises to refuse."""
        if problem_id in self.seed_problem_ids:
            return None
        with self._connect() as conn:
            conn.execute("SELECT pg_advisory_xact_lock(hashtext(%s))", (advisory_lock_key(problem_id),))
            row = conn.execute(
                "SELECT payload FROM clara_problems WHERE problem_id = %s FOR UPDATE",
                (problem_id,),
            ).fetchone()
            if row is None:
                return None
            existing = ProblemRecord.model_validate(_payload(row["payload"]))
            if guard is not None:
                guard()
            updated = mutate(existing)
            if updated is None:
                return None
            conn.execute(
                """
                INSERT INTO clara_problems (problem_id, payload)
                VALUES (%s, %s)
                ON CONFLICT (workspace_id, problem_id) DO UPDATE
                SET payload = excluded.payload, updated_at = now()
                """,
                (updated.problem_id, self._jsonb(_model_payload(updated))),
            )
        return updated

    def update_problem(self, problem_id: str, update, *, guard=None) -> ProblemRecord | None:
        return self._guarded_write(
            problem_id, lambda existing: apply_problem_update(existing, update), guard
        )

    def update_action_proposal(self, problem_id: str, action_id: str, update, *, guard=None):
        return self._guarded_write(
            problem_id,
            lambda existing: apply_action_proposal_update(existing, action_id, update),
            guard,
        )

    def transition_problem_status(
        self,
        problem_id: str,
        status: ProblemStatus,
    ) -> ProblemRecord | None:
        existing = self.get_problem(problem_id)
        if existing is None or problem_id in self.seed_problem_ids:
            return None
        updated = apply_problem_status(existing, status)
        return self._write_problem(updated)

    def update_outcome_contract(
        self,
        problem_id: str,
        update,
        *,
        actor: str | None = None,
        note: str | None = None,
    ) -> ProblemRecord | None:
        existing = self.get_problem(problem_id)
        if existing is None or problem_id in self.seed_problem_ids:
            return None
        updated = apply_outcome_contract_update(existing, update, actor=actor, note=note)
        return self._write_problem(updated)

    def scrub_customer(self, customer_id: str) -> int:
        """GDPR Art. 17: erase a customer's evidence content inside stored problems."""
        scrubbed = 0
        for problem in self.list_problems():
            updated = scrub_customer_evidence(problem, customer_id)
            if updated is not None:
                self._write_problem(updated)
                scrubbed += 1
        return scrubbed


class PostgresSignalStore(PostgresConnectionMixin):
    def list_signals(self) -> list[SignalRecord]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT payload FROM clara_signals ORDER BY payload->>'timestamp', signal_id"
            ).fetchall()
        return [SignalRecord.model_validate(_payload(row["payload"])) for row in rows]

    def import_signals(self, signals: list[SignalRecord]) -> SignalImportResult:
        imported = 0
        with self._connect() as conn:
            for signal in signals:
                # rowcount is 0 when ON CONFLICT skips — counts real inserts, so
                # duplicates WITHIN one batch are reported as skipped (SQLite parity).
                result = conn.execute(
                    """
                    INSERT INTO clara_signals (signal_id, payload)
                    VALUES (%s, %s)
                    ON CONFLICT (workspace_id, signal_id) DO NOTHING
                    """,
                    (signal.signal_id, self._jsonb(_model_payload(signal))),
                )
                imported += result.rowcount
        return SignalImportResult(
            imported=imported,
            skipped_duplicates=len(signals) - imported,
            total_signals=len(self.list_signals()),
        )

    def candidates(self):
        from app.services.signals import theme_candidates

        signals = self.list_signals()
        return [*build_candidates(signals), *theme_candidates(self.list_theme_insights(), signals)]

    def save_theme_insights(self, insights: list[dict[str, Any]], *, run_id: str) -> int:
        from app.services.signals import prepare_theme_insight

        saved = 0
        with self._connect() as conn:
            for insight in insights:
                prepared = prepare_theme_insight(insight, run_id=run_id)
                if prepared is None:
                    continue
                conn.execute(
                    """
                    INSERT INTO clara_theme_insights (theme_tag, payload)
                    VALUES (%s, %s)
                    ON CONFLICT (workspace_id, theme_tag) DO UPDATE
                    SET payload = excluded.payload, updated_at = now()
                    """,
                    (prepared["tag"], self._jsonb(prepared)),
                )
                saved += 1
        return saved

    def list_theme_insights(self) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT payload FROM clara_theme_insights ORDER BY theme_tag"
            ).fetchall()
        return [_payload(row["payload"]) for row in rows]

    def get_candidate_decision(self, candidate_id: str) -> CandidateDecisionRecord | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT payload FROM clara_candidate_decisions WHERE candidate_id = %s",
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
                INSERT INTO clara_candidate_decisions (candidate_id, payload)
                VALUES (%s, %s)
                ON CONFLICT (workspace_id, candidate_id) DO UPDATE
                SET payload = excluded.payload, updated_at = now()
                """,
                (candidate_id, self._jsonb(_model_payload(record))),
            )
        return record

    def update_enrichment(
        self,
        signal_id: str,
        *,
        sentiment: str | None,
        urgency: str | None,
        tags: list[str] | None = None,
    ) -> None:
        patch = {
            "sentiment": sentiment,
            "urgency": urgency,
            "tags": list(tags or []),
            "enriched": True,
        }
        with self._connect() as conn:
            conn.execute(
                "UPDATE clara_signals SET payload = payload || %s WHERE signal_id = %s",
                (self._jsonb(patch), signal_id),
            )

    def update_metadata(self, signal_id: str, metadata: dict[str, str]) -> None:
        """Persist an annotation onto a stored signal. Used by the authenticity
        backfill; the record itself is never otherwise altered."""
        with self._connect() as conn:
            conn.execute(
                "UPDATE clara_signals SET payload = payload || %s WHERE signal_id = %s",
                (self._jsonb({"metadata": dict(metadata)}), signal_id),
            )

    def existing_signal_ids(self) -> set[str]:
        with self._connect() as conn:
            rows = conn.execute("SELECT signal_id FROM clara_signals").fetchall()
        return {row["signal_id"] for row in rows}

    def delete_by_customer(self, customer_id: str) -> int:
        with self._connect() as conn:
            rows = conn.execute(
                "DELETE FROM clara_signals WHERE payload->>'customer_id' = %s RETURNING signal_id",
                (customer_id,),
            ).fetchall()
        return len(rows)

    def delete_signals(self, signal_ids: list[str]) -> int:
        """Bulk-remove signals by id — the undo for a mis-mapped import batch."""
        if not signal_ids:
            return 0
        with self._connect() as conn:
            rows = conn.execute(
                "DELETE FROM clara_signals WHERE signal_id = ANY(%s) RETURNING signal_id",
                (list(signal_ids),),
            ).fetchall()
        return len(rows)


class PostgresJourneyEventStore(PostgresConnectionMixin):
    def list_events(self) -> list[JourneyEventRecord]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT payload FROM clara_journey_events ORDER BY event_id"
            ).fetchall()
        return [JourneyEventRecord.model_validate(_payload(row["payload"])) for row in rows]

    def import_events(self, events: list[JourneyEventRecord]) -> JourneyEventImportResult:
        imported = 0
        with self._connect() as conn:
            for event in events:
                result = conn.execute(
                    """
                    INSERT INTO clara_journey_events (event_id, payload)
                    VALUES (%s, %s)
                    ON CONFLICT (workspace_id, event_id) DO NOTHING
                    """,
                    (event.event_id, self._jsonb(_model_payload(event))),
                )
                imported += result.rowcount
        return JourneyEventImportResult(
            imported=imported,
            skipped_duplicates=len(events) - imported,
            total_events=len(self.list_events()),
        )

    def existing_event_ids(self) -> set[str]:
        with self._connect() as conn:
            rows = conn.execute("SELECT event_id FROM clara_journey_events").fetchall()
        return {row["event_id"] for row in rows}

    def delete_by_customer(self, customer_id: str) -> int:
        with self._connect() as conn:
            rows = conn.execute(
                "DELETE FROM clara_journey_events WHERE payload->>'customer_id' = %s RETURNING event_id",
                (customer_id,),
            ).fetchall()
        return len(rows)


class PostgresCustomerContextStore(PostgresConnectionMixin, CustomerContextStore):
    def list_context(self) -> list[CustomerContextRecord]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT payload FROM clara_customer_context ORDER BY customer_id"
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
                    INSERT INTO clara_customer_context (customer_id, account_id, payload)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (workspace_id, customer_id) DO UPDATE
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
            rows = conn.execute("SELECT customer_id FROM clara_customer_context").fetchall()
        return {row["customer_id"] for row in rows}

    def delete_by_customer(self, customer_id: str) -> int:
        with self._connect() as conn:
            rows = conn.execute(
                "DELETE FROM clara_customer_context WHERE customer_id = %s RETURNING customer_id",
                (customer_id,),
            ).fetchall()
        return len(rows)


# Reads tolerate a briefly-stale snapshot: the dashboard's outcome board calls
# outcome_snapshot + latest_learning_conclusion once per problem, and re-reading
# the whole clara_workflow_records table 2×N times per request over the session
# pooler took the production dashboard from seconds to minutes (16 Jul incident).
# Writes force a refresh regardless — their ID counters must be current, or a
# collision would silently overwrite another instance's record via ON CONFLICT.
_WORKFLOW_REFRESH_TTL_SECONDS = 2.0


class PostgresWorkflowStore(PostgresConnectionMixin, WorkflowStore):
    """DB-backed workflow store.

    #23 parity: multiple instances (local dev + Render) share one database, so
    every public operation re-reads the records instead of trusting the
    boot-time snapshot — a boot snapshot served stale approvals/outcomes and
    reused ID counters across instances. Reads reuse a snapshot younger than
    _WORKFLOW_REFRESH_TTL_SECONDS (cross-instance freshness degrades from
    immediate to <=2s); writes always refresh first.
    """

    def __init__(self, url: str) -> None:
        PostgresConnectionMixin.__init__(self, url)
        WorkflowStore.__init__(self)
        self._load_records()

    # -- reads: refresh, then delegate to the in-memory logic --

    def refresh(self) -> None:
        """Force a reload: reads normally reuse a snapshot younger than
        _WORKFLOW_REFRESH_TTL_SECONDS, which is fine for dashboards but not
        for deciding whether a dispatch is still authorized."""
        self._load_records(force=True)

    def list_approvals(self):
        self._load_records()
        return WorkflowStore.list_approvals(self)

    def list_executions(self):
        self._load_records()
        return WorkflowStore.list_executions(self)

    def list_jira_issue_drafts(self):
        self._load_records()
        return WorkflowStore.list_jira_issue_drafts(self)

    def list_closure_records(self):
        self._load_records()
        return WorkflowStore.list_closure_records(self)

    def latest_learning_conclusion(self, problem, tenant_id=None):
        self._load_records()
        return WorkflowStore.latest_learning_conclusion(self, problem, tenant_id=tenant_id)

    def outcome_snapshot(self, problem):
        self._load_records()
        return WorkflowStore.outcome_snapshot(self, problem)

    def state_for_problem(self, problem, tenant_id=None):
        self._load_records()
        return WorkflowStore.state_for_problem(self, problem, tenant_id=tenant_id)

    def timeline_for_problem(self, problem, tenant_id=None):
        self._load_records()
        return WorkflowStore.timeline_for_problem(self, problem, tenant_id=tenant_id)

    def _load_records(self, *, force: bool = False) -> None:
        # getattr: tests construct via __new__ without __init__, so the
        # timestamp may not exist yet — treat that as "never loaded".
        # The cache is keyed by tenant as well as by age: RLS scopes the SELECT
        # below to the tenant GUC, so a cached snapshot loaded under tenant A
        # must never be served to a request (or background tick) for tenant B.
        tenant = current_tenant()
        if (
            not force
            and getattr(self, "_records_tenant", None) == tenant
            and time.monotonic() - getattr(self, "_records_loaded_at", 0.0)
            < _WORKFLOW_REFRESH_TTL_SECONDS
        ):
            return
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT record_type, payload
                FROM clara_workflow_records
                ORDER BY created_at, record_id
                """
            ).fetchall()

        approvals: list[ApprovalRecord] = []
        executions: list[ExecutionRecord] = []
        jira_drafts: list[JiraIssueDraft] = []
        transitions: list[ProblemTransitionRecord] = []
        outcomes: dict[str, OutcomeMeasurement] = {}
        learning_conclusions: list[LearningConclusionRecord] = []
        closure_records: list[ClosureRecord] = []
        guardrails: list[GuardrailMeasurement] = []

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
            elif record_type == "closure":
                closure_records.append(ClosureRecord.model_validate(payload))
            elif record_type == "guardrail":
                guardrails.append(GuardrailMeasurement.model_validate(payload))

        self._approvals = approvals
        self._executions = executions
        self._jira_issue_drafts = jira_drafts
        self._transitions = transitions
        self._outcomes = outcomes
        self._learning_conclusions = learning_conclusions
        self._closure_records = closure_records
        self._approval_ids = count(_next_id(approvals, "decision_id", "DEC") + 1)
        self._execution_ids = count(_next_id(executions, "execution_id", "EXE") + 1)
        # draft_id format is "JIRA-DRAFT-%04d" (workflow.py) — the prefix must match
        # exactly or _next_id never resumes and regenerates colliding IDs after restart.
        self._jira_draft_ids = count(_next_id(jira_drafts, "draft_id", "JIRA-DRAFT") + 1)
        self._transition_ids = count(_next_id(transitions, "transition_id", "TRN") + 1)
        self._closure_ids = count(_next_id(closure_records, "closure_id", "CLR") + 1)
        self._guardrails = guardrails
        self._guardrail_ids = count(_next_id(guardrails, "guardrail_id", "GRD") + 1)
        self._records_loaded_at = time.monotonic()
        self._records_tenant = tenant

    def _save_workflow_record(
        self,
        record_type: str,
        record_id: str,
        problem_id: str,
        record: Any,
        tenant_id: str | None = None,
        retention_expires_at: str | None = None,
        conn: Any = None,
    ) -> None:
        # Default to the request's tenant (auth ContextVar) so every record type
        # — transitions, approvals, outcomes, executions, drafts — satisfies the
        # FORCEd RLS WITH CHECK; the old 'legacy' default would be rejected.
        tenant_id = tenant_id or current_tenant()
        if conn is not None:
            self._write_record(conn, record_type, record_id, problem_id, record, tenant_id, retention_expires_at)
            return
        with self._connect() as conn:
            self._write_record(conn, record_type, record_id, problem_id, record, tenant_id, retention_expires_at)

    def _write_record(
        self,
        conn: Any,
        record_type: str,
        record_id: str,
        problem_id: str,
        record: Any,
        tenant_id: str,
        retention_expires_at: str | None,
    ) -> None:
        conn.execute("SELECT set_config('app.tenant_id', %s, true)", (tenant_id,))
        conn.execute(
            """
            INSERT INTO clara_workflow_records (
                record_type,
                record_id,
                problem_id,
                tenant_id,
                payload,
                retention_expires_at
            )
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (tenant_id, record_type, record_id) DO UPDATE
            SET problem_id = excluded.problem_id,
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
        self._load_records(force=True)
        transition = WorkflowStore.record_transition(self, *args, **kwargs)
        self._save_workflow_record(
            "transition",
            transition.transition_id,
            transition.problem_id,
            transition,
        )
        return transition

    def record_approval(self, *, problem, decision, evidence_pack_hash=None, four_eyes=False):
        """Record the decision and the execution it completes in ONE
        transaction under the problem's advisory lock (the same key the
        problem store's guarded writes take). Inside the lock the stored
        problem is compared with the one the reviewer decided on: a governed
        edit committed by another worker in between makes the decision a 409
        instead of an approval that signs text the reviewer never read."""
        self._load_records(force=True)
        before_executions = {execution.execution_id for execution in self._executions}
        before_drafts = {draft.draft_id for draft in self._jira_issue_drafts}
        with self._connect() as conn:
            conn.execute(
                "SELECT pg_advisory_xact_lock(hashtext(%s))", (advisory_lock_key(problem.problem_id),)
            )
            row = conn.execute(
                "SELECT payload FROM clara_problems WHERE problem_id = %s", (problem.problem_id,)
            ).fetchone()
            if row is not None:
                stored = ProblemRecord.model_validate(_payload(row["payload"]))
                stored_action = find_action(stored, decision.action_id)
                given_action = find_action(problem, decision.action_id)
                if stored_action is not None and given_action is not None:
                    from app.services.outbound import build_outbound_content

                    if build_outbound_content(stored, stored_action) != build_outbound_content(
                        problem, given_action
                    ):
                        raise HTTPException(
                            status_code=409,
                            detail=(
                                "The problem or action changed while the decision was being "
                                "recorded; reload and review the current text before deciding."
                            ),
                        )
            approval = WorkflowStore.record_approval(
                self,
                problem=problem,
                decision=decision,
                evidence_pack_hash=evidence_pack_hash,
                four_eyes=four_eyes,
            )
            self._save_workflow_record(
                "approval", approval.decision_id, approval.problem_id, approval, conn=conn
            )
            for execution in self._executions:
                if execution.execution_id not in before_executions:
                    self._save_workflow_record(
                        "execution", execution.execution_id, execution.problem_id, execution, conn=conn
                    )
            for draft in self._jira_issue_drafts:
                if draft.draft_id not in before_drafts:
                    self._save_workflow_record(
                        "jira_draft", draft.draft_id, draft.problem_id, draft, conn=conn
                    )
        return approval

    def add_guardrail_measurement(self, *args: Any, **kwargs: Any):
        self._load_records(force=True)
        record = WorkflowStore.add_guardrail_measurement(self, *args, **kwargs)
        self._save_workflow_record(
            "guardrail",
            record.guardrail_id,
            record.problem_id,
            record,
        )
        return record

    def list_guardrail_measurements(self, problem_id: str):
        self._load_records()
        return WorkflowStore.list_guardrail_measurements(self, problem_id)

    def record_outcome(self, *args: Any, **kwargs: Any):
        self._load_records(force=True)
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
        self._load_records(force=True)
        conclusion = WorkflowStore.record_learning_conclusion(self, *args, **kwargs)
        self._save_workflow_record(
            "learning_conclusion",
            conclusion.conclusion_id,
            conclusion.problem_id,
            conclusion,
            conclusion.tenant_id,
            conclusion.retention_expires_at,
        )
        return conclusion

    def record_closure(self, *args: Any, **kwargs: Any):
        self._load_records(force=True)
        closure = WorkflowStore.record_closure(self, *args, **kwargs)
        self._save_workflow_record(
            "closure",
            closure.closure_id,
            closure.problem_id,
            closure,
            closure.tenant_id,
        )
        return closure

    def add_execution(self, execution):
        self._load_records(force=True)  # syncs the EXE- id counter before assignment
        record = super().add_execution(execution)
        self._save_workflow_record("execution", record.execution_id, record.problem_id, record)
        return record

    def update_execution(
        self,
        execution_id,
        *,
        status,
        external_ref=None,
        detail=None,
        disclosure_applied=None,
        dispatched_at=None,
        implemented_at=None,
        implementation_note=None,
    ):
        self._load_records(force=True)
        # Base class mutates the in-memory record; persist the flip too, or a
        # restart resurrects executions as eternal drafts.
        updated = super().update_execution(
            execution_id,
            status=status,
            external_ref=external_ref,
            detail=detail,
            disclosure_applied=disclosure_applied,
            dispatched_at=dispatched_at,
            implemented_at=implemented_at,
            implementation_note=implementation_note,
        )
        self._save_workflow_record("execution", updated.execution_id, updated.problem_id, updated)
        return updated

    def scrub_customer_references(self, customer_id: str) -> int:
        scrubbed = super().scrub_customer_references(customer_id)
        if scrubbed:
            for draft in self._jira_issue_drafts:
                self._save_workflow_record("jira_draft", draft.draft_id, draft.problem_id, draft)
        return scrubbed

    def claim_dispatch(self, execution_id, *, worker, now=None):
        """DB-level compare-and-set: ONE conditional UPDATE on the execution
        row decides the claim, so two workers (or two pods) cannot both win
        and the in-process lock is no longer the only guard. The row must be
        dispatchable and carry no live claim (a claim older than
        DISPATCH_CLAIM_TTL_SECONDS is taken over)."""
        now = now or utc_now()
        tenant_id = current_tenant()
        with self._connect() as conn:
            row = conn.execute(
                """
                UPDATE clara_workflow_records
                SET payload = payload || jsonb_build_object(
                        'dispatch_claimed_at', %s::text, 'dispatch_claimed_by', %s::text),
                    updated_at = now()
                WHERE tenant_id = %s AND record_type = 'execution' AND record_id = %s
                  AND payload->>'status' IN ('draft_created', 'push_failed')
                  AND (
                    NULLIF(payload->>'dispatch_claimed_at', '') IS NULL
                    OR NULLIF(payload->>'dispatch_claimed_at', '')::timestamptz
                       <= %s::timestamptz - make_interval(secs => %s)
                  )
                RETURNING payload
                """,
                (now, worker, tenant_id, execution_id, now, DISPATCH_CLAIM_TTL_SECONDS),
            ).fetchone()
        if row is None:
            return None
        self._load_records(force=True)
        return ExecutionRecord.model_validate(_payload(row["payload"]))

    def release_dispatch(self, execution_id) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE clara_workflow_records
                SET payload = payload - 'dispatch_claimed_at' - 'dispatch_claimed_by',
                    updated_at = now()
                WHERE tenant_id = %s AND record_type = 'execution' AND record_id = %s
                """,
                (current_tenant(), execution_id),
            )
        self._load_records(force=True)


def _next_id(records: list[Any], field_name: str, prefix: str) -> int:
    pattern = re.compile(rf"^{re.escape(prefix)}-(\d+)$")
    maximum = 0
    for record in records:
        match = pattern.match(getattr(record, field_name))
        if match:
            maximum = max(maximum, int(match.group(1)))
    return maximum


class PostgresTaxonomyStore(PostgresConnectionMixin, TaxonomyStore):
    """Per-workspace taxonomy catalogs.

    The base store keeps one in-memory catalog list. Here that list is swapped
    to the active tenant's catalogs (lazy-loaded under RLS) around every
    operation, under a lock, so workspace 2 never reads or edits workspace 1's
    taxonomy — the pitch's "trained on YOUR taxonomy" needs the taxonomy to be
    yours. Bootstrap proposals and review decisions are persisted too (they
    used to live in memory only).
    """

    def __init__(self, url: str) -> None:
        PostgresConnectionMixin.__init__(self, url)
        self._lock = threading.RLock()
        self._by_tenant: dict[str, list[TaxonomyCatalog]] = {}
        TaxonomyStore.__init__(self, self._catalogs_for_tenant())

    def _catalogs_for_tenant(self) -> list[TaxonomyCatalog]:
        tenant = current_tenant()
        with self._lock:
            catalogs = self._by_tenant.get(tenant)
            if catalogs is None:
                catalogs = self._load_catalogs()
                if not catalogs:
                    for catalog in load_seed_taxonomies():
                        self._save_catalog(catalog)
                    catalogs = self._load_catalogs()
                self._by_tenant[tenant] = catalogs
            return catalogs

    def _run(self, operation, *args: Any, **kwargs: Any):
        with self._lock:
            self._catalogs = self._catalogs_for_tenant()
            result = operation(self, *args, **kwargs)
            self._by_tenant[current_tenant()] = self._catalogs
            return result

    def list_catalogs(self) -> list[TaxonomyCatalog]:
        return list(self._catalogs_for_tenant())

    def version_key(self) -> str:
        return self._run(TaxonomyStore.version_key)

    def _load_catalogs(self) -> list[TaxonomyCatalog]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT payload FROM clara_taxonomy_catalogs ORDER BY taxonomy_type"
            ).fetchall()
        return [TaxonomyCatalog.model_validate(_payload(row["payload"])) for row in rows]

    def _save_catalog(self, catalog: TaxonomyCatalog) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO clara_taxonomy_catalogs (taxonomy_type, payload)
                VALUES (%s, %s)
                ON CONFLICT (workspace_id, taxonomy_type) DO UPDATE
                SET payload = excluded.payload, updated_at = now()
                """,
                (catalog.taxonomy_type.value, self._jsonb(_model_payload(catalog))),
            )

    def _mutate(self, operation, *args: Any, **kwargs: Any) -> TaxonomyCatalog:
        catalog = self._run(operation, *args, **kwargs)
        self._save_catalog(catalog)
        return catalog

    def rename_category(self, *args: Any, **kwargs: Any) -> TaxonomyCatalog:
        return self._mutate(TaxonomyStore.rename_category, *args, **kwargs)

    def lock_category(self, *args: Any, **kwargs: Any) -> TaxonomyCatalog:
        return self._mutate(TaxonomyStore.lock_category, *args, **kwargs)

    def merge_categories(self, *args: Any, **kwargs: Any) -> TaxonomyCatalog:
        return self._mutate(TaxonomyStore.merge_categories, *args, **kwargs)

    def split_category(self, *args: Any, **kwargs: Any) -> TaxonomyCatalog:
        return self._mutate(TaxonomyStore.split_category, *args, **kwargs)

    def propose_category(self, *args: Any, **kwargs: Any) -> TaxonomyCatalog:
        return self._mutate(TaxonomyStore.propose_category, *args, **kwargs)

    def review_category(self, *args: Any, **kwargs: Any) -> TaxonomyCatalog:
        return self._mutate(TaxonomyStore.review_category, *args, **kwargs)


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
                "SELECT payload FROM clara_terminology_dictionary ORDER BY term_id"
            ).fetchall()
        return [
            TerminologyDictionaryEntry.model_validate(_payload(row["payload"]))
            for row in rows
        ]

    def _save_entry(self, entry: TerminologyDictionaryEntry) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO clara_terminology_dictionary (term_id, payload)
                VALUES (%s, %s)
                ON CONFLICT (workspace_id, term_id) DO UPDATE
                SET payload = excluded.payload, updated_at = now()
                """,
                (entry.term_id, self._jsonb(_model_payload(entry))),
            )


class PostgresWorkspaceStore(PostgresConnectionMixin):
    def list_workspace_ids(self) -> list[int]:
        """Every workspace the background tick must serve.

        public.workspaces is the Supabase-side registry (004); without it the
        loop stays on the default workspace, which is also the pre-multi-tenant
        behaviour, so this never fails a boot.
        """
        try:
            with self._connect() as conn:
                rows = conn.execute("SELECT id FROM public.workspaces ORDER BY id").fetchall()
            ids = [int(row["id"]) for row in rows]
        except Exception:  # noqa: BLE001 — registry optional
            logger.warning("public.workspaces unavailable; background tick serves workspace 1 only")
            return [1]
        return ids or [1]

    def get(self, workspace_id: int) -> WorkspaceSettings:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT payload FROM clara_workspace_settings WHERE workspace_id = %s",
                (workspace_id,),
            ).fetchone()
        if row is None:
            return WorkspaceSettings()
        return WorkspaceSettings.model_validate(_payload(row["payload"]))

    def put(self, workspace_id: int, settings: WorkspaceSettings) -> WorkspaceSettings:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO clara_workspace_settings (workspace_id, payload)
                VALUES (%s, %s)
                ON CONFLICT (workspace_id) DO UPDATE
                SET payload = excluded.payload, updated_at = now()
                """,
                (workspace_id, self._jsonb(_model_payload(settings))),
            )
        return settings


class PostgresRuleStore(PostgresConnectionMixin):
    def __init__(self, url: str) -> None:
        super().__init__(url)
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS clara_feedback_rules (
                    rule_id TEXT PRIMARY KEY,
                    payload JSONB NOT NULL,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
                )
                """
            )

    def list_rules(self) -> list[FeedbackRule]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT payload FROM clara_feedback_rules ORDER BY created_at DESC"
            ).fetchall()
        rules = [FeedbackRule.model_validate(_payload(row["payload"])) for row in rows]
        return sorted(rules, key=lambda rule: rule.priority, reverse=True)

    def create_rule(self, create: FeedbackRuleCreate) -> FeedbackRule:
        rule = FeedbackRule(rule_id=f"RULE-{uuid4().hex[:8]}", **create.model_dump())
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO clara_feedback_rules (rule_id, payload) VALUES (%s, %s)",
                (rule.rule_id, self._jsonb(_model_payload(rule))),
            )
        return rule

    def delete_rule(self, rule_id: str) -> bool:
        with self._connect() as conn:
            row = conn.execute(
                "DELETE FROM clara_feedback_rules WHERE rule_id = %s RETURNING rule_id",
                (rule_id,),
            ).fetchone()
        return row is not None


class PostgresTelemetryStore(PostgresConnectionMixin):
    """Postgres-backed telemetry (parity with SQLiteTelemetryStore)."""

    def record(
        self,
        event_type: str,
        *,
        entity_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        try:
            with self._connect() as conn:
                # workspace_id intentionally not in the column list: the GUC-based
                # DEFAULT stamps the active tenant, and an explicit value from a
                # different tenant would fail the FORCEd WITH CHECK (silently,
                # thanks to the swallow below).
                conn.execute(
                    "INSERT INTO clara_telemetry (event_type, entity_id, metadata)"
                    " VALUES (%s, %s, %s)",
                    (event_type, entity_id, self._jsonb(metadata or {})),
                )
        except Exception:  # noqa: BLE001 — metrics never break the product...
            # ...but loop verdicts and audit events must not vanish without a trace.
            logger.warning("telemetry write failed for %s", event_type, exc_info=True)

    def list_events(self, *, limit: int = 500) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT id, workspace_id, event_type, entity_id, metadata, created_at"
                " FROM clara_telemetry ORDER BY id DESC LIMIT %s",
                (limit,),
            ).fetchall()
        return [
            {
                "id": row["id"],
                "workspace_id": row["workspace_id"],
                "event_type": row["event_type"],
                "entity_id": row["entity_id"],
                "metadata": _payload(row["metadata"]),
                "created_at": str(row["created_at"]),
            }
            for row in rows
        ]

    def counts_by_type(self) -> dict[str, int]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT event_type, COUNT(*) AS n FROM clara_telemetry GROUP BY event_type"
            ).fetchall()
        return {row["event_type"]: row["n"] for row in rows}

    def has_event(self, event_type: str, entity_id: str) -> bool:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT 1 FROM clara_telemetry WHERE event_type = %s AND entity_id = %s LIMIT 1",
                (event_type, entity_id),
            ).fetchone()
        return row is not None

    def latest_event_at(self, event_type: str) -> str | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT created_at FROM clara_telemetry WHERE event_type = %s"
                " ORDER BY id DESC LIMIT 1",
                (event_type,),
            ).fetchone()
        return str(row["created_at"]) if row else None


class PostgresMeasurementPlanStore(PostgresConnectionMixin):
    """Postgres-backed measurement checkpoints (parity with the SQLite store)."""

    def schedule(
        self,
        *,
        problem_id: str,
        execution_id: str,
        executed_at: str,
        due_at: str,
        kind: str,
        origin: str = "approval",
        contract_revision: int | None = None,
    ) -> bool:
        """Insert one checkpoint; False when an equivalent pending plan exists
        (same contract as the SQLite store, so callers report dedup honestly)."""
        with self._connect() as conn:
            existing = conn.execute(
                "SELECT id FROM clara_measurement_plans"
                " WHERE problem_id = %s AND kind = %s AND status IN ('pending', 'manual_required')",
                (problem_id, kind),
            ).fetchone()
            if existing:
                return False
            conn.execute(
                "INSERT INTO clara_measurement_plans"
                " (problem_id, execution_id, executed_at, due_at, kind, origin, contract_revision)"
                " VALUES (%s, %s, %s, %s, %s, %s, %s)",
                (problem_id, execution_id, executed_at, due_at, kind, origin, contract_revision),
            )
        return True

    def supersede_pending(
        self, problem_id: str, *, note: str, origins: set[str] | None = None
    ) -> int:
        """SQLite-store parity: live plans (pending or manual_required) are
        superseded, optionally only those running from one of ``origins``."""
        sql = (
            "UPDATE clara_measurement_plans SET status = 'superseded', note = %s"
            " WHERE problem_id = %s AND status IN ('pending', 'manual_required')"
        )
        params: list[Any] = [note, problem_id]
        if origins is not None:
            if not origins:
                return 0
            sql += " AND origin = ANY(%s)"
            params.append(sorted(origins))
        with self._connect() as conn:
            result = conn.execute(sql, params)
            return result.rowcount

    def _row_to_plan(self, row: Any) -> dict[str, Any]:
        return {
            "id": row["id"],
            "problem_id": row["problem_id"],
            "execution_id": row["execution_id"],
            "executed_at": row["executed_at"],
            "due_at": row["due_at"],
            "kind": row["kind"],
            "status": row["status"],
            "note": row["note"],
            "created_at": str(row["created_at"]),
            "origin": row.get("origin") or "approval",
            "contract_revision": row.get("contract_revision"),
        }

    def list_plans(self) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM clara_measurement_plans ORDER BY due_at"
            ).fetchall()
        return [self._row_to_plan(row) for row in rows]

    def due(self, now: str) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM clara_measurement_plans"
                " WHERE status = 'pending' AND due_at <= %s ORDER BY due_at",
                (now,),
            ).fetchall()
        return [self._row_to_plan(row) for row in rows]

    def mark(self, plan_id: int, *, status: str, note: str | None = None) -> None:
        with self._connect() as conn:
            conn.execute(
                "UPDATE clara_measurement_plans SET status = %s, note = %s WHERE id = %s",
                (status, note, plan_id),
            )

    def run_due(self, now: str | None = None) -> dict[str, int]:
        """Process due checkpoints via the DB-side function (migration 011).

        clara_run_due_measurements is the single Postgres implementation of the
        measurement tick — pg_cron runs it on schedule, and the in-process loop
        + manual endpoint call it here (FOR UPDATE SKIP LOCKED inside makes
        concurrent callers skip in-flight plans, so nothing double-fires).
        Scoped to the caller's workspace; raises UndefinedFunction on databases
        that predate migration 011 (main.py falls back to the Python path).
        """
        with self._connect() as conn:
            row = conn.execute(
                "SELECT public.clara_run_due_measurements("
                "%s::int, COALESCE(%s::timestamptz, now())) AS result",
                (int(current_tenant()), now),
            ).fetchone()
        result = row["result"]
        return result if isinstance(result, dict) else json.loads(result)


class PostgresLearningStore(PostgresConnectionMixin):
    """Postgres learning memory (parity with SQLiteLearningStore).

    Before this store existed, default_learning_store returned SQLite even on a
    Postgres deployment, so production conclusions were written to an ephemeral
    file inside the container and synthesis never saw a single learning.
    """

    def load(self, workspace_id: int = 1) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT payload FROM clara_learnings WHERE workspace_id = %s ORDER BY updated_at",
                (workspace_id,),
            ).fetchall()
        return [_payload(row["payload"]) for row in rows]

    def persist(self, learning: dict[str, Any], *, workspace_id: int = 1) -> dict[str, Any]:
        cid = learning.get("conclusion_id") or uuid4().hex
        stored = {**learning, "conclusion_id": cid}
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO clara_learnings (workspace_id, conclusion_id, topic, payload)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (workspace_id, conclusion_id) DO UPDATE
                SET topic = excluded.topic, payload = excluded.payload, updated_at = now()
                """,
                (workspace_id, cid, stored.get("topic", ""), self._jsonb(stored)),
            )
        return stored

    def clear(self, workspace_id: int = 1) -> None:
        with self._connect() as conn:
            conn.execute("DELETE FROM clara_learnings WHERE workspace_id = %s", (workspace_id,))


class PostgresConnectorConfigStore(PostgresConnectionMixin):
    """Postgres-backed connector configs — survive redeploys, unlike SQLite on
    a PaaS ephemeral disk (losing them silently killed continuous sync)."""

    def _to_config(self, row: Any):
        from app.connectors.config_store import ConnectorConfig, unseal_config

        payload = _payload(row["payload"])
        # config is sealed (enc:v1: string) by upsert; legacy rows hold the dict.
        payload["config"] = unseal_config(payload.get("config", {}))
        return ConnectorConfig.model_validate(payload)

    def list_configs(self) -> list[Any]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT payload FROM clara_connector_configs ORDER BY connector_type"
            ).fetchall()
        return [self._to_config(row) for row in rows]

    def get_config(self, connector_type: str):
        with self._connect() as conn:
            row = conn.execute(
                "SELECT payload FROM clara_connector_configs WHERE connector_type = %s",
                (connector_type,),
            ).fetchone()
        return self._to_config(row) if row else None

    def upsert_config(self, config: Any):
        from app.connectors.config_store import seal_config

        payload = config.model_dump()
        payload["config"] = seal_config(config.config)
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO clara_connector_configs (connector_type, payload)"
                " VALUES (%s, %s)"
                " ON CONFLICT (workspace_id, connector_type) DO UPDATE"
                " SET payload = excluded.payload, updated_at = now()",
                (config.connector_type, self._jsonb(payload)),
            )
        return config

    def delete_config(self, connector_type: str) -> bool:
        with self._connect() as conn:
            row = conn.execute(
                "DELETE FROM clara_connector_configs WHERE connector_type = %s"
                " RETURNING connector_type",
                (connector_type,),
            ).fetchone()
        return row is not None


class PostgresApiKeyStore(PostgresConnectionMixin):
    """Postgres-backed API keys (parity with SQLiteApiKeyStore)."""

    def create_key(self, *, name: str, role: str):
        from app.services.api_keys import VALID_ROLES, _hash, generate_plaintext

        if role not in VALID_ROLES:
            raise ValueError(f"role must be one of {VALID_ROLES}")
        plaintext = generate_plaintext()
        clean_name = name.strip() or "unnamed"
        with self._connect() as conn:
            row = conn.execute(
                "INSERT INTO clara_api_keys (name, role, key_hash, key_prefix)"
                " VALUES (%s, %s, %s, %s) RETURNING id, created_at",
                (clean_name, role, _hash(plaintext), plaintext[:14]),
            ).fetchone()
        record = {
            "id": row["id"],
            "name": clean_name,
            "role": role,
            "key_prefix": plaintext[:14],
            "created_at": str(row["created_at"]),
            "revoked_at": None,
        }
        return record, plaintext

    def list_keys(self) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT id, name, role, key_prefix, created_at, revoked_at"
                " FROM clara_api_keys ORDER BY id DESC"
            ).fetchall()
        return [
            {**dict(row), "created_at": str(row["created_at"]),
             "revoked_at": str(row["revoked_at"]) if row["revoked_at"] else None}
            for row in rows
        ]

    def revoke(self, key_id: int) -> bool:
        with self._connect() as conn:
            row = conn.execute(
                "UPDATE clara_api_keys SET revoked_at = now()"
                " WHERE id = %s AND revoked_at IS NULL RETURNING id",
                (key_id,),
            ).fetchone()
        return row is not None

    def verify(self, plaintext: str):
        from app.services.api_keys import KEY_PREFIX, _hash

        if not plaintext.startswith(KEY_PREFIX):
            return None
        with self._connect() as conn:  # one pooled checkout == one transaction
            # An X-Api-Key request carries no tenant yet — the key row itself
            # names the workspace. The isolation policy (migration 015) admits
            # a SELECT by exact hash only while this transaction-local flag is
            # on; writes keep the strict WITH CHECK, and the flag dies with the
            # transaction. Without it every key outside workspace 1 was a 401.
            conn.execute("SELECT set_config('app.api_key_lookup', 'on', true)")
            row = conn.execute(
                "SELECT id, name, role, workspace_id FROM clara_api_keys"
                " WHERE key_hash = %s AND revoked_at IS NULL",
                (_hash(plaintext),),
            ).fetchone()
        return dict(row) if row else None
