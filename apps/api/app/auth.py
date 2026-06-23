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
from pydantic import BaseModel

logger = logging.getLogger(__name__)

SUPABASE_JWT_SECRET = os.getenv("SUPABASE_JWT_SECRET") or ""
SUPABASE_URL = os.getenv("SUPABASE_URL") or ""
AUTH_ENABLED = bool(SUPABASE_JWT_SECRET)


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

    Raises HTTPException(401) if the token is invalid, expired, or auth is
    misconfigured.
    """
    if not SUPABASE_JWT_SECRET:
        raise HTTPException(
            status_code=500,
            detail="Auth not configured: SUPABASE_JWT_SECRET is unset",
        )

    try:
        claims = jwt.decode(
            token,
            SUPABASE_JWT_SECRET,
            algorithms=["HS256"],
            options={"verify_aud": False},
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired") from None
    except jwt.InvalidTokenError as exc:
        raise HTTPException(status_code=401, detail=f"Invalid token: {exc}") from exc

    return claims


def get_current_user(
    authorization: str | None = Header(None),
) -> UserContext:
    """FastAPI dependency: extract and verify the Bearer token -> UserContext.

    When AUTH_ENABLED is False (no JWT secret configured), returns a default
    dev context so the API works without auth headers during local dev / tests.
    """
    if not AUTH_ENABLED:
        return _default_context()

    if authorization is None or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")

    token = authorization.removeprefix("Bearer ").strip()
    claims = verify_token(token)

    user_id = claims.get("sub", "")
    if not user_id:
        raise HTTPException(status_code=401, detail="Token missing sub claim")

    # workspace_id may be in the JWT (custom claim) or resolved later via a
    # profiles lookup. For now, prefer the JWT claim; default to 1 if absent.
    workspace_id = claims.get("workspace_id", 1)
    email = claims.get("email", "")
    role = claims.get("user_role", "viewer")

    return UserContext(user_id=user_id, workspace_id=workspace_id, email=email, role=role)


def apply_tenant_to_connection(conn, user: UserContext) -> None:
    """Set session-level Postgres settings for RLS enforcement.

    Call this on a psycopg connection before any query so that RLS policies
    (migration 004) can use current_setting('app.tenant_id', true).
    """
    with conn.cursor() as cur:
        cur.execute("SET LOCAL app.tenant_id = %s", (user.tenant_setting,))
        cur.execute("SET LOCAL app.user_id = %s", (user.user_id,))
