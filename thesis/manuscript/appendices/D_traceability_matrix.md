# Traceability Matrix: Hypotheses → Questions → Evidence

This appendix makes the chain from claim to evidence auditable, and states honestly what each claim's **status** is: *measured* (quantified against data), *demonstrated* (instantiated and shown in the artifact), *perception* (assessed via practitioner instruments), or *pending* (instrument ready, data not yet collected). It is the single place to see what the thesis proves versus what it argues.

## Hypotheses

| # | Claim (abbreviated) | RQ | Instrument / data | Where | Status |
|---|---|---|---|---|---|
| H1 | Teams have insight but cannot act — the insight-action gap | RQ1, RQ4 | Interviews; artifact demonstration | Ch 4; §5B | demonstrated + pending (perception) |
| H2 | Signals are fragmented across sources; unified prioritisation is rare | RQ1, RQ4 | Interviews; multi-source ingestion + cross-signal severity | Ch 4 §4.5; §5B | demonstrated + pending |
| H3 | Signal type affects how reliably feedback can be classified/routed | RQ3 | Gold-set per-field metrics; convergent in-repo LLM eval (`CLARA/…/evals/history.jsonl`), golden set grown 60→80 items with a per-item **language** field (60 en / 20 de; the German stratum is *authored*, not naturally occurring — disclosed); per-language metrics published via `run_live --publish` → `published_metrics.json`, served at `GET /model-card/metrics` | §5A.3–5A.5; §5A.7 | **measured** (two independent gold standards) |
| H4 | Journey stage materially shapes prioritisation | RQ3, RQ4 | Gold-set (journey-stage field, open-vocab); interviews | §5A; §5B | partly measured + pending |
| H5 | Routing to the right owner is a recurring failure point | RQ1, RQ3 | Gold-set (owner field, open-vocab); interviews | §5A; §5B | partly measured + pending |
| H6 | Clear ownership / approval improves perceived trust | RQ2, RQ4 | Task sessions; TAM trust items 9–12 | §5B; App. A | pending (perception) |
| H7 | Stakeholders distrust action they cannot audit | RQ2, RQ4 | Task sessions; TAM trust items; SUS | §5B; App. A | pending (perception) |
| H8 | Closure is rarely practised, and valued when offered | RQ1, RQ4 | Interviews; outcome-contract demonstration | Ch 4 §4.4; §5B | demonstrated + pending |

## Design principles (the contribution)

| Principle | Source decision | Evaluated by | Status |
|---|---|---|---|
| DP1 — Closure is a contract, not a side effect | §4.3 outcome contract | Demonstration (Ch 4); perception (§5B); measurement design shipped and regression-tested (§3.5.5: ITS estimator, approval-time contract proposal, scheduled re-measurement; since 17–19 July 2026 also A–E evidence grading, measurement provenance, and guardrail measurement — table below); **live outcome contract on real data = future work** (in-repo outcome data still simulated) | demonstrated; **not yet measured** |
| DP2 — Organisational memory is perishable | §4.3.2 confidence decay | Demonstration (Ch 4); **influence measured**: remedy adoption 21%→71%, alignment lift 0.503 (§5A.7; `CLARA/…/evals/history.jsonl`, 2026-07-03); outcome benefit pending real outcomes | **partially measured** (influence yes; benefit pending) |
| DP3 — Severity emerges from the set | §4.3.3 cross-signal severity | Demonstration; gold-set risk field (proxy) | demonstrated; partly measured |
| DP4 — Graduate authority; make conflicts explicit | §4.3.1 rule resolution | Demonstration; task sessions (§5B); approval→outcome loop verified running in production after interrupt-resume fix (§4.7, §4.9) | demonstrated + pending (perception) |
| DP5 — Bounded model, deterministic loop | §4.2 architecture | Demonstration; §5A method-dependence finding; within-run A/B design handling model non-determinism (§5A.7) — the 17 July 2026 paired in-run A/B (exemplars off vs on, identical items) is the designed inference: exact-tag-set 8.75%→28.75%, McNemar *p* = 0.001 | demonstrated + **measured (indirect)** |
| DP6 — Adapt by configuration, not retraining | §4.3.5 industry profiles | Demonstration (`CLARA/…/domain/industry_profiles.py`); cross-industry real-data run: sector vocabularies emerge with no fine-tuning (§5A.7) | demonstrated; partly measured |

## Reading

