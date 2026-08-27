"""Policy evaluation engine — the pulled-forward slice of the Phase 6 policy engine.

One evaluator answers "may this consequential call proceed?" for every
enforcement point: workflow approvals (assert_governance_allows_decision),
the triage graph's governance gate, and the /governance/policy/evaluate
endpoint. Callers describe the proposed call as a GovernedCall envelope and
receive a PolicyDecision naming the applicable rules, the findings, and an
allow / needs_review / block outcome.

Three matching paths, evaluated together:

1. Destination path — the destination (or, for governed action classes with
   an unmapped destination, the union of all mapped rules) selects required
   rule ids from the destination-policies seed; a required rule whose
   governance check is missing, failed, or review_required blocks. This
   reproduces the approval gate byte-for-byte (see workflow.py history).
2. Check path — when no destination policy applies, existing governance
   checks are read directly: a blocking failed check blocks; a blocking
   review_required check is advisory (needs_review), matching the historical
   behaviour where only blocking failures stopped an approval.
3. Category path — rules whose applies_to_categories overlap the call's
   data_categories fire on their own: blocking rules fail, advisory rules
   request review. This is what makes the triage governance gate rule-driven.

The before_call/after_call pair is the per-call interface any agentic or
external surface consults: before_call gates execution; after_call only
annotates (it never blocks retroactively — the call already happened).

The destination-policies seed is kept verbatim from the previously hardcoded
map even where it disagrees with the rules' own applies_to_destinations
metadata; reconciling the two changes enforcement behaviour and is a
deliberate, separate decision (docs/engineering/policy-engine-design.md).
"""

from __future__ import annotations

from enum import Enum
from functools import lru_cache
from typing import Any, Literal

from pydantic import BaseModel, Field

from app.domain.models import ActionClass, GovernanceCheck, PolicyRule, RiskLevel
from app.services.common import utc_now

ENGINE_VERSION = "policy-engine/1"

# Check statuses that leave a required rule unresolved on the destination path.
UNRESOLVED_CHECK_STATUSES = {"fail", "review_required"}

# Action classes gated even when their destination has no policy entry.
DEFAULT_GOVERNED_ACTION_CLASSES = frozenset(
    {"customer_recovery", "journey_intervention", "governance"}
)


class EvaluationSource(str, Enum):
    workflow_approval = "workflow_approval"
    triage_graph = "triage_graph"
    api = "api"
    mcp = "mcp"
    external_agent = "external_agent"


class ActorType(str, Enum):
    human = "human"
    system = "system"
    agent = "agent"


class GovernedCall(BaseModel):
    """Normalized envelope for one proposed consequential call or action."""

    source: EvaluationSource
    actor_type: ActorType = ActorType.human
    actor_id: str | None = None
    workspace_id: int | None = None
    action_class: ActionClass | None = None
    destination: str | None = None
    risk_level: RiskLevel | None = None
    tool_name: str | None = None
    data_categories: list[str] = Field(default_factory=list)
    consent_verified: bool | None = None
    evidence_confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    governance_checks: list[GovernanceCheck] = Field(default_factory=list)
    # Problem/action/insight identifier for the audit trail — never personal data.
    reference: str | None = None


class PolicyDecisionStatus(str, Enum):
    allow = "allow"
    needs_review = "needs_review"
    block = "block"


class RuleFinding(BaseModel):
    rule_id: str
    status: Literal["pass", "fail", "review_required", "missing_check"]
    blocking: bool
    reason: str


class PolicyDecision(BaseModel):
    decision: PolicyDecisionStatus
    applicable_rule_ids: list[str]
    blocking_rule_ids: list[str]
    findings: list[RuleFinding]
    reasons: list[str]
    source: EvaluationSource
    evaluated_at: str
    engine_version: str = ENGINE_VERSION


