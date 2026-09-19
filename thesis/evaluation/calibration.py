"""Calibration and abstention read of a probability-bearing predictor run (predict_jev.py).

The generation-based predictors in the harness return a label and nothing else. A
predictor that returns a distribution can be asked two further questions that matter
for a governed pipeline: is its confidence honest (calibration), and what does it cost
to let it abstain below a confidence threshold and route those items to a person
(coverage against accuracy)? This module answers both from the sidecar that
predict_jev.py writes, with no model call and no corpus load: the sidecar carries the
gold label the harness knows for every item.

    python3 calibration.py --sidecar results/jev_probabilities.json --out results/

Writes, each with a header even when no row qualifies:

    jev_calibration.csv     per task and stratum: n, accuracy (Wilson 95 %), expected
                            calibration error (ECE, equal-width bins on the top
                            probability), Brier score, log loss, mean confidence and the
                            confidence-minus-accuracy gap
    jev_reliability.csv     the bins behind the ECE: bin, n, mean confidence, accuracy
    jev_coverage_curve.csv  per task and stratum and threshold: coverage, accuracy on the
                            covered items, end-to-end accuracy (abstentions count as wrong)
    jev_escalation.csv      the high-or-critical boundary per stratum, from the Noul
                            probability and from the risk Choice (P(high) + P(critical)):
                            recall and precision at 0.5, Brier, ECE

Strata are `all` and each language with at least MIN_SLICE items, the harness-wide slice
minimum. Definitions: ECE = sum over bins of (n_bin / n) * |accuracy_bin - confidence_bin|
(Naeini et al., 2015; Guo et al., 2017); multiclass Brier = sum over classes of
(p_k - 1[k = gold])^2; log loss = -ln p(gold), p clipped at 1e-6. The Score answer
(`risk_level`) is read at its most probable level; its mean absolute level error is also
reported because an ordered scale is judged by distance, not only by exact hits.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import os
import sys
from collections import Counter, defaultdict
from typing import Any

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from metrics import wilson_interval

MIN_SLICE = 5
DEFAULT_BINS = 10
DEFAULT_THRESHOLDS = [0.0, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 0.95]
EPS = 1e-6

CAL_COLS = ["task", "stratum", "n", "n_classes", "majority_floor", "accuracy", "accuracy_ci_low",
            "accuracy_ci_high", "ece", "brier", "log_loss", "mean_confidence", "confidence_minus_accuracy",
            "level_mae", "note"]
REL_COLS = ["task", "stratum", "bin_low", "bin_high", "n", "confidence_mean", "accuracy"]
COV_COLS = ["task", "stratum", "threshold", "n", "n_covered", "coverage", "accuracy_covered",
            "accuracy_covered_ci_low", "accuracy_covered_ci_high", "accuracy_end_to_end"]
ESC_COLS = ["source", "stratum", "n", "n_gold_escalate", "base_rate", "threshold", "recall",
            "recall_ci_low", "recall_ci_high", "precision", "brier", "ece", "note"]


# ---------------------------------------------------------------------------
# Pure metric helpers
# ---------------------------------------------------------------------------
def reliability_bins(confidences: list[float], correct: list[bool], n_bins: int = DEFAULT_BINS) -> list[dict]:
    """Equal-width bins over (0, 1]; a confidence of exactly 0 lands in the first bin."""
    if n_bins < 1:
        raise ValueError("n_bins must be at least 1")
    sums = [[0, 0.0, 0] for _ in range(n_bins)]  # n, confidence sum, correct count
    for conf, ok in zip(confidences, correct):
        idx = min(n_bins - 1, max(0, math.ceil(conf * n_bins) - 1))
        sums[idx][0] += 1
        sums[idx][1] += conf
        sums[idx][2] += 1 if ok else 0
    rows = []
    for i, (n, conf_sum, n_ok) in enumerate(sums):
        rows.append({"bin_low": round(i / n_bins, 4), "bin_high": round((i + 1) / n_bins, 4), "n": n,
                     "confidence_mean": round(conf_sum / n, 4) if n else None,
                     "accuracy": round(n_ok / n, 4) if n else None})
    return rows


def ece(confidences: list[float], correct: list[bool], n_bins: int = DEFAULT_BINS) -> float | None:
    n = len(confidences)
    if n == 0:
        return None
    total = 0.0
    for row in reliability_bins(confidences, correct, n_bins):
        if row["n"]:
            total += row["n"] / n * abs(row["accuracy"] - row["confidence_mean"])
    return round(total, 4)


def brier(probabilities: dict[str, float], gold: str) -> float:
    """Multiclass Brier score of one distribution against one gold label. A gold label
    outside the distribution's keys counts as a class with probability 0."""
    keys = set(probabilities) | {gold}
    return sum((float(probabilities.get(k, 0.0)) - (1.0 if k == gold else 0.0)) ** 2 for k in keys)


