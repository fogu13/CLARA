# CLARA — Deployment Guide

## Production (current): Hetzner VPS + Vercel — since July 2026

- API: https://api.clara.odradekai.com — FastAPI in Docker on a Hetzner VPS behind Caddy (auto-TLS)
- Frontend: https://clara.odradekai.com — Next.js on Vercel (DNS: CNAME to Vercel; clara-theta-nine.vercel.app also serves); `NEXT_PUBLIC_API_URL=https://api.clara.odradekai.com`
- DB: Supabase Postgres via the session pooler; Supabase Auth Site URL = the frontend URL
- Server layout: `/opt/stacks/caddy/` (Caddyfile: `api.clara.odradekai.com { reverse_proxy clara-api:8000 }`) and `/opt/stacks/clara/` (compose + `.env` + repo clone at `./repo`)
- Compose: builds `./repo/apps/api`, joins the shared external `proxy` network (`external: true` is required — omitting it silently aborts the stack), publishes no ports (Caddy is the only public entry), sets `CLARA_REPO_ROOT=/app` via `environment:`, mounts `./repo/data` read-only at `/app/data`
- `.env` on the server (chmod 600): `DATABASE_URL` (pooler string), `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `CLARA_REQUIRE_AUTH=true`, `AI_*` vars (defaults are Mistral: `mistral-small-latest` / `mistral-embed` / `AI_EMBED_DIM=0`; set all three explicitly when using another provider), and `APP_CORS_ORIGINS=https://clara.odradekai.com,https://clara-theta-nine.vercel.app,http://localhost:3000`
- Also in `.env` (Jul 2026 additions): `CLARA_CONFIG_SECRET_KEY` (Fernet key — connector secrets encrypted at rest; **back the key up**: losing it means re-entering connector credentials), optional `CLARA_SMTP_*` (weekly digest email; recipient = workspace notification email), and later `CLARA_REQUIRE_AAL2=true` once every user has enrolled MFA
- Sep 2026 additions: `CLARA_AI_REQUIRE_EU=true` (fail-closed data residency — a non-EU or unrecognised AI/embeddings/Langfuse host refuses to boot and cannot be saved from Settings; allowlist a private EU gateway via `CLARA_AI_EU_HOSTS`), `CLARA_TRIAGE_CHECKPOINTER=auto` (PostgresSaver: paused triage approvals survive restarts; `memory` opts out). The image now runs as an unprivileged user with a Docker `HEALTHCHECK` on `/health`; `GET /ready` is the deep probe (DB round-trip + residency) for Caddy/uptime checks
- Vercel production env (not previews): `NEXT_PUBLIC_COOKIE_AUTH=1` + `AUTH_COOKIE_DOMAIN=clara.odradekai.com` (HttpOnly cookie sessions); `NEXT_PUBLIC_LEGAL_PAGES=1` publishes `/legal/*` + the launch surface AFTER legal review (fail-closed: DRAFT-marked docs never publish)

Deploy:

1. Locally: commit + `git push origin HEAD:main`
2. Server: `cd /opt/stacks/clara/repo && git pull`
3. `cd /opt/stacks/clara && docker compose up -d --build`
4. Verify: `python3 scripts/live_smoke.py` from any machine → expect **22/22** checks OK (INFO rows do not count; checks landing claims, security headers on web+API, fail-closed auth, cookie routes, liveness `/health`, readiness `/ready`, model-card endpoint, swagger off; read-only). A `/ready → 404` with `/health → 200` means the running image predates the September 2026 readiness route (commit 01ced20): rebuild with step 3, it is not a Caddy or DB fault.

Notes:

