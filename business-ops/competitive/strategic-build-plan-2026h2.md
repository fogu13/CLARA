# CLARA — Strategic Build & Improvement Plan (2026 H2)
## Closing the Enterpret gap where it matters, widening it where we win

_Compiled 3 Jul 2026. Sources: adversarially-verified [Enterpret feature inventory](enterpret-feature-inventory.md)
(21 confirmed / 4 refuted claims), an honest code-level capability inventory of CLARA (this repo, 3 Jul),
`../../docs/roadmap.md`, and the business-ops GTM/pricing/VC docs. Method: 2 exploration passes
(code + business context) + 2 independent strategy designs (product sequencing; VC proof plan), synthesized._

> **Scope discipline:** every competitive claim herein traces to a **[H]/verified** line in the
> Enterpret inventory. Refuted or unverified **[U]** Enterpret claims are never credited.
> Positioning hierarchy is locked and never inverted: **(1) loop-closure USP →
> (2) learning-repository moat → (3) EU-sovereignty deal-unblocker.**

---

---

## ⚡ STATUS — updated 4 Jul 2026 (read this first)

**The entire build sequence in §2 is DONE** — Sprint 0, NOW, NEXT, and the X8 stretch all
shipped as merged, tested PRs (#39–#69), plus two LATER items pulled forward (taxonomy
hygiene, BI CSV exports) and three unplanned wins: **App Store listening L1** (+ scheduled
source sync; see social-listening-plan.md), **full EN/DE bilingual UI**, and a **marketing
landing page**. Suite: 549 backend tests. Three adversarial review cycles completed
(code 44 agents / copy / UX 72 agents); every HIGH fixed, incl. SQLite thread-safety and
mobile navigation. The codebase is no longer the critical path.

**Remaining engineering, by gate:**
| Work | Gate | Owner trigger |
|---|---|---|
| Render+Supabase recovery, then Postgres parity + tenant enforcement + pg_cron | one DB-connected session | Elvis says "supabase now" |
| Trustpilot L2 | design partner w/ business account | first signed pilot |
| Learning aggregation v2, statistical hardening | ≥5 real measured outcomes | pilots running |
| Detail-page tabs, session refresh, SSR locale cookie | design/arch decisions | post-pilot feedback |

**Proof-arc positions (§5) as of today:** P1 (loop on real data) — CODE READY, needs a real
dataset run + screen recording. P2 (eval report) — harness ready, needs labelled-set growth
(thesis track). P3 trust pack — 1 Aug deadline unchanged. P5 (real outcome) — scheduler is
live; the clock starts the day a pilot's first action is approved. **Every proof point now
waits on business motion, not code.**

**This week (pre-holiday, 6–9 Jul):** the highest-leverage engineering task left is the
Supabase/Render session (hosted demo URL for outreach during the holiday). Everything else
on the critical path is sales/thesis work — see §5/§11 dates, which all still hold.

_12 Jul 2026: X8 re-statused from cut-first to protected (§1, §2, §12) and claims-discipline items 6–9 +
never-say additions (§7) applied, per the Jul-2026 five-angle research sweep — companion doc:
[plan-strategy-implementation-2026-07.md](../../docs/plan-strategy-implementation-2026-07.md)._

---

## 0 · The strategic frame in four sentences

1. **Enterpret owns the LEFT half of the loop** (ingest → structure → understand): 50+ connectors,
   adaptive taxonomy, Wisdom Q&A with citations, MCP server, knowledge graph, SOC2 + ISO 27001/42001/27701.
   CLARA will not out-left them and should not try.
2. **Enterpret's *verified* RIGHT half is thin:** ticket create/route/reassign + alerts + human-approved
   taxonomy proposals. Its three "agentic autonomy" claims were adversarially refuted, and there is **no
   verified evidence** of outcome measurement, policy-gated action, or EU residency/AI-Act governance.
3. **The sharpest asymmetry:** Enterpret is over-certified but not EU-resident; CLARA is EU-resident but
   uncertified. The plan exploits the first half and neutralizes the second with a trust ladder.
4. Therefore: **build the minimum credible left half** (enough to survive the first 15 minutes of a
   discovery call), and **pour everything else into the right half** — govern → execute → prove → learn —
   which is simultaneously the locked positioning, the pilot success metric, and the VC story.

