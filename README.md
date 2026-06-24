# CLARA

CLARA is a governed feedback-to-action platform for an MSc AI thesis and a
future EU-focused SaaS. It is a hybrid of two earlier builds:

- **Base:** CLARA_2 (Python/FastAPI + Next.js) — clean domain model,
  governance-by-design, 86 tests, CI.
- **Ported in:** Elvis_thesis_lovable's AI layer (provider-agnostic, local-first
  via Ollama/vLLM), semantic + adaptive taxonomy, 17-page UI, Supabase Auth +
  RLS multi-tenancy, EU AI Act + GDPR compliance checker.
- **New:** LangGraph agentic orchestration, a real connector layer
  (Zendesk in, Jira + Slack out), self-hosted Supabase + Langfuse.

See [docs/roadmap.md](./docs/roadmap.md) for the canonical phased product plan,
[PLAN.md](./PLAN.md) for architecture notes, and
[docs/hybrid-architecture.md](./docs/hybrid-architecture.md) for what came from
where. Elvis's source is preserved under `reference/elvis/` as a port reference.

> CLARA is the first build of a European Feedback-to-Outcome platform.

The initial product is an evidence-backed Action Queue for customer problems:

1. Ingest customer signals and account context.
2. Cluster signals into problems with evidence.
3. Propose coordinated product, customer, journey, and research actions.
4. Apply governance checks before execution.
5. Track whether the action improved the expected outcome.

The broader vision is a governed operating layer that connects customer feedback, behavior, actions, and outcomes across existing systems.

## Current Scope

This repository starts with the smallest credible slice:

- API skeleton for problem records, action proposals, governance checks, and outcome contracts.
- Web skeleton for the Action Queue.
- Seed data showing the core product flow.
- Architecture and MVP notes for the business build.

## Repository Layout

```text
apps/
  api/      FastAPI backend prototype
  web/      Next.js frontend prototype
data/       Seed data for local development and demos
docs/       Product, architecture, and MVP notes
```

The full phased product plan is tracked in `docs/roadmap.md`.

## Run The API

```bash
cd apps/api
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
uvicorn app.main:app --reload --port 8000
```

API health check:

```bash
curl http://localhost:8000/health
```

By default, workflow state is persisted to `apps/api/.data/clara.db`. Override this with:

```bash
export CLARA_DB_PATH=/absolute/path/to/clara.db
```

For Supabase/Postgres-backed deployments, set `DATABASE_URL` instead. When
`DATABASE_URL` is present, the API stores problems, imported signals, customer
context, workflow records, taxonomy catalogs and terminology dictionaries in
Postgres JSONB tables. The app creates the
required tables idempotently at startup; the same schema is also available at
`apps/api/migrations/001_supabase_postgres.sql` plus later migration files if
you prefer running it in the Supabase SQL editor first.

```bash
export DATABASE_URL=postgresql://postgres.PROJECT_REF:PASSWORD@HOST:PORT/postgres
export APP_CORS_ORIGINS=https://your-vercel-app.vercel.app,https://your-domain.com
```

Learning-conclusion writes require trusted identity headers. For local demos the
web app sends `x-tenant-id=demo_tenant` and `x-actor-id=demo_reviewer` by default;
in shared deployments these headers must be injected by trusted auth/proxy
infrastructure, not accepted directly from browsers.

## Run The Web App

```bash
cd apps/web
npm install
npm run dev
```

Then open `http://localhost:3000`.

Set `NEXT_PUBLIC_API_URL=http://localhost:8000` when the API is running. The UI has local fallback data so it can render before the backend is started.

In Vercel, set `NEXT_PUBLIC_API_URL` in Project Settings to the deployed FastAPI
API domain. This value is the API URL, not the Supabase URL.

## Current API Surface

```text
GET  /health
GET  /signals
POST /signals/import
POST /signals/import-csv
POST /signals/validate-csv
GET  /customer-context
GET  /customer-context/completeness
POST /customer-context/import
POST /customer-context/import-csv
POST /customer-context/validate-csv
GET  /policy-rules
GET  /policy-rules/{rule_id}
GET  /demo-datasets
POST /demo-datasets/{dataset_id}/import
GET  /problem-candidates
POST /problem-candidates/{candidate_id}/accept
POST /problem-candidates/{candidate_id}/reject
POST /problem-candidates/{candidate_id}/promote
GET  /problems
GET  /problems/{problem_id}
GET  /problems/{problem_id}/affected-context
PATCH /problems/{problem_id}
PATCH /problems/{problem_id}/actions/{action_id}
POST /problems/{problem_id}/transitions
POST /problems/{problem_id}/approvals
GET  /problems/{problem_id}/workflow
POST /problems/{problem_id}/outcomes
POST /problems/{problem_id}/learning-conclusions
GET  /problems/{problem_id}/outcome
GET  /outcome-board
GET  /approvals
GET  /executions
GET  /jira-drafts
```

