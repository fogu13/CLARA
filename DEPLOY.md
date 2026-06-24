# CLARA — Deployment Guide

## Architecture

```
User → Vercel (Next.js frontend)
         ↓ API calls
       Render/Railway (FastAPI backend)
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
6. From **Settings → Database**: Connection string
   `postgresql://postgres:PASSWORD@db.XXXXX.supabase.co:5432/postgres`
7. Enable pgvector: **Dashboard → Database → Extensions → vector → Enable**
8. Run migrations in **SQL Editor** (in order):
   - `apps/api/migrations/001_supabase_postgres.sql`
   - `apps/api/migrations/002_workflow_tenant_retention.sql`
   - `apps/api/migrations/003_pgvector_taxonomy.sql`
   - `apps/api/migrations/004_rls_workspace.sql`
   - `apps/api/migrations/005_outcome_events_learnings.sql`

## Step 3 — Deploy API to Render

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
| `DATABASE_URL` | `postgresql://postgres:...@db.XXXXX.supabase.co:5432/postgres` |
| `SUPABASE_JWT_SECRET` | `<JWT secret from Supabase>` |
| `SUPABASE_URL` | `https://XXXXX.supabase.co` |
| `SUPABASE_SERVICE_ROLE_KEY` | `<service role key>` |
| `AI_BASE_URL` | `https://api.openai.com/v1` (or `http://localhost:11434/v1` for Ollama) |
| `AI_API_KEY` | `sk-...` (leave empty for local Ollama) |
| `AI_MODEL` | `gpt-4o-mini` (or `llama3.1` for Ollama) |
| `APP_CORS_ORIGINS` | `https://clara.vercel.app` (add your Vercel URL after Step 4) |

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
3. Add Environment Variable:
   - `NEXT_PUBLIC_API_URL` = `https://clara-api.onrender.com` (your Render URL)
4. Deploy
5. After deploy, copy the Vercel URL (e.g. `https://clara.vercel.app`)
6. Go back to Render → Environment → update `APP_CORS_ORIGINS` to include the Vercel URL
7. Go to Supabase → Auth → URL Configuration:
   - Site URL: `https://clara.vercel.app`
   - Redirect URLs: `https://clara.vercel.app/**`

## Step 5 — Verify end-to-end

1. Open `https://clara.vercel.app/dashboard`
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
| Auth not working | Verify `SUPABASE_JWT_SECRET` matches Supabase project |
| DB connection error | Check `DATABASE_URL` format; Supabase uses port 5432 |
| pgvector not found | Enable `vector` extension in Supabase dashboard |
| API cold start (Render free) | First request takes ~30s; upgrade to paid for always-on |
| LLM calls fail | Check `AI_BASE_URL` + `AI_API_KEY` + `AI_MODEL` are set |
