"""Tests for L2 — Trustpilot Business connector (own-key, no scraping)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.connectors.base import ConnectorError
from app.connectors.config_store import ConnectorConfig, ConnectorConfigStore
from app.connectors.trustpilot import TrustpilotSourceConnector
from app.main import create_app
from app.services.problems import ProblemStore
from app.services.seed import load_seed_problems
from app.services.signals import SQLiteSignalStore
from app.services.workflow import WorkflowStore

UNIT = "46d5a5"
URL = f"https://api.trustpilot.com/v1/business-units/{UNIT}/reviews"
CONFIG = {"api_key": "tp-key", "business_unit_id": UNIT}


def _review(review_id: str, *, text: str, stars: int = 1, name: str = "Max M",
            created: str = "2026-07-01T09:00:00Z", title: str = "Problem") -> dict[str, Any]:
    return {
        "id": review_id,
        "stars": stars,
        "title": title,
        "text": text,
        "createdAt": created,
        "consumer": {"displayName": name, "displayLocation": "Berlin, DE"},
    }


def _page_url(page: int) -> str:
    return f"{URL}?page={page}&perPage=100&orderBy=createdat.desc"


class TestConnector:
    def test_maps_and_pseudonymizes(self, httpx_mock: Any) -> None:
        httpx_mock.add_response(url=_page_url(1), json={"reviews": [
            _review("r1", text="Auszahlung dauert seit zwei Wochen, Support meldet sich nicht."),
        ]})
        signals = TrustpilotSourceConnector().pull(CONFIG)
        assert len(signals) == 1
        signal = signals[0]
        assert signal["signal_id"] == "tp-r1"
        assert signal["source"] == "trustpilot"
        assert signal["language"] == "de"
        assert signal["metadata"]["rating"] == "1"
        import json as _json
        assert "Max M" not in _json.dumps(signal)  # pseudonymized at ingestion
        assert signal["customer_id"].startswith("rev-")
        assert signal["_sync_metadata"]["last_synced_at"] == "2026-07-01T09:00:00Z"

    def test_incremental_cursor_stops_early(self, httpx_mock: Any) -> None:
        httpx_mock.add_response(url=_page_url(1), json={"reviews": [
            _review("new", text="Neue Beschwerde über die App.", created="2026-07-03T10:00:00Z"),
            _review("old", text="Alte Beschwerde.", created="2026-06-01T10:00:00Z"),
        ]})
        signals = TrustpilotSourceConnector().pull(
            {**CONFIG, "last_synced_at": "2026-06-15T00:00:00Z"}
        )
        assert [s["signal_id"] for s in signals] == ["tp-new"]

    def test_auth_and_config_errors(self, httpx_mock: Any) -> None:
        with pytest.raises(ConnectorError):
            TrustpilotSourceConnector().pull({"api_key": "", "business_unit_id": UNIT})
        httpx_mock.add_response(url=_page_url(1), status_code=401)
        with pytest.raises(ConnectorError, match="rejected the API key"):
            TrustpilotSourceConnector().pull(CONFIG)

    def test_empty_and_metadata_only_reviews(self, httpx_mock: Any) -> None:
        httpx_mock.add_response(url=_page_url(1), json={"reviews": [
            {"id": "empty", "stars": 5, "title": "", "text": "", "createdAt": "2026-07-01T00:00:00Z"},
            _review("r2", text="Login broken since the update."),
        ]})
        signals = TrustpilotSourceConnector().pull(CONFIG)
        assert [s["signal_id"] for s in signals] == ["tp-r2"]


class TestPullRoute:
    def test_generalized_route_serves_trustpilot(self, tmp_path: Path, httpx_mock: Any) -> None:
        httpx_mock.add_response(url=_page_url(1), json={"reviews": [
            _review("77", text="Kundenservice antwortet nicht auf Beschwerden."),
        ]})
        config_store = ConnectorConfigStore([
            ConnectorConfig(connector_type="trustpilot", config=dict(CONFIG))
        ])
        client = TestClient(
            create_app(
                problem_store=ProblemStore(load_seed_problems()),
                workflows=WorkflowStore(),
                signals=SQLiteSignalStore(tmp_path / "s.db"),
                connector_configs=config_store,
            )
        )
        body = client.post("/connectors/trustpilot/pull", json={}).json()
        assert body["imported"] == 1
        assert config_store.get_config("trustpilot").config["last_synced_at"]
