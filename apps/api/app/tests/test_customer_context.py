from pathlib import Path

from fastapi.testclient import TestClient

from app.domain.models import CustomerContextRecord
from app.main import create_app
from app.services.contexts import CustomerContextStore, SQLiteCustomerContextStore
from app.services.problems import ProblemStore
from app.services.seed import load_seed_customer_context, load_seed_problems
from app.services.signals import SignalStore
from app.services.workflow import WorkflowStore

VALID_CONTEXT_CSV = """customer_id,account_id,account_name,parent_account_id,parent_account_name,segment,lifecycle_stage,plan_tier,contact_role,account_value,renewal_date,consent_status,health_score,owner,product_owner,region
C-999,A-999,Acme GmbH,PA-1,Acme Holdings,mid_market,onboarding,enterprise,admin,88000,2026-12-31,granted,0.76,cs_dach,onboarding_product,DACH
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


def test_customer_context_is_seeded() -> None:
    client = make_client()

    response = client.get("/customer-context")

    assert response.status_code == 200
    records = response.json()
    assert len(records) == 3
    assert {record["customer_id"] for record in records} >= {"C-294", "C-301", "C-318"}


def test_customer_context_completeness_reports_seed_readiness() -> None:
    client = make_client()

    response = client.get("/customer-context/completeness")

    assert response.status_code == 200
    report = response.json()
    assert report["total_records"] == 3
    assert report["total_accounts"] == 2
    assert report["readiness_level"] == "usable"
    assert report["complete_records"] == 2

    metrics = {metric["field"]: metric for metric in report["metrics"]}
    assert metrics["contact_role"]["coverage"] == 1
    assert metrics["owner"]["coverage"] == 1
    assert metrics["product_owner"]["coverage"] == 1
    assert metrics["renewal_date"]["coverage"] == 1
    assert metrics["consent_status"]["coverage"] == 0.667
    assert report["warnings"][0]["field"] == "consent_status"


def test_customer_context_import_upserts_records() -> None:
    client = make_client()

    response = client.post(
        "/customer-context/import",
        json={
            "records": [
                {
                    "customer_id": "C-999",
                    "account_id": "A-999",
                    "account_name": "Acme GmbH",
                    "parent_account_id": "PA-1",
                    "parent_account_name": "Acme Holdings",
                    "contact_role": "admin",
                    "account_value": 88000,
                    "consent_status": "granted",
                }
            ]
        },
    )

    assert response.status_code == 200
    assert response.json()["imported"] == 1

    update_response = client.post(
        "/customer-context/import",
        json={
            "records": [
                {
                    "customer_id": "C-999",
                    "account_id": "A-999",
                    "account_name": "Acme GmbH",
                    "parent_account_id": "PA-1",
                    "parent_account_name": "Acme Holdings",
                    "contact_role": "admin",
                    "account_value": 92000,
                    "consent_status": "granted",
                }
            ]
        },
    )

    assert update_response.status_code == 200
    assert update_response.json()["updated"] == 1
    records = client.get("/customer-context").json()
    updated = next(record for record in records if record["customer_id"] == "C-999")
    assert updated["account_value"] == 92000
    assert updated["parent_account_id"] == "PA-1"
    assert updated["contact_role"] == "admin"


def test_customer_context_csv_validation_reports_errors() -> None:
    client = make_client()
    invalid_csv = """customer_id,account_id,account_value,health_score
C-999,A-999,not-a-number,1.2
C-999,A-100,12000,0.5
"""

    response = client.post("/customer-context/validate-csv", json={"csv_text": invalid_csv})

    assert response.status_code == 200
    report = response.json()
    assert not report["valid"]
    assert len(report["errors"]) == 3
    assert report["importable_rows"] == 0


def test_customer_context_csv_validation_rejects_non_finite_numbers() -> None:
    # 'nan'/'inf' parse as floats and pass `< 0` checks, but poison every
    # downstream account-value sum — they must be rejected as non-numeric.
    client = make_client()
    csv_text = """customer_id,account_id,account_value,health_score
