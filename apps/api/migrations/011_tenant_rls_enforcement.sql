-- 011 — Tenant isolation enforcement + DB-scheduled measurements
--
-- Closes review findings #25 (Postgres stores never scoped by workspace; RLS
-- inert because the app connects as the table owner and never set the GUCs),
-- #30/#31 (tenant/actor from spoofable client headers), and moves the
-- measurement tick into the database (pg_cron) so it survives restarts and
-- cannot double-fire across Render + local dev sharing this database.
--
-- ORDERING: apply AFTER deploying the matching API code. The new code sets
-- app.tenant_id/app.workspace_id on every pooled checkout (harmless before
-- this migration); the OLD code never sets them, so forcing RLS first would
-- blank every read (fail-closed outage).
--
-- The API-side counterpart lives in PostgresConnectionMixin (_connect sets the
-- GUCs; _run_schema_ddl self-heals the tenant-first PK and the two policies it
-- owns on boot). This file is the one-time enforcement flip for the live DB.
--
-- ROLLBACK (paste as-is):
--   DO $$ DECLARE t text; BEGIN
--     FOREACH t IN ARRAY ARRAY['clara_problems','clara_signals',
--       'clara_candidate_decisions','clara_customer_context',
--       'clara_workflow_records','clara_taxonomy_catalogs',
--       'clara_terminology_dictionary','clara_telemetry',
--       'clara_measurement_plans','clara_connector_configs',
--       'clara_journey_events','clara_feedback_rules',
--       'clara_workspace_settings','clara_api_keys']
--     LOOP EXECUTE format('ALTER TABLE %I NO FORCE ROW LEVEL SECURITY', t);
--     END LOOP; END $$;
--   SELECT cron.unschedule('clara-measurements-due');
--
-- NOTE for ad-hoc SQL-editor DML after this migration: the editor runs as the
-- table owner, which is now bound by RLS. Run
--   SELECT set_config('app.tenant_id','1',false), set_config('app.workspace_id','1',false);
-- first (or use the service role, which keeps BYPASSRLS).

-- ====== 0. Guard: everything below assumes the default workspace is id 1 ======
-- (auth.py UserContext default, the ContextVar default, and every workspace_id
-- DEFAULT all say 1). Do NOT auto-insert an id=1 row here: an explicit-id
-- insert desyncs workspaces_id_seq and breaks handle_new_user signups.
DO $$
DECLARE
  default_ws integer;
BEGIN
  SELECT id INTO default_ws FROM public.workspaces WHERE slug = 'default';
  IF default_ws IS DISTINCT FROM 1 THEN
    RAISE EXCEPTION
      'default workspace has id % (expected 1) — reconcile workspace ids before enforcing RLS',
      default_ws;
  END IF;
END $$;

-- ====== 1. Harden the workspace-predicate casts ======
-- The old bodies cast current_setting('app.tenant_id')::int directly: any
-- non-numeric leftover value would make every policied query ERROR instead of
-- filtering. Guard the cast; non-numeric -> NULL -> COALESCE(...) -> FALSE.
CREATE OR REPLACE FUNCTION public.is_current_workspace(_ws_id integer)
RETURNS BOOLEAN
LANGUAGE sql
STABLE
AS $$
  SELECT COALESCE(
    _ws_id = NULLIF(current_setting('app.tenant_id', true), '')::int,
    _ws_id = (NULLIF(current_setting('request.jwt.claims', true), '')::jsonb ->> 'workspace_id')::int,
    FALSE
  )
  WHERE current_setting('app.tenant_id', true) IS NULL
     OR current_setting('app.tenant_id', true) ~ '^\d*$'
$$;

-- (If the GUC is non-numeric the WHERE filters out the only row, the function
-- returns NULL, and the policy treats NULL as not-visible: fail-closed.)

CREATE OR REPLACE FUNCTION public.current_workspace_id()
RETURNS INTEGER
LANGUAGE sql
STABLE
AS $$
  SELECT NULLIF(current_setting('app.tenant_id', true), '')::int
  WHERE current_setting('app.tenant_id', true) ~ '^\d+$'
  UNION ALL
  SELECT (NULLIF(current_setting('request.jwt.claims', true), '')::jsonb ->> 'workspace_id')::int
  LIMIT 1
$$;

-- ====== 2. Backfill header-era tenant strings -> '1' (default workspace) ======
-- Live values verified 2026-07-05: 'legacy'(4), 'tenant_feature_test'(2);
-- 'demo_tenant' is the local-dev frontend default. The payload rewrite matters:
-- the API filters closure/learning records by the tenant_id INSIDE the payload.
UPDATE clara_workflow_records
SET tenant_id = '1',
    payload = CASE
      WHEN record_type IN ('closure', 'learning_conclusion')
        THEN jsonb_set(payload, '{tenant_id}', '"1"')
      ELSE payload
    END
