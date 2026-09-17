"""Loop-closure tests: the pitch's four steps wired end to end.

collect -> triage (AI themes become candidates) -> route (team owner routes)
-> close & learn (follow-up checkpoint, loop verdict, learning memory that the
next triage run actually receives). Plus the EU residency gate and the
readiness probe added in the same hardening pass.
"""

from __future__ import annotations

import tempfile
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

import app.services.ai as ai
from app.domain.models import SignalRecord
from app.main import create_app
from app.routers.problems import is_overdue
from app.connectors.config_store import ConnectorConfigStore
from app.services.contexts import CustomerContextStore
from app.services.measurement_scheduler import (
    SQLiteMeasurementPlanStore,
    signal_matches_scope,
    signal_rate_per_day,
    unenriched_in_window,
)
from app.services.outcome_engine import loop_verdict
from app.services.problems import ProblemStore
from app.services.seed import load_seed_problems
from app.services.signals import SignalStore, build_candidates, promote_candidate
from app.services.workflow import WorkflowStore
from app.tests.test_triage_graph import _mock_enrich_signals, _mock_synthesize_insights


def _iso(moment: datetime) -> str:
    return moment.isoformat().replace("+00:00", "Z")


def _client(problem_store: ProblemStore | None = None) -> TestClient:
    # Own plan and connector stores per app: the default SQLite file is shared
    # by every test in the process, so pending checkpoints (or a Jira config)
    # left by one loop test would leak into the next test's approvals.
    plans = SQLiteMeasurementPlanStore(Path(tempfile.mkdtemp(prefix="clara-plans-")) / "plans.db")
    return TestClient(
        create_app(
            problem_store=problem_store or ProblemStore([]),
            workflows=WorkflowStore(),
            signals=SignalStore(),
            contexts=CustomerContextStore(),
            connector_configs=ConnectorConfigStore(),
            measurement_plans=plans,
        )
    )


def _mocks():
    return (
        patch("app.agents.triage_graph.enrich_signals", side_effect=_mock_enrich_signals),
        patch("app.agents.triage_graph.synthesize_insights", side_effect=_mock_synthesize_insights),
    )


def _import_signals(client: TestClient, count: int, *, start: datetime, step: timedelta, **extra) -> None:
    rows = [
        {
            "signal_id": f"{extra.get('prefix', 'sig')}-{i}",
            "feedback_text": f"Checkout crashed when I paid, attempt {i}",
            "source": "app_store",
            "customer_id": f"C-{i}",
            "account_id": f"A-{i}",
            "timestamp": _iso(start + step * i),
            **{k: v for k, v in extra.items() if k != "prefix"},
        }
        for i in range(count)
    ]
    response = client.post("/signals/import", json={"signals": rows})
    assert response.status_code == 200, response.text


def _approve_structural(client: TestClient, problem_id: str) -> None:
    transition = client.post(
        f"/problems/{problem_id}/transitions",
        json={"target_status": "approval_needed", "actor": "tester", "note": "reviewed"},
    )
    assert transition.status_code == 200, transition.text
    approval = client.post(
        f"/problems/{problem_id}/approvals",
        json={
            "action_id": f"ACT-{problem_id}-STRUCTURAL",
            "decision": "approved",
            "reviewer": "reviewer",
            "accept_proposed_contract": False,
        },
    )
    assert approval.status_code == 200, approval.text


# ---------------------------------------------------------------------------
# Step 2 -> 4: AI themes enter the Action Queue and the loop closes on them
# ---------------------------------------------------------------------------


