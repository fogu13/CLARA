"""Tests for the taxonomy bootstrap (N3) — cluster -> propose -> human review."""

from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.domain.models import SignalRecord, TaxonomyType
from app.services.taxonomies import (
    TaxonomyStore,
    classify_signals,
    load_seed_taxonomies,
    load_seed_terminology,
)
from app.services.taxonomy_bootstrap import bootstrap_taxonomy


def _signal(signal_id: str, text: str) -> SignalRecord:
    return SignalRecord(
        signal_id=signal_id,
        customer_id=f"C-{signal_id}",
        account_id="A-1",
        source="csv_import",
        journey="support",
        journey_stage="general",
        campaign_exposure=[],
        product_events=[],
        feedback_text=text,
        language="en",
        timestamp="2026-07-01T10:00:00Z",
    )


# Two tight clusters (refunds / login) + one outlier. Orthogonal unit vectors per
# cluster so cosine clustering separates them deterministically.
CLUSTERS = {
    "refund": [1.0, 0.0, 0.0],
    "login": [0.0, 1.0, 0.0],
    "outlier": [0.0, 0.0, 1.0],
}
SIGNALS = [
    _signal("s1", "Refund still not arrived after two weeks"),
    _signal("s2", "Where is my refund? Waiting 10 days"),
    _signal("s3", "Refund promised but never paid out"),
    _signal("s4", "Cannot log in after the update"),
    _signal("s5", "Login loops back to the password screen"),
    _signal("s6", "App logs me out and login fails"),
    _signal("s7", "The new icon looks weird"),
]
VECTORS = [
    CLUSTERS["refund"],
    CLUSTERS["refund"],
    CLUSTERS["refund"],
    CLUSTERS["login"],
    CLUSTERS["login"],
    CLUSTERS["login"],
    CLUSTERS["outlier"],
]


@pytest.fixture
def mocked_ai(monkeypatch: pytest.MonkeyPatch) -> dict[str, int]:
    calls = {"embed": 0, "name": 0}

    def fake_embed(texts: Any, **_: Any) -> list[list[float]]:
        calls["embed"] += 1
        return VECTORS[: len(texts)]

    names = iter(
        [
            {"name": "refund_delay", "description": "Refunds arriving late or never."},
            {"name": "login_failure", "description": "Users cannot sign in."},
        ]
    )

    def fake_call_tool(**_: Any) -> dict[str, str]:
        calls["name"] += 1
        return next(names)

    monkeypatch.setattr("app.services.ai.embed", fake_embed)
    monkeypatch.setattr("app.services.ai.call_tool", fake_call_tool)
    return calls


