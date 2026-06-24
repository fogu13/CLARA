"""LangGraph triage -> action state machines.

Phase 1: replaces CLARA_2's synchronous per-request build_candidates model
(apps/api/app/main.py:384-395) with a durable, resumable graph.
"""

from app.agents.triage_graph import build_default_graph, build_triage_graph

__all__ = ["build_default_graph", "build_triage_graph"]