WHERE tenant_id IN ('legacy', 'demo_tenant', 'tenant_feature_test');

-- Fail loud on anything unexpected: a non-numeric tenant left here is a real
-- header-era string we have not reviewed (numeric ones are actual workspaces).
DO $$
DECLARE
  leftover text;
BEGIN
  SELECT string_agg(DISTINCT tenant_id, ', ') INTO leftover
  FROM clara_workflow_records
  WHERE tenant_id !~ '^\d+$';
  IF leftover IS NOT NULL THEN
    RAISE EXCEPTION 'unreviewed tenant_id values remain: % — extend the backfill list', leftover;
  END IF;
END $$;

-- ====== 3. Tenant-first primary key on workflow records ======
-- Record ids (DEC-0001, EXE-0001, ...) are minted from the tenant-visible rows,
-- so uniqueness must be per tenant: with the old global PK, tenant 2's first
-- approval would ON CONFLICT into tenant 1's (RLS-invisible) row -> 42501.
-- (The API boot self-heal performs the same swap; idempotent here.)
DO $$
DECLARE
  pk_cols text;
BEGIN
  SELECT string_agg(a.attname, ',' ORDER BY k.ord) INTO pk_cols
  FROM pg_constraint c
  JOIN unnest(c.conkey) WITH ORDINALITY AS k(attnum, ord) ON true
  JOIN pg_attribute a ON a.attrelid = c.conrelid AND a.attnum = k.attnum
  WHERE c.conrelid = 'clara_workflow_records'::regclass AND c.contype = 'p';
  IF pk_cols IS DISTINCT FROM 'tenant_id,record_type,record_id' THEN
    ALTER TABLE clara_workflow_records DROP CONSTRAINT clara_workflow_records_pkey;
    ALTER TABLE clara_workflow_records ADD PRIMARY KEY (tenant_id, record_type, record_id);
  END IF;
END $$;

-- ====== 4. One visibility predicate per table ======
-- 004 added a permissive workspace_id policy on clara_workflow_records that
-- ORs with 002's tenant_id policy — under OR, a row with a mismatched pair
-- leaks through whichever column matches. tenant_id is the workflow contract;
-- drop the workspace variant.
DROP POLICY IF EXISTS clara_workflow_records_workspace_isolation ON clara_workflow_records;

-- ====== 5. workspace_id defaults follow the session tenant ======
-- Inserts inherit the tenant set by the API at checkout, with no store naming
-- the column; WITH CHECK still verifies the result. GUC-less sessions fall
-- back to the default workspace.
DO $$
DECLARE
  t text;
BEGIN
  -- INTEGER columns (migration 004 tables)
  FOREACH t IN ARRAY ARRAY[
    'clara_problems', 'clara_signals', 'clara_candidate_decisions',
    'clara_customer_context', 'clara_workflow_records',
    'clara_taxonomy_catalogs', 'clara_terminology_dictionary'
  ] LOOP
    EXECUTE format(
      'ALTER TABLE %I ALTER COLUMN workspace_id SET DEFAULT '
      'COALESCE(NULLIF(current_setting(''app.workspace_id'', true), ''''), ''1'')::integer',
      t
    );
  END LOOP;
  -- BIGINT columns (008/009/010 ops tables; workspace_settings is a PK the
  -- API always writes explicitly, so it keeps no default)
  FOREACH t IN ARRAY ARRAY[
    'clara_telemetry', 'clara_measurement_plans', 'clara_connector_configs',
    'clara_journey_events', 'clara_feedback_rules', 'clara_api_keys'
  ] LOOP
    EXECUTE format(
      'ALTER TABLE %I ALTER COLUMN workspace_id SET DEFAULT '
      'COALESCE(NULLIF(current_setting(''app.workspace_id'', true), ''''), ''1'')::bigint',
      t
    );
  END LOOP;
END $$;

