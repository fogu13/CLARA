# Website Privacy Policy (Datenschutzerklärung)

*This is the controller-side privacy policy for the CLARA public website, marketing pages, and billing — governing personal data CLARA collects about visitors, leads, and account signers. It is distinct from the customer-facing Data Processing Agreement (AVV/DPA), which governs the customer feedback CLARA processes as a **processor** on behalf of its business customers.*

> **DRAFT — have a German Fachanwalt (IT-Recht/Datenschutz) review before use.** This template is a starting point only. Statute references, article numbers and enforcement thresholds were current as of the drafting date below but must be re-verified against the operative legal text at the moment of publication. Populate every `{{PLACEHOLDER}}`, delete inapplicable sections, and confirm the actual data flows against your live tech stack before going live.

> **A German-language version of this Datenschutzerklärung is legally required** whenever the website is directed at German visitors. German is the authoritative, legally binding version for German data subjects and supervisory authorities; this English version is a convenience translation for CLARA's cross-border EU audience. In case of conflict, `{{state which version prevails — typically the German version for DE data subjects}}`.

---

## 0. Document control

| Field | Value |
|---|---|
| Document | Website Privacy Policy (Datenschutzerklärung) |
| Scope | CLARA public website, marketing, lead capture, billing (controller role) |
| Version | `{{VERSION}}` |
| Effective date | `{{EFFECTIVE_DATE}}` |
| Last updated | `{{LAST_UPDATED_DATE}}` |
| Drafting reference date | 2026-07-01 |
| Owner | `{{FOUNDER_NAME}}` |
| Review status | **DRAFT — pending Fachanwalt review** |

---

## 1. Controller and contact (Verantwortlicher)

This policy is issued in accordance with Art. 13 and Art. 14 of the General Data Protection Regulation (Regulation (EU) 2016/679, "GDPR" / "DSGVO"). The controller (Verantwortlicher) responsible for the processing of personal data on this website is:

> `{{FOUNDER_LEGAL_NAME}}` (trading as "CLARA")
> `{{STREET_ADDRESS}}`
> `{{POSTCODE}} {{CITY}}` (Berlin, Germany)
> Email: `{{PRIVACY_CONTACT_EMAIL}}`
> Phone: `{{PHONE_OPTIONAL}}`
> USt-IdNr.: `{{VAT_ID}}`

> **Review note:** Keep the controller identity here consistent with the Impressum (provider identification under **§ 5 Digitale-Dienste-Gesetz (DDG)** — the DDG replaced the Telemediengesetz (TMG), which was repealed on 14 May 2024). The founder currently operates as Freiberufler with a USt-IdNr.; if the productised SaaS is reclassified as a Gewerbe, update the legal form, address and any registration details here and in the Impressum accordingly.

---

## 2. Data Protection Officer (Datenschutzbeauftragter)

`{{CHOOSE ONE — delete the other:}}`

**Option A — no DPO appointed (default for a solo founder):**
CLARA has **not** appointed a Data Protection Officer. Under **§ 38(1) Bundesdatenschutzgesetz (BDSG)**, a non-public body in Germany must appoint a DPO only where it, as a rule, permanently employs **at least 20 persons** engaged in the automated processing of personal data, or where a data protection impact assessment (Art. 35 GDPR) is mandatory, or where personal data is processed commercially for transfer, anonymised transfer or for market/opinion research. As a solo operation, CLARA is below this threshold and is therefore not required to appoint a DPO. You may still direct all data protection enquiries to the controller contact in Section 1.

> **Review note:** The 20-person threshold in § 38(1) BDSG was current as of the drafting date. A raise of the threshold (to 50) and/or a repeal of § 38(1) BDSG were announced by the German federal government (Modernisierungsagenda, 4 Dec 2025) but had **not** entered into force as of drafting — re-verify before publication. Note that even below the § 38 BDSG threshold, a DPO can still be mandatory under **Art. 37(1) GDPR** if CLARA's core activities consist of large-scale regular and systematic monitoring, or large-scale processing of special-category data — assess this for CLARA's actual website (not feedback) processing before relying on Option A.

