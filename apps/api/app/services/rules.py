from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from uuid import uuid4

from app.domain.models import FeedbackRule, FeedbackRuleCreate


class SQLiteRuleStore:
    """Automation rules (conditions -> actions) for the triage/routing engine."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._connection = sqlite3.connect(self.path, check_same_thread=False)
        self._connection.row_factory = sqlite3.Row
        self._connection.execute(
            """
            CREATE TABLE IF NOT EXISTS feedback_rules (
                rule_id TEXT PRIMARY KEY,
                payload TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
            """
        )
        self._connection.commit()

    def list_rules(self) -> list[FeedbackRule]:
        rows = self._connection.execute(
            "SELECT payload FROM feedback_rules ORDER BY created_at DESC"
        ).fetchall()
        rules = [FeedbackRule.model_validate(json.loads(row["payload"])) for row in rows]
        return sorted(rules, key=lambda rule: rule.priority, reverse=True)

    def create_rule(self, create: FeedbackRuleCreate) -> FeedbackRule:
        rule = FeedbackRule(rule_id=f"RULE-{uuid4().hex[:8]}", **create.model_dump())
        self._connection.execute(
            "INSERT INTO feedback_rules (rule_id, payload) VALUES (?, ?)",
            (rule.rule_id, json.dumps(rule.model_dump())),
        )
        self._connection.commit()
        return rule

    def delete_rule(self, rule_id: str) -> bool:
        cursor = self._connection.execute(
            "DELETE FROM feedback_rules WHERE rule_id = ?", (rule_id,)
        )
        self._connection.commit()
        return cursor.rowcount > 0
