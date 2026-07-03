"""Tests for X7 (Zendesk incremental sync + import) and X5 (Slack digest)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

from app.connectors.config_store import ConnectorConfig, ConnectorConfigStore
from app.main import create_app
from app.services.problems import ProblemStore
from app.services.seed import load_seed_problems
from app.services.signals import SQLiteSignalStore
from app.services.telemetry import SQLiteTelemetryStore
from app.services.workflow import WorkflowStore

ZENDESK_CONFIG = ConnectorConfig(
    connector_type="zendesk",
    config={"subdomain": "pilot", "email": "bot@clara.eu", "api_token": "tok"},
)

SLACK_CONFIG = ConnectorConfig(
    connector_type="slack",
    config={"bot_token": "xoxb-test", "channel": "#clara"},
)


def _ticket(ticket_id: int, updated_at: str) -> dict[str, Any]:
    return {
        "id": ticket_id,
        "subject": "Zahlung fehlgeschlagen",
        "description": "Die Zahlung wurde abgelehnt und der Support meldet sich nicht",
        "tags": ["billing"],
        "priority": "high",
        "status": "open",
        "requester_id": 9,
        "organization_id": 2,
        "created_at": "2026-07-01T10:00:00Z",
        "updated_at": updated_at,
    }


def _client(tmp_path: Path, configs: list[ConnectorConfig]):
    # Deep-copy: the pull route mutates the stored config (cursor persistence),
    # and module-level constants must not leak state across tests.
    config_store = ConnectorConfigStore([c.model_copy(deep=True) for c in configs])
    telemetry = SQLiteTelemetryStore(tmp_path / "t.db")
    client = TestClient(
        create_app(
            problem_store=ProblemStore(load_seed_problems()),
            workflows=WorkflowStore(),
            signals=SQLiteSignalStore(tmp_path / "signals.db"),
            connector_configs=config_store,
            telemetry=telemetry,
        )
    )
    return client, config_store, telemetry


class TestZendeskSync:
    def test_pull_imports_signals_and_persists_cursor(
        self, tmp_path: Path, httpx_mock: Any
    ) -> None:
        httpx_mock.add_response(
            url="https://pilot.zendesk.com/api/v2/tickets.json?per_page=100",
            json={"tickets": [_ticket(1, "2026-07-02T08:00:00Z"), _ticket(2, "2026-07-02T09:30:00Z")]},
        )
        client, config_store, _ = _client(tmp_path, [ZENDESK_CONFIG])

        response = client.post("/connectors/zendesk/pull", json={})
        assert response.status_code == 200
        body = response.json()
        assert body["imported"] == 2
        assert body["last_synced_at"] == "2026-07-02T09:30:00Z"

        # Signals actually LANDED in the store (previously they were only returned).
        signals = {s["signal_id"]: s for s in client.get("/signals").json()}
        assert "zd-1" in signals and "zd-2" in signals
        assert signals["zd-1"]["language"] == "de"  # detection fires on pulls
        # Non-string metadata (tags list) was coerced, not dropped.
        assert "billing" in signals["zd-1"]["metadata"]["tags"]

        # Cursor persisted -> next pull is incremental.
        stored = config_store.get_config("zendesk")
        assert stored.config["last_synced_at"] == "2026-07-02T09:30:00Z"

    def test_second_pull_uses_incremental_cursor_and_dedups(
        self, tmp_path: Path, httpx_mock: Any
    ) -> None:
        httpx_mock.add_response(
            url="https://pilot.zendesk.com/api/v2/tickets.json?per_page=100",
            json={"tickets": [_ticket(1, "2026-07-02T08:00:00Z")]},
        )
        client, config_store, _ = _client(tmp_path, [ZENDESK_CONFIG])
        client.post("/connectors/zendesk/pull", json={})

        # The cursor makes the connector hit the incremental endpoint next time.
        start = int(__import__("datetime").datetime.fromisoformat("2026-07-02T08:00:00+00:00").timestamp())
        httpx_mock.add_response(
            url=f"https://pilot.zendesk.com/api/v2/incremental/tickets/cursor.json?start_time={start}",
            json={"tickets": [_ticket(1, "2026-07-02T08:00:00Z")], "end_of_stream": True},
        )
        second = client.post("/connectors/zendesk/pull", json={}).json()
        assert second["imported"] == 0
        assert second["skipped_duplicates"] == 1  # same ticket -> deduped


class TestSlackDigest:
    def test_digest_preview_without_slack_config(self, tmp_path: Path) -> None:
        client, _, _ = _client(tmp_path, [])
        response = client.post("/digest/slack")
        assert response.status_code == 200
        body = response.json()
        assert body["pushed"] is False
        assert "CLARA weekly digest" in body["preview"]
        assert "Emerging problems" in body["preview"]
        assert "Outcomes" in body["preview"]

    def test_digest_pushes_to_slack_when_configured(
        self, tmp_path: Path, httpx_mock: Any
    ) -> None:
        httpx_mock.add_response(
            url="https://slack.com/api/chat.postMessage",
            json={"ok": True, "channel": "C1", "ts": "123.456"},
        )
        client, _, telemetry = _client(tmp_path, [SLACK_CONFIG])

        response = client.post("/digest/slack")
        assert response.status_code == 200
        assert response.json()["pushed"] is True
        assert any(e["event_type"] == "digest_sent" for e in telemetry.list_events())
