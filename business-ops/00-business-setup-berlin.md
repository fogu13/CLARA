# Business & Tax Setup (Berlin/Germany)

_CLARA — AI customer-feedback triage / Voice-of-Customer engine_
_Owner: solo founder (Freiberufler + USt-IdNr), Berlin. Last updated: 2026-07-01._

> **This is not legal or tax advice.** It is a research-backed operational checklist. German
> Freiberufler-vs-Gewerbe classification and any liability/entity structuring are fact-specific and
> ultimately decided by your Finanzamt. Confirm every decision below with a **Steuerberater** (and,
> for entity/liability topics, a **Rechtsanwalt/Notar**) before you rely on it — ideally **before you
> issue the first CLARA invoice.**

---

## Summary

Selling CLARA as a **productised, self-service AI SaaS subscription** in Germany is almost certainly a
**Gewerbe (commercial trade), not a Freiberufler activity** — even though you are already registered as
Freiberufler and hold a USt-IdNr. German tax law treats the licensing/sale of standardised,
mass-reproducible software as commercial trade, distinct from the individual, "engineer-like" bespoke
software development that can qualify under §18 EStG. Practically this means a **Gewerbeanmeldung, IHK
membership, and Gewerbesteuer** — but at solo/early-revenue scale the cash cost is modest (a €24,500
trade-tax allowance plus the §35 EStG credit largely neutralise it, IHK gives new founders a 2-year fee
waiver, and the Berlin trade registration costs ~€15). The **single biggest risk in your current setup is
"Abfärbung" (infection)**: mixing gewerbliche SaaS revenue into your existing freiberuflich activity
without clean separation can retroactively reclassify **all** your income as gewerblich. The highest-leverage
action is therefore to **engage a Steuerberater this month**, before the first SaaS invoice, to (a) get the
classification right, (b) ring-fence the two activities, and (c) set up VAT correctly (waive
Kleinunternehmer, run regular VAT, handle EU reverse-charge/OSS/ZM). Stay a solo Einzelunternehmen to
validate go-to-market and convert to a **UG/GmbH** on concrete triggers (real customer PII at scale, first
investor, a co-founder, or an enterprise buyer demanding a limited-liability counterparty).

## Assumptions

- You are a solo founder, Berlin-resident, currently registered **Freiberufler** with a **USt-IdNr**.
- CLARA will be sold as a **repeatable B2B SaaS subscription** (not one-off bespoke development contracts).
- Primary customers are **VAT-registered EU businesses** (B2B); some may be German, some cross-border EU.
- You want to **move fast** and keep costs/overhead low while remaining defensible.
- Figures below were verified via web search in 2026 and can change — the exact **Berlin Hebesatz**, IHK
  fees, and thresholds should be re-confirmed with the district office / IHK Berlin / your Steuerberater for
  your assessment year.

---

## 1. The core decision: Freiberufler vs Gewerbe

### Why CLARA is (almost certainly) Gewerbe

| Freiberufler (§18 EStG) survives when… | Gewerbe (trade) applies when… |
| --- | --- |
| You perform **individual, bespoke** software development personally, with an "engineer-like" (ingenieurähnliche) qualification (relevant degree). | You **sell/license standardised software** or run a **self-service product/platform** — legally equated with selling copies of a program. |
| Value is your personal expertise on a specific client problem, little repeatable packaging. | Services are **standardised, mass-reproducible**, subscription-based, "own product/platform operated." |

A mass-market, reproducible, subscription AI product does **not** fit the Katalogberuf / ähnlicher Beruf
definition. Expect the Finanzamt to classify CLARA revenue as **gewerblich**. This is the single most
consequential call — **confirm the exact line with a Steuerberater.**

- Existenzgründungsportal (BMWK) — developing vs selling software: <https://www.existenzgruendungsportal.de/Redaktion/DE/BMWK-Infopool/Antworten/Gruendungsplanung/Freie-Berufe/gemischte-Taetig/Software-entwickeln-und-vertreiben-freiberufliche-Taetigkeiten>
- Guhr Steuerberatung — software as gewerblich vs freiberuflich: <https://guhr-steuerberatung.de/blog/softwareentwicklung-gewerbliche-oder-freiberufliche-taetigkeit/>
- BFH decision (software classification): <https://www.bundesfinanzhof.de/en/entscheidungen/entscheidungen-online/decision-detail/STRE201110211/>

