"""Plain-assert CLI test of compare_runs.py on synthetic items (no corpus, no model).
Run: python3 thesis/evaluation/test_compare_runs_cli.py   (exits non-zero on failure)

13 September 2026 review, finding F5: a run whose predictions are all invalid
used to vanish from the accuracy table, a pair with no eligible items was
skipped without a row, and a run that produced no rows left the previous
invocation's CSV on disk. The two cases below run the real CLI (main) with the
corpus loader replaced by twelve fake signals and check what lands on disk:

  (a) a valid keyword floor next to one wholly failed predictor;
  (b) two wholly failed predictors.
"""
from __future__ import annotations

import csv
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import compare_runs as CR  # noqa: E402
from test_run_eval_smoke import SIGS  # noqa: E402  (twelve synthetic signals)


def _rows(path: str) -> list[dict]:
    with open(path, encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def _header(path: str) -> list[str]:
    with open(path, encoding="utf-8") as fh:
        return next(csv.reader(fh))


def _stale(out_dir: str) -> None:
    for name in ("compare_runs_accuracy.csv", "compare_runs_pairs.csv", "compare_runs_agreement.csv"):
        with open(os.path.join(out_dir, name), "w", encoding="utf-8") as fh:
            fh.write("task,run,n\nsentiment,STALE_RUN,999\n")


def _failed_file(out_dir: str, name: str, label: str) -> str:
    path = os.path.join(out_dir, f"{name}.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump([{"id": s.id, "sentiment": label, "risk": label} for s in SIGS], fh)
    return path


def run() -> None:
    CR.load = lambda: list(SIGS)  # the CLI's corpus loader, replaced for the test

    # (a) valid floor + one wholly failed predictor
    out = tempfile.mkdtemp(prefix="clara_compare_runs_a_")
    _stale(out)
    bad = _failed_file(out, "bad", "Bogus")
    assert CR.main(["--out-dir", out, "floor", f"bad={bad}"]) == 0
    acc = _rows(os.path.join(out, "compare_runs_accuracy.csv"))
    assert _header(os.path.join(out, "compare_runs_accuracy.csv")) == CR.ACC_COLS
    assert {r["run"] for r in acc} == {"floor", "bad"}, acc
    assert not any(r["run"] == "STALE_RUN" for r in acc)
    bad_sent = next(r for r in acc if r["run"] == "bad" and r["task"] == "sentiment")
    assert bad_sent["n"] == "0" and bad_sent["accuracy"] == "" and bad_sent["f1_macro"] == "", bad_sent
    assert bad_sent["n_expected"] == "10" and bad_sent["n_valid"] == "0" and bad_sent["n_invalid"] == "10"
    assert bad_sent["coverage"] == "0.0" and bad_sent["accuracy_end_to_end"] == "0.0", bad_sent
    assert bad_sent["note"] == CR.NO_VALID_ROW
    floor_sent = next(r for r in acc if r["run"] == "floor" and r["task"] == "sentiment")
    assert floor_sent["n"] == "10" and floor_sent["note"] == "" and floor_sent["accuracy"] != ""
    pairs = _rows(os.path.join(out, "compare_runs_pairs.csv"))
    assert _header(os.path.join(out, "compare_runs_pairs.csv")) == CR.PAIR_COLS
    assert {(r["task"], r["pair"]) for r in pairs} == {("sentiment", "floor_vs_bad"), ("risk", "floor_vs_bad")}, pairs
    for r in pairs:
        assert r["n_pairs"] == "0" and r["p_exact_two_sided"] == "" and r["note"] == CR.NO_PAIR, r
    assert r["n_dropped"] in {"10", "12"}
    agree = _rows(os.path.join(out, "compare_runs_agreement.csv"))
    assert all(r["n_pairs"] == "0" and r["agreement"] == "" for r in agree) and len(agree) == 2

    # (b) two wholly failed predictors: header-only pair tables, explicit rows, no stale data
    out = tempfile.mkdtemp(prefix="clara_compare_runs_b_")
    _stale(out)
    bad1 = _failed_file(out, "bad1", "Bogus")
    bad2 = _failed_file(out, "bad2", "")
    assert CR.main(["--out-dir", out, f"bad1={bad1}", f"bad2={bad2}"]) == 0
    acc = _rows(os.path.join(out, "compare_runs_accuracy.csv"))
    assert {r["run"] for r in acc} == {"bad1", "bad2"} and len(acc) == 4, acc
    assert all(r["n"] == "0" and r["accuracy"] == "" and r["accuracy_end_to_end"] == "0.0" for r in acc)
    assert all(r["note"] == CR.NO_VALID_ROW for r in acc)
    pairs = _rows(os.path.join(out, "compare_runs_pairs.csv"))
    assert [r["pair"] for r in pairs] == ["bad1_vs_bad2", "bad1_vs_bad2"]
    assert all(r["n_pairs"] == "0" and r["note"] == CR.NO_PAIR for r in pairs)
    for name in ("compare_runs_accuracy.csv", "compare_runs_pairs.csv", "compare_runs_agreement.csv"):
        text = open(os.path.join(out, name), encoding="utf-8").read()
        assert "STALE_RUN" not in text, name

    # _write alone: an empty table is a header, never a no-op.
    empty = os.path.join(out, "empty.csv")
    with open(empty, "w", encoding="utf-8") as fh:
        fh.write("old,data\n1,2\n")
    CR._write(empty, [], CR.AGREE_COLS)
    assert open(empty, encoding="utf-8").read().strip() == ",".join(CR.AGREE_COLS)
    print("compare_runs CLI OK — failed runs and absent pairs are rows, stale files never survive")


if __name__ == "__main__":
    run()
