# Data Processing Agreement (AVV / DPA) — Art. 28 GDPR

_A customer-facing Data Processing Agreement (Auftragsverarbeitungsvertrag) under Art. 28 GDPR that lets CLARA act as the customer's processor for ingested customer-feedback text, with TOMs, sub-processor and EU/international-transfer terms._

> ⚠️ **DRAFT — have a German Fachanwalt (IT-Recht/Datenschutz) review before use.**
> This is a founder-drafted template, not legal advice, and creates no lawyer–client relationship. The clause set, the Annexes, and especially the international-transfer mechanics (SCC module selection, transfer impact assessment) must be reviewed and adapted by a qualified German data-protection lawyer before you sign it with a customer. Fill every `{{PLACEHOLDER}}` before execution.

---

## How to use this template (delete this box before signing)

- **Role.** This DPA assumes **CLARA = processor**, **Customer = controller** for the customer-feedback text CLARA ingests and triages. CLARA is separately a *controller* for its own website/marketing/billing — that is **out of scope** here and governed by CLARA's Datenschutzerklärung.
- **Where it sits.** This AVV/DPA is an **exhibit/annex to the main SaaS contract (AGB / Master Services Agreement)**. On conflict about personal-data processing, this DPA prevails; on all other matters, the main agreement prevails (see §14).
- **Language.** Primary language English (CLARA sells cross-border in the EU). For a **German controller** that requires it, prepare a **German version**; if both are executed, state which language governs (§14.7). The AVV itself is not a statutorily German-only document (unlike the Impressum / Datenschutzerklärung), but many DACH buyers will expect a German text.
- **Placeholders.** `{{...}}` = fill before signing. Bracketed `[choose: A / B]` = pick one option.
- **Verify before use:** Art. 28(3) clause list against the current consolidated GDPR text; the SCC decision reference (Commission Implementing Decision **(EU) 2021/914**); and whether the Commission has adopted the **new/updated SCCs** that were consulted on in Q4 2024 (a set intended, among other things, to cover importers *already* subject to the GDPR) — as of drafting, **2021/914 remains the operative decision**. Sources are listed at the end.

---

## Data Processing Agreement (Auftragsverarbeitungsvertrag)

**pursuant to Article 28(3) of Regulation (EU) 2016/679 (General Data Protection Regulation, "GDPR")**

### Between

**(1) The Customer — "Controller"**

| Field | Value |
|---|---|
| Legal name | `{{CUSTOMER_LEGAL_NAME}}` |
| Legal form | `{{CUSTOMER_LEGAL_FORM}}` |
| Registered address | `{{CUSTOMER_ADDRESS}}` |
| Company register / no. | `{{CUSTOMER_REGISTER_NO}}` |
| Represented by | `{{CUSTOMER_SIGNATORY_NAME}}, {{CUSTOMER_SIGNATORY_ROLE}}` |
| Contact for data-protection matters | `{{CUSTOMER_DP_CONTACT}}` (`{{CUSTOMER_DP_EMAIL}}`) |
| DPO (if appointed) | `{{CUSTOMER_DPO_NAME_OR_NA}}` |

**and**

**(2) CLARA — "Processor"**

| Field | Value |
|---|---|
| Legal name | `{{CLARA_LEGAL_NAME}}` (trading as "CLARA") |
| Legal form | `{{CLARA_LEGAL_FORM}}` |
| Registered address | `{{CLARA_ADDRESS}}` |
| Company register / no. | `{{CLARA_REGISTER_NO_OR_NA}}` |
| USt-IdNr | `{{CLARA_VAT_ID}}` |
| Represented by | `{{CLARA_SIGNATORY_NAME}}, {{CLARA_SIGNATORY_ROLE}}` |
| Contact for data-protection matters | `{{CLARA_DP_CONTACT}}` (`{{CLARA_DP_EMAIL}}`) |
| DPO (if appointed) | `{{CLARA_DPO_NAME_OR_NA}}` |
| EU representative (if applicable, Art. 27) | `{{CLARA_EU_REP_OR_NA}}` |

