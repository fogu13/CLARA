-- 007 — Backfill RLS on every public table (security: rls_disabled_in_public)
--
-- Supabase's advisor flags any table in the `public` schema without Row-Level
-- Security: because PostgREST exposes `public` over the project's anon key,
-- "anyone with the URL can read/edit/delete" such a table.
--
-- Migration 004 already enabled RLS on the known clara_*/public tables, but the
-- live project can still carry tables 004 never reached (created out-of-band, or
-- inherited from the original Lovable/`reference/elvis` schema). This migration is
-- a self-contained, idempotent CATCH-ALL: it enables RLS on EVERY ordinary
-- `public` table that lacks it and re-applies the standard workspace-isolation
-- policy wherever a `workspace_id` column exists.
--
-- Why this is safe for the running app:
--   * The FastAPI backend connects as the table OWNER (`postgres`) and Supabase's
--     `service_role` has BYPASSRLS — neither is affected by RLS (no FORCE here).
--   * The Next.js frontend uses Supabase only for AUTH (GoTrue /auth/v1), never
--     the data API, so it never reads these tables over the anon key.
--   * Net effect: the anon/authenticated PostgREST roles are denied (the hole is
--     closed) while every legitimate access path keeps working.
--
-- Apply to production: run this file in the Supabase SQL Editor (or
--   `psql "$DATABASE_URL" -f 007_rls_backfill_all_public.sql`). Idempotent.

-- Tenant predicate (CREATE OR REPLACE so this migration stands alone even if 004
-- was never applied to the target database). Matches migration 004 exactly.
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

DO $$
DECLARE
  r RECORD;
BEGIN
  FOR r IN
    SELECT c.relname AS tbl,
           EXISTS (
             SELECT 1
             FROM information_schema.columns col
             WHERE col.table_schema = 'public'
               AND col.table_name = c.relname
               AND col.column_name = 'workspace_id'
           ) AS has_workspace_id
    FROM pg_class c
    JOIN pg_namespace n ON n.oid = c.relnamespace
    WHERE n.nspname = 'public'
      AND c.relkind = 'r'         -- ordinary tables only (not views/sequences)
      AND NOT c.relrowsecurity    -- only those still missing RLS
  LOOP
    EXECUTE format('ALTER TABLE public.%I ENABLE ROW LEVEL SECURITY', r.tbl);

    IF r.has_workspace_id THEN
      -- Tenant-scoped access for the JWT path; backend/owner bypasses anyway.
      EXECUTE format('DROP POLICY IF EXISTS %I ON public.%I',
                     r.tbl || '_workspace_isolation', r.tbl);
      EXECUTE format(
        'CREATE POLICY %I ON public.%I
           FOR ALL
           USING (public.is_current_workspace(workspace_id))
           WITH CHECK (public.is_current_workspace(workspace_id))',
        r.tbl || '_workspace_isolation', r.tbl
      );
      RAISE NOTICE 'RLS enabled + workspace policy on public.%', r.tbl;
    ELSE
      -- No tenant column: RLS with no policy denies the anon/authenticated roles
      -- outright (owner/service_role still bypass). Closes the exposure.
      RAISE NOTICE 'RLS enabled (deny-all to anon) on public.%', r.tbl;
    END IF;
  END LOOP;
END $$;

-- Verification (run after; should return ZERO rows):
--   SELECT relname FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
--   WHERE n.nspname='public' AND c.relkind='r' AND NOT c.relrowsecurity;
