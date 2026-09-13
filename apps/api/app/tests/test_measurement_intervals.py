"""Checkpoints read a fixed observation interval under the terms they were
scheduled with (13 September 2026 review, findings F2 and F3). Each test
states the DESIRED invariant:

  F3  a worker that runs late reads the same interval as one that runs on
      time; the follow-up reads its own month; three overdue kinds in one
      tick are read in order and the latest reading is decided by the
      observation interval, not by the processing order; a rerun measures
      nothing twice; a theme checkpoint waits for enrichment inside its
      interval only; guardrails read the same bounded period;
  F2  a contract amendment re-plans the pending checkpoints under the new
      revision on the same clock, with an audit event, for every scoring
      term (target, baseline, metric, direction, method, window); a reading
      is scored under its plan's frozen terms even when the contract was
      changed behind the API; a legacy plan without frozen terms is blocked
      after an amendment and measured only when the link is deterministic.
"""

from __future__ import annotations

import tempfile
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from fastapi import HTTPException

from app.domain.models import OutcomeContractUpdateRequest, OutcomeMeasurement, SignalRecord
from app.services.measurement_scheduler import (
    SQLiteMeasurementPlanStore,
    observation_interval,
    plan_observation_interval,
    plan_scoring_terms,
    run_due_measurements,
    schedule_measurements,
)
from app.services.problems import ProblemStore
from app.services.seed import load_seed_problems
from app.services.signals import SignalStore, build_candidates, promote_candidate
from app.services.telemetry import SQLiteTelemetryStore
from app.services.workflow import (
    SQLiteWorkflowStore,
    WorkflowStore,
    assert_measurement_not_stale,
    outcome_order_key,
)
from app.tests.test_measurement_semantics_gaps import (
    JIRA_CONFIG,
    _amendable_problem,
    _app,
    _approve,
    _events,
    _execution,
    _FakeJira,
    _plans,
)

NOW = datetime(2026, 9, 13, 12, 0, tzinfo=UTC)


def _iso(moment: datetime) -> str:
    return moment.isoformat().replace("+00:00", "Z")


def _signal(signal_id: str, at: datetime, *, enriched: bool = True, tags: list[str] | None = None) -> SignalRecord:
    return SignalRecord(
        signal_id=signal_id,
        customer_id=f"C-{signal_id}",
        account_id="A-1",
        source="webhook",
        journey="checkout",
        journey_stage="payment",
        feedback_text=f"payment problem {signal_id}",
        language="en",
        timestamp=_iso(at),
        enriched=enriched,
        tags=tags or [],
    )


DISPATCH = NOW - timedelta(days=30)
PRE = [_signal(f"pre-{i}", DISPATCH - timedelta(days=5) + timedelta(hours=12 * i)) for i in range(10)]
IN_WINDOW = [_signal(f"w-{i}", DISPATCH + timedelta(hours=1 + i * 2.5)) for i in range(60)]  # inside 7 days
LATER = [_signal(f"l-{i}", DISPATCH + timedelta(days=8 + i * 2)) for i in range(10)]  # after the window


def _problem(**contract):
    problem = promote_candidate(build_candidates(PRE)[0])
    return problem.model_copy(
        update={"outcome_contract": problem.outcome_contract.model_copy(update=contract)}
    )


def _stores(problem, signals: list[SignalRecord], *, sqlite: bool = False):
    scratch = Path(tempfile.mkdtemp(prefix="clara-intervals-"))
    signal_store = SignalStore()
    signal_store.import_signals(signals)
    problems = ProblemStore(load_seed_problems())
    problems.upsert_problem(problem)
    workflows = SQLiteWorkflowStore(scratch / "wf.db") if sqlite else WorkflowStore()
    return {
        "plans": SQLiteMeasurementPlanStore(scratch / "plans.db"),
        "signals": signal_store,
        "problems": problems,
        "workflows": workflows,
        "telemetry": SQLiteTelemetryStore(scratch / "telemetry.db"),
    }


def _tick(stores, now: datetime) -> dict:
    return run_due_measurements(
        plan_store=stores["plans"],
        problem_lookup=stores["problems"].get_problem,
        signal_store=stores["signals"],
        workflow_store=stores["workflows"],
        telemetry=stores["telemetry"],
        now=_iso(now),
    )