**Claim safety note:** "We close the loop" as a standalone slogan is **unsafe** — Enterpret 2.0 markets
"Close the Loop," a Customer Context Graph, and an MCP server. Always lead with the *mechanism*:
policy-gated action, outcome contracts, learning retrieval with confidence decay, EU governance.

---

## 1 · Gap matrix — MATCH / DIFFERENTIATE / SKIP

| Enterpret strength (verified) | Call | Reasoning (DACH pilots + VC optics) |
|---|---|---|
| **50+ connectors** (OAuth, webhook, warehouse, CSV) | **SKIP breadth, MATCH minimum** | Pilots are ≤5 companies whose stacks are known before signing. Zendesk pull + excellent CSV + one generic HMAC webhook covers ~90% of DACH mid-market feedback sources. Connector count is a post-funding hiring problem. VCs fund what's behind connectors, not catalogs. |
| **Adaptive 5-level taxonomy** (drift/dup/emerging detection, human-in-loop proposals) | **DIFFERENTIATE** | CLARA already has both halves in code: embedding discovery (`semantic_taxonomy.py`, dormant) and real governance (versioning, lock/merge/split, RBAC). Wire them into a *governed, confidence-scored, audit-trailed* bootstrap. Backs the "no taxonomy to build" promise AND reads as AI-Act-grade governance — a story Enterpret doesn't have. 2–3 levels **with** confidence beats 5 levels without. |
| **Wisdom conversational Q&A** (citations, model switcher) | **MATCH minimum (NEXT)** | Discovery calls will ask "can I chat with it?" A scoped, citation-grounded "Ask CLARA" with a confidence score and explicit refusal on thin evidence is enough. Model switcher = feature theater, **SKIP permanently**. |
| **MCP server** (Slack/ChatGPT/Claude/Cursor) | **MATCH cheap (NEXT stretch)** | Read-only FastMCP over existing endpoints is S/M effort and yields a disproportionate VC-deck screenshot ("CLARA answers inside Claude/Cursor"). **Shipped — now protected:** interop is where the category is going (Gartner: 1/3 of UX shifting to agentic front-ends by 2028, 40% of enterprise apps embedding agents by end-2026; Enterpret bet on MCP Server v2, May 2026). |
| **Customer knowledge graph** (accounts/users/opportunities) | **MATCH at current scale** | The context model (hierarchy, value, health, **consent**) + `context_impact.py` value-weighted impact already exist. Surface them; do NOT build a CDP. Consent fields are a quiet EU differentiator Enterpret doesn't surface. |
| **Dashboards** | **DIFFERENTIATE via outcome reporting** | Enterpret's G2 complaint is *inflexible reporting*. Don't answer with a report builder (a quarters-long swamp). Answer with time-series (recharts is installed, unused) + exportable, audit-ready **evidence packs**: problem → action → measured outcome with confidence intervals. DACH buyers file PDFs. |
| **Act ceiling** (ticket create/route, alerts) | **DIFFERENTIATE hard — the USP** | Enterpret verifiably stops at "ticket created." CLARA's story: "ticket created *under policy*, outcome *measured*, learning *stored*." Pending branches + moving real Jira/Slack push into the normal approval flow makes this true in code, not slides. |
| **Certifications** (SOC2 T2, ISO 27001/42001/27701) | **SKIP now; DIFFERENTIATE with residency + trust pack** | Certs are money+time a €3.4k/mo burn can't fund. Pilots at €3–5k need: security page, AVV/DPA, subprocessor register, EU residency, audit-log export — all achievable in days. Certs are LATER, post-funding (§6 ladder). |
| **SSO/RBAC** | RBAC **done**; SSO/SCIM **SKIP until LATER** | No €3–5k pilot demands SAML. Needed for €12–30k renewals — WorkOS/Supabase SSO post-thesis. |
| **"Autonomous agents" marketing** | **SKIP — and weaponize** | Refuted even for Enterpret. CLARA's honest counter: *no autonomous actions, ever — policy-gated, human-approved, audited.* In DACH fintech that's a feature, not a limitation. |

---

## 2 · Build sequence — three horizons (holiday-adjusted)

Capacity reality: solo founder + strong AI tooling; **away 10–26 Jul**; thesis tax ≈30% in August;
thesis due September. Effort classes: S = 1–2 days, M = 3–6 days, L = 7–12 days.

### Sprint 0 — 6–9 Jul (the 4 days before holiday)