def test_ai_themes_become_candidates_and_the_loop_closes(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CLARA_SEED_DEMO_DATA", "0")
    enr, syn = _mocks()
    with enr, syn:
        client = _client()
        now = datetime.now(UTC)
        _import_signals(client, 4, start=now - timedelta(hours=3), step=timedelta(minutes=30))

        run = client.post("/triage/run", json={})
        assert run.status_code == 200, run.text
        body = run.json()
        assert body["status"] == "awaiting_approval"
        assert body["theme_candidate_ids"] == ["CAND-THEME-CHECKOUT-FAILURE"]
        assert body["themes_saved"] == 1

        # Enrichment is written back, so later theme measurement can match by tag.
        assert all(signal["tags"] == ["checkout_failure"] for signal in client.get("/signals").json())

        candidates = client.get("/problem-candidates").json()
        theme = next(candidate for candidate in candidates if candidate["origin"] == "ai_theme")
        assert theme["candidate_id"] == "CAND-THEME-CHECKOUT-FAILURE"
        assert theme["theme_tag"] == "checkout_failure"
        assert theme["signal_count"] == 4
        assert theme["customer_count"] == 4
        assert theme["evidence"]
        assert theme["suggested_owner"] == "engineering"  # the model's target team, slugified
        assert theme["review_status"] == "pending"
        assert any("AI-sorted theme" in note for note in theme["known_limitations"])

        accepted = client.post(
            f"/problem-candidates/{theme['candidate_id']}/accept",
            json={"reviewer": "reviewer-1", "note": "Real theme."},
        )
        assert accepted.status_code == 200, accepted.text
        problem = accepted.json()
        problem_id = problem["problem_id"]
        assert problem_id == "PRB-DRAFT-THEME-CHECKOUT-FAILURE"
        assert problem["origin"] == "ai_theme"
        assert problem["theme_tag"] == "checkout_failure"
        assert problem["outcome_contract"]["primary_metric"] == "signal_rate_per_day:theme/checkout_failure"
        assert problem["due_at"] is not None  # resolution timeline starts at promotion

        summary = next(item for item in client.get("/problems").json() if item["problem_id"] == problem_id)
        assert summary["origin"] == "ai_theme"
        assert summary["due_at"] == problem["due_at"]
        assert summary["overdue"] is False

        # Re-running triage keeps the theme keyed by tag: it shows as accepted,
        # never as a fresh pending duplicate.
        client.post("/triage/run", json={})
        again = next(
            candidate
            for candidate in client.get("/problem-candidates").json()
            if candidate["candidate_id"] == theme["candidate_id"]
        )
        assert again["review_status"] == "accepted"

        _approve_structural(client, problem_id)
        plans = [plan for plan in client.get("/measurements").json() if plan["problem_id"] == problem_id]
        assert {plan["kind"] for plan in plans} == {"t7", "window", "followup"}  # keep listening
        snapshot = client.get(f"/problems/{problem_id}/outcome").json()
        assert snapshot["status"] == "not_measured"
        assert snapshot["loop_verdict"] == "measuring"
        # The owner upgrades the contract to segmented regression (the
        # promotion-default path does this on approval; theme problems keep
        # the plain pre/post method unless edited).
        patched = client.patch(
            f"/problems/{problem_id}/outcome-contract",
            json={"comparison_method": "its_segmented_regression"},
        )
        assert patched.status_code == 200, patched.text

        # Keep listening: one tagged complaint arrives after the fix; at the
        # window checkpoint inflow has dropped from 4/day to ~0.03/day.
        executed = datetime.fromisoformat(plans[0]["executed_at"].replace("Z", "+00:00"))
        client.post(
            "/signals/import",
            json={
                "signals": [
                    SignalRecord(
                        signal_id="post-fix-1",
                        feedback_text="Still crashed once",
                        source="app_store",
                        timestamp=_iso(executed + timedelta(days=1)),
                        tags=["checkout_failure"],
                        enriched=True,
                    ).model_dump()
                ]
            },
        )
        at_window = _iso(executed + timedelta(days=40))
        result = client.post("/measurements/run-due", json={"now": at_window}).json()
        assert result["measured"] == 2  # t7 + window; followup is still pending
        assert result["loop_closed"] == 1
        assert result["fix_did_not_land"] == 0

        snapshot = client.get(f"/problems/{problem_id}/outcome").json()
        assert snapshot["status"] == "target_met"
        assert snapshot["measurement_source"] == "instrumented"
        assert snapshot["loop_verdict"] == "loop_closed"
        # The window checkpoint reads its fixed interval [T, T+window], not
        # the cumulative span up to the (late) processing instant.
        window_days = snapshot["measurement_window_days"]
        assert snapshot["latest_value"] == pytest.approx(1 / window_days, abs=1e-4)
        assert snapshot["observation_start"] == _iso(executed)
        assert snapshot["observation_end"] == _iso(executed + timedelta(days=window_days))
        # The contract promises segmented regression; the checkpoint reading
        # itself is an uncontrolled before/after on instrumented inflow
        # (grade D). The live read-time ITS is graded separately on the fit it
        # obtained: four pre-signals over three hours cannot support it, so
        # the engine returned the labelled plain delta (D as well).
        assert snapshot["comparison_method"] == "its_segmented_regression"
        assert snapshot["its"]["method"] == "delta_insufficient_data"
        assert snapshot["its"]["evidence_grade"] == "D"
        assert "live cumulative" in snapshot["its"]["scope"]
        assert snapshot["evidence_grade"] == "D"

        board = client.get("/outcome-board").json()
        assert board["loop_closed"] == 1
        assert board["fix_did_not_land"] == 0
        item = next(item for item in board["items"] if item["problem_id"] == problem_id)
        assert item["loop_verdict"] == "loop_closed"
        assert item["due_at"] == problem["due_at"]


def test_fix_that_did_not_land_is_called_out(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CLARA_SEED_DEMO_DATA", "0")
    enr, syn = _mocks()
    with enr, syn:
        client = _client()
        now = datetime.now(UTC)
        _import_signals(client, 4, start=now - timedelta(hours=3), step=timedelta(minutes=30))
        client.post("/triage/run", json={})
        theme = next(c for c in client.get("/problem-candidates").json() if c["origin"] == "ai_theme")
        problem_id = client.post(
            f"/problem-candidates/{theme['candidate_id']}/accept", json={"reviewer": "r"}
        ).json()["problem_id"]
        _approve_structural(client, problem_id)
        plans = [plan for plan in client.get("/measurements").json() if plan["problem_id"] == problem_id]
        executed = datetime.fromisoformat(plans[0]["executed_at"].replace("Z", "+00:00"))

        # The theme keeps coming: 6/day after the fix vs a 4/day baseline.
        rows = [
            SignalRecord(
                signal_id=f"post-{i}",
                feedback_text="Checkout still crashes",
                source="app_store",
                timestamp=_iso(executed + timedelta(hours=4 * i + 1)),
                tags=["checkout_failure"],
                enriched=True,
            ).model_dump()
            for i in range(240)  # 40 days x 6/day
        ]
        assert client.post("/signals/import", json={"signals": rows}).status_code == 200

        result = client.post(
            "/measurements/run-due", json={"now": _iso(executed + timedelta(days=40))}
        ).json()
        assert result["fix_did_not_land"] == 1
        assert result["loop_closed"] == 0
        snapshot = client.get(f"/problems/{problem_id}/outcome").json()
        assert snapshot["status"] == "not_improved"
        assert snapshot["loop_verdict"] == "fix_did_not_land"
        assert client.get("/outcome-board").json()["fix_did_not_land"] == 1


# ---------------------------------------------------------------------------
# Step 4: a reviewer's conclusion reaches the memory the next triage run reads
# ---------------------------------------------------------------------------


def test_learning_conclusion_reaches_learning_memory_and_next_triage(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CLARA_SEED_DEMO_DATA", "0")
    enr, syn = _mocks()
    with enr, syn:
        client = _client()
        now = datetime.now(UTC)
        _import_signals(client, 3, start=now - timedelta(hours=2), step=timedelta(minutes=20))
        client.post("/triage/run", json={})
        theme = next(c for c in client.get("/problem-candidates").json() if c["origin"] == "ai_theme")
        problem_id = client.post(
            f"/problem-candidates/{theme['candidate_id']}/accept", json={"reviewer": "r"}
        ).json()["problem_id"]
        _approve_structural(client, problem_id)
        metric = client.get(f"/problems/{problem_id}/outcome").json()["metric"]
        measured = client.post(
            f"/problems/{problem_id}/outcomes",
            json={
                "problem_id": problem_id,
                "metric": metric,
                "observed_value": 0.0,
                "measured_at": _iso(datetime.now(UTC)),
                "notes": "manual read",
            },
        )
        assert measured.status_code == 200, measured.text

        # No digits: the request model's PII redaction treats long digit runs as
        # phone numbers, which would rewrite the summary we look up below.
        marker = "Retrying the payment step removed the crashes for the checkout theme."
        conclusion = client.post(
            f"/problems/{problem_id}/learning-conclusions",
            json={
                "learning_status": "worked",
                "summary": marker,
                "limitations": "One workspace, one month of inflow.",
                "next_step": "Watch the follow-up checkpoint.",
            },
        )
        assert conclusion.status_code == 200, conclusion.text

        learnings = client.get("/learnings").json()
        item = next(learning for learning in learnings if learning.get("summary") == marker)
        assert item["problem_id"] == problem_id
        assert item["learning_status"] == "worked"
        assert item["topic"] == "checkout_failure"
        assert item["retrieval_eligible"] is True
        assert item["decayed_confidence"] > 0
        assert any(text.startswith("structural:") for text in item["resolution_actions"])
        assert item["freshness"] == "VALIDATED"

    # The NEXT triage run receives that learning in the synthesis call.
    captured: dict[str, object] = {}

    def synth_capture(enriched, **kw):
        captured["learnings"] = kw.get("learnings")
        return _mock_synthesize_insights(enriched, **kw)

    with patch("app.agents.triage_graph.enrich_signals", side_effect=_mock_enrich_signals), patch(
        "app.agents.triage_graph.synthesize_insights", side_effect=synth_capture
    ):
        run = client.post("/triage/run", json={})
        assert run.status_code == 200
    passed = captured["learnings"] or []
    assert any(learning.get("summary") == marker for learning in passed)


# ---------------------------------------------------------------------------
# Step 3: team routing and the per-team queue
# ---------------------------------------------------------------------------


def test_owner_routes_assign_teams_and_filter_the_queue(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CLARA_SEED_DEMO_DATA", "0")
    client = _client()
    now = datetime.now(UTC)
    _import_signals(
        client,
        2,
        start=now - timedelta(hours=2),
        step=timedelta(minutes=30),
        journey="checkout",
        journey_stage="payment",
    )
    settings = client.put(
        "/workspace",
        json={
            "resolution_sla_days": 14,
            "owner_routes": [
                {
                    "match": "payment",
                    "owner": "payments_team",
                    "destination": "jira",
                    "jira_project_key": "PAY",
                }
            ],
        },
    )
    assert settings.status_code == 200, settings.text
    assert settings.json()["owner_routes"][0]["owner"] == "payments_team"

    candidate = next(
        candidate
        for candidate in client.get("/problem-candidates").json()
        if candidate["candidate_id"] == "CAND-CHECKOUT-PAYMENT"
    )
    assert candidate["suggested_owner"] == "payments_team"

    problem = client.post(
        f"/problem-candidates/{candidate['candidate_id']}/accept", json={"reviewer": "r"}
    ).json()
    assert problem["owner"] == "payments_team"
    structural = next(action for action in problem["action_proposals"] if action["class"] == "structural")
    assert structural["owner"] == "payments_team"
    assert structural["destination"] == "jira"
    assert problem["outcome_contract"]["responsible_owner"] == "payments_team"
    due = datetime.fromisoformat(problem["due_at"].replace("Z", "+00:00"))
    assert timedelta(days=13) < due - now < timedelta(days=15)

    mine = client.get("/problems", params={"owner": "payments_team"}).json()
    assert [item["problem_id"] for item in mine] == [problem["problem_id"]]
    assert client.get("/problems", params={"owner": "someone_else"}).json() == []


def test_overdue_problems_are_flagged_and_filterable() -> None:
    store = ProblemStore([])
    client = _client(store)
    seed = load_seed_problems()[0]
    store.upsert_problem(
        seed.model_copy(update={"due_at": "2020-01-01T00:00:00Z", "status": "in_progress"})
    )
    overdue = client.get("/problems", params={"overdue": "true"}).json()
    assert [item["problem_id"] for item in overdue] == [seed.problem_id]
    assert overdue[0]["overdue"] is True
    assert client.get("/problems", params={"overdue": "false"}).json() == []
    assert client.get("/outcome-board").json()["overdue"] == 1


def test_is_overdue_rules() -> None:
    assert is_overdue("2020-01-01T00:00:00Z", "in_progress", now="2026-01-01T00:00:00Z")
    assert not is_overdue("2020-01-01T00:00:00Z", "resolved", now="2026-01-01T00:00:00Z")
    assert not is_overdue("2030-01-01T00:00:00Z", "in_progress", now="2026-01-01T00:00:00Z")
    assert not is_overdue(None, "in_progress")
    assert not is_overdue("not-a-date", "in_progress")


# ---------------------------------------------------------------------------
# Unit-level: scope matching and verdicts
# ---------------------------------------------------------------------------


def test_theme_scope_matches_by_tag_and_stage_scope_by_columns() -> None:
    tagged = SignalRecord(signal_id="a", feedback_text="x", tags=["Checkout_Failure"])
    staged = SignalRecord(
        signal_id="b", feedback_text="y", journey="checkout", journey_stage="payment"
    )
    assert signal_matches_scope(tagged, journey="theme", journey_stage="checkout failure")
    assert not signal_matches_scope(staged, journey="theme", journey_stage="checkout failure")
    assert signal_matches_scope(staged, journey="Checkout", journey_stage="Payment")
    assert not signal_matches_scope(tagged, journey="checkout", journey_stage="payment")


def test_journey_less_source_candidates_are_measured_by_the_same_scope() -> None:
    """Connector/CSV rows without journey metadata are grouped per source
    ("<source>_feedback") — the contract promoted from them must count those
    same signals, or every such loop reads 0/day and "closes" for free."""
    now = datetime.now(UTC)
    signals = [
        SignalRecord(
            signal_id=f"tp-{i}",
            feedback_text=f"Support never answered, attempt {i}",
            source="trustpilot",
            customer_id=f"C-{i}",
            timestamp=_iso(now - timedelta(days=4 - i)),
        )
        for i in range(4)
    ]
    other = SignalRecord(
        signal_id="as-1",
        feedback_text="App keeps logging me out",
        source="app_store",
        timestamp=_iso(now - timedelta(days=1)),
    )
    candidate = next(
        c for c in build_candidates([*signals, other])
        if c.journey_stage.lower().replace(" ", "_") == "trustpilot_feedback"
    )
    problem = promote_candidate(candidate)
    metric = problem.outcome_contract.primary_metric
    assert metric == "signal_rate_per_day:unknown_journey/trustpilot_feedback"
    assert problem.outcome_contract.baseline > 0

    journey, _, stage = metric.removeprefix("signal_rate_per_day:").partition("/")
    rate, sample = signal_rate_per_day(
        [*signals, other],
        journey=journey.replace("_", " "),
        journey_stage=stage.replace("_", " "),
        since=_iso(now - timedelta(days=5)),
        until=_iso(now),
    )
    assert sample == 4  # the app_store row belongs to its own per-source candidate
    assert rate == pytest.approx(4 / 5, abs=1e-3)
    assert not signal_matches_scope(other, journey="unknown journey", journey_stage="trustpilot feedback")
    # A real journey stage that merely ends in "feedback" still matches by column.
    staged = SignalRecord(signal_id="st-1", feedback_text="x", journey_stage="beta_feedback", source="trustpilot")
    assert signal_matches_scope(staged, journey="unknown journey", journey_stage="beta feedback")
    assert not signal_matches_scope(staged, journey="unknown journey", journey_stage="trustpilot feedback")


def test_theme_measurement_waits_for_enrichment_of_new_inflow(monkeypatch: pytest.MonkeyPatch) -> None:
    """Theme contracts count by tag and tags only exist after triage: a window
    with unenriched inflow stays pending (and says why) instead of reading a
    flattering 0/day. Once triage tags the inflow the checkpoints measure."""
    monkeypatch.setenv("CLARA_SEED_DEMO_DATA", "0")
    enr, syn = _mocks()
    with enr, syn:
        client = _client()
        now = datetime.now(UTC)
        _import_signals(client, 4, start=now - timedelta(hours=3), step=timedelta(minutes=30))
        assert client.post("/triage/run", json={}).status_code == 200
        accepted = client.post(
            "/problem-candidates/CAND-THEME-CHECKOUT-FAILURE/accept",
            json={"reviewer": "reviewer-1", "note": "Real theme."},
        )
        assert accepted.status_code == 200, accepted.text
        problem_id = accepted.json()["problem_id"]
        _approve_structural(client, problem_id)
        plans = [plan for plan in client.get("/measurements").json() if plan["problem_id"] == problem_id]
        executed = datetime.fromisoformat(plans[0]["executed_at"].replace("Z", "+00:00"))

        # New inflow after the fix, imported raw (no tags, not enriched).
        _import_signals(client, 1, start=executed + timedelta(days=1), step=timedelta(minutes=1), prefix="raw")
        at_window = _iso(executed + timedelta(days=40))
        blocked = client.post("/measurements/run-due", json={"now": at_window}).json()
        assert blocked["measured"] == 0
        assert blocked["loop_closed"] == 0
        assert blocked["skipped"] == 2  # t7 and window both wait for triage
        pending = [plan for plan in client.get("/measurements").json() if plan["problem_id"] == problem_id]
        assert {plan["status"] for plan in pending} == {"pending"}
        assert any("not yet enriched" in (plan["note"] or "") for plan in pending)
        assert client.get(f"/problems/{problem_id}/outcome").json()["status"] == "not_measured"

        # Triage tags the inflow (stored enrichment is written back) -> measurable.
        assert client.post("/triage/run", json={}).status_code == 200
        raw = next(signal for signal in client.get("/signals").json() if signal["signal_id"] == "raw-0")
        assert raw["enriched"] is True and raw["tags"] == ["checkout_failure"]
        result = client.post("/measurements/run-due", json={"now": at_window}).json()
        assert result["measured"] == 2
        assert result["loop_closed"] == 1
        assert client.get(f"/problems/{problem_id}/outcome").json()["loop_verdict"] == "loop_closed"


def test_candidate_grouping_ignores_journey_casing() -> None:
    """'Checkout/Payment' and 'checkout/payment' rows are one candidate: ids are
    upper-cased, so two groups would collide on id and split the baseline."""
    now = datetime.now(UTC)
    rows = [
        SignalRecord(signal_id="u", feedback_text="Card declined", journey="Checkout", journey_stage="Payment",
                     timestamp=_iso(now - timedelta(days=2))),
        SignalRecord(signal_id="l", feedback_text="Card declined again", journey="checkout", journey_stage="payment",
                     timestamp=_iso(now - timedelta(days=1))),
        SignalRecord(signal_id="s", feedback_text="Card declined thrice", journey=" checkout ", journey_stage="payment ",
                     timestamp=_iso(now)),
    ]
    candidates = build_candidates(rows)
    assert len(candidates) == 1
    assert candidates[0].candidate_id == "CAND-CHECKOUT-PAYMENT"
    assert candidates[0].signal_count == 3
    assert candidates[0].journey == "Checkout"


def test_unenriched_in_window_counts_only_the_window() -> None:
    now = datetime.now(UTC)
    inside = SignalRecord(signal_id="a", feedback_text="x", timestamp=_iso(now - timedelta(days=1)))
    tagged = SignalRecord(signal_id="b", feedback_text="x", timestamp=_iso(now - timedelta(days=1)), enriched=True)
    before = SignalRecord(signal_id="c", feedback_text="x", timestamp=_iso(now - timedelta(days=9)))
    assert unenriched_in_window([inside, tagged, before], since=_iso(now - timedelta(days=7)), until=_iso(now)) == 1


def test_loop_verdict_matrix() -> None:
    done_window = [{"kind": "window", "status": "done", "problem_id": "p"}]
    pending = [{"kind": "t7", "status": "pending", "problem_id": "p"}]
    manual = [{"kind": "window", "status": "manual_required", "problem_id": "p"}]
    assert loop_verdict(outcome_status="not_measured", plans=[])[0] == "not_measured"
    assert loop_verdict(outcome_status="not_measured", plans=pending)[0] == "measuring"
    assert loop_verdict(outcome_status="not_measured", plans=manual)[0] == "manual_required"
    assert loop_verdict(outcome_status="target_met", plans=pending)[0] == "on_track"
    # Certification is bound to the observation: a done closing plan alone
    # proves nothing about the latest reading. Only an instrumented reading
    # produced by a closing checkpoint it names certifies; a legacy reading
    # without a checkpoint kind has unknown provenance and never does, and a
    # manual reading never does.
    bound_window = [{"id": 7, "kind": "window", "status": "done", "problem_id": "p"}]
    assert (
        loop_verdict(
            outcome_status="target_met", plans=bound_window, measurement_source="instrumented",
            checkpoint_kind="window", plan_id=7,
        )[0]
        == "loop_closed"
    )
    legacy_verdict, legacy_note = loop_verdict(
        outcome_status="target_met", plans=done_window, measurement_source="instrumented"
    )
    assert legacy_verdict == "on_track" and "Provenance unknown" in legacy_note
    assert loop_verdict(outcome_status="target_met", plans=done_window)[0] == "on_track"
    assert (
        loop_verdict(outcome_status="target_met", plans=done_window, measurement_source="manual")[0]
        == "on_track"
    )
    assert loop_verdict(outcome_status="improving", plans=done_window)[0] == "on_track"
    assert loop_verdict(outcome_status="not_improved", plans=pending)[0] == "measuring"
    assert (
        loop_verdict(
            outcome_status="not_improved", plans=bound_window, measurement_source="instrumented",
            checkpoint_kind="window", plan_id=7,
        )[0]
        == "fix_did_not_land"
    )
    assert (
        loop_verdict(outcome_status="not_improved", plans=done_window, measurement_source="instrumented")[0]
        == "measuring"
    )
    assert (
        loop_verdict(outcome_status="not_improved", plans=done_window, measurement_source="manual")[0]
        == "measuring"
    )


# ---------------------------------------------------------------------------
# EU residency + readiness
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        ("https://api.mistral.ai/v1", "eu"),
        ("https://api.openai.com/v1", "non_eu"),
        ("https://generativelanguage.googleapis.com/v1beta/openai", "non_eu"),
        ("https://api.deepseek.com/v1", "non_eu"),
        ("http://localhost:11434/v1", "self_hosted"),
        ("http://10.0.0.5:8000/v1", "self_hosted"),
        ("http://vllm.internal/v1", "self_hosted"),
        ("https://cloud.langfuse.com", "eu"),
        ("https://us.cloud.langfuse.com", "non_eu"),
        ("https://gateway.example.com/v1", "unknown"),
        ("", "unknown"),
    ],
)
def test_provider_residency_classification(url: str, expected: str) -> None:
    assert ai.provider_residency(url) == expected


def test_eu_only_mode_refuses_non_eu_and_unknown_hosts(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(ai, "AI_REQUIRE_EU", True)
    monkeypatch.setattr(ai, "AI_EU_EXTRA_HOSTS", frozenset({"gateway.example.eu"}))
    ai.assert_residency_allowed("https://api.mistral.ai/v1", purpose="AI_BASE_URL")
    ai.assert_residency_allowed("http://localhost:11434/v1", purpose="AI_BASE_URL")
    ai.assert_residency_allowed("https://gateway.example.eu/v1", purpose="AI_BASE_URL")
    with pytest.raises(ai.ResidencyViolation):
        ai.assert_residency_allowed("https://api.openai.com/v1", purpose="AI_BASE_URL")
    with pytest.raises(ai.ResidencyViolation):
        ai.assert_residency_allowed("https://unknown-host.example.com/v1", purpose="AI_BASE_URL")
    monkeypatch.setattr(ai, "AI_REQUIRE_EU", False)
    ai.assert_residency_allowed("https://api.openai.com/v1", purpose="AI_BASE_URL")  # off = allowed


def test_settings_refuse_non_eu_endpoint_in_eu_only_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(ai, "AI_REQUIRE_EU", True)
    client = _client()
    rejected = client.put("/settings/ai", json={"base_url": "https://api.openai.com/v1", "model": "gpt"})
    assert rejected.status_code == 422
    assert "CLARA_AI_REQUIRE_EU" in rejected.json()["detail"]
    accepted = client.put(
        "/settings/ai", json={"base_url": "https://api.mistral.ai/v1", "model": "mistral-small-latest"}
    )
    assert accepted.status_code == 200
    ai.set_runtime_config()  # clear the override so later tests see env config


def test_ready_probe_and_system_config_expose_residency() -> None:
    client = _client()
    ready = client.get("/ready")
    assert ready.status_code == 200
    # Unauthenticated probe: status, build identity and one word for the
    # measurement schema — no backend type, error class or versions.
    assert set(ready.json()) == {"status", "version", "measurement_schema"}
    assert ready.json()["status"] == "ok"
    assert ready.json()["measurement_schema"] == "compatible"  # SQLite: the Python tick is the code's own
    details = client.get("/ready/details")
    assert details.status_code == 200
    body = details.json()
    assert body["status"] == "ok"
    assert body["checks"]["database"]["ok"] is True
    assert set(body["checks"]["ai_residency"]) == {"chat", "embeddings", "eu_only_enforced"}
    config = client.get("/system-config").json()
    assert config["ai_residency"] in {"eu", "self_hosted", "non_eu", "unknown"}
    assert config["eu_only_enforced"] is False


# ---------------------------------------------------------------------------
# Audit follow-ups: keep-listening window, retries, guards, intake hygiene
# ---------------------------------------------------------------------------


def test_followup_reads_the_month_after_the_window_not_the_cumulative_span(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A theme that is quiet during the window but returns in month two must read
    fix_did_not_land at the follow-up, not stay loop_closed on the average."""
    monkeypatch.setenv("CLARA_SEED_DEMO_DATA", "0")
    enr, syn = _mocks()
    with enr, syn:
        client = _client()
        now = datetime.now(UTC)
        _import_signals(client, 4, start=now - timedelta(hours=3), step=timedelta(minutes=30))
        client.post("/triage/run", json={})
        theme = next(c for c in client.get("/problem-candidates").json() if c["origin"] == "ai_theme")
        problem_id = client.post(
            f"/problem-candidates/{theme['candidate_id']}/accept", json={"reviewer": "r"}
        ).json()["problem_id"]
        _approve_structural(client, problem_id)
        plans = [plan for plan in client.get("/measurements").json() if plan["problem_id"] == problem_id]
        executed = datetime.fromisoformat(plans[0]["executed_at"].replace("Z", "+00:00"))
        window_days = client.get(f"/problems/{problem_id}").json()["outcome_contract"]["measurement_window_days"]

        # Window: silence. Month two: the theme is back at 6/day (baseline 4/day).
        rows = [
            SignalRecord(
                signal_id=f"return-{i}",
                feedback_text="Checkout crashes again",
                source="app_store",
                timestamp=_iso(executed + timedelta(days=window_days, hours=4 * i + 1)),
                tags=["checkout_failure"],
                enriched=True,
            ).model_dump()
            for i in range(180)  # 30 days x 6/day
        ]
        assert client.post("/signals/import", json={"signals": rows}).status_code == 200

        window_run = client.post(
            "/measurements/run-due", json={"now": _iso(executed + timedelta(days=window_days))}
        ).json()
        assert window_run["loop_closed"] == 1  # the window itself was quiet
        followup_run = client.post(
            "/measurements/run-due", json={"now": _iso(executed + timedelta(days=window_days + 30))}
        ).json()
        assert followup_run["measured"] == 1
        assert followup_run["fix_did_not_land"] == 1  # cumulative average would have hidden this
        snapshot = client.get(f"/problems/{problem_id}/outcome").json()
        assert snapshot["loop_verdict"] == "fix_did_not_land"
        assert snapshot["latest_value"] == pytest.approx(6.0, rel=0.05)
        followup_plan = next(p for p in client.get("/measurements").json() if p["problem_id"] == problem_id and p["kind"] == "followup")
        assert followup_plan["status"] == "done"


def test_manual_outcome_cannot_be_dated_in_the_future_and_learning_needs_a_reading() -> None:
    client = _client(ProblemStore(load_seed_problems()))
    problem_id = "PRB-108"  # seed problem with a business metric
    metric = client.get(f"/problems/{problem_id}/outcome").json()["metric"]
    future = client.post(
        f"/problems/{problem_id}/outcomes",
        json={
            "problem_id": problem_id,
            "metric": metric,
            "observed_value": 0.5,
            "measured_at": _iso(datetime.now(UTC) + timedelta(days=3)),
        },
    )
    assert future.status_code == 422
    blocked = client.post(
        f"/problems/{problem_id}/learning-conclusions",
        json={"learning_status": "worked", "summary": "x", "limitations": "y"},
    )
    assert blocked.status_code == 409


def test_run_due_refuses_future_clock_outside_demo_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CLARA_ALLOW_CLOCK_OVERRIDE", raising=False)
    client = _client()
    response = client.post(
        "/measurements/run-due", json={"now": _iso(datetime.now(UTC) + timedelta(days=10))}
    )
    assert response.status_code == 422
    assert "CLARA_ALLOW_CLOCK_OVERRIDE" in response.json()["detail"]
    # Real time is always allowed.
    assert client.post("/measurements/run-due", json={}).status_code == 200


def test_failed_push_can_be_retried(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.connectors import DESTINATIONS
    from app.connectors.base import ConnectorError

    monkeypatch.setenv("CLARA_SEED_DEMO_DATA", "0")
    client = _client()
    now = datetime.now(UTC)
    _import_signals(
        client, 2, start=now - timedelta(hours=2), step=timedelta(minutes=30),
        journey="checkout", journey_stage="payment",
    )
    problem_id = client.post(
        "/problem-candidates/CAND-CHECKOUT-PAYMENT/accept", json={"reviewer": "r"}
    ).json()["problem_id"]
    assert client.put(
        "/connectors/jira",
        json={"base_url": "https://example.atlassian.net", "email": "a@b.c", "api_token": "t", "project_key": "PAY"},
    ).status_code == 200

    calls: list[dict] = []

    class _FailingJira:
        connector_type = "jira"

        def push(self, action, config):
            calls.append({"action": action, "config": config})
            if len(calls) == 1:
                raise ConnectorError("Jira returned 500", connector="jira", status=500)
            return {"external_id": "PAY-42", "status": "pushed", "audit": {}}

    monkeypatch.setitem(DESTINATIONS, "jira", _FailingJira())
    _approve_structural(client, problem_id)
    execution = next(e for e in client.get("/executions").json() if e["problem_id"] == problem_id)
    assert execution["status"] == "push_failed"

    # Re-approving is refused (append-only audit) — retry is the way back.
    again = client.post(
        f"/problems/{problem_id}/approvals",
        json={"action_id": f"ACT-{problem_id}-STRUCTURAL", "decision": "approved", "reviewer": "r"},
    )
    assert again.status_code == 409
    retried = client.post(f"/problems/{problem_id}/executions/{execution['execution_id']}/retry")
    assert retried.status_code == 200, retried.text
    assert retried.json()["status"] == "pushed"
    assert retried.json()["external_ref"] == "PAY-42"
    assert calls[-1]["action"]["problem_id"] == problem_id  # deep link payload
    # A second retry is refused: the push already succeeded.
    assert client.post(f"/problems/{problem_id}/executions/{execution['execution_id']}/retry").status_code == 409


def test_team_rollup_on_the_outcome_board(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CLARA_SEED_DEMO_DATA", "0")
    client = _client()
    now = datetime.now(UTC)
    _import_signals(
        client, 2, start=now - timedelta(hours=2), step=timedelta(minutes=30),
        journey="checkout", journey_stage="payment",
    )
    problem = client.post("/problem-candidates/CAND-CHECKOUT-PAYMENT/accept", json={"reviewer": "r"}).json()
    board = client.get("/outcome-board").json()
    rollup = next(item for item in board["by_owner"] if item["owner"] == problem["owner"])
    assert rollup["problems"] == 1
    assert rollup["open"] == 1
    assert rollup["overdue"] == 0


def test_json_import_applies_the_same_door_rules_as_csv(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CLARA_SEED_DEMO_DATA", "0")
    client = _client()
    response = client.post(
        "/signals/import",
        json={
            "signals": [
                {
                    "signal_id": "json-1",
                    "feedback_text": "  Die &amp; App   st\u00fcrzt <b>st\u00e4ndig</b> ab, sehr \u00e4rgerlich.  ",
                    "timestamp": "23.06.2026 10:00",
                }
            ]
        },
    )
    assert response.status_code == 200, response.text
    stored = next(s for s in client.get("/signals").json() if s["signal_id"] == "json-1")
    assert stored["feedback_text"] == "Die & App st\u00fcrzt st\u00e4ndig ab, sehr \u00e4rgerlich."
    assert stored["language"] == "de"
    assert stored["metadata"]["timestamp_defaulted"] == "true"
    assert stored["timestamp"].endswith("Z") and "2026-06-23" not in stored["timestamp"]


def test_semicolon_csv_with_bom_imports_and_warns_on_odd_timestamps(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CLARA_SEED_DEMO_DATA", "0")
    client = _client()
    csv_text = (
        "\ufeffsignal_id;feedback_text;timestamp\n"
        "de-1;Bezahlung schl\u00e4gt fehl;23.06.2026 10:00\n"
        "de-2;Login geht nicht;2026-06-23T10:00:00Z\n"
    )
    report = client.post("/signals/validate-csv", json={"csv_text": csv_text}).json()
    assert report["valid"] is True
    assert report["importable_rows"] == 2
    assert any(issue["field"] == "timestamp" and issue["row_number"] == 2 for issue in report["warnings"])
    imported = client.post("/signals/import-csv", json={"csv_text": csv_text}).json()
    assert imported["imported"] == 2


def test_second_triage_run_keeps_stored_enrichment_and_passes_vocabulary(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CLARA_SEED_DEMO_DATA", "0")
    seen: list[dict] = []

    def enrich_capture(signals, **kw):
        seen.append({"count": len(signals), "vocabulary": kw.get("vocabulary")})
        return _mock_enrich_signals(signals, **kw)

    with patch("app.agents.triage_graph.enrich_signals", side_effect=enrich_capture), patch(
        "app.agents.triage_graph.synthesize_insights", side_effect=_mock_synthesize_insights
    ):
        client = _client()
        now = datetime.now(UTC)
        _import_signals(client, 3, start=now - timedelta(hours=2), step=timedelta(minutes=20))
        client.post("/triage/run", json={})
        assert seen[-1]["count"] == 3
        assert seen[-1]["vocabulary"]  # accepted taxonomy labels reach the prompt
        # Nothing new: the stored enrichment is reused, the model is not called again.
        client.post("/triage/run", json={})
        assert len(seen) == 1
        # force=true re-enriches everything.
        client.post("/triage/run", json={"force": True})
        assert len(seen) == 2 and seen[-1]["count"] == 3


def test_enrichment_and_insight_output_are_sanitized() -> None:
    from app.services.enrichment import sanitize_enrichment
    from app.services.synthesis import sanitize_insight

    assert sanitize_enrichment("not a dict", {"a"}) is None
    assert sanitize_enrichment({"id": "zzz", "tags": ["x"]}, {"a"}) is None  # foreign id
    cleaned = sanitize_enrichment(
        {"id": "a", "sentiment": "FURIOUS", "urgency": "panic", "sentiment_score": -7, "tags": ["Checkout Failure", "", "x" * 100, 42]},
        {"a"},
    )
    assert cleaned == {
        "id": "a",
        "sentiment": None,
        "sentiment_score": -1.0,
        "urgency": "medium",
        "tags": ["checkout_failure", "x" * 60, "42"],
    }
    insight = sanitize_insight({"title": " T ", "confidence": 3, "suggested_actions": ["junk", {"type": "create_ticket", "priority": "9"}], "tag": "t"})
    assert insight["title"] == "T"
    assert insight["confidence"] == 1.0
    assert insight["suggested_actions"] == [{"type": "create_ticket", "title": "", "description": "", "priority": 5}]
    assert insight["tag"] == "t"


def test_clean_feedback_text_and_zendesk_null_ids() -> None:
    from app.connectors.zendesk import ZendeskSourceConnector
    from app.services.signals import clean_feedback_text

    assert clean_feedback_text("  Hi &amp; <b>bye</b>\r\n\r\n\r\nend  ") == "Hi & bye\n\nend"
    connector = ZendeskSourceConnector()
    mapped = connector._map_ticket(
        {"id": 7, "description": "help", "requester_id": None, "organization_id": None, "created_at": None},
        {},
        {},
    )
    assert mapped["customer_id"] == "unknown"
    assert mapped["account_id"] == "unknown"