**Option B — DPO appointed:**
CLARA has appointed the following Data Protection Officer:
> `{{DPO_NAME}}`, `{{DPO_COMPANY_IF_EXTERNAL}}`
> `{{DPO_ADDRESS}}` — Email: `{{DPO_EMAIL}}`

---

## 3. General principles, hosting location and data transfers

CLARA processes personal data only where a legal basis under Art. 6 GDPR applies, in accordance with the principles of Art. 5 GDPR (lawfulness, purpose limitation, data minimisation, accuracy, storage limitation, integrity/confidentiality).

**Hosting / server location.** This website and its supporting infrastructure are hosted `{{DESCRIBE — e.g., "in the European Union with {{HOSTING_PROVIDER}}, data centres in {{REGION/COUNTRY}}"}}`. `{{If any processor or sub-processor stores or accesses data outside the EU/EEA, state this here.}}`

**Third-country transfers.** `{{CHOOSE:}}`
- CLARA does **not** transfer website personal data to countries outside the EU/EEA; **or**
- Where personal data is transferred to a third country (e.g., via `{{PROVIDER}}`), the transfer is safeguarded by `{{one of: an EU adequacy decision under Art. 45 GDPR; EU Standard Contractual Clauses under Art. 46(2)(c) GDPR plus supplementary measures; other}}`. A copy of the relevant safeguards can be requested via the contact in Section 1.

> **Review note:** List every website-side processor (hosting, CDN, email, analytics, error monitoring, payment) and its location; verify each has an Art. 28 GDPR data processing agreement in place and, where applicable, a valid Art. 46 transfer mechanism. This section concerns the **controller-side website only** — the ingested customer feedback is governed separately by the customer AVV/DPA.

---

## 4. Purposes of processing and legal bases (Art. 6 GDPR)

The table below summarises the categories of processing on this website. Detailed descriptions follow.

| # | Processing activity | Data categories | Purpose | Legal basis (Art. 6(1) GDPR) |
|---|---|---|---|---|
| 4.1 | Provision of the website & server logs | IP address, request metadata (see 4.1) | Deliver and secure the site | (f) legitimate interests |
| 4.2 | Cookies / consent | Device/consent data | Consent record & requested features | (a) consent / (f) for strictly necessary |
| 4.3 | Contact form & email | Name, email, message content | Respond to enquiries | (b) pre-contract / (f) or (a) |
| 4.4 | Newsletter *(if used)* | Email, consent metadata | Send marketing updates | (a) consent |
| 4.5 | Web analytics *(if used)* | Usage/device data | Measure & improve the site | (a) consent |
| 4.6 | Account signup & billing | Name, business, email, payment | Contract performance, invoicing | (b) contract / (c) legal obligation |
| 4.7 | Product demo / sales CRM *(if used)* | Contact & interaction data | Sales follow-up | (b) pre-contract / (f) |

---

### 4.1 Provision of the website and server log files

When you visit this website, `{{HOSTING_PROVIDER}}`, acting as processor on CLARA's behalf, automatically collects and stores information that your browser transmits ("server log files"), including:

- anonymised or truncated `{{state which}}` IP address,
- date and time of the request,
- the specific page/resource requested and HTTP status/response size,
- referrer URL (the previously visited page),
- browser type/version, operating system and user-agent string.

**Purpose:** to deliver the website reliably, ensure system security and stability, prevent and detect abuse/attacks, and enable technical troubleshooting.
**Legal basis:** Art. 6(1)(f) GDPR (legitimate interest in a secure, functional website). Where log data is stored on your terminal equipment or read from it, the strictly-necessary exemption in **§ 25(2) TDDDG** applies.
**Retention:** log files are retained for `{{RETENTION_PERIOD — e.g., 7 / 14 / 30 days}}`, after which they are deleted or anonymised, unless a specific incident requires longer retention for evidentiary/security purposes.

