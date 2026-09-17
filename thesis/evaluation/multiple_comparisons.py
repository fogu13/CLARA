"""Holm-adjusted paired tests over the committed McNemar results (§5A.3, §5A.6).

The harness writes one exact two-sided McNemar test per predictor pair and task
(results/mcnemar_paired.csv from run_eval.py; results/compare_runs_pairs.csv from
compare_runs.py; the production default's floor comparison lives in
results_mistral-small-2603/mcnemar_paired.csv). Several pairs are read on the same
task, so a p-value near 0.05 read alone overstates the evidence. This script applies
the Holm step-down correction within ONE retrospective family per task, the ten unique
comparisons among the five predictors reported in Chapter 5 (the lexicon floor, TF-IDF +
logistic regression, the generic prompt on GLM-5.2 run 0, the production stage on GLM-5.2
and the production stage on Mistral Small 4, the production default), and writes
results/paired_tests_holm.csv:

  floor_vs_ml, floor_vs_llm, floor_vs_llm_production
                 results/mcnemar_paired.csv
  floor_vs_mistral_production
                 results_mistral-small-2603/mcnemar_paired.csv, its row
                 floor_vs_llm_production renamed
  ml_vs_glm_generic_run0, ml_vs_glm_production, ml_vs_mistral_production,
  glm_generic_run0_vs_glm_production, glm_generic_run0_vs_mistral_production,
  glm_production_vs_mistral_production
                 results/compare_runs_pairs.csv

The generic-prompt repeats (run1 to run3) and the production-default repeats are
replicates of one configuration, not further hypotheses, so they are not members of the
family; §5A.4.2 reports their range. No primary test was declared before the runs, so the
family is retrospective and every row says so. The rows carry, besides the counts and
the adjusted p, the paired accuracy difference diff = (c - b) / n with a Wald 95%
interval, SE = sqrt(b + c - (c - b)^2 / n) / n: a descriptive effect-size range; the
Holm-adjusted exact test decides.

p_raw is the exact two-sided McNemar p recomputed from the discordant counts b and c at
full precision (metrics.mcnemar_p_from_counts): the source CSVs round it to six
decimals, and the Holm products are reported to six decimals as well.

Run: python3 thesis/evaluation/multiple_comparisons.py   (reads only committed CSVs)
     options: --results DIR (default results/), --mistral-results DIR
              (default results_mistral-small-2603/); the CSV is written under --results.
"""
from __future__ import annotations

import argparse
import csv
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import metrics as M  # noqa: E402

RESULTS = os.environ.get("THESIS_RESULTS_DIR") or os.path.join(HERE, "results")
MISTRAL_RESULTS = os.path.join(HERE, "results_mistral-small-2603")

FAMILY = "retrospective"
FLOOR_PAIRS = ("floor_vs_ml", "floor_vs_llm", "floor_vs_llm_production")
MISTRAL_FLOOR_PAIR = ("floor_vs_llm_production", "floor_vs_mistral_production")  # (source row, family name)
CONFIGURATION_PAIRS = (
    "ml_vs_glm_generic_run0",
    "ml_vs_glm_production",
    "ml_vs_mistral_production",
    "glm_generic_run0_vs_glm_production",
    "glm_generic_run0_vs_mistral_production",
    "glm_production_vs_mistral_production",
)
FAMILY_PAIRS = (*FLOOR_PAIRS, MISTRAL_FLOOR_PAIR[1], *CONFIGURATION_PAIRS)
FAMILY_SIZE = len(FAMILY_PAIRS)
NOTE = ("retrospective family: the ten unique comparisons among the five predictors on this task; "
        "no primary test was declared before the runs")
COLUMNS = ["family", "task", "pair", "n_pairs", "b", "c", "acc_first", "acc_second", "diff",
           "diff_ci_low", "diff_ci_high", "p_raw", "m", "holm_p", "significant_raw_05",
           "significant_holm_05", "note"]
Z95 = 1.959964


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


