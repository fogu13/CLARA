-- 010: API keys for machine-to-machine access (hash-only storage).
CREATE TABLE IF NOT EXISTS clara_api_keys (
    id BIGSERIAL PRIMARY KEY,
    workspace_id BIGINT NOT NULL DEFAULT 1,
    name TEXT NOT NULL,
    role TEXT NOT NULL,
    key_hash TEXT NOT NULL UNIQUE,
    key_prefix TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    revoked_at TIMESTAMPTZ
);
ALTER TABLE clara_api_keys ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS clara_api_keys_workspace_isolation ON clara_api_keys;
CREATE POLICY clara_api_keys_workspace_isolation ON clara_api_keys
  USING (workspace_id = COALESCE(NULLIF(current_setting('app.workspace_id', true), ''), '1')::bigint)
  WITH CHECK (workspace_id = COALESCE(NULLIF(current_setting('app.workspace_id', true), ''), '1')::bigint);
