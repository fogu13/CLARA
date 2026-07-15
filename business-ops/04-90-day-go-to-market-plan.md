# CLARA — 90-Day Go-To-Market Plan

**Summary.** This is a time-boxed, founder-led execution plan to move CLARA from "validated thesis project" to **first paying customers within 90 days** (plan window: **week commencing Mon 6 Jul → Sun 27 Sep 2026**). The motion is deliberately **high-touch, not self-serve**: recruit **5 design partners / paid pilots** from warm and one-hop networks, run **60–90-day pilots each anchored to ONE hard success metric**, and convert **2–3 into paid annual contracts** by day 90. The pitch leads with CLARA's locked USP — **automatically closing the feedback loop** (Signal → Insight → Action → Learning) — and uses **EU data residency + governed/auditable-by-design** as the DACH *deal-unblocker* that clears procurement, timed to the EU AI Act Art. 50 transparency date of **2 Aug 2026** (falls inside this window) as a "why now." Legal/tax setup (Gewerbe classification, VAT, legal pack) and one non-dilutive grant application run **in parallel** so they never block the first invoice. The plan biases hard to speed: talk to buyers in week 1, sign the first pilot by week 4–5, get cash in by week 12.

**Assumptions (read before executing).**
- Product is demo-ready on real data (Henkel / Lieferando / Trade Republic datasets available as named-adjacent proof cases). This plan is GTM, not a build plan — build status lives in `../docs/roadmap.md`.
- Founder is solo, Berlin-based, currently registered **Freiberufler with a USt-IdNr**, moving to sell a **productised SaaS** (this triggers the Gewerbe question below).
- Positioning is the one **locked** in `../business/STRATEGY_SYNTHESIS.md`: headline = **automated loop closure**; **compliance/audit/EU-residency is the layer on top**, not the lead. This document keeps that framing.
- **August is slow in DACH** (holidays). The plan front-loads outbound *prep* in July, uses August for legal pack + build + async content while decision-makers are away, and hits outbound hard from **early September** when they return.
- The founder's **MSc thesis is due Sept 2026** and competes for time in the final weeks — hence outbound is front-loaded and August leans on async content.
- Landing ACV band **€12k–€30k/yr** — matches competitor *entry* economics (Enterpret entry reportedly ≈$12k/yr per review-site data, being validated in discovery calls); the Enterpret ~$36k / Chattermill ~$64k figures are *median-buyer* datapoints, not entry (**median ≠ entry**). Pilot fees credited toward year-one. Sources: <https://www.vendr.com/marketplace/enterpret>, <https://optif.ai/learn/questions/b2b-saas-acv-benchmark/>.

> **This is not legal or tax advice.** German Freiberufler-vs-Gewerbe classification, VAT structuring, DPAs and EU AI Act calls are fact-specific and decided by the Finanzamt/courts. Confirm everything in the "Legal & ops fast-track" section with a **Steuerberater** and, for the legal pack, a **Fachanwalt für IT-Recht/Datenschutz** *before* you invoice your first SaaS customer.

---

## 1. What "success in 90 days" means (north-star + guardrails)

| Metric | Day-90 target | Why |
|---|---|---|
| Design partners / paid pilots signed | **5** (2 free design partners + 3 paid pilots) | Enough for weekly synchronous co-build; >10 degrades to a mailing list |
| Pilots converted to **paid annual** | **2–3** | First real revenue + referenceable logos |
| First cash collected (pilot fees + first annual) | **≥ €10k booked** | Proof of willingness-to-pay in EUR |
| Referenceable case studies (anonymised OK) | **2** | Fuel the next cohort; shorten cycle 2 |
| Discovery calls held | **20+** | Founder-led pipeline; also feeds the outcome-loop |
| LinkedIn thought-leadership posts (DE) | **~36** (3×/week × 12) | Primary DACH top-of-funnel |
| Legal/tax setup closed enough to invoice | **Yes** | Gewerbe call + VAT + legal pack done before first invoice |

