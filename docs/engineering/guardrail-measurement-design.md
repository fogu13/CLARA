# Guardrail measurement — design (external-review item 16)

_Status: design agreed, implementation scheduled with the next measurement-engine
session. Written 17 Jul 2026 as the follow-up the review response deliberately
deferred: "guardrail metrics are declared but never measured — decorative"._

## Verified current state

- `OutcomeContract.guardrail_metrics` is populated at proposal time (e.g.
  `repeat_signal_rate`, `unsubscribe_or_opt_out_rate`) and copied forward, but
  **nothing measures it**: `measurement_scheduler` reads only `primary_metric`,
  ITS scores only the primary series.
- The SQLite `outcomes` table is keyed by `problem_id` (one row per problem,
  upsert) — guardrail readouts cannot reuse it without a breaking PK change.

## Metric semantics (measurability classes)

| Guardrail | Class | Definition when measurable |
|---|---|---|
| `repeat_signal_rate` | **measurable from signals** | Post-execution signals/day matching the problem's theme from customers seen in the pre-window cohort (repeat complainers). Honest counts: exclude `unknown_*` identity buckets — identifier-less signals cannot prove a repeat. |
| `unsubscribe_or_opt_out_rate` | **no data source yet** | Requires outbound sends + opt-out events; neither exists (no customer-facing connectors are live). Report "no data source", never a number. |
| future `contact_rate` / `complaint_rate` | measurable from signals | Same rate machinery as the primary metric, different filter. |

The class is decided per metric NAME at measurement time; unmeasurable
guardrails surface as an explicit "no data source" line — the decorative
failure mode (silently unmeasured) is the thing this design kills.

## Statistical treatment

- Guardrails are **non-inferiority checks against the pre-window baseline**,
  not experiments: the question is "did the action make this worse", so a
  one-sided worsening threshold (default: >20 % relative worsening of the
  guardrail rate, configurable) marks the readout `guardrail_breach`.
- **No significance theater at current n**: report rate, baseline, and the
  breach flag. CIs/alpha-spending join when real outcome volume justifies the
  CUPED/power roadmap (same gate as the deferred experiment machinery).
- A breach is **informative, never blocking** at pilot scale — it appears on
  the readout and in the evidence pack, feeding the learning conclusion
  (worked-but-breached-guardrail ⇒ `partially_worked`, human-decided).

## Implementation sketch (M, one session)

1. New store table `guardrail_measurements(problem_id, metric, observed_value,
   baseline, breached, measured_at)` — append-only, all three store impls
   (in-memory / SQLite / Postgres jsonb payload; the outcomes-table PK stays
   untouched).
2. `measurement_scheduler`: at each existing checkpoint, measure every
   *measurable* declared guardrail with the same rate machinery as the primary
   (`SIGNAL_METRIC_PREFIX` filters + pre-window cohort join for repeats);
   record "no data source" markers for unmeasurable ones once per contract.
3. `OutcomeSnapshot.guardrails: list[...]` — metric, value, baseline, status
   (`ok | breach | no_data_source`), rendered as one line per guardrail on the
   outcome board and in the evidence pack (hash-covered like everything else).
4. Tests: breach detection both directions, unknown-identity exclusion in the
   repeat cohort, no-data-source marker, snapshot/pack rendering.

## Non-goals

- Blocking executions on guardrail forecasts (policy engine territory, not
  measurement).
- Per-guardrail MDE/power — the contract-level detectability note already
  flags underpowered windows; guardrails inherit the same caveat.
