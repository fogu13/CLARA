"""The last deferred plan items: connector-secret encryption at rest, email
digest delivery, and opt-in four-eyes approvals."""

from datetime import datetime, timezone

import pytest
from cryptography.fernet import Fernet
from fastapi import HTTPException

from app.connectors.config_store import (
    ConnectorConfig,
    SQLiteConnectorConfigStore,
    seal_config,
    unseal_config,
)
from app.domain.models import ApprovalDecision, ApprovalDecisionStatus
from app.services.alerts import run_alert_sweep
from app.services.seed import load_seed_problems
from app.services.workflow import SQLiteWorkflowStore, WorkflowStore


# --------------------------------------------------------------------------- #
# Item 20 — encryption at rest
# --------------------------------------------------------------------------- #


class TestConfigEncryption:
    def test_seal_round_trip_with_key(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("CLARA_CONFIG_SECRET_KEY", Fernet.generate_key().decode())
        sealed = seal_config({"api_token": "s3cret"})
        assert sealed.startswith("enc:v1:")
        assert "s3cret" not in sealed
        assert unseal_config(sealed) == {"api_token": "s3cret"}

    def test_legacy_plaintext_still_loads(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("CLARA_CONFIG_SECRET_KEY", Fernet.generate_key().decode())
        assert unseal_config('{"a": 1}') == {"a": 1}
        assert unseal_config({"a": 1}) == {"a": 1}  # legacy Postgres dict payloads

    def test_encrypted_without_key_fails_loud(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("CLARA_CONFIG_SECRET_KEY", Fernet.generate_key().decode())
        sealed = seal_config({"x": 1})
        monkeypatch.delenv("CLARA_CONFIG_SECRET_KEY")
        with pytest.raises(RuntimeError, match="CLARA_CONFIG_SECRET_KEY"):
            unseal_config(sealed)

    def test_sqlite_store_persists_ciphertext(
        self, tmp_path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("CLARA_CONFIG_SECRET_KEY", Fernet.generate_key().decode())
        store = SQLiteConnectorConfigStore(tmp_path / "conn.db")
        store.upsert_config(
            ConnectorConfig(connector_type="slack", config={"bot_token": "xoxb-secret"})
        )
        raw = store._connection.execute(
            "SELECT config FROM connector_configs WHERE connector_type = 'slack'"
        ).fetchone()["config"]
        assert raw.startswith("enc:v1:") and "xoxb-secret" not in raw
        assert store.get_config("slack").config == {"bot_token": "xoxb-secret"}


# --------------------------------------------------------------------------- #
# Item 23 — email digest
# --------------------------------------------------------------------------- #


class _Telemetry:
    def __init__(self) -> None:
        self.events: list[tuple[str, dict]] = []

    def has_event(self, *_args) -> bool:
        return False

    def latest_event_at(self, *_args):
        return None

    def record(self, event_type: str, **kwargs) -> None:
        self.events.append((event_type, kwargs.get("metadata", {})))


class _EmptyReport:
    signals: list = []


class _NoConfigs:
    def get_config(self, *_args):
        return None


def test_email_only_workspace_still_gets_digest() -> None:
    telemetry = _Telemetry()
    sent: list[tuple[str, str]] = []

    result = run_alert_sweep(
        emerging_report=_EmptyReport(),
        connector_config_store=_NoConfigs(),
        telemetry=telemetry,
        push_slack=lambda *_: (_ for _ in ()).throw(AssertionError("no slack configured")),
        build_digest_text=lambda: "digest body",
        send_email=lambda to, subject, body: sent.append((to, subject)) or True,
        digest_email="ops@example.com",
        now=datetime(2026, 7, 18, tzinfo=timezone.utc),
    )

    assert result == {"alerted": 0, "digest_sent": 1}
    assert sent == [("ops@example.com", "CLARA weekly digest")]
    assert telemetry.events[0][1]["channel"] == "email"


def test_no_channels_is_a_noop() -> None:
    result = run_alert_sweep(
        emerging_report=_EmptyReport(),
        connector_config_store=_NoConfigs(),
        telemetry=_Telemetry(),
        push_slack=lambda *_: None,
        build_digest_text=lambda: "digest body",
    )
    assert result == {"alerted": 0, "digest_sent": 0}


# --------------------------------------------------------------------------- #
# Item 21 — four-eyes approvals
# --------------------------------------------------------------------------- #


def _decision(reviewer: str, action_id: str) -> ApprovalDecision:
    return ApprovalDecision(
        action_id=action_id,
        decision=ApprovalDecisionStatus.approved,
        reviewer=reviewer,
    )


class TestFourEyes:
    @pytest.mark.parametrize("store_kind", ["memory", "sqlite"])
    def test_two_distinct_approvers_release_execution(self, store_kind, tmp_path) -> None:
        problem = load_seed_problems()[0]
        action_id = problem.action_proposals[0].action_id
        store = (
            WorkflowStore() if store_kind == "memory" else SQLiteWorkflowStore(tmp_path / "wf.db")
        )

        store.record_approval(
            problem=problem, decision=_decision("user-aaaa", action_id), four_eyes=True
        )
        state = store.state_for_problem(problem)
        assert len(state.approvals) == 1
        assert state.executions == []  # held: first of two

        # The same reviewer cannot confirm their own approval.
        with pytest.raises(HTTPException) as excinfo:
            store.record_approval(
                problem=problem, decision=_decision("user-aaaa", action_id), four_eyes=True
            )
        assert "different approver" in excinfo.value.detail

        store.record_approval(
            problem=problem, decision=_decision("user-bbbb", action_id), four_eyes=True
        )
        state = store.state_for_problem(problem)
        assert len(state.approvals) == 2
        assert len(state.executions) == 1  # released by the second approver

        # A third approval is a plain duplicate.
        with pytest.raises(HTTPException) as excinfo:
            store.record_approval(
                problem=problem, decision=_decision("user-cccc", action_id), four_eyes=True
            )
        assert "already approved" in excinfo.value.detail

    def test_flag_off_keeps_single_approval_semantics(self) -> None:
        problem = load_seed_problems()[0]
        action_id = problem.action_proposals[0].action_id
        store = WorkflowStore()
        store.record_approval(problem=problem, decision=_decision("user-aaaa", action_id))
        state = store.state_for_problem(problem)
        assert len(state.executions) == 1


# --------------------------------------------------------------------------- #
# Item 11 (fuzzy tier) — near-duplicate annotation
# --------------------------------------------------------------------------- #

from app.domain.models import SignalRecord
from app.services.signals import annotate_near_duplicates


def _sig(sid: str, text: str) -> SignalRecord:
    return SignalRecord(signal_id=sid, feedback_text=text)


class TestNearDuplicates:
    def test_minor_edits_are_annotated_never_dropped(self) -> None:
        existing = [_sig("s-1", "The checkout page crashes every time I try to pay with my card")]
        new = [_sig("s-2", "the checkout page crashes every time I try to pay with my card!!")]
        count = annotate_near_duplicates(new, existing)
        assert count == 1
        assert new[0].metadata["near_duplicate_of"] == "s-1"

    def test_different_feedback_is_untouched(self) -> None:
        existing = [_sig("s-1", "The checkout page crashes every time I try to pay")]
        new = [_sig("s-2", "Great support experience, my issue was resolved in minutes")]
        assert annotate_near_duplicates(new, existing) == 0
        assert "near_duplicate_of" not in new[0].metadata

    def test_short_texts_are_skipped(self) -> None:
        existing = [_sig("s-1", "app crashes")]
        new = [_sig("s-2", "app crashes")]
        # Below the token floor: too little signal to call it a duplicate.
        assert annotate_near_duplicates(new, existing) == 0

    def test_intra_batch_duplicates_detected(self) -> None:
        new = [
            _sig("s-1", "Payment failed twice today and support has not responded to me"),
            _sig("s-2", "payment failed twice today and support has not responded to me."),
        ]
        assert annotate_near_duplicates(new, []) == 1
        assert new[1].metadata["near_duplicate_of"] == "s-1"
