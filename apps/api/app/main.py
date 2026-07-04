from __future__ import annotations

import logging
import os
from pathlib import Path

import json

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.auth import AUTH_ENABLED
import app.services.ai as ai
from app.domain.models import (
    CandidateDecisionStatus,
    CandidateReviewStatus,
    ProblemCandidate,
    ProblemRecord,
    SignalRecord,
)
from app.routers import connectors as connectors_routes
from app.routers import governance as governance_routes
from app.routers import measurement as measurement_routes
from app.routers import problems as problems_routes
from app.routers import signals as signals_routes
from app.routers import system as system_routes
from app.routers import taxonomy as taxonomy_routes
from app.routers.problems import build_outcome_board
from app.services.context_impact import (
    enrich_problem_with_context,
)
from app.services.contexts import (
    SQLiteCustomerContextStore,
)
from app.services.emerging import build_emerging_problem_report
from app.services.journeys import (
    SQLiteJourneyEventStore,
    enrich_problem_with_journey,
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
    PostgresTelemetryStore,
    PostgresMeasurementPlanStore,
    PostgresConnectorConfigStore,
    PostgresApiKeyStore,
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
)
from app.services.signals import (
    SQLiteSignalStore,
)
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


def review_match_key(value: str) -> str:
    return value.replace("_", " ").strip().lower()


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
    api_keys=None,
) -> FastAPI:
    api = FastAPI(
        title="CLARA API",
        version="0.1.0",
        summary="Feedback-to-Outcome API prototype",
        # With auth on, public Swagger/OpenAPI would enumerate the admin surface.
        docs_url=None if AUTH_ENABLED else "/docs",
        redoc_url=None if AUTH_ENABLED else "/redoc",
        openapi_url=None if AUTH_ENABLED else "/openapi.json",
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
    _pg_url = database_url()
    telemetry_store = telemetry or (
        PostgresTelemetryStore(_pg_url) if _pg_url else SQLiteTelemetryStore(default_db_path())
    )
    from app.services.measurement_scheduler import (
        SQLiteMeasurementPlanStore,
        attach_measurement_loop,
        run_due_measurements,
    )

    measurement_plan_store = measurement_plans or (
        PostgresMeasurementPlanStore(_pg_url) if _pg_url else SQLiteMeasurementPlanStore(default_db_path())
    )

    def _run_due_measurements(now: str | None = None) -> dict[str, int]:
        return run_due_measurements(
            plan_store=measurement_plan_store,
            problem_lookup=active_problem_store.get_problem,
            signal_store=signal_store,
            workflow_store=workflow_store,
            telemetry=telemetry_store,
            now=now,
        )

    # One background loop, two duties: measurements every tick (15 min), source
    # sync every 4th tick (~hourly). _run_source_sync is defined later in
    # create_app (route section) — Python closures bind late, so by the time the
    # loop first fires the name is resolved.
    _tick_counter = {"n": 0}

    def _background_tick(now: str | None = None) -> dict[str, int]:
        result = _run_due_measurements(now)
        _tick_counter["n"] += 1
        if _tick_counter["n"] % 4 == 1:  # first tick + hourly thereafter
            sync = _run_source_sync()
            result = {**result, **{f"sync_{k}": v for k, v in sync.items()}}
            try:
                alerts = _run_alert_sweep()
                result = {**result, **{f"alert_{k}": v for k, v in alerts.items()}}
            except Exception:  # noqa: BLE001 — alerting must never break the loop
                logger.exception("Alert sweep failed")
        return result

    attach_measurement_loop(api, _background_tick)
    url = database_url()
    taxonomy_store = taxonomies or (PostgresTaxonomyStore(url) if url else TaxonomyStore())
    terminology_store = terminology or (
        PostgresTerminologyStore(url) if url else TerminologyStore()
    )
    active_demo_datasets = demo_datasets or load_demo_datasets()
    from app.connectors.config_store import SQLiteConnectorConfigStore

    # Persistent by default: a pilot's Jira/Zendesk credentials must survive restarts.
    connector_config_store = connector_configs or (
        PostgresConnectorConfigStore(_pg_url) if _pg_url else SQLiteConnectorConfigStore(default_db_path())
    )
    from app.auth import set_api_key_verifier
    from app.services.api_keys import SQLiteApiKeyStore

    api_key_store = api_keys or (
        PostgresApiKeyStore(_pg_url) if _pg_url else SQLiteApiKeyStore(default_db_path())
    )
    set_api_key_verifier(api_key_store.verify)

    # AI runtime config: the Settings GUI persists overrides in the connector
    # config store ("ai" entry, secrets redacted on read like every connector);
    # re-apply on boot so a restart keeps the configured endpoint.
    _ai_stored = connector_config_store.get_config("ai")
    if _ai_stored and _ai_stored.is_active:
        ai.set_runtime_config(
            base_url=_ai_stored.config.get("base_url"),
            model=_ai_stored.config.get("model"),
            api_key=_ai_stored.config.get("api_key"),
        )
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


    def _pull_source_and_import(connector_type: str, config: dict | None = None) -> dict:
        """Shared pull->import->cursor logic for every registered SOURCE connector.

        Used by the manual pull route and the background source-sync loop.
        Cursor is only advanced when pulling with the STORED config.
        """
        from app.connectors import get_source
        from app.connectors.base import ConnectorError

        src = get_source(connector_type)
        if src is None:
            raise HTTPException(
                status_code=404, detail=f"No source connector '{connector_type}'"
            )

        stored = connector_config_store.get_config(connector_type)
        pull_config = config or {}
        if not pull_config:
            if stored is None or not stored.is_active:
                raise HTTPException(
                    status_code=400,
                    detail=f"No active {connector_type} config. configure via PUT /connectors/{connector_type}",
                )
            pull_config = stored.config

        try:
            raw_signals = src.pull(pull_config)
        except ConnectorError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc

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

        if not config and stored is not None and last_synced_at:
            # Re-read before writing: the pull can take seconds and an admin may
            # have edited the config meanwhile. ponytail: re-read shrinks the
            # lost-update window; row versioning if concurrent editing matters.
            fresh = connector_config_store.get_config(connector_type) or stored
            fresh.config["last_synced_at"] = last_synced_at
            connector_config_store.upsert_config(fresh)

        telemetry_store.record(
            "signals_imported",
            metadata={
                "source": connector_type,
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

    def _run_alert_sweep() -> dict[str, int]:
        """Hourly: Slack alerts for new action-grade emerging problems + the
        weekly digest. No-op without an active Slack connector."""
        from app.connectors import get_destination
        from app.services.alerts import run_alert_sweep
        from app.services.digest import build_digest

        def push_slack(title: str, description: str, config: dict) -> None:
            get_destination("slack").push({"title": title, "description": description}, config)

        return run_alert_sweep(
            emerging_report=build_emerging_problem_report(current_candidates()),
            connector_config_store=connector_config_store,
            telemetry=telemetry_store,
            push_slack=push_slack,
            build_digest_text=lambda: build_digest(
                emerging=build_emerging_problem_report(current_candidates()),
                outcome_board=build_outcome_board(
                    active_problem_store.list_problems(), workflow_store
                ),
                measurement_plans=measurement_plan_store.list_plans(),
            ),
        )

    def _run_source_sync() -> dict[str, int]:
        """Background tick: pull every active SOURCE connector. Per-source errors
        are logged and never break the loop or the other sources."""
        from app.connectors import SOURCES

        synced = 0
        failed = 0
        for stored in connector_config_store.list_configs():
            if stored.connector_type not in SOURCES or not stored.is_active:
                continue
            try:
                _pull_source_and_import(stored.connector_type)
                synced += 1
            except HTTPException as exc:
                logger.warning(
                    "Source sync failed for %s: %s", stored.connector_type, exc.detail
                )
                failed += 1
            except Exception:  # noqa: BLE001 — one broken source must not stop the rest
                logger.exception("Source sync crashed for %s", stored.connector_type)
                failed += 1
        return {"synced": synced, "failed": failed}

    # ====== Triage pipeline endpoint ======
    from langgraph.checkpoint.memory import MemorySaver

    from app.agents.triage_graph import build_triage_graph

    # App-scoped graph + checkpointer so a run that pauses at the human-approval
    # interrupt can be RESUMED by a later request (POST /triage/resume). Previously the
    # endpoint built a fresh per-request MemorySaver and discarded it, so the paused
    # state was lost and action/measure/learn never ran for consequential actions —
    # the whole outcome loop was unreachable in production.
    # ponytail: in-process MemorySaver — resume works within one worker. Multi-worker
    # durability needs PostgresSaver (langgraph-checkpoint-postgres is already a dep).
    triage_graph = build_triage_graph(checkpointer=MemorySaver())


    # ====== Domain routers (composition root: stores/closures passed explicitly) ======

    api.include_router(
        system_routes.build_router(
            signal_store=signal_store,
            active_problem_store=active_problem_store,
            workflow_store=workflow_store,
            workspace_store=workspace_store,
            api_key_store=api_key_store,
            telemetry_store=telemetry_store,
            connector_config_store=connector_config_store,
            enrich_problem_for_response=enrich_problem_for_response,
        )
    )
    api.include_router(
        problems_routes.build_router(
            active_problem_store=active_problem_store,
            workflow_store=workflow_store,
            signal_store=signal_store,
            context_store=context_store,
            connector_config_store=connector_config_store,
            telemetry_store=telemetry_store,
            measurement_plan_store=measurement_plan_store,
            require_problem=require_problem,
            enrich_problem_for_response=enrich_problem_for_response,
            list_enriched_problems=list_enriched_problems,
            current_candidates=current_candidates,
            require_candidate=require_candidate,
            triage_graph=triage_graph,
            learning_store_factory=default_learning_store,
        )
    )
    api.include_router(
        connectors_routes.build_router(
            connector_config_store=connector_config_store,
            pull_source_and_import=_pull_source_and_import,
        )
    )
    api.include_router(
        measurement_routes.build_router(
            measurement_plan_store=measurement_plan_store,
            telemetry_store=telemetry_store,
            connector_config_store=connector_config_store,
            active_problem_store=active_problem_store,
            workflow_store=workflow_store,
            run_due_measurements=_run_due_measurements,
            run_alert_sweep=_run_alert_sweep,
            current_candidates=current_candidates,
        )
    )
    api.include_router(
        governance_routes.build_router(
            policy_store=policy_store,
            rule_store=rule_store,
            signal_store=signal_store,
            journey_event_store=journey_event_store,
            context_store=context_store,
            active_problem_store=active_problem_store,
            workflow_store=workflow_store,
            telemetry_store=telemetry_store,
        )
    )
    api.include_router(
        signals_routes.build_router(
            signal_store=signal_store,
            journey_event_store=journey_event_store,
            context_store=context_store,
            telemetry_store=telemetry_store,
            connector_config_store=connector_config_store,
            demo_datasets=active_demo_datasets,
        )
    )
    api.include_router(
        taxonomy_routes.build_router(
            taxonomy_store=taxonomy_store,
            terminology_store=terminology_store,
            signal_store=signal_store,
            telemetry_store=telemetry_store,
        )
    )

    return api


app = create_app()
