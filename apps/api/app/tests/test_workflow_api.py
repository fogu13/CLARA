from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.domain.models import ApprovalDecision
from app.main import create_app
from app.services.problems import ProblemStore
from app.services.seed import load_seed_problems
from app.services.workflow import WorkflowStore

client = TestClient(
    create_app(
        problem_store=ProblemStore(load_seed_problems()),
        workflows=WorkflowStore(),
    )
)

# Tenant/actor identity is JWT-bound (auth-disabled tests resolve to the dev
# context: tenant "1", actor "dev-user"). Spoofed-header regression tests live
# in test_tenant_identity.py.


def test_action_dependency_must_be_approved_first() -> None:
    problem = load_seed_problems()[0]
    independent = problem.action_proposals[0].model_copy(update={"depends_on": []})
    dependent = problem.action_proposals[0].model_copy(
        update={"action_id": "ACT-501-DEP", "depends_on": ["ACT-501"]}
    )
    problem = problem.model_copy(update={"action_proposals": [independent, dependent]})
    store = WorkflowStore()

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


def test_approval_creates_execution_record() -> None:
    response = client.post(
        "/problems/PRB-108/approvals",
        json={
            "action_id": "ACT-501",
            "decision": "approved",
            "reviewer": "test_product_owner",
            "note": "Looks ready for a Jira draft.",
        },
    )

    assert response.status_code == 200
    approval = response.json()
    assert approval["problem_id"] == "PRB-108"
    assert approval["decision"] == "approved"

    workflow = client.get("/problems/PRB-108/workflow").json()
    assert workflow["approvals"]
    assert workflow["executions"]
    assert workflow["executions"][-1]["action_id"] == "ACT-501"
    assert workflow["executions"][-1]["status"] == "draft_created"
    assert workflow["jira_issue_drafts"]
    assert workflow["jira_issue_drafts"][-1]["action_id"] == "ACT-501"
    assert workflow["jira_issue_drafts"][-1]["project_key"] == "ODR"
    assert {event["event_type"] for event in workflow["timeline"]} >= {
        "approval_recorded",
        "execution_created",
        "jira_draft_created",
    }

    jira_drafts = client.get("/jira-drafts").json()
    assert jira_drafts[-1]["problem_id"] == "PRB-108"


def test_non_jira_approval_does_not_create_jira_draft() -> None:
    client = TestClient(
        create_app(
            problem_store=ProblemStore(load_seed_problems()),
            workflows=WorkflowStore(),
        )
    )

    response = client.post(
        "/problems/PRB-108/approvals",
        json={
            "action_id": "ACT-504",
            "decision": "approved",
            "reviewer": "test_research_owner",
        },
    )

    assert response.status_code == 200
    workflow = client.get("/problems/PRB-108/workflow").json()
    assert workflow["executions"][-1]["destination"] == "research_panel"
    assert workflow["jira_issue_drafts"] == []


def test_missing_customer_contact_check_prevents_approval() -> None:
    response = client.post(
        "/problems/PRB-108/approvals",
        json={
            "action_id": "ACT-502",
            "decision": "approved",
            "reviewer": "test_cx_owner",
        },
    )

    assert response.status_code == 409
    assert "blocking governance checks" in response.json()["detail"]


def test_blocking_governance_failure_prevents_approval() -> None:
    response = client.post(
        "/problems/PRB-109/approvals",
        json={
            "action_id": "ACT-510",
            "decision": "approved",
            "reviewer": "test_marketing_owner",
        },
    )

    assert response.status_code == 409
    assert "blocking governance checks" in response.json()["detail"]


def test_closure_record_separates_operational_and_customer_closure() -> None:
    client = TestClient(
        create_app(
            problem_store=ProblemStore(load_seed_problems()),
            workflows=WorkflowStore(),
        )
    )
    response = client.post(
        "/problems/PRB-108/closure",
        json={
            "operational_status": "released",
            "customer_status": "draft_ready",
            "owner": "cx_operations",
            "verified_resolution_facts": ["Document guidance page released."],
            "unresolved_customers": 2,
            "follow_up_channel": "zendesk closure task",
            "limitations": ["Support copy still requires review."],
        },
    )

    assert response.status_code == 200
    closure = response.json()
    assert closure["customer_closure_eligible"] is True
    assert "Draft for human review only" in closure["response_draft"]

    workflow = client.get("/problems/PRB-108/workflow").json()
    assert workflow["closure_records"][-1]["operational_status"] == "released"
    assert "closure_recorded" in {event["event_type"] for event in workflow["timeline"]}


def test_closure_redacts_common_pii() -> None:
    client = TestClient(
        create_app(
            problem_store=ProblemStore(load_seed_problems()),
            workflows=WorkflowStore(),
        )
    )
    response = client.post(
        "/problems/PRB-108/closure",
        json={
            "operational_status": "released",
            "customer_status": "draft_ready",
            "owner": "cx@example.com",
            "verified_resolution_facts": ["Resolved for CUST-123 after phone +1 555 123 4567."],
            "unresolved_customers": 1,
            "follow_up_channel": "zendesk",
            "limitations": [],
        },
    )

    assert response.status_code == 200
    closure = response.json()
    assert closure["owner"] == "[EMAIL REDACTED]"
    assert "[ID REDACTED]" in closure["verified_resolution_facts"][0]
    assert "[PHONE REDACTED]" in closure["verified_resolution_facts"][0]
    assert closure["tenant_id"] == "1"
    assert closure["actor"] == "dev-user"


