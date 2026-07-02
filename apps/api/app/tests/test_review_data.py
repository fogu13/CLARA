"""Regression tests for the data-integrity fixes from the 2026-07-02 review."""

from __future__ import annotations

from types import SimpleNamespace

from app.evals.harness import EvalHarness
from app.services.contexts import parse_context_csv
from app.services.frequency import _parse_timestamp, frequency_factors
from app.services.journeys import parse_journey_event_csv
from app.services.postgres import _next_id
from app.services.signals import parse_signal_csv


class TestJiraDraftIdResumes:
    def test_next_id_resumes_with_correct_prefix(self) -> None:
        drafts = [SimpleNamespace(draft_id="JIRA-DRAFT-0003"),
                  SimpleNamespace(draft_id="JIRA-DRAFT-0007")]
        # correct prefix resumes at the max; the old "JIRA" prefix never matched -> 0
        assert _next_id(drafts, "draft_id", "JIRA-DRAFT") == 7
        assert _next_id(drafts, "draft_id", "JIRA") == 0  # documents the old bug


class TestCsvFallbackIds:
    HEADER = "feedback_text,customer_id,timestamp\n"

    def test_same_content_is_idempotent(self) -> None:
        csv = self.HEADER + "app crashes,c1,2024-01-01T00:00:00Z\n"
        a = parse_signal_csv(csv)[0].signal_id
        b = parse_signal_csv(csv)[0].signal_id
        assert a == b  # re-import stays stable

    def test_different_content_does_not_collide(self) -> None:
        # two DIFFERENT no-signal_id files: their first rows must not share an id
        id1 = parse_signal_csv(self.HEADER + "checkout broken,c1,2024-01-01T00:00:00Z\n")[0].signal_id
        id2 = parse_signal_csv(self.HEADER + "love the app,c2,2024-02-01T00:00:00Z\n")[0].signal_id
        assert id1 != id2  # old positional CSV-0001 collided -> second file lost


class TestHarnessNoGoldenInflation:
    def test_self_comparison_is_100pct(self) -> None:
        # None enrichments = self-comparison baseline (metric definition)
        r = EvalHarness().run_enrichment_eval()
        assert r.sentiment_accuracy == 1.0

    def test_missing_enrichments_score_wrong_not_inflated(self) -> None:
        # a real run that returned NOTHING must not score 100% via golden fallback
        r = EvalHarness().run_enrichment_eval(enrichments=[])
        assert r.sentiment_accuracy == 0.0
        assert r.urgency_accuracy == 0.0


class TestContextCsvProductOwner:
    def test_product_owner_is_parsed(self) -> None:
        csv = "customer_id,account_id,product_owner\nc1,a1,Jane Doe\n"
        rec = parse_context_csv(csv)[0]
        assert rec.product_owner == "Jane Doe"


class TestFrequencyTimestampCoercion:
    def test_timestamps_are_always_aware(self) -> None:
        # both naive-input and aware-input coerce to tz-aware, so min()/max() is safe
        assert _parse_timestamp("2024-01-01T00:00:00").tzinfo is not None
        assert _parse_timestamp("2024-01-01T00:00:00Z").tzinfo is not None

    def test_mixed_naive_and_aware_signals_do_not_crash(self) -> None:
        signals = [
            {"source": "a", "timestamp": "2024-01-01T00:00:00"},   # naive input
            {"source": "b", "timestamp": "2024-02-01T00:00:00Z"},  # aware input
        ]
        result = frequency_factors(signals)  # previously raised TypeError
        assert result["first_seen"] is not None and result["last_seen"] is not None


class TestJourneyCsvBadDuration:
    def test_non_numeric_duration_does_not_raise(self) -> None:
        csv = ("event_id,customer_id,event_name,duration_seconds\n"
               "e1,c1,login,not-a-number\n"
               "e2,c2,logout,12.5\n")
        events = parse_journey_event_csv(csv)  # previously raised ValueError -> HTTP 500
        assert events[0].duration_seconds is None
        assert events[1].duration_seconds == 12.5