Approving an action creates a draft execution record when governance checks allow it. Approved Jira-targeted actions also create a local Jira issue draft for review; no live Jira write happens in this prototype. Blocking governance failures return a conflict instead of creating execution. Customer context, policy rules, approvals, lifecycle transitions, draft execution records, Jira drafts, timeline events, outcome measurements and human learning conclusions are persisted or seeded for local development.

Outcome measurements can be recorded from the Action Queue. The API compares the latest observed value with the outcome contract and reports one of:

- `not_measured`
- `not_improved`
- `improving`
- `target_met`

Outcome direction is inferred from the contract: when `success_threshold` is greater than or equal to `baseline`, higher values are better; when `success_threshold` is lower than `baseline`, lower values are better. Outcome snapshots and the outcome board expose that direction so decrease metrics such as complaint rate are not treated like completion-rate metrics.

After an outcome is measured, a reviewer can record a human learning conclusion: `worked`, `partially_worked`, `did_not_work`, `inconclusive` or `measurement_invalid`. Summary, limitations and next-step text are reviewer-authored; common email, phone, IP, address and customer/account ID patterns are redacted. Reviewer and tenant IDs come from trusted headers, are pseudonymized, and learning-conclusion records carry a 730-day retention-expiry timestamp.

The outcome board aggregates every problem's latest outcome snapshot into a queue-level view with counts for each measurement state and latest learning status.

Imported signals are also persisted in SQLite. The first run seeds the local signal table from `data/sample_signals.json` and the local context table from `data/sample_customer_context.json` when those tables are empty. JSON, pasted CSV, uploaded CSV files and reusable demo datasets share the same signal import path. Uploaded signal CSVs can be mapped to the canonical signal fields in the UI before import. CSV validation reports row counts, importable rows, missing required values, duplicate IDs and warnings for already-imported records. Problem candidates are deterministic groups by journey and journey stage with evidence excerpts and a first-pass root-cause hypothesis. Candidate review flags duplicate journey/stage matches, lets a user accept non-duplicates into the Action Queue, and persists rejected candidates.

Customer context now affects prioritization instead of only appearing as imported metadata. Problem summaries and detail responses include a `context_impact` summary when evidence-linked customer or account IDs match context rows. Account value, account exposure, consent gaps and low health can raise the read-side impact score used by `/problems`, `/outcome-board` and the Action Queue, while stored draft records remain unchanged. `/customer-context/completeness` reports source completeness across scoring, routing and governance fields. `/problems/{problem_id}/affected-context` returns the matched context rows, account rollups, parent-account, contact-role and product-owner context, missing evidence IDs, owner routing recommendations and context data-quality warnings used by the Action Queue explorer.

The Action Queue shows every evidence excerpt attached to a problem, including signal ID, source, customer, account, language and timestamp. Promoted draft problems and their action proposals can be edited from the Action Queue. Lifecycle transitions move durable drafts through status changes and add timeline history to workflow state. Governance checks reference explicit seeded policy-rule objects from `data/sample_policy_rules.json`. Primary workflow panels show explicit loading, empty and API-unavailable notices. Seed problems are read-only demo records; only durable `PRB-DRAFT-*` problems can be changed.

Required signal CSV columns:

```text
signal_id,customer_id,account_id,source,journey,journey_stage,campaign_exposure,product_events,feedback_text,language,timestamp
```

Use `;` or `|` between multiple `campaign_exposure` or `product_events` values.

Required customer-context CSV columns:

```text
customer_id,account_id
```

Recommended customer-context columns:

```text
account_name,parent_account_id,parent_account_name,segment,lifecycle_stage,plan_tier,contact_role,account_value,renewal_date,consent_status,health_score,owner,product_owner,region
```

## Verification

```bash
npm run api:test
npm run web:lint
npm run web:build
```

Or run all checks:

```bash
npm run check
```

`npm run check` includes an end-to-end Phase 0 smoke test that covers context import, signal import, candidate promotion, draft editing, lifecycle transition, approval, execution creation, Jira draft creation and outcome measurement.

## Development Notes

- The first UI should remain the Action Queue, not a dashboard or chat surface.
- AI-generated claims must carry evidence, confidence, limitations, and audit metadata.
- Execution should start as draft-plus-approval. Controlled autonomy comes later.
- Outcome tracking starts simple, then moves toward holdouts and causal measurement where customers have enough data.