def test_closure_records_are_tenant_filtered_in_workflow_state() -> None:
    # Store-level contract: the tenant filter hides other tenants' closures.
    # (API-level isolation with real JWTs is covered in test_tenant_identity.py.)
    from app.domain.models import ClosureRecordRequest

    problem = load_seed_problems()[0]
    store = WorkflowStore()
    closure = ClosureRecordRequest(
        operational_status="released",
        customer_status="draft_ready",
        owner="cx_operations",
        verified_resolution_facts=["Resolution released."],
        unresolved_customers=1,
        follow_up_channel="zendesk",
        limitations=[],
    )
    store.record_closure(problem=problem, closure=closure, tenant_id="1", actor="dev-user")

    own = store.state_for_problem(problem, tenant_id="1")
    other = store.state_for_problem(problem, tenant_id="2")

    assert len(own.closure_records) == 1
    assert other.closure_records == []
    assert "closure_recorded" in {event.event_type for event in own.timeline}
    assert "closure_recorded" not in {event.event_type for event in other.timeline}


def test_closure_unresolved_customers_cannot_exceed_affected_cohort() -> None:
    client = TestClient(
        create_app(
            problem_store=ProblemStore(load_seed_problems()),
            workflows=WorkflowStore(),
        )
    )
    response = client.post(
        "/problems/PRB-108/closure",
        json={
            "operational_status": "released",
            "customer_status": "draft_ready",
            "owner": "cx_operations",
            "verified_resolution_facts": ["Resolution released."],
            "unresolved_customers": 999,
            "follow_up_channel": "zendesk",
            "limitations": [],
        },
    )

    assert response.status_code == 422


def test_outcome_measurement_updates_snapshot() -> None:
    measurement = {
        "problem_id": "PRB-108",
        "metric": "verification_completion_7d",
        "observed_value": 0.72,
        "measured_at": "2026-07-20T12:00:00Z",
        "notes": "Pilot holdout readout.",
    }

    response = client.post("/problems/PRB-108/outcomes", json=measurement)

    assert response.status_code == 200
    snapshot = client.get("/problems/PRB-108/outcome").json()
    assert snapshot["latest_value"] == 0.72
    assert snapshot["status"] == "target_met"

    workflow = client.get("/problems/PRB-108/workflow").json()
    assert "outcome_measured" in {event["event_type"] for event in workflow["timeline"]}


def test_learning_conclusion_requires_measured_outcome() -> None:
    client = TestClient(
        create_app(
            problem_store=ProblemStore(load_seed_problems()),
            workflows=WorkflowStore(),
        )
    )

    response = client.post(
        "/problems/PRB-108/learning-conclusions",
        json={
            "learning_status": "inconclusive",
            "summary": "No readout yet.",
            "limitations": "Outcome has not been measured.",
        },
    )

    assert response.status_code == 409


def test_learning_conclusion_records_review_and_redacts_common_pii() -> None:
    client = TestClient(
        create_app(
            problem_store=ProblemStore(load_seed_problems()),
            workflows=WorkflowStore(),
        )
    )
    client.post(
        "/problems/PRB-108/outcomes",
        json={
            "problem_id": "PRB-108",
            "metric": "verification_completion_7d",
            "observed_value": 0.72,
            "measured_at": "2026-07-20T12:00:00Z",
        },
    )

    response = client.post(
        "/problems/PRB-108/learning-conclusions",
        json={
            "learning_status": "worked",
            "summary": "Worked for jane@example.com from 192.168.1.1.",
            "limitations": "Small sample, call +1 555 123 4567 not retained for CUST-123.",
            "next_step": "Scale after support review.",
        },
    )

    assert response.status_code == 200
    conclusion = response.json()
    assert conclusion["learning_status"] == "worked"
    assert conclusion["tenant_id"] == "1"
    assert conclusion["reviewer"] == "dev-user"
    assert conclusion["retention_expires_at"] is not None
    assert conclusion["summary"] == "Worked for [EMAIL REDACTED] from [IP REDACTED]."
    assert "[PHONE REDACTED]" in conclusion["limitations"]
    assert "[ID REDACTED]" in conclusion["limitations"]

    workflow = client.get("/problems/PRB-108/workflow").json()
    assert workflow["learning_conclusions"][-1]["conclusion_id"] == conclusion["conclusion_id"]
    assert "learning_reviewed" in {event["event_type"] for event in workflow["timeline"]}


def test_learning_conclusion_uses_verified_identity_without_headers() -> None:
    """Identity is server-derived: no headers required (auth-disabled -> dev
    context), and the recorded tenant/reviewer are the verified principal's."""
    client = TestClient(
        create_app(
            problem_store=ProblemStore(load_seed_problems()),
            workflows=WorkflowStore(),
        )
    )
    client.post(
        "/problems/PRB-108/outcomes",
        json={
            "problem_id": "PRB-108",
            "metric": "verification_completion_7d",
            "observed_value": 0.72,
            "measured_at": "2026-07-20T12:00:00Z",
        },
    )

    response = client.post(
        "/problems/PRB-108/learning-conclusions",
        json={
            "learning_status": "worked",
            "summary": "Worked.",
            "limitations": "None noted.",
        },
    )

    assert response.status_code == 200
    assert response.json()["tenant_id"] == "1"
    assert response.json()["reviewer"] == "dev-user"
