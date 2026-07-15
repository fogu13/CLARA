# Compliance: GDPR + EU AI Act — CLARA Readiness Checklist

**Summary.** To be sellable to EU B2B buyers — especially the regulated DACH fintech/insurance and privacy-first mid-market segments CLARA targets — CLARA must arrive at the security review with a ready-made compliance pack, not a promise. Concretely: CLARA is a GDPR **processor** for the customer feedback it ingests (the customer is the controller) and a **controller** for its own website/marketing/billing and product-improvement data. That dual role obliges CLARA to (1) offer every customer an Art. 28 **AVV/DPA** with a **TOMs** annex and a published **subprocessor list**, (2) sign back-to-back AVVs with each subprocessor (LLM API + hosting) and keep them EU-hosted or covered by SCCs + a transfer impact assessment, (3) ship a **DPIA support pack** so customers can complete their own DPIA fast, and (4) run a **ROPA** and a 72-hour breach runbook. On the EU AI Act, a **text-based** sentiment/urgency/theme-triage engine is **not** a prohibited practice and **not** Annex III high-risk (both the Art. 5(1)(f) ban and the Annex III "emotion recognition" head are limited to **biometric** systems) — CLARA is effectively **limited/minimal risk**, a downstream **AI-system provider** (not a GPAI provider, since no fine-tuning). The live AI Act hooks are **Art. 4 AI-literacy** (in force since 2 Feb 2025) and **Art. 50 transparency labelling** (applies 2 Aug 2026, explicitly *not* deferred). Finally, the website needs an **Impressum under §5 DDG** (TMG was repealed 14 May 2024) with the USt-IdNr, a GDPR **Datenschutzerklärung**, **B2B AGB**, and a **§25 TDDDG** cookie banner if non-essential cookies run. This document turns all of that into a phased, checkable readiness plan. Treat "EU-sovereign + governed + auditable, GDPR + EU AI Act aligned" not as overhead but as CLARA's headline sales wedge.

**Assumptions.** This document assumes: (a) CLARA processes customer-feedback **text** only — app-store/review/support text — with no biometric, facial, or voice-print processing; (b) hosting and LLM inference are (or will be) EU-based, consistent with the local-first / EU-residency USP; (c) frontier models are used *without* fine-tuning above the "significant modification" threshold, so CLARA is a downstream AI-system provider, not a GPAI provider; (d) the founder operates as a solo Einzelunternehmen/Freiberufler today with a USt-IdNr, and productised SaaS revenue is very likely **Gewerbe** — a tax-status question flagged in the business-setup document, not resolved here; (e) sales are B2B into DACH/EU. If any assumption breaks (e.g. voice recordings enter scope, or a US-parent LLM API is used), the classification and obligations below change and must be re-run.

> **This is not legal or tax advice.** It is a founder-facing readiness checklist compiled from research and creates no lawyer–client relationship. GDPR role edge-cases, DPIA scope, and AI Act classification are fact-specific; the Freiberufler-vs-Gewerbe question is decided case-by-case by the Finanzamt. Before you rely on any of this — and *before* you sign your first B2B contract or issue your first SaaS invoice — have a German **Fachanwalt für IT-Recht/Datenschutz** review the legal pack and a **Steuerberater** confirm the tax status. Verify Digital Omnibus dates against the Official Journal on publication.

---

## 1. GDPR posture — who is what

CLARA wears **two hats simultaneously**. Getting this mapping explicit is the foundation for every document below, because the two roles trigger different obligations.

| Data flow | Your role | Their role | Key obligation |
|---|---|---|---|
| Customer's feedback text ingested, enriched (sentiment/urgency/`snake_case` themes), clustered, synthesized on the customer's instructions | **Processor** (Art. 4(8), Art. 28) | Customer = **Controller** | Offer an Art. 28 AVV/DPA; process only on documented instructions |
| Website visitors, leads, marketing, billing/invoicing data | **Controller** | — | Datenschutzerklärung, lawful basis, consent |
| Data used to improve CLARA's own model / self-improving loop | **Controller** (for your own purposes) | — | Own lawful basis; possibly your own DPIA if large-scale |

