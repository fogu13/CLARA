from datetime import date, timedelta

from fastapi.testclient import TestClient

from app.domain.models import CustomerContextRecord
from app.main import create_app
from app.services import context_impact as context_impact_module
from app.services.context_impact import enrich_problem_with_context
from app.services.contexts import CustomerContextStore
from app.services.problems import ProblemStore
from app.services.seed import load_seed_customer_context, load_seed_problems
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


def test_context_impact_uses_evidence_linked_accounts() -> None:
    problem = next(
        problem for problem in load_seed_problems() if problem.problem_id == "PRB-108"
    )

    enriched = enrich_problem_with_context(problem, load_seed_customer_context())

    assert enriched.context_impact is not None
    assert enriched.context_impact.matched_customers == 3
    assert enriched.context_impact.matched_accounts == 2
    assert enriched.context_impact.high_value_accounts == 1
    assert enriched.context_impact.total_account_value == 156000
    assert enriched.context_impact.consent_risk_customers == 1
    assert enriched.context_impact.owners == ["cs_dach", "cs_eu"]
    assert enriched.context_impact.product_owners == [
        "identity_product",
        "onboarding_product",
    ]
    assert enriched.impact_factors.financial_exposure > problem.impact_factors.financial_exposure
    assert enriched.impact_score is not None
    assert problem.impact_score is not None
    assert enriched.impact_score > problem.impact_score


def test_context_impact_keeps_problem_without_matching_context_unchanged() -> None:
    problem = next(
        problem for problem in load_seed_problems() if problem.problem_id == "PRB-109"
    )

    enriched = enrich_problem_with_context(problem, load_seed_customer_context())

    assert enriched.context_impact is None
    assert enriched.impact_score == problem.impact_score
    assert enriched.impact_factors == problem.impact_factors


def test_context_impact_uses_renewal_and_lifecycle_in_priority() -> None:
    problem = next(
        problem for problem in load_seed_problems() if problem.problem_id == "PRB-108"
    )
    context = [
        CustomerContextRecord(
            customer_id="C-294",
            account_id="A-52",
            account_name="Nordlicht Finance",
            lifecycle_stage="renewal",
            account_value=1_000.0,
            renewal_date=(date.today() + timedelta(days=30)).isoformat(),
            consent_status="granted",
            health_score=0.9,
            owner="cs_dach",
        )
    ]

    enriched = enrich_problem_with_context(problem, context)

    assert enriched.context_impact is not None
    assert enriched.context_impact.renewal_risk_accounts == 1
    assert enriched.context_impact.priority_lifecycle_accounts == 1
    assert enriched.context_impact.at_risk_lifecycle_accounts == 0
    assert "renewal risk" in enriched.context_impact.drivers
    assert "lifecycle stage" in enriched.context_impact.drivers
    assert enriched.impact_score > problem.impact_score


class _FrozenDate(date):
    """Pin ``date.today()`` so renewal-risk assertions stop depending on the wall clock.

    The seed context carries fixed renewal dates (2026-11-30); once the real
    calendar drifts inside the 90-day urgency window, ``renewal risk`` appears as
    a driver and this test starts failing for reasons unrelated to any change.
    """

    @classmethod
    def today(cls) -> "date":
        return cls(2026, 7, 1)


def test_problem_api_returns_context_adjusted_priority(monkeypatch) -> None:
    monkeypatch.setattr(context_impact_module, "date", _FrozenDate)
    client = make_client()

    detail_response = client.get("/problems/PRB-108")
    summary_response = client.get("/problems")

    assert detail_response.status_code == 200
    assert summary_response.status_code == 200

    problem = detail_response.json()
    summary = next(
        item for item in summary_response.json() if item["problem_id"] == "PRB-108"
    )

    assert problem["context_impact"]["matched_customers"] == 3
    assert problem["context_impact"]["drivers"] == ["financial exposure", "lifecycle stage"]
    assert problem["context_impact"]["priority_lifecycle_accounts"] == 2
    assert problem["context_impact"]["renewal_risk_accounts"] == 0
    assert problem["context_impact"]["score_delta"] > 0
    assert summary["context_impact"]["score_delta"] == problem["context_impact"]["score_delta"]


def test_affected_context_explorer_rolls_up_matched_accounts() -> None:
    client = make_client()

    response = client.get("/problems/PRB-108/affected-context")

    assert response.status_code == 200
    explorer = response.json()
    assert explorer["problem_id"] == "PRB-108"
    assert explorer["context_impact"]["matched_customers"] == 3
    assert explorer["missing_customer_ids"] == []
    assert explorer["missing_account_ids"] == []
    assert {customer["customer_id"] for customer in explorer["customers"]} == {
        "C-294",
        "C-301",
        "C-318",
    }

    nordlicht = next(
        account for account in explorer["accounts"] if account["account_id"] == "A-52"
    )
    assert nordlicht["account_name"] == "Nordlicht Finance"
    assert nordlicht["parent_account_id"] == "PA-9"
    assert nordlicht["parent_account_name"] == "Nordlicht Group"
    assert nordlicht["customer_count"] == 2
    assert nordlicht["high_value"]
    assert nordlicht["consent_risk_customers"] == 1
    assert nordlicht["contact_roles"] == ["admin", "billing_admin"]
    assert nordlicht["owners"] == ["cs_dach"]
    assert nordlicht["product_owners"] == ["identity_product", "onboarding_product"]

    routing = explorer["routing_recommendations"][0]
    assert routing["owner"] == "cs_dach"
    assert routing["priority"] == "high"
    assert routing["account_ids"] == ["A-52"]
    assert routing["contact_roles"] == ["admin", "billing_admin"]
    assert "parent-account relationship" in routing["reason"]

    warnings = {warning["warning_id"]: warning for warning in explorer["warnings"]}
    assert "PRB-108-consent-risk" in warnings
    assert warnings["PRB-108-consent-risk"]["customer_ids"] == ["C-318"]


def test_affected_context_explorer_reports_missing_context() -> None:
    client = make_client()

    response = client.get("/problems/PRB-109/affected-context")

    assert response.status_code == 200
    explorer = response.json()
    assert explorer["accounts"] == []
    assert explorer["customers"] == []
    assert explorer["routing_recommendations"] == []
    assert explorer["context_impact"] is None
    assert explorer["missing_customer_ids"] == ["C-331"]
    assert explorer["missing_account_ids"] == ["A-331"]
    assert {warning["field"] for warning in explorer["warnings"]} == {
        "customer_id",
        "account_id",
    }
