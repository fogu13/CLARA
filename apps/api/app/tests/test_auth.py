from __future__ import annotations

import time
from typing import Any

import jwt
import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient


@pytest.fixture
def _no_auth_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Auth disabled — no JWT secret configured (local dev / test default)."""
    monkeypatch.delenv("SUPABASE_JWT_SECRET", raising=False)
    import importlib

    import app.auth as auth_mod

    importlib.reload(auth_mod)


@pytest.fixture
def _auth_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Auth enabled with a test JWT secret."""
    monkeypatch.setenv("SUPABASE_JWT_SECRET", "test-jwt-secret-for-hybrid")
    import importlib

    import app.auth as auth_mod

    importlib.reload(auth_mod)


def _make_token(secret: str, sub: str = "user-123", workspace_id: int = 42, **extra: Any) -> str:
    claims = {
        "sub": sub,
        "email": "test@example.com",
        "workspace_id": workspace_id,
        "exp": int(time.time()) + 3600,
        **extra,
    }
    return jwt.encode(claims, secret, algorithm="HS256")


class TestAuthDisabled:
    def test_returns_default_context_when_no_secret(self, _no_auth_env: None) -> None:
        from app.auth import AUTH_ENABLED, get_current_user

        assert AUTH_ENABLED is False
        user = get_current_user(authorization=None)
        assert user.user_id == "dev-user"
        assert user.workspace_id == 1
        assert user.role == "owner"

    def test_returns_default_context_even_with_header(self, _no_auth_env: None) -> None:
        from app.auth import get_current_user

        user = get_current_user(authorization="Bearer some-garbage")
        assert user.user_id == "dev-user"


class TestAuthEnabled:
    def test_rejects_missing_header(self, _auth_env: None) -> None:
        from fastapi import HTTPException

        from app.auth import get_current_user

        with pytest.raises(HTTPException) as exc_info:
            get_current_user(authorization=None)

        assert exc_info.value.status_code == 401

    def test_rejects_non_bearer_header(self, _auth_env: None) -> None:
        from fastapi import HTTPException

        from app.auth import get_current_user

        with pytest.raises(HTTPException) as exc_info:
            get_current_user(authorization="Basic abc123")

        assert exc_info.value.status_code == 401

    def test_rejects_invalid_token(self, _auth_env: None) -> None:
        from fastapi import HTTPException

        from app.auth import get_current_user

        with pytest.raises(HTTPException) as exc_info:
            get_current_user(authorization="Bearer not-a-real-jwt")

        assert exc_info.value.status_code == 401

    def test_rejects_expired_token(self, _auth_env: None) -> None:
        from fastapi import HTTPException

        from app.auth import get_current_user

        expired = jwt.encode(
            {"sub": "user-1", "exp": int(time.time()) - 100},
            "test-jwt-secret-for-hybrid",
            algorithm="HS256",
        )

        with pytest.raises(HTTPException) as exc_info:
            get_current_user(authorization=f"Bearer {expired}")

        assert exc_info.value.status_code == 401

    def test_returns_user_context_from_valid_token(self, _auth_env: None) -> None:
        from app.auth import get_current_user

        token = _make_token("test-jwt-secret-for-hybrid", sub="user-abc", workspace_id=7)
        user = get_current_user(authorization=f"Bearer {token}")

        assert user.user_id == "user-abc"
        assert user.workspace_id == 7
        assert user.email == "test@example.com"

    def test_defaults_workspace_id_to_1_when_absent(self, _auth_env: None) -> None:
        from app.auth import get_current_user

        token = jwt.encode(
            {"sub": "user-x", "exp": int(time.time()) + 3600},
            "test-jwt-secret-for-hybrid",
            algorithm="HS256",
        )
        user = get_current_user(authorization=f"Bearer {token}")

        assert user.workspace_id == 1

    def test_rejects_token_without_sub(self, _auth_env: None) -> None:
        from fastapi import HTTPException

        from app.auth import get_current_user

        token = jwt.encode(
            {"exp": int(time.time()) + 3600},
            "test-jwt-secret-for-hybrid",
            algorithm="HS256",
        )

        with pytest.raises(HTTPException) as exc_info:
            get_current_user(authorization=f"Bearer {token}")

        assert exc_info.value.status_code == 401


class TestUserContext:
    def test_tenant_setting_returns_string_workspace_id(self, _no_auth_env: None) -> None:
        from app.auth import UserContext

        ctx = UserContext(user_id="u1", workspace_id=99)
        assert ctx.tenant_setting == "99"


class TestVerifyToken:
    def test_raises_500_when_secret_unset(self, _no_auth_env: None) -> None:
        from fastapi import HTTPException

        from app.auth import verify_token

        with pytest.raises(HTTPException) as exc_info:
            verify_token("some-token")

        assert exc_info.value.status_code == 500


class TestAuthInFastAPI:
    """Verify auth works as a FastAPI dependency without breaking existing routes."""

    def test_protected_route_rejects_unauthed_when_enabled(self, _auth_env: None) -> None:
        from app.auth import get_current_user

        app = FastAPI()

        @app.get("/me")
        def me(user=Depends(get_current_user)):
            return {"user_id": user.user_id, "workspace_id": user.workspace_id}

        client = TestClient(app)

        # No auth header -> 401
        resp = client.get("/me")
        assert resp.status_code == 401

        # Valid token -> 200
        token = _make_token("test-jwt-secret-for-hybrid", sub="user-1", workspace_id=5)
        resp = client.get("/me", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        assert resp.json() == {"user_id": "user-1", "workspace_id": 5}

    def test_protected_route_allows_anon_when_disabled(self, _no_auth_env: None) -> None:
        from app.auth import get_current_user

        app = FastAPI()

        @app.get("/me")
        def me(user=Depends(get_current_user)):
            return {"user_id": user.user_id, "workspace_id": user.workspace_id}

        client = TestClient(app)

        # No auth header -> 200 (auth disabled, returns default dev context)
        resp = client.get("/me")
        assert resp.status_code == 200
        assert resp.json() == {"user_id": "dev-user", "workspace_id": 1}
