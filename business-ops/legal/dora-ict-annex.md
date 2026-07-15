# DORA ICT-Services Annex — Art. 30 Regulation (EU) 2022/2554

_An annex to CLARA's Data Processing Agreement (AVV/DPA) and Main Agreement supplying the contractual provisions a **financial entity** customer (bank, payment/e-money institution, investment firm, insurer, crypto-asset service provider — e.g. a Trade-Republic-like fintech) must obtain from every **ICT third-party service provider** under Article 30 DORA, plus a pre-filled vendor data row for the customer's **Register of Information** (Art. 28(3) DORA)._

> ⚠️ **DRAFT — have a German Fachanwalt (IT-Recht/Datenschutz) review before use.**
> This is a founder-drafted template, not legal advice, and creates no lawyer–client relationship. DORA contractual mechanics (especially the Art. 30(3) critical-function extras, audit-rights scope, and exit/transition terms) must be reviewed by qualified counsel — ideally in the **same review pass as the AVV/TOMs trust pack** — before this annex is attached to any customer contract. Fill every `{{PLACEHOLDER}}` before execution. DORA has applied since **17 January 2025**; verify article references against the current consolidated text.

---

## How to use this template (delete this box before signing)

- **Why customers ask.** DORA (Regulation (EU) 2022/2554) obliges financial entities to include the **Art. 30(2)** minimum contractual provisions in *every* contract for ICT services, and to keep a **Register of Information** on all ICT providers (Art. 28(3), templates in Implementing Regulation (EU) 2024/2956). These demands arrive at CLARA as security questionnaires and contract redlines; this annex pre-answers them.
- **Where it sits.** This annex is an **exhibit to the Main Agreement**, alongside the AVV/DPA ([avv-dpa.md](avv-dpa.md)). It **does not duplicate** the AVV: parties, definitions, data-protection obligations, sub-processor mechanics, breach notice, audit conduct, and deletion/return are **incorporated by reference** from the AVV and only *extended* here where DORA requires more (e.g. non-personal data, insolvency scenarios, authority cooperation).
- **Critical-function posture.** At pilot stage, feedback triage would typically **not** be a "critical or important function" (Art. 3(22) DORA) for the customer. **Part A** (Art. 30(2)) therefore applies always; **Part B** (Art. 30(3)) applies **only if** the customer designates the function as critical or important in §2 — in which case pricing, SLA, and audit scope must be renegotiated.
- **Language.** English primary, matching the AVV (§14.7 of the AVV governs language/precedence). German version on request for DACH buyers.
- **Placeholders.** `{{...}}` = fill before signing. Bracketed `[choose: A / B]` = pick one option.

---

## ICT-Services Annex (DORA)

**to the Main Agreement and the Data Processing Agreement between the Parties, pursuant to Article 30 of Regulation (EU) 2022/2554 on digital operational resilience for the financial sector ("DORA")**

### 1. Parties, incorporation and precedence

1.1 This Annex is entered into between the **Customer** (a financial entity within the meaning of Art. 2 DORA — the "**Financial Entity**") and **CLARA** (`{{CLARA_LEGAL_NAME}}`, acting as an ICT third-party service provider within the meaning of Art. 3(19) DORA — the "**Provider**"), each as identified in the party table of the AVV/DPA ([avv-dpa.md](avv-dpa.md)), which is incorporated here by reference.

1.2 Terms defined in the AVV/DPA have the same meaning here. DORA terms ("ICT services", "ICT-related incident", "critical or important function", "ICT third-party service provider") have the meanings given in **Art. 3 DORA**.

1.3 **Precedence.** On matters of digital operational resilience under DORA, this Annex prevails over the Main Agreement; on matters of personal-data processing, the AVV/DPA (and, where applicable, the SCCs) prevails per §1.4 of the AVV. This Annex, the AVV and the Main Agreement together form the single written contractual arrangement contemplated by **Art. 30(1) DORA**.

