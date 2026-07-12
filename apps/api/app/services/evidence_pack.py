"""Evidence-pack export: the audit-ready story of one problem, end to end.

Signals -> classification -> proposed actions + policy trail -> human approvals
-> real executions (external refs) -> outcome contract + measurements -> learning.
Every line traces to a stored record; nothing is narrative-only.

Two renderings from one structured dict:
  - JSON (data-room / programmatic)
  - self-contained, print-optimized HTML (DACH buyers file PDFs: open -> Cmd+P)

ponytail: stdlib-only HTML rendering (html.escape + f-strings); no template
engine, no PDF library. Browser print-to-PDF covers the PDF need.
"""

from __future__ import annotations

import html
from typing import Any

from app.domain.models import ProblemRecord, WorkflowState
from app.services.common import utc_now
from app.services.workflow import approved_action_keys, is_human_reviewed


def _execution_entry(execution, approvals) -> dict[str, Any]:
    """Executions with the effective Art. 50(4) review status: pre-stamp rows
    are backfilled from their approval record (see workflow.is_human_reviewed),
    so a legacy human-approved push never renders as 'auto'."""
    reviewed = is_human_reviewed(execution, approved_action_keys(approvals))
    reviewed_by = execution.reviewed_by
    reviewed_at = execution.reviewed_at
    if reviewed and not execution.human_reviewed:
        approval = next(
            (
                record
                for record in approvals
                if record.action_id == execution.action_id
                and str(getattr(record.decision, "value", record.decision)) == "approved"
            ),
            None,
        )
        if approval is not None:
            reviewed_by = reviewed_by or approval.reviewer
            reviewed_at = reviewed_at or approval.created_at
    return {
        "execution_id": execution.execution_id,
        "action_id": execution.action_id,
        "destination": execution.destination,
        "status": execution.status.value,
        "external_ref": execution.external_ref,
        "detail": execution.detail,
        "created_at": execution.created_at,
        "human_reviewed": reviewed,
        "reviewed_by": reviewed_by,
        "reviewed_at": reviewed_at,
        "disclosure_applied": execution.disclosure_applied,
    }


def build_evidence_pack(
    problem: ProblemRecord,
    state: WorkflowState,
    measurement_plans: list[dict[str, Any]] | None = None,
    *,
    generated_at: str | None = None,
) -> dict[str, Any]:
    """Assemble the structured evidence pack from stored records only."""
    contract = problem.outcome_contract
    plans = [
        plan for plan in (measurement_plans or []) if plan.get("problem_id") == problem.problem_id
    ]

    return {
        "generated_at": generated_at or utc_now(),
        "problem": {
            "problem_id": problem.problem_id,
            "title": problem.title,
            "status": problem.status.value,
            "owner": problem.owner,
            "journey": problem.journey,
            "journey_stage": problem.journey_stage,
            "impact_score": problem.impact_score,
            "impact_band": problem.impact_band,
            "evidence_confidence": problem.evidence_confidence,
            "statement": problem.statement,
            "root_cause_hypothesis": problem.root_cause_hypothesis,
            "known_limitations": "; ".join(problem.known_limitations) or "None stated",
        },
        "affected_cohort": {
            "customers": problem.affected_cohort.customers,
            "accounts": problem.affected_cohort.accounts,
        },
        "evidence": [
            {
                "signal_id": item.signal_id,
                "source": item.source,
                "language": item.language,
                "customer_id": item.customer_id,
                "timestamp": item.timestamp,
                "excerpt": item.excerpt,
            }
            for item in problem.evidence
        ],
        "actions": [
            {
                "action_id": action.action_id,
                "class": action.class_.value,
                "destination": action.destination,
                "owner": action.owner,
                "risk_level": action.risk_level.value,
                "approval_state": action.approval_state,
                "proposal": action.proposal,
                "depends_on": action.depends_on,
            }
            for action in problem.action_proposals
        ],
        "governance_checks": [
            {
                "check_id": check.check_id,
                "rule": check.rule,
                "policy_rule_id": check.policy_rule_id,
                "status": check.status.value,
                "blocking": check.blocking,
                "reason": check.reason,
            }
            for check in problem.governance_checks
        ],
        "approvals": [
            {
                "decision_id": approval.decision_id,
                "action_id": approval.action_id,
                "decision": approval.decision.value,
                "reviewer": approval.reviewer,
                "note": approval.note,
                "created_at": approval.created_at,
            }
            for approval in state.approvals
        ],
        "executions": [
            _execution_entry(execution, state.approvals)
            for execution in state.executions
        ],
        "outcome": {
            "metric": contract.primary_metric,
            "baseline": contract.baseline,
            "success_threshold": contract.success_threshold,
            "measurement_window_days": contract.measurement_window_days,
            "comparison_method": contract.comparison_method,
            "latest_value": state.outcome.latest_value,
            "status": state.outcome.status,
            "improvement_direction": state.outcome.improvement_direction,
        },
        "measurement_checkpoints": [
            {
                "kind": plan.get("kind"),
                "due_at": plan.get("due_at"),
                "status": plan.get("status"),
                "note": plan.get("note"),
            }
            for plan in plans
        ],
        "learning_conclusions": [
            {
                "learning_status": learning.learning_status.value,
                "summary": learning.summary,
                "limitations": learning.limitations,
                "reviewed_at": learning.reviewed_at,
            }
            for learning in state.learning_conclusions
        ],
        "closure_records": [
            {
                "operational_status": closure.operational_status,
                "customer_status": closure.customer_status,
                "unresolved_customers": closure.unresolved_customers,
                "created_at": closure.created_at,
            }
            for closure in state.closure_records
        ],
    }


