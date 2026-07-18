from __future__ import annotations

import time
from typing import Any

import jwt
import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient


@pytest.fixture
def _no_auth_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Auth disabled — no JWT secret and no JWKS URL (local dev / test default)."""
    monkeypatch.delenv("SUPABASE_JWT_SECRET", raising=False)
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.delenv("CLARA_REQUIRE_AUTH", raising=False)
    import importlib

    import app.auth as auth_mod

    importlib.reload(auth_mod)


@pytest.fixture
def _auth_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Auth enabled with a test HS256 JWT secret (no JWKS URL)."""
    monkeypatch.setenv("SUPABASE_JWT_SECRET", "test-jwt-secret-for-hybrid")
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.delenv("CLARA_REQUIRE_AUTH", raising=False)
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
        from app.auth import AUTH_ENABLED, _resolve_user

        assert AUTH_ENABLED is False
        user = _resolve_user(authorization=None)
        assert user.user_id == "dev-user"
        assert user.workspace_id == 1
        assert user.role == "owner"

    def test_returns_default_context_even_with_header(self, _no_auth_env: None) -> None:
        from app.auth import _resolve_user

        user = _resolve_user(authorization="Bearer some-garbage")
        assert user.user_id == "dev-user"


class TestAuthEnabled:
    def test_rejects_missing_header(self, _auth_env: None) -> None:
        from fastapi import HTTPException

        from app.auth import _resolve_user

        with pytest.raises(HTTPException) as exc_info:
            _resolve_user(authorization=None)

        assert exc_info.value.status_code == 401

    def test_rejects_non_bearer_header(self, _auth_env: None) -> None:
        from fastapi import HTTPException

        from app.auth import _resolve_user

        with pytest.raises(HTTPException) as exc_info:
            _resolve_user(authorization="Basic abc123")

        assert exc_info.value.status_code == 401

    def test_rejects_invalid_token(self, _auth_env: None) -> None:
        from fastapi import HTTPException

        from app.auth import _resolve_user

        with pytest.raises(HTTPException) as exc_info:
            _resolve_user(authorization="Bearer not-a-real-jwt")

        assert exc_info.value.status_code == 401

    def test_rejects_expired_token(self, _auth_env: None) -> None:
        from fastapi import HTTPException

        from app.auth import _resolve_user

        expired = jwt.encode(
            {"sub": "user-1", "exp": int(time.time()) - 100},
            "test-jwt-secret-for-hybrid",
            algorithm="HS256",
        )

        with pytest.raises(HTTPException) as exc_info:
            _resolve_user(authorization=f"Bearer {expired}")

        assert exc_info.value.status_code == 401

    def test_returns_user_context_from_valid_token(self, _auth_env: None) -> None:
        from app.auth import _resolve_user

        token = _make_token("test-jwt-secret-for-hybrid", sub="user-abc", workspace_id=7)
        user = _resolve_user(authorization=f"Bearer {token}")

        assert user.user_id == "user-abc"
        assert user.workspace_id == 7
        assert user.email == "test@example.com"

    def test_defaults_workspace_id_to_1_when_absent(self, _auth_env: None) -> None:
        from app.auth import _resolve_user

        token = jwt.encode(
            {"sub": "user-x", "exp": int(time.time()) + 3600},
            "test-jwt-secret-for-hybrid",
            algorithm="HS256",
        )
        user = _resolve_user(authorization=f"Bearer {token}")

        assert user.workspace_id == 1

    def test_rejects_token_without_sub(self, _auth_env: None) -> None:
        from fastapi import HTTPException

        from app.auth import _resolve_user

        token = jwt.encode(
            {"exp": int(time.time()) + 3600},
            "test-jwt-secret-for-hybrid",
            algorithm="HS256",
        )

        with pytest.raises(HTTPException) as exc_info:
            _resolve_user(authorization=f"Bearer {token}")

        assert exc_info.value.status_code == 401


class TestUserContext:
    def test_tenant_setting_returns_string_workspace_id(self, _no_auth_env: None) -> None:
        from app.auth import UserContext

        ctx = UserContext(user_id="u1", workspace_id=99)
        assert ctx.tenant_setting == "99"


class TestVerifyToken:
    def test_raises_500_for_hs256_token_when_secret_unset(self, _no_auth_env: None) -> None:
        from fastapi import HTTPException

        from app.auth import verify_token

        # A structurally valid HS256 token, but no secret is configured to verify it.
        hs_token = jwt.encode({"sub": "x"}, "irrelevant", algorithm="HS256")
        with pytest.raises(HTTPException) as exc_info:
            verify_token(hs_token)

        assert exc_info.value.status_code == 500

    def test_raises_401_for_garbage_token(self, _auth_env: None) -> None:
        from fastapi import HTTPException

        from app.auth import verify_token

        with pytest.raises(HTTPException) as exc_info:
            verify_token("not-a-jwt")

        assert exc_info.value.status_code == 401


