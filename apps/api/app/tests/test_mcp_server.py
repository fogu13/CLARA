"""Tests for X8 — the read-only MCP server's fetch layer.

The MCP protocol itself is the SDK's job; what CLARA owns is: the fetch
functions hit the right endpoints (through real HTTP semantics via ASGI
transport, so auth/RBAC apply), and the registered tool surface stays
read-only + ask.
"""

from __future__ import annotations

from pathlib import Path

import httpx
import pytest

from app.connectors.config_store import ConnectorConfigStore
from app.main import create_app
from app.mcp_server import (
    fetch_emerging,
    fetch_measurements,
    fetch_outcome_board,
    fetch_problem,
    fetch_problems,
    mcp,
    post_question,
)
from app.services.problems import ProblemStore
from app.services.seed import load_seed_problems
from app.services.signals import SQLiteSignalStore
from app.services.telemetry import SQLiteTelemetryStore
from app.services.workflow import WorkflowStore


@pytest.fixture
def client(tmp_path: Path):
    from fastapi.testclient import TestClient

    app = create_app(
        problem_store=ProblemStore(load_seed_problems()),
        workflows=WorkflowStore(),
        signals=SQLiteSignalStore(tmp_path / "signals.db"),
        connector_configs=ConnectorConfigStore(),
        telemetry=SQLiteTelemetryStore(tmp_path / "t.db"),
    )
    # TestClient IS a sync httpx.Client over ASGI — the fetch functions accept it
    # directly, exercising real HTTP semantics (routing, auth deps, status codes).
    with TestClient(app) as http_client:
        yield http_client


class TestFetchLayer:
    def test_problems_and_detail(self, client: httpx.Client) -> None:
        problems = fetch_problems(client)
        assert problems and "problem_id" in problems[0]

        detail = fetch_problem(client, problems[0]["problem_id"])
        assert detail["problem_id"] == problems[0]["problem_id"]
        assert "evidence" in detail and "action_proposals" in detail

    def test_outcome_board_and_emerging_and_measurements(self, client: httpx.Client) -> None:
        board = fetch_outcome_board(client)
        assert {"total", "items"} <= set(board)

        emerging = fetch_emerging(client)
        assert "signals" in emerging

        assert isinstance(fetch_measurements(client), list)

    def test_unknown_problem_raises(self, client: httpx.Client) -> None:
        with pytest.raises(httpx.HTTPStatusError):
            fetch_problem(client, "PRB-NOPE")

    def test_ask_flows_through_grounded_qa(
        self, client: httpx.Client, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # Mock the AI layer (as in test_ask): the seeded workspace has 3 signals;
        # make them all match so the full grounded path runs.
        monkeypatch.setattr(
            "app.services.ai.embed",
            lambda texts, **_: [[1.0, 0.0]] * len(texts),
        )
        monkeypatch.setattr(
            "app.services.ai.call_tool",
            lambda **_: {
                "answer": "Verification friction dominates [SIG-2001].",
                "confidence": 0.7,
                "insufficient_evidence": False,
            },
        )
        result = post_question(client, "What are customers saying?")
        assert result["refused"] is False
        assert result["citations"]


class TestToolSurface:
    def test_registered_tools_are_read_only_plus_ask(self) -> None:
        import anyio

        tools = anyio.run(mcp.list_tools)
        names = {tool.name for tool in tools}
        assert names == {
            "list_problems",
            "get_problem",
            "get_outcome_board",
            "get_emerging_problems",
            "get_measurement_checkpoints",
            "ask_clara",
        }
        # Governance boundary: no approval/execution/write tools, ever.
        assert not any("approv" in n or "execut" in n or "delete" in n for n in names)
