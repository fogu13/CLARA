"""Tests for G1 — GDPR Art. 20 (data export) and Art. 17 (erasure)."""

from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

from app.connectors.config_store import ConnectorConfigStore
from app.domain.models import JourneyEventRecord, SignalRecord
from app.main import create_app
from app.services.contexts import SQLiteCustomerContextStore, parse_context_csv
from app.services.journeys import SQLiteJourneyEventStore
from app.services.problems import SQLiteProblemStore
from app.services.seed import load_seed_problems
from app.services.signals import SQLiteSignalStore, build_candidates, promote_candidate
from app.services.telemetry import SQLiteTelemetryStore
from app.services.workflow import WorkflowStore

CUSTOMER = "C-4711"

SIGNALS = [
    SignalRecord(
        signal_id=f"G-{i}",
        customer_id=CUSTOMER if i < 3 else "C-OTHER",
        account_id="A-1",
        source="webhook",
        journey="billing",
        journey_stage="payment",
        campaign_exposure=[],
        product_events=[],
        feedback_text=f"Invoice problem number {i}",
        language="en",
        timestamp=f"2026-07-0{i + 1}T10:00:00Z",
    )
    for i in range(4)
]

EVENTS = [
    JourneyEventRecord(
        event_id=f"EV-{i}",
        customer_id=CUSTOMER if i == 0 else "C-OTHER",
        account_id="A-1",
        journey="billing",
        journey_stage="payment",
        event_name="payment_failed",
        status="failed",
        timestamp="2026-07-01T09:00:00Z",
    )
    for i in range(2)
]

CONTEXT_CSV = (
    "customer_id,account_id,account_value,consent_status\n"
    f"{CUSTOMER},A-1,50000,granted\n"
    "C-OTHER,A-1,10000,granted\n"
)


def _app(tmp_path: Path):
    signal_store = SQLiteSignalStore(tmp_path / "signals.db")
    signal_store.import_signals(SIGNALS)
    journey_store = SQLiteJourneyEventStore(tmp_path / "journeys.db")
    journey_store.import_events(EVENTS)
    context_store = SQLiteCustomerContextStore(tmp_path / "context.db")
    context_store.import_context(parse_context_csv(CONTEXT_CSV))

    # A draft problem whose evidence includes the customer (promoted from their signals).
    problem_store = SQLiteProblemStore(tmp_path / "problems.db", load_seed_problems())
    candidate = build_candidates([s for s in SIGNALS if s.customer_id == CUSTOMER])[0]
    problem_store.upsert_problem(promote_candidate(candidate))

    telemetry = SQLiteTelemetryStore(tmp_path / "t.db")
    client = TestClient(
        create_app(
            problem_store=problem_store,
            workflows=WorkflowStore(),
            signals=signal_store,
            journeys=journey_store,
            contexts=context_store,
            connector_configs=ConnectorConfigStore(),
            telemetry=telemetry,
        )
    )
    return client, telemetry


class TestExport:
    def test_export_gathers_all_holdings(self, tmp_path: Path) -> None:
        client, _ = _app(tmp_path)
        response = client.get(f"/customers/{CUSTOMER}/data-export")
        assert response.status_code == 200
        export = response.json()

        assert len(export["signals"]) == 3
        assert len(export["journey_events"]) == 1
        assert len(export["customer_context"]) == 1
        assert len(export["problem_evidence_appearances"]) >= 1
        # Only this customer's data — nothing from C-OTHER leaks in.
        assert all(s["customer_id"] == CUSTOMER for s in export["signals"])


class TestErasure:
    def test_erasure_removes_everything_and_export_is_empty_after(self, tmp_path: Path) -> None:
        client, telemetry = _app(tmp_path)

        response = client.request("DELETE", f"/customers/{CUSTOMER}/data")
        assert response.status_code == 200
        erased = response.json()["erased"]
        assert erased["signals"] == 3
        assert erased["journey_events"] == 1
        assert erased["context_records"] == 1
        assert erased["problems_scrubbed"] == 1

        after = client.get(f"/customers/{CUSTOMER}/data-export").json()
        assert after["signals"] == []
        assert after["journey_events"] == []
        assert after["customer_context"] == []
        assert after["problem_evidence_appearances"] == []

        # Other customers' data untouched.
        other = client.get("/customers/C-OTHER/data-export").json()
        assert len(other["signals"]) == 1

    def test_scrubbed_evidence_keeps_row_but_erases_content(self, tmp_path: Path) -> None:
        client, _ = _app(tmp_path)
        client.request("DELETE", f"/customers/{CUSTOMER}/data")

        problems = client.get("/problems").json()
        draft_id = next(p["problem_id"] for p in problems if p["problem_id"].startswith("PRB-DRAFT"))
        problem = client.get(f"/problems/{draft_id}").json()

        scrubbed = [e for e in problem["evidence"] if e["customer_id"] == "erased"]
        assert scrubbed  # rows kept
        assert all("[erased under GDPR Art. 17]" == e["excerpt"] for e in scrubbed)
        assert all(CUSTOMER not in json.dumps(e) for e in problem["evidence"])

    def test_erasure_telemetry_does_not_retain_identifier(self, tmp_path: Path) -> None:
        client, telemetry = _app(tmp_path)
        client.request("DELETE", f"/customers/{CUSTOMER}/data")

        events = [e for e in telemetry.list_events() if e["event_type"] == "gdpr_erasure"]
        assert len(events) == 1
        assert CUSTOMER not in json.dumps(events[0])  # the erased id is not re-stored

    def test_erasure_is_idempotent(self, tmp_path: Path) -> None:
        client, _ = _app(tmp_path)
        client.request("DELETE", f"/customers/{CUSTOMER}/data")
        second = client.request("DELETE", f"/customers/{CUSTOMER}/data").json()["erased"]
        assert second == {
            "signals": 0,
            "journey_events": 0,
            "context_records": 0,
            "problems_scrubbed": 0,
        }
