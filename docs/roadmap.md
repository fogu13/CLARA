# Product Roadmap

This roadmap tracks the full Feedback-to-Outcome Operating System vision. Section 16 of the original strategy is the smallest credible version, not the full product boundary.

## North Star

Build a governed customer-intelligence and action layer that turns customer signals into evidence-backed problems, affected groups, approved actions, controlled execution, customer closure and measurable organizational learning.

Core chain:

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

## Current Implementation Status

| Area | Status | Current Capability |
| --- | --- | --- |
| Universal Signal Hub | Phase 1 started | JSON, pasted CSV, uploaded mapped CSV, reusable demo datasets and validation reports, persisted in SQLite |
| Customer/Account Context Graph | Started | Customer/account IDs plus CSV/JSON context import, sample context, SQLite persistence and context impact summaries |
| Trusted Intelligence Engine | Started | Deterministic candidates, duplicate detection, candidate review, richer evidence panel and context-aware impact scoring |
| Live Journey Intelligence | Minimal | Journey and journey-stage fields |
| Coordinated Action Studio | Started | Structural, recovery and research action proposals with promoted-draft editing |
| Audience/Intervention Builder | Not started | Planned |
| Governance/Approval Engine | Started | Policy-rule catalog, approval decisions, blocking checks, persisted records |
| Resolution/Customer Closure | Minimal | Draft execution records, Jira issue drafts and problem timeline |
| Outcome Learning Engine | Started | Outcome contracts, measurements, status and outcome board |
| SME Edition | Started | CSV-first local workflow |
| Enterprise Edition | Not started | Planned |
| Industry Packs | Not started | Planned |

## Phase 0 - Operating Spine

Status: complete.

Goal: prove the end-to-end loop before adding broad integrations or AI complexity.

Delivered:

- Action Queue UI
- signal intake panel
- sample JSON import
- pasted CSV import
- uploaded CSV import with column mapping
- validation reports before import
- persisted signals
- customer/account context import
- persisted customer context
- deterministic problem candidates
- durable promoted draft problems
- editable promoted draft problems
- lifecycle transitions
- problem timeline
- policy-rule catalog
- action proposals
- approval decisions
- draft execution records
- Jira issue drafts
- outcome contracts
- outcome measurements
- outcome board
- SQLite persistence
- API tests and frontend build checks

Exit criteria:

- `npm run check` passes.
- A user can import feedback, generate a candidate, promote it, approve an action and record an outcome.
- `test_phase0_operating_spine.py` covers the full API loop from context import through outcome timeline.
- Current local work is committed and pushed.

## Phase 1 - Usable Demo For Design Partners

Goal: make the prototype usable with real customer files.

Features:

- action proposal editing for promoted drafts
- richer evidence panel in the Action Queue
- duplicate candidate detection by journey and stage
- candidate accept/reject flow
- reusable demo datasets for SaaS onboarding, ecommerce checkout and retention cancellation
- basic empty/loading/error states for primary workflows

Primary modules advanced:

- Module 1: Universal Signal Hub
- Module 3: Trusted Intelligence Engine
- Module 5: Coordinated Action Studio
- Module 10: Action Queue UI

## Phase 2 - Context Graph And Impact Model

Goal: make account and customer context materially affect prioritization.

Features:

- customer table
- account table
- account value impact scoring
- consent-risk impact scoring
- health-score impact scoring
- customer/account exposure scoring from linked context
- context impact explanation in the Action Queue
- lifecycle stage
- renewal date
- product ownership
- source completeness checks
- data quality warnings
- affected customer/account explorer
- contact roles
- parent-child account hierarchy

Delivered so far:

