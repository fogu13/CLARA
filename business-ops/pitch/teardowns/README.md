# Loop readouts (private outreach artifacts)

One per target account: public feedback collected, run through **CLARA's production pipeline**
(`enrich_signals` with exemplars ON — the same code path as the committed in-repo evaluation — then
`synthesize_cluster` for the insight→action stage), aggregated into a two-page readout.

**Method & compliance (applies to all readouts):**

- **Sources:** Apple App Store reviews via Apple's public RSS/JSON feed (the sanctioned Phase-L1
  source in `business-ops/competitive/social-listening-plan.md`; DE storefront serves no entries —
  AT/CH storefronts used) **plus** a manually-read sample of recent public Trustpilot review pages,
  captured as **paraphrased research records** (the thesis-corpus method). No product scraping —
  CLARA's own Trustpilot connector stance ("own-presence listening only") is unchanged; in a real
  engagement the customer's own Trustpilot API key replaces the manual sample.
- **Privacy:** reviewer names pseudonymized/dropped at capture (sha256 pattern from
  `connectors/trustpilot.py`); no personal data stored; quotes in readouts are paraphrased.
- **Sampling honesty:** Trustpilot samples are the *most-recent* pages (a June–July 2026 snapshot),
  not a census; App Store feeds cap at the most recent ~50/storefront. Every stat carries its n and
  window. Trade Republic's Trustpilot stream is additionally skewed by **solicited/invited reviews**
  (flagged in the readout).
- **Enrichment ran on GLM 5.2 via a cloud gateway for this internal demo; the production offer is
  EU-resident / self-hostable — say so if asked.**
- **Usage:** private door-opener artifacts for the named account. Do **not** publish or mass-mail
  (UWG §7 / comparative-advertising review pending with the Fachanwalt, ~1 Aug).

Corpora + runner live outside the repo (session workspace); the readouts carry all numbers needed
for the conversation. Rebuild = re-pull feeds + re-run `run_teardown.py` (session tmp).
