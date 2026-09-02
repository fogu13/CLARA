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
LOOP_ALERT_EVENT = "fix_did_not_land_alerted"
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
    send_email: Callable[[str, str, str], bool] | None = None,
    digest_email: str | None = None,
    now: datetime | None = None,
    outcome_board: Any = None,
) -> dict[str, int]:
    """One sweep: alert new action-grade emerging problems, alert once per
    problem whose fix demonstrably did not land (loop verdict), and send the
    weekly digest when due (Slack and/or email — an email-only workspace still
    gets its digest). Returns {alerted, loop_alerted, digest_sent}."""
    slack = connector_config_store.get_config("slack")
    if slack is not None and not slack.is_active:
        slack = None
    email_ready = bool(send_email and digest_email)
    if slack is None and not email_ready:
        return {"alerted": 0, "loop_alerted": 0, "digest_sent": 0}

    alerted = 0
    loop_alerted = 0
    # "Fix did not land": the closing checkpoint showed no improvement. This is
    # the pitch's proof step failing, so it must reach the owning team — a
    # telemetry row nobody reads is not an alert. Once per problem.
    for item in list(getattr(outcome_board, "items", None) or []):
        if getattr(item, "loop_verdict", None) != "fix_did_not_land":
            continue
        key = str(item.problem_id)
        if telemetry.has_event(LOOP_ALERT_EVENT, key):
            continue
        title = "CLARA: fix did not land"
        body = (
            f"*{item.title}*\n"
            f"Owner {item.owner}. Post-fix inflow {item.latest_value} vs baseline {item.baseline} "
            f"(target {item.success_threshold}) on {item.metric}: the closing checkpoint shows no "
            "improvement. Re-open the problem or record why the fix did not land."
        )
        delivered = False
        if slack is not None:
            try:
                push_slack(title, body, slack.config)
                delivered = True
            except Exception as exc:  # noqa: BLE001
                logger.warning("Loop alert Slack push failed: %s", str(exc)[:200])
        if not delivered and email_ready:
            try:
                delivered = bool(send_email(digest_email, title, body.replace("*", "")))
            except Exception as exc:  # noqa: BLE001
                logger.warning("Loop alert email failed: %s", str(exc)[:200])
        if delivered:
            telemetry.record(LOOP_ALERT_EVENT, entity_id=key, metadata={"metric": item.metric})
            loop_alerted += 1
    if slack is None:
        emerging_iter: list[Any] = []  # emerging alerts stay Slack-only for now
    else:
        emerging_iter = list(getattr(emerging_report, "signals", None) or [])
    for item in emerging_iter:
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
        digest_text = build_digest_text()
        channels: list[str] = []
        if slack is not None:
            try:
                push_slack("CLARA weekly digest", digest_text, slack.config)
                channels.append("slack")
            except Exception as exc:  # noqa: BLE001
                logger.warning("Scheduled Slack digest failed: %s", str(exc)[:200])
        if email_ready:
            try:
                if send_email(digest_email, "CLARA weekly digest", digest_text):
                    channels.append("email")
            except Exception as exc:  # noqa: BLE001
                logger.warning("Scheduled email digest failed: %s", str(exc)[:200])
        if channels:
            telemetry.record(
                DIGEST_EVENT, metadata={"channel": ",".join(channels), "trigger": "scheduled"}
            )
            digest_sent = 1

    return {"alerted": alerted, "loop_alerted": loop_alerted, "digest_sent": digest_sent}
