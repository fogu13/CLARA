"""Run the real-data gold-set evaluation and write every result to disk.

Outputs (in evaluation/results/):
  corpus_stats.csv            descriptive stats of the real corpus
  sentiment_*.csv             lexicon sentiment vs star-rating gold (overall/by-language/by-sector/per-class)
  sentiment_confusion.csv     + .png heatmap
  risk_*.csv                  keyword risk vs risk_seed gold (TR + Henkel)
  risk_confusion.csv          + .png heatmap
  f1_breakdown.png            F1 by slice
  summary.json                headline numbers Chapter 5 §5A reads back

If evaluation/results/predictions_llm.json exists (written by predict_llm.py with an
API key), the LLM path is scored alongside the baseline. Otherwise only the baseline runs.
"""
from __future__ import annotations
import csv
import json
import os
import collections

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from load_datasets import load
import baseline as bl
import metrics as M
import ml_baseline as ml

RESULTS = os.path.join(os.path.dirname(__file__), "results")
SENT_LABELS = ["negative", "neutral", "positive"]
RISK_LABELS = ["low", "medium", "high", "critical"]


def _w(name, rows, header):
    os.makedirs(RESULTS, exist_ok=True)
    with open(os.path.join(RESULTS, name), "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=header)
        w.writeheader()
        for r in rows:
            w.writerow(r)


def _heatmap(csv_name, png_name, title):
    path = os.path.join(RESULTS, csv_name)
    with open(path) as fh:
        rows = list(csv.reader(fh))
    labels = rows[0][1:]
    data = [[int(x) for x in r[1:]] for r in rows[1:]]
    fig, ax = plt.subplots(figsize=(4.5, 4))
    im = ax.imshow(data, cmap="Blues")
    ax.set_xticks(range(len(labels))); ax.set_xticklabels(labels, rotation=45, ha="right", fontsize=8)
    ax.set_yticks(range(len(labels))); ax.set_yticklabels(labels, fontsize=8)
    ax.set_xlabel("predicted"); ax.set_ylabel("true (gold)")
    for i in range(len(data)):
        for j in range(len(labels)):
            ax.text(j, i, data[i][j], ha="center", va="center", fontsize=8,
                    color="white" if data[i][j] > (max(max(data)) / 2) else "black")
    ax.set_title(title, fontsize=10)
    fig.colorbar(im, fraction=0.046, pad=0.04)
    fig.tight_layout()
    fig.savefig(os.path.join(RESULTS, png_name), dpi=150)
    plt.close(fig)


def corpus_stats(sigs):
    rows = []
    for key in ["sector", "language", "source"]:
        c = collections.Counter(getattr(s, key) for s in sigs)
        for k, v in sorted(c.items(), key=lambda kv: -kv[1]):
            rows.append({"dimension": key, "value": k, "count": v})
    # gold label coverage
    rows.append({"dimension": "risk_label_present", "value": "yes",
                 "count": sum(1 for s in sigs if s.risk)})
    rows.append({"dimension": "star_rating_present", "value": "yes",
                 "count": sum(1 for s in sigs if s.star_rating is not None)})
    for key in ["theme", "journey_stage", "owner"]:
        rows.append({"dimension": f"{key}_distinct_labels", "value": "(open vocab)",
                     "count": len({getattr(s, key) for s in sigs if getattr(s, key)})})
    _w("corpus_stats.csv", rows, ["dimension", "value", "count"])
    return rows


def eval_sentiment(sigs, summary):
    rated = [s for s in sigs if s.star_rating is not None and s.text]
    y_true = [bl.gold_sentiment_from_stars(s.star_rating) for s in rated]
    y_pred = [bl.predict_sentiment(s.text) for s in rated]
    overall = M.score(y_true, y_true and y_pred)
    _w("sentiment_overall.csv", [overall], list(overall.keys()))
    _w("sentiment_perclass.csv", M.per_class(y_true, y_pred, SENT_LABELS),
       ["label", "precision", "recall", "f1", "support"])
    M.write_confusion(y_true, y_pred, SENT_LABELS, os.path.join(RESULTS, "sentiment_confusion.csv"))
    _heatmap("sentiment_confusion.csv", "sentiment_confusion.png",
             "Sentiment (lexicon) vs star-rating gold")
    # slices
    by_lang, by_sector = [], []
    for lang in sorted({s.language for s in rated}):
        sub = [(bl.gold_sentiment_from_stars(s.star_rating), bl.predict_sentiment(s.text))
               for s in rated if s.language == lang]
        if len(sub) >= 5:
            r = M.score([a for a, _ in sub], [b for _, b in sub]); r["slice"] = lang
            by_lang.append(r)
    for sec in sorted({s.sector for s in rated}):
        sub = [(bl.gold_sentiment_from_stars(s.star_rating), bl.predict_sentiment(s.text))
               for s in rated if s.sector == sec]
        if len(sub) >= 5:
            r = M.score([a for a, _ in sub], [b for _, b in sub]); r["slice"] = sec
            by_sector.append(r)
    cols = ["slice"] + [k for k in overall.keys()]
    _w("sentiment_by_language.csv", by_lang, cols)
    _w("sentiment_by_sector.csv", by_sector, cols)
    summary["sentiment_baseline"] = overall
    summary["sentiment_by_language"] = {r["slice"]: r["f1_macro"] for r in by_lang}
    summary["sentiment_by_sector"] = {r["slice"]: r["f1_macro"] for r in by_sector}
    return by_sector


def eval_risk(sigs, summary):
    have = [s for s in sigs if s.risk in RISK_LABELS and s.text]
    y_true = [s.risk for s in have]
    y_pred = [bl.predict_risk(s.text) for s in have]
    overall = M.score(y_true, y_pred)
    _w("risk_overall.csv", [overall], list(overall.keys()))
    _w("risk_perclass.csv", M.per_class(y_true, y_pred, RISK_LABELS),
       ["label", "precision", "recall", "f1", "support"])
    M.write_confusion(y_true, y_pred, RISK_LABELS, os.path.join(RESULTS, "risk_confusion.csv"))
    _heatmap("risk_confusion.csv", "risk_confusion.png", "Risk (keyword) vs risk_seed gold")
    # binary escalation view (high+critical = escalate)
    esc = lambda x: "escalate" if x in ("high", "critical") else "routine"
    bt = [esc(v) for v in y_true]; bp = [esc(v) for v in y_pred]
    binary = M.score(bt, bp)
    _w("risk_binary_escalation.csv", [binary], list(binary.keys()))
    summary["risk_baseline"] = overall
    summary["risk_binary_escalation"] = binary
    summary["risk_n_datasets"] = sorted({s.dataset for s in have})


def f1_breakdown(by_sector):
    if not by_sector:
        return
    secs = [r["slice"] for r in by_sector]
    f1s = [r["f1_macro"] for r in by_sector]
    fig, ax = plt.subplots(figsize=(5, 3))
    ax.bar(secs, f1s, color="#3b6ea5")
    ax.set_ylim(0, 1); ax.set_ylabel("sentiment F1 (macro)")
    ax.set_title("Baseline sentiment F1 by sector")
    for i, v in enumerate(f1s):
        ax.text(i, v + 0.02, f"{v:.2f}", ha="center", fontsize=9)
    fig.tight_layout()
    fig.savefig(os.path.join(RESULTS, "f1_breakdown.png"), dpi=150)
    plt.close(fig)


def eval_ml(sigs, summary):
    # sentiment vs star gold
    rated = [s for s in sigs if s.star_rating is not None and s.text]
    texts = [s.text for s in rated]
    gold = [bl.gold_sentiment_from_stars(s.star_rating) for s in rated]
    y_true, y_pred, k = ml.cv_predict(texts, gold)
    r = M.score(y_true, y_pred); r["cv_folds"] = k
    _w("sentiment_ml.csv", [r], list(r.keys()))
    summary["sentiment_ml_tfidf_lr"] = r
    # risk vs risk_seed gold (TR + Henkel)
    have = [s for s in sigs if s.risk in RISK_LABELS and s.text]
    yt, yp, k2 = ml.cv_predict([s.text for s in have], [s.risk for s in have])
    r2 = M.score(yt, yp); r2["cv_folds"] = k2
    _w("risk_ml.csv", [r2], list(r2.keys()))
    summary["risk_ml_tfidf_lr"] = r2


def score_llm(sigs, summary):
    cache = os.path.join(RESULTS, "predictions_llm.json")
    if not os.path.exists(cache):
        summary["llm_path"] = "not run (no predictions_llm.json; set AI_API_KEY and run predict_llm.py)"
        return
    preds = {p["id"]: p for p in json.load(open(cache))}
    rated = [s for s in sigs if s.star_rating is not None and s.id in preds and s.text]
    y_true = [bl.gold_sentiment_from_stars(s.star_rating) for s in rated]
    y_pred = [preds[s.id].get("sentiment", "neutral") for s in rated]
    summary["sentiment_llm"] = M.score(y_true, y_pred)
    have = [s for s in sigs if s.risk in RISK_LABELS and s.id in preds and s.text]
    if have:
        summary["risk_llm"] = M.score([s.risk for s in have],
                                      [preds[s.id].get("risk", "low") for s in have])
    summary["llm_path"] = f"scored {len(rated)} sentiment / {len(have)} risk predictions"


def main():
    sigs = load()
    summary = {"corpus_n": len(sigs),
               "datasets": sorted({s.dataset for s in sigs})}
    corpus_stats(sigs)
    by_sector = eval_sentiment(sigs, summary)
    eval_risk(sigs, summary)
    eval_ml(sigs, summary)
    f1_breakdown(by_sector)
    score_llm(sigs, summary)
    with open(os.path.join(RESULTS, "summary.json"), "w") as fh:
        json.dump(summary, fh, indent=2)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
