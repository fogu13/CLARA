"""Works-council mode («Betriebsrat-Modus», §87(1) Nr. 6 BetrVG) — W1.

German works councils co-determine any system OBJECTIVELY capable of monitoring
employee behaviour or performance — intent is irrelevant per case law. CLARA's
audit trail, owner routing, approval records and per-approver stats qualify.
With the per-workspace `works_council_mode` flag on, routine (below-admin) read
responses replace person-capable identifier fields with fixed ROLE labels: the
audit chain stays intact (which role acted, when, on what), but no per-employee
metric can be derived. Admin+ keeps full identities (including /audit-export) —
the works-council agreement typically requires naming who holds that access.

ALL redaction policy lives in this module. Call sites only invoke `redact()`
(the response middleware below and the evidence-pack HTML path) or
`strip_redaction_sentinels()` (write routes whose payloads may round-trip a
redacted read); they never carry their own field lists or role rules.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from fastapi.concurrency import run_in_threadpool
from starlette.datastructures import MutableHeaders

from app.auth import (
    current_request_user,
    reset_current_request_user,
    set_current_request_user,
)
from app.rbac import ROLE_LEVEL, Role

logger = logging.getLogger(__name__)

# Person-capable field name -> fixed role label. Labels answer "which ROLE did
# this", never who: constants, not derived from the hidden value, so equal
# labels across records leak nothing.
REDACTED_FIELDS: dict[str, str] = {
    "reviewer": "approver",
    "reviewed_by": "approver",
    "actor": "editor",
    "owner": "owner",
    "assignee": "owner",
    "responsible_owner": "owner",
}

# Plural aggregations of the same person values (affected-context explorer);
# collapsed to a single label so neither names nor distinct-person counts leak.
REDACTED_LIST_FIELDS: dict[str, str] = {
    "owners": "owner",
    "product_owners": "owner",
}

ROLE_LABELS = frozenset(REDACTED_FIELDS.values())

K_ANONYMITY_FLOOR = 5


def _below_admin(role: str | None) -> bool:
    """True when the caller may NOT see person identities.

    Unknown/absent role counts as below admin — fail closed."""
    return ROLE_LEVEL.get(role or "", 0) < ROLE_LEVEL[Role.admin.value]


def redact(payload: Any, *, enabled: bool, role: str | None) -> Any:
    """Replace person-capable field values with role labels in a JSON structure.

    No-op unless `enabled` (the workspace's works_council_mode) and `role` is
    below admin. Deep-walks dicts/lists; only non-empty string values under
    REDACTED_FIELDS keys are replaced, everything else passes through
    untouched. Idempotent: a role label redacts to itself.
    """
    if not enabled or not _below_admin(role):
        return payload
    return _walk(payload)


def _walk(node: Any) -> Any:
    if isinstance(node, dict):
        return {key: _walk_value(key, value) for key, value in node.items()}
    if isinstance(node, list):
        return [_walk(item) for item in node]
    return node


def _walk_value(key: str, value: Any) -> Any:
    if key in REDACTED_FIELDS and isinstance(value, str) and value:
        return REDACTED_FIELDS[key]
    if (
        key in REDACTED_LIST_FIELDS
        and isinstance(value, list)
        and value
        and all(isinstance(item, str) for item in value)
    ):
        return [REDACTED_LIST_FIELDS[key]]
    return _walk(value)


def k_suppress(
    groups: list[dict], k: int = K_ANONYMITY_FLOOR, *, size_key: str = "count"
) -> list[dict]:
    """k-anonymity floor for per-person aggregate rows.

    Works-council design rule: a per-person aggregate (approval-cycle time per
    approver, actions/approver, override rates, ...) may only leave the API
    when EVERY group is at least k strong (default 5) — a smaller group
    re-identifies its members, so the WHOLE table is suppressed (returns []),
    never just the small rows (their absence would itself leak).

    No server-side per-person aggregate exists today (verified for W1:
    /telemetry and the CSV exports carry no user ids); any future one MUST be
    passed through this helper before serialization.
    """
    if any(int(group.get(size_key, 0) or 0) < k for group in groups):
        return []
    return list(groups)


def strip_redaction_sentinels(model: Any) -> Any:
    """Return a copy of a Pydantic update model with role-label values dropped
    from person-capable fields (set to None so the merge keeps stored values).

    A below-admin client that round-trips a redacted GET payload into a write
    (contract accept/edit, action or draft edits) would otherwise persist the
    literal label ("owner", "approver", ...) and destroy real attribution —
    for every viewer, including admins and the audit trail. Role labels are
    never legitimate person values, so this is safe with the mode off too.
    """
    overrides = {
        name: None
        for name in REDACTED_FIELDS
        if isinstance(getattr(model, name, None), str)
        and getattr(model, name) in ROLE_LABELS
    }
    return model.model_copy(update=overrides) if overrides else model


class WorksCouncilRedactionMiddleware:
    """Pure-ASGI response middleware: the single application choke point.

    Applies `redact()` to `application/json` bodies of 2xx responses on ALL
    methods when the request's workspace has works_council_mode on AND the
    caller's role is below admin — write echoes (POST /approvals, PATCH
    responses) reproduce the same person fields the GET surfaces carry.
    Non-2xx, HTML/CSV/streaming responses pass through untouched.

    Role/workspace come from the request-scoped ContextVar that
    `get_current_user` publishes (async dependency in the same task — pure-ASGI
    middleware sees its writes; a BaseHTTPMiddleware would not, its downstream
    runs in a separate task). The JWT is never re-parsed here. Workspace
    settings are fetched at most once per request, and only when the caller is
    below admin. Routes without the auth dependency have no role -> fail
    closed (redact), which is safe: those surfaces carry no person fields.

    The one JSON-adjacent surface this cannot cover is the evidence-pack HTML
    variant — the problems router redacts that pack at the source with the
    same `redact()` helper.
    """

    def __init__(self, app, get_settings) -> None:
        self.app = app
        self._get_settings = get_settings  # workspace_id -> WorkspaceSettings

    async def __call__(self, scope, receive, send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        token = set_current_request_user(None)  # reset per request; no leakage
        try:
            passthrough = False
            pending_start: dict | None = None
            body_parts: list[bytes] = []

            async def send_wrapper(message: dict) -> None:
                nonlocal passthrough, pending_start
                if message["type"] == "http.response.start":
                    if (
                        200 <= message["status"] < 300
                        and _content_type(message).startswith("application/json")
                        and await self._should_redact()
                    ):
                        # Hold the start message: content-length changes.
                        pending_start = message
                    else:
                        passthrough = True
                        await send(message)
                    return
                if message["type"] != "http.response.body" or passthrough:
                    await send(message)
                    return
                body_parts.append(message.get("body", b""))
                if message.get("more_body"):
                    return
                body = _redacted_body(b"".join(body_parts))
                headers = MutableHeaders(raw=pending_start["headers"])
                headers["content-length"] = str(len(body))
                await send(pending_start)
                await send({"type": "http.response.body", "body": body})

            await self.app(scope, receive, send_wrapper)
        finally:
            reset_current_request_user(token)

    async def _should_redact(self) -> bool:
        meta = current_request_user()
        role = meta[0] if meta else None
        if not _below_admin(role):
            return False  # admin+ always sees full identities; no settings hit
        workspace_id = meta[1] if meta else 1
        try:
            settings = await run_in_threadpool(self._get_settings, workspace_id)
        except Exception:  # noqa: BLE001 — unknown flag state must never leak identities
            logger.exception(
                "works_council: settings lookup failed for workspace %s; "
                "redacting response (fail closed)",
                workspace_id,
            )
            return True
        return bool(getattr(settings, "works_council_mode", False))


def _content_type(start_message: dict) -> str:
    for name, value in start_message.get("headers") or []:
        if name.decode("latin-1").lower() == "content-type":
            return value.decode("latin-1").lower()
    return ""


def _redacted_body(raw: bytes) -> bytes:
    try:
        payload = json.loads(raw)
    except ValueError:
        return raw  # declared JSON but unparseable; nothing key-shaped to leak
    redacted = _walk(payload)
    return json.dumps(redacted, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
