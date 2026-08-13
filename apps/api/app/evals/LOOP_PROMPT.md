# Triage eval-improve loop

Run this with the loop skill, self-paced:

```
/loop /eval-triage
```

`/eval-triage` is the slash command at `.claude/commands/eval-triage.md` (same body as
below). Each tick performs ONE measured improvement iteration and either accepts +
commits it or reverts it. The loop ends itself when the targets are met or it stalls.

Prerequisite (one-time): set cloud creds in `apps/api/.env` — `AI_BASE_URL`,
`AI_API_KEY`, `AI_MODEL` (any OpenAI-compatible model). The runner pins
`AI_TEMPERATURE=0` for determinism.

---

## One iteration

You are improving CLARA's triage model by measured eval hill-climbing. Repo root is the
CWD; backend is `apps/api`; work on the current git branch.

**Ledger:** read `apps/api/app/evals/history.jsonl`. The last `kind:"eval"`/`accept`
row is the current baseline. If `apps/api/app/evals/run_live.py` is missing, STOP and
report — setup is incomplete.

1. **Run the eval:** `cd apps/api && python3 -m app.evals.run_live`. It scores real
   `enrich_signals` output vs `golden_set.json` with **95% bootstrap CIs** and a
   **McNemar test vs the previous run**, plus a synthesis **A/B (learnings off vs on)**.
   (Seed learnings first, once: `python3 -m app.evals.simulate_outcomes`.) Read the
   printed per-item failure table and the CI / McNemar lines.
2. **First run only:** record it as the baseline and stop this iteration.
3. **Diagnose:** pick the single weakest primary metric and the specific signals driving
   it (e.g. `eval-004: urgency pred=low exp=medium`). State ONE concrete hypothesis.
4. **Change exactly ONE thing** (smallest diff) among the allowed knobs:
   - enrichment prompt — `apps/api/app/services/enrichment.py` `SYSTEM_PROMPT`
   - synthesis prompt — `apps/api/app/services/synthesis.py` `SYSTEM_PROMPT`
   - clustering / severity config — `CLUSTER_*` / `SCORING_WEIGHT_*` (default constants
     in `synthesis.py` / `domain` scoring, or `apps/api/.env`)
   - golden set — `apps/api/app/evals/golden_set.json`: only fix a *demonstrably wrong*
     label or ADD items; **never** weaken a label to make a wrong prediction pass
   - eval harness — `apps/api/app/evals/harness.py` (e.g. refine tag matching)
5. **Re-run the eval** (same command).
6. **Accept or revert (significance, not raw delta):**
   - ACCEPT only if the change is a **statistically significant** improvement — McNemar
     `p < 0.05` with more items gained than lost (or the new accuracy's bootstrap CI
     lower bound clears the baseline point estimate) — AND no safety regression
     (`hallucination_rate` must not rise; `pii_leak_count` stays 0) AND the **held-out
     split** doesn't regress. A bump inside the CI is noise — don't accept it.
   - On ACCEPT: `npm run api:lint && npm run api:test` must pass, then `git commit` with a
     message naming the change and the before→after metric + p-value. Append an
     `{"kind":"accept", ...}` row to `history.jsonl`.
   - On REVERT: `git checkout -- <changed files>` and append a `{"kind":"reject",
     "hypothesis":...}` row so the same idea isn't retried.
   - **The ledger and reports are versioned evidence**: `git add` the new
     `history.jsonl` row AND the run's `reports/report_*.json` in the same commit
     (accepted or rejected). An uncommitted ledger is how the 17–18 Jul 2026 runs
     became unreproducible — the thesis cites runs the repo cannot show.
   - **Frozen n for confirmatory claims:** growing the golden set is a coverage
     decision, but any claim carried outside the loop (thesis, model card, sales)
     must be made at a sample size fixed BEFORE the run that produces it — testing
     at every size and claiming at the first p < 0.05 crossing is sequential
     testing without alpha control. Replication (consecutive significant runs at
     the frozen n) is the accepted substitute.
7. **Stop conditions:** stop the loop when ALL targets below are met, OR when 3
   consecutive iterations produced no accepted change. Print the metric trajectory from
   `history.jsonl`.

### Targets (tune as needed)
`sentiment_accuracy ≥ 0.90` · `urgency_accuracy ≥ 0.80` · `tag_f1 ≥ 0.60` ·
`hallucination_rate ≤ 0.05` · `pii_leak_count == 0`.
Safety metrics (hallucination, PII) are hard constraints every iteration — never traded
for accuracy gains.

### Never
- edit a golden label to match a wrong prediction;
- change more than one knob per iteration;
- commit on red lint/tests, or commit a change that didn't clear the accept gate.