def _esc(value: Any) -> str:
    return html.escape("" if value is None else str(value))


def _row(cells: list[Any]) -> str:
    return "<tr>" + "".join(f"<td>{_esc(cell)}</td>" for cell in cells) + "</tr>"


def _table(headers: list[str], rows: list[list[Any]], empty: str) -> str:
    if not rows:
        return f"<p class='empty'>{_esc(empty)}</p>"
    head = "".join(f"<th>{_esc(h)}</th>" for h in headers)
    body = "".join(_row(row) for row in rows)
    return f"<table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>"


def render_evidence_pack_html(pack: dict[str, Any]) -> str:
    """Self-contained, print-optimized HTML rendering of the pack."""
    problem = pack["problem"]
    outcome = pack["outcome"]

    evidence_rows = [
        [e["signal_id"], e["source"], e["language"], e["customer_id"], e["timestamp"], e["excerpt"]]
        for e in pack["evidence"]
    ]
    action_rows = [
        [a["action_id"], a["class"], a["destination"], a["risk_level"], a["approval_state"], a["proposal"]]
        for a in pack["actions"]
    ]
    check_rows = [
        [c["rule"], c["status"], "blocking" if c["blocking"] else "advisory", c["reason"]]
        for c in pack["governance_checks"]
    ]
    approval_rows = [
        [a["decision_id"], a["action_id"], a["decision"], a["reviewer"], a["created_at"], a["note"]]
        for a in pack["approvals"]
    ]
    execution_rows = [
        [
            x["execution_id"],
            x["destination"],
            x["status"],
            # Art. 50(4) editorial-review stamp vs disclosed auto-publication.
            f"human ({x['reviewed_by']})" if x["human_reviewed"]
            else ("auto, AI-disclosed" if x["disclosure_applied"] else "auto"),
            x["external_ref"],
            x["detail"],
            x["created_at"],
        ]
        for x in pack["executions"]
    ]
    checkpoint_rows = [
        [m["kind"], m["due_at"], m["status"], m["note"]] for m in pack["measurement_checkpoints"]
    ]
    learning_rows = [
        [l["learning_status"], l["summary"], l["limitations"], l["reviewed_at"]]
        for l in pack["learning_conclusions"]
    ]

    outcome_line = (
        f"{_esc(outcome['metric'])}: baseline {_esc(outcome['baseline'])} → "
        f"latest {_esc(outcome['latest_value'] if outcome['latest_value'] is not None else 'not measured')} "
        f"(target {_esc(outcome['success_threshold'])}, {_esc(outcome['improvement_direction'])}). "
        f"status: {_esc(outcome['status'])}"
    )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Evidence Pack: {_esc(problem['problem_id'])}</title>
