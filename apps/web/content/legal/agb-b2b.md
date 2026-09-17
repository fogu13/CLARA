# CLARA — B2B SaaS Terms and Conditions (Allgemeine Geschäftsbedingungen / AGB)

_Purpose: General Terms and Conditions governing CLARA's B2B SaaS subscription (AI customer-feedback triage), sold to business customers in the DACH region and the wider EU._

> **DRAFT — have a German Fachanwalt (IT-Recht/Datenschutz) review before use.**
>
> This is a founder-prepared skeleton to hand to a lawyer. It is **not** legal advice and is **not** ready to publish. German AGB law imposes a **statutory content review (Inhaltskontrolle)** on standard terms even in B2B contracts — via § 307 BGB — and the liability clauses below are the single highest-risk part of the document. **Do not deploy without qualified review.** See the liability note in Section 10.

---

## How to use this template

- Replace every `{{PLACEHOLDER}}` with founder- or customer-specific values.
- Language: this English version is the working draft for cross-border EU sales. **A German-language version is strongly recommended (and, for the incorporation/`Einbeziehung` mechanics and enforceability against German customers, effectively expected).** If a German and an English version both exist, the lawyer should specify which prevails — for German-law-governed contracts with German customers, the German version typically prevails.
- This template assumes **B2B only** (customers are `Unternehmer` within the meaning of § 14 BGB). It is **not** drafted for consumers (`Verbraucher`); consumer sales trigger a large additional body of mandatory law (withdrawal rights, § 309 BGB clause bans applying in full, Button-Lösung under § 312j BGB, etc.) and are out of scope here.
- Cross-reference the separate documents in this pack: **Impressum** (§ 5 DDG), **Datenschutzerklärung**, **AVV/DPA** (Art. 28 GDPR), and **TOMs** (Art. 32 GDPR).

---

## 0. Parties and provider identification

**Provider ("CLARA", "we", "us"):**
- {{LEGAL_NAME}} (e.g. {{FOUNDER_NAME}}, sole proprietor / or {{GMBH_UG_NAME}})
- {{ADDRESS_STREET, POSTCODE, BERLIN}}
- Represented by: {{FOUNDER_NAME}}
- Email: {{CONTACT_EMAIL}} · Phone: {{PHONE}}
- USt-IdNr: {{VAT_ID}}
- Register / Handelsregister: {{HRB_NUMBER_IF_ANY}} (if incorporated)

> Provider identification duties sit in the separate **Impressum** under **§ 5 DDG** (the Digitale-Dienste-Gesetz, which replaced the TMG on **14 May 2024**). Keep the Impressum, not these AGB, as the canonical `Anbieterkennzeichnung`.
>
> **Legal-form flag:** the founder is currently `Freiberufler` with a USt-IdNr. A productised SaaS is very likely a `Gewerbe` (trade), not a freelance activity — this affects Gewerbeanmeldung, trade tax (`Gewerbesteuer`), and possibly the legal name/register entry used above. Resolve this with the tax/legal advisor before these AGB go live (flagged in the business-setup document).

**Customer ("Customer", "you"):** the business entity identified in the Order (Section 4) that subscribes to the Services. These AGB apply only to customers acting as `Unternehmer` (§ 14 BGB), legal persons under public law, or public-law special funds.

---

## 1. Scope of application and definitions

