"""R3: closed-set journey-stage routing behind ENRICH_ROUTING_CLOSED_SET."""

from __future__ import annotations

from typing import Any

import pytest

from app.services.enrichment import (
    ROUTING_ABSTAIN,
    enrich_signals,
    merge_enrichment_into_signal,
)

STAGES = ["onboarding", "purchase_checkout", "retention"]


@pytest.fixture
def _routing_on(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENRICH_ROUTING_CLOSED_SET", "1")


def _capture_call(monkeypatch: pytest.MonkeyPatch, captured: dict[str, Any]) -> None:
    def fake_call_tool(*, system: str, user: str, tool: dict, tool_name: str, **_: Any) -> dict:
        captured["system"] = system
        captured["tool"] = tool
        return {"enrichments": [{
            "id": "s1", "sentiment": "negative", "sentiment_score": -0.5,
            "urgency": "high", "tags": ["checkout_failure"],
            "journey_stage": "purchase_checkout",
        }]}

    monkeypatch.setattr("app.services.enrichment.call_tool", fake_call_tool)


class TestPromptAndSchema:
    def test_inventory_becomes_a_closed_enum_with_abstain(
        self, _routing_on: None, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        captured: dict[str, Any] = {}
        _capture_call(monkeypatch, captured)
        enrich_signals([{"id": "s1", "text": "checkout broken"}],
                       journey_stage_inventory=STAGES)
        schema = captured["tool"]["function"]["parameters"]["properties"]["enrichments"]["items"]
        assert schema["properties"]["journey_stage"]["enum"] == [*sorted(STAGES), ROUTING_ABSTAIN]
        assert "journey_stage" in schema["required"]
        assert "Never invent a stage" in captured["system"]

    def test_flag_off_keeps_the_published_configuration(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("ENRICH_ROUTING_CLOSED_SET", raising=False)
        captured: dict[str, Any] = {}
        _capture_call(monkeypatch, captured)
        enrich_signals([{"id": "s1", "text": "x"}], journey_stage_inventory=STAGES)
        schema = captured["tool"]["function"]["parameters"]["properties"]["enrichments"]["items"]
        assert "journey_stage" not in schema["properties"]
        assert "Inventory" not in captured["system"]


class TestMergeRule:
    def test_fills_only_unknown_stage(self) -> None:
        enrichment = {"sentiment": "negative", "urgency": "high", "tags": [],
                      "journey_stage": "purchase_checkout"}
        unknown = merge_enrichment_into_signal(
            {"id": "s1", "journey_stage": "unknown_stage"}, enrichment)
        assert unknown["journey_stage"] == "purchase_checkout"
        assert unknown["routing_source"] == "closed_set_llm"

        provided = merge_enrichment_into_signal(
            {"id": "s2", "journey_stage": "verification"}, enrichment)
        assert provided["journey_stage"] == "verification"  # source truth wins
        assert "routing_source" not in provided

    def test_abstention_is_flagged_for_review_not_invented(self) -> None:
        enrichment = {"sentiment": "negative", "urgency": "high", "tags": [],
                      "journey_stage": ROUTING_ABSTAIN}
        merged = merge_enrichment_into_signal(
            {"id": "s1", "journey_stage": "unknown_stage"}, enrichment)
        assert merged["journey_stage"] == "unknown_stage"
        assert merged["routing_review"] == "stage_abstained"


def test_inventory_helper_excludes_unaccepted_categories() -> None:
    from app.services.taxonomies import TaxonomyStore, journey_stage_inventory

    store = TaxonomyStore()  # seeds itself with the sample catalogs
    stages = journey_stage_inventory(store)
    assert "onboarding" in stages
    assert stages == sorted(set(stages))
