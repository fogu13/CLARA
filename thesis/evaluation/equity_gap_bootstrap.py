"""Between-predictor comparison of the DE/EN escalation-recall gap (§5A.5, review R2).

STATUS. This module was written on 12 September 2026 and has NOT been run on the thesis
corpus in that pass: the corpus lives outside the repository (THESIS_DATA_DIR, the
`Thesis_ChatGPT` datasets) and was absent from the environment in which the module was
written. The synthetic self-test (`test_equity_gap_bootstrap.py`) exercises every code
path; no figure from this module appears in the manuscript. The owner must run:

    cd thesis/evaluation
    THESIS_DATA_DIR=/path/to/Thesis_ChatGPT python3 equity_gap_bootstrap.py
    # optionally THESIS_RESULTS_DIR=... (defaults to ./results)

which writes results/equity_gap_pairs.csv and results/equity_gap_pairs.json, and then
quote the difference-of-gaps interval and permutation p in §5A.5 in place of the
"had not been run" sentence. The output is the statistic that a comparison BETWEEN
predictors' stratum gaps needs; §5A.5's per-predictor Fisher tests are within-predictor
only (Gelman & Stern, 2006).

WHAT IS COMPUTED. For each predictor P, on the gold-escalate items (seed risk label
high or critical, an assistant-drafted reference, §3.7) of the two source-language strata
(de, en), the escalation recall per stratum and the gap
    gap_P = recall_en(P) - recall_de(P)          (positive: DE-source under-escalated).
For each ordered predictor pair (A, B), the difference of gaps D = gap_A - gap_B, with
  (1) a paired item-level bootstrap: gold-escalate items are resampled with replacement
      WITHIN each stratum (8 DE items among DE, 41 EN among EN), each resampled item
      carrying both predictors' hits, so the pairing is preserved; fixed seed, 5000
      resamples, percentile 95% interval on D; and
  (2) an exact permutation test: the same item is scored by both predictors, so under the
      null of exchangeable predictor assignment each item's two hit values may be swapped.
      Only discordant items (hit under exactly one predictor) move D; a swap on an EN item
      changes D by +/-2/n_en and on a DE item by -/+2/n_de, so the null distribution is the
      convolution of two binomials, Bin(k_en, 1/2) and Bin(k_de, 1/2), enumerated exactly.
      Two-sided p = P(|D*| >= |D_obs|).

PREDICTORS. floor = keyword severity recomputed from the text (baseline.predict_risk, the
same code run_eval.py uses); ml = results/predictions_ml.json ["risk"]; llm =
results/predictions_llm.json (the 4 August generic-prompt run); llm_production =
results/predictions_llm_production.json (the 5 September production-stage run on the
model named in its .meta.json). Every prediction file goes through
prediction_validation.validate_predictions exactly as run_eval.equity_slices does
(first row per id wins, a label outside the risk vocabulary is invalid, never a
miss), so an item with no VALID prediction is dropped from the pairs that involve
that predictor — out of the recall denominator — and the drop is reported.

EVIDENCE TYPES. Gold: AI-generated seed labels. Predictions: model outputs. This is a
model comparison on a reference that is not human-labelled; it says nothing about
German-text processing (texts are English paraphrases) and nothing about parity in
general (§5A.5).
"""
from __future__ import annotations

import csv
import json
import math
import os
import random
import sys
from math import comb

HERE = os.path.dirname(os.path.abspath(__file__))
RESULTS = os.environ.get("THESIS_RESULTS_DIR") or os.path.join(HERE, "results")
STRATA = ("de", "en")
ESCALATE = ("high", "critical")
SEED = 20260912
RESAMPLES = 5000

try:  # metrics.py imports scikit-learn at module level; fall back to the same formula.
    from metrics import wilson_interval  # type: ignore
except Exception:  # pragma: no cover - exercised only where scikit-learn is absent
    def wilson_interval(successes: int, n: int, z: float = 1.959964) -> tuple[float, float]:
        """Wilson score interval (identical to metrics.wilson_interval)."""
        if n <= 0:
            return (0.0, 0.0)
        p = successes / n
        z2 = z * z
        denom = 1.0 + z2 / n
        centre = (p + z2 / (2 * n)) / denom
        half = z * math.sqrt(p * (1 - p) / n + z2 / (4 * n * n)) / denom
        return (round(max(0.0, centre - half), 4), round(min(1.0, centre + half), 4))


# --------------------------------------------------------------------------
# pure computation (no corpus, no files): the test targets these
# --------------------------------------------------------------------------
def stratum_recall(items: list[dict], predictor: str) -> dict:
    """Per-stratum recall of `predictor` on gold-escalate items.

    `items` are dicts {"id", "language", "hits": {predictor: bool}}; every item is a
    gold-escalate item. Items whose `hits` lacks the predictor are skipped and counted.
    """
    out = {}
    for lang in STRATA:
        scored = [it for it in items if it["language"] == lang and predictor in it["hits"]]
        k = sum(1 for it in scored if it["hits"][predictor])
        n = len(scored)
        lo, hi = wilson_interval(k, n)
        out[lang] = {"n": n, "hits": k, "recall": round(k / n, 4) if n else None,
                     "ci_low": lo, "ci_high": hi,
                     "n_missing": sum(1 for it in items if it["language"] == lang) - n}
    return out


