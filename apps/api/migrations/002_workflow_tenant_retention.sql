ALTER TABLE odradek_workflow_records
    ADD COLUMN IF NOT EXISTS tenant_id TEXT NOT NULL DEFAULT 'legacy';

ALTER TABLE odradek_workflow_records
    ADD COLUMN IF NOT EXISTS retention_expires_at TIMESTAMPTZ;

CREATE INDEX IF NOT EXISTS odradek_workflow_tenant_problem_idx
    ON odradek_workflow_records (tenant_id, problem_id, record_type);

ALTER TABLE odradek_workflow_records ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS odradek_workflow_records_tenant_isolation
    ON odradek_workflow_records;

CREATE POLICY odradek_workflow_records_tenant_isolation
    ON odradek_workflow_records
    USING (
        tenant_id = current_setting('app.tenant_id', true)
        OR tenant_id = (
            NULLIF(current_setting('request.jwt.claims', true), '')::jsonb
            ->> 'tenant_id'
        )
    )
    WITH CHECK (
        tenant_id = current_setting('app.tenant_id', true)
        OR tenant_id = (
            NULLIF(current_setting('request.jwt.claims', true), '')::jsonb
            ->> 'tenant_id'
        )
    );
