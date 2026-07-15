# Organic & Public Feedback Listening — Strategic Assessment + Build Plan

_3–4 Jul 2026. Grounded in the shipped ingestion code (audited), the verified
Enterpret inventory, the ICP/GTM docs, and the target-accounts research._

---

## 1 · Honest review: how feedback collection works today

| Path | State | Ease for a customer |
|---|---|---|
| **CSV upload/paste** (Sources page) | Excellent: validation report, column mapping with aliases, only `feedback_text` required, content-hash dedup, DE/EN detection | ★★★★★ — any team with a helpdesk export is live in minutes |
| **HMAC webhook** (`/ingest/webhook`) | Generic push from anything that can POST; same pipeline (defaults, dedup, language) | ★★★★ — one engineer, one afternoon |
| **Zendesk connector** | Real incremental sync (cursor persisted), imports + dedups, pull-on-demand | ★★★★ — API token + click |
| **Demo datasets** | Evergreen (timestamp rebase) | demo-only |

**Verdict on ease: yes — for *solicited/internal* feedback (tickets, surveys-as-CSV,
CRM exports) collection is genuinely easy and the pipeline behind it is the
strongest part of the product.**

**The gap: CLARA is deaf to *organic* feedback.** Nothing listens to app-store
reviews, Trustpilot, Google reviews, Reddit or social. The only way in today is
a manual CSV (exactly how the thesis datasets got in). Two consequences:
1. The **emerging radar starts late** — public complaints usually precede
   support-ticket spikes; CLARA currently sees the spike, not the smoke.
2. The **cold start depends on the prospect's internal data** — which needs a
   security conversation before the first wow.

## 2 · Strategic case: should CLARA do public listening? — **Yes, decisively**

1. **It weaponizes the existing GTM motion.** The 75-account target list was
   built on *observable public review pain* — the outbound hook is literally
   "your Trustpilot/app-store reviews show X." A product that ingests those same
   public sources turns the pitch into the demo: *"we loaded your public
   reviews — here is your emerging-problems radar"* — **zero integration, zero
   procurement, before the first call ends.** No competitor demo starts faster.
2. **It multiplies the USP, not just the funnel.** The whole loop gets better:
   public reviews → earlier emerging detection → promoted problems whose
   auto-captured `signal_rate_per_day` baseline now includes public complaint
   rate → **outcome measurement visible without any customer integration**
   (P5 evidence from day one of a pilot).
3. **ICP fit is exact.** DACH fintech lives and dies on Trustpilot + app-store
   ratings (Trade Republic, N26 review wars); e-commerce/delivery on Trustpilot
   + Google reviews; SaaS on G2. Our own fintech demo dataset already mimics
   this mix — the real thing is strictly better.
4. **Competitive necessity, scoped.** Reviews/social ingestion is a verified
   Enterpret strength [H]. We don't need their 50-connector breadth — we need
   the **three sources DACH buyers actually check** (Trustpilot, app stores,
   Google reviews). This is the one left-half element worth matching *now*.
5. **Attractive to buy.** "Listening" turns CLARA from a reactive
   ticket-triage tool into a brand-surveillance + action system — a budget line
   CX *and* marketing recognize. It also makes the Growth tier's "5+ sources"
   gate real, and is a natural expansion/upsell driver.

## 3 · The legal spine (this is where we differ from everyone)

**Product rule: no scraping. "Own-presence listening" only** — the customer
connects sources they own or have API rights to:

| Source | Lawful access path | Notes |
|---|---|---|
| **Apple App Store reviews** | Public Apple RSS/JSON feed per app-id + country | No auth; per-country feeds give DE/EN/AT/CH natively |
| **Trustpilot** | Official Business API with the customer's own API key | Scraping violates Trustpilot ToS — product never does it |
| **Google Play reviews** | Play Developer API, customer's own service account | Owner-only by design — inherently clean |
| **Google Business reviews** | Business Profile API, customer OAuth | Owner-only; heavier OAuth → later phase |
| **Reddit brand mentions** | Official API (registered app) | Commercial-terms check required before GA; phase 4 |
| **X/Twitter** | ❌ skip | API pricing kills unit economics at our ACV |
| **G2** | Vendor's own review export/API | Later; SaaS ICP only |

