-- Phase A2 — Rule conflict resolution.
-- `priority` determines which rule wins when several rules match the same insight.
-- Higher value wins; ties are broken by condition specificity in the evaluate-rules function.

ALTER TABLE public.feedback_rules
  ADD COLUMN IF NOT EXISTS priority INTEGER NOT NULL DEFAULT 0;

COMMENT ON COLUMN public.feedback_rules.priority IS
  'Higher value wins when multiple rules match the same insight. Ties broken by condition specificity (number of conditions).';

CREATE INDEX IF NOT EXISTS idx_feedback_rules_priority
  ON public.feedback_rules (workspace_id, priority DESC);
