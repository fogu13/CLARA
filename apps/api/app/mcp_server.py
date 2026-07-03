"""CLARA MCP server — read-only access for external AI tools (X8).

Exposes the workspace to Claude Desktop / Claude Code / Cursor via MCP:
problems, evidence, outcomes, emerging radar, measurement checkpoints, and the
grounded Ask-CLARA Q&A. STRICTLY read-only + ask — no approvals, no executions,
no writes: governance actions stay in the product where the policy gates live.

Tools call the CLARA REST API over HTTP, so auth/RBAC/rate limits apply exactly
as they do for any client. Configure:
  CLARA_API_URL    (default http://localhost:8000)
  CLARA_API_TOKEN  (optional bearer token for auth-enabled deployments)

Run (stdio transport):
  python -m app.mcp_server

Claude Desktop / Code config snippet:
  {"mcpServers": {"clara": {"command": "python", "args": ["-m", "app.mcp_server"],
                            "cwd": "<repo>/apps/api"}}}
"""

from __future__ import annotations

import os
from typing import Any

import httpx
from mcp.server.fastmcp import FastMCP


def api_client() -> httpx.Client:
    headers = {}
    token = os.getenv("CLARA_API_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return httpx.Client(
        base_url=os.getenv("CLARA_API_URL", "http://localhost:8000"),
        headers=headers,
        timeout=60.0,
    )


# Plain fetch functions (testable with an injected client / ASGI transport).

def fetch_problems(client: httpx.Client) -> list[dict[str, Any]]:
    response = client.get("/problems")
    response.raise_for_status()
    return response.json()


def fetch_problem(client: httpx.Client, problem_id: str) -> dict[str, Any]:
    response = client.get(f"/problems/{problem_id}")
    response.raise_for_status()
    return response.json()


def fetch_outcome_board(client: httpx.Client) -> dict[str, Any]:
    response = client.get("/outcome-board")
    response.raise_for_status()
    return response.json()


def fetch_emerging(client: httpx.Client) -> dict[str, Any]:
    response = client.get("/emerging-problems")
    response.raise_for_status()
    return response.json()


def fetch_measurements(client: httpx.Client) -> list[dict[str, Any]]:
    response = client.get("/measurements")
    response.raise_for_status()
    return response.json()


def post_question(client: httpx.Client, question: str) -> dict[str, Any]:
    response = client.post("/ask", json={"question": question})
    response.raise_for_status()
    return response.json()


mcp = FastMCP(
    "clara",
    instructions=(
        "Read-only access to a CLARA workspace (governed customer-feedback triage). "
        "Use ask_clara for questions about what customers are saying — it answers "
        "with citations and refuses when evidence is thin. Approvals and actions "
        "cannot be performed here; they require the CLARA product's approval flow."
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
def get_outcome_board() -> dict[str, Any]:
    """Outcome status across problems: measured/improving/target-met tallies and
    per-problem metric, baseline, latest value and learning status."""
    with api_client() as client:
        return fetch_outcome_board(client)


@mcp.tool()
def get_emerging_problems() -> dict[str, Any]:
    """The emerging-problems radar: candidates trending up, with scores and counts."""
    with api_client() as client:
        return fetch_emerging(client)


@mcp.tool()
def get_measurement_checkpoints() -> list[dict[str, Any]]:
    """Scheduled outcome re-measurement checkpoints (pending / done / manual_required)."""
    with api_client() as client:
        return fetch_measurements(client)


@mcp.tool()
def ask_clara(question: str) -> dict[str, Any]:
    """Ask a question about the workspace's customer feedback. Grounded in signal
    evidence with citations and a confidence score; refuses when evidence is thin."""
    with api_client() as client:
        return post_question(client, question)


if __name__ == "__main__":
    mcp.run()
