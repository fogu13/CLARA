-- 009: close the RLS gaps 007 missed — three tables were left without
-- row security (found during the live-DB parity session, 4 Jul 2026).

ALTER TABLE clara_journey_events ADD COLUMN IF NOT EXISTS workspace_id BIGINT NOT NULL DEFAULT 1;
ALTER TABLE clara_feedback_rules ADD COLUMN IF NOT EXISTS workspace_id BIGINT NOT NULL DEFAULT 1;

ALTER TABLE clara_journey_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE clara_feedback_rules ENABLE ROW LEVEL SECURITY;
ALTER TABLE clara_workspace_settings ENABLE ROW LEVEL SECURITY;

DO $$
DECLARE
    tbl TEXT;
BEGIN
    FOREACH tbl IN ARRAY ARRAY['clara_journey_events', 'clara_feedback_rules', 'clara_workspace_settings']
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
