"""Tests for the enrichment service — port of enrich-signal edge function."""

from __future__ import annotations

import json
from typing import Any

import pytest


@pytest.fixture
def _mock_ai_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AI_BASE_URL", "http://test-ai.local/v1")
    monkeypatch.setenv("AI_API_KEY", "")
    monkeypatch.setenv("AI_MODEL", "test-model")
    monkeypatch.delenv("LANGFUSE_PUBLIC_KEY", raising=False)
    monkeypatch.delenv("LANGFUSE_SECRET_KEY", raising=False)
    import importlib

    import app.services.ai as ai_mod
    import app.services.enrichment as enr_mod

    importlib.reload(ai_mod)
    importlib.reload(enr_mod)


def _enrichment_response(items: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "enrichments": [
            {
                "id": item["id"],
                "sentiment": "negative",
                "sentiment_score": -0.7,
                "urgency": "high",
                "tags": ["checkout_failure", "payment_error"],
            }
            for item in items
        ]
    }


class TestEnrichSignals:
    def test_enriches_single_signal(self, _mock_ai_env: None, httpx_mock: Any) -> None:
        from app.services.enrichment import enrich_signals

        httpx_mock.add_response(
            url="http://test-ai.local/v1/chat/completions",
            method="POST",
            json={
                "choices": [
                    {
                        "message": {
                            "tool_calls": [
                                {
                                    "function": {
                                        "name": "submit_enrichments",
                                        "arguments": json.dumps(
                                            _enrichment_response([{"id": "sig-1"}])
                                        ),
                                    }
                                }
                            ]
                        }
                    }
                ],
                "usage": {},
            },
        )

        result = enrich_signals([{"id": "sig-1", "text": "The checkout page crashed"}])

        assert len(result) == 1
        assert result[0]["sentiment"] == "negative"
        assert result[0]["urgency"] == "high"
        assert "checkout_failure" in result[0]["tags"]

    def test_enriches_multiple_signals_in_batch(self, _mock_ai_env: None, httpx_mock: Any) -> None:
        from app.services.enrichment import enrich_signals

        signals = [
            {"id": f"sig-{i}", "text": f"Feedback {i}"}
            for i in range(3)
        ]

        httpx_mock.add_response(
            url="http://test-ai.local/v1/chat/completions",
            method="POST",
            json={
                "choices": [
                    {
                        "message": {
                            "tool_calls": [
                                {
                                    "function": {
                                        "name": "submit_enrichments",
                                        "arguments": json.dumps(_enrichment_response(signals)),
                                    }
                                }
                            ]
                        }
                    }
                ],
                "usage": {},
            },
        )

        result = enrich_signals(signals)
        assert len(result) == 3
        assert all(r["sentiment"] == "negative" for r in result)

    def test_returns_empty_for_empty_input(self, _mock_ai_env: None) -> None:
        from app.services.enrichment import enrich_signals

        assert enrich_signals([]) == []

    def test_skips_failed_batch_gracefully(
        self, _mock_ai_env: None, httpx_mock: Any, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from app.services.enrichment import enrich_signals

        monkeypatch.setattr("time.sleep", lambda _: None)
        httpx_mock.add_response(
            url="http://test-ai.local/v1/chat/completions",
            method="POST",
            status_code=500,
            text="server error",
            is_reusable=True,  # a 5xx is retried before the batch is skipped
        )

        result = enrich_signals([{"id": "sig-1", "text": "test"}])
        assert result == []

    def test_batches_large_inputs(self, _mock_ai_env: None, httpx_mock: Any) -> None:
        from app.services.enrichment import enrich_signals

        signals = [{"id": f"sig-{i}", "text": f"Feedback {i}"} for i in range(30)]

        for _ in range(2):
            httpx_mock.add_response(
                url="http://test-ai.local/v1/chat/completions",
                method="POST",
                json={
                    "choices": [
                        {
                            "message": {
                                "tool_calls": [
                                    {
                                        "function": {
                                            "name": "submit_enrichments",
                                            "arguments": json.dumps(
                                                _enrichment_response(
                                                    [{"id": f"sig-{i}"} for i in range(25)]
                                                )
                                            ),
                                        }
                                    }
                                ]
                            }
                        }
                    ],
                    "usage": {},
                },
            )

        result = enrich_signals(signals, batch_size=25)
        assert len(result) >= 25


class TestMergeEnrichment:
    def test_merges_enrichment_into_signal(self, _mock_ai_env: None) -> None:
        from app.services.enrichment import merge_enrichment_into_signal

        signal = {"id": "sig-1", "text": "Great product!"}
        enrichment = {
            "id": "sig-1",
            "sentiment": "positive",
            "sentiment_score": 0.8,
            "urgency": "low",
            "tags": ["positive_trend"],
        }

        merged = merge_enrichment_into_signal(signal, enrichment)

        assert merged["sentiment"] == "positive"
        assert merged["sentiment_score"] == 0.8
        assert merged["urgency"] == "low"
        assert merged["tags"] == ["positive_trend"]
        assert merged["enriched"] is True
        assert "audit" in merged
        assert merged["audit"]["source"] == "llm_enrichment"
        assert merged["audit"]["model"] == "test-model"
