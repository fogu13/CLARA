---
marp: true
theme: default
paginate: true
---

<!-- CLARA pitch deck. Speaker notes + visual suggestions are in HTML comments per slide. -->

# CLARA
### The EU-sovereign, governed, self-improving Voice-of-Customer engine

- Turn raw customer feedback (reviews, support, surveys) into governed, auditable, action-ready insights
- EU data residency + local-first: no US clouds required
- GDPR + EU AI Act built in, fully auditable — governance is the wedge, not overhead
- Validated across 3 industries; ~90% sentiment accuracy vs star-rating proxy
- Solo technical founder, Berlin — product exists and is validated today

<!-- Speaker notes: Open with the one-liner verbatim: CLARA is the EU-sovereign, governed, self-improving customer-feedback engine. Say it plainly: incumbents make you send customer data to US clouds and give you dashboards, not decisions. We do the opposite — local-first, governed, and it learns from real business outcomes. Emphasize this is not a concept: it's validated on real scraped data across three industries. Set the tone: confident, specific, honest. -->
<!-- Visual: Full-bleed clean title slide: CLARA wordmark, one-liner beneath, subtle EU-map motif with a Berlin pin. A thin band of the Signal->Insight->Action->Outcome->Learning loop icons along the bottom. -->

---

# Companies drown in customer feedback and still can't act on it
### The Voice-of-Customer gap in regulated EU markets

- Feedback is scattered across app stores, reviews, support tickets and surveys — high volume, low signal
- Existing VoC tools give dashboards and word clouds, not governed, defensible actions
- Incumbents are US-based and route customer data through US clouds
- Regulated DACH buyers (fintech, insurance) cannot or will not send customer data to the US
- No audit trail: GDPR and the EU AI Act make ungoverned AI triage a compliance liability

<!-- Speaker notes: Frame the pain in two layers. First, the universal VoC problem: teams are buried in feedback and still fly blind — they get sentiment charts, not 'do this next.' Second, the EU-specific wedge: the tools that do exist are US-based, and for a DACH fintech or insurer, shipping customer data to a US cloud is a non-starter. Governance isn't a nice-to-have here; it's the gate to the deal. This is the opening our ICPs are actively looking to fill. -->
<!-- Visual: Left: a chaotic funnel of feedback source logos/icons pouring in. Right: a tiny trickle of 'action' coming out. Red 'US cloud' barrier icon between the buyer and the data. -->

---

# CLARA: from raw feedback to governed, action-ready insight
### One pipeline, EU-sovereign, auditable end to end

- Ingest customer-feedback text: app-store, reviews, support, surveys
- Enrich: sentiment, urgency, concise snake_case theme tags — zero config per industry
- Cluster feedback into coherent themes automatically
- Synthesize governed, auditable, action-ready insights with a full audit trail
- Adaptable across industries WITHOUT fine-tuning frontier models

<!-- Speaker notes: Walk the pipeline left to right in one breath: we ingest text feedback, enrich each item with sentiment, urgency and clean theme tags, cluster into themes, and synthesize insights a CX or product lead can act on. The two things to stress: every step is auditable — you can trace an insight back to the exact signals — and it adapts to a new industry with zero fine-tuning. That last point is what makes our economics work, which I'll come back to. -->
<!-- Visual: Horizontal pipeline diagram: Ingest -> Enrich -> Cluster -> Synthesize, each stage a labeled node. A 'governance / audit log' rail runs underneath every stage. EU-sovereign badge top-right. -->

---

# The engine that compounds: outcome-grounded self-improvement
### Signal -> Insight -> Action -> measured Outcome -> Learning

- Signal: customer feedback enters and is enriched and clustered
- Insight: governed, auditable themes surfaced with recommended actions
- Action: the customer acts on the insight in their business
- Outcome: the measured business result is fed back into CLARA
- Learning: CLARA improves from real outcomes — defensible, compounding advantage

<!-- Speaker notes: This is the heart of the pitch and the moat. Most tools stop at 'insight.' CLARA closes the loop: the customer acts, the outcome is measured, and that measured outcome trains the system. So the product gets better with every customer and every action — not from more model parameters, but from real business results. That's a compounding, defensible advantage a US incumbent bolting on a dashboard can't easily copy, because they don't have the outcome data or the governance rail to trust it. -->
<!-- Visual: A closed loop diagram with five nodes (Signal, Insight, Action, Outcome, Learning) arcing back on itself. Highlight the Outcome->Learning arc as the moat, with a small upward 'compounding' curve inset. -->

