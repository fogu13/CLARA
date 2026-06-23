# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Odradek is a governed feedback-to-action platform: it ingests customer signals, triages them with AI, routes governed actions (auto or human-approved), measures whether the loop closed, and codifies learnings. Built with React + Supabase.

## Commands

- `npm run dev` — Start dev server on localhost:8080
- `npm run build` — Production build
- `npm run lint` — ESLint
- `npm run test` — Run Vitest tests
- `npm run test:watch` — Watch mode tests

## Tech Stack

- **Framework**: React 18 + TypeScript, Vite 5 (SWC)
- **Backend**: Supabase (PostgreSQL + Auth)
- **State**: React Query (@tanstack/react-query) for server state, Context API for auth
- **Routing**: React Router v6
- **UI**: shadcn/ui (Radix primitives) + Tailwind CSS 3.4
- **Forms**: React Hook Form + Zod validation
- **Charts**: Recharts
- **Animations**: Framer Motion
- **Icons**: Lucide React
- **Toasts**: Sonner

## Architecture

### Path Alias
`@/*` maps to `src/*` (configured in vite.config.ts and tsconfig).

### Authentication Flow
- `AuthContext` (`src/contexts/AuthContext.tsx`) wraps the app with Supabase auth session/user/loading state
- `ProtectedRoute` component guards authenticated pages
- Email/password and Google OAuth both via **Supabase-native** auth (`supabase.auth.signInWithOAuth`); no third-party auth provider. Google requires the provider configured in the Supabase dashboard.

### Data Access Pattern
- All data is workspace-scoped: queries filter by `workspace_id` from the user's profile
- `useWorkspaceId()` hook (`src/hooks/use-workspace.ts`) fetches workspace_id from profiles table via React Query
- Supabase client at `src/integrations/supabase/client.ts`, auto-generated types at `src/integrations/supabase/types.ts`

### Edge Functions (`supabase/functions/`)
All in Deno. LLM calls go through the shared, provider-agnostic OpenAI-compatible client `_shared/ai.ts` (configured by `AI_BASE_URL`/`AI_API_KEY`/`AI_MODEL` secrets).
- `evaluate-rules` — matches an insight against rules, **conflict resolution** (priority → specificity → action-type dedupe), executes/queues actions, sets the outcome baseline + `measurement_due_at`. Triggered by `on_insight_created`.
- `measure-outcomes` — recomputes the outcome metric after the window, scores `resolution_score`, resolves the insight (single insight or all-due).
- `enrich-signal` — LLM sentiment/theme/urgency/tags for raw signals.
- `synthesize-insights` — clusters enriched signals into insights with deterministic cross-signal severity.
- `extract-learnings` — LLM-derives A/B learnings from `ab_test_result` signals.
- `ingest-webhook` — public endpoint that turns posted items into signals.
- `sync-source` — pull sync (real for webhook/CSV; credential-checked scaffold for API connectors).
- `check-compliance` — EU AI Act + GDPR assessment.

### Evaluation telemetry
`src/lib/events.ts` `logEvent(...)` writes to the `events` table (time-to-action, approvals, etc.); consumed by `thesis/evaluation/prototype_metrics.py`.

### Route Structure
- `/` — Landing page (public, marketing)
- `/auth`, `/reset-password` — Authentication (public)
- `/app` — Dashboard (protected) — the main entry after login
- `/signals`, `/insights`, `/insights/:id`, `/rules`, `/actions`, `/learnings`, `/sources`, `/integrations`, `/compliance`, `/settings` — All protected

### Domain Models (`src/lib/types.ts`)
- **Signal** — Customer feedback/metric data point (qualitative or quantitative) from various sources (NPS, CSAT, support tickets, etc.)
- **Insight** — Derived intelligence from signals, with status workflow (new → reviewing → action_planned → action_taken → measuring → resolved)
- **FeedbackRule** — Conditional automation rules that trigger actions
- **ActionLog** — Audit trail of executed actions
- **AbLearning** — A/B testing pattern learnings
- **SignalSourceConfig** — Data source connection configs