---

### 2. Classification — critical or important function (Art. 3(22) DORA)

2.1 The Parties record the Financial Entity's own assessment of whether the CLARA service supports a **critical or important function**:

| Field | Value |
|---|---|
| Function supported | AI-assisted triage of customer-feedback text (see §3) |
| Designated critical or important? | `[choose: No (default) / Yes — Part B applies]` |
| Financial Entity's function identifier (for its Register of Information) | `{{CUSTOMER_FUNCTION_ID_OR_NA}}` |
| Date of assessment | `{{ASSESSMENT_DATE}}` |

2.2 **Default posture.** CLARA is an analytics/triage layer over feedback the Financial Entity already holds; disruption of the service does not, by itself, interrupt the Financial Entity's regulated services. The Parties therefore assume **no critical-or-important designation** unless the Financial Entity states otherwise in §2.1. The Financial Entity shall **notify the Provider in writing** if it later designates the function as critical or important; Part B then applies from the date agreed in a written amendment (including any adjusted fees).

---

## Part A — Provisions for all ICT services (Art. 30(2) DORA)

### 3. Description of functions and ICT services — Art. 30(2)(a)

3.1 The Provider provides the **CLARA software-as-a-service platform**: ingestion, storage, automated analysis (sentiment, urgency and theme classification), clustering, de-duplication, synthesis/summarisation, display and export of customer-feedback text, as further described in **§2 and Annex 1 of the AVV** and the Main Agreement / Order Form `{{ORDER_FORM_REF}}`. No other ICT services are in scope.

3.2 **Subcontracting.** Subcontracting of the ICT service is **permitted** under the conditions of **§6 of the AVV** (general written authorisation, `{{SUBPROC_NOTICE_DAYS}}`-day advance notice, right to object, full back-to-back flow-down and Provider liability). The current subcontractor chain is the published subprocessor list ([subprocessor-list.md](subprocessor-list.md), `{{SUBPROCESSOR_LIST_URL}}`), incorporated by reference. For DORA purposes, the notice under §6.2 of the AVV also identifies the subcontractor's **location** and the service it supports.

### 4. Locations of provision and of data processing — Art. 30(2)(b)

4.1 The ICT service is provided from **`{{PROVISION_COUNTRY, e.g. Germany}}`**. Data — personal and non-personal — is processed and stored **exclusively within the EU/EEA**, in region **`{{HOSTING_LOCATION_EU_REGION}}`** (see §5.4 and §10.1 of the AVV and §1/§6 of the TOMs, [toms.md](toms.md)), including backups.

4.2 The Provider shall **notify the Financial Entity in advance** of any envisaged change to the locations in §4.1 (country of provision, processing or storage location), with the same **`{{SUBPROC_NOTICE_DAYS}}`-day** notice and objection mechanics as §6.2 of the AVV, so a single notice channel serves both GDPR and DORA.

### 5. Availability, authenticity, integrity and confidentiality of data — Art. 30(2)(c)

5.1 The Provider maintains the technical and organisational measures described in the **TOMs** ([toms.md](toms.md)), which form Annex 2 of the AVV and are incorporated here. In particular: encryption in transit and at rest (TOMs §2.4), access control and tenant isolation via row-level security (TOMs §2.2–2.3), integrity and input controls with append-only audit logging (TOMs §3), availability, backups and disaster recovery (TOMs §4), and regular testing and evaluation (TOMs §5).

5.2 These measures protect **personal and non-personal data alike**; the Art. 32 GDPR baseline in the AVV (§5) is not reduced by anything in this Annex.

### 6. Access, recovery and return of data; insolvency and discontinuation — Art. 30(2)(d)

6.1 The Financial Entity can **export its workspace data at any time** during the term via the product's export functions, in a structured, commonly used, machine-readable format (see §11.2 of the AVV and TOMs §9) — including the per-workspace **audit trail** (TOMs §3.2).

