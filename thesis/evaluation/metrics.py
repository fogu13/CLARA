"""Thin metric helpers over scikit-learn, plus a confusion-matrix CSV writer.

Kept small on purpose: precision/recall/F1 (macro + weighted), accuracy, and a
labelled confusion matrix. All numbers in Chapter 5 §5A come from here, computed
from data — none are hand-entered.
"""
from __future__ import annotations
import csv
import os
from sklearn.metrics import (
    precision_recall_fscore_support,
    accuracy_score,
    confusion_matrix,
)


def score(y_true: list[str], y_pred: list[str]) -> dict:
    """Return accuracy plus macro and weighted precision/recall/F1."""
    acc = accuracy_score(y_true, y_pred)
    p_m, r_m, f_m, _ = precision_recall_fscore_support(
        y_true, y_pred, average="macro", zero_division=0
    )
    p_w, r_w, f_w, _ = precision_recall_fscore_support(
        y_true, y_pred, average="weighted", zero_division=0
    )
    return {
        "n": len(y_true),
        "accuracy": round(acc, 4),
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
    from math import comb
    b = sum(1 for x, y in zip(a_correct, b_correct) if x and not y)
    c = sum(1 for x, y in zip(a_correct, b_correct) if y and not x)
    n = b + c
    if n == 0:
        return b, c, 1.0
    k = min(b, c)
    tail = sum(comb(n, i) for i in range(k + 1)) / (2 ** n)
    return b, c, min(1.0, 2 * tail)
