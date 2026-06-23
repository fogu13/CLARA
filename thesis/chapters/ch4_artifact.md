# Chapter 4: The Artifact

> **DRAFT for review.** This chapter documents the Odradek platform as built. It is generated from the
> implemented codebase (branch `feat/strategy-alignment`) to align the thesis with the artifact; the
> author should revise prose, verify citations against the reference list, and reconcile section
> numbering with the final manuscript.

## 4.1 Overview

The artifact of this thesis is **Odradek**, a working web platform that instantiates the complete
**Signal → Insight → Action → Learning** cycle. Where Chapter 3 established *how* the artifact is
evaluated, this chapter documents *what was built* and, more importantly, the non-trivial design
decisions that constitute the design-science contribution (Hevner, March, Park, & Ram, 2004, G6).
Odradek is implemented as a React 18 / TypeScript single-page application on a Supabase
(PostgreSQL + Auth + Edge Functions) backend. All data is workspace-scoped through row-level
security, so the platform is multi-tenant by construction.

The platform is deliberately *not* a feedback dashboard. Its claim to contribution is the governed
path from a raw customer signal to a measured outcome and a codified learning — the stages where the
literature locates the feedback-action gap (Bone, Lemon, Voss, & Walsh, 2017) and organisational
knowledge loss (Walsh & Ungson, 1991; Argote, 2013).

## 4.2 Architecture

Odradek is organised as a pipeline of bounded stages, each with a clear interface:

| Stage | Responsibility | Implementation |
|-------|----------------|----------------|
| Ingestion | Capture qualitative and quantitative signals | CSV import, a public `ingest-webhook` endpoint, and connector configs (`signal_sources`) |
| Enrichment | Sentiment, theme, urgency, evidence per signal | `enrich-signal` edge function (LLM) |
| Synthesis | Cluster related signals into insights | `synthesize-insights` edge function with composite severity |
| Action | Match rules, resolve conflicts, execute or queue actions | `evaluate-rules` edge function + `feedback_rules` |
| Approval | Human-in-the-loop clearance for risky actions | `actions_log` (status `pending_approval`) + the Actions UI |
| Measurement | Score whether the issue improved after the window | `measure-outcomes` edge function + the outcome contract |
| Learning | Codify A/B outcomes with decaying confidence | `ab_learnings` + retrieval |
| Governance | EU AI Act + GDPR assessment of marketing use cases | `check-compliance` edge function |

Deterministic logic (schema validation, conflict resolution, audit logging, action execution) lives
in code; bounded language-model reasoning (enrichment, synthesis, learning extraction) is confined to
edge functions behind a single provider-agnostic client (`_shared/ai.ts`). This separation follows the
current guidance that production language-model systems should wrap model calls in deterministic
workflows with explicit checkpoints and human oversight rather than delegating control to free-roaming
agents.

## 4.3 Four non-trivial design decisions

The proposal (Chapter, "Technical Design Contribution") identified four decisions that cannot be
resolved from the literature alone and therefore constitute the artifact's research contribution.
Each is now implemented; this section documents the chosen design and its theoretical grounding.

### 4.3.1 Rule conflict resolution

When several rules match the same insight, the engine must decide which fires, or the system will
either over-act (duplicate tickets, alert fatigue) or under-act. Odradek's `evaluate-rules` function
ranks matched rules by **priority**, breaks ties by **specificity** (number of conditions), and then
deduplicates by **action type** so that each action type fires at most once; superseded rules are
recorded and returned. This is a pragmatic instantiation of conflict-resolution strategies from
production-rule systems (Forgy, 1982; the Rete match/resolve/act cycle) and business-rule management
(Boyer & Mili, 2011), and it operationalises a graduated notion of automation authority (Parasuraman,
Sheridan, & Wickens, 2000) by letting more specific, higher-priority rules dominate.

### 4.3.2 Confidence decay in learnings

