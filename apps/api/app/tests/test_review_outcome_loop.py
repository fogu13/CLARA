"""Regression test for the outcome-loop fix (#19): /triage/run pauses at the human
approval interrupt and /triage/resume runs action -> measure -> learn. Previously the
per-request checkpointer was discarded, so the loop never ran live."""

from __future__ import annotations

from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import create_app
from app.tests.test_triage_graph import (
    _make_signals,
    _mock_enrich_signals,
    _mock_synthesize_insights,
)


def _patched_client() -> TestClient:
    return TestClient(create_app())


def _mocks():
    return (
        patch("app.agents.triage_graph.enrich_signals", side_effect=_mock_enrich_signals),
        patch("app.agents.triage_graph.synthesize_insights", side_effect=_mock_synthesize_insights),
    )


def test_run_pauses_for_approval_then_resume_closes_the_loop() -> None:
    enr, syn = _mocks()
    with enr, syn:
        client = _patched_client()  # same app instance -> shared checkpointer
        run = client.post("/triage/run", json={"signals": _make_signals(3)})
        assert run.status_code == 200
        data = run.json()
        assert data["status"] == "awaiting_approval"
        assert data["thread_id"]
        assert len(data["insights"]) == 1

        resume = client.post(
            "/triage/resume", json={"thread_id": data["thread_id"], "decision": "approved"}
        )
        assert resume.status_code == 200
        rd = resume.json()
        assert rd["approval_decision"] == "approved"
        assert rd["status"] == "learned"          # learn_node ran
        assert rd["outcome"] is not None          # measure_node ran
        assert len(rd["approved_insights"]) == 1
        assert rd["action_results"]               # action_node ran


def test_resume_rejected_skips_action() -> None:
    enr, syn = _mocks()
    with enr, syn:
        client = _patched_client()
        run = client.post("/triage/run", json={"signals": _make_signals(2)}).json()
        rd = client.post(
            "/triage/resume", json={"thread_id": run["thread_id"], "decision": "rejected"}
        ).json()
        assert rd["approval_decision"] == "rejected"
        assert rd["approved_insights"] == []


def test_resume_unknown_thread_is_404() -> None:
    client = _patched_client()
    r = client.post("/triage/resume", json={"thread_id": "does-not-exist", "decision": "approved"})
    assert r.status_code == 404


def test_resume_requires_thread_id_and_valid_decision() -> None:
    client = _patched_client()
    assert client.post("/triage/resume", json={"decision": "approved"}).status_code == 422
    assert client.post(
        "/triage/resume", json={"thread_id": "x", "decision": "maybe"}
    ).status_code == 422
