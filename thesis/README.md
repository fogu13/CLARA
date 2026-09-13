# Thesis — Closing the Loop, Building the Memory

MSc Responsible AI capstone (RAI-9001, 30 ECTS, OPIT). This folder is the **single home for all thesis material**: the manuscript (Markdown source of truth), the evaluation harness (real-data, runnable), the study instruments, the deep-research source log, the defense deck, and the compiled Word build.

> **Unified 16 Jul 2026.** Merged from three locations — `~/Documents/Thesis_writing/` (the active manuscript workspace), the repo's old `thesis/` (June-era, superseded), and `thesis-update/` (July ITS draft + screenshots + supervisor emails). The merge log and the streamline decisions are at the bottom of this file.

## Layout

| Path | Contents |
|------|----------|
| `manuscript/00_front_matter.md` | Title page, abstract, keywords, declarations, ToC stub |
| `manuscript/01_introduction.md` | Ch 1 — problem, motivation, research questions, contributions |
| `manuscript/02_literature_review.md` | Ch 2 — literature review (163 refs, deepened in the research pass) |
| `manuscript/03_methodology.md` | Ch 3 — DSR, mixed methods, evaluation design, **§3.5.5 ITS outcome scoring**, ethics |
| `manuscript/04_artifact.md` | Ch 4 — the artifact (Signal → Insight → Action → Learning) |
| `manuscript/05_evaluation_results.md` | Ch 5 — §5A real-data quantitative results (computed), §5B qualitative protocol + placeholders |
| `manuscript/06_discussion.md` | Ch 6 — design principles, RAI reflections, limitations, future work |
| `manuscript/07_conclusion.md` | Ch 7 — conclusion |
| `manuscript/references.md` | Consolidated APA-7 bibliography |
| `manuscript/appendices/` | EU AI Act/GDPR mapping (obligation vs commitment), DPIA (provider-prepared), traceability matrix (incl. ITS design→code map), external-review episode (Appendix F), provenance and revision log (Appendix G: dated provenance the chapters cross-reference) |
| `instruments/` | Participant information and consent (bound), interview guide, survey, SUS, TAM + friction items, codebook template; `recruitment_outreach.md` is working material and is not bound |
| `evaluation/` | Python harness over the **real** public datasets (Trade Republic, Henkel, Lieferando); `predict_llm.py` (generic prompt) and `predict_llm_production.py` (the artifact's own `enrich_signals` path, pre-registered rules); `compare_runs.py` (paired tests across results folders); `survey_analysis.py`. Outputs: `results/` (GLM-5.2 runs) and `results_mistral-small-2603/` (the production default through the production path) |
| `research/` | Deep-research source log + OPIT citation sourcebook |
| `diagrams/` | Mermaid sources of the deployed build + `render.py` (mermaid-cli locally, mermaid.ink as fallback) + `rendered/` PNG/SVG + UI screenshots (seeded demo data) + `schema.sql` (extracted from the migrations) |
| `defense/` | `defense_deck.pptx` + `make_deck.js` generator |
| `correspondence/` | Supervisor email drafts (July 2026) |
| `build/` | Compiled `thesis.docx` + concatenated `thesis_combined.md` |
| `archive/` | Superseded material — see Merge log |

## Implementation: settled on CLARA (July 2026)

The manuscript previously described **one system with two implementations** (Odradek and CLARA) using tagged `[IMPL · …]` blocks. On 16 Jul 2026 the documented exit procedure was executed: the manuscript is now single-build **CLARA** (the platform in this repository, in production at https://clara.odradekai.com). The earlier Odradek build is acknowledged once, as the first design-cycle iteration (§4.7); its architecture diagram is archived in `archive/odradek/`. No `IMPL` tags remain.

## Citations & build

APA 7, author–date in text, consolidated in `manuscript/references.md`. Compile with the `docx` skill (chapters concatenated in numeric order → `build/thesis.docx`, with heading hierarchy, ToC, and figures).

`build/thesis.docx` and `build/thesis_combined.md` are rebuilt with `bash build_docx.sh` (pandoc 3.9 via `pip install pypandoc-binary`, which the script finds in `.venv` or on `PATH`). The 5 Sep 2026 revision (see `review-2026-09-05-checklist.md`) changed content substantially; rebuild before circulating. This build follows a full manuscript line edit (20 Aug 2026): plainer authorial voice, zero em dashes anywhere in the compiled document (manuscript, appendices, instruments, schema comment), with content, claims and numbers unchanged and verified per file against git HEAD (numbers, section refs, links, code spans and headings all preserved by an automated check). The §3.5.5 display math (`$$…$$`) renders as native Word equations (13 `<m:oMath>` elements, no raw TeX leaking as literal text). Rebuild again after any manuscript edit before circulating.

## Evaluation data

The quantitative evaluation uses **only the real, publicly-sourced** brand datasets in `~/Documents/Thesis_ChatGPT/` (not in this repo). The harness resolves them via the `THESIS_DATA_DIR` env var, defaulting to `../../../Thesis_ChatGPT` relative to `evaluation/` (path updated for this folder's location). The synthetic sets are **excluded by design** and must not enter the evaluation corpus.

Related but separate: `apps/api/app/evals/` is the platform's own committed LLM evaluation (100-case bilingual golden set + `published_metrics.json`; the `history.jsonl` run ledger stays local, excluded by `evals/.gitignore`) — reported in the manuscript as convergent evidence (§5A.7), never merged into the §5A tables (different gold standards).

## Author TODOs (pre-submission)

The full list of items that need the author after the 5 September 2026 revision is in `review-2026-09-05-checklist.md`; the items below are the pre-existing list.

- [x] ~~Rebuild `build/thesis.docx`~~ — done 7 Aug 2026; all diagram renders verified current against their `.mmd` sources
- [x] ~~Rebuild `defense/defense_deck.pptx`~~ — rebuilt 7 Aug 2026, 20 slides (`node defense/make_deck.js`)
- [x] ~~Run the LLM path against the 188-signal harness~~ — completed 4 Aug 2026, 188/188 enriched; it had been failing silently (gateway 403 on urllib's default User-Agent, script exited 0 on an empty file)
- [ ] §5B: collect interview + survey data, fill placeholders (`‹…›`) — **the critical path; not started**
- [ ] Score `theme_seed` and `recommended_action_seed` via the §3.5.2 semantic-agreement procedure — the last 2 of 6 gold fields with no metric
- [ ] Score journey stage / owner in the **free-form production condition** — §5A.4.1 currently reports only the supplied-inventory upper bound
- [ ] Citation verification pass (front-matter declaration promises it; Wagner 2002 / Bernal 2017 added for §3.5.5 — verify page ranges)
- [ ] Repository URL / DOI in front matter; sign declaration
- [ ] Fachanwalt legal-doc review ~1 Aug (see business-ops); thesis-IP letter due 31 Aug

## Merge log (16 Jul 2026)

- **From `Thesis_writing/`**: everything (manuscript → `manuscript/`, plus diagrams, evaluation, instruments, research, defense, build). Word/Office lock files (`~$…`) and `.DS_Store` excluded. The source folder was left untouched — delete it once satisfied.
- **From `thesis-update/`**: `its-methodology-draft.md` **integrated** into the manuscript as §3.5.5 (+ Ch 4 §4.4 contract sentence, Ch 6 §6.5 rewrite, Appendix D mapping table, 2 new references); draft preserved in `archive/`. Screenshots `clara-01/02` added to `diagrams/screenshots/` (03/04 were already there, byte-identical). Email drafts → `correspondence/`.
- **From old `thesis/`**: `PLAN_3_MONTHS.md` (June planning snapshot) → `archive/`. Superseded and dropped (recoverable from git history): `literature_review.md` (79K, Jun 24 — superseded by `manuscript/02_literature_review.md`), `chapters/ch4_artifact.md` (superseded by `manuscript/04_artifact.md`), `recruitment_and_consent.md` (byte-identical to `instruments/consent_and_recruitment.md`), `evaluation/prototype_metrics.py` (preserved as `evaluation/_reference_prototype_metrics.py`).
- **Streamline edits**: dual-build framing removed (front matter, Ch 1, Ch 4, Ch 5, Ch 6, DPIA); Odradek figure 4.2 removed and Ch 4 figures renumbered; deployment fact updated (Render/Railway → Docker on EU VPS behind Caddy, matching production); "four design decisions" → five (Ch 1 §1.9, Ch 3 DSRM table, DSR diagram); consent-form title renamed to CLARA; `schema.sql`/diagram manifests updated.

## Evaluation tooling added 13 September 2026 (no results claimed; runs need the corpus, raters or credentials)

- `evaluation/multiple_comparisons.py` — Holm-adjusted paired tests over the committed McNemar results (`results/paired_tests_holm.csv`, run; quoted in §5A.3, §5A.6, §7).
- `evaluation/annotation_kit.py` — draw blind rating files for two human raters (labels withheld), agreement (κ per field with bootstrap intervals), adjudication, a human-adjudicated gold standard and a re-score of every committed prediction file against it. Needs `THESIS_DATA_DIR` and two raters; no model call.
- `evaluation/retrospective_its.py` — the shipped ITS estimator over an exported signal stream around a known event, with the graded readout (natural experiment; describes, does not attribute). Needs dated real inflow.
- `evaluation/run_matrix.py` — the matched 2×2 rerun plan (both prompts × both models, one day, one batch size); dry run by default, credentials read from named environment variables only.
- `evaluation/predict_embedding.py` — an embedding-classifier baseline (sentence embeddings + logistic regression, out-of-fold) scored by `compare_runs.py`; needs an embedding endpoint or a local sentence-transformers model.

Each has a plain-assert test on synthetic data in `npm run thesis:test`.
