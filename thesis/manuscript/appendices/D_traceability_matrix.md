# Traceability Matrix: Hypotheses → Questions → Evidence

This appendix makes the chain from claim to evidence auditable, and states honestly what each claim's **status** is: *measured* (quantified against data), *demonstrated* (instantiated and shown in the artifact), *perception* (assessed via practitioner instruments), or *pending* (instrument ready, data not yet collected). It is the single place to see what the thesis proves versus what it argues.

## Hypotheses

| # | Claim (abbreviated) | RQ | Instrument / data | Where | Status |
|---|---|---|---|---|---|
| H1 | Teams have insight but cannot act: the insight-action gap | RQ1, RQ4 | Interviews; artifact demonstration | Ch 4; §5B | demonstrated + pending (perception) |
| H2 | Signals are fragmented across sources; unified prioritisation is rare | RQ1, RQ4 | Interviews; multi-source ingestion + cross-signal severity | Ch 4 §4.5; §5B | demonstrated + pending |
| H3 | Signal type affects how reliably feedback can be classified/routed | RQ3a | Gold-set per-field metrics, all three predictors scored on the same gold since the 4 Aug 2026 LLM run (floor 0.37 → learned 0.78 → contextual 0.86 sentiment); convergent in-repo LLM eval (committed snapshot `published_metrics.json`; local run ledger), golden set grown 60→100 items with a per-item **language** field (72 en / 28 de; the German stratum is *authored*, not naturally occurring; disclosed); per-language metrics published via `run_live --publish` → `published_metrics.json`, served at `GET /model-card/metrics`; pairwise exact McNemar on identical items: contextual vs learned p = 0.029 on sentiment (significant), p = 0.644 on risk (not separable); per-source-language escalation recall for all three predictors in `evaluation/results/escalation_recall_by_language.csv` (learned model: DE-source 62.5% vs EN-source 95.1%) | §5A.3–5A.5; §5A.7 | **measured** (two independent gold standards) |
| H4 | Journey stage materially shapes prioritisation | RQ4 | Journey stage **now scored** under a supplied closed inventory: 0.59 accuracy against a 0.20 majority-class floor over 27 classes (§5A.4.1); an *upper* bound, since the supplied inventory is easier than free-form production generation; interviews still carry the prioritisation claim itself | §5A.4.1; §5B | **measured (bounded)** + pending (perception) |
| H5 | Routing to the right owner is a recurring failure point | RQ1, RQ4 | Owner **now scored** under the same supplied inventory: 0.40 accuracy against a 0.15 floor over 51 classes (§5A.4.1); clears the floor, but correct two times in five is explicitly *not* autonomous-routing accuracy, which is evidence for the approval gate (DP4) rather than against it; interviews carry the failure-point claim | §5A.4.1; §5B | **measured (bounded)** + demonstrated + pending |
| H6 | Clear ownership / approval improves perceived trust | RQ2, RQ4 | Task sessions; TAM trust items 9–12 | §5B; App. A | pending (perception) |
| H7 | Stakeholders distrust action they cannot audit | RQ2, RQ4 | Task sessions; TAM trust items; SUS | §5B; App. A | pending (perception) |
| H8 | Closure is rarely practised, and valued when offered | RQ1, RQ4 | Interviews; outcome-contract demonstration | Ch 4 §4.4; §5B | demonstrated + pending |

## Design principles (the contribution)

| Principle | Source decision | Evaluated by | Status |
|---|---|---|---|
| DP1: Closure is a contract, not a side effect | §4.3 outcome contract | Demonstration (Ch 4); perception (§5B); measurement design shipped and regression-tested (§3.5.5: ITS estimator, approval-time contract proposal, scheduled re-measurement; since 17 July 2026 also A–E evidence grading, measurement provenance, and guardrail measurement; table below); **live outcome contract on real data = future work** (in-repo outcome data still simulated) | demonstrated; **not yet measured** |
| DP2: Organisational memory is perishable | §4.3.2 confidence decay | Demonstration (Ch 4); **influence measured**: remedy adoption 21%→71%, alignment lift 0.503 (§5A.7; run of 2026-07-03, local eval ledger); outcome benefit pending real outcomes | **partially measured** (influence yes; benefit pending) |
| DP3: Severity emerges from the set | §4.3.3 cross-signal severity | Demonstration; gold-set risk field (proxy) | demonstrated; partly measured |
| DP4: Graduate authority; make conflicts explicit | §4.3.1 rule resolution | Demonstration; task sessions (§5B); approval→outcome loop verified running in production after interrupt-resume fix (§4.7, §4.9) | demonstrated + pending (perception) |
| DP5: Bounded model, deterministic loop | §4.2 architecture | Demonstration; §5A method-dependence finding; within-run A/B design handling model non-determinism (§5A.7); the paired in-run A/B (exemplars off vs on, identical items) is the designed inference: exact-tag-set 8.75%→28.75%, McNemar *p* = 0.001 (17 July 2026, *n* = 80) and urgency 83%→90%, *p* = 0.039 (*n* = 100) | demonstrated + **measured (indirect)** |
| Ingestion authenticity review (§4.4) | Provenance/duplication/burst/uniformity findings, annotated not enforced | Measured on 6,740 real feedback texts: shipped gate flags 0.86% of 6,154 genuine reviews (all true duplicates) and abstains on 25.1%; the two rejected text-forensic detectors measured 15.0% false-positive rate with a 3.0x cross-language spread, and AUROC 0.326 (worse than chance) respectively | **measured, including the negative result**; per-comment AI authorship deliberately **not implemented**; component not yet in the deployed build |
| DP6: Adapt by configuration, not retraining | §4.3.5 industry profiles | Demonstration (`CLARA/…/domain/industry_profiles.py`); cross-industry real-data run: sector vocabularies emerge with no fine-tuning (§5A.7) | demonstrated; partly measured |

