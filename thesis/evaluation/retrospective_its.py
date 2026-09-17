"""Retrospective observational read of the shipped estimator on real, dated inflow (§3.5.5; §6.5 item 4).

Runs the artifact's own estimator (apps/api: outcome_engine.its_outcome_for_problem, the
code path a scheduled checkpoint uses) over a CSV of dated signals around a known
intervention date, and writes the graded readout the platform would have produced had
that intervention been a CLARA action dispatched on that date. It is a retrospective
observational read on real data, not a CLARA-caused action: it describes rather than
attributes, attribution is not established by an uncontrolled design, and the readout
says so.

    python3 thesis/evaluation/retrospective_its.py --csv signals.csv \
        --intervention 2026-05-14 --journey checkout --stage payment \
        [--window 30] [--now 2026-06-13] --out readout.json [--series-out series.csv]

CSV: the platform's signals export (GET /export/signals.csv: signal_id, customer_id,
account_id, source, journey, journey_stage, language, timestamp, feedback_text) or any
CSV with at least signal_id (or id), timestamp (ISO 8601) and journey, journey_stage.
Timestamps are the review's own date, never the collection date. Journey and stage
match case-insensitively with spaces read as underscores, as the platform groups them.

What the readout contains: the estimator's result (method "its" with effect and 95%
interval, or "delta_insufficient_data" with the labelled plain delta), the evidence
grade (C for a fitted segmented regression, D for a refused fit), the pre/post signal
counts and complete-day counts, and an interpretation in words. Nothing is written
into the thesis results directories by default; pass --out explicitly.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from collections import Counter
from datetime import UTC, datetime, timedelta

HERE = os.path.dirname(os.path.abspath(__file__))
API_DIR = os.path.normpath(os.path.join(HERE, "..", "..", "apps", "api"))
if API_DIR not in sys.path:
    sys.path.insert(0, API_DIR)

from app.domain.models import SignalRecord  # noqa: E402
from app.services.outcome_engine import (  # noqa: E402
    ITS_COMPARISON_METHOD,
    MIN_POST_DAYS,
    MIN_PRE_DAYS,
    TRAILING_BASELINE_DAYS,
    evidence_grade,
    its_outcome_for_problem,
)
from app.services.signals import build_candidates, promote_candidate  # noqa: E402


def _norm(value: str) -> str:
    return (value or "").strip().lower().replace(" ", "_")


def _parse_instant(text: str) -> datetime:
    value = text.strip()
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    moment = datetime.fromisoformat(value)
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=UTC)
    return moment.astimezone(UTC)


def _iso(moment: datetime) -> str:
    return moment.astimezone(UTC).isoformat().replace("+00:00", "Z")


def read_signals(path: str) -> list[SignalRecord]:
    with open(path, encoding="utf-8-sig", newline="") as fh:
        rows = list(csv.DictReader(fh))
    signals: list[SignalRecord] = []
    for row in rows:
        signal_id = (row.get("signal_id") or row.get("id") or "").strip()
        stamp = (row.get("timestamp") or row.get("created_at") or "").strip()
        if not signal_id or not stamp:
            continue
        signals.append(
            SignalRecord(
                signal_id=signal_id,
                feedback_text=(row.get("feedback_text") or row.get("text") or "").strip() or "(text withheld)",
                customer_id=(row.get("customer_id") or "").strip() or "unknown_customer",
                account_id=(row.get("account_id") or "").strip() or "unknown_account",
                source=(row.get("source") or "").strip() or "csv_upload",
                journey=_norm(row.get("journey") or "") or "unknown_journey",
                journey_stage=_norm(row.get("journey_stage") or "") or "unknown_stage",
                language=(row.get("language") or "").strip() or "unknown",
                timestamp=_iso(_parse_instant(stamp)),
            )
        )
    return signals


def daily_series(signals: list[SignalRecord]) -> list[tuple[str, int]]:
    counts = Counter(_parse_instant(s.timestamp).date() for s in signals)
    if not counts:
        return []
    first, last = min(counts), max(counts)
    day, out = first, []
    while day <= last:
        out.append((day.isoformat(), counts.get(day, 0)))
        day += timedelta(days=1)
    return out


def interpret(result: dict, *, grade: str, n_pre: int, n_post: int) -> str:
    if result.get("method") == "its":
        low, high = result["ci_low"], result["ci_high"]
        direction = "excludes" if (high < 0 or low > 0) else "includes"
        return (
            f"Segmented regression fitted on {result['n_pre']} pre and {result['n_post']} post complete "
            f"days (grade {grade}): model-implied change at the end of the window {result['effect']:+.4f} "
            f"signals/day, 95% interval [{low:+.4f}, {high:+.4f}], which {direction} zero. This is an "
            f"uncontrolled interrupted time series on {n_pre + n_post} signals: it describes what the inflow "
            "did around the date, and it does not attribute the change to the intervention."
        )
    return (
        f"Fit refused ({result.get('label', 'insufficient data')}): {result.get('n_pre')} pre and "
        f"{result.get('n_post')} post complete days against the estimator's minimum of {MIN_PRE_DAYS} and "
        f"{MIN_POST_DAYS}. The readout is the labelled plain difference of daily means, "
        f"{result.get('delta'):+.4f} signals/day, with no interval (grade {grade}). That refusal is the "
        "minimum-data rule of §3.5.5 acting on real inflow, not a null result."
    )


def readout(signals: list[SignalRecord], *, journey: str, stage: str, intervention: datetime,
            window_days: int, now: datetime | None = None) -> dict:
    journey, stage = _norm(journey), _norm(stage)
    scoped = [s for s in signals if s.journey == journey and s.journey_stage == stage]
    if not scoped:
        raise SystemExit(f"no signals for journey={journey!r} stage={stage!r}; "
                         f"available: {sorted({(s.journey, s.journey_stage) for s in signals})[:20]}")
    candidates = build_candidates(scoped)
    candidate = next((c for c in candidates if _norm(c.journey) == journey and _norm(c.journey_stage) == stage), None)
    if candidate is None:
        raise SystemExit("the platform's grouping produced no candidate for that journey/stage")
    problem = promote_candidate(candidate)
    problem = problem.model_copy(
        update={"outcome_contract": problem.outcome_contract.model_copy(update={"measurement_window_days": window_days})}
    )
    end = now or (intervention + timedelta(days=window_days))
    result = its_outcome_for_problem(problem, scoped, executed_at=_iso(intervention), now=_iso(end))
    if result is None:
        raise SystemExit("the contract metric is not a signal-rate metric; nothing to fit")
    grade = evidence_grade(
        comparison_method=ITS_COMPARISON_METHOD,
        measurement_source="instrumented",
        realised_method=result.get("method"),
    )
    pre_start = intervention - timedelta(days=TRAILING_BASELINE_DAYS)
    stamps = [_parse_instant(s.timestamp) for s in scoped]
    n_pre = sum(1 for t in stamps if pre_start <= t < intervention)
    n_post = sum(1 for t in stamps if intervention <= t <= end)
    return {
        "design": "retrospective observational read: interrupted time series on real inflow (uncontrolled; describes, does not attribute; §6.5 item 4)",
        "estimator": "apps/api/app/services/outcome_engine.its_outcome_for_problem (the scheduled-checkpoint code path)",
        "journey": journey,
        "journey_stage": stage,
        "intervention": _iso(intervention),
        "window_days": window_days,
        "observation_end": _iso(end),
        "signals_in_scope": len(scoped),
        "signals_pre_28d": n_pre,
        "signals_post_window": n_post,
        "result": result,
        "evidence_grade": grade,
        "interpretation": interpret(result, grade=grade, n_pre=n_pre, n_post=n_post),
        "caveats": [
            "The intervention was not a CLARA action; the date is supplied by the analyst.",
            "Uncontrolled design: trends, seasonality and concurrent events are not separated from the intervention.",
            "Complete UTC days only; the intervention day is excluded from the fit; no pre-window days are fabricated.",
        ],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--csv", required=True)
    parser.add_argument("--intervention", required=True, help="ISO date or instant (UTC)")
    parser.add_argument("--journey", required=True)
    parser.add_argument("--stage", required=True)
    parser.add_argument("--window", type=int, default=30, help="measurement window in days (default 30)")
    parser.add_argument("--now", default=None, help="observation end (default: intervention + window)")
    parser.add_argument("--out", required=True, help="where to write the JSON readout")
    parser.add_argument("--series-out", default=None, help="optional CSV of daily counts in scope")
    args = parser.parse_args(argv)

    signals = read_signals(args.csv)
    if not signals:
        raise SystemExit("no dated signals in the CSV (needs signal_id/id and timestamp columns)")
    intervention = _parse_instant(args.intervention)
    end = _parse_instant(args.now) if args.now else None
    report = readout(signals, journey=args.journey, stage=args.stage, intervention=intervention,
                     window_days=args.window, now=end)
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=2)
    if args.series_out:
        scoped = [s for s in signals if s.journey == _norm(args.journey) and s.journey_stage == _norm(args.stage)]
        with open(args.series_out, "w", encoding="utf-8", newline="") as fh:
            writer = csv.writer(fh)
            writer.writerow(["day", "signals"])
            writer.writerows(daily_series(scoped))
    print(f"grade {report['evidence_grade']}: {report['interpretation']}")
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
