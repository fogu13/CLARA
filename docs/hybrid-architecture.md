# Hybrid Architecture

CLARA_2 (Python/FastAPI) base + Elvis's AI layer + UI ported in.

## What came from where

| Capability | Source | Where it lands in CLARA |
|---|---|---|
| FastAPI engine + domain model | CLARA_2 | apps/api/app/{domain,services,main.py} |
| Governance gate (PolicyRule) | CLARA_2 | apps/api/app/services/{policies,workflow}.py |
| Customer/account context graph | CLARA_2 | apps/api/app/services/context_impact.py |
| 86 tests + CI | CLARA_2 | apps/api/app/tests + .github/workflows/ci.yml |
| Direction-aware outcome_status | CLARA_2 | apps/api/app/services/workflow.py:63-87 |
| Provider-agnostic AI client | Elvis | apps/api/app/services/ai.py (port of _shared/ai.ts) |
| LLM enrichment + synthesis | Elvis | agentic triage/intelligence nodes |
| Semantic + adaptive taxonomy | Elvis | taxonomy services and Postgres migrations |
| Outcome contract + decay learnings | Elvis | workflow and outcome learning services |
| Conflict resolution (priority->specificity) | Elvis | policy/rule services |
| Auth + RLS + multi-tenancy | Elvis | auth/RBAC/RLS layer |
| 17-page UI (dashboard, signals, taxonomy, ...) | Elvis | apps/web/app/(dashboard)/* |
| EU AI Act + GDPR compliance checker | Elvis | compliance route + endpoint |
| Events telemetry for thesis | Elvis | events table + telemetry hooks |
| LangGraph agent orchestration | NEW | apps/api/app/agents/ |
| Connector layer (Zendesk/Jira/Slack) | NEW | apps/api/app/connectors/ |
| Langfuse tracing + evals | NEW | infra/docker-compose.langfuse.yml |
| Self-hosted Supabase | NEW | infra/docker-compose.supabase.yml |

## Why this shape

- **CLARA_2 as base:** stronger domain modeling, governance-by-design,
  testability, scope discipline. Its weaknesses (no AI, no real connectors,
  no auth, no multi-tenancy, thin UI) are exactly what Elvis supplies.
- **Elvis as port source:** its AI layer is genuinely provider-agnostic and
  self-hostable (the EU/local-first moat); its UI is a polished 17-page
  shadcn SPA; its multi-tenancy RLS + Auth + onboarding are already built.
  Porting these into CLARA_2's clean backbone is less work than
  re-engineering CLARA_2's rigor into Elvis.
- **Self-hosted Supabase:** preserves local-first without reinventing Auth +
  RLS + pgvector. Open-source, EU-deployable.
- **LangGraph:** the 2026 production standard for stateful, auditable,
  human-in-the-loop agents — fits governed triage exactly.
- **Langfuse:** open-source, self-hostable observability + evals —
  non-negotiable for the thesis (triage quality must be measured).

## What neither source delivers (the thesis-critical gaps)

1. **Real close-the-loop delivery** — both simulate action execution.
   The Execution Connectors and Customer Closure roadmap phase covers this.
2. **Agentic orchestration** — Elvis uses bounded LLM calls (not agents);
   CLARA_2 has no AI at all. The agentic orchestration enabler covers this when needed by roadmap phases.
3. **Measured triage quality** — neither has an eval harness. The evaluation/tracing enabler covers this and remains thesis-critical.

## Source-of-truth references

- Elvis AI layer: `reference/elvis/supabase/functions/_shared/ai.ts`
- Elvis adaptive taxonomy spec: `reference/elvis/docs/superpowers/specs/2026-06-21-adaptive-taxonomy-design.md`
- Elvis thesis artifact chapter: thesis manuscript, chapter 4 (private repository)
- Canonical CLARA roadmap: `docs/roadmap.md`
- CLARA_2 data model: `docs/data-model.md`
- Architecture notes: `PLAN.md` (top level)
