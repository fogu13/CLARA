"""Connector interface; sources (pull) and destinations (push).

First connectors to prove the brief's headline
("connects to sources ... pushes insights to other platforms"):
  - Zendesk source (pull): tickets/search -> signals via field map
  - Jira destination (push): create issue behind governance gate
  - Slack destination (push): chat.postMessage notify action

Reuses Elvis's api_poll field-mapping design
(reference/elvis/supabase/functions/sync-source/index.ts:79-160)
and replaces CLARA_2's local-only JiraIssueDraft
(apps/api/app/services/workflow.py:125-142).
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class SourceConnector(Protocol):
    """Pulls customer signals from an external system into the signal store."""

    connector_type: str  # e.g. "zendesk"

    def pull(self, config: dict[str, Any]) -> list[dict[str, Any]]:
        """Fetch new items and map them to canonical signal dicts.

        Returns a list of signal dicts aligned with SignalRecord fields
        (signal_id, customer_id, account_id, source, journey, journey_stage,
        feedback_text, language, timestamp) plus a metadata block for
        deduplication (external_id, source_id).
        """
        ...


@runtime_checkable
class DestinationConnector(Protocol):
    """Pushes an approved action to an external system (close the loop)."""

    connector_type: str  # e.g. "jira", "slack"

    def push(self, action: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
        """Execute the action externally and return a result record:
        {external_id, status, raw, audit}.
        Called only after governance approval.
        """
        ...


class ConnectorError(RuntimeError):
    """Base error for connector failures. Non-fatal; logged, not raised."""

    def __init__(self, message: str, connector: str = "", status: int | None = None) -> None:
        super().__init__(message)
        self.connector = connector
        self.status = status


import ipaddress  # noqa: E402
from urllib.parse import urlparse  # noqa: E402

_BLOCKED_HOSTNAMES = {"localhost", "metadata.google.internal", "metadata"}


def validate_external_url(url: str, *, connector: str = "") -> str:
    """SSRF guard for user-supplied connector URLs.

    Rejects non-http(s) schemes and hosts that are internal/private/metadata
    IP literals (169.254.169.254, 127.x, 10.x, 192.168.x, ::1, …) or obvious
    internal hostnames. Returns the URL if it passes.

    # ponytail: literal IP + hostname blocklist, no DNS resolution — blocks the
    # direct SSRF vectors (private-IP/localhost/cloud-metadata base_url) without
    # network I/O in tests. It does NOT stop DNS-rebinding or a public domain that
    # resolves internally; add a resolve-time check + pinned resolver if these
    # connectors ever become non-admin-facing.
    """
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise ConnectorError(f"URL scheme '{parsed.scheme}' not allowed", connector=connector)
    host = (parsed.hostname or "").lower()
    if not host:
        raise ConnectorError("URL has no host", connector=connector)
    if host in _BLOCKED_HOSTNAMES or host.endswith((".local", ".internal")):
        raise ConnectorError(f"URL host '{host}' is not allowed", connector=connector)
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        ip = None
    if ip is not None and (
        ip.is_private or ip.is_loopback or ip.is_link_local
        or ip.is_reserved or ip.is_multicast or ip.is_unspecified
    ):
        raise ConnectorError(f"URL host '{host}' resolves to a blocked address", connector=connector)
    return url