An A/B result that was valid two years ago may no longer hold. Odradek stores each learning's
`last_validated_at` and a `half_life_days`, and computes a **decayed confidence** on read using
exponential decay (`base × 0.5^(age / half-life)`); learnings past their half-life are flagged
"stale." This treats organisational memory as perishable rather than permanent, consistent with work
on knowledge depreciation (Argote, 2013) and the temporal validity of organisational memory (Walsh &
Ungson, 1991), and it provides a transparent, inspectable alternative to opaque recency weighting.

### 4.3.3 Cross-signal severity scoring

A single insight may be corroborated by many signals of differing urgency; flat severity loses this.
The `synthesize-insights` function computes a **composite severity** from the strongest member
urgency, the volume of corroborating signals, and the proportion of negative sentiment, and maps the
score to a severity band. The design draws on data-fusion taxonomy (Bleiholder & Naumann, 2008) and
anomaly consolidation (Chandola, Banerjee, & Kumar, 2009): severity emerges from the *set* of signals
rather than any one of them, which mitigates both single-loud-complaint over-escalation and the
dilution of widespread low-urgency issues.

### 4.3.4 Relevant past-learnings retrieval

When a practitioner plans a new experiment, the system should surface what is already known. Odradek
ranks learnings by token overlap with the query, weighted by decayed confidence, and surfaces them
both in a search interface and inline in the rule builder. The design is an information-retrieval
problem (Salton & McGill, 1983) framed as case-based reasoning (Kolodner, 1993) and knowledge reuse
(Markus, 2001); a semantic (embedding/pgvector) ranking is a drop-in replacement for the scorer and is
identified as future work, keeping the current implementation deterministic and inspectable.

## 4.4 Responsible AI controls

Responsible AI is implemented as a layer over the loop, not a bolt-on:

- **Human-in-the-loop approval.** Rules declare `auto_execute`; when false, actions are written as
  `pending_approval` and require explicit human clearance before they fire, satisfying the human-
  oversight expectation of EU AI Act Article 14.
- **Audit trail.** Every action is recorded in `actions_log` with its parameters, result, executor
  (`system_auto` vs. a user id), and status — an auditable record of automated decisions.
- **Outcome contract and closure levels.** Each action captures the metric and measurement window at
  creation; `measure-outcomes` later scores resolution and distinguishes *operational*, *customer*,
  and *outcome* closure, so "closed loop" denotes a measured improvement, not merely a created ticket.
- **Compliance checker.** `check-compliance` assesses a marketing use case against an embedded
  EU AI Act + GDPR knowledge base and returns scored findings and required actions. The knowledge base
  tracks the live regulatory state, including the 2026 Digital Omnibus on AI (deferred high-risk
  deadlines, Article 50 transparency moved to 2 December 2026, and the new prohibition on
  non-consensual intimate imagery / CSAM).
- **Model sovereignty.** All language-model calls run through a provider-agnostic, OpenAI-compatible
  client configured by environment (`AI_BASE_URL`/`AI_API_KEY`/`AI_MODEL`); the platform can therefore
  run on a hosted API or a fully self-hosted local model (Ollama/vLLM), addressing EU data-residency
  concerns, with no dependency on any third-party app-builder runtime.

## 4.5 Evaluation instrumentation

To support the task-based evaluation (Chapter 3), the platform records an `events` telemetry stream
via `logEvent` (rule creation, approvals, status advances carrying time-to-action, measurement, and
learning retrieval). An exported event log feeds `evaluation/prototype_metrics.py`, providing
objective time-to-action and task-completion measures alongside the facilitator-recorded data and the
SUS instrument.

## 4.6 Design as a search process

Consistent with Hevner et al.'s (2004) sixth guideline, the artifact was built through build-evaluate
cycles, and several scope decisions are themselves findings. The platform deliberately *integrates
with*, rather than replaces, collection and delivery tools; connector *pulls* for enterprise systems
(Zendesk, Jira, HubSpot, Typeform) are scaffolded with credential checks but left as future work, as
is semantic-embedding retrieval — both judged unnecessary for evaluating the design concept and a poor
use of the thesis timeline. These boundaries are documented so the contribution is legible as a
situated instantiation rather than a finished commercial product.
