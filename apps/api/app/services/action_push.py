"""Real action push; fires the destination connector when an action is approved.

Until now the normal approval flow only created local drafts; the real Jira/Slack
push code was reachable only via the connector test endpoint and the LangGraph
action node. This module bridges the gap: after an approval creates its
ExecutionRecord, `push_approved_action` looks up the destination connector config
and performs the real external write, recording the result on the execution.

Design rules:
  - Push failures NEVER fail the approval — the approval already succeeded; the
    failure is recorded on the execution (status=push_failed, detail=error).
  - No config for the destination -> the execution stays a draft (existing
    behaviour), with a detail note so the UI can say why.
  - Idempotent: if an execution for the same problem+action already carries an
    external_ref, we skip instead of creating a duplicate external record.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Protocol

from app.connectors import DESTINATIONS
from app.connectors.base import ConnectorError
from app.domain.models import (
    ActionProposal,
    ExecutionRecord,
    ExecutionStatus,
    OwnerRoute,
    ProblemRecord,
)
from app.services.routing import connector_overrides, route_for_owner

logger = logging.getLogger(__name__)


class _ConfigStore(Protocol):
    def get_config(self, connector_type: str) -> Any: ...


class _WorkflowStore(Protocol):
    def list_executions(self) -> list[ExecutionRecord]: ...

    def update_execution(
        self,
        execution_id: str,
        *,
        status: ExecutionStatus,
        external_ref: str | None = None,
        detail: str | None = None,
        disclosure_applied: bool | None = None,
    ) -> ExecutionRecord: ...


def apply_disclosure(description: str, template: str) -> str:
    """Append the Art. 50 AI-disclosure line to outbound text (final line)."""
    if not template:
        return description
    return f"{description}\n\n{template}" if description else template


def _build_push_payload(
    problem: ProblemRecord, action: ActionProposal, *, disclosure: str | None = None
) -> dict[str, Any]:
    """Map a problem + approved action onto the dict shape connectors expect.

    This is the single choke point for outbound text: a disclosure passed here
    reaches every destination (Jira description, Slack message) unchanged.
    """
    risk_priority = {"critical": 1, "high": 1, "medium": 2, "low": 3}
    description = action.proposal
    if disclosure:
        description = apply_disclosure(description, disclosure)
    # Deep link back to the problem so the team working in Jira/Slack can reach
    # the evidence, the approval trail and the outcome contract in one click.
    web_url = (os.getenv("CLARA_WEB_URL") or "").rstrip("/")
    clara_url = f"{web_url}/insights/{problem.problem_id}" if web_url else ""
    return {
        "title": f"{problem.title} [{action.class_.value}]",
        "description": description,
        "priority": risk_priority.get(action.risk_level.value, 3),
        "problem_id": problem.problem_id,
        "clara_url": clara_url,
        "insight_title": problem.title,
        "insight_summary": problem.statement,
        "insight_severity": problem.impact_band,
        "insight_signal_ids": [
            evidence.signal_id for evidence in problem.evidence[:10] if evidence.signal_id
        ],
    }


def push_approved_action(
    *,
    problem: ProblemRecord,
    action: ActionProposal,
    execution: ExecutionRecord,
    config_store: _ConfigStore,
    workflow_store: _WorkflowStore,
    disclosure_template: str | None = None,
    owner_routes: list[OwnerRoute] | None = None,
) -> ExecutionRecord:
    """Push an approved action to its destination system, if one is configured.

    Returns the (possibly updated) execution record. Never raises for connector
    failures — the outcome is recorded on the execution instead.

    Art. 50: executions without a human-review stamp get `disclosure_template`
    appended to the outbound text and `disclosure_applied=True` recorded;
    human-reviewed executions are Art. 50(4)-exempt and pushed verbatim.

    Team routing: when the workspace declares an ``OwnerRoute`` for the action's
    owner with its own Jira project / Slack channel, that override is layered
    over the workspace connector config (credentials are never overridable), so
    each team receives its work in the tool and place it already uses.
    """
    destination = execution.destination
    connector = DESTINATIONS.get(destination)
    if connector is None:
        # No real connector for this destination (zendesk/hubspot/... are Phase 7+);
        # the draft is the intended behaviour.
        return execution

    config_record = config_store.get_config(destination)
    config = getattr(config_record, "config", None) if config_record else None
    is_active = getattr(config_record, "is_active", True) if config_record else False
    if not config or not is_active:
        return workflow_store.update_execution(
            execution.execution_id,
            status=execution.status,
            detail=f"No active {destination} connector configured. draft only.",
        )

    # Idempotency: an earlier approval for this action already created the
    # external record; do not create a duplicate.
    for existing in workflow_store.list_executions():
        if (
            existing.execution_id != execution.execution_id
            and existing.problem_id == execution.problem_id
            and existing.action_id == execution.action_id
            and existing.external_ref
        ):
            return workflow_store.update_execution(
                execution.execution_id,
                status=ExecutionStatus.pushed,
                external_ref=existing.external_ref,
                detail=f"Reused existing {destination} record (idempotent skip).",
            )

    route = route_for_owner(owner_routes or [], action.owner)
    overrides = connector_overrides(route, destination)
    if overrides:
        config = {**config, **overrides}
    route_note = f" via team route '{route.owner}'" if overrides and route is not None else ""

    disclosure = None if execution.human_reviewed else disclosure_template
    try:
        result = connector.push(
            _build_push_payload(problem, action, disclosure=disclosure), config
        )
    except ConnectorError as exc:
        logger.warning(
            "Action push failed: problem=%s action=%s destination=%s error=%s",
            problem.problem_id,
            action.action_id,
            destination,
            exc,
        )
        return workflow_store.update_execution(
            execution.execution_id,
            status=ExecutionStatus.push_failed,
            detail=str(exc)[:300],
        )
    except Exception as exc:  # noqa: BLE001 — a malformed response or a config
        # error must land on the execution as push_failed (retryable), never
        # leave it looking like an untouched draft.
        logger.exception(
            "Action push crashed: problem=%s action=%s destination=%s",
            problem.problem_id,
            action.action_id,
            destination,
        )
        return workflow_store.update_execution(
            execution.execution_id,
            status=ExecutionStatus.push_failed,
            detail=f"{type(exc).__name__}: {str(exc)[:250]}",
        )

    external_id = result.get("external_id") or ""
    return workflow_store.update_execution(
        execution.execution_id,
        status=ExecutionStatus.pushed,
        external_ref=external_id,
        detail=f"{destination} record created: {external_id}{route_note}",
        disclosure_applied=True if disclosure else None,
    )
