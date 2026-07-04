"""Supabase JWT authentication for FastAPI.

Verifies Supabase-issued JWTs (HS256 with the project JWT secret, or RS256 via
JWKS) and extracts user identity + workspace context. Sets session-level
Postgres settings (app.tenant_id, app.user_id) for RLS enforcement.

Auth is optional during the Phase 0 transition: if SUPABASE_JWT_SECRET is unset,
`get_current_user` returns a default context (workspace_id=1, the default
workspace) so existing tests and local dev keep working without auth headers.
Once auth is enabled, protected routes reject requests without a valid JWT.
"""

from __future__ import annotations

import logging
import os

import jwt
from fastapi import Header, HTTPException
from jwt import PyJWKClient
from pydantic import BaseModel

logger = logging.getLogger(__name__)

SUPABASE_JWT_SECRET = os.getenv("SUPABASE_JWT_SECRET") or ""
SUPABASE_URL = (os.getenv("SUPABASE_URL") or "").rstrip("/")
# Auth is enabled if tokens can be verified either way: a JWKS URL (asymmetric ES256/RS256 —
# the modern Supabase default) or a shared HS256 secret (legacy / local).
AUTH_ENABLED = bool(SUPABASE_JWT_SECRET or SUPABASE_URL)

_JWKS_URL = f"{SUPABASE_URL}/auth/v1/.well-known/jwks.json" if SUPABASE_URL else ""
_jwk_client: PyJWKClient | None = None

# Fail-closed guard. The dev fallback below grants role=owner to every unauthenticated
# request, which is convenient locally but catastrophic in production. Set
# CLARA_REQUIRE_AUTH=true in any real deployment so missing auth config refuses to boot
# instead of silently disabling auth.
REQUIRE_AUTH = (os.getenv("CLARA_REQUIRE_AUTH") or "").strip().lower() in {"1", "true", "yes", "on"}
if REQUIRE_AUTH and not AUTH_ENABLED:
    raise RuntimeError(
        "CLARA_REQUIRE_AUTH is set but neither SUPABASE_URL (JWKS) nor SUPABASE_JWT_SECRET "
        "is configured — refusing to start with authentication disabled."
    )
if not AUTH_ENABLED:
    logger.warning(
        "Neither SUPABASE_URL nor SUPABASE_JWT_SECRET is set: authentication is DISABLED and "
        "every request is treated as role=owner. Configure auth (and CLARA_REQUIRE_AUTH=true) "
        "before deploying."
    )


def _jwks_client() -> PyJWKClient:
    """Lazily build (and cache) the JWKS client for asymmetric token verification."""
    global _jwk_client
    if _jwk_client is None:
        if not _JWKS_URL:
            raise HTTPException(
                status_code=500, detail="Auth not configured: SUPABASE_URL is unset"
            )
        _jwk_client = PyJWKClient(_JWKS_URL)
    return _jwk_client


class UserContext(BaseModel):
    """Identity + tenant context extracted from a verified Supabase JWT."""

    user_id: str
    workspace_id: int = 1
    email: str = ""
    role: str = "viewer"

    @property
    def tenant_setting(self) -> str:
        """Value to SET app.tenant_id to on a psycopg connection for RLS."""
        return str(self.workspace_id)


def _default_context() -> UserContext:
    """Fallback context when auth is disabled (local dev / tests)."""
    return UserContext(user_id="dev-user", workspace_id=1, email="dev@local", role="owner")


def verify_token(token: str) -> dict:
    """Verify a Supabase JWT and return its claims.

    Routes on the token's `alg`: ES256/RS256 (asymmetric, the modern Supabase default) are
    verified against the project JWKS; HS256 is verified with the shared secret. Raises
    HTTPException(401) if the token is invalid/expired, 500 if auth is misconfigured.
    """
    try:
        alg = jwt.get_unverified_header(token).get("alg", "")
        if alg.startswith(("ES", "RS")):
            signing_key = _jwks_client().get_signing_key_from_jwt(token).key
            return jwt.decode(
                token,
                signing_key,
                algorithms=["ES256", "RS256"],
                options={"verify_aud": False},
            )
        if not SUPABASE_JWT_SECRET:
            raise HTTPException(
                status_code=500,
                detail="Auth not configured: no SUPABASE_JWT_SECRET for HS256 tokens",
            )
        return jwt.decode(
            token,
            SUPABASE_JWT_SECRET,
            algorithms=["HS256"],
            options={"verify_aud": False},
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired") from None
    except jwt.PyJWTError as exc:
        raise HTTPException(status_code=401, detail=f"Invalid token: {exc}") from exc


# create_app registers the active key store here so the dependency can verify
# X-Api-Key headers without import cycles. None until an app is constructed.
_API_KEY_VERIFIER = None


def set_api_key_verifier(verify) -> None:
    global _API_KEY_VERIFIER
    _API_KEY_VERIFIER = verify


def get_current_user(
    authorization: str | None = Header(None),
    x_api_key: str | None = Header(None),
) -> UserContext:
    """FastAPI dependency: verify X-Api-Key or the Bearer token -> UserContext.

    When AUTH_ENABLED is False (no JWT secret configured), returns a default
    dev context so the API works without auth headers during local dev / tests.
    An explicitly provided API key is ALWAYS verified strictly, in both modes:
    a bad key must fail loudly, never fall through to a permissive default.
    """
    if isinstance(x_api_key, str) and x_api_key:  # direct calls pass no header; FastAPI injects str|None
        record = _API_KEY_VERIFIER(x_api_key) if _API_KEY_VERIFIER else None
        if record is None:
            raise HTTPException(status_code=401, detail="Invalid or revoked API key")
        return UserContext(
            user_id=f"api-key:{record['id']}",
            workspace_id=1,
            email=f"api-key:{record['name']}",
            role=record["role"],
        )

    if not AUTH_ENABLED:
        return _default_context()

    if authorization is None or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")

    token = authorization.removeprefix("Bearer ").strip()
    claims = verify_token(token)

    user_id = claims.get("sub", "")
    if not user_id:
        raise HTTPException(status_code=401, detail="Token missing sub claim")

    # Role/workspace live in app_metadata (admin-controlled, not user-editable), which
    # Supabase embeds in the JWT. Fall back to top-level custom claims, then defaults.
    app_metadata = claims.get("app_metadata") or {}
    workspace_id = app_metadata.get("workspace_id", claims.get("workspace_id", 1))
    role = app_metadata.get("user_role", claims.get("user_role", "viewer"))
    email = claims.get("email", "")

    return UserContext(user_id=user_id, workspace_id=workspace_id, email=email, role=role)


def apply_tenant_to_connection(conn, user: UserContext) -> None:
    """Set session-level Postgres settings for RLS enforcement.

    Call this on a psycopg connection before any query so that RLS policies
    (migration 004) can use current_setting('app.tenant_id', true).
    """
    with conn.cursor() as cur:
        cur.execute("SET LOCAL app.tenant_id = %s", (user.tenant_setting,))
        cur.execute("SET LOCAL app.user_id = %s", (user.user_id,))
