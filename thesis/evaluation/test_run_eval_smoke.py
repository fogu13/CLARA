"""Synthetic smoke test of the run_eval.py wiring (no corpus, no model, no pytest).
Run: python3 thesis/evaluation/test_run_eval_smoke.py   (exits non-zero on failure)

The real corpus (THESIS_DATA_DIR) is not needed: twelve fake Signal records and
a hand-written predictions_llm.json go into a temp results folder, run_eval's
RESULTS constant is pointed there, and score_llm / significance / equity_slices
are called directly. It proves that the prediction_validation counts reach
summary.json, that the coverage-conditioned and end-to-end views differ by the
non-answers, that the paired test uses valid ids only and reports n_dropped,
and that the confusion table sums to n_valid.
"""
import csv
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from load_datasets import Signal  # noqa: E402
import run_eval as RE  # noqa: E402


def _signal(i: int, language: str, stars, risk: str, text: str) -> Signal:
    return Signal(id=f"S-{i}", dataset="fake", sector="fintech" if language == "en" else "b2b",
                  source="store", language=language, star_rating=stars, text=text,
                  theme="t", journey_stage="j", owner="o", action="a", risk=risk)


# 12 signals: 10 rated (sentiment gold), all 12 risk-labelled; per language 5
# gold-escalate items so the equity table (MIN_SLICE = 5) has both strata.
SIGS = [
    _signal(1, "en", 1, "high", "Account blocked, terrible, lost money"),
    _signal(2, "en", 5, "critical", "This app is great and reliable"),
    _signal(3, "en", 3, "high", "It is okay, nothing special"),
    _signal(4, "en", 1, "high", "Support never answers, awful"),
    _signal(5, "en", 5, "critical", "Love it, fast and easy"),
    _signal(6, "en", None, "low", "Just a comment without a rating"),
    _signal(7, "de", 1, "high", "Konto gesperrt, schrecklich"),
    _signal(8, "de", 5, "critical", "Die App ist schnell und zuverlässig"),
    _signal(9, "de", 3, "high", "Geht so, nichts besonderes"),
    _signal(10, "de", 1, "high", "Kein Support, furchtbar"),
    _signal(11, "de", 5, "critical", "Sehr gut, gerne wieder"),
    _signal(12, "de", None, "medium", "Nur ein Kommentar ohne Bewertung"),
]
GOLD_S = {s.id: RE.bl.gold_sentiment_from_stars(s.star_rating) for s in SIGS if s.star_rating is not None}
GOLD_R = {s.id: s.risk for s in SIGS}

# Prediction file with every defect class the validator has to catch.
PREDICTIONS = [
    {"id": "S-1", "sentiment": "negative", "risk": "high"},            # valid, both right
    {"id": "S-2", "sentiment": "positive", "risk": "critical"},        # valid, both right
    {"id": "S-3", "sentiment": "positive", "risk": "high"},            # sentiment wrong (gold neutral)
    {"id": "S-4", "sentiment": "negative", "risk": "low"},             # risk wrong
    {"id": "S-5"},                                                     # id-only: invalid on both tasks
    {"id": "S-6", "sentiment": "neutral", "risk": "low"},              # unrated -> not expected for sentiment
    {"id": "S-7", "sentiment": "mixed", "risk": "high"},               # invalid sentiment label
    {"id": "S-8", "sentiment": "positive", "risk": "critical"},        # valid
    {"id": "S-8", "sentiment": "negative", "risk": "low"},             # duplicate: must be ignored
    {"id": "S-9", "sentiment": "neutral", "risk": "High"},             # invalid risk label (case)
    {"id": "S-10", "sentiment": "negative", "risk": "high"},           # valid
    # S-11 missing entirely; S-12 missing entirely
    {"id": "GHOST-1", "sentiment": "positive", "risk": "low"},         # unknown id
]


def _confusion_total(path: str) -> int:
    with open(path) as fh:
        rows = list(csv.reader(fh))
    return sum(int(x) for r in rows[1:] for x in r[1:])


