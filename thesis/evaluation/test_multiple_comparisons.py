"""Plain-assert checks for multiple_comparisons.py (no corpus, no results files needed).
Run: python3 thesis/evaluation/test_multiple_comparisons.py   (exits non-zero on failure)
"""
from __future__ import annotations

import csv
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import multiple_comparisons as MC  # noqa: E402


def test_holm_step_down() -> None:
    # Textbook: sorted p (0.01, 0.03, 0.04), m = 3 -> 0.03, 0.06, 0.06 (monotone), in input order.
    assert [round(x, 6) for x in MC.holm([0.01, 0.04, 0.03])] == [0.03, 0.06, 0.06]
    assert MC.holm([0.5]) == [0.5]
    assert MC.holm([0.9, 0.8]) == [1.0, 1.0]
    assert MC.holm([]) == []
    # A zero stays zero and never lifts a later value above what Holm gives it.
    assert [round(x, 4) for x in MC.holm([0.0, 0.028959, 0.226562, 0.281042, 0.0, 0.0])] == [
        0.0, 0.0869, 0.4531, 0.4531, 0.0, 0.0,
    ]


def _write(path: str, rows: list[dict]) -> None:
    cols = ["task", "pair", "n_pairs", "acc_first", "acc_second", "b_first_only_correct",
            "c_second_only_correct", "p_exact_two_sided"]
    with open(path, "w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=cols)
        writer.writeheader()
        for r in rows:
            writer.writerow({c: r.get(c, "") for c in cols})


def test_families_are_adjusted_per_task_and_the_lead_row_is_marked() -> None:
    tmp = tempfile.mkdtemp(prefix="clara_holm_")
    ordering = [
        {"task": "sentiment", "pair": p, "n_pairs": 153, "b_first_only_correct": 1, "c_second_only_correct": 2,
         "p_exact_two_sided": v}
        for p, v in zip(MC.ORDERING_PAIRS, (0.0, 0.0, 0.0, 0.028959, 0.281042, 0.226562))
    ] + [
        {"task": "risk", "pair": p, "n_pairs": 106, "b_first_only_correct": 1, "c_second_only_correct": 2,
         "p_exact_two_sided": v}
        for p, v in zip(MC.ORDERING_PAIRS, (1.5e-5, 0.0, 0.030884, 0.643969, 0.01266, 1.5e-5))
    ] + [{"task": "sentiment", "pair": "not_in_family", "n_pairs": 1, "b_first_only_correct": 0,
          "c_second_only_correct": 0, "p_exact_two_sided": 0.001}]
    config = [
        {"task": "sentiment", "pair": p, "n_pairs": 153, "b_first_only_correct": 3, "c_second_only_correct": 4,
         "p_exact_two_sided": v}
        for p, v in zip(MC.CONFIGURATION_PAIRS, (0.028959, 0.281042, 0.122078, 0.226562, 0.453125, 0.726562))
    ] + [{"task": "sentiment", "pair": "glm_generic_run0_vs_glm_generic_run1", "n_pairs": 153,
          "b_first_only_correct": 1, "c_second_only_correct": 2, "p_exact_two_sided": 1.0}]
    _write(os.path.join(tmp, "mcnemar_paired.csv"), ordering)
    _write(os.path.join(tmp, "compare_runs_pairs.csv"), config)

    assert MC.main([tmp]) == 0
    with open(os.path.join(tmp, "paired_tests_holm.csv"), encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    assert [r for r in rows if r["pair"] in ("not_in_family", "glm_generic_run0_vs_glm_generic_run1")] == []
    lead = next(r for r in rows if r["family"] == "ordering" and r["task"] == "sentiment" and r["pair"] == "ml_vs_llm")
    assert lead["m"] == "6" and lead["significant_raw_05"] == "yes" and lead["significant_holm_05"] == "no"
    assert abs(float(lead["holm_p"]) - 0.086877) < 1e-6 and "no primary test" in lead["note"]
    risk = {r["pair"]: r for r in rows if r["family"] == "ordering" and r["task"] == "risk"}
    assert risk["ml_vs_llm_production"]["significant_holm_05"] == "yes"   # 0.01266 * 3 = 0.038
    assert risk["floor_vs_llm_production"]["significant_holm_05"] == "no"  # 0.030884 * 2 = 0.062
    assert risk["ml_vs_llm"]["holm_p"] == "0.643969"
    cfg = {r["pair"]: r for r in rows if r["family"] == "configuration"}
    assert len(cfg) == 6 and cfg["ml_vs_glm_generic_run0"]["significant_holm_05"] == "no"
    assert all(r["note"] == "" for r in rows if r is not lead)


if __name__ == "__main__":
    failures = 0
    for name, func in sorted(globals().items()):
        if name.startswith("test_") and callable(func):
            try:
                func()
                print(f"ok   {name}")
            except AssertionError as exc:
                failures += 1
                print(f"FAIL {name}: {exc}")
    sys.exit(1 if failures else 0)