| # | Item | Concretely | Effort |
|---|---|---|---|
| N1 | **Merge the pending branches** (`fix/code-review`, `fix/review-frontend-polish`) | 23+ files ready & tested: `/triage/resume` (closes the approval→action→measure→learn loop over HTTP), rate-limiter wiring, read-route auth, learning workspace fix, frontend fixes. Do FIRST — `main.py`/`workflow.py` are conflict hotspots; nothing else touches them until this lands. | S |
| N2a | **Start: real action push in the normal flow** | In `services/workflow.py`: on approval, call `connectors/jira.py`/`slack.py` (today only reachable via the test endpoint). Idempotency key, failure states, external ticket ID + audit record written back onto the action. Draft mode remains the un-configured fallback. | M (start) |
| M0 | **Instrument `product_events`** | One append-only table (tenant_id, event_type, entity_id, ts, metadata JSONB) under existing RLS + emit events from ingestion/insight-view/approval/execution paths. Must exist **before pilot 1 ingests data** so longitudinal metrics accrue from day 1 (§8). | S/M |

### NOW — 27 Jul–22 Aug (pilot-critical)

| # | Item | Concretely | Effort | Unlocks |
|---|---|---|---|---|
| N2 | **Finish real action push** | Complete N2a; demo choreography: approve in CLARA → ticket appears in Jira live. | M | The single moment separating CLARA from Enterpret's verified ceiling. |
| N3 | **Wire embedding-taxonomy bootstrap** | pgvector (migration `003` exists) + `POST /taxonomy/bootstrap` calling `discover_themes()`/`apply_governance()`; proposals land as versioned drafts with confidence; accept/reject review UI in `taxonomy/`. | M | Makes "no taxonomy to build" + "no fine-tuning" TRUE. Core of demo-wow №1. |
| N4 | **Expose merge/split in taxonomy UI** | Backend supports rename/lock/merge/split + versioning; UI has only rename/lock. | S | Governance story complete: AI proposes, human governs, versions audit. |
| N5 | **Time-series + emerging radar** | recharts (installed, unused): per-theme trend lines; surface `services/emerging.py` scoring in a dashboard panel. | S/M | Kills the "single-point aggregates" credibility gap. |
| N6 | **Language detection** | Detect at ingestion (lingua-py or cheap LLM tag); stop hardcoding `"en"` in `zendesk.py`; store original + normalized. NOT full UI i18n. | S/M | A German ticket gets pasted in minute ten of every DACH demo. |
| N7 | **Generic HMAC webhook intake** | `POST /ingest/webhook` + per-source field-map template reusing the CSV validation pipeline; move connector config from in-memory to Postgres while there. | S | "We ingest from anything that can POST" — neutralizes connector-count objection. |
| N8 | **Pilot onboarding kit** | Per-ICP demo datasets from the 3-industry real-data evals; one-command workspace seed/reset; scripted "CSV → bootstrap → first insight" under 30 min; pre-wired demo Jira project. | S | Repeatable discovery-call choreography; attacks Enterpret's "hard setup" G2 complaint. |

### NEXT — 24 Aug–27 Sep (pilot-proof + fundable metrics; thesis tax applies)

