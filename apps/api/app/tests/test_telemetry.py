"""Tests for product telemetry (Sprint-0 M0) — event store + route emissions."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from app.main import create_app
from app.services.problems import ProblemStore
from app.services.seed import load_seed_problems
from app.services.telemetry import SQLiteTelemetryStore
from app.services.workflow import WorkflowStore


def _client(store: SQLiteTelemetryStore) -> TestClient:
    return TestClient(
        create_app(
            problem_store=ProblemStore(load_seed_problems()),
            workflows=WorkflowStore(),
            telemetry=store,
        )
    )


class TestTelemetryStore:
    def test_record_and_list_round_trip(self, tmp_path: Path) -> None:
        store = SQLiteTelemetryStore(tmp_path / "t.db")
        store.record("signals_imported", metadata={"imported": 12})
        store.record("insight_viewed", entity_id="PRB-108")

        events = store.list_events()
        assert len(events) == 2
        assert events[0]["event_type"] == "insight_viewed"  # newest first
        assert events[1]["metadata"] == {"imported": 12}
        assert store.counts_by_type() == {"signals_imported": 1, "insight_viewed": 1}


class TestRouteEmissions:
    def test_insight_view_and_approval_emit_events(self, tmp_path: Path) -> None:
        store = SQLiteTelemetryStore(tmp_path / "t.db")
        client = _client(store)

        client.get("/problems/PRB-108")
        client.post(
            "/problems/PRB-108/approvals",
            json={"action_id": "ACT-501", "decision": "approved", "reviewer": "tester"},
        )

        counts = store.counts_by_type()
        assert counts.get("insight_viewed") == 1
        assert counts.get("approval_recorded") == 1

    def test_telemetry_endpoint_returns_counts_and_events(self, tmp_path: Path) -> None:
        store = SQLiteTelemetryStore(tmp_path / "t.db")
        client = _client(store)
        client.get("/problems/PRB-108")

        response = client.get("/telemetry")
        assert response.status_code == 200
        body = response.json()
        assert body["counts"].get("insight_viewed") == 1
        assert body["events"][0]["event_type"] == "insight_viewed"

    def test_csv_import_emits_signals_imported(self, tmp_path: Path) -> None:
        from app.services.signals import SQLiteSignalStore

        store = SQLiteTelemetryStore(tmp_path / "t.db")
        client = TestClient(
            create_app(
                problem_store=ProblemStore(load_seed_problems()),
                workflows=WorkflowStore(),
                telemetry=store,
                signals=SQLiteSignalStore(tmp_path / "signals.db"),  # isolated — no dev-DB dedup
            )
        )

        csv_text = "signal_id,feedback_text\nTEL-1,Checkout page crashes on payment\n"
        response = client.post("/signals/import-csv", json={"csv_text": csv_text})
        assert response.status_code == 200

        events = [e for e in store.list_events() if e["event_type"] == "signals_imported"]
        assert len(events) == 1
        assert events[0]["metadata"]["source"] == "csv"
        assert events[0]["metadata"]["imported"] >= 1