- `.env` changes need `docker compose up -d --force-recreate` — a plain `restart` does not reload env
- Caddyfile changes: `docker exec caddy caddy reload --config /etc/caddy/Caddyfile`
- `NEXT_PUBLIC_*` vars are build-time → redeploy on Vercel after changing them
- `APP_CORS_ORIGINS` defaults to localhost-only; production must set it (legacy alias `API_CORS_ORIGINS`)
- `/` returns 404 by design — the health endpoint is `/health`
- Server access, DNS and backup details are deliberately kept out of this repo (owner's private notes)
- Uptime: `.github/workflows/uptime.yml` runs this smoke every 30 min from GitHub Actions (independent of both Vercel and the VPS); two consecutive failures open a "Production smoke failing" issue, auto-closed on recovery

---

## From-scratch setup guide (any host)

The steps below reproduce the full stack from zero. Render-specific steps are historical — the
Render service was decommissioned in July 2026 (production runs on the VPS above); any Docker
host or PaaS slots into Step 3.

## Architecture

```
User → Vercel (Next.js frontend)
         ↓ API calls
       Docker host (FastAPI backend)
         ↓ psycopg
       Supabase (Postgres + Auth + pgvector)
         ↑ optional
       Langfuse (self-hosted or cloud)
```

## Step 1 — Push to GitHub

```bash
cd /path/to/CLARA
git remote add origin git@github.com:YOUR_USERNAME/clara.git
git push -u origin main
```

## Step 2 — Create Supabase project

1. Go to https://supabase.com → New Project
2. Choose **EU Central (Frankfurt)** region (GDPR data residency)
3. Set a strong database password
4. Wait for provisioning (~2 min)
5. Note these from **Project Settings → API**:
   - Project URL: `https://XXXXX.supabase.co`
   - Service Role Key: `eyJ...`
   - From **Settings → API → JWT Settings**: JWT Secret
6. From **Connect** (top bar) → **Session pooler**, copy the IPv4 connection string for
   `DATABASE_URL`:
   `postgresql://postgres.PROJECT_REF:PASSWORD@aws-0-<region>.pooler.supabase.com:5432/postgres`
   ⚠️ Use the **pooler**, not the direct `db.<ref>.supabase.co` host — direct is IPv6-only and
   Render's free tier is IPv4-only.
7. Run migrations in the **SQL Editor in this order** — note **004 runs BEFORE 003** (003's
   `unmapped_signals()` references a `workspace_id` column that 004 adds; 003 enables pgvector
   itself, so no separate "enable vector" step is needed):
   - `apps/api/migrations/001_supabase_postgres.sql`
   - `apps/api/migrations/002_workflow_tenant_retention.sql`
   - `apps/api/migrations/004_rls_workspace.sql`
   - `apps/api/migrations/003_pgvector_taxonomy.sql`
   - `apps/api/migrations/005_outcome_events_learnings.sql`
   - `apps/api/migrations/006_clara_workspace_id_default.sql`
   - `apps/api/migrations/007_rls_backfill_all_public.sql`
   - `apps/api/migrations/008_ops_stores.sql`
   - `apps/api/migrations/009_rls_gaps.sql`
   - `apps/api/migrations/010_api_keys.sql`
   - `apps/api/migrations/011_tenant_rls_enforcement.sql` — ⚠️ **deploy the matching API
     code first** (it sets the RLS GUCs per connection); applying 011 under an older API
     fail-closes every read. Afterwards verify with
     `DATABASE_URL=... python scripts/pg_parity_smoke.py` and check the SQL-editor output
     for pg_cron WARNINGs. Ad-hoc SQL-editor DML now needs
     `SELECT set_config('app.tenant_id','1',false), set_config('app.workspace_id','1',false);`
     first (RLS is FORCEd for the owner role too).
   - `apps/api/migrations/013_loop_closure.sql` — AI theme insights (`clara_theme_insights`),
     learning memory (`clara_learnings`, both RLS-forced) and the theme-aware
     `clara_run_due_measurements` that also records `loop_closed` / `fix_did_not_land`
     telemetry on window/follow-up checkpoints. The API self-heals the two tables and their
     RLS on boot; the function replacement only lives in this file, so apply it or theme
     contracts measure 0 signals under pg_cron. Safe to re-run.
   - `apps/api/migrations/015_api_key_lookup_and_indexes.sql` — API keys minted by any
     workspace authenticate (the key row names its workspace; the isolation policy admits
     the one exact-hash lookup inside `verify`), plus indexes for the signal ordering,
     workflow snapshot, plan dedup and alert dedup queries. Safe to re-run.
   - `apps/api/migrations/012_embedding_dim_1024.sql` — **only if `AI_EMBED_MODEL` is
     1024-dim (e.g. `mistral-embed`)**. 003 pins `taxonomy_nodes.embedding` to
     `vector(768)`; this retargets it. ⚠️ **It clears every stored embedding** — vectors
     from two models don't share a similarity space — so run `POST /taxonomy/bootstrap`
     afterwards to re-embed. Until you do, semantic mapping returns no matches (visible,
     not silently wrong); `signal_node_map` history is left intact. Idempotent: re-running
     once the column is `vector(1024)` is a no-op and won't wipe fresh vectors.
   _(For the existing **CLARA** project these are already applied via MCP — listed here for
   reproducibility.)_

## Step 3 — Deploy API (historical: Render; any Docker host or PaaS works)

1. Go to https://render.com → New → Web Service
2. Connect your GitHub repo
3. Settings:
   - **Root Directory:** `apps/api`
   - **Runtime:** Python 3
   - **Build Command:** `pip install -e ".[dev]"`
   - **Start Command:** `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
4. Add Environment Variables:

| Key | Value |
|---|---|
| `DATABASE_URL` | Session-pooler string from Step 2.6 (`...pooler.supabase.com:5432`) |
| `SUPABASE_URL` | `https://XXXXX.supabase.co` (drives JWKS verification of ES256 tokens) |
| `CLARA_REQUIRE_AUTH` | `true` (fail closed — refuse to boot if auth is unconfigured) |
| `CLARA_SEED_DEMO_DATA` | leave unset: defaults to off whenever `DATABASE_URL` is set, so an empty production DB never receives demo signals/problems (`1` only for a demo tenant) |
| `LOG_LEVEL` | `INFO` (app loggers; `DEBUG` for a support session, `WARNING` to quiet tick summaries) |
| `AI_BASE_URL` | `https://api.mistral.ai/v1` (chat) |
| `AI_API_KEY` | `<your Mistral API key>` |
| `AI_MODEL` | `mistral-small-latest` |
| `AI_EMBED_MODEL` | `mistral-embed` (the default). `gemini-embedding-001` is a Google/US model: refused under `CLARA_AI_REQUIRE_EU` |
| `AI_EMBED_DIM` | `0` for Mistral (the default; it 422s on the `dimensions` param); `768` for models that accept a dimension |
| `AI_EMBED_BASE_URL` | *optional* — only when `AI_BASE_URL` is a **chat-only** gateway. OpenCode Zen serves 61 chat models and 404s on `/embeddings`, so a Zen deployment needs e.g. `https://api.mistral.ai/v1` here while chat stays on `glm-5.2`. Unset = same host as chat |
| `AI_EMBED_API_KEY` | *optional* — required whenever `AI_EMBED_BASE_URL` points elsewhere; the chat key is never forwarded to a different provider |
| `APP_CORS_ORIGINS` | `https://clara-theta-nine.vercel.app` (your Vercel URL, set after Step 4) |

> `SUPABASE_JWT_SECRET` is **not** required — this project signs tokens with ES256
> (asymmetric), which the API verifies via the JWKS endpoint derived from `SUPABASE_URL`.
> Only set `SUPABASE_JWT_SECRET` if you switch the project to legacy HS256 signing.

5. Deploy → wait for build to complete
6. Test: `curl https://clara-api.onrender.com/health` → `{"status":"ok"}`

### Alternative: Railway

1. Go to https://railway.app → New Project → Deploy from GitHub
2. Select the repo, set root to `apps/api`
3. Railway auto-detects the Dockerfile
4. Add the same env vars
5. Deploy

## Step 4 — Deploy frontend to Vercel

1. Go to https://vercel.com → New Project → Import from GitHub
2. Settings:
   - **Root Directory:** `apps/web`
   - **Framework Preset:** Next.js
   - **Build Command:** `npm run build`
   - **Output Directory:** `.next`
3. Add Environment Variables:
   - `NEXT_PUBLIC_API_URL` = `https://clara-api.onrender.com` (your Render URL)
   - `NEXT_PUBLIC_SUPABASE_URL` = `https://XXXXX.supabase.co`
   - `NEXT_PUBLIC_SUPABASE_ANON_KEY` = the publishable/anon key (Supabase → Settings → API)
4. Deploy
5. After deploy, copy the Vercel URL (e.g. `https://clara-theta-nine.vercel.app`)
6. Go back to Render → Environment → update `APP_CORS_ORIGINS` to include the Vercel URL
7. Go to Supabase → Auth → URL Configuration:
   - Site URL: `https://clara-theta-nine.vercel.app`
   - Redirect URLs: `https://clara-theta-nine.vercel.app/**`

### Step 4.5 — Create the admin login

The frontend requires a Supabase login (no public signup). Create one admin account:

1. Supabase → **Authentication → Users → Add user** → set email + password, tick
   *Auto Confirm User*.
2. Grant it the owner role by setting its JWT `app_metadata` (the API reads `user_role` /
   `workspace_id` from there). In the **SQL Editor**:
   ```sql
   update auth.users
     set raw_app_meta_data = coalesce(raw_app_meta_data, '{}'::jsonb)
       || '{"user_role":"owner","workspace_id":1}'::jsonb
   where email = 'you@example.com';
   ```
3. Sign in at `https://clara-theta-nine.vercel.app/auth`.

## Step 5 — Verify end-to-end

1. Open your frontend URL at `/dashboard` (production: `https://clara.odradekai.com/dashboard`)
2. Navigate to **Integrations** → configure Zendesk/Jira/Slack
3. Go to **Sources** → import demo data or pull from Zendesk
4. Run the triage pipeline: `POST /triage/run` (or via the Signals page)
5. Check **Insights** for synthesized problems
6. Approve an action → verify Jira ticket created + Slack notification sent

## Optional — Langfuse (tracing + evals)

### Self-hosted (Docker):
```bash
cd infra
cp .env.example .env  # edit passwords
docker compose -f docker-compose.langfuse.yml up -d
# Access at http://localhost:3000
```

### Langfuse Cloud:
1. Go to https://cloud.langfuse.com → create project
2. Get public key + secret key
3. Set on Render: `LANGFUSE_BASE_URL`, `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`

## Cost (thesis demo)

| Service | Free tier | Notes |
|---|---|---|
| Supabase | 500MB DB, 50K MAU | Sufficient for demo |
| Vercel | Hobby (unlimited deploys) | |
| Render | Free (spins down after 15min) | Or $7/mo for always-on |
| Langfuse | Self-hosted free | Or cloud free tier |
| **Total** | **$0/month** | |

## Troubleshooting

| Problem | Fix |
|---|---|
| CORS error in browser | Check `APP_CORS_ORIGINS` includes your Vercel URL |
| Auth not working | Verify `SUPABASE_URL` is set — tokens are ES256, verified via JWKS; `SUPABASE_JWT_SECRET` is only for legacy HS256 |
| DB connection error | Check `DATABASE_URL` format; Supabase uses port 5432 |
| pgvector not found | Enable `vector` extension in Supabase dashboard |
| API cold start (Render free) | First request takes ~30s; upgrade to paid for always-on |
| LLM calls fail | Check `AI_BASE_URL` + `AI_API_KEY` + `AI_MODEL` are set |
| Insights search / taxonomy bootstrap 502s | An embeddings problem, not a chat one: `AI_EMBED_MODEL` defaults to `mistral-embed` and must be a model the embed host actually serves. The `/ask` error names the knob; `docker compose logs api \| grep "AI provider error"` has the provider's raw status. Check the split with `GET /system-config` → `ai_embed_base_url` |
| Embeddings 404 while chat works | The host is chat-only. Point `AI_EMBED_BASE_URL` + `AI_EMBED_API_KEY` at a provider that serves `/embeddings`; no `AI_EMBED_MODEL` value fixes a missing endpoint |
| **`.env` says one thing, `/system-config` says another** | A **Settings-page** AI config beats `.env` and survives restarts — see "Settings overrides env" below. Editing `.env` has no effect until it's cleared |
| Switching embed model | `taxonomy_nodes.embedding` is `vector(768)` (migration 003). A model with different dims needs a migration before taxonomy bootstrap; `/ask` is unaffected (it embeds in memory). **Also recalibrate every cosine threshold** — similarity distributions differ per embedder; run `python3 -m scripts.calibrate_embed_thresholds` and set the printed `ASK_MIN_SIMILARITY` / `TAXONOMY_*` / `CLUSTER_SEMANTIC_THRESHOLD` values in `.env` (for `mistral-embed`, measured 2026-08-08: 0.75 / 0.85 / 0.85 / 0.91 / 0.75 — the legacy defaults admit everything under it) |

## Settings overrides env (AI config) — check this first

**A base URL, model, embed model or API key saved on the Settings page wins over
`.env`, and keeps winning after a restart.** It is persisted as an `"ai"` entry in
the connector config store and re-applied on every boot (`app/main.py`, "AI runtime
config"). `docker compose up -d --force-recreate` does **not** clear it — it reloads
`.env`, then the override re-applies on top.

Ground truth is `GET /system-config`, not the file:

```
ai_base_url · ai_model · ai_embed_model · ai_embed_base_url
```

If those disagree with `.env`, the Settings entry is in control. To hand control back
to env, blank the Endpoint / Model / Embedding-model fields on the Settings page and
save. **Also set the API key field** — the route keeps the previously stored key when
that field is left empty (by design: edit forms would otherwise wipe it), so clearing
only the URL sends the *old* key to the *new* host.

Beware the preset buttons: a preset also sets the embed model, which then overrides
`AI_EMBED_MODEL` from env. On a split setup that posts the preset's model name to your
embed provider. (The non-EU "OpenCode Zen" preset was removed in Sep 2026; any stored
non-EU override is refused at boot and on save while `CLARA_AI_REQUIRE_EU` is on.)

Since Aug 2026 the `/ask` and Test-connection errors say when an override is active,
so you are not sent to edit a file that has no effect.

## Post-merge notes (18 Jul 2026)

- **Rate limiting** (PR #122): add `CLARA_RATE_LIMIT_PER_MINUTE=120` to the API env on the VPS and
  restart to activate; unset/0 keeps it off. Per-process fixed window; `/health` exempt.
- The model card serves the n=100 eval snapshot (urgency significance) after the next pull+restart;
  verify with `python3 scripts/live_smoke.py` as usual.

## User roles (fixing "requires an admin role" / 403 on connectors, api-keys, exports)

CLARA reads each user's role from the Supabase JWT `app_metadata.user_role`
(`owner` > `admin` > `editor` > `viewer`). A user with none set defaults to
**viewer** — read-only, and blocked from connector/API-key/export management.

- **Founder / to never get locked out:** set `CLARA_OWNER_EMAILS=your@email` in
  the API env and restart. That email is always `owner`, no DB write needed.
  Sign out and back in afterwards so a fresh token carries the role.
- **Other teammates:** grant a role in the DB (they re-login after):
  `DATABASE_URL=... python3 apps/api/scripts/set_user_role.py --email x@y.z --role admin`
  or one-off SQL in the Supabase SQL editor:
  `UPDATE auth.users SET raw_app_meta_data = coalesce(raw_app_meta_data,'{}'::jsonb) || '{"user_role":"admin"}'::jsonb WHERE email='x@y.z';`