each a "**Party**" and together the "**Parties**".

---

### Recitals

(A) The Parties have entered into a main agreement for the provision of the CLARA software-as-a-service platform, an AI-assisted customer-feedback triage service (the "**Main Agreement**").

(B) In providing the service, the Processor processes personal data contained in customer-feedback text (e.g. app-store reviews, online reviews, support messages) **on behalf of and on the documented instructions of the Controller**.

(C) The Parties therefore conclude this Data Processing Agreement ("**DPA**") to satisfy Article 28(3) GDPR and, where applicable, § 26 BDSG and any other applicable Union or Member State data-protection law.

(D) This DPA applies to all processing of personal data carried out by the Processor for the Controller under the Main Agreement.

---

### 1. Definitions and order of precedence

1.1 Terms such as "personal data", "processing", "controller", "processor", "sub-processor", "data subject", "personal data breach", "supervisory authority" and "special categories of personal data" have the meanings given in **Art. 4 and Art. 9 GDPR**.

1.2 "**Applicable Data Protection Law**" means the GDPR and all supplementary Union or Member State law applicable to the processing, including the German **BDSG** and, where relevant, the **TDDDG**.

1.3 "**Standard Contractual Clauses**" or "**SCCs**" means the standard contractual clauses for the transfer of personal data to third countries adopted by the European Commission in **Implementing Decision (EU) 2021/914 of 4 June 2021**, as amended or replaced from time to time.

1.4 In case of conflict, the order of precedence is: (1) the SCCs (where they apply to a specific transfer); (2) this DPA; (3) the Main Agreement. This DPA prevails over the Main Agreement on all matters concerning the processing of personal data.

---

### 2. Subject-matter, nature, purpose and duration of the processing — Art. 28(3)

2.1 **Subject-matter.** The processing by the Processor of personal data contained in customer-feedback text submitted, ingested or connected by the Controller to the CLARA platform, for the purpose of providing the CLARA service.

2.2 **Nature of the processing.** Collection/ingestion, storage, structuring, automated analysis (sentiment, urgency and theme classification), clustering, de-duplication, synthesis/summarisation, display, export, and — at the end of the relationship — deletion or return. Processing is carried out by automated means.

2.3 **Purpose.** Solely to provide, maintain, secure and support the CLARA customer-feedback triage service for the Controller under the Main Agreement, and for no other purpose.

2.4 **Duration.** The processing lasts for the term of the Main Agreement and ends in accordance with §11 (deletion/return). This DPA remains in force for as long as the Processor processes personal data on behalf of the Controller.

2.5 **Details** of the processing — categories of data subjects, types of personal data, and any special categories — are set out in **Annex 1**.

---

### 3. Processing only on documented instructions — Art. 28(3)(a)

3.1 The Processor shall process the personal data **only on documented instructions** from the Controller, including with regard to international transfers, unless required to do so by Union or Member State law to which the Processor is subject. In such a case, the Processor shall inform the Controller of that legal requirement **before** processing, unless that law prohibits such information on important grounds of public interest.

3.2 The Controller's **initial and standing instructions** are: (a) this DPA; (b) the Main Agreement; and (c) the Controller's use and configuration of the CLARA platform through its documented features and settings. Any additional or changed instruction must be given in text form (email suffices) to the Processor's data-protection contact and, if it materially changes scope, may entitle the Processor to reasonable remuneration and/or a schedule adjustment.

3.3 The Processor shall **not** use the personal data for its own purposes. In particular, the Processor shall **not** use Controller personal data to train, fine-tune or otherwise develop its own or any third party's AI/ML models, except where such data has been effectively anonymised such that it is no longer personal data, and only to the extent permitted by the Main Agreement.

3.4 **Notice of unlawful instruction — Art. 28(3), final paragraph.** The Processor shall **immediately inform** the Controller if, in its opinion, an instruction infringes the GDPR or other Applicable Data Protection Law. The Processor may suspend execution of the affected instruction until the Controller confirms or amends it, without liability for the suspension.

---

### 4. Confidentiality — Art. 28(3)(b)

