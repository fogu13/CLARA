from fastapi.testclient import TestClient

from app.main import create_app
from app.services.contexts import CustomerContextStore
from app.services.problems import ProblemStore
from app.services.seed import load_seed_problems
from app.services.signals import SignalStore
from app.services.workflow import WorkflowStore


SIGNAL_CSV = """signal_id,customer_id,account_id,source,journey,journey_stage,campaign_exposure,product_events,feedback_text,language,timestamp
SIG-P0-1,C-900,A-900,zendesk,checkout,payment,cart_recovery_v1,payment_started;payment_failed,Payment failed twice and support could not explain why.,en,2026-06-21T10:00:00Z
SIG-P0-2,C-901,A-901,intercom,checkout,payment,cart_recovery_v1,payment_started;payment_failed,Die Zahlung bricht immer wieder ab.,de,2026-06-21T10:05:00Z
"""

CONTEXT_CSV = """customer_id,account_id,account_name,segment,lifecycle_stage,plan_tier,account_value,renewal_date,consent_status,health_score,owner,region
C-900,A-900,Acme GmbH,mid_market,onboarding,enterprise,88000,2026-12-31,granted,0.76,cs_dach,DACH
C-901,A-901,Beispiel AG,growth,onboarding,pro,42000,2027-01-31,granted,0.69,cs_dach,DACH
"""


def make_client() -> TestClient:
    return TestClient(
        create_app(
            problem_store=ProblemStore(load_seed_problems()),
            workflows=WorkflowStore(),
            signals=SignalStore(),
            contexts=CustomerContextStore(),
        )
    )


def test_phase0_operating_spine_end_to_end() -> None:
    client = make_client()

    context_validation = client.post(
        "/customer-context/validate-csv",
        json={"csv_text": CONTEXT_CSV},
    )
    assert context_validation.status_code == 200
    assert context_validation.json()["valid"]

    context_import = client.post(
        "/customer-context/import-csv",
        json={"csv_text": CONTEXT_CSV},
    )
    assert context_import.status_code == 200
    assert context_import.json()["imported"] == 2

    signal_validation = client.post(
        "/signals/validate-csv",
        json={"csv_text": SIGNAL_CSV},
    )
    assert signal_validation.status_code == 200
    assert signal_validation.json()["valid"]

    signal_import = client.post("/signals/import-csv", json={"csv_text": SIGNAL_CSV})
    assert signal_import.status_code == 200
    assert signal_import.json()["imported"] == 2

    candidates = client.get("/problem-candidates").json()
    candidate = next(
        candidate
        for candidate in candidates
        if candidate["candidate_id"] == "CAND-CHECKOUT-PAYMENT"
    )
    assert candidate["signal_count"] == 2
    assert candidate["customer_count"] == 2

    promoted = client.post(
        f"/problem-candidates/{candidate['candidate_id']}/promote"
    )
    assert promoted.status_code == 200
    problem = promoted.json()
    problem_id = problem["problem_id"]
    assert problem_id == "PRB-DRAFT-CHECKOUT-PAYMENT"
    assert problem["status"] == "validation_required"

    edited = client.patch(
        f"/problems/{problem_id}",
        json={
            "title": "Payment failures during checkout",
            "owner": "payments_product",
            "root_cause_hypothesis": "Imported payment signals point to a repeat checkout failure.",
        },
    )
    assert edited.status_code == 200
    assert edited.json()["title"] == "Payment failures during checkout"

    transition = client.post(
        f"/problems/{problem_id}/transitions",
        json={
            "target_status": "approval_needed",
            "actor": "phase0_tester",
            "note": "Evidence and owner reviewed.",
        },
    )
    assert transition.status_code == 200
    assert transition.json()["to_status"] == "approval_needed"

    approval = client.post(
        f"/problems/{problem_id}/approvals",
        json={
            "action_id": f"ACT-{problem_id}-STRUCTURAL",
            "decision": "approved",
            "reviewer": "phase0_reviewer",
            "note": "Create the execution draft.",
        },
    )
    assert approval.status_code == 200
    assert approval.json()["decision"] == "approved"

    outcome = client.post(
        f"/problems/{problem_id}/outcomes",
        json={
            "problem_id": problem_id,
            "metric": "payment_completion_7d",
            "observed_value": 0.2,
            "measured_at": "2026-07-21T12:00:00Z",
            "notes": "Phase 0 closeout smoke test.",
        },
    )
    assert outcome.status_code == 200

    snapshot = client.get(f"/problems/{problem_id}/outcome").json()
    assert snapshot["status"] == "target_met"

    workflow = client.get(f"/problems/{problem_id}/workflow").json()
    assert workflow["approvals"]
    assert workflow["executions"]
    assert workflow["jira_issue_drafts"]
    assert workflow["jira_issue_drafts"][0]["action_id"] == f"ACT-{problem_id}-STRUCTURAL"
    assert {event["event_type"] for event in workflow["timeline"]} >= {
        "status_changed",
        "approval_recorded",
        "execution_created",
        "jira_draft_created",
        "outcome_measured",
    }
