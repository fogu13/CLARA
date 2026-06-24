-- 003 — pgvector + semantic taxonomy
-- Port of Elvis migrations:
--   reference/elvis/supabase/migrations/20260621170000_taxonomy.sql
--   reference/elvis/supabase/migrations/20260622120000_taxonomy_discovery.sql
--   reference/elvis/supabase/migrations/20260622140000_taxonomy_governance.sql
--
-- Adapted to CLARA_2's schema: taxonomy_nodes uses workspace_id from migration 004,
-- signal_node_map references clara_signals.signal_id (TEXT) instead of Elvis's
-- integer signals.id.
--
-- Replaces CLARA_2's substring/term-matching classification
-- (apps/api/app/services/taxonomies.py:364-425) with embedding-based semantic
-- mapping + adaptive discovery + graduated-authority governance.

-- ====== pgvector extension ======
CREATE EXTENSION IF NOT EXISTS vector;

-- ====== Taxonomy nodes — 3-level company taxonomy with embeddings ======
CREATE TABLE IF NOT EXISTS public.taxonomy_nodes (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  workspace_id INTEGER NOT NULL REFERENCES public.workspaces(id) ON DELETE CASCADE,
  parent_id UUID REFERENCES public.taxonomy_nodes(id) ON DELETE CASCADE,
  level INTEGER NOT NULL CHECK (level BETWEEN 1 AND 3),
  name TEXT NOT NULL,
  slug TEXT NOT NULL,
  description TEXT,
  status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active','candidate','merged','archived')),
  origin TEXT NOT NULL DEFAULT 'uploaded' CHECK (origin IN ('uploaded','seeded','discovered')),
  confidence NUMERIC NOT NULL DEFAULT 1.0,
  times_matched INTEGER NOT NULL DEFAULT 0,
  last_matched_at TIMESTAMPTZ,
  last_validated_at TIMESTAMPTZ DEFAULT now(),
  merged_into_id UUID REFERENCES public.taxonomy_nodes(id),
  auto_promoted BOOLEAN NOT NULL DEFAULT false,
  evidence JSONB NOT NULL DEFAULT '{}'::jsonb,
  embedding vector(768),
  created_by TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (workspace_id, parent_id, slug)
);

ALTER TABLE public.taxonomy_nodes ENABLE ROW LEVEL SECURITY;

CREATE INDEX IF NOT EXISTS idx_taxonomy_nodes_ws_status
  ON public.taxonomy_nodes (workspace_id, status);
CREATE INDEX IF NOT EXISTS idx_taxonomy_nodes_parent
  ON public.taxonomy_nodes (workspace_id, parent_id);
CREATE INDEX IF NOT EXISTS idx_taxonomy_nodes_embedding
  ON public.taxonomy_nodes USING hnsw (embedding vector_cosine_ops);

CREATE POLICY taxonomy_nodes_workspace_isolation
  ON public.taxonomy_nodes FOR ALL
  USING (public.is_current_workspace(workspace_id))
  WITH CHECK (public.is_current_workspace(workspace_id));

CREATE TRIGGER set_taxonomy_nodes_updated_at
  BEFORE UPDATE ON public.taxonomy_nodes
  FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();

-- ====== Signal-to-node mapping (multi-label) ======
-- References clara_signals.signal_id (TEXT) instead of Elvis's integer signals.id.
CREATE TABLE IF NOT EXISTS public.signal_node_map (
  id BIGSERIAL PRIMARY KEY,
  signal_id TEXT NOT NULL,
  node_id UUID NOT NULL REFERENCES public.taxonomy_nodes(id) ON DELETE CASCADE,
  workspace_id INTEGER NOT NULL REFERENCES public.workspaces(id) ON DELETE CASCADE,
  score NUMERIC,
  mapped_by TEXT NOT NULL DEFAULT 'system_auto'
    CHECK (mapped_by IN ('system_auto','system_llm','user')),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (signal_id, node_id)
);

ALTER TABLE public.signal_node_map ENABLE ROW LEVEL SECURITY;

CREATE INDEX IF NOT EXISTS idx_signal_node_map_node
  ON public.signal_node_map (node_id);
CREATE INDEX IF NOT EXISTS idx_signal_node_map_workspace
  ON public.signal_node_map (workspace_id);

CREATE POLICY signal_node_map_workspace_isolation
  ON public.signal_node_map FOR ALL
  USING (public.is_current_workspace(workspace_id))
  WITH CHECK (public.is_current_workspace(workspace_id));

-- ====== match_taxonomy_nodes — nearest-neighbour retrieval over ACTIVE nodes ======
CREATE OR REPLACE FUNCTION public.match_taxonomy_nodes(
  p_workspace_id INTEGER,
  p_query_embedding vector(768),
  p_match_count INTEGER DEFAULT 5
)
RETURNS TABLE (id UUID, name TEXT, level INTEGER, slug TEXT, similarity DOUBLE PRECISION)
LANGUAGE sql STABLE
SET search_path = public
AS $$
  SELECT n.id, n.name, n.level, n.slug,
         1 - (n.embedding <=> p_query_embedding) AS similarity
  FROM public.taxonomy_nodes n
  WHERE n.workspace_id = p_workspace_id
    AND n.status = 'active'
    AND n.embedding IS NOT NULL
  ORDER BY n.embedding <=> p_query_embedding
  LIMIT p_match_count;