4.1 The Processor shall ensure that persons authorised to process the personal data have **committed themselves to confidentiality** or are under an appropriate statutory obligation of confidentiality (e.g. § 203 StGB where applicable).

4.2 The Processor shall grant access to the personal data only to personnel who need it to perform the Main Agreement ("need-to-know"), shall bind them in writing to confidentiality and to the instructions of this DPA, and shall ensure the obligation survives termination of their engagement.

---

### 5. Technical and organisational measures (security) — Art. 28(3)(c) / Art. 32

5.1 The Processor shall implement and maintain **appropriate technical and organisational measures ("TOMs")** to ensure a level of security appropriate to the risk, in accordance with **Art. 32 GDPR**, taking into account the state of the art, the costs of implementation, and the nature, scope, context and purposes of processing as well as the risk to data subjects.

5.2 The measures in force at the time of signing are described in **Annex 2 (Technical and Organisational Measures)**. Annex 2 addresses, at minimum: pseudonymisation and encryption where appropriate; confidentiality, integrity, availability and resilience of systems; the ability to restore availability after an incident; and a process for regularly testing and evaluating the effectiveness of the measures (**Art. 32(1)(a)–(d)**).

5.3 The Processor may **update** the TOMs to keep pace with technical developments, provided the level of protection is **not reduced below** that described in Annex 2. Material changes will be made available to the Controller.

5.4 The Processor's platform and the personal data are hosted in the **`{{HOSTING_LOCATION_EU_REGION}}`** region within the EU/EEA; see §10 and Annex 3 for any processing outside the EU/EEA.

---

### 6. Engagement of sub-processors — Art. 28(2), (3)(d) and (4)

6.1 **General authorisation.** The Controller grants the Processor **general written authorisation** to engage sub-processors for the provision of the service. The sub-processors engaged at the date of this DPA are listed in **Annex 3** (and/or at the URL stated there).

6.2 **Notice and right to object.** The Processor shall inform the Controller of any **intended addition or replacement** of a sub-processor at least **`{{SUBPROC_NOTICE_DAYS, e.g. 30}}` days** in advance (by email and/or by updating the published sub-processor list with a subscription/notification option), thereby giving the Controller the opportunity to **object** on reasonable data-protection grounds. If the Controller objects in writing within `{{OBJECTION_WINDOW_DAYS, e.g. 30}}` days and the objection is not resolved, either Party may terminate the affected part of the service; the Controller's sole remedy is such termination and a pro-rata refund of prepaid fees.

6.3 **Back-to-back obligations — Art. 28(4).** Where the Processor engages a sub-processor, it shall impose on that sub-processor, **by written contract**, data-protection obligations **the same as** those set out in this DPA (in particular sufficient guarantees under Art. 28(1) and the Art. 32 security obligations). Where the sub-processor fails to fulfil its data-protection obligations, the **Processor remains fully liable** to the Controller for the performance of that sub-processor's obligations.

6.4 The Processor shall, on request, make available to the Controller a copy of the relevant sub-processor terms (which may be redacted for commercial confidentiality) and disclose the sub-processing chain relevant to the Controller's data.

---

### 7. Assistance with data-subject rights — Art. 28(3)(e)

7.1 Taking into account the nature of the processing, the Processor shall assist the Controller by **appropriate technical and organisational measures**, insofar as this is possible, in fulfilling the Controller's obligation to respond to requests from data subjects exercising their rights under **Chapter III GDPR** (Art. 15–22), including access, rectification, erasure, restriction, data portability, and objection.

7.2 If a data subject contacts the **Processor** directly with such a request, the Processor shall **not respond on the merits** but shall forward the request to the Controller **without undue delay** and, unless legally prohibited, inform the data subject that the Controller is responsible.

7.3 The Processor shall make available to the Controller platform functionality and/or reasonable manual support to locate, export, correct or delete personal data relating to a data subject. Assistance beyond standard platform features may be invoiced at the Processor's then-current rates, to the extent permitted.

---

### 8. Assistance with the controller's Art. 32–36 obligations — Art. 28(3)(f)

