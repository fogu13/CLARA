# CLARA — Investor Data-Room Checklist

**Purpose:** A pre-seed/seed due-diligence index. Everything an EU-focused investor will ask for, mapped to what CLARA can hand over today versus what is being prepared. Honesty is a feature: items are marked truthfully, and known gaps are flagged rather than buried.

**Status legend**
- ✅ **Ready** — exists, current, and can be shared on request.
- 🟡 **To-prepare** — planned or partially drafted; owner and effort noted.
- 🚩 **Flag** — a known risk or open question we surface proactively.

**Company:** CLARA — EU-sovereign, governed, self-improving Voice-of-Customer engine
**Stage:** Bootstrapped to validated product; optional/opportunistic pre-seed
**Founder:** Solo technical founder, Berlin
**Last updated:** 2026-06-28

---

## How to read this room

CLARA is deliberately early on corporate formality and deliberately mature on product, validation, and compliance. We would rather show you a working, tested product with a real governance posture and an honest list of gaps than a polished cap table around vapor. The three items we flag hardest — **thesis-origin IP**, **solo-founder / co-founder gap**, and **entity conversion (Freiberufler → Gewerbe/GmbH)** — are the ones most material to a pre-seed decision, so they appear at the top of their sections.

---

## 1. Company & Corporate

| # | Item | Status | Notes |
|---|------|--------|-------|
| 1.1 | Legal entity registration | 🚩 / 🟡 | Founder currently operates as **Freiberufler with USt-IdNr**. Because CLARA is a productised SaaS (not a personal freelance service), the plan is to **register a Gewerbe and incorporate a GmbH (or UG → GmbH)** before or at close. Flagged because most investors will require a capitalised GmbH to hold IP and take investment. |
| 1.2 | Cap table (current) | 🟡 | Pre-incorporation: **100% founder**, no external holders, no option pool. Formal cap-table spreadsheet to be produced at incorporation. |
| 1.3 | Cap table (pro-forma, post-round) | 🟡 | Model the pre-seed instrument (SAFE/convertible or priced) plus a **10–15% ESOP (VSOP under German practice)** to cover the first hires. To draft alongside the raise. |
| 1.4 | Shareholder / founder agreement | 🟡 | Not yet needed (solo). On incorporation: founder vesting, IP assignment to the entity, and board/consent mechanics. **Founder vesting will be offered** to signal alignment. |
| 1.5 | Articles of association / Gesellschaftsvertrag | 🟡 | Produced at GmbH formation (notarised). |
| 1.6 | Company registration extract (Handelsregisterauszug) | 🟡 | Available once GmbH is registered. |
| 1.7 | Business registration (Gewerbeanmeldung) | 🟡 | In progress as part of the freelance→trade conversion. |
| 1.8 | Prior financings / SAFEs / grants received | ✅ | **None to date — fully bootstrapped.** No dilution, no debt, no encumbrances. Clean sheet. |
| 1.9 | Corporate structure diagram | ✅ | Trivial today: single founder, single (forthcoming) entity, no subsidiaries, no holdco. |
| 1.10 | Bank accounts / signatory list | 🟡 | Business account to be opened with the GmbH. |

---

## 2. Financials

