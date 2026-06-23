from pathlib import Path

from fastapi.testclient import TestClient

from app.domain.models import ProblemStatus
from app.main import create_app
from app.services.problems import ProblemStore, SQLiteProblemStore
from app.services.seed import load_seed_problems, load_seed_signals
from app.services.signals import SignalStore, build_candidates, promote_candidate
from app.services.workflow import SQLiteWorkflowStore, WorkflowStore


def make_client() -> TestClient:
    return TestClient(
        create_app(
            problem_store=ProblemStore(load_seed_problems()),
            workflows=WorkflowStore(),
            signals=SignalStore(),
        )
    )


def promote_first_candidate(client: TestClient) -> str:
    candidate = client.get("/problem-candidates").json()[0]
    problem = client.post(f"/problem-candidates/{candidate['candidate_id']}/promote").json()
    return problem["problem_id"]


def test_promoted_problem_can_transition_status_and_records_timeline() -> None:
    client = make_client()
    problem_id = promote_first_candidate(client)

    response = client.post(
        f"/problems/{problem_id}/transitions",
        json={
            "target_status": "approval_needed",
            "actor": "test_operator",
            "note": "Evidence validated by owner.",
        },
    )

    assert response.status_code == 200
    transition = response.json()
    assert transition["problem_id"] == problem_id
    assert transition["from_status"] == "validation_required"
    assert transition["to_status"] == "approval_needed"

    problem = client.get(f"/problems/{problem_id}").json()
    assert problem["status"] == "approval_needed"

    workflow = client.get(f"/problems/{problem_id}/workflow").json()
    assert workflow["timeline"][0]["event_type"] == "status_changed"
    assert workflow["timeline"][0]["actor"] == "test_operator"
    assert workflow["timeline"][0]["detail"] == "Evidence validated by owner."


def test_duplicate_lifecycle_transition_is_rejected() -> None:
    client = make_client()
    problem_id = promote_first_candidate(client)

    response = client.post(
        f"/problems/{problem_id}/transitions",
        json={"target_status": "validation_required", "actor": "test_operator"},
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "Problem is already in the target status"


def test_seed_problem_lifecycle_transition_is_rejected() -> None:
    client = make_client()

    response = client.post(
        "/problems/PRB-108/transitions",
        json={"target_status": "in_progress", "actor": "test_operator"},
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "Only promoted draft problems can change lifecycle status"


def test_sqlite_lifecycle_state_persists(tmp_path: Path) -> None:
    db_path = tmp_path / "lifecycle.db"
    seed_problems = load_seed_problems()
    candidate = build_candidates(load_seed_signals())[0]
    promoted_problem = promote_candidate(candidate)

    problem_store = SQLiteProblemStore(db_path, seed_problems)
    problem_store.upsert_problem(promoted_problem)
    problem_store.transition_problem_status(
        promoted_problem.problem_id,
        ProblemStatus.approval_needed,
    )

    workflow_store = SQLiteWorkflowStore(db_path)
    workflow_store.record_transition(
        problem=promoted_problem,
        target_status=ProblemStatus.approval_needed,
        actor="test_operator",
        note="Ready for approval.",
    )

    second_problem_store = SQLiteProblemStore(db_path, seed_problems)
    second_workflow_store = SQLiteWorkflowStore(db_path)
    loaded_problem = second_problem_store.get_problem(promoted_problem.problem_id)
    assert loaded_problem is not None
    assert loaded_problem.status == "approval_needed"

    workflow = second_workflow_store.state_for_problem(loaded_problem)
    assert workflow.timeline[0].event_type == "status_changed"
    assert workflow.timeline[0].detail == "Ready for approval."
