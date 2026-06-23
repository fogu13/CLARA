-- 004 — Workspace + RLS multi-tenancy (port of Elvis RLS pattern)
-- Source: reference/elvis/supabase/migrations/20260308202409_*.sql (RLS policies)
--         reference/elvis/supabase/migrations/20260621180000_per_user_workspace_*.sql
--
-- Phase 0 target. Fixes Odradek_2's acknowledged gap
-- (apps/api/app/services/postgres.py:471 — "workflow_records has no tenant_id yet").
--
-- TODO(Phase 0):
--   - workspaces table (id, name, slug, settings JSONB, onboarded bool)
--   - profiles table (user_id -> workspace_id link)
--   - user_roles table (app_role enum owner/admin/editor/viewer)
--   - add workspace_id column to every odradek_* table
--   - enable ROW LEVEL SECURITY on every table
--   - RLS policy: workspace_id IN (SELECT workspace_id FROM profiles WHERE user_id = auth.uid())
--   - handle_new_user() trigger: auto-create isolated workspace at signup

-- Placeholder so the migration is idempotent and safe to apply during scaffolding.
SELECT 1;
