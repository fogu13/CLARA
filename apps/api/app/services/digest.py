"""Weekly digest; CLARA shows up in Slack whether anyone logs in or not.

Summarizes: emerging problems (what's heating up), open loops (approved actions
whose outcome is not yet measured), and measured outcomes (wins/losses). Built
from stored records only; pushed through the existing Slack connector.

ponytail: triggered via POST /digest/slack (external cron / pilot success
manager); fold into the measurement loop with a weekly gate if pilots ask.
"""

from __future__ import annotations

from typing import Any


def build_digest(
    *,
    emerging: dict[str, Any] | Any,
    outcome_board: Any,
    measurement_plans: list[dict[str, Any]],
) -> str:
    """Compose the digest text (Slack-friendly plain text/mrkdwn)."""
    lines: list[str] = ["*CLARA weekly digest*", ""]

    emerging_signals = getattr(emerging, "signals", None) or []
    if emerging_signals:
        lines.append("*Emerging problems*")
        for item in emerging_signals[:3]:
            lines.append(
                f"• {item.title}. {item.trend_label} "
                f"(score {round(item.emerging_score * 100)}%, {item.signal_count} signals, "
                f"{item.customer_count} customers)"
            )
    else:
        lines.append("*Emerging problems*: none above threshold this week.")
    lines.append("")

    pending = [p for p in measurement_plans if p.get("status") == "pending"]
    manual = [p for p in measurement_plans if p.get("status") == "manual_required"]
    lines.append("*Open loops*")
    lines.append(
        f"• {len(pending)} measurement checkpoint(s) scheduled"
        + (f", next due {min(p['due_at'] for p in pending)}" if pending else "")
    )
    if manual:
        lines.append(f"• {len(manual)} measurement(s) need a human-recorded value")
    lines.append("")

    lines.append("*Outcomes*")
    lines.append(
        f"• {outcome_board.target_met} target met · {outcome_board.improving} improving · "
        f"{outcome_board.not_improved} not improved · {outcome_board.not_measured} not yet measured"
    )
    lines.append("")

    # The proof step: did the fix land? Read-time verdicts from the closing
    # checkpoints, plus the resolution timeline.
    loop_closed = getattr(outcome_board, "loop_closed", 0) or 0
    did_not_land = getattr(outcome_board, "fix_did_not_land", 0) or 0
    overdue = getattr(outcome_board, "overdue", 0) or 0
    lines.append("*Loop verdicts*")
    lines.append(
        f"• {loop_closed} loop(s) closed · {did_not_land} fix(es) did not land · "
        f"{overdue} problem(s) past their due date"
    )
    for item in [i for i in getattr(outcome_board, "items", []) if getattr(i, "loop_verdict", None) == "fix_did_not_land"][:3]:
        lines.append(f"  – {item.title} ({item.owner}): {item.metric} still at {item.latest_value} vs baseline {item.baseline}")

    return "\n".join(lines)
