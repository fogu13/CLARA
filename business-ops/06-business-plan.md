# CLARA — Business Plan

*EU-sovereign, governed, self-improving Voice-of-Customer intelligence*

**Prepared:** 2026 · **Stage:** Validated product, pre-revenue · **Location:** Berlin, Germany
**Confidentiality:** This document contains confidential business information intended for prospective investors, lenders, and grant assessors.

---

## 1. Executive Summary

CLARA is an EU-sovereign, governed, self-improving AI engine for customer-feedback / Voice-of-Customer (VoC) analytics. It ingests raw customer feedback (app-store reviews, support tickets, surveys, marketplace reviews), enriches each signal with sentiment, urgency, and concise `snake_case` theme tags, clusters signals into themes, and synthesizes governed, auditable, action-ready insights. A closed outcome-grounded loop — **Signal → Insight → Action → measured Outcome → Learning** — makes the system compound in value the longer a customer runs it.

The market is large, growing, and structurally mismatched with European buyers. Incumbent VoC and CX-insight platforms are overwhelmingly US-based and neither EU-sovereign nor governance-first. That is the wedge. CLARA runs local-first (no US clouds required), ships with GDPR and EU AI Act compliance built in, and is fully auditable — turning governance from overhead into the primary reason to buy. Because CLARA adapts across industries **without fine-tuning frontier models**, inference COGS stay low, supporting **89–94% gross margins**.

This is proof, not vapor. CLARA has been validated on real scraped datasets across three distinct industries — **Henkel** (B2B adhesives), **Lieferando** (food delivery), and **Trade Republic** (fintech). Results: **~90% sentiment accuracy** versus a star-rating proxy; urgency calibration valid across all three industries; industry-specific tag vocabularies generated with **zero configuration**; and genuinely actionable themes surfaced — e.g. Trade Republic's *"pervasive support unresponsiveness on critical financial issues"* clustering 14 signals, and Lieferando's *"refunds denied for undelivered orders"* clustering 28 signals. The product originated as a master thesis with academic rigor: an honest evaluation harness, bootstrap confidence intervals, and an adversarially-verified test set.

**The business.** B2B SaaS with hybrid pricing (recurring base + usage), where the value metric is the volume of feedback signals processed. Three tiers (net, ex-VAT): **Starter €690/mo**, **Growth €1,990/mo** (the flagship land), and **Enterprise €5,000+/mo** custom, including on-prem / local deployment. Merchant-of-Record billing (Paddle) at launch handles EU-VAT compliance. Priority ICPs: (1) DACH mid-market B2B SaaS product/CX teams; (2) EU e-commerce / marketplaces; (3) regulated DACH fintech / insurance (highest willingness-to-pay).

**The ask.** CLARA is bootstrapped to a validated product. The near-term plan is fundable via **non-dilutive** instruments (EXIST Gründungsstipendium, IBB Berlin GründungsBONUS, EIC Accelerator), with an **optional, opportunistic pre-seed** to accelerate go-to-market. Use of funds is concentrated on GTM, first sales/CS hires, and the compliance certification path (ISO 27001 / SOC 2). An illustrative ramp reaches **~€800k ARR by month 12** — presented as a hypothesis to validate, not a forecast.

---

## 2. Company and Product

### 2.1 Company

CLARA is being built by a solo technical founder in Berlin. The company currently operates as a Freiberufler with a USt-IdNr; as CLARA becomes a productised SaaS offering, the founder is registering a **Gewerbe** and will formalise the operating entity (GmbH / UG path) as revenue and hiring warrant. The company is bootstrapped, and the product already exists and is validated.

### 2.2 Product

CLARA is a pipeline, not a dashboard bolt-on. The stages:

1. **Ingest** — customer-feedback text from app stores, review sites, support systems, and surveys.
2. **Enrich** — each signal is annotated with sentiment, urgency, and concise `snake_case` theme tags. Tag vocabularies are generated per-domain with zero configuration.
3. **Cluster** — related signals are grouped into coherent themes.
4. **Synthesize** — governed, auditable, action-ready insights are produced, each traceable to its underlying signals.
5. **Self-improve** — the outcome-grounded loop connects each insight to the action a customer took and the measured business outcome that followed, then learns from it. This is the **Signal → Insight → Action → measured Outcome → Learning** cycle.