8.1 Taking into account the nature of the processing and the information available to it, the Processor shall assist the Controller in ensuring compliance with:

- **Art. 32** — security of processing;
- **Art. 33 / 34** — personal data breach notification to the supervisory authority and communication to data subjects;
- **Art. 35** — data protection impact assessment (DPIA); and
- **Art. 36** — prior consultation with the supervisory authority.

8.2 **Breach notification.** The Processor shall notify the Controller **without undue delay** (and in any event within **`{{BREACH_NOTICE_HOURS, e.g. 48}}` hours**) after becoming aware of a **personal data breach** affecting the Controller's data. The notification shall, to the extent known, describe the nature of the breach, the categories and approximate number of data subjects and records concerned, the likely consequences, and the measures taken or proposed. The Processor shall provide further information in phases as it becomes available and shall reasonably cooperate so the Controller can meet its **72-hour** obligation under Art. 33(1). The Processor shall **not** notify the supervisory authority or data subjects on the Controller's behalf unless expressly instructed.

8.3 **DPIA support pack.** The Processor shall make available documentation (data-flow description, categories of data, TOMs, sub-processor list, transfer information) sufficient for the Controller to carry out a DPIA and, where required, a prior consultation.

---

### 9. Audit, inspection and demonstration of compliance — Art. 28(3)(h)

9.1 The Processor shall **make available to the Controller all information necessary** to demonstrate compliance with the obligations laid down in Art. 28, and shall **allow for and contribute to audits, including inspections**, conducted by the Controller or another auditor mandated by the Controller.

9.2 **Practical conduct.** To limit disruption while preserving the Controller's Art. 28(3)(h) right:

- The Processor may first satisfy an audit request by providing **up-to-date certifications, reports or third-party audit summaries** (e.g. ISO/IEC 27001, SOC 2, or an approved code of conduct/certification under Art. 40/42) where available.
- If these are insufficient for a specific, documented concern, the Controller (or its independent auditor, bound to confidentiality and not a competitor of the Processor) may conduct an on-site or remote audit, on **`{{AUDIT_NOTICE_DAYS, e.g. 30}}` days** prior written notice, during normal business hours, **no more than once per 12-month period** except where required by a supervisory authority or following a personal data breach.
- Audits must not compromise the security or confidentiality of other customers' data. The Controller bears its own audit costs; the Processor's reasonable assistance beyond `{{FREE_AUDIT_HOURS}}` hours may be invoiced.

9.3 The Processor shall inform the Controller if it considers that an audit instruction infringes the GDPR or other Applicable Data Protection Law.

---

### 10. International transfers — SCCs 2021/914 and transfer impact assessment

10.1 **EU/EEA by default.** The Processor shall process the personal data **within the EU/EEA**. A transfer to, or access from, a **third country** (outside the EU/EEA) occurs only where identified in **Annex 3** and only subject to Chapter V GDPR.

10.2 **Adequacy first.** Transfers to a third country benefiting from a valid **European Commission adequacy decision** (Art. 45) are permitted for as long as that decision is in force.

10.3 **SCCs where no adequacy.** Where a sub-processor or transfer is **not** covered by an adequacy decision, the transfer shall be governed by the **Standard Contractual Clauses (Implementing Decision (EU) 2021/914)**, which the Parties (and, back-to-back, the relevant sub-processor) shall conclude, using:

- **Module Two (Controller → Processor)** for transfers where the Controller is the EU exporter and the Processor (or its non-EU affiliate) is the importer; and/or
- **Module Three (Processor → Sub-processor)** where the Processor is the EU exporter and a non-EU sub-processor is the importer.

For the SCCs so incorporated: **Clause 7 (docking)** `[choose: applies / does not apply]`; **Clause 9** general authorisation with `{{SUBPROC_NOTICE_DAYS}}`-day notice (option 2); **Clause 11** independent-dispute-resolution option `[choose: not used]`; **Clause 17** governing law = `{{SCC_GOVERNING_LAW_EU_MS, e.g. German law}}`; **Clause 18** forum = `{{SCC_FORUM_EU_MS}}`. The **Annexes I–III of the SCCs** are populated by **Annexes 1–3 of this DPA**.

