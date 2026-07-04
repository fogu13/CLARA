-- 008: Postgres parity for the ops stores that only existed on SQLite.
-- Without these, a Render deploy keeps telemetry, measurement schedules and
-- connector configs on EPHEMERAL disk: every redeploy silently wipes them.
-- RLS follows the 004/007 workspace pattern.

CREATE TABLE IF NOT EXISTS clara_telemetry (
    id BIGSERIAL PRIMARY KEY,
    workspace_id BIGINT NOT NULL DEFAULT 1,
    event_type TEXT NOT NULL,
    entity_id TEXT,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS clara_telemetry_type_idx ON clara_telemetry (event_type, created_at);

CREATE TABLE IF NOT EXISTS clara_measurement_plans (
    id BIGSERIAL PRIMARY KEY,
    workspace_id BIGINT NOT NULL DEFAULT 1,
    problem_id TEXT NOT NULL,
    execution_id TEXT NOT NULL,
    executed_at TEXT NOT NULL,
    due_at TEXT NOT NULL,
    kind TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    note TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS clara_measurement_plans_due_idx ON clara_measurement_plans (status, due_at);

CREATE TABLE IF NOT EXISTS clara_connector_configs (
    connector_type TEXT PRIMARY KEY,
    workspace_id BIGINT NOT NULL DEFAULT 1,
    payload JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

ALTER TABLE clara_telemetry ENABLE ROW LEVEL SECURITY;
ALTER TABLE clara_measurement_plans ENABLE ROW LEVEL SECURITY;
ALTER TABLE clara_connector_configs ENABLE ROW LEVEL SECURITY;

DO $$
DECLARE
    tbl TEXT;
BEGIN
    FOREACH tbl IN ARRAY ARRAY['clara_telemetry', 'clara_measurement_plans', 'clara_connector_configs']
    LOOP
        EXECUTE format('DROP POLICY IF EXISTS %I_workspace_isolation ON %I', tbl, tbl);
        EXECUTE format(
            'CREATE POLICY %I_workspace_isolation ON %I'
            ' USING (workspace_id = COALESCE(NULLIF(current_setting(''app.workspace_id'', true), ''''), ''1'')::bigint)'
            ' WITH CHECK (workspace_id = COALESCE(NULLIF(current_setting(''app.workspace_id'', true), ''''), ''1'')::bigint)',
            tbl, tbl
        );
    END LOOP;
END $$;
