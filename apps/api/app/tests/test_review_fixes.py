"""Regression tests for the adversarial-review fix batch (July 2026)."""

from __future__ import annotations

from types import SimpleNamespace

from app.services.measurement_scheduler import signal_rate_per_day


def _signal(journey: str, stage: str, ts: str) -> SimpleNamespace:
    return SimpleNamespace(journey=journey, journey_stage=stage, timestamp=ts)


class TestSignalRateRoundTrip:
    def test_underscore_journeys_still_match_after_metric_round_trip(self) -> None:
        # The metric string turns "customer_onboarding" into itself, but the
        # scheduler parses it back as "customer onboarding". Before the fix the
        # comparison missed every signal and recorded a fabricated 0.0.
        signals = [
            _signal("customer_onboarding", "identity_verification", "2026-07-02T10:00:00Z"),
            _signal("Customer Onboarding", "Identity Verification", "2026-07-03T10:00:00Z"),
        ]
        rate, sample = signal_rate_per_day(
            signals,
            journey="customer onboarding",  # post-parse form
            journey_stage="identity verification",
            since="2026-07-01T00:00:00Z",
            until="2026-07-04T00:00:00Z",
        )
        assert sample == 2
        assert rate > 0

    def test_naive_timestamp_does_not_crash_the_run(self) -> None:
        signals = [
            _signal("checkout", "payment", "2026-07-02T10:00:00"),  # naive
            _signal("checkout", "payment", "2026-07-02T12:00:00+02:00"),
        ]
        rate, sample = signal_rate_per_day(
            signals,
            journey="checkout",
            journey_stage="payment",
            since="2026-07-01T00:00:00Z",
            until="2026-07-03T00:00:00Z",
        )
        assert sample == 2


class TestWebhookHardening:
    def _client(self, tmp_path):
        from fastapi.testclient import TestClient

        from app.connectors.config_store import ConnectorConfig, ConnectorConfigStore
        from app.main import create_app
        from app.services.problems import ProblemStore
        from app.services.seed import load_seed_problems
        from app.services.signals import SQLiteSignalStore
        from app.services.workflow import WorkflowStore

        configs = ConnectorConfigStore(
            [ConnectorConfig(connector_type="webhook", config={"secret": "s3cret"})]
        )
        return TestClient(
            create_app(
                problem_store=ProblemStore(load_seed_problems()),
                workflows=WorkflowStore(),
                signals=SQLiteSignalStore(tmp_path / "s.db"),
                connector_configs=configs,
            )
        )

    def test_oversized_body_is_rejected_413(self, tmp_path) -> None:
        client = self._client(tmp_path)
        response = client.post(
            "/ingest/webhook",
            content=b"x" * (2 * 1024 * 1024 + 1),
            headers={"x-clara-signature": "sha256=deadbeef"},
        )
        assert response.status_code == 413

    def test_non_ascii_signature_401s_instead_of_500(self, tmp_path) -> None:
        client = self._client(tmp_path)
        # Raw non-ASCII header bytes: Starlette decodes latin-1 into a str that
        # makes hmac.compare_digest raise TypeError. Must 401, not 500.
        response = client.post(
            "/ingest/webhook",
            json={"signals": []},
            headers={b"x-clara-signature": "sha256=签名".encode("utf-8")},
        )
        assert response.status_code == 401


class TestAppStoreCursor:
    def test_cursor_is_min_across_countries(self, httpx_mock) -> None:
        # de has newer reviews than at; the shared cursor must advance only to
        # at's newest, otherwise the next pull skips at's backlog.
        from app.connectors.app_store import AppStoreSourceConnector
        from app.tests.test_app_store_connector import _entry, _feed, _url

        httpx_mock.add_response(url=_url("de"), json=_feed([
            _entry("1", text="Neues Problem mit der Anmeldung.", updated="2026-07-03T10:00:00-07:00"),
        ]))
        httpx_mock.add_response(url=_url("de", 2), json=_feed([]))
        httpx_mock.add_response(url=_url("at"), json=_feed([
            _entry("2", text="Login geht nicht mehr.", updated="2026-07-01T10:00:00-07:00"),
        ]))
        httpx_mock.add_response(url=_url("at", 2), json=_feed([]))

        signals = AppStoreSourceConnector().pull(
            {"app_id": "1279625243", "countries": "de,at"}
        )
        cursor = signals[0]["_sync_metadata"]["last_synced_at"]
        assert cursor == "2026-07-01T10:00:00-07:00"


class TestJiraDraftScrub:
    def test_sqlite_store_scrubs_customer_id_from_draft_text(self, tmp_path) -> None:
        from app.services.workflow import SQLiteWorkflowStore

        store = SQLiteWorkflowStore(tmp_path / "w.db")
        store._connection.execute(
            "INSERT INTO jira_issue_drafts (problem_id, action_id, execution_id,"
            " project_key, issue_type, summary, description, labels, assignee,"
            " status, created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            ("PRB-1", "ACT-1", "EXE-1", "PROJ", "Bug",
             "Fix issue for CUST-42", "Evidence from CUST-42: cannot log in",
             "[]", "owner", "draft", "2026-07-01T00:00:00Z"),
        )
        store._connection.commit()

        assert store.scrub_customer_references("CUST-42") == 1
        draft = store.list_jira_issue_drafts()[0]
        assert "CUST-42" not in draft.description
        assert "CUST-42" not in draft.summary
        assert "[erased]" in draft.description
