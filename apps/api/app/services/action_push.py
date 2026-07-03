"""Real action push — fires the destination connector when an action is approved.

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
from typing import Any, Protocol

from app.connectors import DESTINATIONS
from app.connectors.base import ConnectorError
from app.domain.models import ActionProposal, ExecutionRecord, ExecutionStatus, ProblemRecord

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
    ) -> ExecutionRecord: ...


def _build_push_payload(problem: ProblemRecord, action: ActionProposal) -> dict[str, Any]:
    """Map a problem + approved action onto the dict shape connectors expect."""
    risk_priority = {"critical": 1, "high": 1, "medium": 2, "low": 3}
    return {
        "title": f"{problem.title} [{action.class_.value}]",
        "description": action.proposal,
        "priority": risk_priority.get(action.risk_level.value, 3),
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
) -> ExecutionRecord:
    """Push an approved action to its destination system, if one is configured.

    Returns the (possibly updated) execution record. Never raises for connector
    failures — the outcome is recorded on the execution instead.
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
            detail=f"No active {destination} connector configured — draft only.",
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

    try:
        result = connector.push(_build_push_payload(problem, action), config)
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

    external_id = result.get("external_id") or ""
    return workflow_store.update_execution(
        execution.execution_id,
        status=ExecutionStatus.pushed,
        external_ref=external_id,
        detail=f"{destination} record created: {external_id}",
    )