Source for the Art. 28 processor framing: <https://gdpr-info.eu/art-28-gdpr/>

**Why this matters commercially:** DACH procurement will not progress without a clear "you are our processor, here is the AVV" story. The `governed and auditable` architecture is the differentiator — foreground it.

### 1.1 Records of Processing Activities (ROPA, Art. 30) — required, no exemption

The <250-employee exemption does **not** apply to CLARA, because processing is **not occasional** and uses AI on potentially sensitive data. Maintain **two** ROPAs:

- **Controller ROPA** (Art. 30(1)): website, leads, billing, product-improvement data.
- **Processor ROPA** (Art. 30(2)): per-customer processing — purposes, data categories, recipients, transfers, retention, general TOMs description.

Review annually and on every new subprocessor or material feature. Source: <https://www.osano.com/articles/what-is-a-ropa-gdpr-requirements-for-record-of-processing-activities>

---

## 2. The legal document pack (this is your sales collateral)

The following pack is **table-stakes to close DACH B2B deals** and doubles as procurement collateral. Build it once, reuse it in every deal.

### 2.1 Customer-facing AVV / DPA (Art. 28 GDPR)

Every B2B customer gets a written **Auftragsverarbeitungsvertrag** as a standard exhibit to the SaaS contract (AGB). It must contain the **9 mandatory Art. 28(3) elements**:

1. Subject-matter of processing
2. Duration
3. Nature and purpose
4. Types of personal data + categories of data subjects
5. Controller's obligations and rights
6. Process **only on documented instructions**
7. Confidentiality commitments of personnel
8. Art. 32 security measures (→ TOMs annex, §2.3)
9. Subprocessor rules; assistance with data-subject rights and DPIAs; **delete or return** data at end of contract; **audit rights**

Source: <https://secureprivacy.ai/blog/data-processing-agreements-dpas-for-saas>

### 2.2 Subprocessor AVVs + published subprocessor list

Your LLM provider and cloud host are **subprocessors** needing **back-to-back Art. 28(4) DPAs** with equivalent obligations. In your customer DPA, use **general authorization**: publish a subprocessor list, notify of changes, and give the customer a right to object. The EDPB requires disclosing the full subprocessor chain to the ultimate controller on request. Source: <https://www.orbiqhq.com/eu-regulations/subprocessor-management-gdpr-article-28>

A starter subprocessor-list table (fill with your actual vendors):

| Subprocessor | Purpose | Location / hosting region | Transfer safeguard | AVV signed |
|---|---|---|---|---|
| _Hosting provider (EU region)_ | Application + data hosting | EU (e.g. DE/EU region) | N/A (intra-EU) | ☐ |
| _LLM / inference provider_ | Enrichment + clustering + synthesis | EU-hosted preferred | If US-linked: SCCs + TIA or EU-US DPF | ☐ |
| _Email / support tooling_ | Transactional email, support | Prefer EU | SCCs if non-EU | ☐ |
| _Billing / MoR (if used)_ | Payments, invoicing | Per vendor | SCCs if non-EU | ☐ |

Publish this at a stable URL (e.g. `clara.example/subprocessors`) and reference it from the DPA.

### 2.3 TOMs annex — technical & organisational measures (Art. 32)

Attach a **TOMs annex** to the DPA. Document, at minimum:

- **Encryption** in transit (TLS) and at rest
- **Role-based access control** + **MFA**
- **Audit logging** (ties directly to the `governed/auditable` USP)
- **Pseudonymisation** where feasible
- **Backups** + tested restore
- **Incident response** with the **Art. 33 72-hour breach notification** to the controller
- **Tenant isolation** (multi-tenant separation)

Source: <https://gdpr-info.eu/art-28-gdpr/> · Your "governed and auditable" architecture is a selling point here — describe it concretely.

