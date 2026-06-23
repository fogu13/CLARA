"""LangGraph triage pipeline — agentic state machine.

Replaces Odradek_2's synchronous per-request build_candidates model
(apps/api/app/main.py:384-395) with a durable, resumable graph:

    ingest -> enrich -> classify -> synthesize -> governance_gate
           -> (interrupt: approve) -> action -> measure -> learn

Design principles (preserved from both source repos):
  - Bounded LLM calls for structured extraction; no autonomous action selection.
  - Human-in-the-loop interrupt for consequential actions (EU AI Act Art 14).
  - Every AI claim carries evidence/confidence/limitations/audit (Odradek_2 model).
  - Deterministic cross-signal severity (Elvis synthesize-insights) stays in code.
  - Governance gate (Odradek_2 PolicyRule) blocks action if checks fail.
  - MemorySaver checkpointer for tests; PostgresSaver for production durability.
"""

from __future__ import annotations

import logging
from typing import Any

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt

from app.agents.state import TriageState
from app.services.enrichment import enrich_signals, merge_enrichment_into_signal
from app.services.synthesis import synthesize_insights

logger = logging.getLogger(__name__)


# ============================================================
# Node functions — each takes TriageState, returns partial update
# ============================================================


def ingest_node(state: TriageState) -> dict[str, Any]:
    """Entry point: validate that signals exist and set initial status."""
    signals = state.get("signals", [])
    if not signals:
        return {"status": "empty", "errors": ["No signals to process"]}
    return {
        "status": "ingested",
        "errors": [],
        "enriched_signals": [],
        "taxonomy_mappings": [],
        "insights": [],
        "governance_checks": [],
        "action_results": [],
    }


def enrich_node(state: TriageState) -> dict[str, Any]:
    """LLM enrichment: extract sentiment/urgency/tags from each signal.

    Port of reference/elvis/supabase/functions/enrich-signal/index.ts.
    Uses app.services.ai.call_tool for provider-agnostic LLM calls.
    """  # noqa: E501
    signals = state.get("signals", [])
    if not signals:
        return {"enriched_signals": [], "enrichment_count": 0}

    # Prepare items for enrichment (only qualitative signals with text)
    items = [
        {
            "id": s.get("signal_id", s.get("id", "")),
            "text": s.get("feedback_text", s.get("text", "")),
            "signal_type": "qualitative",
            "contact_count": s.get("contact_count", 1),
        }
        for s in signals
        if s.get("feedback_text") or s.get("text")
    ]

    if not items:
        return {"enriched_signals": [], "enrichment_count": 0}

    enrichments = enrich_signals(items)

    # Merge enrichments back into signals
    enrichment_map = {e["id"]: e for e in enrichments}
    enriched = []
    for item in items:
        enr = enrichment_map.get(item["id"])
        if enr:
            merged = merge_enrichment_into_signal(item, enr)
            enriched.append(merged)
        else:
            # No enrichment returned — pass through with defaults
            enriched.append({
                **item,
                "sentiment": None,
                "sentiment_score": None,
                "urgency": "medium",
                "tags": [],
                "enriched": False,
            })

    errors = list(state.get("errors", []))
    if len(enriched) < len(items):
        errors.append(f"Enriched {len(enriched)}/{len(items)} signals (partial)")

    return {
        "enriched_signals": enriched,
        "enrichment_count": len(enriched),
        "status": "enriched",
        "errors": errors,
    }


def classify_node(state: TriageState) -> dict[str, Any]:
    """Semantic taxonomy mapping: embed each signal and map to closest node.

    Port of mapSignalToNode (enrich-signal/index.ts:19-43).
    Requires a DB connection — if absent, skips (signals proceed to synthesis).
    """  # noqa: E501
    enriched = state.get("enriched_signals", [])
    if not enriched:
        return {"taxonomy_mappings": [], "classified_count": 0}

    # Classification requires a DB connection (set via config when compiled)
    # In test/no-DB mode, we skip and let synthesis proceed
    mappings: list[dict[str, Any]] = []

    # The actual DB-backed classification is done via semantic_taxonomy.map_signal_to_node
    # which needs a psycopg connection. For the graph, we store mappings in state
    # and the caller (FastAPI route) provides the connection.
    # For now, mark as classified — the DB integration happens in Phase 1 wiring.

    return {
        "taxonomy_mappings": mappings,
        "classified_count": len(mappings),
        "status": "classified",
    }


