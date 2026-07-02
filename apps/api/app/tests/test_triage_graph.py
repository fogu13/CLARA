"""Tests for the LangGraph triage pipeline — the agentic state machine.

Tests the full flow: ingest -> enrich -> classify -> synthesize -> governance
-> approval (interrupt) -> action -> measure -> learn.

Uses mocked LLM calls (via monkeypatch) and MemorySaver checkpointer.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import patch

import pytest
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command


@pytest.fixture
def _mock_ai_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AI_BASE_URL", "http://test-ai.local/v1")
    monkeypatch.setenv("AI_API_KEY", "")
    monkeypatch.setenv("AI_MODEL", "test-model")
    monkeypatch.delenv("LANGFUSE_PUBLIC_KEY", raising=False)
    monkeypatch.delenv("LANGFUSE_SECRET_KEY", raising=False)
    import importlib

    import app.agents.triage_graph as graph_mod
    import app.services.ai as ai_mod
    import app.services.enrichment as enr_mod
    import app.services.synthesis as syn_mod

    importlib.reload(ai_mod)
    importlib.reload(enr_mod)
    importlib.reload(syn_mod)
    importlib.reload(graph_mod)


def _mock_enrich_signals(signals: list[dict], **_kwargs) -> list[dict]:
    """Mock enrichment that adds sentiment/urgency/tags to each signal."""
    return [
        {
            "id": s["id"],
            "sentiment": "negative",
            "sentiment_score": -0.7,
            "urgency": "high",
            "tags": ["checkout_failure"],
        }
        for s in signals
    ]


def _mock_synthesize_insights(enriched: list[dict], **kw: Any) -> list[dict]:
    """Mock synthesis that returns one insight per tag cluster."""
    if not enriched:
        return []
    tag = enriched[0].get("tags", ["unknown"])[0]
    return [
        {
            "title": f"{tag} affecting checkout",
            "summary": f"Multiple users report {tag}",
            "category": "ux_friction",
            "impact_score": 7.5,
            "confidence": 0.85,
            "target_team": "engineering",
            "suggested_actions": [
                {
                    "type": "create_ticket",
                    "title": f"Fix {tag}",
                    "description": "Investigate and fix",
                    "priority": 1,
                }
            ],
            "severity": "high",
            "signal_ids": [s["id"] for s in enriched],
            "qual_signal_count": len(enriched),
            "quant_signal_count": 0,
            "affected_contacts": len(enriched),
            "max_urgency": "high",
            "tag": tag,
            "status": "new",
            "audit": {
                "model": "test-model",
                "source": "llm_synthesis",
                "severity_source": "deterministic_cross_signal",
                "limitations": ["LLM-synthesized; not human-validated"],
            },
        }
    ]


def _make_signals(count: int = 3) -> list[dict]:
    return [
        {
            "signal_id": f"sig-{i}",
            "feedback_text": f"Checkout crashed on step {i}",
            "signal_type": "qualitative",
            "contact_count": 1,
        }
        for i in range(count)
    ]


def _build_graph():
    """Build the triage graph with MemorySaver for testing."""
    from app.agents.triage_graph import build_triage_graph

    return build_triage_graph(checkpointer=MemorySaver())


class TestTriageGraphBasicFlow:
    """Test the graph runs end-to-end with mocked AI."""

    def test_empty_signals_returns_early(self, _mock_ai_env: None) -> None:
        from app.agents.triage_graph import build_triage_graph

        graph = build_triage_graph(checkpointer=MemorySaver())
        config = {"configurable": {"thread_id": "test-empty"}}

        result = graph.invoke({"signals": []}, config=config)

        assert result["status"] == "empty"
        assert "No signals to process" in result["errors"]

    def test_full_flow_without_approval(self, _mock_ai_env: None) -> None:
        """Test that the graph runs through to the approval interrupt."""
        from app.agents.triage_graph import build_triage_graph

        graph = build_triage_graph(checkpointer=MemorySaver())
        config = {"configurable": {"thread_id": "test-full"}}

        with (
            patch("app.agents.triage_graph.enrich_signals", side_effect=_mock_enrich_signals),
            patch("app.agents.triage_graph.synthesize_insights", side_effect=_mock_synthesize_insights),
        ):
            # First invoke should pause at the approval interrupt
            result = graph.invoke({"signals": _make_signals(3)}, config=config)

        # Graph should have paused at approval
        assert result["status"] == "enriched" or result.get("enrichment_count") == 3
        # The interrupt should have surfaced insights for approval
        # Check that we got to governance at least
        assert result.get("insights") is not None
        assert len(result["insights"]) == 1

    def test_enrichment_count_matches_signals(self, _mock_ai_env: None) -> None:
        from app.agents.triage_graph import build_triage_graph

        graph = build_triage_graph(checkpointer=MemorySaver())
        config = {"configurable": {"thread_id": "test-enrich-count"}}

        with (
            patch("app.agents.triage_graph.enrich_signals", side_effect=_mock_enrich_signals),
            patch("app.agents.triage_graph.synthesize_insights", side_effect=_mock_synthesize_insights),
        ):
            result = graph.invoke({"signals": _make_signals(5)}, config=config)

        assert result.get("enrichment_count") == 5
        assert len(result.get("enriched_signals", [])) == 5


class TestTriageGraphApproval:
    """Test the human-in-the-loop approval interrupt and resume."""

    def test_graph_pauses_at_approval(self, _mock_ai_env: None) -> None:
        from app.agents.triage_graph import build_triage_graph

        graph = build_triage_graph(checkpointer=MemorySaver())
        config = {"configurable": {"thread_id": "test-pause"}}

        with (
            patch("app.agents.triage_graph.enrich_signals", side_effect=_mock_enrich_signals),
            patch("app.agents.triage_graph.synthesize_insights", side_effect=_mock_synthesize_insights),
        ):
            result = graph.invoke({"signals": _make_signals(3)}, config=config)

        # Should have insights but no approval decision yet
        assert len(result.get("insights", [])) == 1
        assert result.get("approval_decision") is None

    def test_resume_with_approval_completes_flow(self, _mock_ai_env: None) -> None:
        from app.agents.triage_graph import build_triage_graph

        graph = build_triage_graph(checkpointer=MemorySaver())
        config = {"configurable": {"thread_id": "test-approve"}}

        with (
            patch("app.agents.triage_graph.enrich_signals", side_effect=_mock_enrich_signals),
            patch("app.agents.triage_graph.synthesize_insights", side_effect=_mock_synthesize_insights),
        ):
            # First invoke: runs to approval interrupt
            graph.invoke({"signals": _make_signals(3)}, config=config)

            # Resume with approval
            result = graph.invoke(Command(resume="approved"), config=config)

        assert result["approval_decision"] == "approved"
        assert result["status"] == "learned"
        assert len(result.get("approved_insights", [])) == 1
        assert len(result.get("action_results", [])) == 1
        assert result["action_results"][0]["action_type"] == "create_ticket"
        # Without connector configs, the action is recorded as no_config
        assert result["action_results"][0]["status"] == "no_config"

    def test_resume_with_rejection_skips_action(self, _mock_ai_env: None) -> None:
        from app.agents.triage_graph import build_triage_graph

        graph = build_triage_graph(checkpointer=MemorySaver())
        config = {"configurable": {"thread_id": "test-reject"}}

        with (
            patch("app.agents.triage_graph.enrich_signals", side_effect=_mock_enrich_signals),
            patch("app.agents.triage_graph.synthesize_insights", side_effect=_mock_synthesize_insights),
        ):
            graph.invoke({"signals": _make_signals(3)}, config=config)
            result = graph.invoke(Command(resume="rejected"), config=config)

        assert result["approval_decision"] == "rejected"
        assert result.get("approved_insights") == []
        assert result.get("action_results") == []

    def test_action_result_contains_audit(self, _mock_ai_env: None) -> None:
        from app.agents.triage_graph import build_triage_graph

        graph = build_triage_graph(checkpointer=MemorySaver())
        config = {"configurable": {"thread_id": "test-audit"}}

        with (
            patch("app.agents.triage_graph.enrich_signals", side_effect=_mock_enrich_signals),
            patch("app.agents.triage_graph.synthesize_insights", side_effect=_mock_synthesize_insights),
        ):
            graph.invoke({"signals": _make_signals(3)}, config=config)
            result = graph.invoke(Command(resume="approved"), config=config)

        action = result["action_results"][0]
        assert "audit" in action
        # Without connector configs, the audit records the no_config state
        assert action["audit"]["source"] == "action_node"
        assert "not configured" in action["audit"]["limitations"][0].lower()


class TestTriageGraphGovernance:
    """Test the governance gate blocks action for compliance concerns."""

    def test_compliance_concern_triggers_blocking_check(self, _mock_ai_env: None) -> None:
        from app.agents.triage_graph import build_triage_graph

        graph = build_triage_graph(checkpointer=MemorySaver())
        config = {"configurable": {"thread_id": "test-gov-block"}}

        def mock_synth_compliance(enriched: list[dict], **kw: Any) -> list[dict]:
            return [
                {
                    "title": "GDPR compliance issue",
                    "summary": "Users report data handling concerns",
                    "category": "compliance_concern",
                    "impact_score": 9.0,
                    "confidence": 0.9,
                    "target_team": "engineering",
                    "suggested_actions": [
                        {"type": "create_ticket", "title": "Review GDPR", "description": "Check", "priority": 1}
                    ],
                    "severity": "critical",
                    "signal_ids": [s["id"] for s in enriched],
                    "qual_signal_count": len(enriched),
                    "quant_signal_count": 0,
                    "affected_contacts": len(enriched),
                    "max_urgency": "critical",
                    "tag": "gdpr_concern",
                    "status": "new",
                    "audit": {"model": "test-model", "source": "llm_synthesis"},
                }
            ]

        with (
            patch("app.agents.triage_graph.enrich_signals", side_effect=_mock_enrich_signals),
            patch("app.agents.triage_graph.synthesize_insights", side_effect=mock_synth_compliance),
        ):
            result = graph.invoke({"signals": _make_signals(3)}, config=config)

        # Governance should have blocked
        assert result.get("governance_passed") is False
        assert result.get("approval_decision") == "blocked"
        assert result["status"] == "blocked"
        assert any("blocked" in e.lower() or "governance" in e.lower() for e in result.get("errors", []))

    def test_non_compliance_insight_passes_governance(self, _mock_ai_env: None) -> None:
        from app.agents.triage_graph import build_triage_graph

        graph = build_triage_graph(checkpointer=MemorySaver())
        config = {"configurable": {"thread_id": "test-gov-pass"}}

        with (
            patch("app.agents.triage_graph.enrich_signals", side_effect=_mock_enrich_signals),
            patch("app.agents.triage_graph.synthesize_insights", side_effect=_mock_synthesize_insights),
        ):
            result = graph.invoke({"signals": _make_signals(3)}, config=config)

        assert result.get("governance_passed") is True
        # Should have reached approval (paused)
        assert result.get("approval_decision") is None


class TestTriageGraphAuditMetadata:
    """Test that every AI output carries evidence/confidence/limitations/audit."""

    def test_enriched_signals_have_audit(self, _mock_ai_env: None) -> None:
        from app.agents.triage_graph import build_triage_graph

        graph = build_triage_graph(checkpointer=MemorySaver())
        config = {"configurable": {"thread_id": "test-enrich-audit"}}

        with (
            patch("app.agents.triage_graph.enrich_signals", side_effect=_mock_enrich_signals),
            patch("app.agents.triage_graph.synthesize_insights", side_effect=_mock_synthesize_insights),
        ):
            result = graph.invoke({"signals": _make_signals(3)}, config=config)

        enriched = result.get("enriched_signals", [])
        assert all("audit" in s for s in enriched)
        assert all(s["audit"]["source"] == "llm_enrichment" for s in enriched)

    def test_insights_have_severity_source_audit(self, _mock_ai_env: None) -> None:
        from app.agents.triage_graph import build_triage_graph

        graph = build_triage_graph(checkpointer=MemorySaver())
        config = {"configurable": {"thread_id": "test-synth-audit"}}

        with (
            patch("app.agents.triage_graph.enrich_signals", side_effect=_mock_enrich_signals),
            patch("app.agents.triage_graph.synthesize_insights", side_effect=_mock_synthesize_insights),
        ):
            result = graph.invoke({"signals": _make_signals(3)}, config=config)

        insights = result.get("insights", [])
        assert len(insights) == 1
        assert insights[0]["audit"]["severity_source"] == "deterministic_cross_signal"
        assert "LLM-synthesized" in insights[0]["audit"]["limitations"][0]


class TestEnrichNodeProvenance:
    """Regression: enrich_node must not strip source/timestamp/customer_id/signal_type."""

    def test_enrich_node_preserves_signal_provenance(self, _mock_ai_env: None) -> None:
        from app.agents.triage_graph import enrich_node

        signal = {
            "signal_id": "s1",
            "feedback_text": "checkout broke at payment",
            "source": "zendesk",
            "timestamp": "2026-06-01T00:00:00Z",
            "customer_id": "cust-1",
            "signal_type": "quantitative",
        }
        # No enrichment returned -> exercises the passthrough branch that builds from `item`.
        with patch("app.agents.triage_graph.enrich_signals", return_value=[]):
            result = enrich_node({"signals": [signal]})

        enriched = result["enriched_signals"]
        assert len(enriched) == 1
        s = enriched[0]
        assert s["source"] == "zendesk"
        assert s["timestamp"] == "2026-06-01T00:00:00Z"
        assert s["customer_id"] == "cust-1"
        assert s["signal_type"] == "quantitative"  # real type preserved, not hardcoded


# (Removed test_main_imports_utc_now: /triage/run now generates its thread_id via
# uuid4, and test_review_outcome_loop.py exercises the endpoint end-to-end, which
# would catch any NameError in the run path.)


class TestSemanticTaxonomy:
    """Test the semantic taxonomy helper functions (no DB required)."""

    def test_cosine_sim_identical_vectors(self, _mock_ai_env: None) -> None:
        from app.services.semantic_taxonomy import cosine_sim

        v = [1.0, 0.0, 0.5]
        assert cosine_sim(v, v) == pytest.approx(1.0, abs=1e-6)

    def test_cosine_sim_orthogonal_vectors(self, _mock_ai_env: None) -> None:
        from app.services.semantic_taxonomy import cosine_sim

        assert cosine_sim([1.0, 0.0], [0.0, 1.0]) == pytest.approx(0.0, abs=1e-6)

    def test_cluster_by_threshold_groups_similar(self, _mock_ai_env: None) -> None:
        from app.services.semantic_taxonomy import cluster_by_threshold

        vectors = [
            [1.0, 0.0],
            [0.99, 0.01],
            [0.0, 1.0],
            [0.99, 0.02],
            [0.01, 0.99],
        ]
        clusters = cluster_by_threshold(vectors, threshold=0.95, min_size=2)

        # First three should form one cluster, last two another
        assert len(clusters) >= 1
        # Check that similar vectors are grouped
        flat = sorted(i for cluster in clusters for i in cluster)
        assert 0 in flat and 1 in flat  # vectors 0 and 1 are very similar

    def test_cluster_filters_small_groups(self, _mock_ai_env: None) -> None:
        from app.services.semantic_taxonomy import cluster_by_threshold

        vectors = [[1.0, 0.0], [0.0, 1.0]]
        clusters = cluster_by_threshold(vectors, threshold=0.9, min_size=3)
        assert clusters == []

    def test_slugify(self, _mock_ai_env: None) -> None:
        from app.services.semantic_taxonomy import slugify

        assert slugify("Checkout Failure!") == "checkout_failure"
        assert slugify("  Late Delivery  ") == "late_delivery"
        assert slugify("pricing-unclear") == "pricing_unclear"

    def test_centroid(self, _mock_ai_env: None) -> None:
        from app.services.semantic_taxonomy import centroid

        vectors = [[1.0, 2.0], [3.0, 4.0]]
        c = centroid(vectors)
        assert c == [2.0, 3.0]

    def test_avg_cohesion_single_vector(self, _mock_ai_env: None) -> None:
        from app.services.semantic_taxonomy import avg_cohesion

        assert avg_cohesion([[1.0, 0.0]]) == 1.0

    def test_avg_cohesion_identical_vectors(self, _mock_ai_env: None) -> None:
        from app.services.semantic_taxonomy import avg_cohesion

        v = [1.0, 0.0, 0.5]
        assert avg_cohesion([v, v, v]) == pytest.approx(1.0, abs=1e-6)
