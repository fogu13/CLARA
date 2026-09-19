"""Plain-assert checks for calibration.py on hand-made values (no corpus, no model).
Run: python3 thesis/evaluation/test_calibration.py   (exits non-zero on failure)
"""
from __future__ import annotations

import csv
import json
import math
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import calibration as C


def _choice(choice: str, probs: dict[str, float]) -> dict:
    return {"type": "choice", "choice": choice, "probabilities": probs, "confidence": max(probs.values())}


def test_reliability_bins_and_ece_known_values() -> None:
    confs = [0.95, 0.95, 0.55, 0.55]
    oks = [True, False, True, True]
    rows = C.reliability_bins(confs, oks, 10)
    assert len(rows) == 10 and rows[9]["n"] == 2 and rows[9]["accuracy"] == 0.5 and rows[9]["confidence_mean"] == 0.95
    assert rows[5]["n"] == 2 and rows[5]["accuracy"] == 1.0  # (0.5, 0.6]
    assert abs(C.ece(confs, oks, 10) - 0.45) < 1e-9  # 0.5*0.45 + 0.5*0.45
    assert C.ece([1.0, 1.0], [True, True]) == 0.0
    assert C.ece([], []) is None
    assert C.reliability_bins([0.0], [False], 10)[0]["n"] == 1  # a zero confidence lands in the first bin
    assert C.reliability_bins([1.0], [True], 10)[9]["n"] == 1  # and a full one in the last


def test_brier_and_log_loss() -> None:
    assert C.brier({"a": 1.0, "b": 0.0}, "a") == 0.0
    assert abs(C.brier({k: 0.25 for k in "abcd"}, "a") - 0.75) < 1e-9
    assert abs(C.brier({"a": 0.5, "b": 0.5}, "c") - 1.5) < 1e-9  # gold outside the distribution
    assert C.log_loss(1.0) == 0.0
    assert abs(C.log_loss(0.0) - (-math.log(1e-6))) < 1e-9
    assert abs(C.log_loss(0.5) - math.log(2)) < 1e-9


def test_coverage_curve_endpoints_and_monotone() -> None:
    confs = [0.99, 0.8, 0.6, 0.3]
    oks = [True, True, False, False]
    rows = C.coverage_curve(confs, oks, [0.0, 0.5, 0.7, 0.999])
    assert rows[0]["coverage"] == 1.0 and rows[0]["accuracy_covered"] == 0.5 and rows[0]["accuracy_end_to_end"] == 0.5
    assert [r["coverage"] for r in rows] == [1.0, 0.75, 0.5, 0.0]
    assert rows[1]["accuracy_covered"] == round(2 / 3, 4) and rows[1]["accuracy_end_to_end"] == 0.5
    assert rows[2]["accuracy_covered"] == 1.0 and rows[2]["accuracy_end_to_end"] == 0.5
    assert rows[3]["accuracy_covered"] is None and rows[3]["accuracy_covered_ci_low"] is None
    assert all(r["accuracy_end_to_end"] <= (r["accuracy_covered"] or 0) for r in rows if r["n_covered"])


def test_observation_reads_each_answer_type() -> None:
    obs = C.observation(_choice("high", {"low": 0.1, "medium": 0.2, "high": 0.6, "critical": 0.1}), "critical")
    assert obs["pred"] == "high" and obs["confidence"] == 0.6 and obs["correct"] is False and obs["p_gold"] == 0.1
    score = {"type": "score", "score": 2.4, "legend": {"0": "low: x", "1": "medium: y", "2": "high: z", "3": "critical: w"},
             "probabilities": {"0": 0.05, "1": 0.1, "2": 0.5, "3": 0.35}, "confidence": 0.5}
    obs = C.observation(score, "critical")
    assert obs["pred"] == "high" and obs["correct"] is False and obs["p_gold"] == 0.35
    assert abs(obs["level_error"] - 0.6) < 1e-9
    obs = C.observation({"type": "noul", "noul": 0.8}, True)
    assert obs["pred"] == "true" and obs["correct"] is True and obs["gold_true"] is True and obs["confidence"] == 0.8
    obs = C.observation({"type": "noul", "noul": 0.2}, True)
    assert obs["pred"] == "false" and obs["correct"] is False and obs["p_gold"] == 0.2
    assert C.observation(None, "high") is None and C.observation(_choice("a", {"a": 1.0}), None) is None
    assert C.observation({"type": "choice", "choice": "a"}, "a") is None  # no distribution


