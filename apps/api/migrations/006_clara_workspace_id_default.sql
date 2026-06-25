-- 006 — Default workspace_id on clara_* tables
-- Bridge: the API's Postgres stores are not yet workspace-aware (they INSERT only
-- (id, payload)), but migrations 003-005 made workspace_id NOT NULL. Default it to the
-- 'default' workspace (id 1) so single-tenant inserts succeed. Full per-tenant writes
-- (the API setting workspace_id from the authenticated user) are the deferred
-- tenant-isolation milestone.

DO $$
DECLARE
  default_ws_id integer;
  tbl text;
BEGIN
  SELECT id INTO default_ws_id FROM public.workspaces WHERE slug = 'default';
  IF default_ws_id IS NULL THEN
    RAISE EXCEPTION 'default workspace not found (run migration 004 first)';
  END IF;

  FOR tbl IN
    SELECT unnest(ARRAY[
      'clara_problems',
      'clara_signals',
      'clara_candidate_decisions',
      'clara_customer_context',
      'clara_workflow_records',
      'clara_taxonomy_catalogs',
      'clara_terminology_dictionary'
    ])
  LOOP
    EXECUTE format('ALTER TABLE %I ALTER COLUMN workspace_id SET DEFAULT %L', tbl, default_ws_id);
  END LOOP;
END $$;
