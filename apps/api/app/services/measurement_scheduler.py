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
# AI-theme contracts use the pseudo-journey "theme": the stage part of the
# metric is then a theme TAG and signals match by carrying that tag (written
# back by triage enrichment) instead of by journey/stage columns.
THEME_JOURNEY = "theme"
# "Keep listening": one more checkpoint a month after the measurement window
# closes, so a theme that comes back after a premature "target met" is caught.
FOLLOWUP_GAP_DAYS = 30
LOOP_CHECKPOINT_KINDS = frozenset({"window", "followup"})


def _parse_ts(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        # One naive timestamp must never crash a measurement run: mixing naive
        # and aware datetimes raises TypeError on comparison. Treat naive as UTC.
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


UNKNOWN_JOURNEY_N = "unknown journey"
UNKNOWN_STAGE_N = "unknown stage"
SOURCE_FEEDBACK_SUFFIX = " feedback"


def _norm_stage(value: str) -> str:
    """Journey names round-trip through the metric string as lowercase with
    underscores; normalize both sides so 'customer_onboarding' still matches
    after the metric parser turns it into 'customer onboarding'."""
    return value.lower().replace("_", " ").strip()


def signal_matches_scope(signal: Any, *, journey: str, journey_stage: str) -> bool:
    """Does a signal belong to a contract's scope?

    Journey/stage contracts (promoted from deterministic candidates) match on
    the journey and journey_stage columns. Theme contracts (promoted from AI
    triage themes; journey == "theme") match any signal carrying the theme tag,
    whatever journey it came from — the theme is the unit of ownership there.
    One helper, used by the scheduler, ITS scoring and contract proposals so
    all three count the same signals.
    """
    stage_n = _norm_stage(journey_stage)
    journey_n = _norm_stage(journey)
    if journey_n == THEME_JOURNEY:
        tags = {_norm_stage(str(tag)) for tag in (getattr(signal, "tags", None) or [])}
        return stage_n in tags
    if _norm_stage(signal.journey) != journey_n:
        return False
    signal_stage_n = _norm_stage(signal.journey_stage)
    if signal_stage_n == stage_n:
        return True
    # Journey-less feedback (connector/CSV rows without journey metadata) is
    # grouped per source by build_candidates as "<source>_feedback" while the
    # signals themselves keep journey_stage "unknown_stage". The contract
    # promoted from such a candidate must count those same signals — otherwise
    # every measurement reads 0/day and the loop "closes" without evidence.
    return (
        journey_n == UNKNOWN_JOURNEY_N
        and signal_stage_n == UNKNOWN_STAGE_N
        and stage_n.endswith(SOURCE_FEEDBACK_SUFFIX)
        and _norm_stage(f"{getattr(signal, 'source', '')} feedback") == stage_n
    )


def unenriched_in_window(signals: list[Any], *, since: str, until: str) -> int:
    """Signals inside [since, until] that triage has not enriched yet.

    Theme contracts are counted by tag, and tags only exist after enrichment.
    A window with unenriched signals cannot be read honestly: the count would
    under-report and a theme could be declared "closed" merely because triage
    was never run on the new inflow.
    """
    start = _parse_ts(since)
    end = _parse_ts(until)
    pending = 0
    for signal in signals:
        if getattr(signal, "enriched", False):
            continue
        try:
            ts = _parse_ts(signal.timestamp)
        except ValueError:
            continue
        if start <= ts <= end:
            pending += 1
    return pending


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
    ) -> bool:
        """Insert one checkpoint; False when an equivalent pending plan exists.

        One pending plan per problem+kind — re-approving (or approving a second
        action on the same problem) must not double-schedule or restart the clock.
        """
        existing = self._connection.execute(
            "SELECT id FROM measurement_plans WHERE problem_id = ? AND kind = ?"
            " AND status IN ('pending', 'manual_required')",
            (problem_id, kind),
        ).fetchone()
        if existing:
            return False
        self._connection.execute(
            "INSERT INTO measurement_plans"
            " (problem_id, execution_id, executed_at, due_at, kind, created_at)"
            " VALUES (?, ?, ?, ?, ?, ?)",
            (problem_id, execution_id, executed_at, due_at, kind, utc_now()),
        )
        self._connection.commit()
        return True

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
    # Keep listening after the window closes: the pitch's "if the theme drops
    # the following month, the loop worked; if not, the fix didn't land".
    checkpoints["followup"] = window_days + FOLLOWUP_GAP_DAYS

    scheduled: list[str] = []
    for kind, days in checkpoints.items():
        due_at = (executed + timedelta(days=days)).isoformat().replace("+00:00", "Z")
        inserted = plan_store.schedule(
            problem_id=problem.problem_id,
            execution_id=execution_id,
            executed_at=executed_at,
            due_at=due_at,
            kind=kind,
        )
        # Stores return False when the checkpoint already exists (a second approved
        # action on the same problem); only report what was really scheduled so
        # telemetry never claims a clock that did not start.
        if inserted is not False:
            scheduled.append(kind)
    return scheduled


