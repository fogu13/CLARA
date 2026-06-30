"""Outcome simulation harness — seed the learning store so the loop is demoable.

Real measured-outcome data is not yet flowing in the thesis demo, but the
outcome -> learning -> retrieval loop needs learnings to retrieve. This harness
runs the real triage stages on the demo datasets, fabricates a measured value
per a chosen scenario, drives the *existing* outcome + learning engines
(``build_outcome_contract`` / ``measure_outcome`` /
``build_learning_from_conclusion`` — the same code the graph's measure/learn
nodes use), and persists the resulting learnings.

After seeding, ``run_live`` can A/B synthesis quality with vs without learnings.

Run:  cd apps/api && python3 -m app.evals.simulate_outcomes [improved|no_change|regressed|mixed]
Needs: AI_BASE_URL / AI_API_KEY / AI_MODEL configured.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

# Importing run_live sets AI_TEMPERATURE=0 for deterministic eval calls.
from app.evals.run_live import DEMO_DIR, _normalize_demo_signal
from app.services.ai import AI_MODEL, AIProviderError
from app.services.enrichment import enrich_signals
from app.services.exemplar_store import fewshot_enabled, load_exemplars
from app.services.learning_engine import (
    build_learning_from_conclusion,
    decayed_confidence,
    learning_freshness,
)
from app.services.learning_store import SQLiteLearningStore
from app.services.outcome_engine import build_outcome_contract, measure_outcome
from app.services.synthesis import synthesize_insights

# Auto-conclusion mapping — mirrors learn_node in triage_graph.py.
_STATUS_TO_CONCLUSION = {
    "target_met": ("worked", "Action achieved target for {metric}."),
    "improving": ("partially_worked", "Action showed improvement for {metric}."),
    "not_improved": ("did_not_work", "Action did not improve {metric}."),
    "not_measured": ("inconclusive", "Outcome not yet measured."),
}


def _fabricate_measured(contract: dict[str, Any], scenario: str, idx: int) -> float:
    """Fabricate a plausible post-action metric value for a decrease metric."""
    baseline = float(contract.get("baseline", 0)) or 1.0
    if scenario == "mixed":
        scenario = ("improved", "no_change", "regressed")[idx % 3]
    if scenario == "improved":
        return baseline * 0.1   # large drop -> high resolution -> "worked"
    if scenario == "regressed":
        return baseline * 1.2   # rose -> "did_not_work"
    return baseline             # no_change -> "not_improved"


def _default_db_path() -> Path:
    """Same SQLite file the API uses (apps/api/.data/clara.db), CLARA_DB_PATH-aware."""
    configured = os.getenv("CLARA_DB_PATH")
    if configured:
        return Path(configured)
    # __file__ is apps/api/app/evals/simulate_outcomes.py -> parents[2] is apps/api
    return Path(__file__).resolve().parents[2] / ".data" / "clara.db"


def main() -> int:
    scenario = sys.argv[1] if len(sys.argv) > 1 else "improved"
    if scenario not in ("improved", "no_change", "regressed", "mixed"):
        print(f"Unknown scenario {scenario!r}", file=sys.stderr)
        return 2
    if not AI_MODEL:
        print("AI_MODEL unset — configure AI_BASE_URL/AI_API_KEY/AI_MODEL.", file=sys.stderr)
        return 2

    pool: list[dict] = []
    for f in sorted(DEMO_DIR.glob("*.json")):
        data = json.loads(f.read_text())
        pool.extend(_normalize_demo_signal(s) for s in data.get("signals", []))

    try:
        enrichments = enrich_signals(
            [{"id": s["id"], "text": s["text"]} for s in pool],
            exemplars=load_exemplars() if fewshot_enabled() else None,
        )
    except AIProviderError as exc:
        print(f"LLM call failed: {exc}", file=sys.stderr)
        return 2

    by_id = {e.get("id"): e for e in enrichments}
    enriched = [{**s, "tags": by_id.get(s["id"], {}).get("tags", []),
                 "urgency": by_id.get(s["id"], {}).get("urgency")} for s in pool]

    # Synthesize WITHOUT learnings — these are the seed insights we score outcomes on.
    insights = synthesize_insights(enriched, min_cluster_size=2, min_sources=1)

    store = SQLiteLearningStore(_default_db_path())
    store.clear(workspace_id=1)  # fresh seed for a clean A/B

    seeded = 0
    for idx, insight in enumerate(insights):
        contract = build_outcome_contract(insight=insight)
        measured = _fabricate_measured(contract, scenario, idx)
        outcome = measure_outcome(
            contract=contract,
            measured_value=measured,
            action_results=[{"status": "pushed"}],
        )
        status, summary_tpl = _STATUS_TO_CONCLUSION.get(
            outcome["status"], ("inconclusive", "Outcome inconclusive.")
        )
        conclusion = {
            "learning_status": status,
            "summary": summary_tpl.format(metric=outcome.get("metric", "the metric")),
            "limitations": "Auto-derived from a simulated outcome.",
            "reviewer": "simulation",
        }
        learning = build_learning_from_conclusion(
            conclusion=conclusion, insight=insight, outcome=outcome
        )
        learning["decayed_confidence"] = round(decayed_confidence(learning), 4)
        learning["freshness"] = learning_freshness(learning)
        store.persist(learning, workspace_id=1)
        seeded += 1
        print(f"  seeded learning: [{status}] {learning['topic']} "
              f"(resolution={outcome['resolution_score']}, conf={learning['base_confidence']})")

    print(f"\nScenario '{scenario}': seeded {seeded} learning(s) from {len(insights)} "
          f"insight(s) into {store.path}")
    if seeded == 0:
        print("  (no insights clustered — try more demo signals or lower min_cluster_size)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