| # | Item | Status | Notes |
|---|------|--------|-------|
| 2.1 | Financial model (bottom-up) | 🟡 | Built on the published pricing: **Starter €690/mo (~€8.3k/yr, ≤5k signals/mo), Growth €1,990/mo (~€24k/yr, ≤50k signals/mo — the flagship land), Enterprise €5,000+/mo custom (from ~€60k/yr, incl. on-prem/local)**. Annual prepay ~17% discount. To be packaged as a shareable workbook. |
| 2.2 | Revenue projections | 🟡 / 🚩 | Illustrative ramp shows **~€800k ARR by month 12**. **Flagged and labelled as a hypothesis to validate, not a forecast** — pre-revenue today, so this is a model output, not a track record. |
| 2.3 | Unit economics / gross margin | ✅ | **89–94% gross margin**, structurally driven by local-first / no-fine-tuning architecture → low inference COGS. Defensible and documentable from the tech design. |
| 2.4 | Pricing & packaging rationale | ✅ | Value metric = **volume of feedback signals processed**; hybrid recurring base + usage. Tiers and logic defined above. |
| 2.5 | Burn rate & runway | 🟡 | Effectively **near-zero burn today** (solo founder, bootstrapped, local-first infra keeps cloud spend minimal). Post-raise burn plan tied to use-of-funds below. |
| 2.6 | Use of funds | ✅ | **GTM + first hires (sales/CS) + compliance certifications (ISO 27001 / SOC 2 path).** Directly addresses the two named risks (GTM velocity, co-founder/first-hire gap). |
| 2.7 | Billing & revenue infrastructure | ✅ | **Merchant-of-Record via Paddle at launch** for EU-VAT compliance — removes VAT/OSS overhead and de-risks cross-border EU billing. |
| 2.8 | Historical financials / bookkeeping | 🟡 | Freiberufler EÜR (cash-basis) records exist; formal accounts begin at GmbH. Pre-revenue, so no MRR history yet. |
| 2.9 | Non-dilutive funding pipeline | ✅ | Documented options: **EXIST Gründungsstipendium, IBB Berlin GründungsBONUS, EIC Accelerator.** Pre-seed raise is **optional/opportunistic** to accelerate GTM, not a survival requirement. |
| 2.10 | Tax status / VAT | ✅ | USt-IdNr in place; VAT handling delegated to Paddle as MoR. |

---

## 3. Product & Technology

| # | Item | Status | Notes |
|---|------|--------|-------|
| 3.1 | Product overview / demo | ✅ | Working product. Pipeline: **ingest feedback text (app-store/review/support/survey) → enrich (sentiment, urgency, snake_case theme tags) → cluster into themes → synthesize governed, auditable, action-ready insights → outcome-grounded self-improvement loop.** Live walkthrough available. |
| 3.2 | Architecture documentation | 🟡 | Core design articulable now (local-first, no frontier fine-tuning, industry-adaptable with zero config). To formalise into a shareable architecture doc + diagram. |
| 3.3 | Self-improvement loop design | ✅ | **Signal → Insight → Action → measured Outcome → Learning.** The compounding, outcome-grounded moat — documented conceptually, demonstrable in-product. |
| 3.4 | Validation / evaluation results | ✅ | **Strongest asset. Tested on real scraped datasets across 3 industries — Henkel (B2B adhesives), Lieferando (food delivery), Trade Republic (fintech):** ~90% sentiment accuracy vs star-rating proxy; urgency calibration valid across all three; industry-specific tag vocabularies generated with zero config. |
| 3.5 | Example surfaced insights | ✅ | Trade Republic **"pervasive support unresponsiveness on critical financial issues"** (14 signals clustered); Lieferando **"refunds denied for undelivered orders"** (28 signals clustered). Concrete, action-ready outputs. |
| 3.6 | Eval methodology / rigor | ✅ | Originated as a master thesis: **honest eval harness, bootstrap confidence intervals, adversarially-verified test set.** Academic-grade methodology, not a marketing benchmark. |
| 3.7 | Product roadmap | 🟡 | To document: deeper vertical tag libraries, expanded connectors, on-prem/local Enterprise packaging, Art. 50 transparency features (see 5.6). |
| 3.8 | Security posture / TOMs | 🟡 | Technical & organisational measures (TOMs) drafted as part of the GDPR pack (see §5). Formal ISMS is a post-raise use-of-funds item (ISO 27001 / SOC 2 path). |
| 3.9 | Infrastructure & data residency | ✅ | **EU data residency, local-first — no US clouds required.** This is the core wedge and is architecturally enforced, not a policy promise. |
| 3.10 | Scalability & COGS model | ✅ | Local-first + no fine-tuning underpins the 89–94% margin; scaling story ties inference cost to signal volume. |
| 3.11 | Third-party / model dependencies | 🟡 | List of models, libraries, and any inference providers, with residency confirmation for each — to compile as a formal dependency/subprocessor register (overlaps 5.4). |

