"""Tests for the evaluation harness."""

from __future__ import annotations

from app.evals.harness import (
    EvalHarness,
    _precision_recall_f1,
    check_hallucination,
    check_pii_leak,
    load_golden_set,
)


class TestGoldenSet:
    def test_golden_set_loads(self) -> None:
        data = load_golden_set()
        assert len(data) >= 10
        assert all("id" in item and "text" in item and "expected" in item for item in data)

    def test_golden_set_has_diverse_sentiments(self) -> None:
        data = load_golden_set()
        sentiments = {item["expected"]["sentiment"] for item in data}
        assert "positive" in sentiments
        assert "negative" in sentiments
        assert "mixed" in sentiments

    def test_golden_set_has_diverse_urgencies(self) -> None:
        data = load_golden_set()
        urgencies = {item["expected"]["urgency"] for item in data}
        assert "low" in urgencies
        assert "high" in urgencies or "critical" in urgencies


class TestPrecisionRecallF1:
    def test_perfect_match(self) -> None:
        p, r, f1 = _precision_recall_f1(["a", "b"], ["a", "b"])
        assert p == 1.0 and r == 1.0 and f1 == 1.0

    def test_partial_match(self) -> None:
        p, r, f1 = _precision_recall_f1(["a", "b"], ["a", "c"])
        assert p == 0.5  # 1 true positive, 1 false positive
        assert r == 0.5  # 1 true positive, 1 false negative

    def test_no_match(self) -> None:
        p, r, f1 = _precision_recall_f1(["x"], ["y"])
        assert p == 0.0 and r == 0.0 and f1 == 0.0

    def test_empty_both(self) -> None:
        p, r, f1 = _precision_recall_f1([], [])
        assert p == 1.0 and r == 1.0

    def test_predicted_empty(self) -> None:
        p, r, f1 = _precision_recall_f1([], ["a"])
        assert p == 0.0 and r == 0.0


class TestPIICheck:
    def test_detects_email(self) -> None:
        assert check_pii_leak("Contact john@example.com for details") == 1

    def test_detects_phone(self) -> None:
        assert check_pii_leak("Call +1 555 123 4567") >= 1

    def test_clean_text(self) -> None:
        assert check_pii_leak("The checkout page is broken") == 0

    def test_detects_multiple_pii(self) -> None:
        count = check_pii_leak("Email me at a@b.com or call 555-123-4567")
        assert count >= 2


class TestHallucinationCheck:
    def test_grounded_tags_not_hallucination(self) -> None:
        enrichment = {"tags": ["checkout_failure", "payment_error"]}
        text = "The checkout page crashes when I try to pay"
        assert check_hallucination(enrichment, text) is False

    def test_ungrounded_tags_are_hallucination(self) -> None:
        enrichment = {"tags": ["weather_anomaly", "space_station"]}
        text = "The checkout page crashes when I try to pay"
        assert check_hallucination(enrichment, text) is True

    def test_empty_tags_not_hallucination(self) -> None:
        enrichment = {"tags": []}
        text = "Some feedback"
        assert check_hallucination(enrichment, text) is False


class TestEvalHarness:
    def test_run_enrichment_eval_with_golden_set(self) -> None:
        harness = EvalHarness()
        result = harness.run_enrichment_eval()

        assert result.total_signals == 10
        # When using golden labels as both input and expected, accuracy should be 100%
        assert result.sentiment_accuracy == 1.0
        assert result.urgency_accuracy == 1.0
        assert result.tag_precision == 1.0
        assert result.tag_f1 == 1.0
        assert result.hallucination_rate == 0.0

    def test_run_enrichment_eval_with_actual_enrichments(self) -> None:
        harness = EvalHarness()
        # Simulate enrichments that get 8/10 sentiment right
        golden = load_golden_set()
        enrichments = []
        for i, item in enumerate(golden):
            expected = item["expected"]
            # Flip sentiment on 2 items to simulate errors
            sentiment = expected["sentiment"]
            if i < 2:
                sentiment = "neutral" if sentiment != "neutral" else "positive"
            enrichments.append({
                "id": item["id"],
                "sentiment": sentiment,
                "urgency": expected["urgency"],
                "tags": expected["tags"],
            })

        result = harness.run_enrichment_eval(enrichments=enrichments)

        assert result.sentiment_accuracy == 0.8  # 8/10 correct
        assert result.urgency_accuracy == 1.0

    def test_run_synthesis_eval(self) -> None:
        harness = EvalHarness()
        insights = [
            {
                "category": "ux_friction",
                "severity": "high",
                "confidence": 0.85,
                "suggested_actions": [
                    {"type": "create_ticket", "title": "Fix", "description": "Fix it", "priority": 1}
                ],
            },
            {
                "category": "churn_risk",
                "severity": "critical",
                "confidence": 0.9,
                "suggested_actions": [
                    {"type": "notify", "title": "Alert", "description": "Alert team", "priority": 1}
                ],
            },
        ]
        result = harness.run_synthesis_eval(insights=insights)

        assert result.total_insights == 2
        assert result.severity_accuracy == 1.0
        assert result.action_quality_score == 1.0
        assert result.avg_confidence > 0.8

    def test_full_eval_report(self) -> None:
        harness = EvalHarness()
        report = harness.run_full_eval()

        assert "enrichment" in report
        assert "synthesis" in report
        assert report["total_signals"] == 10
        assert report["enrichment"]["sentiment_accuracy"] == 1.0

    def test_empty_golden_set(self) -> None:
        harness = EvalHarness(golden_set=[])
        result = harness.run_enrichment_eval()
        assert result.total_signals == 0
