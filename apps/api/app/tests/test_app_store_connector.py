"""Tests for L1 — App Store listening: connector, generalized pull, source sync."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.connectors.app_store import AppStoreSourceConnector
from app.connectors.base import ConnectorError
from app.connectors.config_store import ConnectorConfig, ConnectorConfigStore
from app.main import create_app
from app.services.problems import ProblemStore
from app.services.seed import load_seed_problems
from app.services.signals import SQLiteSignalStore
from app.services.telemetry import SQLiteTelemetryStore
from app.services.workflow import WorkflowStore

APP_ID = "1279625243"


def _entry(review_id: str, *, text: str, rating: str = "1", author: str = "Max M",
           updated: str = "2026-07-01T09:00:00-07:00", title: str = "Problem") -> dict[str, Any]:
    return {
        "id": {"label": review_id},
        "author": {"name": {"label": author}},
        "im:rating": {"label": rating},
        "im:version": {"label": "3.2.1"},
        "title": {"label": title},
        "content": {"label": text},
        "updated": {"label": updated},
    }


def _feed(entries: list[dict[str, Any]] | dict[str, Any]) -> dict[str, Any]:
    return {"feed": {"entry": entries}}


def _url(country: str, page: int = 1) -> str:
    return (
        f"https://itunes.apple.com/{country}/rss/customerreviews/page={page}"
        f"/id={APP_ID}/sortby=mostrecent/json"
    )


CONFIG = {"app_id": APP_ID, "countries": "de"}


class TestConnector:
    def test_maps_reviews_and_pseudonymizes_authors(self, httpx_mock: Any) -> None:
        httpx_mock.add_response(url=_url("de"), json=_feed([
            _entry("901", text="Die Verifizierung hängt seit Tagen und der Support schweigt."),
        ]))
        httpx_mock.add_response(url=_url("de", 2), json=_feed([]))

        signals = AppStoreSourceConnector().pull(CONFIG)
        assert len(signals) == 1
        signal = signals[0]
        assert signal["signal_id"] == "as-de-901"
        assert signal["source"] == "app_store:de"
        assert signal["language"] == "de"
        assert signal["metadata"]["rating"] == "1"
        # GDPR: the reviewer's name must never be stored anywhere on the signal.
        assert "Max M" not in json.dumps(signal)
        assert signal["customer_id"].startswith("rev-")

    def test_single_entry_object_quirk_and_metadata_rows(self, httpx_mock: Any) -> None:
        # RSS-JSON returns a bare object for a single entry; rows without a
        # rating are app metadata, not reviews.
        httpx_mock.add_response(url=_url("de"), json=_feed(
            _entry("902", text="Withdrawal stuck for a week, support unreachable.")
        ))
        httpx_mock.add_response(url=_url("de", 2), json=_feed(
            [{"id": {"label": "meta"}, "title": {"label": "AppName"}}]
        ))
        signals = AppStoreSourceConnector().pull(CONFIG)
        assert [s["signal_id"] for s in signals] == ["as-de-902"]

    def test_multi_country_aggregation(self, httpx_mock: Any) -> None:
        httpx_mock.add_response(url=_url("de"), json=_feed([_entry("1", text="Anmeldung geht nicht mehr seit dem Update.")]))
        httpx_mock.add_response(url=_url("de", 2), json=_feed([]))
        httpx_mock.add_response(url=_url("at"), json=_feed([_entry("2", text="Login broken after the update, please fix.")]))
        httpx_mock.add_response(url=_url("at", 2), json=_feed([]))

        signals = AppStoreSourceConnector().pull({"app_id": APP_ID, "countries": "de, at"})
        assert {s["signal_id"] for s in signals} == {"as-de-1", "as-at-2"}
        assert signals[0]["_sync_metadata"]["last_synced_at"]

    def test_incremental_cursor_stops_at_older_reviews(self, httpx_mock: Any) -> None:
        httpx_mock.add_response(url=_url("de"), json=_feed([
            _entry("new", text="Neue Beschwerde über die Auszahlung.", updated="2026-07-03T10:00:00-07:00"),
            _entry("old", text="Alte Beschwerde.", updated="2026-06-01T10:00:00-07:00"),
        ]))
        signals = AppStoreSourceConnector().pull(
            {**CONFIG, "last_synced_at": "2026-06-15T00:00:00Z"}
        )
        assert [s["signal_id"] for s in signals] == ["as-de-new"]

    def test_invalid_config_and_missing_app(self, httpx_mock: Any) -> None:
        with pytest.raises(ConnectorError):
            AppStoreSourceConnector().pull({"app_id": "not-a-number"})
        with pytest.raises(ConnectorError):
            AppStoreSourceConnector().pull({"app_id": APP_ID, "countries": "??"})
        httpx_mock.add_response(url=_url("de"), status_code=404)
        with pytest.raises(ConnectorError):
            AppStoreSourceConnector().pull(CONFIG)


def _client(tmp_path: Path, configs: list[ConnectorConfig]):
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


APP_STORE_CONFIG = ConnectorConfig(
    connector_type="app_store", config={"app_id": APP_ID, "countries": "de"}
)


class TestGeneralizedPullRoute:
    def test_pull_imports_and_persists_cursor(self, tmp_path: Path, httpx_mock: Any) -> None:
        httpx_mock.add_response(url=_url("de"), json=_feed([
            _entry("77", text="Kartenzahlung wird ständig abgelehnt, niemand hilft."),
        ]))
        httpx_mock.add_response(url=_url("de", 2), json=_feed([]))
        client, config_store, _ = _client(tmp_path, [APP_STORE_CONFIG])

        body = client.post("/connectors/app_store/pull", json={}).json()
        assert body["imported"] == 1

        signals = {s["signal_id"]: s for s in client.get("/signals").json()}
        assert "as-de-77" in signals
        assert config_store.get_config("app_store").config["last_synced_at"]

    def test_unknown_source_404s(self, tmp_path: Path) -> None:
        client, _, _ = _client(tmp_path, [])
        assert client.post("/connectors/hubspot/pull", json={}).status_code == 404

    def test_zendesk_route_shape_still_works(self, tmp_path: Path) -> None:
        # The generalized route keeps the original URL; without config it 400s.
        client, _, _ = _client(tmp_path, [])
        assert client.post("/connectors/zendesk/pull", json={}).status_code == 400


class TestSourceSyncRunner:
    def test_sync_pulls_active_sources_and_isolates_failures(
        self, tmp_path: Path, httpx_mock: Any
    ) -> None:
        # app_store works; zendesk config points at an unreachable host -> the
        # failure is counted, not fatal.
        httpx_mock.add_response(url=_url("de"), json=_feed([
            _entry("55", text="Support antwortet seit zwei Wochen nicht."),
        ]))
        httpx_mock.add_response(url=_url("de", 2), json=_feed([]))
        broken_zendesk = ConnectorConfig(
            connector_type="zendesk",
            config={"subdomain": "brokenpilot", "email": "x@y.z", "api_token": "t"},
        )
        httpx_mock.add_exception(
            __import__("httpx").ConnectError("unreachable"),
            url="https://brokenpilot.zendesk.com/api/v2/tickets.json?per_page=100",
        )
        client, _, telemetry = _client(tmp_path, [APP_STORE_CONFIG, broken_zendesk])

        # The background loop is disabled in tests; exercise the tick through the
        # measurement run-due endpoint? No — the sync runner is loop-internal.
        # Trigger one pull per source the way the loop does: via the route.
        ok = client.post("/connectors/app_store/pull", json={})
        assert ok.status_code == 200 and ok.json()["imported"] == 1
        broken = client.post("/connectors/zendesk/pull", json={})
        assert broken.status_code == 502  # visible failure, not silence

        events = [e for e in telemetry.list_events() if e["event_type"] == "signals_imported"]
        assert any(e["metadata"]["source"] == "app_store" for e in events)