def followup_window_start(executed_at: str, window_days: int) -> str:
    """The keep-listening read covers the month AFTER the measurement window,
    not the cumulative span since execution: averaged over [executed, now] a
    theme that fully returns in month two would still read as improved."""
    start = _parse_ts(executed_at) + timedelta(days=window_days)
    return start.isoformat().replace("+00:00", "Z")


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
        if not signal_matches_scope(signal, journey=journey, journey_stage=journey_stage):
            continue
        try:
            ts = _parse_ts(signal.timestamp)
        except ValueError:
            continue
        if start <= ts <= end:
            count += 1
    return round(count / elapsed_days, 4), count


# Guardrail measurement (design: docs/engineering/guardrail-measurement-design.md).
# Non-inferiority vs the pre-window baseline; a breach is informative, never
# blocking. Unmeasurable guardrails surface "no_data_source" explicitly so a
# declared guardrail can never silently stay decorative.
MEASURABLE_GUARDRAILS = {"repeat_signal_rate"}
GUARDRAIL_BREACH_FACTOR = 1.2  # >20% relative worsening flags a breach
GUARDRAIL_BASELINE_DAYS = 28


def measure_guardrails(
    problem: ProblemRecord,
    signals: list[Any],
    *,
    executed_at: str,
    now: str,
    workflow_store: Any,
) -> int:
    """Record one readout per declared guardrail metric. Returns records written."""
    from app.services.signals import UNKNOWN_IDENTITY_VALUES

    written = 0
    for metric in problem.outcome_contract.guardrail_metrics:
        if metric not in MEASURABLE_GUARDRAILS:
            workflow_store.add_guardrail_measurement(
                problem_id=problem.problem_id,
                metric=metric,
                status="no_data_source",
                measured_at=now,
                note=(
                    "Declared guardrail has no data source yet "
                    "(requires outbound sends / opt-out events)."
                ),
            )
            written += 1
            continue

        # repeat_signal_rate: theme signals/day post-execution from customers
        # already seen in the pre-window. Identity-less signals are excluded —
        # an "unknown_customer" row cannot prove a repeat complainer.
        start = _parse_ts(executed_at)
        pre_start = start - timedelta(days=GUARDRAIL_BASELINE_DAYS)
        end = _parse_ts(now)

        def _matches(sig: Any) -> bool:
            return signal_matches_scope(
                sig, journey=problem.journey, journey_stage=problem.journey_stage
            )

        pre_count = 0
        pre_customers: set[str] = set()
        repeat_count = 0
        for sig in signals:
            if not _matches(sig) or sig.customer_id in UNKNOWN_IDENTITY_VALUES:
                continue
            try:
                ts = _parse_ts(sig.timestamp)
            except ValueError:
                continue
            if pre_start <= ts < start:
                pre_count += 1
                pre_customers.add(sig.customer_id)
        for sig in signals:
            if not _matches(sig) or sig.customer_id not in pre_customers:
                continue
            try:
                ts = _parse_ts(sig.timestamp)
            except ValueError:
                continue
            if start <= ts <= end:
                repeat_count += 1

        pre_days = max((start - pre_start).total_seconds() / 86_400, 1.0)
        post_days = max((end - start).total_seconds() / 86_400, 1.0)
        baseline = round(pre_count / pre_days, 4)
        observed = round(repeat_count / post_days, 4)
        breached = (
            observed > baseline * GUARDRAIL_BREACH_FACTOR if baseline > 0 else observed > 0
        )
        workflow_store.add_guardrail_measurement(
            problem_id=problem.problem_id,
            metric=metric,
            status="breach" if breached else "ok",
            observed_value=observed,
            baseline=baseline,
            measured_at=now,
            note=(
                f"{repeat_count} repeat signal(s) from {len(pre_customers)} pre-window "
                "customer(s); identity-less signals excluded."
            ),
        )
        written += 1
    return written