C-901,A-901,nan,0.5
C-902,A-902,inf,0.5
C-903,A-903,12000,0.5
"""

    response = client.post("/customer-context/validate-csv", json={"csv_text": csv_text})

    assert response.status_code == 200
    report = response.json()
    assert not report["valid"]
    assert len(report["errors"]) == 2
    assert report["importable_rows"] == 1


def test_customer_context_completeness_warns_on_sparse_import() -> None:
    client = make_client()
    response = client.post(
        "/customer-context/import",
        json={
            "records": [
                {
                    "customer_id": "C-SPARSE",
                    "account_id": "A-SPARSE",
                    "account_value": 0,
                    "consent_status": "unknown",
                }
            ]
        },
    )
    assert response.status_code == 200

    report = client.get("/customer-context/completeness").json()
    metrics = {metric["field"]: metric for metric in report["metrics"]}

    assert report["readiness_level"] == "usable"
    assert metrics["contact_role"]["coverage"] == 0.75
    assert metrics["account_value"]["coverage"] == 0.75
    assert {warning["field"] for warning in report["warnings"]} >= {
        "account_value",
        "consent_status",
    }


def test_customer_context_csv_import() -> None:
    client = make_client()

    response = client.post("/customer-context/import-csv", json={"csv_text": VALID_CONTEXT_CSV})

    assert response.status_code == 200
    result = response.json()
    assert result["imported"] == 1
    assert result["total_context_records"] == 4

    records = client.get("/customer-context").json()
    imported = next(record for record in records if record["customer_id"] == "C-999")
    assert imported["parent_account_name"] == "Acme Holdings"
    assert imported["contact_role"] == "admin"


def test_sqlite_customer_context_store_persists_records(tmp_path: Path) -> None:
    db_path = tmp_path / "context.db"
    first_store = SQLiteCustomerContextStore(db_path)
    first_store.import_context(
        [
            CustomerContextRecord(
                customer_id="C-999",
                account_id="A-999",
                account_name="Acme GmbH",
                parent_account_id="PA-1",
                parent_account_name="Acme Holdings",
                contact_role="economic_buyer",
                account_value=88000,
                consent_status="granted",
            )
        ]
    )

    second_store = SQLiteCustomerContextStore(db_path)
    records = second_store.list_context()

    assert len(records) == 1
    assert records[0].customer_id == "C-999"
    assert records[0].account_value == 88000
    assert records[0].parent_account_id == "PA-1"
    assert records[0].contact_role == "economic_buyer"


def test_sqlite_customer_context_store_migrates_older_schema(tmp_path: Path) -> None:
    db_path = tmp_path / "legacy-context.db"
    first_store = SQLiteCustomerContextStore(db_path)
    first_store._connection.execute(
        "ALTER TABLE customer_context RENAME TO customer_context_new"
    )
    first_store._connection.execute(
        """
        CREATE TABLE customer_context (
            customer_id TEXT PRIMARY KEY,
            account_id TEXT NOT NULL,
            account_name TEXT,
            segment TEXT,
            lifecycle_stage TEXT,
            plan_tier TEXT,
            account_value REAL NOT NULL,
            renewal_date TEXT,
            consent_status TEXT NOT NULL,
            health_score REAL,
            owner TEXT,
            region TEXT
        )
        """
    )
    first_store._connection.execute(
        """
        INSERT INTO customer_context (
            customer_id,
            account_id,
            account_name,
            account_value,
            consent_status
        )
        VALUES ('C-LEGACY', 'A-LEGACY', 'Legacy Account', 1000, 'granted')
        """
    )
    first_store._connection.execute("DROP TABLE customer_context_new")
    first_store._connection.commit()

    migrated_store = SQLiteCustomerContextStore(db_path)
    migrated_store.import_context(
        [
            CustomerContextRecord(
                customer_id="C-NEW",
                account_id="A-NEW",
                parent_account_id="PA-NEW",
                contact_role="admin",
                account_value=2000,
                consent_status="granted",
                product_owner="activation_product",
            )
        ]
    )

    records = migrated_store.list_context()
    legacy = next(record for record in records if record.customer_id == "C-LEGACY")
    added = next(record for record in records if record.customer_id == "C-NEW")

    assert legacy.contact_role is None
    assert added.parent_account_id == "PA-NEW"
    assert added.contact_role == "admin"
    assert added.product_owner == "activation_product"


def test_seed_customer_context_loader() -> None:
    records = load_seed_customer_context()

    assert len(records) == 3
    assert records[0].account_id
    assert records[0].contact_role
    assert records[0].product_owner
