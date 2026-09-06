-- Appendix E. The deployed CLARA data model (Postgres, Supabase-compatible).
--
-- Source of truth: apps/api/migrations/001-015 plus the boot-time DDL the API
-- applies in apps/api/app/services/postgres.py (PostgresConnectionMixin,
-- SCHEMA_SQL). This file is an extract of that schema as deployed on
-- 5 September 2026, not a design sketch: every table below exists in the
-- running system, and the SQLite fallback used in tests and single-tenant
-- deployments mirrors the same shapes. Diagram 06_data_model_er.mmd draws
-- the same tables.
--
-- Two conventions matter for reading it.
--   1. Document rows. Domain aggregates (problems, signals, workflow records,
--      learnings, theme insights, candidate decisions, customer context) are
--      stored as one JSONB payload per row, keyed by a text id. The payload is
--      validated on every read and write by the pydantic domain model named in
--      the comment (apps/api/app/domain/models.py), so the model, not the
--      column list, is the schema of the aggregate.
--   2. Tenant-first keys and row-level security. Every table carries
--      workspace_id (or tenant_id), the primary key leads with it (migrations
--      011 and 014), RLS is enabled and FORCED on every table (migrations 004,
--      007, 009, 011), and the isolation policy compares the row's workspace
--      to the session GUC app.workspace_id set by the API on each connection.
--      The policy pattern is shown once, after the tables.

CREATE EXTENSION IF NOT EXISTS vector;      -- pgvector, taxonomy_nodes.embedding

