"""R5: burst statistic + BH-FDR gate on the emerging report (science review F5)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.domain.models import (
    Evidence,
    ProblemCandidate,
    SignalRecord,
)
from app.services.emerging import (
    benjamini_hochberg,
    build_emerging_problem_report,
    burst_p_value,
)


def _iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _candidate(cid: str, signal_ids: list[str], score: float = 0.8) -> ProblemCandidate:
    now = datetime.now(timezone.utc)
    return ProblemCandidate(
        candidate_id=cid,
        title=f"Candidate {cid}",
        journey="onboarding",
        journey_stage="verification",
        signal_count=len(signal_ids),
        sources=["app_store", "trustpilot"],  # corroborated
        languages=["de"],
        customer_count=len(signal_ids),
        account_count=1,
        first_seen=_iso(now - timedelta(days=30)),
        last_seen=_iso(now),
        confidence=0.8,
        evidence=[
            Evidence(
                signal_id=sid, source="app_store", language="de", excerpt="x",
                customer_id=f"c-{sid}", account_id="public", timestamp=_iso(now),
            )
            for sid in signal_ids
        ],
        root_cause_hypothesis="verification backlog",
        suggested_owner="onboarding",
        suggested_action="investigate",
        emerging_problem_score=score,
    )


def _signals(prefix: str, days_ago: list[int]) -> list[SignalRecord]:
    now = datetime.now(timezone.utc)
    return [
        SignalRecord(
            signal_id=f"{prefix}-{i}",
            feedback_text="Verifizierung haengt fest.",
            timestamp=_iso(now - timedelta(days=d)),
        )
        for i, d in enumerate(days_ago)
    ]


class TestBurstMath:
    def test_no_events_is_not_a_burst(self) -> None:
        assert burst_p_value(0, 0) == 1.0

    def test_all_recent_events_is_a_burst(self) -> None:
        # 6 signals, all in the last 7 days, none in the prior 28: p = 0.2^6.
        assert burst_p_value(6, 0) < 0.001

    def test_steady_rate_is_not_a_burst(self) -> None:
        # 2 recent / 8 baseline matches the 7:28 window ratio exactly.
        assert burst_p_value(2, 8) > 0.3

    def test_bh_is_monotone_and_order_preserving(self) -> None:
        q = benjamini_hochberg([0.01, 0.04, 0.9])
        assert q[0] <= q[1] <= q[2]
        assert q[2] > 0.5


class TestReportGate:
    def test_steady_presence_is_held_at_watch(self) -> None:
        # High score, corroborated, but the rate matches its own baseline:
        # presence, not emergence -> watch, with the reason as a driver.
        sigs = _signals("s", days_ago=[1, 5, 10, 14, 17, 21, 24, 27, 30, 33])
        cand = _candidate("CAND-STEADY", [s.signal_id for s in sigs])
        report = build_emerging_problem_report([cand], sigs)
        assert report.signals[0].trend_label == "watch"
        assert any("presence, not emergence" in d for d in report.signals[0].drivers)

    def test_genuine_burst_reaches_action(self) -> None:
        sigs = _signals("b", days_ago=[0, 1, 1, 2, 3, 4])  # all within 7d
        cand = _candidate("CAND-BURST", [s.signal_id for s in sigs])
        report = build_emerging_problem_report([cand], sigs)
        assert report.signals[0].trend_label == "action"
        assert report.signals[0].burst_q is not None
        assert report.signals[0].burst_q <= 0.10

    def test_no_signals_keeps_legacy_behaviour(self) -> None:
        cand = _candidate("CAND-LEGACY", ["missing-1", "missing-2", "missing-3"])
        report = build_emerging_problem_report([cand])
        assert report.signals[0].trend_label == "action"  # legacy gate only
        assert report.signals[0].burst_q is None