$$;

-- ====== unmapped_signals — signals without a taxonomy mapping ======
CREATE OR REPLACE FUNCTION public.unmapped_signals(
  p_workspace_id INTEGER,
  p_limit INTEGER DEFAULT 200
)
RETURNS TABLE (signal_id TEXT, text_content TEXT)
LANGUAGE sql STABLE
SET search_path = public
AS $$
  SELECT s.signal_id,
         s.payload->>'feedback_text' AS text_content
  FROM clara_signals s
  WHERE s.workspace_id = p_workspace_id
    AND s.payload->>'feedback_text' IS NOT NULL
    AND s.payload->>'feedback_text' != ''
    AND NOT EXISTS (
      SELECT 1 FROM public.signal_node_map m
      WHERE m.signal_id = s.signal_id AND m.workspace_id = p_workspace_id
    )
  ORDER BY s.created_at DESC
  LIMIT p_limit;
$$;

-- ====== merge_taxonomy_node — merge a node into another, remapping signals ======
CREATE OR REPLACE FUNCTION public.merge_taxonomy_node(p_from UUID, p_into UUID)
RETURNS void
LANGUAGE plpgsql
SET search_path = public
AS $$
BEGIN
  IF p_from = p_into THEN RETURN; END IF;

  UPDATE public.signal_node_map m
    SET node_id = p_into
  WHERE m.node_id = p_from
    AND NOT EXISTS (
      SELECT 1 FROM public.signal_node_map x
      WHERE x.signal_id = m.signal_id AND x.node_id = p_into
    );

  DELETE FROM public.signal_node_map WHERE node_id = p_from;

  UPDATE public.taxonomy_nodes
    SET status = 'merged', merged_into_id = p_into, updated_at = now()
  WHERE id = p_from;
END;
$$;

-- ====== apply_taxonomy_governance — graduated authority: auto-promote/merge/decay ======
-- Port of Elvis's Phase 3 governance. Audited to events (migration 005).
-- Never auto-promotes/merges/archives uploaded taxonomy — only discovered nodes.
CREATE OR REPLACE FUNCTION public.apply_taxonomy_governance(
  p_workspace_id INTEGER,
  p_auto_promote NUMERIC DEFAULT 0.80,
  p_min_size INTEGER DEFAULT 5,
  p_merge_eps NUMERIC DEFAULT 0.95,
  p_stale_days INTEGER DEFAULT 90
)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
  promoted INT := 0;
  archived INT := 0;
  merged INT := 0;
  rec RECORD;
  target UUID;
BEGIN
  -- Auto-promote candidates above confidence + size thresholds
  WITH promo AS (
    UPDATE public.taxonomy_nodes
      SET status = 'active', auto_promoted = true,
          last_validated_at = now(), updated_at = now()
    WHERE workspace_id = p_workspace_id AND status = 'candidate'
      AND confidence >= p_auto_promote
      AND COALESCE((evidence->>'size')::int, 0) >= p_min_size
    RETURNING id
  ) SELECT count(*) INTO promoted FROM promo;

  -- Auto-merge near-duplicate discovered active nodes (cosine >= merge_eps)
  FOR rec IN
    SELECT id, embedding, confidence FROM public.taxonomy_nodes
    WHERE workspace_id = p_workspace_id AND status = 'active'
      AND origin = 'discovered' AND embedding IS NOT NULL
  LOOP
    SELECT id INTO target FROM public.taxonomy_nodes
    WHERE workspace_id = p_workspace_id AND status = 'active'
      AND id <> rec.id AND embedding IS NOT NULL
      AND (1 - (embedding <=> rec.embedding)) >= p_merge_eps
      AND confidence >= rec.confidence
    ORDER BY embedding <=> rec.embedding
    LIMIT 1;
    IF target IS NOT NULL THEN
      PERFORM public.merge_taxonomy_node(rec.id, target);
      merged := merged + 1;
      target := NULL;
    END IF;
  END LOOP;

  -- Decay: archive stale discovered nodes not matched in p_stale_days
  WITH arch AS (
    UPDATE public.taxonomy_nodes
      SET status = 'archived', updated_at = now()
    WHERE workspace_id = p_workspace_id AND status = 'active'
      AND origin = 'discovered'
      AND COALESCE(last_matched_at, created_at) < now() - make_interval(days => p_stale_days)
    RETURNING id
  ) SELECT count(*) INTO archived FROM arch;

  RETURN jsonb_build_object(
    'promoted', promoted,
    'merged', merged,
    'archived', archived
  );
END;
$$;

-- ====== Schedule daily governance via pg_cron (if available) ======
DO $$
BEGIN
  CREATE EXTENSION IF NOT EXISTS pg_cron;
  PERFORM cron.unschedule('taxonomy-governance-daily');
  EXCEPTION WHEN OTHERS THEN NULL;
END $$;

DO $$
BEGIN
  SELECT cron.schedule(
    'taxonomy-governance-daily',
    '0 3 * * *',
    $$ SELECT public.apply_taxonomy_governance(id) FROM public.workspaces $$
  );
  EXCEPTION WHEN OTHERS THEN NULL;
END $$;