The **measured** rows concern triage quality (RQ3) — a precondition of the loop — now corroborated by two independent gold standards (§5A.3–5A.6 seed labels; §5A.7 in-repo golden set + star-proxy). The in-repo corroboration has moved beyond its 60-case, 3 July 2026 state: the golden set was grown to 80 items by authoring 20 German cases (adversarially verified by two independent skeptic agents; 19/20 confirmed, exactly one urgency dispute accepted), and two production-config runs on 17 July 2026 bracket one eval–improve iteration. The published snapshot reports sentiment 97.50% (95% CI 94–100%), urgency 86.25% (CI 79–94%), and tag F1 (fuzzy) 80.17% at *n* = 80, with per-language accuracies published alongside their denominators; the DE/EN urgency gap narrowed from 6.7 pp to 1.7 pp with EN metrics unregressed. The designed inference is the **in-run paired A/B**, not the cross-run delta — the model is non-deterministic even at temperature 0: few-shot exemplars lift exact-tag-set agreement from 8.75% to 28.75% (McNemar *p* = 0.001), while the urgency effect (81.25%→86.25%, *p* = 0.219) is directionally positive but underpowered at *n* = 80. Two disclosures travel with these numbers wherever they appear: the German stratum is **authored**, not naturally occurring, and the hallucination heuristic is EN-scope only by construction. Of the **distinctive** claims, DP2's *influence* is now measured (remedy adoption, §5A.7) while its *benefit* — like DP1's — still awaits a live outcome contract on non-simulated data (Ch 6, §6.5, direction 3). H1 and H8 remain demonstrated and perception-tested. The matrix is the honest map of that boundary.

## Outcome-measurement design → implementation (§3.5.5)

| Design element | Code |
|---|---|
| Segmented-regression fit + CI | `outcome_engine.its_effect` |
| Series construction (complete UTC days, pre-window truncation, execution-day exclusion) | `outcome_engine.its_outcome_for_problem` |
| Contract proposal (trailing baseline, 30-day window, T+7 early read) | `outcome_engine.propose_outcome_contract` |
| Zero-input application at approval | `routers/problems.py` approval route |
| Scheduled T+7 / T+30 re-measurement | `measurement_scheduler.py` + `migrations/011` (pg_cron) |
| Exact-recovery + bias regression tests | `tests/test_outcome_engine.py` |
| Evidence grade A–E stamped on every outcome readout — grades the measurement *design* (A randomized holdout; B controlled quasi-experiment, reserved; C interrupted time series; D uncontrolled before/after; E manual assertion or unmeasured), computed identically on outcome board and problem detail | `outcome_engine.evidence_grade` |
| Measurement provenance (*instrumented* vs *manual*; manual values labelled "unverified manual observation"; the API route force-stamps manual so provenance cannot be spoofed by clients) | `routers/problems.py` measurement route |
| Guardrail measurement at every checkpoint (`repeat_signal_rate` vs the 28-day pre-window baseline, non-inferiority; breach = >20% relative worsening; informative, never blocking; unmeasurable guardrails surface an explicit "no data source" marker) | `measurement_scheduler.measure_guardrails` |
| Detectability note at contract proposal (two-sample Poisson normal-approximation MDE at 80% power; explicitly labelled a heuristic, not a formal power analysis) | `outcome_engine.detectability_note` |

## Trust and governance hardening → implementation (17–19 July 2026)

| Design element | Code |
|---|---|
| Published per-language metrics snapshot (n, per-language accuracies with denominators, CIs, dataset date, provenance notes) written only via an explicit publish step | `evals/run_live.py --publish` → `evals/published_metrics.json`; served at `GET /model-card/metrics` (`routers/system.py`) |
| Evidence-pack tamper evidence: canonical sha256 content hash, stable across re-exports of unchanged records; the approval route stamps the pre-decision hash on the append-only approval record | `evidence_pack.pack_content_hash`; approval route in `routers/problems.py` (`evidence_pack_hash`) |
| Approval reviewer identity bound to the verified login (JWT-derived pseudonym), replacing self-asserted request-body identity | `routers/problems.py` (pseudonym derived from the verified principal) |
| Four-eyes approvals (opt-in, admin-only workspace flag): two distinct approvers required; the first approval is recorded but holds execution; self-confirmation rejected; a rejection resets the tally | `routers/problems.py` (`four_eyes_approval` workspace flag) |
