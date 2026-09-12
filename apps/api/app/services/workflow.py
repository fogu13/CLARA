from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from dataclasses import field as dataclass_field
from datetime import datetime
from itertools import count
from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException

from app.domain.models import (
    ActionProposal,
    ActionProposalChange,
    ActionProposalSnapshot,
    ApprovalDecision,
    ApprovalDecisionStatus,
    ApprovalRecord,
    ClosureRecord,
    ClosureRecordRequest,
    ExecutionRecord,
    ExecutionStatus,
    JiraIssueDraft,
    LearningConclusionRecord,
    GuardrailMeasurement,
    LearningConclusionRequest,
    OutcomeContract,
    OutcomeMeasurement,
    OutcomeSnapshot,
    ProblemRecord,
    ProblemStatus,
    ProblemTransitionRecord,
    TimelineEvent,
    WorkflowState,
    retention_expires_at,
)
from app.services.common import SerializedConnection, action_snapshot, utc_now  # re-exported for importers, SerializedConnection
from app.services import outcome_engine


UNRESOLVED_GOVERNANCE_STATUSES = {"fail", "review_required"}
GOVERNED_ACTION_CLASSES = {"customer_recovery", "journey_intervention", "governance"}
# ponytail: local policy map; pass PolicyRuleStore into workflow if this grows.
GOVERNANCE_RULES_BY_DESTINATION = {
    "zendesk": {
        "customer_contact_requires_consent_review",
        "customer_contact_requires_valid_consent",
        "sensitive_attribute_inference_prohibited",
    },
    "hubspot": {
        "customer_contact_requires_consent_review",
        "customer_contact_requires_valid_consent",
        "audience_activation_requires_privacy_review",
        "sensitive_attribute_inference_prohibited",
        "high_risk_marketing_change_requires_privacy_review",
    },
    "braze": {
        "customer_contact_requires_consent_review",
        "customer_contact_requires_valid_consent",
        "audience_activation_requires_privacy_review",
        "sensitive_attribute_inference_prohibited",
        "high_risk_marketing_change_requires_privacy_review",
    },
    "salesforce": {
        "customer_contact_requires_consent_review",
        "customer_contact_requires_valid_consent",
        "audience_activation_requires_privacy_review",
        "sensitive_attribute_inference_prohibited",
        "high_risk_marketing_change_requires_privacy_review",
    },
    "adobe_experience_platform": {
        "audience_activation_requires_privacy_review",
        "sensitive_attribute_inference_prohibited",
        "high_risk_marketing_change_requires_privacy_review",
    },
    "policy_review": {
        "customer_contact_requires_valid_consent",
        "audience_activation_requires_privacy_review",
        "sensitive_attribute_inference_prohibited",
        "high_risk_marketing_change_requires_privacy_review",
    },
}


def find_action(problem: ProblemRecord, action_id: str):
    action = next((proposal for proposal in problem.action_proposals if proposal.action_id == action_id), None)
    if action is None:
        raise HTTPException(status_code=404, detail="Action proposal not found")

    return action


def _diff_value(value) -> str:
    if hasattr(value, "value"):
        return value.value
    if hasattr(value, "model_dump"):
        return json.dumps(value.model_dump(mode="json"), sort_keys=True)
    return str(value)


def action_diff(action: ActionProposal) -> list[ActionProposalChange]:
    if action.original_snapshot is None:
        return []

    current = action_snapshot(action)
    changes: list[ActionProposalChange] = []
    for field in [
        "owner",
        "destination",
        "proposal",
        "risk_level",
        "approval_state",
        "intervention_brief",
    ]:
        before_value = _diff_value(getattr(action.original_snapshot, field))
        after_value = _diff_value(getattr(current, field))
        if before_value != after_value:
            changes.append(ActionProposalChange(field=field, before=before_value, after=after_value))

    return changes


def assert_dependencies_satisfied(
    *,
    action,
    approved_action_ids: set[str],
) -> None:
    unresolved = [
        dependency_id
        for dependency_id in getattr(action, "depends_on", [])
        if dependency_id not in approved_action_ids
    ]
    if unresolved:
        raise HTTPException(
            status_code=409,
            detail=(
                "Action cannot be approved until dependencies are approved: "
                + ", ".join(unresolved)
            ),
        )


def assert_governance_allows_decision(
    *,
    problem: ProblemRecord,
    decision: ApprovalDecision,
    action,
    approved_action_ids: set[str] | None = None,
) -> None:
    if decision.decision != ApprovalDecisionStatus.approved:
        return

    destination = action.destination.strip().lower()
    applicable_rule_ids = GOVERNANCE_RULES_BY_DESTINATION.get(destination)
    if applicable_rule_ids is None and action.class_.value in GOVERNED_ACTION_CLASSES:
        applicable_rule_ids = {
            rule_id
            for destination_rule_ids in GOVERNANCE_RULES_BY_DESTINATION.values()
            for rule_id in destination_rule_ids
        }

    if applicable_rule_ids is not None:
        checks_by_rule = {check.policy_rule_id or check.rule: check for check in problem.governance_checks}
        blocking_failures = [
            rule_id
            for rule_id in applicable_rule_ids
            if (check := checks_by_rule.get(rule_id)) is None
            or check.status.value in UNRESOLVED_GOVERNANCE_STATUSES
        ]
    else:
        blocking_failures = [
            check
            for check in problem.governance_checks
            if check.blocking and check.status.value == "fail"
        ]
    if blocking_failures:
        raise HTTPException(
            status_code=409,
            detail="Action cannot be approved while blocking governance checks are failing",
        )

    assert_dependencies_satisfied(
        action=action,
        approved_action_ids=approved_action_ids or set(),
    )


def resolve_approval_state(
    ordered_decisions: list[tuple[str, str, str]],
    *,
    decision: ApprovalDecision,
    four_eyes: bool = False,
) -> set[str]:
    """Latest-decision-per-action approval set + repeat-approval guard.

    Approvals are append-only, so the dependency gate must honor the LATEST
    decision per action (a later rejection revokes an earlier approval), and
    re-approving an already-approved action must not mint a duplicate
    execution/Jira draft.

    Four-eyes (opt-in workspace flag): an action needs TWO distinct approvers
    before it counts as approved — the first approval records the decision but
    holds execution, the second (different reviewer) releases it, and the same
    reviewer confirming their own approval is rejected. A rejection resets the
    approver tally (the revised action needs fresh sign-off).
    """
    required = 2 if four_eyes else 1
    latest: dict[str, str] = {}
    approvers: dict[str, list[str]] = {}
    for action_id, decision_value, reviewer in ordered_decisions:
        latest[action_id] = decision_value
        if decision_value == ApprovalDecisionStatus.approved.value:
            names = approvers.setdefault(action_id, [])
            if reviewer not in names:
                names.append(reviewer)
        else:
            approvers[action_id] = []

    if decision.decision == ApprovalDecisionStatus.approved and (
        latest.get(decision.action_id) == ApprovalDecisionStatus.approved.value
    ):
        existing = approvers.get(decision.action_id, [])
        if len(existing) >= required:
            raise HTTPException(status_code=409, detail="Action is already approved")
        if four_eyes and decision.reviewer in existing:
            raise HTTPException(
                status_code=409,
                detail="Four-eyes approval: a different approver must confirm this action",
            )

    return {
        action_id
        for action_id, decision_value in latest.items()
        if decision_value == ApprovalDecisionStatus.approved.value
        and len(approvers.get(action_id, [])) >= required
    }


def fully_approved_now(
    ordered_decisions: list[tuple[str, str, str]],
    *,
    decision: ApprovalDecision,
    four_eyes: bool,
) -> bool:
    """Does THIS approved decision complete the required approver count?"""
    if decision.decision != ApprovalDecisionStatus.approved:
        return False
    if not four_eyes:
        return True
    approvers: set[str] = set()
    for action_id, decision_value, reviewer in ordered_decisions:
        if action_id != decision.action_id:
            continue
        if decision_value == ApprovalDecisionStatus.approved.value:
            approvers.add(reviewer)
        else:
            approvers.clear()
    approvers.add(decision.reviewer)
    return len(approvers) >= 2


# Fields of the approved action snapshot that decide WHAT is dispatched and
# WHERE. `approval_state` is a UI label and `action_id` is the key; neither
# changes the outbound payload, so neither can invalidate an approval.
DISPATCH_SNAPSHOT_FIELDS = (
    "class",
    "owner",
    "destination",
    "proposal",
    "risk_level",
    "intervention_brief",
    "depends_on",
)


@dataclass(frozen=True)
class DispatchAuthorization:
    """Result of binding a dispatch to the approval run that authorises it.

    ``execution_ids`` names the executions the authorising run created; an
    idempotent reuse of an earlier external record is only allowed for one of
    them (a record created under a superseded run carries text nobody
    approved for this revision).
    """

    authorized: bool
    reason: str | None
    detail: str
    decision_ids: list[str] = dataclass_field(default_factory=list)
    changed_fields: list[str] = dataclass_field(default_factory=list)
    execution_ids: list[str] = dataclass_field(default_factory=list)


