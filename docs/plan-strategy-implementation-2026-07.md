# CLARA — Strategy-Implementation Plan (Jul 2026 research findings)

_Compiled 12 Jul 2026 from the five-angle verified research sweep (competitors / DACH market /
regulation / academic / category). Companion to `../business-ops/competitive/strategic-build-plan-2026h2.md`
(the H2 build plan): this plan **adds** the workstreams that research showed missing; it does not
re-sequence what already shipped. Positioning hierarchy unchanged: loop-closure USP → learning-repository
moat → EU-sovereignty deal-unblocker — but the wedge is now explicitly the **combination**, since every
single differentiator was partially matched in the last 9 months (Amplitude behavioral-outcome agents,
Sprinklr audit trails, Medallia+Ada policy-aware execution, Dovetail SMB agents, Zendesk resolution-priced
support loop)._

Effort classes as in the H2 plan: S = 1–2 days, M = 3–6 days, L = 7–12 days.
Calendar constraints honoured: holiday 10–26 Jul; ~30% thesis tax in August; thesis due September.

---

## W1 · Works-council-ready mode («Betriebsrat-Modus») — M

**Why (verified):** §87(1) Nr. 6 BetrVG gives works councils co-determination over any system
*objectively capable* of monitoring employee behaviour/performance — intent irrelevant per case law.
CLARA's audit trail, owner routing, approval-cycle metrics and per-approver stats are exactly that.
Any pilot at a customer with a Betriebsrat can stall for weeks without this. No US/UK competitor
engineers for it → cheap, DACH-unique differentiator.

**Design (per-workspace flag `works_council_mode`, default off):**
1. **Aggregate-only employee views.** Any metric derivable per-employee (approval-cycle time,
   actions/approver, override rates) is exposed only as workspace aggregates with a k-anonymity
   floor (suppress groups < 5). Applies to API responses and dashboard panels alike.
2. **Role-redacted audit exports.** Non-DPO/admin audit exports replace user ids with role labels
   (`cx_lead`, `approver`) — the audit *chain* stays intact for compliance, the *person* is not
   traceable in routine exports. Full-identity export stays available to the designated admin role
   (the works-council agreement will typically require naming who).
3. **UI:** settings toggle + a banner on affected panels ("aggregated under works-council mode").
4. **Paper artifact:** a one-page **Betriebsrat-Information** (DE) describing data categories,
   what is/isn't monitored, retention — template the customer can take into their co-determination
   process. Lives in `business-ops/legal/`.

**Where:** `apps/api/app/main.py` (metrics/read endpoints — serialize through one redaction helper,
don't scatter conditionals), `domain/models.py` (WorkspaceSettings flag), audit-export path in the
existing audit-export service, frontend settings + affected dashboard panels. One helper:
`services/works_council.py` (`redact(payload, mode, role)`), so the rule lives in ONE place.

**Acceptance:** with the flag on, an automated test walks every read endpoint and asserts no
response contains a per-user performance-capable field for a non-admin token; the Betriebsrat
one-pager exists in DE; demo script updated ("and for your works council, this switch…").

**When:** NEXT window (11–22 Aug), before the first pilot with >50-employee customer. Backend-first.

---

## W2 · Article 50(4) editorial-review productisation — S/M

**Why (verified):** Art 50 transparency bites 2 Aug 2026 (Digital Omnibus deferred high-risk, NOT
Art 50). Art 50(4) exempts AI-generated text that underwent **human review with editorial
responsibility** — CLARA's approval gate IS that mechanism. Nobody else can say "our approval gate
is your Article 50 compliance."

**Design:**
1. On approval, stamp the action/content record `human_reviewed = true` + reviewer + timestamp
   (mostly exists in the audit record — surface it as a first-class field).
2. Any **auto-executed** action whose output is customer-facing text gets an automatic AI-disclosure
   line appended (configurable template, DE/EN), and the execution record notes `disclosure_applied`.
3. `/compliance` page gains an "Article 50 status" card: which outbound content classes are
   human-reviewed (exempt via 50(4)) vs auto-published (disclosed), with export.
4. Sales/messaging: claims-discipline addition (see W8).

**Where:** `services/workflow.py` approval path + `services/action_push.py` payload builder
(disclosure injection), compliance route frontend. Small migration for the two fields if not
already derivable from `actions_log`.

**Acceptance:** e2e test: auto-executed customer-facing draft carries disclosure; approved one
carries reviewer stamp and no disclosure; compliance card renders both counts.

**When:** NOW window (27 Jul–8 Aug) — it's small and the 2 Aug date makes it a launch-moment story.

---

## W3 · AI-literacy onboarding module (Art 4 discharge) — S/M

**Why (verified):** Art 4 AI-literacy duty has applied to ALL deployers since 2 Feb 2025 — every
buyer must train the staff who operate CLARA. A built-in module discharges *their* legal duty at
near-zero cost to us and is a procurement-friction reducer.

**Design:** a 5-screen in-product explainer (first login + always in Help): how triage works
(signals → confidence-scored themes), known limitations (n=60 significance caveats — honesty as
feature), when and how to override, what the approval gate does, where the audit trail lives.
Plus a downloadable **AI-Literacy Pack** PDF (same content + model card + link to eval report)
for the customer's compliance folder. **Do NOT track per-user completion by default** (conflicts
with W1 — works-council trap); offer workspace-level "pack delivered" attestation instead.

