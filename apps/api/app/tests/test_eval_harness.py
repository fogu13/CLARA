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

    def test_short_token_tag_present_in_text_is_grounded(self) -> None:
        # "bug"/"ux" have no token longer than 3 chars; they must be grounded
        # via word-boundary match, not auto-flagged as hallucination.
        assert check_hallucination({"tags": ["bug"]}, "there is a bug in checkout") is False
        assert check_hallucination({"tags": ["app_bug"]}, "the bug ruins the app") is False

    def test_short_token_tag_absent_from_text_is_hallucination(self) -> None:
        # "bug" appears only inside "bugle", not as a word -> not grounded.
        assert check_hallucination({"tags": ["bug"]}, "the bugle sounds great") is True


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


class TestWilsonInterval:
    def test_perfect_stratum_is_not_degenerate(self) -> None:
        from app.evals.harness import wilson_interval

        lo, hi = wilson_interval(10, 10)
        assert lo < 1.0 and hi == 1.0  # the bootstrap would report [1.0, 1.0]

    def test_brackets_the_proportion_and_stays_in_unit_interval(self) -> None:
        from app.evals.harness import wilson_interval

        lo, hi = wilson_interval(66, 100)
        assert 0.56 < lo < 0.66 < hi < 0.75
        assert wilson_interval(0, 0) == (0.0, 0.0)
        assert wilson_interval(0, 7)[0] == 0.0