---

### 4.2 Cookies and consent (§ 25 TDDDG)

This website uses cookies and comparable technologies (e.g., local storage, pixels). The storing of information in, and access to information already stored in, your terminal equipment is governed by **§ 25 Telekommunikation-Digitale-Dienste-Datenschutz-Gesetz (TDDDG)** — the successor to the TTDSG, which was renamed with effect from 14 May 2024.

- **Strictly necessary cookies** (required for the website to function, e.g., load balancing, security, storing your consent choice) are set on the basis of **§ 25(2) TDDDG** and do **not** require consent. Any related processing of personal data relies on Art. 6(1)(f) GDPR.
- **All non-essential cookies/technologies** (e.g., analytics, marketing) are set **only after you give prior, informed, specific and unambiguous consent** via our consent banner, on the basis of **§ 25(1) TDDDG** in conjunction with **Art. 6(1)(a) GDPR**.

You can **withdraw or change your consent at any time** with effect for the future via `{{link/mechanism — e.g., "the 'Cookie settings' link in the website footer"}}`. Withdrawal does not affect the lawfulness of processing carried out before withdrawal.

**Overview of cookies used** `{{populate or link to a live cookie table generated by your CMP}}`:

| Cookie / technology | Provider | Purpose | Type | Storage duration |
|---|---|---|---|---|
| `{{name}}` | `{{provider}}` | `{{purpose}}` | Strictly necessary / Analytics / Marketing | `{{duration}}` |

> **Review note:** If you use a Consent Management Platform (CMP), confirm whether it must be a recognised service under the German **Consent Management Ordinance (Einwilligungsverwaltungsverordnung)**, which took effect **1 April 2025** — participation is voluntary but the ordinance shapes acceptable banner/consent-signal design. Ensure "reject all" is as prominent as "accept all," that no non-essential cookies fire before consent, and keep an auditable consent log. Maximum fine for § 25 TDDDG violations is up to EUR 300,000.

---

### 4.3 Contact form and email contact

If you contact CLARA via the contact form, by email (`{{CONTACT_EMAIL}}`), or via `{{other channel}}`, we process the data you provide — typically your `{{name, email address, company, and the content of your message}}` — together with associated metadata.

**Purpose:** to receive, process and respond to your enquiry, and to handle any follow-up.
**Legal basis:**
- Art. 6(1)(b) GDPR where your enquiry relates to entering into or performing a contract (e.g., a sales/demo request);
- Art. 6(1)(f) GDPR (legitimate interest in responding to communications) for general enquiries; and/or
- Art. 6(1)(a) GDPR where you have given consent.

**Retention:** enquiry data is retained for as long as necessary to handle your request and any follow-up, and thereafter deleted, unless statutory retention obligations (see Section 7) apply or the data is needed to establish, exercise or defend legal claims.

> **Review note:** If contact emails are handled through an external mailbox/helpdesk (`{{provider}}`), ensure an Art. 28 DPA is in place and reflected in Section 3.

---

### 4.4 Newsletter and marketing emails *(include only if operated)*

`{{DELETE THIS SECTION IF NO NEWSLETTER.}}`

If you subscribe to CLARA's newsletter or product updates, we process your **email address** and `{{optional: name, company}}`, plus consent metadata (opt-in timestamp, IP address, and the confirmation event).

