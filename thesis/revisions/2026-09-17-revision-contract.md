# Revision contract, 17 September 2026

Binding instructions for the manuscript revision that answers the independent review of 17 September 2026 (ChatGPT) and the author's decision to cap the main text at 28,000 words (OPIT fact sheet: 10,000–20,000; the author accepts up to 28,000). Every editing agent reads this file first and obeys it over any chapter's current wording.

## 1. Scope decision

The thesis is narrowed to **technical design and bounded evaluation**. The practitioner study (RQ4) is reported as **not conducted** at the time of writing. Its protocol, instruments and pre-registered reporting tiers are retained (Appendix A; one short §5B) so that sessions run before submission can be reported under the tiers without rewriting the thesis. Nothing in the manuscript may call the artifact "useful", claim practitioner validation, or call zero-participant work "exploratory" or "small-N".

**Central claim (use this wording, verbatim or near-verbatim, in the abstract, §1.3 and Chapter 7):**

> This thesis develops and examines CLARA, a governed workflow that links customer feedback to approved actions, recorded outcome measurements and reusable learning records. The evaluation establishes selected technical properties and bounded enrichment performance on one corpus. Whether these mechanisms improve practitioner decisions and customer outcomes remains to be established.

## 2. Evidence map (the only permitted status vocabulary: *implemented and tested*, *demonstrated*, *measured (bounded)*, *descriptive*, *literature-supported motivation*, *not conducted*, *untested hypothesis*)

| Claim | Supported now | Open |
|---|---|---|
| RQ1 governed feedback-to-action architecture | Implemented architecture, worked demonstration, regression-tested mechanisms | Whether it improves decisions or resolves customer problems in practice |
| RQ2 governance | Specified and tested approval and provenance controls; a documented regulatory interpretation (Appendix B) | Whether people understand the controls, catch errors and accept their cost (friction clause: not conducted) |
| RQ3a enrichment | Agreement with star-rating proxies and assistant-authored reference labels on the 188-signal corpus | Agreement with independent human judgement; performance on natural deployment data |
| RQ3b escalation disparities | Descriptive differences across source strata; the German-source positive stratum has eight cases | A language effect, a fairness ranking of methods, or evidence of parity |
| RQ4 practitioner experience | Protocol and instruments | All empirical answers: not conducted |
| DP1 contracted, graded closure | Implemented; refusal below minimum data requirements tested | Benefit on live outcome data (the estimator has run on simulated outcome data only) |
| DP2 perishable memory | Implemented decay; retrieval changed recommendations on GLM-5.2 in small probes and did not on the production default | Whether decay changes retrieval appropriately or improves recommendations (untested hypothesis) |
| H1 insight-action gap, H2 fragmentation, H5 ownership, H8 closure | Literature-supported motivation | Practitioner evidence: not conducted |
| H3 signal-type reliability, H4 journey stage | H3 measured (bounded); H4 implementation evidence only (classifying a journey stage does not test whether stage changes prioritisation) | H4 practitioner evidence: not conducted |
| H6 approval and trust, H7 auditability and trust | Design commitments, implemented and tested | Not conducted |

Traceability matrix (Appendix D) rows must use these statuses. "Perception-tested" is banned. Implementing a unified platform is not evidence that organisations suffer fragmentation; a classifier ablation does not compare bounded workflows with autonomous agents.

## 3. Closure: three meanings, two measurements

Use these terms consistently: **delivery** (the approved action left the system: dispatch record with external reference), **target attainment** (a checkpoint reading over its frozen interval met the contracted threshold; grade D; the verdict `loop_closed` can be issued on attainment while the readout states that attribution is not established), **attributed improvement** (a fitted interrupted time series on the problem detail; grade C only when the segmented-regression fit was obtained; still not a validated causal design).

| Measurement | Estimand | Window | Grade | Role |
|---|---|---|---|---|
| Scheduled checkpoint | Signal rate over a fixed interval versus the contracted baseline | Interval frozen when the checkpoint was scheduled (T+7, window close, follow-up) | D | Decides target attainment and the loop verdict |
| Detail-view ITS estimate | Model-implied difference at the window end between the fitted post-intervention trend and the pre-intervention counterfactual | Complete UTC days from the plan origin, intervention day excluded | C when fitted, D when refused | Read-time estimate shown beside the checkpoint; never the verdict |

