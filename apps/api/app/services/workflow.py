from __future__ import annotations

import json
import sqlite3
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
    LearningConclusionRequest,
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
    ordered_decisions: list[tuple[str, str]],
    *,
    decision: ApprovalDecision,
) -> set[str]:
    """Latest-decision-per-action approval set + repeat-approval guard.

    Approvals are append-only, so the dependency gate must honor the LATEST
    decision per action (a later rejection revokes an earlier approval), and
    re-approving an already-approved action must not mint a duplicate
    execution/Jira draft.
    """
    latest: dict[str, str] = {}
    for action_id, decision_value in ordered_decisions:
        latest[action_id] = decision_value
    if (
        decision.decision == ApprovalDecisionStatus.approved
        and latest.get(decision.action_id) == ApprovalDecisionStatus.approved.value
    ):
        raise HTTPException(status_code=409, detail="Action is already approved")
    return {
        action_id
        for action_id, decision_value in latest.items()
        if decision_value == ApprovalDecisionStatus.approved.value
    }


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


def outcome_direction(*, baseline: float, success_threshold: float) -> str:
    return "increase" if success_threshold >= baseline else "decrease"


def outcome_status(
    *,
    baseline: float,
    success_threshold: float,
    latest_value: float | None,
) -> str:
    if latest_value is None:
        return "not_measured"

    if outcome_direction(baseline=baseline, success_threshold=success_threshold) == "increase":
        if latest_value >= success_threshold:
            return "target_met"
        if latest_value > baseline:
            return "improving"
        return "not_improved"

    if latest_value <= success_threshold:
        return "target_met"
    if latest_value < baseline:
        return "improving"
    return "not_improved"


