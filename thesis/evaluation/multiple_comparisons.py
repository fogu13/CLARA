"""Holm-adjusted paired tests over the committed McNemar results (§5A.3, §5A.6).

The harness writes one exact two-sided McNemar p-value per predictor pair and task
(results/mcnemar_paired.csv from run_eval.py; results/compare_runs_pairs.csv from
compare_runs.py). Several pairs are read on the same task, so a p-value near 0.05
read alone overstates the evidence. This script applies the Holm step-down
correction within two pre-defined families per task and writes
results/paired_tests_holm.csv:

  ordering       the six pairs among floor, learned model, generic prompt and the
                 GLM-5.2 production stage (results/mcnemar_paired.csv)
  configuration  the six pairs among the learned model, the generic prompt (the
                 reported 4 August run), the GLM-5.2 production stage and the
                 Mistral production stage (results/compare_runs_pairs.csv)

The generic-prompt repeats (run1-run3) are replicates of one configuration, not
further hypotheses, so they are not members of a family; §5A.4.2 reports their
range. No primary test was declared before the runs; the row for the contextual
path against the learned model on sentiment, the comparison §5A.3 leads with, is
marked so that the manuscript can say both what it is unadjusted and what it is
as one of six.

Run: python3 thesis/evaluation/multiple_comparisons.py   (reads only committed CSVs)
"""
from __future__ import annotations

import csv
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
RESULTS = os.environ.get("THESIS_RESULTS_DIR") or os.path.join(HERE, "results")

ORDERING_PAIRS = (
    "floor_vs_ml",
    "floor_vs_llm",
    "floor_vs_llm_production",
    "ml_vs_llm",
    "ml_vs_llm_production",
    "llm_vs_llm_production",
)
CONFIGURATION_PAIRS = (
    "ml_vs_glm_generic_run0",
    "ml_vs_glm_production",
    "ml_vs_mistral_production",
    "glm_generic_run0_vs_glm_production",
    "glm_generic_run0_vs_mistral_production",
    "glm_production_vs_mistral_production",
)
LEAD_COMPARISON = ("ordering", "sentiment", "ml_vs_llm")
COLUMNS = ["family", "task", "pair", "n_pairs", "b", "c", "p_raw", "m", "holm_p",
           "significant_raw_05", "significant_holm_05", "note"]


def holm(p_values: list[float]) -> list[float]:
    """Holm step-down adjusted p-values, in the input order (capped at 1, monotone)."""
    m = len(p_values)
    order = sorted(range(m), key=lambda i: p_values[i])
    adjusted = [0.0] * m
    running = 0.0
    for rank, idx in enumerate(order):
        candidate = min(1.0, (m - rank) * p_values[idx])
        running = max(running, candidate)
        adjusted[idx] = running
    return adjusted


def _read(path: str) -> list[dict]:
    with open(path, encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def _family_rows(rows: list[dict], family: str, wanted: tuple[str, ...]) -> list[dict]:
    out: list[dict] = []
    for task in sorted({r["task"] for r in rows}):
        members = [r for r in rows if r["task"] == task and r["pair"] in wanted]
        if not members:
            continue
        p_raw = [float(r["p_exact_two_sided"]) for r in members]
        adjusted = holm(p_raw)
        for r, p, hp in zip(members, p_raw, adjusted):
            note = ""
            if (family, task, r["pair"]) == LEAD_COMPARISON:
                note = ("the comparison §5A.3 leads with; no primary test was declared before the runs, "
                        "so it is one of six on this task")
            out.append({
                "family": family, "task": task, "pair": r["pair"], "n_pairs": r["n_pairs"],
                "b": r["b_first_only_correct"], "c": r["c_second_only_correct"],
                "p_raw": f"{p:.6f}", "m": len(members), "holm_p": f"{hp:.6f}",
                "significant_raw_05": "yes" if p < 0.05 else "no",
                "significant_holm_05": "yes" if hp < 0.05 else "no",
                "note": note,
            })
    return out


def compute(results_dir: str = RESULTS) -> list[dict]:
    rows = _family_rows(_read(os.path.join(results_dir, "mcnemar_paired.csv")), "ordering", ORDERING_PAIRS)
    rows += _family_rows(_read(os.path.join(results_dir, "compare_runs_pairs.csv")), "configuration", CONFIGURATION_PAIRS)
    return rows


def main(argv: list[str] | None = None) -> int:
    results_dir = argv[0] if argv else RESULTS
    rows = compute(results_dir)
    out = os.path.join(results_dir, "paired_tests_holm.csv")
    with open(out, "w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    width = max(len(r["pair"]) for r in rows)
    for r in rows:
        print(f"{r['family']:<14}{r['task']:<11}{r['pair']:<{width}}  b={r['b']:>3} c={r['c']:>3}  "
              f"p={float(r['p_raw']):.4f}  Holm(m={r['m']})={float(r['holm_p']):.4f}  "
              f"{'*' if r['significant_holm_05'] == 'yes' else ' '}")
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
