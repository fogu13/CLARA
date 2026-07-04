"""Measurement + alerting routes: checkpoint plans, due-run trigger, alert sweep, digest."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.rbac import Role, require_role
from app.routers.problems import build_outcome_board
from app.services.emerging import build_emerging_problem_report


def build_router(
    *,
    measurement_plan_store,
    telemetry_store,
    connector_config_store,
    active_problem_store,
    workflow_store,
    run_due_measurements,
    run_alert_sweep,
    current_candidates,
) -> APIRouter:
    router = APIRouter()
    read_dep = Depends(require_role(Role.viewer))

    @router.get("/measurements", dependencies=[read_dep])
    def list_measurement_plans() -> list[dict]:
        """Scheduled outcome re-measurement checkpoints (pending/done/manual_required)."""
        return measurement_plan_store.list_plans()

    @router.post("/measurements/run-due", dependencies=[Depends(require_role(Role.editor))])
    def run_due_measurement_plans(body: dict | None = None) -> dict:
        """Process due checkpoints now (the background loop does this every 15 min).

        Optional body {"now": "<iso>"} lets demos/tests advance the clock.
        """
        requested_now = (body or {}).get("now")
        if requested_now is not None:
            from datetime import datetime

            try:
                datetime.fromisoformat(str(requested_now).replace("Z", "+00:00"))
            except ValueError as exc:
                raise HTTPException(status_code=422, detail="'now' must be ISO 8601") from exc
            # Explicit clock overrides stay allowed (tests/demos time-travel),
            # but the honesty-critical outcome loop records them for audit.
            telemetry_store.record(
                "measurement_clock_override", metadata={"now": str(requested_now)}
            )
        return run_due_measurements(now=requested_now)

    @router.post("/digest/slack", dependencies=[Depends(require_role(Role.admin))])
    def send_slack_digest() -> dict:
        """Build the weekly digest and push it to the configured Slack channel.

        Trigger from an external cron (weekly) or manually. Without an active
        Slack connector this still returns the digest text as a preview.
        """
        from app.connectors import get_destination
        from app.connectors.base import ConnectorError
        from app.services.digest import build_digest

        digest_text = build_digest(
            emerging=build_emerging_problem_report(current_candidates()),
            outcome_board=build_outcome_board(active_problem_store.list_problems(), workflow_store),
            measurement_plans=measurement_plan_store.list_plans(),
        )

        slack_config = connector_config_store.get_config("slack")
        if slack_config is None or not slack_config.is_active:
            return {"pushed": False, "reason": "No active Slack connector", "preview": digest_text}

        connector = get_destination("slack")
        try:
            result = connector.push(
                {"title": "CLARA weekly digest", "description": digest_text},
                slack_config.config,
            )
        except ConnectorError as exc:
            return {"pushed": False, "reason": str(exc)[:200], "preview": digest_text}

        telemetry_store.record("digest_sent", metadata={"channel": "slack"})
        return {"pushed": True, "external_id": result.get("external_id"), "preview": digest_text}

    @router.post("/alerts/run", dependencies=[Depends(require_role(Role.admin))])
    def run_alerts_now() -> dict:
        """Run the proactive alert sweep immediately (demo/testing; the
        background loop runs the same sweep hourly)."""
        return run_alert_sweep()

    return router
