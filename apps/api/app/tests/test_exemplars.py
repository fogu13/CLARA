"""Tests for few-shot exemplars (Phase B) and their injection into enrichment."""

from __future__ import annotations

import json

import app.services.enrichment as enr
from app.services.exemplar_store import (
    DEFAULT_EXEMPLARS,
    fewshot_enabled,
    format_fewshot,
    load_exemplars,
)


class TestExemplarStore:
    def test_default_set_covers_all_sentiments_and_urgencies(self) -> None:
        sentiments = {e["sentiment"] for e in DEFAULT_EXEMPLARS}
        urgencies = {e["urgency"] for e in DEFAULT_EXEMPLARS}
        assert {"positive", "negative", "neutral", "mixed"} <= sentiments
        assert {"low", "medium", "high", "critical"} <= urgencies

    def test_format_fewshot_includes_text_and_tags(self) -> None:
        block = format_fewshot(load_exemplars())
        assert "Reference examples" in block
        # a known exemplar tag appears
        assert "positive_trend" in block

    def test_fewshot_enabled_default_on(self, monkeypatch) -> None:
        monkeypatch.delenv("ENRICH_FEWSHOT", raising=False)
        assert fewshot_enabled() is True

    def test_fewshot_disabled_by_env(self, monkeypatch) -> None:
        monkeypatch.setenv("ENRICH_FEWSHOT", "0")
        assert fewshot_enabled() is False


class TestEnrichmentFewShotInjection:
    def test_exemplars_prepended_to_prompt(self, monkeypatch) -> None:
        captured = {}

        def fake_call_tool(*, system, user, tool, tool_name, trace_name=None):
            captured["system"] = system
            captured["user"] = user
            return {"enrichments": []}

        monkeypatch.setattr(enr, "call_tool", fake_call_tool)
        enr.enrich_signals(
            [{"id": "1", "text": "the page crashed"}],
            exemplars=load_exemplars(),
        )
        # Exemplars are instructions, so they ride in the system turn; the user
        # turn carries only the untrusted feedback items (injection hardening).
        assert "Reference examples" in captured["system"]
        assert "Reference examples" not in captured["user"]
        assert "Enrich these feedback items" in captured["user"]

    def test_no_exemplars_no_block(self, monkeypatch) -> None:
        captured = {}

        def fake_call_tool(*, system, user, tool, tool_name, trace_name=None):
            captured["user"] = user
            return {"enrichments": []}

        monkeypatch.setattr(enr, "call_tool", fake_call_tool)
        enr.enrich_signals([{"id": "1", "text": "the page crashed"}])
        assert "Reference examples" not in captured["user"]
        assert captured["user"].startswith("Enrich these feedback items")
        # sanity: the items are valid json after the header
        assert json.loads(captured["user"].split("\n\n", 1)[1])[0]["id"] == "1"