### The Abfärbung ("infection") trap — most important item for your situation

If you keep your Freiberufler registration and simply add gewerbliche SaaS income **inside the same
activity/entity without strict separation**, the commercial activity can **"abfärben" (infect) your entire
income**, making **all** of it gewerblich and Gewerbesteuer-liable — potentially retroactively.

**Mitigation (set up with a Steuerberater BEFORE the first SaaS invoice):**

- Keep **strictly separate bookkeeping** for freiberuflich vs gewerblich activities (separate ledgers,
  ideally a separate business bank account).
- Consider a **separate legal vehicle (UG/GmbH) for the SaaS** as revenue grows — the clean structural fix.
- Get the classification and separation documented so it is defensible to the Finanzamt.

Sources: <https://restio.io/de/blog/gewerbe-vs-freiberufler-2026/> · <https://www.gieron.de/unternehmen/abgrenzung_freiberufliche_taetigkeit_gewerbe_e3623/> · <https://lkm-lawtax.com/freiberufler-oder-gewerbe-2026/>

### Recommendation

> **Assume Gewerbe for CLARA. Do not gamble on Freiberufler status for a self-service SaaS product.**
> Book a Steuerberater consultation **this month**, framed precisely: _"I am a registered Freiberufler with a
> USt-IdNr and want to launch a productised AI SaaS — how do I handle the Gewerbe classification and avoid
> Abfärbung on my existing freelance income?"_ This is the highest-leverage action in this whole document.

---

## 2. Registrations (the paperwork path)

### 2.1 Gewerbeanmeldung (Berlin)

