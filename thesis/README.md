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
| `manuscript/appendices/` | EU AI Act/GDPR mapping, DPIA, traceability matrix (incl. ITS design→code map) |
| `instruments/` | Interview guide, consent form, survey, SUS, TAM items, codebook template |
| `evaluation/` | Python harness over the **real** public datasets (Trade Republic, Henkel, Lieferando) |
| `research/` | Deep-research source log + OPIT citation sourcebook |
| `diagrams/` | Mermaid sources + `render.py` + `rendered/` PNG/SVG + UI screenshots + `schema.sql` |
| `defense/` | `defense_deck.pptx` + `make_deck.js` generator |
| `correspondence/` | Supervisor email drafts (July 2026) |
| `build/` | Compiled `thesis.docx` + concatenated `thesis_combined.md` |
| `archive/` | Superseded material — see Merge log |

## Implementation: settled on CLARA (July 2026)

The manuscript previously described **one system with two implementations** (Odradek and CLARA) using tagged `[IMPL · …]` blocks. On 16 Jul 2026 the documented exit procedure was executed: the manuscript is now single-build **CLARA** (the platform in this repository, in production at https://clara.odradekai.com). The earlier Odradek build is acknowledged once, as the first design-cycle iteration (§4.7); its architecture diagram is archived in `archive/odradek/`. No `IMPL` tags remain.

## Citations & build

APA 7, author–date in text, consolidated in `manuscript/references.md`. Compile with the `docx` skill (chapters concatenated in numeric order → `build/thesis.docx`, with heading hierarchy, ToC, and figures).

⚠️ **`build/thesis.docx` and `build/thesis_combined.md` are stale** (built 13 Jul, before the streamline). Rebuild before circulating. Note §3.5.5 now contains display math (`$$…$$`) — confirm the docx pipeline renders TeX.

## Evaluation data

The quantitative evaluation uses **only the real, publicly-sourced** brand datasets in `~/Documents/Thesis_ChatGPT/` (not in this repo). The harness resolves them via the `THESIS_DATA_DIR` env var, defaulting to `../../../Thesis_ChatGPT` relative to `evaluation/` (path updated for this folder's location). The synthetic sets are **excluded by design** and must not enter the evaluation corpus.

Related but separate: `apps/api/app/evals/` is the platform's own committed LLM evaluation (60-case golden set + `history.jsonl` ledger) — reported in the manuscript as convergent evidence (§5A.7), never merged into the §5A tables (different gold standards).

## Author TODOs (pre-submission)

- [ ] Rebuild `build/thesis.docx` (+ regenerate stale diagram renders: `03_architecture_clara`, `08_dsr_method` — their `.mmd` sources changed; `python3 diagrams/render.py`)
- [ ] Rebuild `defense/defense_deck.pptx` (the "(parallel build: Odradek)" subtitle was removed from `make_deck.js`; the built pptx still carries it)
- [ ] §5B: collect interview + survey data, fill placeholders (`‹…›`)
- [ ] Run the LLM path against the 188-signal harness (`evaluation/predict_llm.py`, needs API key) — closes the "pending" cells in §5A.3–5A.4
- [ ] Citation verification pass (front-matter declaration promises it; Wagner 2002 / Bernal 2017 added for §3.5.5 — verify page ranges)
- [ ] Repository URL / DOI in front matter; sign declaration
- [ ] Fachanwalt legal-doc review ~1 Aug (see business-ops); thesis-IP letter due 31 Aug

## Merge log (16 Jul 2026)

- **From `Thesis_writing/`**: everything (manuscript → `manuscript/`, plus diagrams, evaluation, instruments, research, defense, build). Word/Office lock files (`~$…`) and `.DS_Store` excluded. The source folder was left untouched — delete it once satisfied.
- **From `thesis-update/`**: `its-methodology-draft.md` **integrated** into the manuscript as §3.5.5 (+ Ch 4 §4.4 contract sentence, Ch 6 §6.5 rewrite, Appendix D mapping table, 2 new references); draft preserved in `archive/`. Screenshots `clara-01/02` added to `diagrams/screenshots/` (03/04 were already there, byte-identical). Email drafts → `correspondence/`.
- **From old `thesis/`**: `PLAN_3_MONTHS.md` (June planning snapshot) → `archive/`. Superseded and dropped (recoverable from git history): `literature_review.md` (79K, Jun 24 — superseded by `manuscript/02_literature_review.md`), `chapters/ch4_artifact.md` (superseded by `manuscript/04_artifact.md`), `recruitment_and_consent.md` (byte-identical to `instruments/consent_and_recruitment.md`), `evaluation/prototype_metrics.py` (preserved as `evaluation/_reference_prototype_metrics.py`).
- **Streamline edits**: dual-build framing removed (front matter, Ch 1, Ch 4, Ch 5, Ch 6, DPIA); Odradek figure 4.2 removed and Ch 4 figures renumbered; deployment fact updated (Render/Railway → Docker on EU VPS behind Caddy, matching production); "four design decisions" → five (Ch 1 §1.9, Ch 3 DSRM table, DSR diagram); consent-form title renamed to CLARA; `schema.sql`/diagram manifests updated.
