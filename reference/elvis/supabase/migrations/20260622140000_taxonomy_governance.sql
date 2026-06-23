-- Adaptive taxonomy — Phase 3 (graduated authority). Auto-promote / auto-merge / decay,
-- audited to events, reversible. Never auto-archives or auto-merges uploaded taxonomy.

ALTER TABLE public.taxonomy_nodes
  ADD COLUMN IF NOT EXISTS auto_promoted boolean NOT NULL DEFAULT false;

CREATE OR REPLACE FUNCTION public.apply_taxonomy_governance(
  p_workspace_id integer,
  p_auto_promote numeric DEFAULT 0.80,
  p_min_size integer DEFAULT 5,
  p_merge_eps numeric DEFAULT 0.95,
  p_stale_days integer DEFAULT 90
)
RETURNS jsonb
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
  promoted int := 0; archived int := 0; merged int := 0;
  rec record; target uuid;
BEGIN
  IF auth.uid() IS NOT NULL AND NOT EXISTS (
    SELECT 1 FROM public.profiles WHERE user_id = auth.uid() AND workspace_id = p_workspace_id
  ) THEN
    RAISE EXCEPTION 'not authorized for workspace %', p_workspace_id;
  END IF;

  WITH promo AS (
    UPDATE public.taxonomy_nodes
      SET status = 'active', auto_promoted = true, last_validated_at = now(), updated_at = now()
    WHERE workspace_id = p_workspace_id AND status = 'candidate'
      AND confidence >= p_auto_promote
      AND COALESCE((evidence->>'size')::int, 0) >= p_min_size
    RETURNING id
  ) SELECT count(*) INTO promoted FROM promo;
  IF promoted > 0 THEN
    INSERT INTO public.events (workspace_id, event_type, entity, metadata)
    VALUES (p_workspace_id, 'taxonomy_node_auto_promoted', 'taxonomy_node', jsonb_build_object('count', promoted));
  END IF;

  FOR rec IN
    SELECT id, embedding, confidence FROM public.taxonomy_nodes
    WHERE workspace_id = p_workspace_id AND status = 'active' AND origin = 'discovered' AND embedding IS NOT NULL
  LOOP
    SELECT id INTO target FROM public.taxonomy_nodes
    WHERE workspace_id = p_workspace_id AND status = 'active' AND id <> rec.id AND embedding IS NOT NULL
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
  IF merged > 0 THEN
    INSERT INTO public.events (workspace_id, event_type, entity, metadata)
    VALUES (p_workspace_id, 'taxonomy_node_auto_merged', 'taxonomy_node', jsonb_build_object('count', merged));
  END IF;

  WITH arch AS (
    UPDATE public.taxonomy_nodes
      SET status = 'archived', updated_at = now()
    WHERE workspace_id = p_workspace_id AND status = 'active' AND origin = 'discovered'
      AND COALESCE(last_matched_at, created_at) < now() - make_interval(days => p_stale_days)
    RETURNING id
  ) SELECT count(*) INTO archived FROM arch;
  IF archived > 0 THEN
    INSERT INTO public.events (workspace_id, event_type, entity, metadata)
    VALUES (p_workspace_id, 'taxonomy_node_decayed', 'taxonomy_node', jsonb_build_object('count', archived));
  END IF;

  RETURN jsonb_build_object('promoted', promoted, 'merged', merged, 'archived', archived);
END;
$$;

CREATE EXTENSION IF NOT EXISTS pg_cron;
DO $$
BEGIN
  PERFORM cron.unschedule('taxonomy-governance-daily');
EXCEPTION WHEN OTHERS THEN NULL;
END $$;
SELECT cron.schedule('taxonomy-governance-daily', '0 3 * * *',
  $$ SELECT public.apply_taxonomy_governance(id) FROM public.workspaces $$);