# ---------------------------------------------------------------------------
# F3 — fixed observation intervals
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("sqlite", [False, True])
def test_late_worker_reads_the_same_interval_as_a_punctual_one(sqlite: bool) -> None:
    problem = _problem(measurement_window_days=7)
    readings = {}
    for label, run_at in (("punctual", DISPATCH + timedelta(days=7)), ("late", NOW)):
        stores = _stores(problem, [*PRE, *IN_WINDOW, *LATER], sqlite=sqlite)
        schedule_measurements(stores["plans"], problem=problem, execution_id="EXE-0001", executed_at=_iso(DISPATCH), origin="dispatch")
        assert _tick(stores, run_at)["measured"] == 1
        readings[label] = stores["workflows"].latest_outcome(problem.problem_id)
    punctual, late = readings["punctual"], readings["late"]
    assert punctual.observed_value == late.observed_value == pytest.approx(60 / 7, abs=1e-4)
    assert (punctual.observation_start, punctual.observation_end) == (_iso(DISPATCH), _iso(DISPATCH + timedelta(days=7)))
    assert (late.observation_start, late.observation_end) == (punctual.observation_start, punctual.observation_end)
    assert "60 matching signals" in late.notes and "in the fixed interval" in late.notes
    # measured_at stays the processing instant.
    assert punctual.measured_at == _iso(DISPATCH + timedelta(days=7)) and late.measured_at == _iso(NOW)


def test_plan_carries_its_interval_and_terms_at_scheduling() -> None:
    problem = _problem(measurement_window_days=14, success_threshold=0.25)
    stores = _stores(problem, PRE)
    schedule_measurements(stores["plans"], problem=problem, execution_id="EXE-0001", executed_at=_iso(DISPATCH), origin="dispatch")
    by_kind = {plan["kind"]: plan for plan in stores["plans"].list_plans()}
    assert (by_kind["t7"]["observation_start"], by_kind["t7"]["observation_end"]) == (_iso(DISPATCH), _iso(DISPATCH + timedelta(days=7)))
    assert (by_kind["window"]["observation_start"], by_kind["window"]["observation_end"]) == (_iso(DISPATCH), _iso(DISPATCH + timedelta(days=14)))
    assert (by_kind["followup"]["observation_start"], by_kind["followup"]["observation_end"]) == (_iso(DISPATCH + timedelta(days=14)), _iso(DISPATCH + timedelta(days=44)))
    for plan in by_kind.values():
        assert plan["contract_snapshot"]["success_threshold"] == 0.25
        assert plan["contract_snapshot"]["revision"] == 1
        assert plan["contract_revision"] == 1
    assert observation_interval("followup", executed_at="2026-01-01T00:00:00Z", due_at="2026-03-01T00:00:00Z") == (
        "2026-01-30T00:00:00Z", "2026-03-01T00:00:00Z",
    )
    assert plan_observation_interval({"kind": "t7", "executed_at": "2026-01-01T00:00:00Z", "due_at": "x"}) == (
        "2026-01-01T00:00:00Z", None, False,
    )


def test_three_overdue_kinds_in_one_tick_are_read_in_order_and_the_latest_is_the_followup() -> None:
    problem = _problem(measurement_window_days=14, success_threshold=0.1)
    stores = _stores(problem, [*PRE, *IN_WINDOW, *LATER])
    executed = NOW - timedelta(days=60)
    schedule_measurements(stores["plans"], problem=problem, execution_id="EXE-0001", executed_at=_iso(executed), origin="dispatch")
    result = _tick(stores, NOW)
    assert result["measured"] == 3
    recorded = [e["metadata"]["kind"] for e in _events(stores["telemetry"], "outcome_recorded")]
    assert recorded == ["t7", "window", "followup"]
    latest = stores["workflows"].latest_outcome(problem.problem_id)
    assert latest.checkpoint_kind == "followup"
    assert (latest.observation_start, latest.observation_end) == (_iso(executed + timedelta(days=14)), _iso(executed + timedelta(days=44)))
    assert latest.measured_at == _iso(NOW)
    assert {plan["status"] for plan in stores["plans"].list_plans()} == {"done"}
    # A rerun measures nothing twice.
    assert _tick(stores, NOW + timedelta(hours=1))["measured"] == 0
    assert len(_events(stores["telemetry"], "outcome_recorded")) == 3


