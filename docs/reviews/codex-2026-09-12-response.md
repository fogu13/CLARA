# Response to the Codex review of 12 September 2026

Reviewed baseline: `4e337c765c141bfcc909c6da53343c640bd5b5aa` (main, 6 September 2026).
Working baseline for this response: the same commit (HEAD == reviewed baseline, clean tree, no
uncommitted work in this clone). Every finding was re-checked on that code before any change.

Companion artifacts named by the review (`CLARA-review-2026-09-12.md`,
`test_clara_review_probes.py`, `CLARA-diagnostic-results.txt`,
`CLARA-existing-test-results.txt`) live on the owner's machine and were not available in the
environment that produced this response. Nothing below claims to have read them; the probes were
reconstructed from the finding descriptions and turned into regression tests of the desired
invariants.

Baseline test run on the reviewed commit in this environment: 851 API tests passed (the review
reports 202; the difference is the subset the reviewer ran, not a regression).

## 1. Disposition table

Legend for "validation": the command that proves the row, run on the integrated branch in this
environment. "Verification" is the adversarial pass (independent agents writing probe tests
against the merged code, plus per-area code review); see §1.1.

| ID | Disposition | Reproduction / counter-evidence | Affected files (current) | Chosen change | Validation | Remaining limitation |
|---|---|---|---|---|---|---|
| R0 human-rating provenance | **Accept the question; the answer is the owner's attestation, not a repository fact.** | Repository shows `kappa_sample.csv` and `kappa_risk.json` committed already filled in `24d56fc` (6 Sep, 17:12 UTC), 29 min after the rubric commit; no artefact records who rated or whether any AI suggestion was visible. The review's "identical to a Codex-generated set" observation cannot be checked from the repository. Owner's statement (12 Sep): "another rater", read as a second person, consistent with §3.7. | `thesis/evaluation/results/PROVENANCE_kappa.md` (new), `03_methodology.md` §3.7 + :71, `05:100`, `06:49`, `02:335`, `appendices/D:33`, `defense/make_deck.js`, `board/*` | Provenance record written; the second-person statement kept as an attestation with a one-clause qualifier wherever the rating is used as "the one human check"; deck and board no longer claim that no kappa exists; alternative wording for the AI-rater case prepared in `thesis/review-2026-09-12-response-notes.md`, not applied. `kappa_sample.csv`/`kappa_risk.json` untouched. | Grep: "no kappa" / "no second annotator" = 0 occurrences | Rater identity, return time and AI exposure remain unrecorded; the identical-label observation is unresolved. Any new human rating must be a new draw, new file, new commit. |
| C1 approval bypass on retry | **Accept.** | Confirmed at `problems.py` retry endpoint (status check only) and `action_push.py` (payload from the current action; `human_reviewed` from the execution). Both the edit and the revocation sequences reproduced by the new tests. | `services/workflow.py` (`authorize_dispatch`, SQLite `approvals.execution_id`), `services/action_push.py`, `routers/problems.py`, `apps/web/.../action-proposal-editor.tsx`, `lib/i18n.tsx` | Dispatch (first push and retry) is authorized against the approval run that created the execution: latest decision must be approved, ≥2 distinct reviewers under four-eyes, execution must belong to that run, every approval must carry a snapshot, current action must equal the approved snapshot on class/owner/destination/proposal/risk_level/intervention_brief/depends_on, four-eyes snapshots must match, destination must match. Refusal → 409, no connector call, reason recorded on the execution and in telemetry. PATCH of an actively approved action → 409; PATCH of the problem's title/statement → 409 while any action is approved (they are in the outbound payload). Per-execution in-process lock plus a re-read before dispatch closes the same-worker race. After the adversarial pass: idempotent reuse of an external record is limited to executions of the authorizing approval run (a re-approved revision is dispatched, never mapped onto the old ticket); a refused first push is recorded as `push_failed` with the reason and `action_push_refused` telemetry; the gate uses the effective human-review status so pre-stamp rows are covered; retry refuses executions no approval created; decisions order by numeric id. | `test_dispatch_authorization.py` (21 tests); existing retry test unchanged and passing; full suite | The lock is process-local: two Postgres workers can still race on one execution (a row lock would close it); authorization is re-checked immediately before the connector write, but the network call itself is unguarded. Owner routes and connector configuration are admin settings resolved at dispatch (the resolved route is now named in the execution detail). Auto-published executions that no approval created cannot be retried at all. |
| C2 false provenance in loop closure | **Accept.** | Confirmed at `outcome_engine.loop_verdict` (done-plan check before the manual check); reproduced: target_met + manual latest + old done window plan → `loop_closed` "on real signals". | `services/outcome_engine.py`, `services/measurement_scheduler.py`, `services/workflow.py`, `routers/problems.py`, `migrations/016_measurement_provenance.sql` | Scheduler readings carry `checkpoint_kind`, `plan_id`, `execution_id`, `contract_revision`, `contract_snapshot` (Python and plpgsql). `loop_closed`/`fix_did_not_land` are certified only for an instrumented closing read; a manual reading is never certified and its note says so; wording distinguishes target attainment from causal attribution (evidence grade). After the adversarial pass: readings also carry their own clock (`clock_origin`, `clock_origin_at`) so the certified note names the clock the reading was taken on, not the current anchor; `POST /outcomes` strips every client-supplied provenance field (a forged contract snapshot can no longer re-score a manual reading); the CSV export carries `measurement_source`, `checkpoint_kind` and `loop_verdict`. One existing matrix assertion that encoded the defect was changed (listed in §1.2). | `test_measurement_semantics.py`; `test_loop_closure.py`; Postgres parity (4 tests) against a local PostgreSQL 16 with migration 016 | Legacy readings without `checkpoint_kind` fall back to "instrumented and a done closing plan exists". Postgres readings written by one plpgsql tick share `created_at`, so "latest" among same-tick rows is ordered by a uuid suffix (pre-existing; ticks run one kind at a time in operation). `loop_closed` telemetry events are not retracted when a later manual reading de-certifies the verdict (the board and API are). |
| C3 contract edits rewrite history | **Accept.** | Confirmed at `routers/problems.py` (only the metric is frozen) and `workflow.outcome_snapshot` (scores the stored value against the current contract); reproduced: 100/50/80 → improving; target 90 → target_met with no new observation. | `domain/models.py`, `services/problems.py`, `services/workflow.py`, `services/postgres.py`, `routers/problems.py`, web contract card + types | Contracts carry `revision`, `revised_at`, `revised_by`, `revision_note`; every amendment that changes a term bumps the revision and emits `contract_amended` telemetry with the diff and actor (no-op edits do not). Every recorded measurement freezes the contract it was scored under; the snapshot scores status under that frozen contract, shows current terms, and flags `contract_amended_after_measurement`. Plans record the revision they were scheduled under. Metric change after measurement still 409. After the adversarial pass: the evidence grade and the learning-conclusion score follow the contract the reading was taken under; the amended flag compares scoring terms (not revision numbers) and falls back to the frozen snapshot's revision (plpgsql `COALESCE`); the approval-path auto-proposal also emits `contract_amended`; a note-only PATCH is rejected; a genuine zero reading counts as a measurement for the metric guard. | `test_measurement_semantics.py`; contract-proposal tests unchanged | No event-sourced history of contracts; the audit trail is the revision fields plus telemetry. Amending the window does not move `due_at` of already scheduled plans; the follow-up read now derives its window from the plan's own `due_at`, so the amendment cannot rewrite what a scheduled read covers. Legacy readings without a frozen contract are still scored under the current terms and cannot be flagged. |
| C4 clock starts without an implemented action | **Accept.** | Confirmed: `schedule_measurements(executed_at=execution.created_at)` ran after every approval regardless of push outcome; the scheduler reads "since action execution". | `services/measurement_scheduler.py`, `services/outcome_engine.py` (`intervention_anchor`), `services/workflow.py`, `services/postgres.py`, `routers/problems.py`, migration 016, web checkpoints panel | Three explicit origins on every plan: `dispatch` (from `dispatched_at` of a real push), `approval` (draft is the deliverable; labelled as such in notes and verdicts), `implementation` (new `POST /problems/{id}/executions/{id}/implementation`, human-recorded, supersedes pending plans and reschedules). A failed push schedules nothing (`measurement_not_scheduled` telemetry); a successful retry schedules from its dispatch instant. ITS and the snapshot anchor on implementation > dispatch > approval; failed-only executions anchor nothing. After the adversarial pass: `dispatched_at` is stamped only by a real connector success (legacy pushed rows anchor on `created_at` instead of vanishing); an implementation record requires an authorized, approval-created execution, may not precede dispatch, and supersedes every live plan (so a corrected date moves the checkpoints); a higher-precedence origin supersedes lower ones when scheduling (a real push after a draft-only approval moves the clock). | `test_measurement_semantics.py` (failed push, unconfigured destination, successful push, retry, implementation, validation, legacy DB upgrade); Postgres parity | No UI control yet for recording implementation (API only). A created ticket is still not "implemented"; only the human record moves the clock. A draft created while no connector was configured cannot be dispatched later without a new approval. The API does not detect a Postgres database whose plpgsql function predates migration 016. |
| E1 invalid prediction fields get credit | **Accept, with the review's own caveat kept.** | Confirmed in `run_eval.py` (`or "neutral"`, `or "low"`, silent id intersection, duplicate last-wins, unvalidated labels into macro averages) and the same class in `significance`, `equity_slices`, `compare_runs.py`. Not claimed: that the two committed production prediction files were inflated (188 unique ids, complete fields). | `thesis/evaluation/prediction_validation.py` (new), `run_eval.py`, `compare_runs.py`, two plain-assert tests, `package.json` (`thesis:test`) | Pure validator with expected/returned/valid/invalid/missing/unknown/duplicate counts; coverage-conditioned metrics on valid rows with a fixed label set; new `*_end_to_end` metrics with missing/invalid counted wrong; paired tests report `n_dropped`; confusion tables sum to `n_valid`. After the adversarial pass: taxonomy scoring, equity recall and the equity bootstrap go through the same validator; empty/non-mapping ids, duplicate gold ids, corpus-vs-task unknowns and an empty expected set are handled explicitly; an all-invalid production file no longer crashes the run. | `npm run thesis:test` (3 scripts, synthetic data) | `score_taxonomy` still unvalidated (not in scope; flagged). Committed `summary.json` files predate the new keys and need a re-run with the corpus. |
| E2 wrong denominator | **Accept.** | Confirmed: rate = flagged / all items while non-English items are excluded from flagging. | `apps/api/app/evals/harness.py`, `run_live.py`, tests | Rate over eligible English items; `None` ("not evaluated") when none; eligible/excluded counts exposed; consumers handle `None`. The current zero numerator stays zero. After the adversarial pass: language subtags are normalised (`EN`, `en-US` count); items with no assessable enrichment are counted as unassessed rather than grounded; the published model-card snapshot and the ledger carry the hallucination fields; the hard-coded literacy figure is restated over the eligible English items (2 of 60 = 3.3%, from the 17 July run recorded in commit e454898). | `test_eval_harness.py` | The heuristic itself remains English-only token grounding. |
| R1 held-out effect not computed | **Accept.** | Confirmed: pooled McNemar, ON-only `by_split`, ON-only per-item output; "neither below" at 05:148 is false for sentiment (96.7% < 100%). Tuning audit (git): split membership frozen 18 Jul; golden labels last edited 18 Jul; exemplars unchanged since 18 Jul; enrichment pipeline changed 8 Aug, 2 Sep, 5 Sep; at least five published scorings of the held-out split, exact count not recoverable (`history.jsonl` gitignored). | `run_live.py`, `LOOP_PROMPT.md`, `test_run_live_reporting.py`, manuscript §3.5.3/§5A.7/§6.4/ch.7/App. B, D | Both arms saved with split ids; `by_split_ab` per split (exact McNemar + seeded paired-bootstrap CI on the difference); pooled result kept and labelled exploratory; config block with golden-set/exemplar/held-out hashes; held-out per-item failures hidden by default; consultation count logged; A/B nulled when exemplars are disabled; acceptance rule moved to the optimisation split. After the adversarial pass: the gate is a between-run paired comparison (`--baseline-report`, `vs_baseline`, with guards that never read a null as zero) because the within-run ON/OFF contrast cannot measure a prompt change; held-out per-item rows live in a sidecar the loop is told never to open; reveals are recorded; the exemplar hash covers labels; publish and ledger rows carry the config hashes; an empty exemplar list counts as disabled; the consultation count includes every earlier eval row. Manuscript: "neither below" corrected; held-out numbers described as held-out accuracies of one configuration on a repeatedly consulted validation split; no paired held-out effect claimed. | `test_run_live_reporting.py` (12 tests, no model calls) | The per-split paired effect exists only after the next live run (paid; not executed). Old OFF outputs are gone and were not invented. |
| R2 comparative fairness inference | **Accept.** | 05:119 and 06:69 rank predictors on significant-vs-non-significant stratum tests (Gelman & Stern, 2006). Per-item gold risk and language are only in the external corpus, so the paired comparison cannot be run here. | `thesis/evaluation/equity_gap_bootstrap.py` (new, with synthetic test), manuscript 05/06/07/00/01, App. D, deck, board, `references.md` | Script for the paired within-stratum bootstrap of the DE−EN gap difference and an exact permutation test; manuscript narrowed to descriptive stratum evidence with the eight-item denominator, "equity-worst escalator" replaced by non-ranking per-stratum monitoring, 49-vs-50 count resolved by definition, "genuinely critical" removed. | `python3 thesis/evaluation/test_equity_gap_bootstrap.py` | Not run on the corpus (data absent); the owner must run it with `THESIS_DATA_DIR` and quote the interval. |
| R3 qualitative protocol contradictions | **Accept.** | 03:113 says reflexive TA while requiring codebook consensus and IRR; 05:170 lets a survey below n = 40 suppress interview findings. | `03_methodology.md`, `05_evaluation_results.md`, `instruments/codebook_template.md`, App. D, `references.md` | Codebook (coding-reliability) TA chosen and justified (Braun & Clarke 2006 phases; 2019/2021 distinction); reflexive-specific claims removed; second coder as a role, κ threshold and reconciliation rule stated; interview and survey tiers separated with a table resolving (15,0), (8,100), (5,100), (12,39); placeholders left empty. | Grep of removed phrases (see §1.1) | `survey_analysis.py` still emits a support label from n = 10 (outside the manuscript agent's scope); the text records it as a descriptive count below n = 40. |
| R4 configuration comparison mislabeled | **Accept.** | 05:87-102 compares models at different batch sizes and run dates and reads p > 0.05 as sameness in places. | `05_evaluation_results.md`, `06_discussion.md`, deck | Estimand renamed to a deployment-configuration comparison (model × batch size × run conditions); no equivalence inferred from non-significance (discordant counts stated); controlled rerun named as not run; exact result files cited per figure. | Grep: "model effect" only in negated form | No controlled rerun (paid); prose only. |
| Ops `/ready` 404 | **Accept as a version-lag diagnosis; not an outage.** | Actions log: `/health` 200, model-card 401, headers present, `/ready` 404 with FastAPI's JSON body; route and check added together in `01ced20` (2 Sep). Direct probe blocked by the environment's egress policy. | `DEPLOY.md` | Diagnosis in §2; DEPLOY.md expectation corrected from 17/17 to 22/22 with the failure signature named. Nothing deployed. | n/a | Requires a rebuild/restart by the owner. |

### 1.1 Where the review overreached, and where it was right

- Right on every code claim: all seven code findings (C1–C4, E1, E2, R1) reproduce at the cited
  lines on the reviewed commit. None was already fixed on HEAD.
- Right on the manuscript claims: "neither below" is arithmetically false; the reflexive/codebook
  contradiction and the survey-suppression rule are real; the fairness ranking is the
  significant-vs-non-significant error.
- R0 is a question the repository cannot answer. The review did not assert an answer and neither
  does this response: the owner attests a second person rated; the provenance record states what
  is and is not on record. The review's identical-label observation stays open.
- Scope narrowed in two places: (1) "consider four-eyes sign-offs across revisions" is handled by
  requiring identical snapshots across the approval run rather than a new sign-off model;
  (2) "wholesale event sourcing" for contracts was not needed: a revision counter plus a frozen
  contract on each reading and each plan is the smallest design that stops reinterpretation.
- The review's "202 existing tests" is a subset; the suite on the reviewed commit is 851 tests
  here.

### 1.1a Verification account

Two adversarial passes were run on the integrated branch: seven refuters (one per code finding)
writing throwaway probe tests against the merged code, and four code reviews by area. The
original defects did not reproduce. The refuters and reviews did find 40-odd adjacent gaps, the
most serious being: a forgeable contract snapshot on the manual outcome endpoint; idempotent
reuse that could mark a re-approved revision as pushed against the old ticket; a swallowed
first-push refusal; legacy execution rows bypassing authorization on retry; a stale defence deck
binary; a conflated Braun & Clarke (2021) citation; a wrong date in the held-out audit. All of
them were fixed in a second round (commits `d020105`, `a3ff98d`, `318fe58`, `3763ec4`,
`7b26334`) with a regression test per item (29 new tests in
`test_dispatch_authorization_gaps.py` and `test_measurement_semantics_gaps.py`, 19 in the
evaluation tests, 7 in `thesis/test_manuscript_consistency.py`, 3 more Postgres parity tests).
A third adversarial pass over the second-round fixes was not run: the subagent budget for this
session was exhausted during round two, and the two interrupted writers' worktrees were
completed and integrated by hand after their tests were verified. The second-round tests are
therefore the evidence for the second round; an independent re-probe is listed as a remaining
action.

### 1.2 Existing assertions changed (and why)

- `apps/api/app/tests/test_loop_closure.py::test_loop_verdict_matrix`: `target_met` with a done
  window plan now yields `loop_closed` only with `measurement_source="instrumented"` and
  `on_track` with a manual or absent source; `not_improved` with a done window plan yields
  `fix_did_not_land` only when instrumented and `measuring` when manual. The old rows encoded C2.
- No other existing test was modified, weakened or removed.

## 2. Operational follow-up: `/ready` returned 404 on the scheduled smoke run

Evidence (read-only, from the GitHub Actions log of run 34655293385, job 103446249752, both
attempts at 22:44 and 22:45 UTC on 11 September):

- `/health` → 200, `/model-card/metrics` → 401 (present), security headers present, `/docs` → 404,
  unauthenticated `/problems` → 401. The API container is up and answering.
- `/ready` → 404 with body `{"detail": "Not Found"}`. That body is FastAPI's own 404, so the
  request reached the application: Caddy routing is not the cause.
- `GET /ready` and its smoke check were both added in commit `01ced20` (2 September 2026, merged
  in PR #140). The route is defined unconditionally in `apps/api/app/main.py`.

Diagnosis: version lag. The running production image was built from a commit older than
`01ced20`; the smoke script (checked out from `main`) tests a route that the deployed build does
not have. Every scheduled run since the merge fails on this one check and re-opens the
"Production smoke failing" incident issue.

It does not establish that the service is down (21 of 22 checks pass). The fix is a rebuild and
restart of the API stack per DEPLOY.md step 3 (`docker compose up -d --build` in
`/opt/stacks/clara`), followed by `python3 scripts/live_smoke.py` expecting 22/22. Nothing was
deployed as part of this response.

Documentation correction made here: DEPLOY.md step 4 still said "expect 17/17"; it now states the
current count and names this failure signature.

The direct probe from the review environment was not possible (outbound HTTPS to
`api.clara.odradekai.com` is blocked by the environment's network policy), so the diagnosis rests
on the Actions log and the source history only.

## 3. Environment, unexercised paths and reproducibility limits

- The thesis corpus (188 signals, `THESIS_DATA_DIR`) is external to the repository and absent
  here. `thesis/evaluation/run_eval.py`, `compare_runs.py` and the new
  `equity_gap_bootstrap.py` cannot be executed on real data in this environment; their new logic is
  covered by synthetic plain-assert tests only. No synthetic data was substituted for results.
- The manuscript compiles: `thesis/build_docx.sh` was run with a pandoc binary installed for the
  purpose (`pip install pypandoc_binary`); the generated `.docx` is gitignored as before.
- Exemplars-OFF per-item outputs for earlier runs are not recoverable (`reports/` and
  `history.jsonl` are gitignored and exist in no branch). The per-split paired exemplar effect will
  exist only after the next live run of the updated harness, which is a paid model run and was not
  executed.
- A local PostgreSQL 16 server was available and used for parity tests of the changed
  measurement persistence (migration 016 applied; plpgsql tick exercised). pgvector is not
  installed here, so migrations 003 and 012 were not applied to that database; they do not touch
  the tables changed by this work. `pg_cron` scheduling was not exercised.
- Production Supabase was not touched. No paid model calls were made. No human validation is
  claimed anywhere in this response.

## 4. Remaining human decisions and actions

1. **R0 confirmation (one sentence).** Confirm that "another rater" means a second person, and
   state whether that person could see any AI-generated suggestion for the 40 rows. If the labels
   came from a model, apply `thesis/review-2026-09-12-response-notes.md` verbatim (the statistic
   becomes cross-model agreement; every "human check" phrase is replaced).
2. **New human rating.** Collect a second, independent human rating on a NEW draw of the risk
   seeds, with rater role, hand-over/return dates and an AI-exposure statement recorded, stored as a
   new `kappa_sample_<tag>.csv` in its own commit (rule in `PROVENANCE_kappa.md`).
3. **Paid runs (not executed here).** (a) Re-run the updated in-repo harness so `by_split_ab` and
   the consultation count exist, then update §3.5.3, §5A.7, §6.4, ch. 7, App. B and D from its
   output. (b) Re-run `thesis/evaluation/run_eval.py` and `compare_runs.py` with `THESIS_DATA_DIR`
   to populate the new validation keys, and `equity_gap_bootstrap.py` to quote the paired
   gap-difference interval in §5A.5. (c) Only if an isolated model effect is wanted: rerun both
   models through the production stage with matched batch size and conditions.
4. **Deployment.** Rebuild and restart the API stack (DEPLOY.md step 3) so `/ready` exists in
   production; apply migration 016 in the Supabase SQL editor after 013 (the API also self-heals
   the two plan columns on boot, but the plpgsql function replacement only lives in the migration).
5. **Product decisions.** Whether to add a UI control for recording implementation (the endpoint
   exists) and whether `survey_analysis.py` should suppress its support label below n = 40.
   (`score_taxonomy` now goes through the validator, and the web `ModelCardMetrics` type describes
   the new optional publish keys; both done in the second round.)
6. **Split into PRs if wanted.** The branch holds one commit per area for the first round (C1;
   C2–C4; E2; E1; R1; manuscript; deck) and one per area for the second (dispatch + measurement;
   evaluation harness; loop prompt; manuscript), plus the docs commits. The second-round commits
   depend on the first-round ones of the same area.
7. **Independent re-probe of the second round.** The first adversarial pass was independent of
   the writers; the second-round fixes are covered by their own regression tests only. Re-running
   the probe pass (or the reviewer's own probes) on the final branch is the missing check.
8. **Deck fit check: done.** `check_fit.js` was run with pptxgenjs installed in a scratch prefix.
   The review edits had introduced or worsened eight overflowing text boxes; they were shortened
   without changing any claim (two at a smaller font) and the binary rebuilt. Five overflows on
   slides 2, 6, 8 and 24 predate the review and were left as they were.
9. **Human validation** of the governance behaviour (an approver rejecting, editing and
   re-approving an action; a manual reading after an instrumented one; recording an
   implementation) has not happened and is not claimed.

## 5. Rollout notes

- **Migration 016** (`apps/api/migrations/016_measurement_provenance.sql`): adds `origin` and
  `contract_revision` to `clara_measurement_plans` and replaces `clara_run_due_measurements` with
  the 013 §3 body plus the provenance keys (`checkpoint_kind`, `plan_id`, `execution_id`,
  `contract_revision` with `COALESCE(..., 1)`, `contract_snapshot`, `clock_origin`,
  `clock_origin_at`); the follow-up read now starts at the plan's own `due_at` minus 30 days. Idempotent (re-applied here without error). Rollback
  text is in the file header. Apply after 013. No existing migration file was modified.
- **SQLite** deployments self-upgrade on boot (`_ensure_column` for approvals.execution_id,
  three execution columns, five outcome columns, two plan columns). Verified against a database
  created without the columns.
- **Postgres JSON payloads** (approvals, executions, outcomes, contracts inside problems) need no
  DDL; new fields have defaults and legacy rows load.
- **Behaviour visible to operators after deploy:** a retry of an execution whose action was
  edited or whose approval was revoked now returns 409 with the reason; editing an approved
  action returns 409 until a rejection is recorded; a failed push no longer schedules
  checkpoints; verdict notes name the clock origin; contract edits are versioned and emit
  `contract_amended` telemetry; the new implementation endpoint is available to editors.
- **Evaluation:** the next `run_live.py --publish` writes `by_split_ab` and
  `held_out_consultations` into `published_metrics.json`; the compliance page ignores unknown keys.
- **Checks run on the integrated branch:** `npm run api:lint`, `npm run api:test`,
  `npm run web:lint`, `npm run web:build`, `npm run thesis:test`, and the Postgres parity file with
  `CLARA_TEST_DATABASE_URL` set. Results are recorded in §6.

## 6. Validation record

Final integrated branch (`claude/relaxed-babbage-of6lum`), run in this environment:

| Check | Result |
|---|---|
| `npm run api:lint` | pass |
| `npm run api:test` | 976 passed, 7 skipped, 0 failed |
| Postgres parity (`CLARA_TEST_DATABASE_URL`, local PostgreSQL 16, migration 016 applied twice) | 7 passed |
| `npm run web:lint` | pass (2 pre-existing warnings) |
| `npm run web:build` | pass |
| `npm run thesis:test` (4 plain-assert scripts, synthetic data) | pass |
| `python3 thesis/test_manuscript_consistency.py` | 7 checks pass |
| `bash thesis/build_docx.sh` with a pandoc binary installed via `pypandoc_binary` | builds `build/thesis.docx` (2.0 MB) |
| `node thesis/defense/check_fit.js` (pptxgenjs in a scratch prefix) | 5 pre-existing overflows remain; the 8 edit-related ones fixed |
| `npm run web:lint` / `npm run web:build` after typing the model-card publish keys | pass |
| Baseline on the reviewed commit | 851 passed |

`npm run api:test` on the final branch: **976 passed, 7 skipped** (the skips are the Postgres parity tests, which need `CLARA_TEST_DATABASE_URL` and passed separately as listed), 0 failed.
