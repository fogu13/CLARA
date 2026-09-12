# Triage eval-improve loop

Run this with the loop skill, self-paced:

```
/loop /eval-triage
```

`/eval-triage` is meant to be a slash command with the body below. **There is no
`.claude/commands/eval-triage.md` in this repository** (`.claude/` is gitignored), so
either create that file locally from this document or paste the "One iteration" section
as the loop prompt. Each tick performs ONE measured improvement iteration and either
accepts + commits it or reverts it. The loop ends itself when the targets are met or it
stalls.

Prerequisite (one-time): set cloud creds in `apps/api/.env` — `AI_BASE_URL`,
`AI_API_KEY`, `AI_MODEL` (any OpenAI-compatible model). The runner pins
`AI_TEMPERATURE=0` for determinism (the eval model is still not deterministic at
temperature 0; that is why every A/B is measured within one run, on paired items).

---

## The two splits, and what each is for

`golden_set.json` carries a `split` per item: **optimization** (70 items) and
**held_out** (30 items).

- The **optimisation split** is what the loop tunes on. Accept/reject decisions read it,
  and its per-item failures are printed so you can diagnose.
- The **held-out split is a frozen guardrail.** It is *scored* on every run (the runner
  cannot avoid that — the golden set is enriched as a whole) but it is **not inspected
  per item and it is not part of accept/reject.** The printed report shows only its
  aggregate accuracies and the per-split paired A/B; per-item held-out failures are
  withheld unless you pass `--reveal-held-out`, and doing so is a look at the guardrail
  set that you must be able to justify.
- **Every scoring of the held-out split is logged.** Each `history.jsonl` eval row
  carries `held_out_scored: true` and a running `held_out_consultations` count (prior
  flagged rows + 1). `history.jsonl` is gitignored, so this count is machine-local; it
  exists so the number of looks is on record at all.
- **A repeatedly consulted validation set is not an independent final test.** A split
  that has been scored on every iteration has informed the tuning through the aggregate
  numbers alone, whatever the per-item discipline. Say so wherever its numbers are
  quoted, and quote the consultation count next to them.
- **The only valid held-out statement about exemplars is the per-split paired effect**
  (`by_split_ab.held_out`: off/on accuracy, gained/lost, exact McNemar p, diff with a 95 %
  paired-bootstrap interval). The pooled figure (`enrichment_ab`, labelled
  `enrichment_ab_pooled` with `ab_scope_note`) mixes both strata and is exploratory.
  Neither "held-out accuracy with exemplars on" nor a pooled p-value says anything
  about the exemplars' effect on items the loop never tuned on.
- **The "final" held-out read is declared once, with the date**, in the ledger and in
  whatever document quotes it (thesis, model card). Any later tuning — prompt, exemplars,
  or a golden-set correction — re-opens it: the next read is again a consultation, not a
  final test, and the declaration must be repeated with the new date and the count.

## One iteration

You are improving CLARA's triage model by measured eval hill-climbing. Repo root is the
CWD; backend is `apps/api`; work on the current git branch.

**Ledger:** read `apps/api/app/evals/history.jsonl`. The last `kind:"eval"`/`accept`
row is the current baseline. If `apps/api/app/evals/run_live.py` is missing, STOP and
report — setup is incomplete.

1. **Run the eval:** `cd apps/api && python3 -m app.evals.run_live`. It scores real
   `enrich_signals` output vs `golden_set.json` **twice within the run** (exemplars off vs
   on) and reports: accuracies with **95 % Wilson intervals**, the **in-run paired
   exemplar A/B** (exact McNemar; pooled and per split), per-language and per-split
   accuracy, the hallucination / PII guards, and the synthesis learning-influence probe.
   It does **not** run a McNemar test against the previous run — runs are not paired
   (the model is not deterministic), so cross-run comparison is by interval overlap and
   replication only. (Seed learnings first, once: `python3 -m app.evals.simulate_outcomes`.)
   Read the printed **optimisation-split** failure table and the A/B lines.
2. **First run only:** record it as the baseline and stop this iteration.
3. **Diagnose:** pick the single weakest primary metric on the optimisation split and the
   specific signals driving it (e.g. `eval-004: urgency pred=low exp=medium`). State ONE
   concrete hypothesis. Held-out ids never appear in a hypothesis.
