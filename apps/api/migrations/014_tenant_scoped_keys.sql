-- 014 — Tenant-scoped primary keys
--
-- Every clara_ table carried a single-column primary key (signal_id,
-- problem_id, candidate_id, event_id, customer_id, taxonomy_type, term_id,
-- connector_type) next to a workspace_id column. Under FORCEd RLS a second
-- workspace's INSERT of the same key (Zendesk ticket 123, PRB-DRAFT-CHECKOUT-
-- PAYMENT, the 'jira' connector) conflicts with a row it cannot see: ON
-- CONFLICT DO NOTHING silently drops the import, DO UPDATE raises 42501. 011
-- fixed exactly this for clara_workflow_records; this migration does it for
-- the rest, so multi-workspace deployments stop being single-tenant by key.
--
-- The API self-heals the same swap on boot (PostgresConnectionMixin.
-- _run_schema_ddl); this file is the SQL-editor twin. Safe to re-run: each
-- swap is skipped when the key already has the expected shape or the table
-- has no workspace_id column (pre-004 databases).
--
-- ORDERING: deploy the matching API code first (its ON CONFLICT targets name
-- the composite keys); apply after 013.

DO $$
DECLARE
  spec RECORD;
  pk_cols text;
  pk_name text;
BEGIN
  FOR spec IN
    SELECT * FROM (VALUES
      ('clara_problems', 'problem_id'),
      ('clara_signals', 'signal_id'),
      ('clara_candidate_decisions', 'candidate_id'),
      ('clara_journey_events', 'event_id'),
      ('clara_customer_context', 'customer_id'),
      ('clara_taxonomy_catalogs', 'taxonomy_type'),
      ('clara_terminology_dictionary', 'term_id'),
      ('clara_connector_configs', 'connector_type')
    ) AS t(table_name, key_col)
  LOOP
    IF NOT EXISTS (
      SELECT 1 FROM information_schema.columns
      WHERE table_schema = 'public' AND table_name = spec.table_name AND column_name = 'workspace_id'
    ) THEN
      RAISE WARNING '% has no workspace_id column (apply 004 first); key left as is', spec.table_name;
      CONTINUE;
    END IF;

    EXECUTE format(
      'ALTER TABLE public.%I ALTER COLUMN workspace_id SET DEFAULT '
      'COALESCE(NULLIF(current_setting(''app.workspace_id'', true), ''''), ''1'')::bigint',
      spec.table_name);

    SELECT c.conname, string_agg(a.attname, ',' ORDER BY k.ord)
      INTO pk_name, pk_cols
    FROM pg_constraint c
    JOIN unnest(c.conkey) WITH ORDINALITY AS k(attnum, ord) ON true
    JOIN pg_attribute a ON a.attrelid = c.conrelid AND a.attnum = k.attnum
    WHERE c.conrelid = format('public.%I', spec.table_name)::regclass
      AND c.contype = 'p'
    GROUP BY c.conname;

    IF pk_cols IS DISTINCT FROM 'workspace_id,' || spec.key_col THEN
      IF pk_name IS NOT NULL THEN
        EXECUTE format('ALTER TABLE public.%I DROP CONSTRAINT %I', spec.table_name, pk_name);
      END IF;
      EXECUTE format('ALTER TABLE public.%I ADD PRIMARY KEY (workspace_id, %I)',
                     spec.table_name, spec.key_col);
    END IF;
  END LOOP;
END $$;
