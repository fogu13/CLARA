"""Tests for W4 — auto-proposed outcome contracts at approval.

Covers: the zero-input upgrade on approval (trailing-28d baseline, 30d window,
ITS comparison method + T+7/T+30 checkpoints), the reviewer opt-out, the
proposal preview endpoint, the one-click contract PATCH, and the read-time ITS
field on the outcome snapshot.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

from fastapi.testclient import TestClient

from app.connectors.config_store import ConnectorConfigStore
from app.domain.models import SignalRecord
from app.main import create_app
from app.services.measurement_scheduler import SQLiteMeasurementPlanStore
from app.services.problems import ProblemStore
from app.services.seed import load_seed_problems
from app.services.signals import SQLiteSignalStore
from app.services.telemetry import SQLiteTelemetryStore
from app.services.workflow import WorkflowStore

# Anchored to today: approval flows stamp executed_at with real wall-clock time.
NOW = datetime.now(UTC).replace(hour=12, minute=0, second=0, microsecond=0)


def _iso(dt: datetime) -> str:
    return dt.isoformat().replace("+00:00", "Z")


def _signal(signal_id: str, *, days_ago: float) -> SignalRecord:
    return SignalRecord(
        signal_id=signal_id,
        customer_id=f"C-{signal_id}",
        account_id="A-1",
        source="webhook",
        journey="checkout",
        journey_stage="payment",
        campaign_exposure=[],
        product_events=[],
        feedback_text=f"Payment problem report {signal_id}",
        language="en",
        timestamp=_iso(NOW - timedelta(days=days_ago)),
    )


# 14 matching signals over ~14 observed days -> proposed baseline ~1.0/day
# (rate over the observed span, capped at the trailing 28d).
SIGNALS = [_signal(f"s{i}", days_ago=1 + i) for i in range(14)]


def _app(tmp_path: Path):
    signal_store = SQLiteSignalStore(tmp_path / "signals.db")
    signal_store.import_signals(SIGNALS)
    plan_store = SQLiteMeasurementPlanStore(tmp_path / "plans.db")
    telemetry = SQLiteTelemetryStore(tmp_path / "telemetry.db")
    client = TestClient(
        create_app(
            problem_store=ProblemStore(load_seed_problems()),
            workflows=WorkflowStore(),
            signals=signal_store,
            connector_configs=ConnectorConfigStore(),
            telemetry=telemetry,
            measurement_plans=plan_store,
        )
    )
    return client, plan_store, telemetry


def _promote(client: TestClient) -> dict:
    """Promote the checkout/payment candidate via the API so it lands as a
    DRAFT problem (contract mutations only apply to drafts)."""
    candidates = client.get("/problem-candidates").json()
    candidate = next(c for c in candidates if c["candidate_id"] == "CAND-CHECKOUT-PAYMENT")
    response = client.post(f"/problem-candidates/{candidate['candidate_id']}/promote")
    assert response.status_code == 200
    return response.json()


def _parse_ts(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


class TestApprovalAppliesProposal:
    def test_approval_upgrades_promotion_default_contract(self, tmp_path: Path) -> None:
        client, plan_store, telemetry = _app(tmp_path)
        problem = _promote(client)
        assert problem["outcome_contract"]["comparison_method"] == "pre_post_signal_rate"
        assert problem["outcome_contract"]["measurement_window_days"] == 28

        response = client.post(
            f"/problems/{problem['problem_id']}/approvals",
            json={
                "action_id": problem["action_proposals"][0]["action_id"],
                "decision": "approved",
                "reviewer": "tester",
            },
        )
        assert response.status_code == 200

        contract = client.get(f"/problems/{problem['problem_id']}").json()["outcome_contract"]
        assert contract["comparison_method"] == "its_segmented_regression"
        assert contract["measurement_window_days"] == 30
        # 14 signals over ~14 observed days -> ~1.0/day. The route computes
        # `now` live while NOW here is pinned to 12:00 UTC, so the observed
        # span floats +-12h around 14 days: assert a band, not an instant.
        assert 0.95 <= contract["baseline"] <= 1.05
        assert contract["success_threshold"] == round(contract["baseline"] * 0.5, 4)
        assert contract["primary_metric"] == problem["outcome_contract"]["primary_metric"]

        # Checkpoints follow the upgraded contract: T+7 and T+30.
        plans = {
            plan["kind"]: plan
            for plan in plan_store.list_plans()
            if plan["problem_id"] == problem["problem_id"]
        }
        assert set(plans) == {"t7", "window"}
        executed = _parse_ts(plans["window"]["executed_at"])
        assert (_parse_ts(plans["t7"]["due_at"]) - executed).days == 7
        assert (_parse_ts(plans["window"]["due_at"]) - executed).days == 30

        events = [e for e in telemetry.list_events() if e["event_type"] == "contract_proposed"]
        assert len(events) == 1
        metadata = events[0]["metadata"]
        assert metadata["new_baseline"] == contract["baseline"]
        assert metadata["old_window_days"] == 28 and metadata["new_window_days"] == 30
        assert metadata["old_baseline"] == problem["outcome_contract"]["baseline"]

    def test_opt_out_leaves_contract_untouched(self, tmp_path: Path) -> None:
        client, plan_store, telemetry = _app(tmp_path)
        problem = _promote(client)

        response = client.post(
            f"/problems/{problem['problem_id']}/approvals",
            json={
                "action_id": problem["action_proposals"][0]["action_id"],
                "decision": "approved",
                "reviewer": "tester",
                "accept_proposed_contract": False,
            },
        )
        assert response.status_code == 200

        contract = client.get(f"/problems/{problem['problem_id']}").json()["outcome_contract"]
        assert contract == problem["outcome_contract"]

        # Checkpoints keep the promotion window (T+28), and no proposal event fires.
        plans = {
            plan["kind"]: plan
            for plan in plan_store.list_plans()
            if plan["problem_id"] == problem["problem_id"]
        }
        executed = _parse_ts(plans["window"]["executed_at"])
        assert (_parse_ts(plans["window"]["due_at"]) - executed).days == 28
        assert not [e for e in telemetry.list_events() if e["event_type"] == "contract_proposed"]

    def test_seed_problem_approval_never_touches_business_contract(self, tmp_path: Path) -> None:
        client, _, telemetry = _app(tmp_path)
        before = client.get("/problems/PRB-108").json()["outcome_contract"]

        response = client.post(
            "/problems/PRB-108/approvals",
            json={"action_id": "ACT-501", "decision": "approved", "reviewer": "tester"},
        )
        assert response.status_code == 200

        after = client.get("/problems/PRB-108").json()["outcome_contract"]
        assert after == before
        assert not [e for e in telemetry.list_events() if e["event_type"] == "contract_proposed"]


class TestProposalPreview:
    def test_preview_shows_proposal_for_promotion_default(self, tmp_path: Path) -> None:
        client, _, _ = _app(tmp_path)
        problem = _promote(client)

        preview = client.get(
            f"/problems/{problem['problem_id']}/outcome-contract/proposal"
        ).json()
        assert preview["is_promotion_default"] is True
        assert preview["current"]["comparison_method"] == "pre_post_signal_rate"
        assert preview["proposed"]["comparison_method"] == "its_segmented_regression"
        assert preview["proposed"]["measurement_window_days"] == 30
        assert 0.95 <= preview["proposed"]["baseline"] <= 1.05  # see band note above

    def test_preview_for_business_metric_has_no_proposal(self, tmp_path: Path) -> None:
        client, _, _ = _app(tmp_path)
        preview = client.get("/problems/PRB-108/outcome-contract/proposal").json()
        assert preview["proposed"] is None
        assert preview["is_promotion_default"] is False

    def test_preview_after_upgrade_is_no_longer_promotion_default(self, tmp_path: Path) -> None:
        client, _, _ = _app(tmp_path)
        problem = _promote(client)
        client.post(
            f"/problems/{problem['problem_id']}/approvals",
            json={
                "action_id": problem["action_proposals"][0]["action_id"],
                "decision": "approved",
                "reviewer": "tester",
            },
        )

        preview = client.get(
            f"/problems/{problem['problem_id']}/outcome-contract/proposal"
        ).json()
        assert preview["is_promotion_default"] is False


class TestContractPatch:
    def test_patch_round_trips_an_edit(self, tmp_path: Path) -> None:
        client, _, _ = _app(tmp_path)
        problem = _promote(client)

        response = client.patch(
            f"/problems/{problem['problem_id']}/outcome-contract",
            json={"baseline": 1.25, "measurement_window_days": 45},
        )
        assert response.status_code == 200
        contract = response.json()["outcome_contract"]
        assert contract["baseline"] == 1.25
        assert contract["measurement_window_days"] == 45
        # Untouched fields carry over.
        assert contract["primary_metric"] == problem["outcome_contract"]["primary_metric"]
        assert contract["responsible_owner"] == problem["outcome_contract"]["responsible_owner"]

        refetched = client.get(f"/problems/{problem['problem_id']}").json()["outcome_contract"]
        assert refetched == contract

    def test_patch_rejects_seed_problems(self, tmp_path: Path) -> None:
        client, _, _ = _app(tmp_path)
        response = client.patch(
            "/problems/PRB-108/outcome-contract",
            json={"baseline": 1.0},
        )
        assert response.status_code == 409

    def test_patch_validates_window(self, tmp_path: Path) -> None:
        client, _, _ = _app(tmp_path)
        problem = _promote(client)
        response = client.patch(
            f"/problems/{problem['problem_id']}/outcome-contract",
            json={"measurement_window_days": 0},
        )
        assert response.status_code == 422


class TestOutcomeSnapshotIts:
    def test_snapshot_exposes_honest_its_field_after_approval(self, tmp_path: Path) -> None:
        client, _, _ = _app(tmp_path)
        problem = _promote(client)
        client.post(
            f"/problems/{problem['problem_id']}/approvals",
            json={
                "action_id": problem["action_proposals"][0]["action_id"],
                "decision": "approved",
                "reviewer": "tester",
            },
        )

        snapshot = client.get(f"/problems/{problem['problem_id']}/outcome").json()
        its = snapshot["its"]
        assert its is not None
        # Execution happened just now: at most one post-day bucket exists, so
        # the honest answer is the labelled delta — never a fake CI.
        assert its["method"] == "delta_insufficient_data"
        assert its["label"] == "insufficient data for ITS"
        assert "ci_low" not in its

    def test_snapshot_without_approval_has_no_its(self, tmp_path: Path) -> None:
        client, _, _ = _app(tmp_path)
        problem = _promote(client)
        snapshot = client.get(f"/problems/{problem['problem_id']}/outcome").json()
        assert snapshot["its"] is None

    def test_seed_problem_snapshot_has_no_its(self, tmp_path: Path) -> None:
        client, _, _ = _app(tmp_path)
        client.post(
            "/problems/PRB-108/approvals",
            json={"action_id": "ACT-501", "decision": "approved", "reviewer": "tester"},
        )
        snapshot = client.get("/problems/PRB-108/outcome").json()
        assert snapshot["its"] is None  # business metric — ITS never applies
