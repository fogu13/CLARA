"""Run the real-data gold-set evaluation and write every result to disk.

Outputs (in evaluation/results/):
  corpus_stats.csv            descriptive stats of the real corpus
  sentiment_*.csv             lexicon sentiment vs star-rating gold (overall/by-language/by-sector/by-source/per-class)
  sentiment_confusion.csv     + .png heatmap (also *_ml_* and *_llm_* variants per predictor)
  risk_*.csv                  keyword risk vs risk_seed gold (TR + Henkel), same per-predictor variants
  f1_breakdown.png            F1 by slice
  predictions_ml.json         per-item TF-IDF+LR out-of-fold predictions (paired-test input)
  escalation_recall_by_language.csv   equal-opportunity table, every predictor, Wilson intervals
  escalation_recall_fisher.csv        two-sided Fisher exact tests between language strata
  composition.csv             language x sector / language x source counts (the confound table)
  mcnemar_paired.csv          paired exact McNemar tests, with the one-flip fragility p
  summary.json                headline numbers Chapter 5 §5A reads back

Every accuracy carries a 95% Wilson interval (accuracy_ci_low/high).

Two optional LLM prediction files are scored when present:
  predictions_llm.json             generic 3-class prompt (predict_llm.py)        -> keys *_llm
  predictions_llm_production.json  CLARA's production enrich_signals path
                                   (predict_llm_production.py)                     -> keys *_llm_production
Otherwise only the deterministic baselines run.

Each LLM file is validated against the gold ids first (prediction_validation.py):
duplicate ids keep their first row, rows with no usable id are counted as invalid
ids, unknown ids (not in the corpus) and outside-task ids (in the corpus, not in
this task's gold) are counted separately and ignored, and a missing / empty /
off-vocabulary label is INVALID — never defaulted. Per task the summary carries
the coverage-conditioned score (`sentiment_llm`, valid rows only) and the
end-to-end score (`sentiment_llm_end_to_end`, every gold item, missing or invalid
counted as wrong) with the counts, repeated under `prediction_validation`. The
taxonomy fields (journey_stage, owner; open vocabulary) go through the same
validator under `prediction_validation.llm_taxonomy`.
"""
from __future__ import annotations
import csv
import json
import os
import collections

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from load_datasets import dedupe_signals, load
import baseline as bl
import metrics as M
import ml_baseline as ml
from prediction_validation import validate_predictions

# THESIS_RESULTS_DIR lets exploratory runs (e.g. THESIS_DATASETS=vodafone_de)
# write elsewhere, so the committed thesis results/ are never overwritten.
# Module-level on purpose: the smoke test (test_run_eval_smoke.py) points it at
# a temp folder before calling score_llm/significance directly.
RESULTS = os.environ.get("THESIS_RESULTS_DIR") or os.path.join(os.path.dirname(__file__), "results")
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


MIN_SLICE = 5  # harness-wide minimum n for any reported slice
LLM_RUNS = (
    # (summary key, predictions file, label in summary/paths)
    ("llm", "predictions_llm.json",
     "generic 3-class prompt — predict_llm.py; NOT the artifact's enrichment stage"),
    ("llm_production", "predictions_llm_production.json",
     "CLARA's production enrich_signals path — predict_llm_production.py"),
)


def _compact(r):
    """The columns a slice table carries: n, accuracy + Wilson interval, macro-F1."""
    return {"n": r["n"], "accuracy": r["accuracy"],
            "accuracy_ci_low": r["accuracy_ci_low"],
            "accuracy_ci_high": r["accuracy_ci_high"],
            "f1_macro": r["f1_macro"]}


def _slices(items, y_true, y_pred, attr, labels=None):
    """Score every value of `attr` carrying >= MIN_SLICE items."""
    out = {}
    for val in sorted({getattr(s, attr) for s in items}):
        sub = [(t, p) for t, p, s in zip(y_true, y_pred, items) if getattr(s, attr) == val]
        if len(sub) >= MIN_SLICE:
            out[val] = _compact(M.score([a for a, _ in sub], [b for _, b in sub], labels))
    return out


