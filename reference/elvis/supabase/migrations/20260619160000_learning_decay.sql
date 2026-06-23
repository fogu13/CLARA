-- Phase D1 — confidence decay for learnings (design decision #2).
-- A learning's confidence should erode as it ages, unless re-validated. We store the
-- last validation time and a half-life; the decayed value is computed on read.

ALTER TABLE public.ab_learnings
  ADD COLUMN IF NOT EXISTS last_validated_at TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS half_life_days INTEGER NOT NULL DEFAULT 180;

-- Backfill existing rows so decay has a reference point.
UPDATE public.ab_learnings
  SET last_validated_at = COALESCE(updated_at, created_at)
  WHERE last_validated_at IS NULL;

COMMENT ON COLUMN public.ab_learnings.last_validated_at IS
  'When this learning was last confirmed. Decay is measured from here.';
COMMENT ON COLUMN public.ab_learnings.half_life_days IS
  'Days for confidence to halve via exponential decay (default 180).';