def decision_order(approval: ApprovalRecord) -> tuple[str, int, str]:
    """Sort key for the append-only approvals: created_at, then the NUMERIC
    decision suffix (as strings ``DEC-10000`` sorts before ``DEC-9999``)."""
    _prefix, _, suffix = approval.decision_id.rpartition("-")
    number = int(suffix) if suffix.isdigit() else -1
    return (approval.created_at, number, approval.decision_id)


def latest_decisions(
    approvals: list[ApprovalRecord], problem_id: str
) -> dict[str, ApprovalRecord]:
    """Latest decision per action of a problem, in decision order."""
    latest: dict[str, ApprovalRecord] = {}
    for approval in sorted(
        (approval for approval in approvals if approval.problem_id == problem_id),
        key=decision_order,
    ):
        latest[approval.action_id] = approval
    return latest


def _dispatch_fields(snapshot: ActionProposalSnapshot) -> dict:
    payload = snapshot.model_dump(mode="json", by_alias=True)
    return {name: payload.get(name) for name in DISPATCH_SNAPSHOT_FIELDS}


def _refused(
    reason: str, detail: str, *, changed_fields: list[str] | None = None
) -> DispatchAuthorization:
    return DispatchAuthorization(
        authorized=False,
        reason=reason,
        detail=detail,
        decision_ids=[],
        changed_fields=list(changed_fields or []),
    )


def authorize_dispatch(
    *,
    problem: ProblemRecord,
    action: ActionProposal,
    execution: ExecutionRecord,
    approvals: list[ApprovalRecord],
    four_eyes: bool,
) -> DispatchAuthorization:
    """Decide whether `execution` may be dispatched with the CURRENT `action`.

    An approval signs one revision of one action (its `action_snapshot`).
    Dispatch — the first push or a retry — must send exactly that revision,
    under the decision(s) still in force, for the execution those decisions
    created. Pure: no store access, no side effects. Rules are evaluated in
    order over the append-only approvals of this action, ordered by
    created_at then the numeric decision suffix (``decision_order``):

    1. approval_missing              no decision at all
    2. approval_revoked              latest decision is not `approved`
    3. approval_incomplete           the current approval run has fewer distinct
                                     reviewers than required (2 under four-eyes)
    4. execution_superseded          this execution is not the one the current
                                     approval run created (legacy rows without
                                     execution_id fall back to created_at)
    5. approval_unverifiable         an approval in the run has no snapshot
    6. action_changed_since_approval current action differs from the approved
                                     snapshot on a dispatch-relevant field
    7. approval_revision_mismatch    four-eyes reviewers signed different revisions
    8. destination_changed           execution.destination != approved destination
    """
    relevant = sorted(
        (
            approval
            for approval in approvals
            if approval.problem_id == problem.problem_id
            and approval.action_id == action.action_id
        ),
        key=decision_order,
    )
    if not relevant:
        return _refused(
            "approval_missing",
            f"No approval decision exists for action {action.action_id}.",
        )

    latest = relevant[-1]
    if latest.decision != ApprovalDecisionStatus.approved:
        return _refused(
            "approval_revoked",
            f"The latest decision for action {action.action_id} is "
            f"'{latest.decision.value}' ({latest.decision_id} by {latest.reviewer}); "
            "the earlier approval no longer authorises dispatch.",
        )

    # The approval run: every approval after the last non-approved decision.
    run: list[ApprovalRecord] = []
    for approval in relevant:
        if approval.decision == ApprovalDecisionStatus.approved:
            run.append(approval)
        else:
            run = []

    required = 2 if four_eyes else 1
    reviewers: list[str] = []
    for approval in run:
        if approval.reviewer not in reviewers:
            reviewers.append(approval.reviewer)
    if len(reviewers) < required:
        return _refused(
            "approval_incomplete",
            f"Action {action.action_id} has {len(reviewers)} of {required} required "
            "distinct approvers; execution is still held.",
        )

    bound_execution_ids = [approval.execution_id for approval in run if approval.execution_id]
    if bound_execution_ids:
        belongs = execution.execution_id in bound_execution_ids
    else:
        # Legacy approvals (recorded before execution_id was persisted): the
        # completing approval and its execution share one created_at stamp.
        belongs = any(approval.created_at == execution.created_at for approval in run)
    if not belongs:
        return _refused(
            "execution_superseded",
            f"Execution {execution.execution_id} was not created by the current approval "
            f"run for action {action.action_id} "
            f"({', '.join(approval.decision_id for approval in run)}); "
            "a newer approval created a newer execution.",
        )

    unverifiable = [approval.decision_id for approval in run if approval.action_snapshot is None]
    if unverifiable:
        return _refused(
            "approval_unverifiable",
            f"Approval {', '.join(unverifiable)} carries no action snapshot, so the approved "
            "revision cannot be verified; record a fresh approval.",
        )

    completing = run[-1]
    assert completing.action_snapshot is not None  # guarded above
    approved_fields = _dispatch_fields(completing.action_snapshot)
    current_fields = _dispatch_fields(action_snapshot(action))
    changed = [
        name for name in DISPATCH_SNAPSHOT_FIELDS if approved_fields[name] != current_fields[name]
    ]
    if changed:
        return _refused(
            "action_changed_since_approval",
            f"Action {action.action_id} changed since approval {completing.decision_id} "
            f"(fields: {', '.join(changed)}); record a rejection, then re-approve the revision.",
            changed_fields=changed,
        )

    if four_eyes:
        for approval in run[:-1]:
            assert approval.action_snapshot is not None  # guarded above
            other_fields = _dispatch_fields(approval.action_snapshot)
            mismatch = [
                name for name in DISPATCH_SNAPSHOT_FIELDS if other_fields[name] != approved_fields[name]
            ]
            if mismatch:
                return _refused(
                    "approval_revision_mismatch",
                    f"Approvals {approval.decision_id} and {completing.decision_id} signed "
                    f"different revisions of action {action.action_id} "
                    f"(fields: {', '.join(mismatch)}).",
                    changed_fields=mismatch,
                )

    if execution.destination != approved_fields["destination"]:
        return _refused(
            "destination_changed",
            f"Execution {execution.execution_id} targets '{execution.destination}' but the "
            f"approved destination is '{approved_fields['destination']}'.",
        )

    decision_ids = [approval.decision_id for approval in run]
    return DispatchAuthorization(
        authorized=True,
        reason=None,
        detail=f"Dispatch authorised by {', '.join(decision_ids)}.",
        decision_ids=decision_ids,
        changed_fields=[],
        execution_ids=bound_execution_ids or [execution.execution_id],
    )


def _parse_measured_at(value: str) -> datetime | None:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (ValueError, AttributeError, TypeError):
        return None


def assert_measurement_not_stale(
    existing_measured_at: str | None,
    incoming_measured_at: str,
) -> None:
    """Reject a measurement older than the recorded one: a late backfill must
    not regress latest_value and flip outcome status / the learning gate.
    Equal timestamps stay allowed (corrections supersede by insertion order);
    unparseable timestamps don't block the write."""
    if existing_measured_at is None:
        return
    existing = _parse_measured_at(existing_measured_at)
    incoming = _parse_measured_at(incoming_measured_at)
    if existing is None or incoming is None:
        return
    if incoming < existing:
        raise HTTPException(
            status_code=409,
            detail="A newer measurement already exists for this problem",
        )


def label_token(value: str) -> str:
    return value.lower().replace(" ", "-").replace("_", "-")


def _contract_direction(contract: OutcomeContract) -> str:
    """Improvement direction for a contract's OutcomeSnapshot.

    signal-rate metrics are complaint-style (lower is better) even when the
    baseline is 0 — deriving direction from target >= baseline there would
    report a recurrence as "target_met" (the zero-baseline trap that
    outcome_engine.outcome_status's explicit direction guards against).
    """
    if contract.primary_metric.startswith("signal_rate"):
        return "decrease"
    return outcome_engine.outcome_direction(
        baseline=contract.baseline, target=contract.success_threshold
    )


def _contract_status(contract: OutcomeContract, latest_value: float | None) -> str:
    return outcome_engine.outcome_status(
        baseline=contract.baseline,
        target=contract.success_threshold,
        measured=latest_value,
        direction=_contract_direction(contract),
    )


def learning_label(status: str) -> str:
    return status.replace("_", " ")


def stamp_contract_provenance(
    problem: ProblemRecord, measurement: OutcomeMeasurement
) -> OutcomeMeasurement:
    """Freeze the contract the observation is scored under, unless the
    measurement already carries one (the scheduler stamps its own).

    Snapshot and revision always describe the same contract: without a
    snapshot BOTH come from the problem (a caller-supplied revision alone
    would pair a stale number with a fresh snapshot); with a snapshot the
    revision is the snapshot's."""
    if measurement.contract_snapshot is None:
        return measurement.model_copy(
            update={
                "contract_snapshot": problem.outcome_contract,
                "contract_revision": problem.outcome_contract.revision,
            }
        )
    if measurement.contract_revision is None:
        return measurement.model_copy(
            update={"contract_revision": measurement.contract_snapshot.revision}
        )
    return measurement