10.4 **Transfer impact assessment (TIA) — Schrems II.** For each third-country transfer under §10.3, the Processor shall, in cooperation with the Controller, carry out and document a **transfer impact assessment** assessing whether the laws and practices of the destination country ensure a level of protection essentially equivalent to that in the EU, and shall implement **supplementary measures** (technical, e.g. strong encryption with EU-held keys; contractual; and organisational) where needed, consistent with **EDPB Recommendations 01/2020**. The Processor shall make its TIA available to the Controller on request and shall **notify the Controller** if it can no longer meet its SCC obligations or becomes subject to a third-country access request that conflicts with the SCCs.

10.5 **UK / Switzerland.** Where personal data of UK or Swiss data subjects is in scope, the Parties shall apply the **UK International Data Transfer Addendum** to the SCCs and/or the **Swiss FADP** adaptations, respectively `[include / delete as applicable]`.

---

### 11. Deletion or return at the end of processing — Art. 28(3)(g)

11.1 On termination or expiry of the Main Agreement, the Processor shall, **at the choice of the Controller**, **delete or return** all personal data processed on the Controller's behalf, and delete existing copies, **unless** Union or Member State law requires storage of the personal data.

11.2 The Controller shall state its choice (delete or return) in writing. Absent a choice within **`{{RETURN_WINDOW_DAYS, e.g. 30}}` days** of termination, the Processor shall **delete** the data. Return, where chosen, shall be in a **structured, commonly used, machine-readable format**.

11.3 The Processor shall delete the data **no later than `{{DELETION_DEADLINE_DAYS, e.g. 90}}` days** after termination, including from backups within the ordinary backup rotation cycle (backups are overwritten within `{{BACKUP_CYCLE_DAYS}}` days). The Processor shall **confirm deletion in writing** on request.

11.4 Data the Processor is legally required to retain shall be **isolated, access-restricted, and processed only for the retention purpose** until deletion is permitted.

---

### 12. Records, DPO and cooperation

12.1 The Processor maintains a **record of processing activities carried out on behalf of the Controller** in accordance with **Art. 30(2)**.

12.2 The Processor `[has appointed / is not required to appoint]` a **Data Protection Officer**; contact details are in the party table above (or in Annex 3).

12.3 Each Party shall, upon request, **cooperate with the competent supervisory authority** in the performance of its tasks.

---

### 13. Liability

13.1 Liability between the Parties for damage caused by processing is governed by **Art. 82 GDPR** and by the liability provisions of the Main Agreement. Nothing in this DPA limits any liability that cannot be limited under Applicable Data Protection Law or, where SCCs apply, under the SCCs (whose liability terms prevail for the transfers they govern).

---

### 14. Final provisions

14.1 **Term.** This DPA takes effect on the effective date of the Main Agreement and continues for as long as the Processor processes personal data for the Controller.

14.2 **Amendments.** Changes require text form. The Parties shall amend this DPA where necessary to comply with changes in Applicable Data Protection Law (e.g. adoption of updated SCCs).

14.3 **Severability.** If any provision is or becomes invalid, the remainder stays in force; the Parties shall replace the invalid provision with a valid one closest to its economic and data-protection purpose.

14.4 **No processing beyond scope.** The Processor shall not process personal data outside the scope of this DPA and the Controller's instructions.

14.5 **Governing law.** This DPA is governed by the law of **`{{GOVERNING_LAW, e.g. the Federal Republic of Germany}}`**, excluding conflict-of-laws rules; the SCCs' own governing-law clause prevails for the transfers they govern (§10.3).

14.6 **Jurisdiction.** Place of jurisdiction: **`{{JURISDICTION_VENUE, e.g. Berlin}}`**, to the extent legally permissible.

14.7 **Language.** This DPA is executed in **`{{LANGUAGE, e.g. English}}`**. `[If a German version is also executed: In case of discrepancy, the {{GOVERNING_LANGUAGE}} version prevails.]`

