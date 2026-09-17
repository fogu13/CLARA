"""Regressions for external-review tranche 2: evidence grading, the emerging
corroboration floor, and normalized fallback-id hashing."""

from app.domain.models import ProblemCandidate
from app.services.emerging import emerging_signal_for_candidate
from app.services.outcome_engine import evidence_grade
from app.services.signals import _fallback_signal_id


class TestEvidenceGrade:
    def test_unmeasured_and_manual_are_grade_e(self) -> None:
        assert evidence_grade(comparison_method="randomized_holdout", measurement_source=None) == "E"
        assert evidence_grade(comparison_method="its_segmented_regression", measurement_source="manual") == "E"

    def test_instrumented_designs(self) -> None:
        # Realised designs only (13 Sep 2026 review, F4): CLARA produces no
        # holdout, so a contracted A design is graded on the data it has, an
        # uncontrolled before/after; an ITS is C only once the fit exists.
        assert evidence_grade(comparison_method="randomized_holdout", measurement_source="instrumented") == "D"
        assert evidence_grade(comparison_method="its_segmented_regression", measurement_source="instrumented") == "D"
        assert evidence_grade(comparison_method="its_segmented_regression", measurement_source="instrumented", realised_method="its") == "C"
        assert evidence_grade(comparison_method="before_after", measurement_source="instrumented") == "D"
        assert evidence_grade(comparison_method="pre_post_signal_rate", measurement_source="instrumented") == "D"

    def test_its_contract_that_fell_back_to_a_plain_delta_is_grade_d(self) -> None:
        # The contract promised segmented regression, but the series was too
        # sparse and the engine returned the labelled plain delta: the readout
        # that exists is an uncontrolled before/after, so it is graded D.
        assert (
            evidence_grade(
                comparison_method="its_segmented_regression",
                measurement_source="instrumented",
                realised_method="delta_insufficient_data",
            )
            == "D"
        )
        assert (
            evidence_grade(
                comparison_method="its_segmented_regression",
                measurement_source="instrumented",
                realised_method="its",
            )
            == "C"
        )
        # Manual/unmeasured stays E whatever the fit says.
        assert (
            evidence_grade(
                comparison_method="its_segmented_regression",
                measurement_source="manual",
                realised_method="its",
            )
            == "E"
        )


def _candidate(*, score: float, sources: list[str], customer_count: int) -> ProblemCandidate:
    return ProblemCandidate(
        candidate_id="cand-1",
        title="Checkout friction",
        journey="purchase",
        journey_stage="checkout",
        signal_count=8,
        customer_count=customer_count,
        account_count=0,
        sources=sources,
        languages=["en"],
        first_seen="2026-07-01T00:00:00Z",
        last_seen="2026-07-02T00:00:00Z",
        confidence=0.8,
        evidence=[],
        root_cause_hypothesis="",
        suggested_owner="cx_lead",
        suggested_action="review",
        emerging_problem_score=score,
    )


class TestEmergingCorroborationFloor:
    def test_high_score_without_corroboration_is_held_at_watch(self) -> None:
        signal = emerging_signal_for_candidate(
            _candidate(score=0.9, sources=["csv_import"], customer_count=0)
        )
        assert signal is not None
        assert signal.trend_label == "watch"
        assert any("Held at watch" in driver for driver in signal.drivers)

    def test_multi_source_high_score_is_action(self) -> None:
        signal = emerging_signal_for_candidate(
            _candidate(score=0.9, sources=["csv_import", "trustpilot"], customer_count=0)
        )
        assert signal is not None
        assert signal.trend_label == "action"

    def test_many_identified_customers_is_action(self) -> None:
        signal = emerging_signal_for_candidate(
            _candidate(score=0.9, sources=["csv_import"], customer_count=5)
        )
        assert signal is not None
        assert signal.trend_label == "action"


def test_fallback_id_hash_normalizes_case_and_whitespace() -> None:
    row_a = {"feedback_text": "Great  App ", "customer_id": "C1", "timestamp": "t", "source": "s"}
    row_b = {"feedback_text": "great app", "customer_id": "c1", "timestamp": "t", "source": "s"}
    assert _fallback_signal_id(row_a) == _fallback_signal_id(row_b)
