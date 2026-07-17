"""Regression: no taxonomy/terminology match must never yield a tautological
hypothesis like "General friction is likely driven by general"."""

from app.domain.models import ProblemCandidate
from app.services.taxonomies import generate_root_cause_analysis


def _candidate(journey_stage: str) -> ProblemCandidate:
    return ProblemCandidate(
        candidate_id="cand-1",
        title="General friction",
        journey="General",
        journey_stage=journey_stage,
        signal_count=3,
        customer_count=2,
        account_count=2,
        sources=["csv_import"],
        languages=["en"],
        first_seen="2026-07-01T00:00:00Z",
        last_seen="2026-07-02T00:00:00Z",
        confidence=0.6,
        evidence=[],
        root_cause_hypothesis="",
        suggested_owner="cx_lead",
        suggested_action="review",
    )


def test_no_classification_abstains_instead_of_tautology() -> None:
    analysis = generate_root_cause_analysis(
        candidate=_candidate("General"),
        signals=[],
        classifications=[],
        dictionary_terms=[],
    )
    assert "driven by general" not in analysis.hypothesis.lower()
    assert "insufficient evidence" in analysis.hypothesis.lower()