def _cross_slices(items, y_true, y_pred, labels=None):
    """language x sector cells with >= MIN_SLICE items (the composition check)."""
    out = {}
    for sec in sorted({s.sector for s in items}):
        for lang in sorted({s.language for s in items}):
            sub = [(t, p) for t, p, s in zip(y_true, y_pred, items)
                   if s.sector == sec and s.language == lang]
            if len(sub) >= MIN_SLICE:
                out[f"{lang}|{sec}"] = _compact(
                    M.score([a for a, _ in sub], [b for _, b in sub], labels))
    return out


def _per_class_and_confusion(y_true, y_pred, labels, stem, title):
    present = [lab for lab in labels if lab in set(y_true) | set(y_pred)]
    _w(f"{stem}_perclass.csv", M.per_class(y_true, y_pred, present),
       ["label", "precision", "recall", "f1", "support"])
    M.write_confusion(y_true, y_pred, present, os.path.join(RESULTS, f"{stem}_confusion.csv"))
    _heatmap(f"{stem}_confusion.csv", f"{stem}_confusion.png", title)


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
    overall = M.score(y_true, y_pred)
    _w("sentiment_overall.csv", [overall], list(overall.keys()))
    _per_class_and_confusion(y_true, y_pred, SENT_LABELS, "sentiment",
                             "Sentiment (lexicon) vs star-rating gold")
    # slices: language, sector, source (source = review platform / channel)
    by = {attr: _slices(rated, y_true, y_pred, attr) for attr in ("language", "sector", "source")}
    cols = ["slice"] + list(_compact(overall).keys())
    for attr, table in by.items():
        _w(f"sentiment_by_{attr}.csv", [{"slice": k, **v} for k, v in table.items()], cols)
    summary["sentiment_baseline"] = overall
    # Both metrics, never macro-F1 alone: on small slices with sparse minority
    # classes macro-F1 swings wildly and can invert the accuracy story.
    summary["sentiment_by_language"] = by["language"]
    summary["sentiment_by_sector"] = by["sector"]
    summary["sentiment_by_source"] = by["source"]
    return [{"slice": k, **v} for k, v in by["sector"].items()]


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
    sigs, _ = dedupe_signals(sigs)  # a repeated gold id must never double-score
    cache = os.path.join(RESULTS, "predictions_llm_taxonomy.json")
    if not os.path.exists(cache):
        summary["taxonomy_path"] = ("not run — `python3 predict_llm.py --constrained`"
                                    " writes predictions_llm_taxonomy.json")
        return
    with open(cache) as fh:
        rows = json.load(fh)
    validation = summary.setdefault("prediction_validation", {}).setdefault("llm_taxonomy", {})
    corpus_ids = [s.id for s in sigs]
    for field in ("journey_stage", "owner"):
        # Open vocabulary (labels=None): any non-empty string is a valid answer;
        # a missing row, an empty string or a non-string is invalid, never "".
        expected = [s for s in sigs if getattr(s, field) and s.text]
        if not expected:
            continue
        vt = validate_predictions(rows, expected_ids=[s.id for s in expected],
                                  field=field, labels=None, corpus_ids=corpus_ids)
        validation[field] = vt.detail()
        have = [s for s in expected if s.id in vt.by_id]
        y_true = [getattr(s, field) for s in have]
        y_pred = [vt.by_id[s.id] for s in have]
        summary[f"{field}_llm_closed_set_end_to_end"] = _end_to_end(vt, y_true, y_pred)
        if not have:
            continue
        vocab = set(y_true)
        overall = M.score(y_true, y_pred)
        top = collections.Counter(y_true).most_common(1)[0]
        # Per-class rows only where support >= 5, the harness-wide slice minimum;
        # a 51-class macro-F1 dominated by singletons reports noise.
        supported = sorted({v for v, n in collections.Counter(y_true).items() if n >= 5})
        idx = [i for i, t in enumerate(y_true) if t in supported]
        # labels=supported: the macro average must run over the supported
        # classes only; averaging over every label that appears in y_pred as
        # well silently re-admits the singleton classes the restriction excluded.
        sup = (M.score([y_true[i] for i in idx], [y_pred[i] for i in idx], labels=supported)
               if idx else {})
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


