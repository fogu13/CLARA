"""Small shared helpers used across services (consolidated from byte-identical copies)."""

from __future__ import annotations

from datetime import UTC, datetime

from app.domain.models import ActionProposal, ActionProposalSnapshot


def utc_now() -> str:
    """Current UTC time as an ISO-8601 string with a 'Z' suffix."""
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def action_snapshot(action: ActionProposal) -> ActionProposalSnapshot:
    """Immutable by-alias snapshot of an action proposal (for audit records)."""
    return ActionProposalSnapshot.model_validate(action.model_dump(by_alias=True))
