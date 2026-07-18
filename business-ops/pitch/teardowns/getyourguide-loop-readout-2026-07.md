# GetYourGuide — The pain is supplier operations, and it's measurable

_CLARA loop readout · 18 Jul 2026 · 180 public signals (100 App Store AT+CH, Oct 2025–Jul 2026 +
80 Trustpilot getyourguide.com DE-language sample, 22 Jun–17 Jul; aggregate 3.9★ / 54,410 reviews)
· production enrichment pipeline, exemplars ON · private outreach artifact — do not publish_

**Positioning note (why this account despite Chattermill):** GetYourGuide expanded its Chattermill
partnership in Aug 2025 — theme analytics is covered. This readout deliberately demonstrates the
layer Chattermill does not do: **governed action with measured closure on the supplier side**. The
pitch is displacement-adjacent, not head-on: keep the dashboards, add the loop.

## The one-slide answer

**The product is loved; the marketplace's operational tail is what customers punish.** 113 of 180
signals are positive — booking UX, guides, breadth. The negative tail (52 negative + 13 mixed) is
overwhelmingly **supplier-side operations**: last-minute cancellations (overbooking, "not enough
guests", 20h to 40min before start), no-show pickups (2–3h waits reported), refunds stuck for
weeks after GYG-confirmed bookings, price disputes (children billed as adults; alternatives at
double the price), and an **AI-first support layer customers describe as blocking escalation
precisely when money is at stake**. Every one of these maps to a *named supplier* and a *dated
booking* — i.e., to a governed action (supplier remediation, delisting review, refund SLA) whose
outcome can be measured. That closing step is the gap in the current stack.

## Theme map (negative/mixed)

| Theme | Mentions | What customers report |
|---|---|---|
| Tour cancellations & overbooking (tour_cancellation / overbooking) | ~9 | Operator cancels 20h before start for under-booking; boat full despite valid tickets and punctual arrival; 40-minute-late annulment at the meeting point |
| Refund failures (refund_denied / refund_issue / payment_error) | ~8 | "Stornierte Tour, keine Rückerstattung — seit Wochen"; 5-day refund promises missed; PayPal refunds unresolved; no-refund on app-caused missed meeting points |
| Churn stated outright (churn_risk) | 7 | "Nie wieder" as a recurring literal phrase; advice to book direct with operators — disintermediation risk in customers' own words |
| Support quality (poor_support vs good_support 4:2) | ~6 | AI-only first line prevents escalation on money cases; but when a human engages, praise follows ("Geld problemlos erstattet", WhatsApp/phone contact valued) — the capability exists, the routing fails |
| Pricing integrity (price_gouging / price_discrepancy) | ~5 | Children's tickets billed at adult price; €1 above direct tourist-office price noticed and reviewed; replacement offers at >2× |
| Misleading listings (misleading_description) | ~4 | Katamaran that is a Schlauchboot; Paella course "not as described"; WhatsApp contact from unknown third parties rescheduling bookings (trust/safety adjacent) |

Critical-urgency signals: 3 (money-loss + trust cases). Multi-language: the pipeline processed
DE/EN/FR-market reports natively — no taxonomy work.

## Insight → action (pipeline synthesis stage)

1. **"Rigid refund policies and ineffective support driving customers to book directly with
   providers"** (conf 0.85) — names the disintermediation loop: refund friction → "book direct"
   advice → marketplace bypass. *Action: money-case escalation lane (human within one contact);
   outcome contract on refund-cycle time and repeat-contact rate.*
2. **"Widespread dissatisfaction on cancellation/refund cases across markets"** — consistent across
   FR/DE/EN samples; the 5-day refund promise is publicly failing. *Action: SLA instrumentation with
   breach alerts — CLARA's guardrail mechanic, verbatim.*
3. **"Last-minute operator cancellations causing severe frustration and churn"** — supplier-level
   repeat-offender visibility. *Action: per-supplier cancellation scorecard gating visibility/rank;
   measured via the outcome contract (repeat-cancellation rate per supplier post-intervention).*

## Why this conversation

GYG's Product org already believes in VoC (they bought it). What the current stack cannot answer:
*"we intervened with supplier X in May — did their cancellation complaints actually stop?"* CLARA's
outcome contracts + approval-gated actions + audit trail answer exactly that, in an EU-resident
deployment, without displacing the existing analytics. Entry point: Ops/Supply leadership rather
than the Chattermill-owning insights team.

_Caveats: Trustpilot sample is a 4-week most-recent window of the DE-language page — theme
*shares* are snapshot-level, not annual rates; app-store sample skews positive (store dynamics);
per-supplier attribution in a live deployment would come from booking data, not review text alone.
Method & compliance: see README._
