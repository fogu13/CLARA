"""R6: volume-adjusted ITS readout + placebo check (science review F6)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.domain.models import SignalRecord
from app.services.outcome_engine import its_outcome_for_problem
from app.services.signals import build_candidates, promote_candidate

NOW = datetime.now(UTC).replace(hour=12, minute=0, second=0, microsecond=0)


def _iso(dt: datetime) -> str:
    return dt.isoformat().replace("+00:00", "Z")


def _signal(signal_id: str, *, days_ago: float, journey: str = "checkout",
            stage: str = "payment") -> SignalRecord:
    return SignalRecord(
        signal_id=signal_id,
        customer_id=f"C-{signal_id}",
        account_id="A-1",
        source="webhook",
        journey=journey,
        journey_stage=stage,
        feedback_text=f"Problem report {signal_id}",
        language="en",
        timestamp=_iso(NOW - timedelta(days=days_ago)),
    )


def _series(matched_per_day: list[int], other_per_day: list[int]) -> list[SignalRecord]:
    total_days = len(matched_per_day)
    signals: list[SignalRecord] = []
    for day, count in enumerate(matched_per_day):
        days_ago = total_days - day - 0.1
        signals.extend(
            _signal(f"m-{day}-{i}", days_ago=days_ago) for i in range(count)
        )
    for day, count in enumerate(other_per_day):
        days_ago = total_days - day - 0.1
        signals.extend(
            _signal(f"o-{day}-{i}", days_ago=days_ago, journey="onboarding",
                    stage="verification")
            for i in range(count)
        )
    return signals


def _run(matched_per_day: list[int], other_per_day: list[int], exec_day: int):
    signals = _series(matched_per_day, other_per_day)
    matched_only = [s for s in signals if s.journey == "checkout"]
    problem = promote_candidate(build_candidates(matched_only)[0])
    total_days = len(matched_per_day)
    executed_at = _iso(NOW - timedelta(days=total_days - exec_day))
    return its_outcome_for_problem(problem, signals, executed_at=executed_at, now=_iso(NOW))


def test_volume_drop_confound_is_caught_by_the_share_readout() -> None:
    # Matched signals track total inflow exactly (constant SHARE), but the whole
    # platform's volume halves post-action: the raw count "improves"; the
    # volume-adjusted share must not.
    matched = [4] * 20 + [2] * 12
    other = [12] * 20 + [6] * 12
    result = _run(matched, other, exec_day=20)
    assert result["method"] == "its"
    assert result["effect"] < -0.5
    adjusted = result["volume_adjusted"]
    assert adjusted["method"] == "its"
    assert adjusted["ci_low"] <= 0.0 <= adjusted["ci_high"]


def test_genuine_improvement_survives_the_share_readout() -> None:
    matched = [4] * 20 + [1] * 12
    other = [12] * 32
    result = _run(matched, other, exec_day=20)
    assert result["effect"] < 0
    adjusted = result["volume_adjusted"]
    assert adjusted["method"] == "its"
    assert adjusted["ci_high"] < 0


def test_placebo_is_quiet_on_a_flat_pre_window() -> None:
    matched = [3] * 20 + [1] * 12
    result = _run(matched, [0] * 32, exec_day=20)
    placebo = result.get("placebo")
    assert placebo is not None and placebo["method"] == "its"
    assert placebo["excludes_zero"] is False
    assert "warning" not in placebo


def test_placebo_flags_a_trending_pre_window() -> None:
    # Complaints already falling steeply before the action.
    matched = list(range(20, 0, -1)) + [1] * 12
    result = _run(matched, [0] * 32, exec_day=20)
    placebo = result.get("placebo")
    assert placebo is not None
    if placebo["method"] == "its" and placebo["excludes_zero"]:
        assert "warning" in placebo
