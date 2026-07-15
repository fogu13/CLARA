# CLARA — Subprocessor List (Public)

_This page lists the third-party subprocessors CLARA engages to process personal data on behalf of its business customers (controllers), together with the safeguards applied to any transfer outside the EEA. It is the living list referenced by, and incorporated into, CLARA's Data Processing Agreement (DPA / Auftragsverarbeitungsvertrag, "AVV") under Article 28 GDPR._

> **DRAFT — have a German Fachanwalt (IT-Recht/Datenschutz) review before use.**
> This is a template. Replace every `{{PLACEHOLDER}}` with CLARA's actual, verified data (real vendor legal names, hosting regions, and transfer mechanisms as they appear in each vendor's own DPA/sub-processor terms). Do **not** publish until a qualified German lawyer has confirmed the vendor set, the transfer safeguards, and the notice mechanics against your signed customer DPAs. Statute references were current as of `{{LAST_LEGAL_REVIEW_DATE}}` — re-verify before relying on them.

---

## 1. About this list

CLARA (`{{LEGAL_ENTITY_NAME}}`, `{{ADDRESS}}`, `{{COUNTRY}}`) provides an AI-assisted customer-feedback triage service. When a customer (the **controller**) sends customer-feedback text (app-store reviews, support messages, survey responses — which may contain personal data) into CLARA, CLARA acts as a **processor** under Article 28 GDPR and processes that data only on the customer's documented instructions.

To deliver the service, CLARA engages the third parties listed in Section 3 as **subprocessors** (further processors within the meaning of Article 28(2) and (4) GDPR). Each subprocessor is bound by a written contract imposing data-protection obligations that are, in substance, no less protective than those in CLARA's own DPA with its customers, as required by Article 28(4) GDPR.

**Scope note.** This list covers subprocessors that process **customer personal data ingested into the CLARA service** (CLARA acting as processor). It does **not** cover vendors CLARA uses purely as a **controller** for its own website, marketing, and corporate administration (e.g. Impressum obligations under § 5 DDG, cookie/consent handling under § 25 TDDDG) unless those vendors also touch ingested customer data — those are governed by CLARA's [Privacy Policy / Datenschutzerklärung]({{PRIVACY_POLICY_URL}}), not by the customer DPA. Where a vendor spans both roles, it is flagged in Section 3.

---

## 2. How to read the table

| Column | Meaning |
| --- | --- |
| **Subprocessor** | Legal entity actually contracted (name + country of establishment). |
| **Purpose / service** | What the subprocessor does for CLARA. |
| **Data categories processed** | Categories of personal data the subprocessor may process on CLARA's behalf. For CLARA these are primarily **free-text customer feedback that may contain PII** (names, contact details, or other identifiers a reviewer chooses to include), plus limited **account/identifier and technical metadata**. |
| **Location / processing region** | Region(s) where processing/storage takes place. |
| **Transfer safeguard** | The Chapter V GDPR basis for any transfer outside the EEA: **EEA-only** (no transfer), **Adequacy decision** (Art. 45), or **Standard Contractual Clauses** (Art. 46(2)(c), Commission Implementing Decision (EU) 2021/914) — with the relevant module and any supplementary measures / TIA reference. |

---

## 3. Current subprocessors

> Fill in each row with the **real** vendor and its **own** current terms. Verify the processing region and transfer mechanism against the vendor's published DPA / sub-processor page before publishing — vendors change regions and DPF certification status over time.

### 3.1 Core service delivery (process ingested customer feedback)

| # | Subprocessor | Purpose / service | Data categories processed | Location / processing region | Transfer safeguard |
| --- | --- | --- | --- | --- | --- |
| 1 | `{{LLM_PROVIDER_ENTITY}}` (e.g. inference API provider — legal entity, country) | **LLM inference** — classification, summarisation and triage of feedback text. CLARA uses the API **without fine-tuning/training**; provider engaged as downstream processor. Confirm zero-retention / no-training terms and any EU-region endpoint (e.g. `{{LLM_EU_ENDPOINT_OR_REGION}}`). | Customer-feedback text (may contain PII); derived labels/metadata. | `{{LLM_REGION}}` (e.g. EU region if offered, else US) | `{{LLM_SAFEGUARD}}` — EEA-only if EU endpoint; otherwise SCCs (2021/914, Module 3 processor-to-processor) + Transfer Impact Assessment, and/or provider's EU-US DPF certification if applicable. |
| 2 | `{{CLOUD_HOSTING_ENTITY}}` (e.g. cloud/infra provider — legal entity, country) | **Cloud hosting & storage** — application compute, database, object storage, backups for the CLARA service. | All ingested customer data at rest and in transit; account data; logs. | `{{HOSTING_REGION}}` (e.g. `eu-central-1` / Frankfurt) | `{{HOSTING_SAFEGUARD}}` — EEA-only if EU region selected; SCCs (Module 3) + supplementary measures if any provider support access from outside the EEA. |

