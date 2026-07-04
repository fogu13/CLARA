"""Taxonomy hygiene — keeps the bootstrapped taxonomy alive without silent edits.

Three checks, all REPORT-only (the human acts through the existing merge /
review / rename flows — nothing is ever auto-applied, which is precisely the
governance stance that separates CLARA from "zero-maintenance taxonomy"
marketing):

  1. Near-duplicates: active categories whose label+terms embed too close
     together -> suggest a merge (the UI's merge mode does the rest).
  2. Stale proposals: bootstrap-proposed categories nobody reviewed for N days.
  3. Drifted categories: active categories whose terms match none of the recent
     signals — candidates for rename, term updates, or retirement.

Duplicate detection needs embeddings; when the AI provider is unavailable the
check degrades to reporting that it was skipped (never a silent gap).
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import Any

# Live module reference — reload-safe (see taxonomy_bootstrap).
import app.services.ai as ai
from app.domain.models import SignalRecord, TaxonomyCatalog
from app.services.semantic_taxonomy import cosine_sim
from app.services.taxonomies import searchable_text

logger = logging.getLogger(__name__)

DUPLICATE_SIMILARITY = 0.86
STALE_PROPOSAL_DAYS = 14
DRIFT_WINDOW_DAYS = 30



def _as_utc(parsed: datetime) -> datetime:
    """Naive timestamps must not crash the hygiene sweep with TypeError."""
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)

def _category_text(category: Any) -> str:
    return " ".join([category.label, category.description, *category.terms]).strip()


def _proposed_at(category: Any) -> datetime | None:
    for change in category.change_history:
        if change.operation.value == "propose":
            try:
                return _as_utc(datetime.fromisoformat(change.changed_at.replace("Z", "+00:00")))
            except ValueError:
                return None
    return None


def run_hygiene(
    catalogs: list[TaxonomyCatalog],
    signals: list[SignalRecord],
    *,
    now: datetime | None = None,
    duplicate_similarity: float = DUPLICATE_SIMILARITY,
    stale_days: int = STALE_PROPOSAL_DAYS,
    drift_window_days: int = DRIFT_WINDOW_DAYS,
) -> dict[str, Any]:
    """Compute the hygiene report across all catalogs. Report-only, idempotent."""
    now = now or datetime.now(UTC)

    # --- recent signal corpus for drift detection -----------------------------
    cutoff = now - timedelta(days=drift_window_days)
    recent_texts: list[str] = []
    for signal in signals:
        try:
            ts = _as_utc(datetime.fromisoformat(signal.timestamp.replace("Z", "+00:00")))
        except ValueError:
            continue
        if ts >= cutoff:
            recent_texts.append(searchable_text(signal).lower().replace("_", " "))

    duplicates: list[dict[str, Any]] = []
    stale_proposals: list[dict[str, Any]] = []
    drifted: list[dict[str, Any]] = []
    duplicates_skipped = False

    for catalog in catalogs:
        active = [c for c in catalog.categories if c.status == "active"]

        # 1 · Near-duplicate detection (embeddings; skip gracefully if AI is down).
        if len(active) >= 2:
            try:
                vectors = ai.embed([_category_text(c) for c in active])
                for i in range(len(active)):
                    for j in range(i + 1, len(active)):
                        similarity = cosine_sim(vectors[i], vectors[j])
                        if similarity >= duplicate_similarity:
                            duplicates.append(
                                {
                                    "taxonomy_type": catalog.taxonomy_type.value,
                                    "category_a": active[i].category_id,
                                    "label_a": active[i].label,
                                    "category_b": active[j].category_id,
                                    "label_b": active[j].label,
                                    "similarity": round(similarity, 3),
                                    "suggestion": "Review and merge via the taxonomy merge flow.",
                                }
                            )
            except ai.AIProviderError:
                logger.warning("Embedding unavailable — duplicate check skipped")
                duplicates_skipped = True

        # 2 · Stale proposals nobody reviewed.
        for category in catalog.categories:
            if category.status != "proposed":
                continue
            proposed_at = _proposed_at(category)
            if proposed_at is not None and (now - proposed_at) > timedelta(days=stale_days):
                stale_proposals.append(
                    {
                        "taxonomy_type": catalog.taxonomy_type.value,
                        "category_id": category.category_id,
                        "label": category.label,
                        "proposed_at": proposed_at.isoformat().replace("+00:00", "Z"),
                        "age_days": (now - proposed_at).days,
                        "suggestion": "Accept or reject — unreviewed proposals erode trust in the queue.",
                    }
                )

        # 3 · Drift: active categories whose terms match nothing recent.
        if recent_texts:
            for category in active:
                if category.locked:
                    continue  # locked = deliberate; not flagged
                # searchable_text joins free text with spaces; category terms often use
                # underscores ("identity_verification"). Normalize so a term matches
                # the text it was minted from instead of chronically drifting.
                terms = [
                    t.lower().replace("_", " ")
                    for t in [category.label, *category.terms]
                    if t.strip()
                ]
                if terms and not any(
                    term in text for term in terms for text in recent_texts
                ):
                    drifted.append(
                        {
                            "taxonomy_type": catalog.taxonomy_type.value,
                            "category_id": category.category_id,
                            "label": category.label,
                            "window_days": drift_window_days,
                            "suggestion": "No recent signals match — update terms, rename, or retire.",
                        }
                    )

    return {
        "generated_at": now.isoformat().replace("+00:00", "Z"),
        "duplicates": duplicates,
        "duplicates_skipped": duplicates_skipped,
        "stale_proposals": stale_proposals,
        "drifted_categories": drifted,
        "healthy": not (duplicates or stale_proposals or drifted),
    }
