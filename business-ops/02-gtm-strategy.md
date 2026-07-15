# CLARA — Go-To-Market Strategy

> Business-ops document 02. Companion to the founder tax/legal setup doc (01) and the pricing/financial
> model. Aligns with the locked positioning in `../business/STRATEGY_SYNTHESIS.md` (§6): the USP is
> **automated loop closure**; EU-sovereignty and governance are the **layer on top** and the DACH
> procurement unblocker — not the headline.

## Summary

CLARA goes to market as the **European Feedback-to-Outcome engine**: it closes the full customer-feedback
loop automatically — Signal → Insight → Action → **Learning** — deciding what to do about a customer
problem, executing safely through the tools you already run (Jira, Zendesk, Braze), and proving whether it
worked, then remembering what worked for next time. That automated loop closure plus the compounding
**Experiment Learning Repository** is the differentiator no incumbent (Enterpret included) owns end-to-end;
**EU data residency, GDPR Art. 28 posture, and EU AI Act-aligned audit trails** are the layer that gets
CLARA *past DACH procurement*, where US-hosted tools stall on data residency. The fastest credible motion
for a solo Berlin founder is **founder-led, high-touch sales**: recruit 7–10 design partners / paid pilots
(60–90 days, one hard success metric each) out of warm networks, convert them into referenceable logos,
and fund the slow trust-building phase with non-dilutive grants (EXIST, IBB GründungsBONUS Plus). Land in
the **€12k–€30k/yr mid-market ACV band** — matching the closest competitor's *entry* economics (Enterpret's
entry is reportedly ≈$1,000/mo (~$12k/yr) per review-site data, being validated in discovery calls; its
*median* buyer pays ~$36k and Chattermill averages ~$64k — median ≠ entry) and winning on governed
outcomes + EU sovereignty rather than price — with a
hybrid base-plus-usage model billed through a Merchant-of-Record (Paddle) so a one-person business skips
EU-VAT filing entirely. **Before invoicing the first paid pilot, resolve the Freiberufler-vs-Gewerbe
question** (a productised SaaS is almost certainly *Gewerbe*, not *Freiberufler*) — it is a hard GTM gate.

## Assumptions

- **Product stage:** CLARA is built (React 18 + Supabase); the governed action engine, evidence linking,
  approval/audit, and the outcome-learning repository exist or are partial. This is a commercialization
  GTM, not a pre-build plan.
- **Founder:** solo technical founder in Berlin, currently registered *Freiberufler* with a USt-IdNr,
  moving fast, bootstrapped/grant-funded, no sales team.
- **Geography:** DACH-first (Germany, Austria, Switzerland), EU-wide expansion. B2B only.
- **Proof assets:** validated on scraped Henkel / Lieferando / Trade Republic datasets — used as
  named-adjacent proof cases, not as customer references.
- **Pricing figures** for private competitors (Enterpret, Chattermill, Thematic, Unwrap, SentiSum) are
  third-party estimates (Vendr/G2/Capterra), directional only — verify before quoting to a prospect.
- **Regulatory dates** reflect research as of mid-2026, including the Digital Omnibus deferral of EU AI Act
  high-risk deadlines; confirm on Official Journal publication.

> **This is not legal or tax advice.** The Freiberufler-vs-Gewerbe classification, EU AI Act risk-tier, and
> any "AI Act / GDPR compliant" marketing claim are fact-specific — confirm with a Steuerberater and a
> Fachanwalt für IT-Recht/Datenschutz before relying on them or making categorical claims in market.

---

## 1. Positioning

### 1.1 Category and one-line positioning

**Category:** *feedback-driven journey orchestration* — the governed customer-intelligence and **action**
layer that sits **above** collection tools and helpdesks, not another dashboard.

**Positioning statement (primary — outcome-led):**

> *CLARA is the European Feedback-to-Outcome engine. It decides what to do about customer problems,
> executes the fix safely through the systems you already use, proves whether it worked, and remembers
> what worked — processed and hosted in the EU, governed and fully auditable by design.*

