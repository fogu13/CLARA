"""Embedding-classifier baseline: sentence embeddings + logistic regression, out-of-fold by
stratified cross-validation (§5A.2, a stronger learned local baseline than TF-IDF + LR).

The deployment reading of §5A.4 ("a learned local model is close to sufficient for severity
routing") rests on a lightweight learned model. This predictor tests it against a better
one, with the same out-of-fold discipline as ml_baseline.py, so the paired McNemar tests of
compare_runs.py apply unchanged.

    python3 predict_embedding.py --embedder api                       # the platform's configured embedding endpoint (AI_EMBED_* env)
    python3 predict_embedding.py --embedder st:intfloat/multilingual-e5-small   # a local sentence-transformers model
    python3 predict_embedding.py --embedder hash                      # TEST DOUBLE: hashed char n-grams, not a learned embedding

Writes <results>/predictions_embedding.json (a list of {id, sentiment, risk}, the shape
compare_runs.py reads) and predictions_embedding.meta.json (embedder, dimensions, folds).
Score with:  python3 compare_runs.py floor ml=results/predictions_ml.json emb=results/predictions_embedding.json

Never report the hash embedder: it exists so the pipeline can be tested without a model
or a download. THESIS_RESULTS_DIR redirects the output folder so the reported files are
never overwritten by a trial run.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import sys
from collections import Counter
from datetime import UTC, datetime

HERE = os.path.dirname(os.path.abspath(__file__))
RESULTS = os.environ.get("THESIS_RESULTS_DIR") or os.path.join(HERE, "results")
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import baseline as bl  # noqa: E402
from load_datasets import load  # noqa: E402

RISK = ["low", "medium", "high", "critical"]
HASH_DIMS = 256


def hash_embed(texts: list[str], dims: int = HASH_DIMS) -> list[list[float]]:
    """Deterministic hashed character 3-5-grams, L2-normalised. A test double only."""
    vectors = []
    for text in texts:
        vec = [0.0] * dims
        lowered = f" {text.lower()} "
        for n in (3, 4, 5):
            for i in range(max(0, len(lowered) - n + 1)):
                gram = lowered[i:i + n]
                digest = hashlib.blake2b(gram.encode("utf-8"), digest_size=8).digest()
                bucket = int.from_bytes(digest[:4], "big") % dims
                sign = 1.0 if digest[4] % 2 == 0 else -1.0
                vec[bucket] += sign
        norm = math.sqrt(sum(v * v for v in vec)) or 1.0
        vectors.append([v / norm for v in vec])
    return vectors


def api_embed(texts: list[str]) -> list[list[float]]:
    sys.path.insert(0, os.path.normpath(os.path.join(HERE, "..", "..", "apps", "api")))
    from app.services.ai import embed

    return [list(map(float, vector)) for vector in embed(texts)]


def st_embed(model_name: str):
    def _embed(texts: list[str]) -> list[list[float]]:
        from sentence_transformers import SentenceTransformer

        model = SentenceTransformer(model_name)
        return [list(map(float, row)) for row in model.encode(texts, normalize_embeddings=True)]

    return _embed


def resolve_embedder(name: str):
    if name == "hash":
        return hash_embed, "hash (test double: hashed char n-grams; not a learned embedding; never report)"
    if name == "api":
        return api_embed, "api (the platform's configured embedding endpoint, AI_EMBED_MODEL)"
    if name.startswith("st:"):
        return st_embed(name[3:]), f"sentence-transformers {name[3:]}"
    raise SystemExit(f"unknown embedder {name!r}: use api, st:<model> or hash")


def cv_predict_vectors(vectors: list[list[float]], labels: list[str], *, min_per_class: int = 5):
    """Out-of-fold logistic-regression predictions, folds capped by the smallest class
    (the same policy as ml_baseline.cv_predict). Returns (kept_idx, preds, k)."""
    from sklearn.linear_model import LogisticRegression
    from sklearn.model_selection import StratifiedKFold, cross_val_predict

    counts = Counter(labels)
    keep = {c for c, n in counts.items() if n >= min_per_class}
    idx = [i for i, y in enumerate(labels) if y in keep]
    if len(keep) < 2:
        return [], [], 0
    x = [vectors[i] for i in idx]
    y = [labels[i] for i in idx]
    k = max(2, min(5, min(Counter(y).values())))
    skf = StratifiedKFold(n_splits=k, shuffle=True, random_state=42)
    clf = LogisticRegression(max_iter=4000, class_weight="balanced")
    preds = cross_val_predict(clf, x, y, cv=skf)
    return idx, [str(p) for p in preds], k


def predict(sigs, embedder, *, embedder_label: str) -> tuple[list[dict], dict]:
    sigs = [s for s in sigs if s.text]
    vectors = embedder([s.text for s in sigs])
    out: dict[str, dict] = {s.id: {"id": s.id} for s in sigs}
    meta = {"written_at": datetime.now(UTC).isoformat(), "embedder": embedder_label,
            "dimensions": len(vectors[0]) if vectors else 0, "classifier": "LogisticRegression(class_weight=balanced), out-of-fold",
            "tasks": {}}
    # Sentiment: star-rating gold (the same mapping as run_eval / compare_runs).
    rated = [i for i, s in enumerate(sigs) if s.star_rating is not None]
    labels = [bl.gold_sentiment_from_stars(sigs[i].star_rating) for i in rated]
    kept, preds, k = cv_predict_vectors([vectors[i] for i in rated], labels)
    for local, label in zip(kept, preds):
        out[sigs[rated[local]].id]["sentiment"] = label
    meta["tasks"]["sentiment"] = {"n_labelled": len(rated), "n_predicted": len(kept), "folds": k}
    # Risk: the seed label where present.
    risky = [i for i, s in enumerate(sigs) if s.risk in RISK]
    labels = [sigs[i].risk for i in risky]
    kept, preds, k = cv_predict_vectors([vectors[i] for i in risky], labels)
    for local, label in zip(kept, preds):
        out[sigs[risky[local]].id]["risk"] = label
    meta["tasks"]["risk"] = {"n_labelled": len(risky), "n_predicted": len(kept), "folds": k}
    rows = [row for row in out.values() if len(row) > 1]
    return rows, meta


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--embedder", default="api", help="api | st:<model> | hash (test double)")
    parser.add_argument("--out", default=RESULTS)
    args = parser.parse_args(argv)
    embedder, label = resolve_embedder(args.embedder)
    rows, meta = predict(load(), embedder, embedder_label=label)
    os.makedirs(args.out, exist_ok=True)
    with open(os.path.join(args.out, "predictions_embedding.json"), "w", encoding="utf-8") as fh:
        json.dump(rows, fh, indent=1)
    with open(os.path.join(args.out, "predictions_embedding.meta.json"), "w", encoding="utf-8") as fh:
        json.dump(meta, fh, indent=2)
    print(f"wrote {len(rows)} embedding-classifier predictions ({label}) -> {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