def test_the_latest_reading_is_decided_by_the_observation_interval_not_the_processing_order() -> None:
    contract = _problem().outcome_contract
    later = OutcomeMeasurement(
        problem_id="p", metric=contract.primary_metric, observed_value=1.0, measured_at="2026-09-13T12:00:00Z",
        checkpoint_kind="window", plan_id=2, observation_start="2026-08-01T00:00:00Z", observation_end="2026-08-15T00:00:00Z",
    )
    earlier = later.model_copy(update={"checkpoint_kind": "t7", "plan_id": 1, "observation_end": "2026-08-08T00:00:00Z"})
    assert outcome_order_key(later) > outcome_order_key(earlier)
    # Same measured_at, same interval end: the closing checkpoint ranks above
    # the early one, then the plan id decides.
    tie = later.model_copy(update={"checkpoint_kind": "t7", "plan_id": 3})
    assert outcome_order_key(later) > outcome_order_key(tie)
    assert outcome_order_key(later.model_copy(update={"plan_id": 9})) > outcome_order_key(later)
    # A reading covering an earlier interval never displaces a later one.
    with pytest.raises(HTTPException) as refused:
        assert_measurement_not_stale(
            later.measured_at, earlier.measured_at,
            existing_observation_end=later.observation_end, incoming_observation_end=earlier.observation_end,
        )
    assert "later observation interval" in refused.value.detail
    # Manual and legacy readings keep the measured_at rule.
    assert_measurement_not_stale("2026-09-13T12:00:00Z", "2026-09-13T12:00:00Z") is None
    for workflows in (WorkflowStore(), SQLiteWorkflowStore(Path(tempfile.mkdtemp()) / "wf.db")):
        problem = _problem().model_copy(update={"problem_id": "p"})
        workflows.record_outcome(problem=problem, measurement=later)
        with pytest.raises(HTTPException):
            workflows.record_outcome(problem=problem, measurement=earlier)
        assert workflows.latest_outcome("p").checkpoint_kind == "window"


def test_a_late_early_checkpoint_is_blocked_instead_of_displacing_the_window_read() -> None:
    """Processing order T+7 after window (a plan inserted late, or a worker
    that missed a tick): the T+7 read covers an earlier interval and is
    blocked with the reason; the window reading stands."""
    problem = _problem(measurement_window_days=14)
    stores = _stores(problem, [*PRE, *IN_WINDOW])
    executed = NOW - timedelta(days=40)
    plans = stores["plans"]
    plans.schedule(problem_id=problem.problem_id, execution_id="EXE-0001", executed_at=_iso(executed), due_at=_iso(executed + timedelta(days=14)), kind="window", origin="dispatch", contract_revision=1, contract_snapshot=problem.outcome_contract, observation_start=_iso(executed), observation_end=_iso(executed + timedelta(days=14)))
    assert _tick(stores, NOW)["measured"] == 1
    plans.schedule(problem_id=problem.problem_id, execution_id="EXE-0001", executed_at=_iso(executed), due_at=_iso(executed + timedelta(days=7)), kind="t7", origin="dispatch", contract_revision=1, contract_snapshot=problem.outcome_contract, observation_start=_iso(executed), observation_end=_iso(executed + timedelta(days=7)))
    result = _tick(stores, NOW + timedelta(hours=1))
    assert result["measured"] == 0 and result["skipped"] == 1
    t7 = next(plan for plan in plans.list_plans() if plan["kind"] == "t7")
    assert t7["status"] == "blocked" and "later observation interval" in t7["note"]
    assert stores["workflows"].latest_outcome(problem.problem_id).checkpoint_kind == "window"


def test_theme_checkpoint_waits_for_enrichment_inside_its_interval_only() -> None:
    problem = _problem(primary_metric="signal_rate_per_day:theme/checkout_failure", measurement_window_days=7, baseline=4.0, success_threshold=1.0)
    executed = NOW - timedelta(days=30)
    in_window = [_signal(f"t-{i}", executed + timedelta(days=1 + i), tags=["checkout_failure"]) for i in range(3)]
    unenriched_inside = _signal("raw-inside", executed + timedelta(days=2), enriched=False)
    unenriched_after = _signal("raw-after", executed + timedelta(days=20), enriched=False)
    later_tagged = _signal("late-tagged", executed + timedelta(days=20), tags=["checkout_failure"])
    stores = _stores(problem, [*in_window, unenriched_inside, unenriched_after, later_tagged])
    schedule_measurements(stores["plans"], problem=problem, execution_id="EXE-0001", executed_at=_iso(executed), origin="dispatch")
    result = _tick(stores, NOW)
    assert result["measured"] == 0 and result["skipped"] == 1
    t7 = next(plan for plan in stores["plans"].list_plans() if plan["kind"] == "t7")
    assert t7["status"] == "pending" and "1 in-window signals not yet enriched" in t7["note"]
    # Enrich the one inside the interval; the one after it does not matter.
    stores["signals"].update_enrichment("raw-inside", sentiment="negative", urgency="high", tags=["checkout_failure"])
    assert _tick(stores, NOW + timedelta(hours=1))["measured"] == 1
    reading = stores["workflows"].latest_outcome(problem.problem_id)
    assert "4 matching signals" in reading.notes  # three tagged + the enriched one; the day-20 signal is outside
    assert reading.observed_value == pytest.approx(4 / 7, abs=1e-4)