- Context rows linked by evidence customer IDs and account IDs now create a `context_impact` summary on problem detail and summary responses.
- Account value, customer/account exposure, missing consent and low health can raise impact factors and reorder `/problems` plus `/outcome-board`.
- Priority lifecycle stages and near-term renewal dates now raise context-linked impact factors with explicit lifecycle and renewal-risk drivers.
- The Action Queue shows matched customers, matched accounts, high-value accounts, total account value, health, consent-risk count, score lift, owners and regions.
- `/problems/{problem_id}/affected-context` returns matched context rows, account rollups, missing evidence context IDs and data-quality warnings.
- The Action Queue includes an affected customer/account explorer with account value, health, lifecycle, owner and consent-risk details.
- Customer context now supports parent-account IDs/names and contact roles across JSON, CSV and SQLite persistence.
- Customer context now supports product owners across JSON, CSV, SQLite persistence, completeness checks and affected-account rollups.
- The affected context explorer generates owner routing recommendations from high-value exposure, consent risk, high-influence contacts, low health and parent-account relationships.
- `/customer-context/completeness` reports source completeness across scoring, routing and governance fields with readiness levels and warnings.
- The Customer Context panel shows readiness score, core field coverage and source completeness warnings.
- API tests cover context-linked scoring, unchanged problems without matching context, summary/detail response parity, account rollups, missing-context warnings, source completeness, schema migration and hierarchy/role persistence.

Primary modules advanced:

- Module 2: Customer and Account Context Graph
- Module 3: Trusted Intelligence Engine
- Module 7: Governance and Approval Engine

## Phase 3 - Trusted Intelligence Engine

Goal: move from deterministic grouping to evidence-backed intelligence.

Features:

- taxonomy data model
- product, journey, contact-reason, marketing and compliance taxonomies
- taxonomy versioning
- merge, split, rename and lock categories
- classification confidence
- contradictory evidence
- known limitations
- multilingual German/English handling
- terminology dictionary
- root-cause hypothesis generation
- emerging-problem detection
- evaluation set for classification and routing quality

Delivered so far:

- Added versioned product, journey, contact-reason, marketing and compliance taxonomy catalogs with German/English terms, locked categories and category change history.
- `/taxonomies` exposes taxonomy versions, locale coverage, limitations and category metadata.
- Taxonomy category operations now support merge, split, rename and lock flows with version bumps, change history and locked-category protection.
- `/terminology-dictionary` exposes German/English canonical terms, aliases, definitions and category mappings, and candidate classification uses the dictionary aliases for terminology hits.
- Problem candidates now include structured root-cause analysis with confidence, evidence factors, alternative hypotheses and validation questions.
- Problem candidates now include taxonomy classifications, confidence, matched terminology, multilingual notes, contradictory evidence, known limitations, evaluation notes and an emerging-problem score.
- `/emerging-problems` reports ranked watch/action candidates with trend labels, drivers and recommended next steps.
- The Action Queue UI shows taxonomy readiness and generated-candidate intelligence context.
- API tests cover taxonomy catalog exposure and trusted classification enrichment.

Primary modules advanced:

- Module 3: Trusted Intelligence Engine

## Phase 4 - Live Journey Intelligence

Goal: connect feedback with behavior and journey deviation.

Features:

- journey graph model
- touchpoints
- expected objective and observed outcome
- product-event ingestion
- journey-stage classifier
- friction score
- complainants versus non-complainants comparison
- affected cohort generation
- journey deviation detection
- funnel/session metadata placeholders
- experiment and release context

Primary modules advanced:

- Module 1: Universal Signal Hub
- Module 4: Live Journey Intelligence

## Phase 5 - Full Action Studio

Goal: generate coordinated cross-functional action portfolios.

Features:

- Product fix tab
- Customer recovery tab
- Journey intervention tab
- Campaign/audience tab
- Research tab
- Governance tab
- action templates
- owner routing
- action dependency handling
- action editing and approval diffs
- action confidence and limitations
- experiment proposal generation

Primary modules advanced:

- Module 5: Coordinated Action Studio
- Module 7: Governance and Approval Engine

## Phase 6 - Audience And Intervention Builder

Goal: design governed interventions without becoming a CDP or campaign platform.

