"""Tests for the synthesis service — port of synthesize-insights edge function."""

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
    import app.services.synthesis as syn_mod

    importlib.reload(ai_mod)
    importlib.reload(syn_mod)


def _synth_response(tag: str) -> dict[str, Any]:
    return {
        "title": f"{tag} affecting checkout",
        "summary": f"Multiple users report {tag} during checkout.",
        "category": "ux_friction",
        "impact_score": 7.5,
        "confidence": 0.85,
        "target_team": "engineering",
        "suggested_actions": [
            {
                "type": "create_ticket",
                "title": f"Fix {tag}",
                "description": "Investigate and fix the checkout issue",
                "priority": 1,
            }
        ],
    }


def _make_enriched_signals(tag: str, count: int, *, urgency: str = "high", sentiment: str = "negative") -> list[dict]:
    return [
        {
            "id": f"sig-{i}",
            "text": f"Feedback {i} about {tag}",
            "signal_type": "qualitative",
            "urgency": urgency,
            "sentiment": sentiment,
            "tags": [tag],
            "contact_count": 1,
        }
        for i in range(count)
    ]


class TestCrossSignalSeverity:
    def test_low_severity_for_few_low_urgency_signals(self, _mock_ai_env: None) -> None:
        from app.services.synthesis import cross_signal_severity

        # 2 low-urgency signals: max_urgency=1 + volume_bonus=1 = 2 -> medium
        signals = [
            {"urgency": "low", "sentiment": "neutral"},
            {"urgency": "low", "sentiment": "neutral"},
        ]
        assert cross_signal_severity(signals) == "medium"

    def test_low_severity_for_single_low_urgency(self, _mock_ai_env: None) -> None:
        from app.services.synthesis import cross_signal_severity

        # 1 low-urgency signal: max_urgency=1 + volume_bonus=0 = 1 -> low
        assert cross_signal_severity([{"urgency": "low", "sentiment": "neutral"}]) == "low"

    def test_medium_severity_for_medium_urgency(self, _mock_ai_env: None) -> None:
        from app.services.synthesis import cross_signal_severity

        signals = [
            {"urgency": "medium", "sentiment": "neutral"},
            {"urgency": "medium", "sentiment": "neutral"},
        ]
        assert cross_signal_severity(signals) == "medium"

    def test_high_severity_for_high_urgency(self, _mock_ai_env: None) -> None:
        from app.services.synthesis import cross_signal_severity

        signals = [
            {"urgency": "high", "sentiment": "negative"},
            {"urgency": "high", "sentiment": "negative"},
        ]
        assert cross_signal_severity(signals) == "high"

    def test_critical_severity_for_many_critical(self, _mock_ai_env: None) -> None:
        from app.services.synthesis import cross_signal_severity

        signals = [
            {"urgency": "critical", "sentiment": "negative"},
            {"urgency": "critical", "sentiment": "negative"},
            {"urgency": "high", "sentiment": "negative"},
            {"urgency": "high", "sentiment": "negative"},
        ]
        assert cross_signal_severity(signals) == "critical"

    def test_negativity_bonus(self, _mock_ai_env: None) -> None:
        from app.services.synthesis import cross_signal_severity

        # 3 high-urgency signals, all negative -> gets negativity bonus
        signals = [
            {"urgency": "high", "sentiment": "negative"},
            {"urgency": "high", "sentiment": "negative"},
            {"urgency": "high", "sentiment": "negative"},
        ]
        # max_urgency=3 + volume_bonus=1 + neg_bonus=1 = 5 -> high
        assert cross_signal_severity(signals) == "high"

    def test_empty_signals_returns_low(self, _mock_ai_env: None) -> None:
        from app.services.synthesis import cross_signal_severity

        assert cross_signal_severity([]) == "low"


class TestClusterByTag:
    def test_clusters_by_first_tag(self, _mock_ai_env: None) -> None:
        from app.services.synthesis import cluster_by_tag

        signals = [
            {"tags": ["checkout", "payment"]},
            {"tags": ["checkout"]},
            {"tags": ["onboarding"]},
            {"tags": ["checkout", "bug"]},
        ]
        clusters = cluster_by_tag(signals)

        assert "checkout" in clusters
        assert "onboarding" in clusters
        assert len(clusters["checkout"]) == 3
        assert len(clusters["onboarding"]) == 1

    def test_skips_signals_without_tags(self, _mock_ai_env: None) -> None:
        from app.services.synthesis import cluster_by_tag

        signals = [{"tags": []}, {"tags": None}, {"tags": ["bug"]}]
        clusters = cluster_by_tag(signals)

        assert "bug" in clusters
        assert len(clusters) == 1


class TestSynthesizeInsights:
    def test_synthesizes_cluster_with_enough_signals(
        self, _mock_ai_env: None, httpx_mock: Any
    ) -> None:
        from app.services.synthesis import synthesize_insights

        tag = "checkout_failure"
        signals = _make_enriched_signals(tag, 3)

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
                                        "name": "submit_insight",
                                        "arguments": json.dumps(_synth_response(tag)),
                                    }
                                }
                            ]
                        }
                    }
                ],
                "usage": {},
            },
        )

        insights = synthesize_insights(signals)

        assert len(insights) == 1
        insight = insights[0]
        assert insight["tag"] == "checkout_failure"
        assert insight["severity"] == "high"  # 3 high-urgency negative signals
        assert insight["title"] == "checkout_failure affecting checkout"
        assert insight["signal_ids"] == ["sig-0", "sig-1", "sig-2"]
        assert insight["qual_signal_count"] == 3
        assert insight["audit"]["severity_source"] == "deterministic_cross_signal"

    def test_skips_clusters_below_min_size(self, _mock_ai_env: None) -> None:
        from app.services.synthesis import synthesize_insights

        signals = _make_enriched_signals("rare_tag", 1)
        insights = synthesize_insights(signals, min_cluster_size=2)

        assert insights == []

    def test_empty_signals_returns_empty(self, _mock_ai_env: None) -> None:
        from app.services.synthesis import synthesize_insights

        assert synthesize_insights([]) == []

    def test_multiple_clusters_synthesized(
        self, _mock_ai_env: None, httpx_mock: Any
    ) -> None:
        from app.services.synthesis import synthesize_insights

        signals = (
            _make_enriched_signals("checkout_failure", 2, urgency="high")
            + _make_enriched_signals("onboarding_friction", 2, urgency="medium")
        )

        for tag in ["checkout_failure", "onboarding_friction"]:
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
                                            "name": "submit_insight",
                                            "arguments": json.dumps(_synth_response(tag)),
                                        }
                                    }
                                ]
                            }
                        }
                    ],
                    "usage": {},
                },
            )

        insights = synthesize_insights(signals)

        assert len(insights) == 2
        tags = {i["tag"] for i in insights}
        assert tags == {"checkout_failure", "onboarding_friction"}