def paired_difference(b: int, c: int, n: int) -> tuple[float, float, float]:
    """Paired accuracy difference (second minus first) with its Wald 95% interval.

    diff = (c - b) / n; SE = sqrt(b + c - (c - b)^2 / n) / n. Descriptive only: on fewer
    than ten discordant pairs the interval is approximate.
    """
    diff = (c - b) / n
    se = math.sqrt(max(0.0, b + c - (c - b) ** 2 / n)) / n
    return diff, diff - Z95 * se, diff + Z95 * se


def _read(path: str) -> list[dict]:
    if not os.path.exists(path):
        raise SystemExit(f"missing source file: {path}")
    with open(path, encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def _members(results_dir: str, mistral_dir: str) -> dict[str, dict[str, dict]]:
    """The ten family members per task, keyed task -> pair -> source row."""
    out: dict[str, dict[str, dict]] = {}
    for r in _read(os.path.join(results_dir, "mcnemar_paired.csv")):
        if r["pair"] in FLOOR_PAIRS:
            out.setdefault(r["task"], {})[r["pair"]] = r
    for r in _read(os.path.join(mistral_dir, "mcnemar_paired.csv")):
        if r["pair"] == MISTRAL_FLOOR_PAIR[0]:
            out.setdefault(r["task"], {})[MISTRAL_FLOOR_PAIR[1]] = r
    for r in _read(os.path.join(results_dir, "compare_runs_pairs.csv")):
        if r["pair"] in CONFIGURATION_PAIRS:
            out.setdefault(r["task"], {})[r["pair"]] = r
    for task, members in out.items():
        missing = [p for p in FAMILY_PAIRS if p not in members]
        if missing:
            raise SystemExit(f"{task}: family incomplete, missing {', '.join(missing)}; "
                             f"a family of fewer than {FAMILY_SIZE} members would change every adjusted value")
    return out


def compute(results_dir: str = RESULTS, mistral_dir: str = MISTRAL_RESULTS) -> list[dict]:
    rows: list[dict] = []
    for task, members in sorted(_members(results_dir, mistral_dir).items()):
        ordered = [(pair, members[pair]) for pair in FAMILY_PAIRS]
        counts = [(int(r["b_first_only_correct"]), int(r["c_second_only_correct"]), int(r["n_pairs"]))
                  for _, r in ordered]
        p_raw = [M.mcnemar_p_from_counts(b, c) for b, c, _ in counts]
        adjusted = holm(p_raw)
        for (pair, r), (b, c, n), p, hp in zip(ordered, counts, p_raw, adjusted):
            diff, low, high = paired_difference(b, c, n)
            rows.append({
                "family": FAMILY, "task": task, "pair": pair, "n_pairs": str(n), "b": str(b), "c": str(c),
                "acc_first": f"{float(r['acc_first']):.4f}", "acc_second": f"{float(r['acc_second']):.4f}",
                "diff": f"{diff:.4f}", "diff_ci_low": f"{low:.4f}", "diff_ci_high": f"{high:.4f}",
                "p_raw": f"{p:.6f}", "m": str(len(ordered)), "holm_p": f"{hp:.6f}",
                "significant_raw_05": "yes" if p < 0.05 else "no",
                "significant_holm_05": "yes" if hp < 0.05 else "no",
                "note": NOTE,
            })
    return rows


def write(rows: list[dict], out: str) -> None:
    with open(out, "w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--results", default=RESULTS, help="folder with mcnemar_paired.csv and compare_runs_pairs.csv")
    parser.add_argument("--mistral-results", default=MISTRAL_RESULTS,
                        help="folder with the production default's mcnemar_paired.csv")
    args = parser.parse_args(argv)
    rows = compute(args.results, args.mistral_results)
    out = os.path.join(args.results, "paired_tests_holm.csv")
    write(rows, out)
    width = max(len(r["pair"]) for r in rows)
    for r in rows:
        print(f"{r['task']:<11}{r['pair']:<{width}}  b={r['b']:>3} c={r['c']:>3}  "
              f"diff={float(r['diff']):+.2f} ({float(r['diff_ci_low']):+.2f}, {float(r['diff_ci_high']):+.2f})  "
              f"p={float(r['p_raw']):.4f}  Holm(m={r['m']})={float(r['holm_p']):.4f}  "
              f"{'*' if r['significant_holm_05'] == 'yes' else ' '}")
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