**Where:** frontend onboarding flow; PDF served from `/compliance`; content sourced from the
existing eval report + model card (X6 artifacts — reuse, don't rewrite).

**Acceptance:** new user sees the flow once; PDF downloads with workspace name + date stamped;
X6 governance pack references it.

**When:** NEXT (11–22 Aug), after X6 content exists to reuse.

---

## W4 · Auto-proposed outcome contracts + honest quasi-experimental scoring — M

**Why (verified + academic):** The differentiator currently demands customer discipline (define
metric, wait a window) — the exact discipline whose absence created the feedback-action gap; the
Uber apology field experiment (Halperin et al., Economic Journal 2022) shows well-meant recovery
actions can have null or *negative* effects, so measurement must be default-on, not opt-in.
Naive before/after deltas are also weak evidence; interrupted-time-series (segmented regression)
and, later, synthetic difference-in-differences (Arkhangelsky et al., AER 2021) are the credible
designs when RCTs are infeasible.

**Design:**
1. **Default contract proposal:** at approval time, if no contract set, propose one automatically:
   metric = 7-day moving rate of the action's theme signal volume (rate-normalised — the frequency
   fix already landed), window = 30d with a T+7 early read, baseline = trailing 28d. One-click
   accept/edit in the approval dialog. Zero-input closure becomes the default path.
2. **ITS scoring:** extend the outcome engine: segmented regression on the theme's daily rate
   (level + slope change at action date), report effect with CI; automatic fallback to plain Δ when
   < N observations, clearly labelled "insufficient data for ITS". Reuse the significance machinery
   from `evals/harness.py` (McNemar infra shows the pattern; ITS needs OLS — statsmodels or a
   small closed-form implementation to avoid a heavy dep).
3. **`real_data_source` flag discipline** (already in the H2 plan §8) applies unchanged: ITS runs
   on real-source metrics only; simulated stays quarantined.

**Where:** `services/workflow.py` (proposal at approval), the outcome engine (`outcome_engine.py`)
+ scheduled re-measurement (X1 — this workstream **merges into X1**, it is not additional scope so
much as X1 done right), approval-dialog frontend.

**Acceptance:** approving an action with no contract always yields a proposed contract; a seeded
30-day series produces an ITS effect estimate with CI; sparse series produces the labelled fallback;
thesis Ch-3/6 cite the same design (dual-use).

**When:** early Aug with X1 (its scheduled slot). **This is the P5 keystone — highest priority of
this whole plan.**

---

## W5 · DORA / NIS2 vendor pack (fintech-pilot unblocker) — S

**Why (verified):** NIS2 in force in DE since 6 Dec 2025 (~29k entities; supply-chain security
clauses flow down to SaaS vendors); DORA makes fintech customers demand Art 30 contract clauses and
Register-of-Information data from every ICT provider — and fintech (Trade-Republic-like) is a target
ICP. These arrive as security questionnaires; having the pack pre-written collapses weeks to days.

**Design (documents, minimal product):**
- `business-ops/legal/dora-ict-annex.md`: DORA Art 30 contractual clauses annex to the AVV +
  the customer-side Register-of-Information data row (all fields pre-filled for CLARA).
- `business-ops/legal/nis2-supply-chain-statement.md`: security-measures statement mapped to
  BSIG supply-chain expectations + incident-notification SLA (product already has audit export;
  name the contact path and clock).
- Product: subprocessor register + incident contact rendered on `/compliance` (mostly exists via X6).

