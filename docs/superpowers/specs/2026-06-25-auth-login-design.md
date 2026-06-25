# Spec — Single seeded admin login + secure cloud deploy

**Date:** 2026-06-25
**Status:** approved (design)
**Goal:** Make CLARA deployable with API auth enabled, by giving the Next.js frontend a
real login so it can obtain and send a Supabase JWT. Scope: one pre-seeded admin account
(no public signup, no OAuth). Single-tenant (workspace 1).

## Problem

- The frontend auth page (`apps/web/app/(auth)/auth/page.tsx`) is a stub; nothing sets the
  `clara_access_token` that `apps/web/lib/client-api.ts` reads. With API auth enabled, every
  write returns 401.
- The API (`apps/api/app/auth.py`) reads `user_role`/`workspace_id` from the JWT, but standard
  Supabase access tokens don't carry those top-level claims.
- Migrations 003–005 made `workspace_id NOT NULL` on every `clara_*` table, but the API's
  Postgres stores (`apps/api/app/services/postgres.py`) insert only `(id, payload)` — so the
  API would fail its startup seed insert against the migrated DB.

## Approach

### 1. Frontend login (`apps/web`)
- Add `@supabase/supabase-js`. New `apps/web/lib/supabase.ts` creates a browser client from
  `NEXT_PUBLIC_SUPABASE_URL` + `NEXT_PUBLIC_SUPABASE_ANON_KEY`.
- Replace the stub `(auth)/auth/page.tsx` with an email+password form calling
  `supabase.auth.signInWithPassword`. On success, write `session.access_token` to
  `localStorage['clara_access_token']` (the key `client-api.ts` already reads) and redirect to
  `/dashboard`. Surface auth errors inline.
- `(dashboard)/layout.tsx`: redirect to `/auth` when there is no Supabase session; add a
  sign-out control (`supabase.auth.signOut()` + clear the token) in the app header.
- Keep the token in sync with the Supabase session (write on `onAuthStateChange`).

### 2. API role/workspace from `app_metadata` (`apps/api/app/auth.py`)
- After verifying the JWT (HS256, existing path), read role/workspace from the verified
  claims' `app_metadata` first, then fall back to top-level claims, then defaults:
  `role = app_metadata.user_role or user_role or "viewer"`,
  `workspace_id = app_metadata.workspace_id or workspace_id or 1`.
- `app_metadata` is admin-controlled (not user-editable), so this is safe to trust. No
  Supabase auth hook and no per-request DB query needed.

### 3. Seed the admin (Supabase, via MCP)
- The user creates the auth user (email + password) in the Supabase dashboard (password never
  shared). Then, via `execute_sql`, set
  `raw_app_meta_data = raw_app_meta_data || '{"user_role":"owner","workspace_id":1}'` on that
  `auth.users` row. (Optionally insert matching `public.profiles` + `public.user_roles` rows.)

### 4. DB write compatibility (Supabase, via MCP)
- `ALTER TABLE <clara_*> ALTER COLUMN workspace_id SET DEFAULT 1` on all seven `clara_*`
  tables so the not-yet-workspace-aware API inserts land in workspace 1.
- **Deliberate single-tenant simplification.** Full per-tenant writes (API sets `workspace_id`
  from the authenticated user) are the deferred tenant-isolation work (review item #3).

### 5. Deploy wiring
- **Render** env: `DATABASE_URL` (session pooler, IPv4), `SUPABASE_JWT_SECRET`, `SUPABASE_URL`,
  `SUPABASE_SERVICE_ROLE_KEY`, `CLARA_REQUIRE_AUTH=true`, `AI_BASE_URL=https://api.mistral.ai/v1`,
  `AI_MODEL=mistral-small-latest`, `AI_API_KEY`, `APP_CORS_ORIGINS=<vercel domain>`.
- **Vercel** env: `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY`,
  `NEXT_PUBLIC_API_URL=<render url>`.
- Update `DEPLOY.md`, `apps/api/render.yaml`, `.env.example` files; fix migration 003's
  dollar-quote/ordering bugs in the repo to match what was applied.

## Risks / open checks
- **JWT signing alg.** API verifies HS256 with `SUPABASE_JWT_SECRET`. If the project signs
  access tokens with asymmetric keys (ES256), HS256 verification fails. The anon key is HS256
  (legacy), suggesting HS256 is active — **verify by decoding a real login token** before relying
  on it. If asymmetric, add JWKS verification to `auth.py` (extra step).
- `mistral-embed` is 1024-dim vs `vector(768)`; not exercised by `/triage/run`, so not blocking.

## Testing / verification
- API unit: `get_current_user` resolves `owner`/`workspace_id` from a JWT whose `app_metadata`
  carries them (extend `apps/api/app/tests/test_auth.py`).
- Manual: sign in at `/auth` → token stored → `/dashboard` loads live data; import a demo
  dataset (write path) succeeds (workspace_id default applies); `POST /triage/run` → 200 with
  Mistral; signed-out user is redirected to `/auth`.
- `npm run check` (ruff F + pytest + web lint/build) green.

## Out of scope
Public signup, OAuth, password reset, multi-tenant writes, JWKS/asymmetric JWT (unless the
alg check requires it).
