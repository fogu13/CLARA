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
items against the star-derived gold, risk on the items with a gold risk seed;
a missing field inside a scored item falls back to `neutral` / `low`; items a
run did not score are excluded from that run and from its pairs; b = first run
right and second wrong, c = the reverse, p = exact two-sided binomial(b + c).

Writes compare_runs_accuracy.csv (one row per run and task, with Wilson 95 %
intervals) and compare_runs_pairs.csv (one row per pair and task).
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

SENT_LABELS = ["negative", "neutral", "positive"]
RISK_LABELS = ["low", "medium", "high", "critical"]
DEFAULTS = {"sentiment": "neutral", "risk": "low"}


def load_run(path: str) -> dict[str, dict[str, str]]:
    """Return {task: {id: label}} from either prediction-file format."""
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    if isinstance(data, dict):
        return {task: {str(k): v for k, v in (data.get(task) or {}).items()}
                for task in DEFAULTS}
    out: dict[str, dict[str, str]] = {task: {} for task in DEFAULTS}
    for row in data:
        sid = str(row.get("id") or "")
        if not sid:
            continue
        for task, default in DEFAULTS.items():
            out[task][sid] = row.get(task) or default
    return out


def floor_run(sigs) -> dict[str, dict[str, str]]:
    return {"sentiment": {s.id: bl.predict_sentiment(s.text) for s in sigs if s.text},
            "risk": {s.id: bl.predict_risk(s.text) for s in sigs if s.text}}


def parse_runs(args, sigs) -> dict[str, dict[str, dict[str, str]]]:
    runs: dict[str, dict[str, dict[str, str]]] = {}
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


def compare(sigs, runs: dict[str, dict[str, dict[str, str]]]):
    rated = [s for s in sigs if s.star_rating is not None and s.text]
    have = [s for s in sigs if s.risk in RISK_LABELS and s.text]
    tasks = {
        "sentiment": (rated, lambda s: bl.gold_sentiment_from_stars(s.star_rating), SENT_LABELS),
        "risk": (have, lambda s: s.risk, RISK_LABELS),
    }
    acc_rows, pair_rows = [], []
    for task, (items, gold_fn, labels) in tasks.items():
        correct: dict[str, dict[str, bool]] = {}
        for name, run in runs.items():
            preds = run.get(task) or {}
            scored = [s for s in items if s.id in preds]
            if not scored:
                continue
            y_true = [gold_fn(s) for s in scored]
            y_pred = [preds[s.id] or DEFAULTS[task] for s in scored]
            sc = M.score(y_true, y_pred, labels)
            acc_rows.append({"task": task, "run": name, "n": sc["n"],
                             "accuracy": sc["accuracy"],
                             "accuracy_ci_low": sc["accuracy_ci_low"],
                             "accuracy_ci_high": sc["accuracy_ci_high"],
                             "f1_macro": sc["f1_macro"]})
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
                pair_rows.append({
                    "task": task, "pair": f"{a}_vs_{b_name}", "n_pairs": len(ids),
                    "acc_first": round(sum(av) / len(ids), 4),
                    "acc_second": round(sum(bv) / len(ids), 4),
                    "b_first_only_correct": b, "c_second_only_correct": c,
                    "p_exact_two_sided": round(p, 6),
                    "p_minority_gains_one": sens["p_minority_gains_one"],
                    "p_majority_loses_one": sens["p_majority_loses_one"],
                    "p_one_pair_swaps": sens["p_one_pair_swaps"],
                })
    return acc_rows, pair_rows


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
    acc_rows, pair_rows = compare(sigs, runs)
    os.makedirs(ns.out_dir, exist_ok=True)
    _write(os.path.join(ns.out_dir, "compare_runs_accuracy.csv"), acc_rows)
    _write(os.path.join(ns.out_dir, "compare_runs_pairs.csv"), pair_rows)
    print(f"corpus: {len(sigs)} signals; runs: {', '.join(runs)}")
    print("\n== accuracy (95 % Wilson) ==")
    _print(acc_rows)
    print("\n== paired exact McNemar ==")
    _print(pair_rows)
    print(f"\nwrote compare_runs_accuracy.csv and compare_runs_pairs.csv -> {ns.out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
