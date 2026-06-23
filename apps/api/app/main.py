from __future__ import annotations

import os
from pathlib import Path

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.domain.models import (
    ActionProposalUpdateRequest,
    AffectedContextExplorer,
    ApprovalDecision,
    ApprovalRecord,
    CandidateDecisionStatus,
    CandidateReviewRequest,
    CandidateReviewStatus,
    CustomerContextCompletenessReport,
    CustomerContextCsvImportRequest,
    CustomerContextImportRequest,
    CustomerContextImportResult,
    CustomerContextRecord,
    CustomerContextValidationReport,
    DemoDatasetImportResult,
    DemoDatasetSummary,
    EmergingProblemReport,
    ExecutionRecord,
    JiraIssueDraft,
    LearningConclusionRecord,
    LearningConclusionRequest,
    LearningStatus,
    OutcomeBoard,
    OutcomeBoardItem,
    OutcomeMeasurement,
    OutcomeSnapshot,
    PolicyRule,
    ProblemCandidate,
    ProblemRecord,
    ProblemStatus,
    ProblemSummary,
    ProblemTransitionRecord,
    ProblemTransitionRequest,
    ProblemUpdateRequest,
    SignalCsvImportRequest,
    SignalImportRequest,
    SignalImportResult,
    SignalRecord,
    SignalValidationReport,
    TaxonomyCatalog,
    TaxonomyLockRequest,
    TaxonomyMergeRequest,
    TaxonomyRenameRequest,
    TaxonomySplitRequest,
    TaxonomyType,
    TerminologyDictionaryEntry,
    WorkflowState,
    pseudonymized_identifier,
)
from app.services.context_impact import (
    build_affected_context_explorer,
    enrich_problem_with_context,
)
from app.services.contexts import (
    SQLiteCustomerContextStore,
    context_completeness_report,
    parse_context_csv,
    validate_context_csv,
)
from app.services.emerging import build_emerging_problem_report
from app.services.policies import PolicyRuleStore
from app.services.postgres import (
    PostgresCustomerContextStore,
    PostgresProblemStore,
    PostgresSignalStore,
    PostgresTaxonomyStore,
    PostgresTerminologyStore,
    PostgresWorkflowStore,
    database_url,
)
from app.services.problems import ProblemStore, SQLiteProblemStore
from app.services.seed import (
    load_demo_datasets,
    load_seed_customer_context,
    load_seed_policy_rules,
    load_seed_problems,
    load_seed_signals,
    to_demo_dataset_summary,
)
from app.services.signals import (
    SQLiteSignalStore,
    parse_signal_csv,
    promote_candidate,
    validate_signal_csv,
)
from app.services.taxonomies import TaxonomyStore, TerminologyStore, classify_candidate
from app.services.workflow import SQLiteWorkflowStore


def default_db_path() -> Path:
    configured_path = os.getenv("ODRADEK_DB_PATH")
    if configured_path:
        return Path(configured_path)

    return Path(__file__).resolve().parents[1] / ".data" / "odradek.db"


def default_workflow_store() -> SQLiteWorkflowStore:
    url = database_url()
    if url:
        return PostgresWorkflowStore(url)
    return SQLiteWorkflowStore(default_db_path())


def default_signal_store() -> SQLiteSignalStore:
    url = database_url()
    if url:
        return PostgresSignalStore(url)
    return SQLiteSignalStore(default_db_path())


def default_context_store() -> SQLiteCustomerContextStore:
    url = database_url()
    if url:
        return PostgresCustomerContextStore(url)
    return SQLiteCustomerContextStore(default_db_path())


def default_problem_store() -> SQLiteProblemStore:
    url = database_url()
    if url:
        return PostgresProblemStore(url, load_seed_problems())
    return SQLiteProblemStore(default_db_path(), load_seed_problems())


def default_policy_store() -> PolicyRuleStore:
    return PolicyRuleStore(load_seed_policy_rules())


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


def review_match_key(value: str) -> str:
    return value.replace("_", " ").strip().lower()


class TrustedWorkflowIdentity:
    def __init__(self, *, tenant_id: str, actor_id: str) -> None:
        self.tenant_id = tenant_id
        self.actor_id = actor_id


