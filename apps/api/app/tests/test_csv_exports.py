"""Tests for the BI CSV exports (warehouse EXPORT, not sync)."""

from __future__ import annotations

import csv
import io
from pathlib import Path

from fastapi.testclient import TestClient

from app.connectors.config_store import ConnectorConfigStore
from app.domain.models import SignalRecord
from app.main import create_app
from app.services.exports import rows_to_csv
from app.services.problems import ProblemStore
from app.services.seed import load_seed_problems
from app.services.signals import SQLiteSignalStore
from app.services.telemetry import SQLiteTelemetryStore
from app.services.workflow import WorkflowStore

HOSTILE = SignalRecord(
    signal_id="EVIL-1",
    customer_id="C-1",
    account_id="A-1",
    source="webhook",
    journey="billing",
    journey_stage="payment",
    campaign_exposure=[],
    product_events=[],
    feedback_text='=HYPERLINK("http://evil.example","click")',
    language="en",
    timestamp="2026-07-01T10:00:00Z",
)


def _client(tmp_path: Path):
    signal_store = SQLiteSignalStore(tmp_path / "signals.db")
    signal_store.import_signals([HOSTILE])
    telemetry = SQLiteTelemetryStore(tmp_path / "t.db")
    client = TestClient(
        create_app(
            problem_store=ProblemStore(load_seed_problems()),
            workflows=WorkflowStore(),
            signals=signal_store,
            connector_configs=ConnectorConfigStore(),
            telemetry=telemetry,
        )
    )
    return client, telemetry


class TestNeutralization:
    def test_formula_prefixes_get_apostrophe(self) -> None:
        out = rows_to_csv(["a"], [["=cmd()"], ["+1"], ["-2"], ["@x"], ["safe"]])
        lines = out.strip().split("\n")
        assert lines[1].startswith("'=") or lines[1].startswith("\"'=")
        assert lines[-1] == "safe"


class TestExportEndpoint:
    def test_each_entity_exports_csv(self, tmp_path: Path) -> None:
        client, telemetry = _client(tmp_path)
        for entity, expected_column in [
            ("signals", "feedback_text"),
            ("problems", "impact_score"),
            ("outcomes", "success_threshold"),
            ("telemetry", "event_type"),
        ]:
            response = client.get(f"/export/{entity}.csv")
            assert response.status_code == 200, entity
            assert response.headers["content-type"].startswith("text/csv")
            assert f'filename="clara-{entity}.csv"' in response.headers["content-disposition"]
            header = response.text.splitlines()[0]
            assert expected_column in header, entity

        exported = [e for e in telemetry.list_events() if e["event_type"] == "csv_exported"]
        assert len(exported) == 4

    def test_hostile_feedback_is_neutralized_end_to_end(self, tmp_path: Path) -> None:
        client, _ = _client(tmp_path)
        response = client.get("/export/signals.csv")
        rows = list(csv.reader(io.StringIO(response.text)))
        header, data = rows[0], rows[1:]
        text_index = header.index("feedback_text")
        evil = next(r for r in data if r[header.index("signal_id")] == "EVIL-1")
        assert evil[text_index].startswith("'=")  # Excel/Sheets will not execute it

    def test_unknown_entity_404s_with_catalog(self, tmp_path: Path) -> None:
        client, _ = _client(tmp_path)
        response = client.get("/export/users.csv")
        assert response.status_code == 404
        assert "signals" in response.json()["detail"]
