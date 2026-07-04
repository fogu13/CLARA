"""Tests for the taxonomy hygiene check (drift + duplicates + stale proposals)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.connectors.config_store import ConnectorConfigStore
from app.domain.models import SignalRecord, TaxonomyType
from app.main import create_app
from app.services.problems import ProblemStore
from app.services.seed import load_seed_problems
from app.services.signals import SQLiteSignalStore
from app.services.taxonomies import TaxonomyStore, load_seed_taxonomies
from app.services.taxonomy_hygiene import run_hygiene
from app.services.telemetry import SQLiteTelemetryStore
from app.services.workflow import WorkflowStore

NOW = datetime(2026, 7, 4, 12, 0, tzinfo=UTC)


def _signal(signal_id: str, text: str, *, days_ago: int = 2) -> SignalRecord:
    return SignalRecord(
        signal_id=signal_id,
        customer_id=f"C-{signal_id}",
        account_id="A-1",
        source="csv_import",
        # Neutral journey/stage: searchable_text includes them, and they must not
        # accidentally match category terms like "payment".
        journey="workplace",
        journey_stage="furniture",
        campaign_exposure=[],
        product_events=[],
        feedback_text=text,
        language="en",
        timestamp=(NOW - timedelta(days=days_ago)).isoformat().replace("+00:00", "Z"),
    )


def _store_with_proposal(proposed_days_ago: int) -> TaxonomyStore:
    store = TaxonomyStore(load_seed_taxonomies())
    store.propose_category(
        TaxonomyType.contact_reason,
        category_id="CAT-HYGIENE-TEST",
        label="hygiene_test_theme",
        description="d",
        terms=["hygiene test"],
        confidence=0.8,
        evidence_count=4,
        actor="tester",
    )
    # Backdate the propose entry deterministically.
    catalog = next(
        c for c in store.list_catalogs() if c.taxonomy_type == TaxonomyType.contact_reason
    )
    category = next(c for c in catalog.categories if c.category_id == "CAT-HYGIENE-TEST")
    category.change_history[0].changed_at = (
        (NOW - timedelta(days=proposed_days_ago)).isoformat().replace("+00:00", "Z")
    )
    return store


class TestHygieneService:
    def test_near_duplicates_reported(self, monkeypatch: pytest.MonkeyPatch) -> None:
        store = TaxonomyStore(load_seed_taxonomies())

        def fake_embed(texts: Any, **_: Any) -> list[list[float]]:
            # First two categories identical, rest orthogonal-ish.
            base = [[1.0, 0.0] for _ in texts]
            for index in range(2, len(texts)):
                base[index] = [0.0, 1.0 + index * 0.001]
            return base

        monkeypatch.setattr("app.services.ai.embed", fake_embed)
        report = run_hygiene(store.list_catalogs(), [], now=NOW)

        assert report["duplicates"], "identical embeddings must be flagged"
        first = report["duplicates"][0]
        assert first["similarity"] >= 0.86
        assert first["category_a"] != first["category_b"]
        assert report["duplicates_skipped"] is False

    def test_embed_failure_degrades_visibly(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from app.services.ai import AIProviderError

        def down(*_: Any, **__: Any) -> None:
            raise AIProviderError("down")

        monkeypatch.setattr("app.services.ai.embed", down)
        store = _store_with_proposal(proposed_days_ago=20)
        report = run_hygiene(store.list_catalogs(), [], now=NOW)

        assert report["duplicates"] == []
        assert report["duplicates_skipped"] is True  # skipped is REPORTED, not silent
        assert report["stale_proposals"]  # other checks still ran

    def test_stale_proposal_flagged_fresh_one_not(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("app.services.ai.embed", lambda texts, **_: [[float(i), 1.0] for i in range(len(texts))])

        stale = run_hygiene(_store_with_proposal(20).list_catalogs(), [], now=NOW)
        assert any(p["category_id"] == "CAT-HYGIENE-TEST" for p in stale["stale_proposals"])
        assert stale["stale_proposals"][0]["age_days"] == 20

        fresh = run_hygiene(_store_with_proposal(3).list_catalogs(), [], now=NOW)
        assert fresh["stale_proposals"] == []

    def test_drift_flags_unmatched_active_categories(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr("app.services.ai.embed", lambda texts, **_: [[float(i), 1.0] for i in range(len(texts))])
        store = TaxonomyStore(load_seed_taxonomies())
        catalog = store.list_catalogs()[0]
        active = [c for c in catalog.categories if c.status == "active" and not c.locked]
        target = active[0]

        # Recent signals that match NONE of the categories' terms.
        signals = [_signal("d1", "completely unrelated topic about office chairs")]
        report = run_hygiene([catalog], signals, now=NOW)
        assert any(d["category_id"] == target.category_id for d in report["drifted_categories"])

        # A signal mentioning the category's own term clears the flag for it.
        term = (target.terms[0] if target.terms else target.label).lower()
        signals_matching = [_signal("d2", f"customer complains about {term} again")]
        report2 = run_hygiene([catalog], signals_matching, now=NOW)
        assert not any(
            d["category_id"] == target.category_id for d in report2["drifted_categories"]
        )

    def test_no_recent_signals_skips_drift(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("app.services.ai.embed", lambda texts, **_: [[float(i), 1.0] for i in range(len(texts))])
        store = TaxonomyStore(load_seed_taxonomies())
        old = [_signal("o1", "ancient feedback", days_ago=400)]
        report = run_hygiene(store.list_catalogs(), old, now=NOW)
        assert report["drifted_categories"] == []  # no recent corpus -> no drift claims


class TestHygieneEndpoint:
    def test_endpoint_returns_report_and_telemetry(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr("app.services.ai.embed", lambda texts, **_: [[float(i), 1.0] for i in range(len(texts))])
        telemetry = SQLiteTelemetryStore(tmp_path / "t.db")
        client = TestClient(
            create_app(
                problem_store=ProblemStore(load_seed_problems()),
                workflows=WorkflowStore(),
                signals=SQLiteSignalStore(tmp_path / "signals.db"),
                taxonomies=TaxonomyStore(load_seed_taxonomies()),
                connector_configs=ConnectorConfigStore(),
                telemetry=telemetry,
            )
        )
        response = client.post("/taxonomy/hygiene")
        assert response.status_code == 200
        report = response.json()
        assert {"duplicates", "stale_proposals", "drifted_categories", "healthy"} <= set(report)
        assert any(e["event_type"] == "taxonomy_hygiene_run" for e in telemetry.list_events())
