"""Connector admin routes: config CRUD, manual source pull, connectivity test."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.rbac import Role, require_role

# Connector config keys whose values are secrets and must never be returned to clients.
_SECRET_CONFIG_KEYS = {
    "api_key",
    "refresh_token",
    "client_secret",
    "service_account_json",
    "api_token",
    "bot_token",
    "token",
    "secret",
    "password",
    "access_token",
}


def redacted_connector_config(connector) -> dict:
    """Serialize a ConnectorConfig with secret credential values masked."""
    data = connector.model_dump()
    config = data.get("config")
    if isinstance(config, dict):
        data["config"] = {
            key: ("***redacted***" if key in _SECRET_CONFIG_KEYS and value else value)
            for key, value in config.items()
        }
    return data


def build_router(
    *,
    connector_config_store,
    pull_source_and_import,
) -> APIRouter:
    router = APIRouter()

    @router.get("/connectors", dependencies=[Depends(require_role(Role.admin))])
    def list_connectors() -> list[dict]:
        return [redacted_connector_config(c) for c in connector_config_store.list_configs()]

    @router.put("/connectors/{connector_type}", dependencies=[Depends(require_role(Role.admin))])
    def upsert_connector(
        connector_type: str,
        config: dict,
    ) -> dict:
        from app.connectors.config_store import ConnectorConfig

        existing = connector_config_store.get_config(connector_type)
        display_name = config.pop("_display_name", existing.display_name if existing else "")
        # Preserve stored secrets when the client sends a blank or masked placeholder
        # (the GET endpoint redacts secrets, so edit forms never carry the real value).
        if existing:
            for key in _SECRET_CONFIG_KEYS:
                incoming = config.get(key)
                if (not incoming or incoming == "***redacted***") and key in existing.config:
                    config[key] = existing.config[key]
        stored_cfg = ConnectorConfig(
            connector_type=connector_type,
            config=config,
            display_name=display_name,
        )
        connector_config_store.upsert_config(stored_cfg)
        return {"connector_type": connector_type, "status": "saved"}

    @router.delete("/connectors/{connector_type}", dependencies=[Depends(require_role(Role.admin))])
    def delete_connector(connector_type: str) -> dict:
        deleted = connector_config_store.delete_config(connector_type)
        if not deleted:
            raise HTTPException(status_code=404, detail="Connector not found")
        return {"connector_type": connector_type, "status": "deleted"}

    @router.post("/connectors/{connector_type}/pull", dependencies=[Depends(require_role(Role.admin))])
    def pull_source(connector_type: str, config: dict | None = None) -> dict:
        """Pull + import signals from any registered source connector
        (zendesk, app_store, ...). Uses the stored config when no body is given."""
        return pull_source_and_import(connector_type, config)

    @router.post("/connectors/test/{connector_type}", dependencies=[Depends(require_role(Role.admin))])
    def test_connector(connector_type: str, config: dict) -> dict:
        """Test a connector configuration without saving it."""
        from app.connectors import get_destination, get_source
        from app.connectors.base import ConnectorError

        if connector_type in ("zendesk",):
            src = get_source(connector_type)
            if src is None:
                raise HTTPException(status_code=400, detail="Unknown source connector")
            try:
                signals = src.pull(config)
                return {"status": "ok", "pulled": len(signals)}
            except ConnectorError as exc:
                return {"status": "error", "message": str(exc)}

        if connector_type in ("jira", "slack"):
            dest = get_destination(connector_type)
            if dest is None:
                raise HTTPException(status_code=400, detail="Unknown destination connector")
            # For testing, send a minimal test action
            test_action = {
                "type": "create_ticket" if connector_type == "jira" else "notify",
                "title": "CLARA connector test",
                "description": "This is a test from the CLARA platform.",
                "priority": 3,
                "insight_title": "Test",
                "insight_summary": "Connector configuration test",
                "insight_severity": "low",
            }
            try:
                result = dest.push(test_action, config)
                return {"status": "ok", "result": result}
            except ConnectorError as exc:
                return {"status": "error", "message": str(exc)}

        raise HTTPException(status_code=400, detail=f"Unknown connector type: {connector_type}")

    return router
