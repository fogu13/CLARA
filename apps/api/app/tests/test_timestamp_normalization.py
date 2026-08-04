"""Missing/invalid timestamps must never become a fabricated epoch date.

Regression for the external-review finding "two timestamps were invalid; one
surfaced as 1 January 1970". Epoch-stamped signals silently drop out of every
outcome-measurement window (the engine buckets by calendar day), so a defaulted
timestamp has to land in a real bucket AND stay flagged.
"""

from datetime import UTC, datetime

from app.connectors.app_store import AppStoreSourceConnector
from app.services.common import normalize_timestamp
from app.services.signals import signal_from_row


def _is_recent(timestamp: str) -> bool:
    parsed = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    return abs((datetime.now(UTC) - parsed).total_seconds()) < 60


def test_valid_timestamps_are_preserved_and_normalized_to_utc():
    assert normalize_timestamp("2026-08-04T10:30:00Z") == ("2026-08-04T10:30:00Z", False)
    # offset input is converted, not rejected
    value, defaulted = normalize_timestamp("2026-08-04T12:30:00+02:00")
    assert (value, defaulted) == ("2026-08-04T10:30:00Z", False)
    # naive input is assumed UTC rather than defaulted away
    assert normalize_timestamp("2026-08-04T10:30:00") == ("2026-08-04T10:30:00Z", False)


def test_missing_or_unparseable_timestamps_default_to_now_and_are_flagged():
    for bad in (None, "", "   ", "n/a", "2026-13-45", "not a date"):
        value, defaulted = normalize_timestamp(bad)
        assert defaulted is True, bad
        assert not value.startswith("1970"), bad
        assert _is_recent(value), bad


def test_csv_row_with_bad_timestamp_is_flagged_not_epoched():
    signal = signal_from_row({"feedback_text": "app crashes on login", "timestamp": "n/a"})
    assert not signal.timestamp.startswith("1970")
    assert signal.metadata.get("timestamp_defaulted") == "true"

    clean = signal_from_row(
        {"feedback_text": "works fine", "timestamp": "2026-08-01T09:00:00Z"}
    )
    assert clean.timestamp == "2026-08-01T09:00:00Z"
    assert "timestamp_defaulted" not in clean.metadata


def test_app_store_review_without_updated_field_is_flagged_not_epoched():
    connector = AppStoreSourceConnector()
    # Apple's RSS-JSON wraps every value as {"label": ...} — the mapper must
    # unwrap before parsing, or every real review defaults to ingestion time.
    entry = {
        "id": {"label": "42"},
        "content": {"label": "Transfers keep failing"},
        "im:rating": {"label": "1"},
    }
    mapped = connector._map_review(entry, country="de")
    assert not mapped["timestamp"].startswith("1970")
    assert mapped["metadata"]["timestamp_defaulted"] == "true"

    dated = connector._map_review(
        {**entry, "updated": {"label": "2026-08-02T08:00:00Z"}}, country="de"
    )
    assert dated["timestamp"] == "2026-08-02T08:00:00Z"
    assert "timestamp_defaulted" not in dated["metadata"]