**What makes the architecture distinctive:** CLARA is adaptable across industries **without fine-tuning frontier models**. It generated valid, industry-specific tag vocabularies for adhesives, food delivery, and fintech with no per-customer training. This keeps inference cheap, keeps deployment fast, and removes the model-ops burden that would otherwise fight against EU data residency.

**Governance is the product, not a wrapper.** Every insight is auditable back to source signals. Data can stay in the EU and, at the Enterprise tier, on the customer's own infrastructure. GDPR and EU AI Act obligations are addressed by design (see §8).

---

## 3. The Problem and Why Now

**The problem.** Customer feedback is high-volume, unstructured, and multi-channel. Teams either drown in it or reduce it to vanity metrics (an average star rating, an NPS number) that don't tell them *what to fix* or *whether fixing it worked*. Existing analytics tools stop at description; they rarely close the loop to a measured outcome, and they rarely produce insights a regulator or auditor would accept.

**Why now — three converging forces:**

1. **Regulatory gravity in Europe.** GDPR is enforced and expensive to get wrong. The **EU AI Act** is phasing in, and its **Article 50 transparency obligations apply from 2 August 2026**. European buyers — especially in regulated segments — increasingly cannot or will not send customer data to US clouds. This is a durable, structural buying constraint, not a preference.

2. **Frontier models are now good enough without fine-tuning.** The capability to do accurate, cross-industry sentiment, urgency, and thematic clustering with zero fine-tuning is recent. That is exactly what removes model-ops cost and makes local-first, EU-sovereign deployment economically viable at 89–94% gross margins.

3. **Incumbent mismatch.** The category is dominated by US-based platforms that were never architected for EU sovereignty or auditability. The gap between what European buyers need and what incumbents offer is wide and widening as regulation bites.

CLARA sits precisely at the intersection: EU-sovereign + governed + self-improving, at the moment the regulation lands and the technology makes it affordable.

---

## 4. Market and Sizing

### 4.1 Category

CLARA competes in Voice-of-Customer / customer-feedback-analytics / CX-insight software — a growing segment of the broader customer-experience software market.

### 4.2 Method note (read this first)

We deliberately avoid the top-down "1% of a $X billion global market" fallacy. The figures below are a **defensible bottom-up estimate** built from (a) the population of addressable companies in our ICP segments, (b) a realistic annual contract value (ACV) anchored to CLARA's own published pricing, and (c) conservative penetration assumptions for the obtainable slice. Numbers are directional planning figures, not audited market research, and are stated so an assessor can challenge each input.

### 4.3 Bottom-up estimate (DACH-first, EU-extendable)

**Building blocks — annual contract value.** Anchored to CLARA pricing:
- Growth tier (flagship land): €1,990/mo ≈ **~€24k ACV**
- Starter: ≈ **~€8.3k ACV**
- Enterprise: from **~€60k ACV**
- Blended planning ACV across a healthy mix: **~€25k**.

**TAM (DACH + adjacent EU, ICP-relevant).** The three ICPs — DACH mid-market B2B SaaS, EU e-commerce / marketplaces, and regulated DACH fintech / insurance — collectively contain on the order of **~60,000 companies** with enough customer-feedback volume and CX maturity to buy a governed VoC engine. At a blended **~€25k ACV**, that implies a **TAM ≈ €1.5B/year**.

**SAM (serviceable — sovereignty-constrained, reachable segments).** Narrowing to organisations for whom EU sovereignty and governance are genuine buying criteria and who are reachable by founder-led / early-stage GTM — realistically **~15,000 companies**. At **~€25k ACV**, **SAM ≈ €375M/year**.

**SOM (obtainable, 3-year horizon).** Founder-led sales plus a small early team can credibly win a low-single-digit share of SAM within three years. At **~1–1.5% penetration (~150–225 customers)** and **~€25k ACV**, **SOM ≈ €4–6M ARR** by year three — with the illustrative **~€800k ARR by month 12** as the entry point on that curve.