def _records() -> list[dict]:
    rows = []
    for i in range(12):
        lang = "en" if i < 6 else "de"
        gold_risk = ["low", "medium", "high", "critical"][i % 4]
        hit = i % 3 != 0  # two of three right
        pred_risk = gold_risk if hit else "low" if gold_risk != "low" else "high"
        probs = {k: 0.05 for k in ["low", "medium", "high", "critical"]}
        probs[pred_risk] = 0.85
        p_esc = 0.9 if gold_risk in ("high", "critical") else 0.2
        if not hit:
            p_esc = 1.0 - p_esc
        rows.append({"id": f"R-{i}", "language": lang,
                     "gold": {"sentiment": "negative", "risk": gold_risk, "risk_level": gold_risk,
                              "escalate": gold_risk in ("high", "critical")},
                     "answers": {"sentiment": _choice("negative" if hit else "positive",
                                                      {"negative": 0.7 if hit else 0.3, "neutral": 0.1,
                                                       "positive": 0.2 if hit else 0.6}),
                                 "risk": _choice(pred_risk, probs),
                                 "risk_level": {"type": "score", "score": 1.5,
                                                "legend": {"0": "low: a", "1": "medium: b", "2": "high: c", "3": "critical: d"},
                                                "probabilities": {"0": 0.1, "1": 0.4, "2": 0.4, "3": 0.1}, "confidence": 0.4},
                                 "escalate": {"type": "noul", "noul": p_esc}}})
    return rows


def test_analyse_builds_tables_with_strata() -> None:
    tables = C.analyse(_records())
    cal = {(r["task"], r["stratum"]): r for r in tables["calibration"]}
    assert {"sentiment", "risk", "risk_level"} == {t for t, _ in cal}
    assert {"all", "en", "de"} == {s for _, s in cal}
    assert cal[("risk", "all")]["n"] == 12 and cal[("risk", "all")]["accuracy"] == round(8 / 12, 4)
    assert cal[("risk", "en")]["n"] == 6 and cal[("risk", "de")]["n"] == 6
    assert cal[("risk", "all")]["mean_confidence"] == 0.85
    assert cal[("risk", "all")]["n_classes"] == 4 and cal[("risk", "all")]["majority_floor"] == 0.25
    assert cal[("sentiment", "all")]["n_classes"] == 1 and cal[("sentiment", "all")]["majority_floor"] == 1.0
    assert cal[("risk", "all")]["confidence_minus_accuracy"] == round(0.85 - 8 / 12, 4)
    assert cal[("risk_level", "all")]["level_mae"] is not None
    assert cal[("sentiment", "all")]["note"].startswith("n below 30")
    cov = [r for r in tables["coverage"] if r["task"] == "risk" and r["stratum"] == "all"]
    assert [r["threshold"] for r in cov] == C.DEFAULT_THRESHOLDS and cov[0]["coverage"] == 1.0
    assert cov[-1]["n_covered"] == 0  # nothing at 0.95 with a top probability of 0.85
    rel = [r for r in tables["reliability"] if r["task"] == "risk" and r["stratum"] == "all"]
    assert len(rel) == C.DEFAULT_BINS and sum(r["n"] for r in rel) == 12
    esc = {(r["source"], r["stratum"]): r for r in tables["escalation"]}
    assert ("escalate", "all") in esc and ("escalate_from_risk_choice", "all") in esc
    assert esc[("escalate", "all")]["n_gold_escalate"] == 6 and esc[("escalate", "all")]["base_rate"] == 0.5
    assert esc[("escalate_from_risk_choice", "all")]["n"] == 12
    # The Noul recall: gold-escalate items i in {2,3,6,7,10,11}; misses where i % 3 == 0 -> i = 3, 6 -> 4/6.
    assert esc[("escalate", "all")]["recall"] == round(4 / 6, 4)


def test_cli_writes_headers_even_when_nothing_qualifies() -> None:
    out = tempfile.mkdtemp(prefix="clara_calibration_")
    sidecar = os.path.join(out, "jev_probabilities.json")
    with open(sidecar, "w", encoding="utf-8") as fh:
        json.dump({"meta": {"client": "fake"}, "records": [{"id": "x", "gold": {}, "answers": {}}]}, fh)
    assert C.main(["--sidecar", sidecar, "--out", out]) == 0
    for name, cols in (("jev_calibration.csv", C.CAL_COLS), ("jev_reliability.csv", C.REL_COLS),
                       ("jev_coverage_curve.csv", C.COV_COLS), ("jev_escalation.csv", C.ESC_COLS)):
        with open(os.path.join(out, name), encoding="utf-8") as fh:
            rows = list(csv.reader(fh))
        assert rows[0] == cols and len(rows) == 1, name


def test_cli_on_hand_made_records() -> None:
    out = tempfile.mkdtemp(prefix="clara_calibration_")
    sidecar = os.path.join(out, "jev_probabilities.json")
    with open(sidecar, "w", encoding="utf-8") as fh:
        json.dump({"meta": {"client": "fake"}, "records": _records()}, fh)
    assert C.main(["--sidecar", sidecar, "--out", out, "--thresholds", "0,0.5,0.9", "--bins", "5"]) == 0
    with open(os.path.join(out, "jev_coverage_curve.csv"), encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    assert {r["threshold"] for r in rows} == {"0.0", "0.5", "0.9"}
    with open(os.path.join(out, "jev_reliability.csv"), encoding="utf-8") as fh:
        rel = list(csv.DictReader(fh))
    assert len([r for r in rel if r["task"] == "risk" and r["stratum"] == "all"]) == 5


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