def log_loss(p_gold: float) -> float:
    return -math.log(max(EPS, min(1.0, float(p_gold))))


def coverage_curve(confidences: list[float], correct: list[bool],
                   thresholds: list[float] = DEFAULT_THRESHOLDS) -> list[dict]:
    """For each threshold: cover the items whose confidence is at least the threshold."""
    n = len(confidences)
    rows = []
    for t in thresholds:
        covered = [ok for conf, ok in zip(confidences, correct) if conf >= t]
        n_cov = len(covered)
        n_ok = sum(1 for ok in covered if ok)
        lo, hi = wilson_interval(n_ok, n_cov) if n_cov else (None, None)
        rows.append({"threshold": t, "n": n, "n_covered": n_cov,
                     "coverage": round(n_cov / n, 4) if n else None,
                     "accuracy_covered": round(n_ok / n_cov, 4) if n_cov else None,
                     "accuracy_covered_ci_low": lo, "accuracy_covered_ci_high": hi,
                     "accuracy_end_to_end": round(n_ok / n, 4) if n else None})
    return rows


# ---------------------------------------------------------------------------
# Reading one sidecar record into scored observations per task
# ---------------------------------------------------------------------------
def _level_name(legend: dict, key: str) -> str:
    return str(legend.get(key, key)).split(":")[0].strip()


def observation(answer: dict | None, gold: Any) -> dict | None:
    """One scored observation: predicted label, confidence, correctness, p(gold), Brier,
    and for a Score the absolute level error. None when the answer or the gold is unusable."""
    if not isinstance(answer, dict) or gold is None:
        return None
    kind = answer.get("type")
    try:
        if kind == "choice":
            probs = {str(k): float(v) for k, v in (answer.get("probabilities") or {}).items()}
            if not probs:
                return None
            pred = str(answer.get("choice", max(probs, key=probs.get)))
            conf = float(answer.get("confidence", probs.get(pred, 0.0)))
            return {"pred": pred, "confidence": conf, "correct": pred == str(gold), "gold": str(gold),
                    "p_gold": probs.get(str(gold), 0.0), "brier": brier(probs, str(gold))}
        if kind == "score":
            probs = {str(k): float(v) for k, v in (answer.get("probabilities") or {}).items()}
            if not probs:
                return None
            legend = answer.get("legend") or {}
            top = max(probs, key=probs.get)
            named = {_level_name(legend, k): p for k, p in probs.items()}
            pred = _level_name(legend, top)
            gold_keys = [k for k in probs if _level_name(legend, k) == str(gold)]
            level_err = None
            if gold_keys and "score" in answer:
                level_err = abs(float(answer["score"]) - int(gold_keys[0]))
            return {"pred": pred, "confidence": probs[top], "correct": pred == str(gold), "gold": str(gold),
                    "p_gold": named.get(str(gold), 0.0), "brier": brier(named, str(gold)),
                    "level_error": level_err}
        if kind == "noul":
            p = float(answer["noul"])
            truth = bool(gold)
            pred = p >= 0.5
            return {"pred": "true" if pred else "false", "confidence": max(p, 1.0 - p), "correct": pred == truth,
                    "p_gold": p if truth else 1.0 - p, "brier": (p - (1.0 if truth else 0.0)) ** 2,
                    "p_true": p, "gold_true": truth}
    except (KeyError, TypeError, ValueError):
        return None
    return None


