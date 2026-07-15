# CLARA — Investor FAQ & Objection Handling

**Purpose.** The hard questions a sharp pre-seed investor will ask, with honest, specific answers. No hand-waving. Where something is a hypothesis, it is labelled as one; where it is validated, the proof is named.

**What CLARA is, in one line.** The EU-sovereign, governed, self-improving customer-feedback (Voice-of-Customer) engine: it ingests raw feedback (app-store, reviews, support, surveys), enriches it (sentiment, urgency, snake_case theme tags), clusters it into themes, and synthesises **governed, auditable, action-ready insights** — then closes an outcome-grounded loop (Signal → Insight → Action → measured Outcome → Learning). Adaptable across industries **without fine-tuning frontier models**.

**Status.** Product exists and is validated on real data across three industries. Solo technical founder, Berlin. Bootstrapped to a working, validated product. A pre-seed raise is optional and opportunistic — to accelerate GTM, not to finish the product.

> This document contains forward-looking hypotheses (revenue ramp, margins at scale) explicitly labelled as such. It is not a forecast or a guarantee of returns.

---

## 1. Why now?

Three forces converged in 2026, and CLARA sits at their intersection:

1. **The EU sovereignty mandate stopped being rhetorical.** Data-residency requirements, procurement rules that penalise US-cloud dependence, and boardroom nervousness about sending customer data to US hyperscalers are now hard buying criteria in DACH — especially in regulated segments. Buyers who *cannot* or *will not* export customer feedback to US clouds have almost no governance-first, EU-sovereign option in Voice-of-Customer. The incumbents are US-based.

2. **The EU AI Act moved from abstract to operational.** Article 50 transparency obligations apply from **2 August 2026**. Every serious DACH buyer now needs vendors who can evidence AI-Act posture. CLARA is built GDPR- and AI-Act-first, classified as **limited/minimal risk** (text triage, not biometric), with a ready compliance pack. Governance being *built in* — not bolted on — is a live commercial advantage exactly as the regulation lands.

3. **Local-first / open-weight models became good enough and cheap enough.** The technical premise — enrich, cluster, and synthesise high-quality insight *without* fine-tuning frontier models — only became viable recently. This is what lets CLARA be simultaneously EU-sovereign (no US cloud required) *and* structurally low-cost (inference well under 10% of revenue). Two years ago you had to choose.

**The honest version:** none of these three is a secret. The window is real but not infinite. The advantage goes to whoever *ships a validated, governance-first product into DACH mid-market now* — which is precisely where CLARA already is, while the US incumbents are structurally unable to follow without abandoning their cloud architecture and sales model.

---

## 2. Why you? (The solo-technical-founder question)