Rules: "refuses below its minimum data requirements (10 pre-days, 5 post-days)", never "refuses whenever underpowered". The guardrail is a **worsening-threshold check** (relative worsening above 20%), never "non-inferiority". Randomisation is infeasible *in the single-organisation pilot deployments considered here*, never "unethical or impossible for all remediation actions". A fitted model is not a validated causal design; seasonality, autocorrelation and time-varying confounding (Bernal et al., 2017) are interpretation caveats stated where the model is introduced. Worked example (§4.8): ticket dispatch → verified implementation date recorded by a reviewer → fixed observation window → observed recurrence result → qualified reviewer conclusion; the learning records an observed reduction after release, not a cause; say which steps of the example were executed on the demo dataset and which are illustrative; evidence is a paraphrase, not a verbatim; only sentiment, risk, journey stage and owner are scored in Chapter 5 (theme and action carry labels but no metric).

## 4. Canonical numbers (sources in brackets; no other numbers may be introduced)

Corpus (`corpus_stats.csv`, `composition.csv`): 188 signals, English paraphrases of public reviews, three sectors (fintech, food delivery, B2B industrial); 153 star-rated (sentiment gold: 94 negative, 9 neutral, 50 positive); 106 risk-labelled (36 low, 20 medium, 23 high, 27 critical); source-language strata German 45 signals (8 escalation-worthy), English 59 (41).

Accuracy with 95% Wilson intervals (`compare_runs_accuracy.csv`, `summary.json`):

| Task | Lexicon floor | TF-IDF + LR (5-fold CV) | Generic prompt, GLM-5.2 (run 0; repeats) | Production stage, GLM-5.2 | Production stage, Mistral Small 4 (default) |
|---|---|---|---|---|---|
| Sentiment (n = 153) | 0.37; macro-F1 0.37 | 0.78 (0.71–0.84); 0.52 | 0.86 (0.80–0.91); 0.67; repeats 0.86–0.87 | 0.83 (0.76–0.88); 0.68 | 0.84 (0.78–0.89); 0.64 |
| Risk, four-level (n = 106) | 0.41; 0.26 | 0.68 (0.59–0.76); 0.65 | 0.72 (0.62–0.79); 0.68; repeats 0.65–0.66 | 0.50 (0.41–0.59); 0.41 | 0.59 (0.50–0.68); 0.53 |

Paired exact McNemar, **one retrospective family per task of the nine unique comparisons** (Holm step-down; `paired_tests_holm.csv` after the tooling update; diff = second minus first accuracy with a Wald 95% interval):

| Task | Comparison | b / c | p | Holm (m = 9) | Diff (95%) |
|---|---|---|---|---|---|
| Sentiment | floor → TF-IDF | 15 / 78 | < 0.0001 | < 0.0001 | +0.41 (+0.31, +0.52) |
| Sentiment | floor → generic | 6 / 81 | < 0.0001 | < 0.0001 | +0.49 (+0.40, +0.58) |
| Sentiment | floor → production GLM | 7 / 77 | < 0.0001 | < 0.0001 | +0.46 (+0.37, +0.55) |
| Sentiment | TF-IDF → generic | 7 / 19 | 0.029 | 0.174 | +0.08 (+0.01, +0.14) |
| Sentiment | TF-IDF → production GLM | 12 / 19 | 0.281 | 0.906 | +0.05 (−0.03, +0.12) |
| Sentiment | TF-IDF → production Mistral | 9 / 18 | 0.122 | 0.610 | +0.06 (−0.01, +0.13) |
| Sentiment | generic → production GLM | 8 / 3 | 0.227 | 0.906 | −0.03 (−0.08, +0.01) |
| Sentiment | generic → production Mistral | 5 / 2 | 0.453 | 0.906 | −0.02 (−0.05, +0.01) |
| Sentiment | production GLM → Mistral | 3 / 5 | 0.727 | 0.906 | +0.01 (−0.02, +0.05) |
| Risk | floor → TF-IDF | 8 / 37 | < 0.0001 | 0.0001 | +0.27 (+0.16, +0.39) |
| Risk | floor → generic | 3 / 36 | < 0.0001 | < 0.0001 | +0.31 (+0.21, +0.41) |
| Risk | floor → production GLM | 4 / 14 | 0.031 | 0.124 | +0.09 (+0.02, +0.17) |
| Risk | TF-IDF → generic | 19 / 23 | 0.644 | 0.644 | +0.04 (−0.08, +0.16) |
| Risk | TF-IDF → production GLM | 36 / 17 | 0.013 | 0.064 | −0.18 (−0.31, −0.05) |
| Risk | TF-IDF → production Mistral | 27 / 18 | 0.233 | 0.465 | −0.08 (−0.21, +0.04) |
| Risk | generic → production GLM | 26 / 3 | < 0.0001 | 0.0001 | −0.22 (−0.31, −0.13) |
| Risk | generic → production Mistral | 18 / 5 | 0.011 | 0.064 | −0.12 (−0.21, −0.04) |
| Risk | production GLM → Mistral | 6 / 16 | 0.052 | 0.157 | +0.09 (+0.01, +0.18) |

