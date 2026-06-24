from __future__ import annotations

import importlib
import time

import jwt
from fastapi.testclient import TestClient

from app.services.problems import ProblemStore
from app.services.seed import load_seed_problems
from app.services.signals import SignalStore
from app.services.workflow import WorkflowStore

SECRET = "test-secret-32-chars-minimum-length!"


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

    return TestClient(
        main_mod.create_app(
            problem_store=ProblemStore(load_seed_problems()),
            signals=SignalStore(),
            workflows=WorkflowStore(),
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
    assert set(admin_response.json()) == {"approvals", "executions", "jira_issue_drafts"}
