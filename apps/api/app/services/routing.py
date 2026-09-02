"""Team owner routing — the pitch's "each theme goes to the team that owns it".

A workspace declares ``OwnerRoute`` rules (Settings → Teams): a journey stage or
AI theme substring maps to an owning team and, optionally, to that team's own
Jira project or Slack channel. Routing stays deterministic and inspectable —
no model decides who owns a problem — and falls back to the built-in
``owner_for_stage`` defaults when no rule matches.
"""

from __future__ import annotations

from collections.abc import Iterable

from app.domain.models import OwnerRoute


def _norm(value: str | None) -> str:
    return (value or "").replace("_", " ").strip().lower()


def route_matches(route: OwnerRoute, *keys: str | None) -> bool:
    needle = _norm(route.match)
    if not needle:
        return False
    return any(needle in _norm(key) for key in keys if key)


def resolve_owner_route(routes: Iterable[OwnerRoute], *keys: str | None) -> OwnerRoute | None:
    """First route whose ``match`` is a substring of any key (stage, theme tag)."""
    for route in routes:
        if route_matches(route, *keys):
            return route
    return None


def resolve_owner(routes: Iterable[OwnerRoute], *keys: str | None, default: str) -> str:
    route = resolve_owner_route(routes, *keys)
    return route.owner if route is not None else default


def route_for_owner(routes: Iterable[OwnerRoute], owner: str | None) -> OwnerRoute | None:
    """The route declared for a team, used to pick that team's tool settings."""
    if not owner:
        return None
    wanted = _norm(owner)
    for route in routes:
        if _norm(route.owner) == wanted:
            return route
    return None


def connector_overrides(route: OwnerRoute | None, destination: str) -> dict[str, str]:
    """Per-team connector settings layered over the workspace connector config.

    Only the fields a team can legitimately own are overridable — never
    credentials — so a route can send a team's tickets to its own Jira project
    or its own Slack channel while the workspace keeps one set of secrets.
    """
    if route is None:
        return {}
    if destination == "jira" and route.jira_project_key:
        return {"project_key": route.jira_project_key}
    if destination == "slack" and route.slack_channel:
        return {"channel": route.slack_channel}
    return {}