| Layer | Companies (planning) | Blended ACV | Value |
|---|---|---|---|
| TAM (DACH + adjacent EU, ICP-relevant) | ~60,000 | ~€25k | **~€1.5B/yr** |
| SAM (sovereignty-constrained, reachable) | ~15,000 | ~€25k | **~€375M/yr** |
| SOM (3-yr obtainable) | ~150–225 | ~€25k | **~€4–6M ARR** |

**Sensitivity.** The estimate is most sensitive to (a) blended ACV (Enterprise-heavy mix in regulated fintech/insurance pushes it materially higher) and (b) the sovereignty-driven "reachable" share of SAM, which regulation (EU AI Act, GDPR enforcement) is actively expanding. Both bias the estimate upward over the plan horizon, so the figures above are deliberately conservative.

---

## 5. Business Model and Pricing

**Model.** B2B SaaS, hybrid pricing: a recurring base fee plus usage. The **value metric is the volume of feedback signals processed** — it scales with the value the customer receives and aligns price with usage.

**Tiers (net, ex-VAT):**

| Tier | Price | Annual (approx.) | Included volume | Role |
|---|---|---|---|---|
| **Starter** | €690/mo | ~€8.3k/yr | up to ~5k signals/mo | Entry / small teams |
| **Growth** | €1,990/mo | ~€24k/yr | up to ~50k signals/mo | **Flagship land** |
| **Enterprise** | €5,000+/mo custom | from ~€60k/yr | high volume | On-prem / local deployment, regulated segments |

- **Annual prepay** carries a **~17% discount** to improve cash conversion and retention.
- **Billing:** **Merchant-of-Record via Paddle** at launch, which handles EU-VAT compliance and cross-border invoicing without CLARA building a tax stack.
- **Gross margin: 89–94%**, protected by the local-first, no-fine-tune architecture that keeps inference COGS low.

**Land-and-expand.** Land on **Growth**, then expand to **Enterprise** in regulated segments where on-prem / local deployment and the highest willingness-to-pay coincide (fintech, insurance). Usage-based overage on the signals metric provides natural in-tier expansion before a tier upgrade.

---

## 6. Go-to-Market

**Motion: founder-led sales**, concentrated on the three ICPs in priority order.

1. **Paid design-partner pilots.** Each pilot is scoped to **one metric**, run with **weekly syncs**, and structured so that success converts into a **testimonial and a reference logo**. Paid (not free) pilots qualify seriousness and validate willingness-to-pay from day one.
2. **Thesis-backed content + EU-sovereignty thought leadership.** The academic origin (honest eval harness, bootstrap CIs, adversarial test set) and the three-industry validation are credibility assets few competitors can match. Content leads with sovereignty and governance as the through-line.
3. **90-day plan to first paying customers.** A time-boxed sprint from validated product to first revenue, prioritising the segments with the shortest path to a signed pilot.

**Sequencing.** Start with **DACH mid-market B2B SaaS** (fastest to reach, high CX maturity), run in parallel into **EU e-commerce / marketplaces** (high feedback volume), and use early proof to open **regulated DACH fintech / insurance**, where sales cycles are longer but ACV and retention are highest.

**Compliance as a sales asset.** The AVV/DPA + TOMs + subprocessor list + DPIA support pack (see §8) shortens security/procurement review — often the true bottleneck in regulated deals — and converts governance into a closing accelerant rather than a friction point.

---

## 7. Competition and Moat

**Competitive landscape.** Incumbent VoC / CX-insight platforms are largely **US-based and neither EU-sovereign nor governance-first**. They compete on breadth of integrations and dashboards, not on sovereignty or auditability, and their architectures assume US-cloud data processing — and price is no longer uniformly a gap at entry, so it is not the wedge.

**CLARA's wedge:** EU-sovereign + governed + self-improving, for buyers who **cannot or will not** send customer data to US clouds.

**Moat — why this compounds and defends:**

1. **Outcome-grounded self-improvement.** Learning from *measured business outcomes* (not just labels) makes CLARA better the longer a customer uses it. This is a **compounding, defensible** advantage: a competitor can copy the pipeline but not a customer's accumulated Signal→Outcome→Learning history.
2. **Governance as architecture, not veneer.** EU data residency, local-first deployment, and full auditability are baked in. Retrofitting these into a US-cloud incumbent is a multi-year re-platforming, not a feature toggle.
3. **Zero-fine-tune industry adaptability.** New industries are onboarded without training frontier models — fast time-to-value for customers and low COGS for CLARA, reinforcing the 89–94% margin structure.
4. **Regulatory tailwind.** GDPR enforcement and the EU AI Act (Art. 50 from 2 Aug 2026) widen the set of buyers for whom sovereignty is mandatory, not optional — expanding CLARA's SAM over time.

