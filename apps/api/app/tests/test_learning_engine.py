"""Tests for the learning engine — confidence decay + retrieval + freshness."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from app.services.learning_engine import (
    build_learning_from_conclusion,
    decayed_confidence,
    is_stale,
    learning_freshness,
    rank_learnings,
)


def _now_ts() -> float:
    return datetime.now(UTC).timestamp()


def _make_learning(
    *,
    base_confidence: float = 0.8,
    days_ago: int = 0,
    half_life_days: int = 180,
    topic: str = "checkout_failure",
    pattern: str = "Fix checkout -> reduced complaints",
    winning_examples: list[str] | None = None,
    losing_examples: list[str] | None = None,
    summary: str = "Fixing the payment API reduced checkout complaints.",
) -> dict:
    validated = datetime.now(UTC) - timedelta(days=days_ago)
    return {
        "base_confidence": base_confidence,
        "last_validated_at": validated.isoformat(),
        "half_life_days": half_life_days,
        "topic": topic,
        "pattern": pattern,
        "summary": summary,
        "winning_examples": winning_examples or [],
        "losing_examples": losing_examples or [],
    }


class TestDecayedConfidence:
    def test_fresh_learning_keeps_full_confidence(self) -> None:
        learning = _make_learning(base_confidence=0.8, days_ago=0)
        assert decayed_confidence(learning) == pytest.approx(0.8, abs=0.01)

    def test_learning_at_half_life_has_half_confidence(self) -> None:
        learning = _make_learning(base_confidence=0.8, days_ago=180, half_life_days=180)
        assert decayed_confidence(learning) == pytest.approx(0.4, abs=0.02)

    def test_learning_at_two_half_lives_has_quarter_confidence(self) -> None:
        learning = _make_learning(base_confidence=0.8, days_ago=360, half_life_days=180)
        assert decayed_confidence(learning) == pytest.approx(0.2, abs=0.02)

    def test_zero_confidence_stays_zero(self) -> None:
        learning = _make_learning(base_confidence=0.0, days_ago=100)
        assert decayed_confidence(learning) == 0.0

    def test_no_validation_date_returns_base(self) -> None:
        learning = {"base_confidence": 0.7, "half_life_days": 180}
        assert decayed_confidence(learning) == 0.7

    def test_invalid_date_returns_base(self) -> None:
        learning = {"base_confidence": 0.6, "last_validated_at": "not-a-date"}
        assert decayed_confidence(learning) == 0.6

    def test_custom_half_life(self) -> None:
        learning = _make_learning(base_confidence=1.0, days_ago=30, half_life_days=30)
        assert decayed_confidence(learning) == pytest.approx(0.5, abs=0.02)


class TestIsStale:
    def test_fresh_learning_not_stale(self) -> None:
        learning = _make_learning(base_confidence=0.8, days_ago=10)
        assert is_stale(learning) is False

    def test_learning_past_half_life_is_stale(self) -> None:
        learning = _make_learning(base_confidence=0.8, days_ago=200, half_life_days=180)
        assert is_stale(learning) is True

    def test_zero_confidence_not_stale(self) -> None:
        learning = _make_learning(base_confidence=0.0, days_ago=365)
        assert is_stale(learning) is False


class TestLearningFreshness:
    def test_validated_for_fresh_learning(self) -> None:
        learning = _make_learning(base_confidence=0.8, days_ago=10)
        assert learning_freshness(learning) == "VALIDATED"

    def test_emerging_for_medium_age(self) -> None:
        # At 1.5x half-life: decayed = 0.8 * 0.5^1.5 ≈ 0.28
        # 0.28 >= 0.8 * 0.25 = 0.2 -> EMERGING
        learning = _make_learning(base_confidence=0.8, days_ago=270, half_life_days=180)
        freshness = learning_freshness(learning)
        assert freshness in ("EMERGING", "STALE")
        # Let's test a clearer case: 250 days with 180 half-life
        # decayed = 0.8 * 0.5^(250/180) = 0.8 * 0.5^1.39 ≈ 0.8 * 0.384 = 0.307
        # 0.307 >= 0.2 -> EMERGING
        learning2 = _make_learning(base_confidence=0.8, days_ago=250, half_life_days=180)
        assert learning_freshness(learning2) == "EMERGING"

    def test_stale_for_old_learning(self) -> None:
        # At 3x half-life: decayed = 0.8 * 0.5^3 = 0.1
        # 0.1 < 0.8 * 0.25 = 0.2 -> STALE
        learning = _make_learning(base_confidence=0.8, days_ago=540, half_life_days=180)
        assert learning_freshness(learning) == "STALE"

    def test_stale_for_zero_confidence(self) -> None:
        learning = _make_learning(base_confidence=0.0)
        assert learning_freshness(learning) == "STALE"


class TestRankLearnings:
    def test_ranks_by_token_overlap_weighted_by_confidence(self) -> None:
        learnings = [
            _make_learning(
                topic="checkout_failure",
                base_confidence=0.9,
                days_ago=1,
                summary="Fixing checkout reduced failures",
            ),
            _make_learning(
                topic="onboarding_friction",
                base_confidence=0.5,
                days_ago=300,
                summary="Onboarding improvements helped",
            ),
        ]

        results = rank_learnings(learnings, "checkout failure issue")

        assert len(results) >= 1
        assert results[0]["topic"] == "checkout_failure"

    def test_returns_empty_for_no_matches(self) -> None:
        learnings = [
            _make_learning(
                topic="billing_issue",
                pattern="Fix billing -> reduced complaints",
                summary="Billing problems",
            )
        ]
        results = rank_learnings(learnings, "checkout failure")
        assert results == []

    def test_returns_empty_for_empty_query(self) -> None:
        learnings = [_make_learning()]
        assert rank_learnings(learnings, "") == []

    def test_limits_to_k_results(self) -> None:
        learnings = [
            _make_learning(topic=f"checkout_{i}", summary=f"checkout issue {i}", days_ago=i)
            for i in range(5)
        ]
        results = rank_learnings(learnings, "checkout issue", k=2)
        assert len(results) == 2

    def test_fresher_learning_ranks_higher_with_same_overlap(self) -> None:
        learnings = [
            _make_learning(
                topic="checkout_failure",
                base_confidence=0.5,
                days_ago=300,  # stale
                summary="Old checkout learning",
            ),
            _make_learning(
                topic="checkout_failure",
                base_confidence=0.9,
                days_ago=1,  # fresh
                summary="Fresh checkout learning",
            ),
        ]

        results = rank_learnings(learnings, "checkout failure")

        assert results[0]["summary"] == "Fresh checkout learning"


class TestBuildLearningFromConclusion:
    def test_worked_conclusion_gets_high_confidence(self) -> None:
        learning = build_learning_from_conclusion(
            conclusion={
                "learning_status": "worked",
                "summary": "Fix resolved the issue",
                "limitations": "Only tested on mobile",
                "next_step": "Roll out to desktop",
                "reviewer": "analyst-1",
            },
            insight={"title": "Checkout crash", "tag": "checkout_failure", "category": "ux_friction"},
            outcome={"resolution_score": 0.9, "metric": "tag:checkout_failure", "status": "target_met"},
        )

        assert learning["learning_status"] == "worked"
        assert learning["base_confidence"] >= 0.6
        assert learning["topic"] == "checkout_failure"
        assert learning["evidence"]["resolution_score"] == 0.9
        assert len(learning["winning_examples"]) == 1

    def test_did_not_work_gets_low_confidence(self) -> None:
        learning = build_learning_from_conclusion(
            conclusion={
                "learning_status": "did_not_work",
                "summary": "Fix didn't help",
                "limitations": "None",
                "reviewer": "analyst-1",
            },
            insight={"title": "Checkout crash", "tag": "checkout"},
            outcome={"resolution_score": 0.1, "metric": "tag:checkout", "status": "not_improved"},
        )

        assert learning["learning_status"] == "did_not_work"
        assert learning["base_confidence"] == 0.3
        assert len(learning["losing_examples"]) == 1

    def test_inconclusive_gets_low_confidence(self) -> None:
        learning = build_learning_from_conclusion(
            conclusion={
                "learning_status": "inconclusive",
                "summary": "Can't tell yet",
                "limitations": "Need more data",
                "reviewer": "analyst-1",
            },
            insight={"title": "X", "tag": "y"},
            outcome={"resolution_score": 0.0, "metric": "y", "status": "not_measured"},
        )

        assert learning["base_confidence"] == 0.2

    def test_includes_evidence_block(self) -> None:
        learning = build_learning_from_conclusion(
            conclusion={
                "learning_status": "worked",
                "summary": "S",
                "limitations": "L",
                "reviewer": "r",
            },
            insight={"title": "T", "tag": "tag1", "severity": "high"},
            outcome={"resolution_score": 0.8, "metric": "tag:tag1", "status": "target_met"},
        )

        assert learning["evidence"]["insight_title"] == "T"
        assert learning["evidence"]["insight_severity"] == "high"
        assert learning["evidence"]["outcome_status"] == "target_met"

    def test_half_life_default(self) -> None:
        learning = build_learning_from_conclusion(
            conclusion={"learning_status": "worked", "summary": "S", "limitations": "L", "reviewer": "r"},
            insight={"title": "T", "tag": "t"},
            outcome={"resolution_score": 0.9, "metric": "t", "status": "target_met"},
        )

        assert learning["half_life_days"] == 180


class TestRetrievalGate:
    def test_system_derived_learnings_never_steer_synthesis(self) -> None:
        # Science review F7: learn_node auto-derives "worked" with
        # reviewer="system" from peak-selected outcomes; those must stay out of
        # prompt retrieval until a human validates them.
        from app.services.learning_engine import rank_learnings

        learnings = [
            {"topic": "checkout_failure", "summary": "retry worked",
             "base_confidence": 0.9, "reviewer": "system"},
            {"topic": "checkout_failure", "summary": "retry worked",
             "base_confidence": 0.4, "reviewer": "jane"},
            {"topic": "checkout_failure", "summary": "legacy record, no field",
             "base_confidence": 0.4},
        ]
        ranked = rank_learnings(learnings, "checkout failure", k=3)
        assert all(learning.get("reviewer") != "system" for learning in ranked)
        assert len(ranked) == 2
