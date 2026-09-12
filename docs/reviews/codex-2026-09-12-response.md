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

<!-- FILLED IN SECTION 1 BELOW AFTER IMPLEMENTATION; see the end of this file -->

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

<!-- FILLED AT THE END -->

## 5. Rollout notes

<!-- FILLED AT THE END -->