# The contract terms that decide how a reading is SCORED. An amendment that
# touches only guardrail_metrics or responsible_owner bumps the revision but
# cannot reinterpret an observation, so it does not flag the snapshot.
SCORING_TERM_FIELDS = (
    "primary_metric",
    "baseline",
    "success_threshold",
    "comparison_method",
    "measurement_window_days",
)


def scoring_terms_differ(frozen: OutcomeContract, current: OutcomeContract) -> bool:
    return any(getattr(frozen, name) != getattr(current, name) for name in SCORING_TERM_FIELDS)


def build_outcome_snapshot(
    problem: ProblemRecord,
    measurement: OutcomeMeasurement | None,
    guardrails: list[GuardrailMeasurement],
) -> OutcomeSnapshot:
    """Snapshot = CURRENT contract terms + the latest observation scored and
    graded under the contract revision that was in force when it was taken.
    An amendment after a reading never re-labels that reading; the next
    scheduled read evaluates the new terms. ``contract_amended_after_measurement``
    flags a change of SCORING terms only (a guardrail or owner edit bumps
    the revision without touching how the reading was judged). The clock
    fields are the reading's own when the scheduler stamped one."""
    contract = problem.outcome_contract
    frozen = measurement.contract_snapshot if measurement is not None else None
    scored_under = frozen if frozen is not None else contract
    latest_value = None if measurement is None else measurement.observed_value
    measurement_source = None if measurement is None else measurement.measurement_source
    measured_under = None if measurement is None else measurement.contract_revision
    if measured_under is None and frozen is not None:
        measured_under = frozen.revision
    return OutcomeSnapshot(
        problem_id=problem.problem_id,
        metric=contract.primary_metric,
        baseline=contract.baseline,
        success_threshold=contract.success_threshold,
        latest_value=latest_value,
        status=_contract_status(scored_under, latest_value),
        improvement_direction=_contract_direction(scored_under),
        measurement_window_days=contract.measurement_window_days,
        comparison_method=contract.comparison_method,
        measurement_source=measurement_source,
        # The design grade belongs to the reading: graded under the method
        # in force when it was taken, not the method an amendment upgraded to.
        evidence_grade=outcome_engine.evidence_grade(
            comparison_method=scored_under.comparison_method,
            measurement_source=measurement_source,
        ),
        guardrails=guardrails,
        contract_revision=contract.revision,
        measured_under_revision=measured_under,
        contract_amended_after_measurement=(
            frozen is not None and scoring_terms_differ(frozen, contract)
        ),
        measured_comparison_method=None if measurement is None else scored_under.comparison_method,
        measured_baseline=None if measurement is None else scored_under.baseline,
        measured_success_threshold=None if measurement is None else scored_under.success_threshold,
        measurement_origin=None if measurement is None else measurement.clock_origin,
        measurement_origin_at=None if measurement is None else measurement.clock_origin_at,
        checkpoint_kind=None if measurement is None else measurement.checkpoint_kind,
    )


# Executions that actually left the system — drafts, blocks and failed pushes
# never published content, so Art. 50 accounting excludes them.
PUBLISHED_STATUSES = frozenset(
    {ExecutionStatus.pushed.value, ExecutionStatus.completed.value}
)


def _status_value(status) -> str:
    return str(getattr(status, "value", status))


def approved_action_keys(approvals) -> set[tuple[str, str]]:
    """(problem_id, action_id) pairs with an approved decision on record."""
    return {
        (record.problem_id, record.action_id)
        for record in approvals
        if _status_value(record.decision) == "approved"
    }


def is_human_reviewed(execution, approved_keys: set[tuple[str, str]]) -> bool:
    """Effective Art. 50(4) review status: the W2 stamp, or provable by the
    approval record. Executions are only ever created by record_approval on an
    approved decision, so pre-stamp rows are backfilled at read time — without
    this, every legacy human-approved push reads as an undisclosed AI
    auto-publication."""
    if execution.human_reviewed:
        return True
    return (execution.problem_id, execution.action_id) in approved_keys


def build_response_draft(problem: ProblemRecord, request: ClosureRecordRequest) -> str:
    facts = "; ".join(request.verified_resolution_facts)
    draft = (
        "Draft for human review only: "
        f"We reviewed the {problem.journey} / {problem.journey_stage} issue. "
        f"Verified resolution facts: {facts}. "
        f"Current closure status is {request.customer_status.replace('_', ' ')}. "
        "Please contact support if the problem is still affecting you."
    )
    return draft[:2000]


def customer_closure_eligible(request: ClosureRecordRequest) -> bool:
    return (
        request.operational_status in {"released", "verified"}
        and request.customer_status in {"draft_ready", "contacted"}
        and request.unresolved_customers > 0
    )


def build_jira_issue_draft(
    *,
    draft_id: str,
    problem: ProblemRecord,
    action_id: str,
    execution_id: str,
    assignee: str,
    created_at: str,
) -> JiraIssueDraft:
    evidence_lines = [
        f"- {evidence.source} / {evidence.customer_id}: {evidence.excerpt}"
        for evidence in problem.evidence[:3]
    ]
    description = "\n".join(
        [
            problem.statement,
            "",
            f"Root-cause hypothesis: {problem.root_cause_hypothesis}",
            "",
            "Evidence:",
            *(evidence_lines or ["- No evidence excerpt available."]),
            "",
            "Outcome contract:",
            (
                f"- {problem.outcome_contract.primary_metric}: baseline "
                f"{problem.outcome_contract.baseline}, target "
                f"{problem.outcome_contract.success_threshold}"
            ),
        ]
    )

    return JiraIssueDraft(
        draft_id=draft_id,
        problem_id=problem.problem_id,
        action_id=action_id,
        execution_id=execution_id,
        project_key="ODR",
        issue_type="Task",
        summary=problem.title,
        description=description,
        labels=[
            "clara",
            label_token(problem.journey),
            label_token(problem.journey_stage),
        ],
        assignee=assignee,
        status="draft_created",
        created_at=created_at,
    )


