-- Adaptive taxonomy — Phase 2 (discovery + review). Candidate nodes carry evidence; merging
-- a node remaps its signal mappings onto the target and marks it merged.

ALTER TABLE public.taxonomy_nodes
  ADD COLUMN IF NOT EXISTS evidence jsonb NOT NULL DEFAULT '{}'::jsonb;

COMMENT ON COLUMN public.taxonomy_nodes.evidence IS
  'For discovered candidates: { signal_ids:int[], samples:text[], size:int, cohesion:numeric }.';

-- Merge p_from into p_into: move mappings (dedupe against existing), then mark merged.
CREATE OR REPLACE FUNCTION public.merge_taxonomy_node(p_from uuid, p_into uuid)
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

  DELETE FROM public.signal_node_map WHERE node_id = p_from; -- leftover duplicates

  UPDATE public.taxonomy_nodes
    SET status = 'merged', merged_into_id = p_into, updated_at = now()
  WHERE id = p_from;
END;
$$;
