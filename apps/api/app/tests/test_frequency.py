"""Tests for frequency analysis — time-decayed frequency + trend detection."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.services.frequency import (
    frequency_factors,
    time_decayed_frequency,
    trend_label,
)

NOW = datetime(2026, 6, 24, 12, 0, 0, tzinfo=UTC)


def _signal(days_ago: float, *, source: str = "zendesk", tags: list[str] | None = None) -> dict:
    ts = NOW - timedelta(days=days_ago)
    return {
        "id": f"sig-{days_ago}",
        "timestamp": ts.isoformat(),
        "source": source,
        "tags": tags or ["checkout_failure"],
        "text": "test",
    }


class TestTimeDecayedFrequency:
    def test_empty_signals(self) -> None:
        assert time_decayed_frequency([], now=NOW) == 0.0

    def test_fresh_signal_full_weight(self) -> None:
        sig = _signal(0)
        assert time_decayed_frequency([sig], half_life_days=30, now=NOW) == 1.0

    def test_signal_at_half_life(self) -> None:
        sig = _signal(30)
        result = time_decayed_frequency([sig], half_life_days=30, now=NOW)
        assert abs(result - 0.5) < 0.01

    def test_signal_at_two_half_lives(self) -> None:
        sig = _signal(60)
        result = time_decayed_frequency([sig], half_life_days=30, now=NOW)
        assert abs(result - 0.25) < 0.01

    def test_burst_today_scores_higher_than_spread(self) -> None:
        burst = [_signal(0) for _ in range(10)]
        spread = [_signal(d) for d in range(0, 180, 18)]

        burst_score = time_decayed_frequency(burst, half_life_days=30, now=NOW)
        spread_score = time_decayed_frequency(spread, half_life_days=30, now=NOW)

        assert burst_score > spread_score * 2

    def test_no_timestamp_treated_as_recent(self) -> None:
        sigs = [{"id": "s1", "text": "no ts"}, {"id": "s2", "text": "no ts"}]
        assert time_decayed_frequency(sigs, now=NOW) == 2.0

    def test_custom_half_life(self) -> None:
        sig = _signal(15)
        result = time_decayed_frequency([sig], half_life_days=15, now=NOW)
        assert abs(result - 0.5) < 0.01

    def test_mixed_old_and_new(self) -> None:
        sigs = [_signal(0), _signal(0), _signal(90)]
        result = time_decayed_frequency(sigs, half_life_days=30, now=NOW)
        # 1.0 + 1.0 + 0.5^3 = 2.125
        assert abs(result - 2.125) < 0.01


class TestTrendLabel:
    def test_empty_returns_stable(self) -> None:
        assert trend_label([], now=NOW) == "stable"

    def test_all_recent_returns_new(self) -> None:
        sigs = [_signal(1), _signal(2), _signal(3)]
        assert trend_label(sigs, recent_window_days=7, baseline_window_days=30, now=NOW) == "new"

    def test_rising_trend(self) -> None:
        # 10 signals in recent 7 days, 2 in baseline 30 days before
        recent = [_signal(d) for d in range(0, 7)]
        baseline = [_signal(d) for d in range(8, 10)]
        sigs = recent + baseline
        assert trend_label(sigs, recent_window_days=7, baseline_window_days=30, now=NOW) == "rising"

    def test_falling_trend(self) -> None:
        # 1 signal in recent 7 days, 10 in baseline 30 days before
        recent = [_signal(1)]
        baseline = [_signal(d) for d in range(10, 20)]
        sigs = recent + baseline
        assert trend_label(sigs, recent_window_days=7, baseline_window_days=30, now=NOW) == "falling"

    def test_stable_trend(self) -> None:
        # Similar counts in both windows
        recent = [_signal(d) for d in range(0, 5)]
        baseline = [_signal(d) for d in range(8, 13)]
        sigs = recent + baseline
        assert trend_label(sigs, recent_window_days=7, baseline_window_days=30, now=NOW) == "stable"

    def test_no_timestamp_treated_as_recent(self) -> None:
        sigs = [{"id": "s1", "text": "no ts"}, {"id": "s2", "text": "no ts"}]
        assert trend_label(sigs, now=NOW) == "new"


class TestFrequencyFactors:
    def test_empty_signals(self) -> None:
        result = frequency_factors([], now=NOW)
        assert result["raw_count"] == 0
        assert result["decayed_frequency"] == 0.0
        assert result["trend"] == "stable"
        assert result["first_seen"] is None
        assert result["last_seen"] is None
        assert result["source_count"] == 0

    def test_full_breakdown(self) -> None:
        sigs = [
            _signal(1, source="zendesk"),
            _signal(3, source="zendesk"),
            _signal(5, source="intercom"),
        ]
        result = frequency_factors(sigs, now=NOW)

        assert result["raw_count"] == 3
        assert result["decayed_frequency"] > 0
        assert result["trend"] == "new"
        assert result["first_seen"] is not None
        assert result["last_seen"] is not None
        assert result["source_count"] == 2

    def test_source_count_distinct(self) -> None:
        sigs = [
            _signal(1, source="zendesk"),
            _signal(2, source="zendesk"),
            _signal(3, source="zendesk"),
        ]
        result = frequency_factors(sigs, now=NOW)
        assert result["source_count"] == 1

    def test_first_and_last_seen(self) -> None:
        sigs = [_signal(10), _signal(1), _signal(5)]
        result = frequency_factors(sigs, now=NOW)
        # first_seen = 10 days ago, last_seen = 1 day ago
        assert "2026-06-14" in result["first_seen"]
        assert "2026-06-23" in result["last_seen"]
