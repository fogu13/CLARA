"""Semantic taxonomy service — port of Elvis's adaptive taxonomy system.

Replaces CLARA_2's substring/term-matching classification
(apps/api/app/services/taxonomies.py:364-425) with embedding-based semantic
mapping + adaptive discovery + graduated-authority governance.

Ports:
  - mapSignalToNode (enrich-signal/index.ts:19-43) -> map_signal_to_node
  - evolve-taxonomy (evolve-taxonomy/index.ts) -> discover_themes
  - apply_taxonomy_governance (SQL function) -> apply_governance (SQL RPC call)

Uses apps/api/app/services/ai.py for embeddings (provider-agnostic, local-first).
"""

from __future__ import annotations

import logging
import math
import os
from typing import Any

from app.services.ai import AIProviderError, call_tool, embed, to_vector_literal

logger = logging.getLogger(__name__)

# Cosine thresholds are EMBEDDER-SPECIFIC (the Elvis defaults were tuned under
# text-embedding-004): similarity distributions shift across models, so these
# do not survive an AI_EMBED_MODEL swap. Recalibrate with
# scripts/calibrate_embed_thresholds.py and override via env.
MAP_THRESHOLD = float(os.getenv("TAXONOMY_MAP_THRESHOLD", "0.55"))  # mapping floor
CLUSTER_EPS = float(os.getenv("TAXONOMY_CLUSTER_EPS", "0.70"))  # discovery clustering
MERGE_EPS = float(os.getenv("TAXONOMY_MERGE_EPS", "0.95"))  # governance auto-merge
MIN_CLUSTER = 3  # minimum cluster size for discovery (Elvis default)

NAME_TOOL = {
    "type": "function",
    "function": {
        "name": "name_theme",
        "description": "Name a cluster of related customer feedback as a single theme",
        "parameters": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "short snake_case theme name, e.g. refund_delay",
                },
                "description": {
                    "type": "string",
                    "description": "one sentence describing the theme",
                },
            },
            "required": ["name", "description"],
        },
    },
}


def cosine_sim(a: list[float], b: list[float]) -> float:
    """Cosine similarity between two vectors."""
    dot = sum(x * y for x, y in zip(a, b, strict=False))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def cluster_by_threshold(
    vectors: list[list[float]],
    threshold: float,
    min_size: int,
) -> list[list[int]]:
    """Greedy cosine-threshold clustering — port of evolve-taxonomy:19-31.

    Returns a list of clusters, each being a list of vector indices.
    """  # noqa: E501
    used = [False] * len(vectors)
    clusters: list[list[int]] = []

    for i in range(len(vectors)):
        if used[i]:
            continue
        group = [i]
        used[i] = True
        for j in range(i + 1, len(vectors)):
            if not used[j] and cosine_sim(vectors[i], vectors[j]) >= threshold:
                group.append(j)
                used[j] = True
        if len(group) >= min_size:
            clusters.append(group)

    return clusters


def centroid(vectors: list[list[float]]) -> list[float]:
    """Compute the centroid (mean) of a list of vectors."""
    if not vectors:
        return []
    dim = len(vectors[0])
    out = [0.0] * dim
    for v in vectors:
        for i in range(dim):
            out[i] += v[i]
    return [x / len(vectors) for x in out]


def avg_cohesion(vectors: list[list[float]]) -> float:
    """Average pairwise cosine similarity within a cluster — port of evolve-taxonomy:37-41."""
    if len(vectors) < 2:
        return 1.0
    total = 0.0
    n = 0
    for i in range(len(vectors)):
        for j in range(i + 1, len(vectors)):
            total += cosine_sim(vectors[i], vectors[j])
            n += 1
    return total / n if n > 0 else 1.0


def slugify(s: str) -> str:
    """Slugify a string — port of evolve-taxonomy:42-44."""
    import re

    return re.sub(r"[^a-z0-9]+", "_", s.strip().lower()).strip("_")