def run_due_measurements(
    *,
    plan_store: SQLiteMeasurementPlanStore,
    problem_lookup: Callable[[str], ProblemRecord | None],
    signal_store: Any,
    workflow_store: Any,
    telemetry: Any,
    now: str | None = None,
) -> dict[str, int]:
    """Process all due checkpoints. Returns {measured, manual_required, skipped,
    loop_closed, fix_did_not_land}.

    The last two count window/followup checkpoints whose real-signal readout
    met the contract target (the loop closed) or showed no improvement (the
    fix did not land) — the pitch's proof step, written to telemetry so the
    leadership view and alerts can pick it up without re-deriving it.
    """
    now = now or utc_now()
    measured = 0
    manual = 0
    skipped = 0
    loop_closed = 0
    fix_did_not_land = 0

    for plan in plan_store.due(now):
        problem = problem_lookup(plan["problem_id"])
        if problem is None:
            plan_store.mark(plan["id"], status="skipped", note="Problem no longer exists")
            skipped += 1
            continue

        signals = signal_store.list_signals()
        try:
            measure_guardrails(
                problem,
                signals,
                executed_at=plan["executed_at"],
                now=now,
                workflow_store=workflow_store,
            )
        except Exception:  # noqa: BLE001 — guardrails must not stall the loop
            logger.exception("Guardrail measurement failed for %s", problem.problem_id)

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
        since = plan["executed_at"]
        span_note = "since action execution"
        if plan["kind"] == "followup":
            since = followup_window_start(
                plan["executed_at"], problem.outcome_contract.measurement_window_days
            )
            span_note = "in the month after the measurement window closed (keep-listening read)"
        if _norm_stage(journey) == THEME_JOURNEY:
            pending_enrichment = unenriched_in_window(signals, since=since, until=now)
            if pending_enrichment:
                # Stay pending (re-tried next tick) and say why: the readout
                # would be silently incomplete until triage tags the new inflow.
                plan_store.mark(
                    plan["id"],
                    status="pending",
                    note=(
                        f"{pending_enrichment} in-window signals not yet enriched — run triage"
                        " before this theme can be measured"
                    ),
                )
                skipped += 1
                continue
        rate, sample = signal_rate_per_day(
            signals,
            journey=journey.replace("_", " "),
            journey_stage=stage.replace("_", " "),
            since=since,
            until=now,
        )
        measurement = OutcomeMeasurement(
            problem_id=problem.problem_id,
            metric=metric,
            observed_value=rate,
            measured_at=now,
            measurement_source="instrumented",
            notes=(
                f"Auto-measured by the scheduler ({plan['kind']}): {sample} matching"
                f" signals {span_note}. real_data_source=true"
            ),
        )
        try:
            workflow_store.record_outcome(problem=problem, measurement=measurement)
        except Exception as exc:  # noqa: BLE001 — one bad plan must not stall the loop
            detail = str(getattr(exc, "detail", "") or exc)[:200]
            if getattr(exc, "status_code", None) == 409:
                # A newer (manual) measurement exists: say so instead of a
                # generic skip, so the checkpoint panel can show why.
                plan_store.mark(plan["id"], status="blocked", note=detail)
            else:
                logger.exception("Scheduled measurement failed for %s", problem.problem_id)
                plan_store.mark(plan["id"], status="skipped", note=f"record_outcome failed: {detail}")
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

        # Loop verdict on the closing checkpoints only — the T+7 early read is
        # too soon to declare either way (detectability_note explains why).
        if plan["kind"] in LOOP_CHECKPOINT_KINDS:
            try:
                status = workflow_store.outcome_snapshot(problem).status
            except Exception:  # noqa: BLE001 — a verdict must never stall the loop
                logger.exception("Loop verdict failed for %s", problem.problem_id)
                status = None
            verdict_event = None
            if status == "target_met":
                verdict_event = "loop_closed"
                loop_closed += 1
            elif status == "not_improved":
                verdict_event = "fix_did_not_land"
                fix_did_not_land += 1
            if verdict_event:
                telemetry.record(
                    verdict_event,
                    entity_id=problem.problem_id,
                    metadata={
                        "kind": plan["kind"],
                        "metric": metric,
                        "observed_value": rate,
                        "baseline": problem.outcome_contract.baseline,
                        "success_threshold": problem.outcome_contract.success_threshold,
                        "real_data_source": True,
                    },
                )

    return {
        "measured": measured,
        "manual_required": manual,
        "skipped": skipped,
        "loop_closed": loop_closed,
        "fix_did_not_land": fix_did_not_land,
    }


def measure_guardrails_for_processed(
    processed: list[dict[str, Any]],
    *,
    problem_lookup: Callable[[str], ProblemRecord | None],
    signal_store: Any,
    workflow_store: Any,
    now: str | None = None,
) -> int:
    """Guardrail readouts for plans the DB-side tick already measured.

    clara_run_due_measurements (pg_cron) writes the outcome record but has no
    guardrail branch; without this pass every declared guardrail stayed
    decorative on Postgres while the SQLite path measured it. Returns the
    number of guardrail records written.
    """
    if not processed:
        return 0
    now = now or utc_now()
    signals = signal_store.list_signals()
    written = 0
    for plan in processed:
        problem = problem_lookup(str(plan.get("problem_id")))
        executed_at = plan.get("executed_at")
        if problem is None or not executed_at:
            continue
        try:
            written += measure_guardrails(
                problem, signals, executed_at=str(executed_at), now=now, workflow_store=workflow_store
            )
        except Exception:  # noqa: BLE001 — guardrails must not stall the loop
            logger.exception("Guardrail measurement failed for %s", problem.problem_id)
    return written


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

    # Starlette removed the deprecated startup/shutdown event API (Render's
    # fresh dependency resolve hit the removal; local envs still had it).
    # Compose the router's lifespan instead — supported on every version
    # since 0.26, so this runs identically on old and new stacks.
    from contextlib import asynccontextmanager

    existing_lifespan = api.router.lifespan_context

    @asynccontextmanager
    async def _lifespan_with_loop(app):
        await _start()
        try:
            async with existing_lifespan(app) as maybe_state:
                yield maybe_state
        finally:
            await _stop()

    api.router.lifespan_context = _lifespan_with_loop