Features:

- audience definition builder
- inclusion criteria
- exclusion criteria
- trigger definition
- channel recommendation
- content brief
- personalization variables
- control group
- primary success metric
- guardrail metrics
- consent availability checks
- overlap with active campaigns
- risk of over-contacting
- export formats for HubSpot, Adobe Experience Platform, Braze and Salesforce

Primary modules advanced:

- Module 6: Audience and Intervention Builder
- Module 7: Governance and Approval Engine

## Phase 7 - EU Governance, Privacy And Policy Engine

Goal: make governance a first-class product module.

Features:

- risk-tiered action matrix
- machine-enforceable policy rules
- evidence confidence thresholds
- customer-contact consent checks
- PII detection
- sensitive category safeguards
- retention policy metadata
- lawful basis and purpose metadata
- model/provider/prompt audit metadata
- reviewer decision records
- AI use-case inventory
- AI impact assessment fields
- incident log
- least-privilege tool permission model
- tool allowlist and output checks

Primary modules advanced:

- Module 7: Governance and Approval Engine

## Phase 8 - Execution Connectors And Closure

Goal: move from draft actions to verified operational and customer closure.

Features:

- Jira draft creation
- Jira status sync
- Linear or Azure DevOps draft support
- Zendesk customer recovery task
- HubSpot customer-success task
- execution accepted/completed/released states
- affected customer list
- customer closure eligibility
- response drafting
- follow-up validation prompts
- unresolved customer tracking
- closure timeline

Primary modules advanced:

- Module 5: Coordinated Action Studio
- Module 8: Resolution and Customer Closure

## Phase 9 - Outcome Learning Engine

Goal: build the defensible learning loop.

Features:

- outcome board
- before/after analysis
- matched comparison groups
- holdout/control groups
- phased rollout tracking
- action effectiveness memory
- reusable intervention knowledge
- failed-action learning
- next-best-action recommendations
- problem/action/outcome graph
- longitudinal reporting

Primary modules advanced:

- Module 9: Outcome Learning Engine

## Phase 10 - Editions And Packaging

Goal: turn the platform into sellable packages.

SME edition:

- guided setup
- CSV upload and mapping
- Zendesk, HubSpot, Jira and Teams connectors
- prebuilt taxonomies
- recommended workflows
- simple approval rules
- German/English UI
- one-week implementation path

Enterprise edition:

- SSO and SCIM
- business-unit isolation
- custom taxonomies
- custom account hierarchy
- data warehouse integration
- model routing
- advanced policy engine
- audit export
- configurable retention
- ServiceNow, Salesforce, Adobe, SAP and Azure DevOps connectors
- private tool servers

## Phase 11 - Industry Packs

Goal: make the product easier to buy and implement in specific markets.

B2B industrial pack:

- parent-account hierarchy
- site and plant context
- product family and batch
- technical complaint taxonomy
- quality routing
- product recall or compliance escalation
- multilingual customer communication

SaaS product pack:

- product-area taxonomy
- bugs and feature requests
- usage events
- onboarding and adoption journeys
- Jira and Productboard workflows
- affected-user cohorts
- beta recruitment
- renewal risk

Ecommerce pack:

- delivery, returns and payment taxonomies
- damaged product signals
- review ingestion
- service recovery
- campaign suppression
- Braze or Klaviyo audience export
- repeat-purchase measurement

Financial-services pack:

- onboarding and identity verification
- payment and fraud-review boundaries
- complaint handling
- vulnerability safeguards
- consent and communication controls
- stricter human approval
- complete decision/action lineage

## Non-Goals

- Do not build a full survey platform.
- Do not build a full CDP.
- Do not build a full campaign-delivery platform.
- Do not build a full product-management platform.
- Do not make chat the primary interface.
- Do not start with autonomous customer-facing execution.

## Post-Phase-0 Build Queue

1. Start Phase 2: make customer/account context affect impact scoring and prioritization.
