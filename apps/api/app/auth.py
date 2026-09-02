"""Supabase JWT authentication for FastAPI.

Verifies Supabase-issued JWTs (HS256 with the project JWT secret, or RS256 via
JWKS) and extracts user identity + workspace context. `get_current_user` also
records the tenant in a request-scoped ContextVar; the Postgres store layer
(PostgresConnectionMixin._connect) reads it to SET app.tenant_id /
app.workspace_id on every pooled checkout, which is what drives RLS.

Auth is optional during the Phase 0 transition: if SUPABASE_JWT_SECRET is unset,
`get_current_user` returns a default context (workspace_id=1, the default
workspace) so existing tests and local dev keep working without auth headers.
Once auth is enabled, protected routes reject requests without a valid JWT.
"""

from __future__ import annotations

import logging
import os
from contextvars import ContextVar, Token

import jwt
from fastapi import Cookie, Header, HTTPException
from fastapi.concurrency import run_in_threadpool
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
# request, which is convenient locally but catastrophic in production. To avoid a prod
# deploy silently running open if the JWT env is ever lost, CLARA_REQUIRE_AUTH now
# DEFAULTS to on whenever a real backend (DATABASE_URL) is configured — i.e. a
# deployment. Dev and the test suite run without DATABASE_URL (conftest blanks it) and
# keep the open dev context. An explicit CLARA_REQUIRE_AUTH=false still overrides.
_require_auth_env = (os.getenv("CLARA_REQUIRE_AUTH") or "").strip().lower()
if _require_auth_env in {"1", "true", "yes", "on"}:
    REQUIRE_AUTH = True
elif _require_auth_env in {"0", "false", "no", "off"}:
    REQUIRE_AUTH = False
else:
    REQUIRE_AUTH = bool((os.getenv("DATABASE_URL") or "").strip())
# MFA mandate (see the aal check in _resolve_user). Off by default: flip only
# after every workspace user has enrolled a TOTP factor.
REQUIRE_AAL2 = (os.getenv("CLARA_REQUIRE_AAL2") or "").strip().lower() in {"1", "true", "yes", "on"}

# Founder/owner bootstrap. Roles normally live in Supabase app_metadata, but a
# user whose app_metadata has no user_role defaults to `viewer` — which locked
# the founder out of every admin feature with no admin present to fix it
# (chicken-and-egg). Any verified JWT whose email is listed here is elevated to
# `owner`. Safe: the email comes from the verified token (a user can't claim
# someone else's verified email), and it can only ELEVATE, never demote.
OWNER_EMAILS = frozenset(
    e.strip().lower()
    for e in (os.getenv("CLARA_OWNER_EMAILS") or "").split(",")
    if e.strip()
)
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


# Request-scoped tenant. get_current_user (async, runs in the request task) sets it;
# the value propagates into threadpool-run sync endpoints and store calls, where
# PostgresConnectionMixin._connect applies it as the RLS GUCs. The default "1" keeps
# boot-time seeding, background loops, and unauthenticated paths pinned to the
# default workspace — fail-closed, never cross-tenant.
_current_tenant: ContextVar[str] = ContextVar("clara_current_tenant", default="1")


def current_tenant() -> str:
    return _current_tenant.get()


def set_current_tenant(value: str) -> Token[str]:
    """Set the active tenant; returns the Token so callers (tests, smoke) can reset."""
    return _current_tenant.set(value)


# Request-scoped caller identity for the works-council response middleware:
# (role, workspace_id) of the verified principal, or None before auth ran on
# this request (routes without the get_current_user dependency, e.g. /health).
# Same propagation rules as _current_tenant above: get_current_user is async
# and runs in the request task, so the value it sets is visible to the pure-ASGI
# middleware wrapping that same task. The middleware resets it per request.
_current_request_user: ContextVar[tuple[str, int] | None] = ContextVar(
    "clara_current_request_user", default=None
)


def current_request_user() -> tuple[str, int] | None:
    """(role, workspace_id) of the current request's verified principal, if any."""
    return _current_request_user.get()


def set_current_request_user(
    value: tuple[str, int] | None,
) -> Token[tuple[str, int] | None]:
    return _current_request_user.set(value)


def reset_current_request_user(token: Token[tuple[str, int] | None]) -> None:
    _current_request_user.reset(token)