def collect(records: list[dict]) -> dict[str, list[dict]]:
    """{task: [observation + language]} over every record with a usable answer and gold."""
    by_task: dict[str, list[dict]] = defaultdict(list)
    for rec in records:
        gold = rec.get("gold") or {}
        for task, answer in (rec.get("answers") or {}).items():
            obs = observation(answer, gold.get(task))
            if obs is None:
                continue
            obs["language"] = (rec.get("language") or "").lower()
            obs["id"] = rec.get("id")
            by_task[task].append(obs)
        # The high-or-critical boundary read off the risk Choice, for comparison with the Noul.
        risk = (rec.get("answers") or {}).get("risk")
        if isinstance(risk, dict) and risk.get("type") == "choice" and gold.get("risk") is not None:
            probs = {str(k): float(v) for k, v in (risk.get("probabilities") or {}).items()}
            p_esc = probs.get("high", 0.0) + probs.get("critical", 0.0)
            truth = str(gold["risk"]) in {"high", "critical"}
            by_task["escalate_from_risk_choice"].append({
                "id": rec.get("id"), "language": (rec.get("language") or "").lower(),
                "pred": "true" if p_esc >= 0.5 else "false", "confidence": max(p_esc, 1.0 - p_esc),
                "correct": (p_esc >= 0.5) == truth, "p_gold": p_esc if truth else 1.0 - p_esc,
                "brier": (p_esc - (1.0 if truth else 0.0)) ** 2, "p_true": p_esc, "gold_true": truth})
    return dict(by_task)


def strata(observations: list[dict]) -> list[tuple[str, list[dict]]]:
    out = [("all", observations)]
    by_lang: dict[str, list[dict]] = defaultdict(list)
    for obs in observations:
        if obs.get("language"):
            by_lang[obs["language"]].append(obs)
    for lang in sorted(by_lang):
        if len(by_lang[lang]) >= MIN_SLICE:
            out.append((lang, by_lang[lang]))
    return out


