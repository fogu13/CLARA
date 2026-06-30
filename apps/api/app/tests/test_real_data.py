"""Tests for the real-data eval: combined-CSV parsing + star-proxy scoring.
No live LLM — enrichments are supplied directly."""

from __future__ import annotations

import json

from app.evals.real_data import (
    load_combined_csv,
    score_dataset,
    sentiment_agrees,
    star_to_sentiment,
)

# A combined CSV with a BOM, quoted "type" header, and one signal split across a
# qualitative + a quantitative (star) row sharing a public_signal_id.
_CSV = (
    '﻿"type",source,text,metric_name,metric_value,tags,recorded_at\n'
    'qualitative,app_store,"Checkout keeps failing and support never replies.",,,'
    '"{""public_signal_id"":""S1""}",2024-01-01T00:00:00Z\n'
    'quantitative,app_store,,star_rating_1_5,1,"{""public_signal_id"":""S1""}",2024-01-01T00:00:00Z\n'
    'qualitative,web,"Love the new dashboard, so clean.",,,'
    '"{""public_signal_id"":""S2""}",2024-01-02T00:00:00Z\n'
    'quantitative,web,,star_rating_1_5,5,"{""public_signal_id"":""S2""}",2024-01-02T00:00:00Z\n'
)


def _write(tmp_path, text):
    p = tmp_path / "x_combined_import.csv"
    p.write_text(text, encoding="utf-8")
    return p


class TestLoad:
    def test_merges_text_and_star_by_id(self, tmp_path) -> None:
        sigs = {s["id"]: s for s in load_combined_csv(_write(tmp_path, _CSV))}
        assert set(sigs) == {"S1", "S2"}
        assert sigs["S1"]["star"] == 1 and "Checkout" in sigs["S1"]["text"]
        assert sigs["S2"]["star"] == 5
        assert sigs["S1"]["source"] == "app_store"

    def test_drops_ids_without_text(self, tmp_path) -> None:
        rows = (
            '﻿"type",source,text,metric_name,metric_value,tags,recorded_at\n'
            'quantitative,x,,star_rating_1_5,3,"{""public_signal_id"":""only_rating""}",t\n'
        )
        assert load_combined_csv(_write(tmp_path, rows)) == []


class TestProxy:
    def test_star_to_sentiment(self) -> None:
        assert [star_to_sentiment(s) for s in (1, 2, 3, 4, 5, None)] == \
            ["negative", "negative", "neutral", "positive", "positive", None]

    def test_agreement_is_lenient_on_mixed(self) -> None:
        assert sentiment_agrees("mixed", "negative")   # low star, mixed read = ok
        assert sentiment_agrees("mixed", "neutral")
        assert not sentiment_agrees("mixed", "positive")  # praise must be positive
        assert sentiment_agrees("positive", "positive")
        assert not sentiment_agrees("positive", "negative")


class TestScore:
    def test_scores_proxy_grounding_and_urgency(self) -> None:
        signals = [
            {"id": "S1", "text": "Checkout keeps failing", "star": 1, "source": "a"},
            {"id": "S2", "text": "Love the dashboard", "star": 5, "source": "w"},
        ]
        enrichments = [
            {"id": "S1", "sentiment": "negative", "urgency": "high", "tags": ["checkout_failure"]},
            {"id": "S2", "sentiment": "positive", "urgency": "low", "tags": ["dashboard_praise"]},
        ]
        r = score_dataset(signals, enrichments)
        assert r["sentiment_polar"] == [2, 2]          # both agree with star proxy
        assert r["grounded"] == [2, 2]                 # both tags grounded in text
        assert r["mean_urgency_by_star"] == {1: 2.0, 5: 0.0}  # urgency falls as stars rise
        assert "checkout_failure" in r["top_tags"]

    def test_ungrounded_tag_flagged(self) -> None:
        signals = [{"id": "S1", "text": "totally unrelated words", "star": 1, "source": "a"}]
        enrichments = [{"id": "S1", "sentiment": "negative", "urgency": "high",
                        "tags": ["payment_error"]}]
        r = score_dataset(signals, enrichments)
        assert r["grounded"] == [0, 1]

    def test_sanity_csv_round_trips(self, tmp_path) -> None:
        # the embedded JSON in the tags column parses (guards the escaping)
        assert json.loads('{"public_signal_id":"S1"}')["public_signal_id"] == "S1"