| # | Item | Concretely | Effort | Unlocks |
|---|---|---|---|---|
| X1 | **Scheduled re-measurement** | pg_cron or APScheduler re-runs `outcome_engine.py` at T+7/T+30 post-execution; significance tests reused from `evals/harness.py`. **August item — it IS a thesis chapter.** | M | Kills the "manual/simulated" asterisk. THE pilot metric + pre-seed keystone (P5). |
| X2 | **Evidence-pack export** | Per-problem PDF/CSV: signals → taxonomy (confidence) → approved action + policy trail → outcome Δ + CI. Server-rendered from existing data. | M | The anti-"inflexible reporting" answer; the DACH audit artifact; the VC proof exhibit. |
| X6 | **EU-governance pack** | `/compliance` route grows: audit-export UI, model card, residency statement; off-product: AVV/DPA finalization, subprocessor register. Verify hosting pinned to EU regions. **Thesis-week item (mostly writing).** | S | Pillar-3 deal-unblocker at near-zero code. |
| X7 | **Zendesk incremental sync** | Cursor-based scheduled sync (pagination already landed in the pending branch). | S/M | Pilots see this-morning's tickets. |
| X4 | **Learning-repository surfacing** | `learnings` route: "for problem class X, action Y improved Z in N/M cases," with confidence decay visible; log reuse events. | M | Pillar-2 moat made visible; the compounding-asset VC slide, backed by screenshots. |
| X5 | **Slack weekly digest** | Reuse `connectors/slack.py`: weekly emerging + open-loop status per workspace. | S | Retention hook — CLARA in their Slack every Monday. |
| X3 | **"Ask CLARA" scoped Q&A** | pgvector retrieval (enabled by N3) over signals/problems → grounded answer + citation links + confidence + explicit refusal below evidence threshold. One route, one panel. **September, full velocity.** | M/L | Neutralizes the Wisdom objection; confidence-scored answers are differentiation, not parity. |
| X8 | *(stretch)* **Read-only MCP server** | FastMCP wrapper: `list_problems`, `get_evidence`, `get_outcomes`. | S/M | VC screenshot. **Shipped. Protected status — if October slips, cut X3 conversational polish first.** |
| G1 | **GDPR Art. 17/20 endpoint** | Self-service per-customer data deletion + export. Most-asked vendor-questionnaire item that's cheap to build. Target ~22 Aug. | S/M | Trust-ladder Rung 0 product substitute (§6). |

### LATER — Oct 2026–Jun 2027 (post-thesis / post-funding)

- **SSO/SAML + SCIM** (WorkOS or Supabase SSO) — unblocks €12–30k enterprise procurement.
- **5–8 demand-driven connectors** (Intercom, HubSpot, app-store reviews, Gorgias) — built only against signed-pilot demand, never speculatively.
- **Taxonomy drift + duplicate-detection jobs** — extends bootstrap into a living taxonomy; human-in-loop stays the differentiator.
- **Full conversational Q&A** (memory, corpus-wide, follow-ups).
- **Full DE UI i18n** (+ third language on demand).
- **Warehouse EXPORT** (scheduled Parquet/CSV out or read replica) — satisfies "we need it in our BI" without building sync infra.
- **ISO 27001 readiness → certification** (§6, EXIST-funded).
- **Per-tenant EU LLM routing** (EU-region inference endpoints) — hardens Pillar 3 for fintech.

---

## 3 · Wire, don't build — cheapest wins ranked

1. **Merge the pending branches** — days of review-fix work for the entire USP loop. Nothing approaches this leverage-per-hour.
2. **recharts** — installed, imported nowhere. One sprint converts "single-point aggregates" into trends.
3. **`services/emerging.py`** — scoring wired in the backend, barely surfaced. Pure frontend for a headline demo moment.
4. **Taxonomy merge/split UI** — backend fully supports with versioning; UI exposes 2 of 4 ops.
5. **3-industry real-data evals → per-ICP demo datasets** — the thesis eval investment becomes sales collateral for free.
6. **`semantic_taxonomy.py`** — the one M-sized wiring job that makes two locked marketing claims true.
7. **`context_impact.py`** — real value-weighted impact computation; surface "€-weighted problem ranking."
8. **`connectors/slack.py`** — real push already; reuse for the weekly digest.

## 4 · Do-not-build list (scope-creep guardrails)

- **50+ connector catalog** — ≤5 pilots with known stacks; webhook + CSV covers the rest.
- **Warehouse ingestion** (Snowflake/BigQuery) — no DACH mid-market pilot is feedback-in-warehouse-first.
- **CDP / expanded customer graph** — existing context model suffices; Salesforce-graph is a swamp.
- **Survey/NPS collection** — stay downstream of collection tools; never compete with your sources.
- **Custom report builder** — evidence packs answer the same complaint in 1/10th the time.
- **Q&A model switcher** — feature theater.
- **Autonomous agents** — refuted even at Enterpret; automating away human approval destroys Pillar 3 and invites AI-Act high-risk classification.
- **SSO/SCIM before October** — no €3–5k pilot requires SAML.
- **SOC2/ISO certification now** — a money problem, not a code problem; ship the governance pack instead.
- **Full DE UI i18n in NOW** — German *data* handling is table stakes; German *chrome* is not.
- **Anomaly-alert agent library** — Enterpret's version is refuted marketing; the Slack digest covers the real need.
- **Mobile app / browser extension.**

---

## 5 · VC proof arc — 7 dated proof points

