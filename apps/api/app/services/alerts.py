"""Proactive alerts: CLARA comes to you instead of waiting to be opened.

Two duties, both riding the existing background loop and the existing Slack
connector; both no-ops without an active Slack config:

1. Emerging-problem alerts: when the radar promotes something to the "action"
   trend, post it to Slack ONCE (dedup via a telemetry marker per emerging
   key, so restarts and repeated ticks never re-alert).
2. Weekly digest: the existing /digest/slack content, sent automatically when
   the last send is older than ~a week.

Honesty rule: alerts only relay what the stored radar/board already says;
nothing is computed specially for the notification.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Callable

logger = logging.getLogger(__name__)

ALERT_EVENT = "emerging_alerted"
DIGEST_EVENT = "digest_sent"
DIGEST_INTERVAL = timedelta(days=6, hours=12)  # weekly, tolerant of tick jitter


def _emerging_key(item: Any) -> str:
    return f"{item.journey}/{item.journey_stage}/{item.title}"[:200]


def _parse_ts(value: str) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def run_alert_sweep(
    *,
    emerging_report: Any,
    connector_config_store: Any,
    telemetry: Any,
    push_slack: Callable[[str, str, dict[str, Any]], None],
    build_digest_text: Callable[[], str],
    now: datetime | None = None,
) -> dict[str, int]:
    """One sweep: alert new action-grade emerging problems, send the weekly
    digest when due. Returns {alerted, digest_sent} counts for the loop log."""
    slack = connector_config_store.get_config("slack")
    if slack is None or not slack.is_active:
        return {"alerted": 0, "digest_sent": 0}

    alerted = 0
    for item in getattr(emerging_report, "signals", None) or []:
        if item.trend_label != "action":
            continue
        key = _emerging_key(item)
        if telemetry.has_event(ALERT_EVENT, key):
            continue
        try:
            push_slack(
                "CLARA: emerging problem needs attention",
                (
                    f"*{item.title}*\n"
                    f"{item.journey} / {item.journey_stage}. "
                    f"score {round(item.emerging_score * 100)}%, "
                    f"{item.signal_count} signals, {item.customer_count} customers, "
                    f"{item.source_count} sources.\n"
                    f"Review it in CLARA before it reaches the ticket queue."
                ),
                slack.config,
            )
        except Exception as exc:  # noqa: BLE001 — one failed post must not kill the loop
            logger.warning("Emerging alert failed: %s", str(exc)[:200])
            continue
        telemetry.record(ALERT_EVENT, entity_id=key, metadata={"score": item.emerging_score})
        alerted += 1

    digest_sent = 0
    current = now or datetime.now(timezone.utc)
    last_raw = telemetry.latest_event_at(DIGEST_EVENT)
    last = _parse_ts(last_raw) if last_raw else None
    if last is None or current - last >= DIGEST_INTERVAL:
        try:
            push_slack("CLARA weekly digest", build_digest_text(), slack.config)
            telemetry.record(DIGEST_EVENT, metadata={"channel": "slack", "trigger": "scheduled"})
            digest_sent = 1
        except Exception as exc:  # noqa: BLE001
            logger.warning("Scheduled digest failed: %s", str(exc)[:200])

    return {"alerted": alerted, "digest_sent": digest_sent}
