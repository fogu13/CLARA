
-- Integrations table: stores connected business tool configs per workspace
CREATE TABLE IF NOT EXISTS public.integrations (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  workspace_id integer NOT NULL REFERENCES public.workspaces(id) ON DELETE CASCADE,
  tool_type character varying NOT NULL,
  name character varying NOT NULL,
  config jsonb NOT NULL DEFAULT '{}',
  enabled boolean NOT NULL DEFAULT true,
  connected_at timestamp with time zone NOT NULL DEFAULT now(),
  last_synced_at timestamp with time zone,
  sync_status character varying NOT NULL DEFAULT 'idle',
  sync_error text,
  created_at timestamp with time zone NOT NULL DEFAULT now(),
  updated_at timestamp with time zone NOT NULL DEFAULT now()
);

-- API keys table: user-managed external API keys
CREATE TABLE IF NOT EXISTS public.api_keys (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  workspace_id integer NOT NULL REFERENCES public.workspaces(id) ON DELETE CASCADE,
  name character varying NOT NULL,
  key_prefix character varying NOT NULL,
  key_hash character varying NOT NULL,
  description text,
  last_used_at timestamp with time zone,
  created_at timestamp with time zone NOT NULL DEFAULT now(),
  expires_at timestamp with time zone
);

-- RLS for integrations
ALTER TABLE public.integrations ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can manage integrations in their workspace"
  ON public.integrations FOR ALL
  USING (workspace_id IN (
    SELECT profiles.workspace_id FROM profiles WHERE profiles.user_id = auth.uid()
  ));

-- RLS for api_keys
ALTER TABLE public.api_keys ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can manage api_keys in their workspace"
  ON public.api_keys FOR ALL
  USING (workspace_id IN (
    SELECT profiles.workspace_id FROM profiles WHERE profiles.user_id = auth.uid()
  ));
