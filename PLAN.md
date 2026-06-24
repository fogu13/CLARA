# CLARA Build Plan

The canonical product roadmap is `docs/roadmap.md`.

This file is intentionally not a second phase plan. Earlier versions mixed an older technical port sequence with the Frankenstein product roadmap, which made phase numbers conflict. Use `docs/roadmap.md` for what is done, what is next and how the remaining work is grouped.

## Current Direction

CLARA is a European Feedback-to-Outcome Operating System: a governed customer-intelligence and action layer that connects customer feedback with behavioural and operational data, recommends coordinated interventions, executes safely through existing systems and learns whether the action worked.

Current next phase: Phase 4 - Full Action Studio.

## Target Architecture

```text
Next.js web app
-> FastAPI core API
-> Signal, context, journey, taxonomy, workflow and outcome services
-> SQLite for local demos or Postgres/Supabase for deployed work
-> Connector layer for existing tools
-> Policy and approval engine before consequential actions
-> Outcome learning loop after execution
```

## Technical Enablers

These support the roadmap but are not separate product phases unless `docs/roadmap.md` says so.

- Postgres/Supabase, pgvector and RLS.
- Provider-agnostic AI client with local-first OpenAI-compatible routing.
- LangGraph for agentic orchestration and durable approval interrupts.
- Langfuse or equivalent tracing/evaluation for AI outputs.
- Connector layer for Zendesk, Jira, Slack, HubSpot, Adobe, Braze, Salesforce and ServiceNow.
- Policy service for versioned, auditable controls.
- OpenTelemetry and LLM tracing.

## Reference Map

- `docs/roadmap.md` - canonical product roadmap and phase sequence.
- `docs/hybrid-architecture.md` - what came from each earlier codebase.
- `reference/elvis/` - Elvis source kept for porting reference.
- `thesis/` - academic artifact.
- `business/` - strategy and commercialization notes.

## Guardrails

- Build the smallest useful phase slice before broad platform work.
- Keep the Action Queue and problem record as the primary interface, not chat.
- Every AI-generated claim must carry evidence, confidence, limitations and audit metadata.
- Start with draft-plus-approval execution; increase autonomy only for low-risk actions with evaluation evidence.
- Integrate with survey, CDP, campaign-delivery and product-management systems instead of rebuilding them.
