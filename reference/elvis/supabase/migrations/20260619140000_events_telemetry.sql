-- Phase F1 — Evaluation instrumentation.
-- Lightweight activity log for the timed evaluation tasks (time-to-action, task completion).
-- Consumed by evaluation/prototype_metrics.py.

CREATE TABLE IF NOT EXISTS public.events (
  id BIGSERIAL PRIMARY KEY,
  workspace_id INTEGER NOT NULL REFERENCES public.workspaces(id),
  event_type TEXT NOT NULL,         -- e.g. rule_created, action_approved, insight_status_advanced, outcome_measured, learnings_shown
  entity TEXT,                      -- e.g. insight | rule | action
  entity_id TEXT,
  user_id UUID,
  duration_ms INTEGER,              -- e.g. time from insight.detected_at to action
  metadata JSONB DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

ALTER TABLE public.events ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view events in their workspace" ON public.events
  FOR SELECT TO authenticated
  USING (workspace_id IN (SELECT workspace_id FROM public.profiles WHERE user_id = auth.uid()));

CREATE POLICY "Users can insert events in their workspace" ON public.events
  FOR INSERT TO authenticated
  WITH CHECK (workspace_id IN (SELECT workspace_id FROM public.profiles WHERE user_id = auth.uid()));

CREATE INDEX IF NOT EXISTS idx_events_workspace_type ON public.events (workspace_id, event_type, created_at);
