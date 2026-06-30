"""Tests that retrieved learnings are injected into the synthesis prompt.

This is the wire that closes the outcome -> learning -> retrieval loop: past
learnings must actually reach the LLM prompt and be recorded in the audit.
"""

from __future__ import annotations

from typing import Any

import app.services.synthesis as syn


def _capture_call_tool(monkeypatch) -> dict[str, Any]:
    captured: dict[str, Any] = {}

    def fake_call_tool(*, system: str, user: str, tool, tool_name, trace_name=None):
        captured["user"] = user
        return {
            "title": "t", "summary": "s", "category": "product_issue",
            "impact_score": 5, "confidence": 0.8, "target_team": "product",
            "suggested_actions": [],
        }

    monkeypatch.setattr(syn, "call_tool", fake_call_tool)
    return captured


def test_learnings_injected_into_prompt(monkeypatch) -> None:
    captured = _capture_call_tool(monkeypatch)
    learnings = [
        {"learning_status": "worked", "topic": "checkout_failure",
         "summary": "Adding a retry button recovered carts", "freshness": "VALIDATED"},
    ]
    syn.synthesize_cluster("checkout_failure", [{"text": "payment fails"}], learnings=learnings)

    assert "Relevant past learnings" in captured["user"]
    assert "Adding a retry button recovered carts" in captured["user"]


def test_no_learnings_no_block(monkeypatch) -> None:
    captured = _capture_call_tool(monkeypatch)
    syn.synthesize_cluster("checkout_failure", [{"text": "payment fails"}])
    assert "Relevant past learnings" not in captured["user"]


def test_synthesize_insights_records_applied_learnings_in_audit(monkeypatch) -> None:
    _capture_call_tool(monkeypatch)
    # 3 signals sharing a tag -> one cluster; min_sources=1 so it isn't filtered.
    signals = [
        {"id": f"s{i}", "text": "checkout keeps failing at payment",
         "tags": ["checkout_failure", "payment_error"], "source": "review",
         "signal_type": "qualitative"}
        for i in range(3)
    ]
    learnings = [
        {"learning_status": "worked", "topic": "checkout_failure",
         "summary": "retry button worked", "base_confidence": 0.7,
         "last_validated_at": "2026-06-01T00:00:00+00:00"},
    ]
    insights = syn.synthesize_insights(
        signals, min_cluster_size=2, min_sources=1, learnings=learnings
    )
    assert insights
    assert "checkout_failure" in insights[0]["audit"]["applied_learnings"]
