"""Ingestion routes: signals, webhook intake, journey events, customer context, demo datasets."""

from __future__ import annotations

import hashlib
import hmac
import json

from fastapi import APIRouter, Depends, HTTPException, Request

from app.domain.models import (
    CustomerContextCompletenessReport,
    CustomerContextCsvImportRequest,
    CustomerContextImportRequest,
    CustomerContextImportResult,
    CustomerContextRecord,
    CustomerContextValidationReport,
    DemoDatasetImportResult,
    DemoDatasetSummary,
    JourneyEventCsvImportRequest,
    JourneyEventImportRequest,
    JourneyEventImportResult,
    JourneyEventRecord,
    SignalCsvImportRequest,
    SignalImportRequest,
    SignalImportResult,
    SignalRecord,
    SignalValidationReport,
)
from app.rbac import Role, require_role
from app.services.contexts import (
    context_completeness_report,
    parse_context_csv,
    validate_context_csv,
)
from app.services.journeys import parse_journey_event_csv
from app.services.seed import to_demo_dataset_summary
from app.services.signals import (
    parse_signal_csv,
    signal_from_row,
    validate_signal_csv,
)

WEBHOOK_MAX_BODY_BYTES = 2 * 1024 * 1024  # 2 MB: far above real payloads, far below OOM


