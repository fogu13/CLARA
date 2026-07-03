"""Frequency analysis — time-decayed frequency + trend detection.

Replaces raw `len(signals)` in severity computation with a time-aware metric
that weights recent signals higher than old ones, and detects whether a
cluster is rising, falling, stable, or new.

Functions:
  - time_decayed_frequency(signals) -> float: exponential decay weighting
  - trend_label(signals) -> str: rising/falling/stable/new
  - frequency_factors(signals) -> dict: full frequency breakdown for insights
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import Any

logger = logging.getLogger(__name__)

DAY_SECONDS = 86_400
DEFAULT_HALF_LIFE_DAYS = 30
DEFAULT_RECENT_WINDOW_DAYS = 7
DEFAULT_BASELINE_WINDOW_DAYS = 30


def _parse_timestamp(ts: str | None) -> datetime | None:
    """Parse an ISO timestamp, returning None on failure."""
    if not ts:
        return None
    try:
        parsed = datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None
    # Coerce to tz-aware UTC. Timestamps without an offset parse as naive, and mixing
    # naive + aware in min()/max() (frequency_factors) raises TypeError; the decay math
    # also compares against an aware `now`.
    return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=UTC)


def _signal_timestamp(signal: dict[str, Any]) -> datetime | None:
    """Extract a timestamp from a signal dict, checking common field names."""
    for key in ("timestamp", "recorded_at", "created_at", "ingested_at"):
        ts = signal.get(key)
        if ts:
            parsed = _parse_timestamp(str(ts))
            if parsed:
                return parsed
    return None


def time_decayed_frequency(
    signals: list[dict[str, Any]],
    *,
    half_life_days: float = DEFAULT_HALF_LIFE_DAYS,
    now: datetime | None = None,
) -> float:
    """Compute time-decayed frequency — weights recent signals higher.

    Each signal contributes 0.5^(age_days / half_life) to the total.
    A burst of 10 signals today scores much higher than 10 signals
    spread over 6 months.

    Args:
        signals: list of signal dicts with a timestamp field
        half_life_days: days for a signal's weight to halve (default 30)
        now: reference time (defaults to current UTC)

    Returns:
        float — the decayed frequency score (higher = more recent activity)
    """
    if not signals:
        return 0.0

    if now is None:
        now = datetime.now(UTC)

    total = 0.0
    for signal in signals:
        ts = _signal_timestamp(signal)
        if ts is None:
            # No timestamp — treat as recent (weight = 1.0)
            total += 1.0
            continue

        # Ensure both are timezone-aware for subtraction
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=UTC)
        if now.tzinfo is None:
            now = now.replace(tzinfo=UTC)

        age_days = max(0.0, (now - ts).total_seconds() / DAY_SECONDS)
        weight = 0.5 ** (age_days / half_life_days)
        total += weight

    return round(total, 4)


def trend_label(
    signals: list[dict[str, Any]],
    *,
    recent_window_days: int = DEFAULT_RECENT_WINDOW_DAYS,
    baseline_window_days: int = DEFAULT_BASELINE_WINDOW_DAYS,
    now: datetime | None = None,
) -> str:
    """Detect trend by comparing recent vs baseline frequency.

    Compares the count of signals in the recent window (last N days) against
    the count in the baseline window (the period before that, same length as
    baseline_window_days). Returns:

      - "rising": recent frequency is significantly higher than baseline
      - "falling": recent frequency is significantly lower than baseline
      - "stable": frequencies are similar
      - "new": all signals are within the recent window (no baseline data)

    "Significantly" means a ratio difference of >= 1.5x (configurable by caller
    via the threshold parameter if needed in the future).
    """
    if not signals:
        return "stable"

    if now is None:
        now = datetime.now(UTC)
    if now.tzinfo is None:
        now = now.replace(tzinfo=UTC)

    recent_start = now - timedelta(days=recent_window_days)
    baseline_start = recent_start - timedelta(days=baseline_window_days)

    recent_count = 0
    baseline_count = 0
    has_baseline = False

    for signal in signals:
        ts = _signal_timestamp(signal)
        if ts is None:
            recent_count += 1
            continue
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=UTC)

        if ts >= recent_start:
            recent_count += 1
        elif ts >= baseline_start:
            baseline_count += 1
            has_baseline = True

    if not has_baseline or baseline_count == 0:
        return "new" if recent_count > 0 else "stable"

    # Normalize to per-day RATES before comparing — the recent window (e.g. 7 days) is
    # shorter than the baseline window (e.g. 30 days), so comparing raw counts made a
    # steady stream look like it was "falling" (7/30 < 0.5).
    recent_rate = recent_count / recent_window_days
    baseline_rate = baseline_count / baseline_window_days
    ratio = recent_rate / baseline_rate

    if ratio >= 1.5:
        return "rising"
    if ratio <= 0.5:
        return "falling"
    return "stable"


def frequency_factors(
    signals: list[dict[str, Any]],
    *,
    half_life_days: float = DEFAULT_HALF_LIFE_DAYS,
    recent_window_days: int = DEFAULT_RECENT_WINDOW_DAYS,
    baseline_window_days: int = DEFAULT_BASELINE_WINDOW_DAYS,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Compute full frequency breakdown for an insight.

    Returns:
        {
            raw_count: int,            # total signal count
            decayed_frequency: float,  # time-weighted frequency
            trend: str,                # rising/falling/stable/new
            first_seen: str | None,    # earliest timestamp
            last_seen: str | None,     # latest timestamp
            source_count: int,         # distinct sources
        }
    """
    if not signals:
        return {
            "raw_count": 0,
            "decayed_frequency": 0.0,
            "trend": "stable",
            "first_seen": None,
            "last_seen": None,
            "source_count": 0,
        }

    timestamps: list[datetime] = []
    sources: set[str] = set()

    for signal in signals:
        ts = _signal_timestamp(signal)
        if ts is not None:
            timestamps.append(ts)
        src = signal.get("source")
        if src:
            sources.add(str(src))

    first_seen = min(timestamps) if timestamps else None
    last_seen = max(timestamps) if timestamps else None

    return {
        "raw_count": len(signals),
        "decayed_frequency": time_decayed_frequency(
            signals, half_life_days=half_life_days, now=now
        ),
        "trend": trend_label(
            signals,
            recent_window_days=recent_window_days,
            baseline_window_days=baseline_window_days,
            now=now,
        ),
        "first_seen": first_seen.isoformat() if first_seen else None,
        "last_seen": last_seen.isoformat() if last_seen else None,
        "source_count": len(sources),
    }