**The strength.** CLARA is not a deck — it is a working, validated system built by the person pitching it. The riskiest thing in most pre-seed companies is "can they build it?" That risk is already retired: the product exists, runs on real data, and produces the results in Section 4. The founder built it with genuine academic rigour (it originated as a master's thesis: honest eval harness, bootstrap confidence intervals, an adversarially-verified test set). That is unusually disciplined engineering for a pre-seed technical founder.

**The honest weakness, stated plainly.** The single biggest risk in this company today is **founder concentration**: one person doing product, sales, and compliance. A solo founder is a real risk to sales velocity and to bus-factor. I am not going to pretend otherwise.

**The de-risking plan — concrete, not aspirational:**

- **Co-founder / first-hire gap is the #1 named risk and is being actively worked.** The priority hire is a **commercial co-founder or first sales/CS hire** — not a second engineer. The product is far enough along that the binding constraint is distribution, not code.
- **The 90-day GTM plan is designed for a solo operator** to reach first paying customers *before* the raise is needed — proving the motion works with one person, so a hire is an accelerant on a proven engine, not a bet on an unproven one.
- **Compliance is productised, not founder-dependent.** The AVV/DPA, TOMs, subprocessor list, and DPIA support pack are assets that exist and scale without founder time per deal.
- **Non-dilutive funding buys a runway to hire deliberately.** EXIST Gründungsstipendium, IBB Berlin GründungsBONUS, and EIC Accelerator are live options; a pre-seed raise, if taken, is explicitly earmarked for **GTM + first hires (sales/CS) + compliance certifications (ISO 27001 / SOC 2 path)** — i.e. directly at the founder-concentration risk.

**Why me specifically:** deep technical ownership of an EU-sovereignty product, sitting in Berlin at the centre of the DACH buyer base, having already done the hard, credibility-defining work — the validation. The gap is commercial reach, and it is a fundable, hireable gap, not a foundational one.

---

## 3. How big is this market? Isn't VoC crowded?

**The category is real and funded.** Voice-of-Customer / customer-feedback-analytics / CX-insight software is an established, growing software market with well-capitalised incumbents (Enterpret, Chattermill, Thematic, Unwrap) — which is proof of budget and buying behaviour, not a reason to stay out.

**CLARA is not chasing the whole category.** The serviceable wedge is deliberately narrow and defensible: **EU-sovereign + governed + self-improving**, sold to DACH/EU buyers who cannot or will not send customer data to US clouds. Priority ICPs, in order:

1. **DACH mid-market B2B SaaS** product/CX teams
2. **EU e-commerce / marketplaces**
3. **Regulated DACH fintech / insurance** — highest willingness-to-pay

**Bottom-up, not top-down.** Rather than wave a large TAM number, the model is anchored on ACV and land-and-expand:

- Flagship **Growth** tier lands at **~€24k/yr ACV** (€1,990/mo), inside the DACH mid-market band of €12k–€30k/yr. The honest anchor: the closest competitor's *entry* is now ≈$12k/yr (Enterpret ≈$1,000/mo per review-site estimates — weakly sourced, being validated in discovery calls), even though the *median* Enterpret buyer pays ~$36k/yr and Chattermill averages ~$64k/yr (median ≠ entry). So CLARA does not win on being cheap — **Starter (~€8.3k/yr) matches entry economics**, and **governance + EU sovereignty + zero-config taxonomy + outcome contracts** are what justify Growth and Enterprise.
- **Enterprise** starts at **~€60k/yr** (custom, incl. on-prem/local deployment) for regulated buyers with the highest WTP.
- The value metric — **volume of feedback signals processed** — means accounts expand revenue automatically as usage grows, without a re-sell.

**Illustrative scale (hypothesis, not forecast):** the ramp shows **~€800k ARR by month 12** as *achievable* — a small number of Growth lands plus one or two Enterprise expansions. This is a hypothesis to validate through the 90-day plan and design-partner pilots, not a projection to underwrite.

**The honest framing:** this is not a "capture 1% of a $50B TAM" story. It is a "own the EU-sovereign governance wedge of an existing, budgeted category, land Growth, expand into regulated Enterprise" story — a wedge that the incumbents are structurally positioned *not* to serve.

---

## 4. What's the moat? Anyone could build sentiment tagging.

Sentiment tagging is a commodity. CLARA's defensibility does **not** rest on it. Four layers, in ascending order of durability:

1. **EU-sovereignty + governance as architecture, not a feature.** Local-first, no-US-cloud, GDPR-processor-ready, AI-Act-classified, fully auditable. A US incumbent cannot match this without re-architecting their cloud stack and re-writing their sales model. It is a **structural** barrier for the exact buyers CLARA targets — the wedge is the thing competitors can't cheaply copy.

2. **Industry-adaptability with zero fine-tuning.** CLARA generates **industry-specific tag vocabularies with zero config** — validated live (see below). Competitors that rely on per-customer taxonomy building or fine-tuning carry cost and onboarding friction CLARA doesn't. "No taxonomy to build" is a real sales and margin advantage.

3. **Outcome-grounded self-improvement — the compounding moat.** CLARA learns from **measured business outcomes** (Signal → Insight → Action → Outcome → Learning). This is the durable, compounding layer: the more outcomes a customer's loop closes, the better and more tailored CLARA's insights become for them — raising switching costs and improving with data the customer generates. This is defensible in a way a prompt or a model choice is not.

4. **Validation credibility as a go-to-market moat.** The product is already proven on real, scraped data across three industries — the kind of evidence that shortens enterprise sales cycles and that a fast-follower would have to reproduce from scratch.

**The proof (real validation, done — not vapor):** tested on real scraped datasets across **Henkel** (B2B adhesives), **Lieferando** (food delivery), and **Trade Republic** (fintech):

- **~90% sentiment accuracy** vs star-rating proxy
- **Urgency calibration valid across all three industries**
- **Industry-specific tag vocabularies generated with zero config**
- **Real, actionable themes surfaced** — e.g. Trade Republic *"pervasive support unresponsiveness on critical financial issues"* clustering **14 signals**; Lieferando *"refunds denied for undelivered orders"* clustering **28 signals**

**The honest caveat:** no single moat is impregnable at pre-seed. The compounding defensibility (layer 3) only accrues *with customers and closed loops*. That is exactly why the raise, if taken, funds GTM — to convert an architectural head start into a data-and-outcome moat before a fast-follower can.

---

## 5. You depend on third-party LLMs. What if OpenAI/Anthropic/the model layer changes under you?

This is the right question, and CLARA's architecture is a deliberate answer to it rather than an exposure to it.

- **No frontier fine-tuning; local-first by design.** CLARA runs on **smaller / open-weight models, local-first**. It is not built around one proprietary API. Model dependence is a swappable component, not a foundation.
- **Model-portability is a feature, not a fallback.** Because the value is in the pipeline (enrich → cluster → govern → loop) and the eval harness — not in a specific model's weights — the underlying model can be substituted as the frontier moves. The honest, rigorous eval harness (bootstrap CIs, adversarial test set) is precisely what makes swapping models *safe* and *measurable* rather than a leap of faith.
- **Sovereignty forces independence.** The EU-sovereign requirement already precludes hard dependence on a single US API. What looks like a constraint (can't just call the biggest US model) is what produces the resilience.
- **It protects the unit economics.** Because inference is a swappable, open-weight-capable line and pricing is signal-capped, model-price shocks don't blow up margins (see Section 7).

**The honest exposure:** the *category* of capable models is a dependency — if open-weight and cheap-inference models stopped improving, CLARA's cost/quality frontier would stop improving too. But that is a bet on the entire open-model ecosystem continuing to advance, which is a very different (and far safer) bet than depending on one vendor's pricing or one API's terms of service.

---

## 6. Isn't the EU AI Act / GDPR a regulatory risk that could sink you?

**Reframe: for CLARA, regulation is the wedge, not the risk.** CLARA is *sold to* the buyers most worried about this. Compliance is a sales asset, not overhead.

- **CLARA is a GDPR processor** with a ready **AVV/DPA + TOMs + subprocessor list + DPIA support pack** — these already exist and function as sales collateral for DACH procurement.
- **EU AI Act classification: limited/minimal risk.** CLARA does **text triage, not biometric or high-risk** processing. Article 50 transparency obligations (apply **2 Aug 2026**) are handled with a transparency line — a low-cost, already-planned obligation, not an existential one.
- **The regulation raises the barrier for competitors, not for CLARA.** Every tightening of EU data and AI rules increases the pain of the US-cloud incumbents and increases demand for exactly what CLARA is. Regulatory momentum is a tailwind.

**The honest risk:** regulation *does* move — AI-Act implementing acts, the Digital Omnibus timeline, and GDPR enforcement can shift. The mitigation is that CLARA sits in the *lowest*-risk classification, treats compliance as a maintained product surface (not a one-time checkbox), and — with a raise — puts ISO 27001 / SOC 2 on the roadmap to convert compliance from a defensive necessity into an offensive procurement advantage. The classification is confirmed with counsel, not asserted from memory; specifics get re-verified as the rules settle.

---

## 7. Walk me through the unit economics and the path to profitability.

**Gross margin is the headline strength.** Because CLARA is local-first with no frontier fine-tuning, inference COGS is structurally low. Modelled as cost-per-1,000-signals and *capped by tier volume limits*, inference stays well under 10% of revenue at every tier:

| Tier | Price/mo | Signal cap/mo | Inference (worst realistic) | Inference as % of revenue |
|---|---|---|---|---|
| Starter | €690 | ~5,000 | ~€5 | **~0.7%** |
| Growth *(flagship)* | €1,990 | ~50,000 | ~€50 | **~2.5%** |
| Enterprise | €5,000+ | 200,000+ | €200+ | **~4%** |

This is what supports the **89–94% gross-margin** target — high even by classic-SaaS standards, and a structural outlier at a time when AI-native margins are compressing toward 50–60% industry-wide. The signal-cap pricing model *enforces* the margin: usage cannot outrun revenue.

**Revenue model:** B2B SaaS, hybrid (recurring base + usage), value metric = **volume of feedback signals processed**. Tiers (net, ex-VAT): **Starter €690/mo** · **Growth €1,990/mo** (the flagship land) · **Enterprise €5,000+/mo** custom. **Annual prepay ~17% discount** front-loads cash — the single biggest cash-flow lever for a lean company.

**Billing is de-risked from day one:** **Merchant-of-Record (Paddle)** at launch handles EU-VAT, OSS, and reverse-charge, so a small team carries **zero** multi-country tax-ops burden; migrate to Stripe + Stripe Tax only past ~€50–100k MRR when the ~2× lower processing cost outweighs insourcing.

**Path to profitability:** the ramp shows monthly cash-flow break-even reachable around **month 6** on a design-partner-led motion, with annual-prepay contracts and a possible EXIST stipend turning a thin bootstrap trough into a safe 12–18 month runway. High gross margin + low fixed cost (solo/lean) + prepaid annual cash = a genuinely capital-efficient path.

**The honest caveats:** all prices are **strategic starting hypotheses to validate via willingness-to-pay interviews**, not empirically-derived quotes; competitor prices are third-party estimates because incumbents are sales-gated. The 89–94% margin is a *product-COGS* figure — it does not yet carry a loaded sales team; blended margins compress as you add commercial headcount, which is normal and healthy. Break-even timing assumes the pilot-to-paid conversion in the 90-day plan lands roughly on schedule.

---

## 8. GTM is the hard part — how does a solo founder actually sell this?

Agreed — distribution, not technology, is the binding risk. The plan is built for that reality:

- **Founder-led sales into a warm, specific ICP.** Not "SMBs everywhere" — a named set of DACH mid-market and regulated targets where EU-sovereignty is a *purchase-blocking* criterion for the incumbents. That specificity makes solo outbound tractable.
- **Paid design-partner pilots** as the wedge: one metric, weekly syncs, **testimonial-on-success**. Paid (not free) pilots qualify seriousness and produce revenue plus reference logos. The validated Henkel/Lieferando/Trade Republic results de-risk the first conversation.
- **Thesis-backed content + EU-sovereignty thought leadership** as a top-of-funnel that compounds without paid spend — playing directly to the founder's credibility and the moment's regulatory salience.
- **A concrete 90-day plan to first paying customers**, designed to be executed by one person, converting pilots to paid by week 12. Land Growth, expand to Enterprise in regulated segments.
- **The raise (if taken) buys distribution capacity** — a first sales/CS hire on top of a *proven* motion, not before it.

**The honest risk:** enterprise and regulated DACH sales cycles are long, and a solo founder's throughput is capped. If pilots convert slower than modelled, ARR slips right. Mitigation: prove the motion with one person first (so the model is real before scaling it), keep burn low enough that slipped timing extends runway rather than ending it, and use non-dilutive funding to avoid raising from a position of weakness.

---

## 9. What could kill this?

Straight answers, each with its mitigation:

1. **Founder-concentration / no co-founder.** The top risk. *Mitigation:* prioritise a commercial co-founder / first sales hire; a raise is earmarked for exactly this; the 90-day plan proves the motion is executable solo first.
2. **GTM velocity too slow for a solo operator.** *Mitigation:* narrow ICP where sovereignty blocks incumbents; paid pilots; low burn so slippage extends runway instead of ending the company.
3. **An incumbent decides EU-sovereignty is worth re-architecting for.** Possible but slow and expensive for them (cloud stack + sales model); *mitigation:* convert the architectural head start into a compounding outcome-data moat before a fast-follower arrives.
4. **The open-model / cheap-inference frontier stalls.** Would erode the cost/quality edge. *Mitigation:* model-portable architecture and eval harness mean CLARA rides the whole ecosystem, not one vendor; a bet on the entire open-model field stalling is a low-probability bet.
5. **Regulatory whiplash** (AI-Act implementation, Digital Omnibus, GDPR enforcement shifts). *Mitigation:* CLARA sits in the lowest-risk class, treats compliance as a maintained product surface, and verifies specifics with counsel rather than assuming.
6. **WTP comes in below the modelled tiers.** Prices are hypotheses. *Mitigation:* validate via WTP interviews and paid pilots *before* over-committing to headcount; hybrid usage pricing gives room to re-anchor.
7. **A category shift** — buyers deciding they'd rather have feedback analytics inside their helpdesk (Zendesk/Intercom) than as a governance layer above it. *Mitigation:* CLARA is positioned as the cross-source *insight & governance layer*, not a helpdesk feature — a job the ticketing tools structurally don't do, and can't do sovereignly.

**What makes the company robust despite these:** the product is already built and validated, gross margins are high, burn is low, billing risk is outsourced, and non-dilutive funding is available — so most failure modes slip timing rather than ending the company outright. The one that genuinely could kill it is #1 (founder concentration), which is exactly why it is the explicit #1 use of funds.

---

## 10. What's the exit / return thesis?

**The shape of the return.** CLARA is a capital-efficient, high-gross-margin (89–94%), governance-moated business in a category that already has acquisitive, well-funded incumbents. That combination is what makes it a credible venture return rather than a lifestyle business:

- **Primary path — strategic acquisition.** The natural acquirers are (a) the existing VoC/CX-insight incumbents (Enterpret, Chattermill, Thematic, Unwrap and peers) who need a *credible EU-sovereign, AI-Act-compliant* offering they cannot easily build — CLARA is the fastest way for a US incumbent to become sellable to regulated European buyers; (b) larger EU-sovereign / European enterprise-software platforms assembling a governed AI suite; and (c) CX / customer-experience suites wanting a governance-first feedback layer. CLARA's EU-sovereignty is *precisely* the asset an incumbent can't cheaply replicate — which is what makes it an attractive acquisition rather than a build-vs-buy toss-up.
- **Secondary path — a durable, high-margin independent** in regulated DACH/EU segments, expanding land-and-expand from Growth into Enterprise, where 89–94% margins and low burn compound into strong cash generation and optionality (including a later, larger raise from strength).

**Why the return can be outsized relative to capital in:** high margins + low fixed cost + prepaid annual cash + non-dilutive options mean a modest amount of capital can reach meaningful ARR (illustratively ~€800k by month 12, a hypothesis to validate) with limited dilution — so a strategic exit returns well against a small, efficient cap table.

**The honest framing:** this is not a "next decacorn" pitch. It is a **capital-efficient, defensible, high-margin wedge** with clear strategic acquirers who have a structural reason to buy rather than build — the profile that produces strong multiples-on-invested-capital for early pre-seed money, especially given how little capital is needed to reach the proof points that trigger acquisition interest.

---

## Appendix — the one-paragraph investment case

CLARA is a **validated** (not conceptual) EU-sovereign, governed, self-improving Voice-of-Customer engine, built by a technical founder in Berlin, proven on real data across three industries (**~90% sentiment accuracy**, zero-config industry tag vocabularies, real actionable themes surfaced). It wins a **structurally defensible wedge** — EU-sovereign + governance-first + outcome-grounded self-improvement — that US incumbents can't cheaply follow, exactly as EU sovereignty and the AI Act become hard buying criteria. Unit economics are exceptional (**89–94% gross margin**, inference under 10% of revenue, cash-flow break-even reachable ~month 6, annual-prepay and MoR billing de-risking cash and tax). The honest gap is **commercial: a solo founder needs a co-founder/first sales hire** — which is the explicit #1 use of an optional, opportunistic pre-seed raise, on top of a GTM motion designed to prove itself with one person first. Multiple strategic acquirers have a build-vs-buy reason to want it. Small capital, high margin, real moat, clear buyers.
