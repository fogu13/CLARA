from fastapi.testclient import TestClient

from app.main import create_app
from app.services.problems import ProblemStore
from app.services.seed import load_seed_problems
from app.services.signals import SignalStore, parse_signal_csv
from app.services.workflow import WorkflowStore

CSV_TEXT = """signal_id,customer_id,account_id,source,journey,journey_stage,campaign_exposure,product_events,feedback_text,language,timestamp
SIG-CSV-1,C-900,A-900,csv_upload,checkout,payment,cart_recovery_v1,payment_started;payment_failed,Payment failed twice and support could not explain why.,en,2026-06-21T10:00:00Z
SIG-CSV-2,C-901,A-901,csv_upload,checkout,payment,cart_recovery_v1,payment_started|payment_failed,Die Zahlung bricht immer ab.,de,2026-06-21T10:05:00Z
"""


def make_client() -> TestClient:
    return TestClient(
        create_app(
            problem_store=ProblemStore(load_seed_problems()),
            workflows=WorkflowStore(),
            signals=SignalStore(),
        )
    )


def test_parse_signal_csv_handles_semicolon_and_pipe_lists() -> None:
    signals = parse_signal_csv(CSV_TEXT)

    assert len(signals) == 2
    assert signals[0].product_events == ["payment_started", "payment_failed"]
    assert signals[1].product_events == ["payment_started", "payment_failed"]


def test_csv_import_endpoint_adds_signals_and_candidates() -> None:
    client = make_client()

    response = client.post("/signals/import-csv", json={"csv_text": CSV_TEXT})
    candidates = client.get("/problem-candidates").json()

    assert response.status_code == 200
    assert response.json()["imported"] == 2
    assert any(candidate["journey_stage"] == "Payment" for candidate in candidates)