def map_signal_to_node(
    conn,
    workspace_id: int,
    signal_id: str,
    text: str,
) -> str | None:
    """Embed signal text and map to the closest active taxonomy node.

    Port of mapSignalToNode (enrich-signal/index.ts:19-43).
    Uses pgvector's match_taxonomy_nodes RPC via the provided psycopg connection.

    Returns the node_id if mapped (similarity >= MAP_THRESHOLD), else None.
    """
    if not text:
        return None

    try:
        vectors = embed(text)
    except AIProviderError:
        logger.warning(
            "Embedding failed for signal %s, skipping taxonomy mapping",
            signal_id, exc_info=True,
        )
        return None

    vec_literal = to_vector_literal(vectors[0])

    with conn.cursor() as cur:
        cur.execute(
            "SELECT id, name, similarity FROM match_taxonomy_nodes(%s, %s::vector, 5)",
            (workspace_id, vec_literal),
        )
        matches = cur.fetchall()

    if not matches:
        return None

    node_id, node_name, similarity = matches[0]
    if similarity < MAP_THRESHOLD:
        return None

    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO signal_node_map (signal_id, node_id, workspace_id, score, mapped_by)
            VALUES (%s, %s, %s, %s, 'system_auto')
            ON CONFLICT (signal_id, node_id) DO NOTHING
            """,
            (signal_id, str(node_id), workspace_id, similarity),
        )
        cur.execute(
            """
            UPDATE taxonomy_nodes
            SET times_matched = times_matched + 1, last_matched_at = now()
            WHERE id = %s
            """,
            (str(node_id),),
        )
    conn.commit()

    logger.debug("Mapped signal %s to node '%s' (sim=%.3f)", signal_id, node_name, similarity)
    return str(node_id)


def discover_themes(
    conn,
    workspace_id: int,
    *,
    limit: int = 200,
) -> dict[str, Any]:
    """Discover new taxonomy themes from unmapped signals.

    Port of evolve-taxonomy edge function. Embeds unmapped signals, clusters
    them by cosine similarity, names each cluster via LLM, and inserts as
    candidate taxonomy nodes.

    Returns {scanned, clusters, candidates}.
    """
    with conn.cursor() as cur:
        cur.execute(
            "SELECT signal_id, text_content FROM unmapped_signals(%s, %s)",
            (workspace_id, limit),
        )
        rows = cur.fetchall()

    if len(rows) < MIN_CLUSTER:
        return {"scanned": len(rows), "clusters": 0, "candidates": 0}

    texts = [r[1] for r in rows if r[1]]
    if len(texts) < MIN_CLUSTER:
        return {"scanned": len(rows), "clusters": 0, "candidates": 0}

    try:
        vectors = embed(texts)
    except AIProviderError:
        logger.warning("Embedding failed for theme discovery, aborting", exc_info=True)
        return {"scanned": len(rows), "clusters": 0, "candidates": 0, "error": "embedding_failed"}

    clusters = cluster_by_threshold(vectors, CLUSTER_EPS, MIN_CLUSTER)
    candidates = 0

    for idxs in clusters:
        cluster_vecs = [vectors[i] for i in idxs]
        cluster_sigs = [{"id": rows[i][0], "text": rows[i][1]} for i in idxs]
        c = centroid(cluster_vecs)

        # Find parent node via nearest active node
        vec_literal = to_vector_literal(c)
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, level FROM match_taxonomy_nodes(%s, %s::vector, 1)",
                (workspace_id, vec_literal),
            )
            near = cur.fetchone()
        parent_id = str(near[0]) if near else None
        parent_level = near[1] if near else 0
        level = min(parent_level + 1, 3)

        # Name the cluster via LLM (best-effort fallback)
        try:
            named = call_tool(
                system="You name clusters of related customer feedback as one concise theme.",
                user="Feedback in this cluster:\n"
                + "\n".join(f"- {s['text']}" for s in cluster_sigs),
                tool=NAME_TOOL,
                tool_name="name_theme",
                trace_name="discover:name_theme",
            )
        except AIProviderError:
            lead = " ".join((cluster_sigs[0]["text"] or "theme").split()[:4])
            named = {"name": lead, "description": "Auto-discovered theme — rename in review."}

        slug = slugify(named.get("name", ""))
        if not slug:
            continue

        cohesion = avg_cohesion(cluster_vecs)
        vec_literal_insert = to_vector_literal(c)

        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO taxonomy_nodes
                  (workspace_id, parent_id, level, name, slug, description,
                   status, origin, confidence, embedding, evidence)
                VALUES (%s, %s, %s, %s, %s, %s, 'candidate', 'discovered', %s, %s::vector, %s)
                ON CONFLICT (workspace_id, parent_id, slug) DO NOTHING
                """,
                (
                    workspace_id,
                    parent_id,
                    level,
                    named.get("name", ""),
                    slug,
                    named.get("description", ""),
                    cohesion,
                    vec_literal_insert,
                    {
                        "signal_ids": [s["id"] for s in cluster_sigs],
                        "samples": [s["text"] for s in cluster_sigs[:5]],
                        "size": len(cluster_sigs),
                        "cohesion": cohesion,
                    },
                ),
            )
        candidates += 1

    conn.commit()
    return {"scanned": len(rows), "clusters": len(clusters), "candidates": candidates}


def apply_governance(
    conn,
    workspace_id: int,
    *,
    auto_promote: float = 0.80,
    min_size: int = 5,
    merge_eps: float | None = None,
    stale_days: int = 90,
) -> dict[str, int]:
    """Apply taxonomy governance — calls the SQL function apply_taxonomy_governance.

    Auto-promotes candidates above confidence/size thresholds, auto-merges
    near-duplicate discovered nodes, and archives stale discovered nodes.
    Never touches uploaded taxonomy.
    """
    if merge_eps is None:
        merge_eps = MERGE_EPS
    with conn.cursor() as cur:
        cur.execute(
            "SELECT apply_taxonomy_governance(%s, %s, %s, %s, %s)",
            (workspace_id, auto_promote, min_size, merge_eps, stale_days),
        )
        result = cur.fetchone()
    conn.commit()

    if result and result[0]:
        import json

        parsed = json.loads(result[0]) if isinstance(result[0], str) else result[0]
        return {
            "promoted": int(parsed.get("promoted", 0)),
            "merged": int(parsed.get("merged", 0)),
            "archived": int(parsed.get("archived", 0)),
        }
    return {"promoted": 0, "merged": 0, "archived": 0}
