"""CLARA MCP server — read-only access for external AI tools (X8/W6).

Exposes the workspace to Claude Desktop / Claude Code / Cursor via MCP:
problems, evidence packs, outcomes, emerging radar, measurement checkpoints,
published model-card metrics, and the grounded Ask-CLARA Q&A. STRICTLY
read-only + ask — no approvals, no executions, no writes: governance actions
stay in the product where the policy gates live.

Tools call the CLARA REST API over HTTP (fetch layer: services/mcp_fetch.py),
so auth/RBAC/rate limits apply exactly as they do for any client. Setup and
config snippets: docs/mcp.md.

Run (stdio transport):
  pip install -e "apps/api[mcp]"
  python -m app.mcp_server
"""

from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from app.services.mcp_fetch import (
    api_client,
    fetch_emerging,
    fetch_evidence_pack,
    fetch_measurements,
    fetch_model_card_metrics,
    fetch_outcome_board,
    fetch_problem,
    fetch_problems,
    post_question,
)

mcp = FastMCP(
    "clara",
    instructions=(
        "Read-only access to a CLARA workspace (governed customer-feedback triage). "
        "Use ask_clara for questions about what customers are saying — it answers "
        "with citations and refuses when evidence is thin. get_evidence_pack returns "
        "the audit-grade record of one problem (content-hashed). Approvals and "
        "actions cannot be performed here; they require the CLARA product's "
        "approval flow."
    ),
)


@mcp.tool()
def list_problems() -> list[dict[str, Any]]:
    """List the workspace's problems (id, title, status, impact, affected customers)."""
    with api_client() as client:
        return fetch_problems(client)


@mcp.tool()
def get_problem(problem_id: str) -> dict[str, Any]:
    """Full detail for one problem: statement, root cause, evidence excerpts,
    proposed actions, governance checks and outcome contract."""
    with api_client() as client:
        return fetch_problem(client, problem_id)


@mcp.tool()
def get_evidence_pack(problem_id: str) -> dict[str, Any]:
    """The audit-grade export of one problem: evidence -> actions -> policy trail
    -> approvals -> executions -> outcome (incl. guardrails and evidence grade),
    stamped with a content hash so its integrity is verifiable later."""
    with api_client() as client:
        return fetch_evidence_pack(client, problem_id)


@mcp.tool()
def get_outcome_board() -> dict[str, Any]:
    """Outcome status across problems: measured/improving/target-met tallies and
    per-problem metric, baseline, latest value, evidence grade, guardrails and
    learning status."""
    with api_client() as client:
        return fetch_outcome_board(client)


@mcp.tool()
def get_emerging_problems() -> dict[str, Any]:
    """The emerging-problems radar: candidates trending up, with scores, counts
    and the corroboration floor ("action" needs multi-source or multi-customer)."""
    with api_client() as client:
        return fetch_emerging(client)


@mcp.tool()
def get_measurement_checkpoints() -> list[dict[str, Any]]:
    """Scheduled outcome re-measurement checkpoints (pending / done / manual_required)."""
    with api_client() as client:
        return fetch_measurements(client)


@mcp.tool()
def get_model_card_metrics() -> dict[str, Any]:
    """Published evaluation quality of the triage model: per-language accuracy
    with denominators, CIs and dataset date — how much to trust the data here."""
    with api_client() as client:
        return fetch_model_card_metrics(client)


@mcp.tool()
def ask_clara(question: str) -> dict[str, Any]:
    """Ask a question about the workspace's customer feedback. Grounded in signal
    evidence with citations and a model score; refuses when evidence is thin."""
    with api_client() as client:
        return post_question(client, question)


if __name__ == "__main__":
    mcp.run()