**Consent & double opt-in:** subscription uses a **double opt-in** procedure — after signup we send a confirmation email; your address is added to the list only once you confirm. This documents that you are the account holder and consented.
**Legal basis:** Art. 6(1)(a) GDPR (consent); for the logging of the opt-in, Art. 6(1)(f) GDPR (legitimate interest in demonstrating consent).
**Withdrawal:** you can unsubscribe at any time via the link in every newsletter or by contacting us; withdrawal takes effect for the future.
**Processor:** newsletters are sent via `{{ESP_PROVIDER}}` under an Art. 28 GDPR DPA. `{{State transfer safeguards if the ESP is outside the EU/EEA.}}`
**Retention:** we retain your data until you unsubscribe, after which the email is removed from the active list; consent/withdrawal records are kept as needed to evidence compliance.

> **Review note:** Confirm whether tracking of opens/clicks is used — if so, that tracking is a non-essential technology requiring separate consent (§ 25(1) TDDDG) and must be disclosed here. Consider UWG requirements for commercial email (§ 7 UWG).

---

### 4.5 Web analytics *(include only if operated)*

`{{DELETE THIS SECTION IF NO ANALYTICS, OR ADAPT TO YOUR TOOL.}}`

This website uses `{{ANALYTICS_TOOL — e.g., Matomo (self-hosted, EU), Plausible, Google Analytics 4}}` to understand how visitors use the site and to improve it.

- Data processed: `{{e.g., pages viewed, referrer, truncated IP, device/browser, interaction events}}`.
- IP handling: `{{e.g., "IP addresses are truncated/anonymised before storage"}}`.
- **Legal basis:** Art. 6(1)(a) GDPR **and** § 25(1) TDDDG — analytics runs **only after consent** via the cookie banner. `{{If a genuinely cookieless, consent-free configuration is used, state the assessment and basis (Art. 6(1)(f)) here instead — verify with counsel.}}`
- Processor / transfers: `{{provider, hosting location, Art. 28 DPA, Art. 46 safeguards if applicable}}`.
- Retention: analytics data is retained for `{{RETENTION_PERIOD}}`.

> **Review note:** For any US-based analytics (e.g., GA4), confirm the transfer mechanism (adequacy decision / SCCs + supplementary measures) and that consent is obtained before any script loads. Prefer an EU-hosted, privacy-friendly analytics tool to reduce transfer exposure.

---

### 4.6 Account registration, customer relationship and billing

When you sign up for a CLARA account, request a trial, or purchase a subscription, CLARA processes the data needed to establish and administer the customer relationship: `{{name, business email, company name, billing address, VAT ID, and payment data}}`.

**Purpose:** account creation and authentication, provision of the contracted service, invoicing, payment processing, accounting and tax compliance.
**Legal basis:**
- Art. 6(1)(b) GDPR (performance of a contract / pre-contractual steps) for account and service administration;
- Art. 6(1)(c) GDPR (legal obligation) for invoicing, bookkeeping and tax-retention duties.

**Payment processing:** payments are handled by `{{PAYMENT_PROVIDER — e.g., Stripe}}`, which processes your payment data as `{{controller / processor — verify the provider's role}}`. See that provider's own privacy information at `{{link}}`. CLARA `{{does / does not}}` store full card data.
**Retention:** see Section 7 (statutory retention for invoices/accounting records).

> **Review note:** This section concerns the personal data of CLARA's **business customers and their signatories** (controller role). The customer feedback those customers ingest is processed by CLARA as a **processor** and is governed by the AVV/DPA, not this policy. Confirm the payment provider's controller/processor classification.

---

### 4.7 AI-assisted features on the website *(include only if applicable)*

`{{DELETE IF THE PUBLIC WEBSITE HAS NO AI FEATURES.}}`

`{{If the website offers an AI chatbot, demo, or similar that processes visitor input:}}` CLARA uses a third-party frontier LLM API (`{{PROVIDER}}`) to power `{{feature}}`. CLARA does not fine-tune the model and acts as a downstream AI-system deployer, not a general-purpose AI model provider.
**Legal basis:** `{{Art. 6(1)(a) consent and/or Art. 6(1)(b)/(f)}}`. Do not enter personal or confidential data into `{{feature}}` unless necessary.

