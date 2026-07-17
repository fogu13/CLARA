"""MCP fetch layer (services/mcp_fetch.py) against the real app — every MCP
tool's data path, without the optional `mcp` extra. TestClient IS a sync
httpx.Client subclass, so the fetch functions take it directly."""

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.services.mcp_fetch import (
    api_headers,
    fetch_emerging,
    fetch_evidence_pack,
    fetch_measurements,
    fetch_model_card_metrics,
    fetch_outcome_board,
    fetch_problem,
    fetch_problems,
)
from app.services.problems import ProblemStore
from app.services.seed import load_seed_problems
from app.services.workflow import WorkflowStore


@pytest.fixture
def client():
    app = create_app(problem_store=ProblemStore(load_seed_problems()), workflows=WorkflowStore())
    return TestClient(app)


def test_fetch_problems_and_detail(client) -> None:
    problems = fetch_problems(client)
    assert problems and "problem_id" in problems[0]

    detail = fetch_problem(client, problems[0]["problem_id"])
    assert detail["problem_id"] == problems[0]["problem_id"]
    assert "outcome_contract" in detail


def test_fetch_evidence_pack_is_hashed(client) -> None:
    problems = fetch_problems(client)
    pack = fetch_evidence_pack(client, problems[0]["problem_id"])
    assert pack["problem"]["problem_id"] == problems[0]["problem_id"]
    assert len(pack["content_hash"]) == 64  # sha256 hex — the tamper-evidence stamp


def test_fetch_boards_and_metrics(client) -> None:
    board = fetch_outcome_board(client)
    assert "items" in board and "target_met" in board

    emerging = fetch_emerging(client)
    assert "signals" in emerging

    checkpoints = fetch_measurements(client)
    assert isinstance(checkpoints, list)

    metrics = fetch_model_card_metrics(client)
    assert "published" in metrics


def test_api_key_header_construction(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CLARA_API_KEY", "clara_test_key")
    monkeypatch.delenv("CLARA_API_TOKEN", raising=False)
    headers = api_headers()
    assert headers == {"X-Api-Key": "clara_test_key"}

    monkeypatch.setenv("CLARA_API_TOKEN", "jwt-token")
    headers = api_headers()
    assert headers["Authorization"] == "Bearer jwt-token"
    assert headers["X-Api-Key"] == "clara_test_key"
