from pathlib import Path

from fastapi.testclient import TestClient

from app.domain.models import ActionProposalUpdateRequest, ProblemUpdateRequest
from app.main import create_app
from app.services.problems import ProblemStore, SQLiteProblemStore
from app.services.seed import load_seed_problems, load_seed_signals
from app.services.signals import SignalStore, build_candidates, promote_candidate
from app.services.workflow import WorkflowStore


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


def test_promoted_draft_problem_can_be_edited() -> None:
    client = make_client()
    problem_id = promote_first_candidate(client)

    response = client.patch(
        f"/problems/{problem_id}",
        json={
            "title": "Edited verification problem",
            "statement": "Edited statement for the draft problem.",
            "owner": "cx_operations",
        },
    )

    assert response.status_code == 200
    updated = response.json()
    assert updated["title"] == "Edited verification problem"
    assert updated["statement"] == "Edited statement for the draft problem."
    assert updated["owner"] == "cx_operations"
    assert updated["status"] == "validation_required"


def test_seed_problem_edits_are_rejected() -> None:
    client = make_client()

    response = client.patch("/problems/PRB-108", json={"title": "Do not edit seed"})

    assert response.status_code == 409
    assert response.json()["detail"] == "Only promoted draft problems can be edited"


def test_null_edit_fields_do_not_clear_required_problem_fields() -> None:
    client = make_client()
    problem_id = promote_first_candidate(client)
    original = client.get(f"/problems/{problem_id}").json()

    response = client.patch(f"/problems/{problem_id}", json={"title": None, "owner": None})

    assert response.status_code == 200
    updated = response.json()
    assert updated["title"] == original["title"]
    assert updated["owner"] == original["owner"]


def test_promoted_draft_action_proposal_can_be_edited() -> None:
    client = make_client()
    problem_id = promote_first_candidate(client)
    original_problem = client.get(f"/problems/{problem_id}").json()
    action_id = original_problem["action_proposals"][0]["action_id"]

    response = client.patch(
        f"/problems/{problem_id}/actions/{action_id}",
        json={
            "proposal": "Open a Jira investigation with revised acceptance criteria.",
            "owner": "product_triage",
            "destination": "jira",
            "risk_level": "high",
            "approval_state": "ready_for_product_review",
        },
    )

    assert response.status_code == 200
    updated_action = next(
        action for action in response.json()["action_proposals"] if action["action_id"] == action_id
    )
    assert updated_action["proposal"] == "Open a Jira investigation with revised acceptance criteria."
    assert updated_action["owner"] == "product_triage"
    assert updated_action["risk_level"] == "high"
    assert updated_action["approval_state"] == "ready_for_product_review"


def test_action_intervention_brief_can_be_edited_and_diffed() -> None:
    client = make_client()
    problem_id = promote_first_candidate(client)
    original_problem = client.get(f"/problems/{problem_id}").json()
    action = next(
        action for action in original_problem["action_proposals"] if action["class"] == "journey_intervention"
    )
    brief = action["intervention_brief"]
    brief["recommended_channel"] = "hubspot review list"
    brief["content_brief"] = "Updated reviewer-approved intervention brief."

    response = client.patch(
        f"/problems/{problem_id}/actions/{action['action_id']}",
        json={"intervention_brief": brief},
    )

    assert response.status_code == 200
    updated_action = next(
        item for item in response.json()["action_proposals"] if item["action_id"] == action["action_id"]
    )
    assert updated_action["intervention_brief"]["recommended_channel"] == "hubspot review list"
    assert updated_action["original_snapshot"]["intervention_brief"]["recommended_channel"] == "hubspot workflow draft"

    approval = client.post(
        f"/problems/{problem_id}/approvals",
        json={
            "action_id": action["action_id"],
            "decision": "rejected",
            "reviewer": "test_privacy_owner",
        },
    ).json()
    assert "intervention_brief" in {change["field"] for change in approval["action_diff"]}


def test_action_approval_records_edit_diff() -> None:
    client = make_client()
    problem_id = promote_first_candidate(client)
    original_problem = client.get(f"/problems/{problem_id}").json()
    action_id = original_problem["action_proposals"][0]["action_id"]

    client.patch(
        f"/problems/{problem_id}/actions/{action_id}",
        json={
            "proposal": "Open a Jira investigation with revised acceptance criteria.",
            "owner": "product_triage",
            "approval_state": "ready_for_product_review",
        },
    )
    response = client.post(
        f"/problems/{problem_id}/approvals",
        json={
            "action_id": action_id,
            "decision": "approved",
            "reviewer": "test_product_owner",
        },
    )

    assert response.status_code == 200
    approval = response.json()
    assert approval["action_snapshot"]["owner"] == "product_triage"
    assert {change["field"] for change in approval["action_diff"]} == {
        "owner",
        "proposal",
        "approval_state",
    }

    workflow = client.get(f"/problems/{problem_id}/workflow").json()
    recorded = next(item for item in workflow["approvals"] if item["action_id"] == action_id)
    assert recorded["action_diff"] == approval["action_diff"]


def test_seed_problem_action_edits_are_rejected() -> None:
    client = make_client()

    response = client.patch(
        "/problems/PRB-108/actions/ACT-501",
        json={"proposal": "Do not edit seed action"},
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "Only promoted draft problem actions can be edited"


def test_unknown_action_proposal_edit_returns_not_found() -> None:
    client = make_client()
    problem_id = promote_first_candidate(client)

    response = client.patch(
        f"/problems/{problem_id}/actions/ACT-MISSING",
        json={"proposal": "No matching action"},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Action proposal not found"


def test_sqlite_problem_store_persists_edits(tmp_path: Path) -> None:
    db_path = tmp_path / "problems.db"
    seed_problems = load_seed_problems()
    candidate = build_candidates(load_seed_signals())[0]
    promoted_problem = promote_candidate(candidate)

    first_store = SQLiteProblemStore(db_path, seed_problems)
    first_store.upsert_problem(promoted_problem)
    first_store.update_problem(
        promoted_problem.problem_id,
        ProblemUpdateRequest(
            title="Persisted edited draft",
            owner="product_ops",
        ),
    )

    second_store = SQLiteProblemStore(db_path, seed_problems)
    loaded_problem = second_store.get_problem(promoted_problem.problem_id)

    assert loaded_problem is not None
    assert loaded_problem.title == "Persisted edited draft"
    assert loaded_problem.owner == "product_ops"
    assert loaded_problem.status == "validation_required"


def test_sqlite_problem_store_persists_action_edits(tmp_path: Path) -> None:
    db_path = tmp_path / "problems.db"
    seed_problems = load_seed_problems()
    candidate = build_candidates(load_seed_signals())[0]
    promoted_problem = promote_candidate(candidate)
    action_id = promoted_problem.action_proposals[0].action_id

    first_store = SQLiteProblemStore(db_path, seed_problems)
    first_store.upsert_problem(promoted_problem)
    first_store.update_action_proposal(
        promoted_problem.problem_id,
        action_id,
        ActionProposalUpdateRequest(
            proposal="Persisted edited action proposal.",
            owner="product_triage",
            risk_level="high",
        ),
    )

    second_store = SQLiteProblemStore(db_path, seed_problems)
    loaded_problem = second_store.get_problem(promoted_problem.problem_id)

    assert loaded_problem is not None
    loaded_action = next(
        action for action in loaded_problem.action_proposals if action.action_id == action_id
    )
    assert loaded_action.proposal == "Persisted edited action proposal."
    assert loaded_action.owner == "product_triage"
    assert loaded_action.risk_level == "high"