def synthesize_node(state: TriageState) -> dict[str, Any]:
    """LLM synthesis: cluster enriched signals by tag and synthesize insights.

    Port of reference/elvis/supabase/functions/synthesize-insights/index.ts.
    Severity is computed deterministically (cross_signal_severity); the LLM
    is explicitly told NOT to set it.
    """
    enriched = state.get("enriched_signals", [])
    if not enriched:
        return {"insights": [], "status": "synthesized"}

    insights = synthesize_insights(enriched)

    errors = list(state.get("errors", []))
    if not insights and enriched:
        errors.append("No insights synthesized (may need more signals for corroboration)")

    return {
        "insights": insights,
        "status": "synthesized",
        "errors": errors,
    }


def governance_node(state: TriageState) -> dict[str, Any]:
    """Governance gate: check policy rules before action.

    Wraps Odradek_2's assert_governance_allows_decision pattern
    (workflow.py:43-57). Blocking checks prevent action — the human can
    still review but cannot approve.
    """  # noqa: E501
    insights = state.get("insights", [])
    if not insights:
        return {
            "governance_checks": [],
            "governance_passed": True,
            "status": "governed",
        }

    # Check each insight's suggested actions against policy rules.
    # In the full implementation, this wraps PolicyRuleStore + governance checks.
    # For now, we do a basic check: insights with compliance_concern category
    # get a blocking flag requiring human review.
    checks: list[dict[str, Any]] = []
    for insight in insights:
        if insight.get("category") == "compliance_concern":
            checks.append({
                "insight_id": insight.get("title", ""),
                "rule_id": "compliance_review_required",
                "status": "fail",
                "blocking": True,
                "message": "Compliance concerns require manual review before action",
            })

    passed = not any(c["blocking"] and c["status"] == "fail" for c in checks)

    result = {
        "governance_checks": checks,
        "governance_passed": passed,
        "status": "blocked" if not passed else "governed",
    }
    if not passed:
        result["approval_decision"] = "blocked"
        result["approved_insights"] = []
        result["errors"] = list(state.get("errors", [])) + [
            "Governance gate blocked action — blocking checks must be resolved",
        ]
    return result


def approval_node(state: TriageState) -> dict[str, Any]:
    """Human-in-the-loop approval interrupt.

    Pauses the graph and waits for a human to approve or reject the proposed
    actions. Uses LangGraph's interrupt() mechanism — the graph resumes when
    Command(resume="approved") or Command(resume="rejected") is passed.

    This is the EU AI Act Art 14 human-oversight gate: consequential actions
    (creating tickets, sending notifications, building segments) require
    explicit human approval before execution.
    """
    insights = state.get("insights", [])
    if not insights:
        return {"approval_decision": "skipped", "approved_insights": [], "status": "approved"}

    governance_passed = state.get("governance_passed", True)
    if not governance_passed:
        return {
            "approval_decision": "blocked",
            "approved_insights": [],
            "status": "blocked",
            "errors": list(state.get("errors", []))
            + ["Governance gate blocked action — blocking checks must be resolved"],
        }

    # Interrupt: pause here and wait for human input.
    # The human reviews insights and proposed actions, then resumes with
    # Command(resume="approved") or Command(resume="rejected").
    decision = interrupt({
        "type": "approval_required",
        "insights": [
            {
                "title": i.get("title", ""),
                "summary": i.get("summary", ""),
                "severity": i.get("severity", ""),
                "suggested_actions": i.get("suggested_actions", []),
            }
            for i in insights
        ],
        "message": (
            "Review the proposed insights and actions. "
            "Approve to execute, reject to discard."
        ),
    })

    if decision == "approved":
        return {
            "approval_decision": "approved",
            "approved_insights": insights,
            "status": "approved",
        }
    return {
        "approval_decision": "rejected",
        "approved_insights": [],
        "status": "rejected",
    }


def action_node(state: TriageState) -> dict[str, Any]:
    """Execute approved actions via connectors.

    Phase 2 target: calls Connector.push() for Jira/Slack/etc.
    Currently a stub that records what would be pushed.
    """
    approved = state.get("approved_insights", [])
    if not approved:
        return {"action_results": [], "status": "acted"}

    results: list[dict[str, Any]] = []
    for insight in approved:
        for action in insight.get("suggested_actions", []):
            results.append({
                "insight_id": insight.get("title", ""),
                "action_type": action.get("type", "unknown"),
                "title": action.get("title", ""),
                "external_id": None,  # Phase 2: real connector returns this
                "status": "pending_implementation",  # Phase 2: "pushed" / "failed"
                "audit": {
                    "source": "connector_stub",
                    "limitations": [
                        "Action execution is stubbed — Phase 2 implements real connectors",
                    ],
                },
            })

    return {"action_results": results, "status": "acted"}


