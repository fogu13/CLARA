"""Human annotation kit for the thesis corpus: blind rating files, agreement, adjudication,
a human-adjudicated gold standard, and a re-score of the SAVED predictions against it.
No model is called at any step.

Why. The corpus's seed labels are assistant-drafted and used as delivered (§3.7), and the
one agreement check on them is of unverified provenance (PROVENANCE_kappa.md §5). Two
independent human raters plus adjudication turn the reference into a human gold standard
without new signals and without a model rerun: every predictor's per-item predictions are
already committed, so re-scoring is a file operation.

    draw        python3 annotation_kit.py draw --raters A,B [--n 0] [--seed 20260913] [--out results/annotation]
    agreement   python3 annotation_kit.py agreement results/annotation/rater_A.csv results/annotation/rater_B.csv
    adjudicate  python3 annotation_kit.py adjudicate rater_A.csv rater_B.csv disagreements.csv --out gold_human.csv
    rescore     python3 annotation_kit.py rescore results/annotation/gold_human.csv [--out results/human_gold]

draw writes one CSV per rater (public_signal_id, sector, source, text, and the five
label columns EMPTY: sentiment, risk, urgency, journey_stage, owner), the closed
inventories the raters pick from (inventories.json: the corpus's own journey-stage and
owner vocabularies; sentiment and the two ordinal scales are fixed), INSTRUCTIONS.md (the
rubric, with the production urgency rubric quoted from the artifact's own system prompt),
PROVENANCE_template.md (what must be recorded per rater, PROVENANCE_kappa.md §6) and a
manifest. The seed labels never enter any file the raters see.

agreement computes, per field, exact agreement and Cohen's kappa (unweighted; linear-
weighted as well for the ordinal risk and urgency scales) with percentile-bootstrap 95%
intervals, and writes disagreements.csv for adjudication (fill the `adjudicated` column).

adjudicate builds gold_human.csv: the raters' label where they agree, the adjudicated
label where they disagree; it refuses an unfilled or out-of-vocabulary adjudication.

rescore scores the committed prediction files against the human gold, field by field:
accuracy on valid predictions with a Wilson interval, macro-F1, end-to-end accuracy
(an invalid prediction counts as wrong), and exact McNemar tests between predictors on
identical items. Default sources: results/predictions_ml.json, results/predictions_llm.json,
results/predictions_llm_production.json, results_mistral-small-2603/predictions_llm_production.json,
results/predictions_llm_taxonomy.json; override with --predictions label=path.

rescore --retrain-ml additionally retrains the TF-IDF + logistic regression baseline on
the human gold itself, for sentiment and risk only (the fields the committed learned
model predicts): the texts are joined from the corpus loader by public_signal_id and
ml_baseline.cv_predict gives an out-of-fold prediction per item, with the folds formed on
the human gold rather than on the seed labels; --min-per-class (default 5) is the
smallest class the stratified folds admit, as in the committed run. The rows carry the
predictor name ml_retrained and a note saying so. ml_baseline (scikit-learn) is imported
only on that path, so the rest of the kit runs without it.

What each answer means. rescore answers how each committed prediction file agrees with
a human-adjudicated gold; --retrain-ml answers how a learned model trained on that gold
performs out of fold; neither answers whether the seed labels were correct.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import random
import re
import sys
from collections import Counter
from datetime import UTC, datetime
from itertools import combinations

HERE = os.path.dirname(os.path.abspath(__file__))
RESULTS = os.environ.get("THESIS_RESULTS_DIR") or os.path.join(HERE, "results")
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import metrics as M  # noqa: E402
from load_datasets import load  # noqa: E402

FIELDS = ("sentiment", "risk", "urgency", "journey_stage", "owner")
ORDINAL = ["low", "medium", "high", "critical"]
SENTIMENT = ["negative", "neutral", "positive"]
CLOSED = {"sentiment": SENTIMENT, "risk": ORDINAL, "urgency": ORDINAL}
SEED = 20260913
BOOTSTRAP = 2000

DEFAULT_PREDICTIONS = {
    "ml": os.path.join(RESULTS, "predictions_ml.json"),
    "llm_generic": os.path.join(RESULTS, "predictions_llm.json"),
    "llm_production_glm": os.path.join(RESULTS, "predictions_llm_production.json"),
    "llm_production_mistral": os.path.join(HERE, "results_mistral-small-2603", "predictions_llm_production.json"),
    "llm_taxonomy": os.path.join(RESULTS, "predictions_llm_taxonomy.json"),
}
# Which key of which prediction file answers which human field.
FIELD_SOURCES = {
    "sentiment": {"ml": "sentiment", "llm_generic": "sentiment", "llm_production_glm": "sentiment",
                  "llm_production_mistral": "sentiment"},
    "risk": {"ml": "risk", "llm_generic": "risk", "llm_production_glm": "risk", "llm_production_mistral": "risk"},
    "urgency": {"llm_production_glm": "urgency_raw", "llm_production_mistral": "urgency_raw"},
    "journey_stage": {"llm_taxonomy": "journey_stage", "llm_generic": "journey_stage"},
    "owner": {"llm_taxonomy": "owner", "llm_generic": "owner"},
}


def _norm(value: str | None) -> str:
    return (value or "").strip().lower().replace(" ", "_")


def _sha256(path: str) -> str:
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


# ----------------------------------------------------------------------------- draw

def inventories(sigs) -> dict[str, list[str]]:
    return {
        "sentiment": SENTIMENT,
        "risk": ORDINAL,
        "urgency": ORDINAL,
        "journey_stage": sorted({_norm(s.journey_stage) for s in sigs if _norm(s.journey_stage)}),
        "owner": sorted({_norm(s.owner) for s in sigs if _norm(s.owner)}),
    }


def production_urgency_rubric() -> str:
    """The urgency definition the artifact's own enrichment prompt uses, quoted so the
    raters label the construct the production stage is scored on (§5A.4.2)."""
    try:
        sys.path.insert(0, os.path.normpath(os.path.join(HERE, "..", "..", "apps", "api")))
        from app.services.enrichment import build_system_prompt

        prompt = build_system_prompt()[0]
        match = re.search(r"^- urgency:.*?(?=^- \w+:|\Z)", prompt, re.S | re.M)
        if match:
            return match.group(0).strip()
    except Exception:  # noqa: BLE001  (the kit must still draw without the API package)
        pass
    return ("- urgency: one of low | medium | high | critical, judged by impact and time-sensitivity "
            "(the production rubric could not be loaded; copy it from apps/api/app/services/enrichment.py).")


def instructions(inv: dict[str, list[str]]) -> str:
    rubric_path = os.path.join(RESULTS, "kappa_labelling_instructions.md")
    risk_rubric = ""
    if os.path.exists(rubric_path):
        text = open(rubric_path, encoding="utf-8").read()
        start = text.find("**What \"risk\" means here.**")
        risk_rubric = text[start:] if start >= 0 else text
    return f"""# Blind labelling of the thesis corpus: instructions for each rater

