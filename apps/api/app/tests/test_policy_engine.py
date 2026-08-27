"""Unit tests for the policy evaluation engine.

The parity cases mirror the approval-gate behaviour the workflow API tests pin
end-to-end (test_workflow_api.py): the engine must reproduce the historical
assert_governance_allows_decision semantics exactly.
"""

from app.domain.models import ActionClass, GovernanceCheck, PolicyRule
from app.services.policy_engine import (
    ActorType,
    EvaluationSource,
    GovernedCall,
    PolicyDecisionStatus,
    PolicyEngine,
    default_policy_engine,
    engine_from_rule_dicts,
    governance_checks_from_decision,
)
from app.services.seed import (
    load_seed_destination_policies,
    load_seed_policy_rules,
    load_seed_problems,
)


def make_engine() -> PolicyEngine:
    return PolicyEngine(
        rules=load_seed_policy_rules(),
        destination_policies=load_seed_destination_policies(),
    )


def problem_call(problem_id: str, action_id: str) -> GovernedCall:
    problem = next(p for p in load_seed_problems() if p.problem_id == problem_id)
    action = next(a for a in problem.action_proposals if a.action_id == action_id)
    return GovernedCall(
        source=EvaluationSource.workflow_approval,
        action_class=action.class_,
        destination=action.destination,
        risk_level=action.risk_level,
        governance_checks=problem.governance_checks,
        reference=f"{problem_id}/{action_id}",
    )


def check(rule_id: str, status: str, blocking: bool) -> GovernanceCheck:
    return GovernanceCheck(
        check_id=f"GOV-TEST-{rule_id}",
        rule=rule_id,
        policy_rule_id=rule_id,
        status=status,
        reason=f"test check for {rule_id}",
        blocking=blocking,
    )


class TestWorkflowParity:
    """The seed scenarios the approval API tests pin, evaluated directly."""

    def test_unmapped_destination_without_blocking_failure_allows(self) -> None:
        # PRB-108/ACT-501 (jira, structural): approvable today.
        decision = make_engine().evaluate(problem_call("PRB-108", "ACT-501"))

        assert decision.decision != PolicyDecisionStatus.block
        assert decision.blocking_rule_ids == []

    def test_missing_required_check_blocks_mapped_destination(self) -> None:
        # PRB-108/ACT-502 (zendesk): consent-review check is missing -> 409 today.
        decision = make_engine().evaluate(problem_call("PRB-108", "ACT-502"))

        assert decision.decision == PolicyDecisionStatus.block
        assert "customer_contact_requires_consent_review" in decision.blocking_rule_ids

    def test_failed_required_check_blocks_mapped_destination(self) -> None:
        # PRB-109/ACT-510 (hubspot): failed valid-consent check -> 409 today.
        decision = make_engine().evaluate(problem_call("PRB-109", "ACT-510"))

        assert decision.decision == PolicyDecisionStatus.block
        assert "customer_contact_requires_valid_consent" in decision.blocking_rule_ids

    def test_review_required_check_blocks_mapped_destination(self) -> None:
        engine = make_engine()
        call = GovernedCall(
            source=EvaluationSource.workflow_approval,
            destination="zendesk",
            governance_checks=[
                check("customer_contact_requires_consent_review", "review_required", True),
                check("customer_contact_requires_valid_consent", "pass", True),
                check("sensitive_attribute_inference_prohibited", "pass", True),
            ],
        )

        assert engine.evaluate(call).decision == PolicyDecisionStatus.block

    def test_mapped_destination_with_all_checks_passing_allows(self) -> None:
        engine = make_engine()
        call = GovernedCall(
            source=EvaluationSource.workflow_approval,
            destination="zendesk",
            governance_checks=[
                check("customer_contact_requires_consent_review", "pass", True),
                check("customer_contact_requires_valid_consent", "pass", True),
                check("sensitive_attribute_inference_prohibited", "pass", True),
            ],
        )

        decision = engine.evaluate(call)

        assert decision.decision == PolicyDecisionStatus.allow
        assert decision.reasons == []

    def test_governed_action_class_falls_back_to_union_of_all_rules(self) -> None:
        engine = make_engine()
        call = GovernedCall(
            source=EvaluationSource.workflow_approval,
            action_class=ActionClass.customer_recovery,
            destination="unmapped_destination",
            governance_checks=[],
        )

        decision = engine.evaluate(call)
        all_mapped = {
            rule_id
            for rule_ids in load_seed_destination_policies().values()
            for rule_id in rule_ids
        }

        assert decision.decision == PolicyDecisionStatus.block
        assert set(decision.applicable_rule_ids) == all_mapped

    def test_ungoverned_class_on_unmapped_destination_reads_checks_directly(self) -> None:
        engine = make_engine()
        blocking_fail = GovernedCall(
            source=EvaluationSource.workflow_approval,
            action_class=ActionClass.structural,
            destination="jira",
            governance_checks=[check("some_rule", "fail", True)],
        )
        advisory_review = GovernedCall(
            source=EvaluationSource.workflow_approval,
            action_class=ActionClass.structural,
            destination="jira",
            governance_checks=[check("some_rule", "review_required", True)],
        )
        non_blocking_fail = GovernedCall(
            source=EvaluationSource.workflow_approval,
            action_class=ActionClass.structural,
            destination="jira",
            governance_checks=[check("some_rule", "fail", False)],
        )

        assert engine.evaluate(blocking_fail).decision == PolicyDecisionStatus.block
        # Historically neither of these stopped an approval; they surface as advisory.
        assert engine.evaluate(advisory_review).decision == PolicyDecisionStatus.needs_review
        assert engine.evaluate(non_blocking_fail).decision == PolicyDecisionStatus.needs_review

    def test_legacy_check_keyed_by_rule_field_still_matches(self) -> None:
        engine = make_engine()
        legacy = GovernanceCheck(
            check_id="GOV-LEGACY",
            rule="customer_contact_requires_consent_review",
            policy_rule_id=None,
            status="pass",
            reason="legacy check without policy_rule_id",
            blocking=True,
        )
        call = GovernedCall(
            source=EvaluationSource.workflow_approval,
            destination="zendesk",
            governance_checks=[
                legacy,
                check("customer_contact_requires_valid_consent", "pass", True),
                check("sensitive_attribute_inference_prohibited", "pass", True),
            ],
        )

        assert engine.evaluate(call).decision == PolicyDecisionStatus.allow

    def test_destination_is_normalized_before_lookup(self) -> None:
        engine = make_engine()
        call = GovernedCall(
            source=EvaluationSource.workflow_approval,
            destination="  Zendesk  ",
            governance_checks=[],
        )

        decision = engine.evaluate(call)

        assert decision.decision == PolicyDecisionStatus.block
        assert set(decision.applicable_rule_ids) == load_seed_destination_policies()["zendesk"]