Interpretation rules: the generic prompt's sentiment lead over TF-IDF is *stable across four repeated runs on the same items* (b = 7 throughout, c = 19 or 20, unadjusted p = 0.019–0.029) and *not significant after the retrospective Holm correction* (0.174); no comparison was declared primary before the runs, and all are exploratory. The only comparisons that survive the correction are the floor comparisons and the generic-versus-production-GLM risk contrast. A non-significant difference is not equivalence: write "the two are not distinguishable on this corpus", never "tie", "matches", "at least as good", "close to sufficient" or "earns its cost". Run-to-run stability (`compare_runs_agreement.csv`): production default 99.3–100% identical sentiment labels and 97.2–100% identical urgency labels across four runs; generic GLM-5.2 97.4–99.3% on sentiment and 85.8–94.3% on risk, the three September runs agreeing with each other on 93.4–94.3% and with the August run on 85.8–86.8%. Production-stage mixed handling: GLM-5.2 labelled 23 of 153 *mixed* and 1 *neutral* (Mistral 11 and 4); dropping mixed gives 0.94 (0.88–0.97, n = 130) and 0.89 (0.83–0.93, n = 142). Production risk shift: 100 of 106 predictions within one level of the seed label on GLM-5.2, 96 of 106 on Mistral; critical precision 1.00 / 0.77, recall 0.11 / 0.37; escalation recall 28 of 50 on either model (0.56) against 0.88 (generic run 0), 0.78–0.80 (repeats), 0.90 (TF-IDF); binary escalate-or-not accuracy 0.79 (0.71–0.86) GLM production, 0.78 Mistral, 0.92 generic.

Escalation recall by source stratum (`escalation_recall_by_language.csv`; Fisher `escalation_recall_fisher.csv`): German-source, 8 positives: floor 0 of 8 (0–32%), TF-IDF 5 of 8 (31–86%), generic 7 of 8 (53–98%), production 5 of 8; English-source, 41 positives: floor 8 of 41 (10–34%), TF-IDF 39 of 41 (84–99%), generic 36 of 41 (74–95%), production 22 of 41 (39–68%); Fisher p 0.32 / 0.026 / 1.0 / 0.72; generic repeats 6 of 8 against 32–33 of 41. Descriptive only; no ranking of predictors; the German-source stratum is almost entirely B2B industrial and the texts are English paraphrases.

Routing (`summary.json` closed-set blocks): constrained run, n = 182 (6 signals lost to endpoint errors; report coverage and end-to-end): journey stage 27 classes, majority floor 0.20, accuracy 0.59, macro-F1 0.50; owner 51 classes, floor 0.15, accuracy 0.40, macro-F1 0.32; on classes with at least five examples: macro-F1 0.55 / 0.42, accuracy 0.58 / 0.44. Do not claim the direction of any macro-F1 bias; do not call the supplied-inventory score an upper bound on free-form routing (it is a different, constrained task).

Second rating of 40 risk seeds (`kappa_risk.json`): κ 0.55 (0.38–0.72) unweighted, 0.70 (0.56–0.82) linear-weighted, 27 of 40 exact, 38 of 40 within one level, seven of ten seed-critical rated high; independent human provenance unresolved; never used as human validation.

In-repo golden set (`apps/api/app/evals/published_metrics.json`, 6 September 2026; a development and validation benchmark co-developed with the artifact, not independent confirmation): 100 items (72 EN / 28 DE); GLM-5.2 sentiment 99% (0.95–1.00), urgency 91% (0.84–0.95), tag F1 fuzzy 78.7%; held-out 30 items 96.7% / 93.3% (accuracies of the exemplars-on configuration on a repeatedly scored validation split); production default 95% / 82%, held-out 90.0% / 80.0%; exemplar A/B exact tag sets 9% → 25% (p = 0.002, GLM-5.2) and 2% → 16% (p = 0.001, Mistral); urgency 78% → 91% (p < 0.001, GLM-5.2) and 82% → 82% (Mistral); July trajectory in Appendix G.4. Learning-retrieval probe: remedy adoption 21% → 71% (3 July 2026, GLM-5.2, contemporaneous record only); 6 September: GLM-5.2 three of three themes, coverage 31% → 92%; production default one of four, 40% → 32%.

