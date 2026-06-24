"""Stripe billing stub — SaaS subscription management.

Phase 6 stub: defines the billing model and plan limits without actually
calling the Stripe API. When ready to go live, replace the stub methods
with real Stripe SDK calls.

Plans:
  - free: 100 signals/month, 1 connector, no API keys
  - pro: 10,000 signals/month, 5 connectors, 10 API keys, Langfuse
  - enterprise: unlimited, unlimited connectors, SSO, custom retention
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel


class Plan(str, Enum):  # noqa: UP042
    FREE = "free"
    PRO = "pro"
    ENTERPRISE = "enterprise"


PLAN_LIMITS: dict[str, dict[str, Any]] = {
    Plan.FREE.value: {
        "max_signals_per_month": 100,
        "max_connectors": 1,
        "max_api_keys": 0,
        "langfuse_enabled": False,
        "custom_retention": False,
        "sso_enabled": False,
    },
    Plan.PRO.value: {
        "max_signals_per_month": 10_000,
        "max_connectors": 5,
        "max_api_keys": 10,
        "langfuse_enabled": True,
        "custom_retention": False,
        "sso_enabled": False,
    },
    Plan.ENTERPRISE.value: {
        "max_signals_per_month": -1,  # unlimited
        "max_connectors": -1,
        "max_api_keys": -1,
        "langfuse_enabled": True,
        "custom_retention": True,
        "sso_enabled": True,
    },
}


class Subscription(BaseModel):
    """A workspace subscription."""

    workspace_id: int
    plan: Plan = Plan.FREE
    stripe_customer_id: str | None = None
    stripe_subscription_id: str | None = None
    current_period_end: str | None = None
    is_active: bool = True

    @property
    def limits(self) -> dict[str, Any]:
        return PLAN_LIMITS[self.plan.value]


class BillingStore:
    """In-memory subscription store. Replace with Stripe API calls in production."""

    def __init__(self) -> None:
        self._subs: dict[int, Subscription] = {}

    def get_subscription(self, workspace_id: int) -> Subscription:
        return self._subs.get(workspace_id, Subscription(workspace_id=workspace_id))

    def set_plan(self, workspace_id: int, plan: Plan) -> Subscription:
        sub = self.get_subscription(workspace_id)
        sub.plan = plan
        self._subs[workspace_id] = sub
        return sub

    def check_limit(self, workspace_id: int, limit_key: str, current_count: int) -> bool:
        """Check if a workspace is within its plan limit."""
        sub = self.get_subscription(workspace_id)
        limit = sub.limits.get(limit_key, 0)
        if limit == -1:
            return True  # unlimited
        return current_count < limit


# --- Stripe API stubs (replace with real calls in production) ---


def create_checkout_session(
    workspace_id: int,
    plan: Plan,
    success_url: str,
    cancel_url: str,
) -> dict[str, str]:
    """Create a Stripe Checkout Session.

    TODO: replace with real Stripe SDK call:
        import stripe
        session = stripe.checkout.Session.create(...)
    """
    return {
        "url": f"https://checkout.stripe.com/stub/session?plan={plan.value}&workspace={workspace_id}",
        "session_id": f"cs_stub_{workspace_id}_{plan.value}",
    }


def handle_webhook(payload: dict[str, Any]) -> dict[str, str]:
    """Handle a Stripe webhook.

    TODO: replace with real Stripe webhook signature verification + event handling.
    """
    event_type = payload.get("type", "unknown")
    return {"status": "received", "event_type": event_type}
