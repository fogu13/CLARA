from fastapi.testclient import TestClient

from app.main import create_app
from app.services.problems import ProblemStore
from app.services.seed import load_seed_problems
from app.services.workflow import WorkflowStore


def make_client() -> TestClient:
    return TestClient(
        create_app(
            problem_store=ProblemStore(load_seed_problems()),
            workflows=WorkflowStore(),
        )
    )


TRUSTED_HEADERS = {"x-tenant-id": "test_tenant", "x-actor-id": "test_product_owner"}


def test_outcome_board_lists_problem_outcome_contracts() -> None:
    client = make_client()

    response = client.get("/outcome-board")

    assert response.status_code == 200
    board = response.json()
    assert board["total"] == len(board["items"])
    assert board["not_measured"] == board["total"]
    assert board["not_improved"] == 0
    assert board["improving"] == 0
    assert board["target_met"] == 0

    first_item = board["items"][0]
    assert first_item["problem_id"]
    assert first_item["title"]
    assert first_item["metric"]
    assert first_item["improvement_direction"] in {"increase", "decrease"}
    assert first_item["responsible_owner"]
    assert first_item["outcome_status"] == "not_measured"


def test_outcome_board_reflects_recorded_measurements() -> None:
    client = make_client()
    problem = client.get("/problems/PRB-108").json()
    contract = problem["outcome_contract"]

    response = client.post(
        "/problems/PRB-108/outcomes",
        json={
            "problem_id": "PRB-108",
            "metric": contract["primary_metric"],
            "observed_value": contract["success_threshold"],
            "measured_at": "2026-07-20T12:00:00Z",
            "notes": "Outcome board regression check.",
        },
    )

    assert response.status_code == 200
    board = client.get("/outcome-board").json()
    item = next(item for item in board["items"] if item["problem_id"] == "PRB-108")

    assert board["target_met"] == 1
    assert board["not_measured"] == board["total"] - 1
    assert item["latest_value"] == contract["success_threshold"]
    assert item["outcome_status"] == "target_met"


def test_outcome_board_reflects_decrease_metric_direction() -> None:
    client = make_client()
    problem = client.get("/problems/PRB-109").json()
    contract = problem["outcome_contract"]

    response = client.post(
        "/problems/PRB-109/outcomes",
        json={
            "problem_id": "PRB-109",
            "metric": contract["primary_metric"],
            "observed_value": contract["baseline"] - 0.001,
            "measured_at": "2026-07-20T12:00:00Z",
            "notes": "Lower complaint rate should be improving, not target met.",
        },
    )

    assert response.status_code == 200
    board = client.get("/outcome-board").json()
    item = next(item for item in board["items"] if item["problem_id"] == "PRB-109")

    assert item["improvement_direction"] == "decrease"
    assert item["outcome_status"] == "improving"


def test_outcome_board_shows_latest_learning_conclusion() -> None:
    client = make_client()
    problem = client.get("/problems/PRB-108").json()
    contract = problem["outcome_contract"]
    client.post(
        "/problems/PRB-108/outcomes",
        json={
            "problem_id": "PRB-108",
            "metric": contract["primary_metric"],
            "observed_value": contract["success_threshold"],
            "measured_at": "2026-07-20T12:00:00Z",
        },
    )

    response = client.post(
        "/problems/PRB-108/learning-conclusions",
        headers=TRUSTED_HEADERS,
        json={
            "learning_status": "partially_worked",
            "summary": "Helped a subset of accounts.",
            "limitations": "Pilot cohort was small.",
        },
    )

    assert response.status_code == 200
    board = client.get("/outcome-board", headers={"x-tenant-id": "test_tenant"}).json()
    item = next(item for item in board["items"] if item["problem_id"] == "PRB-108")
    assert board["learning_partially_worked"] == 1
    assert item["latest_learning_status"] == "partially_worked"
    assert item["latest_learning_reviewed_at"] is not None