def test_guardrails_read_the_same_bounded_period(monkeypatch: pytest.MonkeyPatch) -> None:
    problem = _problem(measurement_window_days=7, guardrail_metrics=["repeat_signal_rate"])
    executed = NOW - timedelta(days=30)
    pre_customer = SignalRecord(signal_id="pre-c", customer_id="C-repeat", account_id="A", source="webhook", journey="checkout", journey_stage="payment", feedback_text="before", language="en", timestamp=_iso(executed - timedelta(days=3)))
    inside = pre_customer.model_copy(update={"signal_id": "rep-inside", "timestamp": _iso(executed + timedelta(days=2))})
    after = pre_customer.model_copy(update={"signal_id": "rep-after", "timestamp": _iso(executed + timedelta(days=20))})
    stores = _stores(problem, [pre_customer, inside, after])
    schedule_measurements(stores["plans"], problem=problem, execution_id="EXE-0001", executed_at=_iso(executed), origin="dispatch")
    assert _tick(stores, NOW)["measured"] == 1
    [guardrail] = stores["workflows"].latest_guardrails(problem.problem_id)
    assert guardrail.metric == "repeat_signal_rate"
    assert "1 repeat signal(s)" in guardrail.note  # the day-20 repeat lies outside [T, T+7]
    assert guardrail.observed_value == pytest.approx(1 / 7, abs=1e-4)


# ---------------------------------------------------------------------------
# F2 — pending plans are bound to their contract terms
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("amendment", "changed"),
    [
        ({"success_threshold": 90.0}, ["success_threshold"]),
        ({"baseline": 120.0}, ["baseline"]),
        ({"measurement_window_days": 45}, ["measurement_window_days"]),
        ({"comparison_method": "pre_post_signal_rate"}, ["comparison_method"]),
        ({"primary_metric": "signal_rate_per_day:checkout/refund"}, ["primary_metric"]),
        ({"baseline": 40.0, "success_threshold": 60.0}, ["baseline", "success_threshold"]),  # direction flip
    ],
)
def test_amendment_replans_pending_checkpoints_under_the_new_revision(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, amendment: dict, changed: list[str]) -> None:
    monkeypatch.setitem(__import__("app.connectors", fromlist=["DESTINATIONS"]).DESTINATIONS, "jira", _FakeJira())
    app = _app(tmp_path, problem=_amendable_problem(), connectors=[JIRA_CONFIG])
    client, problem, plans, telemetry = app["client"], app["problem"], app["plans"], app["telemetry"]
    pid = problem.problem_id
    _approve(client, problem)  # dispatch clock
    execution = _execution(client, pid)
    before = _plans(plans, pid)
    assert {p["status"] for p in before} == {"pending"}
    assert all(p["contract_snapshot"]["revision"] == 1 for p in before)

    body = {**amendment}
    if "comparison_method" not in body:
        body["comparison_method"] = "its_segmented_regression"  # keep the method unless the case changes it
    response = client.patch(f"/problems/{pid}/outcome-contract", json=body)
    assert response.status_code == 200, response.text
    assert response.json()["outcome_contract"]["revision"] == 2

    after = _plans(plans, pid)
    superseded = [p for p in after if p["status"] == "superseded"]
    live = [p for p in after if p["status"] == "pending"]
    assert {p["id"] for p in superseded} == {p["id"] for p in before}
    assert all(p["note"] == "superseded by contract revision 2 (amendment)" for p in superseded)
    assert {p["kind"] for p in live} == {"t7", "window", "followup"}
    for plan in live:
        assert plan["contract_snapshot"]["revision"] == 2
        for field, value in amendment.items():
            assert plan["contract_snapshot"][field] == value
        assert plan["origin"] == "dispatch"
        assert plan["execution_id"] == execution["execution_id"]
        assert plan["executed_at"] == execution["dispatched_at"]
    [event] = _events(telemetry, "measurement_replanned")
    assert event["metadata"]["changed"] == sorted(changed)
    assert event["metadata"]["revision"] == 2
    assert event["metadata"]["superseded"] == 3
    assert event["metadata"]["clock"]["origin"] == "dispatch"
    [amended] = _events(telemetry, "contract_amended")
    assert amended["metadata"]["revision"] == 2


