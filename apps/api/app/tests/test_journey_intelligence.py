from fastapi.testclient import TestClient

from app.domain.models import JourneyEventRecord
from app.main import create_app
from app.services.contexts import CustomerContextStore
from app.services.journeys import JourneyEventStore, enrich_problem_with_journey
from app.services.problems import ProblemStore
from app.services.seed import load_seed_problems
from app.services.signals import SignalStore
from app.services.workflow import WorkflowStore


def matching_events() -> list[JourneyEventRecord]:
    return [
        JourneyEventRecord(
            event_id="JEV-1",
            customer_id="C-294",
            account_id="A-52",
            journey="Customer onboarding",
            journey_stage="Identity verification",
            event_name="document_rejection_retry",
            event_type="friction",
            timestamp="2026-06-20T11:40:00Z",
            success=False,
        ),
        JourneyEventRecord(
            event_id="JEV-2",
            customer_id="C-301",
            account_id="A-77",
            journey="Customer onboarding",
            journey_stage="Identity verification",
            event_name="generic_guidance_page_view",
            event_type="behavior",
            timestamp="2026-06-20T12:00:00Z",
            success=True,
        ),
    ]


def test_journey_events_raise_problem_journey_intelligence() -> None:
    problem = next(problem for problem in load_seed_problems() if problem.problem_id == "PRB-108")

    enriched = enrich_problem_with_journey(problem, matching_events())

    assert enriched.journey_impact is not None
    assert enriched.journey_impact.matched_events == 2
    assert enriched.journey_impact.friction_events == 1
    assert enriched.journey_impact.matched_accounts == 2
    assert enriched.impact_score is not None
    assert problem.impact_score is not None
    assert enriched.impact_score >= problem.impact_score


def test_journey_event_import_updates_problem_detail_and_summary() -> None:
    journey_store = JourneyEventStore()
    client = TestClient(
        create_app(
            problem_store=ProblemStore(load_seed_problems()),
            workflows=WorkflowStore(),
            signals=SignalStore(),
            contexts=CustomerContextStore(),
            journeys=journey_store,
        )
    )

    response = client.post(
        "/journey-events/import",
        json={"events": [event.model_dump(mode="json") for event in matching_events()]},
    )

    assert response.status_code == 200
    assert response.json()["imported"] == 2

    detail = client.get("/problems/PRB-108").json()
    summary = next(item for item in client.get("/problems").json() if item["problem_id"] == "PRB-108")

    assert detail["journey_impact"]["matched_events"] == 2
    assert detail["journey_impact"]["friction_events"] == 1
    assert summary["journey_impact"] == detail["journey_impact"]