---

# Why now

- EU AI Act in force — Art. 50 transparency obligations apply from 2 Aug 2026
- GDPR enforcement and data-residency pressure make US-cloud VoC tools a liability for regulated buyers
- Local-first LLMs are now good enough to run governed triage without frontier fine-tuning
- EU-sovereignty has moved from 'preference' to 'procurement requirement' in DACH fintech/insurance
- Sovereign-AI funding and non-dilutive programs (EXIST, IBB, EIC) are actively backing this thesis

<!-- Speaker notes: Three curves are converging right now. One: regulation — the EU AI Act's transparency rules bite in August 2026, and GDPR already makes US-cloud data flows painful for our buyers. Two: local-first models are finally good enough to do this work without expensive fine-tuning. Three: sovereignty has flipped from a talking point to a hard procurement checkbox in regulated DACH segments. The window to be the default EU-sovereign, governed VoC engine is open now. -->
<!-- Visual: Timeline arc landing on 2 Aug 2026 (EU AI Act Art. 50). Three converging arrows labeled 'Regulation', 'Local LLMs viable', 'Sovereignty = requirement' meeting at a 'CLARA' point. -->

---

# Market: Voice-of-Customer / CX-insight software
### EU-sovereign, governance-first is an underserved wedge

- Category: Voice-of-Customer / customer-feedback-analytics / CX-insight software
- Incumbents are largely US-based and not EU-sovereign or governance-first — price is no longer the gap; governance is
- Beachhead: DACH mid-market B2B SaaS, EU e-commerce/marketplaces, regulated DACH fintech/insurance
- Value metric scales with volume of feedback signals processed — expands with the customer
- Wedge: buyers who cannot or will not send customer data to US clouds

<!-- Speaker notes: I'll be honest about sizing rather than throw a fake trillion-dollar number. The category is established and large — VoC and CX-insight software. Our serviceable wedge is specific: EU buyers who need sovereignty and governance, starting in DACH. That's where we win on requirements the US incumbents structurally can't meet without re-architecting. And because we price on signal volume, revenue grows as a customer's feedback volume grows — the account expands itself. -->
<!-- Visual: Concentric-circle TAM/SAM/SOM: outer 'Global VoC/CX software', middle 'EU VoC spend', inner highlighted 'EU-sovereign + governed DACH beachhead'. ICP logos/segment icons in the inner ring. -->

---

# Business model: B2B SaaS, hybrid pricing
### Value metric = volume of feedback signals processed

- Starter EUR 690/mo (~8.3k/yr) — up to ~5k signals/mo
- Growth EUR 1,990/mo (~24k/yr) — up to ~50k signals/mo — flagship land tier
- Enterprise EUR 5,000+/mo custom (from ~60k/yr) — incl. on-prem / local deployment
- Recurring base + usage; annual prepay ~17% discount
- Anchored vs closest competitor entry ~$12k/yr (review-site est.) — CLARA matches entry economics; governance + EU sovereignty justify Growth/Enterprise
- 89-94% gross margin via local-first, no-fine-tune architecture; Paddle Merchant-of-Record for EU-VAT at launch

<!-- Speaker notes: Simple, hybrid model: a recurring base plus usage, metered on the number of feedback signals we process — a metric that maps directly to value delivered. We land on the Growth tier at just under two thousand euros a month and expand into Enterprise, which includes on-prem and local deployment — exactly what regulated buyers pay a premium for. On anchoring, be honest: the closest competitor's entry is around twelve thousand dollars a year per review-site estimates — an estimate we're validating in discovery calls — so we don't pitch cheap; Starter matches those entry economics, and the Growth and Enterprise premium is paid for governance, sovereignty and measured outcomes. Margins are 89 to 94 percent because we don't fine-tune frontier models and we run local-first, so inference COGS stay low. Billing is via Paddle as Merchant-of-Record so EU VAT is handled from day one. -->
<!-- Visual: Three-tier pricing table (Starter / Growth / Enterprise) with the Growth column highlighted as 'land here'. Margin callout badge: '89-94% gross margin'. Small Paddle/MoR compliance note. -->

---

