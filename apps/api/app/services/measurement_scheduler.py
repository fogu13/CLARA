"""Scheduled outcome re-measurement; closes the loop without a human remembering.

When an action is approved, measurement checkpoints are scheduled at T+7 days
and T+measurement_window_days. When a checkpoint comes due:

  - Contracts whose primary_metric is signal-derived (``signal_rate_per_day:
    {journey}/{journey_stage}`` — the auto-captured contract on promoted
    problems) are measured by CLARA itself from REAL signal inflow, and the
    OutcomeMeasurement is recorded automatically (never simulated data).
  - Contracts with business metrics CLARA cannot observe (e.g. seed problems'
    ``*_completion_7d``) are marked ``manual_required`` — a visible measurement
    task for a human, never a fabricated number.

Honesty rule carried from the eval work: auto-recorded outcomes are tagged
real_data_source=true in telemetry; nothing simulated ever flows through here.

The background loop is a plain asyncio task on FastAPI startup (no scheduler
dependency), gated by CLARA_SCHEDULER_ENABLED (tests set it to 0). ponytail:
pg_cron replaces the loop when a Postgres deployment needs multi-worker safety.
"""

from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable

from app.domain.models import OutcomeMeasurement, ProblemRecord
from app.services.common import utc_now, SerializedConnection

logger = logging.getLogger(__name__)

SIGNAL_METRIC_PREFIX = "signal_rate_per_day:"
LOOP_INTERVAL_SECONDS = 15 * 60


