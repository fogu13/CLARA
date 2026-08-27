from __future__ import annotations

import importlib
import os
import time

import jwt
import pytest
from fastapi.testclient import TestClient

from app.services.problems import ProblemStore
from app.services.seed import load_seed_problems
from app.services.signals import SignalStore
from app.services.workflow import WorkflowStore

SECRET = "test-secret-32-chars-minimum-length!"


@pytest.fixture(autouse=True)
def _reset_auth_modules_after_each_test():
    """Root fix for cross-file pollution: make_auth_client reloads app modules with
    a JWT secret set, which leaves AUTH_ENABLED=True for every later test FILE
    (surfaced first as 401s on gated reads, then as the rate limiter enforcing on
    /ask). Reset at the SOURCE so no downstream file inherits a gated app."""
    yield
    os.environ.pop("SUPABASE_JWT_SECRET", None)
    import app.auth
    import app.main
    import app.rate_limit
    import app.rbac

    for mod in (app.auth, app.rbac, app.rate_limit, app.main):
        importlib.reload(mod)


def token(role: str) -> str:
    return jwt.encode(
        {
            "sub": f"user-{role}",
            "workspace_id": 1,
            "user_role": role,
            "exp": int(time.time()) + 3600,
        },
        SECRET,
        algorithm="HS256",
    )


def make_auth_client(monkeypatch) -> TestClient:
    monkeypatch.setenv("SUPABASE_JWT_SECRET", SECRET)

    import app.auth as auth_mod
    import app.rbac as rbac_mod
    import app.main as main_mod

    importlib.reload(auth_mod)
    importlib.reload(rbac_mod)
    importlib.reload(main_mod)

    from app.connectors.config_store import ConnectorConfigStore

    return TestClient(
        main_mod.create_app(
            problem_store=ProblemStore(load_seed_problems()),
            signals=SignalStore(),
            workflows=WorkflowStore(),
            # Isolated in-memory store: the connector PUT test must not persist a
            # half-configured Jira into the shared DB and trip later approval tests.
            connector_configs=ConnectorConfigStore(),
        )
    )


def make_auth_client_with_connectors(monkeypatch, connector_store) -> TestClient:
    monkeypatch.setenv("SUPABASE_JWT_SECRET", SECRET)

    import app.auth as auth_mod
    import app.rbac as rbac_mod
    import app.main as main_mod

    importlib.reload(auth_mod)
    importlib.reload(rbac_mod)
    importlib.reload(main_mod)

    return TestClient(
        main_mod.create_app(
            problem_store=ProblemStore(load_seed_problems()),
            signals=SignalStore(),
            workflows=WorkflowStore(),
            connector_configs=connector_store,
        )
    )


def auth_header(role: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token(role)}"}


def test_write_route_requires_auth_when_auth_enabled(monkeypatch) -> None:
    client = make_auth_client(monkeypatch)

    response = client.post(
        "/problems/PRB-108/approvals",
        json={
            "action_id": "ACT-501",
            "decision": "approved",
            "reviewer": "test_product_owner",
        },
    )

    assert response.status_code == 401


def test_viewer_cannot_import_signals(monkeypatch) -> None:
    client = make_auth_client(monkeypatch)

    response = client.post(
        "/signals/import",
        headers=auth_header("viewer"),
        json={"signals": []},
    )

    assert response.status_code == 403


def test_editor_can_import_signals(monkeypatch) -> None:
    client = make_auth_client(monkeypatch)

    response = client.post(
        "/signals/import",
        headers=auth_header("editor"),
        json={"signals": []},
    )

    assert response.status_code == 200


def test_policy_evaluate_requires_editor(monkeypatch) -> None:
    client = make_auth_client(monkeypatch)
    body = {"source": "api", "destination": "zendesk", "governance_checks": []}

    viewer_response = client.post(
        "/policy/evaluate", headers=auth_header("viewer"), json=body
    )
    editor_response = client.post(
        "/policy/evaluate", headers=auth_header("editor"), json=body
    )

    assert viewer_response.status_code == 403
    assert editor_response.status_code == 200
    assert editor_response.json()["decision"] == "block"


def test_connector_configuration_requires_admin(monkeypatch) -> None:
    client = make_auth_client(monkeypatch)

    editor_response = client.put(
        "/connectors/jira",
        headers=auth_header("editor"),
        json={"base_url": "https://example.atlassian.net", "project_key": "CLARA"},
    )
    admin_response = client.put(
        "/connectors/jira",
        headers=auth_header("admin"),
        json={"base_url": "https://example.atlassian.net", "project_key": "CLARA"},
    )

    assert editor_response.status_code == 403
    assert admin_response.status_code == 200

def test_audit_export_requires_admin(monkeypatch) -> None:
    client = make_auth_client(monkeypatch)

    viewer_response = client.get("/audit-export", headers=auth_header("viewer"))
    admin_response = client.get("/audit-export", headers=auth_header("admin"))

    assert viewer_response.status_code == 403
    assert admin_response.status_code == 200
    assert set(admin_response.json()) == {"approvals", "executions", "closure_records", "jira_issue_drafts"}


def test_article50_status_readable_by_viewer(monkeypatch) -> None:
    client = make_auth_client(monkeypatch)

    assert client.get("/article50-status").status_code == 401

    response = client.get("/article50-status", headers=auth_header("viewer"))
    assert response.status_code == 200
    assert set(response.json()) == {
        "human_reviewed",
        "auto_published",
        "unpublished_count",
        "by_destination",
        "generated_at",
    }


def test_connector_listing_requires_admin_and_redacts_secrets(monkeypatch) -> None:
    from app.connectors.config_store import ConnectorConfig, ConnectorConfigStore

    store = ConnectorConfigStore(
        [
            ConnectorConfig(
                connector_type="slack",
                config={"bot_token": "xoxb-supersecret", "channel": "#alerts"},
            )
        ]
    )
    client = make_auth_client_with_connectors(monkeypatch, store)

    # Read path must be admin-gated like the write/pull/test paths.
    assert client.get("/connectors", headers=auth_header("viewer")).status_code == 403

    response = client.get("/connectors", headers=auth_header("admin"))
    assert response.status_code == 200
    config = response.json()[0]["config"]
    assert config["bot_token"] == "***redacted***"
    assert config["channel"] == "#alerts"  # non-secret fields pass through
    assert "xoxb-supersecret" not in response.text


def test_connector_update_preserves_secret_when_blank(monkeypatch) -> None:
    from app.connectors.config_store import ConnectorConfig, ConnectorConfigStore

    store = ConnectorConfigStore(
        [
            ConnectorConfig(
                connector_type="slack",
                config={"bot_token": "xoxb-supersecret", "channel": "#alerts"},
            )
        ]
    )
    client = make_auth_client_with_connectors(monkeypatch, store)

    # Operator edits a non-secret field; the redacted token comes back blank from the form.
    response = client.put(
        "/connectors/slack",
        headers=auth_header("admin"),
        json={"channel": "#newchannel", "bot_token": ""},
    )
    assert response.status_code == 200

    stored = store.get_config("slack")
    assert stored is not None
    assert stored.config["bot_token"] == "xoxb-supersecret"  # not wiped
    assert stored.config["channel"] == "#newchannel"
