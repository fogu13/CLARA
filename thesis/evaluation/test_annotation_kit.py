"""Plain-assert checks for annotation_kit.py on synthetic signals in a temp dir (no corpus, no model).
Run: python3 thesis/evaluation/test_annotation_kit.py   (exits non-zero on failure)
"""
from __future__ import annotations

import csv
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import annotation_kit as AK  # noqa: E402
from test_run_eval_smoke import SIGS  # noqa: E402  (twelve synthetic signals)

AK.load = lambda: list(SIGS)  # the corpus loader, replaced for the test


def _rows(path: str) -> list[dict]:
    with open(path, encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def _write_rows(path: str, rows: list[dict]) -> None:
    with open(path, "w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def test_cohen_kappa_by_hand() -> None:
    # po = 0.75, pe = 0.5*0.75 + 0.5*0.25 = 0.5 -> kappa = 0.5
    assert abs(AK.cohen_kappa(["x", "x", "y", "y"], ["x", "x", "y", "x"], ["x", "y"]) - 0.5) < 1e-9
    assert AK.cohen_kappa(["a", "b"], ["a", "b"], ["a", "b"]) == 1.0
    assert AK.cohen_kappa([], [], ["a"]) is None
    # Linear weights: one two-level miss on a four-level scale is penalised more than a one-level miss.
    near = AK.cohen_kappa(["low", "high", "critical", "medium"], ["low", "medium", "critical", "medium"], AK.ORDINAL, weighted=True)
    far = AK.cohen_kappa(["low", "high", "critical", "medium"], ["low", "low", "critical", "medium"], AK.ORDINAL, weighted=True)
    assert near > far


def test_draw_withholds_labels_and_writes_the_kit() -> None:
    out = tempfile.mkdtemp(prefix="clara_annotation_")
    manifest = AK.draw(["A", "B"], out_dir=out)
    assert manifest["n"] == len(SIGS) and manifest["raters"] == ["A", "B"]
    rows = _rows(os.path.join(out, "rater_A.csv"))
    assert [r["public_signal_id"] for r in rows] == sorted(s.id for s in SIGS)
    assert all(r[f] == "" for r in rows for f in AK.FIELDS)
    assert set(rows[0]) == {"public_signal_id", "sector", "source", "text", *AK.FIELDS}
    header = open(os.path.join(out, "rater_A.csv"), encoding="utf-8").readline()
    assert "seed" not in header and "star" not in header  # no seed-label or rating column reaches a rater
    assert manifest["labels_in_files"].startswith("none")
    inv = json.load(open(os.path.join(out, "inventories.json"), encoding="utf-8"))
    assert inv["risk"] == AK.ORDINAL and set(inv["journey_stage"]) == {AK._norm(s.journey_stage) for s in SIGS if AK._norm(s.journey_stage)}
    instructions = open(os.path.join(out, "INSTRUCTIONS.md"), encoding="utf-8").read()
    assert "urgency" in instructions and "no AI assistant" in instructions
    assert os.path.exists(os.path.join(out, "PROVENANCE_template.md"))
    subset = AK.draw(["C"], n=5, seed=1, out_dir=os.path.join(out, "sub"))
    assert subset["n"] == 5 and len(_rows(os.path.join(out, "sub", "rater_C.csv"))) == 5


def _fill(rows: list[dict], *, flip: int = 0) -> list[dict]:
    by_id = {s.id: s for s in SIGS}
    filled = []
    for i, r in enumerate(rows):
        s = by_id[r["public_signal_id"]]
        stars = s.star_rating or 3
        row = dict(r)
        row["sentiment"] = "negative" if stars <= 2 else "neutral" if stars == 3 else "positive"
        row["risk"] = s.risk or "low"
        row["urgency"] = s.risk or "low"
        row["journey_stage"] = AK._norm(s.journey_stage)
        row["owner"] = AK._norm(s.owner)
        if i < flip:  # the second rater disagrees on the first `flip` rows
            row["risk"] = "critical" if row["risk"] != "critical" else "low"
            row["sentiment"] = "neutral" if row["sentiment"] != "neutral" else "positive"
        filled.append(row)
    return filled


def test_agreement_adjudication_and_rescore_round_trip() -> None:
    out = tempfile.mkdtemp(prefix="clara_annotation_")
    AK.draw(["A", "B"], out_dir=out)
    a_path, b_path = os.path.join(out, "rater_A.csv"), os.path.join(out, "rater_B.csv")
    _write_rows(a_path, _fill(_rows(a_path)))
    _write_rows(b_path, _fill(_rows(b_path), flip=3))

    report = AK.agreement(a_path, b_path, out_dir=out)
    assert report["n_common_ids"] == len(SIGS)
    assert report["fields"]["journey_stage"]["kappa"] == 1.0 and report["fields"]["owner"]["exact_agreement"] == 1.0
    assert report["fields"]["risk"]["n"] == len(SIGS) and report["fields"]["risk"]["kappa"] < 1.0
    assert "kappa_linear_weighted" in report["fields"]["risk"] and "kappa_linear_weighted" not in report["fields"]["sentiment"]
    assert report["n_disagreements"] == 6  # three rows x (risk, sentiment)
    disagreements = _rows(os.path.join(out, "disagreements.csv"))
    assert {d["field"] for d in disagreements} == {"risk", "sentiment"}

    # Unfilled adjudication is refused; a filled one builds the gold.
    adjudication = os.path.join(out, "disagreements.csv")
    try:
        AK.adjudicate(a_path, b_path, adjudication, out_path=os.path.join(out, "gold_human.csv"))
    except SystemExit as exc:
        assert "no adjudication is recorded" in str(exc)
    else:
        raise AssertionError("an unfilled adjudication must be refused")
    for d in disagreements:
        d["adjudicated"] = d["rater_a"]
    _write_rows(adjudication, disagreements)
    meta = AK.adjudicate(a_path, b_path, adjudication, out_path=os.path.join(out, "gold_human.csv"))
    assert meta["n"] == len(SIGS) and meta["counts"]["risk"]["adjudicated"] == 3 and meta["counts"]["owner"]["agreed"] == len(SIGS)
    gold = _rows(os.path.join(out, "gold_human.csv"))
    assert all(g["risk"] and g["sentiment"] and g["urgency"] for g in gold)

    # Predictions in the shapes the harness commits: dict-of-tasks (ml), list-of-items (llm), production keys, taxonomy.
    ids = [g["public_signal_id"] for g in gold]
    ml = {"sentiment": {i: "negative" for i in ids}, "risk": {i: "low" for i in ids}}
    llm = [{"id": i, "sentiment": g["sentiment"], "risk": g["risk"], "journey_stage": g["journey_stage"], "owner": "nobody"}
           for i, g in zip(ids, gold)]
    production = [{"id": i, "sentiment": "bogus" if k == 0 else g["sentiment"], "risk": g["risk"], "urgency_raw": g["urgency"]}
                  for k, (i, g) in enumerate(zip(ids, gold))]
    taxonomy = [{"id": i, "journey_stage": g["journey_stage"], "owner": g["owner"]} for i, g in zip(ids[:-1], gold)]
    paths = {}
    for name, data in (("ml", ml), ("llm_generic", llm), ("llm_production_glm", production), ("llm_taxonomy", taxonomy)):
        paths[name] = os.path.join(out, f"{name}.json")
        with open(paths[name], "w", encoding="utf-8") as fh:
            json.dump(data, fh)
    paths["llm_production_mistral"] = os.path.join(out, "missing.json")  # absent source: skipped, not an error
    summary = AK.rescore(os.path.join(out, "gold_human.csv"), out_dir=os.path.join(out, "scored"), predictions=paths)
    assert set(summary["predictions_scored"]) == {"ml", "llm_generic", "llm_production_glm", "llm_taxonomy"}
    acc = {(r["field"], r["predictor"]): r for r in _rows(os.path.join(out, "scored", "human_gold_accuracy.csv"))}
    assert acc[("sentiment", "llm_generic")]["accuracy"] == "1.0" and acc[("risk", "llm_generic")]["f1_macro"] == "1.0"
    assert acc[("owner", "llm_generic")]["accuracy"] == "0.0" and acc[("owner", "llm_taxonomy")]["n_absent"] == "1"
    prod = acc[("sentiment", "llm_production_glm")]
    assert prod["n_invalid"] == "1" and prod["accuracy"] == "1.0" and float(prod["accuracy_end_to_end"]) < 1.0
    assert acc[("urgency", "llm_production_glm")]["accuracy"] == "1.0"
    assert ("urgency", "ml") not in acc  # the learned model has no urgency output
    pairs = {(r["field"], r["pair"]): r for r in _rows(os.path.join(out, "scored", "human_gold_pairs.csv"))}
    ml_vs_llm = pairs[("risk", "ml_vs_llm_generic")]
    assert ml_vs_llm["n_pairs"] == str(len(SIGS)) and ml_vs_llm["c_second_only_correct"] != "0"
    assert float(ml_vs_llm["p_exact_two_sided"]) <= 1.0
    assert all(r["note"] == "" for r in acc.values())  # without --retrain-ml no row carries a note


def _agreed_gold(out: str) -> str:
    """Two identical ratings -> no disagreements -> a gold with the seed-derived labels."""
    AK.draw(["A", "B"], out_dir=out)
    a_path, b_path = os.path.join(out, "rater_A.csv"), os.path.join(out, "rater_B.csv")
    _write_rows(a_path, _fill(_rows(a_path)))
    _write_rows(b_path, _fill(_rows(b_path)))
    AK.agreement(a_path, b_path, out_dir=out)
    gold = os.path.join(out, "gold_human.csv")
    AK.adjudicate(a_path, b_path, os.path.join(out, "disagreements.csv"), out_path=gold)
    return gold


def test_retrain_ml_on_the_human_gold_is_lazy_and_out_of_fold() -> None:
    # ml_baseline (scikit-learn) is imported inside the retrain branch only, never at module level.
    assert not hasattr(AK, "ml_baseline")
    source = open(AK.__file__, encoding="utf-8").read()
    assert "\nimport ml_baseline" not in source and "\n    import ml_baseline" in source

    out = tempfile.mkdtemp(prefix="clara_annotation_")
    gold = _agreed_gold(out)
    ids = [g["public_signal_id"] for g in _rows(gold)]
    ml_path = os.path.join(out, "ml.json")
    with open(ml_path, "w", encoding="utf-8") as fh:
        json.dump({"sentiment": {i: "negative" for i in ids}, "risk": {i: "high" for i in ids}}, fh)
    missing = os.path.join(out, "missing.json")
    scored = os.path.join(out, "scored")
    argv = ["rescore", gold, "--out", scored, "--predictions", f"ml={ml_path}", "--retrain-ml", "--min-per-class", "2"]
    for label in ("llm_generic", "llm_production_glm", "llm_production_mistral", "llm_taxonomy"):
        argv += ["--predictions", f"{label}={missing}"]
    assert AK.main(argv) == 0

    acc = {(r["field"], r["predictor"]): r for r in _rows(os.path.join(scored, "human_gold_accuracy.csv"))}
    assert {k for k in acc if k[1] == "ml_retrained"} == {("sentiment", "ml_retrained"), ("risk", "ml_retrained")}
    sentiment = acc[("sentiment", "ml_retrained")]
    assert (sentiment["n_gold"], sentiment["n_valid"], sentiment["n_invalid"], sentiment["n_absent"]) == ("12", "12", "0", "0")
    risk = acc[("risk", "ml_retrained")]
    # low and medium have one item each: below --min-per-class 2 they get no out-of-fold prediction.
    assert (risk["n_gold"], risk["n_valid"], risk["n_absent"]) == ("12", "10", "2")
    for row in (sentiment, risk):
        assert "human gold" in row["note"] and "folds" in row["note"] and "seed labels" in row["note"]
        assert 0.0 <= float(row["accuracy"]) <= 1.0 and 0.0 <= float(row["accuracy_end_to_end"]) <= 1.0
        assert float(row["accuracy_ci_low"]) <= float(row["accuracy"]) <= float(row["accuracy_ci_high"])
    assert acc[("sentiment", "ml")]["note"] == ""
    pairs = {(r["field"], r["pair"]): r for r in _rows(os.path.join(scored, "human_gold_pairs.csv"))}
    assert pairs[("risk", "ml_retrained_vs_ml")]["n_pairs"] == "10"
    assert pairs[("sentiment", "ml_retrained_vs_ml")]["n_pairs"] == "12"
    summary = json.load(open(os.path.join(scored, "human_gold_summary.json"), encoding="utf-8"))
    assert summary["ml_retrained"]["min_per_class"] == 2 and summary["ml_retrained"]["fields"] == ["sentiment", "risk"]
    assert summary["ml_retrained"]["per_field"]["risk"]["folds"] == 4  # capped by the smallest kept class (critical, 4)
    assert "seed labels" in summary["ml_retrained"]["evidence_type"]

    # At the default minimum (5 per class) this twelve-item gold has no two classes large enough: refused, not faked.
    small = AK.rescore(gold, out_dir=os.path.join(out, "scored_default"), retrain_ml=True,
                       predictions={"ml": ml_path, **{label: missing for label in
                                                      ("llm_generic", "llm_production_glm", "llm_production_mistral", "llm_taxonomy")}})
    assert small["ml_retrained"]["min_per_class"] == 5
    acc = {(r["field"], r["predictor"]): r for r in _rows(os.path.join(out, "scored_default", "human_gold_accuracy.csv"))}
    assert acc[("sentiment", "ml_retrained")]["n_valid"] == "0" and acc[("sentiment", "ml_retrained")]["note"].startswith("not retrained")
    assert acc[("sentiment", "ml_retrained")]["accuracy"] == ""


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