def equity_slices(sigs, summary, llm_maps=None, ml_risk=None):
    """Per-language escalation recall (with Wilson intervals and Fisher tests),
    and the composition tables that any per-language claim has to be read against.

    NB: `language` records the SOURCE review's language; the paraphrased texts
    themselves are English (§3.5.1), so these are source-language strata, not
    text-language strata — any claim built on them must say so.

    Escalation recall (TPR on gold-escalate) is the equal-opportunity metric:
    it conditions on the gold label, so the very different base rates across
    language strata do not distort it the way a raw escalation *rate* would.
    Each recall carries a 95% Wilson interval, and every pair of language
    strata gets a two-sided Fisher exact test per predictor, so a gap is
    reported with its uncertainty rather than as two bare proportions.
    `recall_<p>` is coverage-conditioned (gold-escalate items the predictor
    gave a valid label); `recall_<p>_end_to_end` counts a gold-escalate item
    with no valid prediction as a miss.

    The composition tables are written because language is confounded with
    dataset on this corpus (German is largely the B2B stratum, English largely
    fintech). Any per-language claim has to be read against them, so the
    harness emits them rather than leaving it to prose.
    """
    sigs, _ = dedupe_signals(sigs)  # a repeated gold id must never double-score
    esc = lambda x: x in ("high", "critical")
    have = [s for s in sigs if s.risk in RISK_LABELS and s.text]
    llm_maps = llm_maps or {}
    predictors = {"floor": lambda s: esc(bl.predict_risk(s.text))}
    if ml_risk:
        predictors["ml"] = lambda s, m=ml_risk: (s.id in m) and esc(m[s.id])
        scored_by = {"ml": lambda s, m=ml_risk: s.id in m}
    else:
        scored_by = {}
    for key, maps in llm_maps.items():
        # maps["risk"] holds VALID predictions only (prediction_validation);
        # an item without one is not scored for this predictor, never "low".
        risk_map = maps.get("risk") or {}
        predictors[key] = lambda s, m=risk_map: (s.id in m) and esc(m[s.id])
        scored_by[key] = lambda s, m=risk_map: s.id in m

    rows, hits = {}, {}
    for lang in sorted({s.language for s in have}):
        gold = [s for s in have if s.language == lang and esc(s.risk)]
        if len(gold) < MIN_SLICE:  # too small to report; counted in composition instead
            continue
        n_lang = len([s for s in have if s.language == lang])
        row = {"n_signals": n_lang, "n_gold_escalate": len(gold),
               "base_rate": round(len(gold) / n_lang, 4)}
        for name, fn in predictors.items():
            scored = [s for s in gold if name not in scored_by or scored_by[name](s)]
            if not scored:
                # A predictor that answered no gold-escalate item of this
                # stratum validly is still reported: coverage 0, the
                # coverage-conditioned recall null (nothing to condition on)
                # and the end-to-end recall 0 (every item a miss). It cannot
                # enter a Fisher test (no hits, no misses to test).
                row[f"n_gold_escalate_{name}"] = 0
                row[f"recall_{name}"] = None
                row[f"recall_{name}_ci_low"], row[f"recall_{name}_ci_high"] = None, None
                row[f"recall_{name}_end_to_end"] = 0.0
                continue
            k = sum(1 for s in scored if fn(s))
            lo, hi = M.wilson_interval(k, len(scored))
            row[f"n_gold_escalate_{name}"] = len(scored)
            row[f"recall_{name}"] = round(k / len(scored), 4)
            row[f"recall_{name}_ci_low"], row[f"recall_{name}_ci_high"] = lo, hi
            # End-to-end companion: every gold-escalate item in the
            # denominator; an item with no valid prediction is a miss.
            row[f"recall_{name}_end_to_end"] = round(k / len(gold), 4)
            hits[(name, lang)] = (k, len(scored) - k)
        rows[lang] = row
    summary["escalation_recall_by_language"] = rows
    if rows:
        # Column order: the stratum's totals, then per predictor n / recall /
        # interval, in the floor -> ml -> llm order the chapter reads them.
        lead = ["n_signals", "n_gold_escalate", "base_rate"]
        per_pred = [
            col for name in predictors
            for col in (f"n_gold_escalate_{name}", f"recall_{name}",
                        f"recall_{name}_ci_low", f"recall_{name}_ci_high",
                        f"recall_{name}_end_to_end")]
        seen = {c for r in rows.values() for c in r}
        cols = [c for c in lead + per_pred if c in seen]
        _w("escalation_recall_by_language.csv",
           [{"language": lang, **r} for lang, r in sorted(rows.items())],
           ["language"] + cols)

    # Fisher exact test on hits/misses between every pair of reported strata.
    fisher = []
    langs = sorted(rows)
    for name in predictors:
        for i, la in enumerate(langs):
            for lb in langs[i + 1:]:
                if (name, la) not in hits or (name, lb) not in hits:
                    # One stratum has no validly answered gold-escalate item:
                    # the pair is reported as absent, not silently dropped.
                    fisher.append({
                        "predictor": name, "language_a": la, "language_b": lb,
                        "hits_a": None, "misses_a": None, "hits_b": None, "misses_b": None,
                        "recall_a": None, "recall_b": None, "p_fisher_two_sided": None,
                        "note": "no test: a stratum has no validly answered gold-escalate item",
                    })
                    continue
                a, b = hits[(name, la)]
                c, d = hits[(name, lb)]
                fisher.append({
                    "predictor": name, "language_a": la, "language_b": lb,
                    "hits_a": a, "misses_a": b, "hits_b": c, "misses_b": d,
                    "recall_a": round(a / (a + b), 4), "recall_b": round(c / (c + d), 4),
                    "p_fisher_two_sided": round(M.fisher_exact(a, b, c, d), 6),
                    "note": "",
                })
    summary["escalation_recall_fisher"] = fisher
    if fisher:
        _w("escalation_recall_fisher.csv", fisher, list(fisher[0].keys()))

    # Composition: every labelled item, by language x sector and language x source,
    # with the risk-labelled and gold-escalate counts that the recall table draws on.
    comp_rows = []
    for other in ("sector", "source"):
        cells = collections.defaultdict(lambda: [0, 0, 0])
        for s in sigs:
            if s.star_rating is None and s.risk not in RISK_LABELS:
                continue
            cell = cells[(s.language, getattr(s, other))]
            cell[0] += 1
            if s.risk in RISK_LABELS:
                cell[1] += 1
                if esc(s.risk):
                    cell[2] += 1
        for (lang, val), (n_all, n_risk, n_esc) in sorted(cells.items()):
            comp_rows.append({"language": lang, "dimension": other, "value": val,
                              "n_labelled": n_all, "n_risk_labelled": n_risk,
                              "n_gold_escalate": n_esc})
    _w("composition.csv", comp_rows,
       ["language", "dimension", "value", "n_labelled", "n_risk_labelled", "n_gold_escalate"])
    summary["language_sector_composition"] = {
        f"{r['language']}|{r['value']}": r["n_labelled"]
        for r in comp_rows if r["dimension"] == "sector"}
    summary["language_source_composition"] = {
        f"{r['language']}|{r['value']}": r["n_labelled"]
        for r in comp_rows if r["dimension"] == "source"}


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
    _per_class_and_confusion(y_true, y_pred, SENT_LABELS, "sentiment_ml",
                             "Sentiment (TF-IDF+LR, out-of-fold) vs star-rating gold")
    kept = [rated[i] for i in idx]
    summary["sentiment_ml_by_language"] = _slices(kept, y_true, y_pred, "language")
    summary["sentiment_ml_by_source"] = _slices(kept, y_true, y_pred, "source")
    summary["sentiment_ml_tfidf_lr"] = r
    # risk vs risk_seed gold (TR + Henkel)
    have = [s for s in sigs if s.risk in RISK_LABELS and s.text]
    yt, yp, k2, idx2 = ml.cv_predict([s.text for s in have], [s.risk for s in have])
    ml_preds["risk"] = {have[i].id: p for i, p in zip(idx2, yp)}
    r2 = M.score(yt, yp); r2["cv_folds"] = k2
    _w("risk_ml.csv", [r2], list(r2.keys()))
    _per_class_and_confusion(yt, yp, RISK_LABELS, "risk_ml",
                             "Risk (TF-IDF+LR, out-of-fold) vs risk_seed gold")
    summary["risk_ml_tfidf_lr"] = r2
    with open(os.path.join(RESULTS, "predictions_ml.json"), "w") as fh:
        json.dump(ml_preds, fh, indent=2)
    return ml_preds