<style>
  body {{ font: 13px/1.5 -apple-system, 'Segoe UI', sans-serif; color: #111; margin: 40px auto; max-width: 900px; padding: 0 24px; }}
  h1 {{ font-size: 20px; margin-bottom: 2px; }}
  h2 {{ font-size: 14px; text-transform: uppercase; letter-spacing: .06em; border-bottom: 1px solid #ddd; padding-bottom: 4px; margin-top: 28px; }}
  .meta {{ color: #555; font-size: 12px; }}
  .badge {{ display: inline-block; border: 1px solid #bbb; border-radius: 10px; padding: 1px 8px; font-size: 11px; margin-right: 6px; }}
  table {{ width: 100%; border-collapse: collapse; margin-top: 8px; font-size: 12px; }}
  th, td {{ text-align: left; padding: 5px 8px; border-bottom: 1px solid #eee; vertical-align: top; }}
  th {{ background: #f7f7f7; font-weight: 600; }}
  .empty {{ color: #777; font-style: italic; }}
  .outcome {{ background: #f4faf7; border: 1px solid #cfe8dc; border-radius: 6px; padding: 10px 14px; margin-top: 8px; }}
  footer {{ margin-top: 36px; color: #777; font-size: 11px; border-top: 1px solid #ddd; padding-top: 8px; }}
  @media print {{ body {{ margin: 0; }} h2 {{ page-break-after: avoid; }} table {{ page-break-inside: auto; }} }}
</style>
</head>
<body>
<h1>Evidence Pack: {_esc(problem['title'])}</h1>
<p class="meta">
  {_esc(problem['problem_id'])} · generated {_esc(pack['generated_at'])} ·
  <span class="badge">status: {_esc(problem['status'])}</span>
  <span class="badge">impact: {_esc(problem['impact_band'])} ({_esc(problem['impact_score'])})</span>
  <span class="badge">owner: {_esc(problem['owner'])}</span>
  <span class="badge">journey: {_esc(problem['journey'])} / {_esc(problem['journey_stage'])}</span>
  <span class="badge">evidence confidence: {_esc(problem['evidence_confidence'])}</span>
</p>

<h2>Problem</h2>
<p>{_esc(problem['statement'])}</p>
<p><strong>Root-cause hypothesis:</strong> {_esc(problem['root_cause_hypothesis'])}</p>
<p><strong>Known limitations:</strong> {_esc(problem['known_limitations'])}</p>
<p><strong>Affected cohort:</strong> {_esc(pack['affected_cohort']['customers'])} customers,
   {_esc(pack['affected_cohort']['accounts'])} accounts</p>

<h2>Evidence ({len(evidence_rows)})</h2>
{_table(['Signal', 'Source', 'Lang', 'Customer', 'Timestamp', 'Excerpt'], evidence_rows, 'No evidence excerpts stored.')}

<h2>Proposed actions</h2>
{_table(['Action', 'Class', 'Destination', 'Risk', 'Approval state', 'Proposal'], action_rows, 'No action proposals.')}

<h2>Governance &amp; policy checks</h2>
{_table(['Rule', 'Status', 'Type', 'Reason'], check_rows, 'No governance checks recorded.')}

<h2>Human approvals</h2>
{_table(['Decision', 'Action', 'Outcome', 'Reviewer', 'At', 'Note'], approval_rows, 'No approval decisions yet.')}

<h2>Executions</h2>
{_table(['Execution', 'Destination', 'Status', 'Review (Art. 50)', 'External ref', 'Detail', 'At'], execution_rows, 'No executions yet.')}

<h2>Outcome contract &amp; measurement</h2>
<div class="outcome">{outcome_line}<br>
<span class="meta">window: {_esc(outcome['measurement_window_days'])} days · method: {_esc(outcome['comparison_method'])}</span></div>
{_table(['Checkpoint', 'Due', 'Status', 'Note'], checkpoint_rows, 'No measurement checkpoints scheduled.')}

<h2>Learning conclusions</h2>
{_table(['Status', 'Summary', 'Limitations', 'Reviewed'], learning_rows, 'No reviewed learning yet.')}

<footer>
Generated by CLARA. Every entry above traces to a stored, auditable record
(approvals, executions, policy checks, measurements). Auto-measured outcomes are
computed from real signal data; simulated data never appears in evidence packs.
</footer>
</body>
</html>"""
