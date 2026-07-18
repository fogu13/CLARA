"""Tests for the synthesis service — multi-tag clustering + 8-factor severity + frequency."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
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


# Relative to the real clock so trend_label() (which compares to the live now)
# stays correct — a hardcoded date silently goes stale and breaks "new" trends.
NOW = datetime.now(UTC)


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


def _make_enriched_signals(
    tag: str,
    count: int,
    *,
    urgency: str = "high",
    sentiment: str = "negative",
    tags: list[str] | None = None,
    days_ago: float | None = None,
    source: str = "zendesk",
) -> list[dict]:
    if tags is None:
        tags = [tag]
    sigs = []
    for i in range(count):
        ts = (NOW - timedelta(days=days_ago or i)).isoformat() if days_ago is not None else (
            NOW - timedelta(days=i)
        ).isoformat()
        sigs.append({
            "id": f"sig-{tag}-{i}",
            "text": f"Feedback {i} about {tag}",
            "signal_type": "qualitative",
            "urgency": urgency,
            "sentiment": sentiment,
            "tags": tags,
            "contact_count": 1,
            "source": source,
            "timestamp": ts,
        })
    return sigs


class TestCrossSignalSeverity:
    def test_low_severity_for_single_low_urgency(self, _mock_ai_env: None) -> None:
        from app.services.synthesis import cross_signal_severity

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

    def test_empty_signals_returns_low(self, _mock_ai_env: None) -> None:
        from app.services.synthesis import cross_signal_severity

        assert cross_signal_severity([]) == "low"


class TestComputeSeverity:
    def test_simple_fallback_without_context(self, _mock_ai_env: None) -> None:
        from app.services.synthesis import compute_severity

        signals = [
            {"urgency": "high", "sentiment": "negative", "customer_id": "c1"},
            {"urgency": "high", "sentiment": "negative", "customer_id": "c2"},
        ]
        result = compute_severity(signals)
        assert result["method"] == "simple_urgency_volume"
        assert result["band"] in ("low", "medium", "high", "critical")

    def test_8_factor_with_context(self, _mock_ai_env: None) -> None:
        from app.services.synthesis import compute_severity

        signals = [
            {"urgency": "critical", "sentiment": "negative", "customer_id": "c1"},
            {"urgency": "high", "sentiment": "negative", "customer_id": "c2"},
            {"urgency": "high", "sentiment": "negative", "customer_id": "c3"},
        ]
        context = {
            "journey_criticality": 0.8,
            "account_count": 50,
            "financial_exposure": 0.6,
            "regulatory_risk": 0.3,
        }
        result = compute_severity(signals, context_data=context)
        assert result["method"] == "8_factor_impact"
        assert "factors" in result
        assert "customer_reach" in result["factors"]
        assert "severity" in result["factors"]
        assert result["score"] > 0

    def test_empty_signals(self, _mock_ai_env: None) -> None:
        from app.services.synthesis import compute_severity

        result = compute_severity([])
        assert result["band"] == "low"
        assert result["method"] == "empty"


class TestClusterSignals:
    def test_tag_order_independence(self, _mock_ai_env: None) -> None:
        """Signals with the same tags in different order cluster together."""
        from app.services.synthesis import cluster_signals

        signals = [
            {"id": "s1", "tags": ["checkout_failure", "payment_error"]},
            {"id": "s2", "tags": ["payment_error", "checkout_failure"]},
        ]
        clusters = cluster_signals(signals, jaccard_threshold=0.34)
        assert len(clusters) == 1
        assert len(clusters[0][1]) == 2

    def test_disjoint_tags_separate_clusters(self, _mock_ai_env: None) -> None:
        from app.services.synthesis import cluster_signals

        signals = [
            {"id": "s1", "tags": ["checkout_failure"]},
            {"id": "s2", "tags": ["onboarding_friction"]},
        ]
        clusters = cluster_signals(signals, jaccard_threshold=0.34)
        assert len(clusters) == 2

    def test_partial_tag_overlap_clusters(self, _mock_ai_env: None) -> None:
        """Jaccard >= 0.34 means 1/2 overlap = 0.5 -> grouped."""
        from app.services.synthesis import cluster_signals

        signals = [
            {"id": "s1", "tags": ["checkout_failure", "payment_error"]},
            {"id": "s2", "tags": ["checkout_failure", "bug"]},
        ]
        # Jaccard = 1 shared / 3 unique = 0.333; use threshold 0.30 to group
        clusters = cluster_signals(signals, jaccard_threshold=0.30)
        assert len(clusters) == 1

    def test_high_jaccard_threshold_separates_partial(self, _mock_ai_env: None) -> None:
        """High threshold keeps low-token-overlap signals separate."""
        from app.services.synthesis import cluster_signals

        signals = [
            {"id": "s1", "tags": ["checkout_failure", "payment_error"]},
            {"id": "s2", "tags": ["checkout_failure", "billing_dispute"]},
        ]
        # theme tokens {checkout,payment} vs {checkout,billing,dispute}:
        # Jaccard = 1/4 = 0.25; threshold 0.50 keeps them separate
        clusters = cluster_signals(signals, jaccard_threshold=0.50)
        assert len(clusters) == 2

    def test_synonym_tags_cluster_on_theme_token(self, _mock_ai_env: None) -> None:
        """Near-synonym tags collapse onto a shared theme token and group.

        This is the real-data fix: GLM writes support_unresponsive /
        support_unavailable / slow_support for one theme; exact-tag overlap left
        them apart, theme-token overlap merges them.
        """
        from app.services.synthesis import cluster_signals

        signals = [
            {"id": "s1", "tags": ["support_unresponsive"]},
            {"id": "s2", "tags": ["support_unavailable"]},
            {"id": "s3", "tags": ["slow_support"]},
        ]
        clusters = cluster_signals(signals)
        assert len(clusters) == 1
        assert len(clusters[0][1]) == 3

    def test_no_tags_separate(self, _mock_ai_env: None) -> None:
        from app.services.synthesis import cluster_signals

        signals = [
            {"id": "s1", "tags": []},
            {"id": "s2", "tags": []},
        ]
        clusters = cluster_signals(signals)
        assert len(clusters) == 2

    def test_cluster_label_is_most_common_tag(self, _mock_ai_env: None) -> None:
        from app.services.synthesis import cluster_signals

        signals = [
            {"id": "s1", "tags": ["checkout_failure", "payment_error"]},
            {"id": "s2", "tags": ["checkout_failure", "bug"]},
            {"id": "s3", "tags": ["checkout_failure"]},
        ]
        clusters = cluster_signals(signals, jaccard_threshold=0.34)
        assert len(clusters) == 1
        label, sigs = clusters[0]
        assert label == "checkout_failure"

    def test_empty_signals(self, _mock_ai_env: None) -> None:
        from app.services.synthesis import cluster_signals

        assert cluster_signals([]) == []

    def test_semantic_fallback_with_embeddings(self, _mock_ai_env: None) -> None:
        """Signals with no tag overlap but high cosine sim cluster together."""
        from app.services.synthesis import cluster_signals

        signals = [
            {"id": "s1", "tags": ["checkout_failure"]},
            {"id": "s2", "tags": ["payment_crash"]},
        ]
        # High cosine sim embeddings (nearly identical)
        embeddings = [[1.0, 0.0], [0.99, 0.01]]
        clusters = cluster_signals(
            signals,
            jaccard_threshold=0.99,  # no jaccard match
            semantic_threshold=0.70,
            embeddings=embeddings,
        )
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
                "choices": [{
                    "message": {
                        "tool_calls": [{
                            "function": {
                                "name": "submit_insight",
                                "arguments": json.dumps(_synth_response(tag)),
                            }
                        }]
                    }
                }],
                "usage": {},
            },
        )

        insights = synthesize_insights(signals, min_cluster_size=3)

        assert len(insights) == 1
        insight = insights[0]
        assert insight["tag"] == "checkout_failure"
        assert insight["severity"] in ("low", "medium", "high", "critical")
        assert "frequency" in insight
        assert insight["frequency"]["raw_count"] == 3
        assert insight["frequency"]["trend"] in ("rising", "falling", "stable", "new")
        assert insight["source_count"] == 1
        assert insight["cluster_method"] == "token_jaccard"
        assert insight["audit"]["severity_source"] == "simple_urgency_volume"

    def test_max_urgency_consistent_when_argmax_signal_lacks_urgency(
        self, _mock_ai_env: None, httpx_mock: Any
    ) -> None:
        from app.services.synthesis import synthesize_insights

        tag = "checkout_failure"
        signals = _make_enriched_signals(tag, 3, urgency="low")
        # A missing urgency ranks as medium in the argmax key; the reported
        # value must match the ranking, not fall back to "low".
        signals[2]["urgency"] = None
        httpx_mock.add_response(
            url="http://test-ai.local/v1/chat/completions",
            method="POST",
            json={
                "choices": [{
                    "message": {
                        "tool_calls": [{
                            "function": {
                                "name": "submit_insight",
                                "arguments": json.dumps(_synth_response(tag)),
                            }
                        }]
                    }
                }],
                "usage": {},
            },
        )

        insights = synthesize_insights(signals, min_cluster_size=3)

        assert insights[0]["max_urgency"] == "medium"

    def test_skips_clusters_below_min_size(self, _mock_ai_env: None) -> None:
        from app.services.synthesis import synthesize_insights

        signals = _make_enriched_signals("rare_tag", 2)
        insights = synthesize_insights(signals, min_cluster_size=3)
        assert insights == []

    def test_empty_signals_returns_empty(self, _mock_ai_env: None) -> None:
        from app.services.synthesis import synthesize_insights

        assert synthesize_insights([]) == []

    def test_multiple_clusters_synthesized(
        self, _mock_ai_env: None, httpx_mock: Any
    ) -> None:
        from app.services.synthesis import synthesize_insights

        signals = (
            _make_enriched_signals("checkout_failure", 3, urgency="high")
            + _make_enriched_signals("onboarding_friction", 3, urgency="medium")
        )

        for tag in ["checkout_failure", "onboarding_friction"]:
            httpx_mock.add_response(
                url="http://test-ai.local/v1/chat/completions",
                method="POST",
                json={
                    "choices": [{
                        "message": {
                            "tool_calls": [{
                                "function": {
                                    "name": "submit_insight",
                                    "arguments": json.dumps(_synth_response(tag)),
                                }
                            }]
                        }
                    }],
                    "usage": {},
                },
            )

        insights = synthesize_insights(signals, min_cluster_size=3)

        assert len(insights) == 2
        tags = {i["tag"] for i in insights}
        assert tags == {"checkout_failure", "onboarding_friction"}

    def test_8_factor_severity_with_context(
        self, _mock_ai_env: None, httpx_mock: Any
    ) -> None:
        from app.services.synthesis import synthesize_insights

        tag = "checkout_failure"
        signals = _make_enriched_signals(tag, 5)
        httpx_mock.add_response(
            url="http://test-ai.local/v1/chat/completions",
            method="POST",
            json={
                "choices": [{
                    "message": {
                        "tool_calls": [{
                            "function": {
                                "name": "submit_insight",
                                "arguments": json.dumps(_synth_response(tag)),
                            }
                        }]
                    }
                }],
                "usage": {},
            },
        )

        context = {
            "journey_criticality": 0.9,
            "account_count": 30,
            "financial_exposure": 0.5,
            "regulatory_risk": 0.2,
        }
        insights = synthesize_insights(signals, min_cluster_size=3, context_data=context)

        assert len(insights) == 1
        insight = insights[0]
        assert insight["severity_method"] == "8_factor_impact"
        assert "severity_factors" in insight
        assert "customer_reach" in insight["severity_factors"]
        assert "evidence_confidence" in insight["severity_factors"]

    def test_source_corroboration_filter(
        self, _mock_ai_env: None, httpx_mock: Any
    ) -> None:
        from app.services.synthesis import synthesize_insights

        tag = "checkout_failure"
        # All from same source
        signals = _make_enriched_signals(tag, 3, source="zendesk")
        httpx_mock.add_response(
            url="http://test-ai.local/v1/chat/completions",
            method="POST",
            json={
                "choices": [{
                    "message": {
                        "tool_calls": [{
                            "function": {
                                "name": "submit_insight",
                                "arguments": json.dumps(_synth_response(tag)),
                            }
                        }]
                    }
                }],
                "usage": {},
            },
        )

        # min_sources=2 should filter out single-source clusters
        insights = synthesize_insights(signals, min_cluster_size=3, min_sources=2)
        assert insights == []

        # min_sources=1 should pass
        insights = synthesize_insights(signals, min_cluster_size=3, min_sources=1)
        assert len(insights) == 1

    def test_frequency_in_insight_output(
        self, _mock_ai_env: None, httpx_mock: Any
    ) -> None:
        from app.services.synthesis import synthesize_insights

        tag = "checkout_failure"
        signals = _make_enriched_signals(tag, 5, days_ago=1)
        httpx_mock.add_response(
            url="http://test-ai.local/v1/chat/completions",
            method="POST",
            json={
                "choices": [{
                    "message": {
                        "tool_calls": [{
                            "function": {
                                "name": "submit_insight",
                                "arguments": json.dumps(_synth_response(tag)),
                            }
                        }]
                    }
                }],
                "usage": {},
            },
        )

        insights = synthesize_insights(signals, min_cluster_size=3)

        assert len(insights) == 1
        freq = insights[0]["frequency"]
        assert freq["raw_count"] == 5
        assert freq["decayed_frequency"] > 0
        assert freq["trend"] == "new"  # all recent
        assert freq["source_count"] == 1
        assert freq["first_seen"] is not None
        assert freq["last_seen"] is not None


class TestChurnSaveDeskRouting:
    """Deterministic churn routing: stated leaving intent at high/critical
    urgency always proposes a save-desk recovery action (code, not prompt)."""

    def _respond(self, httpx_mock: Any, tag: str) -> None:
        httpx_mock.add_response(
            url="http://test-ai.local/v1/chat/completions",
            method="POST",
            json={
                "choices": [{
                    "message": {
                        "tool_calls": [{
                            "function": {
                                "name": "submit_insight",
                                "arguments": json.dumps(_synth_response(tag)),
                            }
                        }]
                    }
                }],
                "usage": {},
            },
        )

    def test_churn_cluster_at_high_urgency_gets_save_desk_action(
        self, _mock_ai_env: None, httpx_mock: Any
    ) -> None:
        from app.services.synthesis import synthesize_insights

        signals = _make_enriched_signals(
            "churn_risk", 3, urgency="high", tags=["churn_risk", "service_outage"]
        )
        self._respond(httpx_mock, "churn_risk")

        insights = synthesize_insights(signals, min_cluster_size=3)
        assert len(insights) == 1
        insight = insights[0]
        assert insight["churn_save_desk"] is True
        first = insight["suggested_actions"][0]
        assert first["type"] == "customer_recovery"
        assert "save-desk" in first["title"]
        # The LLM's own action is preserved behind the routed one.
        assert any(a["type"] == "create_ticket" for a in insight["suggested_actions"])
        assert any("churn_save_desk" in note for note in insight["audit"]["routing"])

    def test_low_urgency_churn_mentions_are_not_routed(
        self, _mock_ai_env: None, httpx_mock: Any
    ) -> None:
        from app.services.synthesis import synthesize_insights

        signals = _make_enriched_signals(
            "churn_risk", 3, urgency="medium", tags=["churn_risk"]
        )
        self._respond(httpx_mock, "churn_risk")

        insights = synthesize_insights(signals, min_cluster_size=3)
        assert len(insights) == 1
        assert "churn_save_desk" not in insights[0]
        assert insights[0]["suggested_actions"][0]["type"] == "create_ticket"

    def test_existing_recovery_action_is_not_duplicated(
        self, _mock_ai_env: None, httpx_mock: Any
    ) -> None:
        from app.services.synthesis import synthesize_insights

        response = _synth_response("churn_risk")
        response["suggested_actions"] = [{
            "type": "customer_recovery",
            "title": "Call the affected customers",
            "description": "Personal outreach",
            "priority": 1,
        }]
        httpx_mock.add_response(
            url="http://test-ai.local/v1/chat/completions",
            method="POST",
            json={
                "choices": [{
                    "message": {
                        "tool_calls": [{
                            "function": {
                                "name": "submit_insight",
                                "arguments": json.dumps(response),
                            }
                        }]
                    }
                }],
                "usage": {},
            },
        )
        signals = _make_enriched_signals(
            "churn_risk", 3, urgency="critical", tags=["churn_risk"]
        )
        insights = synthesize_insights(signals, min_cluster_size=3)
        actions = insights[0]["suggested_actions"]
        assert insights[0]["churn_save_desk"] is True
        assert sum(1 for a in actions if a["type"] == "customer_recovery") == 1