-- ---------------------------------------------------------------------------
-- Tenancy and identity (migrations 003, 004)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.workspaces (
  id          SERIAL PRIMARY KEY,
  name        VARCHAR(200) NOT NULL,
  slug        VARCHAR(100) UNIQUE NOT NULL,
  settings    JSONB DEFAULT '{}',
  onboarded   BOOLEAN DEFAULT FALSE,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.profiles (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id       UUID NOT NULL UNIQUE,                    -- Supabase auth user
  workspace_id  INTEGER REFERENCES public.workspaces(id),
  email         VARCHAR(255) NOT NULL,
  name          VARCHAR(200),
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.user_roles (             -- role = viewer | editor | admin
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id       UUID NOT NULL,
  workspace_id  INTEGER REFERENCES public.workspaces(id) ON DELETE CASCADE,
  role          app_role NOT NULL,
  UNIQUE (user_id, workspace_id, role)
);

CREATE TABLE IF NOT EXISTS clara_api_keys (                -- machine access, hash-only storage
  id            BIGSERIAL PRIMARY KEY,
  workspace_id  BIGINT NOT NULL DEFAULT COALESCE(NULLIF(current_setting('app.workspace_id', true), ''), '1')::bigint,
  name          TEXT NOT NULL,
  role          TEXT NOT NULL,
  key_hash      TEXT NOT NULL UNIQUE,
  key_prefix    TEXT NOT NULL,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
  revoked_at    TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS clara_workspace_settings (      -- WorkspaceSettings: SLA, owner routes,
  workspace_id  INTEGER PRIMARY KEY,                       -- works-council mode, residency, vocabulary
  payload       JSONB NOT NULL,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ---------------------------------------------------------------------------
-- Signal -> Insight (migration 001, boot DDL, 013)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS clara_signals (                 -- SignalRecord: feedback_text, source,
  workspace_id  BIGINT NOT NULL DEFAULT COALESCE(NULLIF(current_setting('app.workspace_id', true), ''), '1')::bigint,
  signal_id     TEXT NOT NULL,                             --   journey, journey_stage, language,
  payload       JSONB NOT NULL,                            --   timestamp, sentiment, urgency, tags,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),        --   enriched, customer_id, account_id
  updated_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (workspace_id, signal_id)
);

CREATE TABLE IF NOT EXISTS clara_journey_events (          -- JourneyEventRecord (behavioural context)
  workspace_id  BIGINT NOT NULL DEFAULT COALESCE(NULLIF(current_setting('app.workspace_id', true), ''), '1')::bigint,
  event_id      TEXT NOT NULL,
  payload       JSONB NOT NULL,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (workspace_id, event_id)
);

CREATE TABLE IF NOT EXISTS clara_customer_context (        -- CustomerContextRecord (pseudonymous ids,
  workspace_id  BIGINT NOT NULL DEFAULT COALESCE(NULLIF(current_setting('app.workspace_id', true), ''), '1')::bigint,
  customer_id   TEXT NOT NULL,                             --   account value, consent status)
  account_id    TEXT,
  payload       JSONB NOT NULL,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (workspace_id, customer_id)
);

CREATE TABLE IF NOT EXISTS clara_theme_insights (          -- AI triage theme per (workspace, tag):
  workspace_id  BIGINT NOT NULL DEFAULT COALESCE(NULLIF(current_setting('app.workspace_id', true), ''), '1')::bigint,
  theme_tag     TEXT NOT NULL,                             --   synthesised insight, cross-signal
  payload       JSONB NOT NULL,                            --   severity, evidence, suggested actions;
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),        --   surfaces as a problem candidate
  updated_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (workspace_id, theme_tag)
);

CREATE TABLE IF NOT EXISTS clara_candidate_decisions (     -- CandidateDecisionRecord: the human
  workspace_id  BIGINT NOT NULL DEFAULT COALESCE(NULLIF(current_setting('app.workspace_id', true), ''), '1')::bigint,
  candidate_id  TEXT NOT NULL,                             --   accept / reject of a candidate
  payload       JSONB NOT NULL,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (workspace_id, candidate_id)
);

-- Adaptive taxonomy (migration 003; embedding widened to 1024 dims by 012).
CREATE TABLE IF NOT EXISTS public.taxonomy_nodes (
  id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  workspace_id      INTEGER NOT NULL REFERENCES public.workspaces(id) ON DELETE CASCADE,
  parent_id         UUID REFERENCES public.taxonomy_nodes(id) ON DELETE CASCADE,
  level             INTEGER NOT NULL CHECK (level BETWEEN 1 AND 3),
  name              TEXT NOT NULL,
  slug              TEXT NOT NULL,
  description       TEXT,
  status            TEXT NOT NULL DEFAULT 'active'   CHECK (status IN ('active','candidate','merged','archived')),
  origin            TEXT NOT NULL DEFAULT 'uploaded' CHECK (origin IN ('uploaded','seeded','discovered')),
  confidence        NUMERIC NOT NULL DEFAULT 1.0,
  times_matched     INTEGER NOT NULL DEFAULT 0,
  last_matched_at   TIMESTAMPTZ,
  last_validated_at TIMESTAMPTZ DEFAULT now(),
  merged_into_id    UUID REFERENCES public.taxonomy_nodes(id),
  auto_promoted     BOOLEAN NOT NULL DEFAULT false,
  evidence          JSONB NOT NULL DEFAULT '{}'::jsonb,
  embedding         vector(1024),
  created_by        TEXT,
  created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (workspace_id, parent_id, slug)
);

CREATE TABLE IF NOT EXISTS public.signal_node_map (
  id            BIGSERIAL PRIMARY KEY,
  signal_id     TEXT NOT NULL,
  node_id       UUID NOT NULL REFERENCES public.taxonomy_nodes(id) ON DELETE CASCADE,
  workspace_id  INTEGER NOT NULL REFERENCES public.workspaces(id) ON DELETE CASCADE,
  score         NUMERIC,
  mapped_by     TEXT NOT NULL DEFAULT 'system_auto' CHECK (mapped_by IN ('system_auto','system_llm','user')),
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (signal_id, node_id)
);

CREATE TABLE IF NOT EXISTS clara_taxonomy_catalogs (       -- TaxonomyCatalog per taxonomy_type
  workspace_id   BIGINT NOT NULL DEFAULT COALESCE(NULLIF(current_setting('app.workspace_id', true), ''), '1')::bigint,
  taxonomy_type  TEXT NOT NULL,
  payload        JSONB NOT NULL,
  created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (workspace_id, taxonomy_type)
);

CREATE TABLE IF NOT EXISTS clara_terminology_dictionary (  -- TerminologyDictionaryEntry
  workspace_id  BIGINT NOT NULL DEFAULT COALESCE(NULLIF(current_setting('app.workspace_id', true), ''), '1')::bigint,
  term_id       TEXT NOT NULL,
  payload       JSONB NOT NULL,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (workspace_id, term_id)
);

-- ---------------------------------------------------------------------------
-- Problem -> Action -> Outcome -> Learning (migrations 001, 002, 008, 011, 013)
-- ---------------------------------------------------------------------------
-- ProblemRecord carries the outcome contract (DP1) inside its payload:
--   outcome_contract {primary_metric, baseline, success_threshold,
--                     measurement_window_days, comparison_method,
--                     guardrail_metrics, responsible_owner}
-- together with action_proposals[] (each with risk_level, approval state and
-- an intervention brief), governance_checks[] (policy checks; a blocking
-- check withholds approval), evidence[], affected_cohort, impact factors,
-- origin (journey_stage | ai_theme) and due_at.
CREATE TABLE IF NOT EXISTS clara_problems (
  workspace_id  BIGINT NOT NULL DEFAULT COALESCE(NULLIF(current_setting('app.workspace_id', true), ''), '1')::bigint,
  problem_id    TEXT NOT NULL,
  payload       JSONB NOT NULL,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (workspace_id, problem_id)
  -- Migration 005 also added outcome_metric, outcome_baseline, outcome_target,
  -- outcome_measured, resolution_score, measurement_window_days, measured_at,
  -- measurement_due_at, resolution_summary and closure_level columns. The API
  -- does not read them; the contract of record is the payload above.
);

-- One table, eight record types, discriminated by record_type and validated
-- by the matching domain model:
--   approval             ApprovalDecision      (reviewer, decision, rationale)
--   execution            ExecutionRecord       (status, connector result, audit)
--   jira_draft           JiraIssueDraft
--   transition           ProblemTransitionRecord
--   outcome              OutcomeMeasurement    (observed_value, measured_at,
--                                               measurement_source instrumented|manual)
--   guardrail            GuardrailMeasurement  (non-inferiority readout per metric)
--   closure              ClosureRecord         (operational / customer status)
--   learning_conclusion  LearningConclusionRecord (learning_status worked |
--                        partially_worked | did_not_work | inconclusive |
--                        measurement_invalid; summary; limitations; reviewer)
-- Audit attribution lives here: every approval and execution names its
-- reviewer or executor and carries an audit block, and the evidence pack
-- hashed at decision time is reconstructed from these rows.
CREATE TABLE IF NOT EXISTS clara_workflow_records (
  record_type           TEXT NOT NULL,
  record_id             TEXT NOT NULL,
  problem_id            TEXT NOT NULL,
  tenant_id             TEXT NOT NULL DEFAULT 'legacy',
  payload               JSONB NOT NULL,
  retention_expires_at  TIMESTAMPTZ,                       -- GDPR storage limitation (migration 002)
  created_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (tenant_id, record_type, record_id)
);
CREATE INDEX IF NOT EXISTS clara_workflow_problem_idx
  ON clara_workflow_records (problem_id, record_type);

-- Measurement checkpoints scheduled at execution: t7, window, followup.
-- The scheduler recomputes the contract metric from raw signals at each due
-- date (measurement_source = instrumented) and records the loop verdict.
CREATE TABLE IF NOT EXISTS clara_measurement_plans (
  id            BIGSERIAL PRIMARY KEY,
  workspace_id  BIGINT NOT NULL DEFAULT COALESCE(NULLIF(current_setting('app.workspace_id', true), ''), '1')::bigint,
  problem_id    TEXT NOT NULL,
  execution_id  TEXT NOT NULL,
  executed_at   TEXT NOT NULL,
  due_at        TEXT NOT NULL,
  kind          TEXT NOT NULL,                             -- t7 | window | followup
  status        TEXT NOT NULL DEFAULT 'pending',           -- pending | done | skipped
  note          TEXT,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Learning memory (DP2). A reviewed learning_conclusion is copied here as a
-- retrieval document: {conclusion_id, topic, tag, title, category, severity,
-- metric, status, resolution_score, learning_status, summary, limitations,
-- next_step, reviewer, last_validated_at, half_life_days, base_confidence}.
-- Decayed confidence is computed on read (learning_engine.with_decay):
--   confidence_now = base_confidence * 0.5 ^ (age_days / half_life_days)
-- and only human-reviewed rows (reviewer != 'system') are retrieval-eligible.
-- Retrieval into synthesis is lexical ranking over topic/tag, not vector
-- search: no embedding column exists on this table.
CREATE TABLE IF NOT EXISTS clara_learnings (
  workspace_id   BIGINT NOT NULL DEFAULT COALESCE(NULLIF(current_setting('app.workspace_id', true), ''), '1')::bigint,
  conclusion_id  TEXT NOT NULL,
  topic          TEXT,
  payload        JSONB NOT NULL,
  created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (workspace_id, conclusion_id)
);

-- ---------------------------------------------------------------------------
-- Operations (migrations 008, 010)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS clara_telemetry (               -- time-to-action, approvals, loop
  id            BIGSERIAL PRIMARY KEY,                     --   verdicts, retrieval events
  workspace_id  BIGINT NOT NULL DEFAULT COALESCE(NULLIF(current_setting('app.workspace_id', true), ''), '1')::bigint,
  event_type    TEXT NOT NULL,
  entity_id     TEXT,
  metadata      JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS clara_telemetry_type_idx ON clara_telemetry (event_type, created_at);

CREATE TABLE IF NOT EXISTS clara_connector_configs (       -- per-connector credentials/config
  workspace_id    BIGINT NOT NULL DEFAULT COALESCE(NULLIF(current_setting('app.workspace_id', true), ''), '1')::bigint,
  connector_type  TEXT NOT NULL,                           --   (zendesk, jira, slack, ...)
  payload         JSONB NOT NULL,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (workspace_id, connector_type)
);

-- Feedback rules are stored as documents too (FeedbackRule payload: name,
-- conditions, action, priority, enabled). They are configuration the triage
-- graph exposes; there is no auto_execute flag anywhere in the deployed
-- model, and no path executes an action without a recorded human approval.
CREATE TABLE IF NOT EXISTS clara_feedback_rules (
  workspace_id  BIGINT NOT NULL DEFAULT 1,
  rule_id       TEXT PRIMARY KEY,
  payload       JSONB NOT NULL,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Migration 005 additionally creates public.events, public.learning_conclusions,
-- public.feedback_rules and public.action_logs, ported from the first
-- design-cycle build. The deployed API does not read or write them; they are
-- retained for compatibility and are not part of the data model described in
-- Chapter 4.

-- ---------------------------------------------------------------------------
-- Row-level security, the pattern applied to every table above
-- (migrations 004, 007, 009, 011, 013; self-healed by the API on boot)
-- ---------------------------------------------------------------------------
-- ALTER TABLE clara_problems ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE clara_problems FORCE ROW LEVEL SECURITY;
-- CREATE POLICY clara_problems_workspace_isolation ON clara_problems
--   USING      (workspace_id = COALESCE(NULLIF(current_setting('app.workspace_id', true), ''), '1')::bigint)
--   WITH CHECK (workspace_id = COALESCE(NULLIF(current_setting('app.workspace_id', true), ''), '1')::bigint);
-- The API sets app.workspace_id (and app.tenant_id for clara_workflow_records)
-- on every connection from the authenticated user's workspace, so a query can
-- only ever see its own tenant's rows, whichever store issued it.
