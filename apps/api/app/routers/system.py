"""System + settings routes: health, ask, API keys, telemetry, CSV export, workspace, AI endpoint config."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response

import app.services.ai as ai
from app.auth import UserContext, get_current_user
from app.domain.models import SystemConfig, WorkspaceSettings
from app.rate_limit import rate_limiter
from app.rbac import Role, can_admin, require_role
from app.routers.problems import build_outcome_board, to_summary
from app.services.postgres import EXPECTED_MEASUREMENT_FUNCTION_VERSION


def build_identity() -> str | None:
    """The commit the running build was made from: CLARA_BUILD_COMMIT (set by
    the Dockerfile from its GIT_COMMIT build arg), else CLARA_VERSION, else
    None — never invented from the checkout the process happens to run in."""
    import os

    return os.getenv("CLARA_BUILD_COMMIT") or os.getenv("CLARA_VERSION") or None


def measurement_compatibility(database: object) -> dict[str, object]:
    """Fold the database's measurement state into one verdict.

    compatible    the plpgsql tick is at the version this code expects and the
                  plan columns exist (or the backend runs the Python tick)
    fallback      no plpgsql tick at all: the API runs its Python tick, which
                  has the same semantics — safe, but pg_cron does nothing
    incompatible  a plpgsql tick exists at another (older) version, or plan
                  columns are missing: checkpoints could be read with older
                  semantics — apply the pending migration
    unknown       the database probe failed or answered nothing
    """
    verdict: dict[str, object] = {
        "state": "unknown",
        "expected_function_version": EXPECTED_MEASUREMENT_FUNCTION_VERSION,
        "found_function_version": None,
        "columns_missing": [],
        "backend_tick": None,
        "action": "check DATABASE_URL and the database (the readiness probe failed)",
    }
    if not isinstance(database, dict) or not database.get("ok"):
        return verdict
    measurement = database.get("measurement")
    if not isinstance(measurement, dict):
        return verdict
    found = measurement.get("function_version")
    missing = list(measurement.get("columns_missing") or [])
    backend_tick = measurement.get("backend_tick")
    if backend_tick == "python" and database.get("backend") != "postgres":
        state = "compatible"
    elif backend_tick == "python":
        state = "fallback"
    elif found == EXPECTED_MEASUREMENT_FUNCTION_VERSION and not missing:
        state = "compatible"
    else:
        state = "incompatible"
    verdict.update(
        state=state,
        found_function_version=found,
        columns_missing=missing,
        backend_tick=backend_tick,
        action=(
            None
            if state == "compatible"
            else "apply apps/api/migrations/017_measurement_intervals.sql (see DEPLOY.md release step)"
        ),
    )
    return verdict


def build_router(
    *,
    signal_store,
    active_problem_store,
    workflow_store,
    workspace_store,
    api_key_store,
    telemetry_store,
    connector_config_store,
    enrich_problem_for_response,
    readiness_check=None,
    measurement_plan_store=None,
) -> APIRouter:
    router = APIRouter()
    read_dep = Depends(require_role(Role.viewer))

    @router.get("/health")
    def health() -> dict[str, str | None]:
        """Shallow liveness probe: the process is up. Cheap by design (Caddy,
        Docker HEALTHCHECK and the uptime workflow hit it every few seconds).
        Carries the build identity (CLARA_BUILD_COMMIT, baked into the image
        by the Dockerfile) so a smoke run can say WHICH build answered — a
        FastAPI-shaped 404 on a newer route proves version lag only when the
        served commit is known."""
        return {"status": "ok", "version": build_identity()}

    def _readiness_report() -> tuple[bool, dict[str, object]]:
        checks: dict[str, object] = {}
        healthy = True
        if readiness_check is not None:
            try:
                checks["database"] = readiness_check()
            except Exception as exc:  # noqa: BLE001 — the probe must answer, not crash
                healthy = False
                checks["database"] = {"ok": False, "error": type(exc).__name__}
        checks["measurement"] = measurement_compatibility(checks.get("database"))
        checks["ai_residency"] = {
            "chat": ai.provider_residency(ai.effective_base_url()),
            "embeddings": ai.provider_residency(ai.effective_embed_base_url()),
            "eu_only_enforced": ai.eu_only_enforced(),
        }
        checks["build"] = {"version": build_identity()}
        return healthy, checks

    @router.get("/ready")
    def ready(response: Response) -> dict[str, object]:
        """Readiness: can this instance serve requests? Runs the persistence
        probe (SELECT 1 against Postgres, or the SQLite file) and answers 503
        when it fails, so a load balancer stops routing to a broken instance.
        Unauthenticated, therefore minimal: status, the build identity and one
        word for the measurement schema (compatible | fallback | incompatible
        | unknown) — a schema mismatch is reported, never used to take the
        instance out of rotation; backend type, error classes, versions and
        the residency posture are on /ready/details for signed-in users."""
        healthy, checks = _readiness_report()
        if not healthy:
            response.status_code = 503
        measurement = checks.get("measurement") or {}
        return {
            "status": "ok" if healthy else "degraded",
            "version": build_identity(),
            "measurement_schema": measurement.get("state", "unknown"),
        }

    @router.get("/ready/details", dependencies=[read_dep])
    def ready_details(response: Response) -> dict[str, object]:
        """The full readiness report: database probe result, the measurement
        schema/function compatibility (expected vs found function version,
        missing plan columns, which tick runs), the build identity and the AI
        residency classification of the configured providers."""
        healthy, checks = _readiness_report()
        if not healthy:
            response.status_code = 503
        return {"status": "ok" if healthy else "degraded", "checks": checks}

    @router.post("/ask", dependencies=[read_dep, Depends(rate_limiter)])
    def ask_clara_endpoint(body: dict) -> dict:
        """Grounded Q&A over the workspace's signals; citations, confidence,
        and an explicit refusal when the evidence is thin. No chat memory."""
        from app.services import ai as ai_module
        from app.services.ask import ask_clara

        question = (body.get("question") or "").strip()
        if not question:
            raise HTTPException(status_code=422, detail="question is required")
        if len(question) > 500:
            raise HTTPException(status_code=422, detail="question must be under 500 characters")

        try:
            result = ask_clara(question, signal_store.list_signals())
        except ai_module.AIProviderError as exc:
            # "AI provider unavailable" was the same four words for a bad model
            # name, an expired key and an exhausted quota — it sent people to
            # the provider's status page when the fix was in their own env.
            raise HTTPException(
                status_code=502, detail=ai_module.provider_error_detail(exc)
            ) from exc

        telemetry_store.record(
            "question_asked",
            metadata={
                "refused": result["refused"],
                "matches": result.get("matches", 0),
                "confidence": result.get("confidence", 0.0),
            },
        )
        return result

    @router.post("/api-keys", dependencies=[Depends(require_role(Role.admin))])
    def create_api_key(body: dict) -> dict:
        """Mint an API key. The plaintext is returned ONCE and never stored."""
        role = str(body.get("role", "viewer"))
        try:
            record, plaintext = api_key_store.create_key(
                name=str(body.get("name", "")), role=role
            )
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        telemetry_store.record("api_key_created", entity_id=str(record["id"]), metadata={"role": role})
        return {**record, "key": plaintext}

    @router.get("/api-keys", dependencies=[Depends(require_role(Role.admin))])
    def list_api_keys() -> list[dict]:
        return api_key_store.list_keys()

    @router.delete("/api-keys/{key_id}", dependencies=[Depends(require_role(Role.admin))])
    def revoke_api_key(key_id: int) -> dict:
        if not api_key_store.revoke(key_id):
            raise HTTPException(status_code=404, detail="Key not found or already revoked")
        telemetry_store.record("api_key_revoked", entity_id=str(key_id))
        return {"revoked": key_id}

    @router.get("/telemetry", dependencies=[Depends(require_role(Role.admin))])
    def get_telemetry(limit: int = 200) -> dict:
        """Product-metric events (admin): counts by type + recent events.

        Powers the pilot/VC metrics: time-to-first-insight, approval-cycle time,
        outcome-completion rate, learning-reuse rate. Data never leaves this DB.
        """
        return {
            "counts": telemetry_store.counts_by_type(),
            "events": telemetry_store.list_events(limit=min(limit, 1000)),
        }

    @router.get("/export/{entity}.csv", dependencies=[Depends(require_role(Role.admin))])
    def export_entity_csv(entity: str):
        """BI-friendly CSV exports (warehouse EXPORT, not sync): signals,
        problems, outcomes, telemetry. Cells are formula-injection-neutralized."""
        from fastapi.responses import PlainTextResponse

        from app.services import exports

        builders = {
            "signals": lambda: exports.signals_csv(signal_store.list_signals()),
            "problems": lambda: exports.problems_csv(
                [to_summary(enrich_problem_for_response(p)) for p in active_problem_store.list_problems()]
            ),
            # With plans the board carries loop verdicts (measuring / loop_closed /
            # fix_did_not_land); without them every row exported as not_measured.
            "outcomes": lambda: exports.outcomes_csv(
                build_outcome_board(
                    active_problem_store.list_problems(),
                    workflow_store,
                    plans=measurement_plan_store.list_plans() if measurement_plan_store else None,
                )
            ),
            "telemetry": lambda: exports.telemetry_csv(telemetry_store.list_events(limit=1000)),
        }
        builder = builders.get(entity)
        if builder is None:
            raise HTTPException(
                status_code=404,
                detail=f"Unknown export '{entity}'. Available: {', '.join(sorted(builders))}",
            )
        telemetry_store.record("csv_exported", metadata={"entity": entity})
        return PlainTextResponse(
            builder(),
            media_type="text/csv; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename="clara-{entity}.csv"'},
        )

    @router.get("/workspace", response_model=WorkspaceSettings, dependencies=[read_dep])
    def get_workspace(user: UserContext = Depends(get_current_user)) -> WorkspaceSettings:  # noqa: B008
        return workspace_store.get(user.workspace_id)

    # Governance-bearing settings: an editor toggling works_council_mode off
    # would defeat the §87 BetrVG control it exists for, and blanking the
    # disclosure template silently disables the Art. 50 line.
    # owner_routes decide where approved work is pushed (Jira project / Slack
    # channel), so they are admin-only too.
    ADMIN_ONLY_SETTINGS = (
        "works_council_mode",
        "ai_disclosure_template",
        "four_eyes_approval",
        "owner_routes",
    )

    @router.put(
        "/workspace",
        response_model=WorkspaceSettings,
        dependencies=[Depends(require_role(Role.editor))],
    )
    def update_workspace(
        settings: WorkspaceSettings,
        user: UserContext = Depends(get_current_user),  # noqa: B008
    ) -> WorkspaceSettings:
        stored = workspace_store.get(user.workspace_id)
        # Merge semantics: fields absent from the request keep their stored
        # values, so a stale settings tab cannot wipe flags or attestations
        # written elsewhere (full-object PUT lost-update).
        merged = stored.model_copy(
            update={
                name: getattr(settings, name)
                for name in settings.model_fields_set
                if name in WorkspaceSettings.model_fields
            }
        )
        if not can_admin(user):
            changed = [
                name
                for name in ADMIN_ONLY_SETTINGS
                if getattr(merged, name) != getattr(stored, name)
            ]
            if changed:
                raise HTTPException(
                    status_code=403,
                    detail=f"Changing {', '.join(changed)} requires the admin role",
                )
        return workspace_store.put(user.workspace_id, merged)

    @router.put("/settings/ai", dependencies=[Depends(require_role(Role.admin))])
    def update_ai_settings(body: dict) -> dict:
        """Point CLARA at any OpenAI-compatible endpoint (cloud or local) at
        runtime. Empty api_key keeps the previously stored key; empty base_url/
        model/embed_model fall back to the server env. The key is stored like
        every other connector secret and redacted on read."""
        from app.connectors.config_store import ConnectorConfig

        stored = connector_config_store.get_config("ai")
        base_url = str(body.get("base_url") or "").strip()
        model = str(body.get("model") or "").strip()
        embed_model = str(body.get("embed_model") or "").strip()
        api_key = str(body.get("api_key") or "").strip()
        if base_url and not base_url.startswith(("http://", "https://")):
            raise HTTPException(status_code=422, detail="base_url must be http(s)")
        # EU-only mode: refuse to point the product at a non-EU provider from
        # the GUI too — the boot check alone would let a runtime override slip.
        if base_url:
            try:
                ai.assert_residency_allowed(base_url, purpose="AI endpoint")
            except ai.ResidencyViolation as exc:
                raise HTTPException(status_code=422, detail=str(exc)) from exc
        # Edit forms may echo the masked value from the redacted read path back.
        if api_key == "***redacted***":
            api_key = ""
        if not api_key and stored:
            api_key = stored.config.get("api_key", "")

        config = {
            "base_url": base_url,
            "model": model,
            "embed_model": embed_model,
            "api_key": api_key,
        }
        connector_config_store.upsert_config(
            ConnectorConfig(connector_type="ai", config=config, display_name="AI endpoint")
        )
        ai.set_runtime_config(
            base_url=base_url, model=model, api_key=api_key, embed_model=embed_model
        )
        telemetry_store.record("ai_config_changed", metadata={"base_url": base_url or "env", "model": model or "env"})
        result = {
            "ai_base_url": ai.effective_base_url(),
            "ai_model": ai.effective_model(),
            "ai_embed_model": ai.effective_embed_model(),
            "key_set": bool(ai.effective_api_key()),
        }
        if base_url and not api_key and ai.effective_api_key():
            # The env fallback key almost certainly belongs to a DIFFERENT
            # provider than the freshly configured endpoint — a silent 401 trap.
            result["warning"] = (
                "No API key saved for this endpoint; the server's environment "
                "key will be sent instead."
            )
        return result

    @router.post("/settings/ai/test", dependencies=[Depends(require_role(Role.admin))])
    def test_ai_settings() -> dict:
        """One tiny completion + one tiny embedding against the EFFECTIVE
        endpoint - proves the pasted config works before anyone trusts triage
        to it. Ask/taxonomy need embeddings, so a chat-only green would lie."""
        try:
            result = ai.call_tool(
                system="Reply by calling the tool.",
                user="ping",
                tool_name="pong",
                tool={
                    "type": "function",
                    "function": {
                        "name": "pong",
                        "description": "Acknowledge the ping.",
                        "parameters": {
                            "type": "object",
                            "properties": {"ok": {"type": "boolean"}},
                            "required": ["ok"],
                        },
                    },
                },
                timeout=30.0,
            )
        except ai.AIProviderError as exc:
            return {"ok": False, "model": ai.effective_model(), "error": str(exc)[:300]}

        response = {"ok": True, "model": ai.effective_model(), "echo": result}
        try:
            ai.embed("ping", timeout=30.0)
            response["embed_ok"] = True
        except ai.AIProviderError as exc:
            response["embed_ok"] = False
            response["embed_model"] = ai.effective_embed_model()
            response["embed_error"] = str(exc)[:300]
        return response

    @router.get("/model-card/metrics", dependencies=[read_dep])
    def model_card_metrics() -> dict:
        """Published evaluation metrics for the model card (/compliance).

        Serves the committed snapshot written by `run_live --publish` — real
        numbers with denominators and dataset date, never live-computed, so
        what buyers see is exactly what was measured and signed off.
        """
        import json as _json
        from pathlib import Path

        path = Path(__file__).parents[1] / "evals" / "published_metrics.json"
        if not path.exists():
            return {"published": False}
        return {"published": True, **_json.loads(path.read_text())}

    @router.get("/system-config", response_model=SystemConfig, dependencies=[read_dep])
    def get_system_config() -> SystemConfig:
        from app.auth import AUTH_ENABLED

        return SystemConfig(
            ai_base_url=ai.effective_base_url(),
            ai_model=ai.effective_model(),
            ai_embed_model=ai.effective_embed_model(),
            ai_embed_base_url=ai.effective_embed_base_url(),
            ai_residency=ai.provider_residency(ai.effective_base_url()),
            ai_embed_residency=ai.provider_residency(ai.effective_embed_base_url()),
            eu_only_enforced=ai.eu_only_enforced(),
            auth_enabled=AUTH_ENABLED,
        )

    return router