### 2.4 DPIA support pack (Art. 35) — you enable it, the customer runs it

A DPIA is **likely required** for CLARA's customers because the German DSK must-list flags **innovative technologies (explicitly AI)**, **large-scale processing**, and **systematic evaluation/profiling** — CLARA touches all three. The **controller (customer) owns** the DPIA, but you must **assist** (Art. 28(3)(f)). Source: <https://www.activemind.legal/law/de-dpia/>

Ship a **DPIA-support pack** ("CLARA processing facts sheet") so buyers can complete their DPIA quickly — a real friction-remover in enterprise procurement. Include: data categories processed, purposes, retention, subprocessor chain, TOMs summary, EU-residency statement, and no-training-on-customer-data toggle. **Note:** large-scale processing for *your own* purposes (the self-improving loop) may require **your own** DPIA as controller.

### 2.5 Breach / incident runbook (Art. 33)

A one-page runbook mapping the **72-hour** notification path to the controller, with roles, contacts, and a log template. Rehearse it once.

---

## 3. EU hosting / data-residency posture

EU residency is both a legal simplifier and CLARA's headline USP — DACH procurement treats it as a **precondition for the first call**, and "US platforms that process transcripts outside the EU are inherently non-compliant for sensitive German data." Source: <https://compound.law/en-DE/compliance/ai-customer-service-gdpr/>

**Posture rules:**

- Keep **hosting and inference in the EU**. Prefer **EU-hosted / open-weight models** to eliminate transfer exposure entirely.
- Any **US-based or US-parent subprocessor** (many LLM APIs) needs **Art. 46 safeguards**: **Standard Contractual Clauses (SCCs)** + a documented **Transfer Impact Assessment (TIA)**, *or* reliance on the vendor's **EU-US Data Privacy Framework** certification. Source: <https://commission.europa.eu/law/law-topic/data-protection/international-dimension-data-protection/new-standard-contractual-clauses-questions-and-answers-overview_en>
- Offer a **"disable model-training on customer data"** guarantee in the contract — a standard DACH procurement demand.
- Put "EU data residency, no data leaves the EU" on the pricing/security page and in a one-page **compliance datasheet** for security questionnaires.

**Residency checklist:**

- ☐ Hosting region confirmed EU (document the region)
- ☐ Inference EU-hosted, or SCCs + TIA on file for any non-EU model
- ☐ Subprocessor list reflects all data locations
- ☐ No-training-on-customer-data toggle documented and defaulted on
- ☐ Backups stay in the EU

---

## 4. EU AI Act — classification, obligations, timeline

### 4.1 Classification: limited/minimal risk — NOT prohibited, NOT high-risk

**Conclusion:** A **text-based** feedback-triage engine (sentiment + urgency + theme tagging + clustering + synthesis) is **effectively minimal/limited risk**. Write this up as a one-page **classification memo** and keep it on file to rebut any customer or regulator challenge.

**Justification (document this reasoning):**

- The **Art. 5(1)(f) prohibition** on "emotion recognition" covers only **biometric** systems in **workplace/education** contexts. Text-based sentiment is **expressly outside it** per Commission guidelines. Source: <https://oliverpatel.substack.com/p/emotion-recognition-and-the-eu-ai>
- **Annex III(1)(c) "emotion recognition"** (the high-risk head) **also targets biometric** systems. A text feedback-triage engine is therefore **not Annex III high-risk**.
- Because CLARA processes **text, not biometric data**, neither the prohibition nor the high-risk classification applies.

### 4.2 Your role: downstream AI-system provider (not a GPAI provider)

Placing an AI system on the EU market makes CLARA an **AI-system provider**. Because you adapt frontier models **without fine-tuning** above the ~1/3-compute "significant modification" threshold, you do **not** become a **GPAI model provider** and carry **no GPAI obligations**. Your duty is **vendor due diligence**: request the model vendor's **Annex XII downstream information package** and rely on their compliance. Source: <https://www.arnoldporter.com/en/perspectives/advisories/2025/08/does-your-company-have-eu-ai-act-compliance-obligations>

