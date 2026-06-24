-- 005 — Outcome contract + events telemetry + learning decay
-- Port of Elvis migrations:
--   reference/elvis/supabase/migrations/20260619130000_outcome_contract.sql
--   reference/elvis/supabase/migrations/20260619140000_events_telemetry.sql
--   reference/elvis/supabase/migrations/20260619160000_learning_decay.sql
--   reference/elvis/supabase/migrations/20260619120000_add_rule_priority.sql
--
-- Merges Elvis's outcome-contract loop closure with CLARA_2's
-- direction-aware outcome_status (apps/api/app/services/workflow.py:63-87).
--
-- Phase 3 target: closes the loop with measured outcomes + confidence-decay
-- learnings.

-- ====== Events table (telemetry for thesis evaluation) ======
CREATE TABLE IF NOT EXISTS public.events (
  id BIGSERIAL PRIMARY KEY,
  workspace_id INTEGER NOT NULL REFERENCES public.workspaces(id) ON DELETE CASCADE,
  event_type VARCHAR(100) NOT NULL,
  entity VARCHAR(50) NOT NULL,
  entity_id VARCHAR(200),
  user_id VARCHAR(200),
  duration_ms INTEGER,
  metadata JSONB DEFAULT '{}',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

ALTER TABLE public.events ENABLE ROW LEVEL SECURITY;

CREATE INDEX IF NOT EXISTS idx_events_workspace_type
  ON public.events (workspace_id, event_type, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_events_entity
  ON public.events (workspace_id, entity, entity_id);

CREATE POLICY events_workspace_isolation
  ON public.events FOR ALL
  USING (public.is_current_workspace(workspace_id))
  WITH CHECK (public.is_current_workspace(workspace_id));

-- ====== Outcome contract columns on clara_problems ======
-- Elvis adds these to insights; CLARA_2 stores them in the JSONB payload.
-- We add them as real columns on clara_problems for queryability + indexing.
ALTER TABLE clara_problems ADD COLUMN IF NOT EXISTS outcome_metric TEXT;
ALTER TABLE clara_problems ADD COLUMN IF NOT EXISTS outcome_baseline DOUBLE PRECISION;
ALTER TABLE clara_problems ADD COLUMN IF NOT EXISTS outcome_target DOUBLE PRECISION;
ALTER TABLE clara_problems ADD COLUMN IF NOT EXISTS outcome_measured DOUBLE PRECISION;
ALTER TABLE clara_problems ADD COLUMN IF NOT EXISTS resolution_score DOUBLE PRECISION;
ALTER TABLE clara_problems ADD COLUMN IF NOT EXISTS measurement_window_days INTEGER DEFAULT 14;
ALTER TABLE clara_problems ADD COLUMN IF NOT EXISTS measured_at TIMESTAMPTZ;
ALTER TABLE clara_problems ADD COLUMN IF NOT EXISTS measurement_due_at TIMESTAMPTZ;
ALTER TABLE clara_problems ADD COLUMN IF NOT EXISTS resolution_summary TEXT;
ALTER TABLE clara_problems ADD COLUMN IF NOT EXISTS closure_level TEXT;
-- closure_level: 'operational' | 'customer' | 'outcome' (Elvis's closure chips)

CREATE INDEX IF NOT EXISTS idx_problems_outcome_due
  ON clara_problems (workspace_id, measurement_due_at)
  WHERE outcome_measured IS NULL AND measurement_due_at IS NOT NULL;

-- ====== Learning conclusions table (with confidence decay) ======
-- Merges CLARA_2's structured LearningConclusion verdicts with Elvis's
-- confidence-decay model (half_life_days + last_validated_at).
CREATE TABLE IF NOT EXISTS public.learning_conclusions (
  conclusion_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  workspace_id INTEGER NOT NULL REFERENCES public.workspaces(id) ON DELETE CASCADE,
  problem_id TEXT NOT NULL,
  learning_status TEXT NOT NULL CHECK (
    learning_status IN ('worked', 'partially_worked', 'did_not_work', 'inconclusive', 'measurement_invalid')
  ),
  summary TEXT NOT NULL,
  limitations TEXT NOT NULL,
  next_step TEXT,
  reviewer TEXT NOT NULL,
  reviewed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  last_validated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  -- Confidence decay (Elvis design decision #2):
  -- stored confidence erodes exponentially from last_validated_at
  base_confidence NUMERIC NOT NULL DEFAULT 0.5,
  half_life_days INTEGER NOT NULL DEFAULT 180,
  retention_expires_at TIMESTAMPTZ,
  -- Evidence block (Elvis AbLearning pattern):
  evidence JSONB DEFAULT '{}'::jsonb,
  topic TEXT,
  pattern TEXT,
  winning_examples JSONB DEFAULT '[]'::jsonb,
  losing_examples JSONB DEFAULT '[]'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

ALTER TABLE public.learning_conclusions ENABLE ROW LEVEL SECURITY;

CREATE INDEX IF NOT EXISTS idx_learning_workspace
  ON public.learning_conclusions (workspace_id, topic);
CREATE INDEX IF NOT EXISTS idx_learning_status
  ON public.learning_conclusions (workspace_id, learning_status);
CREATE INDEX IF NOT EXISTS idx_learning_problem
  ON public.learning_conclusions (workspace_id, problem_id);

CREATE POLICY learning_conclusions_workspace_isolation
  ON public.learning_conclusions FOR ALL
  USING (public.is_current_workspace(workspace_id))
  WITH CHECK (public.is_current_workspace(workspace_id));

CREATE TRIGGER set_learning_conclusions_updated_at
  BEFORE UPDATE ON public.learning_conclusions
  FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();

-- ====== Feedback rules priority (Elvis conflict resolution) ======
-- Priority for rule conflict resolution: priority -> specificity -> action-type dedupe
-- Stored in a separate table for the triage graph's governance node.
CREATE TABLE IF NOT EXISTS public.feedback_rules (
  id BIGSERIAL PRIMARY KEY,
  workspace_id INTEGER NOT NULL REFERENCES public.workspaces(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  conditions JSONB NOT NULL DEFAULT '[]'::jsonb,
  actions JSONB NOT NULL DEFAULT '[]'::jsonb,
  priority INTEGER NOT NULL DEFAULT 0,
  auto_execute BOOLEAN NOT NULL DEFAULT false,
  measure_after_days INTEGER NOT NULL DEFAULT 14,
  is_active BOOLEAN NOT NULL DEFAULT true,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

ALTER TABLE public.feedback_rules ENABLE ROW LEVEL SECURITY;

CREATE INDEX IF NOT EXISTS idx_rules_workspace_active
  ON public.feedback_rules (workspace_id, is_active, priority DESC);

CREATE POLICY feedback_rules_workspace_isolation
  ON public.feedback_rules FOR ALL
  USING (public.is_current_workspace(workspace_id))
  WITH CHECK (public.is_current_workspace(workspace_id));

CREATE TRIGGER set_feedback_rules_updated_at
  BEFORE UPDATE ON public.feedback_rules
  FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();

-- ====== Action log table (audit trail for executed actions) ======
CREATE TABLE IF NOT EXISTS public.action_logs (
  id BIGSERIAL PRIMARY KEY,
  workspace_id INTEGER NOT NULL REFERENCES public.workspaces(id) ON DELETE CASCADE,
  insight_title TEXT NOT NULL,
  action_type TEXT NOT NULL,
  action_title TEXT NOT NULL,
  external_id TEXT,
  status TEXT NOT NULL DEFAULT 'pending',
  -- 'pushed' | 'failed' | 'no_config' | 'no_connector' | 'pending_approval'
  connector_type TEXT,
  audit JSONB DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

ALTER TABLE public.action_logs ENABLE ROW LEVEL SECURITY;

CREATE INDEX IF NOT EXISTS idx_action_logs_workspace
  ON public.action_logs (workspace_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_action_logs_status
  ON public.action_logs (workspace_id, status);

CREATE POLICY action_logs_workspace_isolation
  ON public.action_logs FOR ALL
  USING (public.is_current_workspace(workspace_id))
  WITH CHECK (public.is_current_workspace(workspace_id));