# Traction: validated on real data across 3 industries
### Proof, not vapor

- Tested on real scraped datasets: Henkel (B2B adhesives), Lieferando (food delivery), Trade Republic (fintech)
- ~90% sentiment accuracy vs star-rating proxy; urgency calibration valid across all 3 industries
- Industry-specific tag vocabularies generated with zero config
- Trade Republic: surfaced 'pervasive support unresponsiveness on critical financial issues' clustering 14 signals
- Lieferando: surfaced 'refunds denied for undelivered orders' clustering 28 signals
- Originated as a master thesis: honest eval harness, bootstrap CIs, adversarially-verified test set

<!-- Speaker notes: This is the slide I'd stake the pitch on. We didn't demo on toy data — we ran CLARA on real scraped feedback for three very different businesses: an industrial B2B adhesives maker, a food-delivery marketplace, and a fintech. Roughly 90 percent sentiment accuracy against the star-rating proxy, urgency calibration held across all three, and the tag vocabularies were generated with zero configuration. And it surfaced genuinely actionable themes — like Trade Republic's support unresponsiveness on critical financial issues, or Lieferando denying refunds on undelivered orders. This came out of a master thesis, so the eval rigor is real: bootstrap confidence intervals, an adversarially-verified test set. This is evidence, not promise. -->
<!-- Visual: Three-column proof panel, one per company (Henkel / Lieferando / Trade Republic) with the ~90% accuracy stat up top and the two real surfaced-theme quotes called out in cards. -->

---

# Go-to-market: founder-led, pilot-proven
### 90 days to first paying customers

- Founder-led sales into the three priority ICPs, starting DACH
- Paid design-partner pilots: one metric, weekly syncs, testimonial-on-success
- Thesis-backed content + EU-sovereignty thought leadership as inbound engine
- 90-day plan to first paying customers
- Land on Growth tier, expand to Enterprise in regulated segments

<!-- Speaker notes: GTM is deliberately lean and evidence-led. I sell it myself into DACH first. The motion is paid design-partner pilots — not free trials — each anchored on a single success metric with weekly syncs and a testimonial when we hit it. On top of that, the thesis and our EU-sovereignty point of view drive inbound; this is content only a founder who did the research can write. The plan is 90 days to first paying customers, land on Growth, then expand into Enterprise where the regulated segments have the highest willingness to pay. -->
<!-- Visual: Funnel-to-flywheel: thought-leadership content -> founder outreach -> paid pilot (weekly syncs) -> Growth contract -> Enterprise expansion. 90-day marker on the pilot->contract step. -->

---

# Competition & moat
### Governance and outcomes are the durable wedge

- Incumbents: US-based, not EU-sovereign, governance bolted on if at all — no longer uniformly expensive at entry, so price is not the moat
- CLARA moat 1 — EU data residency + local-first: structurally hard for US incumbents to match
- CLARA moat 2 — governance built in: GDPR + EU AI Act auditable by design
- CLARA moat 3 — outcome-grounded self-improvement: compounds with every customer, hard to copy
- CLARA moat 4 — industry-adaptable with zero fine-tuning: fast, cheap expansion into new verticals

<!-- Speaker notes: Be honest: the incumbents are bigger, have brand, and at least one now has an accessible entry tier — so we never claim to win on price. But their strengths are in a different game. They're architected for US cloud and retrofitting governance; we're EU-sovereign and governed from the ground up. On the feature matrix that matters to our buyer, we check every box they can't. And the deepest moat is the outcome loop — it compounds with usage, so the longer we run in a segment the harder we are to displace. Zero-fine-tune adaptability means we can enter a new vertical for near-zero marginal model cost while they'd need bespoke engineering. -->
<!-- Visual: 2x2 or feature-matrix: rows = EU-sovereign / Governed-auditable / Self-improving / Zero-fine-tune; columns = CLARA vs 'US incumbents' with checks vs blanks. CLARA column fully checked. -->

---

# Team
### Solo technical founder — honest about the gap

- Solo technical founder in Berlin; built and validated CLARA end to end
- Currently Freiberufler + USt-IdNr, registering Gewerbe as it becomes productized SaaS
- Known risk: co-founder / first-hire gap — being addressed deliberately
- First hires: sales / customer success to scale the founder-led motion
- Deep domain + eval rigor from the master-thesis origin

