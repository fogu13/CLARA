-- 017 — Measurement intervals and frozen terms: checkpoints read a fixed
--       interval under the contract terms they were scheduled with
--
-- Closes the two measurement gaps of the 13 September 2026 follow-up review:
--
--   F2. A pending checkpoint was scored under whatever the outcome contract
--       said when the tick ran: an amendment of the target, baseline, metric,
--       method or window between scheduling and reading silently re-scored
--       the checkpoint (a target loosened from 50 to 90 turned an 80 reading
--       into target_met under revision 2 while the plan was scheduled under
--       revision 1). Plans now carry `contract_snapshot`, the complete terms
--       frozen at scheduling, and the tick scores under them. A legacy plan
--       without a snapshot is scored under the current contract only when
--       the revision recorded on the plan (1 for rows that predate revisions)
--       equals the problem's current revision — a deterministic link; when an
--       amendment happened in between the plan is marked `blocked` with the
--       reason instead of being scored under terms nobody scheduled it with.
--       The API re-plans pending checkpoints explicitly on every amendment
--       (measurement_scheduler.replan_after_amendment, telemetry
--       measurement_replanned).
--   F3. The tick read every checkpoint from the clock origin up to `_now`,
--       the processing instant: a worker that ran on day 30 read a 7-day
--       window as a 30-day cumulative average (2.33/day instead of 8.57/day).
--       Plans now carry `observation_start` / `observation_end`, fixed at
--       scheduling (T+7 and window: [executed, executed + k days]; follow-up:
--       [due - 30 days, due]); the tick reads exactly that interval with
--       inclusive bounds, and the reading records it. `measured_at` stays the
--       processing instant. Two readings processed in one tick keep their
--       order through the plan-id suffix of the record id (016); the API's
--       latest-reading rule prefers the later observation interval.
--
-- The function body is 016 §2 with exactly those changes (mirrors
-- app/services/measurement_scheduler.run_due_measurements — keep the two in
-- step). The API-side DDL (PostgresConnectionMixin._run_schema_ddl)
-- self-heals the three columns on boot; this file is the SQL-editor twin and
-- carries the function replacement, which only lives here.
--
-- ORDERING: apply after 016 (replaces its function; needs clara_safe_ts).
-- Safe to re-run. Until it is applied, the Postgres tick keeps 016
-- behaviour: the API-side plans already carry the frozen terms and the
-- interval (self-healed columns) and the Python fallback tick honours them;
-- GET /ready/details reports the function version so the gap is visible.
--
-- ROLLBACK (paste as-is): re-run section 2 of 016 to restore the previous
-- function body; ALTER TABLE public.clara_measurement_plans
--   DROP COLUMN IF EXISTS contract_snapshot,
--   DROP COLUMN IF EXISTS observation_start,
--   DROP COLUMN IF EXISTS observation_end;

-- ====== 1. Frozen terms + fixed observation interval on plans ======
ALTER TABLE public.clara_measurement_plans
  ADD COLUMN IF NOT EXISTS contract_snapshot JSONB,
  ADD COLUMN IF NOT EXISTS observation_start TEXT,
  ADD COLUMN IF NOT EXISTS observation_end TEXT;

-- ====== 2. Function version marker (read by GET /ready/details) ======
CREATE OR REPLACE FUNCTION public.clara_measurement_function_version()
RETURNS integer
LANGUAGE sql
IMMUTABLE
AS $$ SELECT 17 $$;

-- ====== 3. Measurement tick: fixed intervals, frozen terms ======
-- Same contract as 013 §3 / 016 §2 (returns {measured, manual_required,
-- skipped, loop_closed, fix_did_not_land, processed}); `processed` rows now
-- also carry observation_end so the API's guardrail pass reads the same
-- interval.
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
  terms jsonb;
  metric text;
  rest text;
  journey_n text;
  stage_n text;
  since_ts timestamptz;
  until_ts timestamptz;
  fixed_interval boolean;
  sample integer;
  elapsed_days numeric;
  rate numeric;
  baseline numeric;
  target numeric;
  outcome_status text;
  verdict_event text;
  measured_at_str text;
  existing_measured_at timestamptz;
  existing_observation_end timestamptz;
  scheduled_under integer;
  current_revision integer;
  measured integer := 0;
  manual integer := 0;
  skipped integer := 0;
  loop_closed integer := 0;
  fix_did_not_land integer := 0;
  unenriched integer;
  span_note text;
  blocked_reason text;
  processed jsonb := '[]'::jsonb;