**Acceptance:** a fintech security questionnaire can be answered from the pack alone; AVV annex
reviewed in the same legal pass as the trust pack.

**When:** fold into the ~1 Aug trust-pack finalisation (same legal review session).

---

## W6 · MCP server — re-status from "cut-first" to "protected, post-P5" — S/M

**Why (verified):** Gartner projects a third of user experiences shifting to agentic front-ends by
2028 and 40% of enterprise apps embedding agents by end-2026; Enterpret shipped MCP Server v2
(May 2026) and bet its strategy on interop breadth. The app UI is a depreciating asset; the durable
product is the governed data layer agents call. A read-only FastMCP over existing endpoints
(`list_problems`, `get_evidence`, `get_outcomes`, `get_learnings`) is S/M and future-proofs the moat.

**Change:** X8 keeps its October slot but loses its "first thing cut" designation — if anything
must be sacrificed in October, cut X3 conversational polish before X8. Rationale: X3 matches a
competitor feature; X8 positions for where the category is going.

**When:** October, unchanged slot; protected status.

---

## W7 · Pricing & anchor reframe — doc-only, immediate

**Why (verified):** Enterpret's entry is ≈$1,000/month (~$12k/yr) per review-site data (validate in
discovery calls — review-site pricing is weakly sourced). The "accessible vs $25–64k incumbents"
frame is stale and over-claims.

**Change:** `business-ops/05-pricing-and-financial-model.md`: anchor entry tier vs "~$12k/yr closest
competitor," keep €3–5k pilots and pre-negotiated conversion; deck slides updated. Add a discovery-
call question to verify Enterpret's actual quote in-market ("what were you quoted?").

---

## W8 · Claims & messaging additions (claims-discipline update) — doc-only, immediate

Append to the H2 plan §7 defensible-claims list:

6. **"Our approval gate is your Article 50 compliance"** — human editorial review (Art 50(4))
   stamped and exportable; auto-published text carries the disclosure automatically. *(After W2.)*
7. **"§7-UWG-safe by design: we never send surveys."** CLARA mines signals that already exist
   (tickets, reviews, store feedback) — no consent-requiring outreach (BGH VI ZR 225/17). Turns the
   existing "stay downstream of collection" scope into a *legal* advantage in Germany.
8. **"Works-council-ready."** Aggregate-only employee analytics, role-redacted exports,
   Betriebsrat information sheet included. *(After W1.)*
9. **The Gartner frame for decks/thesis:** ">40% of agentic-AI projects will be cancelled by 2027
   for unclear business value and inadequate risk controls (Gartner, Jun 2025) — outcome contracts
   answer the first, the policy gate answers the second."

**Never-say additions:** don't lead with "AI Act high-risk deadlines" fear (Omnibus moved them to
Dec 2027 — informed buyers know); never claim outcome-measurement uniqueness vs *Amplitude* without
the qualifier "contracted closure with approval-gated cross-system execution" (Amplitude observes,
recommends and acts inside its own analytics; it does not contract and verify cross-system).

---

## Sequencing (delta view — integrates with H2 plan §12)

```
Immediate (docs, no code)   W7 pricing reframe · W8 claims additions
27 Jul–8 Aug (NOW)          W2 Art 50(4) product (small; 2 Aug story) · W4 merged into X1 (P5 keystone)
~1 Aug                      W5 DORA/NIS2 pack into the trust-pack legal review
11–22 Aug (NEXT)            W1 works-council mode (before first Betriebsrat pilot) · W3 AI-literacy module
October                     W6 MCP (protected, not cut-first)
```

**Do-not-build guardrails still apply.** Nothing here adds connectors, CDP, surveys, or autonomy.
W1–W5 total ≈ 12–18 engineering days against the existing calendar; W4 is not net-new (it is X1
specified correctly); W5/W7/W8 are writing.

## Research-maintenance (standing)

- Quarterly re-run of the adversarial competitor inventory, scope = **buyer's alternatives** (incl.
  Amplitude, Zendesk/Intercom, HubSpot Breeze/Agentforce, do-nothing), not only category rivals.
- Monitors: Enterpret changelog · Forrester CFMAS notes · KI-MIG Bundestag progress · Digital-Omnibus
  secondary acts. (Automatable with a change-monitor; alert on real content changes only.)
- One hour with a German IT-/employment-law practitioner to sanity-check W1 (§87 BetrVG scope) and
  the §7 UWG positioning before they go into sales material.
