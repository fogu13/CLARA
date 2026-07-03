from __future__ import annotations

import logging
import os
from collections import Counter
from pathlib import Path
from uuid import uuid4

import hashlib
import hmac
import json

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware

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
    FeedbackRule,
    FeedbackRuleCreate,
    JiraIssueDraft,
    JourneyEventCsvImportRequest,
    JourneyEventImportRequest,
    JourneyEventImportResult,
    JourneyEventRecord,
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
    SystemConfig,
    TaxonomyCatalog,
    TaxonomyLockRequest,
    TaxonomyMergeRequest,
    TaxonomyRenameRequest,
    TaxonomyReviewRequest,
    TaxonomySplitRequest,
    TaxonomyType,
    TerminologyDictionaryEntry,
    WorkflowState,
    WorkspaceSettings,
    pseudonymized_identifier,
)
from app.rate_limit import rate_limiter
from app.rbac import Role, require_role
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
from app.services.journeys import (
    SQLiteJourneyEventStore,
    enrich_problem_with_journey,
    parse_journey_event_csv,
)
from app.services.policies import PolicyRuleStore
from app.services.postgres import (
    PostgresCustomerContextStore,
    PostgresJourneyEventStore,
    PostgresProblemStore,
    PostgresRuleStore,
    PostgresSignalStore,
    PostgresTaxonomyStore,
    PostgresTerminologyStore,
    PostgresWorkflowStore,
    PostgresWorkspaceStore,
    database_url,
)
from app.services.problems import ProblemStore, SQLiteProblemStore
from app.services.rules import SQLiteRuleStore
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
    signal_from_row,
    promote_candidate,
    validate_signal_csv,
)
from app.services.common import utc_now
from app.services.taxonomies import TaxonomyStore, TerminologyStore, classify_candidate
from app.services.telemetry import SQLiteTelemetryStore
from app.services.workflow import SQLiteWorkflowStore
from app.services.workspace import SQLiteWorkspaceStore

logger = logging.getLogger(__name__)


def default_db_path() -> Path:
    configured_path = os.getenv("CLARA_DB_PATH")
    if configured_path:
        return Path(configured_path)

    return Path(__file__).resolve().parents[1] / ".data" / "clara.db"


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


def default_journey_event_store() -> SQLiteJourneyEventStore:
    url = database_url()
    if url:
        return PostgresJourneyEventStore(url)
    return SQLiteJourneyEventStore(default_db_path())


def default_problem_store() -> SQLiteProblemStore:
    url = database_url()
    if url:
        return PostgresProblemStore(url, load_seed_problems())
    return SQLiteProblemStore(default_db_path(), load_seed_problems())


def default_policy_store() -> PolicyRuleStore:
    return PolicyRuleStore(load_seed_policy_rules())


def default_workspace_store():
    url = database_url()
    if url:
        return PostgresWorkspaceStore(url)
    return SQLiteWorkspaceStore(default_db_path())


def default_rule_store():
    url = database_url()
    if url:
        return PostgresRuleStore(url)
    return SQLiteRuleStore(default_db_path())


def default_learning_store():
    """Local-first learning store (SQLite). Feeds rank_learnings into synthesis.

    The Postgres learning_conclusions table (migration 005) is the production
    counterpart; the SQLite store is the local/offline path the thesis runs on.
    """
    from app.services.learning_store import SQLiteLearningStore

    return SQLiteLearningStore(default_db_path())


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


def build_language_quality_report(signals: list[SignalRecord], terms: list[TerminologyDictionaryEntry]) -> dict:
    signal_counts = Counter((signal.language or "unknown").lower() for signal in signals)
    term_counts = Counter(language.lower() for term in terms for language in term.languages)
    languages = sorted({"de", "en", *signal_counts.keys(), *term_counts.keys()})
    rows = []

    for language in languages:
        signal_count = signal_counts[language]
        terminology_entries = term_counts[language]
        rows.append(
            {
                "language": language,
                "signal_count": signal_count,
                "terminology_entries": terminology_entries,
                "original_language_evidence": signal_count,
                "readiness": "ready" if signal_count and terminology_entries else "needs_attention",
            }
        )

    return {
        "total_signals": len(signals),
        "languages": rows,
        "german_english_ready": all(
            row["readiness"] == "ready" for row in rows if row["language"] in {"de", "en"}
        ),
    }


def review_match_key(value: str) -> str:
    return value.replace("_", " ").strip().lower()


