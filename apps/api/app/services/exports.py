"""CSV exports for the customer's own BI — warehouse EXPORT, not ingestion.

Analysts get the data out (signals, problems, outcomes, telemetry) as flat CSV
they can drop into Excel/Metabase/Power BI. Deliberately not a sync pipeline:
the LATER-block rule is export-only until a signed customer demands more.

Safety: cells are neutralized against CSV/formula injection (=, +, -, @ or tab
at the start of a cell would execute as a formula in Excel/Sheets — feedback
text is untrusted input, so every such cell gets a leading apostrophe).
"""

from __future__ import annotations

import csv
import io
from typing import Any

_FORMULA_PREFIXES = ("=", "+", "-", "@", "\t")


def _neutralize(value: Any) -> Any:
    if isinstance(value, str) and value.startswith(_FORMULA_PREFIXES):
        return "'" + value
    return value


def rows_to_csv(headers: list[str], rows: list[list[Any]]) -> str:
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(headers)
    for row in rows:
        writer.writerow([_neutralize(cell) for cell in row])
    return buffer.getvalue()


def signals_csv(signals: list[Any]) -> str:
    headers = [
        "signal_id", "customer_id", "account_id", "source", "journey",
        "journey_stage", "language", "timestamp", "feedback_text",
    ]
    rows = [
        [s.signal_id, s.customer_id, s.account_id, s.source, s.journey,
         s.journey_stage, s.language, s.timestamp, s.feedback_text]
        for s in signals
    ]
    return rows_to_csv(headers, rows)


def problems_csv(summaries: list[Any]) -> str:
    headers = [
        "problem_id", "title", "status", "journey", "journey_stage", "owner",
        "impact_score", "impact_band", "evidence_confidence",
        "affected_customers", "affected_accounts", "approval_pressure",
    ]
    rows = [
        [p.problem_id, p.title, p.status.value, p.journey, p.journey_stage, p.owner,
         p.impact_score, p.impact_band, p.evidence_confidence,
         p.affected_customers, p.affected_accounts, p.approval_pressure]
        for p in summaries
    ]
    return rows_to_csv(headers, rows)


# Provenance columns appended when the board items carry them: what produced
# the reading (instrumented | manual), which checkpoint, and the loop verdict.
OUTCOME_PROVENANCE_COLUMNS = ("measurement_source", "checkpoint_kind", "loop_verdict")


def outcomes_csv(board: Any) -> str:
    headers = [
        "problem_id", "title", "owner", "problem_status", "metric", "baseline",
        "success_threshold", "latest_value", "outcome_status",
        "improvement_direction", "measurement_window_days", "latest_learning_status",
    ]
    provenance = [
        name for name in OUTCOME_PROVENANCE_COLUMNS
        if any(hasattr(i, name) for i in board.items)
    ]
    headers.extend(provenance)
    rows = [
        [i.problem_id, i.title, i.owner, i.problem_status.value, i.metric, i.baseline,
         i.success_threshold, i.latest_value, i.outcome_status,
         i.improvement_direction, i.measurement_window_days,
         i.latest_learning_status.value if i.latest_learning_status else "",
         *[getattr(i, name, None) or "" for name in provenance]]
        for i in board.items
    ]
    return rows_to_csv(headers, rows)


def telemetry_csv(events: list[dict[str, Any]]) -> str:
    headers = ["id", "workspace_id", "event_type", "entity_id", "metadata", "created_at"]
    import json

    rows = [
        [e["id"], e["workspace_id"], e["event_type"], e["entity_id"] or "",
         json.dumps(e["metadata"], ensure_ascii=False), e["created_at"]]
        for e in events
    ]
    return rows_to_csv(headers, rows)