class TestHallucinationDenominator:
    """The heuristic is English-only, so its rate must be over ELIGIBLE (EN)
    items, and 'no eligible items' must read as not evaluated, never 0.0."""

    @staticmethod
    def _item(idx: int, language: str, text: str) -> dict:
        return {
            "id": f"h-{idx}",
            "text": text,
            "language": language,
            "expected": {"sentiment": "negative", "urgency": "low", "tags": ["checkout_failure"]},
        }

    def test_one_flagged_en_plus_one_excluded_de_is_rate_one(self) -> None:
        golden = [
            self._item(1, "en", "The checkout page crashes when I try to pay"),
            self._item(2, "de", "Die Bezahlung bricht im Warenkorb ab"),
        ]
        # Both enrichments carry tags with no grounding in the text; only the
        # EN item is eligible for the heuristic.
        enrichments = [
            {"id": "h-1", "sentiment": "negative", "urgency": "low", "tags": ["weather_anomaly"]},
            {"id": "h-2", "sentiment": "negative", "urgency": "low", "tags": ["weather_anomaly"]},
        ]
        r = EvalHarness(golden_set=golden).run_enrichment_eval(enrichments=enrichments)
        assert r.hallucination_eligible == 1
        # Per-item outcome by golden id (run_live aggregates it per split).
        assert r.hallucination_eligible_ids and len(r.hallucination_eligible_ids) == r.hallucination_eligible
        assert set(r.hallucination_flagged_ids) <= set(r.hallucination_eligible_ids)
        assert r.hallucination_excluded == 1
        assert r.hallucination_rate == 1.0  # the old n=2 denominator reported 0.5
        row = next(x for x in r.results if x.name == "hallucination_coverage")
        assert "1 eligible" in row.detail and "1 excluded" in row.detail

    def test_all_non_english_is_not_evaluated(self) -> None:
        golden = [self._item(1, "de", "Die App ist langsam"), self._item(2, "de", "Alles gut")]
        enrichments = [
            {"id": "h-1", "sentiment": "negative", "urgency": "low", "tags": ["slow_app"]},
            {"id": "h-2", "sentiment": "negative", "urgency": "low", "tags": ["fine"]},
        ]
        r = EvalHarness(golden_set=golden).run_enrichment_eval(enrichments=enrichments)
        assert r.hallucination_rate is None
        assert r.hallucination_eligible == 0
        assert r.hallucination_excluded == 2
        assert "not evaluated" in r.summary()
        assert "not evaluated" in str(next(x for x in r.results if x.name == "hallucination_rate"))
        assert EvalHarness(golden_set=golden).run_full_eval()["enrichment"]["hallucination_rate"] is None

    def test_zero_numerator_keeps_zero_with_right_denominators(self) -> None:
        golden = load_golden_set()
        r = EvalHarness(golden_set=golden).run_enrichment_eval()  # self-comparison
        n_en = sum(1 for g in golden if g.get("language", "en") == "en")
        assert r.hallucination_rate == 0.0
        assert r.hallucination_eligible == n_en
        assert r.hallucination_excluded == len(golden) - n_en
        assert r.hallucination_unassessed == 0
        assert r.hallucination_eligible > 0

    # ---- C18: an EN item the run returned nothing for (or tagged with
    # nothing) is neither grounded nor fabricated: it is unassessed and
    # leaves the eligible denominator.
    def test_all_en_items_dropped_is_not_evaluated_and_counted_unassessed(self) -> None:
        golden = [
            self._item(1, "en", "The checkout page crashes when I try to pay"),
            self._item(2, "en", "Support never answers my tickets"),
            self._item(3, "de", "Die Bezahlung bricht im Warenkorb ab"),
        ]
        r = EvalHarness(golden_set=golden).run_enrichment_eval(enrichments=[])
        assert r.hallucination_rate is None  # the old count read 0.0 over 2 "grounded" items
        assert r.hallucination_eligible == 0
        assert r.hallucination_unassessed == 2
        assert r.hallucination_excluded == 1
        assert "2 EN unassessed" in r.summary()
        assert EvalHarness(golden_set=golden).run_full_eval()["enrichment"]["hallucination_unassessed"] == 0

    def test_tagless_enrichment_is_unassessed_not_grounded(self) -> None:
        golden = [
            self._item(1, "en", "The checkout page crashes when I try to pay"),
            self._item(2, "en", "Support never answers my tickets"),
        ]
        enrichments = [
            {"id": "h-1", "sentiment": "negative", "urgency": "low", "tags": ["weather_anomaly"]},
            {"id": "h-2", "sentiment": "negative", "urgency": "low", "tags": []},
        ]
        r = EvalHarness(golden_set=golden).run_enrichment_eval(enrichments=enrichments)
        assert r.hallucination_eligible == 1 and r.hallucination_unassessed == 1
        assert r.hallucination_rate == 1.0  # the old denominator of 2 read 0.5
        row = next(x for x in r.results if x.name == "hallucination_coverage")
        assert "1 unassessed" in row.detail

    # ---- C7: eligibility is by normalised primary subtag, in one helper.
    def test_language_normalisation_shared_by_check_and_counter(self) -> None:
        from app.evals.harness import hallucination_eligible_language, language_primary_subtag

        assert language_primary_subtag("EN") == "en"
        assert language_primary_subtag("en-US") == "en"
        assert language_primary_subtag("en_GB") == "en"
        assert language_primary_subtag(" De ") == "de"
        assert language_primary_subtag(None) is None
        assert language_primary_subtag("") is None
        assert language_primary_subtag(3) is None
        assert hallucination_eligible_language("EN") and hallucination_eligible_language("en-US")
        assert not hallucination_eligible_language(None) and not hallucination_eligible_language("de-DE")
        ungrounded = {"tags": ["weather_anomaly"]}
        text = "The checkout page crashes when I try to pay"
        assert check_hallucination(ungrounded, text, language="EN") is True
        assert check_hallucination(ungrounded, text, language="en-US") is True
        assert check_hallucination(ungrounded, text, language="de-DE") is False
        assert check_hallucination(ungrounded, text, language=None) is False

        golden = [
            self._item(1, "EN", text),
            self._item(2, "en-US", text),
            {"id": "h-3", "text": text,
             "expected": {"sentiment": "negative", "urgency": "low", "tags": ["checkout_failure"]}},
        ]
        golden[2].pop("language", None)  # missing language: excluded, never assumed English
        enrichments = [{"id": f"h-{i}", "sentiment": "negative", "urgency": "low",
                        "tags": ["weather_anomaly"]} for i in (1, 2, 3)]
        r = EvalHarness(golden_set=golden).run_enrichment_eval(enrichments=enrichments)
        assert r.hallucination_eligible == 2 and r.hallucination_excluded == 1
        assert r.hallucination_rate == 1.0  # both EN variants flagged, the None item excluded