def _parse_ts(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        # One naive timestamp must never crash a measurement run: mixing naive
        # and aware datetimes raises TypeError on comparison. Treat naive as UTC.
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def _norm_stage(value: str) -> str:
    """Journey names round-trip through the metric string as lowercase with
    underscores; normalize both sides so 'customer_onboarding' still matches
    after the metric parser turns it into 'customer onboarding'."""
    return value.lower().replace("_", " ").strip()


class SQLiteMeasurementPlanStore:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._connection = SerializedConnection(self.path)
        self._connection.execute(
            """
            CREATE TABLE IF NOT EXISTS measurement_plans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                problem_id TEXT NOT NULL,
                execution_id TEXT NOT NULL,
                executed_at TEXT NOT NULL,
                due_at TEXT NOT NULL,
                kind TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                note TEXT,
                created_at TEXT NOT NULL
            )
            """
        )
        self._connection.commit()

    def schedule(
        self,
        *,
        problem_id: str,
        execution_id: str,
        executed_at: str,
        due_at: str,
        kind: str,
    ) -> None:
        # One pending plan per problem+kind — re-approving must not double-schedule.
        existing = self._connection.execute(
            "SELECT id FROM measurement_plans WHERE problem_id = ? AND kind = ?"
            " AND status IN ('pending', 'manual_required')",
            (problem_id, kind),
        ).fetchone()
        if existing:
            return
        self._connection.execute(
            "INSERT INTO measurement_plans"
            " (problem_id, execution_id, executed_at, due_at, kind, created_at)"
            " VALUES (?, ?, ?, ?, ?, ?)",
            (problem_id, execution_id, executed_at, due_at, kind, utc_now()),
        )
        self._connection.commit()

    def list_plans(self) -> list[dict[str, Any]]:
        rows = self._connection.execute(
            "SELECT * FROM measurement_plans ORDER BY due_at"
        ).fetchall()
        return [dict(row) for row in rows]

    def due(self, now: str) -> list[dict[str, Any]]:
        rows = self._connection.execute(
            "SELECT * FROM measurement_plans WHERE status = 'pending' AND due_at <= ?"
            " ORDER BY due_at",
            (now,),
        ).fetchall()
        return [dict(row) for row in rows]

    def mark(self, plan_id: int, *, status: str, note: str | None = None) -> None:
        self._connection.execute(
            "UPDATE measurement_plans SET status = ?, note = ? WHERE id = ?",
            (status, note, plan_id),
        )
        self._connection.commit()


def schedule_measurements(
    plan_store: SQLiteMeasurementPlanStore,
    *,
    problem: ProblemRecord,
    execution_id: str,
    executed_at: str,
) -> list[str]:
    """Schedule the T+7 and T+window checkpoints for an approved action."""
    window_days = problem.outcome_contract.measurement_window_days
    executed = _parse_ts(executed_at)
    checkpoints = {"t7": 7}
    if window_days != 7:
        checkpoints["window"] = window_days

    scheduled: list[str] = []
    for kind, days in checkpoints.items():
        due_at = (executed + timedelta(days=days)).isoformat().replace("+00:00", "Z")
        plan_store.schedule(
            problem_id=problem.problem_id,
            execution_id=execution_id,
            executed_at=executed_at,
            due_at=due_at,
            kind=kind,
        )
        scheduled.append(kind)
    return scheduled


def signal_rate_per_day(
    signals: list[Any],
    *,
    journey: str,
    journey_stage: str,
    since: str,
    until: str,
) -> tuple[float, int]:
    """REAL post-action metric: matching signals per day in [since, until]."""
    start = _parse_ts(since)
    end = _parse_ts(until)
    elapsed_days = max((end - start).total_seconds() / 86_400, 1.0)

    count = 0
    for signal in signals:
        if _norm_stage(signal.journey) != _norm_stage(journey):
            continue
        if _norm_stage(signal.journey_stage) != _norm_stage(journey_stage):
            continue
        try:
            ts = _parse_ts(signal.timestamp)
        except ValueError:
            continue
        if start <= ts <= end:
            count += 1
    return round(count / elapsed_days, 4), count


def run_due_measurements(
    *,
    plan_store: SQLiteMeasurementPlanStore,
    problem_lookup: Callable[[str], ProblemRecord | None],
    signal_store: Any,
    workflow_store: Any,
    telemetry: Any,
    now: str | None = None,
) -> dict[str, int]:
    """Process all due checkpoints. Returns {measured, manual_required, skipped}."""
    now = now or utc_now()
    measured = 0
    manual = 0
    skipped = 0

    for plan in plan_store.due(now):
        problem = problem_lookup(plan["problem_id"])
        if problem is None:
            plan_store.mark(plan["id"], status="skipped", note="Problem no longer exists")
            skipped += 1
            continue

        metric = problem.outcome_contract.primary_metric
        if not metric.startswith(SIGNAL_METRIC_PREFIX):
            # CLARA cannot observe this metric — surface a human task, never invent data.
            plan_store.mark(
                plan["id"],
                status="manual_required",
                note=f"Metric '{metric}' needs a human-recorded measurement.",
            )
            telemetry.record(
                "measurement_due",
                entity_id=problem.problem_id,
                metadata={"kind": plan["kind"], "metric": metric},
            )
            manual += 1
            continue

        journey, _, stage = metric.removeprefix(SIGNAL_METRIC_PREFIX).partition("/")
        rate, sample = signal_rate_per_day(
            signal_store.list_signals(),
            journey=journey.replace("_", " "),
            journey_stage=stage.replace("_", " "),
            since=plan["executed_at"],
            until=now,
        )
        measurement = OutcomeMeasurement(
            problem_id=problem.problem_id,
            metric=metric,
            observed_value=rate,
            measured_at=now,
            notes=(
                f"Auto-measured by the scheduler ({plan['kind']}): {sample} matching"
                f" signals since action execution. real_data_source=true"
            ),
        )
        try:
            workflow_store.record_outcome(problem=problem, measurement=measurement)
        except Exception:  # noqa: BLE001 — one bad plan must not stall the loop
            logger.exception("Scheduled measurement failed for %s", problem.problem_id)
            plan_store.mark(plan["id"], status="skipped", note="record_outcome failed")
            skipped += 1
            continue

        plan_store.mark(
            plan["id"], status="done", note=f"observed {rate}/day from {sample} signals"
        )
        telemetry.record(
            "outcome_recorded",
            entity_id=problem.problem_id,
            metadata={
                "source": "scheduler",
                "real_data_source": True,
                "kind": plan["kind"],
                "observed_value": rate,
            },
        )
        measured += 1

    return {"measured": measured, "manual_required": manual, "skipped": skipped}


def scheduler_enabled() -> bool:
    return os.getenv("CLARA_SCHEDULER_ENABLED", "1") not in ("0", "false", "False")


def attach_measurement_loop(api: Any, runner: Callable[[], dict[str, int]]) -> None:
    """Register a background asyncio loop on the FastAPI app (env-gated)."""
    if not scheduler_enabled():
        return

    state: dict[str, Any] = {}

    async def _loop() -> None:
        while True:
            try:
                # The runner does blocking work (SQLite, HTTP pulls to Zendesk or
                # Apple). Run it in a worker thread so a slow source sync never
                # freezes the event loop and with it every API request.
                result = await asyncio.to_thread(runner)
                if any(result.values()):
                    logger.info("Measurement loop: %s", result)
            except Exception:  # noqa: BLE001
                logger.exception("Measurement loop iteration failed")
            await asyncio.sleep(LOOP_INTERVAL_SECONDS)

    async def _start() -> None:
        state["task"] = asyncio.create_task(_loop())

    async def _stop() -> None:
        task = state.get("task")
        if task:
            task.cancel()

    api.add_event_handler("startup", _start)
    api.add_event_handler("shutdown", _stop)