---

## 4. Intellectual Property

| # | Item | Status | Notes |
|---|------|--------|-------|
| 4.1 | **Thesis-origin IP question** | 🚩 | **Flagged proactively.** CLARA originated as a **master thesis**. We will provide written confirmation of the ownership position: what the university's IP/exploitation rules say, whether any institutional claim, funding condition, or supervisor/co-author contribution exists, and confirmation that the commercial codebase is the founder's own work. **Clean resolution here is a gating item and we treat it as such.** |
| 4.2 | IP assignment to company | 🟡 | On incorporation, founder assigns all CLARA IP (code, models, datasets, brand) to the GmbH. Assignment deed to be executed at formation. |
| 4.3 | Code ownership & authorship | ✅ (to confirm) | Codebase authored by the solo founder; no external contractors or contributors to date → clean chain of authorship, subject to 4.1. |
| 4.4 | Trademarks | 🟡 | "CLARA" word/logo mark — EUIPO search + filing to plan. **Flag:** "CLARA" is a common name; confirm availability in relevant classes. |
| 4.5 | Domains & brand assets | 🟡 | Domain(s) and marketing site held; to be transferred into the entity. |
| 4.6 | Open-source & licence compliance | 🟡 | Dependency licence review (permissive vs copyleg) to confirm no viral-licence contamination of proprietary code. |
| 4.7 | Data rights / training data | ✅ | Validation used **publicly scraped review datasets** for evaluation, not for fine-tuning frontier models (**zero fine-tuning** is core to the design). We will document dataset provenance and lawful-basis reasoning for the evaluation use. |
| 4.8 | Patents | ✅ (N/A) | None filed; strategy is trade-secret + execution + compliance moat rather than patents. Stated plainly. |

---

## 5. Legal & Compliance

*Compliance is CLARA's wedge, so this section is intentionally strong — governance is the product, not overhead.*

| # | Item | Status | Notes |
|---|------|--------|-------|
| 5.1 | GDPR role & posture | ✅ | **CLARA = GDPR processor.** Role and responsibilities defined. |
| 5.2 | AVV/DPA (data processing agreement) | ✅ | **Ready AVV/DPA** template for customers. |
| 5.3 | TOMs (technical & organisational measures) | ✅ | Documented TOMs pack included with the DPA. |
| 5.4 | Subprocessor list | ✅ | Maintained subprocessor register (overlaps 3.11). |
| 5.5 | DPIA support pack | ✅ | **DPIA support materials** to help customers run their own assessments — a sales asset for regulated buyers. |
| 5.6 | EU AI Act memo | ✅ | Positioned as **limited/minimal risk** (text triage, not biometric/high-risk). **Art. 50 transparency obligations apply 2 Aug 2026** — memo states the classification reasoning and the transparency roadmap. |
| 5.7 | Customer contracts / T&Cs / SLA | 🟡 | Standard SaaS T&Cs, order form, and SLA to finalise for launch. |
| 5.8 | Paddle / MoR agreement | ✅ | Merchant-of-Record arrangement covers EU-VAT and cross-border billing compliance. |
| 5.9 | Insurance | 🟡 | Professional/cyber liability to arrange post-incorporation. |
| 5.10 | Litigation / disputes | ✅ | **None.** No claims, disputes, or encumbrances. |
| 5.11 | Certifications roadmap | 🟡 | **ISO 27001 / SOC 2 path** is a named post-raise use-of-funds item; no certifications held yet — stated honestly. |

---

## 6. Customers & Traction

