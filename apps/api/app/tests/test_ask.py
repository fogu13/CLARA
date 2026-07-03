"""Tests for X3 — Ask CLARA (grounded Q&A: citations, confidence, honest refusal)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.connectors.config_store import ConnectorConfigStore
from app.domain.models import SignalRecord
from app.main import create_app
from app.services.ask import ask_clara
from app.services.problems import ProblemStore
from app.services.seed import load_seed_problems
from app.services.signals import SQLiteSignalStore
from app.services.telemetry import SQLiteTelemetryStore
from app.services.workflow import WorkflowStore


def _signal(signal_id: str, text: str) -> SignalRecord:
    return SignalRecord(
        signal_id=signal_id,
        customer_id=f"C-{signal_id}",
        account_id="A-1",
        source="webhook",
        journey="billing",
        journey_stage="payment",
        campaign_exposure=[],
        product_events=[],
        feedback_text=text,
        language="en",
        timestamp="2026-07-01T10:00:00Z",
    )


REFUND_SIGNALS = [
    _signal("r1", "Refund still missing after two weeks"),
    _signal("r2", "Where is my refund, waited ten days"),
    _signal("r3", "Refund was promised but never arrived"),
]
LOGIN_SIGNALS = [
    _signal("l1", "Cannot log in since the update"),
    _signal("l2", "Login loops back to the password screen"),
]
ALL_SIGNALS = [*REFUND_SIGNALS, *LOGIN_SIGNALS]

REFUND_VEC = [1.0, 0.0]
LOGIN_VEC = [0.0, 1.0]
QUESTION_VEC = [0.95, 0.05]  # a refund-ish question


def _fake_embed(texts: Any, **_: Any) -> list[list[float]]:
    # First entry is the question; signals follow in the order given.
    vectors = [QUESTION_VEC]
    for text in texts[1:]:
        vectors.append(REFUND_VEC if "efund" in text else LOGIN_VEC)
    return vectors


class TestAskService:
    def test_grounded_answer_with_citations(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("app.services.ai.embed", _fake_embed)
        monkeypatch.setattr(
            "app.services.ai.call_tool",
            lambda **kwargs: {
                "answer": "Refunds are delayed; three customers report waits over a week [r1][r2][r3].",
                "confidence": 0.9,
                "insufficient_evidence": False,
            },
        )

        result = ask_clara("What are customers saying about refunds?", ALL_SIGNALS)
        assert result["refused"] is False
        assert "[r1]" in result["answer"]
        cited = {c["signal_id"] for c in result["citations"]}
        assert {"r1", "r2", "r3"} <= cited
        assert "l1" not in cited  # low-similarity signals never reach the model
        # Overall confidence is capped by retrieval strength, not just model bravado.
        assert 0 < result["confidence"] <= result["model_confidence"]

    def test_refuses_when_too_few_matches(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("app.services.ai.embed", _fake_embed)
        called = {"llm": False}
        monkeypatch.setattr(
            "app.services.ai.call_tool",
            lambda **kwargs: called.__setitem__("llm", True),
        )

        # Only 2 login signals exist and the question matches them, not refunds.
        monkeypatch.setattr("app.services.ask.MIN_SIMILARITY", 0.5)
        result = ask_clara(
            "What about refunds?", LOGIN_SIGNALS
        )  # question vec ~ refund; login signals score ~0.05
        assert result["refused"] is True
        assert result["citations"] == []
        assert called["llm"] is False  # no LLM call without evidence — no token burn

    def test_model_reported_insufficient_evidence_becomes_refusal(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr("app.services.ai.embed", _fake_embed)
        monkeypatch.setattr(
            "app.services.ai.call_tool",
            lambda **kwargs: {"answer": "", "confidence": 0.2, "insufficient_evidence": True},
        )
        result = ask_clara("What are refund amounts in euros?", ALL_SIGNALS)
        assert result["refused"] is True
        assert result["answer"] is None

    def test_empty_workspace_refuses(self) -> None:
        assert ask_clara("Anything?", [])["refused"] is True


class TestAskEndpoint:
    def _client(self, tmp_path: Path):
        signal_store = SQLiteSignalStore(tmp_path / "signals.db")
        signal_store.import_signals(ALL_SIGNALS)
        telemetry = SQLiteTelemetryStore(tmp_path / "t.db")
        client = TestClient(
            create_app(
                problem_store=ProblemStore(load_seed_problems()),
                workflows=WorkflowStore(),
                signals=signal_store,
                connector_configs=ConnectorConfigStore(),
                telemetry=telemetry,
            )
        )
        return client, telemetry

    def test_ask_over_http(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("app.services.ai.embed", _fake_embed)
        monkeypatch.setattr(
            "app.services.ai.call_tool",
            lambda **kwargs: {
                "answer": "Refund delays dominate [r1].",
                "confidence": 0.8,
                "insufficient_evidence": False,
            },
        )
        client, telemetry = self._client(tmp_path)

        response = client.post("/ask", json={"question": "What is going on with refunds?"})
        assert response.status_code == 200
        body = response.json()
        assert body["refused"] is False and body["citations"]
        assert any(e["event_type"] == "question_asked" for e in telemetry.list_events())

    def test_validation_and_provider_failure(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        client, _ = self._client(tmp_path)
        assert client.post("/ask", json={}).status_code == 422
        assert client.post("/ask", json={"question": "x" * 501}).status_code == 422

        from app.services.ai import AIProviderError

        def down(*_: Any, **__: Any) -> None:
            raise AIProviderError("down")

        monkeypatch.setattr("app.services.ai.embed", down)
        response = client.post("/ask", json={"question": "Anything about refunds?"})
        assert response.status_code == 502
