"""HttpOnly-cookie sessions (docs/engineering/auth-hardening-design.md):
the API accepts the access token from the clara_access_token cookie whenever
no Authorization header is present — additive, bearer keeps working."""

import time

import jwt
import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.services.problems import ProblemStore
from app.services.seed import load_seed_problems
from app.services.workflow import WorkflowStore

SECRET = "cookie-auth-test-secret"


def _token(role: str = "editor") -> str:
    return jwt.encode(
        {
            "sub": "cafebabe-cafe-babe-cafe-babecafebabe",
            "email": f"{role}@example.com",
            "exp": int(time.time()) + 3600,
            "app_metadata": {"workspace_id": 1, "user_role": role},
        },
        SECRET,
        algorithm="HS256",
    )


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr("app.auth.AUTH_ENABLED", True)
    monkeypatch.setattr("app.auth.SUPABASE_JWT_SECRET", SECRET)
    app = create_app(problem_store=ProblemStore(load_seed_problems()), workflows=WorkflowStore())
    return TestClient(app)


def test_cookie_session_authenticates(client) -> None:
    client.cookies.set("clara_access_token", _token())
    response = client.get("/problems")
    assert response.status_code == 200


def test_invalid_cookie_is_rejected(client) -> None:
    client.cookies.set("clara_access_token", "not-a-jwt")
    assert client.get("/problems").status_code == 401


def test_bearer_header_wins_over_cookie(client) -> None:
    # An explicit Authorization header is authoritative; a stale cookie must
    # not silently override it (and bearer-only clients stay unaffected).
    client.cookies.set("clara_access_token", "not-a-jwt")
    response = client.get("/problems", headers={"Authorization": f"Bearer {_token()}"})
    assert response.status_code == 200


def test_no_credentials_still_rejected(client) -> None:
    assert client.get("/problems").status_code == 401


def _aal_token(aal: str | None) -> str:
    payload = {
        "sub": "cafebabe-cafe-babe-cafe-babecafebabe",
        "email": "editor@example.com",
        "exp": int(time.time()) + 3600,
        "app_metadata": {"workspace_id": 1, "user_role": "editor"},
    }
    if aal is not None:
        payload["aal"] = aal
    return jwt.encode(payload, SECRET, algorithm="HS256")


def test_aal2_mandate_rejects_password_only_sessions(client, monkeypatch) -> None:
    monkeypatch.setattr("app.auth.REQUIRE_AAL2", True)
    headers = {"Authorization": f"Bearer {_aal_token('aal1')}"}
    response = client.get("/problems", headers=headers)
    assert response.status_code == 401
    assert "MFA required" in response.text

    ok = client.get("/problems", headers={"Authorization": f"Bearer {_aal_token('aal2')}"})
    assert ok.status_code == 200


def test_aal1_allowed_when_mandate_off(client) -> None:
    response = client.get("/problems", headers={"Authorization": f"Bearer {_aal_token('aal1')}"})
    assert response.status_code == 200
