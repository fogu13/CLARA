"""Paired comparison of prediction runs that live in different results folders.

run_eval.py pairs the predictors inside ONE results folder. The production-path
question in Chapter 5 (§5A.2) needs pairs ACROSS folders: the same model on the
generic prompt and on the production path (pipeline effect), and two models on
the production path (model effect). This script scores any number of labelled
prediction files on the same gold and reports, for every pair, the exact
McNemar test with the three single-item sensitivities that run_eval.py uses.

usage (from the repository root, THESIS_DATA_DIR set as for run_eval.py):

  python thesis/evaluation/compare_runs.py \\
      --out-dir thesis/evaluation/results \\
      floor \\
      ml=thesis/evaluation/results/predictions_ml.json \\
      glm_generic=thesis/evaluation/results/predictions_llm.json \\
      glm_production=thesis/evaluation/results/predictions_llm_production.json \\
      mistral_production=thesis/evaluation/results_mistral-small-2603/predictions_llm_production.json

Each positional argument is `label=path`, or the bare word `floor` for the
keyword baseline. A path may hold either format the harness writes: a list of
per-signal dicts with `id`, `sentiment`, `risk` (predict_llm*.py) or a dict
`{"sentiment": {id: label}, "risk": {id: label}}` (ml_baseline via run_eval).

Conventions match run_eval.significance(): sentiment is scored on the rated
items against the star-derived gold, risk on the items with a gold risk seed.
Every run's file is first passed through prediction_validation: a row whose
label is missing, empty or outside the task vocabulary is INVALID, a gold item
with no row is MISSING, duplicate ids keep their first row, rows for unknown
ids are counted and ignored. Nothing is defaulted to `neutral` / `low`. The
accuracy table carries both views per run — coverage-conditioned (valid rows
only) and end-to-end (missing / invalid count as wrong over every gold item) —
with the counts; pairs use the intersection of VALID ids and report n_dropped;
b = first run right and second wrong, c = the reverse, p = exact two-sided
binomial(b + c).

Writes compare_runs_accuracy.csv (one row per run and task, with Wilson 95 %
intervals), compare_runs_pairs.csv (one row per pair and task) and
compare_runs_agreement.csv (per pair and task: the share of jointly scored
items given the identical label, which is the run-to-run stability figure
when the runs are repeats of one configuration).
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import baseline as bl  # noqa: E402
import metrics as M  # noqa: E402
from load_datasets import load  # noqa: E402
from prediction_validation import validate_predictions  # noqa: E402

SENT_LABELS = ["negative", "neutral", "positive"]
RISK_LABELS = ["low", "medium", "high", "critical"]
TASKS = ("sentiment", "risk")


def load_run(path: str) -> dict[str, list[dict]]:
    """Return {task: rows} from either prediction-file format, unvalidated.

    Rows are `{"id": ..., <task>: <raw label>}` exactly as the file carries
    them (no defaulting, no de-duplication); compare() validates them against
    the gold ids per task.
    """
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    if isinstance(data, dict):
        return {task: [{"id": k, task: v} for k, v in (data.get(task) or {}).items()]
                for task in TASKS}
    return {task: [{"id": row.get("id"), task: row.get(task)} for row in data]
            for task in TASKS}


def floor_run(sigs) -> dict[str, list[dict]]:
    return {"sentiment": [{"id": s.id, "sentiment": bl.predict_sentiment(s.text)}
                          for s in sigs if s.text],
            "risk": [{"id": s.id, "risk": bl.predict_risk(s.text)} for s in sigs if s.text]}


def parse_runs(args, sigs) -> dict[str, dict[str, list[dict]]]:
    runs: dict[str, dict[str, list[dict]]] = {}
    for spec in args:
        if spec == "floor":
            runs["floor"] = floor_run(sigs)
            continue
        if "=" not in spec:
            raise SystemExit(f"expected label=path or 'floor', got {spec!r}")
        label, path = spec.split("=", 1)
        if not os.path.exists(path):
            raise SystemExit(f"{label}: no such file {path}")
        runs[label] = load_run(path)
    if len(runs) < 2:
        raise SystemExit("need at least two runs to compare")
    return runs


def compare(sigs, runs: dict[str, dict[str, list[dict]]]):
    rated = [s for s in sigs if s.star_rating is not None and s.text]
    have = [s for s in sigs if s.risk in RISK_LABELS and s.text]
    tasks = {
        "sentiment": (rated, lambda s: bl.gold_sentiment_from_stars(s.star_rating), SENT_LABELS),
        "risk": (have, lambda s: s.risk, RISK_LABELS),
    }
    acc_rows, pair_rows, agree_rows = [], [], []
    for task, (items, gold_fn, labels) in tasks.items():
        if not items:
            continue
        correct: dict[str, dict[str, bool]] = {}
        labelled: dict[str, dict[str, str]] = {}
        for name, run in runs.items():
            vs = validate_predictions(run.get(task) or [], expected_ids=[s.id for s in items],
                                      field=task, labels=labels)
            scored = [s for s in items if s.id in vs.by_id]
            if not scored:
                continue
            y_true = [gold_fn(s) for s in scored]
            y_pred = [vs.by_id[s.id] for s in scored]
            labelled[name] = {s.id: p for s, p in zip(scored, y_pred)}
            sc = M.score(y_true, y_pred, labels)
            n_correct = sum(1 for t, p in zip(y_true, y_pred) if t == p)
            e2e_lo, e2e_hi = M.wilson_interval(n_correct, vs.n_expected)
            acc_rows.append({"task": task, "run": name, "n": sc["n"],
                             "accuracy": sc["accuracy"],
                             "accuracy_ci_low": sc["accuracy_ci_low"],
                             "accuracy_ci_high": sc["accuracy_ci_high"],
                             "f1_macro": sc["f1_macro"],
                             # end-to-end view: every gold item in the denominator,
                             # missing / invalid predictions count as wrong
                             "n_expected": vs.n_expected, "n_valid": vs.n_valid,
                             "n_invalid": vs.n_invalid, "n_missing": vs.n_missing,
                             "n_unknown_ids": vs.n_unknown_ids,
                             "n_duplicate_ids": vs.n_duplicate_ids,
                             "coverage": vs.coverage,
                             "accuracy_end_to_end": round(n_correct / vs.n_expected, 4),
                             "accuracy_end_to_end_ci_low": e2e_lo,
                             "accuracy_end_to_end_ci_high": e2e_hi})
            correct[name] = {s.id: p == t for s, p, t in zip(scored, y_pred, y_true)}
        names = list(correct)
        for i, a in enumerate(names):
            for b_name in names[i + 1:]:
                ids = sorted(set(correct[a]) & set(correct[b_name]))
                if not ids:
                    continue
                av = [correct[a][x] for x in ids]
                bv = [correct[b_name][x] for x in ids]
                b, c, p = M.mcnemar_exact(av, bv)
                sens = M.mcnemar_sensitivity(b, c)
                same = sum(labelled[a][x] == labelled[b_name][x] for x in ids)
                lo, hi = M.wilson_interval(same, len(ids))
                agree_rows.append({"task": task, "pair": f"{a}_vs_{b_name}", "n_pairs": len(ids),
                                   "n_same_label": same, "agreement": round(same / len(ids), 4),
                                   "agreement_ci_low": lo, "agreement_ci_high": hi})
                pair_rows.append({
                    "task": task, "pair": f"{a}_vs_{b_name}", "n_pairs": len(ids),
                    "n_dropped": len(items) - len(ids),
                    "acc_first": round(sum(av) / len(ids), 4),
                    "acc_second": round(sum(bv) / len(ids), 4),
                    "b_first_only_correct": b, "c_second_only_correct": c,
                    "p_exact_two_sided": round(p, 6),
                    "p_minority_gains_one": sens["p_minority_gains_one"],
                    "p_majority_loses_one": sens["p_majority_loses_one"],
                    "p_one_pair_swaps": sens["p_one_pair_swaps"],
                })
    return acc_rows, pair_rows, agree_rows


def _write(path: str, rows: list[dict]) -> None:
    if not rows:
        return
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)


def _print(rows: list[dict]) -> None:
    if not rows:
        return
    cols = list(rows[0].keys())
    widths = {c: max(len(c), *(len(str(r[c])) for r in rows)) for c in cols}
    print("  ".join(c.ljust(widths[c]) for c in cols))
    for r in rows:
        print("  ".join(str(r[c]).ljust(widths[c]) for c in cols))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--out-dir", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "results"))
    ap.add_argument("runs", nargs="+", help="label=path, or 'floor'")
    ns = ap.parse_args(argv)
    sigs = load()
    runs = parse_runs(ns.runs, sigs)
    acc_rows, pair_rows, agree_rows = compare(sigs, runs)
    os.makedirs(ns.out_dir, exist_ok=True)
    _write(os.path.join(ns.out_dir, "compare_runs_accuracy.csv"), acc_rows)
    _write(os.path.join(ns.out_dir, "compare_runs_pairs.csv"), pair_rows)
    _write(os.path.join(ns.out_dir, "compare_runs_agreement.csv"), agree_rows)
    print(f"corpus: {len(sigs)} signals; runs: {', '.join(runs)}")
    print("\n== accuracy (95 % Wilson) ==")
    _print(acc_rows)
    print("\n== paired exact McNemar ==")
    _print(pair_rows)
    print("\n== label agreement between runs (95 % Wilson) ==")
    _print(agree_rows)
    print(f"\nwrote compare_runs_accuracy.csv, compare_runs_pairs.csv and compare_runs_agreement.csv -> {ns.out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
