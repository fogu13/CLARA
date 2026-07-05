# CLARA full feature walkthrough — synthetic dataset (2026-07-05)

Environment: **live local workspace** (localhost API → Supabase Pro, Mistral
`mistral-small-latest` + `mistral-embed` configured via the Settings GUI).
Dataset: **150 generated signals** across 5 journeys (onboarding/verification,
purchase/checkout, billing/invoicing, support, renewal/cancellation), DE/EN mixed,
timestamps spread over 30 days with a deliberate 3-day checkout spike, 40 test
customers (`C-T001…C-T040`) across 10 accounts, plus 40 customer-context rows and
60 journey events. Imported as two batches (140 + 10 sacrificial) so the
remove-batch feature could be exercised destructively.

## Feature matrix

| # | Feature | Result | Evidence |
|---|---|---|---|
| F1 | CSV validate + import | ✅ | 140/140 importable, 0 errors; import 140/0 dupes |
| F2 | Second import batch | ✅ | 10 imported, batch identity preserved |
| F3 | Webhook intake (HMAC) | ✅ | 2 signals accepted with valid signature; **bad signature → 401** |
| F4 | Journey events import | ✅ | 60/60 |
| F5 | Customer context import + completeness | ✅ | 40 imported; report `ready`, sparse rows surfaced |
| F6 | Language quality report | ✅ | 255 signals; DE 157 / EN 87 / FR 11; DE+EN ready |
| F7 | Problem candidates | ✅ | 13 journey-grouped candidates (Checkout 41 sigs / 25 customers); dupe-detection flagged Identity Verification vs seed problem |
| F8 | Emerging radar | ✅ | 13 candidates, all action-grade |
| F9 | Triage pipeline (255 signals) | ✅ | 101s, **255/255 enriched**, 23 insights, 0 errors; **trend engine differentiates**: spike themes `rising`, recent `new`, others `stable`/`falling` |
| F10 | Taxonomy bootstrap (embeddings) | ✅ | 250 scanned → 6 proposed categories in 8.4s (checkout_errors conf 0.77 / n=137) |
| F11 | Category governance | ✅ | accept → rename → lock all 200 with change history |
| F12 | Taxonomy hygiene | ✅ | healthy; 0 duplicates/stale/drifted |
| F13 | Candidate → problem promotion | ✅ | cohort 25 customers / 11 accounts / 1 high-value; context+journey enrichment attached; 5 action proposals |
| F14 | Affected-context explorer | ✅ | accounts/customers/missing-IDs/routing recommendations |
| F15 | Approval → execution → Jira draft → checkpoints | ✅ | execution + draft created; 2 measurement checkpoints scheduled; **repeat approval → 409** (#84 guard live) |
| F16 | Scheduled measurement run-due (time travel) | ✅ | 1 measured, 1 manual_required, 2 skipped |
| F17 | Outcome recording + stale guard | ✅ | snapshot `target_met` (decrease-aware); **older measured_at → 409** — fired against the scheduler's auto-measurement, exactly as designed |
| F18 | Learning conclusion + closure | ✅ | learning gate satisfied post-measurement; closure with trusted tenant/actor headers |
| F19 | Triage resume (approval interrupt) | ✅ | action→measure→learn ran to `learned`; 23 approved insights; actions correctly `no_connector` |
| F20 | Ask CLARA | ✅ | grounded, cited answer on German billing question (run before the stall episode; see issue 1) |
| F21 | Evidence pack / audit export / CSV export / telemetry | ✅ | 10-section pack; audit trails populated; problems.csv; 20+ telemetry event types |
| F22 | GDPR export + erasure | ✅ | C-T040: 2 signals + 1 event + 1 context exported, then erased to 0/0/0 |
| F23 | API keys | ✅ | mint (plaintext shown once) → authed read → revoke |
| F24 | Slack digest + alert sweep | ✅ | no connector → preview mode (498-char digest), no false pushes |
| F25 | **Remove import batch** (new) | ✅ | sacrificial batch: 10/10 deleted, totals correct |
| F26 | Connector secret redaction | ✅ | webhook secret reads back `***redacted***` |

Dashboard verified in-browser after the walkthrough: 3 problems, 1 target-met
outcome, approval/execution counters correct, journey-grouped emerging radar.

## Issues found

1. **[HIGH — fixed during the test] Supabase connection exhaustion caused multi-minute
   request hangs.** Every store call opened a fresh session-pooler connection with no
   `connect_timeout`; under walkthrough burst load, new connects queued indefinitely,
   and each stuck request parked an `idle in transaction` session (observed up to
   **10.4 hours old**, incl. from a zombie dev-server process) that consumed another
   pooler slot — a self-reinforcing stall. GDPR export (4 sequential connections per
   request) hung 4/7 attempts; `/export/problems.csv` once. **Fix applied:** shared
   `psycopg_pool.ConnectionPool` per DATABASE_URL (max 5, 15s bounded wait, 10s
   connect timeout) in `PostgresConnectionMixin` — 15/15 burst requests green after.
   Shipped as its own PR. This would have hit Render in the first pilot demo.
2. **[MEDIUM] Severity saturates at critical** (18 of 23 insights) even with context
   data present. The 8-factor model needs calibration/spread — pilots can't
   prioritise a wall of red.
3. **[LOW] Cluster fragmentation persists**: two VAT-error insights
   (`billing_error` n=9 / `invoice_error` n=4) and two `app_crash` insights didn't
   merge. Same token-jaccard threshold tuning opportunity as the E2E test.
4. **[LOW] Webhook signals without a timestamp default to epoch 1970**, which
   stretches problem cohort date ranges ("1970-01-01 to …"). Defaulting to
   ingest-time would be more honest.
5. **[OBSERVATION] Two dev-server processes from prior sessions survived kills** and
   kept background loops + leaked connections against Supabase. Local hygiene issue,
   but reinforces the pool fix: production restarts (Render deploys) would strand
   sessions the same way until TCP timeout.

## What impressed

- The **governed loop is real end to end**: interrupt → human approve → execute →
  scheduled re-measurement → direction-aware outcome → learning record, with every
  step auditable in the evidence pack.
- **Bilingual clustering just works**: German and English complaints about the same
  defect land in one insight with grounded tags.
- **Security posture held at every trust boundary tested**: HMAC webhook (bad sig
  401), API-key lifecycle, secret redaction, duplicate-approval 409, stale-outcome
  409, GDPR erasure to zero.
