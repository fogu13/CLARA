"""Problem/workflow routes: problems, candidates, approvals, outcomes, learning, triage."""

from __future__ import annotations

import logging
from collections import defaultdict
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from langgraph.types import Command

from app import auth
from app.auth import UserContext, get_current_user
from app.domain.models import (
    ActionProposal,
    ActionProposalUpdateRequest,
    SignalRecord,
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
    ExecutionStatus,
    ImplementationRecordRequest,
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
    OwnerRollup,
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
from app.services.learning_engine import learning_from_problem_conclusion, with_decay
from app.services.measurement_scheduler import schedule_measurements
from app.services.outcome_engine import (
    ITS_COMPARISON_METHOD,
    detectability_note,
    evidence_grade,
    intervention_anchor,
    its_outcome_for_problem,
    loop_verdict,
    propose_outcome_contract,
    resolution_score,
)
from app.services.problems import outcome_contract_changes
from app.services.routing import resolve_owner_route
from app.services.signals import promote_candidate, theme_candidate_id
from app.services.works_council import strip_redaction_sentinels

logger = logging.getLogger(__name__)


def is_overdue(due_at: str | None, status: ProblemStatus | str, now: str | None = None) -> bool:
    """A problem is overdue once its resolution due date has passed and it is
    not resolved. Unparseable or missing due dates are never overdue (honest
    default: no deadline was set)."""
    if not due_at or str(getattr(status, "value", status)) == ProblemStatus.resolved.value:
        return False
    try:
        due = datetime.fromisoformat(due_at.replace("Z", "+00:00"))
        current = datetime.fromisoformat((now or utc_now()).replace("Z", "+00:00"))
    except ValueError:
        return False
    if due.tzinfo is None:
        due = due.replace(tzinfo=UTC)
    if current.tzinfo is None:
        current = current.replace(tzinfo=UTC)
    return due < current


def to_summary(problem: ProblemRecord, *, now: str | None = None) -> ProblemSummary:
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
        due_at=problem.due_at,
        overdue=is_overdue(problem.due_at, problem.status, now),
        origin=problem.origin,
        theme_tag=problem.theme_tag,
    )