class WorkflowStore:
    def __init__(self) -> None:
        self._approval_ids = count(1)
        self._execution_ids = count(1)
        self._jira_draft_ids = count(1)
        self._transition_ids = count(1)
        self._closure_ids = count(1)
        self._guardrail_ids = count(1)
        self._approvals: list[ApprovalRecord] = []
        self._executions: list[ExecutionRecord] = []
        self._jira_issue_drafts: list[JiraIssueDraft] = []
        self._outcomes: dict[str, OutcomeMeasurement] = {}
        self._transitions: list[ProblemTransitionRecord] = []
        self._learning_conclusions: list[LearningConclusionRecord] = []
        self._closure_records: list[ClosureRecord] = []
        self._guardrails: list[GuardrailMeasurement] = []

    def add_guardrail_measurement(
        self,
        *,
        problem_id: str,
        metric: str,
        status: str,
        observed_value: float | None = None,
        baseline: float | None = None,
        measured_at: str,
        note: str | None = None,
    ) -> GuardrailMeasurement:
        record = GuardrailMeasurement(
            guardrail_id=f"GRD-{next(self._guardrail_ids):04d}",
            problem_id=problem_id,
            metric=metric,
            status=status,
            observed_value=observed_value,
            baseline=baseline,
            measured_at=measured_at,
            note=note,
        )
        self._guardrails.append(record)
        return record

    def list_guardrail_measurements(self, problem_id: str) -> list[GuardrailMeasurement]:
        return [g for g in self._guardrails if g.problem_id == problem_id]

    def latest_guardrails(self, problem_id: str) -> list[GuardrailMeasurement]:
        """Latest readout per metric (records are append-only)."""
        latest: dict[str, GuardrailMeasurement] = {}
        for record in self.list_guardrail_measurements(problem_id):
            latest[record.metric] = record
        return [latest[m] for m in sorted(latest)]

    def list_approvals(self) -> list[ApprovalRecord]:
        return self._approvals

    def list_executions(self) -> list[ExecutionRecord]:
        return self._executions

    def add_execution(self, execution: ExecutionRecord) -> ExecutionRecord:
        """Record an execution created outside the approval flow (the LangGraph
        triage path) so audit export and Art. 50 accounting see it. The store
        assigns the execution id; any caller-provided id is replaced."""
        record = execution.model_copy(
            update={"execution_id": f"EXE-{next(self._execution_ids):04d}"}
        )
        self._executions.append(record)
        return record

    def update_execution(
        self,
        execution_id: str,
        *,
        status: ExecutionStatus,
        external_ref: str | None = None,
        detail: str | None = None,
        disclosure_applied: bool | None = None,
        dispatched_at: str | None = None,
        implemented_at: str | None = None,
        implementation_note: str | None = None,
    ) -> ExecutionRecord:
        for index, execution in enumerate(self._executions):
            if execution.execution_id == execution_id:
                update: dict = {"status": status, "external_ref": external_ref, "detail": detail}
                if disclosure_applied is not None:
                    update["disclosure_applied"] = disclosure_applied
                if dispatched_at is not None:
                    # Only the push that really left CLARA stamps the clock
                    # origin (action_push); a status update never invents one.
                    update["dispatched_at"] = dispatched_at
                if implemented_at is not None:
                    update["implemented_at"] = implemented_at
                if implementation_note is not None:
                    update["implementation_note"] = implementation_note
                updated = execution.model_copy(update=update)
                self._executions[index] = updated
                return updated
        raise HTTPException(status_code=404, detail="Execution not found")

    def list_jira_issue_drafts(self) -> list[JiraIssueDraft]:
        return self._jira_issue_drafts

    def scrub_customer_references(self, customer_id: str) -> int:
        """GDPR erasure: redact a customer's id inside Jira draft text.

        Drafts embed evidence excerpts (and with them customer ids) in their
        summary/description; erasure must reach them too.
        """
        scrubbed = 0
        for index, draft in enumerate(self._jira_issue_drafts):
            if customer_id in draft.description or customer_id in draft.summary:
                self._jira_issue_drafts[index] = draft.model_copy(
                    update={
                        "description": draft.description.replace(customer_id, "[erased]"),
                        "summary": draft.summary.replace(customer_id, "[erased]"),
                    }
                )
                scrubbed += 1
        return scrubbed

    def list_closure_records(self) -> list[ClosureRecord]:
        return self._closure_records

    def record_transition(
        self,
        *,
        problem: ProblemRecord,
        target_status: ProblemStatus,
        actor: str,
        note: str | None = None,
    ) -> ProblemTransitionRecord:
        if problem.status == target_status:
            raise HTTPException(status_code=409, detail="Problem is already in the target status")

        record = ProblemTransitionRecord(
            transition_id=f"TRN-{next(self._transition_ids):04d}",
            problem_id=problem.problem_id,
            from_status=problem.status,
            to_status=target_status,
            actor=actor,
            note=note,
            created_at=utc_now(),
        )
        self._transitions.append(record)
        return record

    def record_approval(
        self,
        *,
        problem: ProblemRecord,
        decision: ApprovalDecision,
        evidence_pack_hash: str | None = None,
        four_eyes: bool = False,
    ) -> ApprovalRecord:
        action = find_action(problem, decision.action_id)
        ordered = [
            (approval.action_id, approval.decision.value, approval.reviewer)
            for approval in self._approvals
            if approval.problem_id == problem.problem_id
        ]
        approved_action_ids = resolve_approval_state(
            ordered, decision=decision, four_eyes=four_eyes
        )
        completes_approval = fully_approved_now(
            ordered, decision=decision, four_eyes=four_eyes
        )
        assert_governance_allows_decision(
            problem=problem,
            decision=decision,
            action=action,
            approved_action_ids=approved_action_ids,
        )

        record = ApprovalRecord(
            decision_id=f"DEC-{next(self._approval_ids):04d}",
            problem_id=problem.problem_id,
            action_id=decision.action_id,
            decision=decision.decision,
            reviewer=decision.reviewer,
            note=decision.note,
            created_at=utc_now(),
            action_snapshot=action_snapshot(action),
            action_diff=action_diff(action),
            evidence_pack_hash=evidence_pack_hash,
        )
        self._approvals.append(record)

        # Four-eyes: the first of two approvals records the decision but holds
        # execution until a different reviewer confirms (completes_approval).
        if completes_approval:
            execution = ExecutionRecord(
                execution_id=f"EXE-{next(self._execution_ids):04d}",
                problem_id=problem.problem_id,
                action_id=action.action_id,
                destination=action.destination,
                status=ExecutionStatus.draft_created,
                owner=action.owner,
                summary=f"Draft {action.destination} execution created for {action.class_.value}.",
                created_at=record.created_at,
                # Art. 50(4): this execution exists because a named human approved
                # it — stamp the editorial review as a first-class field.
                human_reviewed=True,
                reviewed_by=decision.reviewer,
                reviewed_at=record.created_at,
            )
            self._executions.append(execution)
            if action.destination == "jira":
                self._jira_issue_drafts.append(
                    build_jira_issue_draft(
                        draft_id=f"JIRA-DRAFT-{next(self._jira_draft_ids):04d}",
                        problem=problem,
                        action_id=action.action_id,
                        execution_id=execution.execution_id,
                        assignee=action.owner,
                        created_at=record.created_at,
                    )
                )
            record = record.model_copy(update={"execution_id": execution.execution_id})
            self._approvals[-1] = record

        return record

    def record_outcome(
        self,
        *,
        problem: ProblemRecord,
        measurement: OutcomeMeasurement,
    ) -> OutcomeMeasurement:
        if measurement.metric != problem.outcome_contract.primary_metric:
            raise HTTPException(status_code=422, detail="Metric does not match the outcome contract")

        existing = self._outcomes.get(problem.problem_id)
        assert_measurement_not_stale(
            existing.measured_at if existing is not None else None,
            measurement.measured_at,
        )
        measurement = stamp_contract_provenance(problem, measurement)
        self._outcomes[problem.problem_id] = measurement
        return measurement

    def record_learning_conclusion(
        self,
        *,
        problem: ProblemRecord,
        conclusion: LearningConclusionRequest,
        tenant_id: str,
        actor: str,
    ) -> LearningConclusionRecord:
        reviewed_at = utc_now()

        record = LearningConclusionRecord(
            conclusion_id=f"LRN-{uuid4().hex}",
            problem_id=problem.problem_id,
            tenant_id=tenant_id,
            reviewer=actor,
            reviewed_at=reviewed_at,
            retention_expires_at=retention_expires_at(reviewed_at),
            **conclusion.model_dump(),
        )
        self._learning_conclusions.append(record)
        return record

    def record_closure(
        self,
        *,
        problem: ProblemRecord,
        closure: ClosureRecordRequest,
        tenant_id: str,
        actor: str,
    ) -> ClosureRecord:
        if closure.unresolved_customers > problem.affected_cohort.customers:
            raise HTTPException(status_code=422, detail="Unresolved customers cannot exceed affected cohort")
        created_at = utc_now()
        record = ClosureRecord(
            closure_id=f"CLR-{next(self._closure_ids):04d}",
            problem_id=problem.problem_id,
            tenant_id=tenant_id,
            actor=actor,
            customer_closure_eligible=customer_closure_eligible(closure),
            created_at=created_at,
            response_draft=closure.response_draft or build_response_draft(problem, closure),
            **closure.model_dump(exclude={"response_draft"}),
        )
        self._closure_records.append(record)
        return record

    def latest_learning_conclusion(
        self,
        problem: ProblemRecord,
        tenant_id: str | None = None,
    ) -> LearningConclusionRecord | None:
        conclusions = [
            conclusion
            for conclusion in self._learning_conclusions
            if conclusion.problem_id == problem.problem_id
            and (tenant_id is None or conclusion.tenant_id == tenant_id)
        ]
        return max(conclusions, key=lambda conclusion: conclusion.reviewed_at, default=None)

    def latest_outcome(self, problem_id: str) -> OutcomeMeasurement | None:
        return self._outcomes.get(problem_id)

    def outcome_snapshot(self, problem: ProblemRecord) -> OutcomeSnapshot:
        return build_outcome_snapshot(
            problem,
            self._outcomes.get(problem.problem_id),
            self.latest_guardrails(problem.problem_id),
        )

    def state_for_problem(self, problem: ProblemRecord, tenant_id: str | None = None) -> WorkflowState:
        return WorkflowState(
            problem_id=problem.problem_id,
            approvals=[
                approval for approval in self._approvals if approval.problem_id == problem.problem_id
            ],
            executions=[
                execution for execution in self._executions if execution.problem_id == problem.problem_id
            ],
            jira_issue_drafts=[
                draft for draft in self._jira_issue_drafts if draft.problem_id == problem.problem_id
            ],
            outcome=self.outcome_snapshot(problem),
            learning_conclusions=[
                conclusion
                for conclusion in self._learning_conclusions
                if conclusion.problem_id == problem.problem_id
                and (tenant_id is None or conclusion.tenant_id == tenant_id)
            ],
            closure_records=[
                closure
                for closure in self._closure_records
                if closure.problem_id == problem.problem_id
                and (tenant_id is None or closure.tenant_id == tenant_id)
            ],
            timeline=self.timeline_for_problem(problem, tenant_id=tenant_id),
        )

    def timeline_for_problem(
        self,
        problem: ProblemRecord,
        tenant_id: str | None = None,
    ) -> list[TimelineEvent]:
        events: list[TimelineEvent] = []

        events.extend(
            TimelineEvent(
                event_id=transition.transition_id,
                problem_id=transition.problem_id,
                event_type="status_changed",
                label=f"Status changed to {transition.to_status.value.replace('_', ' ')}",
                detail=transition.note
                or f"{transition.from_status.value.replace('_', ' ')} -> {transition.to_status.value.replace('_', ' ')}",
                actor=transition.actor,
                created_at=transition.created_at,
            )
            for transition in self._transitions
            if transition.problem_id == problem.problem_id
        )

        events.extend(
            TimelineEvent(
                event_id=approval.decision_id,
                problem_id=approval.problem_id,
                event_type="approval_recorded",
                label=f"Action {approval.decision.value.replace('_', ' ')}",
                detail=approval.note or f"{approval.action_id} reviewed.",
                actor=approval.reviewer,
                created_at=approval.created_at,
            )
            for approval in self._approvals
            if approval.problem_id == problem.problem_id
        )

        events.extend(
            TimelineEvent(
                event_id=execution.execution_id,
                problem_id=execution.problem_id,
                event_type="execution_created",
                label=f"Execution {execution.status.value.replace('_', ' ')}",
                detail=execution.summary,
                actor=execution.owner,
                created_at=execution.created_at,
            )
            for execution in self._executions
            if execution.problem_id == problem.problem_id
        )

        events.extend(
            TimelineEvent(
                event_id=draft.draft_id,
                problem_id=draft.problem_id,
                event_type="jira_draft_created",
                label="Jira draft created",
                detail=f"{draft.project_key} {draft.issue_type}: {draft.summary}",
                actor=draft.assignee,
                created_at=draft.created_at,
            )
            for draft in self._jira_issue_drafts
            if draft.problem_id == problem.problem_id
        )

        measurement = self._outcomes.get(problem.problem_id)
        if measurement is not None:
            events.append(
                TimelineEvent(
                    event_id=f"OUT-{problem.problem_id}",
                    problem_id=problem.problem_id,
                    event_type="outcome_measured",
                    label="Outcome measured",
                    detail=f"{measurement.metric} observed at {measurement.observed_value}.",
                    actor=None,
                    created_at=measurement.measured_at,
                )
            )

        events.extend(
            TimelineEvent(
                event_id=conclusion.conclusion_id,
                problem_id=conclusion.problem_id,
                event_type="learning_reviewed",
                label=f"Learning: {learning_label(conclusion.learning_status.value)}",
                detail=conclusion.summary,
                actor=conclusion.reviewer,
                created_at=conclusion.reviewed_at,
            )
            for conclusion in self._learning_conclusions
            if conclusion.problem_id == problem.problem_id
            and (tenant_id is None or conclusion.tenant_id == tenant_id)
        )
        events.extend(
            TimelineEvent(
                event_id=closure.closure_id,
                problem_id=closure.problem_id,
                event_type="closure_recorded",
                label="Closure recorded",
                detail=(
                    f"Operational: {closure.operational_status.replace('_', ' ')} / "
                    f"customer: {closure.customer_status.replace('_', ' ')} / "
                    f"unresolved customers: {closure.unresolved_customers}"
                ),
                actor=closure.actor,
                created_at=closure.created_at,
            )
            for closure in self._closure_records
            if closure.problem_id == problem.problem_id
            and (tenant_id is None or closure.tenant_id == tenant_id)
        )

        return sorted(events, key=lambda event: event.created_at, reverse=True)


