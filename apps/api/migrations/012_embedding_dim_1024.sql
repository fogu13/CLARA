-- 012 — retarget taxonomy embeddings at a 1024-dimension model (mistral-embed)
--
-- 003 pinned taxonomy_nodes.embedding to vector(768), matching the default
-- AI_EMBED_MODEL=gemini-embedding-001 (requested at 768 dims). A deployment
-- whose AI_BASE_URL is Mistral must use mistral-embed, which is 1024-dim, so
-- every taxonomy write would fail on the column type.
--
-- CHANGING MODEL DISCARDS THE OLD VECTORS ON PURPOSE. Embeddings from two
-- different models do not share a similarity space; a 768->1024 "conversion"
-- would be meaningless even if it were possible. This migration therefore
-- clears the column and the taxonomy must be re-embedded afterwards:
--
--     POST /taxonomy/bootstrap
--
-- Until that runs, match_taxonomy_nodes() returns nothing (it already skips
-- NULL embeddings) and semantic mapping degrades to no matches — visible and
-- safe, not silently wrong. Existing signal_node_map rows are LEFT INTACT:
-- they are historical mappings, and deleting a workspace's classification
-- history is not this migration's call.
--
-- Idempotent: re-running once the column is vector(1024) is a no-op, so a
-- second application cannot wipe embeddings that were re-generated in between.
--
-- Picking a different provider? Change the two 1024s in the DO block below to
-- your model's dimension and keep AI_EMBED_DIM in the API env consistent with
-- it (see DEPLOY.md). pgvector's hnsw index supports up to 2000 dimensions.

DO $$
DECLARE
  current_type text;
BEGIN
  SELECT format_type(a.atttypid, a.atttypmod) INTO current_type
  FROM pg_attribute a
  JOIN pg_class c ON c.oid = a.attrelid
  JOIN pg_namespace n ON n.oid = c.relnamespace
  WHERE n.nspname = 'public'
    AND c.relname = 'taxonomy_nodes'
    AND a.attname = 'embedding'
    AND a.attnum > 0
    AND NOT a.attisdropped;

  IF current_type IS NULL THEN
    RAISE NOTICE '012: public.taxonomy_nodes.embedding not found — run 003 first; nothing to do';
    RETURN;
  END IF;

  IF current_type = 'vector(1024)' THEN
    RAISE NOTICE '012: embedding is already vector(1024) — leaving existing vectors intact';
    RETURN;
  END IF;

  RAISE NOTICE '012: converting embedding from % to vector(1024); vectors cleared, re-run taxonomy bootstrap', current_type;

  -- The hnsw index is built for the old dimension; drop before the rewrite.
  EXECUTE 'DROP INDEX IF EXISTS public.idx_taxonomy_nodes_embedding';

  -- USING NULL does the clear as part of the type change: one table rewrite,
  -- and DDL so it is not filtered by the FORCEd RLS that 011 put on this table
  -- (a plain UPDATE from the SQL editor would touch 0 rows without first
  -- calling set_config('app.tenant_id',...), then the type change would fail
  -- on the rows it left behind).
  EXECUTE 'ALTER TABLE public.taxonomy_nodes ALTER COLUMN embedding TYPE vector(1024) USING NULL';

  EXECUTE 'CREATE INDEX idx_taxonomy_nodes_embedding'
       || ' ON public.taxonomy_nodes USING hnsw (embedding vector_cosine_ops)';
END $$;

-- Kept in sync with the column for readability only: Postgres drops the typmod
-- from function argument types, so this signature is (integer, vector, integer)
-- either way and CREATE OR REPLACE replaces 003's definition rather than adding
-- an overload. Body is unchanged from 003.
CREATE OR REPLACE FUNCTION public.match_taxonomy_nodes(
  p_workspace_id INTEGER,
  p_query_embedding vector(1024),
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
