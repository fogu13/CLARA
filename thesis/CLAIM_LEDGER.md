# Claim-to-evidence ledger (12 September 2026 review: R0–R4, C1–C4, E1, E2)

One row per claim touched by the 12 September 2026 review. Appendix D remains the
traceability matrix by hypothesis and design principle; this ledger is the per-claim audit
of what evidence stands behind each sentence after the review edits, and is pointed to
from Appendix D. Line numbers are those of the manuscript files after the edits recorded
in commit history under the same date. Commits are the last commit that touched the
evidence artefact at the time of writing.

**Evidence types** (kept distinct throughout): authored fixtures · AI-generated labels ·
human labels · human-reviewed AI labels · star-rating proxies · simulated outcomes · model
comparisons · real intervention observations. Repeat runs on the same items are not
replication over new items.

**Status vocabulary:** supported · narrowed (claim retained in a weaker form) · pending
regeneration (evidence will be re-produced by a harness or code change) · pending human
collection (needs a person to rate, run, confirm or collect).

## R0 — provenance of the blind second risk rating

| # | Claim (file:line) | Evidence artefact (path @ commit) | Evidence type | Status | Note |
|---|---|---|---|---|---|
| R0.1 | The risk seed labels have one human check: a blind 40-item second rating, κ = 0.55 unweighted (0.38–0.72), 0.70 linear-weighted (0.56–0.82), 27/40 exact, 38/40 on escalate-or-not (`03_methodology.md:126`) | `thesis/evaluation/results/kappa_sample.csv` @ 24d56fc; `kappa_risk.json` @ 5ee0c35; rubric `kappa_labelling_instructions.md` @ c2d6f57 | human labels (on the owner's attestation) compared against AI-generated labels | narrowed | The statistic is reproducible from the files. What the rating *is* rests on attestation: `PROVENANCE_kappa.md` §3–§5. |
| R0.2 | The rater was a second person, not the author (`03_methodology.md:126`) | Owner's attestation of 12 Sep 2026 ("another rater"), recorded in `thesis/evaluation/results/PROVENANCE_kappa.md` (new file, this commit) | human attestation, not a committed artefact | narrowed; pending human confirmation | Identity, return time and AI exposure unrecorded; the external review's identical-label observation is unresolved (`PROVENANCE_kappa.md` §5). Alternative wording prepared in `review-2026-09-12-response-notes.md`. |
| R0.3 | "The one human check" echoes (`03_methodology.md:71`, `05_evaluation_results.md:100`, `06_discussion.md:49`, `appendices/D_traceability_matrix.md:33`, `02_literature_review.md:335`) | as R0.1 | as R0.1 | narrowed | Each carries the qualifier "a second person's rating on the owner's attestation, exposure to AI-generated suggestions unrecorded". |
| R0.4 | Deck and board formerly stated that no kappa and no second annotator existed (`defense/make_deck.js:191, 297, 314, 323, 336`; `board/board_spec.json` card `ladder`) | as R0.1 | as R0.1 | supported (contradiction removed) | Now state the κ with the same qualifier; the ask is a second *independent* human rating on a *new* sample, rater and date recorded. |

## R1 — held-out split of the in-repo golden set

| # | Claim (file:line) | Evidence artefact (path @ commit) | Evidence type | Status | Note |
|---|---|---|---|---|---|
| R1.1 | Held-out half: 96.7% sentiment (0.83–0.99), 93.3% urgency (0.79–0.98), n = 30, GLM-5.2; 90.0% / 80.0% on the production default (`05_evaluation_results.md:145, 148`; echoes `06_discussion.md:53`, `07_conclusion.md:5`, `appendices/B_eu_ai_act_gdpr_mapping.md:72`, `appendices/D_traceability_matrix.md:11, 33`) | `apps/api/app/evals/published_metrics.json` (`by_split`) @ bf26f3d; `golden_set.json` @ 5d250fb | authored fixtures (golden set; German and boundary items AI-audited) scored against model output | narrowed | Now stated as held-out *accuracies* of the exemplars-on configuration on a frozen validation split consulted on every run; not a held-out paired exemplar effect. |
| R1.2 | The held-out split is the confirmatory read of the urgency exemplar effect (former wording at `03_methodology.md:67`, `05_evaluation_results.md:150`) | none: no paired OFF/ON held-out result exists in any committed artefact | — | pending regeneration | The updated `run_live.py` (`by_split_ab`, other agent) will produce it on the next run; the manuscript now says the read has not been made. |
| R1.3 | Sentiment held-out "neither below the optimisation half" (former `05_evaluation_results.md:148`) | `published_metrics.json` `by_split` @ bf26f3d: held-out 0.9667 vs optimisation 1.0 sentiment; 0.9333 vs 0.90 urgency | authored fixtures | corrected | Rewritten: sentiment below by one item, urgency above; at n = 30 neither informative. |
| R1.4 | In-run exemplar effect, pooled over both halves: tags 9% → 25% (p = 0.002), urgency 78% → 91% (p < 0.001) on GLM-5.2; tags 2% → 16% (p = 0.001), urgency 82% → 82% on the production default (`05_evaluation_results.md:145, 150`) | `published_metrics.json` @ bf26f3d (GLM-5.2); production-default run unpublished, recorded in §5A.7 from the run output | authored fixtures; model comparisons (within-run paired) | supported as exploratory | Same-day re-runs bound model noise; not replication over items; sequential testing disclosed. |
| R1.5 | Split scored on every run since defined; at least five scorings; exact count not recoverable; pipeline changed after freeze on 8 Aug, 2 Sep, 5 Sep (`03_methodology.md:67`, `05_evaluation_results.md:148`) | git history: `published_metrics.json` commits a1c1b8e, e454898, 58504f3, 5d250fb, bf26f3d; `services/enrichment.py` c868476, 01ced20, 4bd1af8; `reports/` and `history.jsonl` gitignored | repository record | supported | Audit facts supplied with the review brief and checked against `git log` in this worktree. |

## R2 — comparative fairness inference

| # | Claim (file:line) | Evidence artefact (path @ commit) | Evidence type | Status | Note |
|---|---|---|---|---|---|
| R2.1 | Learned model escalation recall DE-source 62.5% (5/8; 31–86%) vs EN-source 95.1% (39/41; 84–99%), Fisher p = 0.026 (`05_evaluation_results.md:116–119`) | `thesis/evaluation/results/escalation_recall_by_language.csv`, `escalation_recall_fisher.csv`, `summary.json` @ 2598de5; `predictions_ml.json` @ 7ced4fd | AI-generated labels (seed risk) vs model output; model comparisons | narrowed | Reported as descriptive, exploratory, within-predictor; denominator 8 stated. |
| R2.2 | Contextual path 87.5% (7/8) vs 87.8% (36/41), p = 1.0; repeats 6/8 vs 32–33/41 (`05_evaluation_results.md:119`) | same files @ 2598de5; `predictions_llm.json` @ e032d16; repeats in `results_glm_generic_run1..3/` | as R2.1 | narrowed | Descriptive; the within-predictor test does not establish parity. |
| R2.3 | Former inference: significant-vs-non-significant ranks the learned model as "the equity-worst escalator" (former `06_discussion.md:69`; echoes `05:119`, `06:33`, `07:5`, `00:20`, `01:72`, deck 161/221/253/338) | none: no test on the difference of gaps exists in any committed artefact | — | rejected as an inference; replaced by a monitoring recommendation | Gelman & Stern (2006) cited at `05:119`, `06:33`, `07:5`; reference added. |
| R2.4 | A paired bootstrap and exact permutation test on the difference of gaps (`05_evaluation_results.md:119`) | `thesis/evaluation/equity_gap_bootstrap.py` + `test_equity_gap_bootstrap.py` (new, this commit); no `equity_gap_pairs.*` output exists | — (synthetic self-test only) | pending human collection (owner must run with `THESIS_DATA_DIR`) | Corpus absent in the writing environment; scikit-learn also absent, so `metrics.wilson_interval` falls back to an identical local formula there. |
| R2.5 | Gold-escalate counts: 50 over all 106 risk-labelled signals (23 high + 27 critical), 49 in the de+en strata (8 + 41), the fiftieth from a Dutch-language source (`05_evaluation_results.md:100, 119`) | `risk_confusion.csv` @ 71cefe3; `composition.csv` @ 2598de5 (row `nl,sector,fintech,…,1`) | AI-generated labels | supported | Both counts now stated with their definition. |
| R2.6 | "Warrants escalation" means labelled high or critical in the assistant-drafted reference, not established ground truth (`05:112`, `01:35`, `07:5`, `00:20`) | `load_datasets.py` docstring; §3.7 provenance | AI-generated labels | narrowed | "Genuinely critical" removed from the manuscript. |

## R3 — qualitative protocol

| # | Claim (file:line) | Evidence artefact (path @ commit) | Evidence type | Status | Note |
|---|---|---|---|---|---|
| R3.1 | Transcripts are analysed by codebook thematic analysis with a consensus codebook, a second coder (role), Cohen's κ ≥ 0.60 threshold and a reconciliation rule (`03_methodology.md:113, 144, 146`; `05_evaluation_results.md:187, 282`; `instruments/codebook_template.md:3`) | `thesis/instruments/codebook_template.md` (this commit); Braun & Clarke (2006, 2019, 2021) in `references.md` | protocol; no data yet | pending human collection | "Reflexive" label removed; no session run, no coder named. |
| R3.2 | Interview/task reporting tiers depend only on the interview count; survey tiers only on survey n; the survey never suppresses or upgrades interview findings; four cases resolved (`05_evaluation_results.md:170`) | `thesis/evaluation/survey_analysis.py` (`MIN_N = 10`) | protocol | pending human collection | The script writes a support label from n = 10; the manuscript records it as a descriptive count, not a verdict, below n = 40. The script was not changed. |

## R4 — deployment-configuration comparison

| # | Claim (file:line) | Evidence artefact (path @ commit) | Evidence type | Status | Note |
|---|---|---|---|---|---|
| R4.1 | Production stage GLM-5.2 (batch 10, 5 Sep) vs Mistral Small 4 (batch 25, 5 Sep): sentiment 0.83 → 0.84, 3 vs 5 discordant, p = 0.73; risk 0.50 → 0.59, 6 vs 16, p = 0.052 (`05_evaluation_results.md:92, 96, 98, 102`; `06_discussion.md:51`) | `thesis/evaluation/results/compare_runs_pairs.csv` (row `glm_production_vs_mistral_production`) and `compare_runs_accuracy.csv` @ e9e1dfb; `predictions_llm_production.json` (+ `.meta.json`, `model: glm-5.2`) @ 2598de5; Mistral run in `results_mistral-small-2603/` @ e512f83 | model comparisons against AI-generated labels and star-rating proxies | narrowed | Renamed from "model effect" to deployment-configuration comparison; p > 0.05 no longer read as sameness. |
| R4.2 | "No measured accuracy cost" of the sovereignty commitment on the seed-label corpus (`05:102`, `06:51`) | as R4.1 | as R4.1 | narrowed | Now: no cost was measured, which does not show there is none; an isolated model effect needs a matched rerun, not run. |
| R4.3 | Four-run stability of the production default: sentiment 0.843–0.850, risk 0.585–0.604, label agreement 99.3–100% / 97.2–100% (`05_evaluation_results.md:102`) | `thesis/evaluation/results_mistral-small-2603/compare_runs_accuracy.csv`, `compare_runs_agreement.csv`, `compare_runs_pairs.csv` (runs `mistral_run0..3`) @ e512f83 | model comparisons (same-item re-runs) | supported | Files now named exactly in the text; same-item re-runs bound model noise, not replication. |
| R4.4 | Golden-set comparison of the two models (production default four points below on sentiment, nine on urgency) (`05_evaluation_results.md:148`) | `published_metrics.json` @ bf26f3d (GLM-5.2); Mistral run unpublished, §5A.7 | authored fixtures; model comparisons | narrowed | Labelled a configuration comparison through the same runner on 6 Sep. |

## Code findings C1–C4, E1, E2 (manuscript wording; code changes by other agents)

The code changes for these findings are being made outside this worktree. The rows record
the manuscript sentence, the artefact it currently rests on, and that its evidence is
pending regeneration once those changes land. No manuscript sentence in this block was
changed in this pass; the wording is listed so that the sentence can be re-checked.

| # | Claim (file:line) | Evidence artefact (path @ commit) | Evidence type | Status | Note |
|---|---|---|---|---|---|
| C1 | No action reaches an external system without a recorded approval; the approval record carries the pre-decision evidence-pack hash (`04_artifact.md:79, 90`; `06_discussion.md:29`; `appendices/D_traceability_matrix.md:25, 55`) | `apps/api/app/routers/problems.py` @ 4bd1af8; `apps/api/app/services/action_push.py` @ 01ced20; `apps/api/app/tests/test_action_push.py` @ 4bd1af8 | authored fixtures (regression tests) | pending regeneration | Finding C1 (bind push retry to the approved action revision): whether a retried push is bound to the revision that was approved is what the fix establishes; the sentence stands as a design statement until the tests cover it. |
| C2 | When measurement is inconclusive the loop verdict stays open; closure is asserted only on evidence (`04_artifact.md:149`; `06_discussion.md:9` DP1) | `apps/api/app/services/outcome_engine.py` @ 4bd1af8; `services/measurement_scheduler.py` @ 01ced20; `tests/test_loop_closure.py`, `tests/test_review_outcome_loop.py` @ 4bd1af8 | simulated outcomes; authored fixtures | pending regeneration | Finding C2 (bind loop verdict to the actual closing observation). Outcome data behind every verdict so far is simulated (§6.4 item 4). |
| C3 | Contracts are proposed at approval time and are editable and declinable by the approver (`04_artifact.md:82`; `03_methodology.md:91`; deck slide B4 "no choosing a friendly metric afterwards") | `routers/problems.py` @ 4bd1af8; `tests/test_problem_updates.py` @ 4bd1af8 | authored fixtures | pending regeneration | Finding C3 (contract amendments must not reinterpret recorded observations): the manuscript does not yet say what happens to observations already recorded when a contract is edited; add one sentence once the rule is implemented. |
| C4 | The action is executed at day t₀, the execution day is excluded from the fit, and checkpoints run at T+7 / T+30 (`03_methodology.md:77–91`; `04_artifact.md:82`; `appendices/D_traceability_matrix.md:41, 43`) | `services/outcome_engine.py` @ 4bd1af8; `services/measurement_scheduler.py` @ 01ced20; `tests/test_outcome_engine.py`, `tests/test_measurement_scheduler.py` @ 4bd1af8 | authored fixtures; simulated outcomes | pending regeneration | Finding C4 (measurement clock needs an implemented action): which timestamp t₀ is read from is what the fix fixes; the manuscript's "executed at day t₀" should be re-checked against it. |
| E1 | The in-repo harness's designed inference is the within-run paired A/B; held-out failures are not used for tuning (`03_methodology.md:63–67`; `05_evaluation_results.md:135, 148, 150`) | `apps/api/app/evals/run_live.py`, `harness.py` @ 4bd1af8; `LOOP_PROMPT.md` @ 9ec9377; `tests/test_eval_harness.py` @ 4bd1af8 | authored fixtures; model comparisons | narrowed; pending regeneration | Finding E1 (harness validity): until the updated harness hides held-out failures and reports `by_split_ab`, the split is a consulted validation split (R1.5). |
| E2 | Per-language accuracies are published with their denominators (EN n = 72, DE n = 28; held-out n = 30) (`03_methodology.md:63`; `05_evaluation_results.md:148`; `appendices/B:72`; `appendices/D:33`) | `published_metrics.json` (`by_language`, `by_split`) @ bf26f3d | authored fixtures | supported; pending regeneration for the next publish | Finding E2 (denominators): the published snapshot carries them; the next publish should carry the split/exemplar/golden-set hashes the updated harness adds. |
| D-1 | Approval→outcome loop "verified running in production after interrupt-resume fix" (`appendices/D_traceability_matrix.md:25`; `04_artifact.md:147`) | `docs/archive/code-review-2026-07-02.md`; production deployment (not in repository) | real intervention observations of the *mechanism* on seeded and simulated data; no real outcome | supported as demonstration | Not a measured outcome: no live outcome contract on real data exists (§6.5 direction 3). |

## Human actions that remain (summary)

1. Confirm or correct the provenance of the 40 blind risk labels (R0.2); if a model produced them, apply `review-2026-09-12-response-notes.md`.
2. Collect a second, independent human rating on a new sample of the risk seeds, rater and date recorded, stored per `PROVENANCE_kappa.md` §6.
3. Run `thesis/evaluation/equity_gap_bootstrap.py` with `THESIS_DATA_DIR` set and quote its output in §5A.5 (R2.4).
4. Re-run the updated in-repo harness so that `by_split_ab` supplies the paired held-out exemplar effect (R1.2, E1), and update §3.5.3, §5A.7, §6.4, Chapter 7, Appendices B and D from it.
5. A controlled rerun with matched batch size and conditions if an isolated model effect is to be claimed (R4.2); otherwise the configuration wording stands.
6. Fill the second-coder role and run the practitioner study (R3); no placeholder was filled.
7. Re-check C1–C4 sentences against the merged code changes and regenerate the test evidence.
