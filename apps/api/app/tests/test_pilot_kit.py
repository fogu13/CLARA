"""Tests for N8 — the fintech demo dataset + evergreen timestamp rebase."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

from fastapi.testclient import TestClient

from app.connectors.config_store import ConnectorConfigStore
from app.main import create_app
from app.services.problems import ProblemStore
from app.services.seed import load_seed_problems
from app.services.signals import SQLiteSignalStore
from app.services.telemetry import SQLiteTelemetryStore
from app.services.workflow import WorkflowStore


def _client(tmp_path: Path) -> TestClient:
    return TestClient(
        create_app(
            problem_store=ProblemStore(load_seed_problems()),
            workflows=WorkflowStore(),
            signals=SQLiteSignalStore(tmp_path / "signals.db"),
            connector_configs=ConnectorConfigStore(),
            telemetry=SQLiteTelemetryStore(tmp_path / "t.db"),
        )
    )


class TestFintechDataset:
    def test_dataset_is_listed_and_sized_for_demos(self, tmp_path: Path) -> None:
        client = _client(tmp_path)
        datasets = {d["dataset_id"]: d for d in client.get("/demo-datasets").json()}
        assert "fintech_identity" in datasets
        assert datasets["fintech_identity"]["industry"] == "fintech"

    def test_import_rebases_timestamps_to_yesterday(self, tmp_path: Path) -> None:
        client = _client(tmp_path)
        result = client.post("/demo-datasets/fintech_identity/import", json={}).json()
        assert result["signals"]["imported"] == 24

        signals = [s for s in client.get("/signals").json() if s["signal_id"].startswith("DEMO-FIN")]
        newest = max(datetime.fromisoformat(s["timestamp"].replace("Z", "+00:00")) for s in signals)
        oldest = min(datetime.fromisoformat(s["timestamp"].replace("Z", "+00:00")) for s in signals)
        now = datetime.now(UTC)

        assert abs((now - timedelta(days=1)) - newest) < timedelta(minutes=5)  # newest ≈ yesterday
        assert (newest - oldest) > timedelta(days=10)  # relative spread preserved

    def test_rebase_can_be_disabled(self, tmp_path: Path) -> None:
        client = _client(tmp_path)
        client.post("/demo-datasets/fintech_identity/import", json={"rebase": False})
        signals = [s for s in client.get("/signals").json() if s["signal_id"].startswith("DEMO-FIN")]
        assert all(s["timestamp"].startswith(("2026-06", "2026-07")) for s in signals)

    def test_dataset_produces_three_candidates_with_auto_contracts(self, tmp_path: Path) -> None:
        client = _client(tmp_path)
        client.post("/demo-datasets/fintech_identity/import", json={})

        # Candidate labels are normalized to Title Case by the candidate builder.
        candidates = [
            c for c in client.get("/problem-candidates").json()
            if c["journey"] in ("Customer Onboarding", "Payments", "Support")
        ]
        stages = {c["journey_stage"] for c in candidates}
        assert {"Identity Verification", "Withdrawal", "Response Time"} <= stages

        # Each theme is big enough for the demo (bootstrap MIN_CLUSTER=3, radar volume).
        counts = {c["journey_stage"]: c["signal_count"] for c in candidates}
        assert counts["Identity Verification"] >= 9
        assert counts["Withdrawal"] >= 8
        assert counts["Response Time"] >= 7

        # German handling: the dataset is DE-heavy and languages surface on candidates.
        verification = next(c for c in candidates if c["journey_stage"] == "Identity Verification")
        assert "de" in verification["languages"]
