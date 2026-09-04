#!/usr/bin/env python3
"""Recompute the statistics the 4 September review disputes.

Every number this prints is derived from files already in the repository:
  thesis/evaluation/results/{summary.json,escalation_recall_by_language.csv,
                             journey_stage_perclass.csv,owner_perclass.csv}
  apps/api/app/evals/published_metrics.json

No dependencies beyond the standard library, so it runs anywhere the harness does.
Run from the repository root:  python3 thesis/review-2026-09-04-recompute.py
"""
from __future__ import annotations

import csv
import json
import math
import os
from math import comb

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RES = os.path.join(ROOT, "thesis", "evaluation", "results")
EVALS = os.path.join(ROOT, "apps", "api", "app", "evals")


# ---------- interval estimators ----------

def wilson(k: int, n: int, z: float = 1.959964) -> tuple[float, float]:
    p = k / n
    d = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / d
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return centre - half, centre + half


def _binom_cdf(x: int, n: int, p: float) -> float:
    return sum(comb(n, i) * p**i * (1 - p) ** (n - i) for i in range(x + 1))


def _bisect(f, lo: float = 1e-12, hi: float = 1 - 1e-12) -> float:
    for _ in range(200):
        mid = (lo + hi) / 2
        if f(lo) * f(mid) <= 0:
            hi = mid
        else:
            lo = mid
    return (lo + hi) / 2


def clopper_pearson(k: int, n: int, alpha: float = 0.05) -> tuple[float, float]:
    lo = 0.0 if k == 0 else _bisect(lambda p: 1 - _binom_cdf(k - 1, n, p) - alpha / 2)
    hi = 1.0 if k == n else _bisect(lambda p: _binom_cdf(k, n, p) - alpha / 2)
    return lo, hi


# ---------- exact tests ----------

def fisher_exact_two_sided(a: int, b: int, c: int, d: int) -> float:
    """Two-sided Fisher exact test on the 2x2 table [[a,b],[c,d]]."""
    n, row1, col1 = a + b + c + d, a + b, a + c
    def prob(x: int) -> float:
        return comb(row1, x) * comb(n - row1, col1 - x) / comb(n, col1)
    observed = prob(a)
    lo = max(0, col1 - (n - row1))
    hi = min(row1, col1)
    return sum(prob(x) for x in range(lo, hi + 1) if prob(x) <= observed + 1e-12)


def mcnemar_exact(b: int, c: int) -> float:
    """Two-sided exact McNemar on the discordant pairs (b, c)."""
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    return min(1.0, 2 * sum(comb(n, i) for i in range(k + 1)) / 2**n)


# ---------- checks ----------

def restricted_macro_f1() -> None:
    """§5A.4.1 reports 0.28 / 0.18 as macro-F1 'restricted to classes with >= 5 gold
    examples'. run_eval.score_taxonomy restricts the ITEMS but calls a macro average
    with no labels= argument, so out-of-set predictions enter as phantom zero-F1
    classes. Averaging the per-class file over the supported labels is the figure the
    sentence describes."""
    print("\n== Restricted macro-F1 for the routing fields (addendum A7) ==")
    summary = json.load(open(os.path.join(RES, "summary.json")))
    for field, key in (("journey_stage", "journey_stage_llm_closed_set"),
                       ("owner", "owner_llm_closed_set")):
        path = os.path.join(RES, f"{field}_perclass.csv")
        rows = list(csv.DictReader(open(path)))
        supported = [r for r in rows if float(r["support"]) >= 5]
        mean_f1 = sum(float(r["f1"]) for r in supported) / len(supported)
        zeros = [r["label"] for r in supported if float(r["f1"]) == 0.0]
        reported = summary[key]["f1_macro_on_supported"]
        print(f"  {field}: reported {reported:.4f} | over the {len(supported)} supported "
              f"classes {mean_f1:.4f}")
        print(f"    classes at F1 = 0: {', '.join(zeros) if zeros else 'none'}")