END_TO_END_RULE = ("every gold-labelled item is in the denominator; an item with no "
                   "prediction (missing) or an invalid label (empty / off-vocabulary) "
                   "counts as wrong")


def _end_to_end(vs, y_true, y_pred):
    """Accuracy over ALL expected items, missing/invalid counted as wrong.

    The coverage-conditioned score next to it is computed on the valid rows
    only, so the two views differ exactly by the model's non-answers; both are
    reported because neither alone describes a model that abstains.
    """
    correct = sum(1 for t, p in zip(y_true, y_pred) if t == p)
    n = vs.n_expected
    if not n:
        # Nothing expected: the accuracy is undefined, not 0.0, and there is
        # no interval to report.
        return {"rule": END_TO_END_RULE, **vs.counts(), "n_correct": correct,
                "accuracy": None, "accuracy_ci_low": None, "accuracy_ci_high": None}
    lo, hi = M.wilson_interval(correct, n)
    return {"rule": END_TO_END_RULE, **vs.counts(), "n_correct": correct,
            "accuracy": round(correct / n, 4),
            "accuracy_ci_low": lo, "accuracy_ci_high": hi}


def score_llm(sigs, summary, *, key="llm", cache="predictions_llm.json", label=""):
    """Score one LLM prediction file under summary keys `*_{key}`.

    Returns {"sentiment": {id: label}, "risk": {id: label}} holding the VALID
    predictions only (see prediction_validation), or None when the file is
    absent. Every gold item falls into valid / invalid / missing, and the
    counts are written under summary["prediction_validation"][key][task].

    Two quality views per task:
      sentiment_{key}, risk_{key}               coverage-conditioned: valid rows
                                                only, class set fixed to the task
                                                labels (no stray class in the
                                                macro average)
      sentiment_{key}_end_to_end, risk_{key}_end_to_end
                                                denominator = every gold item;
                                                missing / invalid count as wrong
    Per-class and confusion tables use the valid rows only, so they sum to
    n_valid. No label is defaulted anywhere.

    Two files are supported (see LLM_RUNS): the generic-prompt run and the
    production-path run. A production file carries `sentiment_raw` (the
    4-class production label) next to the pre-registered 3-class mapping
    (mixed -> neutral); when present, a sensitivity score that drops the
    mixed items is reported next to the primary one, so the reader can see
    how much of the result rests on the mapping rule.
    """
    sigs, _ = dedupe_signals(sigs)  # a repeated gold id must never double-score
    path = os.path.join(RESULTS, cache)
    if not os.path.exists(path):
        summary[f"{key}_path"] = f"not run (no {cache}; {label})"
        return None
    with open(path) as fh:
        rows = json.load(fh)
    # First row per id, for the raw-label sensitivity below (same "first
    # occurrence wins" rule as the validator). A row that is not a mapping
    # has no id: the validator counts it under n_invalid_ids; skip it here.
    first_row = {}
    for r in rows:
        if isinstance(r, dict) and r.get("id") not in (None, ""):
            first_row.setdefault(str(r.get("id")), r)
    validation = summary.setdefault("prediction_validation", {}).setdefault(key, {})
    maps = {}
    corpus_ids = [s.id for s in sigs]

    rated_all = [s for s in sigs if s.star_rating is not None and s.text]
    vs = validate_predictions(rows, expected_ids=[s.id for s in rated_all],
                              field="sentiment", labels=SENT_LABELS, corpus_ids=corpus_ids)
    validation["sentiment"] = vs.detail()
    maps["sentiment"] = dict(vs.by_id)
    rated = [s for s in rated_all if s.id in vs.by_id]
    y_true = [bl.gold_sentiment_from_stars(s.star_rating) for s in rated]
    y_pred = [vs.by_id[s.id] for s in rated]
    summary[f"sentiment_{key}_end_to_end"] = _end_to_end(vs, y_true, y_pred)
    if rated:
        summary[f"sentiment_{key}"] = M.score(y_true, y_pred, SENT_LABELS)
        _per_class_and_confusion(y_true, y_pred, SENT_LABELS, f"sentiment_{key}",
                                 f"Sentiment ({key}) vs star-rating gold")
        # Same slices as the lexicon floor (same >= MIN_SLICE minimum), so §5A.5
        # compares like with like instead of a floor-only breakdown.
        for attr in ("language", "sector", "source"):
            summary[f"sentiment_{key}_by_{attr}"] = _slices(rated, y_true, y_pred, attr, SENT_LABELS)
        # Language x sector, because language is confounded with sector here: any
        # aggregate per-language gap may be a composition effect. Only a sector
        # carrying both languages supports a within-sector language claim.
        summary[f"sentiment_{key}_by_language_sector"] = _cross_slices(rated, y_true, y_pred, SENT_LABELS)
    if any("sentiment_raw" in r for r in rows if isinstance(r, dict)):
        raw = collections.Counter(first_row[s.id].get("sentiment_raw") for s in rated)
        keep = [i for i, s in enumerate(rated) if first_row[s.id].get("sentiment_raw") != "mixed"]
        summary[f"sentiment_{key}_raw_label_counts"] = dict(raw)
        excl = {
            "rule": "sensitivity: items the production model labelled mixed are dropped;"
                    " the primary score maps mixed -> neutral (pre-registered)",
            "n_valid": len(keep),
            "n_dropped": len(rated) - len(keep),
        }
        if keep:
            excl.update(M.score([y_true[i] for i in keep], [y_pred[i] for i in keep], SENT_LABELS))
        else:
            # No valid non-mixed row is left: there is nothing to condition on
            # (M.score would raise on empty input); the counts say why.
            excl["note"] = "no valid non-mixed prediction; no coverage-conditioned score"
        summary[f"sentiment_{key}_excluding_mixed"] = excl

    have_all = [s for s in sigs if s.risk in RISK_LABELS and s.text]
    have = []
    if have_all:
        vr = validate_predictions(rows, expected_ids=[s.id for s in have_all],
                                  field="risk", labels=RISK_LABELS, corpus_ids=corpus_ids)
        validation["risk"] = vr.detail()
        maps["risk"] = dict(vr.by_id)
        have = [s for s in have_all if s.id in vr.by_id]
        rt = [s.risk for s in have]
        rp = [vr.by_id[s.id] for s in have]
        summary[f"risk_{key}_end_to_end"] = _end_to_end(vr, rt, rp)
        if have:
            summary[f"risk_{key}"] = M.score(rt, rp, RISK_LABELS)
            _per_class_and_confusion(rt, rp, RISK_LABELS, f"risk_{key}",
                                     f"Risk ({key}) vs risk_seed gold")
            esc = lambda x: "escalate" if x in ("high", "critical") else "routine"
            summary[f"risk_{key}_binary_escalation"] = M.score(
                [esc(v) for v in rt], [esc(v) for v in rp], ["escalate", "routine"])
    summary[f"{key}_path"] = (
        f"scored {len(rated)} valid of {len(rated_all)} sentiment / "
        f"{len(have)} valid of {len(have_all)} risk predictions ({label}); "
        f"see prediction_validation.{key} for missing / invalid / duplicate / unknown-id counts")
    return maps