def gap(items: list[dict], predictor: str) -> float | None:
    r = stratum_recall(items, predictor)
    if not r["en"]["n"] or not r["de"]["n"]:
        return None
    return r["en"]["hits"] / r["en"]["n"] - r["de"]["hits"] / r["de"]["n"]


def _paired(items: list[dict], a: str, b: str) -> list[dict]:
    return [it for it in items if a in it["hits"] and b in it["hits"]]


def diff_of_gaps(items: list[dict], a: str, b: str) -> float | None:
    p = _paired(items, a, b)
    ga, gb = gap(p, a), gap(p, b)
    if ga is None or gb is None:
        return None
    return ga - gb


def bootstrap_diff(items: list[dict], a: str, b: str, resamples: int = RESAMPLES,
                   seed: int = SEED) -> dict:
    """Paired item-level bootstrap of D = gap_a - gap_b, resampling within stratum."""
    p = _paired(items, a, b)
    by_lang = {lang: [it for it in p if it["language"] == lang] for lang in STRATA}
    if any(not v for v in by_lang.values()):
        return {"n_resamples": 0, "ci_low": None, "ci_high": None, "note": "empty stratum"}
    rng = random.Random(seed)
    draws = []
    for _ in range(resamples):
        d = 0.0
        for lang, sign in (("en", 1.0), ("de", -1.0)):
            pool = by_lang[lang]
            n = len(pool)
            sample = [pool[rng.randrange(n)] for _ in range(n)]
            ra = sum(1 for it in sample if it["hits"][a]) / n
            rb = sum(1 for it in sample if it["hits"][b]) / n
            d += sign * (ra - rb)
        draws.append(d)
    draws.sort()
    lo_i = int(math.floor(0.025 * (resamples - 1)))
    hi_i = int(math.ceil(0.975 * (resamples - 1)))
    return {"n_resamples": resamples, "seed": seed,
            "ci_low": round(draws[lo_i], 4), "ci_high": round(draws[hi_i], 4)}


def permutation_exact(items: list[dict], a: str, b: str) -> dict:
    """Exact two-sided permutation p for D under within-item swaps of predictor labels."""
    p = _paired(items, a, b)
    n = {lang: sum(1 for it in p if it["language"] == lang) for lang in STRATA}
    if not n["en"] or not n["de"]:
        return {"p_two_sided": None, "note": "empty stratum"}
    d_obs = diff_of_gaps(p, a, b)
    # discordant counts per stratum: items where exactly one predictor hit
    k = {lang: sum(1 for it in p if it["language"] == lang and it["hits"][a] != it["hits"][b])
         for lang in STRATA}
    # Under swaps, each EN discordant item contributes +/-1/n_en to D and each DE item
    # -/+1/n_de. With x EN items favouring A and y DE items favouring A:
    #   D* = (2x - k_en)/n_en - (2y - k_de)/n_de,  x ~ Bin(k_en, .5), y ~ Bin(k_de, .5).
    total = 2 ** (k["en"] + k["de"])
    tail = 0
    thresh = abs(d_obs) - 1e-12
    for x in range(k["en"] + 1):
        for y in range(k["de"] + 1):
            d_star = (2 * x - k["en"]) / n["en"] - (2 * y - k["de"]) / n["de"]
            if abs(d_star) >= thresh:
                tail += comb(k["en"], x) * comb(k["de"], y)
    return {"p_two_sided": round(min(1.0, tail / total), 6),
            "n_discordant_en": k["en"], "n_discordant_de": k["de"],
            "n_pairs": len(p)}


def compare_all(items: list[dict], predictors: list[str], resamples: int = RESAMPLES,
                seed: int = SEED) -> dict:
    """Per-predictor stratum recalls plus every ordered pair's difference of gaps."""
    per_pred = {p: stratum_recall(items, p) for p in predictors}
    for p in predictors:
        g = gap(items, p)
        per_pred[p]["gap_en_minus_de"] = round(g, 4) if g is not None else None
    pairs = []
    for i, a in enumerate(predictors):
        for b in predictors[i + 1:]:
            d = diff_of_gaps(items, a, b)
            row = {"predictor_a": a, "predictor_b": b,
                   "n_pairs": len(_paired(items, a, b)),
                   "gap_a": None, "gap_b": None,
                   "diff_of_gaps_a_minus_b": round(d, 4) if d is not None else None}
            pp = _paired(items, a, b)
            ga, gb = gap(pp, a), gap(pp, b)
            row["gap_a"] = round(ga, 4) if ga is not None else None
            row["gap_b"] = round(gb, 4) if gb is not None else None
            boot = bootstrap_diff(items, a, b, resamples=resamples, seed=seed)
            row["boot_ci_low"], row["boot_ci_high"] = boot.get("ci_low"), boot.get("ci_high")
            row["boot_resamples"], row["boot_seed"] = boot.get("n_resamples"), seed
            perm = permutation_exact(items, a, b)
            row["perm_p_two_sided"] = perm.get("p_two_sided")
            row["n_discordant_en"] = perm.get("n_discordant_en")
            row["n_discordant_de"] = perm.get("n_discordant_de")
            pairs.append(row)
    return {"per_predictor": per_pred, "pairs": pairs,
            "method": {"bootstrap": "paired item-level, resampled within stratum, "
                                    "percentile 95% interval",
                       "permutation": "exact, within-item swap of predictor labels on "
                                      "discordant items, two-sided",
                       "gap_sign": "recall_en - recall_de"}}


