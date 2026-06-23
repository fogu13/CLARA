-- Phase B — Close the loop: the "outcome contract".
-- When an action fires, we capture what to measure (metric), the baseline at action time,
-- and the window. A measurement pass later fills the measured value + resolution score.
-- (resolution_score / resolution_summary already exist on insights.)

ALTER TABLE public.insights
  ADD COLUMN IF NOT EXISTS outcome_metric TEXT,
  ADD COLUMN IF NOT EXISTS outcome_baseline NUMERIC,
  ADD COLUMN IF NOT EXISTS outcome_measured NUMERIC,
  ADD COLUMN IF NOT EXISTS outcome_target NUMERIC,
  ADD COLUMN IF NOT EXISTS measurement_window_days INTEGER,
  ADD COLUMN IF NOT EXISTS measured_at TIMESTAMPTZ;

COMMENT ON COLUMN public.insights.outcome_metric IS
  'What the loop measures for this insight, e.g. "tag:late_delivery" (recurrence of related signals) or "affected_contacts".';
COMMENT ON COLUMN public.insights.outcome_baseline IS
  'Value of outcome_metric captured at action time, used as the comparison baseline.';

-- Helps the measurement pass find insights that are due.
CREATE INDEX IF NOT EXISTS idx_insights_measurement_due
  ON public.insights (workspace_id, status, measurement_due_at)
  WHERE measured_at IS NULL;
