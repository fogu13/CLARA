"""Tests for RBAC, billing, and rate limiting."""

from __future__ import annotations

import time

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from app.auth import UserContext
from app.billing import (
    PLAN_LIMITS,
    BillingStore,
    Plan,
    create_checkout_session,
    handle_webhook,
)
from app.rbac import can_admin, can_edit, is_owner

# --- RBAC tests ---


class TestRBAC:
    def test_owner_can_do_everything(self) -> None:
        user = UserContext(user_id="u1", workspace_id=1, role="owner")
        assert is_owner(user) is True
        assert can_admin(user) is True
        assert can_edit(user) is True

    def test_viewer_cannot_edit(self) -> None:
        user = UserContext(user_id="u2", workspace_id=1, role="viewer")
        assert can_edit(user) is False
        assert can_admin(user) is False
        assert is_owner(user) is False

    def test_editor_can_edit_but_not_admin(self) -> None:
        user = UserContext(user_id="u3", workspace_id=1, role="editor")
        assert can_edit(user) is True
        assert can_admin(user) is False

    def test_admin_can_admin_but_not_owner(self) -> None:
        user = UserContext(user_id="u4", workspace_id=1, role="admin")
        assert can_admin(user) is True
        assert is_owner(user) is False


class TestRequireRole:
    def test_viewer_blocked_from_admin_endpoint(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("SUPABASE_JWT_SECRET", "test-secret-32-chars-minimum-length!")
        import importlib

        import app.auth as auth_mod
        import app.rbac as rbac_mod
        importlib.reload(auth_mod)
        importlib.reload(rbac_mod)

        import jwt

        token = jwt.encode(
            {"sub": "user-view", "workspace_id": 1, "user_role": "viewer",
             "exp": int(time.time()) + 3600},
            "test-secret-32-chars-minimum-length!",
            algorithm="HS256",
        )

        app = FastAPI()

        @app.delete("/signals/{id}")
        def delete_signal(
            _: None = Depends(rbac_mod.require_role(rbac_mod.Role.editor)),
        ):
            return {"deleted": True}

        client = TestClient(app)
        resp = client.delete("/signals/1", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 403

    def test_editor_allowed_on_editor_endpoint(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("SUPABASE_JWT_SECRET", "test-secret-32-chars-minimum-length!")
        import importlib

        import app.auth as auth_mod
        import app.rbac as rbac_mod
        importlib.reload(auth_mod)
        importlib.reload(rbac_mod)

        import jwt

        token = jwt.encode(
            {"sub": "user-edit", "workspace_id": 1, "user_role": "editor",
             "exp": int(time.time()) + 3600},
            "test-secret-32-chars-minimum-length!",
            algorithm="HS256",
        )

        app = FastAPI()

        @app.post("/signals")
        def create_signal(
            _: None = Depends(rbac_mod.require_role(rbac_mod.Role.editor)),
        ):
            return {"created": True}

        client = TestClient(app)
        resp = client.post("/signals", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200


# --- Billing tests ---


class TestBilling:
    def test_free_plan_limits(self) -> None:
        limits = PLAN_LIMITS[Plan.FREE.value]
        assert limits["max_signals_per_month"] == 100
        assert limits["max_connectors"] == 1
        assert limits["langfuse_enabled"] is False

    def test_pro_plan_limits(self) -> None:
        limits = PLAN_LIMITS[Plan.PRO.value]
        assert limits["max_signals_per_month"] == 10_000
        assert limits["langfuse_enabled"] is True

    def test_enterprise_unlimited(self) -> None:
        limits = PLAN_LIMITS[Plan.ENTERPRISE.value]
        assert limits["max_signals_per_month"] == -1
        assert limits["max_connectors"] == -1

    def test_billing_store_get_default(self) -> None:
        store = BillingStore()
        sub = store.get_subscription(42)
        assert sub.plan == Plan.FREE
        assert sub.workspace_id == 42

    def test_billing_store_set_plan(self) -> None:
        store = BillingStore()
        sub = store.set_plan(42, Plan.PRO)
        assert sub.plan == Plan.PRO
        assert store.get_subscription(42).plan == Plan.PRO

    def test_check_limit_within_bounds(self) -> None:
        store = BillingStore()
        assert store.check_limit(1, "max_connectors", 0) is True

    def test_check_limit_exceeded(self) -> None:
        store = BillingStore()
        # Free plan: max 1 connector
        assert store.check_limit(1, "max_connectors", 1) is False

    def test_check_limit_unlimited(self) -> None:
        store = BillingStore()
        store.set_plan(1, Plan.ENTERPRISE)
        assert store.check_limit(1, "max_connectors", 999) is True

    def test_create_checkout_session_stub(self) -> None:
        result = create_checkout_session(1, Plan.PRO, "https://success", "https://cancel")
        assert "url" in result
        assert "session_id" in result
        assert "pro" in result["session_id"]

    def test_handle_webhook_stub(self) -> None:
        result = handle_webhook({"type": "checkout.session.completed"})
        assert result["status"] == "received"
        assert result["event_type"] == "checkout.session.completed"


# --- Rate limiter tests ---


class TestRateLimiter:
    def test_allows_under_limit(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("SUPABASE_JWT_SECRET", raising=False)
        import importlib

        import app.auth as auth_mod
        import app.rate_limit as rl_mod
        importlib.reload(auth_mod)
        importlib.reload(rl_mod)

        app = FastAPI()

        @app.get("/test")
        def test_endpoint(
            _: None = Depends(rl_mod.rate_limiter),
        ):
            return {"ok": True}

        client = TestClient(app)
        resp = client.get("/test")
        assert resp.status_code == 200
