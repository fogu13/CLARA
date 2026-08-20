"""Run the real-data gold-set evaluation and write every result to disk.

Outputs (in evaluation/results/):
  corpus_stats.csv            descriptive stats of the real corpus
  sentiment_*.csv             lexicon sentiment vs star-rating gold (overall/by-language/by-sector/per-class)
  sentiment_confusion.csv     + .png heatmap
  risk_*.csv                  keyword risk vs risk_seed gold (TR + Henkel)
  risk_confusion.csv          + .png heatmap
  f1_breakdown.png            F1 by slice
  predictions_ml.json         per-item TF-IDF+LR out-of-fold predictions (paired-test input)
  escalation_recall_by_language.csv   equal-opportunity table, all three predictors
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
    # Both metrics, never macro-F1 alone: on small slices with sparse minority
    # classes macro-F1 swings wildly and can invert the accuracy story.
    _pair = lambda r: {"n": r["n"], "accuracy": r["accuracy"], "f1_macro": r["f1_macro"]}
    summary["sentiment_by_language"] = {r["slice"]: _pair(r) for r in by_lang}
    summary["sentiment_by_sector"] = {r["slice"]: _pair(r) for r in by_sector}
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


def score_taxonomy(sigs, summary):
    """Closed-set scoring for journey_stage and owner (the §3.5.2 design).

    Scored from the CONSTRAINED run (`predict_llm.py --constrained`), where the
    workspace's inventory is supplied, because free-form generation cannot be
    compared to the gold vocabulary. Reported separately from §5A.3-5A.4, which
    come from the production-config run.

    Three numbers travel together: a majority-class floor (accuracy over 27 or
    51 classes is meaningless without one), the model's accuracy, and the
    in-vocabulary rate — if the model ignores the inventory, the comparison is
    void and the reader has to be able to see that.
    """
    cache = os.path.join(RESULTS, "predictions_llm_taxonomy.json")
    if not os.path.exists(cache):
        summary["taxonomy_path"] = ("not run — `python3 predict_llm.py --constrained`"
                                    " writes predictions_llm_taxonomy.json")
        return
    preds = {p["id"]: p for p in json.load(open(cache))}
    for field in ("journey_stage", "owner"):
        have = [s for s in sigs if getattr(s, field) and s.id in preds and s.text]
        if not have:
            continue
        y_true = [getattr(s, field) for s in have]
        y_pred = [str(preds[s.id].get(field, "") or "").strip() for s in have]
        vocab = set(y_true)
        overall = M.score(y_true, y_pred)
        top = collections.Counter(y_true).most_common(1)[0]
        # Per-class rows only where support >= 5, the harness-wide slice minimum;
        # a 51-class macro-F1 dominated by singletons reports noise.
        supported = sorted({v for v, n in collections.Counter(y_true).items() if n >= 5})
        idx = [i for i, t in enumerate(y_true) if t in supported]
        sup = M.score([y_true[i] for i in idx], [y_pred[i] for i in idx]) if idx else {}
        _w(f"{field}_perclass.csv",
           M.per_class(y_true, y_pred, sorted(vocab)),
           ["label", "precision", "recall", "f1", "support"])
        summary[f"{field}_llm_closed_set"] = {
            "n": overall["n"],
            "n_classes": len(vocab),
            "accuracy": overall["accuracy"],
            "f1_macro_all_classes": overall["f1_macro"],
            "majority_class_floor": round(top[1] / len(y_true), 4),
            "majority_class": top[0],
            "in_vocabulary_rate": round(
                sum(1 for p in y_pred if p in vocab) / len(y_pred), 4),
            "classes_with_support_5plus": len(supported),
            "coverage_of_those_classes": round(len(idx) / len(y_true), 4),
            "accuracy_on_supported": sup.get("accuracy"),
            "f1_macro_on_supported": sup.get("f1_macro"),
        }
    summary["taxonomy_path"] = "scored from the constrained run (inventory supplied)"


def equity_slices(sigs, summary, preds=None, ml_risk=None):
    """Per-language escalation recall, and the language x sector composition.

    NB: `language` records the SOURCE review's language; the paraphrased texts
    themselves are English (§3.5.1), so these are source-language strata, not
    text-language strata — any claim built on them must say so.

    Escalation recall (TPR on gold-escalate) is the equal-opportunity metric:
    it conditions on the gold label, so the very different base rates across
    language strata do not distort it the way a raw escalation *rate* would.

    The composition table is reported alongside because language is confounded
    with dataset on this corpus (German is largely the B2B stratum, English
    largely fintech). Any per-language claim has to be read against it, so the
    harness emits it rather than leaving it to prose.
    """
    esc = lambda x: x in ("high", "critical")
    have = [s for s in sigs if s.risk in RISK_LABELS and s.text]
    rows = {}
    for lang in sorted({s.language for s in have}):
        gold = [s for s in have if s.language == lang and esc(s.risk)]
        if len(gold) < 5:  # too small to report; counted in composition instead
            continue
        row = {
            "n_signals": len([s for s in have if s.language == lang]),
            "n_gold_escalate": len(gold),
            "base_rate": round(len(gold) / len([s for s in have if s.language == lang]), 4),
            "recall_floor": round(
                sum(1 for s in gold if esc(bl.predict_risk(s.text))) / len(gold), 4),
        }
        if ml_risk:
            scored_ml = [s for s in gold if s.id in ml_risk]
            if scored_ml:
                row["recall_ml"] = round(
                    sum(1 for s in scored_ml if esc(ml_risk[s.id])) / len(scored_ml), 4)
                row["n_gold_escalate_ml"] = len(scored_ml)
        if preds:
            scored = [s for s in gold if s.id in preds]
            if scored:
                row["recall_llm"] = round(
                    sum(1 for s in scored if esc(preds[s.id].get("risk", "low")))
                    / len(scored), 4)
                row["n_gold_escalate_llm"] = len(scored)
        rows[lang] = row
    summary["escalation_recall_by_language"] = rows
    if rows:
        _w("escalation_recall_by_language.csv",
           [{"language": lang, **r} for lang, r in sorted(rows.items())],
           ["language", "n_signals", "n_gold_escalate", "base_rate",
            "recall_floor", "n_gold_escalate_ml", "recall_ml",
            "n_gold_escalate_llm", "recall_llm"])

    comp = {}
    for s in sigs:
        if s.star_rating is None and s.risk not in RISK_LABELS:
            continue
        comp[f"{s.language}|{s.sector}"] = comp.get(f"{s.language}|{s.sector}", 0) + 1
    summary["language_sector_composition"] = dict(sorted(comp.items()))


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
    """Score the TF-IDF + LR baseline and persist its per-item OOF predictions.

    The per-item cache (results/predictions_ml.json) is what makes the paired
    significance tests possible: McNemar needs both classifiers' calls on the
    SAME items, not two accuracy totals — and it lets the ML predictor join
    the per-language escalation-recall table alongside floor and LLM.
    """
    ml_preds = {"sentiment": {}, "risk": {}}
    # sentiment vs star gold
    rated = [s for s in sigs if s.star_rating is not None and s.text]
    texts = [s.text for s in rated]
    gold = [bl.gold_sentiment_from_stars(s.star_rating) for s in rated]
    y_true, y_pred, k, idx = ml.cv_predict(texts, gold)
    ml_preds["sentiment"] = {rated[i].id: p for i, p in zip(idx, y_pred)}
    r = M.score(y_true, y_pred); r["cv_folds"] = k
    _w("sentiment_ml.csv", [r], list(r.keys()))
    summary["sentiment_ml_tfidf_lr"] = r
    # risk vs risk_seed gold (TR + Henkel)
    have = [s for s in sigs if s.risk in RISK_LABELS and s.text]
    yt, yp, k2, idx2 = ml.cv_predict([s.text for s in have], [s.risk for s in have])
    ml_preds["risk"] = {have[i].id: p for i, p in zip(idx2, yp)}
    r2 = M.score(yt, yp); r2["cv_folds"] = k2
    _w("risk_ml.csv", [r2], list(r2.keys()))
    summary["risk_ml_tfidf_lr"] = r2
    with open(os.path.join(RESULTS, "predictions_ml.json"), "w") as fh:
        json.dump(ml_preds, fh, indent=2)
    return ml_preds


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
    # Same slices as the lexicon floor (same >=5 minimum), so §5A.5 compares
    # like with like instead of a floor-only breakdown.
    for attr in ("language", "sector"):
        out = {}
        for val in sorted({getattr(s, attr) for s in rated}):
            sub = [(t, p) for t, p, s in zip(y_true, y_pred, rated)
                   if getattr(s, attr) == val]
            if len(sub) >= 5:
                r = M.score([a for a, _ in sub], [b for _, b in sub])
                out[val] = {"n": r["n"], "accuracy": r["accuracy"], "f1_macro": r["f1_macro"]}
        summary[f"sentiment_llm_by_{attr}"] = out

    # Language x sector, because language is confounded with sector here: any
    # aggregate per-language gap may be a composition effect. Only a sector
    # carrying both languages supports a within-sector language claim.
    cross = {}
    for sec in sorted({s.sector for s in rated}):
        for lang in sorted({s.language for s in rated}):
            sub = [(t, p) for t, p, s in zip(y_true, y_pred, rated)
                   if s.sector == sec and s.language == lang]
            if len(sub) >= 5:
                r = M.score([a for a, _ in sub], [b for _, b in sub])
                cross[f"{lang}|{sec}"] = {
                    "n": r["n"], "accuracy": r["accuracy"], "f1_macro": r["f1_macro"]}
    summary["sentiment_llm_by_language_sector"] = cross
    have = [s for s in sigs if s.risk in RISK_LABELS and s.id in preds and s.text]
    if have:
        summary["risk_llm"] = M.score([s.risk for s in have],
                                      [preds[s.id].get("risk", "low") for s in have])
    summary["llm_path"] = f"scored {len(rated)} sentiment / {len(have)} risk predictions"


def significance(sigs, summary, ml_preds, llm_preds):
    """Paired exact McNemar tests between the three predictors (§3.5.3, §5A.6).

    §5A reports the floor -> learned -> contextual ordering; this makes each
    pairwise step carry its own test instead of an eyeballed gap. Convention
    matches the platform's in-repo harness (metrics.mcnemar_exact): b = first
    predictor right & second wrong, c = the reverse, p = exact two-sided
    binomial(b + c, 0.5). Each entry is computed on the intersection of items
    both predictors scored, and reports both accuracies on exactly that paired
    subset, so the tested gap is visible next to its p-value.
    """
    rated = [s for s in sigs if s.star_rating is not None and s.text]
    have = [s for s in sigs if s.risk in RISK_LABELS and s.text]
    tasks = {
        "sentiment": (rated,
                      lambda s: bl.gold_sentiment_from_stars(s.star_rating),
                      lambda s: bl.predict_sentiment(s.text),
                      (ml_preds or {}).get("sentiment", {}), "sentiment", "neutral"),
        "risk": (have,
                 lambda s: s.risk,
                 lambda s: bl.predict_risk(s.text),
                 (ml_preds or {}).get("risk", {}), "risk", "low"),
    }
    out = {}
    for task, (items, gold_fn, floor_fn, ml_map, fld, default) in tasks.items():
        correct = {"floor": {s.id: floor_fn(s) == gold_fn(s) for s in items}}
        if ml_map:
            correct["ml"] = {s.id: ml_map[s.id] == gold_fn(s)
                             for s in items if s.id in ml_map}
        if llm_preds:
            correct["llm"] = {s.id: llm_preds[s.id].get(fld, default) == gold_fn(s)
                              for s in items if s.id in llm_preds}
        res = {}
        for a, b_name in (("floor", "ml"), ("floor", "llm"), ("ml", "llm")):
            if a not in correct or b_name not in correct:
                continue
            ids = sorted(set(correct[a]) & set(correct[b_name]))
            if not ids:
                continue
            av = [correct[a][i] for i in ids]
            bv = [correct[b_name][i] for i in ids]
            b, c, p = M.mcnemar_exact(av, bv)
            res[f"{a}_vs_{b_name}"] = {
                "n_pairs": len(ids),
                f"acc_{a}": round(sum(av) / len(ids), 4),
                f"acc_{b_name}": round(sum(bv) / len(ids), 4),
                "b_first_only_correct": b,
                "c_second_only_correct": c,
                "p_exact_two_sided": round(p, 6),
            }
        out[task] = res
    summary["mcnemar_paired"] = out


def main():
    sigs = load()
    summary = {"corpus_n": len(sigs),
               "datasets": sorted({s.dataset for s in sigs})}
    corpus_stats(sigs)
    by_sector = eval_sentiment(sigs, summary)
    eval_risk(sigs, summary)
    ml_preds = eval_ml(sigs, summary)
    f1_breakdown(by_sector)
    score_llm(sigs, summary)
    score_taxonomy(sigs, summary)
    cache = os.path.join(RESULTS, "predictions_llm.json")
    llm_preds = ({p["id"]: p for p in json.load(open(cache))}
                 if os.path.exists(cache) else None)
    equity_slices(sigs, summary, llm_preds,
                  ml_preds.get("risk") if ml_preds else None)
    significance(sigs, summary, ml_preds, llm_preds)
    with open(os.path.join(RESULTS, "summary.json"), "w") as fh:
        json.dump(summary, fh, indent=2)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
