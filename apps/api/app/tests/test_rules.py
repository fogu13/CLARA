from fastapi.testclient import TestClient

from app.main import create_app
from app.services.problems import ProblemStore
from app.services.rules import SQLiteRuleStore
from app.services.seed import load_seed_problems
from app.services.signals import SignalStore
from app.services.workflow import WorkflowStore


def make_client(tmp_path) -> TestClient:
    return TestClient(
        create_app(
            problem_store=ProblemStore(load_seed_problems()),
            workflows=WorkflowStore(),
            signals=SignalStore(),
            feedback_rules=SQLiteRuleStore(tmp_path / "rules.db"),
        )
    )


def test_rules_crud(tmp_path) -> None:
    client = make_client(tmp_path)

    assert client.get("/rules").json() == []

    created = client.post(
        "/rules",
        json={
            "name": "Churn risk -> Slack",
            "conditions": [{"field": "category", "operator": "equals", "value": "churn_risk"}],
            "actions": [{"type": "notify", "target": "#alerts"}],
            "priority": 5,
            "is_active": True,
        },
    )
    assert created.status_code == 200
    rule = created.json()
    assert rule["name"] == "Churn risk -> Slack"
    assert rule["rule_id"].startswith("RULE-")
    rule_id = rule["rule_id"]

    listed = client.get("/rules").json()
    assert len(listed) == 1
    assert listed[0]["rule_id"] == rule_id

    assert client.delete(f"/rules/{rule_id}").status_code == 200
    assert client.get("/rules").json() == []
    assert client.delete(f"/rules/{rule_id}").status_code == 404


def test_rules_sorted_by_priority(tmp_path) -> None:
    client = make_client(tmp_path)
    client.post("/rules", json={"name": "low", "priority": 1})
    client.post("/rules", json={"name": "high", "priority": 9})

    names = [rule["name"] for rule in client.get("/rules").json()]
    assert names == ["high", "low"]
