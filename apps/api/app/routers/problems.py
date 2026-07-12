"""Problem/workflow routes: problems, candidates, approvals, outcomes, learning, triage."""

from __future__ import annotations

import logging
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from langgraph.types import Command

from app.auth import UserContext, get_current_user
from app.domain.models import (
    ActionProposalUpdateRequest,
    AffectedContextExplorer,
    ApprovalDecision,
    ApprovalDecisionStatus,
    ApprovalRecord,
    CandidateDecisionStatus,
    CandidateReviewRequest,
    CandidateReviewStatus,
    ClosureRecord,
    ClosureRecordRequest,
    EmergingProblemReport,
    ExecutionRecord,
    JiraIssueDraft,
    LearningConclusionRecord,
    LearningConclusionRequest,
    LearningStatus,
    OutcomeBoard,
    OutcomeBoardItem,
    OutcomeContractProposalPreview,
    OutcomeContractUpdateRequest,
    OutcomeMeasurement,
    OutcomeSnapshot,
    ProblemCandidate,
    ProblemRecord,
    ProblemStatus,
    ProblemSummary,
    ProblemTransitionRecord,
    ProblemTransitionRequest,
    ProblemUpdateRequest,
    WorkflowState,
)
from app.rate_limit import rate_limiter
from app.rbac import Role, require_role
from app.services.common import utc_now
from app.services.context_impact import build_affected_context_explorer
from app.services.emerging import build_emerging_problem_report
from app.services.measurement_scheduler import schedule_measurements
from app.services.outcome_engine import (
    ITS_COMPARISON_METHOD,
    its_outcome_for_problem,
    propose_outcome_contract,
)
from app.services.signals import promote_candidate

logger = logging.getLogger(__name__)


def to_summary(problem: ProblemRecord) -> ProblemSummary:
    return ProblemSummary(
        problem_id=problem.problem_id,
        title=problem.title,
        journey=problem.journey,
        journey_stage=problem.journey_stage,
        owner=problem.owner,
        status=problem.status,
        impact_score=problem.impact_score or 0.0,
        impact_band=problem.impact_band or "low",
        evidence_confidence=problem.evidence_confidence,
        affected_customers=problem.affected_cohort.customers,
        affected_accounts=problem.affected_cohort.accounts,
        approval_pressure=problem.approval_pressure or "ready",
        top_action_classes=[proposal.class_ for proposal in problem.action_proposals[:3]],
        context_impact=problem.context_impact,
        journey_impact=problem.journey_impact,
    )


def build_outcome_board(
    problems: list[ProblemRecord],
    workflow_store,
    tenant_id: str | None = None,
) -> OutcomeBoard:
    items: list[OutcomeBoardItem] = []
    learning_counts = {
        LearningStatus.worked: 0,
        LearningStatus.partially_worked: 0,
        LearningStatus.did_not_work: 0,
        LearningStatus.inconclusive: 0,
        LearningStatus.measurement_invalid: 0,
    }
    for problem in problems:
        snapshot = workflow_store.outcome_snapshot(problem)
        latest_learning = workflow_store.latest_learning_conclusion(problem, tenant_id=tenant_id)
        if latest_learning is not None:
            learning_counts[latest_learning.learning_status] += 1
        items.append(
            OutcomeBoardItem(
                problem_id=problem.problem_id,
                title=problem.title,
                owner=problem.owner,
                problem_status=problem.status,
                impact_score=problem.impact_score or 0.0,
                impact_band=problem.impact_band or "low",
                metric=snapshot.metric,
                baseline=snapshot.baseline,
                success_threshold=snapshot.success_threshold,
                latest_value=snapshot.latest_value,
                outcome_status=snapshot.status,
                improvement_direction=snapshot.improvement_direction,
                latest_learning_status=(
                    latest_learning.learning_status if latest_learning is not None else None
                ),
                latest_learning_reviewed_at=(
                    latest_learning.reviewed_at if latest_learning is not None else None
                ),
                measurement_window_days=snapshot.measurement_window_days,
                comparison_method=snapshot.comparison_method,
                responsible_owner=problem.outcome_contract.responsible_owner,
            )
        )

    items = sorted(items, key=lambda item: item.impact_score, reverse=True)
    counts = {
        "not_measured": 0,
        "not_improved": 0,
        "improving": 0,
        "target_met": 0,
    }
    for item in items:
        if item.outcome_status in counts:
            counts[item.outcome_status] += 1

    return OutcomeBoard(
        total=len(items),
        not_measured=counts["not_measured"],
        not_improved=counts["not_improved"],
        improving=counts["improving"],
        target_met=counts["target_met"],
        learning_worked=learning_counts[LearningStatus.worked],
        learning_partially_worked=learning_counts[LearningStatus.partially_worked],
        learning_did_not_work=learning_counts[LearningStatus.did_not_work],
        learning_inconclusive=learning_counts[LearningStatus.inconclusive],
        learning_measurement_invalid=learning_counts[LearningStatus.measurement_invalid],
        items=items,
    )