---

### Signatures

| Controller (`{{CUSTOMER_LEGAL_NAME}}`) | Processor (CLARA — `{{CLARA_LEGAL_NAME}}`) |
|---|---|
| Name: `{{CUSTOMER_SIGNATORY_NAME}}` | Name: `{{CLARA_SIGNATORY_NAME}}` |
| Role: `{{CUSTOMER_SIGNATORY_ROLE}}` | Role: `{{CLARA_SIGNATORY_ROLE}}` |
| Place / date: `{{______}}` | Place / date: `{{______}}` |
| Signature: `{{______}}` | Signature: `{{______}}` |

---

## Annex 1 — Details of the processing (populates SCC Annex I)

**1. Parties / roles**

- Data exporter / **Controller:** `{{CUSTOMER_LEGAL_NAME}}`, `{{CUSTOMER_ADDRESS}}`, contact `{{CUSTOMER_DP_CONTACT}}`. Role: controller.
- Data importer / **Processor:** `{{CLARA_LEGAL_NAME}}` (CLARA), `{{CLARA_ADDRESS}}`, contact `{{CLARA_DP_CONTACT}}`. Role: processor (AI customer-feedback triage SaaS).

**2. Categories of data subjects.** The individuals whose personal data appears in the customer-feedback text the Controller submits to CLARA — typically:

- The Controller's **customers / end users / app users**;
- **Reviewers and complainants** (app-store / review-site / support-channel authors);
- Any **third parties named** by such individuals inside free-text feedback.

**3. Types / categories of personal data.** As contained in feedback text and associated metadata, potentially including:

- **Identifiers**: username / handle / reviewer name, user or account ID, order/ticket reference;
- **Contact data** where included by the author: email address, phone number;
- **Content of communications**: the free-text feedback itself and any personal data the author chooses to include;
- **Technical/usage metadata** attached to the feedback: device/OS, app version, locale, star rating, timestamp, source channel.

> The Controller controls what it submits. CLARA does **not** require and does not solicit special-category or highly sensitive identifiers; the Controller should minimise/pseudonymise before ingestion where feasible.

**4. Special categories of personal data (Art. 9).** `[choose] `
- `[A] None intended.` Free-text feedback may **incidentally** contain special-category data (e.g. health or religious references an author volunteers). The Controller shall not deliberately route special-category data to CLARA. **Additional safeguards** where any such data may occur: restricted access, encryption, minimisation, and prompt review. **OR**
- `[B] The following special categories are in scope: {{LIST}}, with safeguards: {{SAFEGUARDS}}.`

**5. Nature and purpose of processing.** AI-assisted triage of customer feedback: ingestion, storage, automated sentiment/urgency/theme classification, clustering, de-duplication, synthesis/summarisation, display/export, deletion — solely to provide the CLARA service to the Controller (see §2).

**6. Frequency.** `[continuous / on-demand]` for the duration of the Main Agreement.

**7. Duration / retention.** For the term of the Main Agreement; deletion/return per §11. Configured retention: `{{RETENTION_PERIOD}}`.

