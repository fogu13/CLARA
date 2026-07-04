"""API keys: mint once, hash-only storage, role-scoped machine access."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from app.main import create_app
from app.services.api_keys import SQLiteApiKeyStore
from app.services.problems import ProblemStore
from app.services.seed import load_seed_problems
from app.services.signals import SQLiteSignalStore
from app.services.workflow import WorkflowStore


def _client(tmp_path: Path) -> TestClient:
    return TestClient(
        create_app(
            problem_store=ProblemStore(load_seed_problems()),
            workflows=WorkflowStore(),
            signals=SQLiteSignalStore(tmp_path / "s.db"),
            api_keys=SQLiteApiKeyStore(tmp_path / "keys.db"),
        )
    )


class TestStore:
    def test_plaintext_never_stored_and_verify_round_trips(self, tmp_path: Path) -> None:
        store = SQLiteApiKeyStore(tmp_path / "k.db")
        record, plaintext = store.create_key(name="bi export", role="viewer")
        assert plaintext.startswith("clara_sk_")
        assert record["key_prefix"] == plaintext[:14]

        rows = store._connection.execute("SELECT key_hash FROM api_keys").fetchall()
        assert plaintext not in str([dict(r) for r in rows])

        verified = store.verify(plaintext)
        assert verified is not None and verified["role"] == "viewer"
        assert store.verify("clara_sk_" + "0" * 32) is None

    def test_revoked_key_stops_verifying(self, tmp_path: Path) -> None:
        store = SQLiteApiKeyStore(tmp_path / "k.db")
        record, plaintext = store.create_key(name="temp", role="admin")
        assert store.revoke(record["id"]) is True
        assert store.verify(plaintext) is None
        assert store.revoke(record["id"]) is False  # already revoked


class TestRoutesAndAuth:
    def test_lifecycle_and_header_auth(self, tmp_path: Path) -> None:
        client = _client(tmp_path)

        created = client.post("/api-keys", json={"name": "ci", "role": "viewer"}).json()
        assert created["key"].startswith("clara_sk_")

        listed = client.get("/api-keys").json()
        assert listed[0]["name"] == "ci"
        assert "key" not in listed[0] and "key_hash" not in listed[0]

        # The key authenticates requests via X-Api-Key.
        response = client.get("/problems", headers={"X-Api-Key": created["key"]})
        assert response.status_code == 200

        # A wrong key must 401 even in auth-disabled dev mode: an explicitly
        # presented credential is always verified strictly.
        bad = client.get("/problems", headers={"X-Api-Key": "clara_sk_" + "f" * 32})
        assert bad.status_code == 401

        # Revocation kills it.
        assert client.delete(f"/api-keys/{created['id']}").status_code == 200
        revoked = client.get("/problems", headers={"X-Api-Key": created["key"]})
        assert revoked.status_code == 401

    def test_invalid_role_is_422(self, tmp_path: Path) -> None:
        client = _client(tmp_path)
        assert client.post("/api-keys", json={"name": "x", "role": "owner"}).status_code == 422
