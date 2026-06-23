# Hybrid Architecture

Odradek_2 (Python/FastAPI) base + Elvis's AI layer + UI ported in.

## What came from where

| Capability | Source | Where it lands in Hybrid_GLM |
|---|---|---|
| FastAPI engine + domain model | Odradek_2 | apps/api/app/{domain,services,main.py} |
| Governance gate (PolicyRule) | Odradek_2 | apps/api/app/services/{policies,workflow}.py |
| Customer/account context graph | Odradek_2 | apps/api/app/services/context_impact.py |
| 86 tests + CI | Odradek_2 | apps/api/app/tests + .github/workflows/ci.yml |
| Direction-aware outcome_status | Odradek_2 | apps/api/app/services/workflow.py:63-87 |
| Provider-agnostic AI client | Elvis | apps/api/app/services/ai.py (port of _shared/ai.ts) |
| LLM enrichment + synthesis | Elvis | LangGraph nodes (Phase 1) |
| Semantic + adaptive taxonomy | Elvis | migrations 003 + taxonomies service (Phase 1) |
| Outcome contract + decay learnings | Elvis | migration 005 + workflow service (Phase 3) |
| Conflict resolution (priority->specificity) | Elvis | rule engine (Phase 1) |
| Auth + RLS + multi-tenancy | Elvis | migration 004 + FastAPI JWT middleware (Phase 0) |
| 17-page UI (dashboard, signals, taxonomy, ...) | Elvis | apps/web/app/(dashboard)/* (Phase 4) |
| EU AI Act + GDPR compliance checker | Elvis | compliance route + endpoint (Phase 5) |
| Events telemetry for thesis | Elvis | events table + logEvent (Phase 5) |
| LangGraph agent orchestration | NEW | apps/api/app/agents/ (Phase 1) |
| Connector layer (Zendesk/Jira/Slack) | NEW | apps/api/app/connectors/ (Phase 2) |
| Langfuse tracing + evals | NEW | infra/docker-compose.langfuse.yml (Phase 0) |
| Self-hosted Supabase | NEW | infra/docker-compose.supabase.yml (Phase 0) |

## Why this shape

- **Odradek_2 as base:** stronger domain modeling, governance-by-design,
  testability, scope discipline. Its weaknesses (no AI, no real connectors,
  no auth, no multi-tenancy, thin UI) are exactly what Elvis supplies.
- **Elvis as port source:** its AI layer is genuinely provider-agnostic and
  self-hostable (the EU/local-first moat); its UI is a polished 17-page
  shadcn SPA; its multi-tenancy RLS + Auth + onboarding are already built.
  Porting these into Odradek_2's clean backbone is less work than
  re-engineering Odradek_2's rigor into Elvis.
- **Self-hosted Supabase:** preserves local-first without reinventing Auth +
  RLS + pgvector. Open-source, EU-deployable.
- **LangGraph:** the 2026 production standard for stateful, auditable,
  human-in-the-loop agents — fits governed triage exactly.
- **Langfuse:** open-source, self-hostable observability + evals —
  non-negotiable for the thesis (triage quality must be measured).

## What neither source delivers (the thesis-critical gaps)

1. **Real close-the-loop delivery** — both simulate action execution.
   Phase 2's Zendesk->Jira->Slack slice fixes this.
2. **Agentic orchestration** — Elvis uses bounded LLM calls (not agents);
   Odradek_2 has no AI at all. Phase 1's LangGraph state machine fixes this.
3. **Measured triage quality** — neither has an eval harness. Phase 5's
   Langfuse golden-set evaluation fixes this and is thesis-critical.

## Source-of-truth references

- Elvis AI layer: `reference/elvis/supabase/functions/_shared/ai.ts`
- Elvis adaptive taxonomy spec: `reference/elvis/docs/superpowers/specs/2026-06-21-adaptive-taxonomy-design.md`
- Elvis thesis artifact chapter: `thesis/chapters/ch4_artifact.md`
- Odradek_2 roadmap: `docs/roadmap.md`
- Odradek_2 data model: `docs/data-model.md`
- Execution plan: `PLAN.md` (top level)
