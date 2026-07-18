# Trade Republic — Did the €XXM service offensive work? A measured, public-data read

_CLARA loop readout · 18 Jul 2026 · 250 public signals (200 Trustpilot 9 Jun–17 Jul + 50 App Store
AT 22 Mar–12 Jul, spanning the ~20 Apr 2026 launch of 1,000+ agents / 24-7 phone) · production
enrichment pipeline, exemplars ON · private outreach artifact — do not publish_

## The one-slide answer

**The fix registers in customers' language — not yet detectably in the numbers.** Post-launch
reviews explicitly praise "echte Menschen im Service" and call the old support "Manko beseitigt";
the support-complaint share moved down only directionally (31.6% → 25.8% on the dated App-Store
series, p ≈ 0.66 — statistically **not detectable** at this public sample size), and the complaint
*type* shifted from "support doesn't exist" to "support exists but is templated and deflective on
hard cases." A double-digit-million-euro intervention currently has **no statistically powered
public evidence that it worked** — that is a measurement gap, not a service verdict, and closing it
is precisely what an instrumented outcome contract does.

## What CLARA found (theme map, negative/mixed signals)

| Theme (pipeline tags, merged) | Mentions | What customers actually report |
|---|---|---|
| Support quality (poor/unresponsive/no/missing_support) | **35** | Template answers repeated verbatim ("16 near-identical replies" was already a Stiftung Warentest finding); screenshots ignored; agent changes mid-chat forcing full repetition; "senior department" deferrals; 4-month-old tickets (portfolio-transfer cost errors); 24/7 promise vs hours-long waits |
| Funds/transfer friction | ~12 | Transfers held for days pending Mittelherkunft evidence (incl. a €2,100 private transfer needing a handwritten declaration); instant transfers not executed; accounts frozen post-deposit; BaFin complaints announced by reviewers |
| Account access & onboarding | ~9 | Registration stuck for weeks at "Beruf auswählen"; selfie-ident failures locking the app 48h; SMS-PIN never arriving; login impossible after tax-ID entry |
| UI regression (new desktop) | 3+ | June/July desktop redesign: "Mini-Schrift" unreadable, old design removed, PC login broken — a fresh, self-inflicted theme the service org will feel next |
| Order integrity | ~5 | Limit orders deleted without notification; IPO order partial-fills without explanation; tax mis-calculations (€5,000 case) |
| Critical-urgency signals | **6** | Blocked crypto transaction escalated to lawyers; funds "verschwunden" for days; fraud-case handling failures |

Positive counterweight (161 of 250 positive): conditions/Zinsen, Saveback, ease of use — and,
new in 2026, explicit praise for human phone support. Caveat that matters for any Trustpilot-based
KPI: **the recent stream is flooded with solicited invited 5-star reviews** (pages of one-line
"Alles super" entries) — TR began actively inviting reviews around the relaunch, which inflates
naive rating averages and is exactly why theme-level measurement beats star-gazing.

## The pre/post measurement (dated App-Store series crossing 20 Apr)

| | n | Support-complaint share | 95% CI | Mean rating |
|---|---|---|---|---|
| Pre-launch (22 Mar–19 Apr) | 19 | 31.6% | 15–54% | 2.58 |
| Post-launch (20 Apr–12 Jul) | 31 | 25.8% | 14–43% | 2.65 |
| Trustpilot snapshot (Jun–Jul) | 200 | 16.0% | 12–22% | — |

Two-proportion test p ≈ 0.66: **the improvement is not statistically detectable from public data at
this n.** That is the pitch, not a caveat: with TR's internal ticket stream + full review firehose,
the same outcome contract (baseline window → intervention date → scheduled re-measurement,
interrupted-time-series estimator, A–E evidence grading) would have had the power to give the board
a real answer — and CLARA stamps every readout with its evidence grade instead of a vanity metric.

## Insight → action (produced by the pipeline's synthesis stage)

1. **"Support unresponsive on critical issues despite recent service improvements"** (conf 0.85) —
   recognizes the 2026 shift to real people, isolates the unresolved high-severity tail (missing
   funds, 4-month tickets, PIN resets). *Action direction: escalation lane with named ownership +
   SLA for funds-at-risk cases; measure repeat-contact rate on that lane.*
2. **"Systemic support failures eroding trust across product areas"** — referral-bonus payouts, tax
   errors, blocked crypto, fraud handling; template-and-deflect pattern. *Action: theme-routed
   queues instead of generic L1; measure template-reuse rate.*
3. **"Customers churning over app bugs, support and cross-border account barriers"** — churn is
   stated, not inferred; competitor comparisons explicit. *Action: churn-intent flag on triage
   (CLARA tags it natively) feeding a save-desk.*

## Why this conversation (and why now)

BaFin's Aug-2025 Aufsichtsmitteilung and the 2025 complaint statistics (securities complaints
+16%, >50% of arbitration cases neo-brokerage) make *auditable* complaint-theme evidence a
regulator-facing asset, not just a CX tool. TR has already spent the money on the fix; CLARA is the
governed, EU-resident layer that proves — to the board, to BaFin, to the press — whether it worked,
theme by theme, with evidence grades and an audit trail. This readout was built from public data
alone, pipeline-processed, in one day; the in-house version runs on their own streams.

_Method, sampling limits and compliance stance: see README in this folder. All figures reproducible
from the dated corpus; nothing hand-typed._
