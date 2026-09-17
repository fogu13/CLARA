"""The reviewed outbound content of an approved action.

One choke point builds what the destination connector receives from a problem
and an action, so that (a) the approval can freeze it (``OutboundContent`` on
the approval record, with a SHA-256), (b) dispatch can compare the current
content against the frozen one and refuse on drift, and (c) dispatch sends
the frozen content rather than whatever the problem says at retry time. The
disclosure line (Art. 50) and the deep link are added at dispatch: they are
not reviewed text, and the link depends on the deployment.
"""

from __future__ import annotations

import hashlib
import json
import os
from typing import Any

from app.domain.models import ActionProposal, OutboundContent, ProblemRecord

# Priority of the external record from the approved risk level.
RISK_PRIORITY = {"critical": 1, "high": 1, "medium": 2, "low": 3}

# Field order of the frozen content, used for the changed-field report.
OUTBOUND_FIELDS = (
    "title",
    "description",
    "priority",
    "problem_id",
    "insight_title",
    "insight_summary",
    "insight_severity",
    "insight_signal_ids",
)


def build_outbound_content(problem: ProblemRecord, action: ActionProposal) -> OutboundContent:
    """The reviewed content as the reviewer sees it at approval time."""
    return OutboundContent(
        title=f"{problem.title} [{action.class_.value}]",
        description=action.proposal,
        priority=RISK_PRIORITY.get(action.risk_level.value, 3),
        problem_id=problem.problem_id,
        insight_title=problem.title,
        insight_summary=problem.statement,
        insight_severity=problem.impact_band,
        insight_signal_ids=[
            evidence.signal_id for evidence in problem.evidence[:10] if evidence.signal_id
        ],
    )


def outbound_sha256(content: OutboundContent) -> str:
    """Canonical-JSON SHA-256 of the content (sorted keys, compact)."""
    canonical = json.dumps(
        content.model_dump(mode="json"), sort_keys=True, separators=(",", ":"), ensure_ascii=False
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def outbound_changes(frozen: OutboundContent, current: OutboundContent) -> list[str]:
    """Names of the content fields that differ between two snapshots."""
    return [name for name in OUTBOUND_FIELDS if getattr(frozen, name) != getattr(current, name)]


def apply_disclosure(description: str, template: str) -> str:
    """Append the Art. 50 AI-disclosure line to outbound text (final line)."""
    if not template:
        return description
    return f"{description}\n\n{template}" if description else template


def deep_link(problem_id: str) -> str:
    web_url = (os.getenv("CLARA_WEB_URL") or "").rstrip("/")
    return f"{web_url}/insights/{problem_id}" if web_url else ""


def outbound_payload(content: OutboundContent, *, disclosure: str | None = None) -> dict[str, Any]:
    """The dict shape connectors expect, from frozen (or freshly built) content.

    ``disclosure`` reaches every destination unchanged (Jira description,
    Slack message); the deep link is resolved here because it depends on the
    deployment, not on what was reviewed.
    """
    description = content.description
    if disclosure:
        description = apply_disclosure(description, disclosure)
    return {
        "title": content.title,
        "description": description,
        "priority": content.priority,
        "problem_id": content.problem_id,
        "clara_url": deep_link(content.problem_id),
        "insight_title": content.insight_title,
        "insight_summary": content.insight_summary,
        "insight_severity": content.insight_severity,
        "insight_signal_ids": list(content.insight_signal_ids),
    }