---

## 8. Operations and Compliance

**Operating posture.** Local-first architecture means CLARA does not require US clouds and can run within EU boundaries, up to fully on-prem / local at the Enterprise tier. This is both a product feature and an operational simplification (fewer subprocessors, tighter data-flow control).

**Compliance is a sales asset, delivered as a ready pack:**

- **Role:** CLARA acts as a **GDPR processor**.
- **Ready artefacts:** AVV / DPA, Technical and Organisational Measures (TOMs), subprocessor list, and a **DPIA support pack** for customer risk assessments.
- **EU AI Act classification:** **limited / minimal risk** — CLARA performs text triage, not biometric or high-risk processing. **Article 50 transparency obligations apply from 2 August 2026**, and CLARA is positioned to meet them.
- **Certification path (funded post-raise / via grants):** **ISO 27001**, then **SOC 2**, to unlock the largest regulated accounts.

**Billing & tax operations.** Merchant-of-Record via **Paddle** at launch removes EU-VAT and cross-border invoicing overhead from CLARA's operational surface area.

---

## 9. Team and Hiring Plan

**Today.** A **solo technical founder in Berlin**. The product exists and is independently validated across three industries — the technical risk is substantially retired.

**The honest risk: single-founder concentration.** A solo founder is a real and known risk to execution velocity, key-person dependency, and, for some investors and grant bodies, fundability. We do not minimise it. The mitigations are explicit and sequenced:

1. **Highest-priority gap: a commercial co-founder or first senior GTM hire.** The founder's strength is product and technical depth; the complementary gap is sales / CS leadership. Closing this is the single most important hiring milestone and is the first call on any GTM funding.
2. **Early hires (post first revenue / raise):** one **Sales/BDR** and one **Customer Success** — the two roles that most directly convert the validated product into recurring revenue and retention.
3. **Advisory bench** in EU compliance and DACH B2B SaaS GTM to de-risk regulated-segment sales before full-time hires are affordable.
4. **Grant leverage.** EXIST explicitly supports team formation; a successful application both funds and formalises the co-founder / first-hire step.

**Hiring sequence (indicative):** commercial co-founder / senior GTM → Sales/BDR → Customer Success → compliance/security lead (aligned to the ISO 27001 / SOC 2 path).

---

## 10. Financial Plan and 3-Year Projection Summary

**Economics.** Gross margin **89–94%**, structurally protected by local-first, no-fine-tune inference. Revenue is recurring (base) plus usage (signals processed), with annual prepay (~17% discount) improving cash conversion.

**Unit economics (planning anchors).**
- Blended ACV **~€25k** (Growth-led mix, Enterprise upside).
- Gross margin **~90%** → **~€22.5k gross profit per customer per year**.
- Land on Growth; expand into Enterprise in regulated segments.

**Illustrative ramp (a hypothesis to validate, not a forecast):**

| Horizon | Milestone | ARR (illustrative) |
|---|---|---|
| Month 3 | First paying customers from 90-day plan | early pilots |
| **Month 12** | **~€800k ARR** per the ramp | **~€800k** |
| Year 2 | Expansion into Enterprise / regulated; CS-driven net retention | scaling |
| Year 3 | Low-single-digit SAM penetration (~150–225 customers) | **~€4–6M ARR** (SOM) |

The **~€800k ARR by month 12** figure ties directly to the tier pricing and land-Growth motion (roughly the revenue of ~30–35 Growth-equivalent customers, or fewer with Enterprise mix). It is presented as a target to validate, not a committed forecast. The three-year **€4–6M ARR** endpoint corresponds to the SOM derived bottom-up in §4.

**Margin and cash.** At 89–94% gross margin, the model reaches operating self-sustainability at modest ARR; the primary cash consumption is GTM headcount and compliance certification, both directly fundable via the non-dilutive instruments below.

---

