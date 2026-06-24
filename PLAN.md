# CLARA — Build Plan

CLARA_2 (Python/FastAPI) as the base, porting Elvis's AI layer + UI in.
Thesis + business in parallel. Local-first LLMs are a hard requirement (EU moat).
First real connectors: Zendesk (in) + Jira + Slack (out).

## Target architecture

```
                     Next.js 15 (apps/web)
       shadcn/ui port of Elvis's 17 pages: dashboard, signals, taxonomy,
       insights, rules, actions, learnings, sources, integrations, compliance
                              | REST
                     FastAPI engine (apps/api)  — the core
       Connector layer (Zendesk pull / Jira+Slack push)
       LangGraph triage->action state machine
       Provider-agnostic AI client (port of reference/elvis/_shared/ai.ts)
       Semantic taxonomy (pgvector + evolve + governance)
       Governance gate (PolicyRule) + context graph
       Outcome engine (direction-aware + decay learnings)
       Auth middleware (verifies Supabase JWT)
                              | psycopg + service role
       Self-hosted Supabase = Postgres + Auth + RLS + pgvector + pg_cron
                              | (EU-resident, local-first)
       Langfuse (self-hosted) — traces + evals for thesis
```

CLARA_2's clean domain model + governance + tests stay the backbone. Elvis's
missing-from-CLARA_2 capabilities (AI, UI, auth, multi-tenancy, semantic
taxonomy, real ingestion) get ported in as new modules. Self-hosted Supabase
keeps the local-first/EU moat intact while giving Auth + RLS + pgvector without
reinventing them.

## Phases

### Phase 0 — Foundation alignment (~1.5 weeks)
- [ ] Postgres-only + pgvector + RLS; add workspace_id/tenant_id to every table
      (fixes postgres.py:471 gap); port Elvis RLS policy pattern.
- [ ] Port `_shared/ai.ts` -> `apps/api/app/services/ai.py` (provider-agnostic,
      OpenAI-compatible, keyless Ollama/vLLM, tool-calling structured output,
      embeddings). **Highest-value port.**
- [ ] Stand up self-hosted Langfuse; trace every ai.py call.
- [ ] FastAPI middleware verifying Supabase JWT -> injects workspace_id.
- [ ] Create migrations 003/004/005 (currently stubs).
- **Verify:** `npm run check` passes; protected route rejects unauthed; an
  Ollama-backed ai.py call returns structured JSON traced in Langfuse.

### Phase 1 — Agentic triage engine (~2 weeks)
- [ ] LangGraph state machine replacing synchronous `build_candidates`
      (main.py:384-395): ingest -> enrich -> classify -> synthesize ->
      governance_gate -> (interrupt: approve) -> action -> measure -> learn.
      Postgres checkpointer for durability/resumability.
- [ ] Port Elvis semantic taxonomy (pgvector, match_taxonomy_nodes, evolve,
      graduated-authority governance) -> replaces substring matching
      (taxonomies.py:364-425).
- [ ] Port Elvis LLM enrichment + synthesis with deterministic cross-signal
      severity (synthesize-insights/index.ts:26-36).
- [ ] Keep CLARA_2 context graph (context_impact.py) + PolicyRule gate
      (workflow.py:42-56) as graph nodes.
- [ ] Make every AI output carry evidence/confidence/limitations/audit.
- **Verify:** golden-set eval in Langfuse (precision/recall vs deterministic
  baseline); graph pauses at approval interrupt and resumes.

### Phase 2 — Real connectors (~2 weeks)  <- proves the thesis claim
- [ ] `Connector` abstraction (apps/api/app/connectors/base.py) — already stubbed.
- [ ] Zendesk source (pull): tickets/search -> signals via field map; reuse
      Elvis api_poll design (sync-source/index.ts:79-160).
- [ ] Jira destination (push): real POST /rest/api/3/issue behind governance
      gate; replaces local-only JiraIssueDraft (workflow.py:125-142).
- [ ] Slack destination (push): real chat.postMessage; replaces simulated
      notify (evaluate-rules/index.ts:142-153).
- [ ] Keep webhook + CSV ingestion (already work).
- **Verify:** a Zendesk ticket flows through triage -> governance-approved Jira
  issue created in a test project -> Slack notification posted.

