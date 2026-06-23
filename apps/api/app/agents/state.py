"""Triage state for the LangGraph agent pipeline.

Defines the TriageState TypedDict that flows through the graph nodes:
  ingest -> enrich -> classify -> synthesize -> governance_gate
         -> (interrupt: approve) -> action -> measure -> learn
"""

from __future__ import annotations

from typing import Any, TypedDict


class TriageState(TypedDict, total=False):
    """State that flows through the triage graph.

    Fields are progressively populated as each node runs. `total=False` so
    nodes can return partial updates without populating every field.
    """

    # --- Input ---
    workspace_id: int
    signals: list[dict[str, Any]]  # raw signals to process

    # --- After enrich ---
    enriched_signals: list[dict[str, Any]]  # signals with sentiment/urgency/tags
    enrichment_count: int  # number of successfully enriched signals

    # --- After classify (semantic taxonomy mapping) ---
    taxonomy_mappings: list[dict[str, Any]]  # {signal_id, node_id, score}
    classified_count: int

    # --- After synthesize ---
    insights: list[dict[str, Any]]  # synthesized insights with severity

    # --- After governance gate ---
    governance_checks: list[dict[str, Any]]  # {rule_id, status, blocking, message}
    governance_passed: bool

    # --- After approval (human-in-the-loop) ---
    approval_decision: str | None  # "approved" | "rejected" | None
    approved_insights: list[dict[str, Any]]

    # --- After action ---
    action_results: list[dict[str, Any]]  # {insight_id, action_type, external_id, status}
    connector_configs: dict[str, dict[str, Any]]  # connector_type -> config (for push)

    # --- After measure ---
    outcome: dict[str, Any] | None  # {metric, baseline, measured, resolution_score}

    # --- After learn ---
    learning: dict[str, Any] | None  # {conclusion, confidence_decay, ...}

    # --- Pipeline metadata ---
    errors: list[str]  # accumulated non-fatal errors
    # current: ingested/enriched/classified/synthesized/governed/approved/acted/measured/learned
    status: str
