"""HTTP fetch layer for the CLARA MCP server (app/mcp_server.py).

Separate module so tests can exercise every tool's data path WITHOUT the
optional `mcp` extra installed (CI installs `[dev]` only): plain httpx against
the REST API, auth/RBAC/rate limits applying exactly as for any client.

Credentials (either works; API keys are the intended machine credential —
minted show-once in Integrations, role-scoped, revocable):
  CLARA_API_URL    default http://localhost:8000
  CLARA_API_KEY    sent as X-Api-Key
  CLARA_API_TOKEN  sent as Authorization: Bearer (JWT alternative)
"""

from __future__ import annotations

import os
from typing import Any

import httpx


def api_headers() -> dict[str, str]:
    headers: dict[str, str] = {}
    api_key = os.getenv("CLARA_API_KEY")
    if api_key:
        headers["X-Api-Key"] = api_key
    token = os.getenv("CLARA_API_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def api_client() -> httpx.Client:
    return httpx.Client(
        base_url=os.getenv("CLARA_API_URL", "http://localhost:8000"),
        headers=api_headers(),
        timeout=60.0,
    )


def fetch_problems(client: httpx.Client) -> list[dict[str, Any]]:
    response = client.get("/problems")
    response.raise_for_status()
    return response.json()


def fetch_problem(client: httpx.Client, problem_id: str) -> dict[str, Any]:
    response = client.get(f"/problems/{problem_id}")
    response.raise_for_status()
    return response.json()


def fetch_evidence_pack(client: httpx.Client, problem_id: str) -> dict[str, Any]:
    """The audit-grade export: evidence -> actions -> approvals -> executions ->
    outcome (incl. guardrails + evidence grade), stamped with a content hash."""
    response = client.get(f"/problems/{problem_id}/evidence-pack", params={"format": "json"})
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


def fetch_model_card_metrics(client: httpx.Client) -> dict[str, Any]:
    response = client.get("/model-card/metrics")
    response.raise_for_status()
    return response.json()


def post_question(client: httpx.Client, question: str) -> dict[str, Any]:
    response = client.post("/ask", json={"question": question})
    response.raise_for_status()
    return response.json()