class PolicyEngine:
    def __init__(
        self,
        rules: list[PolicyRule],
        destination_policies: dict[str, set[str]] | None = None,
        governed_action_classes: frozenset[str] | set[str] | None = None,
    ) -> None:
        self._rules = {rule.rule_id: rule for rule in rules}
        self._destination_policies = {
            destination: set(rule_ids)
            for destination, rule_ids in (destination_policies or {}).items()
        }
        self._governed_action_classes = frozenset(
            governed_action_classes
            if governed_action_classes is not None
            else DEFAULT_GOVERNED_ACTION_CLASSES
        )

    def applicable_rule_ids(self, call: GovernedCall) -> set[str] | None:
        """Rule ids the destination path requires; None when it does not apply."""
        if call.destination is not None:
            mapped = self._destination_policies.get(call.destination.strip().lower())
            if mapped is not None:
                return set(mapped)
        if call.action_class is not None and call.action_class.value in self._governed_action_classes:
            return {
                rule_id
                for rule_ids in self._destination_policies.values()
                for rule_id in rule_ids
            }
        return None

    def evaluate(self, call: GovernedCall) -> PolicyDecision:
        findings: list[RuleFinding] = []
        applicable = self.applicable_rule_ids(call)

        if applicable is not None:
            checks_by_rule = {
                check.policy_rule_id or check.rule: check for check in call.governance_checks
            }
            for rule_id in sorted(applicable):
                check = checks_by_rule.get(rule_id)
                if check is None:
                    findings.append(
                        RuleFinding(
                            rule_id=rule_id,
                            status="missing_check",
                            blocking=True,
                            reason=f"No governance check recorded for required rule {rule_id}",
                        )
                    )
                elif check.status.value in UNRESOLVED_CHECK_STATUSES:
                    findings.append(
                        RuleFinding(
                            rule_id=rule_id,
                            status=check.status.value,
                            blocking=True,
                            reason=check.reason,
                        )
                    )
                else:
                    findings.append(
                        RuleFinding(
                            rule_id=rule_id, status="pass", blocking=False, reason=check.reason
                        )
                    )
        else:
            for check in call.governance_checks:
                status = check.status.value
                if status == "pass":
                    continue
                findings.append(
                    RuleFinding(
                        rule_id=check.policy_rule_id or check.rule,
                        status=status,  # "fail" or "review_required"
                        blocking=check.blocking and status == "fail",
                        reason=check.reason,
                    )
                )

        if call.data_categories:
            categories = set(call.data_categories)
            for rule in self._rules.values():
                if rule.status != "active" or not categories & set(rule.applies_to_categories):
                    continue
                findings.append(
                    RuleFinding(
                        rule_id=rule.rule_id,
                        status="fail" if rule.default_blocking else "review_required",
                        blocking=rule.default_blocking,
                        reason=rule.description,
                    )
                )

        blocking_rule_ids = sorted({f.rule_id for f in findings if f.blocking})
        if blocking_rule_ids:
            decision = PolicyDecisionStatus.block
        elif any(f.status in ("fail", "review_required") for f in findings):
            decision = PolicyDecisionStatus.needs_review
        else:
            decision = PolicyDecisionStatus.allow

        return PolicyDecision(
            decision=decision,
            applicable_rule_ids=(
                sorted(applicable)
                if applicable is not None
                else sorted({f.rule_id for f in findings})
            ),
            blocking_rule_ids=blocking_rule_ids,
            findings=findings,
            reasons=[f.reason for f in findings if f.status != "pass"],
            source=call.source,
            evaluated_at=utc_now(),
        )

    def before_call(self, call: GovernedCall) -> PolicyDecision:
        """Pre-execution gate: a `block` decision means the call must not run."""
        return self.evaluate(call)

    def after_call(self, call: GovernedCall, result: dict[str, Any] | None = None) -> PolicyDecision:
        """Post-execution annotation: never blocks retroactively.

        The call already happened, so the strongest outcome here is
        needs_review — either because the envelope would have been blocked
        (a gap upstream worth surfacing) or because the result reports a
        failure state.
        """
        decision = self.evaluate(call)
        updates: dict[str, Any] = {}
        if decision.decision == PolicyDecisionStatus.block:
            updates = {
                "decision": PolicyDecisionStatus.needs_review,
                "reasons": [
                    *decision.reasons,
                    "Post-call annotation: this call would have been blocked pre-execution",
                ],
            }
        result_status = str((result or {}).get("status", "")).lower()
        if result_status in {"failed", "error"} and not updates:
            if decision.decision == PolicyDecisionStatus.allow:
                updates = {
                    "decision": PolicyDecisionStatus.needs_review,
                    "reasons": [
                        *decision.reasons,
                        f"Call result reported status {result_status!r}",
                    ],
                }
        return decision.model_copy(update=updates) if updates else decision


def engine_from_rule_dicts(rules: list[dict[str, Any]]) -> PolicyEngine:
    """Build an engine from serialized rules (e.g. triage-graph state).

    Rules travel through checkpointable graph state as plain dicts; destination
    policies are deliberately absent — graph envelopes carry categories and
    checks, not destinations.
    """
    return PolicyEngine(rules=[PolicyRule.model_validate(rule) for rule in rules])


@lru_cache(maxsize=1)
def default_policy_engine() -> PolicyEngine:
    from app.services.seed import load_seed_destination_policies, load_seed_policy_rules

    return PolicyEngine(
        rules=load_seed_policy_rules(),
        destination_policies=load_seed_destination_policies(),
    )


def governance_checks_from_decision(
    decision: PolicyDecision, *, insight_id: str
) -> list[dict[str, Any]]:
    """Render non-pass findings in the triage graph's governance-check shape."""
    return [
        {
            "insight_id": insight_id,
            "rule_id": finding.rule_id,
            "status": "fail" if finding.status in ("fail", "missing_check") else finding.status,
            "blocking": finding.blocking,
            "message": finding.reason,
        }
        for finding in decision.findings
        if finding.status != "pass"
    ]