Written before any label is assigned. You receive one CSV with the text of every signal and
five EMPTY label columns. Fill every cell. Do not look at any other file, use no AI assistant,
model or automatic classifier for any row, and do not discuss rows with the author or the other
rater until both files are returned. Record the date you received the file and the date you
returned it, and confirm the no-AI-assistance statement, in PROVENANCE_template.md.

## sentiment (negative | neutral | positive)

The customer's overall evaluation as the text expresses it. Praise-and-complaint texts take
the evaluation that dominates; a genuinely balanced text is neutral. Ignore the star rating
if you know it; label the words.

## risk (low | medium | high | critical)

{risk_rubric.strip() or "What is at stake for the customer or the company if nothing is done, judged from the text alone."}

## urgency (low | medium | high | critical)

How soon someone must act, as the artifact's production prompt defines it (quoted verbatim
from the enrichment stage so that the labels match the construct the production stage is
scored on; risk above is a different question, and the two may differ for one text):

```
{production_urgency_rubric()}
```

## journey_stage and owner (pick one from the inventory)

Choose the single best value from `inventories.json` for each field; write it exactly as
listed. If nothing fits, write `other` and note the row in your provenance record.

Inventory sizes: journey_stage {len(inv['journey_stage'])} values, owner {len(inv['owner'])} values.

## Return

The same CSV with every label cell filled and nothing else changed, plus your completed
PROVENANCE_template.md. Expect two to three hours for the full corpus.
"""


PROVENANCE_TEMPLATE = """# Provenance record for this rating (one per rater; PROVENANCE_kappa.md §6)

