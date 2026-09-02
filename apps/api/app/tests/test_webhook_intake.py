"""Tests for N7 — generic HMAC webhook intake + persistent connector config."""

from __future__ import annotations

import hashlib
import hmac
import json
from pathlib import Path

from fastapi.testclient import TestClient

from app.connectors.config_store import (
    ConnectorConfig,
    ConnectorConfigStore,
    SQLiteConnectorConfigStore,
)
from app.main import create_app
from app.services.signals import SQLiteSignalStore
from app.services.telemetry import SQLiteTelemetryStore

SECRET = "test-webhook-secret"

WEBHOOK_CONFIG = ConnectorConfig(
    connector_type="webhook",
    config={"secret": SECRET},
    is_active=True,
)


def _sign(body: bytes, secret: str = SECRET) -> str:
    return "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


def _client(tmp_path: Path, config: ConnectorConfig | None = WEBHOOK_CONFIG) -> TestClient:
    return TestClient(
        create_app(
            signals=SQLiteSignalStore(tmp_path / "signals.db"),
            connector_configs=ConnectorConfigStore([config] if config else []),
            telemetry=SQLiteTelemetryStore(tmp_path / "t.db"),
        )
    )


class TestPersistentConfigStore:
    def test_upsert_survives_restart(self, tmp_path: Path) -> None:
        store = SQLiteConnectorConfigStore(tmp_path / "cfg.db")
        store.upsert_config(
            ConnectorConfig(
                connector_type="jira",
                config={"base_url": "https://x.atlassian.net", "api_token": "tok"},
                display_name="Team Jira",
            )
        )

        reopened = SQLiteConnectorConfigStore(tmp_path / "cfg.db")
        loaded = reopened.get_config("jira")
        assert loaded is not None
        assert loaded.config["base_url"] == "https://x.atlassian.net"
        assert loaded.display_name == "Team Jira"
        assert loaded.is_active is True

    def test_upsert_overwrites_and_delete_removes(self, tmp_path: Path) -> None:
        store = SQLiteConnectorConfigStore(tmp_path / "cfg.db")
        store.upsert_config(ConnectorConfig(connector_type="slack", config={"bot_token": "a"}))
        store.upsert_config(
            ConnectorConfig(connector_type="slack", config={"bot_token": "b"}, is_active=False)
        )
        loaded = store.get_config("slack")
        assert loaded is not None and loaded.config["bot_token"] == "b"
        assert loaded.is_active is False

        assert store.delete_config("slack") is True
        assert store.get_config("slack") is None
        assert store.delete_config("slack") is False


class TestWebhookIntake:
    def test_valid_signature_imports_signals(self, tmp_path: Path) -> None:
        client = _client(tmp_path)
        body = json.dumps(
            {
                "signals": [
                    {
                        "signal_id": "WH-1",
                        "feedback_text": "Checkout crashes when paying by card",
                        "journey": "checkout",
                    },
                    {
                        "signal_id": "WH-2",
                        "feedback_text": "Die Zahlung wurde abgelehnt und niemand hilft mir",
                    },
                ]
            }
        ).encode()

        response = client.post(
            "/ingest/webhook", content=body, headers={"x-clara-signature": _sign(body)}
        )
        assert response.status_code == 200
        assert response.json()["imported"] == 2

        signals = {s["signal_id"]: s for s in client.get("/signals").json()}
        assert signals["WH-1"]["source"] == "webhook"
        assert signals["WH-2"]["language"] == "de"  # detection fires on webhook rows too

    def test_unusable_rows_are_counted_not_swallowed(self, tmp_path: Path) -> None:
        client = _client(tmp_path)
        body = json.dumps(
            {
                "signals": [
                    {
                        "signal_id": "WH-OK",
                        "feedback_text": "Refund took three weeks",
                        "metadata": {"ticket": {"id": 42, "tags": ["refund"]}},
                    },
                    {"signal_id": "WH-EMPTY", "feedback_text": "   "},
                    "not-an-object",
                ]
            }
        ).encode()
        response = client.post(
            "/ingest/webhook", content=body, headers={"x-clara-signature": _sign(body)}
        )
        assert response.status_code == 200, response.text
        assert response.json()["imported"] == 1
        assert response.json()["dropped_rows"] == 2
        stored = {s["signal_id"]: s for s in client.get("/signals").json()}
        assert "WH-OK" in stored and "WH-EMPTY" not in stored  # seed signals may coexist

    def test_replay_is_deduplicated(self, tmp_path: Path) -> None:
        client = _client(tmp_path)
        body = json.dumps(
            {"signals": [{"signal_id": "WH-9", "feedback_text": "Refund missing"}]}
        ).encode()
        headers = {"x-clara-signature": _sign(body)}

        assert client.post("/ingest/webhook", content=body, headers=headers).json()["imported"] == 1
        second = client.post("/ingest/webhook", content=body, headers=headers).json()
        assert second["imported"] == 0
        assert second["skipped_duplicates"] == 1

    def test_invalid_signature_rejected(self, tmp_path: Path) -> None:
        client = _client(tmp_path)
        body = b'{"signals": [{"feedback_text": "spoofed"}]}'
        response = client.post(
            "/ingest/webhook", content=body, headers={"x-clara-signature": _sign(body, "wrong")}
        )
        assert response.status_code == 401
        assert client.post("/ingest/webhook", content=body).status_code == 401  # missing header

    def test_unconfigured_webhook_rejected(self, tmp_path: Path) -> None:
        client = _client(tmp_path, config=None)
        body = b'{"signals": [{"feedback_text": "x"}]}'
        response = client.post(
            "/ingest/webhook", content=body, headers={"x-clara-signature": _sign(body)}
        )
        assert response.status_code == 400

    def test_inactive_webhook_rejected(self, tmp_path: Path) -> None:
        inactive = WEBHOOK_CONFIG.model_copy(update={"is_active": False})
        client = _client(tmp_path, config=inactive)
        body = b'{"signals": [{"feedback_text": "x"}]}'
        response = client.post(
            "/ingest/webhook", content=body, headers={"x-clara-signature": _sign(body)}
        )
        assert response.status_code == 400

    def test_malformed_payloads_rejected(self, tmp_path: Path) -> None:
        client = _client(tmp_path)
        for body in (b"not json", b"{}", b"[]", b'{"signals": [{"customer_id": "no-text"}]}'):
            response = client.post(
                "/ingest/webhook", content=body, headers={"x-clara-signature": _sign(body)}
            )
            assert response.status_code == 422, body
