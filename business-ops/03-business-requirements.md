# CLARA — Business Requirements Document (BRD)

> **File:** `business-ops/03-business-requirements.md`
> **Owner:** Founder (solo, Berlin) · **Status:** Draft v1 · **Last updated:** 2026-07-01
> **Related docs:** `../business/STRATEGY_SYNTHESIS.md` (locked positioning), `../docs/roadmap.md` (canonical build plan), `../docs/eu-ai-act-mapping.md`, `../docs/dpia-template.md`

**Summary.** CLARA is a European, governed **Voice-of-Customer (VoC) engine that automatically closes the feedback loop** — Signal → Insight → Action → Learning — for privacy-first DACH/EU B2B companies. Its differentiator is not "better AI analysis" (now table stakes) but the **outcome-grounded, self-improving loop** (governed action + the Experiment Learning Repository that remembers which actions actually solved which customer problems), with **EU data residency, GDPR + EU AI Act auditability** riding on top as the deal-unblocker DACH procurement demands. This BRD defines the business model, objectives and KPIs, target market and personas, the product-market-fit hypotheses to validate, the operational/compliance requirements a solo Berlin founder must satisfy to invoice legally, the phased revenue roadmap, and the key risks and assumptions. The go-to-market is a **founder-led design-partner motion** (7–10 pilots), landing at **€12k–€30k ACV** — matching the closest competitor's *entry* economics (Enterpret entry reportedly ≈$12k/yr per review-site data) with governance + EU sovereignty carrying the Growth/Enterprise premium — funded through the trust-building phase by **non-dilutive grants** (EXIST, IBB GründungsBONUS Plus).

**Assumptions (read first).** This BRD assumes: (1) CLARA is sold as a **productised SaaS subscription**, which German tax practice almost certainly classifies as **Gewerbe (trade), not Freiberufler** — the single most consequential open item (see §5.1); (2) the founder remains a **solo Einzelunternehmen** with an existing USt-IdNr through GTM validation, converting to UG/GmbH on defined triggers; (3) the thesis (MSc Responsible AI, OPIT, 30 ECTS) completes **Sept 2026**, after which commercialization accelerates; (4) pricing figures are **strategic hypotheses to validate via willingness-to-pay interviews**, not empirically fixed; (5) the current-year date is **mid-2026**, so all regulatory deadlines below are live planning constraints. Numbers marked with sources are point-in-time — verify before relying on them.

> **This is not legal or tax advice.** The classification, tax, GDPR and EU AI Act content below is research-grounded orientation, not a binding opinion. Confirm every legal/tax/regulatory point with a **Steuerberater** and, for data-protection/AI-Act specifics, a **Fachanwalt für IT-Recht/Datenschutz** before you invoice a customer or publish a compliance claim.

---

## 1. Business Model

### 1.1 Value proposition & positioning (locked)

**Positioning line (locked, per `STRATEGY_SYNTHESIS.md` §6):**
> *Enterpret tells product teams what customers say and opens a ticket; CLARA governs the action across product and marketing, proves it worked against a contract, and remembers what worked — in your own EU cloud.*

Three value pillars, in priority order:

| # | Pillar | What it means | Why it wins |
|---|--------|---------------|-------------|
| 1 | **Automated loop closure (the USP)** | Signal → Insight → **governed Action** → **Learning**, run automatically with human-in-the-loop where risk warrants. | Incumbents stop at "themes in a dashboard → Jira ticket". Auto-execution with an *outcome contract* (metric + window defined at action creation) is the mechanism competitors lack. |
| 2 | **Outcome-grounded self-improving memory (the moat)** | The **Experiment Learning Repository**: confidence decay + "relevant past learnings" retrieval — a growing proprietary graph of which actions solved which problems in which context. | No VoC vendor and no frontier model ships this. It compounds with customer data → widening moat. |
| 3 | **EU-sovereign, governed & auditable (the deal-unblocker)** | Local-first / EU data residency, no frontier-model fine-tuning, GDPR Art. 28 DPA, EU AI Act Art. 12/50-aligned tamper-resistant audit logs, human-in-loop. | In DACH, data residency + GDPR posture is a **precondition to the first call** and a top reason deals stall — US-hosted tools fail procurement outright. ([compound.law](https://compound.law/en-DE/compliance/ai-customer-service-gdpr/)) |

**Framing discipline:** lead sales and product with pillars 1–2 (loop + memory); pillar 3 is the *table-stakes trust layer* that unblocks the DACH deal, not the headline. A governance-first framing was explicitly considered and rejected.

### 1.2 Revenue model — hybrid (recurring base + usage)

Pure per-seat is the wrong metric (value is *throughput of feedback and governed insights*, not viewers). Adopt **tiered packaging + a usage meter on volume-of-signals ingested/enriched/clustered per month**, with generous/unlimited seats so viewing insight is never gated. (IDC: ~70% of vendors move off pure per-seat by 2028; hybrid grows companies ~30% faster. ([nxcode.io](https://www.nxcode.io/resources/news/saas-pricing-strategy-guide-2026)))

| Tier | Price (annual billing) | Volume / scope | Key features |
|------|------------------------|----------------|--------------|
| **Starter** | **€490–990 / mo** (~€6–12k/yr) | 1–2 sources, ≤ ~5,000 signals/mo | Core enrichment (sentiment, urgency, snake_case themes), standard clustering, EU residency |
| **Growth** | **€1,500–3,000 / mo** (~€18–36k/yr) | 5+ sources, ~25k–50k signals/mo | Governed insight synthesis + action engine, audit log, GDPR/EU-AI-Act reporting, API |
| **Enterprise** | **€5,000–9,000+ / mo** (custom, annual) | Unlimited sources, high volume | Outcome-grounded learning loop, SSO/SCIM, DPA/VPC/on-prem, policy-as-code, local-model routing, SLA |

- **Landing band: €12k–€30k ACV** — mid-market, above self-serve. Enterpret's *entry* is reportedly ≈$1,000/mo (~$12k/yr) per review-site data (weakly sourced — validating in discovery calls); its *median* buyer pays ~$36k/yr and Chattermill averages ~$64k (**median ≠ entry**). Starter matches entry economics; governance + EU sovereignty justify Growth/Enterprise. ([vendr.com/Enterpret](https://www.vendr.com/marketplace/enterpret))
- **Editions (per strategy):** *SME* = EU-hosted SaaS, no-code, prebuilt taxonomies, 1-week setup. *Enterprise* = VPC/on-prem, SSO/SCIM, policy engine, local-model routing.
- **Land-and-expand:** target **15–25% annual ACV expansion** as signal volume/sources grow.
- **Optional outcome-based component** on Enterprise later (tied to insights actioned / measured impact) — rides the "40% of enterprise SaaS include outcome-based elements by 2026" trend and lifts retention.
- **Currency:** price in **EUR** (CHF for Switzerland). USD pricing on a `.de` page signals "not a serious vendor" to DACH procurement. ([embedworkflow.com](https://embedworkflow.com/blog/selling-saas-in-germany-austria-and-switzerland-dach/))

### 1.3 Unit economics — LLM inference is a first-class COGS line

AI-native gross margins are compressing to **50–60%** vs classic SaaS 75%+ (ICONIQ Jan 2026: avg AI product GM 52%). ([getmonetizely.com](https://www.getmonetizely.com/articles/the-economics-of-ai-first-b2b-saas-in-2026-margins-pricing-models-and-profitability))

- Meter **inference cost per 1,000 signals** and enforce tier volume caps.
- Keep **inference < 10% of revenue** to hold a **70%+ gross margin** target.
- CLARA's **local-first, no-fine-tuning, smaller/open-model** architecture *structurally* lowers this — quantify it and market it as a margin/cost advantage.

### 1.4 Billing infrastructure — Merchant-of-Record at launch

| Stage | Choice | Why |
|-------|--------|-----|
| **Launch → ~€50–100k MRR** | **Paddle** (Merchant of Record) | Paddle is the legal seller — it collects, files and remits EU VAT/OSS for you, eliminating VAT registration across 30+ countries for a solo founder. ~5% + €0.50/txn; absorbs most chargeback liability. Prefer Paddle over Lemon Squeezy (fewer stacked fees). ([globalsolo.global](https://www.globalsolo.global/blog/stripe-vs-paddle-vs-lemon-squeezy-2026), [paddle.com](https://www.paddle.com/help/sell/tax/how-paddle-handles-vat-on-your-behalf)) |
| **Past ~€50–100k MRR** | **Stripe + Stripe Tax** | ~2.9% + €0.30 + ~0.5% tax; you remain seller and file VAT/OSS yourself, but margin improves. Stripe Tax auto-validates EU B2B VAT IDs and applies reverse-charge. ([docs.stripe.com](https://docs.stripe.com/tax/supported-countries/european-union)) |

> **Nuance:** an MoR simplifies *tax* but does not remove the German **Gewerbe/Freiberufler classification** question (§5.1) — that applies to *your* activity regardless of who sells.

### 1.5 Lean solo ops stack (~€150–500/mo)

Billing: Paddle → Stripe. Product analytics: **PostHog** (EU-hosted option, fits residency story). Web analytics: **Plausible/Fathom** (EU, privacy-first). Support: **Crisp**. E-sign: **Documenso** (open-source, EU/data-residency) or a low-cost EU-friendly tier. CRM: spreadsheet/free HubSpot/Attio until lead volume warrants more. ([freemius.com](https://freemius.com/blog/micro-saas-tech-stack/))

---

## 2. Objectives & Success Metrics (KPIs)

### 2.1 North-star metrics

- **Product north-star:** **# of governed insights actioned that hit their outcome contract** (loops closed with *proven* business outcome). This is the USP made measurable and it feeds the learning moat.
- **Commercial north-star:** **Net Revenue Retention (NRR)** and **ARR** — NRR proves the loop compounds value inside accounts.

### 2.2 KPI dashboard (track weekly) with 2026 benchmarks

| KPI | CLARA target | 2026 benchmark / note | Source |
|-----|--------------|-----------------------|--------|
| **LTV : CAC** | **> 3 : 1** | Healthy SaaS floor | [beancount.io](https://beancount.io/blog/2026/05/10/saas-metrics-founders-must-track-2026-ltv-cac-nrr-churn-cac-payback-benchmarks-guide) |
| **CAC payback** | **< 12 months** | Typical 15–20 mo — beat it | ↑ |
| **NRR** | **> 100%** (aim 111%+) | 2026 median compressed to ~101%; best-in-class 130%+ | ↑ |
| **Gross margin (net of inference)** | **≥ 70%** | AI-native avg ~52% — CLARA's architecture must beat it | [getmonetizely.com](https://www.getmonetizely.com/articles/the-economics-of-ai-first-b2b-saas-in-2026-margins-pricing-models-and-profitability) |
| **Logo churn** | **< 5% / yr** | B2B SaaS avg ~3.5%/yr | [beancount.io](https://beancount.io/blog/2026/05/10/saas-metrics-founders-must-track-2026-ltv-cac-nrr-churn-cac-payback-benchmarks-guide) |
| **Inference as % of revenue** | **< 10%** | Public SaaS disclose ~4–9% | ↑ |
| **CAC (DACH founder-led)** | **€200–700** early | Generic B2B median ~$1,200 — DACH founder-led is cheaper if network-sourced | [lishchuk.com](https://lishchuk.com/blog/b2b-saas-launch-playbook-dach-2026.html) |
| **Runway** | **≥ 6 mo always; 12–18 mo pre-full-time** | Never operate < 6 mo | [softwareseni.com](https://www.softwareseni.com/solo-founder-saas-metrics-from-0-to-10k-mrr-in-6-months-with-realistic-timelines/) |

### 2.3 Phase objectives (OKR-style)

- **O1 — Prove the loop (by Q4 2026):** 3–5 design partners each hit **one measured outcome** in a 60–90-day pilot; ≥ 2 convert to paid.
- **O2 — Land paying revenue (by Q1 2027):** **€30–60k ARR**; ≥ 1 named reference logo per ICP.
- **O3 — Repeatable GTM (by Q4 2027):** 8–15 paying customers, **€150–300k ARR**, NRR > 100%, CAC payback < 12 mo.
- **O4 — Scale (2028):** **€500k–1M ARR**, Enterprise edition live, first non-grant capital (EIC Accelerator) in pipeline.

---

## 3. Target Market & Personas

### 3.1 Category & where CLARA sits

The VoC / feedback-analytics category has consolidated around US/UK enterprise incumbents (Enterpret, Chattermill, Thematic, Unwrap, SentiSum; survey giants Qualtrics/Medallia). **AI-native analysis is table stakes.** CLARA's white space: **EU sovereignty + governed auditable loop closure + learning memory** — features the leaders do *not* foreground. Do **not** compete as a helpdesk (Zendesk owns ticket triage); sit **above** Zendesk/Intercom/app-store reviews as the cross-source insight-and-governance layer.

**EU/DACH grounding:** Bitkom 2026 — ~41% of firms ≥20 staff use AI, **93% would prefer a German AI provider**; validates EU-first + the SME/enterprise split.

### 3.2 Ideal Customer Profiles (ICPs) — priority order

| # | Segment | Buyer | Pain / why-now | CLARA fit | Priority |
|---|---------|-------|----------------|-----------|----------|
| **ICP-1** | **Regulated DACH fintech / insurance** (Trade Republic-type) | Head of CX **+ Compliance/DPO co-signer** | Cannot send feedback to US LLMs; need governed, auditable, human-reviewable insights for BaFin/GDPR; AI Act pressure | Governed & auditable loop, tamper-resistant logs, local-first — **strongest fit, highest willingness-to-pay** | **Highest WTP** |
| **ICP-2** | **DACH mid-market B2B SaaS** (100–999 staff) | VP Product / Head of CX / Customer Insights | Feedback scattered; US tools blocked in security review; taxonomy build is heavy; AI Act Aug-2026 forces procurement questions | EU-sovereign + auto snake_case theming (no taxonomy labour) + audit trail | **Volume + faster cycles** |
| **ICP-3** | **EU e-commerce / marketplaces / food-delivery** (Lieferando-type) | Head of CX / VoC / Operations | High multilingual review + support volume; needs German-language theming + urgency triage; EU residency for consumer PII | Sentiment+urgency triage, clustering, outcome loop tied to CSAT/retention | **Proof-case volume** |

> Validation datasets map 1:1 to ICPs as named-adjacent proof cases: **Trade Republic → fintech**, **Lieferando → e-commerce**, **Henkel → brand/CPG**.

### 3.3 Personas

- **Economic buyer — "Head of CX / VP Product":** owns the budget and the pain (scattered feedback, slow loop). Cares about time-to-value, measurable outcome, EUR pricing, a personal demo. Won't buy from a US-hosted tool that fails the security review.
- **Champion — "Head of Customer Insights / Product Ops":** feels the taxonomy-building pain daily; loves "no taxonomy to build, no fine-tuning." Runs the pilot, becomes the internal advocate.
- **Blocker / co-signer — "DPO / Compliance / IT-Security" (decisive in ICP-1):** can kill any deal on data residency. Needs the **trust pack** (EU-hosting statement, DPA/AVV, sub-processor list, deletion process, AI Act audit-log description) to say yes. In regulated segments, treat them as a **co-buyer**, not a gate.

### 3.4 Sales motion (DACH-specific)

**High-touch, founder-led** — self-serve fails in DACH (buyers expect a demo + contract in their language + GDPR-by-default proof). Recruit **7–10 design partners** (cap at 10 — beyond that you lose weekly synchronous time). No mass cold email/DMs (GDPR-report / block risk). German LinkedIn 3×/week, opinionated, benchmark-backed. Warm/network sourcing yields 40–60% of design partners. ([unusual.vc](https://www.unusual.vc/field-guide/build-a-sales-motion-with-design-partners-for-a-b2b-product/), [embedworkflow.com](https://embedworkflow.com/blog/selling-saas-in-germany-austria-and-switzerland-dach/))

---

## 4. Product-Market-Fit Hypotheses to Test

Each hypothesis has an explicit **test** and a **kill/keep threshold**. Run these through the design-partner pilots.

| # | Hypothesis | How to test | Success threshold (keep) | Kill signal |
|---|-----------|-------------|--------------------------|-------------|
| **H1 — Loop closure is the wedge** | Buyers pay a premium for *governed auto-action + outcome contract*, not just analysis. | Pilot pitch leads with loop closure; measure whether the *action/outcome* feature (not the dashboard) is what closes the deal. | ≥ 3/5 pilots cite loop closure as the primary reason to buy. | Buyers only want "themes in a dashboard" → reposition. |
| **H2 — EU-sovereignty unblocks deals** | Data residency + audit is a *precondition*, and US tools are disqualified in security review. | Track how many deals reference residency/AI Act in procurement; A/B the trust-pack in the sales cycle. | ≥ 60% of ICP-1/2 deals name residency as a filter. | Residency rarely mentioned → it's fine print, not a wedge. |
| **H3 — "No taxonomy to build" beats incumbents on time-to-value** | Auto snake_case theming removes the setup friction Enterpret/Chattermill impose (5,000+ items/mo min). | Measure time-to-first-insight in pilot vs their prior tool/manual process. | First useful insight in **< 1 week**, no manual taxonomy. | Setup drags > 2 weeks / needs heavy config. |
| **H4 — Landing band €12k–30k is right** | Mid-market DACH will pay €12–30k/yr; below incumbents, above self-serve. | Willingness-to-pay interviews + real pilot-to-paid conversions at proposed tiers. | ≥ 2 paid conversions in-band without heavy discounting. | Repeated pushback below €12k → SMB-only, revisit model. |
| **H5 — The learning memory compounds retention** | Outcome-grounded self-improvement drives expansion/NRR over time. | Cohort NRR after 2–3 quarters; qualitative "would you miss it" test. | NRR > 100% in first renewing cohort. | Flat usage after novelty → loop not sticky. |
| **H6 — Regulated fintech has highest WTP** | ICP-1 pays most and closes on differentiator fit. | Compare ACV and cycle length across ICPs. | ICP-1 ACV ≥ 1.5× ICP-2/3. | ICP-1 cycles too long/compliance-blocked → lead with ICP-2. |

---

## 5. Operational & Compliance Requirements

> **This is not legal or tax advice.** German Freiberufler-vs-Gewerbe classification and DPIA/AI-Act edge calls are fact-specific and decided by the Finanzamt / authorities. Engage a **Steuerberater** and a **Fachanwalt für IT-Recht/Datenschutz** before relying on any of this.

### 5.1 Legal & tax setup — the head-on nuance

**Selling a productised, self-service SaaS in Germany is almost certainly *Gewerbe* (trade), NOT Freiberufler** — even though you currently hold a Freiberufler registration + USt-IdNr. German tax law equates licensing/selling standardised, mass-reproducible software with commercial trade; the §18 EStG freelance route only survives for genuinely bespoke, personally-performed "engineer-like" development. ([existenzgruendungsportal.de](https://www.existenzgruendungsportal.de/Redaktion/DE/BMWK-Infopool/Antworten/Gruendungsplanung/Freie-Berufe/gemischte-Taetig/Software-entwickeln-und-vertreiben-freiberufliche-Taetigkeiten))

**Critical trap — Abfärbung (infection):** mixing gewerbliche SaaS income into your existing freiberuflich activity *without strict separation* can retroactively reclassify **ALL** your income as gewerblich. ([restio.io](https://restio.io/de/blog/gewerbe-vs-freiberufler-2026/))

**Required actions (before the first SaaS invoice):**

- [ ] **Book a Steuerberater THIS month.** Framing: *"I am a registered Freiberufler with a USt-IdNr launching a productised AI SaaS — how do I handle Gewerbe classification and avoid Abfärbung on my freelance income?"* Highest-leverage action.
- [ ] **Assume Gewerbe.** File the **Gewerbeanmeldung** in your Berlin Bezirk via [berlin.de/ea](https://www.berlin.de) (~€15 online). Berlin has no central Gewerbeamt — jurisdiction follows your business seat.
- [ ] **Keep strictly separate bookkeeping** for freiberuflich vs gewerblich (separate ledgers, ideally a separate business bank account) to block Abfärbung.
- [ ] **Complete the Fragebogen zur steuerlichen Erfassung** (ELSTER) for the new activity.
- [ ] **IHK Berlin membership** is automatic on Gewerbe; new founders may get a **2-year fee waiver** — but your prior Freiberufler income *may disqualify* it. Verify with IHK/Steuerberater. ([ihk.de/berlin](https://www.ihk.de/berlin/ueber-uns/mitgliedschaft-und-beitrag/das-verfahren-der-beitragserhebung/besonderheiten-der-beitragserhebung/existenzgruender-2280552))

**Gewerbesteuer is largely neutralised at small profit:** €24,500 allowance + Berlin Hebesatz **410%** + the **§35 EStG credit (4× the Messbetrag)** offsets trade tax up to ~400% Hebesatz — only a tiny residual remains for a small solo profit. ([fuer-gruender.de](https://www.fuer-gruender.de/wissen/unternehmen-gruenden/finanzen/steuern/gewerbesteuer-rechner/), [gesetze-im-internet.de/estg §35](https://www.gesetze-im-internet.de/estg/__35.html))

**Legal form:** stay a **solo Einzelunternehmen** for GTM validation (cheapest, EÜR cash-basis bookkeeping). **Convert to UG (from €1) / GmbH** on concrete triggers: (a) real customer PII at scale (liability shield for GDPR/AI-Act exposure), (b) first investor, (c) a co-founder, (d) an enterprise B2B customer demanding a GmbH counterparty. UG/GmbH formation needs a Notar. ([derstartupanwalt.de](https://www.derstartupanwalt.de/news/gruendung-ug-gmbh-fuer-gruender-und-startups))

### 5.2 VAT, invoicing & e-invoicing

- **Waive §19 Kleinunternehmer, opt into regular VAT** for the SaaS activity. B2B buyers are VAT-neutral, and you gain **input-VAT recovery** on cloud/AI/infra + a clean USt-IdNr for EU reverse-charge. (Kleinunternehmer thresholds: ≤ €25k prior year AND ≤ €100k current year, €100k now a hard limit. ([ihk.de/stuttgart](https://www.ihk.de/stuttgart/fuer-unternehmen/recht-und-steuern/steuerrecht/umsatzsteuer-national/kleinunternehmerregelung-in-der-umsatzsteuer-1843632)))
- **EU B2B:** invoice net, apply **§13b reverse charge** — state *"Steuerschuldnerschaft des Leistungsempfängers / Reverse charge"*, show **both** USt-IdNrs, **validate every customer VAT ID via VIES**, and file a **quarterly Zusammenfassende Meldung (ZM)**. **B2C EU digital services:** charge local VAT via **OSS**. ([restio.io](https://restio.io/en/blog/reverse-charge-international-germany/))
- **Invoice content (§14 UStG):** supplier + recipient name/address, Steuernummer or USt-IdNr, sequential invoice number, date, scope, time of supply, net/VAT/rate. ([gesetze-im-internet.de/ustg §14](https://www.gesetze-im-internet.de/ustg_1980/__14.html))
- **E-invoicing (E-Rechnung):** you must **already be able to RECEIVE** structured e-invoices (XRechnung/ZUGFeRD, since 1 Jan 2025) and archive them GoBD-compliant. **SENDING** for a business your size (≤ €800k turnover) is mandatory from **1 Jan 2028** (2027 for >€800k). Adopt e-invoice-capable software now — it also fits CLARA's own "governed/auditable" story. ([bundesfinanzministerium.de](https://www.bundesfinanzministerium.de/Content/DE/FAQ/e-rechnung.html), [rickert.law](https://rickert.law/e-rechnung-b2b-2027/))
- **Bookkeeping:** simple **EÜR (cash-basis, Anlage EÜR via ELSTER)** as a solo Einzelunternehmen until you cross ~€800k turnover / ~€80k profit or form a GmbH/UG (double-entry).

### 5.3 GDPR (product & company)

CLARA wears **two hats**: **Processor** for ingested customer feedback (your B2B customer is controller), **Controller** for its own website/leads/billing/self-improvement data. ([gdpr-info.eu Art. 28](https://gdpr-info.eu/art-28-gdpr/))

**Requirements checklist:**

- [ ] **Art. 28 AVV/DPA** offered to every customer (a standard exhibit to the SaaS contract), with all 9 mandatory elements.
- [ ] **Back-to-back AVVs with every subprocessor** (LLM API + hosting); publish a **subprocessor list** with general-authorization + right-to-object wording.
- [ ] **EU data residency** for hosting + inference. Any US-linked subprocessor needs **SCCs + a Transfer Impact Assessment** (or DPF certification). Prefer **EU-hosted/open-weight models** to eliminate transfer risk.
- [ ] **TOMs annex (Art. 32):** TLS, encryption at rest, RBAC, MFA, audit logging, pseudonymisation, backups, tenant isolation, incident response with **72-hour Art. 33 breach notification** to the controller.
- [ ] **DPIA support pack (Art. 35):** CLARA touches innovative AI + large-scale + profiling → the customer owns the DPIA but you must **assist**. Ship a DPIA-support template + "CLARA processing facts" sheet (see `../docs/dpia-template.md`).
- [ ] **ROPA (Art. 30)** in both roles — the <250-employee exemption does **not** apply.

### 5.4 EU AI Act

**Classification:** a **text-based** sentiment/triage engine is **NOT prohibited** (the Art. 5(1)(f) emotion-recognition ban is limited to **biometric** systems in workplace/education) and **NOT Annex III high-risk** (Annex III "emotion recognition" is also biometric) → effectively **minimal/limited risk**. Building on third-party frontier models **without fine-tuning** makes you a **downstream AI-system provider**, not a GPAI provider. **Write a one-page classification memo** documenting this reasoning to rebut any customer/regulator challenge. ([oliverpatel.substack.com](https://oliverpatel.substack.com/p/emotion-recognition-and-the-eu-ai), [arnoldporter.com](https://www.arnoldporter.com/en/perspectives/advisories/2025/08/does-your-company-have-eu-ai-act-compliance-obligations))

**Deadlines to track:**

| Date | Obligation | Applies to CLARA? |
|------|-----------|-------------------|
| **2 Feb 2025** (live) | Prohibited practices + **Art. 4 AI-literacy** | ✅ Yes — add a short AI-use policy + training log now |
| **2 Aug 2025** (live) | GPAI model-provider obligations | ❌ No (you're a system provider) |
| **2 Aug 2026** | **Art. 50 transparency** (disclose AI use / label AI-generated content) — **NOT deferred** | ✅ Yes — ship "AI-generated/AI-assisted" labelling before this date |
| **2 Dec 2027** | Annex-III high-risk (deferred from Aug 2026 by the Digital Omnibus) | ❌ Not high-risk, but monitor |

([compliancehub.wiki](https://compliancehub.wiki/eu-ai-act-article-50-transparency-digital-omnibus-2026/), [gibsondunn.com](https://www.gibsondunn.com/eu-ai-act-omnibus-agreement-postponed-high-risk-deadlines-and-other-key-changes/)) See `../docs/eu-ai-act-mapping.md`.

> **Customer-facing angle:** CLARA's built-in **tamper-resistant audit logs (AI Act Art. 12-aligned)** let the *deployer* (your customer) discharge *their own* compliance — a concrete purchase justification, not just your own hygiene.

### 5.5 Website legals (fix immediately — stale refs invite Abmahnung)

- **Impressum** under **§5 DDG** (TMG was repealed 14 May 2024) — full name, physical address, email + phone, **USt-IdNr**. Remove any "TMG"/"Telemedien"/ODR-platform relics. ([it-recht-kanzlei.de](https://www.it-recht-kanzlei.de/tmg-ttdsg-ausser-kraft-impressum-datenschutz.html))
- **Datenschutzerklärung** (GDPR Art. 13/14) — separate from the customer DPA.
- **B2B AGB / Terms of Service** with AVV/DPA + TOMs as annexes (SLA, liability caps, IP, term/termination).
- **Cookie consent** under **§25 TDDDG** for non-essential cookies, or go **essential-only** to skip the banner.

### 5.6 Sales/compliance trust pack (table-stakes to close DACH deals)

Assemble once, attach to every demo: **EU-hosting statement · data-residency + sub-processor sheet · Art. 28 DPA template · TOMs annex · deletion / right-to-be-forgotten process · DPIA-support template · one-page AI Act & GDPR datasheet (residency, no-training toggle) · AI Act classification memo.** Doubles as sales collateral and survives DACH security questionnaires.

---

## 6. Revenue Roadmap & Milestones

### 6.1 Phased plan

| Phase | Window | Revenue target | Key commercial milestones | Funding |
|-------|--------|----------------|---------------------------|---------|
| **P0 — Foundation & validation** | now → **Sep 2026** (thesis) | €0 (pilots free/discounted) | Steuerberater ruling; Gewerbeanmeldung; VAT opt-out; trust pack v1; **3–5 design partners** signed; 1 grant application filed | EXIST / IBB application |
| **P1 — First paid revenue** | **Q4 2026 – Q1 2027** | **€30–60k ARR** | Convert ≥ 2 pilots to paid; ≥ 1 named reference per ICP; Art. 50 labelling shipped (pre-2 Aug 2026); e-invoice receive+archive live | Grant funds landed |
| **P2 — Repeatable GTM** | **2027** | **€150–300k ARR** | 8–15 customers; NRR > 100%; land-and-expand proven; consider **UG/GmbH** conversion; e-invoice *sending* ready before 1 Jan 2028 | Consider Pro FIT / revenue |
| **P3 — Scale** | **2028** | **€500k–1M ARR** | Enterprise edition (VPC/SSO/policy-as-code); ISO 27001 / SOC 2 in progress; **EIC Accelerator** application | EIC Accelerator (grant < €2.5M + equity) |

### 6.2 90-day launch plan (parallel tracks)

- **Weeks 1–2 — Legal foundation:** Steuerberater consult (Gewerbe/Abfärbung); model Gewerbesteuer; decide UG/GmbH timing. **Do NOT invoice under an unverified Freiberufler assumption.**
- **Weeks 1–2 — Grant triage (parallel):** contact the thesis university's **EXIST** office (Gründungsstipendium: **€2,500–3,000/mo for 12 mo + up to €10k material**, year-round); email **IBB Business Team** re **GründungsBONUS Plus** (up to **€50k / 50% of costs**, start-up < 18 months old); book a **Coaching BONUS** for GTM/sales coaching. ([exist.de](https://exist.de/en/programm/gruendungsstipendium/), [ibb.de](https://www.ibb.de/en/foerderprogramme/gruendungsbonus-plus.html))
- **Weeks 1–2 — ICP + assets:** lock **one beachhead ICP**; German-language one-pager (WIN metric, EU residency + GDPR + AI Act auditability, EUR pricing, 60–90-day pilot offer).
- **Weeks 2–4 — Pipeline:** 40–60 warm/one-hop targets; founder-led outbound (5–7 touches/14 days: short German email + warm intro + one LinkedIn message). **No mass cold outreach.**
- **Weeks 3–8 — Land design partners:** sign **3–5** using the pitch template *"reduce {metric} by {target} in 60–90 days, weekly 30-min syncs, testimonial on success."* One measured outcome per pilot → feeds the learning loop AND becomes the case study.
- **Weeks 2–12 — Content engine:** German LinkedIn 3×/week, opinionated + benchmark-backed (thesis, AI Act, VoC results); 1–2 anonymised benchmark case studies.
- **Weeks 4–12 — Compliance kit:** finish the §5.6 trust pack.

### 6.3 Funding / grants ledger

| Instrument | Amount | Fit / eligibility | Action |
|-----------|--------|-------------------|--------|
| **EXIST Gründungsstipendium** | €2,500–3,000/mo × 12 + ≤€10k material | University/thesis-affiliated; graduated ≤ 5 yrs; solo eligible | Apply via thesis university startup office (year-round) |
| **IBB GründungsBONUS Plus** | ≤ €50k / 50% costs, up to 2 yrs | Berlin, digital/tech, start-up < 18 mo, German application | Email IBB Business Team; confirm 18-mo window |
| **IBB Pro FIT + Coaching BONUS** | Grants+loans; coach ≤ €1,000/day | Berlin innovative tech | Later phase; use Coaching BONUS now |
| **Gründungszuschuss** | ALG I + €300/mo | Only if drawing **ALG I** with ≥150 days left | Likely **N/A** (you're not on ALG I) — verify |
| **EIC Accelerator** | Grant < €2.5M + equity €0.5–10M | Individuals/SMEs; deep-tech | 2028 roadmap; 2026 cut-offs incl. **8 Jul, 2 Sep, 4 Nov** ([eic.ec.europa.eu](https://eic.ec.europa.eu/eic-funding-opportunities/eic-accelerator_en)) |

**Runway framing:** plan **6–9 months** before DACH revenue covers DACH costs and **9–24 month CAC payback** — exactly the gap the non-dilutive grants are meant to bridge. Never drop below 6 months runway.

---

## 7. Key Risks & Assumptions

### 7.1 Risk register

| # | Risk | Likelihood | Impact | Mitigation |
|---|------|-----------|--------|------------|
| R1 | **Abfärbung** reclassifies all income as gewerblich | Medium | High | Steuerberater before first invoice; strict separate bookkeeping; ring-fence SaaS (separate vehicle as revenue grows) |
| R2 | Misclassifying as Freiberufler → back-taxes/penalties | Medium | High | Assume Gewerbe; Gewerbeanmeldung + Fragebogen; written Steuerberater assessment |
| R3 | GDPR/AI-Act liability handling real PII as unlimited-liability sole trader | Medium | High | EU-only hosting/models; SCCs where needed; **convert to UG/GmbH** on PII-at-scale trigger; robust TOMs + breach runbook |
| R4 | Incumbents (Enterpret) add EU residency / "close the loop" and erase the wedge | Medium | High | Lead with the **mechanism they lack** — governed cross-functional action + **learning memory**; deepen the moat with proprietary outcome graph |
| R5 | Long DACH sales cycles / CAC payback exhaust runway | High | Medium | Non-dilutive grants; founder-led warm sourcing; land-and-expand; cap pilots at 10 |
| R6 | Inference COGS erodes margin below 70% | Medium | Medium | Meter cost/1,000 signals; tier caps; local/open models; keep inference < 10% of revenue |
| R7 | Solo-founder capacity / bus factor | High | Medium | Ruthless scope (feature freeze per strategy); lean stack; automate ops; prioritise references over feature breadth |
| R8 | Pricing mis-set (too low = SMB-only; too high = stalls) | Medium | Medium | Validate via WTP interviews (H4); anchor on competitor *entry* economics (≈$12k/yr), sell the governance premium; usage-based expansion |
| R9 | IHK founder-waiver disqualified by prior Freiberufler income | Medium | Low | Budget ~€64/yr Grundbeitrag; confirm eligibility with IHK |
| R10 | Regulatory dates shift (Digital Omnibus text pending OJ publication) | Low | Low | Track official sources; the near-term ones (Art. 50 = 2 Aug 2026, e-invoice receive since 2025) are firm |

### 7.2 Assumptions log

1. **CLARA = Gewerbe** for tax purposes (to be confirmed by Steuerberater) — drives §5.1 and R1/R2.
2. **Solo Einzelunternehmen** through validation; UG/GmbH on defined triggers.
3. **Regular VAT** (waive §19) — B2B-optimal.
4. **Text-only triage = minimal/limited-risk** under the AI Act; downstream system provider, no fine-tuning.
5. **EU-hosted models/infra** — the residency USP and the transfer-risk mitigation both depend on this.
6. **Pricing (€12–30k ACV, hybrid)** = hypothesis to validate, not fixed.
7. **Thesis completes Sept 2026**; commercialization is deliberately post-thesis (avoid bloating the thesis scope per `STRATEGY_SYNTHESIS.md` §8).
8. **Positioning locked:** loop closure + learning memory lead; EU governance is the trust layer, not the headline.

---

## 8. Open Decisions (owner: founder, next 30 days)

- [ ] Steuerberater engaged; Gewerbe vs Freiberufler call in writing.
- [ ] Gewerbeanmeldung filed; VAT opt-out submitted.
- [ ] Beachhead ICP chosen (recommend **ICP-1 fintech for WTP + ICP-2 SaaS for volume**).
- [ ] Pricing tiers ratified after ≥ 5 WTP interviews.
- [ ] EXIST + IBB GründungsBONUS Plus applications submitted.
- [ ] Trust pack v1 complete (§5.6).
- [ ] Art. 50 AI labelling scheduled before **2 Aug 2026**.
- [ ] UG/GmbH conversion trigger thresholds written down.

---

*Sources are linked inline where a claim depends on a current figure or deadline. All tax/legal/regulatory content is orientation only — confirm with a Steuerberater and an IT-/data-protection lawyer before acting.*