def build_router(
    *,
    signal_store,
    journey_event_store,
    context_store,
    telemetry_store,
    connector_config_store,
    demo_datasets,
) -> APIRouter:
    router = APIRouter()
    read_dep = Depends(require_role(Role.viewer))

    def require_demo_dataset(dataset_id: str):
        dataset = next(
            (
                dataset
                for dataset in demo_datasets
                if dataset.dataset_id == dataset_id
            ),
            None,
        )
        if dataset is None:
            raise HTTPException(status_code=404, detail="Demo dataset not found")

        return dataset

    @router.get("/signals", response_model=list[SignalRecord], dependencies=[read_dep])
    def list_signals() -> list[SignalRecord]:
        return signal_store.list_signals()

    @router.post("/signals/import", response_model=SignalImportResult, dependencies=[Depends(require_role(Role.editor))])
    def import_signals(request: SignalImportRequest) -> SignalImportResult:
        return signal_store.import_signals(request.signals)

    @router.post("/signals/import-csv", response_model=SignalImportResult, dependencies=[Depends(require_role(Role.editor))])
    def import_signal_csv(request: SignalCsvImportRequest) -> SignalImportResult:
        report = validate_signal_csv(
            request.csv_text,
            existing_signal_ids=signal_store.existing_signal_ids(),
        )
        if not report.valid:
            raise HTTPException(status_code=422, detail=report.model_dump(mode="json"))

        result = signal_store.import_signals(parse_signal_csv(request.csv_text))
        telemetry_store.record(
            "signals_imported",
            metadata={"source": "csv", "imported": result.imported, "skipped": result.skipped_duplicates},
        )
        return result

    @router.post("/ingest/webhook", response_model=SignalImportResult)
    async def ingest_webhook(request: Request) -> SignalImportResult:
        """Generic push ingestion: anything that can POST JSON can feed CLARA.

        Auth is the HMAC signature (X-Clara-Signature: sha256=<hex>) computed over
        the raw body with the shared secret from the "webhook" connector config —
        external systems don't hold user JWTs, so this route deliberately carries
        no role dependency. Body: {"signals": [{...flat fields...}]} or a bare list;
        rows get the same defaults/dedup/language handling as CSV import.
        """
        webhook_config = connector_config_store.get_config("webhook")
        secret = (webhook_config.config.get("secret") if webhook_config else "") or ""
        if webhook_config is None or not webhook_config.is_active or not secret:
            raise HTTPException(
                status_code=400,
                detail="No active webhook configured. set a secret via PUT /connectors/webhook",
            )

        # Cap the body BEFORE buffering it: this is the one unauthenticated data
        # route, so an oversized POST must be rejected cheaply, not hashed.
        content_length = request.headers.get("content-length")
        if content_length and content_length.isdigit() and int(content_length) > WEBHOOK_MAX_BODY_BYTES:
            raise HTTPException(status_code=413, detail="Payload too large")
        raw_body = await request.body()
        if len(raw_body) > WEBHOOK_MAX_BODY_BYTES:
            raise HTTPException(status_code=413, detail="Payload too large")
        expected = "sha256=" + hmac.new(secret.encode(), raw_body, hashlib.sha256).hexdigest()
        provided = request.headers.get("x-clara-signature", "")
        try:
            valid = hmac.compare_digest(expected, provided)
        except TypeError:
            valid = False  # non-ASCII header must 401, not 500
        if not valid:
            raise HTTPException(status_code=401, detail="Invalid webhook signature")

        try:
            payload = json.loads(raw_body)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail="Body must be valid JSON") from exc
        rows = payload.get("signals") if isinstance(payload, dict) else payload
        if not isinstance(rows, list) or not rows:
            raise HTTPException(
                status_code=422,
                detail='Expected {"signals": [...]} or a non-empty JSON array',
            )
        if len(rows) > 1000:
            raise HTTPException(status_code=422, detail="Max 1000 signals per webhook call")

        records = [
            signal_from_row(
                {key: str(value) for key, value in row.items() if value is not None},
                default_source="webhook",
            )
            for row in rows
            if isinstance(row, dict)
        ]
        records = [record for record in records if record.feedback_text.strip()]
        if not records:
            raise HTTPException(status_code=422, detail="No rows with feedback_text")

        result = signal_store.import_signals(records)
        telemetry_store.record(
            "signals_imported",
            metadata={"source": "webhook", "imported": result.imported, "skipped": result.skipped_duplicates},
        )
        return result

    @router.post("/signals/delete", dependencies=[Depends(require_role(Role.editor))])
    def delete_signals(body: dict) -> dict:
        """Bulk-remove signals by id — the undo for a mis-mapped import batch.

        Editor-gated like import (whoever can create signals can retract their
        own mistake). Derived insights are recomputed on the next triage run.
        """
        ids = body.get("signal_ids")
        if not isinstance(ids, list) or not ids:
            raise HTTPException(status_code=422, detail="signal_ids must be a non-empty list")
        if len(ids) > 5000:
            raise HTTPException(status_code=422, detail="Max 5000 signal_ids per call")
        deleted = signal_store.delete_signals([str(i) for i in ids])
        telemetry_store.record(
            "signals_deleted", metadata={"requested": len(ids), "deleted": deleted}
        )
        return {"deleted": deleted}

    @router.post("/signals/validate-csv", response_model=SignalValidationReport, dependencies=[read_dep])
    def validate_signal_csv_import(request: SignalCsvImportRequest) -> SignalValidationReport:
        return validate_signal_csv(
            request.csv_text,
            existing_signal_ids=signal_store.existing_signal_ids(),
        )

    @router.get("/journey-events", response_model=list[JourneyEventRecord], dependencies=[read_dep])
    def list_journey_events() -> list[JourneyEventRecord]:
        return journey_event_store.list_events()

    @router.post("/journey-events/import", response_model=JourneyEventImportResult, dependencies=[Depends(require_role(Role.editor))])
    def import_journey_events(request: JourneyEventImportRequest) -> JourneyEventImportResult:
        return journey_event_store.import_events(request.events)

    @router.post("/journey-events/import-csv", response_model=JourneyEventImportResult, dependencies=[Depends(require_role(Role.editor))])
    def import_journey_event_csv(request: JourneyEventCsvImportRequest) -> JourneyEventImportResult:
        return journey_event_store.import_events(parse_journey_event_csv(request.csv_text))

    @router.get("/customer-context", response_model=list[CustomerContextRecord], dependencies=[read_dep])
    def list_customer_context() -> list[CustomerContextRecord]:
        return context_store.list_context()

    @router.get(
        "/customer-context/completeness",
        response_model=CustomerContextCompletenessReport,
        dependencies=[read_dep],
    )
    def get_customer_context_completeness() -> CustomerContextCompletenessReport:
        return context_completeness_report(context_store.list_context())

    @router.post("/customer-context/import", response_model=CustomerContextImportResult, dependencies=[Depends(require_role(Role.editor))])
    def import_customer_context(
        request: CustomerContextImportRequest,
    ) -> CustomerContextImportResult:
        return context_store.import_context(request.records)

    @router.post("/customer-context/import-csv", response_model=CustomerContextImportResult, dependencies=[Depends(require_role(Role.editor))])
    def import_customer_context_csv(
        request: CustomerContextCsvImportRequest,
    ) -> CustomerContextImportResult:
        report = validate_context_csv(
            request.csv_text,
            existing_customer_ids=context_store.existing_customer_ids(),
        )
        if not report.valid:
            raise HTTPException(status_code=422, detail=report.model_dump(mode="json"))

        return context_store.import_context(parse_context_csv(request.csv_text))

    @router.post("/customer-context/validate-csv", response_model=CustomerContextValidationReport, dependencies=[read_dep])
    def validate_customer_context_csv(
        request: CustomerContextCsvImportRequest,
    ) -> CustomerContextValidationReport:
        return validate_context_csv(
            request.csv_text,
            existing_customer_ids=context_store.existing_customer_ids(),
        )

    @router.get("/demo-datasets", response_model=list[DemoDatasetSummary], dependencies=[read_dep])
    def list_demo_datasets() -> list[DemoDatasetSummary]:
        return [to_demo_dataset_summary(dataset) for dataset in demo_datasets]

    @router.post("/demo-datasets/{dataset_id}/import", response_model=DemoDatasetImportResult, dependencies=[Depends(require_role(Role.editor))])
    def import_demo_dataset(dataset_id: str, body: dict | None = None) -> DemoDatasetImportResult:
        dataset = require_demo_dataset(dataset_id)
        signals_to_import = dataset.signals
        # Evergreen demos: shift timestamps so the newest signal lands yesterday,
        # preserving relative spacing — the trend chart, emerging radar and
        # signal-rate baselines stay meaningful whenever the demo runs.
        # Opt out with {"rebase": false} for reproducible fixed-date imports.
        if (body or {}).get("rebase", True):
            from datetime import UTC, datetime, timedelta

            parsed = []
            for signal in signals_to_import:
                try:
                    parsed.append(datetime.fromisoformat(signal.timestamp.replace("Z", "+00:00")))
                except ValueError:
                    parsed.append(None)
            valid = [ts for ts in parsed if ts is not None]
            if valid:
                shift = (datetime.now(UTC) - timedelta(days=1)) - max(valid)
                signals_to_import = [
                    signal.model_copy(
                        update={"timestamp": (ts + shift).isoformat().replace("+00:00", "Z")}
                    )
                    if ts is not None
                    else signal
                    for signal, ts in zip(signals_to_import, parsed)
                ]
        signal_result = signal_store.import_signals(signals_to_import)
        context_result = context_store.import_context(dataset.customer_context)
        telemetry_store.record(
            "signals_imported",
            metadata={"source": "demo_dataset", "dataset": dataset_id, "imported": signal_result.imported},
        )
        return DemoDatasetImportResult(
            dataset_id=dataset.dataset_id,
            title=dataset.title,
            signals=signal_result,
            customer_context=context_result,
        )

    return router