def analyse(records: list[dict], *, n_bins: int = DEFAULT_BINS,
            thresholds: list[float] = DEFAULT_THRESHOLDS) -> dict[str, list[dict]]:
    by_task = collect(records)
    cal, rel, cov, esc = [], [], [], []
    for task in sorted(by_task):
        if task in ("escalate", "escalate_from_risk_choice"):
            continue
        for stratum, obs in strata(by_task[task]):
            confs = [o["confidence"] for o in obs]
            oks = [o["correct"] for o in obs]
            n = len(obs)
            n_ok = sum(oks)
            lo, hi = wilson_interval(n_ok, n)
            level_errors = [o["level_error"] for o in obs if o.get("level_error") is not None]
            gold_counts = Counter(o.get("gold") for o in obs)
            cal.append({"task": task, "stratum": stratum, "n": n, "n_classes": len(gold_counts),
                        # the share of the most common gold label: accuracy over a 27- or
                        # 51-class routing inventory means nothing without this floor
                        "majority_floor": round(max(gold_counts.values()) / n, 4),
                        "accuracy": round(n_ok / n, 4), "accuracy_ci_low": lo, "accuracy_ci_high": hi,
                        "ece": ece(confs, oks, n_bins),
                        "brier": round(sum(o["brier"] for o in obs) / n, 4),
                        "log_loss": round(sum(log_loss(o["p_gold"]) for o in obs) / n, 4),
                        "mean_confidence": round(sum(confs) / n, 4),
                        "confidence_minus_accuracy": round(sum(confs) / n - n_ok / n, 4),
                        "level_mae": round(sum(level_errors) / len(level_errors), 4) if level_errors else None,
                        "note": "" if n >= 30 else "n below 30: read the interval, not the point"})
            for row in reliability_bins(confs, oks, n_bins):
                rel.append({"task": task, "stratum": stratum, **row})
            for row in coverage_curve(confs, oks, thresholds):
                cov.append({"task": task, "stratum": stratum, **row})
    for source in ("escalate", "escalate_from_risk_choice"):
        for stratum, obs in strata(by_task.get(source, [])):
            n = len(obs)
            if not n:
                continue
            gold_true = [o for o in obs if o.get("gold_true")]
            hits = [o for o in gold_true if o["pred"] == "true"]
            flagged = [o for o in obs if o["pred"] == "true"]
            r_lo, r_hi = wilson_interval(len(hits), len(gold_true)) if gold_true else (None, None)
            esc.append({"source": source, "stratum": stratum, "n": n, "n_gold_escalate": len(gold_true),
                        "base_rate": round(len(gold_true) / n, 4) if n else None, "threshold": 0.5,
                        "recall": round(len(hits) / len(gold_true), 4) if gold_true else None,
                        "recall_ci_low": r_lo, "recall_ci_high": r_hi,
                        "precision": round(len(hits) / len(flagged), 4) if flagged else None,
                        "brier": round(sum(o["brier"] for o in obs) / n, 4) if n else None,
                        "ece": ece([o["confidence"] for o in obs], [o["correct"] for o in obs], n_bins),
                        "note": "" if gold_true else "no gold escalation in this stratum"})
    return {"calibration": cal, "reliability": rel, "coverage": cov, "escalation": esc}


def _write(path: str, rows: list[dict], columns: list[str]) -> None:
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=columns, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def _print(rows: list[dict], columns: list[str]) -> None:
    if not rows:
        print("  (no rows)")
        return
    widths = {c: max(len(c), *(len(str(r.get(c, ""))) for r in rows)) for c in columns}
    print("  ".join(c.ljust(widths[c]) for c in columns))
    for r in rows:
        print("  ".join(str(r.get(c, "")).ljust(widths[c]) for c in columns))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--sidecar", required=True, help="jev_probabilities*.json from predict_jev.py")
    parser.add_argument("--out", default=os.path.join(HERE, "results"))
    parser.add_argument("--bins", type=int, default=DEFAULT_BINS)
    parser.add_argument("--thresholds", default=",".join(str(t) for t in DEFAULT_THRESHOLDS))
    parser.add_argument("--prefix", default="jev", help="file-name prefix for the four tables")
    args = parser.parse_args(argv)
    with open(args.sidecar, encoding="utf-8") as fh:
        data = json.load(fh)
    records = data["records"] if isinstance(data, dict) else data
    thresholds = [float(t) for t in args.thresholds.split(",") if t.strip()]
    tables = analyse(records, n_bins=args.bins, thresholds=thresholds)
    os.makedirs(args.out, exist_ok=True)
    files = {"calibration": CAL_COLS, "reliability": REL_COLS, "coverage": COV_COLS, "escalation": ESC_COLS}
    for name, cols in files.items():
        _write(os.path.join(args.out, f"{args.prefix}_{name if name != 'coverage' else 'coverage_curve'}.csv"),
               tables[name], cols)
    meta = data.get("meta") if isinstance(data, dict) else {}
    print(f"sidecar: {len(records)} records; client {meta.get('client', '?')}")
    print("\n== calibration per task and stratum ==")
    _print(tables["calibration"], CAL_COLS)
    print("\n== coverage against accuracy ==")
    _print(tables["coverage"], COV_COLS)
    print("\n== escalation boundary ==")
    _print(tables["escalation"], ESC_COLS)
    print(f"\nwrote {args.prefix}_calibration.csv, {args.prefix}_reliability.csv, "
          f"{args.prefix}_coverage_curve.csv, {args.prefix}_escalation.csv -> {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