### Component Layout
- `src/components/layout/` — AppLayout, AppSidebar, AppHeader (shared shell for protected pages)
- `src/components/dashboard/` — KPI cards, charts, trends, funnels
- `src/components/shared/` — Reusable badges and status components
- `src/components/ui/` — shadcn/ui component library (do not edit manually; use shadcn CLI to add/update)

### Styling
Colors use CSS custom properties via HSL (defined in `src/index.css`). Tailwind extends with semantic color scales:
- `severity-{low,medium,high,critical}` — for urgency/severity badges
- `sentiment-{positive,neutral,negative,mixed}` — for sentiment indicators
- `team-{marketing,product,cx,sales,engineering}` — for team routing

### Seed / Mock Data
`supabase/seed.sql` is the real demo/eval seed (run in the Supabase SQL editor after signup; idempotent, targets the first workspace). `src/lib/mock-data.ts` is **dead reference data** — not imported anywhere; keep it type-valid but don't rely on it at runtime.

## Environment Variables

Client build vars (`.env`, `VITE_`-prefixed):
```
VITE_SUPABASE_URL
VITE_SUPABASE_PUBLISHABLE_KEY
VITE_SUPABASE_PROJECT_ID
```
Edge-function secrets (set in Supabase, not `.env`):
```
AI_BASE_URL   # OpenAI-compatible base, default https://api.openai.com/v1
AI_API_KEY    # provider key (omit for local Ollama/vLLM)
AI_MODEL      # default gpt-4o-mini
```

## Conventions & gotchas
- **Generated types are hand-synced.** No Supabase MCP type-regen in this env — when adding a column/table via migration, manually mirror it in `src/integrations/supabase/types.ts` AND the domain type in `src/lib/types.ts`.
- **`vite build` does NOT type-check** (SWC strips types). Type-check with `npx tsc -p tsconfig.app.json --noEmit`. The `src/test/*.test.tsx` files have pre-existing, unrelated mock type errors — exclude them when checking your work.
- **Migrations + edge functions are applied/deployed in the user's own Supabase project** (apply migrations in timestamp order; `supabase functions deploy <name>`, or via the Supabase MCP when it's connected to the user's project).
- **Do NOT bump Vite past 5.** `@vitejs/plugin-react-swc@3.11` peers `vite ^4–^7`; Vite 8 breaks the Vercel build with an `ERESOLVE` peer-dependency error on a clean `npm install`.
- **Fresh Supabase project bootstrap.** `handle_new_user()` creates a *profile* but NOT a workspace, so on a new project every screen is empty until you create one and link it: `insert into public.workspaces (name,slug) values ('My Workspace','my-workspace') on conflict (slug) do nothing;` then `update public.profiles set workspace_id=(select id from public.workspaces order by id limit 1) where workspace_id is null;`. Run `supabase/seed.sql` after that.
- **`signals.tags` and `ab_learnings.test_ids` are JSONB**, not Postgres arrays — insert with `to_jsonb(ARRAY[...])` and match with `tags @> '["x"]'::jsonb`.
- **Ignore the Next.js validator hook** (`"use client"` suggestions) — this is a Vite SPA, not Next.js.
- New `feedback_rules.priority` (conflict resolution) and `insights` outcome-contract fields (`outcome_metric`, `outcome_baseline`, `measured_at`, …) back the action engine and close-the-loop flow.

## Deployment
- Hosted on **Vercel** (project `ai-dream-builder`, `https://ai-dream-builder.vercel.app`); auto-deploys on push to `main`.
- `vercel.json` has the SPA catch-all rewrite (`/(.*) → /index.html`) so client routes don't 404 on refresh.
- Set the 3 `VITE_SUPABASE_*` env vars in Vercel to the active Supabase project; add the Vercel URL to Supabase → Auth → URL Configuration (Site URL + Redirect URLs).
