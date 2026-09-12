-- 016 — Measurement provenance: clock origins, contract revisions, bound readings
--
-- Closes three semantic gaps in the close-the-loop measurement path:
--
--   1. The measurement clock started at APPROVAL time for every approved
--      action — including pushes that failed and drafts that never left
--      CLARA — so "signals since execution" could measure a fix that never
--      happened. Plans now carry an `origin` (approval | dispatch |
--      implementation): the API schedules from the dispatch instant of a
--      real push, from the human-recorded implementation instant when one
--      exists, and from approval only when the draft itself is the
--      deliverable; a failed push starts no clock. Plans a later
--      implementation record replaces are marked `superseded`.
--   2. Outcome contracts carry a `revision` (in the problem payload; no DDL
--      needed). `contract_revision` on a plan records the terms the
--      checkpoints were scheduled under.
--   3. clara_run_due_measurements bound nothing to the reading it wrote: the
--      loop verdict was inferred from "a closing plan is done", so a manual
--      reading after an old window read could be certified "on real
--      signals". The outcome payload now names the checkpoint that produced
--      it (checkpoint_kind, plan_id, execution_id), freezes the contract
--      it was scored under (contract_revision — COALESCEd to 1 for problems
--      written before contracts carried a revision — and contract_snapshot)
--      and records the clock it was taken on (clock_origin, clock_origin_at
--      = the plan's origin and executed_at); the API reads status, verdict
--      and the verdict's clock from that binding. The span note names the
--      clock origin. The follow-up read starts at the plan's own due_at
--      minus the 30-day gap, so a window amended after scheduling cannot
--      rewrite what the follow-up reads.
--
-- The function body is 013 §3 with exactly those payload/span changes
-- (mirrors app/services/measurement_scheduler.run_due_measurements — keep the
-- two in step). The API-side DDL (PostgresConnectionMixin._run_schema_ddl)
-- self-heals the two columns on boot; this file is the SQL-editor twin and
-- carries the function replacement, which only lives here.
--
-- ORDERING: apply after 013 (replaces its function; needs clara_safe_ts and
-- the RLS conventions of 011). Safe to re-run.
--
-- ROLLBACK (paste as-is): re-run section 3 of 013 to restore the previous
-- function body; ALTER TABLE public.clara_measurement_plans
--   DROP COLUMN IF EXISTS origin, DROP COLUMN IF EXISTS contract_revision;

-- ====== 1. Plan clock origin + contract revision ======
ALTER TABLE public.clara_measurement_plans
  ADD COLUMN IF NOT EXISTS origin TEXT NOT NULL DEFAULT 'approval',
  ADD COLUMN IF NOT EXISTS contract_revision INTEGER;

-- ====== 2. Measurement tick with bound, provenance-carrying readings ======
-- Same contract as 013 §3 (returns {measured, manual_required, skipped,
-- loop_closed, fix_did_not_land, processed}).
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
  unenriched integer;
  span_note text;
  processed jsonb := '[]'::jsonb;
BEGIN
  PERFORM set_config('app.tenant_id', _ws_id::text, true);
  PERFORM set_config('app.workspace_id', _ws_id::text, true);

  FOR plan IN
    SELECT id, problem_id, execution_id, executed_at, due_at, kind, origin
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
      -- The clock origin (approval | dispatch | implementation) is part of
      -- the record: a reader must be able to tell what "since" means.
      span_note := format('since %s (%s)',
        COALESCE(plan.origin, 'approval'), substr(plan.executed_at, 1, 10));
      IF plan.kind = 'followup' THEN
        -- Keep-listening read: the month AFTER the window the plan was
        -- scheduled with, not the cumulative span and not the CURRENT window
        -- (mirrors measurement_scheduler.followup_window_start: due_at was
        -- fixed at scheduling as executed + window + 30 days).
        since_ts := clara_safe_ts(plan.due_at) - make_interval(days => 30);
        IF since_ts IS NULL THEN
          RAISE EXCEPTION 'unparseable due_at: %', plan.due_at;
        END IF;
        span_note := format(
          'in the month after the measurement window closed (keep-listening read; clock from %s %s)',
          COALESCE(plan.origin, 'approval'), substr(plan.executed_at, 1, 10));
      END IF;

      IF journey_n = 'theme' THEN
        -- Tags only exist after triage enrichment: a window holding unenriched
        -- signals cannot be read honestly — the count would under-report and a
        -- theme could "close" merely because triage never ran on the new inflow.
        -- Stay pending (re-tried next tick) and say why
        -- (mirrors measurement_scheduler.unenriched_in_window).
        SELECT count(*) INTO unenriched
        FROM clara_signals s
        WHERE NOT coalesce((s.payload->>'enriched')::boolean, false)
          AND clara_safe_ts(s.payload->>'timestamp') BETWEEN since_ts AND _now;
        IF unenriched > 0 THEN
          UPDATE clara_measurement_plans
            SET note = format(
              '%s in-window signals not yet enriched — run triage before this theme can be measured',
              unenriched)
            WHERE id = plan.id;
          skipped := skipped + 1;
          CONTINUE;
        END IF;
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
      ELSIF journey_n = 'unknown journey' AND stage_n LIKE '% feedback' THEN
        -- Journey-less feedback is grouped per source ("<source>_feedback") by
        -- build_candidates while the signals keep journey_stage unknown_stage;
        -- count those same signals or the contract reads 0/day forever
        -- (mirrors measurement_scheduler.signal_matches_scope).
        SELECT count(*) INTO sample
        FROM clara_signals s
        WHERE btrim(lower(replace(s.payload->>'journey', '_', ' '))) = journey_n
          AND (
            btrim(lower(replace(s.payload->>'journey_stage', '_', ' '))) = stage_n
            OR (
              btrim(lower(replace(s.payload->>'journey_stage', '_', ' '))) = 'unknown stage'
              AND btrim(lower(replace(coalesce(s.payload->>'source', ''), '_', ' '))) || ' feedback'
                  = stage_n
            )
          )
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
            'Auto-measured by the scheduler (%s): %s matching signals %s. real_data_source=true',
            plan.kind, sample, span_note),
          'measurement_source', 'instrumented',
          -- Provenance (mirrors measurement_scheduler.run_due_measurements):
          -- which checkpoint produced the reading and which contract terms
          -- it was scored under, frozen so a later amendment cannot
          -- reinterpret it.
          'checkpoint_kind', plan.kind,
          'plan_id', plan.id,
          'execution_id', plan.execution_id,
          'contract_revision', COALESCE((problem_payload #>> '{outcome_contract,revision}')::int, 1),
          'contract_snapshot', problem_payload->'outcome_contract',
          -- The clock the reading was taken on (the plan's origin and
          -- instant), so a later anchor cannot relabel it.
          'clock_origin', COALESCE(plan.origin, 'approval'),
          'clock_origin_at', plan.executed_at
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
      processed := processed || jsonb_build_object(
        'problem_id', plan.problem_id, 'executed_at', plan.executed_at, 'kind', plan.kind);

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

  -- 'processed' lets the API run the Python guardrail pass for exactly the
  -- plans this tick measured (the function has no guardrail branch).
  RETURN jsonb_build_object(
    'measured', measured, 'manual_required', manual, 'skipped', skipped,
    'loop_closed', loop_closed, 'fix_did_not_land', fix_did_not_land,
    'processed', processed);
END;
$$;
