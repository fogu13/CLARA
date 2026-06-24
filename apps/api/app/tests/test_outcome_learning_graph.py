"""Tests for the measure + learn nodes in the LangGraph triage pipeline.

Verifies that the outcome engine and learning engine are correctly wired
into the graph: outcome contracts are built, resolution_score is computed,
closure levels are assigned, and learnings carry confidence decay.
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


def _mock_enrich(signals: list[dict]) -> list[dict]:
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


def _mock_synthesize(enriched: list[dict], **kw: Any) -> list[dict]:
    return [
        {
            "title": "Checkout failure",
            "summary": "Users report crashes",
            "category": "ux_friction",
            "impact_score": 8.0,
            "confidence": 0.9,
            "target_team": "engineering",
            "suggested_actions": [
                {"type": "create_ticket", "title": "Fix checkout", "description": "Fix", "priority": 1},
            ],
            "severity": "high",
            "signal_ids": [s["id"] for s in enriched],
            "qual_signal_count": len(enriched),
            "quant_signal_count": 0,
            "affected_contacts": len(enriched),
            "max_urgency": "high",
            "tag": "checkout_failure",
            "status": "new",
            "audit": {"model": "test", "source": "llm_synthesis"},
        }
    ]


def _make_signals(n: int = 3) -> list[dict]:
    return [
        {"signal_id": f"sig-{i}", "feedback_text": f"Checkout crashed {i}", "signal_type": "qualitative"}
        for i in range(n)
    ]


def _run_to_approval(graph, config, **extra_state):
    """Helper: run graph to approval interrupt with mocked AI."""
    with (
        patch("app.agents.triage_graph.enrich_signals", side_effect=_mock_enrich),
        patch("app.agents.triage_graph.synthesize_insights", side_effect=_mock_synthesize),
    ):
        graph.invoke({"signals": _make_signals(3), **extra_state}, config=config)
        return graph.invoke(Command(resume="approved"), config=config)


class TestMeasureNode:
    def test_outcome_contract_captured_when_no_measurement(self, _mock_ai_env: None) -> None:
        from app.agents.triage_graph import build_triage_graph

        graph = build_triage_graph(checkpointer=MemorySaver())
        config = {"configurable": {"thread_id": "test-measure-contract"}}

        result = _run_to_approval(graph, config)

        outcome = result.get("outcome")
        assert outcome is not None
        assert outcome["metric"] == "tag:checkout_failure"
        assert outcome["baseline"] == 3  # qual_signal_count
        assert outcome["measured"] is None
        assert outcome["status"] == "not_measured"
        assert outcome["closure_level"] == "operational"
        assert "contract" in outcome

    def test_resolution_score_computed_with_measured_value(self, _mock_ai_env: None) -> None:
        from app.agents.triage_graph import build_triage_graph

        graph = build_triage_graph(checkpointer=MemorySaver())
        config = {"configurable": {"thread_id": "test-measure-score"}}

        # Pass a measured_value: 1 new recurrence after action
        result = _run_to_approval(graph, config, measured_value=1)

        outcome = result.get("outcome")
        assert outcome is not None
        assert outcome["measured"] == 1
        # resolution_score = 1 - 1/3 ≈ 0.6667
        assert outcome["resolution_score"] is not None
        assert outcome["resolution_score"] > 0.5
        assert outcome["status"] == "improving"
        assert outcome["closure_level"] == "outcome"

    def test_full_resolution_when_measured_zero(self, _mock_ai_env: None) -> None:
        from app.agents.triage_graph import build_triage_graph

        graph = build_triage_graph(checkpointer=MemorySaver())
        config = {"configurable": {"thread_id": "test-measure-zero"}}

        result = _run_to_approval(graph, config, measured_value=0)

        outcome = result.get("outcome")
        assert outcome["resolution_score"] == 1.0
        assert outcome["status"] == "target_met"

    def test_no_improvement_when_measured_high(self, _mock_ai_env: None) -> None:
        from app.agents.triage_graph import build_triage_graph

        graph = build_triage_graph(checkpointer=MemorySaver())
        config = {"configurable": {"thread_id": "test-measure-high"}}

        result = _run_to_approval(graph, config, measured_value=10)

        outcome = result.get("outcome")
        assert outcome["resolution_score"] == 0.0
        assert outcome["status"] == "not_improved"
        assert outcome["closure_level"] == "operational"

    def test_summary_includes_tag_and_numbers(self, _mock_ai_env: None) -> None:
        from app.agents.triage_graph import build_triage_graph

        graph = build_triage_graph(checkpointer=MemorySaver())
        config = {"configurable": {"thread_id": "test-measure-summary"}}

        result = _run_to_approval(graph, config, measured_value=2)

        outcome = result.get("outcome")
        assert "checkout_failure" in outcome["summary"]
        assert "2" in outcome["summary"]


class TestLearnNode:
    def test_auto_derives_worked_conclusion_from_target_met(self, _mock_ai_env: None) -> None:
        from app.agents.triage_graph import build_triage_graph

        graph = build_triage_graph(checkpointer=MemorySaver())
        config = {"configurable": {"thread_id": "test-learn-worked"}}

        result = _run_to_approval(graph, config, measured_value=0)

        learning = result.get("learning")
        assert learning is not None
        assert learning["learning_status"] == "worked"
        assert learning["base_confidence"] >= 0.6
        assert learning["freshness"] == "VALIDATED"
        assert learning["decayed_confidence"] > 0

    def test_auto_derives_partially_worked_from_improving(self, _mock_ai_env: None) -> None:
        from app.agents.triage_graph import build_triage_graph

        graph = build_triage_graph(checkpointer=MemorySaver())
        config = {"configurable": {"thread_id": "test-learn-partial"}}

        result = _run_to_approval(graph, config, measured_value=2)

        learning = result.get("learning")
        assert learning["learning_status"] == "partially_worked"

    def test_auto_derives_did_not_work_from_not_improved(self, _mock_ai_env: None) -> None:
        from app.agents.triage_graph import build_triage_graph

        graph = build_triage_graph(checkpointer=MemorySaver())
        config = {"configurable": {"thread_id": "test-learn-failed"}}

        result = _run_to_approval(graph, config, measured_value=10)

        learning = result.get("learning")
        assert learning["learning_status"] == "did_not_work"
        assert learning["base_confidence"] == 0.3
        assert len(learning["losing_examples"]) == 1

    def test_auto_derives_inconclusive_when_not_measured(self, _mock_ai_env: None) -> None:
        from app.agents.triage_graph import build_triage_graph

        graph = build_triage_graph(checkpointer=MemorySaver())
        config = {"configurable": {"thread_id": "test-learn-inconclusive"}}

        result = _run_to_approval(graph, config)

        learning = result.get("learning")
        assert learning["learning_status"] == "inconclusive"

    def test_human_conclusion_overrides_auto(self, _mock_ai_env: None) -> None:
        from app.agents.triage_graph import build_triage_graph

        graph = build_triage_graph(checkpointer=MemorySaver())
        config = {"configurable": {"thread_id": "test-learn-human"}}

        human = {
            "learning_status": "worked",
            "summary": "The fix completely resolved the checkout issue.",
            "limitations": "Only tested on web, not mobile.",
            "next_step": "Roll out to mobile app.",
            "reviewer": "analyst-1",
        }

        result = _run_to_approval(graph, config, human_conclusion=human)

        learning = result.get("learning")
        assert learning["learning_status"] == "worked"
        assert learning["summary"] == "The fix completely resolved the checkout issue."
        assert learning["reviewer"] == "analyst-1"

    def test_learning_has_evidence_block(self, _mock_ai_env: None) -> None:
        from app.agents.triage_graph import build_triage_graph

        graph = build_triage_graph(checkpointer=MemorySaver())
        config = {"configurable": {"thread_id": "test-learn-evidence"}}

        result = _run_to_approval(graph, config, measured_value=0)

        learning = result.get("learning")
        assert "evidence" in learning
        assert learning["evidence"]["outcome_metric"] == "tag:checkout_failure"
        assert learning["evidence"]["resolution_score"] == 1.0
        assert learning["evidence"]["insight_title"] == "Checkout failure"

    def test_learning_has_decay_and_freshness(self, _mock_ai_env: None) -> None:
        from app.agents.triage_graph import build_triage_graph

        graph = build_triage_graph(checkpointer=MemorySaver())
        config = {"configurable": {"thread_id": "test-learn-decay"}}

        result = _run_to_approval(graph, config, measured_value=0)

        learning = result.get("learning")
        assert "decayed_confidence" in learning
        assert "freshness" in learning
        assert learning["freshness"] == "VALIDATED"
        assert learning["decayed_confidence"] == pytest.approx(
            learning["base_confidence"], abs=0.1
        )

    def test_no_outcome_returns_none_learning(self, _mock_ai_env: None) -> None:
        from app.agents.triage_graph import build_triage_graph

        graph = build_triage_graph(checkpointer=MemorySaver())
        config = {"configurable": {"thread_id": "test-learn-none"}}

        # Reject at approval -> no action -> no outcome -> no learning
        with (
            patch("app.agents.triage_graph.enrich_signals", side_effect=_mock_enrich),
            patch("app.agents.triage_graph.synthesize_insights", side_effect=_mock_synthesize),
        ):
            graph.invoke({"signals": _make_signals(3)}, config=config)
            result = graph.invoke(Command(resume="rejected"), config=config)

        # Rejected -> graph routes to END, skipping measure + learn
        assert result.get("learning") is None
        assert result.get("outcome") is None
        assert result["status"] == "rejected"
        assert result["approval_decision"] == "rejected"
