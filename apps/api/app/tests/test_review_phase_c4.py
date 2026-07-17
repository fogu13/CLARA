"""Regressions for external-review tranche 4: JWT-bound reviewer identity and
the honest detectability (MDE) heuristic."""

import time

import jwt
import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.services.outcome_engine import detectability_note
from app.services.problems import ProblemStore
from app.services.seed import load_seed_problems
from app.services.workflow import WorkflowStore

SECRET = "reviewer-binding-test-secret"


@pytest.fixture
def authed_client(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr("app.auth.AUTH_ENABLED", True)
    monkeypatch.setattr("app.auth.SUPABASE_JWT_SECRET", SECRET)
    app = create_app(
        problem_store=ProblemStore(load_seed_problems()),
        workflows=WorkflowStore(),
    )
    return TestClient(app)


def _bearer(sub: str = "cafebabe-cafe-babe-cafe-babecafebabe") -> dict[str, str]:
    token = jwt.encode(
        {
            "sub": sub,
            "email": "editor@example.com",
            "exp": int(time.time()) + 3600,
            "app_metadata": {"workspace_id": 1, "user_role": "editor"},
        },
        SECRET,
        algorithm="HS256",
    )
    return {"Authorization": f"Bearer {token}"}


def test_reviewer_comes_from_jwt_not_request_body(authed_client) -> None:
    problem = load_seed_problems()[0]
    response = authed_client.post(
        f"/problems/{problem.problem_id}/approvals",
        json={
            "action_id": problem.action_proposals[0].action_id,
            "decision": "approved",
            "reviewer": "spoofed-someone-else@example.com",
        },
        headers=_bearer(),
    )
    assert response.status_code == 200, response.text
    record = response.json()
    # _actor_identifier(sub) -> user-<first 8 hex>; the body value is ignored.
    assert record["reviewer"] == "user-cafebabe"


class TestDetectabilityNote:
    def test_none_for_zero_baseline(self) -> None:
        assert detectability_note(baseline_rate=0.0, window_days=30) is None

    def test_underpowered_window_is_called_directional(self) -> None:
        note = detectability_note(baseline_rate=0.05, window_days=7)
        assert note is not None and "directional" in note

    def test_powered_window_reports_relative_mde(self) -> None:
        note = detectability_note(baseline_rate=5.0, window_days=30)
        assert note is not None
        assert "%" in note and "heuristic" in note