### 3.2 Operational / supporting subprocessors

| # | Subprocessor | Purpose / service | Data categories processed | Location / processing region | Transfer safeguard |
| --- | --- | --- | --- | --- | --- |
| 3 | `{{ERROR_ANALYTICS_ENTITY}}` (e.g. error monitoring / product analytics — legal entity, country) | **Error tracking & product analytics** — application error/exception capture and usage telemetry. Configure PII scrubbing / data-minimisation so feedback text is **not** sent where avoidable. | Technical metadata, error payloads (may incidentally contain PII if not scrubbed), usage events, IP/device data. | `{{ERROR_ANALYTICS_REGION}}` | `{{ERROR_ANALYTICS_SAFEGUARD}}` — EEA-only / Adequacy / SCCs (Module 3) as applicable. |
| 4 | `{{EMAIL_ENTITY}}` (e.g. transactional email provider — legal entity, country) | **Transactional email** — service notifications, alerts, and account communications on CLARA's behalf. | Recipient name and email address; message content/metadata. | `{{EMAIL_REGION}}` | `{{EMAIL_SAFEGUARD}}` — EEA-only / Adequacy / SCCs (Module 3). |
| 5 | `{{BILLING_MOR_ENTITY}}` (e.g. billing / Merchant-of-Record — legal entity, country) | **Billing & payments (Merchant-of-Record).** Note: an MoR often acts as an **independent controller** for tax/payment purposes rather than as CLARA's processor — confirm the vendor's role. Included here for transparency. Typically processes **CLARA-customer contact/billing data**, not end-customer feedback. | Billing contact name, email, company, address, VAT/USt-IdNr, payment/transaction metadata (no card PAN held by CLARA). | `{{BILLING_MOR_REGION}}` | `{{BILLING_MOR_SAFEGUARD}}` — often controller-to-controller (Art. 45 Adequacy or SCCs Module 1) rather than an Art. 28 subprocessing. |