# Connector config keys whose values are secrets and must never be returned to clients.
_SECRET_CONFIG_KEYS = {
    "api_token",
    "bot_token",
    "token",
    "secret",
    "password",
    "access_token",
    "client_secret",
}


def redacted_connector_config(connector) -> dict:
    """Serialize a ConnectorConfig with secret credential values masked."""
    data = connector.model_dump()
    config = data.get("config")
    if isinstance(config, dict):
        data["config"] = {
            key: ("***redacted***" if key in _SECRET_CONFIG_KEYS and value else value)
            for key, value in config.items()
        }
    return data


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
    connector_configs=None,
    journeys=None,
    workspace=None,
    feedback_rules=None,
    telemetry=None,
    measurement_plans=None,
) -> FastAPI:
    api = FastAPI(
        title="CLARA API",
        version="0.1.0",
        summary="Feedback-to-Outcome API prototype",
    )

    cors_env = os.getenv("APP_CORS_ORIGINS") or os.getenv("API_CORS_ORIGINS") or "http://localhost:3000,http://127.0.0.1:3000"
    cors_origins = [
        origin.strip()
        for origin in cors_env.split(",")
        if origin.strip()
    ]

    api.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Read access: any authenticated user (viewer+). In dev (auth disabled)
    # get_current_user returns a default owner context, so tests/local are unaffected.
    read_dep = Depends(require_role(Role.viewer))

    active_problem_store = problem_store
    if active_problem_store is None and problems is not None:
        active_problem_store = ProblemStore(list(problems.values()))
    if active_problem_store is None:
        active_problem_store = default_problem_store()

    workflow_store = workflows or default_workflow_store()
    signal_store = signals or default_signal_store()
    context_store = contexts or default_context_store()
    journey_event_store = journeys or default_journey_event_store()
    policy_store = policies or default_policy_store()
    workspace_store = workspace or default_workspace_store()
    rule_store = feedback_rules or default_rule_store()
    telemetry_store = telemetry or SQLiteTelemetryStore(default_db_path())
    from app.services.measurement_scheduler import (
        SQLiteMeasurementPlanStore,
        attach_measurement_loop,
        run_due_measurements,
        schedule_measurements,
    )

    measurement_plan_store = measurement_plans or SQLiteMeasurementPlanStore(default_db_path())

    def _run_due_measurements(now: str | None = None) -> dict[str, int]:
        return run_due_measurements(
            plan_store=measurement_plan_store,
            problem_lookup=active_problem_store.get_problem,
            signal_store=signal_store,
            workflow_store=workflow_store,
            telemetry=telemetry_store,
            now=now,
        )

    attach_measurement_loop(api, _run_due_measurements)
    url = database_url()
    taxonomy_store = taxonomies or (PostgresTaxonomyStore(url) if url else TaxonomyStore())
    terminology_store = terminology or (
        PostgresTerminologyStore(url) if url else TerminologyStore()
    )
    active_demo_datasets = demo_datasets or load_demo_datasets()
    from app.connectors.config_store import SQLiteConnectorConfigStore

    # Persistent by default: a pilot's Jira/Zendesk credentials must survive restarts.
    connector_config_store = connector_configs or SQLiteConnectorConfigStore(default_db_path())
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
        context_enriched = enrich_problem_with_context(problem, context_store.list_context())
        return enrich_problem_with_journey(context_enriched, journey_event_store.list_events())

    def list_enriched_problems() -> list[ProblemRecord]:
        context_records = context_store.list_context()
        journey_events = journey_event_store.list_events()
        return [
            enrich_problem_with_journey(enrich_problem_with_context(problem, context_records), journey_events)
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

    @api.get("/problems", response_model=list[ProblemSummary], dependencies=[read_dep])
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

    @api.get("/problems/{problem_id}", response_model=ProblemRecord, dependencies=[read_dep])
    def get_problem(problem_id: str) -> ProblemRecord:
        problem = enrich_problem_for_response(require_problem(problem_id))
        # time-to-first-insight numerator: first insight viewed after first ingest.
        telemetry_store.record("insight_viewed", entity_id=problem_id)
        return problem

    @api.get(
        "/problems/{problem_id}/affected-context",
        response_model=AffectedContextExplorer,
        dependencies=[read_dep],
    )
    def get_affected_context(problem_id: str) -> AffectedContextExplorer:
        return build_affected_context_explorer(
            require_problem(problem_id),
            context_store.list_context(),
        )

    @api.patch("/problems/{problem_id}", response_model=ProblemRecord, dependencies=[Depends(require_role(Role.editor))])
    def update_problem(problem_id: str, update: ProblemUpdateRequest) -> ProblemRecord:
        require_problem(problem_id)
        updated_problem = active_problem_store.update_problem(problem_id, update)
        if updated_problem is None:
            raise HTTPException(
                status_code=409,
                detail="Only promoted draft problems can be edited",
            )

        return enrich_problem_for_response(updated_problem)

    @api.patch("/problems/{problem_id}/actions/{action_id}", response_model=ProblemRecord, dependencies=[Depends(require_role(Role.editor))])
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

    @api.post("/problems/{problem_id}/transitions", response_model=ProblemTransitionRecord, dependencies=[Depends(require_role(Role.editor))])
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

    @api.get("/signals", response_model=list[SignalRecord], dependencies=[read_dep])
    def list_signals() -> list[SignalRecord]:
        return signal_store.list_signals()

    @api.post("/signals/import", response_model=SignalImportResult, dependencies=[Depends(require_role(Role.editor))])
    def import_signals(request: SignalImportRequest) -> SignalImportResult:
        return signal_store.import_signals(request.signals)

    @api.post("/signals/import-csv", response_model=SignalImportResult, dependencies=[Depends(require_role(Role.editor))])
    def import_signal_csv(request: SignalCsvImportRequest) -> SignalImportResult:
        report = validate_signal_csv(
            request.csv_text,
            existing_signal_ids=signal_store.existing_signal_ids(),
        )
        if not report.valid:
            raise HTTPException(status_code=422, detail=report.model_dump(mode="json"))

        result = signal_store.import_signals(parse_signal_csv(request.csv_text))
        telemetry_store.record(
            "signals_imported",
            metadata={"source": "csv", "imported": result.imported, "skipped": result.skipped_duplicates},
        )
        return result

    @api.post("/ingest/webhook", response_model=SignalImportResult)
    async def ingest_webhook(request: Request) -> SignalImportResult:
        """Generic push ingestion: anything that can POST JSON can feed CLARA.

        Auth is the HMAC signature (X-Clara-Signature: sha256=<hex>) computed over
        the raw body with the shared secret from the "webhook" connector config —
        external systems don't hold user JWTs, so this route deliberately carries
        no role dependency. Body: {"signals": [{...flat fields...}]} or a bare list;
        rows get the same defaults/dedup/language handling as CSV import.
        """
        webhook_config = connector_config_store.get_config("webhook")
        secret = (webhook_config.config.get("secret") if webhook_config else "") or ""
        if webhook_config is None or not webhook_config.is_active or not secret:
            raise HTTPException(
                status_code=400,
                detail="No active webhook configured — set a secret via PUT /connectors/webhook",
            )

        raw_body = await request.body()
        expected = "sha256=" + hmac.new(secret.encode(), raw_body, hashlib.sha256).hexdigest()
        provided = request.headers.get("x-clara-signature", "")
        if not hmac.compare_digest(expected, provided):
            raise HTTPException(status_code=401, detail="Invalid webhook signature")

        try:
            payload = json.loads(raw_body)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail="Body must be valid JSON") from exc
        rows = payload.get("signals") if isinstance(payload, dict) else payload
        if not isinstance(rows, list) or not rows:
            raise HTTPException(
                status_code=422,
                detail='Expected {"signals": [...]} or a non-empty JSON array',
            )
        if len(rows) > 1000:
            raise HTTPException(status_code=422, detail="Max 1000 signals per webhook call")

        records = [
            signal_from_row(
                {key: str(value) for key, value in row.items() if value is not None},
                default_source="webhook",
            )
            for row in rows
            if isinstance(row, dict)
        ]
        records = [record for record in records if record.feedback_text.strip()]
        if not records:
            raise HTTPException(status_code=422, detail="No rows with feedback_text")

        result = signal_store.import_signals(records)
        telemetry_store.record(
            "signals_imported",
            metadata={"source": "webhook", "imported": result.imported, "skipped": result.skipped_duplicates},
        )
        return result

    @api.post("/signals/validate-csv", response_model=SignalValidationReport)
    def validate_signal_csv_import(request: SignalCsvImportRequest) -> SignalValidationReport:
        return validate_signal_csv(
            request.csv_text,
            existing_signal_ids=signal_store.existing_signal_ids(),
        )

    @api.get("/journey-events", response_model=list[JourneyEventRecord], dependencies=[read_dep])
    def list_journey_events() -> list[JourneyEventRecord]:
        return journey_event_store.list_events()

    @api.post("/journey-events/import", response_model=JourneyEventImportResult, dependencies=[Depends(require_role(Role.editor))])
    def import_journey_events(request: JourneyEventImportRequest) -> JourneyEventImportResult:
        return journey_event_store.import_events(request.events)

    @api.post("/journey-events/import-csv", response_model=JourneyEventImportResult, dependencies=[Depends(require_role(Role.editor))])
    def import_journey_event_csv(request: JourneyEventCsvImportRequest) -> JourneyEventImportResult:
        return journey_event_store.import_events(parse_journey_event_csv(request.csv_text))

    @api.get("/customer-context", response_model=list[CustomerContextRecord], dependencies=[read_dep])
    def list_customer_context() -> list[CustomerContextRecord]:
        return context_store.list_context()

    @api.get(
        "/customer-context/completeness",
        response_model=CustomerContextCompletenessReport,
        dependencies=[read_dep],
    )
    def get_customer_context_completeness() -> CustomerContextCompletenessReport:
        return context_completeness_report(context_store.list_context())

    @api.post("/customer-context/import", response_model=CustomerContextImportResult, dependencies=[Depends(require_role(Role.editor))])
    def import_customer_context(
        request: CustomerContextImportRequest,
    ) -> CustomerContextImportResult:
        return context_store.import_context(request.records)

    @api.post("/customer-context/import-csv", response_model=CustomerContextImportResult, dependencies=[Depends(require_role(Role.editor))])
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

    @api.get("/policy-rules", response_model=list[PolicyRule], dependencies=[read_dep])
    def list_policy_rules() -> list[PolicyRule]:
        return policy_store.list_rules()

    @api.get("/taxonomies", response_model=list[TaxonomyCatalog], dependencies=[read_dep])
    def list_taxonomies() -> list[TaxonomyCatalog]:
        return taxonomy_store.list_catalogs()

    @api.get("/terminology-dictionary", response_model=list[TerminologyDictionaryEntry], dependencies=[read_dep])
    def list_terminology_dictionary() -> list[TerminologyDictionaryEntry]:
        return terminology_store.list_entries()

    @api.get("/language-quality", dependencies=[read_dep])
    def get_language_quality() -> dict:
        return build_language_quality_report(signal_store.list_signals(), terminology_store.list_entries())

    @api.post("/taxonomy/bootstrap", dependencies=[Depends(require_role(Role.editor))])
    def bootstrap_taxonomy_from_signals(body: dict | None = None) -> dict:
        """Cluster the workspace's signals into proposed taxonomy categories.

        The governed "no taxonomy to build" path: embeddings cluster the signals,
        the LLM names each cluster, and proposals land as status='proposed'
        categories (confidence-scored) awaiting human accept/reject.
        """
        from app.services.taxonomy_bootstrap import bootstrap_taxonomy

        body = body or {}
        taxonomy_type = TaxonomyType(body.get("taxonomy_type", "contact_reason"))
        limit = min(int(body.get("limit", 200)), 1000)

        report = bootstrap_taxonomy(
            signal_store.list_signals(),
            taxonomy_store,
            taxonomy_type=taxonomy_type,
            limit=limit,
        )
        if report.get("error") == "embedding_failed":
            raise HTTPException(
                status_code=502,
                detail="Embedding provider unavailable — taxonomy bootstrap aborted (no partial writes)",
            )
        telemetry_store.record(
            "taxonomy_bootstrapped",
            metadata={
                "taxonomy_type": taxonomy_type.value,
                "scanned": report["scanned"],
                "proposed": report["proposed"],
            },
        )
        return report

    @api.post("/taxonomies/{taxonomy_type}/categories/review", response_model=TaxonomyCatalog, dependencies=[Depends(require_role(Role.editor))])
    def review_taxonomy_category(
        taxonomy_type: TaxonomyType,
        request: TaxonomyReviewRequest,
    ) -> TaxonomyCatalog:
        catalog = taxonomy_store.review_category(
            taxonomy_type,
            category_id=request.category_id,
            decision=request.decision,
            actor=request.actor,
        )
        telemetry_store.record(
            "taxonomy_reviewed",
            entity_id=request.category_id,
            metadata={"decision": request.decision},
        )
        return catalog

    @api.post("/taxonomies/{taxonomy_type}/categories/rename", response_model=TaxonomyCatalog, dependencies=[Depends(require_role(Role.editor))])
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

    @api.post("/taxonomies/{taxonomy_type}/categories/lock", response_model=TaxonomyCatalog, dependencies=[Depends(require_role(Role.editor))])
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

    @api.post("/taxonomies/{taxonomy_type}/categories/merge", response_model=TaxonomyCatalog, dependencies=[Depends(require_role(Role.editor))])
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

    @api.post("/taxonomies/{taxonomy_type}/categories/split", response_model=TaxonomyCatalog, dependencies=[Depends(require_role(Role.editor))])
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

    @api.get("/policy-rules/{rule_id}", response_model=PolicyRule, dependencies=[read_dep])
    def get_policy_rule(rule_id: str) -> PolicyRule:
        policy_rule = policy_store.get_rule(rule_id)
        if policy_rule is None:
            raise HTTPException(status_code=404, detail="Policy rule not found")

        return policy_rule

    @api.get("/demo-datasets", response_model=list[DemoDatasetSummary], dependencies=[read_dep])
    def list_demo_datasets() -> list[DemoDatasetSummary]:
        return [to_demo_dataset_summary(dataset) for dataset in active_demo_datasets]

    @api.post("/demo-datasets/{dataset_id}/import", response_model=DemoDatasetImportResult, dependencies=[Depends(require_role(Role.editor))])
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

    @api.get("/problem-candidates", response_model=list[ProblemCandidate], dependencies=[read_dep])
    def list_problem_candidates() -> list[ProblemCandidate]:
        return current_candidates()

    @api.get("/emerging-problems", response_model=EmergingProblemReport, dependencies=[read_dep])
    def list_emerging_problems() -> EmergingProblemReport:
        return build_emerging_problem_report(current_candidates())

    @api.post("/problem-candidates/{candidate_id}/promote", response_model=ProblemRecord, dependencies=[Depends(require_role(Role.editor))])
    def promote_problem_candidate(candidate_id: str) -> ProblemRecord:
        candidate = require_candidate(candidate_id)
        problem = promote_candidate(candidate)
        existing_problem = active_problem_store.get_problem(problem.problem_id)
        if existing_problem is not None:
            return enrich_problem_for_response(existing_problem)

        return enrich_problem_for_response(active_problem_store.upsert_problem(problem))

    @api.post("/problem-candidates/{candidate_id}/accept", response_model=ProblemRecord, dependencies=[Depends(require_role(Role.editor))])
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

    @api.post("/problem-candidates/{candidate_id}/reject", response_model=ProblemCandidate, dependencies=[Depends(require_role(Role.editor))])
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

    @api.post("/problems/{problem_id}/approvals", response_model=ApprovalRecord, dependencies=[Depends(require_role(Role.editor))])
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

    @api.get("/problems/{problem_id}/evidence-pack", dependencies=[read_dep])
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

    @api.get("/problems/{problem_id}/workflow", response_model=WorkflowState, dependencies=[read_dep])
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

    @api.post("/problems/{problem_id}/outcomes", response_model=OutcomeMeasurement, dependencies=[Depends(require_role(Role.editor))])
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

    @api.post("/problems/{problem_id}/closure", response_model=ClosureRecord, dependencies=[Depends(require_role(Role.editor))])
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

    @api.post(
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

    @api.get("/problems/{problem_id}/outcome", response_model=OutcomeSnapshot, dependencies=[read_dep])
    def get_outcome_snapshot(problem_id: str) -> OutcomeSnapshot:
        problem = require_problem(problem_id)
        return workflow_store.outcome_snapshot(problem)

    @api.get("/outcome-board", response_model=OutcomeBoard, dependencies=[read_dep])
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

    @api.get("/approvals", response_model=list[ApprovalRecord], dependencies=[read_dep])
    def list_approvals() -> list[ApprovalRecord]:
        return workflow_store.list_approvals()

    @api.get("/executions", response_model=list[ExecutionRecord], dependencies=[read_dep])
    def list_executions() -> list[ExecutionRecord]:
        return workflow_store.list_executions()

    @api.get("/jira-drafts", response_model=list[JiraIssueDraft], dependencies=[read_dep])
    def list_jira_drafts() -> list[JiraIssueDraft]:
        return workflow_store.list_jira_issue_drafts()

    @api.get("/measurements", dependencies=[read_dep])
    def list_measurement_plans() -> list[dict]:
        """Scheduled outcome re-measurement checkpoints (pending/done/manual_required)."""
        return measurement_plan_store.list_plans()

    @api.post("/measurements/run-due", dependencies=[Depends(require_role(Role.editor))])
    def run_due_measurement_plans(body: dict | None = None) -> dict:
        """Process due checkpoints now (the background loop does this every 15 min).

        Optional body {"now": "<iso>"} lets demos/tests advance the clock.
        """
        return _run_due_measurements(now=(body or {}).get("now"))

    @api.get("/customers/{customer_id}/data-export", dependencies=[Depends(require_role(Role.admin))])
    def export_customer_data(customer_id: str) -> dict:
        """GDPR Art. 20 (portability): everything CLARA holds about one customer."""
        signals = [
            s.model_dump(mode="json") for s in signal_store.list_signals()
            if s.customer_id == customer_id
        ]
        events = [
            e.model_dump(mode="json") for e in journey_event_store.list_events()
            if e.customer_id == customer_id
        ]
        context = [
            c.model_dump(mode="json") for c in context_store.list_context()
            if c.customer_id == customer_id
        ]
        evidence_appearances = [
            {"problem_id": p.problem_id, "excerpt": ev.excerpt, "timestamp": ev.timestamp}
            for p in active_problem_store.list_problems()
            for ev in p.evidence
            if ev.customer_id == customer_id
        ]
        telemetry_store.record(
            "gdpr_export",
            metadata={
                "signals": len(signals),
                "journey_events": len(events),
                "context_records": len(context),
                "evidence_appearances": len(evidence_appearances),
            },
        )
        return {
            "customer_id": customer_id,
            "exported_at": utc_now(),
            "signals": signals,
            "journey_events": events,
            "customer_context": context,
            "problem_evidence_appearances": evidence_appearances,
        }

    @api.delete("/customers/{customer_id}/data", dependencies=[Depends(require_role(Role.admin))])
    def erase_customer_data(customer_id: str) -> dict:
        """GDPR Art. 17 (erasure): delete/scrub a customer across every store.

        Signals, journey events and the context record are deleted; evidence
        excerpts inside draft problems are scrubbed (entry kept, content erased,
        so aggregate counts stay honest). The telemetry event deliberately does
        NOT retain the erased identifier.
        """
        # All-or-nothing: a silent PARTIAL erasure would be a compliance failure.
        # Postgres stores gain these methods in the DB-connected workstream.
        erasers = {
            "signals": getattr(signal_store, "delete_by_customer", None),
            "journey_events": getattr(journey_event_store, "delete_by_customer", None),
            "context_records": getattr(context_store, "delete_by_customer", None),
            "problems_scrubbed": getattr(active_problem_store, "scrub_customer", None),
        }
        missing = [name for name, fn in erasers.items() if fn is None]
        if missing:
            raise HTTPException(
                status_code=501,
                detail=f"Erasure not supported by this deployment backend yet for: {', '.join(missing)}",
            )
        deleted = {name: fn(customer_id) for name, fn in erasers.items()}
        telemetry_store.record("gdpr_erasure", metadata=deleted)  # no customer id retained
        return {
            "erased": deleted,
            "note": (
                "Signals, journey events and context deleted; draft-problem evidence "
                "scrubbed in place. Seed/demo problems contain synthetic data only."
            ),
        }

    @api.post("/digest/slack", dependencies=[Depends(require_role(Role.admin))])
    def send_slack_digest() -> dict:
        """Build the weekly digest and push it to the configured Slack channel.

        Trigger from an external cron (weekly) or manually. Without an active
        Slack connector this still returns the digest text as a preview.
        """
        from app.connectors import get_destination
        from app.connectors.base import ConnectorError
        from app.services.digest import build_digest

        digest_text = build_digest(
            emerging=build_emerging_problem_report(current_candidates()),
            outcome_board=build_outcome_board(active_problem_store.list_problems(), workflow_store),
            measurement_plans=measurement_plan_store.list_plans(),
        )

        slack_config = connector_config_store.get_config("slack")
        if slack_config is None or not slack_config.is_active:
            return {"pushed": False, "reason": "No active Slack connector", "preview": digest_text}

        connector = get_destination("slack")
        try:
            result = connector.push(
                {"title": "CLARA weekly digest", "description": digest_text},
                slack_config.config,
            )
        except ConnectorError as exc:
            return {"pushed": False, "reason": str(exc)[:200], "preview": digest_text}

        telemetry_store.record("digest_sent", metadata={"channel": "slack"})
        return {"pushed": True, "external_id": result.get("external_id"), "preview": digest_text}

    @api.get("/telemetry", dependencies=[Depends(require_role(Role.admin))])
    def get_telemetry(limit: int = 200) -> dict:
        """Product-metric events (admin): counts by type + recent events.

        Powers the pilot/VC metrics: time-to-first-insight, approval-cycle time,
        outcome-completion rate, learning-reuse rate. Data never leaves this DB.
        """
        return {
            "counts": telemetry_store.counts_by_type(),
            "events": telemetry_store.list_events(limit=min(limit, 1000)),
        }

    @api.get("/audit-export", dependencies=[Depends(require_role(Role.admin))])
    def export_audit_log() -> dict:
        return {
            "approvals": [
                record.model_dump(mode="json", by_alias=True) for record in workflow_store.list_approvals()
            ],
            "executions": [record.model_dump(mode="json", by_alias=True) for record in workflow_store.list_executions()],
            "closure_records": [
                record.model_dump(mode="json", by_alias=True) for record in workflow_store.list_closure_records()
            ],
            "jira_issue_drafts": [
                record.model_dump(mode="json", by_alias=True) for record in workflow_store.list_jira_issue_drafts()
            ],
        }

    @api.get("/workspace", response_model=WorkspaceSettings, dependencies=[read_dep])
    def get_workspace(user: UserContext = Depends(get_current_user)) -> WorkspaceSettings:  # noqa: B008
        return workspace_store.get(user.workspace_id)

    @api.put(
        "/workspace",
        response_model=WorkspaceSettings,
        dependencies=[Depends(require_role(Role.editor))],
    )
    def update_workspace(
        settings: WorkspaceSettings,
        user: UserContext = Depends(get_current_user),  # noqa: B008
    ) -> WorkspaceSettings:
        return workspace_store.put(user.workspace_id, settings)

    @api.get("/system-config", response_model=SystemConfig, dependencies=[read_dep])
    def get_system_config() -> SystemConfig:
        from app.auth import AUTH_ENABLED

        return SystemConfig(
            ai_base_url=os.getenv("AI_BASE_URL") or "https://api.openai.com/v1",
            ai_model=os.getenv("AI_MODEL") or "gpt-4o-mini",
            auth_enabled=AUTH_ENABLED,
        )

    @api.get("/rules", response_model=list[FeedbackRule], dependencies=[read_dep])
    def list_rules() -> list[FeedbackRule]:
        return rule_store.list_rules()

    @api.post(
        "/rules",
        response_model=FeedbackRule,
        dependencies=[Depends(require_role(Role.editor))],
    )
    def create_rule(rule: FeedbackRuleCreate) -> FeedbackRule:
        return rule_store.create_rule(rule)

    @api.delete("/rules/{rule_id}", dependencies=[Depends(require_role(Role.editor))])
    def delete_rule(rule_id: str) -> dict:
        if not rule_store.delete_rule(rule_id):
            raise HTTPException(status_code=404, detail="Rule not found")
        return {"rule_id": rule_id, "status": "deleted"}

    # ====== Connector endpoints (Phase 2) ======

    @api.get("/connectors", dependencies=[Depends(require_role(Role.admin))])
    def list_connectors() -> list[dict]:
        return [redacted_connector_config(c) for c in connector_config_store.list_configs()]

    @api.put("/connectors/{connector_type}", dependencies=[Depends(require_role(Role.admin))])
    def upsert_connector(
        connector_type: str,
        config: dict,
    ) -> dict:
        from app.connectors.config_store import ConnectorConfig

        existing = connector_config_store.get_config(connector_type)
        display_name = config.pop("_display_name", existing.display_name if existing else "")
        # Preserve stored secrets when the client sends a blank or masked placeholder
        # (the GET endpoint redacts secrets, so edit forms never carry the real value).
        if existing:
            for key in _SECRET_CONFIG_KEYS:
                incoming = config.get(key)
                if (not incoming or incoming == "***redacted***") and key in existing.config:
                    config[key] = existing.config[key]
        stored_cfg = ConnectorConfig(
            connector_type=connector_type,
            config=config,
            display_name=display_name,
        )
        connector_config_store.upsert_config(stored_cfg)
        return {"connector_type": connector_type, "status": "saved"}

    @api.delete("/connectors/{connector_type}", dependencies=[Depends(require_role(Role.admin))])
    def delete_connector(connector_type: str) -> dict:
        deleted = connector_config_store.delete_config(connector_type)
        if not deleted:
            raise HTTPException(status_code=404, detail="Connector not found")
        return {"connector_type": connector_type, "status": "deleted"}

    @api.post("/connectors/zendesk/pull", dependencies=[Depends(require_role(Role.admin))])
    def pull_zendesk(config: dict | None = None) -> dict:
        """Pull tickets from Zendesk and return mapped signals.

        Uses stored config if no config is provided in the body.
        """
        from app.connectors import get_source
        from app.connectors.base import ConnectorError

        src = get_source("zendesk")
        if src is None:
            raise HTTPException(status_code=400, detail="Zendesk connector not available")

        stored = connector_config_store.get_config("zendesk")
        pull_config = config or {}
        if not pull_config:
            if stored is None:
                raise HTTPException(
                    status_code=400,
                    detail="No Zendesk config — configure via PUT /connectors/zendesk",
                )
            pull_config = stored.config

        try:
            raw_signals = src.pull(pull_config)
        except ConnectorError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc

        # Import into the signal store (dedup by zd-<id>) — previously the pull
        # only RETURNED the tickets and they never landed in /signals.
        last_synced_at = None
        records = []
        for item in raw_signals:
            sync_meta = item.pop("_sync_metadata", None)
            if sync_meta and sync_meta.get("last_synced_at"):
                last_synced_at = sync_meta["last_synced_at"]
            metadata = {
                key: value if isinstance(value, str) else json.dumps(value)
                for key, value in (item.get("metadata") or {}).items()
            }
            records.append(SignalRecord.model_validate({**item, "metadata": metadata}))
        result = signal_store.import_signals(records)

        # Persist the incremental cursor so the next pull fetches only new/updated
        # tickets (the connector uses config["last_synced_at"] for the cursor API).
        # Only when pulling with the STORED config — ad-hoc test pulls don't move it.
        if not config and stored is not None and last_synced_at:
            stored.config["last_synced_at"] = last_synced_at
            connector_config_store.upsert_config(stored)

        telemetry_store.record(
            "signals_imported",
            metadata={
                "source": "zendesk",
                "imported": result.imported,
                "skipped": result.skipped_duplicates,
            },
        )
        return {
            "pulled": len(records),
            "imported": result.imported,
            "skipped_duplicates": result.skipped_duplicates,
            "last_synced_at": last_synced_at,
            "signals": raw_signals[:10],
        }

    @api.post("/connectors/test/{connector_type}", dependencies=[Depends(require_role(Role.admin))])
    def test_connector(connector_type: str, config: dict) -> dict:
        """Test a connector configuration without saving it."""
        from app.connectors import get_destination, get_source
        from app.connectors.base import ConnectorError

        if connector_type in ("zendesk",):
            src = get_source(connector_type)
            if src is None:
                raise HTTPException(status_code=400, detail="Unknown source connector")
            try:
                signals = src.pull(config)
                return {"status": "ok", "pulled": len(signals)}
            except ConnectorError as exc:
                return {"status": "error", "message": str(exc)}

        if connector_type in ("jira", "slack"):
            dest = get_destination(connector_type)
            if dest is None:
                raise HTTPException(status_code=400, detail="Unknown destination connector")
            # For testing, send a minimal test action
            test_action = {
                "type": "create_ticket" if connector_type == "jira" else "notify",
                "title": "CLARA connector test",
                "description": "This is a test from the CLARA platform.",
                "priority": 3,
                "insight_title": "Test",
                "insight_summary": "Connector configuration test",
                "insight_severity": "low",
            }
            try:
                result = dest.push(test_action, config)
                return {"status": "ok", "result": result}
            except ConnectorError as exc:
                return {"status": "error", "message": str(exc)}

        raise HTTPException(status_code=400, detail=f"Unknown connector type: {connector_type}")

    # ====== Triage pipeline endpoint ======
    from langgraph.checkpoint.memory import MemorySaver
    from langgraph.types import Command

    from app.agents.triage_graph import build_triage_graph

    # App-scoped graph + checkpointer so a run that pauses at the human-approval
    # interrupt can be RESUMED by a later request (POST /triage/resume). Previously the
    # endpoint built a fresh per-request MemorySaver and discarded it, so the paused
    # state was lost and action/measure/learn never ran for consequential actions —
    # the whole outcome loop was unreachable in production.
    # ponytail: in-process MemorySaver — resume works within one worker. Multi-worker
    # durability needs PostgresSaver (langgraph-checkpoint-postgres is already a dep).
    triage_graph = build_triage_graph(checkpointer=MemorySaver())

    @api.post("/triage/run", dependencies=[Depends(require_role(Role.editor)), Depends(rate_limiter)])
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
            learnings = default_learning_store().load(workspace_id=user.workspace_id)
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

    @api.post("/triage/resume", dependencies=[Depends(require_role(Role.editor)), Depends(rate_limiter)])
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

    return api


app = create_app()
