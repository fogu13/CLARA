# Revision of 5 September 2026: what was done, and what needs the author

This file closes the review cycle that began with `review-2026-09-02.md` and `review-2026-09-04-addendum.md`. The decisions taken were **2a = A** (re-run the corpus through the production `enrich_signals` path; script prepared, run pending), **2b = A** (redaction before model input, implemented and tested) and **2c = B** (describe CLARA as approval-only; DP4 reframed as authority graduated by consequence class; the first cycle's rule resolver recorded in §4.7). Everything below that says "done" is committed on `claude/thesis-review-critique-afwkm7`; everything under "needs the author" cannot be done from this environment.

## Done (six commits)

| Commit | Scope |
|---|---|
| Phase 1 | PII redaction before model calls in enrichment and synthesis, with tests; `evidence_grade` re-graded on the realised ITS fit (refusal reads D), with unit and route tests; thesis harness: `labels=` in the restricted macro-F1, Wilson intervals on every accuracy and recall, Fisher exact tests and composition tables, per-class and confusion outputs for all predictors, by-source slices, the one-flip McNemar fragility p, `predict_llm_production.py` with pre-registered rules and `*_llm_production` scoring, `survey_analysis.py` verdict logic; in-repo eval: Wilson intervals and held-out split reporting. API suite 850 passed; lint clean; thesis self-checks pass; synthetic end-to-end run of `run_eval.py` verified. |
| Phase 2 | Appendix E extracted from the migrations and boot DDL; ER diagram and the four architecture, pipeline and sequence diagrams redrawn to the deployed build and re-rendered locally (mermaid-cli); Figure 4.6/4.7 captions state seeded data and what 4.7 shows; defence deck corrected (Bone, auto_execute, PII-in-Postgres, rule resolver, endpoint count) and rebuilt. |
| Phase 3 | Chapter 4 truth pass; Appendix B relabelled obligation vs commitment with Article 50 by paragraph and the Omnibus as Regulation (EU) 2026/1744; Appendix C as provider-prepared assessment; Appendix D aligned; statistics corrected in §5A.4.1, §5A.5, §5A.7, Ch 7; Chapter 6 DP4, §6.3, §6.4 (numbered), §6.6; instruments (outreach split out, consent durations, SUS anchors, reverse-keyed friction items, time-cost probe, survey logic). |
| Phase 4 | Chapter 2 cuts and renumbering; hypotheses demoted; evidence framing reversed; §3.10–3.12 merged; §5A.7 compressed; external-review episode to Appendix F; fallback protocol for §5B; DP1 restated, DP3/DP6 demoted, DP7 added, "why not an agent"; abstract rewritten. |
| Phase 5 | 40 in-text citations reworded to what their sources show; 25 reference entries corrected, 22 added, 36 uncited removed, peer-reviewed sources refiled, legislation section. |
| Phase 6 | Build script fixed (Appendix A headings demoted, pandoc located in `.venv`); document built (`build/thesis.docx`, 2.0 MB; gitignored); cross-reference, figure and image checks pass; README updated; this checklist. |

## Needs the author: runs that need the data or an API key

Run these in order; each feeds the next. Every place in the manuscript that waits on a run carries a marked placeholder (`‹…›`).

1. **Regenerate the harness outputs before anything else.** `THESIS_DATA_DIR=… python thesis/evaluation/run_eval.py`, then `git diff thesis/evaluation/results/`. Expected changes: `f1_macro_on_supported` ≈ 0.54 (journey) and ≈ 0.37 (owner); `composition.csv` with 38/39 German-source B2B (37/37 star-rated) and 58/67 English-source fintech (36/45); `escalation_recall_fisher.csv` with p ≈ 0.026 (learned), 0.32 (floor), 1.0 (contextual), and Wilson intervals; `mcnemar_paired.csv` with `p_if_one_pair_flipped`; `sentiment_by_source.csv` (H3). If any figure differs from what §5A.4.1, §5A.5 or Chapter 7 now states, the manuscript follows the file, not the reverse.
2. **The production-path run (decision 2a).** From the repo root with the platform's `AI_BASE_URL`, `AI_API_KEY`, `AI_MODEL` and `THESIS_DATA_DIR` set: `python thesis/evaluation/predict_llm_production.py` (add `--limit 10` first as a smoke test). Then re-run `run_eval.py`; the `*_llm_production` keys, the drop-mixed sensitivity and the production row of the escalation and McNemar tables appear. Fill the §5A.2 placeholder and decide whether §5A.3–5A.5 report the production predictor beside or instead of the generic prompt; update Appendix D's H3 row and Appendix B's Article 15 row accordingly.
3. **Three runs for the McNemar range** (optional but recommended): re-run `predict_llm.py` (or the production script) three times, report the range of (b, c, p) in §5A.6; the one-flip p is already stated.
4. **In-repo evaluation on the held-out split**: `apps/api/app/evals/run_live.py --publish`. Fill the held-out figures in §5A.7 and Appendix D (`by_split.held_out`), and the model card picks up Wilson intervals. Then, if time allows, run it once with `AI_MODEL=mistral-small-latest` (the configured production model, §4.1, §6.4 item 2) and once with a self-hosted or EU-hosted model, and add a three-row accuracy/cost/latency table (Langfuse has the token counts).
5. **Survey and interviews**: `python thesis/evaluation/survey_analysis.py responses.csv` once data exist; apply the §5B.1 fallback rule to whatever the study reaches and delete every empty §5B cell (39 placeholders remain in Chapter 5, all in §5A.2, §5A.7 and §5B).

## Needs the author: facts only you have

- **Label and paraphrase provenance** (§3.7 placeholder; §3.10): who produced the paraphrases and the seed labels for the three thesis datasets, whether a language model drafted them, and the result of a blind double-labelling of a 40-signal sample on risk (Cohen's κ). The dataset loader's own notes call the later datasets' labels assistant-drafted and author-reviewed.
- **English golden-set authorship** (§5A.7, §6.4 item 3): the German stratum's authorship is documented; state the English items' the same way.
- **Ethics route and reference** (§3.9, Appendix C, consent form): obtain the RAI-9001 ethics confirmation from the supervisor and record it. The consent durations were filled as two weeks (withdrawal) and six months after completion (retention); confirm or change both.
- **The external-review tally** (Appendix F): the outcomes sum to 43; the text said 45. Reconcile against the verification log.
- **Cross-industry ≈90% run** (§5A.7 disclosure iv): n and date from the local ledger, or drop the figure.
- **Figure 4.7**: the caption is now honest about the empty board; recapturing from a workspace with a closed contract would be better evidence for DP1.
- **Front matter**: repository URL or DOI; sign the declaration; the lists of figures and tables are inserted in Word from the captions.
- **Reference entries marked ‹verify›**: Regulation (EU) 2026/1744 (title, OJ issue, ELI; and the four-month Article 50(2) grace period against the OJ text), Forrester RES185117 (2025c), the Fazio (2025) Forrester post, Forrester (2026) landscape post, Qualtrics XM Institute (2025), Qualtrics (2026b) URL, Latham & Watkins (2026), Li (2025) COLING pages, Hatalis et al. (2025) arXiv authors, the anonymous "Human–agent collaboration" survey (find its authors or drop it), Gupta et al. (2020) EMNLP (identify or delete the sentence), the four literature-gap sources flagged in §2.13 (verify each before citing).
- **Sample the "supported" citations** (addendum D8): 12–15 whose claim sentence carries a number or a mechanism, checked against the primary text, to bound the error rate of the sweep.

## Editorial follow-ups not finished here

- Repetition: "authored" 24×, "declared" 11×, "honest" 13×, "deliberately" 19×, "is itself" 8×, "rather than" 141× across the chapters; p = 0.029 appears 6×. Trim on the read-through.
- The abstract is 383 words (target ~280).
- Open the built `thesis.docx` and check: figure order (4.1 implementation, 4.2 logical), the 13 equations of §3.5.5, Appendix A's demoted headings, the tables in Appendix B and D.
- The defence deck's speaker notes still quote p = 0.029 without the one-flip caveat and the escalation contrast without the Fisher tests; align the results and equity slides with §5A.5 as revised.
- The Chapter 1 evidence-status table and Appendix D should be re-read together after the runs above, so that every "pending" becomes a status.

## Decisions taken here that you may want to revisit

- DP4 reframed (2c = B) rather than porting the rule resolver; the first cycle's design is recorded in §4.7 and the rules survive as configuration.
- Cut from Chapter 2: anomaly detection (old §2.4), churn prediction (old §2.7), dashboard design (old §2.9), A/B statistics and meta-analysis (old §2.6.2–2.6.5), *Competing on Analytics* (old §2.3.3), the cross-industry statistics table (old §2.12.8); their reference entries were removed. Everything is recoverable from git history.
- DP3 and DP6 demoted to implementation decisions; DP7 added; H1–H8 kept only as coding labels and Appendix D rows.
- §5A.8 moved to Appendix F; §3.10–3.12 merged; the practitioner study labelled exploratory with a fallback rule fixed in advance.

## Step-by-step, in order

Time estimates are for a laptop with the datasets in `~/Documents/Thesis_ChatGPT` and the API keys in `apps/api/.env`. Every command is run from the repository root unless a `cd` says otherwise.

### Where to run

On the machine that has (a) the datasets folder (`~/Documents/Thesis_ChatGPT`), (b) the earlier evaluation ledger (`apps/api/app/evals/history.jsonl`, gitignored) and (c) the model API key. Nothing here needs a GPU, the database or the production server; the model runs are a few hundred short API calls. Steps 9–12 (reference checks, editorial, build, merge) run anywhere with the repository checked out.

### Step 0. Get the branch and the tools (20 min)

```bash
git fetch origin claude/thesis-review-critique-afwkm7
git checkout claude/thesis-review-critique-afwkm7
python3 -m venv .venv
.venv/bin/pip install -e "apps/api[dev]" scikit-learn matplotlib pypandoc-binary
source .venv/bin/activate          # npm run api:test uses python3 on PATH
npm run api:lint && npm run api:test          # expect: All checks passed! / 850 passed
python thesis/evaluation/test_metrics.py      # expect: OK: all metric/baseline self-checks passed
python thesis/evaluation/survey_analysis.py --demo
```

### Step 1. Regenerate the harness outputs and reconcile the numbers (30 min)

```bash
export THESIS_DATA_DIR=~/Documents/Thesis_ChatGPT
cd thesis/evaluation
python run_eval.py > /tmp/run_eval.log        # baselines, ML, the 4 Aug LLM file, taxonomy, equity, McNemar
git status --short results/                   # new: composition.csv, escalation_recall_fisher.csv, mcnemar_paired.csv,
                                              #      sentiment_by_source.csv, *_ml_* and *_llm_* per-class/confusion files
git diff results/summary.json
```

Read these keys in `results/summary.json` and compare with the manuscript; the file wins:

| Key | Expected | Manuscript location |
|---|---|---|
| `journey_stage_llm_closed_set.f1_macro_on_supported`, `owner_…` | ≈ 0.54, ≈ 0.37 | §5A.4.1 last paragraph |
| `language_sector_composition` (`de|b2b_industrial`, `en|fintech`, denominators from `composition.csv`) | 38/39, 58/67 (full corpus); 37/37, 36/45 (star-rated) | §5A.5 confound paragraph |
| `escalation_recall_fisher` (`p_fisher_two_sided` per predictor) | learned ≈ 0.026, floor ≈ 0.32, contextual ≈ 1.0 | §5A.5 escalation paragraph; §6.2; Ch 7 |
| `escalation_recall_by_language` (`recall_*_ci_low/high`) | Wilson intervals | §5A.5 table note |
| `mcnemar_paired.sentiment.ml_vs_llm.p_if_one_pair_flipped` | ≈ 0.043 / 0.052 | §5A.6, §6.4 item 3 |
| `sentiment_by_source`, `sentiment_llm_by_source` | one row per source with n ≥ 5 | Appendix D, H3 row (currently "reported once re-run") |

Commit `thesis/evaluation/results/` together with any sentence you changed.

### Step 2. The production-path run, decision 2a (1 h, ~8 model calls)

Run it first with the **same model and gateway as the 4 August run** (GLM-5.2), so that the only thing that differs from the §5A predictor is the pipeline; then, optionally, once more with the configured production model.

Do **not** source the whole `apps/api/.env` for this run: the residency gate switches itself on whenever `DATABASE_URL` is set (or `CLARA_AI_REQUIRE_EU=true`), and it refuses the GLM-5.2 gateway at import time as "unknown". Export only the model variables, and switch the gate off explicitly for the comparison run:

```bash
export AI_BASE_URL=<the gateway used on 4 August>   # e.g. https://opencode.ai/zen/v1
export AI_API_KEY=<key> AI_MODEL=glm-5.2
export CLARA_AI_REQUIRE_EU=0                          # comparison run only; the Mistral run below passes the gate
export THESIS_DATA_DIR=~/Documents/Thesis_ChatGPT
python thesis/evaluation/predict_llm_production.py --limit 10      # smoke test: 10 signals, one batch
python thesis/evaluation/predict_llm_production.py                 # full run; --exemplars auto = production default
cat thesis/evaluation/results/predictions_llm_production.meta.json # model, exemplars flag, batch size, n scored
cd thesis/evaluation && python run_eval.py > /tmp/run_eval2.log
```

New keys in `summary.json`: `sentiment_llm_production` (accuracy with Wilson interval), `sentiment_llm_production_excluding_mixed` (the sensitivity variant), `sentiment_llm_production_raw_label_counts`, `risk_llm_production`, `risk_llm_production_binary_escalation`, the `recall_llm_production` columns in `escalation_recall_by_language.csv`, and `llm_vs_llm_production` pairs in `mcnemar_paired.csv`. Then:

1. Fill the placeholder in §5A.2 item 3 (`05_evaluation_results.md`, the "Contextual LLM path" item) with the production row's n, sentiment accuracy and interval, and the mixed-label count.
2. Add a "Production enrichment stage" row to the §5A.3 and §5A.4 tables and a column to the §5A.5 escalation table, or replace the generic-prompt predictor if you decide the production stage is the predictor the thesis should report; say which in §5A.2.
3. Update Appendix D (H3 row: "the contextual predictor is a generic prompt…" becomes the production figure), Appendix B (Article 15 row: "pending its re-run"), §6.4 item 2, §6.5 direction 1, and Chapter 7 if the headline number moves.
4. Optional second run: `export AI_MODEL=mistral-small-latest AI_BASE_URL=https://api.mistral.ai/v1`, repeat, and keep both meta files; report the pair in §6.4 item 2.

### Step 3. The McNemar range (30 min, optional)

```bash
cd thesis/evaluation
for k in 1 2 3; do
  python predict_llm.py && mkdir -p results_run$k && cp results/predictions_llm.json results_run$k/
  THESIS_RESULTS_DIR=results_run$k python run_eval.py > /dev/null
  grep "ml_vs_llm" results_run$k/mcnemar_paired.csv
done
```

Report the range of (b, c, p) across the three runs in §5A.6 next to the one-flip p; keep the 4 August file as the reported run.

### Step 4. The in-repo evaluation on the held-out split (30 min per model)

```bash
cd apps/api
export AI_BASE_URL=<gateway> AI_API_KEY=<key> AI_MODEL=glm-5.2 CLARA_AI_REQUIRE_EU=0   # same caveat as Step 2
python -m app.evals.run_live --publish
```

Run this on the machine that holds the earlier run ledger (`app/evals/history.jsonl` and `app/evals/reports/`, both gitignored): the run appends to it, and Step 6 reads the July entries from it.

`app/evals/published_metrics.json` now carries `by_split` (`optimization`, `held_out`) and Wilson intervals, and the model card serves it. Paste the held-out sentiment and urgency accuracies (n = 30) into the §5A.7 placeholder and Appendix D's reading paragraph; if the pooled figures changed, update §5A.7's table row, Appendix B's Article 15 row and Chapter 7. Then, if you have the time, run without `--publish` once with `AI_MODEL=mistral-small-latest` and once with a self-hosted model; take `enrich_latency_ms` from the report and token counts from Langfuse, and add the three-row accuracy/cost/latency table to §5A.7 with a sentence in §6.4 item 2.

### Step 5. The κ double-labelling sample (one afternoon, two people)

```bash
cd thesis/evaluation
python kappa_sample.py draw               # results/kappa_sample.csv: 40 risk-labelled signals, seed labels withheld
# hand the file to a second labeller (or label it yourself after two weeks without looking at the seeds);
# they fill blind_risk with low | medium | high | critical
python kappa_sample.py score results/kappa_sample.csv     # results/kappa_risk.json
```

Put κ (unweighted and linear-weighted), the exact agreement and the escalate agreement into the §3.7 provenance placeholder and §6.4 item 1.

### Step 6. Provenance and authorship facts (1 h of writing)

- §3.7 (`03_methodology.md`, the provenance placeholder): who wrote the paraphrases and the seed labels for the three thesis datasets, whether a language model drafted either, what review they received, and the κ result from Step 5.
- §5A.7 second paragraph and §6.4 item 3: who authored the English golden-set items (ids `eval-001`–`060` and `081`–`100`), stated the way the German stratum's authorship is.
- Appendix F: reconcile the tally (the text says 43 claims; the outcomes sum to 43; the earlier text said 45) against your verification log.
- §5A.7 disclosure (iv): the n and date of the cross-industry ≈90% run from your local `history.jsonl`, or delete the figure.

### Step 7. Ethics (email today; insert when confirmed)

Ask the supervisor for the RAI-9001 ethics route and a reference. Insert it in §3.9 (`03_methodology.md`), Appendix C §0, and `instruments/consent_and_recruitment.md` (the note at the top of Part B). Confirm the two durations the consent form now states: withdrawal within two weeks, retention six months after completion.

### Step 8. Survey and interviews (the critical path)

1. Build the form from `instruments/survey.md`; copy each question's exact header into `COLS` in `thesis/evaluation/survey_analysis.py`.
2. Recruit with `instruments/recruitment_outreach.md` (working copy, not bound).
3. When responses arrive: `cd thesis && python evaluation/survey_analysis.py path/to/responses.csv` writes `evaluation/results/survey_verdicts.csv`; paste the table into the §5B.0 placeholder and Appendix D's hypothesis rows.
4. Interviews: apply the rule fixed in §5B.1 (12+, 6–11, fewer than 6). The 31 remaining placeholders in §5B.4.1–5B.4.6 are filled or deleted accordingly; no `‹…›` may survive into the submitted document.

### Step 9. Reference entries marked ‹verify› (2 h at a library terminal)

Search `references.md` for `‹`: Regulation (EU) 2026/1744 (title, OJ issue, ELI, and whether the Article 50(2) grace period is four months, also in Appendix B); Forrester (2025c) RES185117; Fazio (2025) and Forrester (2026) posts; Qualtrics XM Institute (2025); Qualtrics (2026b) URL; Latham & Watkins (2026); Li (2025) COLING pages; Hatalis et al. (2025) arXiv authors; the anonymous "Human–agent collaboration" survey (authors or delete); Gupta et al. (2020) in §2.2.6 (identify or delete the sentence); the four literature-gap sources in §2.13 (verify before citing, then write them into §2.1.2, §2.8 and §2.12 as short paragraphs). Then sample 12–15 "supported" citations whose sentence carries a number or a mechanism and check them against the primary text.

### Step 10. Editorial pass (half a day)

Trim the repeated caveats (counts in the section above), bring the abstract to about 280 words, re-read §1.7's table and Appendix D together so every "pending" has become a status, and align the defence deck's results and equity slides with the revised §5A.5 (the one-flip p and the Fisher tests).

### Step 11. Rebuild and check (30 min)

```bash
cd thesis && bash build_docx.sh                        # build/thesis.docx (gitignored)
cd diagrams && python render.py                        # only if a .mmd changed; uses mmdc if installed
cd ../defense && npm install pptxgenjs && node make_deck.js   # only if the deck changed
```

Open the `.docx` and check: figure order (4.1 implementation, 4.2 logical), the 13 equations of §3.5.5, Appendix A's demoted headings, the Appendix B and D tables. Insert the lists of figures and tables in Word (pandoc captions are plain paragraphs, so either convert them to Word captions or write the two lists by hand), sign the declaration, add the repository URL or DOI.

### Step 12. Merge

Review the six commits on the branch, then merge them into `main` yourself (agents do not merge here) and tag the manuscript state you submit.