### Phase 3 — Close-the-loop + outcome engine (~1.5 weeks)
- [ ] Real action execution wired into the LangGraph action node (Phase 2).
- [ ] Upgrade CLARA_2 outcome_status (workflow.py:63-87) with Elvis
      resolution_score + closure chips (Operational/Customer/Outcome).
- [ ] Port Elvis confidence-decay learnings (learnings.ts) + retrieval, merged
      with CLARA_2 structured LearningConclusion verdicts.
- [ ] Durable retries via LangGraph checkpointer (Temporal only if outgrown).
- **Verify:** approved Jira action -> outcome measured after window ->
  resolution_score + learning conclusion + decayed confidence reflected.

### Phase 4 — UI port into Next.js (~2.5 weeks)
- [ ] Add shadcn/ui to apps/web via CLI (do NOT copy Elvis's src/components/ui).
- [ ] Rebuild Elvis's 17 pages as App Router routes (route stubs already exist
      in apps/web/app/(auth) and (dashboard)). Each is a rewrite, not a copy —
      Elvis is Vite + React Router; these become RSC/client components.
- [ ] Reuse Elvis component structure + types.ts as blueprints.
- **Verify:** each page wired to FastAPI; loading/empty/error states.

### Phase 5 — Evals + EU AI Act + thesis integration (~1.5 weeks)
- [ ] Eval harness in Langfuse: golden set (~100-200 labeled signals),
      classification precision/recall, routing accuracy, hallucination/PII
      checks. **Thesis-critical.**
- [ ] Port Elvis EU AI Act + GDPR compliance checker (the one feature Elvis
      actually runs) as a page + endpoint.
- [ ] EU AI Act mapping doc + DPIA template: position as transparency + human
      oversight by design (Art 14/50); keep human-in-the-loop for consequential
      actions. Thesis chapter + SaaS moat.
- [ ] Wire events telemetry (Elvis logEvent) for thesis evaluation scripts.
- **Verify:** eval dashboard shows scores; compliance checker returns a report.

### Phase 6 — SaaS readiness (post-thesis, stub now) (~1 week stub)
- [ ] Enforce RBAC (CLARA_2 has none; Elvis has schema only).
- [ ] Stripe billing stub + plan limits; team-invite; API-key validation
      middleware (Elvis generates keys but nothing consumes them).
- [ ] Rate limiting.

## What to learn (prioritized)

1. LangGraph (state, checkpointer, interrupt)            — Phase 1 engine
2. Langfuse                                              — all AI calls, Phase 5 evals
3. Provider-agnostic LLM via OpenAI-compatible base_url  — ai.py, Phase 0
4. pgvector + semantic taxonomy + adaptive discovery     — Phase 1
5. OAuth2 + Zendesk/Jira/Slack APIs + Connector iface    — Phase 2
6. Supabase Auth + RLS verified in FastAPI               — Phase 0
7. Pydantic AI (optional, typed structured outputs)      — Phase 1
8. EU AI Act (Art 14/50) + DPIA                          — Phase 5
9. shadcn/ui in Next.js App Router                       — Phase 4
10. Stripe billing / RBAC enforcement (later)            — Phase 6

## Open decisions

- **Thesis deadline** (chosen: thesis + business in parallel). Sized to
  ~10-11 weeks of build (Phases 0-5) assuming ~3 months. If time gets tight,
  trim Phase 6 stub first, then the full UI port — a strong eval harness +
  one real Zendesk->Jira->Slack loop + the EU AI Act chapter matter more for
  the thesis than 17 polished pages.

## Reference map

- `reference/elvis/` — Elvis source kept for porting reference (read-only):
  - `supabase/functions/_shared/ai.ts`        -> apps/api/app/services/ai.py
  - `supabase/functions/*/index.ts`           -> LangGraph nodes
  - `supabase/migrations/*.sql`               -> migrations 003/004/005
  - `src/lib/{types,learnings,events,taxonomy}.ts` -> apps/web/lib + apps/api
  - `src/pages/*.tsx`                         -> apps/web/app/(dashboard)/*
  - `src/components/{dashboard,layout,rules,shared,taxonomy}/*` -> apps/web/components
  - `src/contexts/AuthContext.tsx`            -> apps/web auth layer
  - `docs/superpowers/{specs,plans}/*`        -> design intent
- `thesis/`  — primary academic artifact (moved from Elvis)
- `business/` — strategy (moved from Elvis)