- Rater role (not name; e.g. "practitioner, CX lead", "MSc student, not on this project"):
- Relationship to the author and to the artifact (none / colleague / ...):
- File received on (date, time zone):
- File returned on (date, time zone):
- Environment used to enter labels (spreadsheet application / text editor / other):
- AI assistance: I confirm that no AI assistant, model or automatic classifier was consulted for any row  [ yes / no ]
- Rows marked `other` and why:
- Signature or written confirmation (the author records this file with the returned CSV in the same commit):
"""


def draw(raters: list[str], *, n: int = 0, seed: int = SEED, out_dir: str) -> dict:
    sigs = sorted((s for s in load() if s.text), key=lambda s: s.id)
    if n:
        sigs = sorted(random.Random(seed).sample(sigs, min(n, len(sigs))), key=lambda s: s.id)
    os.makedirs(out_dir, exist_ok=True)
    columns = ["public_signal_id", "sector", "source", "text", *FIELDS]
    for rater in raters:
        path = os.path.join(out_dir, f"rater_{rater}.csv")
        with open(path, "w", encoding="utf-8", newline="") as fh:
            writer = csv.writer(fh)
            writer.writerow(columns)
            for s in sigs:
                writer.writerow([s.id, s.sector, s.source, s.text, "", "", "", "", ""])
    inv = inventories(sigs)
    with open(os.path.join(out_dir, "inventories.json"), "w", encoding="utf-8") as fh:
        json.dump(inv, fh, indent=2)
    with open(os.path.join(out_dir, "INSTRUCTIONS.md"), "w", encoding="utf-8") as fh:
        fh.write(instructions(inv))
    with open(os.path.join(out_dir, "PROVENANCE_template.md"), "w", encoding="utf-8") as fh:
        fh.write(PROVENANCE_TEMPLATE)
    manifest = {
        "drawn_at": datetime.now(UTC).isoformat(),
        "n": len(sigs),
        "seed": seed if n else None,
        "ids_sha256": hashlib.sha256("\n".join(s.id for s in sigs).encode()).hexdigest(),
        "fields": list(FIELDS),
        "raters": raters,
        "labels_in_files": "none: the seed labels are withheld from every rater file",
    }
    with open(os.path.join(out_dir, "manifest.json"), "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2)
    return manifest


# ------------------------------------------------------------------------ agreement

def cohen_kappa(a: list[str], b: list[str], labels: list[str], *, weighted: bool = False) -> float | None:
    n = len(a)
    if n == 0:
        return None
    k = len(labels)
    index = {label: i for i, label in enumerate(labels)}
    observed = [[0.0] * k for _ in range(k)]
    for x, y in zip(a, b):
        observed[index[x]][index[y]] += 1.0 / n
    pa = [sum(row) for row in observed]
    pb = [sum(observed[i][j] for i in range(k)) for j in range(k)]
    if weighted:
        weight = lambda i, j: abs(i - j) / (k - 1) if k > 1 else 0.0  # noqa: E731
        po = sum(weight(i, j) * observed[i][j] for i in range(k) for j in range(k))
        pe = sum(weight(i, j) * pa[i] * pb[j] for i in range(k) for j in range(k))
        return 1.0 if pe == 0 else 1.0 - po / pe
    po = sum(observed[i][i] for i in range(k))
    pe = sum(pa[i] * pb[i] for i in range(k))
    return 1.0 if pe >= 1.0 else (po - pe) / (1.0 - pe)


def _bootstrap_kappa(a: list[str], b: list[str], labels: list[str], *, weighted: bool, seed: int = SEED,
                     resamples: int = BOOTSTRAP) -> tuple[float, float] | None:
    n = len(a)
    if n < 2:
        return None
    rng = random.Random(seed)
    values = []
    for _ in range(resamples):
        picks = [rng.randrange(n) for _ in range(n)]
        value = cohen_kappa([a[i] for i in picks], [b[i] for i in picks], labels, weighted=weighted)
        if value is not None:
            values.append(value)
    values.sort()
    return values[int(0.025 * len(values))], values[min(len(values) - 1, int(0.975 * len(values)))]


def _read_rating(path: str) -> dict[str, dict]:
    with open(path, encoding="utf-8-sig", newline="") as fh:
        rows = list(csv.DictReader(fh))
    return {r["public_signal_id"].strip(): r for r in rows if r.get("public_signal_id", "").strip()}


def agreement(a_path: str, b_path: str, *, out_dir: str | None = None) -> dict:
    a, b = _read_rating(a_path), _read_rating(b_path)
    ids = sorted(set(a) & set(b))
    report: dict[str, dict] = {"n_common_ids": len(ids), "fields": {}}
    disagreements: list[dict] = []
    for field in FIELDS:
        pairs = []
        for signal_id in ids:
            x, y = _norm(a[signal_id].get(field)), _norm(b[signal_id].get(field))
            if x and y:
                pairs.append((signal_id, x, y))
        labels = CLOSED.get(field) or sorted({x for _, x, _ in pairs} | {y for _, _, y in pairs})
        invalid = [(i, x, y) for i, x, y in pairs if x not in labels or y not in labels]
        pairs = [p for p in pairs if p not in invalid]
        xs, ys = [x for _, x, _ in pairs], [y for _, _, y in pairs]
        entry: dict = {"n": len(pairs), "n_invalid_dropped": len(invalid),
                       "exact_agreement": round(sum(x == y for x, y in zip(xs, ys)) / len(pairs), 4) if pairs else None}
        kappa = cohen_kappa(xs, ys, labels)
        entry["kappa"] = None if kappa is None else round(kappa, 4)
        ci = _bootstrap_kappa(xs, ys, labels, weighted=False)
        entry["kappa_ci95"] = [round(ci[0], 4), round(ci[1], 4)] if ci else None
        if field in ("risk", "urgency"):
            kw = cohen_kappa(xs, ys, labels, weighted=True)
            entry["kappa_linear_weighted"] = None if kw is None else round(kw, 4)
            ciw = _bootstrap_kappa(xs, ys, labels, weighted=True)
            entry["kappa_linear_weighted_ci95"] = [round(ciw[0], 4), round(ciw[1], 4)] if ciw else None
        report["fields"][field] = entry
        for signal_id, x, y in pairs:
            if x != y:
                disagreements.append({"field": field, "public_signal_id": signal_id,
                                      "text": a[signal_id].get("text", ""), "rater_a": x, "rater_b": y,
                                      "adjudicated": ""})
    report["n_disagreements"] = len(disagreements)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
        with open(os.path.join(out_dir, "agreement.json"), "w", encoding="utf-8") as fh:
            json.dump(report, fh, indent=2)
        with open(os.path.join(out_dir, "disagreements.csv"), "w", encoding="utf-8", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=["field", "public_signal_id", "text", "rater_a", "rater_b", "adjudicated"])
            writer.writeheader()
            writer.writerows(disagreements)
    return report


# ------------------------------------------------------------------------ adjudicate

def adjudicate(a_path: str, b_path: str, adjudication_path: str, *, out_path: str) -> dict:
    a, b = _read_rating(a_path), _read_rating(b_path)
    with open(adjudication_path, encoding="utf-8-sig", newline="") as fh:
        adjudicated = {(r["field"], r["public_signal_id"].strip()): _norm(r.get("adjudicated")) for r in csv.DictReader(fh)}
    ids = sorted(set(a) & set(b))
    inv_path = os.path.join(os.path.dirname(os.path.abspath(a_path)), "inventories.json")
    inv = json.load(open(inv_path, encoding="utf-8")) if os.path.exists(inv_path) else {}
    rows: list[dict] = []
    counts = {field: {"agreed": 0, "adjudicated": 0, "missing": 0} for field in FIELDS}
    problems: list[str] = []
    for signal_id in ids:
        row = {"public_signal_id": signal_id}
        for field in FIELDS:
            x, y = _norm(a[signal_id].get(field)), _norm(b[signal_id].get(field))
            if not x or not y:
                counts[field]["missing"] += 1
                row[field] = ""
                continue
            if x == y:
                counts[field]["agreed"] += 1
                row[field] = x
                continue
            value = adjudicated.get((field, signal_id), "")
            vocab = CLOSED.get(field) or inv.get(field) or []
            if not value:
                problems.append(f"{field}/{signal_id}: raters disagree ({x} vs {y}) and no adjudication is recorded")
                row[field] = ""
                continue
            if vocab and value not in vocab and value != "other":
                problems.append(f"{field}/{signal_id}: adjudicated value {value!r} is not in the vocabulary")
                row[field] = ""
                continue
            counts[field]["adjudicated"] += 1
            row[field] = value
        rows.append(row)
    if problems:
        raise SystemExit("adjudication incomplete:\n  " + "\n  ".join(problems))
    with open(out_path, "w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=["public_signal_id", *FIELDS])
        writer.writeheader()
        writer.writerows(rows)
    meta = {
        "built_at": datetime.now(UTC).isoformat(),
        "n": len(rows),
        "counts": counts,
        "sources": {"rater_a": {"path": os.path.basename(a_path), "sha256": _sha256(a_path)},
                    "rater_b": {"path": os.path.basename(b_path), "sha256": _sha256(b_path)},
                    "adjudication": {"path": os.path.basename(adjudication_path), "sha256": _sha256(adjudication_path)}},
        "evidence_type": "human labels: two independent raters with adjudication (provenance records per rater required)",
    }
    with open(out_path[:-4] + ".meta.json" if out_path.endswith(".csv") else out_path + ".meta.json", "w", encoding="utf-8") as fh:
        json.dump(meta, fh, indent=2)
    return meta


# --------------------------------------------------------------------------- rescore

def _load_predictions(path: str) -> dict[str, dict]:
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    if isinstance(data, list):
        out: dict[str, dict] = {}
        for item in data:
            signal_id = str(item.get("id") or "").strip()
            if signal_id and signal_id not in out:
                out[signal_id] = item
        return out
    if isinstance(data, dict):  # {task: {id: label}}
        out = {}
        for task, mapping in data.items():
            if not isinstance(mapping, dict):
                continue
            for signal_id, label in mapping.items():
                out.setdefault(str(signal_id), {})[task] = label
        return out
    raise SystemExit(f"{path}: unrecognised prediction file shape")


RETRAIN_FIELDS = ("sentiment", "risk")
RETRAINED = "ml_retrained"
MIN_PER_CLASS = 5


def _retrain(field: str, gold_items: dict[str, str], texts: dict[str, str], *, min_per_class: int) -> dict:
    """Out-of-fold predictions of the learned baseline retrained on the human gold for one field.

    Returns the accuracy row pieces and the per-item correctness map. ml_baseline
    (scikit-learn) is imported here, not at module level, so the kit's other commands
    never need it.
    """
    import ml_baseline  # lazy on purpose: only the retrain path needs scikit-learn

    ids = [signal_id for signal_id in gold_items if texts.get(signal_id)]
    n_absent = len(gold_items) - len(ids)
    labels = [gold_items[i] for i in ids]
    eligible = {label for label, count in Counter(labels).items() if count >= min_per_class}
    if len(eligible) < 2:
        return {"n_valid": 0, "n_absent": len(gold_items), "scored": {}, "correct": {}, "folds": 0,
                "note": f"not retrained: fewer than two classes reach --min-per-class {min_per_class} on the human gold"}
    kept_labels, preds, k, kept_idx = ml_baseline.cv_predict([texts[i] for i in ids], labels, min_per_class=min_per_class)
    kept_ids = [ids[i] for i in kept_idx]
    n_absent += len(ids) - len(kept_ids)  # items of classes too rare for the folds get no prediction
    correct = {i: t == p for i, t, p in zip(kept_ids, kept_labels, preds)}
    return {"n_valid": len(kept_ids), "n_absent": n_absent, "scored": M.score(kept_labels, list(preds), CLOSED[field]),
            "correct": correct, "folds": k,
            "note": (f"TF-IDF + logistic regression retrained on the human gold: {k} stratified folds formed on "
                     f"the human gold (not the seed labels), min {min_per_class} items per class; out-of-fold predictions")}


def rescore(gold_path: str, *, out_dir: str, predictions: dict[str, str] | None = None,
            retrain_ml: bool = False, min_per_class: int = MIN_PER_CLASS) -> dict:
    sources = dict(DEFAULT_PREDICTIONS)
    if predictions:
        sources.update(predictions)
    available = {label: _load_predictions(path) for label, path in sources.items() if os.path.exists(path)}
    gold = _read_rating(gold_path)
    texts = {s.id: s.text for s in load() if s.text} if retrain_ml else {}
    retrained: dict[str, dict] = {}
    acc_rows: list[dict] = []
    pair_rows: list[dict] = []
    for field in FIELDS:
        gold_items = {signal_id: _norm(row.get(field)) for signal_id, row in gold.items() if _norm(row.get(field))}
        if not gold_items:
            continue
        vocab = CLOSED.get(field)
        correct_by_predictor: dict[str, dict[str, bool]] = {}
        if retrain_ml and field in RETRAIN_FIELDS:
            result = _retrain(field, gold_items, texts, min_per_class=min_per_class)
            retrained[field] = {"n_valid": result["n_valid"], "folds": result["folds"], "note": result["note"]}
            scored = result["scored"]
            acc_rows.append({
                "field": field, "predictor": RETRAINED, "n_gold": len(gold_items), "n_valid": result["n_valid"],
                "n_invalid": 0, "n_absent": result["n_absent"],
                "accuracy": scored.get("accuracy", ""), "accuracy_ci_low": scored.get("accuracy_ci_low", ""),
                "accuracy_ci_high": scored.get("accuracy_ci_high", ""), "f1_macro": scored.get("f1_macro", ""),
                "accuracy_end_to_end": round(sum(result["correct"].values()) / len(gold_items), 4),
                "note": result["note"],
            })
            if result["correct"]:
                correct_by_predictor[RETRAINED] = result["correct"]
        for predictor, key in FIELD_SOURCES[field].items():
            preds = available.get(predictor)
            if preds is None:
                continue
            y_true, y_pred, valid_ids = [], [], []
            n_invalid = n_absent = 0
            for signal_id, truth in gold_items.items():
                item = preds.get(signal_id)
                value = _norm(item.get(key)) if item else ""
                if not item or not value:
                    n_absent += 1
                    continue
                if vocab and value not in vocab:
                    n_invalid += 1
                    continue
                y_true.append(truth)
                y_pred.append(value)
                valid_ids.append(signal_id)
            correct = sum(t == p for t, p in zip(y_true, y_pred))
            scored = M.score(y_true, y_pred, vocab) if y_true else {}
            acc_rows.append({
                "field": field, "predictor": predictor, "n_gold": len(gold_items), "n_valid": len(y_true),
                "n_invalid": n_invalid, "n_absent": n_absent,
                "accuracy": scored.get("accuracy", ""), "accuracy_ci_low": scored.get("accuracy_ci_low", ""),
                "accuracy_ci_high": scored.get("accuracy_ci_high", ""), "f1_macro": scored.get("f1_macro", ""),
                "accuracy_end_to_end": round(correct / len(gold_items), 4),
                "note": "",
            })
            correct_by_predictor[predictor] = {i: t == p for i, t, p in zip(valid_ids, y_true, y_pred)}
        for first, second in combinations(correct_by_predictor, 2):
            common = sorted(set(correct_by_predictor[first]) & set(correct_by_predictor[second]))
            b = sum(1 for i in common if correct_by_predictor[first][i] and not correct_by_predictor[second][i])
            c = sum(1 for i in common if correct_by_predictor[second][i] and not correct_by_predictor[first][i])
            pair_rows.append({"field": field, "pair": f"{first}_vs_{second}", "n_pairs": len(common),
                              "b_first_only_correct": b, "c_second_only_correct": c,
                              "p_exact_two_sided": M.mcnemar_p_from_counts(b, c) if common else ""})
    os.makedirs(out_dir, exist_ok=True)
    for name, rows, cols in (
        ("human_gold_accuracy.csv", acc_rows, ["field", "predictor", "n_gold", "n_valid", "n_invalid", "n_absent", "accuracy",
                                               "accuracy_ci_low", "accuracy_ci_high", "f1_macro", "accuracy_end_to_end", "note"]),
        ("human_gold_pairs.csv", pair_rows, ["field", "pair", "n_pairs", "b_first_only_correct", "c_second_only_correct",
                                             "p_exact_two_sided"]),
    ):
        with open(os.path.join(out_dir, name), "w", encoding="utf-8", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=cols)
            writer.writeheader()
            writer.writerows(rows)
    summary = {"gold": os.path.basename(gold_path), "gold_sha256": _sha256(gold_path),
               "predictions_scored": {label: os.path.relpath(path, HERE) for label, path in sources.items() if label in available},
               "n_accuracy_rows": len(acc_rows), "n_pair_rows": len(pair_rows),
               "evidence_type": "model predictions (committed files, no rerun) against human-adjudicated labels"}
    if retrain_ml:
        summary["ml_retrained"] = {"fields": list(RETRAIN_FIELDS), "min_per_class": min_per_class, "per_field": retrained,
                                   "evidence_type": "learned baseline retrained on the human gold, scored out of fold; "
                                                    "folds formed on the human gold, not on the seed labels"}
    with open(os.path.join(out_dir, "human_gold_summary.json"), "w", encoding="utf-8") as fh:
        json.dump(summary, fh, indent=2)
    return summary


# ------------------------------------------------------------------------------ cli

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    d = sub.add_parser("draw")
    d.add_argument("--raters", required=True, help="comma-separated rater tags, e.g. A,B")
    d.add_argument("--n", type=int, default=0, help="draw a random subset of this size (default: the whole corpus)")
    d.add_argument("--seed", type=int, default=SEED)
    d.add_argument("--out", default=os.path.join(RESULTS, "annotation"))
    g = sub.add_parser("agreement")
    g.add_argument("rater_a")
    g.add_argument("rater_b")
    g.add_argument("--out", default=None, help="directory for agreement.json and disagreements.csv (default: the raters' folder)")
    j = sub.add_parser("adjudicate")
    j.add_argument("rater_a")
    j.add_argument("rater_b")
    j.add_argument("adjudication", help="disagreements.csv with the adjudicated column filled")
    j.add_argument("--out", required=True, help="gold_human.csv to write")
    r = sub.add_parser("rescore")
    r.add_argument("gold")
    r.add_argument("--out", default=os.path.join(RESULTS, "human_gold"))
    r.add_argument("--predictions", action="append", default=[], help="label=path (overrides or adds a source)")
    r.add_argument("--retrain-ml", action="store_true",
                   help="also retrain TF-IDF + logistic regression on the human gold (sentiment and risk), scored out of fold")
    r.add_argument("--min-per-class", type=int, default=MIN_PER_CLASS,
                   help=f"smallest class the retrained model's stratified folds admit (default {MIN_PER_CLASS})")
    args = parser.parse_args(argv)

    if args.command == "draw":
        manifest = draw([t.strip() for t in args.raters.split(",") if t.strip()], n=args.n, seed=args.seed, out_dir=args.out)
        print(f"drew {manifest['n']} signals for raters {', '.join(manifest['raters'])} -> {args.out} (labels withheld)")
    elif args.command == "agreement":
        out_dir = args.out or os.path.dirname(os.path.abspath(args.rater_a))
        report = agreement(args.rater_a, args.rater_b, out_dir=out_dir)
        for field, entry in report["fields"].items():
            print(f"{field:<14} n={entry['n']:<4} agreement={entry['exact_agreement']} kappa={entry['kappa']} "
                  f"ci={entry['kappa_ci95']}" + (f" weighted={entry['kappa_linear_weighted']}" if "kappa_linear_weighted" in entry else ""))
        print(f"{report['n_disagreements']} disagreements -> {os.path.join(out_dir, 'disagreements.csv')}")
    elif args.command == "adjudicate":
        meta = adjudicate(args.rater_a, args.rater_b, args.adjudication, out_path=args.out)
        print(f"wrote {args.out}: {meta['n']} rows; per field {meta['counts']}")
    elif args.command == "rescore":
        overrides = dict(spec.split("=", 1) for spec in args.predictions)
        summary = rescore(args.gold, out_dir=args.out, predictions=overrides or None,
                          retrain_ml=args.retrain_ml, min_per_class=args.min_per_class)
        print(f"scored {summary['n_accuracy_rows']} predictor/field rows and {summary['n_pair_rows']} pairs -> {args.out}")
        for field, entry in summary.get("ml_retrained", {}).get("per_field", {}).items():
            print(f"{RETRAINED} {field}: n={entry['n_valid']} folds={entry['folds']}; {entry['note']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