def test_guardrail_or_owner_only_amendments_do_not_replan(tmp_path: Path) -> None:
    app = _app(tmp_path, problem=_amendable_problem())
    client, problem, plans, telemetry = app["client"], app["problem"], app["plans"], app["telemetry"]
    _approve(client, problem)
    before = {p["id"] for p in _plans(plans, problem.problem_id)}
    response = client.patch(f"/problems/{problem.problem_id}/outcome-contract", json={"guardrail_metrics": ["repeat_signal_rate"], "comparison_method": "its_segmented_regression"})
    assert response.status_code == 200, response.text
    assert {p["id"] for p in _plans(plans, problem.problem_id) if p["status"] == "pending"} == before
    assert _events(telemetry, "measurement_replanned") == []


def test_reading_is_scored_under_the_plans_frozen_terms_when_the_contract_changed_behind_the_api() -> None:
    problem = _problem(baseline=5.0, success_threshold=0.0001, measurement_window_days=7)
    stores = _stores(problem, [*PRE, *IN_WINDOW])
    schedule_measurements(stores["plans"], problem=problem, execution_id="EXE-0001", executed_at=_iso(DISPATCH), origin="dispatch")
    # A store-level edit (no route, no re-planning): the terms change underneath.
    amended = stores["problems"].update_outcome_contract(problem.problem_id, OutcomeContractUpdateRequest(success_threshold=100.0), actor="editor", note="loosened")
    assert amended.outcome_contract.revision == 2
    assert _tick(stores, NOW)["measured"] == 1
    reading = stores["workflows"].latest_outcome(problem.problem_id)
    assert reading.contract_revision == 1
    assert reading.contract_snapshot.success_threshold == 0.0001
    snapshot = stores["workflows"].outcome_snapshot(amended)
    assert snapshot.status == "not_improved"  # 8.57/day above the frozen baseline 5; the loosened target 100 would read target_met
    assert snapshot.measured_under_revision == 1
    assert snapshot.contract_amended_after_measurement is True
    assert snapshot.contract_revision == 2


def test_legacy_plan_without_frozen_terms_is_blocked_after_an_amendment_and_measured_when_the_link_is_deterministic() -> None:
    problem = _problem(measurement_window_days=7)
    stores = _stores(problem, [*PRE, *IN_WINDOW])
    plans = stores["plans"]
    # A pre-017 row: no snapshot, no interval, revision recorded at scheduling.
    plans._connection.execute(
        "INSERT INTO measurement_plans (problem_id, execution_id, executed_at, due_at, kind, created_at, origin, contract_revision)"
        " VALUES (?, ?, ?, ?, 't7', ?, 'dispatch', 1)",
        (problem.problem_id, "EXE-0001", _iso(DISPATCH), _iso(DISPATCH + timedelta(days=7)), _iso(DISPATCH)),
    )
    plans._connection.commit()
    [legacy] = plans.list_plans()
    assert legacy["contract_snapshot"] is None and legacy["observation_end"] is None
    assert plan_scoring_terms(legacy, problem) == (problem.outcome_contract, None)

    amended = stores["problems"].update_outcome_contract(problem.problem_id, OutcomeContractUpdateRequest(success_threshold=0.5), actor="editor")
    terms, reason = plan_scoring_terms(legacy, amended)
    assert terms is None and "revision 1 -> 2" in reason
    result = _tick(stores, NOW)
    assert result["measured"] == 0 and result["skipped"] == 1
    [row] = plans.list_plans()
    assert row["status"] == "blocked" and "carries no frozen terms" in row["note"]
    [blocked] = _events(stores["telemetry"], "measurement_blocked")
    assert blocked["metadata"]["plan_id"] == row["id"]
    assert stores["workflows"].latest_outcome(problem.problem_id) is None

    # Same legacy row, no amendment in between: the link is deterministic and
    # the reading (open-ended, up to the processing instant) says so.
    fresh = _stores(problem, [*PRE, *IN_WINDOW])
    fresh["plans"]._connection.execute(
        "INSERT INTO measurement_plans (problem_id, execution_id, executed_at, due_at, kind, created_at, origin, contract_revision)"
        " VALUES (?, ?, ?, ?, 't7', ?, 'dispatch', 1)",
        (problem.problem_id, "EXE-0001", _iso(DISPATCH), _iso(DISPATCH + timedelta(days=7)), _iso(DISPATCH)),
    )
    fresh["plans"]._connection.commit()
    assert _tick(fresh, NOW)["measured"] == 1
    reading = fresh["workflows"].latest_outcome(problem.problem_id)
    assert reading.contract_revision == 1 and reading.observation_end is None
    assert reading.observation_start == _iso(DISPATCH)
    assert "since dispatch" in reading.notes
