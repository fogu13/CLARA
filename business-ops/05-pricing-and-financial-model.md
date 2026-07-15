# 05 — Pricing & Financial Model

**Summary.** CLARA should sell on a **hybrid pricing model** — a recurring per-tier base plus usage metered on *volume of feedback signals processed* — packaged into three tiers (Starter ≈ €490–990/mo, Growth ≈ €1,500–3,000/mo, Enterprise ≈ €5,000–9,000+/mo, all billed annually). This lands the flagship **Growth** tier around **€24k/yr ACV**, comfortably inside the recommended DACH mid-market band of **€12k–€30k/yr** — at rough parity with the closest competitor's entry point (Enterpret's entry tier is ≈$1,000/mo ≈ $12k/yr per weakly-sourced review-site estimates, to validate in discovery; its *median buyer* still pays ~$36k and Chattermill averages ~$64k). CLARA therefore does not sell on cheapness: it matches entry economics and wins on **governed outcomes + EU sovereignty**, which justify the Growth/Enterprise premium. For billing, launch on a **Merchant-of-Record (Paddle)** so a solo founder avoids all EU-VAT registration, OSS filing and reverse-charge admin, then migrate to **Stripe + Stripe Tax** past ~€50–100k MRR to recover margin. Because pricing is capped by signal volume, **LLM inference stays well under 10% of revenue**, protecting a **70%+ gross margin** even though AI-native SaaS margins are compressing toward 50–60% industry-wide. The runway model below shows a solo founder reaching monthly cash-flow break-even around **month 6** on a design-partner-led ramp, with an EXIST stipend and annual-prepay contracts turning a thin bootstrap trough into a safe 12–18 month runway.

> **This is not legal, tax or accounting advice.** Figures for German tax, VAT, e-invoicing and legal status are research summaries and change frequently — **confirm every number and the Gewerbe-vs-Freiberufler classification with a Steuerberater before you invoice your first SaaS customer.** The Abfärbung (infection) rule means mixing productised-SaaS revenue into your existing Freiberufler income without clean separation can retroactively make *all* your income trade-taxed. See `../business-ops/01-*` legal/tax doc (or your Steuerberater) for the full treatment.

---

## Assumptions

- **Product:** CLARA = EU-sovereign Voice-of-Customer / feedback-triage engine. The billable *value metric* is the **volume of feedback signals ingested → enriched → clustered → looped into governed insights**, not viewer seats.
- **Founder:** solo technical founder, Berlin, currently Freiberufler with a USt-IdNr. **Working assumption: productised SaaS = Gewerbe** (register the trade; ring-fence from freelance income). Verify with a Steuerberater.
- **Customer:** DACH/EU **B2B**, VAT-registered businesses. Primary ICPs: (1) DACH mid-market B2B SaaS product/CX teams, (2) EU e-commerce/marketplaces, (3) regulated DACH fintech/insurance (highest willingness-to-pay).
- **VAT posture:** waive the §19 Kleinunternehmer exemption and register for **regular VAT** — B2B buyers are VAT-neutral and you reclaim input VAT on cloud/AI spend. B2B EU sales run under **reverse charge**; MoR abstracts this at launch.
- **Cost architecture:** CLARA is **local-first / no frontier-model fine-tuning**, using smaller/open-weight models. This structurally lowers inference COGS — a quantified margin advantage, not just a compliance story.
- **All € prices are net (ex-VAT)** and are **strategic starting hypotheses to validate via willingness-to-pay interviews**, not empirically derived quotes. Competitor prices are third-party estimates (Vendr/G2/review sites) because incumbents publish little pricing; Enterpret's ≈$1,000/mo entry tier in particular is weakly-sourced review-site data — validate it against real quotes in discovery calls.

---

## 1. Pricing model & tiers

### 1.1 Why hybrid (base + usage), not per-seat