# --------------------------------------------------------------------------
# corpus loading (requires THESIS_DATA_DIR and the committed prediction files)
# --------------------------------------------------------------------------
RISK_LABELS = ["low", "medium", "high", "critical"]
PREDICTION_FILES = {"ml": "predictions_ml.json", "llm": "predictions_llm.json",
                    "llm_production": "predictions_llm_production.json"}


def _rows(path: str) -> list[dict]:
    """The prediction file as validator rows: {"id", "risk"} per item, unvalidated."""
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    if isinstance(data, dict) and "risk" in data:      # predictions_ml.json
        return [{"id": k, "risk": v} for k, v in data["risk"].items()]
    return list(data)                                   # list files (predict_llm*.py)


def _load_predictions(expected_ids: list[str], corpus_ids: list[str] | None = None,
                      results: str | None = None) -> dict[str, dict[str, str]]:
    """{predictor: {id: VALID risk label}} — validated, never last-row-wins.

    `expected_ids` is the same denominator run_eval.equity_slices validates
    against (every risk-labelled item with text); an invalid label (e.g. "High")
    or a missing row leaves the item out of that predictor's map, so it is
    dropped from the recall denominator instead of counting as a miss.
    """
    from prediction_validation import validate_predictions

    out = {}
    for key, name in PREDICTION_FILES.items():
        path = os.path.join(results or RESULTS, name)
        if os.path.exists(path):
            vr = validate_predictions(_rows(path), expected_ids=expected_ids, field="risk",
                                      labels=RISK_LABELS, corpus_ids=corpus_ids)
            out[key] = dict(vr.by_id)
            if vr.n_invalid or vr.n_missing:
                print(f"note: {name}: {vr.n_valid} valid, {vr.n_invalid} invalid, "
                      f"{vr.n_missing} missing of {vr.n_expected} risk-labelled items",
                      file=sys.stderr)
        else:
            print(f"note: {path} absent, predictor {key} skipped", file=sys.stderr)
    return out


def build_items(sigs, preds: dict[str, dict[str, str]]) -> tuple[list[dict], list[str]]:
    """Gold-escalate items of the two strata with each predictor's hit (pure)."""
    import baseline as bl

    items = []
    for s in sigs:
        if s.risk not in ESCALATE or s.language not in STRATA or not s.text:
            continue
        hits = {"floor": bl.predict_risk(s.text) in ESCALATE}
        for key, table in preds.items():
            if s.id in table:
                hits[key] = table[s.id] in ESCALATE
        items.append({"id": s.id, "language": s.language, "hits": hits})
    predictors = ["floor"] + [k for k in PREDICTION_FILES if k in preds]
    return items, predictors


def load_items() -> tuple[list[dict], list[str]]:
    from load_datasets import load  # same THESIS_DATA_DIR contract as run_eval.py

    sigs = load()
    expected = [s.id for s in sigs if s.risk in RISK_LABELS and s.text]
    preds = _load_predictions(expected, corpus_ids=[s.id for s in sigs])
    return build_items(sigs, preds)


def main(argv: list[str]) -> int:
    resamples = RESAMPLES
    seed = SEED
    for i, a in enumerate(argv):
        if a == "--resamples":
            resamples = int(argv[i + 1])
        if a == "--seed":
            seed = int(argv[i + 1])
    items, predictors = load_items()
    result = compare_all(items, predictors, resamples=resamples, seed=seed)
    result["n_gold_escalate"] = {lang: sum(1 for it in items if it["language"] == lang)
                                 for lang in STRATA}
    result["note"] = ("gold = assistant-drafted seed risk label (high/critical); strata are "
                      "source-language strata of English paraphrases; not a German-text result")
    os.makedirs(RESULTS, exist_ok=True)
    with open(os.path.join(RESULTS, "equity_gap_pairs.json"), "w", encoding="utf-8") as fh:
        json.dump(result, fh, indent=2)
    cols = ["predictor_a", "predictor_b", "n_pairs", "gap_a", "gap_b",
            "diff_of_gaps_a_minus_b", "boot_ci_low", "boot_ci_high", "boot_resamples",
            "boot_seed", "perm_p_two_sided", "n_discordant_en", "n_discordant_de"]
    with open(os.path.join(RESULTS, "equity_gap_pairs.csv"), "w", newline="",
              encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        for row in result["pairs"]:
            w.writerow({c: row.get(c) for c in cols})
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