class SQLiteWorkflowStore:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._connection = SerializedConnection(self.path)
        self._initialize()

    def _initialize(self) -> None:
        self._connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS approvals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                problem_id TEXT NOT NULL,
                action_id TEXT NOT NULL,
                decision TEXT NOT NULL,
                reviewer TEXT NOT NULL,
                note TEXT,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS executions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                problem_id TEXT NOT NULL,
                action_id TEXT NOT NULL,
                destination TEXT NOT NULL,
                status TEXT NOT NULL,
                owner TEXT NOT NULL,
                summary TEXT NOT NULL,
                created_at TEXT NOT NULL,
                external_ref TEXT,
                detail TEXT,
                human_reviewed INTEGER NOT NULL DEFAULT 0,
                reviewed_by TEXT,
                reviewed_at TEXT,
                disclosure_applied INTEGER NOT NULL DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS jira_issue_drafts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                problem_id TEXT NOT NULL,
                action_id TEXT NOT NULL,
                execution_id TEXT NOT NULL,
                project_key TEXT NOT NULL,
                issue_type TEXT NOT NULL,
                summary TEXT NOT NULL,
                description TEXT NOT NULL,
                labels TEXT NOT NULL,
                assignee TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS outcomes (
                problem_id TEXT PRIMARY KEY,
                metric TEXT NOT NULL,
                observed_value REAL NOT NULL,
                measured_at TEXT NOT NULL,
                notes TEXT,
                measurement_source TEXT NOT NULL DEFAULT 'manual'
            );

            CREATE TABLE IF NOT EXISTS guardrail_measurements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                problem_id TEXT NOT NULL,
                metric TEXT NOT NULL,
                status TEXT NOT NULL,
                observed_value REAL,
                baseline REAL,
                measured_at TEXT NOT NULL,
                note TEXT
            );

            CREATE TABLE IF NOT EXISTS problem_transitions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                problem_id TEXT NOT NULL,
                from_status TEXT NOT NULL,
                to_status TEXT NOT NULL,
                actor TEXT NOT NULL,
                note TEXT,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS learning_conclusions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conclusion_id TEXT NOT NULL UNIQUE,
                problem_id TEXT NOT NULL,
                tenant_id TEXT NOT NULL DEFAULT 'legacy',
                learning_status TEXT NOT NULL,
                reviewer TEXT NOT NULL,
                reviewed_at TEXT NOT NULL,
                retention_expires_at TEXT NOT NULL DEFAULT '',
                summary TEXT NOT NULL,
                limitations TEXT NOT NULL,
                next_step TEXT
            );

            CREATE TABLE IF NOT EXISTS closure_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                closure_id TEXT NOT NULL UNIQUE,
                problem_id TEXT NOT NULL,
                payload TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            """
        )
        self._ensure_column("approvals", "action_snapshot", "TEXT")
        self._ensure_column("approvals", "action_diff", "TEXT NOT NULL DEFAULT '[]'")
        self._ensure_column("approvals", "evidence_pack_hash", "TEXT")
        self._ensure_column("approvals", "execution_id", "TEXT")
        self._ensure_column("outcomes", "measurement_source", "TEXT NOT NULL DEFAULT 'manual'")
        self._ensure_column("learning_conclusions", "tenant_id", "TEXT NOT NULL DEFAULT 'legacy'")
        self._ensure_column("learning_conclusions", "retention_expires_at", "TEXT NOT NULL DEFAULT ''")
        self._ensure_column("executions", "external_ref", "TEXT")
        self._ensure_column("executions", "detail", "TEXT")
        self._ensure_column("executions", "human_reviewed", "INTEGER NOT NULL DEFAULT 0")
        self._ensure_column("executions", "reviewed_by", "TEXT")
        self._ensure_column("executions", "reviewed_at", "TEXT")
        self._ensure_column("executions", "disclosure_applied", "INTEGER NOT NULL DEFAULT 0")
        self._ensure_column("executions", "dispatched_at", "TEXT")
        self._ensure_column("executions", "implemented_at", "TEXT")
        self._ensure_column("executions", "implementation_note", "TEXT")
        self._ensure_column("outcomes", "contract_revision", "INTEGER")
        self._ensure_column("outcomes", "contract_json", "TEXT")
        self._ensure_column("outcomes", "checkpoint_kind", "TEXT")
        self._ensure_column("outcomes", "plan_id", "INTEGER")
        self._ensure_column("outcomes", "execution_id", "TEXT")
        self._ensure_column("outcomes", "clock_origin", "TEXT")
        self._ensure_column("outcomes", "clock_origin_at", "TEXT")
        # Idempotent backfill for the JWT-tenant migration: header-era rows were
        # tagged with client strings ('demo_tenant'/...); the tenant key is now
        # str(workspace_id) and local dev is the default workspace ('1'). Closure
        # rows keep tenant inside the payload JSON, hence the json_set.
        self._connection.execute(
            "UPDATE learning_conclusions SET tenant_id = '1'"
            " WHERE tenant_id IN ('legacy', 'demo_tenant', 'tenant_feature_test')"
        )
        self._connection.execute(
            "UPDATE closure_records SET payload = json_set(payload, '$.tenant_id', '1')"
            " WHERE json_extract(payload, '$.tenant_id')"
            " IN ('legacy', 'demo_tenant', 'tenant_feature_test')"
        )
        self._connection.commit()

    def _ensure_column(self, table: str, column: str, definition: str) -> None:
        columns = {
            row["name"]
            for row in self._connection.execute(f"PRAGMA table_info({table})").fetchall()
        }
        if column not in columns:
            self._connection.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")

    def list_approvals(self) -> list[ApprovalRecord]:
        rows = self._connection.execute("SELECT * FROM approvals ORDER BY id").fetchall()
        return [self._approval_from_row(row) for row in rows]

    def add_execution(self, execution: ExecutionRecord) -> ExecutionRecord:
        """Record an execution created outside the approval flow (the LangGraph
        triage path). The row id assigns the EXE-{rowid} execution id."""
        cursor = self._connection.execute(
            """
            INSERT INTO executions
                (problem_id, action_id, destination, status, owner, summary, created_at,
                 external_ref, detail, human_reviewed, reviewed_by, reviewed_at,
                 disclosure_applied, dispatched_at, implemented_at, implementation_note)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                execution.problem_id,
                execution.action_id,
                execution.destination,
                execution.status.value,
                execution.owner,
                execution.summary,
                execution.created_at,
                execution.external_ref,
                execution.detail,
                int(execution.human_reviewed),
                execution.reviewed_by,
                execution.reviewed_at,
                int(execution.disclosure_applied),
                execution.dispatched_at,
                execution.implemented_at,
                execution.implementation_note,
            ),
        )
        self._connection.commit()
        return execution.model_copy(
            update={"execution_id": f"EXE-{cursor.lastrowid:04d}"}
        )

    def update_execution(
        self,
        execution_id: str,
        *,
        status: ExecutionStatus,
        external_ref: str | None = None,
        detail: str | None = None,
        disclosure_applied: bool | None = None,
        dispatched_at: str | None = None,
        implemented_at: str | None = None,
        implementation_note: str | None = None,
    ) -> ExecutionRecord:
        # execution_id is derived as EXE-{rowid:04d}; map back to the numeric row id.
        try:
            row_id = int(execution_id.removeprefix("EXE-"))
        except ValueError as exc:
            raise HTTPException(status_code=404, detail="Execution not found") from exc

        assignments = "status = ?, external_ref = ?, detail = ?"
        values: list = [status.value, external_ref, detail]
        if disclosure_applied is not None:
            assignments += ", disclosure_applied = ?"
            values.append(int(disclosure_applied))
        if dispatched_at is not None:
            # Only the push that really left CLARA stamps the clock origin
            # (action_push); a status update never invents one.
            assignments += ", dispatched_at = ?"
            values.append(dispatched_at)
        if implemented_at is not None:
            assignments += ", implemented_at = ?"
            values.append(implemented_at)
        if implementation_note is not None:
            assignments += ", implementation_note = ?"
            values.append(implementation_note)
        cursor = self._connection.execute(
            f"UPDATE executions SET {assignments} WHERE id = ?",
            (*values, row_id),
        )
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Execution not found")
        self._connection.commit()
        row = self._connection.execute(
            "SELECT * FROM executions WHERE id = ?", (row_id,)
        ).fetchone()
        return self._execution_from_row(row)

    def list_executions(self) -> list[ExecutionRecord]:
        rows = self._connection.execute("SELECT * FROM executions ORDER BY id").fetchall()
        return [self._execution_from_row(row) for row in rows]

    def list_jira_issue_drafts(self) -> list[JiraIssueDraft]:
        rows = self._connection.execute("SELECT * FROM jira_issue_drafts ORDER BY id").fetchall()
        return [self._jira_issue_draft_from_row(row) for row in rows]

    def scrub_customer_references(self, customer_id: str) -> int:
        """GDPR erasure: redact a customer's id inside stored Jira draft text."""
        like = f"%{customer_id}%"
        cursor = self._connection.execute(
            "UPDATE jira_issue_drafts SET"
            " description = REPLACE(description, ?, '[erased]'),"
            " summary = REPLACE(summary, ?, '[erased]')"
            " WHERE description LIKE ? OR summary LIKE ?",
            (customer_id, customer_id, like, like),
        )
        self._connection.commit()
        return cursor.rowcount

    def list_closure_records(self) -> list[ClosureRecord]:
        rows = self._connection.execute("SELECT * FROM closure_records ORDER BY id").fetchall()
        return [ClosureRecord.model_validate(json.loads(row["payload"])) for row in rows]

    def record_transition(
        self,
        *,
        problem: ProblemRecord,
        target_status: ProblemStatus,
        actor: str,
        note: str | None = None,
    ) -> ProblemTransitionRecord:
        if problem.status == target_status:
            raise HTTPException(status_code=409, detail="Problem is already in the target status")

        created_at = utc_now()
        cursor = self._connection.execute(
            """
            INSERT INTO problem_transitions
                (problem_id, from_status, to_status, actor, note, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                problem.problem_id,
                problem.status.value,
                target_status.value,
                actor,
                note,
                created_at,
            ),
        )
        self._connection.commit()
        row = self._connection.execute(
            "SELECT * FROM problem_transitions WHERE id = ?",
            (cursor.lastrowid,),
        ).fetchone()
        return self._transition_from_row(row)

    def record_approval(
        self,
        *,
        problem: ProblemRecord,
        decision: ApprovalDecision,
        evidence_pack_hash: str | None = None,
        four_eyes: bool = False,
    ) -> ApprovalRecord:
        action = find_action(problem, decision.action_id)
        decision_rows = self._connection.execute(
            "SELECT action_id, decision, reviewer FROM approvals WHERE problem_id = ? ORDER BY id",
            (problem.problem_id,),
        ).fetchall()
        ordered = [(row["action_id"], row["decision"], row["reviewer"]) for row in decision_rows]
        approved_action_ids = resolve_approval_state(
            ordered, decision=decision, four_eyes=four_eyes
        )
        completes_approval = fully_approved_now(
            ordered, decision=decision, four_eyes=four_eyes
        )
        assert_governance_allows_decision(
            problem=problem,
            decision=decision,
            action=action,
            approved_action_ids=approved_action_ids,
        )

        created_at = utc_now()
        cursor = self._connection.execute(
            """
            INSERT INTO approvals (
                problem_id,
                action_id,
                decision,
                reviewer,
                note,
                created_at,
                action_snapshot,
                action_diff,
                evidence_pack_hash
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                problem.problem_id,
                decision.action_id,
                decision.decision.value,
                decision.reviewer,
                decision.note,
                created_at,
                json.dumps(action_snapshot(action).model_dump(mode="json", by_alias=True)),
                json.dumps([change.model_dump(mode="json") for change in action_diff(action)]),
                evidence_pack_hash,
            ),
        )
        approval_id = cursor.lastrowid

        # Four-eyes: the first of two approvals records the decision but holds
        # execution until a different reviewer confirms (completes_approval).
        execution_id: str | None = None
        if completes_approval:
            execution_cursor = self._connection.execute(
                """
                INSERT INTO executions
                    (problem_id, action_id, destination, status, owner, summary, created_at,
                     human_reviewed, reviewed_by, reviewed_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    problem.problem_id,
                    action.action_id,
                    action.destination,
                    ExecutionStatus.draft_created.value,
                    action.owner,
                    f"Draft {action.destination} execution created for {action.class_.value}.",
                    created_at,
                    1,
                    decision.reviewer,
                    created_at,
                ),
            )
            execution_id = f"EXE-{execution_cursor.lastrowid:04d}"
            # Bind the completing decision to the execution it created so a
            # later retry can prove it dispatches under THIS approval run.
            self._connection.execute(
                "UPDATE approvals SET execution_id = ? WHERE id = ?",
                (execution_id, approval_id),
            )
            if action.destination == "jira":
                draft = build_jira_issue_draft(
                    draft_id="JIRA-DRAFT-PENDING",
                    problem=problem,
                    action_id=action.action_id,
                    execution_id=execution_id,
                    assignee=action.owner,
                    created_at=created_at,
                )
                self._connection.execute(
                    """
                    INSERT INTO jira_issue_drafts (
                        problem_id,
                        action_id,
                        execution_id,
                        project_key,
                        issue_type,
                        summary,
                        description,
                        labels,
                        assignee,
                        status,
                        created_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        draft.problem_id,
                        draft.action_id,
                        draft.execution_id,
                        draft.project_key,
                        draft.issue_type,
                        draft.summary,
                        draft.description,
                        ",".join(draft.labels),
                        draft.assignee,
                        draft.status,
                        draft.created_at,
                    ),
                )

        self._connection.commit()
        row = self._connection.execute("SELECT * FROM approvals WHERE id = ?", (approval_id,)).fetchone()
        record = self._approval_from_row(row)
        if execution_id is not None:
            record = record.model_copy(update={"execution_id": execution_id})
        return record

    def record_outcome(
        self,
        *,
        problem: ProblemRecord,
        measurement: OutcomeMeasurement,
    ) -> OutcomeMeasurement:
        if measurement.metric != problem.outcome_contract.primary_metric:
            raise HTTPException(status_code=422, detail="Metric does not match the outcome contract")

        existing_row = self._connection.execute(
            "SELECT measured_at FROM outcomes WHERE problem_id = ?",
            (measurement.problem_id,),
        ).fetchone()
        assert_measurement_not_stale(
            existing_row["measured_at"] if existing_row is not None else None,
            measurement.measured_at,
        )
        measurement = stamp_contract_provenance(problem, measurement)
        self._connection.execute(
            """
            INSERT INTO outcomes (problem_id, metric, observed_value, measured_at, notes,
                                  measurement_source, contract_revision, contract_json,
                                  checkpoint_kind, plan_id, execution_id,
                                  clock_origin, clock_origin_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(problem_id) DO UPDATE SET
                metric = excluded.metric,
                observed_value = excluded.observed_value,
                measured_at = excluded.measured_at,
                notes = excluded.notes,
                measurement_source = excluded.measurement_source,
                contract_revision = excluded.contract_revision,
                contract_json = excluded.contract_json,
                checkpoint_kind = excluded.checkpoint_kind,
                plan_id = excluded.plan_id,
                execution_id = excluded.execution_id,
                clock_origin = excluded.clock_origin,
                clock_origin_at = excluded.clock_origin_at
            """,
            (
                measurement.problem_id,
                measurement.metric,
                measurement.observed_value,
                measurement.measured_at,
                measurement.notes,
                measurement.measurement_source,
                measurement.contract_revision,
                (
                    json.dumps(measurement.contract_snapshot.model_dump(mode="json"))
                    if measurement.contract_snapshot is not None
                    else None
                ),
                measurement.checkpoint_kind,
                measurement.plan_id,
                measurement.execution_id,
                measurement.clock_origin,
                measurement.clock_origin_at,
            ),
        )
        self._connection.commit()
        return measurement

    def record_learning_conclusion(
        self,
        *,
        problem: ProblemRecord,
        conclusion: LearningConclusionRequest,
        tenant_id: str,
        actor: str,
    ) -> LearningConclusionRecord:
        reviewed_at = utc_now()
        record = LearningConclusionRecord(
            conclusion_id=f"LRN-{uuid4().hex}",
            problem_id=problem.problem_id,
            tenant_id=tenant_id,
            reviewer=actor,
            reviewed_at=reviewed_at,
            retention_expires_at=retention_expires_at(reviewed_at),
            **conclusion.model_dump(),
        )
        self._connection.execute(
            """
            INSERT INTO learning_conclusions (
                conclusion_id,
                problem_id,
                tenant_id,
                learning_status,
                reviewer,
                reviewed_at,
                retention_expires_at,
                summary,
                limitations,
                next_step
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record.conclusion_id,
                record.problem_id,
                record.tenant_id,
                record.learning_status.value,
                record.reviewer,
                record.reviewed_at,
                record.retention_expires_at,
                record.summary,
                record.limitations,
                record.next_step,
            ),
        )
        self._connection.commit()
        return record

    def record_closure(
        self,
        *,
        problem: ProblemRecord,
        closure: ClosureRecordRequest,
        tenant_id: str,
        actor: str,
    ) -> ClosureRecord:
        if closure.unresolved_customers > problem.affected_cohort.customers:
            raise HTTPException(status_code=422, detail="Unresolved customers cannot exceed affected cohort")
        created_at = utc_now()
        record = ClosureRecord(
            closure_id=f"CLR-{uuid4().hex}",
            problem_id=problem.problem_id,
            tenant_id=tenant_id,
            actor=actor,
            customer_closure_eligible=customer_closure_eligible(closure),
            created_at=created_at,
            response_draft=closure.response_draft or build_response_draft(problem, closure),
            **closure.model_dump(exclude={"response_draft"}),
        )
        self._connection.execute(
            """
            INSERT INTO closure_records (closure_id, problem_id, payload, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (
                record.closure_id,
                record.problem_id,
                json.dumps(record.model_dump(mode="json")),
                record.created_at,
            ),
        )
        self._connection.commit()
        return record

    def add_guardrail_measurement(
        self,
        *,
        problem_id: str,
        metric: str,
        status: str,
        observed_value: float | None = None,
        baseline: float | None = None,
        measured_at: str,
        note: str | None = None,
    ) -> GuardrailMeasurement:
        cursor = self._connection.execute(
            """
            INSERT INTO guardrail_measurements
                (problem_id, metric, status, observed_value, baseline, measured_at, note)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (problem_id, metric, status, observed_value, baseline, measured_at, note),
        )
        self._connection.commit()
        return GuardrailMeasurement(
            guardrail_id=f"GRD-{cursor.lastrowid:04d}",
            problem_id=problem_id,
            metric=metric,
            status=status,
            observed_value=observed_value,
            baseline=baseline,
            measured_at=measured_at,
            note=note,
        )

    def list_guardrail_measurements(self, problem_id: str) -> list[GuardrailMeasurement]:
        rows = self._connection.execute(
            "SELECT * FROM guardrail_measurements WHERE problem_id = ? ORDER BY id",
            (problem_id,),
        ).fetchall()
        return [
            GuardrailMeasurement(
                guardrail_id=f"GRD-{row['id']:04d}",
                problem_id=row["problem_id"],
                metric=row["metric"],
                status=row["status"],
                observed_value=row["observed_value"],
                baseline=row["baseline"],
                measured_at=row["measured_at"],
                note=row["note"],
            )
            for row in rows
        ]

    def latest_guardrails(self, problem_id: str) -> list[GuardrailMeasurement]:
        latest: dict[str, GuardrailMeasurement] = {}
        for record in self.list_guardrail_measurements(problem_id):
            latest[record.metric] = record
        return [latest[m] for m in sorted(latest)]

    def latest_outcome(self, problem_id: str) -> OutcomeMeasurement | None:
        row = self._connection.execute(
            "SELECT * FROM outcomes WHERE problem_id = ?",
            (problem_id,),
        ).fetchone()
        return None if row is None else self._measurement_from_row(row)

    def outcome_snapshot(self, problem: ProblemRecord) -> OutcomeSnapshot:
        return build_outcome_snapshot(
            problem,
            self.latest_outcome(problem.problem_id),
            self.latest_guardrails(problem.problem_id),
        )

    def latest_learning_conclusion(
        self,
        problem: ProblemRecord,
        tenant_id: str | None = None,
    ) -> LearningConclusionRecord | None:
        tenant_clause = "AND tenant_id = ?" if tenant_id is not None else ""
        params = (problem.problem_id, tenant_id) if tenant_id is not None else (problem.problem_id,)
        row = self._connection.execute(
            f"""
            SELECT * FROM learning_conclusions
            WHERE problem_id = ?
            {tenant_clause}
            ORDER BY reviewed_at DESC, id DESC
            LIMIT 1
            """,
            params,
        ).fetchone()
        return None if row is None else self._learning_conclusion_from_row(row)

    def state_for_problem(self, problem: ProblemRecord, tenant_id: str | None = None) -> WorkflowState:
        approvals = self._connection.execute(
            "SELECT * FROM approvals WHERE problem_id = ? ORDER BY id",
            (problem.problem_id,),
        ).fetchall()
        executions = self._connection.execute(
            "SELECT * FROM executions WHERE problem_id = ? ORDER BY id",
            (problem.problem_id,),
        ).fetchall()
        jira_issue_drafts = self._connection.execute(
            "SELECT * FROM jira_issue_drafts WHERE problem_id = ? ORDER BY id",
            (problem.problem_id,),
        ).fetchall()
        learning_clause = "AND tenant_id = ?" if tenant_id is not None else ""
        learning_params = (problem.problem_id, tenant_id) if tenant_id is not None else (problem.problem_id,)
        learning_conclusions = self._connection.execute(
            f"SELECT * FROM learning_conclusions WHERE problem_id = ? {learning_clause} ORDER BY id",
            learning_params,
        ).fetchall()
        closure_rows = self._connection.execute(
            "SELECT * FROM closure_records WHERE problem_id = ? ORDER BY id",
            (problem.problem_id,),
        ).fetchall()

        return WorkflowState(
            problem_id=problem.problem_id,
            approvals=[self._approval_from_row(row) for row in approvals],
            executions=[self._execution_from_row(row) for row in executions],
            jira_issue_drafts=[
                self._jira_issue_draft_from_row(row) for row in jira_issue_drafts
            ],
            outcome=self.outcome_snapshot(problem),
            learning_conclusions=[
                self._learning_conclusion_from_row(row) for row in learning_conclusions
            ],
            closure_records=[
                record
                for record in (ClosureRecord.model_validate(json.loads(row["payload"])) for row in closure_rows)
                if tenant_id is None or record.tenant_id == tenant_id
            ],
            timeline=self.timeline_for_problem(problem, tenant_id=tenant_id),
        )

    def timeline_for_problem(
        self,
        problem: ProblemRecord,
        tenant_id: str | None = None,
    ) -> list[TimelineEvent]:
        events: list[TimelineEvent] = []
        transition_rows = self._connection.execute(
            "SELECT * FROM problem_transitions WHERE problem_id = ? ORDER BY id",
            (problem.problem_id,),
        ).fetchall()
        approval_rows = self._connection.execute(
            "SELECT * FROM approvals WHERE problem_id = ? ORDER BY id",
            (problem.problem_id,),
        ).fetchall()
        execution_rows = self._connection.execute(
            "SELECT * FROM executions WHERE problem_id = ? ORDER BY id",
            (problem.problem_id,),
        ).fetchall()
        jira_draft_rows = self._connection.execute(
            "SELECT * FROM jira_issue_drafts WHERE problem_id = ? ORDER BY id",
            (problem.problem_id,),
        ).fetchall()
        outcome_row = self._connection.execute(
            "SELECT * FROM outcomes WHERE problem_id = ?",
            (problem.problem_id,),
        ).fetchone()
        learning_clause = "AND tenant_id = ?" if tenant_id is not None else ""
        learning_params = (problem.problem_id, tenant_id) if tenant_id is not None else (problem.problem_id,)
        learning_rows = self._connection.execute(
            f"SELECT * FROM learning_conclusions WHERE problem_id = ? {learning_clause} ORDER BY id",
            learning_params,
        ).fetchall()
        closure_rows = self._connection.execute(
            "SELECT * FROM closure_records WHERE problem_id = ? ORDER BY id",
            (problem.problem_id,),
        ).fetchall()

        events.extend(
            self._transition_timeline_event(self._transition_from_row(row))
            for row in transition_rows
        )
        events.extend(
            self._approval_timeline_event(self._approval_from_row(row))
            for row in approval_rows
        )
        events.extend(
            self._execution_timeline_event(self._execution_from_row(row))
            for row in execution_rows
        )
        events.extend(
            self._jira_draft_timeline_event(self._jira_issue_draft_from_row(row))
            for row in jira_draft_rows
        )
        if outcome_row is not None:
            events.append(self._outcome_timeline_event(problem.problem_id, outcome_row))
        events.extend(
            self._learning_timeline_event(self._learning_conclusion_from_row(row))
            for row in learning_rows
        )
        events.extend(
            self._closure_timeline_event(record)
            for record in (ClosureRecord.model_validate(json.loads(row["payload"])) for row in closure_rows)
            if tenant_id is None or record.tenant_id == tenant_id
        )

        return sorted(events, key=lambda event: event.created_at, reverse=True)

    @staticmethod
    def _approval_from_row(row: sqlite3.Row) -> ApprovalRecord:
        snapshot_payload = row["action_snapshot"] if "action_snapshot" in row.keys() else None
        diff_payload = row["action_diff"] if "action_diff" in row.keys() else "[]"
        return ApprovalRecord(
            decision_id=f"DEC-{row['id']:04d}",
            problem_id=row["problem_id"],
            action_id=row["action_id"],
            decision=row["decision"],
            reviewer=row["reviewer"],
            note=row["note"],
            created_at=row["created_at"],
            action_snapshot=ActionProposalSnapshot.model_validate(json.loads(snapshot_payload))
            if snapshot_payload
            else None,
            action_diff=[ActionProposalChange.model_validate(item) for item in json.loads(diff_payload or "[]")],
            evidence_pack_hash=row["evidence_pack_hash"] if "evidence_pack_hash" in row.keys() else None,
            execution_id=row["execution_id"] if "execution_id" in row.keys() else None,
        )

    @staticmethod
    def _execution_from_row(row: sqlite3.Row) -> ExecutionRecord:
        return ExecutionRecord(
            execution_id=f"EXE-{row['id']:04d}",
            problem_id=row["problem_id"],
            action_id=row["action_id"],
            destination=row["destination"],
            status=row["status"],
            owner=row["owner"],
            summary=row["summary"],
            created_at=row["created_at"],
            external_ref=row["external_ref"],
            detail=row["detail"],
            human_reviewed=bool(row["human_reviewed"]),
            reviewed_by=row["reviewed_by"],
            reviewed_at=row["reviewed_at"],
            disclosure_applied=bool(row["disclosure_applied"]),
            dispatched_at=row["dispatched_at"],
            implemented_at=row["implemented_at"],
            implementation_note=row["implementation_note"],
        )

    @staticmethod
    def _measurement_from_row(row: sqlite3.Row) -> OutcomeMeasurement:
        keys = row.keys()

        def _col(name: str):
            return row[name] if name in keys else None

        contract_json = _col("contract_json")
        return OutcomeMeasurement(
            problem_id=row["problem_id"],
            metric=row["metric"],
            observed_value=float(row["observed_value"]),
            measured_at=row["measured_at"],
            notes=row["notes"],
            measurement_source=_col("measurement_source") or "manual",
            contract_revision=_col("contract_revision"),
            contract_snapshot=(
                OutcomeContract.model_validate(json.loads(contract_json)) if contract_json else None
            ),
            checkpoint_kind=_col("checkpoint_kind"),
            plan_id=_col("plan_id"),
            execution_id=_col("execution_id"),
            clock_origin=_col("clock_origin"),
            clock_origin_at=_col("clock_origin_at"),
        )

    @staticmethod
    def _jira_issue_draft_from_row(row: sqlite3.Row) -> JiraIssueDraft:
        return JiraIssueDraft(
            draft_id=f"JIRA-DRAFT-{row['id']:04d}",
            problem_id=row["problem_id"],
            action_id=row["action_id"],
            execution_id=row["execution_id"],
            project_key=row["project_key"],
            issue_type=row["issue_type"],
            summary=row["summary"],
            description=row["description"],
            labels=[label for label in row["labels"].split(",") if label],
            assignee=row["assignee"],
            status=row["status"],
            created_at=row["created_at"],
        )

    @staticmethod
    def _transition_from_row(row: sqlite3.Row) -> ProblemTransitionRecord:
        return ProblemTransitionRecord(
            transition_id=f"TRN-{row['id']:04d}",
            problem_id=row["problem_id"],
            from_status=row["from_status"],
            to_status=row["to_status"],
            actor=row["actor"],
            note=row["note"],
            created_at=row["created_at"],
        )

    @staticmethod
    def _learning_conclusion_from_row(row: sqlite3.Row) -> LearningConclusionRecord:
        return LearningConclusionRecord(
            conclusion_id=row["conclusion_id"],
            problem_id=row["problem_id"],
            tenant_id=row["tenant_id"],
            learning_status=row["learning_status"],
            reviewer=row["reviewer"],
            reviewed_at=row["reviewed_at"],
            retention_expires_at=row["retention_expires_at"] or retention_expires_at(row["reviewed_at"]),
            summary=row["summary"],
            limitations=row["limitations"],
            next_step=row["next_step"],
        )

    @staticmethod
    def _closure_timeline_event(closure: ClosureRecord) -> TimelineEvent:
        return TimelineEvent(
            event_id=closure.closure_id,
            problem_id=closure.problem_id,
            event_type="closure_recorded",
            label="Closure recorded",
            detail=(
                f"Operational: {closure.operational_status.replace('_', ' ')} / "
                f"customer: {closure.customer_status.replace('_', ' ')} / "
                f"unresolved customers: {closure.unresolved_customers}"
            ),
            actor=closure.actor,
            created_at=closure.created_at,
        )

    @staticmethod
    def _transition_timeline_event(transition: ProblemTransitionRecord) -> TimelineEvent:
        return TimelineEvent(
            event_id=transition.transition_id,
            problem_id=transition.problem_id,
            event_type="status_changed",
            label=f"Status changed to {transition.to_status.value.replace('_', ' ')}",
            detail=transition.note
            or f"{transition.from_status.value.replace('_', ' ')} -> {transition.to_status.value.replace('_', ' ')}",
            actor=transition.actor,
            created_at=transition.created_at,
        )

    @staticmethod
    def _approval_timeline_event(approval: ApprovalRecord) -> TimelineEvent:
        return TimelineEvent(
            event_id=approval.decision_id,
            problem_id=approval.problem_id,
            event_type="approval_recorded",
            label=f"Action {approval.decision.value.replace('_', ' ')}",
            detail=approval.note or f"{approval.action_id} reviewed.",
            actor=approval.reviewer,
            created_at=approval.created_at,
        )

    @staticmethod
    def _execution_timeline_event(execution: ExecutionRecord) -> TimelineEvent:
        return TimelineEvent(
            event_id=execution.execution_id,
            problem_id=execution.problem_id,
            event_type="execution_created",
            label=f"Execution {execution.status.value.replace('_', ' ')}",
            detail=execution.summary,
            actor=execution.owner,
            created_at=execution.created_at,
        )

    @staticmethod
    def _jira_draft_timeline_event(draft: JiraIssueDraft) -> TimelineEvent:
        return TimelineEvent(
            event_id=draft.draft_id,
            problem_id=draft.problem_id,
            event_type="jira_draft_created",
            label="Jira draft created",
            detail=f"{draft.project_key} {draft.issue_type}: {draft.summary}",
            actor=draft.assignee,
            created_at=draft.created_at,
        )

    @staticmethod
    def _learning_timeline_event(conclusion: LearningConclusionRecord) -> TimelineEvent:
        return TimelineEvent(
            event_id=conclusion.conclusion_id,
            problem_id=conclusion.problem_id,
            event_type="learning_reviewed",
            label=f"Learning: {learning_label(conclusion.learning_status.value)}",
            detail=conclusion.summary,
            actor=conclusion.reviewer,
            created_at=conclusion.reviewed_at,
        )

    @staticmethod
    def _outcome_timeline_event(problem_id: str, row: sqlite3.Row) -> TimelineEvent:
        return TimelineEvent(
            event_id=f"OUT-{problem_id}",
            problem_id=problem_id,
            event_type="outcome_measured",
            label="Outcome measured",
            detail=f"{row['metric']} observed at {row['observed_value']}.",
            actor=None,
            created_at=row["measured_at"],
        )
