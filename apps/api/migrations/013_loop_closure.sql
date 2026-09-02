-- 013 — Loop closure: AI theme insights, learning memory, theme-aware measurements
--
-- Closes three production gaps against the product promise ("collect →
-- triage → route → close & learn, and prove it"):
--
--   1. POST /triage/run sorted feedback into AI themes and then DROPPED them —
--      the insights lived only in the HTTP response. clara_theme_insights
--      persists them per (workspace, theme tag) so they surface as problem
--      candidates (origin = ai_theme) and enter the same accept → approve →
--      measure path as journey/stage candidates.
--   2. Reviewer learning conclusions were appended to clara_workflow_records
--      but never reached the retrieval store synthesis reads (the API used an
--      ephemeral SQLite file even on Postgres). clara_learnings is the
--      Postgres learning memory; rank_learnings reads it on every triage run.
--   3. clara_run_due_measurements only matched signals by journey/stage
--      columns. Theme contracts (metric 'signal_rate_per_day:theme/<tag>')
--      match signals carrying the tag instead, and closing checkpoints
--      (window / followup) now record a loop verdict (loop_closed or
--      fix_did_not_land) in telemetry — the pitch's "if the theme drops the
--      following month, the loop worked".
--
-- The API-side DDL (PostgresConnectionMixin._run_schema_ddl) creates the two
-- tables and self-heals their RLS on boot; this file is the SQL-editor twin
-- and carries the function replacement, which only lives here.
--
-- ORDERING: apply after 011 (needs clara_safe_ts, is_current_workspace and the
-- FORCE RLS conventions). Safe to re-run.
--
-- ROLLBACK (paste as-is): re-run section 7 of 011 to restore the previous
-- function body; DROP TABLE clara_theme_insights, clara_learnings.

-- ====== 1. Theme insights ======
CREATE TABLE IF NOT EXISTS public.clara_theme_insights (
  workspace_id BIGINT NOT NULL DEFAULT COALESCE(NULLIF(current_setting('app.workspace_id', true), ''), '1')::bigint,
  theme_tag TEXT NOT NULL,
  payload JSONB NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (workspace_id, theme_tag)
);
ALTER TABLE public.clara_theme_insights ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS clara_theme_insights_workspace_isolation ON public.clara_theme_insights;
CREATE POLICY clara_theme_insights_workspace_isolation ON public.clara_theme_insights
  USING (workspace_id = COALESCE(NULLIF(current_setting('app.workspace_id', true), ''), '1')::bigint)
  WITH CHECK (workspace_id = COALESCE(NULLIF(current_setting('app.workspace_id', true), ''), '1')::bigint);
ALTER TABLE public.clara_theme_insights FORCE ROW LEVEL SECURITY;

-- ====== 2. Learning memory ======
CREATE TABLE IF NOT EXISTS public.clara_learnings (
  workspace_id BIGINT NOT NULL DEFAULT COALESCE(NULLIF(current_setting('app.workspace_id', true), ''), '1')::bigint,
  conclusion_id TEXT NOT NULL,
  topic TEXT,
  payload JSONB NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (workspace_id, conclusion_id)
);
ALTER TABLE public.clara_learnings ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS clara_learnings_workspace_isolation ON public.clara_learnings;
CREATE POLICY clara_learnings_workspace_isolation ON public.clara_learnings
  USING (workspace_id = COALESCE(NULLIF(current_setting('app.workspace_id', true), ''), '1')::bigint)
  WITH CHECK (workspace_id = COALESCE(NULLIF(current_setting('app.workspace_id', true), ''), '1')::bigint);
ALTER TABLE public.clara_learnings FORCE ROW LEVEL SECURITY;
CREATE INDEX IF NOT EXISTS clara_learnings_topic_idx ON public.clara_learnings (workspace_id, topic);

-- ====== 3. Theme-aware, verdict-recording measurement tick ======
-- Same contract as 011 §7 (returns {measured, manual_required, skipped}); adds
-- loop_closed / fix_did_not_land counters and the theme branch. Mirrors
-- app/services/measurement_scheduler.run_due_measurements exactly.
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
  baseline numeric;
  target numeric;
  outcome_status text;
  verdict_event text;
  measured_at_str text;
  existing_measured_at timestamptz;
  measured integer := 0;
  manual integer := 0;
  skipped integer := 0;
  loop_closed integer := 0;
  fix_did_not_land integer := 0;
BEGIN
  PERFORM set_config('app.tenant_id', _ws_id::text, true);
  PERFORM set_config('app.workspace_id', _ws_id::text, true);

  FOR plan IN
    SELECT id, problem_id, executed_at, kind
    FROM clara_measurement_plans
    WHERE status = 'pending' AND clara_safe_ts(due_at) <= _now
    ORDER BY due_at
    FOR UPDATE SKIP LOCKED
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

      rest := substr(metric, length('signal_rate_per_day:') + 1);
      journey_n := btrim(lower(replace(split_part(rest, '/', 1), '_', ' ')));
      stage_n := btrim(lower(replace(
        CASE WHEN strpos(rest, '/') > 0 THEN substr(rest, strpos(rest, '/') + 1) ELSE '' END,
        '_', ' ')));

      since_ts := clara_safe_ts(plan.executed_at);
      IF since_ts IS NULL THEN
        RAISE EXCEPTION 'unparseable executed_at: %', plan.executed_at;
      END IF;

      IF journey_n = 'theme' THEN
        -- Theme contract: a signal is in scope when it carries the theme tag
        -- (written back by triage enrichment), whatever journey it came from.
        SELECT count(*) INTO sample
        FROM clara_signals s
        WHERE EXISTS (
                SELECT 1
                FROM jsonb_array_elements_text(
                  CASE WHEN jsonb_typeof(s.payload->'tags') = 'array'
                       THEN s.payload->'tags' ELSE '[]'::jsonb END) AS t(tag)
                WHERE btrim(lower(replace(t.tag, '_', ' '))) = stage_n)
          AND clara_safe_ts(s.payload->>'timestamp') BETWEEN since_ts AND _now;
      ELSE
        SELECT count(*) INTO sample
        FROM clara_signals s
        WHERE btrim(lower(replace(s.payload->>'journey', '_', ' '))) = journey_n
          AND btrim(lower(replace(s.payload->>'journey_stage', '_', ' '))) = stage_n
          AND clara_safe_ts(s.payload->>'timestamp') BETWEEN since_ts AND _now;
      END IF;

      elapsed_days := GREATEST(EXTRACT(EPOCH FROM (_now - since_ts)) / 86400.0, 1.0);
      rate := trim_scale(round((sample / elapsed_days)::numeric, 4));

      SELECT clara_safe_ts(payload->>'measured_at') INTO existing_measured_at
      FROM clara_workflow_records
      WHERE record_type = 'outcome' AND problem_id = plan.problem_id
      ORDER BY created_at DESC, record_id DESC
      LIMIT 1;
      IF existing_measured_at IS NOT NULL AND _now < existing_measured_at THEN
        RAISE EXCEPTION 'a newer measurement already exists';
      END IF;

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
            plan.kind, sample),
          'measurement_source', 'instrumented'
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

      -- Loop verdict on the closing checkpoints (outcome_engine.outcome_status,
      -- decrease direction: signal-rate metrics are complaint-style).
      IF plan.kind IN ('window', 'followup') THEN
        baseline := (problem_payload #>> '{outcome_contract,baseline}')::numeric;
        target := (problem_payload #>> '{outcome_contract,success_threshold}')::numeric;
        IF baseline = 0 AND target = 0 AND rate = 0 THEN
          outcome_status := 'not_measured';
        ELSIF rate <= target THEN
          outcome_status := 'target_met';
        ELSIF rate < baseline THEN
          outcome_status := 'improving';
        ELSE
          outcome_status := 'not_improved';
        END IF;
        verdict_event := NULL;
        IF outcome_status = 'target_met' THEN
          verdict_event := 'loop_closed';
          loop_closed := loop_closed + 1;
        ELSIF outcome_status = 'not_improved' THEN
          verdict_event := 'fix_did_not_land';
          fix_did_not_land := fix_did_not_land + 1;
        END IF;
        IF verdict_event IS NOT NULL THEN
          INSERT INTO clara_telemetry (event_type, entity_id, metadata)
            VALUES (verdict_event, plan.problem_id,
                    jsonb_build_object('kind', plan.kind, 'metric', metric,
                                       'observed_value', rate, 'baseline', baseline,
                                       'success_threshold', target, 'real_data_source', true));
        END IF;
      END IF;

    EXCEPTION WHEN OTHERS THEN
      UPDATE clara_measurement_plans
        SET status = 'skipped', note = 'record_outcome failed'
        WHERE id = plan.id;
      skipped := skipped + 1;
    END;
  END LOOP;

  RETURN jsonb_build_object(
    'measured', measured, 'manual_required', manual, 'skipped', skipped,
    'loop_closed', loop_closed, 'fix_did_not_land', fix_did_not_land);
END;
$$;