## 11. Funding Ask and Use of Funds

**Position.** CLARA is **bootstrapped to a validated product**. Capital accelerates GTM; it is not required to prove the technology (that is done).

**Preferred path — non-dilutive first:**
- **EXIST Gründungsstipendium** — founder stipend + team-formation support (directly addresses the solo-founder gap).
- **IBB Berlin GründungsBONUS** — Berlin-specific early-stage grant.
- **EIC Accelerator** — larger non-dilutive (with optional equity component) for scale-up.

**Optional / opportunistic:** a **pre-seed equity raise** to compress the GTM timeline if terms are favourable. Dilution is a choice here, not a necessity.

**Use of funds (priority order):**
1. **Go-to-market** — founder-led sales capacity, pilot execution, thesis-backed content engine.
2. **First hires** — commercial co-founder / senior GTM, then **Sales** and **Customer Success**.
3. **Compliance certifications** — **ISO 27001 → SOC 2** path to unlock regulated Enterprise accounts.

---

## 12. Roadmap and Milestones

**Now → Month 3**
- Execute the 90-day plan; convert paid design-partner pilots into first paying customers.
- Publish the first tranche of thesis-backed, EU-sovereignty thought-leadership content.
- Submit non-dilutive grant applications (EXIST / GründungsBONUS).

**Month 3 → Month 12**
- Land Growth-tier customers across ICP 1 (DACH B2B SaaS) and ICP 2 (EU e-commerce).
- Close the commercial co-founder / first GTM hire; add Sales + CS.
- Open regulated fintech/insurance (ICP 3) with the DPIA/DPA compliance pack.
- Track toward the illustrative **~€800k ARR** waypoint.
- Begin **ISO 27001** groundwork.

**Year 2 → Year 3**
- Enterprise / on-prem expansion in regulated segments; net-revenue-retention focus.
- Complete **ISO 27001**, begin **SOC 2**.
- Broaden from DACH into adjacent EU markets.
- Track toward **~€4–6M ARR** (3-year SOM).

---

## 13. Risks and Mitigations

| Risk | Assessment | Mitigation |
|---|---|---|
| **Solo-founder concentration** | High / known | Prioritise commercial co-founder + early GTM hires; EXIST for team formation; advisory bench. See §9. |
| **GTM execution / long regulated sales cycles** | Medium–High | Sequence DACH B2B SaaS first (fastest), use compliance pack to shorten procurement, paid pilots to qualify. |
| **Incumbent response / large US players adding "EU mode"** | Medium | Governance-as-architecture and outcome-grounded learning are hard to retrofit; regulatory tailwind favours native sovereignty. |
| **Model / dependency cost or availability** | Medium | No-fine-tune, local-first design reduces lock-in and keeps COGS low; architecture is model-portable. |
| **Regulatory shift (EU AI Act interpretation)** | Medium | Positioned as limited/minimal-risk text triage; Art. 50 transparency readiness for 2 Aug 2026; monitored actively. |
| **ARR ramp slower than illustrative model** | Medium | ~€800k/mo-12 is an explicit hypothesis; high gross margin (89–94%) extends runway; non-dilutive funding reduces burn pressure. |
| **Concentration in DACH early** | Low–Medium | Architecture and validation are industry- and geography-agnostic; EU expansion built into Year 2–3 roadmap. |

---

### Appendix A — Validation Evidence (summary)

Tested on **real scraped datasets** across three industries:

- **Henkel** (B2B adhesives), **Lieferando** (food delivery), **Trade Republic** (fintech).
- **~90% sentiment accuracy** vs star-rating proxy.
- **Urgency calibration valid** across all three industries.
- **Industry-specific tag vocabularies** generated with **zero configuration**.
- **Actionable themes surfaced**, e.g.:
  - Trade Republic — *"pervasive support unresponsiveness on critical financial issues"* (14 signals clustered).
  - Lieferando — *"refunds denied for undelivered orders"* (28 signals clustered).
- Methodological rigor from its master-thesis origin: honest evaluation harness, **bootstrap confidence intervals**, and an **adversarially-verified test set**.

*This is proof, not a promise: the technology risk is substantially retired, and the plan's remaining risk is commercial execution — which is what funding and hiring address.*
