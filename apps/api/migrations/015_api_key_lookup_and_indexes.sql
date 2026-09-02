-- 015: API keys resolvable across workspaces + indexes for the hot predicates.
--
-- (1) An X-Api-Key request carries no tenant until the key row is found: the
--     row itself names the workspace. Under the strict per-workspace policy the
--     lookup ran as workspace 1 and every key minted by another workspace was
--     a 401. The policy now admits a SELECT while the transaction-local flag
--     app.api_key_lookup is 'on' — set only inside PostgresApiKeyStore.verify,
--     for one exact-hash lookup, and gone with the transaction. Writes keep the
--     strict WITH CHECK. The API self-heals the same policy on boot.
DROP POLICY IF EXISTS clara_api_keys_workspace_isolation ON public.clara_api_keys;
CREATE POLICY clara_api_keys_workspace_isolation ON public.clara_api_keys
  USING (
    workspace_id = COALESCE(NULLIF(current_setting('app.workspace_id', true), ''), '1')::bigint
    OR current_setting('app.api_key_lookup', true) = 'on'
  )
  WITH CHECK (workspace_id = COALESCE(NULLIF(current_setting('app.workspace_id', true), ''), '1')::bigint);

-- (2) Indexes matching the queries the stores actually run (all RLS-filtered on
--     workspace_id first). Safe to re-run.
--     list_signals: ORDER BY payload->>'timestamp', signal_id
CREATE INDEX IF NOT EXISTS clara_signals_ws_ts_idx
  ON public.clara_signals (workspace_id, (payload->>'timestamp'), signal_id);
--     workflow snapshot load: ORDER BY created_at, record_id
CREATE INDEX IF NOT EXISTS clara_workflow_ws_created_idx
  ON public.clara_workflow_records (workspace_id, created_at, record_id);
--     schedule dedup: WHERE problem_id = ? AND kind = ? AND status IN (...)
CREATE INDEX IF NOT EXISTS clara_measurement_plans_problem_kind_idx
  ON public.clara_measurement_plans (workspace_id, problem_id, kind, status);
--     alert / verdict dedup: WHERE event_type = ? AND entity_id = ?
CREATE INDEX IF NOT EXISTS clara_telemetry_type_entity_idx
  ON public.clara_telemetry (workspace_id, event_type, entity_id);
