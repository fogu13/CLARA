from pathlib import Path

import pytest

from app.domain.models import ApprovalDecision, ClosureRecordRequest, LearningConclusionRequest, OutcomeMeasurement
from fastapi import HTTPException
from app.services.seed import load_seed_problems
from app.services.workflow import SQLiteWorkflowStore, action_snapshot


def test_sqlite_store_persists_approvals_and_executions(tmp_path: Path) -> None:
    problem = load_seed_problems()[0]
    db_path = tmp_path / "workflow.db"

    first_store = SQLiteWorkflowStore(db_path)
    first_store.record_approval(
        problem=problem,
        decision=ApprovalDecision(
            action_id="ACT-501",
            decision="approved",
            reviewer="test_product_owner",
        ),
    )

    second_store = SQLiteWorkflowStore(db_path)
    state = second_store.state_for_problem(problem)

    assert state.approvals[0].action_id == "ACT-501"
    assert state.approvals[0].action_snapshot is not None
    assert state.executions[0].status == "draft_created"
    assert state.jira_issue_drafts[0].action_id == "ACT-501"
    assert state.jira_issue_drafts[0].execution_id == state.executions[0].execution_id
    assert "verification" in state.jira_issue_drafts[0].description.lower()


def test_sqlite_store_persists_approval_action_diff(tmp_path: Path) -> None:
    problem = load_seed_problems()[0]
    action = problem.action_proposals[0]
    edited_action = action.model_copy(
        update={
            "owner": "edited_owner",
            "original_snapshot": action_snapshot(action),
        }
    )
    problem = problem.model_copy(
        update={"action_proposals": [edited_action, *problem.action_proposals[1:]]}
    )
    db_path = tmp_path / "workflow.db"

    first_store = SQLiteWorkflowStore(db_path)
    first_store.record_approval(
        problem=problem,
        decision=ApprovalDecision(
            action_id="ACT-501",
            decision="approved",
            reviewer="test_product_owner",
        ),
    )

    second_store = SQLiteWorkflowStore(db_path)
    approval = second_store.state_for_problem(problem).approvals[0]

    assert approval.action_snapshot is not None
    assert approval.action_snapshot.owner == "edited_owner"
    assert approval.action_diff[0].field == "owner"
    assert approval.action_diff[0].before == action.owner
    assert approval.action_diff[0].after == "edited_owner"


def test_sqlite_store_blocks_approval_until_dependency_approved(tmp_path: Path) -> None:
    problem = load_seed_problems()[0]
    independent = problem.action_proposals[0].model_copy(update={"depends_on": []})
    dependent = problem.action_proposals[0].model_copy(
        update={"action_id": "ACT-501-DEP", "depends_on": ["ACT-501"]}
    )
    problem = problem.model_copy(update={"action_proposals": [independent, dependent]})
    store = SQLiteWorkflowStore(tmp_path / "workflow.db")

    try:
        store.record_approval(
            problem=problem,
            decision=ApprovalDecision(
                action_id="ACT-501-DEP",
                decision="approved",
                reviewer="test_reviewer",
            ),
        )
    except HTTPException as exc:
        assert exc.status_code == 409
        assert "dependencies are approved" in exc.detail
    else:
        raise AssertionError("dependent action was approved before its dependency")

    store.record_approval(
        problem=problem,
        decision=ApprovalDecision(
            action_id="ACT-501",
            decision="approved",
            reviewer="test_reviewer",
        ),
    )
    follow_up = store.record_approval(
        problem=problem,
        decision=ApprovalDecision(
            action_id="ACT-501-DEP",
            decision="approved",
            reviewer="test_reviewer",
        ),
    )
    assert follow_up.decision.value == "approved"


def test_rejection_revokes_dependency_and_repeat_approval_is_blocked(tmp_path: Path) -> None:
    problem = load_seed_problems()[0]
    independent = problem.action_proposals[0].model_copy(update={"depends_on": []})
    dependent = problem.action_proposals[0].model_copy(
        update={"action_id": "ACT-501-DEP", "depends_on": ["ACT-501"]}
    )
    problem = problem.model_copy(update={"action_proposals": [independent, dependent]})
    store = SQLiteWorkflowStore(tmp_path / "workflow.db")

    store.record_approval(
        problem=problem,
        decision=ApprovalDecision(action_id="ACT-501", decision="approved", reviewer="r"),
    )

    # Re-approving an already-approved action must 409, not mint a second execution.
    with pytest.raises(HTTPException) as exc_info:
        store.record_approval(
            problem=problem,
            decision=ApprovalDecision(action_id="ACT-501", decision="approved", reviewer="r"),
        )
    assert exc_info.value.status_code == 409
    assert len(store.state_for_problem(problem).executions) == 1

    # A corrective rejection is the LATEST decision, so the dependency gate
    # must treat ACT-501 as no longer approved.
    store.record_approval(
        problem=problem,
        decision=ApprovalDecision(action_id="ACT-501", decision="rejected", reviewer="r"),
    )
    with pytest.raises(HTTPException) as exc_info:
        store.record_approval(
            problem=problem,
            decision=ApprovalDecision(action_id="ACT-501-DEP", decision="approved", reviewer="r"),
        )
    assert exc_info.value.status_code == 409
    assert "dependencies are approved" in exc_info.value.detail