AI-authorship detectors (Appendix or one subsection): 6,740 texts; stylometric detector at 81% recall flagged 15.0% of genuine reviews (mean 2.21 stars against 2.70; flag rate 3.0× across languages); Binoculars-style AUROC 0.326 on English; abstains below ten words (23% of a real corpus). Detectability heuristic: break-even about 37.6 signals per day per theme for the default contract under the estimator's own variance, against 2.2 under the two-sample bound.

## 5. Deployment dating (new; from the 15 September 2026 outage investigation)

The platform has run in production since July 2026. On 15 September 2026 the serving API image was three weeks old (built in the last week of August 2026, before commit 01ced20 of 2 September). Therefore the following were **implemented and regression-tested at the cited commits but not deployed at the time of writing**: the readiness route and audit hardening (01ced20, 2 Sep), identifier redaction at the model boundary (4bd1af8, 5 Sep), measurement clock origins and bound readings (migration 016, 12–13 Sep), frozen contract terms, fixed observation intervals and explicit grades (be86add and migration 017, 13 Sep), and the binding of dispatch to the reviewed outbound content (d29b8b6, 13 Sep). Write "the build at commit …" or "implemented and tested" for these; reserve "deployed" and "in production" for what was live. Appendix G.8 records this; Chapter 4 states it once in §4.1.

## 6. Wording rules

Banned: "the honest reading", "the plain reading", "rather than smoothing over", "not a convenient interpretation", "the only basis … to be believed", "verified" for competitor claims (use "documented in the sources reviewed" / "not documented" / "contradicted by …"), "replicated" (use "stable across repeated runs on the same items"), "ties", "matches", "at least as good", "close to sufficient", "earns its cost", "safe to deploy at all", "expert labels" (use "reference labels" with provenance), "human-labelled" for any gold here, "exploratory" or "small-N" for the practitioner study, "verbatim" for paraphrased evidence, "non-inferiority", "natural experiment", "no single tool", "owned by no one", "no design-science artifact" without the search-scope qualifier below, "perception-tested", "externally-labelled".
Novelty: "within the literature and product documentation reviewed for this chapter (references; §6.3), no evaluated system was identified that combines …".
Approval gate: it controls false positives (wrong or harmful actions reaching an external system); it cannot recover escalation-worthy signals the enrichment ranks too low (22 of 50 under the seed labels on the production rubric). Say both wherever the gate is defended.
Citations: no new references may be added. Bone et al. (2017) supports only that soliciting feedback changes purchasing behaviour; the insight-action gap is supported by Forrester (2025b), Fazio et al. (2025), Homburg and Fürst (2005) and Wirtz et al. (2010). Hill et al. (2026) is an analogy and a reason to verify coding, not validation of the taxonomy design (κ ≈ 0.34 in a low-prevalence setting alongside high raw agreement).
Emphasis: reduce bold and italics to defined terms and table headers; remove journal names from running prose; use "GLM-5.2", "Mistral Small 4 (the production default)", "TF-IDF + logistic regression", "the generic prompt", "the production stage" consistently.
Every number must appear in §4 above or in a cited results file; agents may not compute new figures.

## 7. Structure, targets and ownership (main text ≤ 28,000 words; targets are ceilings)