### 4.3 The obligations that DO apply to CLARA

| Obligation | What to do | Effort | Status/Deadline |
|---|---|---|---|
| **Art. 4 AI literacy** | Short internal AI-use policy + training record for anyone touching the system | Low | **In force since 2 Feb 2025** |
| **Art. 50 transparency** | Label AI output clearly ("AI-generated / AI-assisted") where end-users see/interact with it | Low–medium | **Applies 2 Aug 2026 (NOT deferred)** |
| **Vendor due diligence** | Keep the LLM vendor's compliance/Annex XII info package on file | Low | Ongoing |
| **Classification memo** | One-page memo concluding limited/minimal risk, citing biometric-only scope | Low | Now |

Sources: Art. 50 not deferred — <https://compliancehub.wiki/eu-ai-act-article-50-transparency-digital-omnibus-2026/> · timeline — <https://artificialintelligenceact.eu/implementation-timeline/>

### 4.4 EU AI Act timeline (track these dates)

| Date | Milestone | Relevance to CLARA |
|---|---|---|
| **2 Feb 2025** | Prohibited practices + **AI literacy** live | AI-literacy policy applies now |
| **2 Aug 2025** | GPAI model-provider obligations live | Not you (no GPAI); vendor due diligence |
| **2 Aug 2026** | **Art. 50 transparency** applies | Ship AI-labelling before this date |
| **2 Dec 2027** | Annex III high-risk (deferred from 2 Aug 2026 by the Digital Omnibus) | Not you today, but re-check if scope changes |
| **2 Aug 2028** | High-risk embedded in regulated products | Not you |

Source on the Digital Omnibus deferral (Council green light 29 Jun 2026, EP endorsed 16 Jun 2026): <https://www.gibsondunn.com/eu-ai-act-omnibus-agreement-postponed-high-risk-deadlines-and-other-key-changes/> — **verify final dates on Official Journal publication.**

### 4.5 Compliance as USP (the sales angle)

CLARA's customers are **deployers** with their own AI Act and GDPR duties. CLARA's built-in **tamper-resistant audit logs** and **human-in-the-loop** governance let buyers discharge *their own* obligations — a concrete purchase justification. Package a one-page **"AI Act & GDPR compliance datasheet"** (data residency, DPA/Art. 28, subprocessor list, no-training toggle, audit-log description) to survive DACH security questionnaires. Have counsel review before making categorical "AI Act compliant" marketing claims.

---

## 5. Website & legal pages required

Fix these **immediately** — stale references (e.g. "TMG", "Telemedien", ODR-platform link) invite an **Abmahnung**.

| Page | Legal basis | Must contain |
|---|---|---|
| **Impressum** | **§5 DDG** (TMG repealed **14 May 2024**); commercial comms §6 DDG | Full name, physical address, email **+ phone**, and your **USt-IdNr**. Remove any "TMG"/"Telemedien" relics. No explicit "per DDG" reference needed. |
| **Datenschutzerklärung** (privacy policy) | GDPR Art. 13/14 | Identity/contact, purposes + legal bases, recipients/subprocessors, transfers, retention, data-subject rights, contact point. Separate from the customer DPA. |
| **AGB / Terms of Service** | B2B SaaS contract | Subscription, SLA, liability caps, IP, term/termination; **AVV/DPA + TOMs as annexes**. **Drop** the EU ODR/OS-Plattform clause — that requirement **ended in 2025**. |
| **Cookie / consent banner** | **§25 TDDDG** (former TTDSG) | Prior informed consent for any **non-essential** storage/access on the user's device. Go **essential-only** to skip the banner entirely, or use a compliant CMP. The EinwV (central consent management) has been in force since 1 Apr 2025 (optional). |