> **Review note:** From **2 August 2026**, EU AI Act **Art. 50** transparency obligations apply — where users interact with an AI system (e.g., a chatbot), they must be clearly informed that they are interacting with AI unless obvious from context. Ensure a clear AI-interaction notice is present at the point of use. CLARA's overall EU AI Act classification is limited/minimal risk; re-confirm before relying on this.

---

## 5. Recipients and processors (Auftragsverarbeiter)

CLARA discloses personal data only to recipients who need it to fulfil the purposes above. Processors act only on CLARA's documented instructions under an Art. 28 GDPR data processing agreement. Typical categories of recipients:

- **Hosting / infrastructure:** `{{provider(s)}}`
- **Email / helpdesk:** `{{provider}}`
- **Newsletter / ESP:** `{{provider}}`
- **Analytics / monitoring:** `{{provider}}`
- **Payment / billing:** `{{provider}}`
- **CRM / sales tooling:** `{{provider}}`
- **Public authorities / courts:** where required by law.

`{{Optionally provide a full current sub-processor list or a link to one.}}`

---

## 6. Data subject rights (Art. 15–21 GDPR) and right to complain

As a data subject you have the following rights regarding your personal data, exercisable free of charge in most cases:

- **Right of access** (Art. 15 GDPR) — confirmation of whether we process your data and a copy of it.
- **Right to rectification** (Art. 16 GDPR) — correction of inaccurate or incomplete data.
- **Right to erasure / "right to be forgotten"** (Art. 17 GDPR) — deletion where the legal conditions are met.
- **Right to restriction of processing** (Art. 18 GDPR).
- **Right to data portability** (Art. 20 GDPR) — receipt of data you provided in a structured, commonly used, machine-readable format.
- **Right to object** (Art. 21 GDPR) — you may **object at any time, on grounds relating to your particular situation, to processing based on Art. 6(1)(f)**. Where data is processed for **direct marketing**, you may object at any time with no need to give reasons, after which we will stop such processing.
- **Right to withdraw consent** (Art. 7(3) GDPR) — where processing is based on consent, you may withdraw it at any time with effect for the future, without affecting prior lawful processing.

To exercise any of these rights, contact CLARA using the details in **Section 1**. We may need to verify your identity before responding and will reply within the statutory time limits (as a rule, one month per Art. 12(3) GDPR).

**Right to lodge a complaint (Art. 77 GDPR).** Without prejudice to any other remedy, you have the right to lodge a complaint with a data protection supervisory authority, in particular in the Member State of your habitual residence, place of work, or the place of the alleged infringement. The authority competent for CLARA is:

> **Berliner Beauftragte für Datenschutz und Informationsfreiheit (BlnBDI)**
> Alt-Moabit 59–61, 10555 Berlin, Germany
> Website: https://www.datenschutz-berlin.de/

> **Review note:** Verify the BlnBDI's current postal address and complaint channel at publication; the authority is CLARA's lead/competent supervisory authority as a Berlin-based establishment. Data subjects may alternatively complain to their own local authority.

---

## 7. Storage duration and erasure (Art. 5(1)(e) GDPR)

CLARA stores personal data only as long as necessary for the purposes for which it was collected, or as required by statutory retention obligations. Once the purpose ceases and no retention obligation applies, the data is deleted or anonymised. Key periods:

- **Server logs:** `{{e.g., 7–30 days}}` (Section 4.1).
- **Contact/enquiry data:** duration of handling plus any limitation period for legal claims (Section 4.3).
- **Newsletter data:** until unsubscription (Section 4.4).
- **Analytics data:** `{{period}}` (Section 4.5).
- **Invoicing / accounting records:** retained to comply with German statutory retention duties — as a rule **`{{8 years for accounting records / invoices per § 147 AO and § 257 HGB — verify current period}}`**, and **`{{6 years for commercial and business letters}}`** — calculated from the end of the relevant calendar year.