class TestAppMetadataClaims:
    def test_resolves_role_and_workspace_from_app_metadata(self, _auth_env: None) -> None:
        from app.auth import _resolve_user

        token = _make_token(
            "test-jwt-secret-for-hybrid",
            sub="admin-1",
            app_metadata={"user_role": "owner", "workspace_id": 2},
        )
        user = _resolve_user(authorization=f"Bearer {token}")

        assert user.role == "owner"
        assert user.workspace_id == 2

    def test_app_metadata_overrides_top_level_claims(self, _auth_env: None) -> None:
        from app.auth import _resolve_user

        token = _make_token(
            "test-jwt-secret-for-hybrid",
            sub="admin-2",
            user_role="viewer",  # top-level
            app_metadata={"user_role": "admin"},  # app_metadata wins
        )
        user = _resolve_user(authorization=f"Bearer {token}")

        assert user.role == "admin"


class TestAsymmetricVerification:
    def test_es256_token_verified_via_jwks(
        self, _auth_env: None, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        pytest.importorskip("cryptography")
        from cryptography.hazmat.primitives.asymmetric import ec

        import app.auth as auth_mod

        private_key = ec.generate_private_key(ec.SECP256R1())
        token = jwt.encode(
            {
                "sub": "user-es",
                "app_metadata": {"user_role": "owner", "workspace_id": 3},
                "exp": int(time.time()) + 3600,
            },
            private_key,
            algorithm="ES256",
        )

        class _FakeSigningKey:
            key = private_key.public_key()

        class _FakeJWKSClient:
            def get_signing_key_from_jwt(self, _token: str) -> _FakeSigningKey:
                return _FakeSigningKey()

        monkeypatch.setattr(auth_mod, "_jwks_client", lambda: _FakeJWKSClient())

        user = auth_mod._resolve_user(authorization=f"Bearer {token}")
        assert user.user_id == "user-es"
        assert user.role == "owner"
        assert user.workspace_id == 3


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


def test_deployment_fails_closed_without_auth_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Audit finding A1: with a real backend (DATABASE_URL) but no JWT env and
    no explicit override, auth must refuse to boot rather than run role=owner."""
    import importlib

    import app.auth as auth_mod

    monkeypatch.delenv("SUPABASE_JWT_SECRET", raising=False)
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.delenv("CLARA_REQUIRE_AUTH", raising=False)
    monkeypatch.setenv("DATABASE_URL", "postgresql://x/y")
    try:
        with pytest.raises(RuntimeError, match="refusing to start"):
            importlib.reload(auth_mod)

        # Explicit opt-out still permitted (e.g. a deliberately open staging box).
        monkeypatch.setenv("CLARA_REQUIRE_AUTH", "false")
        importlib.reload(auth_mod)
        assert auth_mod.AUTH_ENABLED is False
    finally:
        monkeypatch.setenv("DATABASE_URL", "")
        monkeypatch.delenv("CLARA_REQUIRE_AUTH", raising=False)
        importlib.reload(auth_mod)


def test_owner_email_bootstrap_elevates_to_owner(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A CLARA_OWNER_EMAILS address is always owner, even with no app_metadata
    role — the founder-lockout fix. Case-insensitive; non-listed stays viewer."""
    import importlib

    import app.auth as auth_mod

    monkeypatch.setenv("SUPABASE_JWT_SECRET", "test-jwt-secret-for-hybrid")
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.delenv("CLARA_REQUIRE_AUTH", raising=False)
    monkeypatch.setenv("DATABASE_URL", "")
    monkeypatch.setenv("CLARA_OWNER_EMAILS", "Founder@Example.com, ops@x.com")
    importlib.reload(auth_mod)
    try:
        founder = _make_token(
            "test-jwt-secret-for-hybrid", sub="f-1", email="founder@example.com"
        )
        assert auth_mod._resolve_user(authorization=f"Bearer {founder}").role == "owner"

        # Not on the list -> default viewer, unchanged.
        other = _make_token(
            "test-jwt-secret-for-hybrid", sub="v-1", email="nobody@example.com"
        )
        assert auth_mod._resolve_user(authorization=f"Bearer {other}").role == "viewer"

        # An explicit app_metadata role is preserved for non-owner emails.
        editor = _make_token(
            "test-jwt-secret-for-hybrid", sub="e-1", email="ed@example.com",
            app_metadata={"user_role": "editor"},
        )
        assert auth_mod._resolve_user(authorization=f"Bearer {editor}").role == "editor"
    finally:
        # Fully restore the auth-disabled test default BEFORE reloading —
        # monkeypatch only reverts env at teardown (after this block), so the
        # reload must see clean env or AUTH_ENABLED leaks True into later tests.
        monkeypatch.delenv("CLARA_OWNER_EMAILS", raising=False)
        monkeypatch.delenv("SUPABASE_JWT_SECRET", raising=False)
        monkeypatch.delenv("SUPABASE_URL", raising=False)
        importlib.reload(auth_mod)
