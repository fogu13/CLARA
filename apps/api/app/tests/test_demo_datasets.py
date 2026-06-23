from fastapi.testclient import TestClient

from app.main import create_app
from app.services.contexts import CustomerContextStore
from app.services.problems import ProblemStore
from app.services.seed import load_seed_problems
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


def test_demo_datasets_are_listed() -> None:
    client = make_client()

    response = client.get("/demo-datasets")

    assert response.status_code == 200
    datasets = response.json()
    dataset_ids = {dataset["dataset_id"] for dataset in datasets}
    assert {"saas_onboarding", "ecommerce_checkout", "retention_cancellation"} <= dataset_ids
    assert all(dataset["signal_count"] > 0 for dataset in datasets)
    assert all(dataset["context_count"] > 0 for dataset in datasets)


def test_demo_dataset_imports_signals_context_and_candidates() -> None:
    client = make_client()

    response = client.post("/demo-datasets/ecommerce_checkout/import")

    assert response.status_code == 200
    result = response.json()
    assert result["dataset_id"] == "ecommerce_checkout"
    assert result["signals"]["imported"] == 3
    assert result["customer_context"]["imported"] == 3

    candidates = client.get("/problem-candidates").json()
    checkout_candidate = next(
        candidate
        for candidate in candidates
        if candidate["candidate_id"] == "CAND-CHECKOUT-PAYMENT"
    )
    assert checkout_candidate["signal_count"] == 3
    assert checkout_candidate["review_status"] == "pending"


def test_demo_dataset_reimport_skips_signal_duplicates_and_updates_context() -> None:
    client = make_client()
    client.post("/demo-datasets/ecommerce_checkout/import")

    response = client.post("/demo-datasets/ecommerce_checkout/import")

    assert response.status_code == 200
    result = response.json()
    assert result["signals"]["imported"] == 0
    assert result["signals"]["skipped_duplicates"] == 3
    assert result["customer_context"]["updated"] == 3


def test_unknown_demo_dataset_returns_not_found() -> None:
    client = make_client()

    response = client.post("/demo-datasets/missing/import")

    assert response.status_code == 404
    assert response.json()["detail"] == "Demo dataset not found"
