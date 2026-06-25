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
- **No SDK dependency** (CI runs `npm ci`; adding a dep without regenerating the lockfile
  would break the build, and sign-in is one POST). `apps/web/lib/auth-client.ts` calls Supabase
  GoTrue directly: `signIn` POSTs `{SUPABASE_URL}/auth/v1/token?grant_type=password` with the
  anon key, stores `access_token` in `localStorage['clara_access_token']` (the key
  `client-api.ts` already reads); `signOut` clears it; `isAuthenticated` checks token presence +
  `exp`. Config from `NEXT_PUBLIC_SUPABASE_URL` + `NEXT_PUBLIC_SUPABASE_ANON_KEY`.
- Replace the stub `(auth)/auth/page.tsx` with an email+password form → `signIn` → redirect to
  `/dashboard`; errors shown inline.
- `components/auth/auth-guard.tsx` wraps `(dashboard)/layout.tsx`: redirects to `/auth` when
  auth is configured and there's no valid token; no-op when auth isn't configured (local dev).
- Sign-out control in the app header (`signOut` + redirect to `/auth`).

### 2. API JWT verification + role/workspace from `app_metadata` (`apps/api/app/auth.py`)
- **The project signs access tokens with ES256 (asymmetric JWT keys)** — confirmed via the
  JWKS endpoint. So `verify_token` routes on the token's `alg`: ES256/RS256 → verify against the
  Supabase JWKS (`{SUPABASE_URL}/auth/v1/.well-known/jwks.json`) using `jwt.PyJWKClient`; HS256 →
  verify with `SUPABASE_JWT_SECRET` (kept as a fallback for legacy/local). No shared secret is
  needed in ES256 mode. Requires `PyJWT[crypto]` (cryptography) for EC verification.
- `AUTH_ENABLED = bool(SUPABASE_JWT_SECRET or SUPABASE_URL)`.
- Read role/workspace from the verified claims' `app_metadata` first, then top-level, then
  defaults: `role = app_metadata.user_role or user_role or "viewer"`,
  `workspace_id = app_metadata.workspace_id or workspace_id or 1`. `app_metadata` is
  admin-controlled (not user-editable), so it is safe to trust; no Supabase auth hook needed.

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
- **JWT signing alg — RESOLVED.** Probed the JWKS endpoint: the project signs with ES256
  (asymmetric). Handled by JWKS verification in component 2. `SUPABASE_URL` is therefore required
  on the API (for the JWKS URL); `SUPABASE_JWT_SECRET` is optional.
- Verify at test time that a real signed-in token's `app_metadata` carries `user_role`/`workspace_id`.
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
