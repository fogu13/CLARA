from fastapi.testclient import TestClient

from app.main import create_app
from app.services.contexts import CustomerContextStore
from app.services.problems import ProblemStore
from app.services.seed import load_seed_policy_rules, load_seed_problems
from app.services.signals import SignalStore
from app.services.workflow import WorkflowStore


def make_client() -> TestClient:
    return TestClient(
        create_app(
            problem_store=ProblemStore(load_seed_problems()),
            workflows=WorkflowStore(),
            signals=SignalStore(),
            contexts=CustomerContextStore(),
        )
    )


def test_policy_rules_are_listed() -> None:
    client = make_client()

    response = client.get("/policy-rules")

    assert response.status_code == 200
    rules = response.json()
    assert len(rules) >= 6
    assert {rule["rule_id"] for rule in rules} >= {
        "candidate_promotion_requires_evidence",
        "customer_contact_requires_valid_consent",
        "customer_contact_requires_consent_review",
    }


def test_policy_rule_detail_endpoint() -> None:
    client = make_client()

    response = client.get("/policy-rules/customer_contact_requires_consent_review")

    assert response.status_code == 200
    rule = response.json()
    assert rule["default_blocking"]
    assert rule["severity"] == "high"
    assert "consent_status" in rule["required_evidence"]


def test_missing_policy_rule_returns_404() -> None:
    client = make_client()

    response = client.get("/policy-rules/not_a_rule")

    assert response.status_code == 404
    assert response.json()["detail"] == "Policy rule not found"


def test_seed_problem_checks_reference_policy_rules() -> None:
    policy_rule_ids = {rule.rule_id for rule in load_seed_policy_rules()}
    problem = load_seed_problems()[0]

    assert problem.governance_checks
    assert all(check.policy_rule_id in policy_rule_ids for check in problem.governance_checks)


def test_promoted_problem_checks_reference_policy_rules() -> None:
    client = make_client()
    candidate = client.get("/problem-candidates").json()[0]
    problem = client.post(f"/problem-candidates/{candidate['candidate_id']}/promote").json()

    assert problem["governance_checks"]
    assert {
        check["policy_rule_id"]
        for check in problem["governance_checks"]
    } >= {
        "candidate_promotion_requires_evidence",
        "customer_contact_requires_consent_review",
    }
