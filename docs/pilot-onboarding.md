# Pilot Onboarding Runbook — the 30-minute cold start

The scripted discovery-call choreography: from an empty workspace to a governed,
measured action in under 30 minutes, on the prospect's own data or the bundled
per-ICP demo dataset. Every step below maps to a demo-wow moment from the
strategy doc (§9).

## 0 · Before the call (10 min, once per prospect)

1. **Fresh workspace** (local-first):
   ```bash
   rm -f apps/api/.data/clara.db          # wipe the demo workspace
   cd apps/api && uvicorn app.main:app --port 8000   # terminal 1
   npm run web:dev                                    # terminal 2 → localhost:3000/dashboard
   ```
2. **Pre-wire the demo Jira** (Integrations → Jira): base URL of a Jira project
   YOU control (e.g. `https://<you>.atlassian.net`, project `CLARA`), email +
   API token. Test with *Save → Test*. This powers the close-a-loop-live moment.
3. **Optional Slack**: bot token + a channel the prospect can see → the digest
   and approval notifications land there live.
4. Have the prospect export a CSV from their helpdesk (any columns — only
   `feedback_text` is required). If they can't, use the bundled dataset for
   their ICP:
   | ICP | dataset_id |
   |---|---|
   | Fintech / regulated DACH | `fintech_identity` (24 signals, DE+EN, 3 themes) |
   | B2B SaaS | `saas_onboarding` |
   | E-commerce / delivery | `ecommerce_checkout`, `retention_cancellation` |

## 1 · Cold start (minutes 0–10) — "no taxonomy to build"

1. **Import** — either the prospect's CSV (Signals → upload; only
   `feedback_text` must map) or:
   ```bash
   curl -X POST localhost:8000/demo-datasets/fintech_identity/import -H 'Content-Type: application/json' -d '{}'
   ```
   Timestamps auto-rebase to "yesterday" so every chart is live.
2. **Dashboard** (30 s): signal-volume trend + emerging-problems radar are already
   populated. *"This issue first appeared in German-language tickets — here's its
   trajectory."*
3. **Taxonomy → "Bootstrap themes from signals"**: confidence-scored theme
   proposals appear (German feedback handled natively). **Accept/reject live** —
   AI proposes, the human governs, every decision is versioned.

## 2 · Close a loop, live (minutes 10–20)

4. **Signals → candidates**: promote the top candidate. Its outcome contract is
   auto-captured (complaint rate/day baseline from its own signals — show it).
5. **Insight detail**: statement, root-cause hypothesis, evidence with sources,
   affected cohort, action portfolio, governance checks. If a policy blocks —
   better: *"no autonomous actions, ever."*
6. **Approve the product-fix action** → the real Jira ticket appears in the
   pre-wired project, on screen. Show the execution record: external ref + audit
   detail.
7. Point at **Learnings → Measurement checkpoints**: T+7 and window-close are
   already scheduled. *"CLARA measures whether this actually worked — from real
   signal data, automatically."*

## 3 · Receipts (minutes 20–30)

8. **Ask CLARA** (Insights page): ask the prospect's own question
   (*"What are customers saying about withdrawals?"*). Answer with inline
   citations + confidence. Ask something the data can't answer → **it refuses**.
   That refusal is the trust moment.
9. **Evidence pack** (insight detail → Evidence pack): the full audit story as a
   fileable document. *"This is what your compliance team gets."*
10. **Compliance page**: model card (live), data residency, GDPR Art. 17/20
    endpoints, downloadable audit log.
11. **The follow-up-call hook**: schedule call 2 "after the first measurement
    window" — open Learnings and press **Run due now** on that call:
    *"here's the outcome CLARA measured since we last spoke."*

## Push ingestion (if the prospect asks "can you connect X?")

Anything that can POST JSON can feed CLARA today:
```bash
SECRET=<shared secret from Integrations → Webhook>
BODY='{"signals":[{"feedback_text":"Die Zahlung schlägt fehl","source":"crm"}]}'
SIG="sha256=$(printf '%s' "$BODY" | openssl dgst -sha256 -hmac "$SECRET" | cut -d' ' -f2)"
curl -X POST localhost:8000/ingest/webhook -H "x-clara-signature: $SIG" -d "$BODY"
```
Native connectors beyond Zendesk/Jira/Slack are built against signed pilots, not
speculatively.

## Talking points to keep handy (claims discipline)
- Lead with the **mechanism**: policy-gated action → real execution → measured
  outcome → retained learning. (Never the bare slogan "we close the loop".)
- Confidence scores with receipts everywhere — including the eval page if they
  want the methodology.
- Residency + transparency, never "more secure than X": EU-resident by design,
  certification roadmap dated and budgeted, audit rights contractual.

## Pilot success metrics (agree these BEFORE the pilot starts)

Adopted from the Jul-2026 external strategic review — a six-week "Governed CX
Action Pilot" is judged on numbers both sides can verify in the product:

- **Time from signal to validated problem** (telemetry: time-to-first-insight).
- **Precision of high-priority alerts** (emerging "action" candidates the team
  confirms as real — corroboration floor keeps this honest).
- **% of claims with traceable evidence** (evidence-pack coverage; content hash
  proves what the approver saw).
- **Approval cycle time** and **policy-block rate + justified overrides**
  (governance working ≠ governance stalling).
- **Action execution completion** (approved → pushed, with external refs).
- **Outcome measurement coverage** (% of executed actions with a readout;
  evidence grade A–E on each readout) and the **estimated effect ± CI**.
- **Reviewer agreement / override behaviour** (how often humans overrule the
  model — trust calibration, not a performance score for individuals; keep
  works-council mode semantics in mind: aggregates only).
- **Connector uptime and data freshness** during the pilot window.

Walk the prospect through this list at kickoff, capture baseline values in the
first week, and export the evidence pack + telemetry CSVs for the closing
readout. "Prove it worked" is only claimable for grade A/B readouts — grade C/D
say "estimated effect", grade E says "observed, unverified".