def require_trusted_workflow_identity(
    x_tenant_id: str | None = Header(default=None, alias="x-tenant-id"),
    x_actor_id: str | None = Header(default=None, alias="x-actor-id"),
) -> TrustedWorkflowIdentity:
    if x_tenant_id is None or x_actor_id is None:
        raise HTTPException(status_code=401, detail="Trusted tenant and actor headers are required")
    try:
        tenant_id = pseudonymized_identifier(x_tenant_id, "Tenant ID")
        actor_id = pseudonymized_identifier(x_actor_id, "Actor ID")
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return TrustedWorkflowIdentity(tenant_id=tenant_id, actor_id=actor_id)


def matching_problem_for_candidate(
    candidate: ProblemCandidate,
    problems: list[ProblemRecord],
) -> ProblemRecord | None:
    candidate_key = (
        review_match_key(candidate.journey),
        review_match_key(candidate.journey_stage),
    )
    return next(
        (
            problem
            for problem in problems
            if (
                review_match_key(problem.journey),
                review_match_key(problem.journey_stage),
            )
            == candidate_key
        ),
        None,
    )


def enrich_candidate(
    candidate: ProblemCandidate,
    *,
    problems: list[ProblemRecord],
    signal_store,
    taxonomy_store: TaxonomyStore,
    terminology_store: TerminologyStore,
) -> ProblemCandidate:
    decision = signal_store.get_candidate_decision(candidate.candidate_id)
    duplicate_problem = matching_problem_for_candidate(candidate, problems)
    updates: dict[str, object] = {}

    if duplicate_problem is not None:
        updates.update(
            {
                "duplicate_problem_id": duplicate_problem.problem_id,
                "duplicate_reason": (
                    "Same journey and journey stage as an existing Action Queue problem."
                ),
            }
        )

    if decision is not None:
        review_status = (
            CandidateReviewStatus.accepted
            if decision.decision == CandidateDecisionStatus.accepted
            else CandidateReviewStatus.rejected
        )
        updates.update(
            {
                "review_status": review_status,
                "reviewer": decision.reviewer,
                "review_note": decision.note,
                "reviewed_at": decision.created_at,
            }
        )
    elif duplicate_problem is not None:
        updates["review_status"] = CandidateReviewStatus.duplicate

    enriched_candidate = candidate.model_copy(update=updates)
    return classify_candidate(
        enriched_candidate,
        signals=signal_store.list_signals(),
        taxonomy_store=taxonomy_store,
        terminology_store=terminology_store,
    )


