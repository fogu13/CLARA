# The three problems CLARA must solve

Recorded 15 September 2026 from the owner's instruction. Every roadmap item, pilot and thesis claim
should be checked against these three problems. Coverage below is the honest state of the
repository on that date; update the coverage notes when something material ships.

## 1. Connect multiple feedback sources, not just CSAT surveys

Care and support tickets, public reviews, surveys, and the other places customers already speak,
normalised into one signal stream.

**Coverage (about 7/10).** One normalised signal schema; CSV/JSON import (only the text column is
required); HMAC-signed webhook; pull connectors for Zendesk (tickets), Trustpilot, App Store,
Google Play and Google Business (reviews); Jira and Slack are push targets, not sources. Language
detection, authenticity review, duplicate flagging and pseudonymisation at the connector boundary.

**Gaps.** No survey-tool connector (surveys arrive only as CSV, so the "not just CSAT" claim is
true but CSAT itself is the weakest path); no Intercom, Freshdesk, HubSpot or Salesforce although
the ICP uses them; no chat, e-mail or call transcripts; source-specific numbers (star rating, CSAT
score) live in free metadata, not first-class fields; no coverage view that shows which sources
are connected and what share of the customer's voice they represent; App Store connector needs
hardening (multi-storefront fallback, retries).

## 2. Combine quantitative and qualitative data into the themes and the why

Themes that carry both the verbatims and the numbers, with an evidenced root-cause hypothesis.

**Coverage (about 5.5/10; qualitative 8, quantitative 4).** Qualitative side is strong: LLM
enrichment (sentiment, urgency, tags) with measured accuracy, three-level adaptive taxonomy,
clustering into problems, deterministic composite severity (urgency mix, volume, negative share,
time-decayed frequency), emerging-theme detection, root-cause hypothesis with evidence factors,
confidence, alternatives, contradictory evidence and validation questions, Ask CLARA with
receipts. Quantitative side is partial: volume and rate per theme, trends, outcome measurement on
signal rates, context impact (affected cohort, accounts, exposure, health, renewal) from imported
context records.

**Gaps.** No first-class numeric score on a signal (rating, CSAT, NPS, with scale), so no
theme-by-score driver analysis ("which themes explain the low scores"); no join to operational
metrics (ticket volume, handle time, refunds, churn); behavioural fields (product events, campaign
exposure) exist but are unused; corroboration across sources is a threshold (two sources) rather
than a visible triangulation per problem; no quant-versus-qual reconciliation view ("the numbers
say X, the verbatims say Y").

## 3. A blueprint for how a company sets itself up: governance, roles, resources

What the customer organisation must put in place for the loop to close: owners, approvers,
decision rights, cadence, staffing, policies, KPIs, works-council path.

**Coverage (about 3/10).** Fragments exist: roles (viewer, editor, admin), four-eyes approvals,
seeded policy rules, works-council mode and pack, AI-literacy module, compliance page, evidence
packs, a five-step in-product onboarding (product-centric), the pilot onboarding runbook and
pilot success metrics (sales-centric), the legal kit (AVV, TOMs, DPIA, Betriebsrat documents),
the EU AI Act mapping, the thesis design principles and practical implications.

**Gaps.** No coherent, customer-facing operating-model blueprint: decision-rights matrix by
consequence class, RACI (problem owner, approver, second approver, policy owner, data steward,
works-council liaison), meeting cadence (weekly triage, monthly outcome review), staffing estimate
per signal volume, KPI set for the loop (time-to-owner, approval cycle time, closure rate, measured
outcome coverage), policy-rule starter sets per industry, escalation paths, a first-90-days plan,
and the works-agreement path. No in-product governance setup wizard.

## Priority order (15 September 2026)

1. **Blueprint (problem 3).** Cheapest and highest leverage for adoption; validate it in the
   practitioner interviews (H5 ownership, H8 closure). Deliverable: an operating-model document
   with RACI, decision rights, cadence, KPIs and a 90-day plan; later a governance setup wizard.
2. **Quantitative layer (problem 2).** First-class score field on signals, theme-by-score driver
   table, per-problem source triangulation, a quant-versus-qual panel on the problem detail.
3. **Source breadth (problem 1).** A survey CSV template with score mapping first (feeds item 2),
   Intercom next, survey-tool and CRM connectors only on signed pilot demand, plus a coverage map.
