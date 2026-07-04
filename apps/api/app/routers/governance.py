"""Governance routes: policy rules, feedback rules, GDPR export/erasure, audit export."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.domain.models import FeedbackRule, FeedbackRuleCreate, PolicyRule
from app.rbac import Role, require_role
from app.services.common import utc_now


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
