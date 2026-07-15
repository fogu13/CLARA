from __future__ import annotations

import json
import os
from pathlib import Path

from app.domain.models import (
    CustomerContextRecord,
    DemoDataset,
    DemoDatasetSummary,
    PolicyRule,
    ProblemRecord,
    SignalRecord,
)
from app.domain.scoring import approval_pressure, impact_band, normalized_impact_score

def _find_repo_root() -> Path:
    """Resolve the repo root both on dev machines (monorepo layout) and in containers.

    Priority: explicit CLARA_REPO_ROOT env var > monorepo parents[4] > container /app.
    """
    env_root = os.getenv("CLARA_REPO_ROOT")
    if env_root:
        return Path(env_root)
    try:
        return Path(__file__).resolve().parents[4]
    except IndexError:
        return Path("/app")


REPO_ROOT = _find_repo_root()
PROBLEMS_PATH = REPO_ROOT / "data" / "sample_problems.json"
SIGNALS_PATH = REPO_ROOT / "data" / "sample_signals.json"
CUSTOMER_CONTEXT_PATH = REPO_ROOT / "data" / "sample_customer_context.json"
POLICY_RULES_PATH = REPO_ROOT / "data" / "sample_policy_rules.json"
DEMO_DATASETS_PATH = REPO_ROOT / "data" / "demo_datasets"


def load_seed_problems(path: Path = PROBLEMS_PATH) -> list[ProblemRecord]:
    raw_records = json.loads(path.read_text(encoding="utf-8"))
    problems: list[ProblemRecord] = []

    for record in raw_records:
        governance_failures = sum(
            1
            for check in record.get("governance_checks", [])
            if check.get("blocking") and check.get("status") == "fail"
        )
        for check in record.get("governance_checks", []):
            check.setdefault("policy_rule_id", check.get("rule"))

        score = normalized_impact_score(record["impact_factors"])
        record["impact_score"] = score
        record["impact_band"] = impact_band(score)
        record["approval_pressure"] = approval_pressure(record["status"], governance_failures)
        problems.append(ProblemRecord.model_validate(record))

    return problems


def load_seed_signals(path: Path = SIGNALS_PATH) -> list[SignalRecord]:
    raw_records = json.loads(path.read_text(encoding="utf-8"))
    return [SignalRecord.model_validate(record) for record in raw_records]


def load_seed_customer_context(
    path: Path = CUSTOMER_CONTEXT_PATH,
) -> list[CustomerContextRecord]:
    raw_records = json.loads(path.read_text(encoding="utf-8"))
    return [CustomerContextRecord.model_validate(record) for record in raw_records]


def load_seed_policy_rules(path: Path = POLICY_RULES_PATH) -> list[PolicyRule]:
    raw_records = json.loads(path.read_text(encoding="utf-8"))
    return [PolicyRule.model_validate(record) for record in raw_records]


def load_demo_datasets(path: Path = DEMO_DATASETS_PATH) -> list[DemoDataset]:
    datasets: list[DemoDataset] = []
    for dataset_path in sorted(path.glob("*.json")):
        datasets.append(DemoDataset.model_validate_json(dataset_path.read_text(encoding="utf-8")))

    return datasets


def to_demo_dataset_summary(dataset: DemoDataset) -> DemoDatasetSummary:
    return DemoDatasetSummary(
        dataset_id=dataset.dataset_id,
        title=dataset.title,
        description=dataset.description,
        industry=dataset.industry,
        signal_count=len(dataset.signals),
        context_count=len(dataset.customer_context),
        journeys=sorted({signal.journey for signal in dataset.signals}),
    )