class TestCategoryPath:
    def test_blocking_category_rule_fires(self) -> None:
        decision = make_engine().evaluate(
            GovernedCall(
                source=EvaluationSource.triage_graph,
                actor_type=ActorType.system,
                data_categories=["compliance_concern"],
            )
        )

        assert decision.decision == PolicyDecisionStatus.block
        assert decision.blocking_rule_ids == ["compliance_concern_requires_review"]

    def test_unmatched_category_allows(self) -> None:
        decision = make_engine().evaluate(
            GovernedCall(
                source=EvaluationSource.triage_graph,
                actor_type=ActorType.system,
                data_categories=["usability"],
            )
        )

        assert decision.decision == PolicyDecisionStatus.allow
        assert decision.findings == []

    def test_advisory_category_rule_requests_review(self) -> None:
        rules = load_seed_policy_rules() + [
            PolicyRule(
                rule_id="advisory_category_rule",
                title="Advisory category rule",
                description="Advisory only.",
                category="test",
                severity="low",
                applies_to_categories=["billing"],
                default_blocking=False,
                owner="test",
                version="test",
            )
        ]
        engine = PolicyEngine(rules=rules)

        decision = engine.evaluate(
            GovernedCall(source=EvaluationSource.api, data_categories=["billing"])
        )

        assert decision.decision == PolicyDecisionStatus.needs_review

    def test_inactive_rule_never_fires(self) -> None:
        rules = [
            PolicyRule(
                rule_id="retired_rule",
                title="Retired",
                description="Retired rule.",
                category="test",
                severity="high",
                applies_to_categories=["compliance_concern"],
                default_blocking=True,
                owner="test",
                version="test",
                status="retired",
            )
        ]
        engine = PolicyEngine(rules=rules)

        decision = engine.evaluate(
            GovernedCall(source=EvaluationSource.api, data_categories=["compliance_concern"])
        )

        assert decision.decision == PolicyDecisionStatus.allow


class TestCallHooks:
    def test_before_call_matches_evaluate(self) -> None:
        engine = make_engine()
        call = problem_call("PRB-108", "ACT-502")

        assert engine.before_call(call).decision == engine.evaluate(call).decision

    def test_after_call_never_blocks_retroactively(self) -> None:
        engine = make_engine()
        call = problem_call("PRB-108", "ACT-502")  # would block pre-execution

        decision = engine.after_call(call, {"status": "pushed"})

        assert decision.decision == PolicyDecisionStatus.needs_review
        assert any("would have been blocked" in reason for reason in decision.reasons)

    def test_after_call_flags_failed_results(self) -> None:
        engine = make_engine()
        call = GovernedCall(source=EvaluationSource.external_agent, tool_name="list_problems")

        assert engine.after_call(call, {"status": "ok"}).decision == PolicyDecisionStatus.allow
        flagged = engine.after_call(call, {"status": "failed"})
        assert flagged.decision == PolicyDecisionStatus.needs_review


class TestHelpers:
    def test_engine_from_rule_dicts(self) -> None:
        rules = [rule.model_dump(mode="json") for rule in load_seed_policy_rules()]
        engine = engine_from_rule_dicts(rules)

        decision = engine.evaluate(
            GovernedCall(
                source=EvaluationSource.triage_graph,
                data_categories=["compliance_concern"],
            )
        )

        assert decision.decision == PolicyDecisionStatus.block

    def test_default_policy_engine_is_cached(self) -> None:
        assert default_policy_engine() is default_policy_engine()

    def test_governance_checks_from_decision_renders_non_pass_findings(self) -> None:
        decision = make_engine().evaluate(
            GovernedCall(
                source=EvaluationSource.triage_graph,
                data_categories=["compliance_concern"],
            )
        )

        checks = governance_checks_from_decision(decision, insight_id="Insight title")

        assert checks == [
            {
                "insight_id": "Insight title",
                "rule_id": "compliance_concern_requires_review",
                "status": "fail",
                "blocking": True,
                "message": checks[0]["message"],
            }
        ]

    def test_governance_checks_from_decision_skips_pass_findings(self) -> None:
        engine = make_engine()
        call = GovernedCall(
            source=EvaluationSource.workflow_approval,
            destination="zendesk",
            governance_checks=[
                check("customer_contact_requires_consent_review", "pass", True),
                check("customer_contact_requires_valid_consent", "pass", True),
                check("sensitive_attribute_inference_prohibited", "pass", True),
            ],
        )

        assert governance_checks_from_decision(engine.evaluate(call), insight_id="x") == []