def significance(sigs, summary, ml_preds, llm_maps=None):
    """Paired exact McNemar tests between every pair of predictors (§3.5.3, §5A.6).

    §5A reports the floor -> learned -> contextual ordering; this makes each
    pairwise step carry its own test instead of an eyeballed gap. Convention
    matches the platform's in-repo harness (metrics.mcnemar_exact): b = first
    predictor right & second wrong, c = the reverse, p = exact two-sided
    binomial(b + c, 0.5). Each entry is computed on the intersection of items
    both predictors scored with a VALID label (an LLM run's missing or invalid
    predictions are not defaulted, they drop the item from the pair), and
    reports both accuracies on exactly that paired subset plus `n_dropped`
    (gold items for the task outside the pair), so the tested gap is visible
    next to its p-value and its coverage.

    The three `p_*_one*` columns are the fragility check: the p-value after a
    single item's correctness changes, in each of the three ways it can. On a
    corpus this size several "significant" gaps rest on one item; the table has
    to show that rather than leave it to a reader's arithmetic.
    """
    sigs, _ = dedupe_signals(sigs)  # a repeated gold id must never double-score
    rated = [s for s in sigs if s.star_rating is not None and s.text]
    have = [s for s in sigs if s.risk in RISK_LABELS and s.text]
    llm_maps = llm_maps or {}
    tasks = {
        "sentiment": (rated,
                      lambda s: bl.gold_sentiment_from_stars(s.star_rating),
                      lambda s: bl.predict_sentiment(s.text),
                      (ml_preds or {}).get("sentiment", {}), "sentiment"),
        "risk": (have,
                 lambda s: s.risk,
                 lambda s: bl.predict_risk(s.text),
                 (ml_preds or {}).get("risk", {}), "risk"),
    }
    order = ["floor", "ml"] + [key for key, _, _ in LLM_RUNS]
    out, csv_rows = {}, []
    for task, (items, gold_fn, floor_fn, ml_map, fld) in tasks.items():
        correct = {"floor": {s.id: floor_fn(s) == gold_fn(s) for s in items}}
        if ml_map:
            correct["ml"] = {s.id: ml_map[s.id] == gold_fn(s)
                             for s in items if s.id in ml_map}
        for key, maps in llm_maps.items():
            # maps[fld] holds VALID predictions only (score_llm); no default.
            valid = maps.get(fld) or {}
            correct[key] = {s.id: valid[s.id] == gold_fn(s)
                            for s in items if s.id in valid}
        present = [name for name in order if name in correct]
        res = {}
        for i, a in enumerate(present):
            for b_name in present[i + 1:]:
                ids = sorted(set(correct[a]) & set(correct[b_name]))
                if not ids:
                    continue
                av = [correct[a][x] for x in ids]
                bv = [correct[b_name][x] for x in ids]
                b, c, p = M.mcnemar_exact(av, bv)
                entry = {
                    "n_pairs": len(ids),
                    "n_dropped": len(items) - len(ids),
                    f"acc_{a}": round(sum(av) / len(ids), 4),
                    f"acc_{b_name}": round(sum(bv) / len(ids), 4),
                    "b_first_only_correct": b,
                    "c_second_only_correct": c,
                    "p_exact_two_sided": round(p, 6),
                }
                sens = M.mcnemar_sensitivity(b, c)
                entry.update({k: v for k, v in sens.items() if k != "p_observed"})
                res[f"{a}_vs_{b_name}"] = entry
                csv_rows.append({"task": task, "pair": f"{a}_vs_{b_name}",
                                 "n_pairs": len(ids), "n_dropped": len(items) - len(ids),
                                 "acc_first": entry[f"acc_{a}"],
                                 "acc_second": entry[f"acc_{b_name}"],
                                 "b_first_only_correct": b, "c_second_only_correct": c,
                                 "p_exact_two_sided": entry["p_exact_two_sided"],
                                 "p_minority_gains_one": sens["p_minority_gains_one"],
                                 "p_majority_loses_one": sens["p_majority_loses_one"],
                                 "p_one_pair_swaps": sens["p_one_pair_swaps"]})
        out[task] = res
    summary["mcnemar_paired"] = out
    if csv_rows:
        _w("mcnemar_paired.csv", csv_rows, list(csv_rows[0].keys()))


def main():
    sigs = load()
    summary = {"corpus_n": len(sigs),
               "datasets": sorted({s.dataset for s in sigs}),
               "ci_method": "accuracy/recall intervals are 95% Wilson score intervals"}
    corpus_stats(sigs)
    by_sector = eval_sentiment(sigs, summary)
    eval_risk(sigs, summary)
    ml_preds = eval_ml(sigs, summary)
    f1_breakdown(by_sector)
    llm_maps = {}
    for key, cache, label in LLM_RUNS:
        preds = score_llm(sigs, summary, key=key, cache=cache, label=label)
        if preds:
            llm_maps[key] = preds
    score_taxonomy(sigs, summary)
    equity_slices(sigs, summary, llm_maps, ml_preds.get("risk") if ml_preds else None)
    significance(sigs, summary, ml_preds, llm_maps)
    with open(os.path.join(RESULTS, "summary.json"), "w") as fh:
        json.dump(summary, fh, indent=2)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