Berlin has **no central Gewerbeamt** — it is decentralised by Bezirk (district); jurisdiction follows your
business seat. Register online via **berlin.de/ea/** (eMeldung).

| Item | Detail |
| --- | --- |
| Where | Ordnungsamt of your Bezirk, online at <https://www.berlin.de/ea/> |
| Cost | ~**€15 online** (natural person) · €26 in person · **€31** for a legal entity (GmbH/UG) |
| Payment | SEPA or card |
| Output | Gewerbeschein by post/digitally; **Finanzamt and IHK notified automatically** |

Sources: <https://berlinecho.de/gewerbe-anmelden-berlin-kosten-ablauf/> · <https://www.gewerbe-anmeldung.com/gewerbeamt-berlin-gewerbeanmeldung-gewerbeschein.html> · <https://qonto.com/de/blog/unternehmensgruendung/einzelunternehmen/gewerbe-anmelden-berlin>

### 2.2 Finanzamt — Fragebogen zur steuerlichen Erfassung (via ELSTER)

After the Gewerbeanmeldung, complete the **"Fragebogen zur steuerlichen Erfassung"** via ELSTER. You declare
expected turnover, the Kleinunternehmer choice, and VAT registration; the Finanzamt assigns/updates tax
numbers. You already have this channel and a USt-IdNr as a Freiberufler — the **new gewerbliche activity must
be added/registered correctly** (and cleanly separated). Source: <https://norman.finance/blog/gewerbeanmeldung>

### 2.3 IHK Berlin membership (compulsory) + fees

Registering a Gewerbe triggers **automatic, mandatory IHK Berlin membership.**

- **New founders (Existenzgründer): no IHK fee for the first 2 years**, and only the Grundbeitrag (no Umlage)
  in years 3–4 — provided you are a non-registered sole proprietor and Gewerbeertrag/profit stays ≤ €25,000.
- IHK Berlin **Grundbeitrag ~€64/yr**; the Umlage has a nationwide **€15,340 profit allowance**; **no
  Grundbeitrag if Gewerbeertrag < €5,200**.
- ⚠️ **The founder waiver is void if you had commercial/freelance income (or a >10% stake in a corporation)
  in the prior 5 years.** Your existing Freiberufler status may therefore **disqualify you** — flag this to
  the IHK / Steuerberater explicitly.

Sources: <https://www.ihk.de/berlin/ueber-uns/mitgliedschaft-und-beitrag/das-verfahren-der-beitragserhebung/besonderheiten-der-beitragserhebung/existenzgruender-2280552> · <https://www.ihk.de/berlin/ueber-uns/mitgliedschaft-und-beitrag/das-verfahren-der-beitragserhebung/bestandteile-des-beitrags-2280542>

### 2.4 Gewerbesteuer — and why it barely stings at your scale

- **€24,500 profit allowance** for sole proprietors before trade tax applies.
- Federal Messzahl **3.5%**; **Berlin Hebesatz 410%** (as of 2026 — re-confirm for your assessment year).
- **§35 EStG credits 4× the Gewerbesteuer-Messbetrag** against your personal income tax, fully offsetting
  trade tax up to a Hebesatz of ~400% — so at Berlin's 410% only a tiny residual remains.
- Worked example: **€70k profit in Berlin ≈ €6,527 trade tax**, largely neutralised by the §35 credit.

**Net effect for a small solo profit: Gewerbesteuer is largely neutralised** — the Gewerbe classification is
far less painful financially than it first sounds.

Sources: <https://www.fuer-gruender.de/wissen/unternehmen-gruenden/finanzen/steuern/gewerbesteuer-rechner/> · <https://www.gesetze-im-internet.de/estg/__35.html> · <https://www.juhn.com/fachwissen/unternehmensbesteuerung/anrechnung-der-gewerbesteuer-nach-35-estg/>

---

## 3. VAT (Umsatzsteuer) handling

### 3.1 Kleinunternehmerregelung (§19 UStG) — waive it for B2B SaaS

New **permanent thresholds since 1 Jan 2025** (unchanged for 2026): **≤ €25,000 turnover in the prior year
AND ≤ €100,000 in the current year.** The €100,000 is now a **hard limit** — the moment you exceed it you
switch to standard VAT immediately, for every further euro. New founders start as Kleinunternehmer
automatically.

> **Recommendation: opt OUT (waive §19) and register for regular VAT.** Your B2B customers are VAT-neutral
> (they don't care about the VAT line), and you gain **input-VAT (Vorsteuer) recovery** on cloud/AI/infra/
> tooling spend plus a clean USt-IdNr for EU reverse-charge. Kleinunternehmer status mainly helps B2C/consumers.
> Confirm with your Steuerberater whether VAT should run across both activities.

Sources: <https://www.ihk.de/stuttgart/fuer-unternehmen/recht-und-steuern/steuerrecht/umsatzsteuer-national/kleinunternehmerregelung-in-der-umsatzsteuer-1843632> · <https://taxfix.de/ratgeber/selbststaendige/kleinunternehmergrenze/> · <https://www.nwb.de/rechnungswesen/neuregelungen-fuer-kleinunternehmer-ab-2025>

### 3.2 EU B2B: reverse charge + Zusammenfassende Meldung (ZM)

For SaaS sold to **VAT-registered EU businesses:**

1. Invoice **net (no German VAT)** and apply the **§13b reverse charge**.
2. The invoice must state **"Steuerschuldnerschaft des Leistungsempfängers"** / **"Reverse charge"** and show
   **both parties' USt-IdNr**.
3. **Validate every customer VAT ID via VIES** before invoicing.
4. File a **quarterly Zusammenfassende Meldung (ZM)** listing these EU B2B sales.

### 3.3 EU B2C: One-Stop-Shop (OSS)

For **B2C digital services** across the EU, reverse charge does **not** apply — you charge the **customer's
local VAT rate** and remit via the **OSS portal** (single registration, one quarterly return). Your existing
USt-IdNr is the prerequisite for both mechanisms.

Sources: <https://www.mehrwertsteuerrechner.de/reverse-charge/> · <https://restio.io/en/blog/reverse-charge-international-germany/> · <https://www.steuerberater-braun.de/steuerwissen/allgemein/influencer-auslandskooperationen-umsatzsteuer-richtig-loesen-b2b-b2c-reverse-charge-oss/>

### 3.4 Operational shortcut: Merchant-of-Record (MoR) billing

If the VAT admin above feels heavy for a solo founder, a **Merchant-of-Record** billing platform (**Paddle**
or **Lemon Squeezy**) becomes the **legal seller of record** and handles EU-VAT collection/filing/OSS **for
you** — at roughly **5% + €0.50/transaction** (about 2× the raw cost of Stripe ~2.9% + €0.30 plus Stripe Tax
~0.5%/txn). Trade-off: higher fees, near-zero tax ops.

- **Launch default (solo, cross-border):** MoR (Paddle preferred — it absorbs most chargeback liability).
- **Migrate to Stripe + Stripe Tax** past ~€50–100k MRR, when insourcing tax is worth the margin.
- Note: with Stripe you remain legally responsible for VAT registration/OSS/ZM — Stripe Tax **calculates**
  and validates VAT IDs / applies reverse charge but does **not file** returns for you.

Sources: <https://www.globalsolo.global/blog/stripe-vs-paddle-vs-lemon-squeezy-2026> · <https://www.paddle.com/help/sell/tax/how-paddle-handles-vat-on-your-behalf> · <https://docs.stripe.com/tax/supported-countries/european-union> · <https://stripe.com/guides/introduction-to-eu-vat-and-european-vat-oss>

---

## 4. Invoicing rules

### 4.1 Content requirements (§14 UStG)

| Regular invoice (> €250 gross) — §14 UStG | Kleinbetragsrechnung (≤ €250 gross) — §33 UStDV |
| --- | --- |
| Full name + address of **supplier AND recipient** | Supplier name + address only |
| Your **Steuernummer OR USt-IdNr** | (not required) |
| **Unique sequential invoice number** | (not required) |
| Issue date | Date |
| Quantity/type of goods or scope/type of service | Quantity/type |
| Time of supply | — |
| Net amount, **VAT rate and VAT amount** (or exemption/reverse-charge note) | Gross sum **with VAT rate** |

For EU B2B, add the reverse-charge note + both USt-IdNr (see §3.2). Sources:
<https://www.gesetze-im-internet.de/ustg_1980/__14.html> · <https://www.handelskammer-hamburg.de/recht-steuern/steuerrecht/umsatzsteuer-mehrwertsteuer/umsatzsteuer-mehrwertsteuer-national/umsatzsteuer-pflichtangaben-rechnungen-6680494> · <https://sevdesk.de/ratgeber/buchhaltung-finanzen/rechnungen/art/kleinbetragsrechnung/>

### 4.2 B2B E-Rechnung mandate — your deadlines

Structured e-invoicing means **EN 16931 format** (e.g. **XRechnung / ZUGFeRD**), not a PDF.

| Obligation | When it applies to you (≤ €800k turnover) |
| --- | --- |
| **RECEIVE** structured e-invoices | **Already mandatory since 1 Jan 2025.** A plain email inbox suffices to receive, but you need software to **read + archive GoBD-compliant** in the original structured format. |
| **SEND** — transition period | Paper/PDF still allowed **until 31 Dec 2026** (with recipient consent). |
| **SEND** — > €800k prior-year turnover | From **1 Jan 2027**. |
| **SEND** — ≤ €800k (you) | From **1 Jan 2028** (you have until 31 Dec 2027). |
| **SEND** — all B2B | From **1 Jan 2028**. |

Exceptions: invoices ≤ €250 (Kleinbetrag) and Kleinunternehmer (§34a UStDV) are exempt from **issuing**
e-invoices even after 2028 — but must still be able to **receive**.

> **Action now:** adopt invoicing software that can **receive + archive** XRechnung/ZUGFeRD (GoBD-compliant).
> Plan to **send** structured e-invoices before 1 Jan 2028 — doing it early is a low-cost win that also fits
> CLARA's own "governed & auditable" positioning.

Sources: <https://www.bundesfinanzministerium.de/Content/DE/FAQ/e-rechnung.html> · <https://www.ihk-muenchen.de/ratgeber/steuern/elektronische-rechnungen/> · <https://rickert.law/e-rechnung-b2b-2027/> · <https://sevdesk.de/ratgeber/buchhaltung-finanzen/rechnungen/e-rechnung/kleinunternehmer-pflicht/>

---

## 5. Bookkeeping

- As a non-registered sole proprietor (Einzelunternehmen/Freiberufler) you use the simple
  **Einnahmen-Überschuss-Rechnung (EÜR)** — **cash-basis, no double-entry Bilanz** — filed annually via
  ELSTER (**Anlage EÜR**).
- This holds until you exceed the accounting thresholds (~**> €800k turnover** or **> €80k profit**) or form a
  **GmbH/UG** (which requires double-entry Bilanzierung).
- Keep **GoBD-compliant** records and **archive e-invoices in their original structured format.**
- **Keep freiberuflich and gewerblich ledgers strictly separate** (see Abfärbung, §1) — separate ledgers,
  ideally a separate bank account.

Source: <https://sevdesk.de/ratgeber/gruenden/selbstaendigkeit-anmelden/gewerbe/gewerbe-anmelden-in-berlin/>

---

## 6. Entity choice: stay solo now, incorporate on triggers

| Form | Setup cost / capital | Liability | Accounting | Best for |
| --- | --- | --- | --- | --- |
| **Einzelunternehmen** (now) | ~€15–50 | **Unlimited personal** | EÜR (cash-basis) | Cheapest; fast GTM validation |
| **UG** ("mini-GmbH") | From €1 capital; ~€350–1,000 setup | Limited | Double-entry | Liability shield on a budget; must retain 25% of profit until €25k reserve reached |
| **GmbH** | €25,000 share capital (**€12,500 min. paid-in**); notary + Handelsregister | Limited | Double-entry | Strongest B2B/investor credibility |

**Recommendation:** stay a **solo Einzelunternehmen** to validate go-to-market and keep costs low. Convert to
a **UG or GmbH** when you hit a concrete trigger:

1. You handle **significant real customer PII at scale** → liability shield (CLARA's GDPR / EU-AI-Act
   data-processing exposure is a **legitimate reason to incorporate earlier** — discuss with a lawyer).
2. You **take investment** (business angels / EIC).
3. A **co-founder** joins.
4. An **enterprise B2B customer** demands a GmbH counterparty.

> Notarised UG/GmbH formation **requires a Notar/Rechtsanwalt**, a business bank account (for the paid-in
> capital, deposited **before** Handelsregister entry), and double-entry accounting.

Sources: <https://www.derstartupanwalt.de/news/gruendung-ug-gmbh-fuer-gruender-und-startups> · <https://qonto.com/de/blog/rechtsformen/ug/ug-vs-gmbh> · <https://www.fuer-gruender.de/wissen/existenzgruendung-planen/recht-und-steuern/rechtsform/unternehmergesellschaft/>

---

## 7. Bank account

- **Legally optional** for an Einzelunternehmen, but **strongly advised** for clean separation (and it
  reinforces the Abfärbung firewall).
- **Mandatory for UG/GmbH** — the paid-in capital must be deposited before Handelsregister entry.
- Fast, solo-friendly options: **Qonto, Finom, Holvi** (rapid IBAN issuance, EU-based — consistent with
  CLARA's EU-residency positioning).

Source: <https://qonto.com/de/blog/unternehmensgruendung/einzelunternehmen/gewerbe-anmelden-kosten>

---

## 8. Insurance

> Standard German market coverage for a solo B2B SaaS founder. The research did not fix specific premiums, so
> the ranges below are **illustrative market ballparks — get a broker quote** (e.g. Hiscox, exali, Finanzchef24)
> and have your Steuerberater confirm deductibility.

| Insurance | Why it matters for CLARA | Typical solo ballpark (confirm) |
| --- | --- | --- |
| **Vermögensschadenhaftpflicht** (professional indemnity) | Covers financial-loss claims from faulty advice/insights or SaaS errors — core exposure for an insight/decision product | ~€300–1,000/yr |
| **Cyber-Versicherung** (cyber liability) | You process customer feedback text (potential PII) under GDPR — covers breach response, notification, third-party claims | ~€300–1,500/yr |
| **Betriebs-/Berufshaftpflicht** (general/professional liability) | General business third-party liability | ~€150–500/yr |
| **Krankenversicherung** (health) | Self-employed = self-insured; confirm private vs voluntary statutory (freiwillig GKV) | Varies significantly |

Practical note: **Vermögensschadenhaftpflicht + Cyber** are the two that most directly match CLARA's risk
profile (advice/insight liability + PII processing) and are frequently requested in DACH B2B procurement — pair
them with your GDPR DPA/TOMs pack (see the legal/compliance document).

---

## 9. Cross-references (out of scope here, do not forget)

- **Impressum (§5 DDG)** must include your **USt-IdNr** — a business-setup touchpoint handled in the
  legal/compliance document. TMG was repealed 14 May 2024; cite **§5 DDG**, not TMG.
  <https://www.it-recht-kanzlei.de/tmg-ttdsg-ausser-kraft-impressum-datenschutz.html>
- **GDPR (Art. 28 DPA/AVV, TOMs, ROPA, DPIA) and EU AI Act** obligations → legal/compliance document.
- **Grants/funding** (EXIST, IBB GründungsBONUS Plus, EIC Accelerator) → go-to-market/funding document.

---

## 10. Status checklist (Done / To do)

### Done

| Item | Status | Note |
| --- | --- | --- |
| Freiberufler registration (freelance licence) | Done | Existing — but likely **not** the right basis for productised SaaS (§1) |
| USt-IdNr (VAT number) | Done | Prerequisite for EU reverse-charge + OSS; keep it |

### To do — do first (before the first SaaS invoice)

| # | Item | Priority | Notes |
| --- | --- | --- | --- |
| 1 | **Book a Steuerberater** (software/SaaS-savvy) | Now | Classification + Abfärbung firewall + VAT setup. Highest leverage. |
| 2 | Decide **Freiberufler vs Gewerbe** (assume Gewerbe) | Now | Get it documented/defensible |
| 3 | **Ring-fence** freiberuflich vs gewerblich (separate ledgers/bank) | Now | Prevents infection of all income |
| 4 | **Waive §19 Kleinunternehmer**, register for regular VAT | Now | B2B input-VAT recovery + clean reverse-charge |

### To do — setup (weeks 1–4)

| # | Item | Priority | Notes |
| --- | --- | --- | --- |
| 5 | **Gewerbeanmeldung** via berlin.de/ea/ (~€15) | Soon | Your Bezirk's Ordnungsamt |
| 6 | Update **Fragebogen zur steuerlichen Erfassung** (ELSTER) | Soon | Add the gewerbliche activity |
| 7 | **IHK Berlin** — confirm membership + **check founder-waiver eligibility** | Soon | Prior Freiberufler income may void the 2-yr waiver |
| 8 | Set up **EU B2B reverse-charge invoicing** (both USt-IdNr, "Reverse charge") + **VIES validation** + quarterly **ZM** | Soon | Or use a MoR platform (§3.4) |
| 9 | **OSS registration** — only if selling B2C across EU | If needed | Not needed for pure B2B |
| 10 | **Business bank account** (Qonto/Finom/Holvi) | Soon | Clean separation; mandatory later for UG/GmbH |
| 11 | **E-invoice RECEIVE + archive** capability (XRechnung/ZUGFeRD, GoBD) | Soon | **Already mandatory since 2025** |
| 12 | Set up **EÜR bookkeeping** (GoBD-compliant) | Soon | Anlage EÜR via ELSTER |
| 13 | **Insurance**: Vermögensschadenhaftpflicht + Cyber (+ health check) | Soon | Match CLARA's advice/PII risk profile |

### To do — plan ahead (triggers / deadlines)

| # | Item | When |
| --- | --- | --- |
| 14 | **E-invoice SEND** capability | Before **1 Jan 2028** (do it early — low-cost win) |
| 15 | **UG/GmbH conversion** | On trigger: PII at scale · investor · co-founder · enterprise buyer |
| 16 | Verify **Berlin Hebesatz (410%)**, IHK fees, €800k EÜR threshold for your assessment year | Before filing/relying |

---

### One-line reminder

**Do not issue a single CLARA SaaS invoice before a Steuerberater has (a) confirmed the Gewerbe classification,
(b) set up the Abfärbung firewall, and (c) configured your VAT (waive §19, EU reverse-charge/OSS/ZM).**

> _Not legal or tax advice — confirm with a Steuerberater (and a Rechtsanwalt/Notar for entity/liability
> matters) before relying on anything above._