4. **Change exactly ONE thing** (smallest diff). The loop's knobs are the **prompt and the
   exemplars only**:
   - enrichment prompt — `apps/api/app/services/enrichment.py` `SYSTEM_PROMPT`
   - exemplars — `apps/api/app/services/exemplar_store.py` `DEFAULT_EXEMPLARS`
     (must stay disjoint from the golden set)
   - synthesis prompt — `apps/api/app/services/synthesis.py` `SYSTEM_PROMPT`
     (affects the synthesis metrics only)
   - clustering / severity config — `CLUSTER_*` / `SCORING_WEIGHT_*` (synthesis only)

   **Not knobs:** `golden_set.json` and `harness.py`. Editing a golden label to improve a
   score is forbidden. A golden-set *correction* (a demonstrably wrong label, with the
   reason written into the commit message and the ledger row) is a separate, documented
   change outside an iteration: it changes `config.golden_set_sha256`, re-opens the
   held-out read, and resets the baseline. Harness changes (e.g. tag matching) are
   likewise outside the loop and must not be judged by whether the score went up.
5. **Re-run the eval** (same command).
6. **Accept or revert (significance, not raw delta):**
   - ACCEPT only if the change is a **statistically significant** improvement **on the
     optimisation split's paired A/B** — `by_split_ab.optimization` shows exact McNemar
     `p < 0.05` with more items gained than lost for the metric under test — AND the
     safety guards hold: `hallucination_rate` must not rise (compared only when both
     runs report a number; `null` means "not evaluated", not 0) and `pii_leak_count`
     stays 0. A bump inside the Wilson interval, or a pooled p-value, is not an accept.
     The held-out split plays no part in accept/reject: do not accept because it went
     up and do not reject because it went down — its per-split A/B is recorded, not
     acted on.
   - Note: a prompt change with exemplars ON is compared *within* the run against
     exemplars OFF, which is the exemplar effect, not the prompt effect. To test a prompt
     change, compare the new run's optimisation-split accuracy and interval against the
     baseline run's, and require replication (a second run reproducing the gain) before
     calling it accepted; the interval width tells you when a delta is noise.
   - If exemplars are disabled (`ENRICH_FEWSHOT=0`), the runner reports no A/B at all
     (`ab_note`); never present two identical arms as an experiment.
   - On ACCEPT: `npm run api:lint && npm run api:test` must pass, then `git commit` with a
     message naming the change and the before→after metric + p-value. Append an
     `{"kind":"accept", ...}` row to `history.jsonl`.
   - On REVERT: `git checkout -- <changed files>` and append a `{"kind":"reject",
     "hypothesis":...}` row so the same idea isn't retried.
   - **The ledger and reports are versioned evidence**: copy the run's
     `reports/report_*.json` and the new `history.jsonl` rows into a committed location
     (both files are gitignored in place) in the same commit (accepted or rejected). An
     uncommitted ledger is how the 17–18 Jul 2026 runs became unreproducible — the
     thesis cites runs the repo cannot show. The report's `config` block (golden-set,
     held-out-id and exemplar hashes, git commit) is what makes a run citable.
   - **Frozen n for confirmatory claims:** growing the golden set is a coverage
     decision, but any claim carried outside the loop (thesis, model card, sales)
     must be made at a sample size fixed BEFORE the run that produces it — testing
     at every size and claiming at the first p < 0.05 crossing is sequential
     testing without alpha control. Replication (consecutive significant runs at
     the frozen n) is the accepted substitute.
7. **Stop conditions:** stop the loop when ALL targets below are met, OR when 3
   consecutive iterations produced no accepted change. Print the metric trajectory from
   `history.jsonl`, including the `held_out_consultations` count.

### Targets (tune as needed)
Measured on the optimisation split:
`sentiment_accuracy ≥ 0.90` · `urgency_accuracy ≥ 0.80` · `tag_f1 ≥ 0.60` ·
`hallucination_rate ≤ 0.05` (when evaluated) · `pii_leak_count == 0`.
Safety metrics (hallucination, PII) are hard constraints every iteration — never traded
for accuracy gains. `hallucination_rate` is an English-only token-grounding heuristic
computed over the eligible EN items (`hallucination_eligible`); it says nothing about
the DE items (`hallucination_excluded`).

### Declaring the final held-out read
When tuning stops, run the eval once more, and record in the ledger and in the citing
document: the date, `config.golden_set_sha256`, `config.held_out_ids_sha256`,
`config.exemplars_sha256`, `held_out_consultations`, and `by_split_ab.held_out`. State
that the split was consulted N times before this read. Any change to prompt, exemplars
or golden set after this point re-opens it.

### Never
- edit a golden label to match a wrong prediction, or to move any score;
- inspect held-out failures per item to form a hypothesis;
- accept or reject on the held-out split, or on the pooled A/B;
- change more than one knob per iteration;
- commit on red lint/tests, or commit a change that didn't clear the accept gate.