**Positioning statement (DACH procurement-led framing, for security-gated buyers):**

> *CLARA is the EU-sovereign Voice-of-Customer-to-action engine for privacy-first and regulated DACH
> companies. Unlike US-hosted VoC platforms (Enterpret, Chattermill, Thematic), CLARA processes feedback
> in the EU, turns it into governed, fully auditable actions across product and marketing, and
> self-improves from your measured business outcomes — with no fine-tuning of frontier models and no
> taxonomy to build.*

### 1.2 The locked USP — and how governance rides on top

Per the locked internal positioning (`STRATEGY_SYNTHESIS.md` §6), CLARA is **sold and evaluated as the
system that closes the loop**, not as a compliance gate. The hierarchy matters for every asset:

| Layer | What it is | Role in the sale |
|---|---|---|
| **Headline (the USP)** | Automated loop closure: Signal → Insight → Action → **Learning**, run automatically with human-in-the-loop where risk warrants | The thing you **win on** and demo |
| **The moat** | Experiment Learning Repository — remembers *which actions solved which problems in which contexts*; confidence decay + relevant-learnings retrieval | The compounding, category-of-one differentiator no competitor ships |
| **The layer on top** | EU residency / local-first, GDPR Art. 28 DPA, EU AI Act-aligned audit logs (Art. 12/50), graduated authority / policy-as-code, human-in-the-loop | The **procurement unblocker** that gets you *into* DACH deals |

**The GTM narrative in one sentence:** *governance opens the door; loop closure and the learning memory
close the deal.* Do **not** invert this — a governance-first pitch was explicitly rejected internally
because it buries the differentiator and reads as "just another compliance tool."

### 1.3 Reframes to adopt (cheap, high-leverage)

- **Dual-action framing:** every problem yields a *permanent structural fix* **and** an *immediate action
  for the customers affected today*. Nobody else frames both.
- **Policy-as-code:** describe approval/risk tiers as governed "policy-as-code" — strengthens the
  Responsible-AI story without new build.
- **Outcome category line:** *"Decide what to do about customer problems, execute safely through the
  systems you already use, and prove whether it worked."*

---

## 2. Competitive wedge

AI-native analysis (sentiment, auto-themes, clustering) is **table stakes in 2026** — Enterpret,
Chattermill, Thematic, Unwrap, SentiSum all have it. CLARA does **not** win on "better AI." The durable
wedge is the **mechanism competitors lack** plus **EU sovereignty**.

### 2.1 Landscape and CLARA's role

