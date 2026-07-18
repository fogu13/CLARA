"""Per-entity attribution rollup (metadata['entity'] convention)."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from app.domain.models import SignalRecord
from app.main import create_app
from app.services.entities import entity_rollup
from app.services.problems import ProblemStore
from app.services.seed import load_seed_problems
from app.services.signals import SQLiteSignalStore
from app.services.workflow import WorkflowStore


def _signal(sid: str, entity: str | None = None, sentiment: str | None = None,
            urgency: str | None = None, ts: str = "2026-07-01T00:00:00Z",
            tags: list[str] | None = None) -> SignalRecord:
    return SignalRecord(
        signal_id=sid,
        feedback_text="text",
        metadata={"entity": entity} if entity else {},
        sentiment=sentiment,
        urgency=urgency,
        tags=tags or [],
        timestamp=ts,
    )


def test_rollup_groups_ranks_and_excludes_entityless() -> None:
    signals = [
        _signal("s1", "acme_tours", "negative", "high", tags=["overbooking", "refund_issue"]),
        _signal("s2", "acme_tours", "negative", "critical", ts="2026-07-03T00:00:00Z",
                tags=["overbooking"]),
        _signal("s3", "acme_tours", "positive", "low"),
        _signal("s4", "beta_travel", "positive", "low"),
        _signal("s5", "beta_travel", "mixed", "medium"),
        _signal("s6", None, "negative", "high"),  # no entity: excluded
        _signal("s7", "gamma_gmbh"),  # not yet enriched
    ]
    rollup = entity_rollup(signals)
    assert [r["entity"] for r in rollup] == ["acme_tours", "beta_travel", "gamma_gmbh"]

    acme = rollup[0]
    assert acme["signal_count"] == 3
    assert acme["negative_count"] == 2
    assert acme["negative_share"] == round(2 / 3, 4)
    assert acme["urgent_count"] == 2
    assert acme["top_tags"][0] == ["overbooking", 2] or acme["top_tags"][0] == ("overbooking", 2)
    assert acme["first_seen"] == "2026-07-01T00:00:00Z"
    assert acme["last_seen"] == "2026-07-03T00:00:00Z"

    gamma = rollup[2]
    assert gamma["enriched_count"] == 0
    assert gamma["negative_share"] is None


def test_entities_endpoint(tmp_path: Path) -> None:
    signals = SQLiteSignalStore(tmp_path / "signals.db")
    client = TestClient(
        create_app(
            problem_store=ProblemStore(load_seed_problems()),
            workflows=WorkflowStore(),
            signals=signals,
        )
    )
    body = {"signals": [
        _signal("s1", "acme_tours", "negative", "high").model_dump(),
        _signal("s2", None, "positive", "low").model_dump(),
    ]}
    assert client.post("/signals/import", json=body).status_code == 200

    rollup = client.get("/signals/entities").json()
    assert len(rollup) == 1
    assert rollup[0]["entity"] == "acme_tours"
    assert rollup[0]["urgent_count"] == 1