> **Role flag.** Rows 3–5 may be relevant to CLARA both as processor (if they touch ingested feedback) and as controller (CLARA's own operations). Where a vendor acts as an independent controller (e.g. a Merchant-of-Record for tax), it is **not** a subprocessor under Art. 28 and the change-notification right in Section 4 does not strictly apply — keep it in this list for transparency but label the role accurately.

### 3.3 Emergency / ad-hoc

CLARA may, in an emergency, engage a temporary subprocessor to protect the vital security or continuity of the service. In such a case CLARA will add the subprocessor to this list and notify customers as set out in Section 4 as soon as reasonably practicable.

---

## 4. Change notification and objection right

_This clause pairs with, and is incorporated by reference into, CLARA's DPA (Article 28 GDPR). The DPA grants CLARA a **general written authorisation** to engage subprocessors under Article 28(2), first sentence; this Section governs how changes are notified and objected to under Article 28(2), second sentence._

1. **General authorisation.** By entering into the DPA, the customer grants CLARA a **general written authorisation** to engage the subprocessors listed in Section 3 and to add or replace subprocessors in accordance with this Section (Art. 28(2) GDPR).

2. **Advance notice of changes.** Before a new or replacement subprocessor begins processing customer personal data, CLARA will give **at least `{{NOTICE_PERIOD_DAYS}}` days' (recommended: 30) advance notice** of the intended addition or replacement, identifying the subprocessor's name, location, and processing purpose. Notice is given by `{{NOTIFICATION_METHOD}}` (e.g. email to the customer's designated contact and/or update to this page with an RSS/email subscription at `{{SUBSCRIBE_URL}}`). Customers are responsible for keeping their notification contact current and, where notice is via this page, for subscribing to updates.

3. **Right to object.** Within the notice period, the customer may object to a new or replacement subprocessor on **reasonable data-protection grounds** by written notice to `{{DPO_OR_PRIVACY_CONTACT_EMAIL}}`, describing the grounds for the objection.

4. **Resolution of an objection.** If the customer objects, the parties will work in good faith to resolve the concern, which may include CLARA:
   (a) offering a commercially reasonable alternative (e.g. a different region or subprocessor) to avoid the processing objected to; or
   (b) recommending a configuration change that removes the objected-to processing.
   If, within `{{RESOLUTION_PERIOD_DAYS}}` days (recommended: 30), no reasonable resolution is found and CLARA elects to proceed with the subprocessor, **the customer may terminate the affected service** by written notice, as its sole and exclusive remedy, and receive a pro-rata refund of prepaid fees for the terminated portion, as set out in the DPA / Order Form.

5. **Deemed acceptance.** If the customer does not object within the notice period, the change is deemed accepted and CLARA may engage the subprocessor. (Under a general authorisation, notice followed by no objection is sufficient — Art. 28(2) GDPR.)

6. **Flow-down obligation.** CLARA will impose on each subprocessor, by written contract, data-protection obligations that are in substance no less protective than those in the DPA, and CLARA remains **fully liable** to the customer for the performance of each subprocessor's obligations (Art. 28(4) GDPR).

> **Drafting note.** Keep the notice period, resolution period, and remedy identical here and in the signed DPA — a mismatch is a common audit finding. EDPB **Opinion 22/2024** (adopted 7 Oct 2024) stresses that the controller must receive **enough information and enough time** for a meaningful, informed objection, and that the processor must be able to evidence the chain of subprocessor obligations. Ensure `{{NOTICE_PERIOD_DAYS}}` is genuinely long enough to act on.

---

## 5. Transfers outside the EEA

Where a subprocessor processes personal data outside the European Economic Area, CLARA relies on one of the Chapter V GDPR mechanisms noted in the table:

- **Adequacy decision** (Art. 45 GDPR) — for transfers to a third country the European Commission has recognised as adequate (including, where applicable, transfers to a US organisation self-certified under the **EU–US Data Privacy Framework**; verify the vendor's active certification at `{{DPF_LIST_URL}}`).
- **Standard Contractual Clauses** (Art. 46(2)(c) GDPR) — the SCCs in **Commission Implementing Decision (EU) 2021/914** (4 June 2021), using the applicable module (typically **Module 3, processor-to-processor**), supplemented where needed by a documented **Transfer Impact Assessment** and technical/organisational supplementary measures (encryption in transit and at rest, access controls, etc.).

Details of the safeguards for any specific transfer are available to customers on request to `{{DPO_OR_PRIVACY_CONTACT_EMAIL}}`.

---

## 6. Related documents and legal references

- **CLARA Data Processing Agreement (DPA / AVV)** — `{{DPA_URL}}` (Art. 28 GDPR).
- **Technical & Organisational Measures (TOMs)** — `{{TOMS_URL}}` (Art. 32 GDPR).
- **Privacy Policy / Datenschutzerklärung** — `{{PRIVACY_POLICY_URL}}`.
- **Imprint / Impressum** — `{{IMPRESSUM_URL}}` (§ 5 Digitale-Dienste-Gesetz (DDG); TMG repealed 14 May 2024).

**Key statutory references (verify at review):**
- Article 28 GDPR — processor / subprocessor obligations; Art. 28(2) (authorisation, notice, objection) and Art. 28(4) (flow-down + full liability).
- Commission Implementing Decision (EU) 2021/914 — Standard Contractual Clauses (Modules 1–4).
- Articles 44–46 GDPR — international transfers; Art. 45 adequacy; Art. 46(2)(c) SCCs.
- EDPB Opinion 22/2024 (7 Oct 2024) — subprocessor information and objection expectations.
- **EU AI Act (Regulation (EU) 2024/1689)** — CLARA is a downstream AI-system deployer/provider using a third-party model **without fine-tuning** (not a GPAI-model provider); its use case is limited/minimal risk. **Article 50 transparency obligations** (informing people they are interacting with / seeing AI output) apply from **2 August 2026** — factor this into the customer-facing notice, not this subprocessor list, but keep vendor AI terms consistent with it.

---

## 7. Document control

| Field | Value |
| --- | --- |
| Version | `{{VERSION}}` |
| Effective date | `{{EFFECTIVE_DATE}}` |
| Last updated | `{{LAST_UPDATED_DATE}}` |
| Last legal review | `{{LAST_LEGAL_REVIEW_DATE}}` by `{{REVIEWING_LAWYER}}` |
| Owner / contact | `{{DPO_OR_PRIVACY_CONTACT_EMAIL}}` |
| Change-notice subscription | `{{SUBSCRIBE_URL}}` |

---

_Language note: CLARA sells cross-border in the EU, so this list is maintained in **English** as the primary version. A **German** version is advisable for German customers and should be kept in sync; where German-law documents are legally required in German (Impressum, Datenschutzerklärung, and AGB for German consumers), those are maintained separately. In case of conflict, specify a controlling language in the DPA._
