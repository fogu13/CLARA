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