def run() -> None:
    tmp = tempfile.mkdtemp(prefix="clara_run_eval_smoke_")
    RE.RESULTS = tmp
    with open(os.path.join(tmp, "predictions_llm.json"), "w") as fh:
        json.dump(PREDICTIONS, fh)

    summary: dict = {}
    maps = RE.score_llm(SIGS, summary, key="llm", cache="predictions_llm.json", label="smoke")
    assert maps is not None

    # --- sentiment: 10 expected; S-5 invalid, S-7 invalid, S-11 missing; S-8 dup; S-6 & GHOST unknown
    pv = summary["prediction_validation"]["llm"]["sentiment"]
    assert pv["n_expected"] == 10, pv
    assert pv["n_returned"] == len(PREDICTIONS)
    assert pv["n_valid"] == 7 and pv["n_invalid"] == 2 and pv["n_missing"] == 1, pv
    assert pv["n_duplicate_ids"] == 1 and pv["duplicate_ids"] == ["S-8"], pv
    assert pv["n_unknown_ids"] == 2 and set(pv["unknown_ids"]) == {"S-6", "GHOST-1"}, pv
    assert pv["missing_ids"] == ["S-11"], pv
    assert [e[0] for e in pv["invalid_examples"]] == ["S-5", "S-7"], pv
    assert maps["sentiment"]["S-8"] == "positive"  # first occurrence won
    assert "S-5" not in maps["sentiment"] and "S-7" not in maps["sentiment"]

    cond = summary["sentiment_llm"]
    e2e = summary["sentiment_llm_end_to_end"]
    assert cond["n"] == 7, cond
    # valid rows: S-1 ok, S-2 ok, S-3 wrong, S-4 ok, S-8 ok, S-9 ok, S-10 ok -> 6/7
    assert abs(cond["accuracy"] - 6 / 7) < 1e-3, cond
    assert e2e["n_expected"] == 10 and e2e["n_correct"] == 6 and e2e["accuracy"] == 0.6, e2e
    assert e2e["accuracy"] < cond["accuracy"]
    assert e2e["coverage"] == 0.7 and e2e["n_missing"] == 1 and e2e["n_invalid"] == 2, e2e
    assert "missing" in e2e["rule"]
    # confusion table over valid rows only, sums to n_valid
    assert _confusion_total(os.path.join(tmp, "sentiment_llm_confusion.csv")) == 7

    # --- risk: 12 expected; S-5 invalid, S-9 invalid ("High"), S-11 + S-12 missing
    pr = summary["prediction_validation"]["llm"]["risk"]
    assert pr["n_expected"] == 12 and pr["n_valid"] == 8 and pr["n_invalid"] == 2 and pr["n_missing"] == 2, pr
    assert "S-9" not in maps["risk"] and maps["risk"]["S-6"] == "low"
    rc, re2e = summary["risk_llm"], summary["risk_llm_end_to_end"]
    # valid: S-1 ok, S-2 ok, S-3 ok, S-4 wrong, S-6 ok, S-7 ok, S-8 ok, S-10 ok -> 7/8
    assert rc["n"] == 8 and abs(rc["accuracy"] - 7 / 8) < 1e-3, rc
    assert re2e["n_expected"] == 12 and re2e["n_correct"] == 7, re2e
    assert re2e["accuracy"] < rc["accuracy"]
    assert _confusion_total(os.path.join(tmp, "risk_llm_confusion.csv")) == 8
    assert summary["llm_path"].startswith("scored 7 valid of 10 sentiment / 8 valid of 12 risk")

    # --- paired test: intersection of VALID ids, n_dropped reported
    RE.significance(SIGS, summary, None, {"llm": maps})
    pair = summary["mcnemar_paired"]["sentiment"]["floor_vs_llm"]
    assert pair["n_pairs"] == 7 and pair["n_dropped"] == 3, pair
    rpair = summary["mcnemar_paired"]["risk"]["floor_vs_llm"]
    assert rpair["n_pairs"] == 8 and rpair["n_dropped"] == 4, rpair
    with open(os.path.join(tmp, "mcnemar_paired.csv")) as fh:
        rows = list(csv.DictReader(fh))
    assert {r["pair"] for r in rows} == {"floor_vs_llm"} and all("n_dropped" in r for r in rows)

    # --- equity: the LLM recall row counts only gold-escalate items with a VALID risk prediction
    RE.equity_slices(SIGS, summary, {"llm": maps}, None)
    eq = summary["escalation_recall_by_language"]
    assert set(eq) == {"de", "en"}, eq
    # en gold-escalate: S-1..S-5 (5); valid llm risk among them: S-1,2,3,4 (S-5 invalid) -> 4
    assert eq["en"]["n_gold_escalate"] == 5 and eq["en"]["n_gold_escalate_llm"] == 4, eq["en"]
    # de gold-escalate: S-7..S-11 (5); valid: S-7, S-8, S-10 (S-9 invalid, S-11 missing) -> 3
    assert eq["de"]["n_gold_escalate"] == 5 and eq["de"]["n_gold_escalate_llm"] == 3, eq["de"]
    assert eq["en"]["recall_llm"] == 0.75  # S-4 predicted low
    assert eq["de"]["recall_llm"] == 1.0

    # --- an absent file is reported, never scored
    assert RE.score_llm(SIGS, summary, key="llm_production",
                        cache="predictions_llm_production.json", label="x") is None
    assert summary["llm_production_path"].startswith("not run")

    # summary.json round-trips (the counts are plain JSON)
    json.dumps(summary)


if __name__ == "__main__":
    run()
    print("OK: run_eval wiring smoke test passed (synthetic data, no corpus)")