class TrustedWorkflowIdentity:
    def __init__(self, *, tenant_id: str, actor_id: str) -> None:
        self.tenant_id = tenant_id
        self.actor_id = actor_id


def _actor_identifier(user: UserContext) -> str:
    """Stable pseudonym for audit records, derived from the verified principal.

    JWT subs are UUIDs, and a raw UUID can trip the phone-number pattern in
    pseudonymized_identifier (any digit/hyphen run >= 9 chars matches), so JWT
    actors are recorded as user-<first 8 hex> — too short for that pattern,
    still correlatable to the Supabase user. Short ids (dev-user, api-key:N)
    pass through unchanged.
    """
    if len(user.user_id) >= 20:
        return f"user-{user.user_id[:8]}"
    return user.user_id


def require_trusted_workflow_identity(
    user: UserContext = Depends(get_current_user),
) -> TrustedWorkflowIdentity:
    """Tenant + actor for workflow audit records, bound to the verified JWT /
    API key (review #30/#31): the old x-tenant-id/x-actor-id client headers
    were spoofable and are now ignored entirely."""
    return TrustedWorkflowIdentity(
        tenant_id=user.tenant_setting,
        actor_id=_actor_identifier(user),
    )


def build_router(
    *,
    active_problem_store,
    workflow_store,
    signal_store,
    context_store,
    connector_config_store,
    telemetry_store,
    measurement_plan_store,
    require_problem,
    enrich_problem_for_response,
    list_enriched_problems,
    current_candidates,
    require_candidate,
    triage_graph,
    learning_store_factory,
) -> APIRouter:
    router = APIRouter()
    read_dep = Depends(require_role(Role.viewer))

    @router.get("/problems", response_model=list[ProblemSummary], dependencies=[read_dep])
    def list_problems(status: ProblemStatus | None = None) -> list[ProblemSummary]:
        current_problems = list_enriched_problems()
        if status is not None:
            current_problems = [
                problem for problem in current_problems if problem.status == status
            ]

        return sorted(
            [to_summary(problem) for problem in current_problems],
            key=lambda problem: problem.impact_score,
            reverse=True,
        )

    @router.get("/problems/{problem_id}", response_model=ProblemRecord, dependencies=[read_dep])
    def get_problem(problem_id: str) -> ProblemRecord:
        problem = enrich_problem_for_response(require_problem(problem_id))
        # time-to-first-insight numerator: first insight viewed after first ingest.
        telemetry_store.record("insight_viewed", entity_id=problem_id)
        return problem

    @router.get(
        "/problems/{problem_id}/affected-context",
        response_model=AffectedContextExplorer,
        dependencies=[read_dep],
    )
    def get_affected_context(problem_id: str) -> AffectedContextExplorer:
        return build_affected_context_explorer(
            require_problem(problem_id),
            context_store.list_context(),
        )

    @router.patch("/problems/{problem_id}", response_model=ProblemRecord, dependencies=[Depends(require_role(Role.editor))])
    def update_problem(problem_id: str, update: ProblemUpdateRequest) -> ProblemRecord:
        require_problem(problem_id)
        updated_problem = active_problem_store.update_problem(problem_id, update)
        if updated_problem is None:
            raise HTTPException(
                status_code=409,
                detail="Only promoted draft problems can be edited",
            )

        return enrich_problem_for_response(updated_problem)

    @router.patch("/problems/{problem_id}/actions/{action_id}", response_model=ProblemRecord, dependencies=[Depends(require_role(Role.editor))])
    def update_action_proposal(
        problem_id: str,
        action_id: str,
        update: ActionProposalUpdateRequest,
    ) -> ProblemRecord:
        problem = require_problem(problem_id)
        action = next(
            (proposal for proposal in problem.action_proposals if proposal.action_id == action_id),
            None,
        )
        if action is None:
            raise HTTPException(status_code=404, detail="Action proposal not found")

        updated_problem = active_problem_store.update_action_proposal(
            problem_id,
            action_id,
            update,
        )
        if updated_problem is None:
            raise HTTPException(
                status_code=409,
                detail="Only promoted draft problem actions can be edited",
            )

        return enrich_problem_for_response(updated_problem)

    @router.get(
        "/problems/{problem_id}/outcome-contract/proposal",
        response_model=OutcomeContractProposalPreview,
        dependencies=[read_dep],
    )
    def get_outcome_contract_proposal(problem_id: str) -> OutcomeContractProposalPreview:
        """Preview what approving with accept_proposed_contract=True will apply."""
        problem = require_problem(problem_id)
        proposed = propose_outcome_contract(
            problem, signal_store.list_signals(), now=utc_now()
        )
        return OutcomeContractProposalPreview(
            problem_id=problem_id,
            current=problem.outcome_contract,
            proposed=proposed,
            is_promotion_default=(
                proposed is not None
                and problem.outcome_contract.comparison_method != ITS_COMPARISON_METHOD
            ),
        )

    @router.patch(
        "/problems/{problem_id}/outcome-contract",
        response_model=ProblemRecord,
        dependencies=[Depends(require_role(Role.editor))],
    )
    def update_outcome_contract(
        problem_id: str,
        update: OutcomeContractUpdateRequest,
    ) -> ProblemRecord:
        require_problem(problem_id)
        updated_problem = active_problem_store.update_outcome_contract(problem_id, update)
        if updated_problem is None:
            raise HTTPException(
                status_code=409,
                detail="Only promoted draft problem contracts can be edited",
            )

        return enrich_problem_for_response(updated_problem)

    @router.post("/problems/{problem_id}/transitions", response_model=ProblemTransitionRecord, dependencies=[Depends(require_role(Role.editor))])
    def transition_problem(
        problem_id: str,
        transition: ProblemTransitionRequest,
    ) -> ProblemTransitionRecord:
        problem = require_problem(problem_id)
        if problem.status == transition.target_status:
            raise HTTPException(status_code=409, detail="Problem is already in the target status")

        updated_problem = active_problem_store.transition_problem_status(
            problem_id,
            transition.target_status,
        )
        if updated_problem is None:
            raise HTTPException(
                status_code=409,
                detail="Only promoted draft problems can change lifecycle status",
            )

        return workflow_store.record_transition(
            problem=problem,
            target_status=transition.target_status,
            actor=transition.actor,
            note=transition.note,
        )

    @router.get("/problem-candidates", response_model=list[ProblemCandidate], dependencies=[read_dep])
    def list_problem_candidates() -> list[ProblemCandidate]:
        return current_candidates()

    @router.get("/emerging-problems", response_model=EmergingProblemReport, dependencies=[read_dep])
    def list_emerging_problems() -> EmergingProblemReport:
        return build_emerging_problem_report(current_candidates())

    @router.post("/problem-candidates/{candidate_id}/promote", response_model=ProblemRecord, dependencies=[Depends(require_role(Role.editor))])
    def promote_problem_candidate(candidate_id: str) -> ProblemRecord:
        candidate = require_candidate(candidate_id)
        problem = promote_candidate(candidate)
        existing_problem = active_problem_store.get_problem(problem.problem_id)
        if existing_problem is not None:
            return enrich_problem_for_response(existing_problem)

        return enrich_problem_for_response(active_problem_store.upsert_problem(problem))

    @router.post("/problem-candidates/{candidate_id}/accept", response_model=ProblemRecord, dependencies=[Depends(require_role(Role.editor))])
    def accept_problem_candidate(
        candidate_id: str,
        request: CandidateReviewRequest,
    ) -> ProblemRecord:
        candidate = require_candidate(candidate_id)
        if candidate.review_status == CandidateReviewStatus.rejected:
            raise HTTPException(status_code=409, detail="Candidate has already been rejected")
        if candidate.duplicate_problem_id is not None:
            raise HTTPException(
                status_code=409,
                detail=f"Candidate duplicates existing problem {candidate.duplicate_problem_id}",
            )

        problem = promote_candidate(candidate)
        promoted_problem = active_problem_store.upsert_problem(problem)
        signal_store.record_candidate_decision(
            candidate_id=candidate.candidate_id,
            decision=CandidateDecisionStatus.accepted,
            reviewer=request.reviewer,
            note=request.note,
        )
        return enrich_problem_for_response(promoted_problem)

    @router.post("/problem-candidates/{candidate_id}/reject", response_model=ProblemCandidate, dependencies=[Depends(require_role(Role.editor))])
    def reject_problem_candidate(
        candidate_id: str,
        request: CandidateReviewRequest,
    ) -> ProblemCandidate:
        candidate = require_candidate(candidate_id)
        if candidate.review_status == CandidateReviewStatus.accepted:
            raise HTTPException(status_code=409, detail="Candidate has already been accepted")

        signal_store.record_candidate_decision(
            candidate_id=candidate.candidate_id,
            decision=CandidateDecisionStatus.rejected,
            reviewer=request.reviewer,
            note=request.note,
        )
        return require_candidate(candidate_id)

    @router.post("/problems/{problem_id}/approvals", response_model=ApprovalRecord, dependencies=[Depends(require_role(Role.editor))])
    def record_approval(problem_id: str, decision: ApprovalDecision) -> ApprovalRecord:
        problem = require_problem(problem_id)
        record = workflow_store.record_approval(problem=problem, decision=decision)
        # approval-cycle-time denominator + decision mix.
        telemetry_store.record(
            "approval_recorded",
            entity_id=decision.action_id,
            metadata={"problem_id": problem_id, "decision": record.decision.value},
        )

        # Real action push: an approved action fires its destination connector
        # (Jira/Slack) when one is configured; otherwise the draft stands. Push
        # failures are recorded on the execution and never fail the approval.
        if record.decision == ApprovalDecisionStatus.approved:
            from app.services.action_push import push_approved_action
            from app.services.workflow import find_action

            # W4 zero-input closure: upgrade the promotion-default contract to
            # the auto-proposed one (trailing-28d baseline, 30d window, ITS
            # scoring) unless the reviewer opted out. Best-effort — the
            # approval is already recorded and must never fail here.
            if (
                decision.accept_proposed_contract
                and problem.outcome_contract.comparison_method != ITS_COMPARISON_METHOD
            ):
                try:
                    proposed = propose_outcome_contract(
                        problem, signal_store.list_signals(), now=utc_now()
                    )
                    upgraded = (
                        active_problem_store.update_outcome_contract(
                            problem_id,
                            OutcomeContractUpdateRequest(**proposed.model_dump()),
                        )
                        if proposed is not None
                        else None
                    )
                    if proposed is not None and upgraded is not None:
                        telemetry_store.record(
                            "contract_proposed",
                            entity_id=problem_id,
                            metadata={
                                "old_baseline": problem.outcome_contract.baseline,
                                "new_baseline": proposed.baseline,
                                "old_window_days": problem.outcome_contract.measurement_window_days,
                                "new_window_days": proposed.measurement_window_days,
                                "comparison_method": proposed.comparison_method,
                            },
                        )
                        # schedule_measurements below reads the upgraded window.
                        problem = upgraded
                except Exception:  # noqa: BLE001 — contract upgrade is best-effort
                    logger.exception("Contract proposal failed for %s", problem_id)

            execution = next(
                (
                    e
                    for e in reversed(workflow_store.list_executions())
                    if e.problem_id == problem_id and e.action_id == decision.action_id
                ),
                None,
            )
            if execution is not None:
                try:
                    pushed = push_approved_action(
                        problem=problem,
                        action=find_action(problem, decision.action_id),
                        execution=execution,
                        config_store=connector_config_store,
                        workflow_store=workflow_store,
                    )
                    if pushed.status.value in ("pushed", "push_failed"):
                        telemetry_store.record(
                            f"action_{pushed.status.value}",
                            entity_id=pushed.execution_id,
                            metadata={
                                "problem_id": problem_id,
                                "destination": pushed.destination,
                                "external_ref": pushed.external_ref,
                            },
                        )
                except Exception:  # noqa: BLE001 — approval already recorded; push is best-effort
                    logger.exception("Action push failed unexpectedly for %s", decision.action_id)

                # Close-the-loop clock starts now: schedule T+7 / T+window
                # re-measurement checkpoints for this problem's outcome contract.
                try:
                    kinds = schedule_measurements(
                        measurement_plan_store,
                        problem=problem,
                        execution_id=execution.execution_id,
                        executed_at=execution.created_at,
                    )
                    telemetry_store.record(
                        "measurement_scheduled",
                        entity_id=problem_id,
                        metadata={"kinds": kinds, "execution_id": execution.execution_id},
                    )
                except Exception:  # noqa: BLE001 — scheduling is best-effort too
                    logger.exception("Measurement scheduling failed for %s", problem_id)

        return record

    @router.get("/problems/{problem_id}/evidence-pack", dependencies=[read_dep])
    def export_evidence_pack(problem_id: str, format: str = "html"):
        """Audit-ready export of one problem: evidence -> actions -> policy trail ->
        approvals -> executions -> outcome -> learning. HTML (print-to-PDF) or JSON."""
        from fastapi.responses import HTMLResponse

        from app.services.evidence_pack import build_evidence_pack, render_evidence_pack_html

        problem = enrich_problem_for_response(require_problem(problem_id))
        state = workflow_store.state_for_problem(problem)
        pack = build_evidence_pack(problem, state, measurement_plan_store.list_plans())
        telemetry_store.record(
            "evidence_pack_exported", entity_id=problem_id, metadata={"format": format}
        )
        if format == "json":
            return pack
        return HTMLResponse(render_evidence_pack_html(pack))

    @router.get("/problems/{problem_id}/workflow", response_model=WorkflowState, dependencies=[read_dep])
    def get_workflow_state(
        problem_id: str,
        user: UserContext = Depends(get_current_user),  # noqa: B008
    ) -> WorkflowState:
        problem = require_problem(problem_id)
        return workflow_store.state_for_problem(problem, tenant_id=user.tenant_setting)

    @router.post("/problems/{problem_id}/outcomes", response_model=OutcomeMeasurement, dependencies=[Depends(require_role(Role.editor))])
    def record_outcome(problem_id: str, measurement: OutcomeMeasurement) -> OutcomeMeasurement:
        problem = require_problem(problem_id)
        if measurement.problem_id != problem_id:
            raise HTTPException(status_code=422, detail="Outcome problem_id must match the route")

        recorded = workflow_store.record_outcome(problem=problem, measurement=measurement)
        # real_data_source flag: manual API entry, NOT the simulated eval path —
        # simulated and real outcome data must never mix in a metrics chart.
        telemetry_store.record(
            "outcome_recorded",
            entity_id=problem_id,
            metadata={"source": "api", "real_data_source": True},
        )
        return recorded

    @router.post("/problems/{problem_id}/closure", response_model=ClosureRecord, dependencies=[Depends(require_role(Role.editor))])
    def record_closure(
        problem_id: str,
        closure: ClosureRecordRequest,
        identity: TrustedWorkflowIdentity = Depends(require_trusted_workflow_identity),
    ) -> ClosureRecord:
        problem = require_problem(problem_id)
        return workflow_store.record_closure(
            problem=problem,
            closure=closure,
            tenant_id=identity.tenant_id,
            actor=identity.actor_id,
        )

    @router.post(
        "/problems/{problem_id}/learning-conclusions",
        response_model=LearningConclusionRecord,
        dependencies=[Depends(require_role(Role.editor))],
    )
    def record_outcome_learning(
        problem_id: str,
        conclusion: LearningConclusionRequest,
        identity: TrustedWorkflowIdentity = Depends(require_trusted_workflow_identity),
    ) -> LearningConclusionRecord:
        problem = require_problem(problem_id)
        if workflow_store.outcome_snapshot(problem).status == "not_measured":
            raise HTTPException(
                status_code=409,
                detail="Outcome must be measured before recording a learning conclusion",
            )

        learning = workflow_store.record_learning_conclusion(
            problem=problem,
            conclusion=conclusion,
            tenant_id=identity.tenant_id,
            actor=identity.actor_id,
        )
        # learning-reuse-rate numerator source: every reviewed conclusion is a
        # candidate for retrieval into future proposals.
        telemetry_store.record(
            "learning_recorded",
            entity_id=problem_id,
            metadata={"status": conclusion.learning_status.value},
        )
        return learning

    @router.get("/problems/{problem_id}/outcome", response_model=OutcomeSnapshot, dependencies=[read_dep])
    def get_outcome_snapshot(problem_id: str) -> OutcomeSnapshot:
        problem = require_problem(problem_id)
        snapshot = workflow_store.outcome_snapshot(problem)
        # W4 honest quasi-experimental read: ITS segmented regression on the
        # raw signal series, anchored at the first approved action's execution.
        # Read-time only — the scheduler/plpgsql measurement path is unchanged.
        approved_action_ids = {
            approval.action_id
            for approval in workflow_store.list_approvals()
            if approval.problem_id == problem_id
            and approval.decision == ApprovalDecisionStatus.approved
        }
        executed_at = min(
            (
                execution.created_at
                for execution in workflow_store.list_executions()
                if execution.problem_id == problem_id
                and execution.action_id in approved_action_ids
            ),
            default=None,
        )
        if executed_at is not None:
            snapshot.its = its_outcome_for_problem(
                problem,
                signal_store.list_signals(),
                executed_at=executed_at,
                now=utc_now(),
            )
        return snapshot

    @router.get("/outcome-board", response_model=OutcomeBoard, dependencies=[read_dep])
    def get_outcome_board(
        user: UserContext = Depends(get_current_user),  # noqa: B008
    ) -> OutcomeBoard:
        return build_outcome_board(
            list_enriched_problems(), workflow_store, tenant_id=user.tenant_setting
        )

    @router.get("/approvals", response_model=list[ApprovalRecord], dependencies=[read_dep])
    def list_approvals() -> list[ApprovalRecord]:
        return workflow_store.list_approvals()

    @router.get("/executions", response_model=list[ExecutionRecord], dependencies=[read_dep])
    def list_executions() -> list[ExecutionRecord]:
        return workflow_store.list_executions()

    @router.get("/jira-drafts", response_model=list[JiraIssueDraft], dependencies=[read_dep])
    def list_jira_drafts() -> list[JiraIssueDraft]:
        return workflow_store.list_jira_issue_drafts()

    @router.post("/triage/run", dependencies=[Depends(require_role(Role.editor)), Depends(rate_limiter)])
    def run_triage_pipeline(body: dict, user: UserContext = Depends(get_current_user)) -> dict:  # noqa: B008
        """Run the LangGraph triage pipeline on signals.

        Runs ingest -> enrich -> classify -> synthesize -> governance -> approval.
        When consequential actions require human approval the graph PAUSES at the
        approval interrupt and this returns status="awaiting_approval" with a
        thread_id; resume via POST /triage/resume to run action -> measure -> learn.
        """
        raw_signals = body.get("signals", [])
        if not raw_signals:
            # If no signals provided, pull from the signal store
            raw_signals = [
                {
                    "signal_id": s.signal_id,
                    "id": s.signal_id,
                    "feedback_text": s.feedback_text,
                    "text": s.feedback_text,
                    "signal_type": "qualitative",
                    "source": s.source,
                    "customer_id": s.customer_id,
                    "account_id": s.account_id,
                    "timestamp": s.timestamp,
                    "contact_count": 1,
                }
                for s in signal_store.list_signals()
            ]

        if not raw_signals:
            return {"insights": [], "status": "empty", "errors": ["No signals to process"]}

        # Gather connector configs for the action node
        conn_configs: dict[str, dict] = {}
        for cc in connector_config_store.list_configs():
            if cc.is_active:
                conn_configs[cc.connector_type] = cc.config

        # Optional context data for 8-factor severity
        context_data = body.get("context_data")

        # Past learnings inform synthesis (outcome-grounded self-improvement loop).
        # ponytail: best-effort — synthesis works fine without learnings, so a
        # store/DB hiccup degrades gracefully rather than failing the triage run.
        try:
            learnings = learning_store_factory().load(workspace_id=user.workspace_id)
        except Exception:
            learnings = []

        thread_id = f"triage-{uuid4().hex}"
        config = {"configurable": {"thread_id": thread_id}}

        result = triage_graph.invoke(
            {
                "signals": raw_signals,
                "connector_configs": conn_configs,
                "context_data": context_data,
                "learnings": learnings,
            },
            config=config,
        )

        # A non-empty `next` means the graph paused at the approval interrupt.
        if triage_graph.get_state(config).next:
            return {
                "status": "awaiting_approval",
                "thread_id": thread_id,
                "insights": result.get("insights", []),
                "enriched_count": result.get("enrichment_count", 0),
                "errors": result.get("errors", []),
            }

        # Ran to completion (no consequential actions / approval skipped).
        telemetry_store.record(
            "triage_completed",
            metadata={
                "status": result.get("status", "unknown"),
                "insights": len(result.get("insights", [])),
                "enriched": result.get("enrichment_count", 0),
            },
        )
        return {
            "insights": result.get("insights", []),
            "enriched_count": result.get("enrichment_count", 0),
            "status": result.get("status", "unknown"),
            "errors": result.get("errors", []),
            "thread_id": thread_id,
        }

    @router.post("/triage/resume", dependencies=[Depends(require_role(Role.editor)), Depends(rate_limiter)])
    def resume_triage_pipeline(body: dict, user: UserContext = Depends(get_current_user)) -> dict:  # noqa: B008
        """Resume a paused triage run after human approval.

        Input: { "thread_id": "...", "decision": "approved" | "rejected" }. On
        approval the graph runs action -> measure -> learn (closing the outcome loop).
        """
        thread_id = body.get("thread_id")
        decision = (body.get("decision") or "approved").strip().lower()
        if not thread_id:
            raise HTTPException(status_code=422, detail="thread_id is required")
        if decision not in ("approved", "rejected"):
            raise HTTPException(status_code=422, detail="decision must be 'approved' or 'rejected'")

        config = {"configurable": {"thread_id": thread_id}}
        if not triage_graph.get_state(config).next:
            raise HTTPException(
                status_code=404,
                detail="No triage run awaiting approval for that thread_id (expired or already resumed)",
            )

        result = triage_graph.invoke(Command(resume=decision), config=config)
        return {
            "status": result.get("status", "unknown"),
            "approval_decision": result.get("approval_decision"),
            "approved_insights": result.get("approved_insights", []),
            "action_results": result.get("action_results", []),
            "outcome": result.get("outcome"),
            "learning": result.get("learning"),
            "errors": result.get("errors", []),
        }

    return router