-- ====== 6. FORCE ROW LEVEL SECURITY ======
-- The app connects as the table owner; without FORCE every policy above is
-- decorative (the core of finding #25). service_role keeps BYPASSRLS.
-- Deliberately NOT forced: public.workspaces (handle_new_user + the cron
-- per-workspace loops read it), taxonomy_nodes / signal_node_map (the
-- taxonomy governance job manages workspaces explicitly), and the unused
-- public.* tables from 005.
DO $$
DECLARE
  t text;
BEGIN
  FOREACH t IN ARRAY ARRAY[
    'clara_problems', 'clara_signals', 'clara_candidate_decisions',
    'clara_customer_context', 'clara_workflow_records',
    'clara_taxonomy_catalogs', 'clara_terminology_dictionary',
    'clara_telemetry', 'clara_measurement_plans', 'clara_connector_configs',
    'clara_journey_events', 'clara_feedback_rules',
    'clara_workspace_settings', 'clara_api_keys'
  ] LOOP
    EXECUTE format('ALTER TABLE %I FORCE ROW LEVEL SECURITY', t);
  END LOOP;
END $$;

-- ====== 7. The measurement tick, in the database ======
-- Faithful port of run_due_measurements (measurement_scheduler.py) +
-- record_outcome's staleness guard (workflow.py). Divergences, all accepted:
-- rounding is numeric half-up vs Python banker's (ties at 5e-5 only); the
-- due_at comparison casts to timestamptz instead of comparing ISO text; and
-- ::timestamptz accepts a few formats Python's fromisoformat would reject.

-- Mirror of Python's per-signal try/except: unparseable timestamps become
-- NULL (skipped) instead of aborting the whole workspace's pass.
CREATE OR REPLACE FUNCTION public.clara_safe_ts(_value text)
RETURNS timestamptz
LANGUAGE plpgsql
STABLE
SET search_path = public
AS $$
BEGIN
  RETURN _value::timestamptz;
EXCEPTION WHEN OTHERS THEN
  RETURN NULL;
END;
$$;

CREATE OR REPLACE FUNCTION public.clara_run_due_measurements(
  _ws_id integer,
  _now timestamptz DEFAULT now()
)
RETURNS jsonb
LANGUAGE plpgsql
SET search_path = public
AS $$
DECLARE
  plan RECORD;
  problem_payload jsonb;
  metric text;
  rest text;
  journey_n text;
  stage_n text;
  since_ts timestamptz;
  sample integer;
  elapsed_days numeric;
  rate numeric;
  measured_at_str text;
  existing_measured_at timestamptz;
  measured integer := 0;
  manual integer := 0;
  skipped integer := 0;
BEGIN
  -- Runs as the job owner, which FORCE binds to RLS: scope the transaction to
  -- the target workspace exactly like the API's connection checkout does.
  PERFORM set_config('app.tenant_id', _ws_id::text, true);
  PERFORM set_config('app.workspace_id', _ws_id::text, true);

  FOR plan IN
    SELECT id, problem_id, executed_at, kind
    FROM clara_measurement_plans
    WHERE status = 'pending' AND clara_safe_ts(due_at) <= _now
    ORDER BY due_at
    FOR UPDATE SKIP LOCKED
    -- SKIP LOCKED is the no-double-fire guarantee: pg_cron, the in-process
    -- loop, and the manual endpoint can overlap; in-flight plans are skipped.
  LOOP
    BEGIN
      SELECT payload INTO problem_payload
      FROM clara_problems WHERE problem_id = plan.problem_id;

      IF problem_payload IS NULL THEN
        UPDATE clara_measurement_plans
          SET status = 'skipped', note = 'Problem no longer exists'
          WHERE id = plan.id;
        skipped := skipped + 1;
        CONTINUE;
      END IF;

      metric := problem_payload #>> '{outcome_contract,primary_metric}';
      IF metric IS NULL OR metric NOT LIKE 'signal_rate_per_day:%' THEN
        -- CLARA cannot observe this metric — surface a human task, never
        -- invent data (the honesty rule from the eval work).
        UPDATE clara_measurement_plans
          SET status = 'manual_required',
              note = format('Metric ''%s'' needs a human-recorded measurement.', metric)
          WHERE id = plan.id;
        INSERT INTO clara_telemetry (event_type, entity_id, metadata)
          VALUES ('measurement_due', plan.problem_id,
                  jsonb_build_object('kind', plan.kind, 'metric', metric));
        manual := manual + 1;
        CONTINUE;
      END IF;

      -- metric = 'signal_rate_per_day:{journey}/{stage}', split at the FIRST
      -- slash (Python str.partition), then _norm_stage on both sides.
      rest := substr(metric, length('signal_rate_per_day:') + 1);
      journey_n := btrim(lower(replace(split_part(rest, '/', 1), '_', ' ')));
      stage_n := btrim(lower(replace(
        CASE WHEN strpos(rest, '/') > 0 THEN substr(rest, strpos(rest, '/') + 1) ELSE '' END,
        '_', ' ')));

      since_ts := clara_safe_ts(plan.executed_at);
      IF since_ts IS NULL THEN
        RAISE EXCEPTION 'unparseable executed_at: %', plan.executed_at;
      END IF;

      SELECT count(*) INTO sample
      FROM clara_signals s
      WHERE btrim(lower(replace(s.payload->>'journey', '_', ' '))) = journey_n
        AND btrim(lower(replace(s.payload->>'journey_stage', '_', ' '))) = stage_n
        AND clara_safe_ts(s.payload->>'timestamp') BETWEEN since_ts AND _now;

      elapsed_days := GREATEST(EXTRACT(EPOCH FROM (_now - since_ts)) / 86400.0, 1.0);
      rate := trim_scale(round((sample / elapsed_days)::numeric, 4));

      -- assert_measurement_not_stale: reject only strictly-older than the
      -- problem's latest recorded outcome (latest by created_at, record_id —
      -- the order _load_records applies before its last-wins overwrite).
      SELECT clara_safe_ts(payload->>'measured_at') INTO existing_measured_at
      FROM clara_workflow_records
      WHERE record_type = 'outcome' AND problem_id = plan.problem_id
      ORDER BY created_at DESC, record_id DESC
      LIMIT 1;
      IF existing_measured_at IS NOT NULL AND _now < existing_measured_at THEN
        RAISE EXCEPTION 'a newer measurement already exists';
      END IF;

      -- utc_now() shape: microseconds + 'Z'
      measured_at_str := to_char(_now AT TIME ZONE 'utc', 'YYYY-MM-DD"T"HH24:MI:SS.US') || 'Z';

      INSERT INTO clara_workflow_records (record_type, record_id, problem_id, tenant_id, payload)
      VALUES (
        'outcome',
        plan.problem_id || ':' || metric || ':' || measured_at_str || ':'
          || replace(gen_random_uuid()::text, '-', ''),
        plan.problem_id,
        _ws_id::text,
        jsonb_build_object(
          'problem_id', plan.problem_id,
          'metric', metric,
          'observed_value', rate,
          'measured_at', measured_at_str,
          'notes', format(
            'Auto-measured by the scheduler (%s): %s matching signals since action execution. real_data_source=true',
            plan.kind, sample)
        )
      );

      UPDATE clara_measurement_plans
        SET status = 'done',
            note = format('observed %s/day from %s signals', rate, sample)
        WHERE id = plan.id;
      INSERT INTO clara_telemetry (event_type, entity_id, metadata)
        VALUES ('outcome_recorded', plan.problem_id,
                jsonb_build_object('source', 'scheduler', 'real_data_source', true,
                                   'kind', plan.kind, 'observed_value', rate));
      measured := measured + 1;

    EXCEPTION WHEN OTHERS THEN
      -- Subtransaction rollback mirrors the Python catch: one bad plan must
      -- not stall the pass, and its partial writes vanish.
      UPDATE clara_measurement_plans
        SET status = 'skipped', note = 'record_outcome failed'
        WHERE id = plan.id;
      skipped := skipped + 1;
    END;
  END LOOP;

  RETURN jsonb_build_object(
    'measured', measured, 'manual_required', manual, 'skipped', skipped);