def golden_set_intervals() -> None:
    """§5A.7 and Appendix B quote percentile-bootstrap intervals on proportions at the
    boundary. Wilson and Clopper-Pearson are the standard alternatives."""
    print("\n== Golden-set intervals (addendum B1) ==")
    pub = json.load(open(os.path.join(EVALS, "published_metrics.json")))
    overall, by_lang = pub["overall"], pub["by_language"]
    cases = [
        ("sentiment, all items", round(overall["sentiment_accuracy"] * 100), 100,
         overall.get("sentiment_ci95")),
        ("urgency, all items", round(overall["urgency_accuracy"] * 100), 100,
         overall.get("urgency_ci95")),
        ("sentiment, DE", round(by_lang["de"]["sentiment_accuracy"] * by_lang["de"]["n"]),
         by_lang["de"]["n"], by_lang["de"].get("sentiment_ci")),
        ("sentiment, EN", round(by_lang["en"]["sentiment_accuracy"] * by_lang["en"]["n"]),
         by_lang["en"]["n"], by_lang["en"].get("sentiment_ci")),
    ]
    for label, k, n, published in cases:
        w, cp = wilson(k, n), clopper_pearson(k, n)
        pub_txt = (f"published [{published[0]:.3f}, {published[1]:.3f}]"
                   if published else "published: none")
        print(f"  {label}: {k}/{n} | {pub_txt} | Wilson [{w[0]:.3f}, {w[1]:.3f}] | "
              f"Clopper-Pearson [{cp[0]:.3f}, {cp[1]:.3f}]")


def escalation_tests() -> None:
    """§5A.5 asserts a method-by-stratum contrast. These are the tests the harness
    never runs."""
    print("\n== Escalation equity, exact tests (addendum B1) ==")
    rows = {r["language"]: r for r in
            csv.DictReader(open(os.path.join(RES, "escalation_recall_by_language.csv")))}
    de, en = rows["de"], rows["en"]
    n_de, n_en = int(de["n_gold_escalate"]), int(en["n_gold_escalate"])
    hits = {}
    for name, col in (("floor", "recall_floor"), ("learned", "recall_ml"), ("contextual", "recall_llm")):
        hits[name] = (round(float(de[col]) * n_de), round(float(en[col]) * n_en))
    for name, (k_de, k_en) in hits.items():
        p = fisher_exact_two_sided(k_de, n_de - k_de, k_en, n_en - k_en)
        print(f"  {name:11s} DE {k_de}/{n_de} vs EN {k_en}/{n_en}: Fisher p = {p:.4f}")
    k_llm, k_ml = hits["contextual"][0], hits["learned"][0]
    p = fisher_exact_two_sided(k_llm, n_de - k_llm, k_ml, n_de - k_ml)
    print(f"  contextual vs learned on the DE stratum ({k_llm}/{n_de} vs {k_ml}/{n_de}): "
          f"Fisher p = {p:.4f}")
    for name, (k_de, _) in hits.items():
        lo, hi = clopper_pearson(k_de, n_de)
        print(f"  {name:11s} DE recall 95% interval: [{lo:.3f}, {hi:.3f}]")


def mcnemar_sensitivity() -> None:
    """The headline p = 0.029 rests on one LLM run whose documented same-day noise is
    1-3 items per 100. This is how far the result is from the 0.05 line."""
    print("\n== McNemar sensitivity to model noise (addendum B1) ==")
    summary = json.load(open(os.path.join(RES, "summary.json")))
    paired = summary["mcnemar_paired"]
    for task in ("sentiment", "risk"):
        cell = paired[task]["ml_vs_llm"]
        b, c = cell["b_first_only_correct"], cell["c_second_only_correct"]
        print(f"  {task}: reported p = {cell['p_exact_two_sided']:.4f} (b = {b}, c = {c})")
        for flips in (0, 1, 2, 3):
            bb, cc = b + flips, c - flips
            if cc < 0:
                break
            print(f"    {flips} contextual-correct item(s) flipped: b = {bb}, c = {cc}, "
                  f"p = {mcnemar_exact(bb, cc):.4f}")


def corpus_composition() -> None:
    """§5A.5's composition figures ('37 of 38', '58 of 66') match no denominator."""
    print("\n== Language x sector composition (addendum B4) ==")
    summary = json.load(open(os.path.join(RES, "summary.json")))
    comp = summary["language_sector_composition"]
    sectors: dict[str, dict[str, int]] = {}
    for key, n in comp.items():
        lang, sector = key.split("|")
        sectors.setdefault(sector, {})[lang] = n
    for sector, langs in sorted(sectors.items()):
        total = sum(langs.values())
        parts = ", ".join(f"{lang} {n}" for lang, n in sorted(langs.items()))
        print(f"  {sector}: n = {total} ({parts})")
    star = summary.get("sentiment_llm_by_language_sector", {})
    if star:
        print("  star-rated subset (the denominator behind the per-slice accuracies):")
        for key, cell in sorted(star.items()):
            print(f"    {key}: n = {cell['n']}")


if __name__ == "__main__":
    restricted_macro_f1()
    golden_set_intervals()
    escalation_tests()
    mcnemar_sensitivity()
    corpus_composition()
