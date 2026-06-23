"""Zendesk source connector (pull).

Fetches tickets from Zendesk Support and maps them to canonical signal dicts
via a field map. Uses the Zendesk REST API v2 with basic auth (email/token).

Auth: config = {
    "subdomain": "company",
    "email": "user@company.com",
    "api_token": "..."
}

Field mapping: config["field_map"] = {
    "text": "description",          # ticket field for feedback text
    "external_id": "id",            # dedup key
    "recorded_at": "created_at",    # timestamp
    "customer_id": "requester_id",  # customer
    "tags": "tags",                 # ticket tags
}

Incremental: if config["last_synced_at"] is set, only fetches tickets updated
after that timestamp. Updates last_synced_at in the returned metadata.
"""

from __future__ import annotations

import base64
import logging
from datetime import datetime
from typing import Any

import httpx

from app.connectors.base import ConnectorError

logger = logging.getLogger(__name__)


class ZendeskSourceConnector:
    """Pulls Zendesk tickets and maps them to canonical signal dicts."""

    connector_type = "zendesk"

    def pull(self, config: dict[str, Any]) -> list[dict[str, Any]]:
        """Fetch tickets from Zendesk and return canonical signal dicts.

        Raises ConnectorError on auth failure or unreachable API.
        """
        subdomain = config.get("subdomain", "")
        email = config.get("email", "")
        api_token = config.get("api_token", "")

        if not subdomain or not email or not api_token:
            raise ConnectorError(
                "Missing Zendesk credentials (subdomain, email, api_token required)",
                connector="zendesk",
            )

        field_map = config.get("field_map", {})
        last_synced = config.get("last_synced_at")
        base_url = f"https://{subdomain}.zendesk.com/api/v2"

        # Build the search/ticket URL
        # Use incremental export for efficiency if last_synced is set
        if last_synced:
            url = f"{base_url}/incremental/tickets/cursor.json"
            params: dict[str, Any] = {"start_time": _to_unix(last_synced)}
        else:
            url = f"{base_url}/tickets.json"
            params = {"per_page": 100}

        # Zendesk uses basic auth with email/token
        auth_str = f"{email}/token:{api_token}"
        auth_b64 = base64.b64encode(auth_str.encode()).decode()
        headers = {
            "Authorization": f"Basic {auth_b64}",
            "Accept": "application/json",
        }

        try:
            with httpx.Client(timeout=30.0) as client:
                resp = client.get(url, headers=headers, params=params)
        except httpx.RequestError as exc:
            raise ConnectorError(
                f"Zendesk API unreachable: {exc}",
                connector="zendesk",
            ) from exc

        if resp.status_code == 401:
            raise ConnectorError(
                "Zendesk auth failed — check email and api_token",
                connector="zendesk",
                status=401,
            )
        if resp.status_code == 429:
            raise ConnectorError(
                "Zendesk rate limit exceeded — retry later",
                connector="zendesk",
                status=429,
            )
        if resp.status_code != 200:
            raise ConnectorError(
                f"Zendesk API error {resp.status_code}: {resp.text[:200]}",
                connector="zendesk",
                status=resp.status_code,
            )

        data = resp.json()
        tickets = data.get("tickets", [])
        if not tickets:
            return []

        # Map tickets to canonical signal dicts
        signals: list[dict[str, Any]] = []
        for ticket in tickets:
            signal = self._map_ticket(ticket, field_map, config)
            if signal:
                signals.append(signal)

        # Return the latest timestamp for incremental sync
        if tickets:
            latest = max(t.get("updated_at", "") for t in tickets)
            if signals:
                signals[0].setdefault("_sync_metadata", {})["last_synced_at"] = latest

        return signals

    def _map_ticket(
        self,
        ticket: dict[str, Any],
        field_map: dict[str, str],
        config: dict[str, Any],
    ) -> dict[str, Any] | None:
        """Map a Zendesk ticket to a canonical signal dict.

        Uses field_map to extract: text, external_id, recorded_at,
        customer_id, tags. Falls back to sensible defaults.
        """
        text_key = field_map.get("text", "description")
        ext_id_key = field_map.get("external_id", "id")
        recorded_at_key = field_map.get("recorded_at", "created_at")
        customer_id_key = field_map.get("customer_id", "requester_id")
        tags_key = field_map.get("tags", "tags")

        text = str(ticket.get(text_key, "") or "").strip()
        if not text:
            return None

        external_id = str(ticket.get(ext_id_key, ""))
        recorded_at = str(ticket.get(recorded_at_key, ""))
        customer_id = str(ticket.get(customer_id_key, "unknown"))
        tags_raw = ticket.get(tags_key, [])
        tags = tags_raw if isinstance(tags_raw, list) else []

        # Determine journey/stage from tags or subject
        subject = str(ticket.get("subject", "") or "")
        journey = "support"
        journey_stage = "general"
        if "billing" in tags or "billing" in subject.lower():
            journey = "billing"
            journey_stage = "payment"
        elif "onboarding" in tags or "onboarding" in subject.lower():
            journey = "onboarding"
            journey_stage = "setup"
        elif "bug" in tags or "bug" in subject.lower():
            journey = "product"
            journey_stage = "bug_report"

        return {
            "signal_id": f"zd-{external_id}",
            "customer_id": customer_id,
            "account_id": str(ticket.get("organization_id", "unknown")),
            "source": "zendesk",
            "journey": journey,
            "journey_stage": journey_stage,
            "campaign_exposure": [],
            "product_events": [],
            "feedback_text": text[:2000],  # cap for LLM context
            "language": "en",  # Zendesk doesn't reliably provide this
            "timestamp": recorded_at,
            "metadata": {
                "external_id": external_id,
                "source_id": config.get("source_id", "zendesk"),
                "subject": subject,
                "tags": tags,
                "priority": ticket.get("priority", ""),
                "status": ticket.get("status", ""),
                "imported": True,
            },
        }


def _to_unix(timestamp: str) -> int:
    """Convert an ISO timestamp to Unix seconds for Zendesk incremental API."""
    try:
        dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        return int(dt.timestamp())
    except (ValueError, AttributeError):
        return 0