The investable narrative: *"Analytics is commoditized — Enterpret won that half. The unclaimed half is
governed action with measured outcomes, and EU regulation makes governance a purchase requirement.
CLARA is the only product where that loop mechanism exists in code."* Each proof point is something the
product **demonstrates**, not says.

| # | Proof point | Product must demonstrate | Earliest credible | Needed for |
|---|---|---|---|---|
| P1 | Governed loop end-to-end on real data | Live tenant: ingest → confidence-scored triage → policy gate → RBAC approval → real Jira/Zendesk write → audit export. One unbroken screen recording, **no simulation flags**. | **~8 Aug** | EXIST |
| P2 | Quality measured, not claimed | Published eval report: 60→100-item golden set, significance methodology, ~90% sentiment across 3 real industries, confidence in UI. Weaponizes Enterpret's "no confidence scores" G2 complaint. | **~8 Aug** | EXIST |
| P3 | Verifiable EU-sovereignty | All-EU subprocessor register, residency architecture doc, AI-Act deployer mapping, local-model option demoed once. Crowned by a **signed AVV from a real DACH customer**. | Pack **~1 Aug**; signed AVV **~end Aug** | EXIST (pack) / pre-seed (AVV) |
| P4 | DACH willingness to pay | 3 paid pilots €3–5k, cash collected, **pre-negotiated annual conversion price in each contract**. LOIs substitute for EXIST. | LOIs **31 Aug**; paid **27 Sep** | EXIST → pre-seed |
| P5 | **One outcome contract completed on real (non-simulated) data** | Contract at action time, baseline auto-captured from a real source (e.g. Zendesk ticket volume), window elapses, verdict displayed. **The single most important pre-seed artifact — the thing Enterpret verifiably does not have.** | **~mid-Sep** (X1 live early Aug + measurement window) | Pre-seed |
| P6 | Learning repository compounds | Learning from experiment 1 retrieved (decay visible) into proposal N; reuse events logged; ≥5 completed real experiments. | **~mid-Nov** | Pre-seed (instance) / seed (rate) |
| P7 | Pilot → ARR conversion | First €10–20k annual conversion; €30–60k ARR per OKR. | Q4-26 / Q1-27 | Seed |

**Stage gates:** **EXIST submission target 15 Sep 2026** (P1 + P2 + P3-pack + LOIs + thesis-IP letter;
pre-GmbH status is an *asset* — EXIST requires not-yet-founded). **Pre-seed conversations open ~15 Oct**
with 12 weeks of instrumented metrics and a dated pen-test report. **Seed H2 2027** (P6 as a rate, P7 with retention, ISO 27001 in audit).

## 6 · Trust ladder (uncertified solo founder → DACH fintech)

Core insight: at pilot scale, German vendor-risk teams accept **contractual + technical evidence in lieu
of certification** — if the pack is complete and professional. Certs unblock deal *size*, not deal *existence*.

| Rung | What | When / cost | Unblocks |
|---|---|---|---|
| 0 | **Trust pack**: AVV (Art. 28) + TOMs, all-EU subprocessor register w/ change notification, Art. 30 records, DPIA template, professional + cyber insurance (~€1–2k/yr). Product substitutes: audit-log export ✓, RLS policy dump, RBAC screenshots, **Art. 17/20 deletion/export endpoint (G1, ~22 Aug)**. | **~1 Aug** / €1–2k legal review | €3–5k pilots; fintech pilots on pseudonymized data |
| 1 | **External pen test** (German boutique, web-app scope, remediation letter) + CAIQ-Lite filled once, reused forever. | Aug–Sep / €5–10k; **report dated ≤15 Oct** (data room) | €10–25k contracts; production-data fintech pilots |
| 2 | **ISO 27001 readiness** (ISMS, risk register, internal audit, consultant attestation; Secfix/DataGuard-class tooling). | Q4-26–Q1-27 / €10–20k, **EXIST-funded** | €25–50k deals; regulated mid-market w/ contractual cert commitment |
| 3 | **ISO 27001 certification.** Defer SOC2 (US-exit artifact); bundle ISO 42001 with first surveillance audit 2028. | Q2→Q4 2027 / €15–30k total | €50k+ / hard-gated RFPs |

**The line to a fintech CISO:** "Residency today, certification on this dated & budgeted roadmap, audit
rights in the contract meanwhile." The published cert roadmap is itself a trust artifact.

## 7 · Claims discipline

