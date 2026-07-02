"""Rate limiting — simple in-memory rate limiter for the FastAPI API.

Phase 6: protects the API from abuse. In production, replace with Redis-based
rate limiting for multi-instance deployments.

Limits:
  - free: 60 requests/minute
  - pro: 600 requests/minute
  - enterprise: 6000 requests/minute
"""

from __future__ import annotations

import time
from collections import defaultdict

from fastapi import Depends, HTTPException

import app.auth as auth
from app.auth import UserContext, get_current_user
from app.billing import Plan

RATE_LIMITS: dict[str, int] = {
    Plan.FREE.value: 60,
    Plan.PRO.value: 600,
    Plan.ENTERPRISE.value: 6000,
}

# In-memory store: { (workspace_id, minute): count }
_request_counts: dict[tuple[int, int], int] = defaultdict(int)


def rate_limiter(user: UserContext = Depends(get_current_user)) -> None:  # noqa: B008
    """FastAPI dependency: enforce rate limits per workspace per minute.

    Usage:
        @app.get("/signals")
        def list_signals(
            user: UserContext = Depends(get_current_user),
            _: None = Depends(rate_limiter),
        ):
            ...
    """
    # Rate limiting is off when auth is disabled (local dev / tests are single-user
    # and would otherwise trip the per-minute cap during fast test runs). Referenced
    # live (not import-bound) so it tracks auth (re)configuration.
    if not auth.AUTH_ENABLED:
        return

    current_minute = int(time.time() // 60)
    key = (user.workspace_id, current_minute)

    _request_counts[key] += 1

    # Get limit (default to free plan)
    limit = RATE_LIMITS.get(Plan.FREE.value, 60)

    if _request_counts[key] > limit:
        raise HTTPException(
            status_code=429,
            detail=(
                f"Rate limit exceeded: {limit} requests/minute. "
                "Upgrade your plan for higher limits."
            ),
            headers={"Retry-After": "60"},
        )

    # Cleanup old entries (every 100 requests, clean entries > 2 minutes old)
    if len(_request_counts) > 1000:
        cutoff = current_minute - 2
        for k in list(_request_counts.keys()):
            if k[1] < cutoff:
                del _request_counts[k]