| File | Target | Owner agent | Instructions |
|---|---|---|---|
| 00_front_matter.md | ≤ 900 | front-matter agent | Abstract: adopt the reviewer's abstract (in §9 below) with the canonical numbers. Acknowledgements: remove the interviewee clause. Generative-AI declaration: disclose assistant-led corpus collection, paraphrasing, de-identification and seed labelling (21 June 2026), AI reviewer agents on the golden set, AI coding assistants, and AI-assisted drafting and review of the manuscript; verification claims limited to work completed. Conflict statement: replace "externally-labelled" with "reference labels of stated provenance, a reproducible pipeline and standardised instruments". Data availability: an examiner package on request (paraphrased corpus, labels, immutable prediction files, run metadata, hashes). Contents note lists Appendices A–G. |
| 01_introduction.md | ≤ 1,800 | ch1 agent | One problem statement (§1.1–1.2 merged), one aim-and-RQ table, one evidence-status table (from §2 of this contract), the artifact in one paragraph, contributions as design knowledge, scope, structure. §1.7 loses the "accuracy bar"; practitioner work is "not conducted". Keep heading numbers 1.1–1.10 but they may be merged (state the final list). |
| 02_literature_review.md | ≤ 5,500 | ch2 agent | Reorganise as: 2.1 Turning feedback into accountable action (VoC, loops, NPS, multi-channel, condensed practitioner evidence with attributed commercial interest); 2.2 Enriching feedback under imperfect labels (sentiment, aspect, calibration, transformers, LLM coders); 2.3 Interpreting outcome evidence (experimentation, quasi-experiments, decision support, automation and human oversight); 2.4 Reusing knowledge under changing conditions (knowledge management, organisational learning, learning from failure); 2.5 Design Science Research; 2.6 Responsible AI and EU law (compressed; the article-level analysis lives in Appendix B); 2.7 The research gap (with the search-scope qualifier). Fold "recent developments" into 2.1–2.4. Remove market-size figures, acquisitions and vendor announcements that do not change a design decision. Publish the new heading map in the report. |
| 03_methodology.md | ≤ 4,700 | ch3 agent | One data-provenance account (§3.7, using the replacement paragraph in §9), one completed-methods account; §3.5.5 keeps the model, bias controls, minimum-data refusal, the two-measurement table and grades, with the causal caveats at the model; §3.6 stays as protocol (planned; double-coding planned; semantic adjudication planned, not executed); §3.8 "reference labels"; §3.10 shortened; run history and instrument instructions go to Appendix G / A. Keep heading numbers. |
| 04_artifact.md | ≤ 4,500 | ch4 agent | Centre §4.3 (decisions), §4.4 (controls, compressed to what the controls do and why the research adopts them; regulatory analysis by reference to Appendix B), §4.8 (rewritten per §3 of this contract), §4.1 with the deployment-dating sentence; compress §4.2 table, §4.5 (fix the "theme scored" sentence), §4.6, §4.7 and §4.9 to a short DSR iteration table plus pointers (Appendix G.8, repository history); the AI-detector experiment becomes one compact paragraph. Keep heading numbers. |
| 05_evaluation_results.md | ≤ 7,000 | ch5 agent | Production-first main table near the start (predictor, task, reference standard, eligible n, answered n, accuracy with interval, macro-F1, escalation recall); §5A.3–5A.4 rewritten to the interpretation rules; §5A.4.2 kept as a heading but shortened; §5A.5 shortened (descriptive only); §5A.6 one consistent statistical interpretation; §5A.7 condensed with the golden set called a development and validation benchmark; delete §5A.8 (pointer to Appendix F in §4.7); §5B collapsed to: 5B.1 status (not conducted), 5B.2 protocol pointer (Appendix A), 5B.3 reporting rule (the pre-registered tiers in one paragraph), no scaffold tables. Detailed pairwise tests and run histories move to Appendix G (short) or are dropped where the CSV is cited. |
| 06_discussion.md | ≤ 3,700 | ch6 agent | One principle / evidence / boundary table (DP1–DP7, each as context → mechanism → expected consequence → evidence → boundary); DP2 uses the replacement text in §9; §6.2 interprets, does not repeat; §6.3 competitor table with "documented / not documented / contradicted"; §6.4 one limitations account; §6.5 an ordered, bounded research agenda (five items, ≤ 250 words); §6.6 short. Keep heading numbers. |
| 07_conclusion.md | ≤ 700 | ch7 agent | Answer the RQs directly with the evidence-map statuses; RQ4 replacement sentence from §9; no rerun of Chapter 5; no "useful". |
| Appendices B, C, D, G; instruments | n/a | appendix agent | B: rewrite the Article 50 rows (50(2) is a provider marking duty on synthetic text output subject to the Act's exceptions, assessed by output and role, not by whether the deployer publishes; 50(4) is the deployer disclosure for public-interest text; keep the enacted-omnibus paragraph). C: distinguish a possible lawful basis and technical safeguards from a controller's completed assessment. D: statuses from §2; delete the duplicated results narrative; keep rows short. G: add the deployment dating (§5) to G.8; G.6 says the rerun is a prompt-and-pipeline configuration × model design (generic per item, production batched). Instruments: survey Q1e → "I'd be more comfortable letting software act on feedback automatically if a person approved each action before it was sent."; email opt-in moves to a separate, unlinked form; distribution copy moves to `instruments/survey_distribution.md` (not bound); interview guide T2 wording is the source of truth for §5B. |
| evaluation scripts | n/a | tooling agent | `multiple_comparisons.py`: one family per task with the nine unique comparisons (floor_vs_ml, floor_vs_llm, floor_vs_llm_production, ml_vs_glm_generic_run0, ml_vs_glm_production, ml_vs_mistral_production, glm_generic_run0_vs_glm_production, glm_generic_run0_vs_mistral_production, glm_production_vs_mistral_production), columns diff and Wald 95% interval, note column stating the family is retrospective; update its test. `run_matrix.py`: design string and docstring say "prompt-and-pipeline configuration × model; generic prompt per item, production stage batched"; update its test. `annotation_kit.py rescore`: add `--retrain-ml` that retrains TF-IDF + LR by stratified cross-validation on the human gold (via `ml_baseline.cv_predict`) and scores it as `ml_retrained`; update its test; docstring states exactly which question rescoring answers. |

Cross-references: chapters 1, 3, 4, 5, 6, 7 keep their heading numbers except the deletion of §5A.8 and the collapse of §5B.0–5B.5 into §5B.1–5B.3; Chapter 2 is renumbered per the map above. Every agent greps its own file for "§2." and "§5B." references and updates them to the new map; for any reference it cannot resolve it lists the reference in its report instead of guessing.

## 8. Tests and reporting

`thesis/test_manuscript_consistency.py` pins phrases from earlier review rounds. Editing agents do not touch it; they list in their report every test they expect to break and why. A later stage updates tests only where the pinned intent still holds under the new wording, with a one-line justification per change. `npm run thesis:test` and `python3 thesis/test_manuscript_consistency.py` must pass before commit. `bash thesis/build_docx.sh` must build.

Each agent's report (structured): file, words before, words after, final heading list, cross-references changed, numbers used with their source, tests expected to break, unresolved items.

## 9. Replacement passages (use as written, adjusting only cross-references)

Abstract:

> Customer-feedback systems can record that an action was taken without establishing whether the underlying problem improved. This design-science study develops CLARA, a workflow linking customer signals to human-approved actions, outcome contracts and reusable learning records. The design combines versioned measurement terms, explicit evidence grades and confidence-weighted retrieval of past conclusions.
>
> Evaluation examines technical controls and feedback enrichment on 188 English paraphrases of public reviews from three sectors. Against star-rating proxies on 153 items, the production configurations achieved sentiment agreement of 0.83–0.84, compared with 0.78 for a TF-IDF classifier. Against assistant-authored risk labels on 106 items, production agreement was 0.50–0.59; disagreement may reflect differences between the risk and urgency constructs. Source-stratum escalation comparisons are exploratory because language and sector are confounded and one positive stratum contains only eight cases.
>
> The artifact demonstrates an implementable approach to governed workflow execution and explicit outcome provenance. Practitioner usefulness, benefit from memory decay and improvement in real customer outcomes have not been established. The contribution is the integrated design and a set of provisional design principles, together with evidence about the limits of the enrichment and measurement components.

§3.7 second-rating paragraph:

> The corpus was collected, paraphrased and labelled in an assistant-led research session and has not been independently human-adjudicated. Customer star ratings provide a human-origin sentiment proxy; the remaining seeds are assistant judgements. A second rating of 40 risk-labelled items is available, but its independent human provenance is unresolved, so it is not used as human validation. Appendix G.1 documents the provenance and agreement statistics.

DP2:

> CLARA reduces a learning's retrieval weight with age using an explicit half-life. Small probes show that retrieval can alter recommendations on GLM-5.2, but this effect did not reproduce on the production-default model. The probes did not vary learning age or assess recommendation quality. Decay is therefore an implemented design hypothesis whose benefit remains untested.

Worked example ending:

> Creating the Jira item records operational delivery. If the feature is subsequently released, a reviewer records its implementation date and the observation window runs from that intervention. A qualifying checkpoint can show that complaint inflow met the contracted target. Without a defensible causal design, the learning records an observed reduction after release and its limitations, rather than asserting that the feature caused the reduction.

Conclusion, RQ4:

> RQ4 remains unanswered because the practitioner study was not conducted. The current evidence supports the feasibility of the architecture and bounded agreement with reference labels, but does not establish practitioner usefulness or improved customer outcomes.