6.2 On **termination or expiry**, deletion or return of data follows **§11 of the AVV**, extended for DORA purposes to cover **non-personal data** of the Financial Entity on the same terms and timelines.

6.3 In the event of the Provider's **insolvency, resolution or discontinuation of business operations**, the Provider shall (to the extent legally able) maintain the Financial Entity's access to its data and export functions for at least **`{{INSOLVENCY_ACCESS_DAYS, e.g. 30}}` days** after notice of the event, and shall in any case not withhold data as leverage in any dispute.

### 7. Service levels — Art. 30(2)(e)

7.1 Service-level descriptions, including the availability target of **`{{UPTIME_TARGET, e.g. 99.5%}}`** measured monthly, support channels and response times, are set out in `{{SLA_REF, e.g. the Order Form / SLA schedule of the Main Agreement}}`. Updates and revisions to the service description or SLA are made per the change mechanics of the Main Agreement and never reduce the protections in §5.

> **Drafting note (delete):** Art. 30(2)(e) requires service-level *descriptions* for all ICT services; precise quantitative/qualitative *targets* are only mandatory under Art. 30(3)(a) for critical functions. At pilot stage, keep the SLA honest and modest — do not promise enterprise SLOs the solo-operated stack cannot evidence (see the solo-founder note in TOMs §4).

### 8. Incident assistance — Art. 30(2)(f)

8.1 Where an **ICT-related incident** connected to the CLARA service occurs, the Provider shall provide assistance to the Financial Entity `[choose: at no additional cost / at the ex-ante rates in {{RATE_CARD_REF}}]` — incidents caused by the Provider's own failure are always assisted at no additional cost.

8.2 **Notification.** The Provider shall notify the Financial Entity of any incident affecting the confidentiality, integrity or availability of the Financial Entity's data **without undue delay and in any event within the `{{BREACH_NOTICE_HOURS, e.g. 48}}`-hour deadline of §8.2 of the AVV** (personal-data breaches) — the same clock applies to security incidents involving non-personal data, so the two regimes never diverge. Contact path, content and phased follow-up per §8.2 of the AVV and TOMs §8. This enables the Financial Entity to meet its own incident-reporting clocks under **Art. 19 DORA**.

### 9. Cooperation with competent and resolution authorities — Art. 30(2)(g)

9.1 The Provider shall **fully cooperate** with the competent authorities and resolution authorities of the Financial Entity (including **BaFin**, the Deutsche Bundesbank, the ECB, or persons appointed by them), including providing information relating to the ICT service that such authorities lawfully request in connection with their supervision of the Financial Entity.

### 10. Termination rights and notice periods — Art. 30(2)(h)

10.1 Ordinary termination follows the Main Agreement (notice period **`{{TERMINATION_NOTICE, e.g. 3 months to term end}}`**).

10.2 In addition, the Financial Entity may terminate this Annex and the affected ICT service in the circumstances contemplated by **Art. 28(7) DORA**, namely: (a) significant breach by the Provider of applicable law or the contractual arrangement; (b) circumstances identified in monitoring that could alter the performance of the ICT service, including material changes affecting the arrangement or the Provider's situation; (c) evidenced weaknesses in the Provider's overall ICT risk management, in particular regarding availability, authenticity, integrity or confidentiality of data; (d) where the competent authority can no longer effectively supervise the Financial Entity as a result of the arrangement. Notice period for such termination: **`{{DORA_TERMINATION_NOTICE, e.g. 30}}` days**, or shorter where an authority so requires.

10.3 Termination assistance (export, deletion/return, reasonable handover cooperation) follows §6 above and §11 of the AVV.

### 11. Security awareness and resilience training — Art. 30(2)(i)