def learning_label(status: str) -> str:
    return status.replace("_", " ")


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
        self._approvals: list[ApprovalRecord] = []
        self._executions: list[ExecutionRecord] = []
        self._jira_issue_drafts: list[JiraIssueDraft] = []
        self._outcomes: dict[str, OutcomeMeasurement] = {}
        self._transitions: list[ProblemTransitionRecord] = []
        self._learning_conclusions: list[LearningConclusionRecord] = []
        self._closure_records: list[ClosureRecord] = []

    def list_approvals(self) -> list[ApprovalRecord]:
        return self._approvals

    def list_executions(self) -> list[ExecutionRecord]:
        return self._executions

    def update_execution(
        self,
        execution_id: str,
        *,
        status: ExecutionStatus,
        external_ref: str | None = None,
        detail: str | None = None,
    ) -> ExecutionRecord:
        for index, execution in enumerate(self._executions):
            if execution.execution_id == execution_id:
                updated = execution.model_copy(
                    update={"status": status, "external_ref": external_ref, "detail": detail}
                )
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
    ) -> ApprovalRecord:
        action = find_action(problem, decision.action_id)
        approved_action_ids = resolve_approval_state(
            [
                (approval.action_id, approval.decision.value)
                for approval in self._approvals
                if approval.problem_id == problem.problem_id
            ],
            decision=decision,
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
        )
        self._approvals.append(record)

        if decision.decision == ApprovalDecisionStatus.approved:
            execution = ExecutionRecord(
                execution_id=f"EXE-{next(self._execution_ids):04d}",
                problem_id=problem.problem_id,
                action_id=action.action_id,
                destination=action.destination,
                status=ExecutionStatus.draft_created,
                owner=action.owner,
                summary=f"Draft {action.destination} execution created for {action.class_.value}.",
                created_at=record.created_at,
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

    def outcome_snapshot(self, problem: ProblemRecord) -> OutcomeSnapshot:
        contract = problem.outcome_contract
        measurement = self._outcomes.get(problem.problem_id)
        latest_value = None if measurement is None else measurement.observed_value

        return OutcomeSnapshot(
            problem_id=problem.problem_id,
            metric=contract.primary_metric,
            baseline=contract.baseline,
            success_threshold=contract.success_threshold,
            latest_value=latest_value,
            status=outcome_status(
                baseline=contract.baseline,
                success_threshold=contract.success_threshold,
                latest_value=latest_value,
            ),
            improvement_direction=outcome_direction(
                baseline=contract.baseline,
                success_threshold=contract.success_threshold,
            ),
            measurement_window_days=contract.measurement_window_days,
            comparison_method=contract.comparison_method,
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
                detail TEXT
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
                notes TEXT
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
        self._ensure_column("learning_conclusions", "tenant_id", "TEXT NOT NULL DEFAULT 'legacy'")
        self._ensure_column("learning_conclusions", "retention_expires_at", "TEXT NOT NULL DEFAULT ''")
        self._ensure_column("executions", "external_ref", "TEXT")
        self._ensure_column("executions", "detail", "TEXT")
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

    def update_execution(
        self,
        execution_id: str,
        *,
        status: ExecutionStatus,
        external_ref: str | None = None,
        detail: str | None = None,
    ) -> ExecutionRecord:
        # execution_id is derived as EXE-{rowid:04d}; map back to the numeric row id.
        try:
            row_id = int(execution_id.removeprefix("EXE-"))
        except ValueError as exc:
            raise HTTPException(status_code=404, detail="Execution not found") from exc

        cursor = self._connection.execute(
            "UPDATE executions SET status = ?, external_ref = ?, detail = ? WHERE id = ?",
            (status.value, external_ref, detail, row_id),
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
    ) -> ApprovalRecord:
        action = find_action(problem, decision.action_id)
        decision_rows = self._connection.execute(
            "SELECT action_id, decision FROM approvals WHERE problem_id = ? ORDER BY id",
            (problem.problem_id,),
        ).fetchall()
        approved_action_ids = resolve_approval_state(
            [(row["action_id"], row["decision"]) for row in decision_rows],
            decision=decision,
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
                action_diff
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
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
            ),
        )
        approval_id = cursor.lastrowid

        if decision.decision == ApprovalDecisionStatus.approved:
            execution_cursor = self._connection.execute(
                """
                INSERT INTO executions
                    (problem_id, action_id, destination, status, owner, summary, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    problem.problem_id,
                    action.action_id,
                    action.destination,
                    ExecutionStatus.draft_created.value,
                    action.owner,
                    f"Draft {action.destination} execution created for {action.class_.value}.",
                    created_at,
                ),
            )
            if action.destination == "jira":
                execution_id = f"EXE-{execution_cursor.lastrowid:04d}"
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
        return self._approval_from_row(row)

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
        self._connection.execute(
            """
            INSERT INTO outcomes (problem_id, metric, observed_value, measured_at, notes)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(problem_id) DO UPDATE SET
                metric = excluded.metric,
                observed_value = excluded.observed_value,
                measured_at = excluded.measured_at,
                notes = excluded.notes
            """,
            (
                measurement.problem_id,
                measurement.metric,
                measurement.observed_value,
                measurement.measured_at,
                measurement.notes,
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

    def outcome_snapshot(self, problem: ProblemRecord) -> OutcomeSnapshot:
        contract = problem.outcome_contract
        row = self._connection.execute(
            "SELECT * FROM outcomes WHERE problem_id = ?",
            (problem.problem_id,),
        ).fetchone()

        latest_value = None if row is None else float(row["observed_value"])

        return OutcomeSnapshot(
            problem_id=problem.problem_id,
            metric=contract.primary_metric,
            baseline=contract.baseline,
            success_threshold=contract.success_threshold,
            latest_value=latest_value,
            status=outcome_status(
                baseline=contract.baseline,
                success_threshold=contract.success_threshold,
                latest_value=latest_value,
            ),
            improvement_direction=outcome_direction(
                baseline=contract.baseline,
                success_threshold=contract.success_threshold,
            ),
            measurement_window_days=contract.measurement_window_days,
            comparison_method=contract.comparison_method,
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
