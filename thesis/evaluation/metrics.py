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