## Reading

The **measured** rows concern triage quality (RQ3a) and escalation equity (RQ3b), a precondition of the loop, now corroborated by two independent gold standards (§5A.3–5A.6 seed labels; §5A.7 in-repo golden set + star-proxy). Since 4 August 2026 both streams score the same LLM path, so the corroboration is a genuine comparison rather than two adjacent stories: 0.86 sentiment accuracy against the independent star proxy, 0.97 against curated in-repo labels; the divergence is expected, and the conservative figure is the one quoted. The in-repo corroboration has moved beyond its 60-case, 3 July 2026 state: the set grew to 80 items by authoring 20 German cases (adversarially verified by two independent skeptic agents; 19/20 confirmed, exactly one urgency dispute accepted), then to **100 items (72 en / 28 de)** with the German stratum completed to the two-tag rubric. The published snapshot (18 July 2026) reports sentiment **97%** (95% CI 93–100%), urgency **90%** (CI 84–95%), and tag F1 (fuzzy) **82.7%** at *n* = 100, with per-language accuracies published alongside their denominators; the DE/EN urgency gap stands at roughly one percentage point. The designed inference is the **in-run paired A/B**, not the cross-run delta; the model is non-deterministic even at temperature 0: few-shot exemplars lift exact-tag-set agreement from 8.75% to 28.75% (McNemar *p* = 0.001), and at *n* = 100 the urgency effect reaches significance too (83%→90%, *p* = 0.039, three consecutive runs) after being reported as underpowered and **not claimed** at *n* = 80 (*p* = 0.219). Tag metrics are not comparable across the DE-rubric completion, which improved them partly by construction; disclosed in the published provenance. Two disclosures travel with these numbers wherever they appear: the German stratum is **authored**, not naturally occurring, and the hallucination heuristic is EN-scope only by construction. Of the **distinctive** claims, DP2's *influence* is now measured (remedy adoption, §5A.7) while its *benefit*, like DP1's, still awaits a live outcome contract on non-simulated data (Ch 6, §6.5, direction 3). H1 and H8 remain demonstrated and perception-tested. The matrix is the honest map of that boundary.

## Outcome-measurement design → implementation (§3.5.5)

| Design element | Code |
|---|---|
| Segmented-regression fit + CI | `outcome_engine.its_effect` |
| Series construction (complete UTC days, pre-window truncation, execution-day exclusion) | `outcome_engine.its_outcome_for_problem` |
| Contract proposal (trailing baseline, 30-day window, T+7 early read) | `outcome_engine.propose_outcome_contract` |
| Zero-input application at approval | `routers/problems.py` approval route |
| Scheduled T+7 / T+30 re-measurement | `measurement_scheduler.py` + `migrations/011` (pg_cron) |
| Exact-recovery + bias regression tests | `tests/test_outcome_engine.py` |
| Evidence grade A–E stamped on every outcome readout: grades the measurement *design* (A randomized holdout; B controlled quasi-experiment, reserved; C interrupted time series; D uncontrolled before/after; E manual assertion or unmeasured), computed identically on outcome board and problem detail | `outcome_engine.evidence_grade` |
| Measurement provenance (*instrumented* vs *manual*; manual values labelled "unverified manual observation"; the API route force-stamps manual so provenance cannot be spoofed by clients) | `routers/problems.py` measurement route |
| Guardrail measurement at every checkpoint (`repeat_signal_rate` vs the 28-day pre-window baseline, non-inferiority; breach = >20% relative worsening; informative, never blocking; unmeasurable guardrails surface an explicit "no data source" marker) | `measurement_scheduler.measure_guardrails` |
| Detectability note at contract proposal (two-sample Poisson normal-approximation MDE at 80% power; explicitly labelled a heuristic, not a formal power analysis) | `outcome_engine.detectability_note` |

## Trust and governance hardening → implementation (17 July 2026)

| Design element | Code |
|---|---|
| Published per-language metrics snapshot (n, per-language accuracies with denominators, CIs, dataset date, provenance notes) written only via an explicit publish step | `evals/run_live.py --publish` → `evals/published_metrics.json`; served at `GET /model-card/metrics` (`routers/system.py`) |
| Evidence-pack tamper evidence: canonical sha256 content hash, stable across re-exports of unchanged records; the approval route stamps the pre-decision hash on the append-only approval record | `evidence_pack.pack_content_hash`; approval route in `routers/problems.py` (`evidence_pack_hash`) |
| Approval reviewer identity bound to the verified login (JWT-derived pseudonym), replacing self-asserted request-body identity | `routers/problems.py` (pseudonym derived from the verified principal) |
| Four-eyes approvals (opt-in, admin-only workspace flag): two distinct approvers required; the first approval is recorded but holds execution; self-confirmation rejected; a rejection resets the tally | `routers/problems.py` (`four_eyes_approval` workspace flag) |