11.1 On the Financial Entity's reasonable request, the Provider shall participate in the Financial Entity's **ICT security awareness programmes and digital operational resilience training** (Art. 13(6) DORA) relevant to the CLARA service — remotely, up to **`{{TRAINING_HOURS, e.g. 4}}` hours per contract year** at no additional cost; additional participation at the ex-ante rates in `{{RATE_CARD_REF}}`.

### 12. Audit and information rights

12.1 The Financial Entity's audit, inspection and information rights, and the certification-first conduct of audits, are governed by **§9 of the AVV**, which the Parties apply equally to DORA-driven reviews. Nothing in §9 of the AVV limits the authority-cooperation duty in §9 of this Annex.

---

## Part B — Additional provisions **only** where the function is designated critical or important (Art. 30(3) DORA)

> **Applies only if §2.1 says "Yes".** At pilot stage CLARA does not offer these terms by default; a critical-or-important designation triggers a commercial and legal renegotiation (SLA uplift, audit scope, pricing). The table shows what each Art. 30(3) element would require so the Parties can scope it quickly.

| Art. 30(3) | Requirement | CLARA posture if designated |
|---|---|---|
| (a) | **Full service-level descriptions** with precise quantitative and qualitative performance targets | Replace §7 with a measured SLO schedule `{{SLO_SCHEDULE_REF}}`; agreed remedies/credits |
| (b) | **Notice periods and reporting obligations** for developments materially impacting the service | Provider notifies material developments within `{{MATERIAL_CHANGE_NOTICE_DAYS}}` days |
| (c) | **Business contingency plans**; ICT security measures, tools and policies; implementation and **testing** | DR runbook + restore testing per TOMs §4–5, extended with customer-visible test evidence `{{EVIDENCE_REF}}` |
| (d) | Participation in the Financial Entity's **threat-led penetration testing (TLPT)** (Art. 26–27 DORA) | Provider participates and fully cooperates; scope/cost agreed per exercise |
| (e) | **Unrestricted rights of access, inspection and audit** by the Financial Entity, appointed third parties and the competent authority; full cooperation in onsite inspections | Extends §9 of the AVV: frequency cap and certification-first conduct do not apply to competent-authority inspections; onsite access on `{{ONSITE_NOTICE_DAYS}}` days' notice |
| (f) | **Exit strategy**: mandatory adequate **transition period** during which the Provider continues the service; support for migration to another provider or in-house solution | Transition period `{{TRANSITION_MONTHS, e.g. 6}}` months post-termination at then-current fees; export + reasonable migration assistance; data return per §6 |

---

## Register of Information — pre-filled CLARA vendor row (Art. 28(3) DORA)

_The Financial Entity must record every ICT provider in its **Register of Information** using the templates of **Implementing Regulation (EU) 2024/2956** and report it to its competent authority. The row below pre-answers the vendor-side fields so the Financial Entity's compliance team can copy them in. Verify field names and codes against the current ITS annexes before submission._

