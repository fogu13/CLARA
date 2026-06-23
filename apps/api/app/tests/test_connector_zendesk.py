"""Tests for the Zendesk source connector — ticket pull + field mapping."""

from __future__ import annotations

import base64
from typing import Any

import pytest


def _zendesk_tickets_response(tickets: list[dict[str, Any]]) -> dict[str, Any]:
    return {"tickets": tickets}


def _make_ticket(
    ticket_id: int = 123,
    *,
    subject: str = "Checkout page broken",
    description: str = "The checkout page crashes when I try to pay.",
    tags: list[str] | None = None,
    priority: str = "urgent",
    status: str = "open",
) -> dict[str, Any]:
    return {
        "id": ticket_id,
        "subject": subject,
        "description": description,
        "tags": tags or ["checkout", "bug"],
        "priority": priority,
        "status": status,
        "requester_id": 5001,
        "organization_id": 200,
        "created_at": "2026-06-23T10:00:00Z",
        "updated_at": "2026-06-23T11:00:00Z",
    }


class TestZendeskPull:
    def test_pulls_and_maps_tickets(self, httpx_mock: Any) -> None:
        from app.connectors.zendesk import ZendeskSourceConnector

        httpx_mock.add_response(
            url="https://company.zendesk.com/api/v2/tickets.json?per_page=100",
            method="GET",
            json=_zendesk_tickets_response([_make_ticket(101), _make_ticket(102)]),
        )

        connector = ZendeskSourceConnector()
        signals = connector.pull({
            "subdomain": "company",
            "email": "user@company.com",
            "api_token": "secret-token",
        })

        assert len(signals) == 2
        assert signals[0]["signal_id"] == "zd-101"
        assert signals[0]["source"] == "zendesk"
        assert "checkout page crashes" in signals[0]["feedback_text"]
        assert signals[0]["customer_id"] == "5001"
        assert signals[0]["metadata"]["external_id"] == "101"

    def test_uses_basic_auth_header(self, httpx_mock: Any) -> None:
        from app.connectors.zendesk import ZendeskSourceConnector

        httpx_mock.add_response(
            url="https://company.zendesk.com/api/v2/tickets.json?per_page=100",
            method="GET",
            json=_zendesk_tickets_response([_make_ticket()]),
        )

        connector = ZendeskSourceConnector()
        connector.pull({
            "subdomain": "company",
            "email": "user@company.com",
            "api_token": "secret-token",
        })

        request = httpx_mock.get_requests()[-1]
        auth_header = request.headers.get("authorization", "")
        assert auth_header.startswith("Basic ")
        decoded = base64.b64decode(auth_header.removeprefix("Basic ")).decode()
        assert decoded == "user@company.com/token:secret-token"

    def test_raises_on_missing_credentials(self) -> None:
        from app.connectors.base import ConnectorError
        from app.connectors.zendesk import ZendeskSourceConnector

        connector = ZendeskSourceConnector()
        with pytest.raises(ConnectorError) as exc_info:
            connector.pull({"subdomain": "company"})

        assert "Missing Zendesk credentials" in str(exc_info.value)

    def test_raises_on_auth_failure(self, httpx_mock: Any) -> None:
        from app.connectors.base import ConnectorError
        from app.connectors.zendesk import ZendeskSourceConnector

        httpx_mock.add_response(
            url="https://company.zendesk.com/api/v2/tickets.json?per_page=100",
            method="GET",
            status_code=401,
            text="Unauthorized",
        )

        connector = ZendeskSourceConnector()
        with pytest.raises(ConnectorError) as exc_info:
            connector.pull({
                "subdomain": "company",
                "email": "user@company.com",
                "api_token": "wrong-token",
            })

        assert "auth failed" in str(exc_info.value).lower()

    def test_raises_on_rate_limit(self, httpx_mock: Any) -> None:
        from app.connectors.base import ConnectorError
        from app.connectors.zendesk import ZendeskSourceConnector

        httpx_mock.add_response(
            url="https://company.zendesk.com/api/v2/tickets.json?per_page=100",
            method="GET",
            status_code=429,
            text="Rate limited",
        )

        connector = ZendeskSourceConnector()
        with pytest.raises(ConnectorError) as exc_info:
            connector.pull({
                "subdomain": "company",
                "email": "user@company.com",
                "api_token": "token",
            })

        assert "rate limit" in str(exc_info.value).lower()

    def test_returns_empty_for_no_tickets(self, httpx_mock: Any) -> None:
        from app.connectors.zendesk import ZendeskSourceConnector

        httpx_mock.add_response(
            url="https://company.zendesk.com/api/v2/tickets.json?per_page=100",
            method="GET",
            json={"tickets": []},
        )

        connector = ZendeskSourceConnector()
        signals = connector.pull({
            "subdomain": "company",
            "email": "user@company.com",
            "api_token": "token",
        })

        assert signals == []

    def test_skips_tickets_without_text(self, httpx_mock: Any) -> None:
        from app.connectors.zendesk import ZendeskSourceConnector

        tickets = [
            _make_ticket(1, description="Has feedback"),
            _make_ticket(2, description=""),
        ]
        httpx_mock.add_response(
            url="https://company.zendesk.com/api/v2/tickets.json?per_page=100",
            method="GET",
            json=_zendesk_tickets_response(tickets),
        )

        connector = ZendeskSourceConnector()
        signals = connector.pull({
            "subdomain": "company",
            "email": "user@company.com",
            "api_token": "token",
        })

        assert len(signals) == 1
        assert signals[0]["signal_id"] == "zd-1"

    def test_determines_journey_from_tags(self, httpx_mock: Any) -> None:
        from app.connectors.zendesk import ZendeskSourceConnector

        tickets = [
            _make_ticket(1, subject="Billing issue", tags=["billing"], description="Payment failed"),
            _make_ticket(2, subject="Onboarding help", tags=["onboarding"], description="Can't set up"),
            _make_ticket(3, subject="Bug report", tags=["bug"], description="App crashes"),
        ]
        httpx_mock.add_response(
            url="https://company.zendesk.com/api/v2/tickets.json?per_page=100",
            method="GET",
            json=_zendesk_tickets_response(tickets),
        )

        connector = ZendeskSourceConnector()
        signals = connector.pull({
            "subdomain": "company",
            "email": "user@company.com",
            "api_token": "token",
        })

        assert signals[0]["journey"] == "billing"
        assert signals[1]["journey"] == "onboarding"
        assert signals[2]["journey"] == "product"

    def test_incremental_pull_uses_cursor_endpoint(self, httpx_mock: Any) -> None:
        from app.connectors.zendesk import ZendeskSourceConnector

        httpx_mock.add_response(
            url="https://company.zendesk.com/api/v2/incremental/tickets/cursor.json?start_time=1719100800",
            method="GET",
            json=_zendesk_tickets_response([_make_ticket(999)]),
        )

        connector = ZendeskSourceConnector()
        signals = connector.pull({
            "subdomain": "company",
            "email": "user@company.com",
            "api_token": "token",
            "last_synced_at": "2024-06-23T00:00:00Z",
        })

        assert len(signals) == 1
        assert signals[0]["signal_id"] == "zd-999"