> **Review note:** Confirm the current retention periods under **§ 147 Abgabenordnung (AO)** and **§ 257 Handelsgesetzbuch (HGB)**. The invoice/accounting retention period was reduced from 10 to 8 years by recent legislation — verify the operative period and transitional rules for CLARA's records at publication.

---

## 8. Obligation to provide data; automated decision-making

- **Provision of data:** you are under no statutory or contractual obligation to provide personal data to browse the public website. However, certain data is required to use specific functions (e.g., an email address is necessary to receive a reply, create an account, or receive the newsletter); without it, that function cannot be provided.
- **Automated decision-making / profiling (Art. 22 GDPR):** CLARA `{{does not carry out automated decision-making, including profiling, that produces legal or similarly significant effects on website visitors / OR: describe and give the legal basis and safeguards}}`.

---

## 9. Data security (Art. 32 GDPR)

CLARA implements appropriate technical and organisational measures to protect personal data against unauthorised access, loss, alteration and disclosure, taking into account the state of the art, implementation cost, and the nature, scope, context and purposes of processing, as well as the risks to data subjects. Measures include `{{TLS/HTTPS encryption in transit, access controls, least-privilege, encryption at rest where appropriate, logging, backups}}`. Full technical and organisational measures (TOMs) under Art. 32 GDPR are documented separately.

---

## 10. Changes to this privacy policy

CLARA may update this policy to reflect changes in its services or the legal framework. The current version is always available on this website. Material changes will be communicated `{{how — e.g., via a notice on the site or by email to registered users}}`. Version and effective date are shown in Section 0.

---

## 11. Sources and legal references *(internal note — remove before publishing)*

Key statutory references used in this draft (re-verify at publication):

- **§ 5 DDG** (Digitale-Dienste-Gesetz) — provider identification / Impressum; DDG replaced the TMG, repealed 14 May 2024. See [gesetz-digitale-dienste.de](https://gesetz-digitale-dienste.de/) and [IT-Recht Kanzlei](https://www.it-recht-kanzlei.de/tmg-ttdsg-ausser-kraft-impressum-datenschutz.html).
- **§ 25 TDDDG** (formerly TTDSG, renamed 14 May 2024) — consent for storing/accessing information on terminal equipment. See [Securiti TDDDG guide](https://securiti.ai/blog/german-ttdsg-guide/) and [Usercentrics on the Consent Management Ordinance](https://usercentrics.com/knowledge-hub/cookie-flood-control-consent-management-ordinance-tdddg/).
- **Consent Management Ordinance (Einwilligungsverwaltungsverordnung)** — effective 1 April 2025. See [Didomi](https://www.didomi.io/blog/german-consent-management-ordinance).
- **§ 38 BDSG** — DPO appointment threshold (20 persons), current at drafting; announced repeal (Modernisierungsagenda, 4 Dec 2025) not yet in force. See [dsgvo-gesetz.de/bdsg/38-bdsg](https://dsgvo-gesetz.de/bdsg/38-bdsg/) and [dr-datenschutz.de](https://www.dr-datenschutz.de/faellt-die-pflicht-zum-datenschutzbeauftragten-bis-ende-2026/).
- **Arts. 5, 6, 13, 15–22, 32, 77 GDPR** (Regulation (EU) 2016/679).
- **EU AI Act (Regulation (EU) 2024/1689) Art. 50** — AI transparency, applicable 2 August 2026.
- **BlnBDI** — competent supervisory authority, Alt-Moabit 59–61, 10555 Berlin. See [datenschutz-berlin.de](https://www.datenschutz-berlin.de/).
- **§ 147 AO / § 257 HGB** — accounting/invoice retention (verify current 8-year period).

---

*End of draft template. Populate all placeholders, remove Section 11 before publishing, prepare the binding German-language version, and obtain sign-off from a German Fachanwalt für IT-Recht / Datenschutzrecht before making this policy live.*
