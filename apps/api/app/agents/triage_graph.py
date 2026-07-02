"""LangGraph triage pipeline — agentic state machine.

Replaces CLARA_2's synchronous per-request build_candidates model
(apps/api/app/main.py:384-395) with a durable, resumable graph:

    ingest -> enrich -> classify -> synthesize -> governance_gate
           -> (interrupt: approve) -> action -> measure -> learn

Design principles (preserved from both source repos):
  - Bounded LLM calls for structured extraction; no autonomous action selection.
  - Human-in-the-loop interrupt for consequential actions (EU AI Act Art 14).
  - Every AI claim carries evidence/confidence/limitations/audit (CLARA_2 model).
  - Deterministic cross-signal severity (Elvis synthesize-insights) stays in code.
  - Governance gate (CLARA_2 PolicyRule) blocks action if checks fail.
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
            # Carry the full original signal forward so downstream frequency, trend,
            # source corroboration and 8-factor severity keep source/timestamp/customer_id.
            **s,
            "id": s.get("signal_id", s.get("id", "")),
            "text": s.get("feedback_text", s.get("text", "")),
            "signal_type": s.get("signal_type", "qualitative"),
            "contact_count": s.get("contact_count", 1),
        }
        for s in signals
        if s.get("feedback_text") or s.get("text")
    ]

    if not items:
        return {"enriched_signals": [], "enrichment_count": 0}

    # Few-shot exemplars pin the model to the project's tag vocabulary + urgency
    # calibration (Phase B). On by default; disable with ENRICH_FEWSHOT=0.
    from app.services.exemplar_store import fewshot_enabled, load_exemplars

    exemplars = load_exemplars() if fewshot_enabled() else None
    enrichments = enrich_signals(items, exemplars=exemplars)

    # Merge enrichments back into signals. Guard e.get("id") — a record missing its
    # id would otherwise KeyError and crash the whole pipeline.
    enrichment_map = {e["id"]: e for e in enrichments if e.get("id") is not None}
    enriched = []
    success = 0
    for item in items:
        enr = enrichment_map.get(item["id"])
        if enr:
            enriched.append(merge_enrichment_into_signal(item, enr))
            success += 1
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

    # Compare successfully-enriched vs total. `enriched` always == len(items) (we
    # append a fallback for every item), so the old len(enriched) check was dead code.
    errors = list(state.get("errors", []))
    if success < len(items):
        errors.append(f"Enriched {success}/{len(items)} signals (partial)")

    return {
        "enriched_signals": enriched,
        "enrichment_count": success,
        "status": "enriched",
        "errors": errors,
    }


def classify_node(state: TriageState) -> dict[str, Any]:
    """Semantic taxonomy mapping: embed each signal and map to closest node.

    Port of mapSignalToNode (enrich-signal/index.ts:19-43).
    When a DB connection is available (passed via state), calls
    map_signal_to_node for each enriched signal. If absent (tests/no-DB),
    skips gracefully — signals proceed to synthesis without taxonomy mapping.
    """  # noqa: E501
    enriched = state.get("enriched_signals", [])
    if not enriched:
        return {"taxonomy_mappings": [], "classified_count": 0}

    workspace_id = state.get("workspace_id", 1)
    db_conn = state.get("db_connection")
    mappings: list[dict[str, Any]] = []

    if db_conn is not None:
        from app.services.semantic_taxonomy import map_signal_to_node

        for sig in enriched:
            sig_id = sig.get("id", sig.get("signal_id", ""))
            text = sig.get("text", sig.get("feedback_text", ""))
            try:
                node_id = map_signal_to_node(db_conn, workspace_id, str(sig_id), text)
                if node_id:
                    mappings.append({"signal_id": sig_id, "node_id": node_id})
            except Exception:
                logger.debug("Taxonomy mapping failed for %s, skipping", sig_id, exc_info=True)

    return {
        "taxonomy_mappings": mappings,
        "classified_count": len(mappings),
        "status": "classified",
    }


def synthesize_node(state: TriageState) -> dict[str, Any]:
    """LLM synthesis: cluster enriched signals and synthesize insights.

    Uses multi-tag Jaccard clustering + optional semantic fallback.
    Severity uses the 8-factor impact model when context_data is available,
    falling back to the simple urgency+volume+negativity formula.
    Frequency analysis provides time-decayed counts + trend labels.
    """
    enriched = state.get("enriched_signals", [])
    if not enriched:
        return {"insights": [], "status": "synthesized"}

    context_data = state.get("context_data")
    insights = synthesize_insights(
        enriched,
        context_data=context_data,
        learnings=state.get("learnings"),
    )

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

    Wraps CLARA_2's assert_governance_allows_decision pattern
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
    """Execute approved actions via real connectors.

    Calls Connector.push() for Jira (create_ticket), Slack (notify), etc.
    Connector configs are looked up from the connector config store. If no
    connector is configured for an action type, the action is recorded as
    'no_connector' (non-fatal — the insight is still approved, just not pushed).
    """
    from app.connectors import get_destination_for_action
    from app.connectors.base import ConnectorError

    approved = state.get("approved_insights", [])
    if not approved:
        return {"action_results": [], "status": "acted"}

    # Connector configs are passed via state (injected by the FastAPI route
    # when it invokes the graph). Falls back to empty dict = no connectors.
    connector_configs: dict[str, dict[str, Any]] = state.get("connector_configs", {})

    results: list[dict[str, Any]] = []
    errors = list(state.get("errors", []))

    for insight in approved:
        for action in insight.get("suggested_actions", []):
            action_type = action.get("type", "unknown")
            insight_ctx = {
                "insight_title": insight.get("title", ""),
                "insight_summary": insight.get("summary", ""),
                "insight_severity": insight.get("severity", ""),
                "insight_signal_ids": insight.get("signal_ids", []),
            }
            full_action = {**action, **insight_ctx}

            # Look up the destination connector for this action type
            dest = get_destination_for_action(action_type)
            if dest is None:
                results.append({
                    "insight_id": insight.get("title", ""),
                    "action_type": action_type,
                    "title": action.get("title", ""),
                    "external_id": None,
                    "status": "no_connector",
                    "audit": {
                        "source": "action_node",
                        "limitations": [
                            f"No connector registered for action type '{action_type}'",
                        ],
                    },
                })
                continue

            dest_type = dest.connector_type
            config = connector_configs.get(dest_type, {})

            if not config:
                results.append({
                    "insight_id": insight.get("title", ""),
                    "action_type": action_type,
                    "title": action.get("title", ""),
                    "external_id": None,
                    "status": "no_config",
                    "audit": {
                        "source": "action_node",
                        "connector": dest_type,
                        "limitations": [
                            f"Connector '{dest_type}' not configured — "
                            "configure via PUT /connectors/" + dest_type,
                        ],
                    },
                })
                continue

            try:
                result = dest.push(full_action, config)
                results.append({
                    "insight_id": insight.get("title", ""),
                    "action_type": action_type,
                    "title": action.get("title", ""),
                    "external_id": result.get("external_id"),
                    "status": result.get("status", "pushed"),
                    "audit": result.get("audit", {}),
                })
            except ConnectorError as exc:
                results.append({
                    "insight_id": insight.get("title", ""),
                    "action_type": action_type,
                    "title": action.get("title", ""),
                    "external_id": None,
                    "status": "failed",
                    "audit": {
                        "source": "action_node",
                        "connector": dest_type,
                        "error": str(exc),
                        "limitations": [f"Connector push failed: {exc}"],
                    },
                })
                errors.append(
                    f"Connector '{dest_type}' failed for action "
                    f"'{action.get('title', '')}': {exc}"
                )

    return {"action_results": results, "status": "acted", "errors": errors}


def measure_node(state: TriageState) -> dict[str, Any]:
    """Measure outcomes after action execution.

    Port of Elvis's measure-outcomes edge fn + CLARA_2's direction-aware
    outcome_status. Builds an outcome contract at action time, then measures
    the metric and computes resolution_score + closure_level.

    In the full implementation, the measured_value is recomputed from new
    signals after the measurement window. For the synchronous graph, the
    caller can pass a measured_value via state; if absent, we record the
    contract and mark as 'measuring' (pending window expiry).
    """
    from app.services.outcome_engine import (
        build_outcome_contract,
        closure_level,
        measure_outcome,
    )

    approved = state.get("approved_insights", [])
    action_results = state.get("action_results", [])

    if not approved or not action_results:
        return {"outcome": None, "status": "measured"}

    # Build outcome contract from the first approved insight
    insight = approved[0]
    contract = build_outcome_contract(insight=insight)

    # Check if a measured value was provided (e.g. from a scheduled pass
    # after the measurement window, or a manual "Measure now" action).
    # If not provided, record the contract and mark as 'measuring'.
    measured_value = state.get("measured_value")

    if measured_value is not None:
        outcome = measure_outcome(
            contract=contract,
            measured_value=float(measured_value),
            action_results=action_results,
        )
    else:
        # No measurement yet — record the contract for later measurement
        outcome = {
            "metric": contract["metric"],
            "baseline": contract["baseline"],
            "target": contract["target"],
            "measured": None,
            "resolution_score": None,
            "status": "not_measured",
            "closure_level": closure_level(
                action_results=action_results,
                measured=None,
                score=None,
            ),
            "summary": (
                f"Outcome contract captured: {contract['metric']} "
                f"baseline {contract['baseline']}. "
                "Measurement pending window expiry."
            ),
            "contract": contract,
        }

    return {"outcome": outcome, "status": "measured"}


def learn_node(state: TriageState) -> dict[str, Any]:
    """Extract learnings from the action-outcome cycle.

    Merges Elvis's confidence-decay AbLearning model with CLARA_2's
    structured LearningConclusion verdicts. If a human conclusion is provided
    via state, builds a learning record with appropriate confidence.
    Otherwise, auto-derives a preliminary conclusion from the outcome status.
    """
    from app.services.learning_engine import (
        build_learning_from_conclusion,
        decayed_confidence,
        learning_freshness,
    )

    outcome = state.get("outcome")
    approved = state.get("approved_insights", [])

    if not outcome or not approved:
        return {"learning": None, "status": "learned"}

    insight = approved[0]

    # If a human conclusion was provided via state, use it.
    # Otherwise, auto-derive a preliminary conclusion from the outcome.
    human_conclusion = state.get("human_conclusion")

    if human_conclusion:
        conclusion = human_conclusion
    else:
        # Auto-derive preliminary conclusion from outcome status
        status = outcome.get("status", "not_measured")

        if status == "target_met":
            auto_status = "worked"
            auto_summary = f"Action achieved target for {outcome.get('metric', 'the metric')}."
        elif status == "improving":
            auto_status = "partially_worked"
            auto_summary = f"Action showed improvement for {outcome.get('metric', 'the metric')}."
        elif status == "not_improved":
            auto_status = "did_not_work"
            auto_summary = f"Action did not improve {outcome.get('metric', 'the metric')}."
        else:  # not_measured
            auto_status = "inconclusive"
            auto_summary = "Outcome not yet measured — conclusion is preliminary."

        conclusion = {
            "learning_status": auto_status,
            "summary": auto_summary,
            "limitations": "Auto-derived from outcome status; awaiting human validation.",
            "next_step": "Validate this learning with a human review.",
            "reviewer": "system",
        }

    learning = build_learning_from_conclusion(
        conclusion=conclusion,
        insight=insight,
        outcome=outcome,
    )

    # Compute current decayed confidence + freshness badge
    decayed = decayed_confidence(learning)
    freshness = learning_freshness(learning)

    learning["decayed_confidence"] = round(decayed, 4)
    learning["freshness"] = freshness

    return {"learning": learning, "status": "learned"}


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