**Defensible now:**
1. "Every automated action passes a **policy gate** with configurable thresholds, RBAC, and an exportable audit trail." *(Enterpret's verified ceiling: routing/alerts; no policy engine.)*
2. "Actions are bound to **outcome contracts** — a measurable target defined before acting, measured after." *(Capability-phrased until P5; then "demonstrated with customers.")*
3. "**EU-resident by design**: data + inference stay in the EU; full subprocessor transparency; AI-Act deployer support." *(No verified Enterpret EU residency.)*
4. "**Confidence scores with significance testing** on a published golden set." *(Literal G2 complaint about Enterpret.)*
5. "**First governed action within days from a CSV export** — no multi-week connector project." *(Once the time-to-first-insight metric backs it.)*
6. "Our approval gate is your **Article 50 compliance**" — human editorial review (Art 50(4)) stamped and exportable; auto-published text carries the disclosure automatically. *(Claimable once W2 ships — in progress Jul 2026.)*
7. "**§7-UWG-safe by design**: we never send surveys." CLARA mines signals that already exist (tickets, reviews, store feedback) — no consent-requiring outreach (BGH VI ZR 225/17). *(Turns the existing "stay downstream of collection" scope into a legal advantage in Germany.)*
8. "**Works-council-ready.**" Aggregate-only employee analytics, role-redacted exports, Betriebsrat information sheet included. *(Claimable once W1 ships — in progress Jul 2026.)*
9. **The Gartner frame for decks/thesis:** ">40% of agentic-AI projects will be cancelled by 2027 for unclear business value and inadequate risk controls (Gartner, Jun 2025) — outcome contracts answer the first, the policy gate answers the second."

**Never say:** standalone "we close the loop" • "autonomous agents" (poison: undermines the governance USP,
invites AI-Act high-risk classification) • anything about connector breadth or taxonomy automation vs
Enterpret's verified left half • any *security-posture* superiority (we're uncertified — claim residency
and transparency, never "more secure") • "our learning engine improves outcomes" while learning data is simulated •
don't lead with "AI Act high-risk deadlines" fear (the Digital Omnibus moved high-risk deadlines to Dec 2027 —
informed buyers know; Art 50 transparency still bites 2 Aug 2026) • never claim outcome-measurement uniqueness vs
*Amplitude* without the qualifier "contracted closure with approval-gated cross-system execution" (Amplitude
observes, recommends and acts inside its own analytics; it does not contract and verify cross-system).

**Claims needing product work:** (A) real-outcome proof → X1, true ~15 Sep. (B) learning reuse visible in UI
→ X4 + ≥5 real experiments, ~15 Nov. (C) cited Q&A → X3, Oct — never displacing P5 work.

## 8 · Metric instrumentation (build in Sprint 0, before pilot 1)

One append-only `product_events` table under existing RLS + weekly rollup. **No US analytics vendor** —
it would contaminate the subprocessor register; "we don't even use US analytics" is itself a sales line.

| Metric | Proves | Captured at |
|---|---|---|
| Time-to-first-insight | Onboarding speed; monetizes "hard setup" G2 complaint | ingest-complete + first insight-view events |
| % feedback auto-triaged above confidence | Model quality → gross-margin story | triage output + human-override events |
| Approval-cycle time | "Governance ≠ slow" — the #1 objection to policy gating | existing approval audit-log transitions + rollup |
| Outcome-contract completion rate + **`real_data_source` flag** | THE pre-seed metric; the flag separates simulated vs real — mixing them in a VC chart is a diligence landmine | outcome engine + metric-pull job |
| Learning-reuse rate | The moat compounds; switching cost grows with tenure | retrieval calls + proposal-composition events |
| Approver-WAU + actions/week/tenant | CLARA is in the operating workflow, not a monthly dashboard | session + execution events |

By ~15 Oct: ~12 weeks of longitudinal data across up to 5 tenants → real charts in the pre-seed deck.

## 9 · Demo-wow choreography (mapped to Enterpret's G2 weaknesses)

