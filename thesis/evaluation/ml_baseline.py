"""Classical-ML baseline: TF-IDF + Logistic Regression, evaluated by stratified CV.

Sits between the rule-based lexicon floor (baseline.py) and the LLM enrichment path
(predict_llm.py), so Chapter 5 reports a three-rung progression on the SAME real gold
labels. cross_val_predict gives an out-of-fold prediction for every signal, so the
reported metrics are honest (no training-on-test leakage). Char n-grams make it robust
to the EN/DE mix without language detection.
"""
from __future__ import annotations
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.model_selection import StratifiedKFold, cross_val_predict


def _pipe():
    return Pipeline([
        ("tfidf", TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5),
                                  min_df=2, sublinear_tf=True)),
        ("clf", LogisticRegression(max_iter=2000, class_weight="balanced")),
    ])


def cv_predict(texts: list[str], labels: list[str], min_per_class: int = 5):
    """Out-of-fold predictions via stratified CV. Folds capped by the smallest class.

    Returns (labels, preds, k, kept_idx). kept_idx maps every returned position
    back to the caller's input order (ultra-rare classes may be dropped), so a
    caller can align per-item predictions by signal id — which is what makes
    the paired McNemar tests in run_eval.significance possible.
    """
    from collections import Counter
    counts = Counter(labels)
    idx = list(range(len(labels)))
    if min(counts.values()) < min_per_class:
        # drop ultra-rare classes the CV can't support, so folds stay valid
        keep = {c for c, n in counts.items() if n >= min_per_class}
        idx = [i for i, y in enumerate(labels) if y in keep]
        texts = [texts[i] for i in idx]
        labels = [labels[i] for i in idx]
        counts = Counter(labels)
    k = max(2, min(5, min(counts.values())))
    skf = StratifiedKFold(n_splits=k, shuffle=True, random_state=42)
    preds = cross_val_predict(_pipe(), texts, labels, cv=skf)
    return labels, list(preds), k, idx