| RoI field (ITS — verify exact template/column) | CLARA value |
|---|---|
| Name of ICT third-party service provider | `{{CLARA_LEGAL_NAME}}` (legal name as in the Impressum, [impressum.md](impressum.md)), trading as "CLARA" |
| Identification code / type of code | LEI: `{{CLARA_LEI}}` `[or, if registered in the Handelsregister: EUID {{CLARA_EUID}}]` |
| Country of the provider's headquarters | Germany (DE) |
| Type of ICT service (ITS taxonomy) | Cloud services: **SaaS** — `{{TAXONOMY_CODE — verify against the ICT-services list in the ITS annex}}` |
| Country of provision of the ICT service | `{{PROVISION_COUNTRY, e.g. Germany (DE)}}` |
| Storage of data | Yes |
| Location of data at rest (storage) | `{{HOSTING_LOCATION_EU_REGION}}` — EU/EEA only |
| Location of data processing | EU/EEA only (see §4 above; AVV §10.1) |
| Sensitiveness of data | Per the Financial Entity's own classification; categories per Annex 1 of the AVV (customer-feedback text, may contain personal data) |
| Subcontractors (rank 2 and below) | Chain per the published subprocessor list ([subprocessor-list.md](subprocessor-list.md)): hosting `{{CLOUD_HOSTING_ENTITY}}`, LLM inference `{{LLM_PROVIDER_ENTITY}}`, `{{OTHER_SUBPROCESSORS}}` — locations and safeguards as listed there |
| Supports a critical or important function | `[No (default — see §2) / Yes]` — the Financial Entity's own assessment |
| Substitutability assessment | `{{CUSTOMER_ASSESSMENT — suggested basis: standard SaaS with machine-readable full export and no proprietary lock-in; alternative feedback-triage providers exist → typically "easily substitutable"}}` |
| Exit strategy / exit plan | Data export + deletion/return per §6 of this Annex and §11 of the AVV; transition assistance per Part B(f) if designated critical |
| Contract reference / start and end date | `{{CONTRACT_REF}}` / `{{START_DATE}}` – `{{END_DATE_OR_INDEFINITE}}` |
| Notice period for termination | `{{TERMINATION_NOTICE}}` (ordinary); `{{DORA_TERMINATION_NOTICE}}` days (Art. 28(7) grounds, §10.2) |
| Governing law of the arrangement | `{{GOVERNING_LAW}}` (per §14.5 of the AVV) |
| Annual expense / estimated cost | `{{ANNUAL_FEES}}` `{{CURRENCY}}` (per Order Form) |

> **LEI note (founder action, delete before sending):** a solo Einzelunternehmen without a Handelsregister entry has **no EUID**, so fintech customers will ask for an **LEI** for their Register of Information. LEIs are issued to sole proprietors by accredited LEI issuers for a modest annual fee — obtain one **before** the first fintech pilot signs, or the customer's RoI submission stalls on your row.

---

### Signatures

_Executed as an annex to the Main Agreement and the AVV/DPA; signature by the persons identified in the AVV party table._

| Financial Entity (`{{CUSTOMER_LEGAL_NAME}}`) | Provider (CLARA — `{{CLARA_LEGAL_NAME}}`) |
|---|---|
| Name: `{{CUSTOMER_SIGNATORY_NAME}}` | Name: `{{CLARA_SIGNATORY_NAME}}` |
| Role: `{{CUSTOMER_SIGNATORY_ROLE}}` | Role: `{{CLARA_SIGNATORY_ROLE}}` |
| Place / date: `{{______}}` | Place / date: `{{______}}` |
| Signature: `{{______}}` | Signature: `{{______}}` |

---

### Sources (verify on execution)

- DORA — Regulation (EU) 2022/2554 (digital operational resilience for the financial sector), applicable since 17 Jan 2025; Art. 28 (general principles, register of information, termination), Art. 30 (key contractual provisions): <https://eur-lex.europa.eu/eli/reg/2022/2554/oj>
- Implementing Regulation (EU) 2024/2956 — ITS on the Register of Information templates (Art. 28(9) DORA): <https://eur-lex.europa.eu/eli/reg_impl/2024/2956/oj>
- ESAs — Register of Information (reporting, taxonomy, validation): <https://www.eba.europa.eu/activities/direct-supervision-and-oversight/digital-operational-resilience-act>
- BaFin — DORA supervision hub (German competent authority): <https://www.bafin.de/DE/Aufsicht/DORA/DORA_node.html>

_Cross-references within the CLARA pack: parties/definitions/data-protection terms in [avv-dpa.md](avv-dpa.md); security measures in [toms.md](toms.md) (cited by TOMs section above); subcontractor chain and change notice in [subprocessor-list.md](subprocessor-list.md); provider identity in [impressum.md](impressum.md); the NIS2-side counterpart is [nis2-supply-chain-statement.md](nis2-supply-chain-statement.md)._
