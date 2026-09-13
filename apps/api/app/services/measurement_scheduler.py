"""Scheduled outcome re-measurement; closes the loop without a human remembering.

Measurement checkpoints are scheduled at T+7 days, T+measurement_window_days
and a keep-listening follow-up. T is the plan's *origin*: ``dispatch`` when the
approved action really left CLARA (dispatched_at), ``implementation`` when a
human recorded that the fix landed (implemented_at), and ``approval`` only when
the draft itself is the deliverable (no connector for the destination). A
failed push starts no clock. When a checkpoint comes due:

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

import json

from app.domain.models import OutcomeContract, OutcomeMeasurement, ProblemRecord
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
# Where a plan's clock starts (see module docstring). ``approval`` is the
# legacy default for rows that predate the origin column.
PLAN_ORIGINS = frozenset({"approval", "dispatch", "implementation"})
DEFAULT_PLAN_ORIGIN = "approval"
# Precedence between clocks: a later, more real origin replaces the plans of a
# lower one (a real push moves the clock off the approval; an implementation
# record moves it off both).
ORIGIN_RANK = {"approval": 0, "dispatch": 1, "implementation": 2}


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
                created_at TEXT NOT NULL,
                origin TEXT NOT NULL DEFAULT 'approval',
                contract_revision INTEGER,
                contract_json TEXT,
                observation_start TEXT,
                observation_end TEXT
            )
            """
        )
        # Databases created before the origin/revision columns existed, and
        # before the frozen terms / observation interval (13 Sep 2026 review).
        self._ensure_column("origin", "TEXT NOT NULL DEFAULT 'approval'")
        self._ensure_column("contract_revision", "INTEGER")
        self._ensure_column("contract_json", "TEXT")
        self._ensure_column("observation_start", "TEXT")
        self._ensure_column("observation_end", "TEXT")
        self._connection.commit()

    def _ensure_column(self, column: str, definition: str) -> None:
        columns = {
            row["name"]
            for row in self._connection.execute("PRAGMA table_info(measurement_plans)").fetchall()
        }
        if column not in columns:
            self._connection.execute(
                f"ALTER TABLE measurement_plans ADD COLUMN {column} {definition}"
            )

    def schedule(
        self,
        *,
        problem_id: str,
        execution_id: str,
        executed_at: str,
        due_at: str,
        kind: str,
        origin: str = DEFAULT_PLAN_ORIGIN,
        contract_revision: int | None = None,
        contract_snapshot: OutcomeContract | dict[str, Any] | None = None,
        observation_start: str | None = None,
        observation_end: str | None = None,
    ) -> bool:
        """Insert one checkpoint; False when an equivalent pending plan exists.

        One pending plan per problem+kind — re-approving (or approving a second
        action on the same problem) must not double-schedule or restart the clock.
        ``contract_snapshot`` freezes the scoring terms the checkpoint will be
        read under; ``observation_start``/``observation_end`` fix the interval
        it reads, whenever the worker gets to it.
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
            " (problem_id, execution_id, executed_at, due_at, kind, created_at,"
            "  origin, contract_revision, contract_json, observation_start, observation_end)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                problem_id,
                execution_id,
                executed_at,
                due_at,
                kind,
                utc_now(),
                origin,
                contract_revision,
                contract_snapshot_json(contract_snapshot),
                observation_start,
                observation_end,
            ),
        )
        self._connection.commit()
        return True

    def supersede_pending(
        self, problem_id: str, *, note: str, origins: set[str] | None = None
    ) -> int:
        """Mark a problem's LIVE plans (pending or manual_required — the ones
        holding a checkpoint slot) as superseded, optionally only those whose
        clock runs from one of ``origins``. Returns rows changed."""
        sql = (
            "UPDATE measurement_plans SET status = 'superseded', note = ?"
            " WHERE problem_id = ? AND status IN ('pending', 'manual_required')"
        )
        params: list[Any] = [note, problem_id]
        if origins is not None:
            wanted = sorted(origins)
            if not wanted:
                return 0
            sql += f" AND origin IN ({', '.join('?' for _ in wanted)})"
            params.extend(wanted)
        cursor = self._connection.execute(sql, params)
        self._connection.commit()
        return cursor.rowcount

    @staticmethod
    def _plan(row: Any) -> dict[str, Any]:
        plan = dict(row)
        raw = plan.pop("contract_json", None)
        plan["contract_snapshot"] = json.loads(raw) if raw else None
        return plan

    def list_plans(self) -> list[dict[str, Any]]:
        rows = self._connection.execute(
            "SELECT * FROM measurement_plans ORDER BY due_at, id"
        ).fetchall()
        return [self._plan(row) for row in rows]

    def due(self, now: str) -> list[dict[str, Any]]:
        rows = self._connection.execute(
            "SELECT * FROM measurement_plans WHERE status = 'pending' AND due_at <= ?"
            " ORDER BY due_at, id",
            (now,),
        ).fetchall()
        return [self._plan(row) for row in rows]

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
    origin: str,
    contract_revision: int | None = None,
) -> list[str]:
    """Schedule the T+7, T+window and follow-up checkpoints for an action.

    ``origin`` names what ``executed_at`` is: the dispatch instant of a real
    push, the human-recorded implementation instant, or — only when the draft
    is the deliverable — the approval. ``contract_revision`` records which
    contract terms the checkpoints were scheduled under (defaults to the
    problem's current revision). Returns the kinds actually inserted: nothing
    when a higher-ranked clock already governs the problem.
    """
    if origin not in PLAN_ORIGINS:
        raise ValueError(f"Unknown measurement origin: {origin!r}")
    if contract_revision is None:
        contract_revision = problem.outcome_contract.revision
    # Origin precedence: live plans on a lower-ranked clock give way (a real
    # push after a draft-only approval moves the clock to the dispatch); a
    # same-or-higher clock keeps its plans and the insert below dedupes.
    higher = {name for name, rank in ORIGIN_RANK.items() if rank > ORIGIN_RANK[origin]}
    if higher and any(
        str(plan.get("problem_id")) == problem.problem_id
        and (plan.get("origin") or DEFAULT_PLAN_ORIGIN) in higher
        and plan.get("status") in ("pending", "manual_required", "done", "blocked")
        for plan in plan_store.list_plans()
    ):
        # A higher-ranked clock already governs this problem (live or already
        # read): a lower clock must not re-open its checkpoints, or a later
        # draft-only approval would certify the loop on the approval clock
        # after the real dispatch was measured.
        return []
    lower = {name for name, rank in ORIGIN_RANK.items() if rank < ORIGIN_RANK[origin]}
    if lower:
        plan_store.supersede_pending(
            problem.problem_id,
            note=f"superseded by {origin} clock ({execution_id})",
            origins=lower,
        )
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
        start, end = observation_interval(kind, executed_at=executed_at, due_at=due_at)
        inserted = plan_store.schedule(
            problem_id=problem.problem_id,
            execution_id=execution_id,
            executed_at=executed_at,
            due_at=due_at,
            kind=kind,
            origin=origin,
            contract_revision=contract_revision,
            # The terms the checkpoint will be scored under and the interval it
            # reads are fixed now; neither moves with a later amendment or a
            # late worker (13 Sep 2026 review, F2/F3).
            contract_snapshot=problem.outcome_contract,
            observation_start=start,
            observation_end=end,
        )
        # Stores return False when the checkpoint already exists (a second approved
        # action on the same problem); only report what was really scheduled so
        # telemetry never claims a clock that did not start.
        if inserted is not False:
            scheduled.append(kind)
    return scheduled


def contract_snapshot_json(contract: OutcomeContract | dict[str, Any] | None) -> str | None:
    if contract is None:
        return None
    payload = contract.model_dump(mode="json") if isinstance(contract, OutcomeContract) else dict(contract)
    return json.dumps(payload, sort_keys=True)


def observation_interval(kind: str, *, executed_at: str, due_at: str) -> tuple[str, str]:
    """The inclusive interval a checkpoint reads: from the clock origin to its
    due instant for the T+7 and window reads; the month before the due
    instant for the keep-listening follow-up (``followup_window_start``)."""
    if kind == "followup":
        return followup_window_start(due_at), due_at
    return executed_at, due_at


def plan_observation_interval(plan: dict[str, Any]) -> tuple[str, str | None, bool]:
    """(start, end, fixed) for a plan row: the stored interval when the plan
    carries one; else the legacy bounds (the follow-up's own month, or
    ``executed_at`` open-ended), flagged fixed=False."""
    start = plan.get("observation_start")
    end = plan.get("observation_end")
    if start and end:
        return str(start), str(end), True
    if plan["kind"] == "followup":
        return followup_window_start(plan["due_at"]), plan["due_at"], False
    return plan["executed_at"], None, False


def plan_scoring_terms(
    plan: dict[str, Any], problem: ProblemRecord
) -> tuple[OutcomeContract | None, str | None]:
    """The contract terms a due checkpoint is scored under.

    A plan scheduled since the 13 Sep 2026 review carries a frozen
    ``contract_snapshot``: those terms, whatever the contract says now (an
    amendment re-plans pending checkpoints explicitly, see
    ``replan_after_amendment``). A legacy plan without one is scored under
    the current contract only when the link is deterministic: the revision
    recorded on the plan (revision 1 for rows that predate revisions) equals
    the problem's current revision, so no amendment happened in between.
    Otherwise (None, reason): the checkpoint is blocked rather than scored
    under terms it was not scheduled with.
    """
    snapshot = plan.get("contract_snapshot")
    if snapshot:
        contract = snapshot if isinstance(snapshot, OutcomeContract) else OutcomeContract.model_validate(snapshot)
        return contract, None
    scheduled_under = plan.get("contract_revision") or 1
    current = problem.outcome_contract.revision
    if scheduled_under == current:
        return problem.outcome_contract, None
    return None, (
        f"contract amended after scheduling (revision {scheduled_under} -> {current}) and the"
        " plan carries no frozen terms; amend the contract again to re-plan its checkpoints"
    )


def replan_after_amendment(
    plan_store: SQLiteMeasurementPlanStore,
    *,
    problem: ProblemRecord,
    note: str,
) -> dict[str, Any]:
    """Explicit supersession and re-planning after a contract amendment.

    Every live checkpoint (pending or manual_required) of the problem is
    marked superseded with ``note`` and re-scheduled under the amended terms
    from the SAME clock (origin, execution, instant): the reading a pending
    checkpoint will produce must be scored under terms a human chose for it,
    never under terms that changed underneath it. Done plans and their
    readings are untouched. Returns {superseded, kinds, clock}.
    """
    live = [
        plan
        for plan in plan_store.list_plans()
        if str(plan.get("problem_id")) == problem.problem_id
        and plan.get("status") in ("pending", "manual_required")
    ]
    if not live:
        return {"superseded": 0, "kinds": [], "clock": None}
    # Live plans share one clock (origin precedence keeps a single origin
    # live); take the highest-ranked one defensively.
    anchor = max(live, key=lambda plan: ORIGIN_RANK.get(plan.get("origin") or DEFAULT_PLAN_ORIGIN, 0))
    superseded = plan_store.supersede_pending(problem.problem_id, note=note)
    kinds = schedule_measurements(
        plan_store,
        problem=problem,
        execution_id=str(anchor["execution_id"]),
        executed_at=str(anchor["executed_at"]),
        origin=anchor.get("origin") or DEFAULT_PLAN_ORIGIN,
    )
    return {
        "superseded": superseded,
        "kinds": kinds,
        "clock": {"origin": anchor.get("origin") or DEFAULT_PLAN_ORIGIN, "executed_at": anchor["executed_at"], "execution_id": anchor["execution_id"]},
    }


def followup_window_start(due_at: str, gap_days: int = FOLLOWUP_GAP_DAYS) -> str:
    """The keep-listening read covers the month BEFORE the follow-up came due —
    i.e. the month after the measurement window the plan was scheduled with —
    not the cumulative span since execution: averaged over [executed, now] a
    theme that fully returns in month two would still read as improved.

    Derived from the plan's own ``due_at`` (fixed at scheduling as
    executed + window + gap): a window amended after scheduling must not
    rewrite what the follow-up reads."""
    start = _parse_ts(due_at) - timedelta(days=gap_days)
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
    until: str | None = None,
) -> int:
    """Record one readout per declared guardrail metric. Returns records written.

    The post period is ``[executed_at, until]`` — the checkpoint's fixed
    observation end when the caller has one — so a late worker reads the same
    period as a punctual one; ``now`` stays the readout's processing stamp."""
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
        end = _parse_ts(until or now)

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

        # The terms this checkpoint is scored under: frozen on the plan, or
        # deterministically the current ones; never terms that changed
        # underneath a pending checkpoint.
        contract, blocked_reason = plan_scoring_terms(plan, problem)
        if contract is None:
            plan_store.mark(plan["id"], status="blocked", note=blocked_reason)
            telemetry.record(
                "measurement_blocked",
                entity_id=problem.problem_id,
                metadata={"kind": plan["kind"], "plan_id": plan["id"], "reason": blocked_reason},
            )
            skipped += 1
            continue
        # The interval this checkpoint reads: fixed at scheduling; a late
        # worker reads the same interval as a punctual one.
        obs_start, obs_end, fixed_interval = plan_observation_interval(plan)
        until = obs_end or now

        signals = signal_store.list_signals()
        try:
            measure_guardrails(
                problem,
                signals,
                executed_at=plan["executed_at"],
                now=now,
                workflow_store=workflow_store,
                until=obs_end if fixed_interval else None,
            )
        except Exception:  # noqa: BLE001 — guardrails must not stall the loop
            logger.exception("Guardrail measurement failed for %s", problem.problem_id)

        metric = contract.primary_metric
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
        since = obs_start
        origin = plan.get("origin") or DEFAULT_PLAN_ORIGIN
        span_note = f"since {origin} ({str(plan['executed_at'])[:10]})"
        if fixed_interval:
            span_note = (
                f"in the fixed interval {str(obs_start)[:10]}..{str(obs_end)[:10]}"
                f" (clock from {origin} {str(plan['executed_at'])[:10]})"
            )
        elif plan["kind"] == "followup":
            span_note = (
                "in the month after the measurement window closed (keep-listening read;"
                f" clock from {origin} {str(plan['executed_at'])[:10]})"
            )
        if _norm_stage(journey) == THEME_JOURNEY:
            pending_enrichment = unenriched_in_window(signals, since=since, until=until)
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
            until=until,
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
            # Bind the observation to the checkpoint that produced it and to
            # the contract terms it was scored under (mirrored by the plpgsql
            # tick in migration 017).
            checkpoint_kind=plan["kind"],
            plan_id=plan["id"],
            execution_id=plan.get("execution_id"),
            contract_revision=contract.revision,
            contract_snapshot=contract,
            # The clock this reading was taken on, so a later anchor (an
            # implementation recorded afterwards) cannot relabel it.
            clock_origin=origin,
            clock_origin_at=plan["executed_at"],
            # The interval it covers (fixed at scheduling; legacy plans read
            # up to the processing instant and say so through a None end).
            observation_start=obs_start,
            observation_end=obs_end if fixed_interval else None,
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
        # Scored under the terms the reading was taken under (its frozen
        # snapshot), which outcome_snapshot honours.
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
                        "baseline": contract.baseline,
                        "success_threshold": contract.success_threshold,
                        "contract_revision": contract.revision,
                        "observation_start": obs_start,
                        "observation_end": obs_end if fixed_interval else None,
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
                problem,
                signals,
                executed_at=str(executed_at),
                now=now,
                workflow_store=workflow_store,
                until=plan.get("observation_end") or None,
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