BEGIN
  PERFORM set_config('app.tenant_id', _ws_id::text, true);
  PERFORM set_config('app.workspace_id', _ws_id::text, true);

  FOR plan IN
    SELECT id, problem_id, execution_id, executed_at, due_at, kind, origin,
           contract_revision, contract_snapshot, observation_start, observation_end
    FROM clara_measurement_plans
    WHERE status = 'pending' AND clara_safe_ts(due_at) <= _now
    ORDER BY due_at, id
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

      -- The terms this checkpoint is scored under (mirrors
      -- measurement_scheduler.plan_scoring_terms): the frozen snapshot, or the
      -- current contract when no amendment happened since scheduling.
      current_revision := COALESCE((problem_payload #>> '{outcome_contract,revision}')::int, 1);
      IF plan.contract_snapshot IS NOT NULL THEN
        terms := plan.contract_snapshot;
      ELSE
        scheduled_under := COALESCE(plan.contract_revision, 1);
        IF scheduled_under IS DISTINCT FROM current_revision THEN
          blocked_reason := format(
            'contract amended after scheduling (revision %s -> %s) and the plan carries no frozen terms; amend the contract again to re-plan its checkpoints',
            scheduled_under, current_revision);
          UPDATE clara_measurement_plans
            SET status = 'blocked', note = blocked_reason
            WHERE id = plan.id;
          INSERT INTO clara_telemetry (event_type, entity_id, metadata)
            VALUES ('measurement_blocked', plan.problem_id,
                    jsonb_build_object('kind', plan.kind, 'plan_id', plan.id, 'reason', blocked_reason));
          skipped := skipped + 1;
          CONTINUE;
        END IF;
        terms := problem_payload->'outcome_contract';
      END IF;

      metric := terms->>'primary_metric';
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

      -- The interval this checkpoint reads (mirrors
      -- measurement_scheduler.plan_observation_interval): fixed at scheduling,
      -- or the legacy bounds for plans that predate 017.
      fixed_interval := plan.observation_start IS NOT NULL AND plan.observation_end IS NOT NULL;
      IF fixed_interval THEN
        since_ts := clara_safe_ts(plan.observation_start);
        until_ts := clara_safe_ts(plan.observation_end);
        IF since_ts IS NULL OR until_ts IS NULL THEN
          RAISE EXCEPTION 'unparseable observation interval: % .. %',
            plan.observation_start, plan.observation_end;
        END IF;
        span_note := format('in the fixed interval %s..%s (clock from %s %s)',
          substr(plan.observation_start, 1, 10), substr(plan.observation_end, 1, 10),
          COALESCE(plan.origin, 'approval'), substr(plan.executed_at, 1, 10));
      ELSE
        since_ts := clara_safe_ts(plan.executed_at);
        IF since_ts IS NULL THEN
          RAISE EXCEPTION 'unparseable executed_at: %', plan.executed_at;
        END IF;
        until_ts := _now;
        span_note := format('since %s (%s)',
          COALESCE(plan.origin, 'approval'), substr(plan.executed_at, 1, 10));
        IF plan.kind = 'followup' THEN
          since_ts := clara_safe_ts(plan.due_at) - make_interval(days => 30);
          IF since_ts IS NULL THEN
            RAISE EXCEPTION 'unparseable due_at: %', plan.due_at;
          END IF;
          span_note := format(
            'in the month after the measurement window closed (keep-listening read; clock from %s %s)',
            COALESCE(plan.origin, 'approval'), substr(plan.executed_at, 1, 10));
        END IF;
      END IF;

      IF journey_n = 'theme' THEN
        -- Tags only exist after triage enrichment: a window holding unenriched
        -- signals cannot be read honestly (mirrors
        -- measurement_scheduler.unenriched_in_window).
        SELECT count(*) INTO unenriched
        FROM clara_signals s
        WHERE NOT coalesce((s.payload->>'enriched')::boolean, false)
          AND clara_safe_ts(s.payload->>'timestamp') BETWEEN since_ts AND until_ts;
        IF unenriched > 0 THEN
          UPDATE clara_measurement_plans
            SET note = format(
              '%s in-window signals not yet enriched — run triage before this theme can be measured',
              unenriched)
            WHERE id = plan.id;
          skipped := skipped + 1;
          CONTINUE;
        END IF;
        SELECT count(*) INTO sample
        FROM clara_signals s
        WHERE EXISTS (
                SELECT 1
                FROM jsonb_array_elements_text(
                  CASE WHEN jsonb_typeof(s.payload->'tags') = 'array'
                       THEN s.payload->'tags' ELSE '[]'::jsonb END) AS t(tag)
                WHERE btrim(lower(replace(t.tag, '_', ' '))) = stage_n)
          AND clara_safe_ts(s.payload->>'timestamp') BETWEEN since_ts AND until_ts;
      ELSIF journey_n = 'unknown journey' AND stage_n LIKE '% feedback' THEN
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
          AND clara_safe_ts(s.payload->>'timestamp') BETWEEN since_ts AND until_ts;
      ELSE
        SELECT count(*) INTO sample
        FROM clara_signals s
        WHERE btrim(lower(replace(s.payload->>'journey', '_', ' '))) = journey_n
          AND btrim(lower(replace(s.payload->>'journey_stage', '_', ' '))) = stage_n
          AND clara_safe_ts(s.payload->>'timestamp') BETWEEN since_ts AND until_ts;
      END IF;

      elapsed_days := GREATEST(EXTRACT(EPOCH FROM (until_ts - since_ts)) / 86400.0, 1.0);
      rate := trim_scale(round((sample / elapsed_days)::numeric, 4));

      -- The latest reading on record: a reading covering a later observation
      -- interval is never displaced (mirrors workflow.assert_measurement_not_stale).
      SELECT clara_safe_ts(payload->>'measured_at'), clara_safe_ts(payload->>'observation_end')
        INTO existing_measured_at, existing_observation_end
      FROM clara_workflow_records
      WHERE record_type = 'outcome' AND problem_id = plan.problem_id
      ORDER BY created_at DESC, record_id DESC
      LIMIT 1;
      IF fixed_interval AND existing_observation_end IS NOT NULL
         AND until_ts < existing_observation_end THEN
        UPDATE clara_measurement_plans
          SET status = 'blocked',
              note = 'A reading covering a later observation interval already exists for this problem'
          WHERE id = plan.id;
        skipped := skipped + 1;
        CONTINUE;
      END IF;
      IF existing_measured_at IS NOT NULL AND _now < existing_measured_at THEN
        RAISE EXCEPTION 'a newer measurement already exists';
      END IF;

      measured_at_str := to_char(_now AT TIME ZONE 'utc', 'YYYY-MM-DD"T"HH24:MI:SS.US') || 'Z';

      INSERT INTO clara_workflow_records (record_type, record_id, problem_id, tenant_id, payload)
      VALUES (
        'outcome',
        plan.problem_id || ':' || metric || ':' || measured_at_str || ':'
          || lpad(plan.id::text, 12, '0'),
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
          'checkpoint_kind', plan.kind,
          'plan_id', plan.id,
          'execution_id', plan.execution_id,
          -- The terms the reading was scored under: the plan's frozen
          -- snapshot (or the deterministically linked current contract).
          'contract_revision', COALESCE((terms->>'revision')::int, 1),
          'contract_snapshot', terms,
          'clock_origin', COALESCE(plan.origin, 'approval'),
          'clock_origin_at', plan.executed_at,
          -- The interval the reading covers; a legacy open-ended read says so
          -- through a null end.
          'observation_start', CASE WHEN fixed_interval THEN plan.observation_start
                                    ELSE to_char(since_ts AT TIME ZONE 'utc', 'YYYY-MM-DD"T"HH24:MI:SS.US') || 'Z' END,
          'observation_end', CASE WHEN fixed_interval THEN plan.observation_end ELSE NULL END
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
        'problem_id', plan.problem_id, 'executed_at', plan.executed_at, 'kind', plan.kind,
        'observation_end', CASE WHEN fixed_interval THEN plan.observation_end ELSE NULL END);

      -- Loop verdict on the closing checkpoints, under the frozen terms
      -- (outcome_engine.outcome_status, decrease direction: signal-rate
      -- metrics are complaint-style).
      IF plan.kind IN ('window', 'followup') THEN
        baseline := (terms->>'baseline')::numeric;
        target := (terms->>'success_threshold')::numeric;
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
                                       'success_threshold', target,
                                       'contract_revision', COALESCE((terms->>'revision')::int, 1),
                                       'observation_start', CASE WHEN fixed_interval THEN plan.observation_start ELSE NULL END,
                                       'observation_end', CASE WHEN fixed_interval THEN plan.observation_end ELSE NULL END,
                                       'real_data_source', true));
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
    'loop_closed', loop_closed, 'fix_did_not_land', fix_did_not_land,
    'processed', processed);
END;
$$;
