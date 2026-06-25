from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import create_app
from app.services.problems import ProblemStore
from app.services.seed import load_seed_problems
from app.services.workflow import WorkflowStore


def _client_with_env(monkeypatch, cors_env: str | None, legacy: str | None = None) -> TestClient:
    monkeypatch.delenv("APP_CORS_ORIGINS", raising=False)
    monkeypatch.delenv("API_CORS_ORIGINS", raising=False)
    if cors_env is not None:
        monkeypatch.setenv("APP_CORS_ORIGINS", cors_env)
    if legacy is not None:
        monkeypatch.setenv("API_CORS_ORIGINS", legacy)

    return TestClient(
        create_app(
            problem_store=ProblemStore(load_seed_problems()),
            workflows=WorkflowStore(),
        )
    )


def test_app_cors_origins_allows_configured_origin(monkeypatch) -> None:
    client = _client_with_env(monkeypatch, cors_env="https://clara-theta-nine.vercel.app")

    response = client.get(
        "/taxonomies",
        headers={"Origin": "https://clara-theta-nine.vercel.app"},
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "https://clara-theta-nine.vercel.app"


def test_default_cors_origins_include_loopback_variants(monkeypatch) -> None:
    client = _client_with_env(monkeypatch, cors_env=None)

    localhost = client.get("/taxonomies", headers={"Origin": "http://localhost:3000"})
    loopback = client.get("/taxonomies", headers={"Origin": "http://127.0.0.1:3000"})

    assert localhost.headers["access-control-allow-origin"] == "http://localhost:3000"
    assert loopback.headers["access-control-allow-origin"] == "http://127.0.0.1:3000"


def test_legacy_api_cors_origins_still_respected(monkeypatch) -> None:
    client = _client_with_env(monkeypatch, cors_env=None, legacy="https://legacy.example")

    response = client.get("/taxonomies", headers={"Origin": "https://legacy.example"})

    assert response.headers["access-control-allow-origin"] == "https://legacy.example"


def test_unlisted_origin_gets_no_allow_origin_header(monkeypatch) -> None:
    client = _client_with_env(monkeypatch, cors_env="https://clara-theta-nine.vercel.app")

    response = client.get("/taxonomies", headers={"Origin": "https://evil.example"})

    assert "access-control-allow-origin" not in response.headers
