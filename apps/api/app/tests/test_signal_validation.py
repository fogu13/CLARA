from fastapi.testclient import TestClient

from app.main import create_app
from app.services.problems import ProblemStore
from app.services.seed import load_seed_problems
from app.services.signals import SignalStore
from app.services.workflow import WorkflowStore


VALID_CSV = """signal_id,customer_id,account_id,source,journey,journey_stage,campaign_exposure,product_events,feedback_text,language,timestamp
SIG-VAL-1,C-1,A-1,csv_upload,onboarding,verification,reminder_v1,verification_started,The instructions are unclear.,en,2026-06-21T10:00:00Z
"""

INVALID_CSV = """signal_id,customer_id,account_id,source,journey,journey_stage,campaign_exposure,product_events,feedback_text,language,timestamp
SIG-VAL-1,C-1,A-1,csv_upload,onboarding,verification,reminder_v1,verification_started,,en,2026-06-21T10:00:00Z
SIG-VAL-1,C-2,A-2,csv_upload,onboarding,verification,reminder_v1,verification_started,Duplicate ID.,en,2026-06-21T10:05:00Z
"""


def make_client() -> TestClient:
    return TestClient(
        create_app(
            problem_store=ProblemStore(load_seed_problems()),
            workflows=WorkflowStore(),
            signals=SignalStore(),
        )
    )


def test_validate_csv_accepts_clean_import() -> None:
    client = make_client()

    response = client.post("/signals/validate-csv", json={"csv_text": VALID_CSV})

    assert response.status_code == 200
    report = response.json()
    assert report["valid"] is True
    assert report["total_rows"] == 1
    assert report["importable_rows"] == 1
    assert report["errors"] == []


def test_validate_csv_reports_missing_values_and_duplicates() -> None:
    client = make_client()

    response = client.post("/signals/validate-csv", json={"csv_text": INVALID_CSV})

    assert response.status_code == 200
    report = response.json()
    assert report["valid"] is False
    assert report["importable_rows"] == 0
    assert any(issue["field"] == "feedback_text" for issue in report["errors"])
    assert any("Duplicate signal_id" in issue["message"] for issue in report["errors"])


def test_import_csv_rejects_invalid_report() -> None:
    client = make_client()

    response = client.post("/signals/import-csv", json={"csv_text": INVALID_CSV})

    assert response.status_code == 422
    assert response.json()["detail"]["valid"] is False


def test_validate_csv_warns_for_existing_signal_ids() -> None:
    client = make_client()
    existing_csv = """signal_id,customer_id,account_id,source,journey,journey_stage,campaign_exposure,product_events,feedback_text,language,timestamp
SIG-20492,C-294,A-52,zendesk,customer_onboarding,identity_verification,verification_reminder_v2,document_rejected,Repeated import.,de,2026-06-20T11:45:00Z
"""

    response = client.post("/signals/validate-csv", json={"csv_text": existing_csv})

    report = response.json()
    assert report["valid"] is True
    assert report["importable_rows"] == 0
    assert any("already exists" in issue["message"] for issue in report["warnings"])

