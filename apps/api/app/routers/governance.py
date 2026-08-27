"""Governance routes: policy rules, feedback rules, GDPR export/erasure, audit export."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.domain.models import FeedbackRule, FeedbackRuleCreate, PolicyRule
from app.rate_limit import rate_limiter
from app.rbac import Role, require_role
from app.services.common import utc_now
from app.services.policy_engine import GovernedCall, PolicyDecision, PolicyEngine
from app.services.seed import load_seed_destination_policies
from app.services.workflow import (
    PUBLISHED_STATUSES,
    _status_value,
    approved_action_keys,
    is_human_reviewed,
)


def build_router(
    *,
    policy_store,
    rule_store,
    signal_store,
    journey_event_store,
    context_store,
    active_problem_store,
    workflow_store,
    telemetry_store,
) -> APIRouter:
    router = APIRouter()
    read_dep = Depends(require_role(Role.viewer))

    @router.get("/policy-rules", response_model=list[PolicyRule], dependencies=[read_dep])
    def list_policy_rules() -> list[PolicyRule]:
        return policy_store.list_rules()

    @router.get("/policy-rules/{rule_id}", response_model=PolicyRule, dependencies=[read_dep])
    def get_policy_rule(rule_id: str) -> PolicyRule:
        policy_rule = policy_store.get_rule(rule_id)
        if policy_rule is None:
            raise HTTPException(status_code=404, detail="Policy rule not found")

        return policy_rule

    # One engine per app over the workspace's policy rules; the destination map
    # is seed data (see docs/engineering/policy-engine-design.md).
    policy_engine = PolicyEngine(
        rules=policy_store.list_rules(),
        destination_policies=load_seed_destination_policies(),
    )

    @router.post(
        "/policy/evaluate",
        response_model=PolicyDecision,
        dependencies=[Depends(require_role(Role.editor)), Depends(rate_limiter)],
    )
    def evaluate_policy(call: GovernedCall) -> PolicyDecision:
        """Side-effect-free policy evaluation for one proposed consequential call.

        The per-call decision seam: any surface preparing a consequential call
        (a future agentic client, an MCP consumer, an integration) can ask
        "would this be allowed?" before acting. Evaluates only the envelope the
        caller supplies against workspace-global rules — it reads no signals,
        problems, or customer data — and records an audit event with rule ids
        only. It never executes or approves anything.
        """
        decision = policy_engine.evaluate(call)
        telemetry_store.record(
            "policy_decision",
            entity_id=call.reference,
            metadata={
                "source": call.source.value,
                "decision": decision.decision.value,
                "applicable_rule_ids": decision.applicable_rule_ids,
                "blocking_rule_ids": decision.blocking_rule_ids,
                "reference": call.reference,
                "actor_type": call.actor_type.value,
            },
        )
        return decision

    @router.get("/customers/{customer_id}/data-export", dependencies=[Depends(require_role(Role.admin))])
    def export_customer_data(customer_id: str) -> dict:
        """GDPR Art. 20 (portability): everything CLARA holds about one customer."""
        signals = [
            s.model_dump(mode="json") for s in signal_store.list_signals()
            if s.customer_id == customer_id
        ]
        events = [
            e.model_dump(mode="json") for e in journey_event_store.list_events()
            if e.customer_id == customer_id
        ]
        context = [
            c.model_dump(mode="json") for c in context_store.list_context()
            if c.customer_id == customer_id
        ]
        evidence_appearances = [
            {"problem_id": p.problem_id, "excerpt": ev.excerpt, "timestamp": ev.timestamp}
            for p in active_problem_store.list_problems()
            for ev in p.evidence
            if ev.customer_id == customer_id
        ]
        telemetry_store.record(
            "gdpr_export",
            metadata={
                "signals": len(signals),
                "journey_events": len(events),
                "context_records": len(context),
                "evidence_appearances": len(evidence_appearances),
            },
        )
        return {
            "customer_id": customer_id,
            "exported_at": utc_now(),
            "signals": signals,
            "journey_events": events,
            "customer_context": context,
            "problem_evidence_appearances": evidence_appearances,
        }

    @router.delete("/customers/{customer_id}/data", dependencies=[Depends(require_role(Role.admin))])
    def erase_customer_data(customer_id: str) -> dict:
        """GDPR Art. 17 (erasure): delete/scrub a customer across every store.

        Signals, journey events and the context record are deleted; evidence
        excerpts inside draft problems are scrubbed (entry kept, content erased,
        so aggregate counts stay honest). The telemetry event deliberately does
        NOT retain the erased identifier.
        """
        # All-or-nothing: a silent PARTIAL erasure would be a compliance failure.
        # Postgres stores gain these methods in the DB-connected workstream.
        erasers = {
            "signals": getattr(signal_store, "delete_by_customer", None),
            "journey_events": getattr(journey_event_store, "delete_by_customer", None),
            "context_records": getattr(context_store, "delete_by_customer", None),
            "problems_scrubbed": getattr(active_problem_store, "scrub_customer", None),
            "jira_drafts_scrubbed": getattr(workflow_store, "scrub_customer_references", None),
        }
        missing = [name for name, fn in erasers.items() if fn is None]
        if missing:
            raise HTTPException(
                status_code=501,
                detail=f"Erasure not supported by this deployment backend yet for: {', '.join(missing)}",
            )
        deleted = {name: fn(customer_id) for name, fn in erasers.items()}
        telemetry_store.record("gdpr_erasure", metadata=deleted)  # no customer id retained
        return {
            "erased": deleted,
            "note": (
                "Signals, journey events and context deleted; draft-problem evidence "
                "scrubbed in place. Seed/demo problems contain synthetic data only."
            ),
        }

    @router.get("/article50-status", dependencies=[read_dep])
    def article50_status() -> dict:
        """EU AI Act Art. 50 transparency aggregate: which PUBLISHED outbound
        executions were human-reviewed (Art. 50(4) exempt) vs auto-published
        (disclosed). Aggregates only, so viewer role is enough.

        Review status is derived, not just read from the stamp: executions are
        only ever created by record_approval on an approved decision, so pre-W2
        rows without the human_reviewed column are backfilled at read time from
        their approval record — otherwise every legacy human-approved push
        would be reported as an undisclosed AI auto-publication. Drafts and
        failed pushes never left the system and are excluded from both buckets.
        """
        executions = workflow_store.list_executions()
        approved = approved_action_keys(workflow_store.list_approvals())
        published = [e for e in executions if _status_value(e.status) in PUBLISHED_STATUSES]
        reviewed = [e for e in published if is_human_reviewed(e, approved)]
        auto_published = [e for e in published if not is_human_reviewed(e, approved)]
        by_destination: dict[str, dict[str, int]] = {}
        for execution in published:
            row = by_destination.setdefault(
                execution.destination, {"human_reviewed": 0, "disclosed": 0}
            )
            if is_human_reviewed(execution, approved):
                row["human_reviewed"] += 1
            if execution.disclosure_applied:
                row["disclosed"] += 1
        return {
            "human_reviewed": {
                "count": len(reviewed),
                "latest_at": max((e.created_at for e in reviewed), default=None),
            },
            "auto_published": {
                "count": len(auto_published),
                "disclosed_count": sum(1 for e in auto_published if e.disclosure_applied),
                "latest_at": max((e.created_at for e in auto_published), default=None),
            },
            "unpublished_count": len(executions) - len(published),
            "by_destination": [
                {"destination": destination, **counts}
                for destination, counts in sorted(by_destination.items())
            ],
            "generated_at": utc_now(),
        }

    @router.get("/audit-export", dependencies=[Depends(require_role(Role.admin))])
    def export_audit_log() -> dict:
        return {
            "approvals": [
                record.model_dump(mode="json", by_alias=True) for record in workflow_store.list_approvals()
            ],
            "executions": [record.model_dump(mode="json", by_alias=True) for record in workflow_store.list_executions()],
            "closure_records": [
                record.model_dump(mode="json", by_alias=True) for record in workflow_store.list_closure_records()
            ],
            "jira_issue_drafts": [
                record.model_dump(mode="json", by_alias=True) for record in workflow_store.list_jira_issue_drafts()
            ],
        }

    @router.get("/rules", response_model=list[FeedbackRule], dependencies=[read_dep])
    def list_rules() -> list[FeedbackRule]:
        return rule_store.list_rules()

    @router.post(
        "/rules",
        response_model=FeedbackRule,
        dependencies=[Depends(require_role(Role.editor))],
    )
    def create_rule(rule: FeedbackRuleCreate) -> FeedbackRule:
        return rule_store.create_rule(rule)

    @router.delete("/rules/{rule_id}", dependencies=[Depends(require_role(Role.editor))])
    def delete_rule(rule_id: str) -> dict:
        if not rule_store.delete_rule(rule_id):
            raise HTTPException(status_code=404, detail="Rule not found")
        return {"rule_id": rule_id, "status": "deleted"}

    return router
