"""Tests for the local learning store (outcome-grounded loop persistence)."""

from __future__ import annotations

from pathlib import Path

from app.services.learning_store import SQLiteLearningStore


def test_persist_and_load_round_trip(tmp_path: Path) -> None:
    store = SQLiteLearningStore(tmp_path / "clara.db")
    stored = store.persist(
        {"topic": "refund_delay", "summary": "Faster refunds cut churn", "base_confidence": 0.6},
        workspace_id=1,
    )
    assert stored["conclusion_id"]  # an id was assigned

    loaded = store.load(workspace_id=1)
    assert len(loaded) == 1
    assert loaded[0]["topic"] == "refund_delay"
    assert loaded[0]["conclusion_id"] == stored["conclusion_id"]


def test_load_is_workspace_scoped(tmp_path: Path) -> None:
    store = SQLiteLearningStore(tmp_path / "clara.db")
    store.persist({"topic": "a"}, workspace_id=1)
    store.persist({"topic": "b"}, workspace_id=2)
    assert len(store.load(workspace_id=1)) == 1
    assert len(store.load(workspace_id=2)) == 1


def test_persist_same_id_upserts(tmp_path: Path) -> None:
    store = SQLiteLearningStore(tmp_path / "clara.db")
    store.persist({"conclusion_id": "x", "topic": "v1"}, workspace_id=1)
    store.persist({"conclusion_id": "x", "topic": "v2"}, workspace_id=1)
    loaded = store.load(workspace_id=1)
    assert len(loaded) == 1
    assert loaded[0]["topic"] == "v2"


def test_clear(tmp_path: Path) -> None:
    store = SQLiteLearningStore(tmp_path / "clara.db")
    store.persist({"topic": "a"}, workspace_id=1)
    store.clear(workspace_id=1)
    assert store.load(workspace_id=1) == []
