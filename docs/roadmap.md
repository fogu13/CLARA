# Unified Product Roadmap

This is the canonical CLARA roadmap. Older phase lists in `PLAN.md`, thesis notes, and reference plans are historical context only.

CLARA is a European Feedback-to-Outcome Operating System: a governed customer-intelligence and action layer that connects feedback with behavioural and operational data, identifies broken journeys, recommends coordinated product, service and marketing interventions, executes through existing systems, and learns whether the action solved the customer problem.

Working category: feedback-driven journey orchestration.

## North Star

```text
Signal
-> Problem
-> Root cause hypothesis
-> Affected customers/accounts
-> Coordinated action plan
-> Governance approval
-> Execution in existing systems
-> Customer closure
-> Outcome measurement
-> Organizational learning
```

Positioning: "We help organizations decide what to do about customer problems, execute safely through the systems they already use, and prove whether the action worked."

## Product Modules

| Module | Purpose | Status |
| --- | --- | --- |
| 1. Universal Signal Hub | Bring feedback, support, behaviour, CRM and operational signals into one canonical event model. | Started |
| 2. Customer and Account Context Graph | Link contacts, accounts, hierarchy, lifecycle, value, consent, ownership and affected cohorts. | Started |
| 3. Trusted Intelligence Engine | Evidence-backed taxonomy, classification, root-cause hypotheses, multilingual DE/EN handling and emerging-problem detection. | Started |
| 4. Live Journey Intelligence | Connect what customers say with what they did, then score journey friction and deviation. | Started |
| 5. Coordinated Action Studio | Generate product, customer, journey, research and governance actions as one portfolio. | Started |
| 6. Audience and Intervention Builder | Design governed audiences and intervention briefs without becoming a CDP or campaign platform. | Not started |
| 7. Governance and Approval Engine | Enforce risk, privacy, evidence, model and tool policies before action. | Started |
| 8. Resolution and Customer Closure | Track operational closure, customer follow-up and unresolved customers. | Minimal |
| 9. Outcome Learning Engine | Measure outcomes and build reusable memory of which actions worked in which contexts. | Started |
| 10. Editions and Industry Packs | Package SME, enterprise and vertical templates for sale. | Not started |

## Current Build Status

| Phase | Name | Status | Branch/commit intent |
| --- | --- | --- | --- |
| 0 | Sellable UI / Operating Spine | Done | End-to-end demo UI and workflow |
| 1 | EU Trust Baseline | Done | RBAC, audit export, Postgres migration trust checks |
| 2 | German Intelligence | Done | DE/EN readiness, taxonomy and terminology trust slice |
| 3 | Live Journey Intelligence Lite | Done | Journey event import, journey impact, problem-detail evidence |
| 4 | Full Action Studio | Done | Action portfolio workspace, approval diffs and dependencies |
| 5 | Audience and Intervention Builder | In progress | Governed briefs, audience readiness and export-ready drafts |
| 6 | EU Governance and Policy Engine | Planned | Policy-as-code and AI governance |
| 7 | Execution Connectors and Closure | Planned | Real tool execution and customer closure |
| 8 | Outcome Learning Engine | Planned | Stronger measurement and reusable action memory |
| 9 | Packaging and Industry Packs | Planned | SME/enterprise editions and vertical packs |

## Phase 0 - Sellable UI / Operating Spine

Status: done.

Goal: make the smallest credible product loop visible and usable.

Delivered:

- Signal intake panel for JSON, pasted CSV and uploaded mapped CSV.
- Reusable demo datasets and validation reports.
- Customer/account context import and persistence.
- Deterministic problem candidates and durable promoted draft problems.
- Editable draft problems and action proposals.
- Problem detail pages linked from insights.
- Lifecycle transitions and problem timeline.
- Policy-rule catalog, approval decisions and duplicate-approval protection.
- Draft execution records and Jira issue drafts.
- Outcome contracts, outcome measurements and outcome board.
- SQLite persistence for local demos.
- API tests plus frontend lint/build checks.

Remaining later:

- Demo screenshots and short buyer walkthrough.
- Existing lint-warning cleanup.

## Phase 1 - EU Trust Baseline

Status: done.

Goal: make the prototype safe enough for shared EU/DACH demos.

Delivered:

