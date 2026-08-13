from __future__ import annotations

import csv
import io
import json
import sqlite3

from app.services.common import SerializedConnection
from collections import Counter
from pathlib import Path

from app.services.common import normalize_timestamp
from app.domain.models import (
    JourneyEventImportResult,
    JourneyEventRecord,
    JourneyImpactSummary,
    ProblemRecord,
)
from app.domain.scoring import impact_band, normalized_impact_score

FRICTION_TERMS = ("abandon", "blocked", "drop", "error", "fail", "friction", "rage", "retry", "timeout")


def normalize(value: str) -> str:
    return value.replace("_", " ").replace("-", " ").strip().lower()


def parse_bool(value: str | None) -> bool | None:
    if value is None or not value.strip():
        return None
    return value.strip().lower() in {"1", "true", "yes", "y", "success", "succeeded"}


def parse_metadata(value: str | None) -> dict[str, str]:
    if not value:
        return {}
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return {}
    return {str(key): str(item) for key, item in parsed.items()} if isinstance(parsed, dict) else {}


def _parse_duration(value: str | None) -> float | None:
    """Parse duration_seconds, tolerating blank/non-numeric cells (no HTTP 500)."""
    if not value or not str(value).strip():
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None


def parse_journey_event_csv(csv_text: str) -> list[JourneyEventRecord]:
    reader = csv.DictReader(io.StringIO(csv_text.strip()))
    events: list[JourneyEventRecord] = []
    for index, row in enumerate(reader, start=1):
        events.append(
            JourneyEventRecord(
                event_id=row.get("event_id") or f"JEV-CSV-{index:04d}",
                customer_id=row.get("customer_id") or "unknown_customer",
                account_id=row.get("account_id") or "unknown_account",
                journey=row.get("journey") or "unknown_journey",
                journey_stage=row.get("journey_stage") or "unknown_stage",
                event_name=row.get("event_name") or "unknown_event",
                event_type=row.get("event_type") or "behavior",
                timestamp=normalize_timestamp(row.get("timestamp"))[0],
                success=parse_bool(row.get("success")),
                duration_seconds=_parse_duration(row.get("duration_seconds")),
                metadata=parse_metadata(row.get("metadata")),
            )
        )
    return events


def event_is_friction(event: JourneyEventRecord) -> bool:
    if event.success is False:
        return True
    haystack = f"{event.event_name} {event.event_type}".lower()
    return any(term in haystack for term in FRICTION_TERMS)


def event_matches_problem(event: JourneyEventRecord, problem: ProblemRecord) -> bool:
    customer_ids = {evidence.customer_id for evidence in problem.evidence}
    account_ids = {evidence.account_id for evidence in problem.evidence}
    return (
        (event.customer_id in customer_ids or event.account_id in account_ids)
        and normalize(event.journey) == normalize(problem.journey)
        and normalize(event.journey_stage) == normalize(problem.journey_stage)
    )


def summarize_journey_impact(
    problem: ProblemRecord,
    events: list[JourneyEventRecord],
) -> JourneyImpactSummary | None:
    matched = [event for event in events if event_matches_problem(event, problem)]
    if not matched:
        return None

    friction_events = [event for event in matched if event_is_friction(event)]
    event_counts = Counter(event.event_name for event in matched)
    deviation_score = min(1.0, (len(friction_events) / len(matched)) + min(0.25, len(matched) / 100))
    drivers = [
        f"{len(matched)} matched journey events for evidence customers/accounts.",
        f"{len(friction_events)} events show failed, blocked or retry behavior.",
    ]
    if event_counts:
        drivers.append(f"Most common event: {event_counts.most_common(1)[0][0]}.")

    return JourneyImpactSummary(
        matched_events=len(matched),
        matched_customers=len({event.customer_id for event in matched}),
        matched_accounts=len({event.account_id for event in matched}),
        friction_events=len(friction_events),
        deviation_score=round(deviation_score, 3),
        top_event_names=[event for event, _ in event_counts.most_common(5)],
        drivers=drivers,
    )


def enrich_problem_with_journey(
    problem: ProblemRecord,
    events: list[JourneyEventRecord],
) -> ProblemRecord:
    summary = summarize_journey_impact(problem, events)
    if summary is None:
        return problem.model_copy(update={"journey_impact": None})

    impact_factors = problem.impact_factors.model_copy(
        update={
            "journey_criticality": min(
                1.0,
                problem.impact_factors.journey_criticality + (summary.deviation_score * 0.18),
            ),
            "evidence_confidence": min(
                1.0,
                problem.impact_factors.evidence_confidence + min(0.08, summary.matched_events * 0.01),
            ),
        }
    )
    score = normalized_impact_score(impact_factors.model_dump())
    return problem.model_copy(
        update={
            "impact_factors": impact_factors,
            "evidence_confidence": impact_factors.evidence_confidence,
            "impact_score": score,
            "impact_band": impact_band(score),
            "journey_impact": summary,
        }
    )


class JourneyEventStore:
    def __init__(self) -> None:
        self._events: dict[str, JourneyEventRecord] = {}

    def list_events(self) -> list[JourneyEventRecord]:
        return sorted(self._events.values(), key=lambda event: event.timestamp)

    def delete_by_customer(self, customer_id: str) -> int:
        """GDPR Art. 17: remove every journey event belonging to a customer."""
        doomed = [eid for eid, e in self._events.items() if e.customer_id == customer_id]
        for event_id in doomed:
            del self._events[event_id]
        return len(doomed)

    def import_events(self, events: list[JourneyEventRecord]) -> JourneyEventImportResult:
        imported = 0
        skipped = 0
        for event in events:
            if event.event_id in self._events:
                skipped += 1
                continue
            self._events[event.event_id] = event
            imported += 1
        return JourneyEventImportResult(
            imported=imported,
            skipped_duplicates=skipped,
            total_events=len(self._events),
        )


class SQLiteJourneyEventStore:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._connection = SerializedConnection(self.path)
        self._initialize()

    def _initialize(self) -> None:
        self._connection.execute(
            """
            CREATE TABLE IF NOT EXISTS journey_events (
                event_id TEXT PRIMARY KEY,
                payload TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        self._connection.commit()

    def list_events(self) -> list[JourneyEventRecord]:
        rows = self._connection.execute(
            "SELECT payload FROM journey_events ORDER BY event_id"
        ).fetchall()
        return [JourneyEventRecord.model_validate(json.loads(row["payload"])) for row in rows]

    def delete_by_customer(self, customer_id: str) -> int:
        """GDPR Art. 17: remove every journey event belonging to a customer.

        Events are stored as JSON payloads, so match in Python (small scale).
        """
        doomed = [
            event.event_id for event in self.list_events() if event.customer_id == customer_id
        ]
        for event_id in doomed:
            self._connection.execute(
                "DELETE FROM journey_events WHERE event_id = ?", (event_id,)
            )
        self._connection.commit()
        return len(doomed)

    def import_events(self, events: list[JourneyEventRecord]) -> JourneyEventImportResult:
        imported = 0
        skipped = 0
        for event in events:
            try:
                self._connection.execute(
                    "INSERT INTO journey_events (event_id, payload) VALUES (?, ?)",
                    (event.event_id, json.dumps(event.model_dump(mode="json"))),
                )
                imported += 1
            except sqlite3.IntegrityError:
                skipped += 1
        self._connection.commit()
        total = self._connection.execute("SELECT COUNT(*) FROM journey_events").fetchone()[0]
        return JourneyEventImportResult(
            imported=imported,
            skipped_duplicates=skipped,
            total_events=total,
        )