Sources: DDG/Impressum + Datenschutzerklärung — <https://www.it-recht-kanzlei.de/tmg-ttdsg-ausser-kraft-impressum-datenschutz.html> · ODR clause removal — <https://www.apite.io/insights/ddg-ersetzt-tmg> · TDDDG §25 consent — <https://usercentrics.com/knowledge-hub/cookie-flood-control-consent-management-ordinance-tdddg/>

---

## 6. Master readiness checklist (phased)

### Phase 0 — Before the first paid B2B contract (do now)

- ☐ Engage a **Fachanwalt für IT-Recht/Datenschutz** to review the legal pack
- ☐ Confirm **Freiberufler vs Gewerbe** with a Steuerberater (flagged in the business-setup doc — do not invoice SaaS on an unverified status)
- ☐ Draft **customer-facing AVV/DPA** with all 9 Art. 28(3) elements
- ☐ Draft **TOMs annex** (encryption, RBAC+MFA, audit logging, backups, tenant isolation, 72h breach path)
- ☐ Sign **back-to-back AVVs** with hosting + LLM subprocessors
- ☐ Publish a **subprocessor list** at a stable URL, with general-authorization + right-to-object wording
- ☐ Confirm **EU hosting + EU inference**; put SCCs + TIA on file for any non-EU/US-linked vendor
- ☐ Write the **AI Act classification memo** (text-triage = limited/minimal risk, biometric-only scope of Art. 5(1)(f) / Annex III(1)(c))
- ☐ Add a short **AI-literacy policy + training log** (Art. 4 already in force)
- ☐ Stand up **Impressum (§5 DDG + USt-IdNr)**, **Datenschutzerklärung**, **B2B AGB**, and a **§25 TDDDG** banner (or go essential-only)
- ☐ Create **ROPA** (controller + processor versions)
- ☐ Write the **72-hour breach runbook**

### Phase 1 — Sales enablement (parallel)

- ☐ **DPIA support pack** / "CLARA processing facts" sheet for buyers
- ☐ One-page **AI Act & GDPR compliance datasheet** for security questionnaires
- ☐ **No-training-on-customer-data** toggle documented and default-on
- ☐ EU-residency + subprocessor sheet + right-to-be-forgotten process description
- ☐ Put "EU data residency, governed & auditable, GDPR + EU AI Act aligned, no frontier-model fine-tuning" on the pricing page

### Phase 2 — Before 2 Aug 2026 (AI Act transparency)

- ☐ Ship **Art. 50 "AI-generated / AI-assisted" labelling** across the product
- ☐ Re-verify Digital Omnibus final dates on Official Journal publication
- ☐ Review classification memo if product scope changes (e.g. voice/biometric data enters)

### Phase 3 — Scale hardening (as revenue/PII grows)

- ☐ Pursue **ISO 27001 / SOC 2** early — DACH shortlists filter on these
- ☐ Re-run ROPA + subprocessor list on each new feature/vendor (at least annually)
- ☐ Consider a **UG/GmbH** liability shield once handling real customer PII at scale (legal/tax decision, out of scope here)

---

## 7. Priority ranking (if you can only do five things)

1. **Customer AVV/DPA + TOMs annex + subprocessor list** — no DACH deal closes without it.
2. **EU hosting/inference confirmed** (SCCs + TIA for any exception) — the USP and the deal-unblocker.
3. **AI Act classification memo + AI-literacy policy** — cheap, already-live obligations; pre-empts objections.
4. **Website legals** (Impressum §5 DDG + USt-IdNr, Datenschutzerklärung, AGB, §25 TDDDG) — removes Abmahnung risk today.
5. **DPIA support pack + compliance datasheet** — turns compliance into a procurement accelerator and a sales asset.

---

> **Reminder — not legal or tax advice.** Confirm the legal pack with a German **Fachanwalt für IT-Recht/Datenschutz** and the tax status with a **Steuerberater** before relying on this. AI Act interpretation and DPIA scope are still being clarified by national authorities in 2026; have counsel review before making categorical "AI Act compliant" claims in marketing.