### 1.1 Scope (`Anwendungsbereich`)
1. These AGB govern the contract between CLARA and the Customer for the provision of the CLARA software-as-a-service offering and related services (together, the **"Services"**).
2. These AGB apply exclusively. **Conflicting, deviating, or supplementary terms of the Customer** (e.g. the Customer's own purchasing conditions) do **not** become part of the contract unless CLARA has expressly agreed to them in text form. This applies even where CLARA renders performance without reservation while aware of such customer terms. _(Standard B2B defensive-clause / `Abwehrklausel` — lawyer to confirm wording under § 305 / § 307 BGB.)_
3. These AGB also apply to all future contracts with the Customer within an ongoing business relationship, in the version in force at the time.

### 1.2 Definitions
- **"Services"** — the CLARA hosted application that ingests customer-feedback text (e.g. app-store reviews, review-site content, support messages) and performs automated triage, categorisation, and analysis, together with the web interface, APIs, and documentation.
- **"Customer Data"** — all data the Customer or its end users upload to, or generate within, the Services, including ingested customer-feedback text (which may contain personal data).
- **"Feedback Data"** — the subset of Customer Data consisting of end-customer feedback text submitted for triage.
- **"DPA" / "AVV"** — the Data Processing Agreement / Auftragsverarbeitungsvertrag under **Art. 28 GDPR** referenced in Section 6.
- **"Order"** — the order form, online sign-up, or written offer accepted under Section 4 that specifies the plan, scope, term, and fees.
- **"Subscription Term"** — the term stated in the Order (see Section 11).
- **"SLA"** — the service-level commitments in Section 2 / Annex A, if agreed.
- **"AI Provider"** — the third-party frontier LLM API CLARA uses to perform triage (used **without fine-tuning** by CLARA).
- **"Text form"** (`Textform`, § 126b BGB) — a readable declaration on a durable medium naming the declaring person; includes email. Where these AGB require text form, email suffices unless stated otherwise.

---

## 2. Service description, availability and SLA

### 2.1 Service description
1. CLARA provides the Services as a multi-tenant SaaS, accessible over the internet. CLARA hosts the Services in the **EU/EEA** ({{HOSTING_REGION_AND_PROVIDER}}). _(Confirm current hosting region; the compliance document notes an EU-hosting posture / migration.)_
2. The functional scope is defined by the then-current product documentation and the plan selected in the Order. CLARA may enhance, and will maintain, the Services; see Section 12 on changes.
3. **AI-assisted processing / transparency.** Triage and categorisation are performed with the assistance of an AI system that calls a third-party LLM API. Outputs are **probabilistic** and may contain errors, mis-categorisations, or omissions; they are **decision support, not a substitute for human judgement.** The Customer remains responsible for decisions it takes on the basis of CLARA's output.
   > **EU AI Act flag:** CLARA is a **downstream deployer/provider of an AI system** using a third-party model without fine-tuning (not a provider of a general-purpose AI model). CLARA assesses the offering as **limited/minimal risk**. The **Article 50 transparency obligations** for certain AI systems apply from **2 August 2026** (with a marking grace period to 2 December 2026 for pre-existing generative systems under the AI Omnibus provisional agreement of May 2026). Lawyer to confirm which, if any, Art. 50 duties apply to CLARA's use case and reflect them here and in the product UI.

### 2.2 Availability
1. CLARA targets an availability of **{{TARGET_UPTIME e.g. 99.5%}}** per calendar month for the production Services, measured as set out in Annex A, **excluding**:
   - scheduled maintenance announced at least {{NOTICE_HOURS e.g. 48}} hours in advance (CLARA will endeavour to schedule outside {{BUSINESS_HOURS_TZ}});
   - emergency maintenance required to preserve security or integrity;
   - downtime caused by force majeure (Section 10.6), the Customer, the Customer's infrastructure, or third-party services outside CLARA's control (including the AI Provider and upstream connectivity).
2. **Support:** {{SUPPORT_CHANNEL e.g. email}}, response targets per plan/Annex A, during {{SUPPORT_HOURS}}.

### 2.3 Service levels (optional)
- If an SLA with credits is agreed, the sole and exclusive remedy for missing a committed service level is the **service credit** defined in Annex A; service credits do not constitute an acknowledgement of liability and are capped at {{CREDIT_CAP e.g. one month's fee}}.
  > Lawyer to confirm that an exclusive-remedy service-credit regime survives § 307 BGB `Inhaltskontrolle` and does not improperly exclude claims that cannot be excluded (see Section 10). If no SLA is offered, delete 2.3 and soften 2.2 to a non-binding availability target.

---

## 3. Subscription, pricing and payment

1. **Fees.** Fees are set out in the Order or the then-current price list for the selected plan (e.g. per seat, per volume of feedback items, or flat per plan). All prices are **net**, i.e. **exclusive of value added tax (VAT/USt)** and any other applicable taxes or levies, which are added at the statutory rate where due.
2. **VAT / reverse charge.**
   - For business customers in Germany: German VAT at the applicable rate is added.
   - For business customers in other **EU** member states who provide a valid VAT identification number, the **reverse-charge mechanism** applies (Art. 196 VAT Directive 2006/112/EC; § 13b UStG context); invoices are issued net with a reverse-charge note and the Customer accounts for VAT in its member state.
   - The Customer is responsible for providing a valid VAT ID and for the correctness of its tax status; if the VAT ID is invalid, CLARA may charge applicable VAT.
   > Tax treatment (place of supply for B2B electronic services, reverse-charge notes, invoice content under § 14/§ 14a UStG) to be confirmed with the tax advisor.
3. **Billing cycle and payment terms.** Fees are billed **{{monthly/annually}} in advance**. Invoices are due within **{{PAYMENT_DAYS e.g. 14}}** days of the invoice date, net, without deduction, to the account stated on the invoice. Payment method: {{PAYMENT_METHOD e.g. SEPA direct debit / card / bank transfer}}.
4. **Late payment.** On default, CLARA is entitled to statutory default interest (for B2B, **9 percentage points above the base rate**, § 288(2) BGB) and to the **€40 lump sum** under § 288(5) BGB, without prejudice to further damage. CLARA may, after a reasonable warning, **suspend** the Services while the Customer is in material payment default. _(Suspension right — lawyer to confirm proportionality and notice under § 307 BGB.)_
5. **Price changes.** CLARA may adjust fees for renewal terms; see Section 12. Fee changes do not affect a running prepaid Subscription Term.
6. **No set-off / retention.** The Customer may set off only claims that are undisputed or finally adjudicated, and may assert a right of retention only based on claims from the same contractual relationship. _(Standard B2B clause; permissible in B2B but still subject to § 307 — lawyer to verify.)_
7. **Free trials / betas**, if offered, are provided "as is", may be modified or withdrawn, and carry no availability or warranty commitments (see Section 9).

---

## 4. Order and formation of contract

1. The presentation of the Services (website, price list) is an invitation to treat, not a binding offer.
2. The contract is formed when the Customer submits an Order (via online sign-up, signed order form, or written acceptance of a CLARA offer) **and** CLARA confirms it in text form or begins providing the Services, whichever is earlier.
3. By placing an Order, the Customer confirms it acts as an `Unternehmer` (§ 14 BGB) and not as a consumer.
4. The person placing the Order warrants they are authorised to bind the Customer.
5. These AGB, the Order, the DPA (Section 6), and any Annexes together form the contract. In case of conflict, the order of precedence is: **(1)** individually negotiated terms in the Order, **(2)** the DPA for data-protection matters, **(3)** these AGB, **(4)** the documentation. _(Individually negotiated terms prevail over AGB by operation of § 305b BGB in any event.)_

---

## 5. Intellectual property and licence grant

1. **CLARA IP.** CLARA and its licensors retain all rights, title, and interest in and to the Services, the underlying software, models integrations, documentation, and all improvements. No rights are granted except as expressly set out here.
2. **Licence to the Customer.** Subject to payment and these AGB, CLARA grants the Customer a **non-exclusive, non-transferable, non-sublicensable, time-limited** right to use the Services for its own internal business purposes during the Subscription Term.
3. **Customer Data.** The Customer retains all rights in Customer Data. The Customer grants CLARA a non-exclusive, worldwide, royalty-free licence to host, process, transmit, display, and otherwise use Customer Data **solely** to provide, secure, and maintain the Services and as instructed under the DPA. **CLARA does not use Customer Data or Feedback Data to train, fine-tune, or improve any AI model**, and passes Feedback Data to the AI Provider only for the immediate triage request. _(Confirm this matches the actual AI Provider's data-use terms and the DPA; this is a load-bearing representation for DACH/EU buyers.)_
4. **Aggregated/anonymised data.** CLARA may generate and use **aggregated and fully anonymised** statistics (that do not identify the Customer, any individual, or any end customer) to operate and improve the Services. _(Anonymisation must be genuine per GDPR Recital 26 — lawyer/DPO to confirm; if in doubt, delete.)_
5. **Feedback about the product.** If the Customer voluntarily provides suggestions about the Services, CLARA may use them without restriction or obligation. (This concerns product feedback, **not** Feedback Data.)
6. **Third-party components / open source** are used under their respective licences; a list is available on request.

---

## 6. Customer data and data protection (DPA reference)

1. In providing the Services, CLARA processes personal data contained in Feedback Data **on behalf of the Customer**. With respect to that processing, the **Customer is the controller** and **CLARA is the processor** within the meaning of **Art. 4(7) and 4(8) GDPR**.
2. The parties conclude a separate **Data Processing Agreement (DPA / Auftragsverarbeitungsvertrag)** under **Art. 28 GDPR**, which forms part of the contract and prevails over these AGB on data-protection matters. The DPA sets out subject-matter, duration, nature and purpose of processing, categories of data subjects and personal data, sub-processors (including the EU hosting provider and the AI Provider), international-transfer safeguards, and the **technical and organisational measures (TOMs) under Art. 32 GDPR**.
3. The **Customer warrants** that it has a valid legal basis to submit Feedback Data for processing, that it has provided all required notices to and (where applicable) obtained consents from data subjects, and that its instructions comply with data-protection law. The Customer must not submit special-category data (Art. 9 GDPR) unless expressly agreed in the DPA.
4. For CLARA's **own** processing (website, marketing, billing, account administration), CLARA acts as **controller**; that processing is described in CLARA's **Datenschutzerklärung**. Cookie/tracking consent on CLARA's website is handled under **§ 25 TDDDG** (Telekommunikation-Digitale-Dienste-Datenschutz-Gesetz).
5. CLARA supports the Customer's obligations (data-subject requests, breach notification, DPIAs) as detailed in the DPA.
   > The DPA, Datenschutzerklärung, and TOMs are separate documents in this pack. Ensure the sub-processor list there names the actual hosting provider and AI Provider, and that transfer mechanisms are in place if any processing leaves the EEA.

---

## 7. Acceptable use

1. The Customer must use the Services only lawfully and in accordance with the contract and documentation. The Customer must not, and must not permit any user to:
   - upload content it is not lawfully entitled to submit, or that infringes third-party rights;
   - upload malware, or attempt to gain unauthorised access to, disrupt, overload, or reverse-engineer the Services (except to the extent § 69e UrhG / mandatory law permits);
   - use the Services to build a competing product, or to benchmark for a competitor;
   - submit special-category (Art. 9 GDPR) or unlawful content outside the agreed scope;
   - exceed the usage limits of the selected plan or resell/provide the Services to third parties without authorisation.
2. **Responsibility for users.** The Customer is responsible for its authorised users' use, for keeping credentials confidential, and for all activity under its account.
3. **Enforcement.** On a material or legally material breach of this Section, CLARA may suspend the affected access or content after reasonable notice (immediately where required to prevent imminent harm, protect the Services, or comply with law), without prejudice to termination rights in Section 11.
4. The Customer indemnifies CLARA against third-party claims arising from Customer Data or the Customer's breach of this Section, save where CLARA is responsible. _(Indemnity scope/cap — lawyer to align with Section 10 and § 307 BGB.)_

---

## 8. Warranties and cooperation

1. **Nature of the obligation.** The provision of SaaS access is generally treated under German law as a **contract for lease/rental of services (`Mietvertrag`, §§ 535 ff. BGB)** for the software access element, potentially with service-contract (`Dienstvertrag`) elements for support. The exact classification affects the applicable warranty regime and must be confirmed by the lawyer, as it drives which mandatory rules (e.g. rent-reduction rights, § 536 BGB) apply and cannot be excluded.
2. CLARA will provide the Services with due professional care and substantially in accordance with the documentation during the Subscription Term.
3. **No guarantee of specific results.** Because triage output is AI-generated and probabilistic (Section 2.1(3)), CLARA does **not** warrant that output will be complete, accurate, or fit for any particular decision, nor that the Services will be uninterrupted or error-free.
4. **Customer cooperation.** The Customer will provide accurate configuration, maintain compatible systems and connectivity, and cooperate reasonably (including timely bug reports). Delays caused by missing cooperation extend CLARA's performance times accordingly.
5. **Defect notification.** The Customer will report defects without undue delay in text form with enough detail to reproduce them.

---

## 9. Disclaimers

1. Except as expressly stated in Section 8, and to the extent permitted by mandatory law, CLARA disclaims all other warranties, whether express, implied, or statutory, including any implied warranties of merchantability, fitness for a particular purpose, and non-infringement.
2. The Services are **not** designed for use in high-risk or safety-critical contexts, nor as the **sole** basis for decisions producing legal or similarly significant effects on individuals. The Customer is responsible for maintaining appropriate human oversight of AI-assisted output.
3. Free trials, beta features, and pre-release functionality are provided **"as is"** without any warranty or availability commitment.
   > Blanket "as is" / warranty-disclaimer language is **strongly limited** under German AGB law and can be void under § 307 BGB, especially given the likely `Mietvertrag` classification (§ 536 BGB warranty is hard to exclude). These disclaimers must be reworked by the lawyer to what German law actually allows — do not rely on this Anglo-American-style wording.

---

## 10. Limitation of liability

> **HIGHEST-RISK SECTION — MANDATORY LAWYER REVIEW.** German law tightly constrains liability caps and exclusions in standard terms. Although **§ 309 BGB** (clause bans without valuation possibility) does **not directly** apply between businesses (**§ 310(1) BGB**), the courts apply its value judgements **indirectly through the general content review of § 307 BGB**, so many § 309-type clauses are **also void in B2B**. In particular: liability for **intent and gross negligence**, for **injury to life, body, or health**, for claims under the **Produkthaftungsgesetz**, and for breach of **essential/cardinal contractual obligations (`Kardinalpflichten`)** — even by **slight negligence** — **cannot be excluded** and generally cannot be capped below the foreseeable, contract-typical damage. Any single "we are not liable" or fixed-euro-cap clause drafted the Anglo-American way will likely be **struck down in its entirety** (no `geltungserhaltende Reduktion`), which can expose CLARA to **unlimited** liability. Treat the wording below as a **structure to be redrafted**, not final text.

Suggested (to-be-reviewed) structure:

1. **Unlimited liability.** CLARA is liable without limitation for damages arising from **intent** and **gross negligence**; from **injury to life, body, or health**; under the **Produkthaftungsgesetz (Product Liability Act)**; and to the extent CLARA has assumed a **guarantee** or fraudulently concealed a defect.
2. **Cardinal obligations.** For **slightly negligent** breach of an **essential contractual obligation** (a `Kardinalpflicht` — an obligation whose fulfilment makes proper performance of the contract possible at all and on whose observance the Customer regularly relies), CLARA is liable, but **limited to the foreseeable, contract-typical damage**.
3. **Other cases.** Any further liability for slight negligence is excluded.
4. **Cap (indicative only — lawyer to validate).** Where liability under 10.2 can be limited by amount, it is capped at {{LIABILITY_CAP e.g. the fees paid by the Customer in the 12 months preceding the event}} per event / per contract year. **This cap must not undercut the foreseeable contract-typical damage and must not touch the non-excludable heads in 10.1.**
5. **Data loss.** Liability for loss of data is limited to the typical restoration effort that would have arisen had the Customer maintained regular, risk-appropriate backups. _(Only valid alongside a genuine allocation of backup responsibility — confirm with DPA/TOMs.)_
6. **Force majeure.** Neither party is liable for failure or delay caused by events beyond its reasonable control (e.g. outages of the AI Provider or upstream infrastructure, natural events, war, strikes, state measures), for the duration of the event.
7. The above limitations apply equally to the personal liability of CLARA's legal representatives, employees, and vicarious agents (`Erfüllungsgehilfen`).
8. Statutory limitation periods (`Verjährung`) apply; any contractual shortening must respect mandatory minimums and is left to the lawyer.

> Do not import a US-style "IN NO EVENT SHALL... AGGREGATE LIABILITY... CONSEQUENTIAL DAMAGES" clause. It does not map to German law and is a common cause of total invalidity under § 307 BGB.

---

## 11. Confidentiality

1. Each party will keep the other's **Confidential Information** (non-public business, technical, and commercial information, including the Services' non-public features, pricing, and Customer Data) confidential, use it only to perform the contract, and protect it with at least reasonable care.
2. Exceptions: information that is or becomes public without breach, was lawfully known before disclosure, is independently developed, or is lawfully received from a third party.
3. Disclosure required by law, court, or authority is permitted, with prior notice to the other party where legally possible.
4. Confidentiality survives termination for **{{CONFIDENTIALITY_SURVIVAL e.g. 3}}** years; trade secrets remain protected under the **Geschäftsgeheimnisgesetz (GeschGehG)** for as long as they qualify.
5. Data protection obligations for personal data are governed by the DPA and take precedence for such data.

---

## 12. Term and termination

1. **Term.** The Subscription Term is stated in the Order. Unless the Order says otherwise, it runs for an initial term of **{{INITIAL_TERM e.g. 12 months}}** and **renews automatically** for successive periods of **{{RENEWAL_TERM e.g. 12 months}}** unless terminated with **{{NOTICE_PERIOD e.g. 30 days / 3 months}}** notice in text form before the end of the current term.
   > **Auto-renewal flag:** German rules on automatic contract renewal and notice periods that were tightened for consumer contracts (`Gesetz für faire Verbraucherverträge`, § 309 Nr. 9 BGB) do **not** apply in B2B, but a court may still test long tie-in/renewal/notice terms via § 307 BGB. Keep terms moderate and have the lawyer confirm.
2. **Ordinary termination.** Fixed-term subscriptions end at the term's end per 12.1; there is no ordinary termination for convenience during a running term unless the Order allows it.
3. **Termination for cause.** Either party may terminate for good cause (`außerordentliche Kündigung aus wichtigem Grund`, § 314 BGB / § 543 BGB as applicable) without notice, including for the other party's uncured material breach after a reasonable cure period, or on insolvency to the extent legally permitted. Grounds for CLARA include serious or repeated breach of Sections 3 (payment), 6 (data), or 7 (acceptable use).
4. **Effect of termination.** On termination, the Customer's right to use the Services ends and CLARA may disable access. Prepaid fees are non-refundable except where termination results from CLARA's uncured material breach.
5. **Data export and deletion.** For **{{RETRIEVAL_WINDOW e.g. 30}}** days after termination, CLARA will make Customer Data available for export in a common format; thereafter CLARA will delete or return Customer Data **in accordance with the DPA** (subject to statutory retention duties, e.g. § 147 AO / § 257 HGB for CLARA's own commercial records).
6. Termination must be in text form.

---

## 13. Changes to the Services and to these terms

1. **Changes to the Services.** CLARA may modify the Services to reflect technical progress, security, or legal requirements, provided the changes do not **materially degrade** the core functionality the Customer subscribed to. Material adverse changes will be notified in advance.
2. **Changes to these AGB.** CLARA may amend these AGB for the future (e.g. for legal changes, new features, or price adjustments at renewal). CLARA will notify the Customer in text form at least **{{AGB_CHANGE_NOTICE e.g. 6 weeks}}** before the change takes effect.
   - The change is deemed accepted unless the Customer objects in text form before the effective date, **provided** CLARA drew the Customer's attention to this consequence and to the objection right in the notice.
   - If the Customer objects, either party may terminate to the effective date; otherwise the existing terms continue until the end of the current Subscription Term.
   > **Change-of-terms clauses (`Änderungsvorbehalt`) are closely scrutinised under § 308 Nr. 4 / § 307 BGB.** A silence-is-consent mechanism must be fair, well-signposted, and paired with a genuine objection/termination right. Lawyer must confirm the notice period and the deemed-acceptance mechanism are enforceable, and limit unilateral changes to reasonable ones.

---

## 14. Miscellaneous, governing law, jurisdiction, and severability

1. **Assignment.** The Customer may not assign the contract without CLARA's prior text-form consent (not to be unreasonably withheld). CLARA may assign to an affiliate or in connection with a merger or sale of the business, subject to data-protection continuity.
2. **Subcontractors.** CLARA may use subcontractors/sub-processors; for personal data this is governed by the DPA.
3. **Entire agreement.** The contract (Order, DPA, these AGB, Annexes) is the complete agreement on its subject matter and supersedes prior understandings. There are no verbal side agreements. Amendments require text form; this also applies to any change to the text-form requirement itself. _(Note § 305b BGB: individually negotiated terms always prevail over these AGB regardless of this clause.)_
4. **Notices** must be in text form to the contact addresses in the Order/account.
5. **Governing law.** The contract and these AGB are governed by the **law of the Federal Republic of Germany**, excluding the **UN Convention on Contracts for the International Sale of Goods (CISG)** and excluding conflict-of-laws rules that would lead to another jurisdiction's law.
6. **Jurisdiction (`Gerichtsstand`).** For all disputes arising from or in connection with the contract, the **exclusive place of jurisdiction is Berlin, Germany**, provided the Customer is a merchant (`Kaufmann`), a legal person under public law, or a public-law special fund (§ 38 ZPO). CLARA may also sue at the Customer's general place of jurisdiction.
   > A B2B exclusive-jurisdiction clause is generally valid under § 38 ZPO, but for **EU-cross-border** customers the lawyer should confirm interplay with the **Brussels Ia Regulation (EU) No 1215/2012** on jurisdiction/enforcement.
7. **Severability / `salvatorische Klausel`.** Should any provision be or become invalid or unenforceable, the validity of the remaining provisions is unaffected. **Note:** under German law a severability clause does **not** save an invalid **AGB** clause by replacing it with a valid one (no `geltungserhaltende Reduktion`); the gap is filled by statutory law (§ 306(2) BGB). This clause is therefore mainly declaratory — the lawyer should ensure each individual clause stands on its own.
8. **Language.** {{PREVAILING_LANGUAGE clause — e.g. "In case of discrepancy between the German and English versions, the German version prevails for customers domiciled in Germany."}}

---

_End of skeleton. Version {{VERSION}} · Effective {{EFFECTIVE_DATE}} · Prepared for legal review, not for publication._

---

## Reviewer checklist (for the Fachanwalt — delete before publishing)

- [ ] Confirm B2B-only scope; add consumer terms/withdrawal set if any B2C is planned.
- [ ] Redraft **Section 10 (liability)** to § 307/§ 309-via-§ 310 standards — the current text is a structure, not final.
- [ ] Confirm contract-type classification (Miet-/Dienst-/gemischter Vertrag) and its impact on Sections 8–9 warranties (§ 536 BGB).
- [ ] Validate the change-of-terms mechanism (Section 13) under § 308 Nr. 4 / § 307 BGB.
- [ ] Validate auto-renewal/notice terms (Section 12) under § 307 BGB (B2B).
- [ ] Confirm VAT/reverse-charge and invoice wording with the tax advisor (Section 3).
- [ ] Cross-check DPA, Datenschutzerklärung, TOMs, Impressum consistency (Sections 0, 6).
- [ ] Confirm EU AI Act Art. 50 transparency obligations applicable to CLARA and reflect (Section 2.1).
- [ ] Resolve the Freiberufler-vs-Gewerbe / legal-form question before the provider block goes live (Section 0).
- [ ] Prepare an authoritative **German-language** version and set the prevailing-language rule (Section 14.8).

## Key sources consulted (verify currency at review time)

- § 309 BGB (Klauselverbote ohne Wertungsmöglichkeit): https://www.gesetze-im-internet.de/bgb/__309.html
- § 310 BGB (Anwendungsbereich — AGB gegenüber Unternehmern; § 309 applied indirectly via § 307): https://www.gesetze-im-internet.de/bgb/__310.html
- AGB liability limits in B2B (Kardinalpflichten; gross negligence not excludable): https://www.wbs.legal/allgemein/haftungsbeschrankung-in-agb-zwischen-unternehmern-14364/
- TMG repealed 14 May 2024 → § 5 DDG for Impressum: https://www.it-recht-kanzlei.de/tmg-ttdsg-ausser-kraft-impressum-datenschutz.html
- DDG overview (implements the EU DSA): https://www.e-recht24.de/news/datenschutz/13296-webseitenbetreiber-aufgepasst-das-tmg-wird-zum-digitale-dienste-gesetz-aktualisieren-sie-jetzt-ihr-impressum.html
- EU AI Act Article 50 (transparency obligations, apply 2 Aug 2026): https://artificialintelligenceact.eu/article/50/
- EU AI Act Art. 50 timing / marking grace period (Omnibus): https://datamatters.sidley.com/2026/06/24/eu-ai-act-transparency-obligations-preparing-for-compliance-by-2-august-2026/