<!-- Speaker notes: Straight talk here builds credibility. I'm a solo technical founder in Berlin. I designed, built and validated the product myself, which is why the eval work is rigorous. The honest risk is that I'm solo — the co-founder and first-hire gap is real and I'm treating it as a priority, not hiding it. The first hires are commercial: sales and customer success to take the founder-led motion and make it repeatable. I'd rather name the gap and show the plan than pretend it isn't there. -->
<!-- Visual: Simple founder card (photo, Berlin, one-line bio) plus a small 'org plan' showing current founder and two dashed-outline planned hires (Sales, CS). Honesty badge: 'known risks, stated'. -->

---

# Financials (illustrative)
### A hypothesis to validate, not a forecast

- Illustrative ramp: ~EUR 800k ARR by month 12 per the modeled path
- Driven by landing Growth tier (~24k/yr) and expanding to Enterprise (60k+/yr)
- 89-94% gross margin — low inference COGS from local-first, no-fine-tune architecture
- Revenue scales with signals processed; annual prepay (~17% discount) improves cash
- Paddle Merchant-of-Record keeps EU-VAT compliance and billing overhead low

<!-- Speaker notes: I'll flag clearly that this is illustrative — a modeled hypothesis I intend to validate, not a promise. The path to roughly 800k ARR by month 12 comes from landing Growth-tier customers and expanding a subset into Enterprise. The margin story is the durable part: 89 to 94 percent gross margin, because our architecture keeps inference cheap. Annual prepay helps cash, and Merchant-of-Record billing keeps compliance overhead near zero. The numbers to hold me to are the leading indicators — pilots and first paying customers — not this curve. -->
<!-- Visual: ARR ramp line/bar chart climbing to ~800k at month 12, clearly labeled 'illustrative'. Side callout: gross margin band 89-94%. Mix bars showing Growth vs Enterprise contribution over time. -->

---

# The ask & use of funds
### Optional, opportunistic — to accelerate GTM

- Bootstrapped to a validated product; a pre-seed raise is optional/opportunistic to accelerate
- Non-dilutive options in motion: EXIST Grundungsstipendium, IBB Berlin GrundungsBONUS, EIC Accelerator
- Use of funds: GTM + first hires (sales / CS)
- Use of funds: compliance certifications — ISO 27001 / SOC 2 path
- Compliance pack ready: GDPR processor, AVV/DPA + TOMs + subprocessor list + DPIA support

<!-- Speaker notes: Positioning matters: I've reached a validated product on a bootstrap, so I'm not raising out of need. A pre-seed is opportunistic — capital to go faster on GTM. In parallel I'm pursuing non-dilutive funding: EXIST, IBB's GrundungsBONUS, EIC Accelerator. Wherever the money comes from, it goes to three places: go-to-market, the first sales and CS hires, and formal compliance certifications — the ISO 27001 and SOC 2 path — because those certs unlock the regulated Enterprise deals. And note we already ship the practical compliance pack: DPA, TOMs, subprocessor list, DPIA support. -->
<!-- Visual: Use-of-funds donut (GTM / Hires / Compliance-certifications) alongside a two-track 'Non-dilutive + optional pre-seed' funding path. Compliance-readiness checklist ticked on the right. -->

---

# The EU-sovereign standard for governed customer intelligence
### Signal -> Insight -> Action -> Outcome -> Learning

- Vision: the default engine for governed, self-improving Voice-of-Customer in Europe
- Land in DACH VoC/CX, expand across EU verticals with zero fine-tuning
- Compounding moat: every customer outcome makes CLARA smarter and harder to displace
- Validated today across 3 industries — this is a starting line, not a promise
- Let's talk: elvisshehi@gmail.com — Berlin

<!-- Speaker notes: Close on the arc. Near term we're the EU-sovereign, governed VoC engine for DACH. Longer term we're the standard for governed customer intelligence across Europe — because the outcome loop means every deployment compounds our lead. The reason to believe is on the traction slide: this already works on real data across three industries. That's the starting line. If you want to be part of building the sovereign, governed default for customer intelligence in Europe, let's talk. Give clear contact and a concrete next step — a pilot conversation or a follow-up. -->
<!-- Visual: Closing hero: CLARA wordmark, the loop rendered as the through-line, tagline, and contact block. EU-sovereign badge. Clean, confident, single focal point. -->
