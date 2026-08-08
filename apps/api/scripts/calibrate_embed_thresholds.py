"""Calibrate every cosine threshold against the LIVE embedding model.

Why this exists (science review 2026-08-08, finding F1): the pipeline's seven
cosine thresholds were tuned under one embedding model, and cosine similarity
distributions are NOT comparable across models — a floor that is conservative
under one embedder can be near-vacuous under another. Swapping AI_EMBED_MODEL
without recalibrating silently changes what maps, merges, clusters and refuses.

Method: build labelled pairs from data already in the repo (no new annotation):
  - RELATED pairs   = two golden-set items sharing the same expected.category
  - UNRELATED pairs = two golden-set items from different categories
  - MAPPING pairs   = golden item text vs its own category centroid (positive)
                      and vs other categories' centroids (negative)
  - DUPLICATE pairs = an item vs itself with trivial edits (near-verbatim), the
                      only pair class that should clear a duplicate threshold

Each threshold is then derived from a stated rule (quantile of the relevant
distribution), so the constants become measured quantities with provenance
instead of folklore. Output: a JSON report + a ready-to-paste .env block.

Run:  cd apps/api && python3 -m scripts.calibrate_embed_thresholds
Needs AI_EMBED_* configured (falls back to AI_BASE_URL like the app).
"""

from __future__ import annotations

import json
import random
import sys
from datetime import datetime, timezone
from itertools import combinations
from pathlib import Path

from app.evals.harness import load_golden_set
from app.services import ai
from app.services.semantic_taxonomy import centroid, cosine_sim

OUT_DIR = Path(__file__).resolve().parents[1] / "app" / "evals"
REPORT_PATH = OUT_DIR / "embed_calibration.json"

# Bound pair counts so the report is cheap and deterministic.
MAX_PAIRS_PER_CLASS = 400
SEED = 20260808


def _quantile(values: list[float], q: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, int(q * (len(ordered) - 1))))
    return ordered[index]


def _stats(values: list[float]) -> dict[str, float]:
    if not values:
        return {"n": 0}
    mean = sum(values) / len(values)
    return {
        "n": len(values),
        "mean": round(mean, 4),
        "p05": round(_quantile(values, 0.05), 4),
        "p50": round(_quantile(values, 0.50), 4),
        "p95": round(_quantile(values, 0.95), 4),
        "p99": round(_quantile(values, 0.99), 4),
        "min": round(min(values), 4),
        "max": round(max(values), 4),
    }


def _near_verbatim(text: str) -> str:
    """A trivial edit of the same complaint — the duplicate-pair generator."""
    return text.replace(".", "!").replace("really", "very") + " Please fix this."


def main() -> int:
    golden = load_golden_set()
    if len(golden) < 20:
        print("Golden set too small to calibrate against.", file=sys.stderr)
        return 1

    texts = [item["text"] for item in golden]
    categories = [item.get("expected", {}).get("category", "unknown") for item in golden]

    print(f"Embedding {len(texts)} golden texts + duplicates via {ai.effective_embed_model()}"
          f" @ {ai.effective_embed_base_url()} ...")
    dup_texts = [_near_verbatim(t) for t in texts]
    vectors = ai.embed(texts + dup_texts)
    base_vecs, dup_vecs = vectors[: len(texts)], vectors[len(texts):]

    rng = random.Random(SEED)
    related: list[float] = []
    unrelated: list[float] = []
    all_pairs = list(combinations(range(len(texts)), 2))
    rng.shuffle(all_pairs)
    for i, j in all_pairs:
        sim = cosine_sim(base_vecs[i], base_vecs[j])
        bucket = related if categories[i] == categories[j] else unrelated
        if len(bucket) < MAX_PAIRS_PER_CLASS:
            bucket.append(sim)
        if len(related) >= MAX_PAIRS_PER_CLASS and len(unrelated) >= MAX_PAIRS_PER_CLASS:
            break

    duplicates = [cosine_sim(base_vecs[i], dup_vecs[i]) for i in range(len(texts))]

    by_cat: dict[str, list[list[float]]] = {}
    for vec, cat in zip(base_vecs, categories):
        by_cat.setdefault(cat, []).append(vec)
    centroids = {cat: centroid(vecs) for cat, vecs in by_cat.items() if len(vecs) >= 3}
    map_pos: list[float] = []
    map_neg: list[float] = []
    for vec, cat in zip(base_vecs, categories):
        for c_cat, c_vec in centroids.items():
            sim = cosine_sim(vec, c_vec)
            (map_pos if c_cat == cat else map_neg).append(sim)

    # Derivation rules — each threshold is a stated quantile of the distribution
    # that should NOT clear it, with the distribution that SHOULD clear it
    # reported alongside so the operating point is auditable.
    derived = {
        # Relevance floor: admit almost nothing unrelated (5% FPR).
        "ASK_MIN_SIMILARITY": {
            "rule": "p95 of unrelated-pair sims (5% false-admit)",
            "value": round(_quantile(unrelated, 0.95), 2),
        },
        # Taxonomy mapping floor: above nearly all wrong-category sims.
        "TAXONOMY_MAP_THRESHOLD": {
            "rule": "p95 of wrong-category centroid sims",
            "value": round(_quantile(map_neg, 0.95), 2),
        },
        # Clustering: between the bulk of unrelated and the bulk of related.
        "CLUSTER_SEMANTIC_THRESHOLD": {
            "rule": "midpoint of p95(unrelated) and p50(related)",
            "value": round((_quantile(unrelated, 0.95) + _quantile(related, 0.50)) / 2, 2),
        },
        # Duplicate flag: above p99 of same-category (related-but-distinct) pairs.
        "TAXONOMY_DUPLICATE_SIMILARITY": {
            "rule": "p99 of related-pair sims (distinct items must not flag)",
            "value": round(_quantile(related, 0.99), 2),
        },
        # Auto-merge: strictly above everything except true near-verbatim pairs.
        "TAXONOMY_MERGE_EPS": {
            "rule": "midpoint of max(related) and p05(near-verbatim duplicates)",
            "value": round((max(related) + _quantile(duplicates, 0.05)) / 2, 2),
        },
    }

    report = {
        "calibrated_at": datetime.now(timezone.utc).isoformat(),
        "embed_model": ai.effective_embed_model(),
        "embed_host": ai.effective_embed_base_url(),
        "pair_counts": {
            "related": len(related),
            "unrelated": len(unrelated),
            "near_verbatim_duplicates": len(duplicates),
            "mapping_pos": len(map_pos),
            "mapping_neg": len(map_neg),
        },
        "distributions": {
            "related_same_category": _stats(related),
            "unrelated_cross_category": _stats(unrelated),
            "near_verbatim_duplicates": _stats(duplicates),
            "own_category_centroid": _stats(map_pos),
            "other_category_centroid": _stats(map_neg),
        },
        "derived_thresholds": derived,
        "notes": [
            "Pairs come from golden_set.json category labels; distributions are"
            " workspace-shaped, not universal. Re-run after changing the embed"
            " model — thresholds do not transfer across embedders.",
            "Values are recommendations; the code reads them from env so an"
            " operator can override any single one.",
        ],
    }
    REPORT_PATH.write_text(json.dumps(report, indent=2) + "\n")

    print(json.dumps(report["distributions"], indent=2))
    print("\n# Paste into apps/api/.env (and the VPS .env) for"
          f" {ai.effective_embed_model()}:")
    for key, spec in derived.items():
        print(f"{key}={spec['value']}")
    print(f"\nReport written to {REPORT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
