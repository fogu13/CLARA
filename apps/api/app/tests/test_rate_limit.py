"""Rate-limit middleware: off by default, per-client fixed window when enabled."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.services.problems import ProblemStore
from app.services.seed import load_seed_problems
from app.services.signals import SQLiteSignalStore
from app.services.workflow import WorkflowStore


def _client(tmp_path: Path) -> TestClient:
    return TestClient(
        create_app(
            problem_store=ProblemStore(load_seed_problems()),
            workflows=WorkflowStore(),
            signals=SQLiteSignalStore(tmp_path / "signals.db"),
        )
    )


def test_disabled_by_default(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CLARA_RATE_LIMIT_PER_MINUTE", raising=False)
    client = _client(tmp_path)
    for _ in range(10):
        assert client.get("/health").status_code == 200
        assert client.get("/problems").status_code in (200, 401)


def test_limit_enforced_per_client(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("CLARA_RATE_LIMIT_PER_MINUTE", "3")
    client = _client(tmp_path)

    statuses = [client.get("/problems").status_code for _ in range(4)]
    assert statuses[:3] == [statuses[0]] * 3  # first three pass the limiter
    assert statuses[3] == 429

    limited = client.get("/problems")
    assert limited.status_code == 429
    assert limited.json()["detail"] == "Rate limit exceeded"
    assert 0 < int(limited.headers["retry-after"]) <= 60
    assert limited.headers["x-ratelimit-limit"] == "3"

    # A different client identity (API key header) has its own bucket.
    assert client.get(
        "/problems", headers={"X-Api-Key": "clara_sk_other"}
    ).status_code != 429


def test_health_stays_exempt(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CLARA_RATE_LIMIT_PER_MINUTE", "1")
    client = _client(tmp_path)
    for _ in range(5):
        assert client.get("/health").status_code == 200


def test_invalid_env_value_disables(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("CLARA_RATE_LIMIT_PER_MINUTE", "not-a-number")
    client = _client(tmp_path)
    for _ in range(5):
        assert client.get("/problems").status_code in (200, 401)
