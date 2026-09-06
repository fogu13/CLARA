"""Thin metric helpers over scikit-learn, plus a confusion-matrix CSV writer.

Kept small on purpose: precision/recall/F1 (macro + weighted), accuracy with a
Wilson interval, a labelled confusion matrix, and two exact tests (McNemar for
paired predictors, Fisher for a 2x2 recall comparison). All numbers in Chapter 5
§5A come from here, computed from data — none are hand-entered.
"""
from __future__ import annotations
import csv
import math
import os
from math import comb
from sklearn.metrics import (
    precision_recall_fscore_support,
    accuracy_score,
    confusion_matrix,
)


def wilson_interval(successes: int, n: int, z: float = 1.959964) -> tuple[float, float]:
    """Wilson score interval for a binomial proportion (95% two-sided by default).

    Used for every accuracy/recall proportion the harness reports. A percentile
    bootstrap of 0/1 scores collapses to a degenerate interval at 0 or 1 and is
    too narrow on n < 30; the Wilson interval has the right coverage on the
    sizes this corpus produces (n = 5 .. 188) and never leaves [0, 1].
    """
    if n <= 0:
        return (0.0, 0.0)
    p = successes / n
    z2 = z * z
    denom = 1.0 + z2 / n
    centre = (p + z2 / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z2 / (4 * n * n)) / denom
    return (round(max(0.0, centre - half), 4), round(min(1.0, centre + half), 4))


def score(y_true: list[str], y_pred: list[str], labels: list[str] | None = None) -> dict:
    """Return accuracy (with a 95% Wilson interval) plus macro and weighted P/R/F1.

    `labels` restricts the macro/weighted averages to those classes. Without it
    scikit-learn averages over every label that appears in y_true OR y_pred, so
    a restricted-item evaluation (e.g. "classes with support >= 5") would still
    be pulled down by stray predicted labels outside the restriction.
    """
    n = len(y_true)
    acc = accuracy_score(y_true, y_pred) if n else 0.0
    correct = sum(1 for t, p in zip(y_true, y_pred) if t == p)
    lo, hi = wilson_interval(correct, n)
    kw = {"labels": labels} if labels else {}
    p_m, r_m, f_m, _ = precision_recall_fscore_support(
        y_true, y_pred, average="macro", zero_division=0, **kw
    )
    p_w, r_w, f_w, _ = precision_recall_fscore_support(
        y_true, y_pred, average="weighted", zero_division=0, **kw
    )
    return {
        "n": n,
        "accuracy": round(acc, 4),
        "accuracy_ci_low": lo,
        "accuracy_ci_high": hi,
        "precision_macro": round(p_m, 4),
        "recall_macro": round(r_m, 4),
        "f1_macro": round(f_m, 4),
        "precision_weighted": round(p_w, 4),
        "recall_weighted": round(r_w, 4),
        "f1_weighted": round(f_w, 4),
    }


def per_class(y_true: list[str], y_pred: list[str], labels: list[str]) -> list[dict]:
    p, r, f, s = precision_recall_fscore_support(
        y_true, y_pred, labels=labels, zero_division=0
    )
    return [
        {
            "label": lab,
            "precision": round(p[i], 4),
            "recall": round(r[i], 4),
            "f1": round(f[i], 4),
            "support": int(s[i]),
        }
        for i, lab in enumerate(labels)
    ]


def write_confusion(y_true, y_pred, labels, path: str) -> None:
    cm = confusion_matrix(y_true, y_pred, labels=labels)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["true\\pred"] + labels)
        for i, lab in enumerate(labels):
            w.writerow([lab] + list(cm[i]))


def mcnemar_exact(a_correct: list[bool], b_correct: list[bool]) -> tuple[int, int, float]:
    """Exact two-sided McNemar test on two classifiers' PAIRED per-item correctness.

    Deliberately the same convention as the platform's in-repo harness
    (apps/api/app/evals/harness.py::mcnemar_exact), so both evidence streams
    report the same statistic: b = A right & B wrong, c = A wrong & B right,
    p = two-sided exact binomial(n = b + c, 0.5). A small p with c > b means
    B is significantly better on these paired items. The paired test is the
    right instrument on a corpus this size — two accuracy totals cannot
    separate the predictors, their per-item agreement can (§3.5.3).
    """
    b = sum(1 for x, y in zip(a_correct, b_correct) if x and not y)
    c = sum(1 for x, y in zip(a_correct, b_correct) if y and not x)
    n = b + c
    if n == 0:
        return b, c, 1.0
    k = min(b, c)
    tail = sum(comb(n, i) for i in range(k + 1)) / (2 ** n)
    return b, c, min(1.0, 2 * tail)


def mcnemar_p_from_counts(b: int, c: int) -> float:
    """Exact two-sided McNemar p from the discordant counts alone."""
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    tail = sum(comb(n, i) for i in range(k + 1)) / (2 ** n)
    return min(1.0, 2 * tail)


def mcnemar_one_flip_p(b: int, c: int) -> float:
    """p-value after moving ONE discordant pair from the majority side to the minority.

    A fragility check for small corpora: if a single relabelled item would push
    p across .05, the difference rests on that item and the text must say so.
    """
    if b == c:
        return mcnemar_p_from_counts(b, c)
    if b > c:
        return mcnemar_p_from_counts(b - 1, c + 1)
    return mcnemar_p_from_counts(b + 1, c - 1)


def mcnemar_sensitivity(b: int, c: int) -> dict:
    """Three single-item perturbations of a paired result, each as an exact p.

    With c > b (the second predictor ahead):
      minority_gains_one  one both-wrong or both-right item becomes first-only
                          correct: (b + 1, c)       -> p
      majority_loses_one  one second-only-correct item becomes both-wrong or
                          both-right: (b, c - 1)    -> p
      one_pair_swaps      one discordant pair changes sides: (b + 1, c - 1) -> p
    The three are reported together because they answer the question an
    examiner asks, "what if one label were different?", in its three forms;
    quoting only the mildest would understate the fragility.
    """
    lo, hi = (b, c) if b <= c else (c, b)
    return {
        "p_observed": round(mcnemar_p_from_counts(b, c), 6),
        "p_minority_gains_one": round(mcnemar_p_from_counts(lo + 1, hi), 6),
        "p_majority_loses_one": round(mcnemar_p_from_counts(lo, max(hi - 1, 0)), 6),
        "p_one_pair_swaps": round(mcnemar_one_flip_p(b, c), 6),
    }


def fisher_exact(a: int, b: int, c: int, d: int) -> float:
    """Two-sided Fisher exact p for the 2x2 table [[a, b], [c, d]] (stdlib only).

    Sums the hypergeometric probabilities of every table with the same margins
    whose probability does not exceed the observed table's (the convention
    scipy.stats.fisher_exact uses). Used to compare escalation recall between
    two language strata: a/b = hits/misses in one language, c/d in the other.
    """
    n = a + b + c + d
    if n == 0:
        return 1.0
    row1, col1 = a + b, a + c
    total = comb(n, col1)

    def prob(x: int) -> float:
        return comb(row1, x) * comb(n - row1, col1 - x) / total

    observed = prob(a)
    lo, hi = max(0, col1 - (n - row1)), min(row1, col1)
    p = sum(prob(x) for x in range(lo, hi + 1) if prob(x) <= observed * (1 + 1e-9))
    return min(1.0, p)