| # | Item | Status | Notes |
|---|------|--------|-------|
| 6.1 | Validation as proof | ✅ | **Proof, not vapor:** three-industry validation (Henkel / Lieferando / Trade Republic) demonstrates cross-industry generalisation with zero fine-tuning. This is our traction substitute at pre-revenue stage — and we present it as such. |
| 6.2 | Paying customers | 🚩 | **None yet — pre-revenue.** Flagged honestly. The raise (if taken) funds the path to first paying customers. |
| 6.3 | Design-partner / pilot pipeline | 🟡 | GTM motion defined: **paid design-partner pilots — one metric, weekly syncs, testimonial-on-success.** Pipeline list to be built and shared as it develops. |
| 6.4 | Target market & sizing | ✅ | **Voice-of-Customer / customer-feedback-analytics / CX-insight software.** Incumbents are largely US-based and not EU-sovereign or governance-first — the whitespace CLARA occupies. |
| 6.5 | ICPs | ✅ | (1) **DACH mid-market B2B SaaS product/CX teams**; (2) **EU e-commerce/marketplaces**; (3) **regulated DACH fintech/insurance** (highest willingness-to-pay). |
| 6.6 | GTM plan | ✅ | Founder-led sales; thesis-backed content + EU-sovereignty thought leadership; **90-day plan to first paying customers**; land Growth tier, expand to Enterprise in regulated segments. |
| 6.7 | Competitive positioning | ✅ | Wedge: **EU-sovereign + governed + self-improving** for buyers who cannot or will not send customer data to US clouds. Documented against the US-incumbent landscape. |
| 6.8 | Sales collateral & references | 🟡 | Deck, one-pager, and compliance one-pager exist/are in progress; customer references pending first pilots. |

---

## 7. Team

| # | Item | Status | Notes |
|---|------|--------|-------|
| 7.1 | Founder profile | ✅ | **Solo technical founder, Berlin.** Built and validated the product single-handed — evidence of unusual technical range across ML, product, and compliance. |
| 7.2 | **Co-founder / first-hire gap** | 🚩 | **Flagged as a known, material risk.** Single-founder companies carry key-person and bandwidth risk. Mitigation: use-of-funds prioritises **first hires (sales/CS)**, and a commercial co-founder / senior GTM hire is an active priority. We are not hiding this. |
| 7.3 | Org & hiring plan | 🟡 | Post-raise plan: sales/CS first, then compliance/security to drive the ISO/SOC path. To be detailed alongside the model. |
| 7.4 | Advisors | 🟡 | Academic/thesis lineage provides credible technical advisory roots; formal advisor list to compile. |
| 7.5 | Key-person dependency & continuity | 🚩 | Directly tied to 7.2. Founder vesting (4.2/1.4) and documentation of the codebase reduce, but do not eliminate, this dependency — stated plainly. |
| 7.6 | References (founder) | 🟡 | Available on request. |

---

## 8. Priority gaps we are surfacing (read this first, investor)

We would rather you hear these from us:

1. 🚩 **Thesis-origin IP (4.1)** — we will hand over a clean written ownership position; treat it as a gating item, because we do.
2. 🚩 **Entity conversion (1.1)** — Freiberufler → Gewerbe/GmbH is in progress; investment and IP assignment land in the GmbH.
3. 🚩 **Solo-founder / co-founder gap (7.2)** — real key-person risk; use-of-funds and an active co-founder search are the mitigation.
4. 🚩 **Pre-revenue (6.2)** — no paying customers yet; the ~€800k ARR ramp (2.2) is an explicit hypothesis, and three-industry validation (6.1) is the current proof.

Everything else in this room is either ready today or a short, funded, well-understood step away. What CLARA already has that most pre-seed companies don't: **a working, adversarially-tested product; ~90% sentiment accuracy validated across three real industries; a full GDPR/AI-Act governance pack; 89–94% structural gross margins; and zero dilution or debt on the sheet.**

---

*Prepared for pre-seed/seed diligence. Confident, specific, and honest by design — governance and EU-sovereignty are the through-line.*