def create_app(
    *,
    problems: dict[str, ProblemRecord] | None = None,
    problem_store=None,
    workflows=None,
    signals=None,
    contexts=None,
    policies=None,
    taxonomies=None,
    terminology=None,
    demo_datasets=None,
) -> FastAPI:
    api = FastAPI(
        title="Odradek API",
        version="0.1.0",
        summary="Feedback-to-Outcome API prototype",
    )

    cors_origins = [
        origin.strip()
        for origin in os.getenv("API_CORS_ORIGINS", "http://localhost:3000").split(",")
        if origin.strip()
    ]

    api.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    active_problem_store = problem_store
    if active_problem_store is None and problems is not None:
        active_problem_store = ProblemStore(list(problems.values()))
    if active_problem_store is None:
        active_problem_store = default_problem_store()

    workflow_store = workflows or default_workflow_store()
    signal_store = signals or default_signal_store()
    context_store = contexts or default_context_store()
    policy_store = policies or default_policy_store()
    url = database_url()
    taxonomy_store = taxonomies or (PostgresTaxonomyStore(url) if url else TaxonomyStore())
    terminology_store = terminology or (
        PostgresTerminologyStore(url) if url else TerminologyStore()
    )
    active_demo_datasets = demo_datasets or load_demo_datasets()
    if not signal_store.list_signals():
        signal_store.import_signals(load_seed_signals())
    if not context_store.list_context():
        context_store.import_context(load_seed_customer_context())

    def require_problem(problem_id: str) -> ProblemRecord:
        problem = active_problem_store.get_problem(problem_id)
        if problem is None:
            raise HTTPException(status_code=404, detail="Problem not found")

        return problem

    def enrich_problem_for_response(problem: ProblemRecord) -> ProblemRecord:
        return enrich_problem_with_context(problem, context_store.list_context())

    def list_enriched_problems() -> list[ProblemRecord]:
        context_records = context_store.list_context()
        return [
            enrich_problem_with_context(problem, context_records)
            for problem in active_problem_store.list_problems()
        ]

    def require_demo_dataset(dataset_id: str):
        dataset = next(
            (
                dataset
                for dataset in active_demo_datasets
                if dataset.dataset_id == dataset_id
            ),
            None,
        )
        if dataset is None:
            raise HTTPException(status_code=404, detail="Demo dataset not found")

        return dataset

    def current_candidates() -> list[ProblemCandidate]:
        problems = active_problem_store.list_problems()
        return [
            enrich_candidate(
                candidate,
                problems=problems,
                signal_store=signal_store,
                taxonomy_store=taxonomy_store,
                terminology_store=terminology_store,
            )
            for candidate in signal_store.candidates()
        ]

    def require_candidate(candidate_id: str) -> ProblemCandidate:
        candidate = next(
            (candidate for candidate in current_candidates() if candidate.candidate_id == candidate_id),
            None,
        )
        if candidate is None:
            raise HTTPException(status_code=404, detail="Problem candidate not found")

        return candidate

    @api.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @api.get("/problems", response_model=list[ProblemSummary])
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

    @api.get("/problems/{problem_id}", response_model=ProblemRecord)
    def get_problem(problem_id: str) -> ProblemRecord:
        return enrich_problem_for_response(require_problem(problem_id))

    @api.get(
        "/problems/{problem_id}/affected-context",
        response_model=AffectedContextExplorer,
    )
    def get_affected_context(problem_id: str) -> AffectedContextExplorer:
        return build_affected_context_explorer(
            require_problem(problem_id),
            context_store.list_context(),
        )

    @api.patch("/problems/{problem_id}", response_model=ProblemRecord)
    def update_problem(problem_id: str, update: ProblemUpdateRequest) -> ProblemRecord:
        require_problem(problem_id)
        updated_problem = active_problem_store.update_problem(problem_id, update)
        if updated_problem is None:
            raise HTTPException(
                status_code=409,
                detail="Only promoted draft problems can be edited",
            )

        return enrich_problem_for_response(updated_problem)

    @api.patch("/problems/{problem_id}/actions/{action_id}", response_model=ProblemRecord)
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

    @api.post("/problems/{problem_id}/transitions", response_model=ProblemTransitionRecord)
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

    @api.get("/signals", response_model=list[SignalRecord])
    def list_signals() -> list[SignalRecord]:
        return signal_store.list_signals()

    @api.post("/signals/import", response_model=SignalImportResult)
    def import_signals(request: SignalImportRequest) -> SignalImportResult:
        return signal_store.import_signals(request.signals)

    @api.post("/signals/import-csv", response_model=SignalImportResult)
    def import_signal_csv(request: SignalCsvImportRequest) -> SignalImportResult:
        report = validate_signal_csv(
            request.csv_text,
            existing_signal_ids=signal_store.existing_signal_ids(),
        )
        if not report.valid:
            raise HTTPException(status_code=422, detail=report.model_dump(mode="json"))

        return signal_store.import_signals(parse_signal_csv(request.csv_text))

    @api.post("/signals/validate-csv", response_model=SignalValidationReport)
    def validate_signal_csv_import(request: SignalCsvImportRequest) -> SignalValidationReport:
        return validate_signal_csv(
            request.csv_text,
            existing_signal_ids=signal_store.existing_signal_ids(),
        )

    @api.get("/customer-context", response_model=list[CustomerContextRecord])
    def list_customer_context() -> list[CustomerContextRecord]:
        return context_store.list_context()

    @api.get(
        "/customer-context/completeness",
        response_model=CustomerContextCompletenessReport,
    )
    def get_customer_context_completeness() -> CustomerContextCompletenessReport:
        return context_completeness_report(context_store.list_context())

    @api.post("/customer-context/import", response_model=CustomerContextImportResult)
    def import_customer_context(
        request: CustomerContextImportRequest,
    ) -> CustomerContextImportResult:
        return context_store.import_context(request.records)

    @api.post("/customer-context/import-csv", response_model=CustomerContextImportResult)
    def import_customer_context_csv(
        request: CustomerContextCsvImportRequest,
    ) -> CustomerContextImportResult:
        report = validate_context_csv(
            request.csv_text,
            existing_customer_ids=context_store.existing_customer_ids(),
        )
        if not report.valid:
            raise HTTPException(status_code=422, detail=report.model_dump(mode="json"))

        return context_store.import_context(parse_context_csv(request.csv_text))

    @api.post("/customer-context/validate-csv", response_model=CustomerContextValidationReport)
    def validate_customer_context_csv(
        request: CustomerContextCsvImportRequest,
    ) -> CustomerContextValidationReport:
        return validate_context_csv(
            request.csv_text,
            existing_customer_ids=context_store.existing_customer_ids(),
        )

    @api.get("/policy-rules", response_model=list[PolicyRule])
    def list_policy_rules() -> list[PolicyRule]:
        return policy_store.list_rules()

    @api.get("/taxonomies", response_model=list[TaxonomyCatalog])
    def list_taxonomies() -> list[TaxonomyCatalog]:
        return taxonomy_store.list_catalogs()

    @api.get("/terminology-dictionary", response_model=list[TerminologyDictionaryEntry])
    def list_terminology_dictionary() -> list[TerminologyDictionaryEntry]:
        return terminology_store.list_entries()

    @api.post("/taxonomies/{taxonomy_type}/categories/rename", response_model=TaxonomyCatalog)
    def rename_taxonomy_category(
        taxonomy_type: TaxonomyType,
        request: TaxonomyRenameRequest,
    ) -> TaxonomyCatalog:
        try:
            return taxonomy_store.rename_category(
                taxonomy_type,
                category_id=request.category_id,
                label=request.label,
                description=request.description,
                actor=request.actor,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @api.post("/taxonomies/{taxonomy_type}/categories/lock", response_model=TaxonomyCatalog)
    def lock_taxonomy_category(
        taxonomy_type: TaxonomyType,
        request: TaxonomyLockRequest,
    ) -> TaxonomyCatalog:
        try:
            return taxonomy_store.lock_category(
                taxonomy_type,
                category_id=request.category_id,
                actor=request.actor,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @api.post("/taxonomies/{taxonomy_type}/categories/merge", response_model=TaxonomyCatalog)
    def merge_taxonomy_categories(
        taxonomy_type: TaxonomyType,
        request: TaxonomyMergeRequest,
    ) -> TaxonomyCatalog:
        try:
            return taxonomy_store.merge_categories(
                taxonomy_type,
                source_category_ids=request.source_category_ids,
                target_category_id=request.target_category_id,
                target_label=request.target_label,
                target_description=request.target_description,
                actor=request.actor,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @api.post("/taxonomies/{taxonomy_type}/categories/split", response_model=TaxonomyCatalog)
    def split_taxonomy_category(
        taxonomy_type: TaxonomyType,
        request: TaxonomySplitRequest,
    ) -> TaxonomyCatalog:
        try:
            return taxonomy_store.split_category(
                taxonomy_type,
                source_category_id=request.source_category_id,
                categories=request.categories,
                actor=request.actor,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @api.get("/policy-rules/{rule_id}", response_model=PolicyRule)
    def get_policy_rule(rule_id: str) -> PolicyRule:
        policy_rule = policy_store.get_rule(rule_id)
        if policy_rule is None:
            raise HTTPException(status_code=404, detail="Policy rule not found")

        return policy_rule

    @api.get("/demo-datasets", response_model=list[DemoDatasetSummary])
    def list_demo_datasets() -> list[DemoDatasetSummary]:
        return [to_demo_dataset_summary(dataset) for dataset in active_demo_datasets]

    @api.post("/demo-datasets/{dataset_id}/import", response_model=DemoDatasetImportResult)
    def import_demo_dataset(dataset_id: str) -> DemoDatasetImportResult:
        dataset = require_demo_dataset(dataset_id)
        signal_result = signal_store.import_signals(dataset.signals)
        context_result = context_store.import_context(dataset.customer_context)
        return DemoDatasetImportResult(
            dataset_id=dataset.dataset_id,
            title=dataset.title,
            signals=signal_result,
            customer_context=context_result,
        )

    @api.get("/problem-candidates", response_model=list[ProblemCandidate])
    def list_problem_candidates() -> list[ProblemCandidate]:
        return current_candidates()

    @api.get("/emerging-problems", response_model=EmergingProblemReport)
    def list_emerging_problems() -> EmergingProblemReport:
        return build_emerging_problem_report(current_candidates())

    @api.post("/problem-candidates/{candidate_id}/promote", response_model=ProblemRecord)
    def promote_problem_candidate(candidate_id: str) -> ProblemRecord:
        candidate = require_candidate(candidate_id)
        problem = promote_candidate(candidate)
        existing_problem = active_problem_store.get_problem(problem.problem_id)
        if existing_problem is not None:
            return enrich_problem_for_response(existing_problem)

        return enrich_problem_for_response(active_problem_store.upsert_problem(problem))

    @api.post("/problem-candidates/{candidate_id}/accept", response_model=ProblemRecord)
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

    @api.post("/problem-candidates/{candidate_id}/reject", response_model=ProblemCandidate)
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

    @api.post("/problems/{problem_id}/approvals", response_model=ApprovalRecord)
    def record_approval(problem_id: str, decision: ApprovalDecision) -> ApprovalRecord:
        problem = require_problem(problem_id)
        return workflow_store.record_approval(problem=problem, decision=decision)

    @api.get("/problems/{problem_id}/workflow", response_model=WorkflowState)
    def get_workflow_state(
        problem_id: str,
        x_tenant_id: str | None = Header(default=None, alias="x-tenant-id"),
    ) -> WorkflowState:
        problem = require_problem(problem_id)
        tenant_id = ""
        if x_tenant_id is not None:
            try:
                tenant_id = pseudonymized_identifier(x_tenant_id, "Tenant ID")
            except ValueError as exc:
                raise HTTPException(status_code=422, detail=str(exc)) from exc
        return workflow_store.state_for_problem(problem, tenant_id=tenant_id)

    @api.post("/problems/{problem_id}/outcomes", response_model=OutcomeMeasurement)
    def record_outcome(problem_id: str, measurement: OutcomeMeasurement) -> OutcomeMeasurement:
        problem = require_problem(problem_id)
        if measurement.problem_id != problem_id:
            raise HTTPException(status_code=422, detail="Outcome problem_id must match the route")

        return workflow_store.record_outcome(problem=problem, measurement=measurement)

    @api.post(
        "/problems/{problem_id}/learning-conclusions",
        response_model=LearningConclusionRecord,
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

        return workflow_store.record_learning_conclusion(
            problem=problem,
            conclusion=conclusion,
            tenant_id=identity.tenant_id,
            actor=identity.actor_id,
        )

    @api.get("/problems/{problem_id}/outcome", response_model=OutcomeSnapshot)
    def get_outcome_snapshot(problem_id: str) -> OutcomeSnapshot:
        problem = require_problem(problem_id)
        return workflow_store.outcome_snapshot(problem)

    @api.get("/outcome-board", response_model=OutcomeBoard)
    def get_outcome_board(
        x_tenant_id: str | None = Header(default=None, alias="x-tenant-id"),
    ) -> OutcomeBoard:
        tenant_id = ""
        if x_tenant_id is not None:
            try:
                tenant_id = pseudonymized_identifier(x_tenant_id, "Tenant ID")
            except ValueError as exc:
                raise HTTPException(status_code=422, detail=str(exc)) from exc
        return build_outcome_board(list_enriched_problems(), workflow_store, tenant_id=tenant_id)

    @api.get("/approvals", response_model=list[ApprovalRecord])
    def list_approvals() -> list[ApprovalRecord]:
        return workflow_store.list_approvals()

    @api.get("/executions", response_model=list[ExecutionRecord])
    def list_executions() -> list[ExecutionRecord]:
        return workflow_store.list_executions()

    @api.get("/jira-drafts", response_model=list[JiraIssueDraft])
    def list_jira_drafts() -> list[JiraIssueDraft]:
        return workflow_store.list_jira_issue_drafts()

    return api


app = create_app()
