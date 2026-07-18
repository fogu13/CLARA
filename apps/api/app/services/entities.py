"""Per-entity attribution rollup — supplier/vendor/vertical accountability.

Convention: a signal's accountable external unit lives in ``metadata["entity"]``
— set by a connector, a webhook payload, or simply an ``entity`` column in a
CSV import (unmapped columns land in metadata as-is). Marketplace suppliers,
insurance verticals, delivery partners, BPO providers all fit.

The rollup answers "which entity drives which pain" from signals already
ingested — the July-2026 GetYourGuide teardown lesson: complaints map to
*named suppliers*, and a supplier intervention needs a per-entity view to be
proposed and a per-entity baseline to be measured. Tags are not yet persisted
on signal records, so the rollup keys on sentiment/urgency; theme-level
per-entity views ride on that once tag write-back lands.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any

from app.domain.models import SignalRecord

NEGATIVE_SENTIMENTS = {"negative", "mixed"}
URGENT = {"high", "critical"}


def entity_rollup(signals: list[SignalRecord]) -> list[dict[str, Any]]:
    """Group signals by metadata['entity'] and summarize each entity's pain.

    Signals without an entity are excluded (this is an attribution view, not
    a census — the caller's /signals list remains the census).
    """
    groups: dict[str, list[SignalRecord]] = defaultdict(list)
    for signal in signals:
        entity = (signal.metadata or {}).get("entity", "").strip()
        if entity:
            groups[entity].append(signal)

    rollup: list[dict[str, Any]] = []
    for entity, group in groups.items():
        enriched = [s for s in group if s.sentiment]
        negative = sum(1 for s in enriched if s.sentiment in NEGATIVE_SENTIMENTS)
        urgency_counts = Counter(s.urgency for s in group if s.urgency)
        timestamps = sorted(s.timestamp for s in group)
        rollup.append({
            "entity": entity,
            "signal_count": len(group),
            "enriched_count": len(enriched),
            "negative_count": negative,
            "negative_share": round(negative / len(enriched), 4) if enriched else None,
            "urgent_count": sum(
                count for urgency, count in urgency_counts.items() if urgency in URGENT
            ),
            "urgency_counts": dict(urgency_counts),
            "sources": sorted({s.source for s in group}),
            "first_seen": timestamps[0],
            "last_seen": timestamps[-1],
        })

    # Most pain first: urgent volume, then negative volume, then size.
    rollup.sort(
        key=lambda r: (r["urgent_count"], r["negative_count"], r["signal_count"]),
        reverse=True,
    )
    return rollup
