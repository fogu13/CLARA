"""Tests for the evaluation harness."""

from __future__ import annotations

from app.evals.harness import (
    EvalHarness,
    _precision_recall_f1,
    _tags_match,
    bootstrap_ci,
    check_hallucination,
    check_pii_leak,
    load_golden_set,
    mcnemar_exact,
)


class TestSplits:
    def test_split_filter_partitions_golden_set(self) -> None:
        opt = load_golden_set(split="optimization")
        held = load_golden_set(split="held_out")
        all_items = load_golden_set()
        assert opt and held
        assert len(opt) + len(held) == len(all_items)


class TestBootstrapCI:
    def test_all_correct_ci_is_one(self) -> None:
        lo, hi = bootstrap_ci([1, 1, 1, 1, 1])
        assert lo == 1.0 and hi == 1.0

    def test_ci_brackets_the_mean(self) -> None:
        per_item = [1, 0, 1, 0, 1, 1, 0, 1, 0, 1]  # mean 0.6
        lo, hi = bootstrap_ci(per_item)
        assert 0.0 <= lo <= 0.6 <= hi <= 1.0

    def test_deterministic(self) -> None:
        data = [1, 0, 1, 1, 0]
        assert bootstrap_ci(data) == bootstrap_ci(data)


class TestMcNemar:
    def test_b_significantly_better(self) -> None:
        # A wrong / B right on 10 items, none the other way -> highly significant
        a = [False] * 10
        b = [True] * 10
        b_only, c_only, p = mcnemar_exact(a, b)
        assert b_only == 0 and c_only == 10
        assert p < 0.05

    def test_no_discordance_is_not_significant(self) -> None:
        a = [True, False, True]
        b_only, c_only, p = mcnemar_exact(a, a)
        assert b_only == 0 and c_only == 0 and p == 1.0


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


class TestFuzzyTagMatch:
    def test_near_miss_tag_matches_when_fuzzy(self) -> None:
        # payment_failure vs payment_error share the `payment` stem.
        assert _tags_match("payment_failure", "payment_error") is True
        p, r, f1 = _precision_recall_f1(["payment_failure"], ["payment_error"], fuzzy=True)
        assert p == 1.0 and r == 1.0 and f1 == 1.0

    def test_near_miss_tag_misses_when_exact(self) -> None:
        p, r, _ = _precision_recall_f1(["payment_failure"], ["payment_error"], fuzzy=False)
        assert p == 0.0 and r == 0.0

    def test_unrelated_tags_do_not_match(self) -> None:
        assert _tags_match("weather_anomaly", "payment_error") is False
        p, r, _ = _precision_recall_f1(["weather_anomaly"], ["payment_error"], fuzzy=True)
        assert p == 0.0 and r == 0.0

    def test_short_tokens_stay_exact_under_fuzzy(self) -> None:
        # Single-char tags can't fuzzy-match, so behaviour matches exact scoring.
        p, r, _ = _precision_recall_f1(["a", "b"], ["a", "c"], fuzzy=True)
        assert p == 0.5 and r == 0.5


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

        assert result.total_signals == len(load_golden_set())
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
        n = len(golden)
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

        assert result.sentiment_accuracy == (n - 2) / n  # 2 flipped
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
        assert report["total_signals"] == len(load_golden_set())
        assert report["enrichment"]["sentiment_accuracy"] == 1.0

    def test_empty_golden_set(self) -> None:
        harness = EvalHarness(golden_set=[])
        result = harness.run_enrichment_eval()
        assert result.total_signals == 0