1. **The 30-minute cold start** *(needs N3+N8)* — prospect exports helpdesk CSV → upload → bootstrap proposes a confidence-scored taxonomy → they accept/reject themes live → first insights before the call ends. Counter to "setup is hard and slow."
2. **Close a loop, live** *(N1+N2; devastating follow-up after X1)* — problem → action → policy gate fires → approve → real Jira ticket on screen → re-measurement auto-scheduled. Next call: "here's the outcome we measured since we spoke." Nobody in the category demos this.
3. **Confidence with receipts** *(exists — choreograph)* — every decision carries confidence; open the eval page: golden set, significance tests, three industries. Thesis-grade rigor as a sales asset.
4. **Emerging radar, in German** *(N5+N6)* — "this issue first appeared in German-language tickets 9 days ago; here's its trajectory."
5. **The EU-sovereignty page** *(X6)* — open `/compliance` in-product: audit export, residency, model card, consent fields. The moment the procurement objection dies.

## 10 · Risk killers (the five diligence questions)

| Question | Neutralizing artifact | Deadline |
|---|---|---|
| "Does the university own the thesis code?" | Written IP clearance (Freigabeerklärung) + commit history showing post-thesis evolution | **31 Aug** (blocks EXIST) |
| "Solo founder." | EXIST-funds-the-team plan (stipend covers up to 3) + first-hire profile; 2 signed advisor agreements (technical + DACH-fintech GTM) by Sep; shipped-vs-roadmap velocity ledger; DEPLOY.md/runbooks for bus factor | Sep |
| "Enterpret launches an EU region — then what?" | One-page moat memo: residency is the *wedge*; the moat is the per-tenant learning corpus (show a 90-day learning export from a real pilot) + governance workflow embedded in the customer's approval process. An EU region gives them hosting, **not architecture** — policy gates, outcome contracts, learning retrieval don't exist in their verified product; post-2.0 investment is all left-half. | Oct (pre-seed) |
| "Uncertified and selling to fintech?" | In order of power: signed AVVs from pilot fintechs → pen-test report (≤15 Oct) → published budgeted cert roadmap → product evidence bundle (audit export, RLS dump, deletion endpoint, EU subprocessor list) | rolling |
| "Pre-revenue." | 3 executed paid-pilot agreements with cash receipts + pre-negotiated conversion prices (makes Q1-27 ARR contractually visible); ≥20 qualified DACH conversations in CRM; unit economics. For EXIST: LOIs + P1 demo suffice — **don't delay the submission waiting for paid conversions.** | 27 Sep |

## 11 · Trust & Evidence track (thesis interleave)

The thesis and the business share one evidence engine — run them as one track:

- **Next week (post-server-fix): local-vs-cloud model benchmark** on the same labelled set — accuracy,
  reproducibility (local pinned: fixed seed, greedy decoding), cost, residency. Feeds the thesis
  (reproducibility finding) AND Pillar-3 sales ("local model option, demoed").
- **Labelled set 60 → 100+** — powers the significance claims (currently underpowered at n=60,
  McNemar p≈1.0 on urgency) and upgrades P2.
- **X1 scheduled re-measurement** = a thesis chapter AND the P5 keystone. Schedule in August when
  thesis tax bites — it's dual-use.
- **`real_data_source` separation is absolute** — simulated vs real outcome data never mixes in any
  chart, deck, or thesis table. The eval harness's honesty is a differentiator; guard it.

## 12 · Sequencing summary (critical path)

```
6–9 Jul     N1 merge branches · N2a real-push start · M0 product_events
10–26 Jul   HOLIDAY (no scheduled work)
27 Jul–8 Aug  N2 finish · N3 bootstrap · N5 charts → P1+P2 artifacts recorded ~8 Aug
            Trust pack finalized ~1 Aug · X1 re-measurement live early Aug
11–22 Aug   N4 N6 N7 N8 · G1 deletion endpoint · pen test booked · first AVV signing
24 Aug–15 Sep  X2 evidence packs · X6 governance pack · X7 sync · thesis-IP letter (31 Aug)
            → EXIST submitted 15 Sep · P5 first real outcome completes ~mid-Sep
15–27 Sep   X4 learnings UI · X5 digest · X3 Ask-CLARA · 3 paid pilots closed 27 Sep
Oct         X8 MCP (stretch) · pre-seed conversations open ~15 Oct
```

**Execution risks:** `main.py` (~46K) and `workflow.py` (~49K) are monolith hotspots — merge N1 first,
then serialize all work through those files (never two concurrent branches). Demo Jira must be pre-wired
per workspace (fold into N8). August: only dual-use (thesis-synergy) items scheduled; X8 (MCP/interop follow-on
work) is protected; X3 conversational polish is the designated sacrifice.