**GDPR framing — the differentiator:** public data is still personal data.
CLARA's angle vs "scrape-everything" tools: documented **legitimate-interest
basis** per source (template in the trust pack), **author pseudonymization at
ingestion** (reuse `pseudonymized_identifier` — we analyze themes, never
profile reviewers), retention via existing rules, and every listening source
visible on the compliance page. **"Governed listening"** joins governed action
in the positioning — nobody else in the category says this.

**Prospecting demos** (their public reviews *before* they're a customer) stay a
**manual internal research workflow** (CSV import, as the thesis did) — a sales
tool, not a product feature, keeping product hands clean on ToS.

## 4 · Build plan

### Phase L1 — App Store reviews + scheduled source sync (S/M, ~2–3 days) ← start here
- `connectors/app_store.py` (SourceConnector): fetch Apple review feed per
  `{app_id, countries[]}`; map → signals (`signal_id=as-{review_id}`, source
  `app_store:{country}`, rating→metadata, journey `public_reviews`, DE/EN
  detection already fires); reuse pagination/dedup patterns from Zendesk.
- **Scheduled source sync**: a sync tick alongside the measurement loop
  (same env-gated asyncio pattern) pulling all active *pull* connectors every
  N hours; per-source `last_synced_at` already persists in connector config.
  This also upgrades Zendesk from button-press to true continuous sync.
- Integrations card (app id + country list); Sources page shows per-source
  last-sync + counts.
- **Why first:** zero auth, public endpoint, fintech-ICP-perfect, smallest
  legal surface — and it makes the whole "listening" story demoable in week 1.

### Phase L2 — Trustpilot Business connector (M, ~3–4 days)
Customer's API key; incremental by review time; the DACH heavyweight. Gate on
one design partner with a Trustpilot business account (demand-driven, per the
plan's own rule).

### Phase L3 — Google Play (M) → Google Business Profile (M, OAuth)
Owner service-account JSON first (clean), Business Profile OAuth second.

### Phase L4 — Reddit keyword/subreddit monitor (M, flagged)
Brand/product keywords → signals. **Blocker to clear first:** commercial API
terms review. Value: dev-tool/fintech communities surface issues days early.

### Cross-cutting (in L1)
- Rating-aware enrichment hint (1–2★ → urgency prior) — metadata only, the
  LLM still judges; volume caps + per-source dedup already handled by the
  pipeline; telemetry `signals_imported {source: app_store}` for free.
- Compliance page: listening sources listed with their lawful-basis line.
- Trust pack: one-page legitimate-interest template per source.

### Explicitly NOT building
Scraping of any property; X/Twitter; Instagram/TikTok; sentiment-over-time
social dashboards (we are action, not media monitoring); influencer/PR
features. The moment listening drifts toward Brandwatch, we've left our lane.

## 5 · GTM hooks
- **Demo opener:** "Give us your app-store ID — nothing else — and come back in
  10 minutes." Radar + themes + German handling, no procurement.
- **Pricing:** listening sources count toward the source gates (Starter 1–2 →
  Growth 5+); public-listening-only entry deal → expand into helpdesk + loop.
- **Claims discipline:** "CLARA listens to your public customers and acts under
  governance" — never "social media monitoring" (wrong category, wrong buyer).

## 6 · Risks
| Risk | Mitigation |
|---|---|
| Apple feed is unofficial-ish / could change | Isolate in connector; feed loss degrades to CSV path, never breaks the pipeline |
| Review-bomb noise floods the radar | Existing dedup + emerging thresholds; per-source daily caps |
| Reddit/API commercial terms shift | Phase-gated behind a terms review; never load-bearing |
| "Listening" scope creep toward media monitoring | The NOT-building list above is part of this plan's acceptance |
| GDPR challenge on public data | Legitimate-interest docs + pseudonymized authors + themes-not-people processing — stronger posture than any incumbent |

## 7 · Success metrics (telemetry already in place)
- % of pilots activating ≥1 public source in week 1 (target: 100% — it's the opener)
- Time-to-first-insight for public-only workspaces (target: <30 min)
- Emerging-radar lead time: public-source detection vs first internal ticket
- Expansion: public-listening-entry deals that add a helpdesk source within 60 days
