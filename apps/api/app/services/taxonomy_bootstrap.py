"""Taxonomy bootstrap — "no taxonomy to build" made true, locally.

Wires the dormant embedding-clustering machinery (semantic_taxonomy.py) into the
local-first flow: embed the workspace's signals, cluster by cosine similarity,
name each cluster via the LLM, and land the results as *proposed* categories in
the TaxonomyStore — versioned, confidence-scored, awaiting human accept/reject.

This is the governed counterpart to "fully automatic taxonomy": CLARA proposes,
a human decides, and every step carries a confidence score and an audit entry.

The Postgres path (semantic_taxonomy.discover_themes over pgvector +
taxonomy_nodes) stays as-is for DB-connected deployments; this module serves
the SQLite/local demo and pilots. ponytail: same clustering constants
(CLUSTER_EPS/MIN_CLUSTER) so both paths behave alike.
"""

from __future__ import annotations

import logging
from typing import Any

from app.domain.models import SignalRecord, TaxonomyType

# Live module reference (not `from ... import`): tests reload app.services.ai to
# re-read env, which replaces the AIProviderError class; a live reference keeps
# except-clauses and monkeypatches pointing at the current module attributes.
import app.services.ai as ai
from app.services.semantic_taxonomy import (
    NAME_TOOL,
    CLUSTER_EPS,
    MIN_CLUSTER,
    avg_cohesion,
    cluster_by_threshold,
    slugify,
)
from app.services.taxonomies import TaxonomyStore, searchable_text

logger = logging.getLogger(__name__)


_STOPWORDS = frozenset(
    "the and for with that this from have has was were are is not you your after"
    " still never where when what been being will would could very much".split()
)


def _cluster_terms(texts: list[str], label: str) -> list[str]:
    """Terms that actually occur in the cluster, so substring classification matches.

    The label alone ("refund_delay") rarely appears verbatim in feedback; the top
    recurring content words ("refund") do.
    """
    from collections import Counter

    counts: Counter[str] = Counter()
    for text in texts:
        for raw in text.lower().split():
            token = raw.strip(".,!?:;()[]\"'")
            if len(token) > 3 and token not in _STOPWORDS:
                counts[token] += 1
    top = [token for token, n in counts.most_common(3) if n >= 2]
    label_term = label.replace("_", " ").strip().lower()
    return list(dict.fromkeys([label_term, *top])) if label_term else top


def _name_cluster(sample_texts: list[str]) -> dict[str, str]:
    """LLM-name a cluster; fall back to the lead words when the AI is unavailable."""
    try:
        return ai.call_tool(
            system="You name clusters of related customer feedback as one concise theme.",
            user="Feedback in this cluster:\n" + "\n".join(f"- {t}" for t in sample_texts),
            tool=NAME_TOOL,
            tool_name="name_theme",
            trace_name="bootstrap:name_theme",
        )
    except ai.AIProviderError:
        lead = " ".join((sample_texts[0] or "theme").split()[:4])
        return {"name": lead, "description": "Auto-discovered theme — rename in review."}


def bootstrap_taxonomy(
    signals: list[SignalRecord],
    taxonomy_store: TaxonomyStore,
    *,
    taxonomy_type: TaxonomyType = TaxonomyType.contact_reason,
    limit: int = 200,
    actor: str = "taxonomy_bootstrap",
) -> dict[str, Any]:
    """Cluster signals into proposed taxonomy categories.

    Returns {scanned, clusters, proposed, skipped, proposals[], error?}.
    Embedding failure aborts cleanly (error="embedding_failed") — no partial writes.
    """
    scoped = signals[:limit]
    texts = [searchable_text(signal) for signal in scoped]
    pairs = [(signal, text) for signal, text in zip(scoped, texts) if text.strip()]
    if len(pairs) < MIN_CLUSTER:
        return {"scanned": len(scoped), "clusters": 0, "proposed": 0, "skipped": 0, "proposals": []}

    try:
        vectors = ai.embed([text for _, text in pairs])
    except ai.AIProviderError:
        logger.warning("Embedding failed for taxonomy bootstrap, aborting", exc_info=True)
        return {
            "scanned": len(scoped),
            "clusters": 0,
            "proposed": 0,
            "skipped": 0,
            "proposals": [],
            "error": "embedding_failed",
        }

    clusters = cluster_by_threshold(vectors, CLUSTER_EPS, MIN_CLUSTER)
    existing_ids = {
        category.category_id
        for catalog in taxonomy_store.list_catalogs()
        for category in catalog.categories
    }

    proposals: list[dict[str, Any]] = []
    skipped = 0
    for idxs in clusters:
        cluster_signals = [pairs[i][0] for i in idxs]
        sample_texts = [pairs[i][1] for i in idxs][:5]
        named = _name_cluster(sample_texts)
        slug = slugify(named.get("name", ""))
        if not slug:
            skipped += 1
            continue

        category_id = f"CAT-{slug.upper().replace('_', '-')}"
        if category_id in existing_ids:
            skipped += 1  # already known (seed or earlier bootstrap) — don't re-propose
            continue

        confidence = avg_cohesion([vectors[i] for i in idxs])
        cluster_texts = [pairs[i][1] for i in idxs]
        taxonomy_store.propose_category(
            taxonomy_type,
            category_id=category_id,
            label=named.get("name", slug),
            description=named.get("description", ""),
            terms=_cluster_terms(cluster_texts, named.get("name", slug)),
            confidence=confidence,
            evidence_count=len(cluster_signals),
            actor=actor,
        )
        existing_ids.add(category_id)
        proposals.append(
            {
                "category_id": category_id,
                "label": named.get("name", slug),
                "description": named.get("description", ""),
                "confidence": round(confidence, 3),
                "evidence_count": len(cluster_signals),
                "signal_ids": [signal.signal_id for signal in cluster_signals[:10]],
                "samples": sample_texts[:3],
            }
        )

    return {
        "scanned": len(scoped),
        "clusters": len(clusters),
        "proposed": len(proposals),
        "skipped": skipped,
        "proposals": proposals,
    }
