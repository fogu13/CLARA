"""Regression tests for the data-integrity fixes from the 2026-07-02 review."""

from __future__ import annotations

from types import SimpleNamespace

from app.evals.harness import EvalHarness
from app.services.contexts import parse_context_csv
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
