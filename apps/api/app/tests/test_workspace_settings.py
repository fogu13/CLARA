from fastapi.testclient import TestClient

from app.main import create_app
from app.services.problems import ProblemStore
from app.services.seed import load_seed_problems
from app.services.signals import SignalStore
from app.services.workflow import WorkflowStore
from app.services.workspace import SQLiteWorkspaceStore


def make_client(tmp_path) -> TestClient:
    return TestClient(
        create_app(
            problem_store=ProblemStore(load_seed_problems()),
            workflows=WorkflowStore(),
            signals=SignalStore(),
            workspace=SQLiteWorkspaceStore(tmp_path / "workspace.db"),
        )
    )


def test_workspace_settings_round_trip(tmp_path) -> None:
    client = make_client(tmp_path)

    assert client.get("/workspace").json()["name"] == "My Workspace"

    updated = client.put(
        "/workspace",
        json={
            "name": "Acme",
            "slug": "acme",
            "notification_email": "alerts@acme.com",
            "measurement_window_days": 30,
            "learning_half_life_days": 90,
        },
    )
    assert updated.status_code == 200

    after = client.get("/workspace").json()
    assert after["name"] == "Acme"
    assert after["measurement_window_days"] == 30
    assert after["notification_email"] == "alerts@acme.com"


def test_system_config_reports_ai_settings(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("AI_BASE_URL", "https://api.mistral.ai/v1")
    monkeypatch.setenv("AI_MODEL", "mistral-small-latest")
    client = make_client(tmp_path)

    config = client.get("/system-config").json()
    assert config["ai_base_url"] == "https://api.mistral.ai/v1"
    assert config["ai_model"] == "mistral-small-latest"


def test_ai_settings_runtime_override_and_redaction(monkeypatch, tmp_path) -> None:
    import app.services.ai as ai

    monkeypatch.setenv("AI_BASE_URL", "https://env.example/v1")
    monkeypatch.setenv("AI_MODEL", "env-model")
    client = make_client(tmp_path)

    saved = client.put(
        "/settings/ai",
        json={"base_url": "http://localhost:11434/v1", "model": "qwen3:32b", "api_key": "sk-local"},
    ).json()
    assert saved == {"ai_base_url": "http://localhost:11434/v1", "ai_model": "qwen3:32b", "key_set": True}

    config = client.get("/system-config").json()
    assert config["ai_model"] == "qwen3:32b"

    # The stored key is redacted on the connector read path.
    connectors = client.get("/connectors").json()
    ai_row = next(c for c in connectors if c["connector_type"] == "ai")
    assert ai_row["config"]["api_key"] != "sk-local"

    # Empty key on re-save keeps the stored one; empty url/model fall back to env.
    client.put("/settings/ai", json={"base_url": "", "model": "", "api_key": ""})
    assert ai.effective_api_key() == "sk-local"
    assert client.get("/system-config").json()["ai_model"] == "env-model"

    # rejected: non-http url
    assert client.put("/settings/ai", json={"base_url": "ftp://x"}).status_code == 422
    ai.set_runtime_config()  # reset for other tests
