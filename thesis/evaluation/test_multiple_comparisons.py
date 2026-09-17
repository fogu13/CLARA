"""Plain-assert checks for multiple_comparisons.py.
Run: python3 thesis/evaluation/test_multiple_comparisons.py   (exits non-zero on failure)

Two kinds of check: pure-function and synthetic-folder tests that need no results files,
and assertions on the committed CSVs (results/ and results_mistral-small-2603/), which pin
the ten-comparison retrospective family the manuscript quotes (revision contract of
17 September 2026, section 4).
"""
from __future__ import annotations

import csv
import math
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import multiple_comparisons as MC  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))


def test_holm_step_down() -> None:
    # Textbook: sorted p (0.01, 0.03, 0.04), m = 3 -> 0.03, 0.06, 0.06 (monotone), in input order.
    assert [round(x, 6) for x in MC.holm([0.01, 0.04, 0.03])] == [0.03, 0.06, 0.06]
    assert MC.holm([0.5]) == [0.5]
    assert MC.holm([0.9, 0.8]) == [1.0, 1.0]
    assert MC.holm([]) == []
    # Zeros stay zero and never lift a later value above what Holm gives it; monotone from below.
    assert [round(x, 4) for x in MC.holm([0.0, 0.02, 0.5, 0.3, 0.0])] == [0.0, 0.06, 0.6, 0.6, 0.0]


def test_wald_interval_by_hand() -> None:
    # Sentiment floor -> TF-IDF: b = 15, c = 78, n = 153.
    # diff = 63 / 153 = 0.41176; SE = sqrt(93 - 63^2 / 153) / 153 = sqrt(67.0588) / 153 = 0.053523.
    diff, low, high = MC.paired_difference(15, 78, 153)
    assert abs(diff - 63 / 153) < 1e-12
    se = math.sqrt(93 - 63 ** 2 / 153) / 153
    assert abs(low - (diff - 1.959964 * se)) < 1e-12 and abs(high - (diff + 1.959964 * se)) < 1e-12
    assert (round(diff, 2), round(low, 2), round(high, 2)) == (0.41, 0.31, 0.52)
    # No discordant pairs: a zero difference with a zero-width interval, never a domain error.
    assert MC.paired_difference(0, 0, 10) == (0.0, 0.0, 0.0)


