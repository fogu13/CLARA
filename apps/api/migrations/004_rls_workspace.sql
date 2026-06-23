-- 004 — Workspaces + RLS multi-tenancy
-- Port of Elvis RLS pattern (reference/elvis/supabase/migrations/20260308202409_*.sql
-- and 20260621180000_per_user_workspace_*.sql), reconciled with Odradek_2's
-- migration 002 tenant_id pattern.
--
-- Fixes Odradek_2's acknowledged gap (apps/api/app/services/postgres.py:471 —
-- "workflow_records has no tenant_id yet; future RLS milestone adds DB tenant
-- boundaries").
--
-- Approach: workspace_id INTEGER as the primary tenant key (Elvis pattern).
-- RLS policies accept EITHER:
--   (a) current_setting('app.tenant_id', true) — set by FastAPI auth middleware
--       on the psycopg connection after JWT verification, OR
--   (b) the workspace_id claim in the Supabase JWT (for direct Supabase-client
--       access, e.g. from the Next.js frontend).
-- This keeps both access paths working.

-- ====== Utility function for updated_at ======
CREATE OR REPLACE FUNCTION public.update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql SET search_path = public;

-- ====== Workspaces ======
CREATE TABLE IF NOT EXISTS public.workspaces (
  id SERIAL PRIMARY KEY,
  name VARCHAR(200) NOT NULL,
  slug VARCHAR(100) UNIQUE NOT NULL,
  settings JSONB DEFAULT '{}',
  onboarded BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
ALTER TABLE public.workspaces ENABLE ROW LEVEL SECURITY;

-- ====== User Roles ======
CREATE TYPE IF NOT EXISTS public.app_role AS ENUM ('owner', 'admin', 'editor', 'viewer');

CREATE TABLE IF NOT EXISTS public.user_roles (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL,
  workspace_id INTEGER REFERENCES public.workspaces(id) ON DELETE CASCADE,
  role app_role NOT NULL,
  UNIQUE (user_id, workspace_id, role)
);
ALTER TABLE public.user_roles ENABLE ROW LEVEL SECURITY;

CREATE OR REPLACE FUNCTION public.has_role(_user_id UUID, _role app_role)
RETURNS BOOLEAN
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = public
AS $$
  SELECT EXISTS (
    SELECT 1 FROM public.user_roles WHERE user_id = _user_id AND role = _role
  )
$$;

-- ====== Profiles ======
CREATE TABLE IF NOT EXISTS public.profiles (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL UNIQUE,
  workspace_id INTEGER REFERENCES public.workspaces(id),
  email VARCHAR(255) NOT NULL,
  name VARCHAR(200),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own profile"
  ON public.profiles FOR SELECT
  USING (user_id::text = current_setting('app.user_id', true)
         OR user_id::text = (NULLIF(current_setting('request.jwt.claims', true), '')::jsonb ->> 'sub'));

CREATE POLICY "Users can update own profile"
  ON public.profiles FOR UPDATE
  USING (user_id::text = current_setting('app.user_id', true)
         OR user_id::text = (NULLIF(current_setting('request.jwt.claims', true), '')::jsonb ->> 'sub'));

CREATE POLICY "Users can insert own profile"
  ON public.profiles FOR INSERT
  WITH CHECK (user_id::text = current_setting('app.user_id', true)
              OR user_id::text = (NULLIF(current_setting('request.jwt.claims', true), '')::jsonb ->> 'sub'));

-- ====== Helper: unique workspace slug from email ======
CREATE OR REPLACE FUNCTION public.unique_workspace_slug(_email text)
RETURNS text
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
  base_slug text;
  final_slug text;
  suffix integer := 0;
BEGIN
  base_slug := regexp_replace(lower(split_part(coalesce(_email, ''), '@', 1)), '[^a-z0-9]+', '-', 'g');
  base_slug := trim(both '-' from base_slug);
  IF base_slug IS NULL OR base_slug = '' THEN
    base_slug := 'workspace';
  END IF;
  final_slug := base_slug;
  WHILE EXISTS (SELECT 1 FROM public.workspaces WHERE slug = final_slug) LOOP
    suffix := suffix + 1;
    final_slug := base_slug || '-' || suffix;
  END LOOP;
  RETURN final_slug;
END;
$$;

-- ====== Auto-create workspace + profile on signup ======
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
  new_workspace_id integer;
BEGIN
  INSERT INTO public.workspaces (name, slug)
  VALUES (
    coalesce(nullif(split_part(NEW.email, '@', 1), ''), 'My') || '''s Workspace',
    public.unique_workspace_slug(NEW.email)
  )
  RETURNING id INTO new_workspace_id;

  INSERT INTO public.profiles (user_id, email, workspace_id)
  VALUES (NEW.id, NEW.email, new_workspace_id);

  INSERT INTO public.user_roles (user_id, workspace_id, role)
  VALUES (NEW.id, new_workspace_id, 'owner');

  RETURN NEW;
END;
$$;

-- ====== Add workspace_id to all odradek_* tables ======
-- Default to a 'default' workspace so existing data is not orphaned.

DO $$
DECLARE
  default_ws_id integer;
BEGIN
  -- Ensure a default workspace exists for legacy data.
  INSERT INTO public.workspaces (name, slug)
  VALUES ('Default Workspace', 'default')
  ON CONFLICT (slug) DO NOTHING
  RETURNING id INTO default_ws_id;

  IF default_ws_id IS NULL THEN
    SELECT id INTO default_ws_id FROM public.workspaces WHERE slug = 'default';
  END IF;

  -- odradek_problems
  ALTER TABLE odradek_problems ADD COLUMN IF NOT EXISTS workspace_id INTEGER REFERENCES public.workspaces(id);
  UPDATE odradek_problems SET workspace_id = default_ws_id WHERE workspace_id IS NULL;
  ALTER TABLE odradek_problems ALTER COLUMN workspace_id SET NOT NULL;
  CREATE INDEX IF NOT EXISTS odradek_problems_workspace_idx ON odradek_problems(workspace_id);

  -- odradek_signals
  ALTER TABLE odradek_signals ADD COLUMN IF NOT EXISTS workspace_id INTEGER REFERENCES public.workspaces(id);
  UPDATE odradek_signals SET workspace_id = default_ws_id WHERE workspace_id IS NULL;
  ALTER TABLE odradek_signals ALTER COLUMN workspace_id SET NOT NULL;
  CREATE INDEX IF NOT EXISTS odradek_signals_workspace_idx ON odradek_signals(workspace_id);

  -- odradek_candidate_decisions
  ALTER TABLE odradek_candidate_decisions ADD COLUMN IF NOT EXISTS workspace_id INTEGER REFERENCES public.workspaces(id);
  UPDATE odradek_candidate_decisions SET workspace_id = default_ws_id WHERE workspace_id IS NULL;
  ALTER TABLE odradek_candidate_decisions ALTER COLUMN workspace_id SET NOT NULL;
  CREATE INDEX IF NOT EXISTS odradek_candidate_decisions_workspace_idx ON odradek_candidate_decisions(workspace_id);

  -- odradek_customer_context
  ALTER TABLE odradek_customer_context ADD COLUMN IF NOT EXISTS workspace_id INTEGER REFERENCES public.workspaces(id);
  UPDATE odradek_customer_context SET workspace_id = default_ws_id WHERE workspace_id IS NULL;
  ALTER TABLE odradek_customer_context ALTER COLUMN workspace_id SET NOT NULL;
  CREATE INDEX IF NOT EXISTS odradek_customer_context_workspace_idx ON odradek_customer_context(workspace_id);

  -- odradek_taxonomy_catalogs
  ALTER TABLE odradek_taxonomy_catalogs ADD COLUMN IF NOT EXISTS workspace_id INTEGER REFERENCES public.workspaces(id);
  UPDATE odradek_taxonomy_catalogs SET workspace_id = default_ws_id WHERE workspace_id IS NULL;
  ALTER TABLE odradek_taxonomy_catalogs ALTER COLUMN workspace_id SET NOT NULL;

  -- odradek_terminology_dictionary
  ALTER TABLE odradek_terminology_dictionary ADD COLUMN IF NOT EXISTS workspace_id INTEGER REFERENCES public.workspaces(id);
  UPDATE odradek_terminology_dictionary SET workspace_id = default_ws_id WHERE workspace_id IS NULL;
  ALTER TABLE odradek_terminology_dictionary ALTER COLUMN workspace_id SET NOT NULL;
END $$;

-- odradek_workflow_records already has tenant_id TEXT from migration 002.
-- Add workspace_id INTEGER alongside it (tenant_id stays for backward compat).
ALTER TABLE odradek_workflow_records ADD COLUMN IF NOT EXISTS workspace_id INTEGER REFERENCES public.workspaces(id);
UPDATE odradek_workflow_records SET workspace_id = (
  SELECT id FROM public.workspaces WHERE slug = 'default'
) WHERE workspace_id IS NULL;
ALTER TABLE odradek_workflow_records ALTER COLUMN workspace_id SET NOT NULL;
CREATE INDEX IF NOT EXISTS odradek_workflow_workspace_idx ON odradek_workflow_records(workspace_id, problem_id, record_type);

-- ====== RLS policies on all odradek_* tables ======
-- Dual check: app.tenant_id (set by FastAPI middleware) OR JWT claim (Supabase client).

CREATE OR REPLACE FUNCTION public.current_workspace_id()
RETURNS INTEGER
LANGUAGE sql
STABLE
AS $$
  SELECT NULLIF(current_setting('app.tenant_id', true), '')::int
  UNION ALL
  SELECT (NULLIF(current_setting('request.jwt.claims', true), '')::jsonb ->> 'workspace_id')::int
  LIMIT 1
$$;

-- Helper: workspace_id matches the current tenant context.
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
$$;

-- Enable RLS + apply uniform policy on each table.
DO $$
DECLARE
  tbl text;
BEGIN
  FOR tbl IN
    SELECT unnest(ARRAY[
      'odradek_problems',
      'odradek_signals',
      'odradek_candidate_decisions',
      'odradek_customer_context',
      'odradek_workflow_records',
      'odradek_taxonomy_catalogs',
      'odradek_terminology_dictionary'
    ])
  LOOP
    EXECUTE format('ALTER TABLE %I ENABLE ROW LEVEL SECURITY', tbl);

    EXECUTE format('DROP POLICY IF EXISTS %I ON %I', tbl || '_workspace_isolation', tbl);

    EXECUTE format(
      'CREATE POLICY %I ON %I
        FOR ALL
        USING (public.is_current_workspace(workspace_id))
        WITH CHECK (public.is_current_workspace(workspace_id))',
      tbl || '_workspace_isolation', tbl
    );
  END LOOP;
END $$;

-- ====== updated_at triggers ======
DO $$
DECLARE
  tbl text;
BEGIN
  FOR tbl IN
    SELECT unnest(ARRAY[
      'odradek_problems', 'odradek_signals', 'odradek_candidate_decisions',
      'odradek_customer_context', 'odradek_workflow_records',
      'odradek_taxonomy_catalogs', 'odradek_terminology_dictionary'
    ])
  LOOP
    EXECUTE format(
      'DROP TRIGGER IF EXISTS set_updated_at ON %I;'
      'CREATE TRIGGER set_updated_at BEFORE UPDATE ON %I
         FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column()',
      tbl, tbl
    );
  END LOOP;
END $$;
