"""Synthetic smoke test of the run_eval.py wiring (no corpus, no model, no pytest).
Run: python3 thesis/evaluation/test_run_eval_smoke.py   (exits non-zero on failure)

The real corpus (THESIS_DATA_DIR) is not needed: twelve fake Signal records and
a hand-written predictions_llm.json go into a temp results folder, run_eval's
RESULTS constant is pointed there, and score_llm / significance / equity_slices
/ score_taxonomy are called directly. It proves that the prediction_validation
counts reach summary.json (unknown ids split from outside-task ids, rows with
no usable id counted as invalid ids), that the coverage-conditioned and
end-to-end views differ by the non-answers, that the paired test uses valid ids
only and reports n_dropped, that the confusion table sums to n_valid, that the
equity table carries the end-to-end recall, that the taxonomy fields are
validated, and that a production file with no valid non-mixed row does not
crash the scorer.
"""
import csv
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from load_datasets import Signal  # noqa: E402
import run_eval as RE  # noqa: E402
import compare_runs as CR  # noqa: E402


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
    {"id": "S-6", "sentiment": "neutral", "risk": "low"},              # unrated -> outside the sentiment task
    {"id": "S-7", "sentiment": "mixed", "risk": "high"},               # invalid sentiment label
    {"id": "S-8", "sentiment": "positive", "risk": "critical"},        # valid
    {"id": "S-8", "sentiment": "negative", "risk": "low"},             # duplicate: must be ignored
    {"id": "S-9", "sentiment": "neutral", "risk": "High"},             # invalid risk label (case)
    {"id": "S-10", "sentiment": "negative", "risk": "high"},           # valid
    # S-11 missing entirely; S-12 missing entirely
    {"id": "GHOST-1", "sentiment": "positive", "risk": "low"},         # unknown id (not in corpus)
    "not a row at all",                                                # non-mapping row (C12)
    {"sentiment": "positive", "risk": "low"},                          # no id (C9)
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

    # --- sentiment: 10 expected; S-5 invalid, S-7 invalid, S-11 missing; S-8 dup;
    #     GHOST unknown (not in corpus), S-6 outside the task (corpus item, unrated);
    #     the string row and the id-less row are invalid ids.
    pv = summary["prediction_validation"]["llm"]["sentiment"]
    assert pv["n_expected"] == 10, pv
    assert pv["n_returned"] == len(PREDICTIONS)
    assert pv["n_valid"] == 7 and pv["n_invalid"] == 2 and pv["n_missing"] == 1, pv
    assert pv["n_duplicate_ids"] == 1 and pv["duplicate_ids"] == ["S-8"], pv
    assert pv["n_unknown_ids"] == 1 and pv["unknown_ids"] == ["GHOST-1"], pv           # C10
    assert pv["n_outside_task"] == 1 and pv["outside_task_ids"] == ["S-6"], pv          # C10
    assert pv["n_invalid_ids"] == 2, pv                                                 # C9 / C12
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
    assert pr["n_unknown_ids"] == 1 and pr["n_outside_task"] == 0 and pr["n_invalid_ids"] == 2, pr
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
    # C13: end-to-end companion — every gold-escalate item in the denominator,
    # a missing / invalid prediction is a miss: en 3/5, de 3/5; the floor has
    # no non-answers, so its two views coincide.
    assert eq["en"]["recall_llm_end_to_end"] == 0.6, eq["en"]
    assert eq["de"]["recall_llm_end_to_end"] == 0.6, eq["de"]
    assert eq["en"]["recall_floor_end_to_end"] == eq["en"]["recall_floor"]
    with open(os.path.join(tmp, "escalation_recall_by_language.csv")) as fh:
        eq_rows = list(csv.DictReader(fh))
    assert {r["language"]: float(r["recall_llm_end_to_end"]) for r in eq_rows} == {"de": 0.6, "en": 0.6}

    # --- an absent file is reported, never scored
    assert RE.score_llm(SIGS, summary, key="llm_production",
                        cache="predictions_llm_production.json", label="x") is None
    assert summary["llm_production_path"].startswith("not run")

    # --- C5: taxonomy fields go through the validator (open vocabulary)
    taxonomy = [
        {"id": "S-1", "journey_stage": "j", "owner": "o"},        # both right
        {"id": "S-2", "journey_stage": "k", "owner": "o"},        # stage wrong
        {"id": "S-3", "journey_stage": "", "owner": " o "},       # stage invalid (empty); owner right after strip
        {"id": "S-4", "journey_stage": None, "owner": None},      # both invalid
        {"id": "S-5", "owner": "p"},                              # stage missing from row -> invalid; owner wrong
        {"id": "S-6", "journey_stage": "j", "owner": "o"},
        {"id": "S-6", "journey_stage": "x", "owner": "x"},        # duplicate ignored
        {"id": "GHOST-2", "journey_stage": "j", "owner": "o"},    # unknown id
        "garbage",                                                # non-mapping row
        # S-7..S-12 missing entirely
    ]
    with open(os.path.join(tmp, "predictions_llm_taxonomy.json"), "w") as fh:
        json.dump(taxonomy, fh)
    RE.score_taxonomy(SIGS, summary)
    tv = summary["prediction_validation"]["llm_taxonomy"]
    js, ow = tv["journey_stage"], tv["owner"]
    assert js["n_expected"] == 12 and js["n_valid"] == 3 and js["n_invalid"] == 3 and js["n_missing"] == 6, js
    assert js["n_unknown_ids"] == 1 and js["n_invalid_ids"] == 1 and js["n_duplicate_ids"] == 1, js
    assert ow["n_expected"] == 12 and ow["n_valid"] == 5 and ow["n_invalid"] == 1 and ow["n_missing"] == 6, ow
    cs = summary["journey_stage_llm_closed_set"]
    assert cs["n"] == 3 and abs(cs["accuracy"] - 2 / 3) < 1e-3, cs   # coverage-conditioned, keys kept
    assert cs["in_vocabulary_rate"] == round(2 / 3, 4) and cs["majority_class"] == "j"
    js_e2e = summary["journey_stage_llm_closed_set_end_to_end"]
    assert js_e2e["n_expected"] == 12 and js_e2e["n_correct"] == 2, js_e2e
    assert abs(js_e2e["accuracy"] - 2 / 12) < 1e-3 and js_e2e["accuracy"] < cs["accuracy"]
    ow_e2e = summary["owner_llm_closed_set_end_to_end"]
    # owner valid: S-1 o, S-2 o, S-3 o (stripped), S-5 p (wrong), S-6 o -> 4 correct of 12
    assert ow_e2e["n_correct"] == 4 and abs(ow_e2e["accuracy"] - 4 / 12) < 1e-3, ow_e2e
    assert summary["owner_llm_closed_set"]["n"] == 5
    assert summary["taxonomy_path"].startswith("scored")

    # --- C8: a production file whose every valid sentiment row is "mixed"
    #     (mapped to neutral) must not crash the mixed-sensitivity block, and a
    #     file with no valid sentiment row at all must not either.
    all_mixed = [{"id": s.id, "sentiment": "neutral", "sentiment_raw": "mixed", "risk": "low"}
                 for s in SIGS if s.star_rating is not None]
    with open(os.path.join(tmp, "predictions_llm_production.json"), "w") as fh:
        json.dump(all_mixed, fh)
    prod_summary: dict = {}
    assert RE.score_llm(SIGS, prod_summary, key="llm_production",
                        cache="predictions_llm_production.json", label="all mixed") is not None
    excl = prod_summary["sentiment_llm_production_excluding_mixed"]
    assert excl["n_valid"] == 0 and excl["n_dropped"] == 10 and "accuracy" not in excl, excl
    assert prod_summary["sentiment_llm_production"]["n"] == 10  # the primary (mixed -> neutral) view
    none_valid = [{"id": s.id, "sentiment": "Mixed", "sentiment_raw": "mixed", "risk": "low"}
                  for s in SIGS if s.star_rating is not None]
    with open(os.path.join(tmp, "predictions_llm_production.json"), "w") as fh:
        json.dump(none_valid, fh)
    prod_summary = {}
    RE.score_llm(SIGS, prod_summary, key="llm_production",
                 cache="predictions_llm_production.json", label="none valid")
    pvp = prod_summary["prediction_validation"]["llm_production"]["sentiment"]
    assert pvp["n_valid"] == 0 and pvp["n_invalid"] == 10, pvp
    assert "sentiment_llm_production" not in prod_summary  # no coverage-conditioned block
    assert prod_summary["sentiment_llm_production_end_to_end"]["accuracy"] == 0.0
    assert prod_summary["sentiment_llm_production_excluding_mixed"]["n_valid"] == 0
    with open(os.path.join(tmp, "summary.json"), "w") as fh:  # summary.json still written
        json.dump(prod_summary, fh)

    # --- C11: nothing expected -> end-to-end accuracy None, no interval, never 0.0
    unrated = [s for s in SIGS if s.star_rating is None]
    empty_summary: dict = {}
    RE.score_llm(unrated, empty_summary, key="llm", cache="predictions_llm.json", label="no gold")
    e0 = empty_summary["sentiment_llm_end_to_end"]
    assert e0["n_expected"] == 0 and e0["accuracy"] is None, e0
    assert e0["accuracy_ci_low"] is None and e0["accuracy_ci_high"] is None and e0["coverage"] is None

    # --- C10 / C12 in compare_runs: same split of unknown vs outside-task, non-mapping rows tolerated
    runs = {"floor": CR.floor_run(SIGS), "llm": CR.load_run(os.path.join(tmp, "predictions_llm.json"))}
    acc_rows, pair_rows, agree_rows = CR.compare(SIGS, runs)
    llm_sent = next(r for r in acc_rows if r["run"] == "llm" and r["task"] == "sentiment")
    assert llm_sent["n_unknown_ids"] == 1 and llm_sent["n_outside_task"] == 1 and llm_sent["n_invalid_ids"] == 2
    assert llm_sent["accuracy_end_to_end"] == 0.6 and llm_sent["n_valid"] == 7
    assert any(r["pair"] == "floor_vs_llm" and r["n_pairs"] == 7 for r in pair_rows)

    # summary.json round-trips (the counts are plain JSON)
    json.dumps(summary)


if __name__ == "__main__":
    run()
    print("OK: run_eval wiring smoke test passed (synthetic data, no corpus)")