def measure_node(state: TriageState) -> dict[str, Any]:
    """Measure outcomes after action execution.

    Phase 3 target: recompute metrics, score resolution_score, resolve insight.
    Currently a stub that records the measurement intent.
    """
    results = state.get("action_results", [])
    if not results:
        return {"outcome": None, "status": "measured"}

    return {
        "outcome": {
            "metric": "affected_contacts",  # Phase 3: from outcome contract
            "baseline": None,  # Phase 3: captured at action time
            "measured": None,  # Phase 3: recomputed after window
            "resolution_score": None,  # Phase 3: clamp01(1 - measured/baseline)
            "status": "pending_implementation",
        },
        "status": "measured",
    }


def learn_node(state: TriageState) -> dict[str, Any]:
    """Extract learnings from the action-outcome cycle.

    Phase 3 target: LLM distils learnings, confidence decay applied.
    Currently a stub that records the learning intent.
    """
    outcome = state.get("outcome")
    if not outcome:
        return {"learning": None, "status": "learned"}

    return {
        "learning": {
            "conclusion": None,  # Phase 3: worked/partially_worked/did_not_work
            "confidence_decay": None,  # Phase 3: exponential decay
            "status": "pending_implementation",
        },
        "status": "learned",
    }


# ============================================================
# Edge routing
# ============================================================


def route_after_ingest(state: TriageState) -> str:
    """Route after ingest: if no signals, skip to END; otherwise enrich."""
    if state.get("status") == "empty" or not state.get("signals"):
        return END
    return "enrich"


def route_after_governance(state: TriageState) -> str:
    """Route after governance: if blocked, skip to END; otherwise go to approval."""
    if state.get("approval_decision") == "blocked" or not state.get("governance_passed", True):
        return END
    return "approval"


def route_after_approval(state: TriageState) -> str:
    """Route after approval: if rejected, skip to END; otherwise execute actions."""
    decision = state.get("approval_decision")
    if decision in ("rejected", "blocked", "skipped"):
        return END
    return "action"


# ============================================================
# Graph construction
# ============================================================


def build_triage_graph(
    *,
    checkpointer: Any = None,
) -> Any:
    """Build and compile the triage state machine.

    Args:
        checkpointer: A LangGraph checkpointer for durability/resumability.
            Use MemorySaver for tests, PostgresSaver for production.
            If None, no checkpointing (graph runs to completion or interrupt).

    Returns:
        A compiled LangGraph that can be invoked with .invoke() or .stream().
    """
    graph = StateGraph(TriageState)

    # Add nodes
    graph.add_node("ingest", ingest_node)
    graph.add_node("enrich", enrich_node)
    graph.add_node("classify", classify_node)
    graph.add_node("synthesize", synthesize_node)
    graph.add_node("governance", governance_node)
    graph.add_node("approval", approval_node)
    graph.add_node("action", action_node)
    graph.add_node("measure", measure_node)
    graph.add_node("learn", learn_node)

    # Add edges (linear flow with conditional branches)
    graph.add_edge(START, "ingest")
    graph.add_conditional_edges("ingest", route_after_ingest)
    graph.add_edge("enrich", "classify")
    graph.add_edge("classify", "synthesize")
    graph.add_edge("synthesize", "governance")

    # Conditional: governance -> approval or END (if blocked)
    graph.add_conditional_edges("governance", route_after_governance)

    # Conditional: approval -> action or END (if rejected/blocked)
    graph.add_conditional_edges("approval", route_after_approval)

    graph.add_edge("action", "measure")
    graph.add_edge("measure", "learn")
    graph.add_edge("learn", END)

    return graph.compile(checkpointer=checkpointer)


def build_default_graph() -> Any:
    """Build the triage graph with an in-memory checkpointer.

    Use this for tests and local dev. For production, use
    build_triage_graph(checkpointer=PostgresSaver(...)).
    """
    return build_triage_graph(checkpointer=MemorySaver())