| Group | Players | CLARA's stance |
|---|---|---|
| **Closest threats** (intelligence → action) | Enterpret, Dovetail, Chattermill, SentiSum, Thematic, Unwrap | Match evidence-linking + feedback→ticket; **beat on governed action + learning memory + EU residency** |
| **Enterprise VoC suites** | Qualtrics, Medallia, Sprinklr, InMoment, Forsta | **Sources/partners, not rivals** — they collect, CLARA operationalizes |
| **Product-feedback / roadmap** | Pendo, Productboard, Sprig, Canny | Strong on "what to build," weak on service/marketing/outcome |
| **EU/DACH feedback SaaS** | zenloop, Mopinion, Feedier | Data-residency reference points; CLARA out-differentiates on action + learning |
| **Helpdesk triage** | Zendesk (Advanced-AI Copilot +$50/agent/mo; autonomous resolutions billed $1.50–$2.00 each, uncapped since Jan 2026, [richpanel.com](https://www.richpanel.com/learn/zendesk-pricing)) | **Do NOT compete as a helpdesk** — sit *above* it as the cross-source insight/governance/action layer |

### 2.2 The sharp wedge vs Enterpret (closest threat, reviewed June 2026)

Enterpret now *also* markets "Close the Loop," a Customer Context Graph, and an MCP server — so **the
generic "we close the loop" claim is no longer safe.** Lead with the mechanism Enterpret lacks:

1. **Governed action** — approval matrix, risk tiers, rule-conflict resolution, full audit. *Enterpret
   opens a ticket; CLARA governs what fires.*
2. **Cross-functional + marketing activation** — one insight → product **and** marketing/CX (segments,
   suppression, campaigns). Enterpret stops at product/support.
3. **Experiment Learning Repository** — confidence decay + relevant-learnings retrieval. **No VoC vendor
   ships this. The blue ocean.**
4. **European-first** — self-hostable, your-own-model, EU residency, EU AI Act checks *on the actions*.
   Enterpret is US cloud SaaS (GDPR data-processor, not self-hostable).
5. **SMB / mid-market, governance-first** — a segment Enterpret does not court.

**One-liner vs Enterpret:** *"Enterpret tells product teams what customers say and opens a ticket; CLARA
governs the action across product and marketing, proves it worked against a contract, and remembers what
worked — in your own EU cloud."*

### 2.3 Why-now (buying trigger)

- **EU AI Act Art. 50 transparency applies 2 Aug 2026** (not deferred by the Digital Omnibus) — buyers
  need AI-use disclosure and defensible audit trails now ([compliancehub.wiki](https://compliancehub.wiki/eu-ai-act-article-50-transparency-digital-omnibus-2026/)).
- **The deployer (your customer) carries obligations.** CLARA's built-in tamper-resistant logs let the
  buyer discharge *their* compliance — a concrete purchase justification, especially for regulated buyers.
- **DACH data-residency is a hard procurement filter:** "US platforms that process transcripts outside the
  EU are inherently non-compliant for sensitive German data" ([compound.law](https://compound.law/en-DE/compliance/ai-customer-service-gdpr/)). EU-native peers buyers already
  trust: Cognigy (Düsseldorf), Parloa (Berlin).
- **Bitkom 2026:** ~41% of German firms ≥20 staff use AI, and **93% would prefer a German AI provider** —
  direct tailwind for EU-first, German-language positioning.

> Note on risk-tier: CLARA's text-based triage is most likely **minimal/limited-risk** under the AI Act
> (the emotion-recognition prohibition and Annex III entry are **biometric-only**). Sell the audit trail
> as helping *the customer* meet *their* obligations; avoid categorical "CLARA is AI Act high-risk
> compliant" claims until counsel signs off. **Not legal advice.**

---

## 3. Ideal Customer Profiles (ICPs)

Three ICPs, mirroring CLARA's validation datasets. **Beachhead decision: prioritise ICP #3 for
willingness-to-pay and differentiator fit; run ICP #1 in parallel for volume and faster cycles.**

| | **ICP #1 — DACH mid-market B2B SaaS** | **ICP #2 — EU e-commerce / marketplaces** | **ICP #3 — Regulated DACH fintech / insurance** ⭐ |
|---|---|---|---|
| **Segment** | B2B SaaS, 100–999 employees, DE/AT/CH | DACH/EU e-commerce, food-delivery, marketplaces | Fintech, banking, insurance, DE/AT/CH |
| **Primary buyer** | VP Product / Head of CX / Head of Customer Insights | Head of CX / VoC / Operations | Head of CX **+ DPO/Compliance co-signer** |
| **Core pain** | Feedback scattered across app stores, support, reviews, NPS; US tools blocked in security review; taxonomy build is heavy | Very high multilingual review + support volume; needs German-language theming + urgency triage; consumer-PII residency | Cannot send feedback to US LLMs; needs governed, auditable, human-reviewable insights for BaFin/GDPR |
| **Why now** | AI Act Aug-2026 procurement questions + annual budget cycle | AI Act + peak-season review spikes | AI Act high-risk pressure + regulator focus; feedback is high-stakes |
| **CLARA fit** | EU-sovereign + auto snake_case theming (no taxonomy labor) + governed action + audit | Sentiment+urgency triage, clustering, outcome loop tied to CSAT/retention | **Strongest match:** governed & auditable, tamper-resistant logs, local-first — highest WTP |
| **Proof case** | — | **Lieferando** (validation set) | **Trade Republic** (validation set) |
| **Sales velocity** | Faster cycles, higher volume | Medium | Slower, highest ACV |

**Named-adjacent proof cases (one per ICP):** e-commerce = Lieferando · fintech = Trade Republic ·
brand/CPG = Henkel. Present as "validated on real scraped data from…", never as paying customers.

**Reconciling with the thesis scope:** the thesis targets SMB marketing/CX teams (10–500). Treat that as
the **entry motion** (Starter tier, self-serve-lite later); ICP #1/#3 mid-market is where the first paid
ACVs come from. Same product, two sizes.

---

## 4. Value proposition & messaging pillars

**Master value prop:** *"Turn scattered customer feedback into governed, audit-ready action — and prove it
worked — without sending a single record outside the EU."*

### Three messaging pillars

| # | Pillar | Claim | Proof / substantiation |
|---|---|---|---|
| **1** | **Automated loop closure** (the headline) | "Decide what to do, execute safely through the systems you already use, and prove whether it worked." Dual-action: structural fix + immediate action for affected customers. | Governed action engine, outcome contract (metric + window at action creation), three closure levels (operational/customer/outcome) |
| **2** | **Compounding learning memory** (the moat) | "CLARA remembers which actions solved which problems in which contexts — and gets sharper with every outcome." | Experiment Learning Repository: A/B pattern capture, confidence decay, relevant-learnings retrieval. **No competitor ships this.** |
| **3** | **Governed & EU-sovereign by design** (the layer) | "Local-first EU processing, GDPR Art. 28 DPA, EU AI Act-aligned audit logs, human-in-the-loop, no frontier fine-tuning, no taxonomy to build." | EU hosting; subprocessor list; graduated authority / policy-as-code; audit trail; open/EU model routing |

**Counter-positioning claims to make explicit** (lower-friction vs incumbents):
- **"No taxonomy to build"** — Enterpret/Chattermill require heavy taxonomy setup and 5,000+ feedback
  items/month minimums; CLARA auto-tags snake_case themes.
- **"No fine-tuning of frontier models"** — adaptable across industries without a bespoke model, which
  also structurally lowers inference COGS (a margin story you can price against).
- **"Sits above your stack"** — integrates with Zendesk/app-store/reviews rather than replacing them.

---

## 5. Messaging & objection handling (DACH-specific)

- **Language:** German-language collateral is effectively required for SMB/procurement buyers; price in
  **EUR** (CHF for Switzerland). A `.de` page with USD pricing signals "not a serious vendor."
- **Tone:** German LinkedIn etiquette ≈ formal email. Opinionated, benchmark-backed thought leadership
  out-pipelines pretty ad campaigns; mass cold DMs get you blocked or GDPR-reported.

| Objection | Response |
|---|---|
| "US tools already do sentiment/themes." | Correct — that's table stakes. CLARA *acts* and *learns*: it governs the fix across product and marketing and remembers what worked. And it's EU-hosted. |
| "Data residency / GDPR?" | Local-first EU processing, Art. 28 DPA + TOMs annex, published subprocessor list, no-training toggle, deletion/right-to-erasure process. One-page datasheet attached to every demo. |
| "Are you AI Act compliant?" | CLARA's audit trail helps *you* (the deployer) discharge *your* Art. 12/50 obligations; text-triage is minimal/limited-risk. (Counsel-reviewed wording only.) |
| "You're a solo founder / small vendor." | Founder-led = direct line to the person who builds it, weekly changes, priority support. As liability scales, CLARA moves to a GmbH/UG counterparty. |
| "We already use Zendesk/Qualtrics." | Keep them. CLARA sits *above* as the cross-source insight + governed-action + learning layer; those are sources, not competitors. |

**Compliance-as-collateral:** publish "EU data residency, governed & auditable, GDPR + EU AI Act aligned,
no frontier-model fine-tuning" on the pricing page — it's a differentiator for DACH buyers, not fine print.

---

## 6. Pricing strategy (summary)

> Full model lives in the pricing/financial doc; this is the GTM-facing summary.

**Model:** hybrid **recurring base + usage on volume-of-signals** (feedback items ingested/enriched/
clustered per month) + number of connected sources. **Seats generous/unlimited** — viewing insights is
never gated. Pure per-seat is declining (IDC: 70% of vendors refactor away from pure per-seat by 2028).
Add an optional **outcome-based** component to Enterprise later (Gartner: 40% of enterprise SaaS to
include outcome elements by 2026).

**Value metric:** volume of signals + connected sources (not seats) — value is in feedback throughput and
governed action, not viewers.

### Recommended tiers (DACH/EU mid-market, annual)

| Tier | Price (monthly, billed annual) | Includes |
|---|---|---|
| **Starter** | **€490–990/mo** | 1–2 sources, ~5,000 signals/mo, core enrichment (sentiment/urgency/snake_case themes), standard clustering, EU residency |
| **Growth** | **€1,500–3,000/mo** | 5+ sources, ~25k–50k signals/mo, governed action + audit log, GDPR/EU-AI-Act reporting, API |
| **Enterprise** | **€5,000–9,000+/mo** (custom) | Unlimited sources, high volume, outcome-grounded learning loop, SSO/SCIM, DPA / on-prem / local model routing, SLA |

**Landing band: €12k–€30k/yr ACV** — mid-market, **above** self-serve. Note **median ≠ entry**: the
figures below mix *median-buyer* and *entry* datapoints; Enterpret's *entry* tier is reportedly
≈$1,000/mo (~$12k/yr) per review-site data (weakly sourced — validate in discovery calls), so CLARA
**matches entry economics** (Starter ~€8.3k/yr) and sells governed outcomes + EU sovereignty, not cheapness:

| Competitor | Est. entry / typical ACV | Source |
|---|---|---|
| Enterpret | ~$36,302 median (range $23k–$98k); entry reportedly ≈$1,000/mo (~$12k/yr) | [vendr.com](https://www.vendr.com/marketplace/enterpret); review-site est. |
| Chattermill | ~$64,000 avg | [chattermill.com](https://chattermill.com/) |
| Unwrap.ai | $24,000/yr floor | [unwrap.ai](https://www.unwrap.ai/post/best-enterpret-alternatives-2026) |
| Thematic | ~$25,000/yr entry | [enterpret.com/guides](https://www.enterpret.com/guides/the-7-best-voice-of-customer-analytics-software-ranked) |
| SentiSum | ~$36k/yr (~$3k/mo) | [sentisum.com](https://www.sentisum.com/) |
| Dovetail | $15–30/user/mo (per-seat pattern) | [zonkafeedback.com](https://www.zonkafeedback.com/blog/chattermill-alternatives-and-competitors) |

**Expansion:** land-and-expand, target **15–25% annual ACV expansion** as feedback volume/sources grow.

**Billing / tax (solo-founder default):** launch on a **Merchant-of-Record — Paddle** (~5% + €0.50/txn):
Paddle is the legal seller and files/remits EU VAT for you, eliminating OSS/registration burden entirely
([paddle.com](https://www.paddle.com/help/sell/tax/how-paddle-handles-vat-on-your-behalf)). Migrate to
**Stripe + Stripe Tax** (2.9% + €0.30 + ~0.5%) past **~€50–100k MRR**, when the ~2× fee saving justifies
insourcing tax ops. For direct EU B2B invoices, apply **reverse-charge** (state both USt-IdNrs,
"Steuerschuldnerschaft des Leistungsempfängers") and file the quarterly **Zusammenfassende Meldung**.

> **This is not tax advice.** Reverse-charge, OSS, and MoR interactions with your Freiberufler/Gewerbe
> status must be confirmed with a Steuerberater.

---

## 7. Channels

**Motion choice: HIGH-TOUCH, founder-led — not low-touch self-serve.** DACH buyers expect a personal
demo, a contract in their language, and GDPR-by-default proof; US-style self-serve growth-hacks fail here.
Reserve a PLG-lite/self-serve Starter tier for *after* you have references.

| Channel | How | Expected yield / notes |
|---|---|---|
| **Warm network + investor/portfolio intros** | Direct asks; one-hop referrals | **40–60% of design-partner yield** — the highest-converting channel |
| **German LinkedIn thought leadership** | Post **3×/week**, opinionated, benchmark-backed (thesis + Henkel/Lieferando/Trade Republic results, EU AI Act, VoC governance) | Primary top-of-funnel in DACH; one thoughtful German post > 200 cold DMs |
| **Targeted LinkedIn outreach (ONE ICP)** | Personalised, referencing a specific post/talk; 5–7 touches / 14 days | 10–20% yield. **No mass cold email/DMs** (blocked, GDPR-reported) |
| **Founder communities** | ARRtist SUMMIT (Berlin, invite-only B2B SaaS founders + investors); CX/product/VoC practitioner communities; Berlin science-startup ecosystem | Network + investor surface; SaaS-scaling exchange |
| **Integration/partner surface** | 1–2 lightweight integrations where feedback lives (app-store/review sources, Zendesk/Freshdesk, product analytics) | Lowers pilot friction; co-marketing/referral surface |
| **Non-dilutive grants (runway, not revenue)** | Fund the slow trust-building phase | See §7.1 |

### 7.1 Grant funding to extend runway (parallel to GTM)

| Grant | Amount | Fit / condition |
|---|---|---|
| **EXIST Gründungsstipendium** | €2,500–3,000/mo × 12 mo + up to €10k material + €150/child/mo | Year-round; needs university affiliation — approach the thesis university's EXIST/startup office ([exist.de](https://exist.de/en/programm/gruendungsstipendium/)) |
| **IBB GründungsBONUS Plus** | Up to €50,000 (50% of costs), up to 2 yrs | Berlin, tech/digital model, **start-up < 18 months old**, German application ([ibb.de](https://www.ibb.de/en/foerderprogramme/gruendungsbonus-plus.html)) |
| **IBB Coaching BONUS** | Subsidised coaching (coach ≤ €1,000/day) | Cheap GTM/sales coaching |
| **EIC Accelerator** (later) | Grant < €2.5M + equity €0.5–10M | Deep-tech; after pilots/traction. 2026 cut-offs incl. **8 Jul, 2 Sep, 4 Nov** ([eic.ec.europa.eu](https://eic.ec.europa.eu/eic-funding-opportunities/eic-accelerator_en)) |
| **Gründungszuschuss** | ALG I + €300/mo | **Likely N/A** — requires drawing ALG I (you don't). Verify. |

---

## 8. Sales motion

### 8.1 Design-partner / paid-pilot program (the core motion)

Recruit **7–10** (range 5–15; beyond ~15 it degrades into a mailing list as you lose weekly synchronous
time). Two tiers:

- **Design partners** — deep weekly co-builders, discounted/free, success tied to **one metric**.
- **Paid pilots** — small fee or discounted list price, production-scope, **60–90 days**, success tied to a
  business outcome + adoption.

**Pitch template (lead with the WIN, not the product):**
> *"I'm recruiting 3 design partners to run a 60–90 day pilot to reduce {metric} by {target}. You get a
> focused build on your workflow, weekly changes, and priority support. In return: 30 min/week + a
> testimonial if we hit the target."*

Each pilot defines **one success metric tied to a measured business outcome** — which double-serves as (a)
the case study and (b) fuel for CLARA's outcome-learning loop.

### 8.2 Compliance sales kit (table-stakes to close DACH deals)

Assemble once, attach to every demo — doubles as sales collateral:

- [ ] EU-hosting statement + data-residency & **subprocessor list** (general-authorization / right-to-object)
- [ ] **Art. 28 DPA/AVV** template + **TOMs annex**
- [ ] Deletion / right-to-erasure process description
- [ ] **AI Act & GDPR one-page datasheet** (residency, DPA, subprocessors, no-training toggle, audit log)
- [ ] **DPIA-support pack** + "CLARA processing facts" sheet (removes enterprise-procurement friction)
- [ ] B2B **AGB/Terms** with DPA + TOMs as annexes; **Impressum** citing **§5 DDG** (not TMG) with USt-IdNr

### 8.3 Sales-cycle & CAC expectations (plan runway accordingly)

- **DACH sales cycle:** 6–9 months before DACH revenue covers DACH costs (not 3).
- **CAC:** DACH founder-led ~**€200–700**; global B2B SaaS median ~$1,200. Payback typically **9–24 months**.
- This slow trust-building phase is exactly what the non-dilutive grants (§7.1) are buying.

### 8.4 Funnel

Thought leadership + warm intros → design-partner pitch → 60–90 day pilot (one metric) → outcome proven →
named reference/testimonial → shorten next cohort's cycle → land-and-expand (volume/sources) → Enterprise
outcome-based upsell.

---

## 9. 90-day GTM plan (checklist)

**Weeks 1–2 — Foundations (gate + fuel, in parallel)**
- [ ] **BUSINESS-SETUP GATE:** book a Steuerberater; get a written Freiberufler-vs-Gewerbe assessment
      **before invoicing any paid pilot**. Assume **Gewerbe**; ring-fence SaaS revenue to avoid *Abfärbung*
      tainting freelance income; decide on regular-VAT opt-out. *(See doc 01.)*
- [ ] Contact thesis university's EXIST office; email IBB about GründungsBONUS Plus (confirm <18-month window)
- [ ] Lock the **beachhead ICP** (recommend #3 fintech/insurance for WTP; #1 SaaS for volume)
- [ ] German-language one-pager: the WIN metric, EU-residency/GDPR/AI-Act line, EUR pricing, 60–90 day pilot offer

**Weeks 2–4 — Pipeline**
- [ ] Build a 40–60 warm + one-hop target list
- [ ] Founder-led outbound (5–7 touches / 14 days: short German email + warm intro + one LinkedIn message)
- [ ] Stand up the compliance sales kit (§8.2)

**Weeks 3–8 — Land design partners**
- [ ] Sign **3–5** design partners / paid pilots (keep total ≤10), each with **one** outcome metric
- [ ] Ship the pricing page with the compliance line and EUR tiers; wire **Paddle (MoR)** billing

**Weeks 2–12 — Content engine**
- [ ] German LinkedIn **3×/week**; publish 1–2 anonymised benchmark case studies (thesis + validation data)

**Months 2–3 — Integrations & references**
- [ ] Ship 1–2 lightweight integrations (app-store/reviews, Zendesk/Freshdesk, product analytics)
- [ ] Convert successful pilots into **named references**; pursue **ISO 27001 / SOC 2** early (DACH shortlist filter)

**Months 6–12 — Scale capital**
- [ ] Prepare EIC Accelerator application (post-traction); attend ARRtist SUMMIT

---

## 10. KPIs to track

| Metric | Target | Why |
|---|---|---|
| Design partners signed | 3–5 by wk 8; ≤10 total | Core motion health |
| Pilot → paid conversion | ≥50% | Product-market signal |
| NRR (net revenue retention) | **>100%** (best-in-class 111%+) | Expansion > churn; "matters more than MRR" |
| CAC payback | **<12 months** | Beat the 15–20mo norm |
| LTV:CAC | **>3:1** | Efficiency |
| Gross margin (net of inference) | **≥70%** | Hold vs AI-native 50–60% compression |
| LLM inference COGS | **<10% of revenue** | Protect margin; CLARA's no-fine-tuning/local-first structurally helps |
| Logo + revenue churn | Low | DACH B2B avg ~3.5%/yr |

Track **NRR and CAC payback over vanity MRR.** Instrument LLM inference as an explicit COGS line from day one.

---

## 11. Risks & mitigations

| Risk | Mitigation |
|---|---|
| **Freiberufler/Gewerbe misclassification + *Abfärbung*** (all income reclassified as trade) | Steuerberater ruling **before first SaaS invoice**; separate bookkeeping/entity; assume Gewerbe. **GTM gate.** |
| Enterpret now claims "close the loop" | Lead with the **mechanism** it lacks: governed cross-functional closure + learning memory + EU self-host (§2.2) |
| "Solo founder" credibility in enterprise | Founder-led as a feature; move to UG/GmbH counterparty as liability/PII scales; ISO 27001/SOC 2 early |
| Over-claiming AI Act compliance | Counsel-review all compliance copy; frame as "helps the deployer meet *their* obligations"; text-triage = limited-risk |
| Long DACH cycles burn runway | Non-dilutive grants (EXIST/IBB) + maintain 12–18 mo runway; never <6 months |
| AI-native margin compression | Meter inference per 1,000 signals; tier volume caps; market the no-fine-tuning cost advantage |
| Positioning drift to "compliance tool" | Enforce the pillar hierarchy: loop closure headline, governance as the layer (§1.2) |

---

## 12. Sources

Positioning/competitive: internal `../business/STRATEGY_SYNTHESIS.md`; [vendr.com/marketplace/enterpret](https://www.vendr.com/marketplace/enterpret);
[chattermill.com](https://chattermill.com/); [unwrap.ai](https://www.unwrap.ai/post/best-enterpret-alternatives-2026);
[enterpret.com/guides](https://www.enterpret.com/guides/the-7-best-voice-of-customer-analytics-software-ranked); [sentisum.com](https://www.sentisum.com/);
[compound.law (DACH residency)](https://compound.law/en-DE/compliance/ai-customer-service-gdpr/).
Regulatory: [EU AI Act Art. 50 / Digital Omnibus](https://compliancehub.wiki/eu-ai-act-article-50-transparency-digital-omnibus-2026/);
[AI Act timeline](https://artificialintelligenceact.eu/implementation-timeline/); [Impressum §5 DDG](https://www.it-recht-kanzlei.de/tmg-ttdsg-ausser-kraft-impressum-datenschutz.html).
Pricing/billing: [Paddle VAT/MoR](https://www.paddle.com/help/sell/tax/how-paddle-handles-vat-on-your-behalf);
[Stripe vs Paddle vs Lemon Squeezy](https://www.globalsolo.global/blog/stripe-vs-paddle-vs-lemon-squeezy-2026);
[ACV benchmarks](https://optif.ai/learn/questions/b2b-saas-acv-benchmark/).
Channels/grants: [EXIST](https://exist.de/en/programm/gruendungsstipendium/); [IBB GründungsBONUS Plus](https://www.ibb.de/en/foerderprogramme/gruendungsbonus-plus.html);
[EIC Accelerator](https://eic.ec.europa.eu/eic-funding-opportunities/eic-accelerator_en); [DACH SaaS launch playbook](https://lishchuk.com/blog/b2b-saas-launch-playbook-dach-2026.html);
[design-partner motion](https://www.unusual.vc/field-guide/build-a-sales-motion-with-design-partners-for-a-b2b-product/); [ARRtist SUMMIT](https://www.arrtist.net/).
Metrics: [SaaS metrics 2026](https://beancount.io/blog/2026/05/10/saas-metrics-founders-must-track-2026-ltv-cac-nrr-churn-cac-payback-benchmarks-guide);
[AI-native margins](https://www.getmonetizely.com/articles/the-economics-of-ai-first-b2b-saas-in-2026-margins-pricing-models-and-profitability).

> **Reminder — not legal or tax advice.** Confirm the Gewerbe classification, EU AI Act risk-tier, and any
> compliance marketing claim with a Steuerberater and a Fachanwalt für IT-Recht/Datenschutz before relying
> on them.