def verify_token(token: str) -> dict:
    """Verify a Supabase JWT and return its claims.

    Routes on the token's `alg`: ES256/RS256 (asymmetric, the modern Supabase default) are
    verified against the project JWKS; HS256 is verified with the shared secret. Raises
    HTTPException(401) if the token is invalid/expired, 500 if auth is misconfigured.
    """
    # Supabase mints access tokens with aud="authenticated" and iss=<url>/auth/v1.
    # In a real deployment (REQUIRE_AUTH) both are verified, so a token minted
    # for another audience with a shared HS256 secret is refused; local/dev
    # tokens (tests) carry neither claim and stay accepted.
    decode_options = {"verify_aud": REQUIRE_AUTH}
    decode_kwargs: dict = {}
    if REQUIRE_AUTH:
        decode_kwargs["audience"] = "authenticated"
        if SUPABASE_URL:
            decode_kwargs["issuer"] = f"{SUPABASE_URL}/auth/v1"
    try:
        alg = jwt.get_unverified_header(token).get("alg", "")
        if alg.startswith(("ES", "RS")):
            signing_key = _jwks_client().get_signing_key_from_jwt(token).key
            return jwt.decode(
                token,
                signing_key,
                algorithms=["ES256", "RS256"],
                options=decode_options,
                **decode_kwargs,
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
            options=decode_options,
            **decode_kwargs,
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


def _resolve_user(
    authorization: str | None = None,
    x_api_key: str | None = None,
) -> UserContext:
    """Verify X-Api-Key or the Bearer token -> UserContext (sync core).

    When AUTH_ENABLED is False (no JWT secret configured), returns a default
    dev context so the API works without auth headers during local dev / tests.
    An explicitly provided API key is ALWAYS verified strictly, in both modes:
    a bad key must fail loudly, never fall through to a permissive default.
    """
    if isinstance(x_api_key, str) and x_api_key:  # direct calls pass no header; FastAPI injects str|None
        record = _API_KEY_VERIFIER(x_api_key) if _API_KEY_VERIFIER else None
        if record is None:
            raise HTTPException(status_code=401, detail="Invalid or revoked API key")
        # The key's own workspace (Postgres stores return it; SQLite is single
        # workspace). Pinning every key to workspace 1 made keys minted by any
        # other workspace act inside the default tenant.
        try:
            key_workspace = int(record.get("workspace_id") or 1)
        except (TypeError, ValueError):
            key_workspace = 1
        return UserContext(
            user_id=f"api-key:{record['id']}",
            workspace_id=key_workspace,
            email=f"api-key:{record['name']}",
            role=record["role"],
        )

    if not AUTH_ENABLED:
        return _default_context()

    if authorization is None or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")

    token = authorization.removeprefix("Bearer ").strip()
    claims = verify_token(token)

    # Optional MFA mandate: once every user is enrolled, CLARA_REQUIRE_AAL2=true
    # rejects password-only (aal1) sessions — otherwise the legacy bearer flow
    # could silently bypass the TOTP challenge. Default off (enrollment first).
    if REQUIRE_AAL2 and claims.get("aal") != "aal2":
        raise HTTPException(status_code=401, detail="MFA required: sign in with your second factor")

    user_id = claims.get("sub", "")
    if not user_id:
        raise HTTPException(status_code=401, detail="Token missing sub claim")

    # Role/workspace live in app_metadata (admin-controlled, not user-editable), which
    # Supabase embeds in the JWT. Fall back to top-level custom claims, then defaults.
    app_metadata = claims.get("app_metadata") or {}
    raw_workspace = app_metadata.get("workspace_id", claims.get("workspace_id"))
    role = app_metadata.get("user_role", claims.get("user_role", "viewer"))
    email = claims.get("email", "")
    is_bootstrap_owner = bool(email and email.lower() in OWNER_EMAILS)

    # Fail closed on tenancy: a verified login with NO workspace assignment used
    # to fall into workspace 1 as a viewer — any account the Supabase project
    # accepts could read the default tenant. In a real deployment
    # (REQUIRE_AUTH) that token is refused unless it is the bootstrap owner.
    if raw_workspace is None:
        if REQUIRE_AUTH and not is_bootstrap_owner:
            raise HTTPException(
                status_code=401,
                detail="No workspace assigned to this account (app_metadata.workspace_id)",
            )
        raw_workspace = 1
    try:
        workspace_id = int(raw_workspace)
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=401, detail="Invalid workspace claim") from exc

    # SQLite has no tenant scoping at all: in a real deployment (REQUIRE_AUTH)
    # without DATABASE_URL the backend is single-workspace by construction, so
    # a token for any other workspace must not be served workspace 1's data.
    # The hybrid dev mode (secret set, REQUIRE_AUTH off) keeps parsing claims
    # as-is so multi-workspace tokens can be exercised without Postgres.
    if REQUIRE_AUTH and not (os.getenv("DATABASE_URL") or "").strip() and workspace_id != 1:
        raise HTTPException(
            status_code=403,
            detail="This deployment serves a single workspace (SQLite backend)",
        )

    # Founder bootstrap: a configured owner email is always `owner`, so the
    # operator can never be locked out of admin features by a missing
    # app_metadata role. `owner` is the highest role, so this only ever elevates.
    if is_bootstrap_owner:
        role = "owner"

    return UserContext(user_id=user_id, workspace_id=workspace_id, email=email, role=role)


async def get_current_user(
    authorization: str | None = Header(None),
    x_api_key: str | None = Header(None),
    clara_access_token: str | None = Cookie(None),
) -> UserContext:
    """FastAPI dependency: `_resolve_user` + tenant ContextVar.

    Async on purpose: it runs in the request task, so the ContextVar set here
    propagates into threadpool-run sync endpoints and their store calls (a sync
    dependency's ContextVar writes happen in a throwaway context copy and would
    be lost). Verification itself stays off the event loop — token checks can
    hit the JWKS endpoint and the API-key store.
    """
    # HttpOnly-cookie sessions (docs/engineering/auth-hardening-design.md): the
    # browser can't attach a Bearer header for a token it can't read, so accept
    # the access token from the cookie when no Authorization header is present.
    # Additive — bearer tokens and API keys keep working unchanged.
    if authorization is None and clara_access_token:
        authorization = f"Bearer {clara_access_token}"
    user = await run_in_threadpool(_resolve_user, authorization, x_api_key)
    set_current_tenant(user.tenant_setting)
    # Works-council middleware reads this after the route ran (same task).
    set_current_request_user((user.role, user.workspace_id))
    return user
