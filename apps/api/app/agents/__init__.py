"""LangGraph triage -> action state machines.

Phase 1 target. Replaces Odradek_2's synchronous per-request `build_candidates`
model (apps/api/app/main.py:384-395) with a durable, resumable graph:

    ingest -> enrich -> classify -> synthesize -> governance_gate
           -> (interrupt: human approve) -> action -> measure -> learn

Design principles (preserved from both source repos):
  - Bounded LLM calls for structured extraction; no autonomous action selection.
  - Human-in-the-loop interrupt for consequential actions (EU AI Act Art 14).
  - Every AI claim carries evidence/confidence/limitations/audit (Odradek_2 model).
  - Deterministic cross-signal severity (Elvis synthesize-insights) stays in code.
  - Postgres checkpointer for durability + resumability.

TODO(Phase 1):
  - define TriageState TypedDict
  - build StateGraph nodes wrapping services/{ai,taxonomies,context_impact,policies,workflow}
  - add interrupt() before action execution
  - register PostgresSaver checkpointer
"""