class TestBootstrapService:
    def test_clusters_become_proposed_categories(self, mocked_ai: dict[str, int]) -> None:
        store = TaxonomyStore(load_seed_taxonomies())
        report = bootstrap_taxonomy(SIGNALS, store)

        assert report["scanned"] == 7
        assert report["proposed"] == 2  # outlier cluster < MIN_CLUSTER never proposed
        labels = {p["label"] for p in report["proposals"]}
        assert labels == {"refund_delay", "login_failure"}
        assert all(0.0 < p["confidence"] <= 1.0 for p in report["proposals"])
        assert all(p["evidence_count"] == 3 for p in report["proposals"])

        catalog = next(
            c for c in store.list_catalogs() if c.taxonomy_type == TaxonomyType.contact_reason
        )
        proposed = [c for c in catalog.categories if c.status == "proposed"]
        assert {c.label for c in proposed} == {"refund_delay", "login_failure"}
        assert all(c.confidence is not None for c in proposed)
        assert all(c.change_history[-1].operation.value == "propose" for c in proposed)

    def test_proposed_categories_do_not_classify_until_accepted(
        self, mocked_ai: dict[str, int]
    ) -> None:
        store = TaxonomyStore(load_seed_taxonomies())
        bootstrap_taxonomy(SIGNALS, store)

        matches = classify_signals(SIGNALS, store.list_catalogs(), load_seed_terminology())
        matched_ids = {m.category_id for m in matches}
        assert "CAT-REFUND-DELAY" not in matched_ids  # proposed -> not classifying

        store.review_category(
            TaxonomyType.contact_reason,
            category_id="CAT-REFUND-DELAY",
            decision="accept",
            actor="tester",
        )
        matches_after = classify_signals(SIGNALS, store.list_catalogs(), load_seed_terminology())
        assert "CAT-REFUND-DELAY" in {m.category_id for m in matches_after}

    def test_rerun_is_idempotent(self, monkeypatch: pytest.MonkeyPatch) -> None:
        store = TaxonomyStore(load_seed_taxonomies())

        def fake_embed(texts: Any, **_: Any) -> list[list[float]]:
            return VECTORS[: len(texts)]

        def fake_call_tool(**_: Any) -> dict[str, str]:
            return {"name": "refund_delay", "description": "dup"}

        monkeypatch.setattr("app.services.ai.embed", fake_embed)
        monkeypatch.setattr("app.services.ai.call_tool", fake_call_tool)

        first = bootstrap_taxonomy(SIGNALS, store)
        second = bootstrap_taxonomy(SIGNALS, store)
        assert first["proposed"] >= 1
        assert second["proposed"] == 0  # existing ids skipped, not duplicated
        assert second["skipped"] >= 1

    def test_embedding_failure_aborts_without_writes(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from app.services.ai import AIProviderError

        store = TaxonomyStore(load_seed_taxonomies())
        before = sum(len(c.categories) for c in store.list_catalogs())

        def failing_embed(*_: Any, **__: Any) -> list[list[float]]:
            raise AIProviderError("down")

        monkeypatch.setattr("app.services.ai.embed", failing_embed)
        report = bootstrap_taxonomy(SIGNALS, store)

        assert report["error"] == "embedding_failed"
        assert sum(len(c.categories) for c in store.list_catalogs()) == before


class TestReviewStore:
    def test_reject_keeps_audit_trail(self) -> None:
        store = TaxonomyStore(load_seed_taxonomies())
        store.propose_category(
            TaxonomyType.contact_reason,
            category_id="CAT-TEST-THEME",
            label="test_theme",
            description="d",
            terms=["test theme"],
            confidence=0.8,
            evidence_count=4,
            actor="tester",
        )
        catalog = store.review_category(
            TaxonomyType.contact_reason,
            category_id="CAT-TEST-THEME",
            decision="reject",
            actor="tester",
        )
        category = next(c for c in catalog.categories if c.category_id == "CAT-TEST-THEME")
        assert category.status == "rejected"
        assert [ch.operation.value for ch in category.change_history] == ["propose", "review"]

    def test_review_requires_proposed_status(self) -> None:
        from fastapi import HTTPException

        store = TaxonomyStore(load_seed_taxonomies())
        catalog = store.list_catalogs()[0]
        active = next(c for c in catalog.categories if c.status == "active")
        with pytest.raises(HTTPException) as exc:
            store.review_category(
                catalog.taxonomy_type,
                category_id=active.category_id,
                decision="accept",
                actor="tester",
            )
        assert exc.value.status_code == 409


class TestBootstrapEndpoint:
    def test_bootstrap_and_review_over_http(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Any
    ) -> None:
        from app.main import create_app
        from app.services.signals import SQLiteSignalStore
        from app.services.telemetry import SQLiteTelemetryStore

        def fake_embed(texts: Any, **_: Any) -> list[list[float]]:
            return VECTORS[: len(texts)]

        names = iter(
            [
                {"name": "refund_delay", "description": "Refunds late."},
                {"name": "login_failure", "description": "Login broken."},
            ]
        )
        monkeypatch.setattr("app.services.ai.embed", fake_embed)
        monkeypatch.setattr(
            "app.services.ai.call_tool", lambda **_: next(names)
        )

        signal_store = SQLiteSignalStore(tmp_path / "signals.db")
        signal_store.import_signals(SIGNALS)
        telemetry = SQLiteTelemetryStore(tmp_path / "t.db")
        client = TestClient(
            create_app(
                signals=signal_store,
                taxonomies=TaxonomyStore(load_seed_taxonomies()),
                telemetry=telemetry,
            )
        )

        response = client.post("/taxonomy/bootstrap", json={})
        assert response.status_code == 200
        report = response.json()
        assert report["proposed"] == 2

        review = client.post(
            "/taxonomies/contact_reason/categories/review",
            json={"category_id": report["proposals"][0]["category_id"], "decision": "accept"},
        )
        assert review.status_code == 200
        reviewed = next(
            c
            for c in review.json()["categories"]
            if c["category_id"] == report["proposals"][0]["category_id"]
        )
        assert reviewed["status"] == "active"

        counts = telemetry.counts_by_type()
        assert counts.get("taxonomy_bootstrapped") == 1
        assert counts.get("taxonomy_reviewed") == 1