- RBAC dependencies on consequential API write routes.
- Admin-only audit export endpoint.
- Self-contained Postgres migration trust checks.
- Frontend bearer-token forwarding from `clara_access_token`.
- Tests for protected routes, audit export and migration prerequisites.

Remaining later:

- Real login/session UI.
- Remove direct browser-sent trusted identity headers in production; inject identity server-side or through trusted infrastructure.
- Deeper RLS verification across all persisted objects.
- Audit export UI.

## Phase 2 - German Intelligence

Status: done.

Goal: prove CLARA is not just English-first feedback triage.

Delivered:

- Versioned product, journey, contact-reason, marketing and compliance taxonomy catalogs.
- German/English terminology dictionary with aliases, definitions and category mappings.
- Classification confidence, matched terminology, multilingual notes, contradictory evidence, limitations and evaluation notes on candidates.
- Root-cause analysis with confidence, evidence factors, alternatives and validation questions.
- Emerging-problem report with ranked watch/action candidates.
- Language-quality endpoint and taxonomy UI readiness card.
- API tests for taxonomy exposure, classification enrichment and language readiness.

Remaining later:

- German UI localization.
- Larger DE/EN labeled evaluation set.
- Stronger terminology QA and classification-quality scoring.
- Industry-specific German dictionaries.

## Phase 3 - Live Journey Intelligence Lite

Status: done.

Goal: connect feedback to behaviour without pretending to be a full product analytics suite.

Delivered:

- Journey event model for CSV/JSON imported behavioural events.
- `/journey-events`, `/journey-events/import` and `/journey-events/import-csv` endpoints.
- SQLite and Postgres journey-event storage.
- Read-time problem enrichment with `journey_impact`.
- Matching by evidence customer/account plus journey and journey stage.
- Friction/deviation scoring from failed, blocked, retry or error-like events.
- Problem-detail Journey Intelligence card, hidden when no events match.
- API tests proving journey events affect problem evidence/priority responses.

Remaining later:

- Timestamp-window matching instead of broad same-stage matching.
- Complainants versus non-complainants comparison.
- Funnel/session metadata and release/experiment context.
- Full journey graph visualization.

Do not build yet:

- Full behavioural analytics.
- Session replay.
- CDP-style customer profiles.
- Custom funnel tooling.

## Phase 4 - Full Action Studio

Status: done.

Goal: turn one recommended action into a coordinated cross-functional action portfolio.

Scope:

- Product fix tab.
- Customer recovery tab.
- Journey intervention tab.
- Campaign/audience tab.
- Research tab.
- Governance tab.
- Action templates for the five action classes.
- Owner routing from context impact, journey impact and policy rules.
- Action dependency handling.
- Action editing and approval diffs.
- Action confidence, limitations and evidence links.
- Experiment proposal generation.

Exit criteria:

- A problem page shows a coherent product + customer + journey + research + governance portfolio.
- Reviewer can edit and approve/reject each action with visible evidence and policy checks.
- Tests cover action portfolio generation/editing and approval diffs.

## Phase 5 - Audience and Intervention Builder

Status: in progress.

Goal: design governed interventions without replacing Adobe, Braze, HubSpot, Salesforce or a CDP.

Delivered so far:

- Governed intervention briefs attached to customer recovery and journey intervention actions.
- Audience readiness estimates with eligibility, consent, suppression and over-contact signals.
- Export-ready draft metadata for downstream systems without live campaign activation.
- Leadership dashboard and action-queue UX for intervention readiness.

Scope:

- Audience definition builder.
- Inclusion and exclusion criteria.
- Trigger definition.
- Channel recommendation.
- Content brief and personalization variables.
- Control group and primary success metric.
- Guardrail metrics.
- Consent availability checks.
- Active-campaign overlap and over-contact risk.
- Export formats for HubSpot, Adobe Experience Platform, Braze and Salesforce.

Exit criteria:

- CLARA can produce a governed audience/intervention draft from an approved problem.
- The draft states who is included, who is excluded, why, what should happen, what must be measured and what approvals are required.

## Phase 6 - EU Governance and Policy Engine

Status: planned.

Goal: make governance a product module, not documentation pasted on top.

Scope:

