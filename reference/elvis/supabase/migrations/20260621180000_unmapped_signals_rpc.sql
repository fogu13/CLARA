-- Adaptive taxonomy — backfill support. Returns qualitative signals that have text but
-- are not yet mapped to any taxonomy node, so a batch job can embed + map them without
-- re-running LLM enrichment.

CREATE OR REPLACE FUNCTION public.unmapped_signals(
  p_workspace_id integer,
  p_limit integer DEFAULT 100
)
RETURNS TABLE (id integer, text_content text)
LANGUAGE sql STABLE
SET search_path = public
AS $$
  SELECT s.id, s.text_content
  FROM public.signals s
  WHERE s.workspace_id = p_workspace_id
    AND s.text_content IS NOT NULL
    AND NOT EXISTS (SELECT 1 FROM public.signal_node_map m WHERE m.signal_id = s.id)
  ORDER BY s.id
  LIMIT p_limit;
$$;