**Guardrails (don't do these):**
- Don't build self-serve signup flows for month 1 — DACH buyers expect a demo + contract in their language + GDPR-by-default proof (<https://embedworkflow.com/blog/selling-saas-in-germany-austria-and-switzerland-dach/>).
- Don't compete as a helpdesk / ticket-triage tool against Zendesk — position **above** Zendesk/Intercom/app-store reviews as the cross-source insight-and-governance layer.
- Don't mass cold-email or spray LinkedIn DMs — in DACH this gets you blocked, GDPR-reported, or mocked. One thoughtful German-language post beats 200 cold DMs (<https://lishchuk.com/blog/b2b-saas-launch-playbook-dach-2026.html>).
- Don't invoice a single SaaS customer before the Steuerberater has ruled on Gewerbe vs Freiberufler and ring-fenced the activities (Abfärbung risk).

---

## 2. The offer (what you actually sell in the pilot)

**One-liner (locked USP first, governance as enabler):**
> *"CLARA automatically closes your customer-feedback loop — it ingests feedback from every source, tags sentiment/urgency/themes, clusters them, and turns them into governed, audit-ready insights that route to action and self-improve from your measured outcomes. All processed in the EU, GDPR- and EU-AI-Act-aligned, with no taxonomy to build and no fine-tuning of frontier models."*

**The pilot pitch template (lead with the WIN, not the product):**
> *"I'm recruiting 3 design partners to run a 60–90-day pilot to {cut time-to-insight on monthly feedback from X days to <1 day / surface the top 5 revenue-linked themes you're missing}. You get a focused build on your workflow, weekly changes, and priority support. In return: 30 min/week and a testimonial if we hit the target."*

**Two-tier program design:**

| | **Design Partner (×2)** | **Paid Pilot (×3)** |
|---|---|---|
| Commitment from them | 30 min/week co-build; testimonial on success | Production-scope use; success review |
| Price | Free or deep discount | **€3,000–€5,000 pilot fee, credited to year-one** |
| Duration | 8–12 weeks | 60–90 days |
| Success = ONE metric | e.g. time-to-first-insight < 1 day | e.g. ≥ 90% of last month's feedback routed into governed, actioned insights |
| What you get | Deep product feedback + case study | Revenue + a conversion path to annual |
| Cap | Total design partners + pilots **≤ 10** | — |

**Pricing you quote for year-one conversion** (hybrid: base + usage on volume-of-signals, generous seats):
- **Starter €490–€990/mo** — 1–2 sources, ~5,000 signals/mo, core enrichment, EU residency.
- **Growth €1,500–€3,000/mo** — 5+ sources, ~25k–50k signals/mo, governed insight synthesis, audit log, GDPR/AI-Act reporting, API.
- **Enterprise €5,000–€9,000+/mo (custom)** — unlimited sources, outcome-grounded loop, SSO, DPA/on-prem, SLA.
Sources for banding: <https://cpoclub.com/tools/best-voice-of-customer-analytics/>, <https://www.unwrap.ai/post/best-enterpret-alternatives-2026> (Unwrap floor $24k/yr), <https://userpilot.com/blog/saas-pricing-models/>.

---

## 3. ICP & the target list (who you hunt)

Prioritise **ICP #3 for willingness-to-pay + differentiator fit**, use **ICP #1 for volume + faster cycles**, keep **ICP #2** for a high-signal e-commerce proof case.

| # | Segment | Buyer (+ co-signer) | Killer pain | Proof case to name |
|---|---|---|---|---|
| **1** (volume) | DACH mid-market **B2B SaaS**, 100–999 emp. | VP Product / Head of CX / Head of Customer Insights | Feedback scattered across app stores/support/reviews/NPS; US tools blocked in security review; taxonomy build is heavy | (adjacent) |
| **2** (proof) | DACH/EU **e-commerce / food-delivery / marketplaces** | Head of CX / VoC / Ops | Huge multilingual review + support volume; needs German theming + urgency triage; consumer PII residency | **Lieferando** dataset |
| **3** (WTP) | Regulated DACH **fintech / insurance** | Head of CX **+ DPO/Compliance co-signer** | Cannot send feedback to US LLMs; needs governed, auditable, human-reviewable insight for BaFin/GDPR | **Trade Republic** dataset |
| (brand/CPG) | Large consumer brand / CPG | Head of Consumer Insights | Brand-level feedback at scale | **Henkel** dataset |

**Target-list build (do this in week 1–2):** assemble **40–60 accounts** = warm network + one-hop intros + a tight LinkedIn list within ONE ICP. Expected yield: investor/network portfolio **40–60%**, targeted personalised LinkedIn **10–20%** (<https://www.unusual.vc/field-guide/build-a-sales-motion-with-design-partners-for-a-b2b-product/>).

---

## 4. The 90-day plan (weeks 1–4 / 5–8 / 9–12)

### Phase 1 — Weeks 1–4: Foundation + first conversations (6 Jul → 2 Aug)
*Theme: get legal/tax unblocked, ship the sales assets, open 40–60 accounts, and hold the first discovery calls. Anchor the "why now" to Art. 50 (2 Aug 2026).*

| Week (2026) | Actions | Weekly goal |
|---|---|---|
| **W1 · 6–12 Jul** | Book **Steuerberater** consult (frame: *"registered Freiberufler + USt-IdNr, launching productised AI SaaS — handle the Gewerbe classification and avoid Abfärbung"*). Email thesis university's **EXIST office** to open a Gründungsstipendium application. Email **IBB Business Team** re: GründungsBONUS Plus (confirm the <18-month window applies). Lock ONE beachhead ICP. Draft German one-pager (WIN metric + EU-residency/AI-Act + EUR pricing + 60–90-day pilot offer). | Steuerberater booked; ICP locked; one-pager v1 drafted |
| **W2 · 13–19 Jul** | Build the **40–60 target account list** (warm + one-hop + LinkedIn ICP). Draft the outbound sequence (5–7 touches / 14 days). Set up **Paddle** (Merchant-of-Record) sandbox for VAT-free-to-you EU B2B billing. Publish LinkedIn post #1–3. | List built; sequence drafted; MoR chosen |
| **W3 · 20–26 Jul** | Launch outbound to **first 20 accounts** (short DE email + warm intro + one LinkedIn message). Start the **legal pack** (AGB + Art. 28 AVV/DPA + TOMs + subprocessor list) with counsel. File the **Gewerbeanmeldung** if the Steuerberater confirms (berlin.de/ea, ~€15). | 20 accounts contacted; first calls booked |
| **W4 · 27 Jul–2 Aug** | Hold **3–5 discovery calls**. Send **first 2 pilot proposals**. Ship the **AI-Act classification memo** (text triage = minimal/limited risk) + one-page compliance datasheet. Post the "**Art. 50 applies 2 Aug 2026**" countdown piece. | ≥3 discovery calls; ≥2 pilot proposals out; **first pilot verbally agreed** |

**Phase 1 deliverables:** Steuerberater engaged · target list · outbound live · legal pack in draft · compliance datasheet + AI-Act memo · first pilot in motion.

### Phase 2 — Weeks 5–8: Land pilots + build proof (3 Aug → 30 Aug)
*Theme: sign 3–5 pilots, run weekly co-build syncs, and start manufacturing case studies. August is slow — expect fewer new calls; use the lull to onboard signed pilots deeply and stockpile content.*

| Week (2026) | Actions | Weekly goal |
|---|---|---|
| **W5 · 3–9 Aug** | Convert the W4 verbal into a **signed pilot** (pilot one-pager: ONE metric, weekly 30-min syncs, testimonial-on-success). Onboard: connect 1–2 sources, agree the baseline metric. Continue outbound to accounts 21–40. | **Pilot #1 signed + onboarded** |
| **W6 · 10–16 Aug** | Weekly pilot sync (change something visible every week). Send **2 more pilot proposals**. Finalise legal pack v1 (customer-ready AVV/DPA + TOMs + published subprocessor list). Waive **§19 Kleinunternehmer** and register for regular VAT (with Steuerberater). | Pilot #1 first outcome logged; 2 proposals out |
| **W7 · 17–23 Aug** | **Sign pilots #2–3.** Set up reverse-charge EU B2B invoicing (both USt-IdNrs, "Steuerschuldnerschaft des Leistungsempfängers", VIES check) + quarterly ZM process. Draft anonymised **case study #1** from pilot #1's early result. | 3 pilots live; invoicing pipeline ready |
| **W8 · 24–30 Aug** | Weekly syncs for all pilots. **Sign pilots #4–5** (target reached). Prep September outbound cohort (accounts 41–60) for the post-holiday return. Publish case study #1 (anonymised). | **5 pilots live**; case study #1 published |

**Phase 2 deliverables:** 5 pilots live · legal pack v1 customer-ready · VAT/reverse-charge invoicing operational · 1 case study.

### Phase 3 — Weeks 9–12: Convert to paid + set up cohort 2 (31 Aug → 27 Sep)
*Theme: prove the ONE metric, convert pilots to paid annual, collect cash, and turn references into the next cohort. Thesis deadline competes for time — protect conversion calls, lean on async content.*

| Week (2026) | Actions | Weekly goal |
|---|---|---|
| **W9 · 31 Aug–6 Sep** | **Mid-pilot outcome reviews**: show each pilot its ONE metric vs baseline. Hit September outbound hard (accounts 41–60 now that DACH is back). Open **EIC Accelerator** file for the **2 Sep 2026** cut-off *if* traction supports it (otherwise target **4 Nov**). | Outcome reviews done; September pipeline reopened |
| **W10 · 7–13 Sep** | Send **year-one conversion proposals** to the 2–3 strongest pilots (Starter/Growth band, pilot fee credited). Draft **case study #2**. Continue discovery calls from the new cohort. | Conversion proposals out |
| **W11 · 14–20 Sep** | **Close conversion #1–2**: signed annual order + first invoice (reverse-charge or MoR). Handle procurement/security questionnaire with the compliance datasheet + DPA + DPIA-support pack. | **First paid annual signed; first invoice issued** |
| **W12 · 21–27 Sep** | **Close conversion #2–3**; collect first cash. Publish case study #2 + a "90-day results" post. **Retro**: lock cohort-2 target list and repeat the motion. | **2–3 paying customers; ≥ €10k booked; retro done** |

**Phase 3 deliverables:** 2–3 paying customers · first cash collected · 2 case studies · cohort-2 pipeline queued · (optional) EIC application in flight.

---

## 5. Outbound engine (targets, cadence, channels)

**Volume math (founder-led funnel to 5 pilots → 2–3 paid):**

| Stage | Target | Conversion assumption |
|---|---|---|
| Target accounts | 60 | — |
| Reached (warm intro / personalised) | ~40 | 65% |
| First (discovery) calls | ~20 | ~50% of reached |
| Pilot proposals | ~8–10 | ~45% of calls |
| Pilots signed | **5** | ~55% of proposals |
| Paid conversions | **2–3** | ~50% of pilots |

**Cadence per account:** 5–7 touches over 14 days = short DE email → warm intro (best yield) → one LinkedIn message referencing a specific post/talk → follow-up email → soft break. **No** mass sends. Channels ranked: warm network / investor-portfolio intros (40–60% of pilot yield) > targeted personalised LinkedIn (10–20%) > inbound from content.

**DACH etiquette (non-negotiable):** German LinkedIn is closer to formal email than US-style DMs; personalise hard; price in EUR with VAT clarity; offer a personal demo and a contract in German. USD pricing on a `.de` page reads as "not a serious vendor." (<https://embedworkflow.com/blog/selling-saas-in-germany-austria-and-switzerland-dach/>)

**The compliance sales kit (attach to every demo — this is what unblocks DACH deals):** EU-hosting statement · data-residency + subprocessor sheet · Art. 28 **AVV/DPA template** · TOMs annex · deletion / right-to-be-forgotten process · one-page **AI-Act & GDPR datasheet** · **DPIA-support pack** so the customer (controller) can finish their DPIA fast.

---

## 6. Content cadence (primary DACH top-of-funnel)

**3 German-language LinkedIn posts/week**, opinionated, benchmark-backed. Founders who post real opinions out-pipeline companies running prettier ads (<https://lishchuk.com/blog/b2b-saas-launch-playbook-dach-2026.html>).

| Slot | Theme | Example angle |
|---|---|---|
| **Mon — POV** | Loop-closure / VoC craft | *"Tagging feedback isn't insight. Closing the loop is."* |
| **Wed — Proof** | Benchmark from Henkel/Lieferando/Trade Republic | *"We ran 3 real German datasets through CLARA — here's what the top themes revealed."* |
| **Fri — Build-in-public / why-now** | EU AI Act countdown, governance, milestones | *"Art. 50 transparency applies 2 Aug 2026 — what it actually means for your VoC stack."* |

Plus: **1–2 anonymised case studies** over the 90 days (one per closed pilot). Show up in CX/product/VoC practitioner communities and Berlin's science-startup ecosystem; consider **ARRtist SUMMIT** (Berlin, B2B SaaS founders + investors) for network once you have a pilot result to talk about.

---

## 7. Weekly scorecard (run every Friday, 30 min)

Track these 7 numbers; prioritise **pilots signed** and **discovery calls** early, **conversions** and **cash** late:

1. New accounts contacted (target ≥ 10/wk in outbound weeks)
2. Discovery calls held (cumulative → 20+)
3. Pilot proposals sent
4. Pilots signed (cumulative → 5)
5. Paid conversions (cumulative → 2–3)
6. €€ booked (→ ≥ €10k)
7. LinkedIn posts shipped (3/wk)

Leading indicators to sanity-check pricing later: **NRR > 100%, CAC payback < 12 mo, LTV:CAC > 3:1, gross margin 70%+ net of inference** (<https://beancount.io/blog/2026/05/10/saas-metrics-founders-must-track-2026-ltv-cac-nrr-churn-cac-payback-benchmarks-guide>). Keep **LLM-inference cost < 10% of revenue** — CLARA's local-first / no-fine-tuning architecture is a structural margin advantage; quantify and sell it.

---

## 8. Legal & ops fast-track (runs in parallel — must not block the first invoice)

> **Not legal/tax advice — confirm with a Steuerberater/Fachanwalt.**

**Do before the first SaaS invoice:**
- [ ] **Steuerberater ruling** on Freiberufler-vs-Gewerbe. **Assume Gewerbe** for a productised SaaS; ring-fence it from any Freiberufler income (separate ledger/bank account, possibly a separate vehicle) to avoid **Abfärbung** tainting all income. (<https://restio.io/de/blog/gewerbe-vs-freiberufler-2026/>)
- [ ] **Gewerbeanmeldung** in your Berlin Bezirk via **berlin.de/ea** (~€15 online). Finanzamt + IHK are notified automatically. (<https://qonto.com/de/blog/unternehmensgruendung/einzelunternehmen/gewerbe-anmelden-berlin>)
- [ ] **Waive §19 Kleinunternehmer, register for regular VAT** (you already hold a USt-IdNr) — B2B customers are VAT-neutral and you reclaim input VAT on cloud/AI spend. §19 thresholds since 2025: ≤ €25k prior year / ≤ €100k current (hard limit). (<https://taxfix.de/ratgeber/selbststaendige/kleinunternehmergrenze/>)
- [ ] **EU B2B invoicing set up correctly**: net invoice, "Steuerschuldnerschaft des Leistungsempfängers / Reverse charge", both USt-IdNrs, **VIES-validate every customer**, file quarterly **Zusammenfassende Meldung**. (<https://restio.io/en/blog/reverse-charge-international-germany/>)
- [ ] **E-invoice capability**: be able to **receive + archive** XRechnung/ZUGFeRD (mandatory since **1 Jan 2025**); sending mandatory for your size by **1 Jan 2028** — do it early, it fits CLARA's "governed/auditable" story. (<https://www.bundesfinanzministerium.de/Content/DE/FAQ/e-rechnung.html>)
- [ ] **Billing platform**: launch on **Paddle (Merchant-of-Record)** — it becomes the legal seller and handles EU VAT/OSS/filing for you at ~5% + €0.50/txn; migrate to Stripe + Stripe Tax past ~€50–100k MRR. (<https://www.globalsolo.global/blog/stripe-vs-paddle-vs-lemon-squeezy-2026>) *Note: if you invoice B2B under reverse-charge from your own entity, you may skip MoR — decide with your Steuerberater which path is cleaner for your mix.*

**Customer-facing legal pack (doubles as sales collateral):** SaaS **AGB** + **Art. 28 AVV/DPA** + **TOMs annex** + published **subprocessor list** (general authorization + right-to-object) + **AI-Act classification memo** (text triage = not prohibited, not Annex III high-risk; Art. 50 transparency labelling live by **2 Aug 2026**) + **DPIA-support pack**. Sign **back-to-back AVVs** with your LLM + hosting vendors; prefer EU-hosted/open-weight models. (<https://gdpr-info.eu/art-28-gdpr/>, <https://compliancehub.wiki/eu-ai-act-article-50-transparency-digital-omnibus-2026/>)

**Website legals:** Impressum under **§5 DDG** (not TMG — repealed 14 May 2024) incl. your USt-IdNr · GDPR Datenschutzerklärung · **§25 TDDDG** cookie consent (or go essential-only to skip the banner). (<https://www.it-recht-kanzlei.de/tmg-ttdsg-ausser-kraft-impressum-datenschutz.html>)

**Consider incorporating (UG from €1 / GmbH €25k) when** you handle real customer PII at scale, take investment, add a co-founder, or an enterprise buyer demands a limited-liability counterparty — CLARA's GDPR/AI-Act data-processing exposure is a legitimate reason to move earlier rather than later. (<https://qonto.com/de/blog/rechtsformen/ug/ug-vs-gmbh>)

---

## 9. Non-dilutive funding (parallel track — buys runway, don't let it block sales)

| Program | Amount | Fit / deadline |
|---|---|---|
| **EXIST Gründungsstipendium** | €2,500–€3,000/mo × 12 + up to €10k materials | Year-round; needs host-university affiliation — CLARA's thesis origin qualifies; contact the uni startup office. (<https://exist.de/en/programm/gruendungsstipendium/>) |
| **IBB GründungsBONUS Plus** | up to €50,000 (≤50% costs) | Berlin, tech/digital model, **start-up < 18 months old** — time-sensitive, apply in German. (<https://www.ibb.de/en/foerderprogramme/gruendungsbonus-plus.html>) |
| **IBB Coaching BONUS** | subsidised coaching (coach ≤ €1,000/day) | Cheap way to buy GTM/sales coaching. (<https://www.ibb.de/en/foerderprogramme/coaching-bonus.html>) |
| **EIC Accelerator** | grant < €2.5M + equity | Later-stage; 2026 cut-offs incl. **2 Sep**, **4 Nov** — pursue only after pilots show measured outcomes. (<https://eic.ec.europa.eu/eic-funding-opportunities/eic-accelerator_en>) |

> *Gründungszuschuss almost certainly does not apply (you're not drawing ALG I).*

---

## 10. Tools & budget (lean solo stack, ~€150–500/mo)

| Job | Tool | Note |
|---|---|---|
| Billing / VAT | **Paddle** (MoR) → Stripe+Stripe Tax at scale | Removes EU-VAT ops burden while solo |
| Product analytics | **PostHog** (EU-hosted option) | Fits data-residency story; free to 1M events/mo |
| Web analytics | Plausible / Fathom | Privacy-friendly, EU |
| Support / chat | Crisp / Brevo | Free/low tiers |
| CRM | Spreadsheet → free HubSpot/Attio | Add only at real lead volume |
| E-sign | Documenso (self-host) / PandaDoc | EU-friendly |

---

## 11. Top risks & mitigations

| Risk | Mitigation |
|---|---|
| **Abfärbung** taints all income as trade | Steuerberater ring-fences SaaS from Freiberufler income *before* first invoice; separate ledger/bank account |
| **August dead zone** stalls pipeline | Front-load outbound prep in July; use Aug to onboard signed pilots + stockpile content; reopen outbound early Sep |
| **Thesis deadline (Sept)** eats selling time | Protect conversion calls in W9–12; lean on async LinkedIn; do the heavy prospecting in July |
| Pilots don't produce a clear outcome | Define **ONE hard metric + baseline** at onboarding; review at mid-pilot; ship a visible change weekly |
| Procurement blocks on data residency | Lead demos with the compliance kit (EU hosting + DPA + subprocessor list + AI-Act datasheet) |
| Margin erosion from LLM inference | Meter inference/1k signals against tier caps; keep < 10% of revenue |
| Messaging drift | Keep the **locked** framing: loop-closure is the headline; governance/EU-residency is the enabling layer, not the lead |

---

## Appendix A — Pilot agreement one-pager (fill-in)

- **Goal (ONE metric):** reduce **{metric}** from **{baseline}** to **{target}** by **{date}**.
- **Scope:** sources connected = **{X}**; signals/mo = **{Y}**.
- **Cadence:** 30 min/week; visible change shipped weekly.
- **Duration:** **{60–90}** days, start **{date}**.
- **Commercials:** pilot fee **€{3,000–5,000}**, credited to a year-one Starter/Growth subscription on conversion.
- **Success → testimonial + named/anonymised case study.**
- **Attached:** AVV/DPA · TOMs · subprocessor list · compliance datasheet.

## Appendix B — First outbound email (DE, ~5 lines)

> Betreff: {konkrete Zahl} aus Ihrem Kundenfeedback — 15 Min?
> Hallo {Name}, ich habe {spezifischer Bezug: Ihr Post/Talk/Produkt}. Wir schließen bei VoC-Teams den Feedback-Loop automatisch — von der Quelle bis zur governance-fähigen, prüfbaren Insight, EU-gehostet. Für {ICP} habe ich auf echten deutschen Datensätzen {konkretes Ergebnis} gezeigt. Ich suche 3 Design-Partner für einen 60–90-Tage-Piloten. Hätten Sie 15 Minuten nächste Woche? Viele Grüße, {Name}

## Appendix C — Key dates in this window

- **2 Aug 2026** — EU AI Act **Art. 50 transparency** applies (the "why now" anchor).
- **2 Sep / 4 Nov 2026** — EIC Accelerator full-application cut-offs.
- **1 Jan 2028** — mandatory e-invoice **sending** for your size (be able to *receive* already).