Pure per-seat pricing is in structural decline — IDC projects 70% of vendors move off pure per-seat by 2028, and 37% of surveyed companies now run hybrid subscription+usage as their primary model, which correlates with ~30% faster growth ([nxcode 2026 guide](https://www.nxcode.io/resources/news/saas-pricing-strategy-guide-2026); [userpilot](https://userpilot.com/blog/saas-pricing-models/)). For CLARA:

- **Value metric = feedback signals/month + connected sources.** Value scales with throughput of feedback and closed loops, not with how many people log in to *read* insights.
- **Seats are generous/unlimited** — never gate the act of viewing an insight; that kills adoption and NRR.
- **Tiered packaging sits on top** of the hybrid model (tiering is packaging, not a pricing model).
- **Outcome-based component is a later add-on** for Enterprise (Gartner: 40% of enterprise SaaS to include outcome elements by 2026; +31% retention) — fits CLARA's outcome-grounded self-improving loop once it can *measure* the business outcome. Do not ship it at launch; it complicates billing and forecasting.

### 1.2 Recommended tiers (DACH/EU mid-market)

| | **Starter** | **Growth** *(flagship land)* | **Enterprise** |
|---|---|---|---|
| **Price (annual billing)** | **€490–990/mo** (anchor **€690/mo**, ~€8.3k/yr) | **€1,500–3,000/mo** (anchor **€1,990/mo**, ~€24k/yr) | **€5,000–9,000+/mo**, custom (from ~€60k/yr) |
| **Feedback signals / mo** | up to ~5,000 | up to ~50,000 | high-volume / unlimited |
| **Connected sources** | 1–2 | 5+ | unlimited |
| **Enrichment** (sentiment, urgency, snake_case themes) | ✓ | ✓ | ✓ |
| **Clustering & governed insight synthesis** | standard | ✓ + audit log | ✓ + full audit trail |
| **Automated loop closure (Signal→Insight→Action→Learning)** | basic | ✓ | ✓ outcome-grounded self-improving loop |
| **EU data residency** | ✓ | ✓ | ✓ + on-prem / local deployment option |
| **GDPR / EU AI Act reporting, API** | — | ✓ | ✓ + SSO, DPA, SLA |
| **Seats** | generous | unlimited | unlimited |
| **Overage** | per 1,000 signals | per 1,000 signals | negotiated |
| **Target ICP** | entry / land, smaller teams | mid-market SaaS & e-commerce | regulated fintech/insurance (highest WTP) |

**Overage pricing:** meter signals above the cap at a per-1,000 rate that stays a healthy multiple of inference cost (see §3) — e.g. **€8–€15 per 1,000 signals**. This makes overage margin-accretive and nudges heavy users to upgrade a tier.

**Annual-prepay incentive:** offer **~2 months free (≈17% discount) for annual upfront**. For a solo founder this is the single biggest cash-flow lever (see §5) — it front-loads a full year of cash and slashes involuntary churn.

### 1.3 Pricing rationale & competitive anchoring

- **Match the closest competitor's entry economics, own the governance premium.** Enterpret's *entry* tier is reportedly **≈$1,000/mo (~$12k/yr)** per review-site data — weakly sourced, so treat it as an estimate and **validate it in discovery calls** ("what were you quoted?"). Its *median buyer* still lands at ~$36.3k/yr (est. contract range $23k–$98k/yr — [Vendr](https://www.vendr.com/marketplace/enterpret)) — **median ≠ entry**: the Vendr figures describe what a typical buyer ends up spending, not the cheapest way in. Elsewhere: Chattermill avg contract ~$64k/yr ([chattermill.com](https://chattermill.com/)); Thematic entry ~$25k/yr; Unwrap floor $24k/yr ([unwrap.ai](https://www.unwrap.ai/post/best-enterpret-alternatives-2026)). So CLARA cannot claim to "undercut the incumbents" at entry — **Starter (~€8.3k/yr) matches the ~$12k/yr competitor entry**, and the sale is not cheapness: **EU-sovereignty + audit-ready governance + outcome contracts + no taxonomy to build** are what justify **Growth ~€24k/yr** and the **Enterprise €60k+/yr** premium for regulated buyers.
- **Land in the €12k–€30k mid-market band** (mid-market B2B SaaS ACV averages ~$40k, range $15k–$50k — [optif.ai](https://optif.ai/learn/questions/b2b-saas-acv-benchmark/)). Starter is deliberately *below* the band as a low-friction land/expansion foothold, not the target ACV.
- **Land-and-expand:** target **15–25% annual ACV expansion** as feedback volume and connected sources grow — the volume value-metric expands revenue automatically without a re-sell.
- **Do not compete as a helpdesk.** Zendesk owns ticket triage with uncapped per-resolution billing ([richpanel](https://www.richpanel.com/learn/zendesk-pricing)); CLARA is the cross-source *insight & governance layer above* Zendesk/Intercom/app-store reviews.
- **Price in EUR, VAT-clear.** USD pricing on a `.de` page signals "not a serious vendor" to DACH procurement.

---

## 2. EU-VAT-compliant billing

### 2.1 The core decision: Merchant of Record vs self-managed tax

| | **Merchant of Record — Paddle** *(launch default)* | **Stripe + Stripe Tax** *(migrate at scale)* |
|---|---|---|
| **Who is the legal seller** | Paddle (they sell to your customer) | **You** |
| **Who files/remits EU VAT & OSS** | **Paddle — fully handled** | **You** (Stripe Tax *calculates* but does **not** file) |
| **VAT registration burden** | none | you register + file OSS / ZM yourself |
| **Reverse-charge / VAT-ID validation** | handled | Stripe Tax validates EU B2B IDs, applies reverse charge; you issue compliant invoice + keep evidence |
| **Headline cost** | **~5% + €0.50 / txn** | **2.9% + €0.30** + Stripe Tax **~0.5%/txn** where registered |
| **Chargebacks** | Paddle absorbs most liability | your liability |
| **Best when** | solo founder, cross-border EU B2B, **no finance team** | past **~€50–100k MRR**, when ~2× lower processing cost outweighs insourced tax ops |

Sources: [Stripe vs Paddle vs Lemon Squeezy 2026](https://www.globalsolo.global/blog/stripe-vs-paddle-vs-lemon-squeezy-2026); [Paddle VAT handling](https://www.paddle.com/help/sell/tax/how-paddle-handles-vat-on-your-behalf); [Stripe Tax EU](https://docs.stripe.com/tax/supported-countries/european-union).

**Recommendation:** **Launch on Paddle.** For a one-person team selling cross-border EU B2B, a MoR replaces an accountant + multi-country VAT filing + OSS returns for a predictable ~5% fee — it buys back time and eliminates the single biggest operational tax risk. Prefer Paddle over Lemon Squeezy (Lemon Squeezy stacks +1.5% international, +0.5% subscription, +1% non-US payout and passes chargebacks to you). Revisit Stripe + Stripe Tax only once MRR and margin make insourcing worth it.

### 2.2 If/when you self-manage (Stripe path) — the German B2B checklist

- **EU B2B reverse charge:** invoice **net, 0% German VAT**, state **"Steuerschuldnerschaft des Leistungsempfängers / Reverse charge"** and show **both** parties' USt-IdNr. Validate every customer VAT ID via **VIES**.
- **Quarterly Zusammenfassende Meldung (ZM):** file the recapitulative statement listing EU B2B sales.
- **B2C EU digital services:** reverse charge does **not** apply — charge the customer's local VAT rate and remit via the **OSS** portal.
- **Invoice content (§14 UStG):** supplier + recipient name/address, your Steuernummer *or* USt-IdNr, sequential invoice number, issue date, scope/type of service, time of supply, net amount + VAT rate/amount (or exemption note). Invoices ≤ €250 gross are simplified Kleinbetragsrechnungen ([§14 UStG](https://www.gesetze-im-internet.de/ustg_1980/__14.html)).

### 2.3 E-invoicing deadlines (B2B, structured XRechnung/ZUGFeRD)

| Obligation | Who | Deadline |
|---|---|---|
| **Receive & archive** structured e-invoices (GoBD) | every German B2B incl. you | **already in force since 1 Jan 2025** |
| **Send** e-invoices | businesses > €800k prior-year turnover | from **1 Jan 2027** |
| **Send** e-invoices | businesses ≤ €800k (**you**) | from **1 Jan 2028** (paper/PDF allowed until 31 Dec 2027 with consent) |
| Exempt from *issuing* | invoices ≤ €250, Kleinunternehmer | (but must still be able to *receive*) |

Source: [BMF e-Rechnung FAQ](https://www.bundesfinanzministerium.de/Content/DE/FAQ/e-rechnung.html); [rickert.law](https://rickert.law/e-rechnung-b2b-2027/). **Action now:** adopt invoicing software (or rely on Paddle) that can receive/archive XRechnung/ZUGFeRD — this is already mandatory. Sending structured e-invoices early is a low-cost win that reinforces CLARA's own "governed/auditable" positioning.

### 2.4 Kleinunternehmer note

New permanent §19 thresholds (unchanged 2026): **≤ €25,000 prior year AND ≤ €100,000 current year (hard limit)** ([IHK Stuttgart](https://www.ihk.de/stuttgart/fuer-unternehmen/recht-und-steuern/steuerrecht/umsatzsteuer-national/kleinunternehmerregelung-in-der-umsatzsteuer-1843632)). **For B2B SaaS, waive it and register for regular VAT** — you gain input-VAT recovery and a clean USt-IdNr for reverse charge; Kleinunternehmer mainly helps B2C.

---

## 3. Unit economics & gross margin (with LLM inference in COGS)

### 3.1 Why inference must be a first-class COGS line

AI-native gross margins are compressing toward **50–60%** vs classic SaaS 75%+ (ICONIQ Jan 2026: average AI-product gross margin **52%**; inference alone ~**23% of COGS**; public SaaS disclose inference at ~**4–9% of revenue**) ([Monetizely](https://www.getmonetizely.com/articles/the-economics-of-ai-first-b2b-saas-in-2026-margins-pricing-models-and-profitability); [The SaaS CFO](https://www.thesaascfo.com/your-ai-feature-is-quietly-destroying-your-gross-margin/)). **Rule: model inference as cost per 1,000 signals, cap it with tier volume limits, and keep it under 10% of revenue to hold 70%+ gross margin.** CLARA's signal-cap pricing structurally enforces this.

### 3.2 Inference cost model (illustrative — validate against your live model choice)

Assume one signal ≈ one feedback item, effective ~1,500 tokens processed across enrichment + share of clustering + insight synthesis, on a small/open-weight or cheap model.

- **Blended inference cost: ~€0.30–€1.50 per 1,000 signals** (lower bound = self-hosted/open-weight amortized; upper bound = cheap frontier API). Because CLARA does **no frontier fine-tuning** and runs **local-first**, target the low end and **quantify it in the pitch**.

| Tier | Price/mo | Signal cap | Inference @ €1.00/1k (worst realistic) | **Inference as % of revenue** |
|---|---|---|---|---|
| Starter | €690 | 5,000 | €5 | **0.7%** |
| Growth | €1,990 | 50,000 | €50 | **2.5%** |
| Enterprise | €5,000+ | 200,000+ | €200+ | **~4%** |

Even at a pessimistic **€3/1,000**, Growth inference is €150/mo = **7.5% of revenue** — still under the 10% guardrail. **The cap does the work.**

### 3.3 Worked gross-margin example (Growth tier, €1,990/mo, fully utilized)

| Line | Monthly | Notes |
|---|---|---|
| Revenue (net) | €1,990 | |
| − LLM inference (COGS) | −€50 | 50k signals @ €1/1k |
| − Hosting/infra allocation | −€40 | EU-hosted |
| − Support/success (variable) | −€30 | light-touch at this tier |
| **Gross profit (excl. payment fees)** | **€1,870** | **~94% gross margin** |
| − Paddle MoR fee (5% + €0.50) | −€100 | treat as distribution/payment cost |
| **Contribution after payment fees** | **€1,770** | **~89%** |

Whether MoR/payment fees sit in COGS or below the line, CLARA clears the **70%+ gross-margin** target with wide headroom. The margin risk is *not* inference at these price points — it is **heavy overage without a cap** (avoid) and **support cost drift on Enterprise** (price it in).

### 3.4 CAC, LTV and payback (targets)

- **CAC** (2026 median B2B SaaS ~$1,200/customer, up 60% in 5 yrs) — a founder-led, warm-network design-partner motion should keep CAC *below* median early. DACH benchmark CAC €200–700 with 9–24 month payback ([lishchuk](https://lishchuk.com/blog/b2b-saas-launch-playbook-dach-2026.html)).
- **LTV:CAC > 3:1**, **CAC payback < 12 months** ([beancount](https://beancount.io/blog/2026/05/10/saas-metrics-founders-must-track-2026-ltv-cac-nrr-churn-cac-payback-benchmarks-guide)).
- **Example LTV:** Growth at €24k/yr, ~90% gross margin, ~3.5%/yr logo churn → multi-year LTV comfortably >€60k → LTV:CAC far above 3:1 if CAC stays in the low thousands. Guard it by prioritizing referenceable design partners over paid acquisition.

---

## 4. SaaS metrics to track

Track a tight weekly dashboard — **NRR and CAC payback matter more than raw MRR**.

| Metric | Target / benchmark | Why it matters for CLARA |
|---|---|---|
| **MRR / ARR** | grow steadily | primary growth signal |
| **NRR (net revenue retention)** | **> 100%** (2026 median ~101%, top 111%+, best-in-class 130%+) | signal-volume value metric drives expansion; the north star |
| **CAC payback** | **< 12 months** (typical 15–20mo — beat it) | founder-led motion should be capital-efficient |
| **LTV:CAC** | **> 3:1** | sustainability of the go-to-market |
| **Gross margin (net of inference)** | **> 70%** | AI-native margin discipline; CLARA's structural edge |
| **Inference cost / revenue** | **< 10%** | the AI-specific margin guardrail (§3) |
| **Logo & revenue churn** | logo < ~3.5%/yr; keep revenue churn negative via expansion | small base = each logo matters |
| **Rule of 40 / burn multiple** | efficiency > growth-at-all-costs for a bootstrapper | solo micro-SaaS avg ~45% profit margin, top quartile 80%+ |
| **Signals processed / active source** | usage-health leading indicator | predicts expansion and inference COGS |

Benchmarks: [averi.ai 2026 metrics](https://www.averi.ai/blog/15-essential-saas-metrics-every-founder-must-track-in-2026-(with-benchmarks)); [beancount](https://beancount.io/blog/2026/05/10/saas-metrics-founders-must-track-2026-ltv-cac-nrr-churn-cac-payback-benchmarks-guide).

---

## 5. Solo-founder financial & runway model

### 5.1 Assumptions

- **Starting cash:** €25,000 personal savings.
- **Fixed monthly burn ≈ €3,450:** personal living (Berlin) €2,800 + tooling/software €300 + Steuerberater/accounting €200 + buffer (IHK, insurance, bank) €150. Lean stack (Paddle + PostHog EU + Plausible + Crisp + Documenso) runs ~€150–500/mo ([freemius](https://freemius.com/blog/micro-saas-tech-stack/)).
- **Revenue:** design-partner-led ramp — 3 free design partners in M1–M3, converting to paid **Growth (€1,990/mo)** from M4, reaching ~5 paying customers by M12. Net revenue ≈ 90% of MRR after inference + payment fees.
- **Taxes:** VAT is a pass-through (and MoR-handled at launch). Reserve **~25–30% of profit** for income tax; **Gewerbesteuer is largely neutralized** at small profit by the €24,500 allowance + §35 EStG credit (4× Messbetrag), leaving only a small residual at Berlin's 410% Hebesatz ([§35 EStG](https://www.gesetze-im-internet.de/estg/__35.html)).

### 5.2 Scenario A — Bootstrap only (no grant), monthly cash balance

| Month | MRR | Net rev (~0.9×) | − Burn | **End cash** |
|---|---|---|---|---|
| M1 | €0 | €0 | €3,450 | €21,550 |
| M2 | €0 | €0 | €3,450 | €18,100 |
| M3 | €0 | €0 | €3,450 | €14,650 |
| M4 | €1,990 | €1,791 | €3,450 | €12,991 |
| M5 | €1,990 | €1,791 | €3,450 | **€11,332** *(trough)* |
| M6 | €3,980 | €3,582 | €3,450 | €11,464 |
| M7 | €3,980 | €3,582 | €3,450 | €11,596 |
| M8 | €5,970 | €5,373 | €3,450 | €13,519 |
| M9 | €5,970 | €5,373 | €3,450 | €15,442 |
| M10 | €7,960 | €7,164 | €3,450 | €19,156 |
| M11 | €7,960 | €7,164 | €3,450 | €22,870 |
| M12 | €9,950 | €8,955 | €3,450 | €28,375 |

**Read:** monthly cash-flow break-even around **M6** (net revenue ≈ fixed burn); cash troughs at **~€11,300 in M5** — survivable but thin (~3 months of buffer at the low point). This is exactly the phase grants and annual prepay are meant to cover.

### 5.3 Scenario B — With EXIST stipend (recommended)

Add **€2,500/mo (EXIST Gründungsstipendium, 12 months + up to €10k material)** to every month ([exist.de](https://exist.de/en/programm/gruendungsstipendium/); thesis origin qualifies — approach the university's EXIST office). The trough never drops below the €25k start, break-even effectively arrives immediately, and year-end cash is ~€58k. Also pursue **Berlin IBB GründungsBONUS Plus** (up to **€50k / 50% of costs**, start-up < 18 months — [ibb.de](https://www.ibb.de/en/foerderprogramme/gruendungsbonus-plus.html)).

### 5.4 Annual-prepay lever

The models above recognize revenue monthly. In reality, **annual upfront billing front-loads cash dramatically**: 5 Growth customers on annual contracts at ~€23,880/yr = **~€119k cash collected in year one**, even as recognized MRR ramps. Push annual prepay (2 months free) from the first paid customer — it is the cheapest capital a bootstrapper can raise.

### 5.5 Runway rules of thumb

- **Runway = cash ÷ (monthly burn − net revenue contribution).** Never operate below **6 months** runway (impairs decision-making).
- **Safe full-time transition:** 12–18 months runway **plus** €3–5k MRR already validated ([softwareseni](https://www.softwareseni.com/solo-founder-saas-metrics-from-0-to-10k-mrr-in-6-months-with-realistic-timelines/)). CLARA reaches ~€6k MRR by M9 in Scenario A — combine with EXIST to cross the transition threshold safely.
- **Prioritize profitability over growth:** solo micro-SaaS averages ~45% profit margin, top quartile 80%+ by staying lean.

---

## 6. Fast-mover decision checklist

- [ ] **Book a Steuerberater this month** — resolve Gewerbe-vs-Freiberufler *before the first SaaS invoice*; ring-fence SaaS from freelance income to avoid Abfärbung. **Highest-leverage action.**
- [ ] **File the Gewerbeanmeldung** (Berlin Bezirk via [berlin.de/ea](https://www.berlin.de/ea/), ~€15 online); assume Gewerbe for productised CLARA.
- [ ] **Waive §19, register for regular VAT** for the SaaS activity.
- [ ] **Set up Paddle (MoR)** as the launch billing stack — eliminates EU-VAT/OSS/ZM admin day one.
- [ ] **Ship 3 tiers** — Starter €690, Growth €1,990 (flagship), Enterprise €5,000+ custom — with signal-volume caps and **annual-prepay (2 months free)**.
- [ ] **Instrument inference cost per 1,000 signals** from day one; enforce caps; keep inference < 10% of revenue.
- [ ] **Stand up the weekly metrics dashboard** (MRR, NRR, CAC payback, gross margin net of inference, churn).
- [ ] **Apply to EXIST** (via thesis university) and **IBB GründungsBONUS Plus** in parallel with landing the first 3–5 design partners.
- [ ] **Validate the € price points** with 5–10 DACH willingness-to-pay interviews before hard-coding them.
- [ ] **Plan the Stripe + Stripe Tax migration** trigger at ~€50–100k MRR.

---

### Sources (key figures & deadlines)

- Pricing model trends: <https://www.nxcode.io/resources/news/saas-pricing-strategy-guide-2026>, <https://userpilot.com/blog/saas-pricing-models/>
- Competitor pricing anchors: <https://www.vendr.com/marketplace/enterpret> (median-buyer/contract-range figures), <https://chattermill.com/>, <https://www.unwrap.ai/post/best-enterpret-alternatives-2026>, <https://optif.ai/learn/questions/b2b-saas-acv-benchmark/>. Enterpret's ≈$1,000/mo entry tier is a review-site estimate (weakly sourced) — validate in discovery calls.
- Billing / MoR vs Stripe: <https://www.globalsolo.global/blog/stripe-vs-paddle-vs-lemon-squeezy-2026>, <https://www.paddle.com/help/sell/tax/how-paddle-handles-vat-on-your-behalf>, <https://docs.stripe.com/tax/supported-countries/european-union>
- VAT / reverse charge / invoices: <https://www.gesetze-im-internet.de/ustg_1980/__14.html>, <https://www.ihk.de/stuttgart/fuer-unternehmen/recht-und-steuern/steuerrecht/umsatzsteuer-national/kleinunternehmerregelung-in-der-umsatzsteuer-1843632>
- E-invoicing deadlines: <https://www.bundesfinanzministerium.de/Content/DE/FAQ/e-rechnung.html>, <https://rickert.law/e-rechnung-b2b-2027/>
- Gewerbesteuer / §35 credit: <https://www.gesetze-im-internet.de/estg/__35.html>, <https://www.fuer-gruender.de/wissen/unternehmen-gruenden/finanzen/steuern/gewerbesteuer-rechner/>
- AI margins / inference COGS: <https://www.getmonetizely.com/articles/the-economics-of-ai-first-b2b-saas-in-2026-margins-pricing-models-and-profitability>, <https://www.thesaascfo.com/your-ai-feature-is-quietly-destroying-your-gross-margin/>
- SaaS metrics benchmarks: <https://beancount.io/blog/2026/05/10/saas-metrics-founders-must-track-2026-ltv-cac-nrr-churn-cac-payback-benchmarks-guide>, <https://www.averi.ai/blog/15-essential-saas-metrics-every-founder-must-track-in-2026-(with-benchmarks)>
- Runway / solo model & stack: <https://www.softwareseni.com/solo-founder-saas-metrics-from-0-to-10k-mrr-in-6-months-with-realistic-timelines/>, <https://freemius.com/blog/micro-saas-tech-stack/>
- Grants: <https://exist.de/en/programm/gruendungsstipendium/>, <https://www.ibb.de/en/foerderprogramme/gruendungsbonus-plus.html>

*Prices and tax/legal figures are directional and time-sensitive (research current as of mid-2026). Validate € price points via WTP interviews and all tax/legal points with a Steuerberater/lawyer before relying on them.*