def test_stale_measurement_cannot_overwrite_newer_one(tmp_path: Path) -> None:
    problem = load_seed_problems()[1]
    store = SQLiteWorkflowStore(tmp_path / "workflow.db")
    metric = problem.outcome_contract.primary_metric

    def measurement(value: float, measured_at: str) -> OutcomeMeasurement:
        return OutcomeMeasurement(
            problem_id=problem.problem_id,
            metric=metric,
            observed_value=value,
            measured_at=measured_at,
        )

    store.record_outcome(problem=problem, measurement=measurement(5.0, "2026-07-20T12:00:00Z"))

    with pytest.raises(HTTPException) as exc_info:
        store.record_outcome(problem=problem, measurement=measurement(9.0, "2026-07-10T12:00:00Z"))
    assert exc_info.value.status_code == 409
    assert store.outcome_snapshot(problem).latest_value == 5.0

    # Same measured_at = a correction; it supersedes by insertion order.
    store.record_outcome(problem=problem, measurement=measurement(4.0, "2026-07-20T12:00:00Z"))
    assert store.outcome_snapshot(problem).latest_value == 4.0


def test_sqlite_store_classifies_decrease_outcomes(tmp_path: Path) -> None:
    problem = load_seed_problems()[1]
    db_path = tmp_path / "workflow.db"
    store = SQLiteWorkflowStore(db_path)

    store.record_outcome(
        problem=problem,
        measurement=OutcomeMeasurement(
            problem_id=problem.problem_id,
            metric=problem.outcome_contract.primary_metric,
            observed_value=problem.outcome_contract.baseline - 0.001,
            measured_at="2026-07-20T12:00:00Z",
        ),
    )

    second_store = SQLiteWorkflowStore(db_path)
    snapshot = second_store.outcome_snapshot(problem)

    assert snapshot.improvement_direction == "decrease"
    assert snapshot.status == "improving"


def test_sqlite_store_persists_learning_conclusions(tmp_path: Path) -> None:
    problem = load_seed_problems()[0]
    db_path = tmp_path / "workflow.db"
    first_store = SQLiteWorkflowStore(db_path)

    record = first_store.record_learning_conclusion(
        problem=problem,
        conclusion=LearningConclusionRequest(
            learning_status="worked",
            summary="Outcome improved.",
            limitations="Small holdout.",
        ),
        tenant_id="test_tenant",
        actor="test_reviewer",
    )

    second_store = SQLiteWorkflowStore(db_path)
    state = second_store.state_for_problem(problem, tenant_id="test_tenant")

    assert state.learning_conclusions[0].conclusion_id == record.conclusion_id
    assert state.learning_conclusions[0].tenant_id == "test_tenant"
    assert state.learning_conclusions[0].reviewer == "test_reviewer"
    assert state.learning_conclusions[0].retention_expires_at is not None
    latest = second_store.latest_learning_conclusion(problem, tenant_id="test_tenant")
    assert latest is not None
    assert latest.learning_status.value == "worked"
    assert "learning_reviewed" in {event.event_type for event in state.timeline}



def test_sqlite_store_persists_closure_records(tmp_path: Path) -> None:
    problem = load_seed_problems()[0]
    db_path = tmp_path / "workflow.db"
    first_store = SQLiteWorkflowStore(db_path)

    record = first_store.record_closure(
        problem=problem,
        closure=ClosureRecordRequest(
            operational_status="released",
            customer_status="draft_ready",
            owner="cx_operations",
            verified_resolution_facts=["Resolution released."],
            unresolved_customers=2,
            follow_up_channel="zendesk closure task",
            limitations=["Support review required."],
        ),
        tenant_id="test_tenant",
        actor="test_operator",
    )

    second_store = SQLiteWorkflowStore(db_path)
    state = second_store.state_for_problem(problem)

    assert state.closure_records[0].closure_id == record.closure_id
    assert state.closure_records[0].customer_closure_eligible is True
    assert "closure_recorded" in {event.event_type for event in state.timeline}