def _write(path: str, rows: list[dict]) -> None:
    cols = ["task", "pair", "n_pairs", "acc_first", "acc_second", "b_first_only_correct",
            "c_second_only_correct", "p_exact_two_sided"]
    with open(path, "w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=cols)
        writer.writeheader()
        for r in rows:
            writer.writerow({c: r.get(c, "") for c in cols})


def _row(task: str, pair: str, b: int, c: int, n: int) -> dict:
    return {"task": task, "pair": pair, "n_pairs": n, "acc_first": 0.5, "acc_second": 0.6,
            "b_first_only_correct": b, "c_second_only_correct": c, "p_exact_two_sided": 0.0}


def _synthetic_folders(*, drop: str | None = None) -> tuple[str, str]:
    results = tempfile.mkdtemp(prefix="clara_holm_")
    mistral = tempfile.mkdtemp(prefix="clara_holm_mistral_")
    floor = [_row("sentiment", p, 2, 20, 50) for p in MC.FLOOR_PAIRS if p != drop]
    floor += [_row("sentiment", "ml_vs_llm", 5, 6, 50)]  # a pair outside the family
    config = [_row("sentiment", p, 4, 4 + i, 50) for i, p in enumerate(MC.CONFIGURATION_PAIRS) if p != drop]
    config += [_row("sentiment", "glm_generic_run0_vs_glm_generic_run1", 1, 2, 50)]  # a replicate pair
    _write(os.path.join(results, "mcnemar_paired.csv"), floor)
    _write(os.path.join(mistral, "mcnemar_paired.csv"),
           [_row("sentiment", "floor_vs_llm_production", 3, 21, 50), _row("sentiment", "ml_vs_llm_production", 9, 8, 50)])
    _write(os.path.join(results, "compare_runs_pairs.csv"), config)
    return results, mistral


def test_family_is_assembled_from_the_three_sources_and_refuses_an_incomplete_one() -> None:
    results, mistral = _synthetic_folders()
    assert MC.main(["--results", results, "--mistral-results", mistral]) == 0
    with open(os.path.join(results, "paired_tests_holm.csv"), encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    assert list(rows[0]) == MC.COLUMNS
    assert [r["pair"] for r in rows] == list(MC.FAMILY_PAIRS) and len(rows) == 10
    assert {r["m"] for r in rows} == {"10"} and {r["family"] for r in rows} == {"retrospective"}
    assert all("retrospective" in r["note"] and "no primary test" in r["note"] for r in rows)
    renamed = next(r for r in rows if r["pair"] == "floor_vs_mistral_production")
    assert (renamed["b"], renamed["c"]) == ("3", "21")  # the Mistral folder's floor_vs_llm_production row
    # p_raw is recomputed from b and c, not copied from the source file (which carried 0.0 here).
    assert float(renamed["p_raw"]) > 0.0 and renamed["p_raw"] == f"{MC.M.mcnemar_p_from_counts(3, 21):.6f}"
    assert float(renamed["diff"]) == round(18 / 50, 4)
    for drop in ("floor_vs_llm", "ml_vs_mistral_production"):
        results, mistral = _synthetic_folders(drop=drop)
        try:
            MC.compute(results, mistral)
        except SystemExit as exc:
            assert "family incomplete" in str(exc) and drop in str(exc)
        else:
            raise AssertionError(f"a family missing {drop} must be refused")


def _committed() -> dict[tuple[str, str], dict]:
    rows = MC.compute(os.path.join(HERE, "results"), os.path.join(HERE, "results_mistral-small-2603"))
    return {(r["task"], r["pair"]): r for r in rows}


def test_committed_csvs_give_the_ten_comparison_family() -> None:
    rows = _committed()
    assert len(rows) == 20 and {r["m"] for r in rows.values()} == {"10"}
    assert rows[("sentiment", "ml_vs_glm_generic_run0")]["holm_p"] == "0.173756"
    assert rows[("risk", "ml_vs_glm_production")]["holm_p"] == "0.063732"
    assert rows[("risk", "glm_generic_run0_vs_mistral_production")]["holm_p"] == "0.063732"
    assert rows[("risk", "floor_vs_llm_production")]["holm_p"] == "0.123535"
    assert rows[("sentiment", "ml_vs_glm_generic_run0")]["significant_holm_05"] == "no"
    assert rows[("risk", "ml_vs_glm_production")]["significant_holm_05"] == "no"
    assert rows[("risk", "floor_vs_llm_production")]["significant_holm_05"] == "no"
    surviving = {k for k, r in rows.items() if r["significant_holm_05"] == "yes"}
    assert surviving == {
        ("sentiment", "floor_vs_ml"), ("sentiment", "floor_vs_llm"),
        ("sentiment", "floor_vs_llm_production"), ("sentiment", "floor_vs_mistral_production"),
        ("risk", "floor_vs_ml"), ("risk", "floor_vs_llm"), ("risk", "floor_vs_mistral_production"),
        ("risk", "glm_generic_run0_vs_glm_production"),
    }
    first = rows[("sentiment", "floor_vs_ml")]
    assert (first["b"], first["c"], first["n_pairs"]) == ("15", "78", "153")
    assert (first["diff"], first["diff_ci_low"], first["diff_ci_high"]) == ("0.4118", "0.3069", "0.5167")
    assert (first["acc_first"], first["acc_second"]) == ("0.3725", "0.7843")


def test_committed_holm_csv_is_regenerated() -> None:
    path = os.path.join(HERE, "results", "paired_tests_holm.csv")
    with open(path, encoding="utf-8", newline="") as fh:
        on_disk = list(csv.DictReader(fh))
    fresh = MC.compute(os.path.join(HERE, "results"), os.path.join(HERE, "results_mistral-small-2603"))
    assert [dict(r) for r in on_disk] == [{k: str(v) for k, v in r.items()} for r in fresh], (
        "results/paired_tests_holm.csv is stale: run python3 thesis/evaluation/multiple_comparisons.py"
    )


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
