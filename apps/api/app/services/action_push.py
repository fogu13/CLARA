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
  - Idempotent: if an execution created by the SAME approval run for this
    action already carries an external_ref, we reuse it instead of creating a
    duplicate external record. A record created under a superseded run is
    never reused: it carries text nobody approved for the current revision.
"""

from __future__ import annotations

import logging
import os
import threading
from typing import Any, Protocol

from app.connectors import DESTINATIONS
from app.connectors.base import ConnectorError
from app.domain.models import (
    ActionProposal,
    ApprovalRecord,
    ExecutionRecord,
    ExecutionStatus,
    OwnerRoute,
    ProblemRecord,
)
from app.services.common import utc_now
from app.services.routing import connector_overrides, route_for_owner
from app.services.workflow import (
    DispatchAuthorization,
    approved_action_keys,
    authorize_dispatch,
    is_human_reviewed,
)

logger = logging.getLogger(__name__)


class DispatchNotAuthorized(Exception):
    """The execution's approval trail does not authorise dispatching the
    current action revision. `reason` is one of the authorize_dispatch codes."""

    def __init__(self, reason: str, detail: str) -> None:
        super().__init__(detail)
        self.reason = reason
        self.detail = detail


# One lock per execution so a concurrent first push and retry (or two retries)
# cannot both pass the status check and create two external records.
_EXECUTION_LOCKS: dict[str, threading.Lock] = {}
_EXECUTION_LOCKS_GUARD = threading.Lock()

# Only executions in these states may be dispatched; anything else is
# finished (pushed) or was never meant to leave CLARA (blocked/not_started).
_DISPATCHABLE = {ExecutionStatus.draft_created, ExecutionStatus.push_failed}


def _execution_lock(execution_id: str) -> threading.Lock:
    with _EXECUTION_LOCKS_GUARD:
        return _EXECUTION_LOCKS.setdefault(execution_id, threading.Lock())


class _ConfigStore(Protocol):
    def get_config(self, connector_type: str) -> Any: ...


class _WorkflowStore(Protocol):
    def list_executions(self) -> list[ExecutionRecord]: ...

    def list_approvals(self) -> list[ApprovalRecord]: ...

    def update_execution(
        self,
        execution_id: str,
        *,
        status: ExecutionStatus,
        external_ref: str | None = None,
        detail: str | None = None,
        disclosure_applied: bool | None = None,
        dispatched_at: str | None = None,
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
    four_eyes: bool = False,
) -> ExecutionRecord:
    """Push an approved action to its destination system, if one is configured.

    Returns the (possibly updated) execution record. Never raises for connector
    failures — the outcome is recorded on the execution instead. Raises
    ``DispatchNotAuthorized`` when the approval trail does not cover this
    dispatch (see below); the refusal is also recorded on the execution's
    ``detail`` while its status and external_ref stay untouched.

    Authorisation: an execution that is effectively human-reviewed (the
    Art. 50(4) stamp, or — for rows written before the stamp existed — an
    approval on record for its action, see ``workflow.is_human_reviewed``)
    exists because named reviewers approved ONE revision of the action.
    Before any outbound write (first push or retry) the current action, the
    execution and the workspace's four-eyes setting are checked against the
    append-only approvals by ``workflow.authorize_dispatch``: the latest
    decision must be an approval, the approval run must have created THIS
    execution, and the action must still match the approved snapshot. The
    check is re-run on a fresh read of the approvals immediately before the
    connector call (after the connector config and team route are resolved),
    so a rejection recorded in between still refuses the write; the network
    call itself remains unguarded — a rejection that lands while the
    connector is writing cannot recall the record. Executions with no
    approval at all (auto-published graph pushes) have nothing to bind to and
    keep the Art. 50 disclosure path below.

    Not part of the approval: the workspace connector config and the team
    routing (``OwnerRoute`` overrides) are admin configuration, resolved at
    dispatch time. The resolved override is named in the execution's detail
    so the audit trail says where the record really went.

    Concurrency: the whole check-and-push runs under a per-execution
    in-process lock and re-reads the execution first, so two retries in one
    process cannot both create an external record. Known limitation: the lock
    is process-local. In a multi-worker Postgres deployment two workers can
    still race on the same execution; closing that needs a DB row lock
    (SELECT ... FOR UPDATE on the execution) rather than this lock.

    Art. 50: executions without a human-review stamp get `disclosure_template`
    appended to the outbound text and `disclosure_applied=True` recorded;
    human-reviewed executions are Art. 50(4)-exempt and pushed verbatim.

    Team routing: when the workspace declares an ``OwnerRoute`` for the action's
    owner with its own Jira project / Slack channel, that override is layered
    over the workspace connector config (credentials are never overridable), so
    each team receives its work in the tool and place it already uses.
    """
    with _execution_lock(execution.execution_id):
        current = next(
            (
                item
                for item in workflow_store.list_executions()
                if item.execution_id == execution.execution_id
            ),
            execution,
        )
        if current.status not in _DISPATCHABLE:
            # A concurrent dispatch already finished (or the record was never
            # dispatchable): return what stands, never push a second time.
            return current

        approvals = workflow_store.list_approvals()
        gated = is_human_reviewed(current, approved_action_keys(approvals))
        authorization: DispatchAuthorization | None = None
        if gated:
            authorization = _check_authorization(
                problem=problem,
                action=action,
                execution=current,
                approvals=approvals,
                four_eyes=four_eyes,
                workflow_store=workflow_store,
            )

        return _dispatch(
            problem=problem,
            action=action,
            execution=current,
            config_store=config_store,
            workflow_store=workflow_store,
            disclosure_template=disclosure_template,
            owner_routes=owner_routes,
            authorization=authorization,
            four_eyes=four_eyes,
        )


def _check_authorization(
    *,
    problem: ProblemRecord,
    action: ActionProposal,
    execution: ExecutionRecord,
    approvals: list[ApprovalRecord],
    four_eyes: bool,
    workflow_store: _WorkflowStore,
) -> DispatchAuthorization:
    """Run ``authorize_dispatch``; on refusal record it on the execution's
    detail (status and external_ref untouched) and raise."""
    authorization = authorize_dispatch(
        problem=problem,
        action=action,
        execution=execution,
        approvals=approvals,
        four_eyes=four_eyes,
    )
    if not authorization.authorized:
        logger.warning(
            "Action dispatch refused: problem=%s action=%s execution=%s reason=%s",
            problem.problem_id,
            action.action_id,
            execution.execution_id,
            authorization.reason,
        )
        # update_execution resets external_ref/detail when omitted:
        # pass both explicitly so only the detail changes.
        workflow_store.update_execution(
            execution.execution_id,
            status=execution.status,
            external_ref=execution.external_ref,
            detail=f"Dispatch refused ({authorization.reason}): {authorization.detail}"[:300],
        )
        raise DispatchNotAuthorized(authorization.reason or "refused", authorization.detail)
    return authorization


def _route_note(route: OwnerRoute | None, overrides: dict[str, str]) -> str:
    """Audit note naming the team route and the resolved override, e.g.
    " via team route 'payments' -> project ELSEWHERE"."""
    if route is None or not overrides:
        return ""
    labels = {"project_key": "project", "channel": "channel"}
    resolved = ", ".join(f"{labels.get(key, key)} {value}" for key, value in overrides.items())
    return f" via team route '{route.owner}' → {resolved}"


def _dispatch(
    *,
    problem: ProblemRecord,
    action: ActionProposal,
    execution: ExecutionRecord,
    config_store: _ConfigStore,
    workflow_store: _WorkflowStore,
    disclosure_template: str | None,
    owner_routes: list[OwnerRoute] | None,
    authorization: DispatchAuthorization | None,
    four_eyes: bool,
) -> ExecutionRecord:
    """The outbound write itself; callers hold the execution lock and have
    already authorised the dispatch (``authorization`` is None only for
    executions with no approval to bind to)."""
    authorized_by = authorization.decision_ids if authorization is not None else []
    authorization_note = f" · authorized by {', '.join(authorized_by)}" if authorized_by else ""
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

    # Idempotency: an execution created by the SAME approval run for this
    # action already created the external record; do not create a duplicate.
    # Records of earlier (superseded) runs carry a different revision and
    # are never reused — a re-approved revision gets its own record.
    reusable = set(authorization.execution_ids) if authorization is not None else set()
    for existing in workflow_store.list_executions():
        if (
            existing.execution_id != execution.execution_id
            and existing.execution_id in reusable
            and existing.problem_id == execution.problem_id
            and existing.action_id == execution.action_id
            and existing.external_ref
        ):
            return workflow_store.update_execution(
                execution.execution_id,
                status=ExecutionStatus.pushed,
                external_ref=existing.external_ref,
                detail=f"Reused existing {destination} record (idempotent skip).",
                # The clock ran from the reused record's dispatch, not from now.
                dispatched_at=existing.dispatched_at,
            )

    route = route_for_owner(owner_routes or [], action.owner)
    overrides = connector_overrides(route, destination)
    if overrides:
        config = {**config, **overrides}
    route_note = _route_note(route, overrides)

    if authorization is not None:
        # Close the check-then-act window as far as the store allows: a
        # decision recorded while config and route were being resolved must
        # refuse the write. The connector call below stays unguarded.
        authorization = _check_authorization(
            problem=problem,
            action=action,
            execution=execution,
            approvals=workflow_store.list_approvals(),
            four_eyes=four_eyes,
            workflow_store=workflow_store,
        )

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
        detail=f"{destination} record created: {external_id}{route_note}{authorization_note}",
        disclosure_applied=True if disclosure else None,
        # The measurement clock origin: the instant the record really left CLARA.
        dispatched_at=utc_now(),
    )