- Risk-tiered action matrix.
- Machine-enforceable policy rules.
- Evidence confidence thresholds.
- Customer-contact consent checks.
- PII detection and sensitive-category safeguards.
- Retention, lawful-basis and purpose metadata.
- Model/provider/prompt audit metadata.
- AI use-case inventory and impact-assessment fields.
- Incident log.
- Least-privilege tool permission model.
- Tool allowlist and output checks.

Exit criteria:

- High-risk actions are blocked or escalated by policy before execution.
- Each AI-assisted recommendation records evidence, model/provider metadata, reviewer decision and audit trail.

## Phase 7 - Execution Connectors and Customer Closure

Status: planned.

Goal: move from drafts to verified operational and customer closure through existing systems.

Scope:

- Real Jira issue creation and status sync.
- Linear or Azure DevOps draft support.
- Zendesk customer recovery task.
- HubSpot customer-success task.
- Execution accepted, completed and released states.
- Affected-customer list for closure follow-up.
- Customer closure eligibility.
- Response drafting with verified resolution facts only.
- Follow-up validation prompts.
- Unresolved-customer tracking.
- Closure timeline.

Exit criteria:

- An approved action creates or updates the external system record.
- CLARA can show operational closure and customer closure separately.

## Phase 8 - Outcome Learning Engine

Status: planned.

Goal: build the defensible moat: reusable knowledge of which actions worked in which contexts.

Scope:

- Stronger outcome board.
- Before/after analysis.
- Matched comparison groups.
- Holdout/control groups.
- Phased rollout tracking.
- Action effectiveness memory.
- Reusable intervention knowledge.
- Failed-action learning.
- Next-best-action recommendations.
- Problem/action/outcome graph.
- Longitudinal reporting.

Exit criteria:

- Every approved action has an outcome contract and a measured result.
- Similar future problems can retrieve prior action outcomes and warn when a previous approach failed.

## Phase 9 - Packaging and Industry Packs

Status: planned.

Goal: make CLARA easier to buy and implement.

SME edition:

- Guided setup.
- CSV upload and mapping.
- Zendesk, HubSpot, Jira and Teams connectors.
- Prebuilt taxonomies.
- Recommended workflows.
- Simple approval rules.
- German/English UI.
- One-week implementation path.

Enterprise edition:

- SSO and SCIM.
- Business-unit isolation.
- Custom taxonomies and account hierarchy.
- Data warehouse integration.
- Model routing.
- Advanced policy engine.
- Audit export and configurable retention.
- ServiceNow, Salesforce, Adobe, SAP and Azure DevOps connectors.
- Private tool servers.

Industry packs:

- B2B industrial: sites, plants, product family, batch, quality routing and recall/compliance escalation.
- SaaS product: product-area taxonomy, bugs/features, usage events, onboarding/adoption, Productboard/Jira and renewal risk.
- Ecommerce: delivery, returns, payment, reviews, service recovery, campaign suppression and repeat-purchase measurement.
- Financial services: onboarding, identity verification, fraud-review boundaries, vulnerability safeguards and stricter approvals.

## Technical Enablers

These are implementation details, not separate product phases unless a phase explicitly needs them.

- Postgres/Supabase, pgvector and RLS.
- Provider-agnostic AI client with local-first OpenAI-compatible routing.
- LangGraph for agentic orchestration and durable approval interrupts.
- Langfuse or equivalent tracing/evaluation for AI outputs.
- Connector layer for Zendesk, Jira, Slack, HubSpot, Adobe, Braze, Salesforce and ServiceNow.
- Policy service for versioned, auditable controls.
- OpenTelemetry and LLM tracing.

## Non-Goals

- Do not build a full survey platform.
- Do not build a full CDP.
- Do not build a full campaign-delivery platform.
- Do not build a full product-management platform.
- Do not make chat the primary interface.
- Do not start with autonomous customer-facing execution.
- Do not compete with Adobe/Braze delivery infrastructure; generate governed intervention drafts and push to those systems.

## Current Next Step

Finish Phase 5 v1, then move to Phase 7 customer closure.

Remaining useful Phase 5 slice:

1. Add explicit export/download drafts for approved interventions.
2. Attach consent and suppression metadata from customer context where available.
3. Show intervention readiness in a dedicated operator workflow.
4. Keep execution as draft-plus-human-approval; do not send campaigns from CLARA.
