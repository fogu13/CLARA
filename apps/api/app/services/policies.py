from __future__ import annotations

from app.domain.models import PolicyRule


class PolicyRuleStore:
    def __init__(self, policy_rules: list[PolicyRule]) -> None:
        self._policy_rules = {rule.rule_id: rule for rule in policy_rules}

    def list_rules(self) -> list[PolicyRule]:
        return sorted(
            self._policy_rules.values(),
            key=lambda rule: (rule.category, rule.severity.value, rule.rule_id),
        )

    def get_rule(self, rule_id: str) -> PolicyRule | None:
        return self._policy_rules.get(rule_id)