**8. For SCC transfers:** competent supervisory authority = `{{LEAD_SA, e.g. the Berlin Beauftragte für Datenschutz und Informationsfreiheit}}` (the Controller's lead supervisory authority where the Controller is the exporter).

---

## Annex 2 — Technical and Organisational Measures (TOMs, Art. 32) — (populates SCC Annex II)

The Processor's technical and organisational measures are described in the separate document **`TOMs` (see `{{TOMS_DOC_REFERENCE_OR_URL}}`)**, which forms an integral part of this DPA and of SCC Annex II. Summary of measure categories (full detail in the TOMs document):

| Art. 32 area | Measures (summary — see TOMs doc for detail) |
|---|---|
| Pseudonymisation & encryption | Encryption in transit (TLS) and at rest; key management; pseudonymisation where feasible |
| Confidentiality (access control) | Physical access control at EU data-centre; role-based access; MFA; least privilege; need-to-know |
| Integrity | Transfer & input controls; audit logging; change management |
| Availability & resilience | Backups; redundancy; DDoS/resilience measures; documented restore capability (Art. 32(1)(c)) |
| Regular testing & evaluation | Vulnerability scanning / pen-testing cadence; review of TOMs effectiveness (Art. 32(1)(d)) |
| Sub-processor & transfer controls | Vendor due diligence; back-to-back DPAs; EU hosting; SCCs + TIA where non-EU |
| Data-subject support & deletion | Tooling for access/export/erasure; documented deletion workflow |

> **Fill before use:** replace the summary with, or attach, CLARA's actual TOMs document. The TOMs must be specific (not generic) to survive DACH security review.

---

## Annex 3 — Sub-processors (populates SCC Annex III) and international-transfer register

**Authorisation basis:** general written authorisation (§6). The current, authoritative sub-processor list is published at **`{{SUBPROCESSOR_LIST_URL}}`** and notification of changes is provided per §6.2. The list at the date of signing:

| # | Sub-processor | Purpose / service | Processing location | Transfer mechanism (if outside EU/EEA) |
|---|---|---|---|---|
| 1 | `{{HOSTING_PROVIDER, e.g. EU cloud host}}` | Infrastructure / hosting | `{{EU_REGION}}` (EU/EEA) | N/A — EU/EEA |
| 2 | `{{LLM_API_PROVIDER}}` | LLM inference for classification/synthesis (no fine-tuning) | `{{LLM_REGION}}` | `[EU/EEA — N/A]` **or** `[adequacy decision]` **or** `[SCCs 2021/914 Module 3 + TIA]` |
| 3 | `{{OTHER_SUBPROCESSOR}}` | `{{PURPOSE}}` | `{{LOCATION}}` | `{{MECHANISM}}` |

**International-transfer notes.**

- Preferred posture: **EU/EEA-only** processing (CLARA's data-residency USP). Keep this table EU-only wherever possible.
- For any row processed outside the EU/EEA without an adequacy decision: attach the concluded **SCCs (2021/914)** with the correct module (§10.3) and the documented **transfer impact assessment** (§10.4).
- Re-verify each provider's actual processing region and legal entity before signing — do not assume "EU region" means no third-country access.

---

### Sources (verify on execution)

- Art. 28 GDPR (processor; required contract clauses, sub-processor rules): <https://gdpr-info.eu/art-28-gdpr/>
- Art. 32 GDPR (security of processing / TOMs): <https://gdpr-info.eu/art-32-gdpr/>
- ICO — "What needs to be included in the contract?" (Art. 28(3) checklist): <https://ico.org.uk/for-organisations/uk-gdpr-guidance-and-resources/accountability-and-governance/contracts-and-liabilities-between-controllers-and-processors-multi/what-needs-to-be-included-in-the-contract/>
- Standard Contractual Clauses — Commission Implementing Decision (EU) 2021/914 (EUR-Lex): <https://eur-lex.europa.eu/eli/dec_impl/2021/914/oj/eng>
- European Commission — New SCCs, Questions & Answers overview: <https://commission.europa.eu/law/law-topic/data-protection/international-dimension-data-protection/new-standard-contractual-clauses-questions-and-answers-overview_en>
- EDPB Recommendations 01/2020 on supplementary measures (transfer impact assessment, post-Schrems II): <https://www.edpb.europa.eu/our-work-tools/our-documents/recommendations/recommendations-012020-measures-supplement-transfer_en>
- 2025 SCC update watch (Commission consultation Q4 2024; new SCCs for importers already subject to GDPR anticipated — 2021/914 remains operative until adopted): <https://www.privacyanddatasecurityinsight.com/2024/09/another-update-already-new-eu-standard-contractual-clauses-on-the-horizon-to-further-safeguard-cross-border-data-transfers/>

_Cross-references within the CLARA pack: role mapping and the compliance rationale are in `01-compliance-gdpr-eu-ai-act.md`. This DPA should be accompanied by the **TOMs** document (Annex 2) and the **sub-processor list** (Annex 3)._
