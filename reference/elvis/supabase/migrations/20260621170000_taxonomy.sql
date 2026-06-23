-- Adaptive taxonomy — Phase 1. 3-level company taxonomy + governed signal mapping + pgvector.

CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS public.taxonomy_nodes (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  workspace_id integer NOT NULL REFERENCES public.workspaces(id) ON DELETE CASCADE,
  parent_id uuid REFERENCES public.taxonomy_nodes(id) ON DELETE CASCADE,
  level integer NOT NULL CHECK (level BETWEEN 1 AND 3),
  name text NOT NULL,
  slug text NOT NULL,
  description text,
  status text NOT NULL DEFAULT 'active' CHECK (status IN ('active','candidate','merged','archived')),
  origin text NOT NULL DEFAULT 'uploaded' CHECK (origin IN ('uploaded','seeded','discovered')),
  confidence numeric NOT NULL DEFAULT 1.0,
  times_matched integer NOT NULL DEFAULT 0,
  last_matched_at timestamptz,
  last_validated_at timestamptz DEFAULT now(),
  merged_into_id uuid REFERENCES public.taxonomy_nodes(id),
  embedding vector(768),
  created_by text,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (workspace_id, parent_id, slug)
);
ALTER TABLE public.taxonomy_nodes ENABLE ROW LEVEL SECURITY;

CREATE INDEX IF NOT EXISTS idx_taxonomy_nodes_ws_status ON public.taxonomy_nodes (workspace_id, status);
CREATE INDEX IF NOT EXISTS idx_taxonomy_nodes_parent ON public.taxonomy_nodes (workspace_id, parent_id);
CREATE INDEX IF NOT EXISTS idx_taxonomy_nodes_embedding ON public.taxonomy_nodes USING hnsw (embedding vector_cosine_ops);

CREATE POLICY "Users manage taxonomy in their workspace" ON public.taxonomy_nodes
  FOR ALL TO authenticated
  USING (workspace_id IN (SELECT workspace_id FROM public.profiles WHERE user_id = auth.uid()))
  WITH CHECK (workspace_id IN (SELECT workspace_id FROM public.profiles WHERE user_id = auth.uid()));

CREATE TRIGGER set_taxonomy_nodes_updated_at
  BEFORE UPDATE ON public.taxonomy_nodes
  FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();

CREATE TABLE IF NOT EXISTS public.signal_node_map (
  id bigserial PRIMARY KEY,
  signal_id integer NOT NULL REFERENCES public.signals(id) ON DELETE CASCADE,
  node_id uuid NOT NULL REFERENCES public.taxonomy_nodes(id) ON DELETE CASCADE,
  score numeric,
  mapped_by text NOT NULL DEFAULT 'system_auto' CHECK (mapped_by IN ('system_auto','system_llm','user')),
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (signal_id, node_id)
);
ALTER TABLE public.signal_node_map ENABLE ROW LEVEL SECURITY;
CREATE INDEX IF NOT EXISTS idx_signal_node_map_node ON public.signal_node_map (node_id);

CREATE POLICY "Users view signal map in their workspace" ON public.signal_node_map
  FOR SELECT TO authenticated
  USING (signal_id IN (
    SELECT s.id FROM public.signals s
    JOIN public.profiles p ON p.workspace_id = s.workspace_id
    WHERE p.user_id = auth.uid()
  ));

-- Nearest-neighbour retrieval over ACTIVE nodes for a workspace.
CREATE OR REPLACE FUNCTION public.match_taxonomy_nodes(
  p_workspace_id integer,
  p_query_embedding vector(768),
  p_match_count integer DEFAULT 5
)
RETURNS TABLE (id uuid, name text, level integer, slug text, similarity double precision)
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