END;
$$;

-- ====== 8. Schedule via pg_cron ======
-- Migration 003 wrapped CREATE EXTENSION in a silent exception swallow, and on
-- this database it had silently FAILED — no pg_cron, no taxonomy job (found
-- 2026-07-05). Failures here surface as WARNINGs (visible in the SQL editor /
-- psql output) so the isolation work above still commits, and
-- scripts/pg_parity_smoke.py hard-asserts the jobs exist afterwards.
DO $$
BEGIN
  CREATE EXTENSION IF NOT EXISTS pg_cron;
EXCEPTION WHEN OTHERS THEN
  RAISE WARNING 'pg_cron could not be enabled (%). Enable it in the Supabase dashboard, then re-run section 8 of this migration.', SQLERRM;
END $$;

DO $$
BEGIN
  -- cron.schedule upserts by jobname on pg_cron >= 1.4 (Supabase ships 1.6);
  -- re-running this migration is safe.
  PERFORM cron.schedule(
    'clara-measurements-due',
    '*/15 * * * *',
    'SELECT public.clara_run_due_measurements(w.id) FROM public.workspaces w'
  );
  -- Re-heal the job 003 meant to create.
  IF EXISTS (SELECT 1 FROM pg_proc WHERE proname = 'apply_taxonomy_governance') THEN
    PERFORM cron.schedule(
      'taxonomy-governance-daily',
      '0 3 * * *',
      'SELECT public.apply_taxonomy_governance(id) FROM public.workspaces'
    );
  END IF;
EXCEPTION WHEN OTHERS THEN
  RAISE WARNING 'pg_cron scheduling failed (%): the measurement tick stays in-process until this section is re-run.', SQLERRM;
END $$;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM cron.job WHERE jobname = 'clara-measurements-due'
  ) THEN
    RAISE WARNING 'clara-measurements-due is NOT scheduled — measurements only run while an API instance is awake.';
  END IF;
EXCEPTION WHEN undefined_table THEN
  RAISE WARNING 'pg_cron absent: clara-measurements-due is NOT scheduled.';
END $$;