def build_outcome_board(
    problems: list[ProblemRecord],
    workflow_store,
    tenant_id: str | None = None,
    plans: list[dict] | None = None,
    now: str | None = None,
) -> OutcomeBoard:
    items: list[OutcomeBoardItem] = []
    plans_by_problem: dict[str, list[dict]] = defaultdict(list)
    for plan in plans or []:
        plans_by_problem[str(plan.get("problem_id"))].append(plan)
    loop_closed = 0
    fix_did_not_land = 0
    overdue_count = 0
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
        verdict, _note = loop_verdict(
            outcome_status=snapshot.status,
            plans=plans_by_problem.get(problem.problem_id, []),
            measurement_source=snapshot.measurement_source,
            checkpoint_kind=snapshot.checkpoint_kind,
        )
        if verdict == "loop_closed":
            loop_closed += 1
        elif verdict == "fix_did_not_land":
            fix_did_not_land += 1
        overdue = is_overdue(problem.due_at, problem.status, now)
        if overdue:
            overdue_count += 1
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
                measurement_source=snapshot.measurement_source,
                evidence_grade=snapshot.evidence_grade,
                guardrails=snapshot.guardrails,
                loop_verdict=verdict,
                due_at=problem.due_at,
                overdue=overdue,
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

    # Leadership view: where problems concentrate, per owning team.
    rollups: dict[str, OwnerRollup] = {}
    for item in items:
        rollup = rollups.get(item.owner)
        if rollup is None:
            rollup = OwnerRollup(
                owner=item.owner, problems=0, open=0, overdue=0, blocked=0, loop_closed=0, fix_did_not_land=0
            )
            rollups[item.owner] = rollup
        rollup.problems += 1
        if item.problem_status != ProblemStatus.resolved:
            rollup.open += 1
        if item.overdue:
            rollup.overdue += 1
        if item.problem_status == ProblemStatus.blocked_by_policy:
            rollup.blocked += 1
        if item.loop_verdict == "loop_closed":
            rollup.loop_closed += 1
        elif item.loop_verdict == "fix_did_not_land":
            rollup.fix_did_not_land += 1
    by_owner = sorted(rollups.values(), key=lambda r: (r.open, r.overdue, r.problems), reverse=True)

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
        loop_closed=loop_closed,
        fix_did_not_land=fix_did_not_land,
        overdue=overdue_count,
        by_owner=by_owner,
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
    workspace_store,
    require_problem,
    enrich_problem_for_response,
    list_enriched_problems,
    current_candidates,
    require_candidate,
    triage_graph,
    learning_store_factory,
    taxonomy_store=None,
) -> APIRouter:
    router = APIRouter()
    read_dep = Depends(require_role(Role.viewer))

    def _finalize_promotion(problem: ProblemRecord, workspace_id: int) -> ProblemRecord:
        """Apply workspace policy to a freshly promoted draft: the resolution
        due date (SLA) and the team route for its stage/theme. Pure overlay on
        the promotion output; seed problems never pass through here."""
        settings = workspace_store.get(workspace_id)
        due_at = (
            datetime.now(UTC) + timedelta(days=settings.resolution_sla_days)
        ).isoformat().replace("+00:00", "Z")
        updates: dict[str, object] = {"due_at": due_at}
        route = resolve_owner_route(
            settings.owner_routes, problem.journey_stage, problem.theme_tag
        )
        if route is not None:
            updates["owner"] = route.owner
            routed_actions: list[ActionProposal] = []
            for action in problem.action_proposals:
                if action.class_.value != "structural":
                    routed_actions.append(action)
                    continue
                payload = action.model_dump(by_alias=True)
                payload["owner"] = route.owner
                if route.destination:
                    payload["destination"] = route.destination
                routed_actions.append(ActionProposal.model_validate(payload))
            updates["action_proposals"] = routed_actions
            updates["outcome_contract"] = problem.outcome_contract.model_copy(
                update={"responsible_owner": route.owner}
            )
        return problem.model_copy(update=updates)

    @router.get("/problems", response_model=list[ProblemSummary], dependencies=[read_dep])
    def list_problems(
        status: ProblemStatus | None = None,
        owner: str | None = None,
        overdue: bool | None = None,
    ) -> list[ProblemSummary]:
        """Action Queue summaries. ``owner`` narrows to one team's problems (the
        pitch's "every team sees what it can act on"); ``overdue`` keeps only
        problems past (or within) their resolution due date."""
        current_problems = list_enriched_problems()
        if owner is not None:
            wanted = owner.strip().lower().replace("_", " ")
            current_problems = [
                problem
                for problem in current_problems
                if problem.owner.strip().lower().replace("_", " ") == wanted
            ]
        if status is not None:
            current_problems = [
                problem for problem in current_problems if problem.status == status
            ]

        now = utc_now()
        summaries = [to_summary(problem, now=now) for problem in current_problems]
        if overdue is not None:
            summaries = [summary for summary in summaries if summary.overdue == overdue]
        return sorted(summaries, key=lambda problem: problem.impact_score, reverse=True)

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
        update = strip_redaction_sentinels(update)
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

        # An approval signs one revision of the action. Editing the approved
        # revision in place would let a retry dispatch text nobody approved
        # under the human-review stamp, so the approval must be revoked first
        # (append-only trail: a rejection, then edit, then re-approve).
        decisions = sorted(
            (
                approval
                for approval in workflow_store.list_approvals()
                if approval.problem_id == problem_id and approval.action_id == action_id
            ),
            key=lambda approval: (approval.created_at, approval.decision_id),
        )
        if decisions and decisions[-1].decision == ApprovalDecisionStatus.approved:
            raise HTTPException(
                status_code=409,
                detail="Action is approved; record a rejection first, then edit and re-approve.",
            )

        updated_problem = active_problem_store.update_action_proposal(
            problem_id,
            action_id,
            strip_redaction_sentinels(update),
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
            detectability_note=(
                detectability_note(
                    baseline_rate=proposed.baseline,
                    window_days=proposed.measurement_window_days,
                )
                if proposed is not None
                else None
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
        user: UserContext = Depends(get_current_user),  # noqa: B008
    ) -> ProblemRecord:
        """Amend the outcome contract. Every real change is a new contract
        revision (who / when / why) and is recorded as contract_amended
        telemetry with the field diff; an observation already on record keeps
        the status it earned under the revision it was scored against."""
        problem = require_problem(problem_id)
        update = strip_redaction_sentinels(update)
        had_measurement = workflow_store.outcome_snapshot(problem).status != "not_measured"
        if (
            update.primary_metric
            and update.primary_metric != problem.outcome_contract.primary_metric
            and had_measurement
        ):
            raise HTTPException(
                status_code=409,
                detail="Cannot change the contract metric after an outcome was recorded against it",
            )
        term_fields_set = update.model_fields_set - {"amendment_note"}
        if term_fields_set and update.comparison_method is None:
            # An explicit edit upgrades the method to ITS unless the caller
            # says otherwise — and marks the contract as deliberately authored,
            # so the next approval's auto-proposal will not silently overwrite it.
            update = update.model_copy(update={"comparison_method": ITS_COMPARISON_METHOD})
        updated_problem = active_problem_store.update_outcome_contract(
            problem_id,
            update,
            actor=_actor_identifier(user),
            note=update.amendment_note,
        )
        if updated_problem is None:
            raise HTTPException(
                status_code=409,
                detail="Only promoted draft problem contracts can be edited",
            )
        changed = outcome_contract_changes(
            problem.outcome_contract, updated_problem.outcome_contract
        )
        if changed:
            telemetry_store.record(
                "contract_amended",
                entity_id=problem_id,
                metadata={
                    "problem_id": problem_id,
                    "revision": updated_problem.outcome_contract.revision,
                    "changed": changed,
                    "actor": _actor_identifier(user),
                    "note": update.amendment_note,
                    "had_measurement": had_measurement,
                },
            )

        return enrich_problem_for_response(updated_problem)

    @router.post("/problems/{problem_id}/transitions", response_model=ProblemTransitionRecord, dependencies=[Depends(require_role(Role.editor))])
    def transition_problem(
        problem_id: str,
        transition: ProblemTransitionRequest,
        user: UserContext = Depends(get_current_user),  # noqa: B008
    ) -> ProblemTransitionRecord:
        problem = require_problem(problem_id)
        if problem.status == transition.target_status:
            raise HTTPException(status_code=409, detail="Problem is already in the target status")
        # A "resolved" transition is the resolution proof: attribute it to the
        # verified principal, never to a name the client typed (approvals already
        # work this way).
        if auth.AUTH_ENABLED:
            transition = transition.model_copy(update={"actor": _actor_identifier(user)})

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
        return build_emerging_problem_report(current_candidates(), signal_store.list_signals())

    @router.post("/problem-candidates/{candidate_id}/promote", response_model=ProblemRecord, dependencies=[Depends(require_role(Role.editor))])
    def promote_problem_candidate(
        candidate_id: str,
        user: UserContext = Depends(get_current_user),  # noqa: B008
    ) -> ProblemRecord:
        candidate = require_candidate(candidate_id)
        problem = promote_candidate(candidate)
        existing_problem = active_problem_store.get_problem(problem.problem_id)
        if existing_problem is not None:
            return enrich_problem_for_response(existing_problem)

        problem = _finalize_promotion(problem, user.workspace_id)
        return enrich_problem_for_response(active_problem_store.upsert_problem(problem))

    @router.post("/problem-candidates/{candidate_id}/accept", response_model=ProblemRecord, dependencies=[Depends(require_role(Role.editor))])
    def accept_problem_candidate(
        candidate_id: str,
        request: CandidateReviewRequest,
        user: UserContext = Depends(get_current_user),  # noqa: B008
    ) -> ProblemRecord:
        candidate = require_candidate(candidate_id)
        if candidate.review_status == CandidateReviewStatus.rejected:
            raise HTTPException(status_code=409, detail="Candidate has already been rejected")
        if candidate.duplicate_problem_id is not None:
            raise HTTPException(
                status_code=409,
                detail=f"Candidate duplicates existing problem {candidate.duplicate_problem_id}",
            )

        problem = _finalize_promotion(promote_candidate(candidate), user.workspace_id)
        promoted_problem = active_problem_store.upsert_problem(problem)
        telemetry_store.record(
            "candidate_accepted",
            entity_id=promoted_problem.problem_id,
            metadata={
                "origin": candidate.origin,
                "theme_tag": candidate.theme_tag,
                "owner": promoted_problem.owner,
                "due_at": promoted_problem.due_at,
            },
        )
        signal_store.record_candidate_decision(
            candidate_id=candidate.candidate_id,
            decision=CandidateDecisionStatus.accepted,
            reviewer=_actor_identifier(user) if auth.AUTH_ENABLED else request.reviewer,
            note=request.note,
        )
        return enrich_problem_for_response(promoted_problem)

    @router.post("/problem-candidates/{candidate_id}/reject", response_model=ProblemCandidate, dependencies=[Depends(require_role(Role.editor))])
    def reject_problem_candidate(
        candidate_id: str,
        request: CandidateReviewRequest,
        user: UserContext = Depends(get_current_user),  # noqa: B008
    ) -> ProblemCandidate:
        candidate = require_candidate(candidate_id)
        if candidate.review_status == CandidateReviewStatus.accepted:
            raise HTTPException(status_code=409, detail="Candidate has already been accepted")

        signal_store.record_candidate_decision(
            candidate_id=candidate.candidate_id,
            decision=CandidateDecisionStatus.rejected,
            reviewer=_actor_identifier(user) if auth.AUTH_ENABLED else request.reviewer,
            note=request.note,
        )
        return require_candidate(candidate_id)

    @router.post("/problems/{problem_id}/approvals", response_model=ApprovalRecord, dependencies=[Depends(require_role(Role.editor))])
    def record_approval(
        problem_id: str,
        decision: ApprovalDecision,
        user: UserContext = Depends(get_current_user),  # noqa: B008
    ) -> ApprovalRecord:
        problem = require_problem(problem_id)
        # The reviewer identity comes from the verified JWT, never the request
        # body: a self-asserted reviewer would let any editor sign approvals as
        # someone else, defeating the Art. 50(4) editorial-responsibility stamp
        # and the audit trail. (Module attr so tests can monkeypatch app.auth.)
        if auth.AUTH_ENABLED:
            decision = decision.model_copy(update={"reviewer": _actor_identifier(user)})
        # Hash the evidence pack AS THE APPROVER SAW IT (pre-decision state) and
        # stamp it on the append-only approval record: a later re-export whose
        # content_hash differs proves the pack changed after sign-off. Never set
        # from the request body (spoof-proof), best-effort (approval must not fail).
        pack_hash: str | None = None
        try:
            from app.services.evidence_pack import build_evidence_pack

            pack_hash = build_evidence_pack(
                enrich_problem_for_response(problem),
                workflow_store.state_for_problem(problem),
                measurement_plan_store.list_plans(),
            )["content_hash"]
        except Exception:  # noqa: BLE001
            logger.warning("Evidence-pack hashing failed for %s", problem_id, exc_info=True)
        record = workflow_store.record_approval(
            problem=problem,
            decision=decision,
            evidence_pack_hash=pack_hash,
            four_eyes=workspace_store.get(user.workspace_id).four_eyes_approval,
        )
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
                            actor=decision.reviewer,
                            note="auto-proposed contract accepted at approval",
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

            # The store names the execution this decision completed; scanning
            # the shared list for "latest with this action" raced with cache
            # refreshes and could push (or schedule) the wrong record, or none.
            execution = (
                next(
                    (e for e in workflow_store.list_executions() if e.execution_id == record.execution_id),
                    None,
                )
                if record.execution_id
                else None
            )
            if execution is not None:
                pushed: ExecutionRecord | None = None
                try:
                    workspace_settings = workspace_store.get(user.workspace_id)
                    pushed = push_approved_action(
                        problem=problem,
                        action=find_action(problem, decision.action_id),
                        execution=execution,
                        config_store=connector_config_store,
                        workflow_store=workflow_store,
                        disclosure_template=workspace_settings.ai_disclosure_template,
                        owner_routes=workspace_settings.owner_routes,
                        four_eyes=workspace_settings.four_eyes_approval,
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

                # The close-the-loop clock has three possible origins and one
                # non-start:
                #   pushed        -> from dispatched_at (the action left CLARA)
                #   draft_created -> from approval time: no connector for the
                #                    destination, the draft is the deliverable
                #   push_failed / anything else -> NO clock. Nothing reached the
                #                    world, so signals "since execution" would
                #                    measure a fix that never happened. A retry
                #                    or an implementation record starts it.
                # A human-recorded implementation (POST .../implementation)
                # later supersedes either clock with the moment the fix landed.
                _schedule_after_push(
                    problem=problem,
                    execution=execution,
                    pushed=pushed,
                )

        return record

    def _schedule_after_push(
        *, problem: ProblemRecord, execution: ExecutionRecord, pushed: ExecutionRecord | None
    ) -> None:
        status = pushed.status.value if pushed is not None else "push_error"
        if status == ExecutionStatus.pushed.value:
            origin, executed_at = "dispatch", pushed.dispatched_at or utc_now()
        elif status == ExecutionStatus.draft_created.value:
            origin, executed_at = "approval", execution.created_at
        else:
            telemetry_store.record(
                "measurement_not_scheduled",
                entity_id=problem.problem_id,
                metadata={
                    "problem_id": problem.problem_id,
                    "execution_id": execution.execution_id,
                    "reason": status,
                },
            )
            return
        try:
            kinds = schedule_measurements(
                measurement_plan_store,
                problem=problem,
                execution_id=execution.execution_id,
                executed_at=executed_at,
                origin=origin,
            )
            telemetry_store.record(
                "measurement_scheduled",
                entity_id=problem.problem_id,
                metadata={
                    "kinds": kinds,
                    "execution_id": execution.execution_id,
                    "origin": origin,
                    "executed_at": executed_at,
                },
            )
        except Exception:  # noqa: BLE001 — scheduling is best-effort
            logger.exception("Measurement scheduling failed for %s", problem.problem_id)

    @router.post(
        "/problems/{problem_id}/executions/{execution_id}/retry",
        response_model=ExecutionRecord,
        dependencies=[Depends(require_role(Role.editor))],
    )
    def retry_execution(
        problem_id: str,
        execution_id: str,
        user: UserContext = Depends(get_current_user),  # noqa: B008
    ) -> ExecutionRecord:
        """Re-run the destination push for an execution whose push failed.

        Without this a failed push was terminal: the approval stands (so a
        second approval is refused) and nothing retries. The idempotency scan in
        push_approved_action prevents duplicate external records.
        """
        from app.services.action_push import DispatchNotAuthorized, push_approved_action
        from app.services.workflow import find_action

        problem = require_problem(problem_id)
        execution = next(
            (
                item
                for item in workflow_store.list_executions()
                if item.execution_id == execution_id and item.problem_id == problem_id
            ),
            None,
        )
        if execution is None:
            raise HTTPException(status_code=404, detail="Execution not found")
        if execution.status != ExecutionStatus.push_failed:
            raise HTTPException(
                status_code=409, detail="Only executions whose push failed can be retried"
            )
        action = find_action(problem, execution.action_id)
        if action is None:
            raise HTTPException(status_code=404, detail="Action not found")
        settings = workspace_store.get(user.workspace_id)
        try:
            pushed = push_approved_action(
                problem=problem,
                action=action,
                execution=execution,
                config_store=connector_config_store,
                workflow_store=workflow_store,
                disclosure_template=settings.ai_disclosure_template,
                owner_routes=settings.owner_routes,
                four_eyes=settings.four_eyes_approval,
            )
        except DispatchNotAuthorized as exc:
            # The approval bound to this execution no longer covers the current
            # action revision (or was revoked/superseded): no outbound write.
            telemetry_store.record(
                "action_push_refused",
                entity_id=execution_id,
                metadata={"problem_id": problem_id, "reason": exc.reason},
            )
            raise HTTPException(status_code=409, detail=f"{exc.reason}: {exc.detail}") from exc
        telemetry_store.record(
            "action_push_retried",
            entity_id=execution_id,
            metadata={"problem_id": problem_id, "status": pushed.status.value},
        )
        if pushed.status == ExecutionStatus.pushed:
            # The failed push started no clock; the successful retry does,
            # from the moment the action really left CLARA.
            _schedule_after_push(problem=problem, execution=execution, pushed=pushed)
        return pushed

    @router.post(
        "/problems/{problem_id}/executions/{execution_id}/implementation",
        response_model=ExecutionRecord,
        dependencies=[Depends(require_role(Role.editor))],
    )
    def record_implementation(
        problem_id: str,
        execution_id: str,
        request: ImplementationRecordRequest,
        user: UserContext = Depends(get_current_user),  # noqa: B008
    ) -> ExecutionRecord:
        """Human attestation that the approved action's fix was implemented.

        A created ticket is not an implemented fix. Recording the implementation
        instant restarts the measurement clock from it: pending checkpoints that
        ran from approval or dispatch are superseded and new ones are scheduled
        from implemented_at, so post-fix inflow is read after the fix.
        """
        problem = require_problem(problem_id)
        execution = next(
            (
                item
                for item in workflow_store.list_executions()
                if item.execution_id == execution_id and item.problem_id == problem_id
            ),
            None,
        )
        if execution is None:
            raise HTTPException(status_code=404, detail="Execution not found")
        try:
            implemented_at = datetime.fromisoformat(request.implemented_at.replace("Z", "+00:00"))
        except ValueError as exc:
            raise HTTPException(status_code=422, detail="implemented_at must be ISO 8601") from exc
        if implemented_at.tzinfo is None:
            implemented_at = implemented_at.replace(tzinfo=UTC)
        if implemented_at > datetime.now(UTC) + timedelta(minutes=5):
            raise HTTPException(status_code=422, detail="implemented_at cannot be in the future")
        created_at = datetime.fromisoformat(execution.created_at.replace("Z", "+00:00"))
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=UTC)
        if implemented_at < created_at:
            raise HTTPException(
                status_code=422,
                detail="implemented_at cannot precede the execution's approval",
            )
        implemented_iso = implemented_at.astimezone(UTC).isoformat().replace("+00:00", "Z")

        updated = workflow_store.update_execution(
            execution_id,
            status=execution.status,
            external_ref=execution.external_ref,
            detail=execution.detail,
            implemented_at=implemented_iso,
            implementation_note=request.note,
        )
        superseded = measurement_plan_store.supersede_pending(
            problem_id, note=f"superseded by implementation record {execution_id}"
        )
        kinds = schedule_measurements(
            measurement_plan_store,
            problem=problem,
            execution_id=execution_id,
            executed_at=implemented_iso,
            origin="implementation",
        )
        telemetry_store.record(
            "implementation_recorded",
            entity_id=problem_id,
            metadata={
                "problem_id": problem_id,
                "execution_id": execution_id,
                "implemented_at": implemented_iso,
                "actor": _actor_identifier(user),
                "superseded_plans": superseded,
                "kinds": kinds,
            },
        )
        return updated

    @router.get("/problems/{problem_id}/evidence-pack", dependencies=[read_dep])
    def export_evidence_pack(
        problem_id: str,
        format: str = "html",
        user: UserContext = Depends(get_current_user),  # noqa: B008
    ):
        """Audit-ready export of one problem: evidence -> actions -> policy trail ->
        approvals -> executions -> outcome -> learning. HTML (print-to-PDF) or JSON."""
        from fastapi.responses import HTMLResponse

        from app.services.evidence_pack import build_evidence_pack, render_evidence_pack_html
        from app.services.works_council import redact as works_council_redact

        problem = enrich_problem_for_response(require_problem(problem_id))
        state = workflow_store.state_for_problem(problem)
        pack = build_evidence_pack(problem, state, measurement_plan_store.list_plans())
        # W1 Betriebsrat-Modus: the HTML rendering below bypasses the JSON
        # response middleware, so redact the pack dict at the source for BOTH
        # formats (idempotent under the middleware's second pass on JSON).
        pack = works_council_redact(
            pack,
            enabled=workspace_store.get(user.workspace_id).works_council_mode,
            role=user.role,
        )
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

        # A future measured_at would out-rank every scheduled checkpoint (staleness
        # guard rejects older readings), silencing the real measurements for good.
        try:
            measured_at = datetime.fromisoformat(measurement.measured_at.replace("Z", "+00:00"))
        except ValueError as exc:
            raise HTTPException(status_code=422, detail="measured_at must be ISO 8601") from exc
        if measured_at.tzinfo is None:
            measured_at = measured_at.replace(tzinfo=UTC)
        if measured_at > datetime.now(UTC) + timedelta(minutes=5):
            raise HTTPException(status_code=422, detail="measured_at cannot be in the future")

        # Anything posted over the API is a manual assertion; only the measurement
        # scheduler (which calls the store directly) records "instrumented".
        measurement = measurement.model_copy(update={"measurement_source": "manual"})
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
        user: UserContext = Depends(get_current_user),  # noqa: B008
    ) -> LearningConclusionRecord:
        problem = require_problem(problem_id)
        snapshot = workflow_store.outcome_snapshot(problem)
        if snapshot.latest_value is None:
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

        # Close the loop: the audit record above is append-only evidence; the
        # learning MEMORY below is what the next triage run retrieves
        # (rank_learnings -> synthesis prompt). Until this write existed the two
        # never met on the production path, so the model never learned from a
        # single real outcome. Best-effort: the conclusion is already recorded.
        try:
            score = None
            if snapshot.latest_value is not None:
                score = resolution_score(
                    baseline=snapshot.baseline,
                    measured=snapshot.latest_value,
                    direction=snapshot.improvement_direction,
                )
            approved_action_ids = {
                approval.action_id
                for approval in workflow_store.list_approvals()
                if approval.problem_id == problem_id
                and approval.decision == ApprovalDecisionStatus.approved
            }
            resolution_actions = [
                f"{action.class_.value}: {action.proposal}"
                for action in problem.action_proposals
                if action.action_id in approved_action_ids
            ]
            memory = learning_from_problem_conclusion(
                problem=problem,
                conclusion=learning,
                outcome_status=snapshot.status,
                resolution_score=score,
                resolution_actions=resolution_actions,
            )
            learning_store_factory().persist(memory, workspace_id=user.workspace_id)
            telemetry_store.record(
                "learning_persisted",
                entity_id=problem_id,
                metadata={
                    "conclusion_id": learning.conclusion_id,
                    "status": conclusion.learning_status.value,
                    "topic": memory.get("topic"),
                },
            )
        except Exception:  # noqa: BLE001 — memory write must never fail the conclusion
            logger.exception("Learning memory write failed for %s", problem_id)
        return learning

    @router.get("/learnings", dependencies=[read_dep])
    def list_learnings(user: UserContext = Depends(get_current_user)) -> list[dict]:  # noqa: B008
        """The workspace's learning memory with live decayed confidence.

        ``retrieval_eligible`` is False for auto-derived (reviewer=system)
        learnings: they are shown as pending but never steer synthesis.
        """
        try:
            items = learning_store_factory().load(workspace_id=user.workspace_id)
        except Exception as exc:  # noqa: BLE001
            logger.exception("Learning memory unavailable")
            raise HTTPException(status_code=503, detail="Learning memory unavailable") from exc
        decayed = [with_decay(item) for item in items]
        return sorted(
            decayed,
            key=lambda item: (item["retrieval_eligible"], item["decayed_confidence"]),
            reverse=True,
        )

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
        anchor = intervention_anchor(
            [
                execution
                for execution in workflow_store.list_executions()
                if execution.problem_id == problem_id
                and execution.action_id in approved_action_ids
            ]
        )
        executed_at = None
        if anchor is not None:
            snapshot.measurement_origin, snapshot.measurement_origin_at = anchor
            executed_at = anchor[1]
        if executed_at is not None:
            snapshot.its = its_outcome_for_problem(
                problem,
                signal_store.list_signals(),
                executed_at=executed_at,
                now=utc_now(),
            )
            if snapshot.its is not None:
                # Re-grade on the fit actually obtained: an ITS contract whose
                # series was too sparse for segmented regression is a plain
                # before/after delta (grade D), not an ITS (grade C).
                snapshot.evidence_grade = evidence_grade(
                    comparison_method=snapshot.comparison_method,
                    measurement_source=snapshot.measurement_source,
                    realised_method=snapshot.its.get("method"),
                )
        plans = [
            plan
            for plan in measurement_plan_store.list_plans()
            if str(plan.get("problem_id")) == problem_id
        ]
        snapshot.loop_verdict, snapshot.loop_note = loop_verdict(
            outcome_status=snapshot.status,
            plans=plans,
            measurement_source=snapshot.measurement_source,
            checkpoint_kind=snapshot.checkpoint_kind,
            measurement_origin=snapshot.measurement_origin,
            measurement_origin_at=snapshot.measurement_origin_at,
        )
        return snapshot

    @router.get("/outcome-board", response_model=OutcomeBoard, dependencies=[read_dep])
    def get_outcome_board(
        user: UserContext = Depends(get_current_user),  # noqa: B008
    ) -> OutcomeBoard:
        return build_outcome_board(
            list_enriched_problems(),
            workflow_store,
            tenant_id=user.tenant_setting,
            plans=measurement_plan_store.list_plans(),
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
        from pydantic import ValidationError

        from app.services.signals import UNKNOWN_IDENTITY_VALUES

        def _graph_signal(record) -> dict:
            # The WHOLE record travels: metadata (near-duplicate annotations feed
            # the reach count), journey_stage (closed-set routing must not
            # overwrite a source-provided stage), persisted tags/enrichment.
            return {
                **record.model_dump(),
                "id": record.signal_id,
                "text": record.feedback_text,
                "signal_type": "qualitative",
                "contact_count": 1,
            }

        body_signals = body.get("signals") or []
        if body_signals:
            # Caller-supplied rows are untrusted input: validate them like an
            # import, and never let them overwrite enrichment on foreign ids.
            try:
                validated = [SignalRecord.model_validate(item) for item in body_signals]
            except ValidationError as exc:
                raise HTTPException(status_code=422, detail=exc.errors()) from exc
            raw_signals = [_graph_signal(record) for record in validated]
            known_ids = signal_store.existing_signal_ids()
        else:
            raw_signals = [_graph_signal(record) for record in signal_store.list_signals()]
            known_ids = {item["signal_id"] for item in raw_signals}

        if not raw_signals:
            return {"insights": [], "status": "empty", "errors": ["No signals to process"]}

        # Gather connector configs for the action node
        conn_configs: dict[str, dict] = {}
        for cc in connector_config_store.list_configs():
            if cc.is_active:
                conn_configs[cc.connector_type] = cc.config

        # Severity = volume x severity x VALUE OF THE CUSTOMER AT RISK: derive the
        # context block from the imported customer/account context whenever the
        # caller did not supply one, so the 8-factor model runs in production.
        context_data = body.get("context_data")
        if context_data is None:
            try:
                context_rows = context_store.list_context()
            except Exception:  # noqa: BLE001 — context is an overlay
                context_rows = []
            if context_rows:
                from app.services.context_impact import has_valid_consent

                customer_ids = {
                    str(item.get("customer_id"))
                    for item in raw_signals
                    if item.get("customer_id") not in UNKNOWN_IDENTITY_VALUES
                }
                account_ids = {
                    str(item.get("account_id"))
                    for item in raw_signals
                    if item.get("account_id") not in UNKNOWN_IDENTITY_VALUES
                }
                matched = [
                    row
                    for row in context_rows
                    if row.customer_id in customer_ids or row.account_id in account_ids
                ]
                if matched:
                    account_values: dict[str, float] = {}
                    for row in matched:
                        account_values[row.account_id] = max(
                            account_values.get(row.account_id, 0.0), float(row.account_value or 0.0)
                        )
                    context_data = {
                        "account_count": len(account_values),
                        "context_impact": {
                            "matched_customers": len({row.customer_id for row in matched}),
                            "matched_accounts": len(account_values),
                            "total_account_value": round(sum(account_values.values()), 2),
                            "consent_risk_customers": sum(
                                1 for row in matched if not has_valid_consent(row)
                            ),
                        },
                    }

        # The workspace's own vocabulary steers the tag label space: accepted
        # taxonomy categories and terminology canonical terms ("trained on YOUR
        # taxonomy"), refreshed on every run so taxonomy edits feed back.
        workspace_vocabulary: list[str] = []
        if taxonomy_store is not None:
            try:
                from app.services.taxonomies import workspace_vocabulary as build_vocabulary

                workspace_vocabulary = build_vocabulary(taxonomy_store)
            except Exception:  # noqa: BLE001 — vocabulary is guidance, not a gate
                logger.warning("Workspace vocabulary unavailable", exc_info=True)

        # Past learnings inform synthesis (outcome-grounded self-improvement loop).
        # ponytail: best-effort — synthesis works fine without learnings, so a
        # store/DB hiccup degrades gracefully rather than failing the triage run.
        try:
            learnings = learning_store_factory().load(workspace_id=user.workspace_id)
        except Exception:
            learnings = []

        thread_id = f"triage-{uuid4().hex}"
        config = {"configurable": {"thread_id": thread_id}}

        # Closed-set routing inventory (R3): only when the flag is on and the
        # workspace has an accepted journey taxonomy to route against.
        stage_inventory: list[str] = []
        if taxonomy_store is not None:
            from app.services.enrichment import routing_closed_set_enabled
            from app.services.taxonomies import journey_stage_inventory

            if routing_closed_set_enabled():
                stage_inventory = journey_stage_inventory(taxonomy_store)

        result = triage_graph.invoke(
            {
                "workspace_id": user.workspace_id,
                "signals": raw_signals,
                "connector_configs": conn_configs,
                "context_data": context_data,
                "learnings": learnings,
                "journey_stage_inventory": stage_inventory,
                "workspace_vocabulary": workspace_vocabulary,
                "force_enrich": bool(body.get("force")),
            },
            config=config,
        )

        # Persist enrichment back to the signal store — without this the feed's
        # "Enriched" tile stays 0 forever and sentiment/urgency badges never
        # render (enrichment otherwise lives only inside the graph state).
        for enriched_signal in result.get("enriched_signals") or []:
            if not enriched_signal.get("enriched"):
                continue
            if (enriched_signal.get("audit") or {}).get("source") == "persisted_enrichment":
                continue  # already stored; nothing new to write
            sid = enriched_signal.get("signal_id") or enriched_signal.get("id")
            if not sid or sid not in known_ids:
                continue
            try:
                signal_store.update_enrichment(
                    sid,
                    sentiment=enriched_signal.get("sentiment"),
                    urgency=enriched_signal.get("urgency"),
                    tags=enriched_signal.get("tags"),
                )
            except Exception:  # noqa: BLE001 — best-effort; the triage result stands
                logger.warning("Failed to persist enrichment for %s", sid, exc_info=True)

        # Persist the AI themes so they surface as problem candidates
        # (origin=ai_theme) in the same accept -> approve -> measure path as
        # journey/stage candidates. Before this the insights existed only in
        # this response: the model's triage never reached the Action Queue.
        insights = result.get("insights") or []
        themes_saved = 0
        try:
            themes_saved = signal_store.save_theme_insights(insights, run_id=thread_id)
        except Exception:  # noqa: BLE001 — the triage result stands; persistence is best-effort
            logger.exception("Failed to persist triage themes for %s", thread_id)
        theme_candidate_ids = [
            theme_candidate_id(str(insight["tag"]).strip().lower().replace(" ", "_"))
            for insight in insights
            if insight.get("tag")
        ]
        telemetry_store.record(
            "themes_persisted",
            entity_id=thread_id,
            metadata={"themes": themes_saved, "insights": len(insights)},
        )

        # A non-empty `next` means the graph paused at the approval interrupt.
        if triage_graph.get_state(config).next:
            return {
                "status": "awaiting_approval",
                "thread_id": thread_id,
                "insights": insights,
                "theme_candidate_ids": theme_candidate_ids,
                "themes_saved": themes_saved,
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
            "insights": insights,
            "theme_candidate_ids": theme_candidate_ids,
            "themes_saved": themes_saved,
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
        paused = triage_graph.get_state(config)
        not_found = HTTPException(
            status_code=404,
            detail="No triage run awaiting approval for that thread_id (expired or already resumed)",
        )
        if not paused.next:
            raise not_found
        # Thread ids are random, but a paused run belongs to the workspace that
        # started it: another tenant guessing the id must see the same 404, not
        # be able to approve (and push) someone else's actions.
        # A thread without a recorded workspace is unattributable, so it is
        # treated the same way (fail closed) rather than assumed to be ours.
        thread_workspace = (paused.values or {}).get("workspace_id")
        if thread_workspace is None or str(thread_workspace) != str(user.workspace_id):
            raise not_found

        result = triage_graph.invoke(Command(resume=decision), config=config)

        # Durable Art. 50 accounting for graph pushes: action_node results
        # otherwise live only in graph state — no execution record, invisible
        # to /article50-status and the audit export. The resume decision is
        # the human gate, so the resuming principal is recorded as reviewer.
        execution_ids: list[str] = []
        if decision == "approved":
            reviewer = _actor_identifier(user)
            recorded_at = utc_now()
            status_map = {
                "pushed": ExecutionStatus.pushed,
                "failed": ExecutionStatus.push_failed,
                "no_connector": ExecutionStatus.blocked,
                "no_config": ExecutionStatus.blocked,
            }
            for item in result.get("action_results", []):
                audit = item.get("audit") or {}
                execution = ExecutionRecord(
                    execution_id="EXE-PENDING",  # store assigns the real id
                    problem_id=f"TRIAGE-{thread_id}",
                    action_id=str(item.get("action_type", "unknown")),
                    destination=str(
                        audit.get("connector") or item.get("action_type", "unknown")
                    ),
                    status=status_map.get(
                        str(item.get("status", "")), ExecutionStatus.blocked
                    ),
                    owner=reviewer,
                    summary=(
                        f"Triage push: {item.get('title') or item.get('insight_id') or 'action'}"
                    )[:200],
                    created_at=recorded_at,
                    external_ref=item.get("external_id"),
                    detail="; ".join(audit.get("limitations", [])) or None,
                    human_reviewed=True,
                    reviewed_by=reviewer,
                    reviewed_at=recorded_at,
                )
                execution_ids.append(workflow_store.add_execution(execution).execution_id)

            # The learn node's auto-derived learning is visible memory (pending
            # human validation: reviewer=system keeps it out of retrieval).
            learning = result.get("learning")
            if isinstance(learning, dict):
                try:
                    learning_store_factory().persist(
                        {
                            **learning,
                            "conclusion_id": f"triage-{thread_id}",
                            "problem_id": f"TRIAGE-{thread_id}",
                            "source": "triage_resume",
                            "created_at": recorded_at,
                        },
                        workspace_id=user.workspace_id,
                    )
                except Exception:  # noqa: BLE001 — memory write is best-effort
                    logger.exception("Learning memory write failed for triage %s", thread_id)

        return {
            "status": result.get("status", "unknown"),
            "approval_decision": result.get("approval_decision"),
            "approved_insights": result.get("approved_insights", []),
            "action_results": result.get("action_results", []),
            "execution_ids": execution_ids,
            "outcome": result.get("outcome"),
            "learning": result.get("learning"),
            "errors": result.get("errors", []),
        }

    return router
