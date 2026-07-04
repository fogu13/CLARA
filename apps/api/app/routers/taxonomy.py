"""Taxonomy governance routes: catalogs, terminology, bootstrap, hygiene, category ops."""

from __future__ import annotations

from collections import Counter

from fastapi import APIRouter, Depends, HTTPException

from app.domain.models import (
    SignalRecord,
    TaxonomyCatalog,
    TaxonomyLockRequest,
    TaxonomyMergeRequest,
    TaxonomyRenameRequest,
    TaxonomyReviewRequest,
    TaxonomySplitRequest,
    TaxonomyType,
    TerminologyDictionaryEntry,
)
from app.rbac import Role, require_role


def build_language_quality_report(signals: list[SignalRecord], terms: list[TerminologyDictionaryEntry]) -> dict:
    signal_counts = Counter((signal.language or "unknown").lower() for signal in signals)
    term_counts = Counter(language.lower() for term in terms for language in term.languages)
    languages = sorted({"de", "en", *signal_counts.keys(), *term_counts.keys()})
    rows = []

    for language in languages:
        signal_count = signal_counts[language]
        terminology_entries = term_counts[language]
        rows.append(
            {
                "language": language,
                "signal_count": signal_count,
                "terminology_entries": terminology_entries,
                "original_language_evidence": signal_count,
                "readiness": "ready" if signal_count and terminology_entries else "needs_attention",
            }
        )

    return {
        "total_signals": len(signals),
        "languages": rows,
        "german_english_ready": all(
            row["readiness"] == "ready" for row in rows if row["language"] in {"de", "en"}
        ),
    }


def build_router(
    *,
    taxonomy_store,
    terminology_store,
    signal_store,
    telemetry_store,
) -> APIRouter:
    router = APIRouter()
    read_dep = Depends(require_role(Role.viewer))

    @router.get("/taxonomies", response_model=list[TaxonomyCatalog], dependencies=[read_dep])
    def list_taxonomies() -> list[TaxonomyCatalog]:
        return taxonomy_store.list_catalogs()

    @router.get("/terminology-dictionary", response_model=list[TerminologyDictionaryEntry], dependencies=[read_dep])
    def list_terminology_dictionary() -> list[TerminologyDictionaryEntry]:
        return terminology_store.list_entries()

    @router.get("/language-quality", dependencies=[read_dep])
    def get_language_quality() -> dict:
        return build_language_quality_report(signal_store.list_signals(), terminology_store.list_entries())

    @router.post("/taxonomy/bootstrap", dependencies=[Depends(require_role(Role.editor))])
    def bootstrap_taxonomy_from_signals(body: dict | None = None) -> dict:
        """Cluster the workspace's signals into proposed taxonomy categories.

        The governed "no taxonomy to build" path: embeddings cluster the signals,
        the LLM names each cluster, and proposals land as status='proposed'
        categories (confidence-scored) awaiting human accept/reject.
        """
        from app.services.taxonomy_bootstrap import bootstrap_taxonomy

        body = body or {}
        try:
            taxonomy_type = TaxonomyType(body.get("taxonomy_type", "contact_reason"))
            limit = min(int(body.get("limit", 200)), 1000)
        except (ValueError, TypeError) as exc:
            raise HTTPException(status_code=422, detail=f"Invalid bootstrap request: {exc}") from exc

        report = bootstrap_taxonomy(
            signal_store.list_signals(),
            taxonomy_store,
            taxonomy_type=taxonomy_type,
            limit=limit,
        )
        if report.get("error") == "embedding_failed":
            raise HTTPException(
                status_code=502,
                detail="Embedding provider unavailable. taxonomy bootstrap aborted (no partial writes)",
            )
        telemetry_store.record(
            "taxonomy_bootstrapped",
            metadata={
                "taxonomy_type": taxonomy_type.value,
                "scanned": report["scanned"],
                "proposed": report["proposed"],
            },
        )
        return report

    @router.post("/taxonomy/hygiene", dependencies=[Depends(require_role(Role.editor))])
    def run_taxonomy_hygiene() -> dict:
        """Report-only taxonomy health check: near-duplicate active categories,
        stale unreviewed proposals, and categories drifting away from recent
        signals. Humans act via the existing merge/review/rename flows —
        nothing is auto-applied."""
        from app.services.taxonomy_hygiene import run_hygiene

        report = run_hygiene(taxonomy_store.list_catalogs(), signal_store.list_signals())
        telemetry_store.record(
            "taxonomy_hygiene_run",
            metadata={
                "duplicates": len(report["duplicates"]),
                "stale_proposals": len(report["stale_proposals"]),
                "drifted": len(report["drifted_categories"]),
                "healthy": report["healthy"],
            },
        )
        return report

    @router.post("/taxonomies/{taxonomy_type}/categories/review", response_model=TaxonomyCatalog, dependencies=[Depends(require_role(Role.editor))])
    def review_taxonomy_category(
        taxonomy_type: TaxonomyType,
        request: TaxonomyReviewRequest,
    ) -> TaxonomyCatalog:
        catalog = taxonomy_store.review_category(
            taxonomy_type,
            category_id=request.category_id,
            decision=request.decision,
            actor=request.actor,
        )
        telemetry_store.record(
            "taxonomy_reviewed",
            entity_id=request.category_id,
            metadata={"decision": request.decision},
        )
        return catalog

    @router.post("/taxonomies/{taxonomy_type}/categories/rename", response_model=TaxonomyCatalog, dependencies=[Depends(require_role(Role.editor))])
    def rename_taxonomy_category(
        taxonomy_type: TaxonomyType,
        request: TaxonomyRenameRequest,
    ) -> TaxonomyCatalog:
        try:
            return taxonomy_store.rename_category(
                taxonomy_type,
                category_id=request.category_id,
                label=request.label,
                description=request.description,
                actor=request.actor,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @router.post("/taxonomies/{taxonomy_type}/categories/lock", response_model=TaxonomyCatalog, dependencies=[Depends(require_role(Role.editor))])
    def lock_taxonomy_category(
        taxonomy_type: TaxonomyType,
        request: TaxonomyLockRequest,
    ) -> TaxonomyCatalog:
        try:
            return taxonomy_store.lock_category(
                taxonomy_type,
                category_id=request.category_id,
                actor=request.actor,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @router.post("/taxonomies/{taxonomy_type}/categories/merge", response_model=TaxonomyCatalog, dependencies=[Depends(require_role(Role.editor))])
    def merge_taxonomy_categories(
        taxonomy_type: TaxonomyType,
        request: TaxonomyMergeRequest,
    ) -> TaxonomyCatalog:
        try:
            return taxonomy_store.merge_categories(
                taxonomy_type,
                source_category_ids=request.source_category_ids,
                target_category_id=request.target_category_id,
                target_label=request.target_label,
                target_description=request.target_description,
                actor=request.actor,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @router.post("/taxonomies/{taxonomy_type}/categories/split", response_model=TaxonomyCatalog, dependencies=[Depends(require_role(Role.editor))])
    def split_taxonomy_category(
        taxonomy_type: TaxonomyType,
        request: TaxonomySplitRequest,
    ) -> TaxonomyCatalog:
        try:
            return taxonomy_store.split_category(
                taxonomy_type,
                source_category_id=request.source_category_id,
                categories=request.categories,
                actor=request.actor,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    return router
