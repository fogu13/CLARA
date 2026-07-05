"""JWT-bound workflow identity (review #30/#31) + tenant ContextVar plumbing.

These tests flip auth ON by patching app.auth module globals (the route
dependencies read them at call time), so they build their own app instances —
the rest of the suite runs auth-disabled and must stay that way.
"""

from __future__ import annotations

import time

import jwt
import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.domain.models import ClosureRecordRequest, LearningConclusionRecord
from app.main import create_app
from app.routers.problems import _actor_identifier
from app.services.problems import ProblemStore
from app.services.seed import load_seed_problems
from app.services.workflow import WorkflowStore

SECRET = "tenant-identity-test-secret"
UUID_SUB = "12345678-1234-5678-1234-567812345678"  # digit-heavy on purpose

CLOSURE_BODY = {
    "operational_status": "released",
    "customer_status": "draft_ready",
    "owner": "cx_operations",
    "verified_resolution_facts": ["Resolution released."],
    "unresolved_customers": 1,
    "follow_up_channel": "zendesk",
    "limitations": [],
}


def _token(workspace_id: int, sub: str = UUID_SUB, role: str = "editor") -> str:
    return jwt.encode(
        {
            "sub": sub,
            "email": "identity-test@example.com",
            "exp": int(time.time()) + 3600,
            "app_metadata": {"workspace_id": workspace_id, "user_role": role},
        },
        SECRET,
        algorithm="HS256",
    )


def _bearer(workspace_id: int, **kwargs) -> dict[str, str]:
    return {"Authorization": f"Bearer {_token(workspace_id, **kwargs)}"}


@pytest.fixture
def auth_client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setattr("app.auth.AUTH_ENABLED", True)
    monkeypatch.setattr("app.auth.SUPABASE_JWT_SECRET", SECRET)
    return TestClient(
        create_app(
            problem_store=ProblemStore(load_seed_problems()),
            workflows=WorkflowStore(),
        )
    )


def test_spoofed_tenant_and_actor_headers_are_ignored(auth_client: TestClient) -> None:
    """The #30/#31 regression: x-tenant-id / x-actor-id are dead — identity
    comes from the verified JWT, whatever the client claims in headers."""
    response = auth_client.post(
        "/problems/PRB-108/closure",
        headers={**_bearer(2), "x-tenant-id": "999", "x-actor-id": "mallory"},
        json=CLOSURE_BODY,
    )

    assert response.status_code == 200
    closure = response.json()
    assert closure["tenant_id"] == "2"
    assert closure["actor"] == f"user-{UUID_SUB[:8]}"


def test_cross_tenant_workflow_isolation_via_jwt(auth_client: TestClient) -> None:
    posted = auth_client.post(
        "/problems/PRB-108/closure", headers=_bearer(2), json=CLOSURE_BODY
    )
    assert posted.status_code == 200

    own = auth_client.get("/problems/PRB-108/workflow", headers=_bearer(2)).json()
    other = auth_client.get("/problems/PRB-108/workflow", headers=_bearer(3)).json()
    default_ws = auth_client.get("/problems/PRB-108/workflow", headers=_bearer(1)).json()

    assert len(own["closure_records"]) == 1
    assert other["closure_records"] == []
    assert default_ws["closure_records"] == []


def test_request_without_token_is_rejected_when_auth_enabled(auth_client: TestClient) -> None:
    response = auth_client.post("/problems/PRB-108/closure", json=CLOSURE_BODY)
    assert response.status_code == 401


def test_contextvar_reaches_sync_endpoint(monkeypatch: pytest.MonkeyPatch) -> None:
    """The store layer reads the tenant ContextVar from threadpool-run sync
    endpoints; get_current_user must be async for the set to propagate there
    (a sync dependency's set dies with its throwaway context copy)."""
    from app.auth import current_tenant, get_current_user

    monkeypatch.setattr("app.auth.AUTH_ENABLED", True)
    monkeypatch.setattr("app.auth.SUPABASE_JWT_SECRET", SECRET)

    probe = FastAPI()

    @probe.get("/tenant")
    def read_tenant(user=Depends(get_current_user)):  # noqa: B008 — sync on purpose
        return {"ctx": current_tenant(), "user_ws": user.workspace_id}

    client = TestClient(probe)
    response = client.get("/tenant", headers=_bearer(7))
    assert response.json() == {"ctx": "7", "user_ws": 7}


def test_contextvar_defaults_to_workspace_one_when_auth_disabled() -> None:
    from app.auth import current_tenant, get_current_user

    probe = FastAPI()

    @probe.get("/tenant")
    def read_tenant(user=Depends(get_current_user)):  # noqa: B008
        return {"ctx": current_tenant(), "user_id": user.user_id}

    client = TestClient(probe)
    response = client.get("/tenant")
    assert response.json() == {"ctx": "1", "user_id": "dev-user"}


def test_uuid_actor_survives_pseudonymization() -> None:
    """Raw UUIDs can trip the phone-pattern redaction (digit/hyphen runs >= 9
    chars); the derived user-<8 hex> actor never can."""
    from app.auth import UserContext

    actor = _actor_identifier(UserContext(user_id=UUID_SUB, workspace_id=2))
    assert actor == "user-12345678"

    problem = load_seed_problems()[0]
    record = WorkflowStore().record_closure(
        problem=problem,
        closure=ClosureRecordRequest(**CLOSURE_BODY),
        tenant_id="2",
        actor=actor,
    )
    assert record.actor == actor

    # Short principals pass through unchanged.
    assert _actor_identifier(UserContext(user_id="dev-user", workspace_id=1)) == "dev-user"
    assert _actor_identifier(UserContext(user_id="api-key:3", workspace_id=1)) == "api-key:3"


def test_email_reviewer_still_rejected_at_model_layer() -> None:
    """The old API-level test sent an email via x-actor-id; the header is gone,
    but the model validator remains the PII backstop."""
    with pytest.raises(ValidationError):
        LearningConclusionRecord(
            conclusion_id="LRN-test",
            problem_id="PRB-108",
            tenant_id="1",
            reviewer="owner@example.com",
            reviewed_at="2026-07-20T12:00:00Z",
            retention_expires_at="2028-07-20T12:00:00Z",
            learning_status="worked",
            summary="Worked.",
            limitations="None noted.",
        )
