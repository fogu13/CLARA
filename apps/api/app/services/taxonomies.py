from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from fastapi import HTTPException

from app.domain.models import (
    ProblemCandidate,
    RootCauseAnalysis,
    RootCauseEvidenceFactor,
    SignalRecord,
    TaxonomyCatalog,
    TaxonomyCategory,
    TaxonomyChange,
    TaxonomyClassification,
    TaxonomyOperation,
    TaxonomySplitCategoryRequest,
    TaxonomyType,
    TerminologyDictionaryEntry,
)
from app.services.paths import REPO_ROOT


def load_seed_taxonomies(path: Path | None = None) -> list[TaxonomyCatalog]:
    taxonomy_path = path or REPO_ROOT / "data" / "sample_taxonomies.json"
    raw_catalogs = json.loads(taxonomy_path.read_text(encoding="utf-8"))
    return [TaxonomyCatalog.model_validate(catalog) for catalog in raw_catalogs]


def load_seed_terminology(path: Path | None = None) -> list[TerminologyDictionaryEntry]:
    terminology_path = path or REPO_ROOT / "data" / "sample_terminology_dictionary.json"
    raw_entries = json.loads(terminology_path.read_text(encoding="utf-8"))
    return [TerminologyDictionaryEntry.model_validate(entry) for entry in raw_entries]


class TerminologyStore:
    def __init__(self, entries: list[TerminologyDictionaryEntry] | None = None) -> None:
        self._entries = entries or load_seed_terminology()

    def list_entries(self) -> list[TerminologyDictionaryEntry]:
        return list(self._entries)


class TaxonomyStore:
    def __init__(self, catalogs: list[TaxonomyCatalog] | None = None) -> None:
        self._catalogs = catalogs or load_seed_taxonomies()

    def list_catalogs(self) -> list[TaxonomyCatalog]:
        return list(self._catalogs)

    def version_key(self) -> str:
        return "|".join(
            f"{catalog.taxonomy_type.value}:{catalog.version}"
            for catalog in sorted(self._catalogs, key=lambda item: item.taxonomy_type.value)
        )

    def rename_category(
        self,
        taxonomy_type: TaxonomyType,
        *,
        category_id: str,
        label: str,
        description: str | None,
        actor: str,
    ) -> TaxonomyCatalog:
        catalog_index, catalog = self._catalog(taxonomy_type)
        category = self._category(catalog, category_id)
        self._ensure_unlocked(category)
        change = self._change(
            TaxonomyOperation.rename,
            f"Renamed {category.label} to {label}.",
            actor,
        )
        categories = [
            item.model_copy(
                update={
                    "label": label,
                    "description": description or item.description,
                    "change_history": [*item.change_history, change],
                }
            )
            if item.category_id == category_id
            else item
            for item in catalog.categories
        ]
        return self._replace_catalog(catalog_index, catalog, categories)

    def lock_category(
        self,
        taxonomy_type: TaxonomyType,
        *,
        category_id: str,
        actor: str,
    ) -> TaxonomyCatalog:
        catalog_index, catalog = self._catalog(taxonomy_type)
        category = self._category(catalog, category_id)
        change = self._change(
            TaxonomyOperation.lock,
            f"Locked {category.label} against taxonomy edits.",
            actor,
        )
        categories = [
            item.model_copy(
                update={
                    "locked": True,
                    "change_history": [*item.change_history, change],
                }
            )
            if item.category_id == category_id
            else item
            for item in catalog.categories
        ]
        return self._replace_catalog(catalog_index, catalog, categories)

    def propose_category(
        self,
        taxonomy_type: TaxonomyType,
        *,
        category_id: str,
        label: str,
        description: str,
        terms: list[str],
        confidence: float,
        evidence_count: int,
        actor: str,
    ) -> TaxonomyCatalog:
        """Add a bootstrap-discovered category as status='proposed' (human review pending)."""
        catalog_index, catalog = self._catalog(taxonomy_type)
        if any(item.category_id == category_id for item in catalog.categories):
            raise HTTPException(status_code=409, detail=f"Category {category_id} already exists")

        change = self._change(
            TaxonomyOperation.propose,
            f"Proposed from signal clustering (confidence {confidence:.2f}, {evidence_count} signals).",
            actor,
        )
        proposed = TaxonomyCategory(
            category_id=category_id,
            label=label,
            description=description,
            terms=terms,
            status="proposed",
            confidence=round(confidence, 3),
            evidence_count=evidence_count,
            change_history=[change],
        )
        return self._replace_catalog(catalog_index, catalog, [*catalog.categories, proposed])

    def review_category(
        self,
        taxonomy_type: TaxonomyType,
        *,
        category_id: str,
        decision: str,
        actor: str,
    ) -> TaxonomyCatalog:
        """Accept or reject a proposed category. Accept -> active; reject -> rejected."""
        if decision not in ("accept", "reject"):
            raise HTTPException(status_code=422, detail="decision must be 'accept' or 'reject'")

        catalog_index, catalog = self._catalog(taxonomy_type)
        category = self._category(catalog, category_id)
        if category.status != "proposed":
            raise HTTPException(
                status_code=409,
                detail=f"Category {category_id} is not awaiting review (status={category.status})",
            )

        new_status = "active" if decision == "accept" else "rejected"
        change = self._change(
            TaxonomyOperation.review,
            f"{'Accepted' if decision == 'accept' else 'Rejected'} proposed category {category.label}.",
            actor,
        )
        categories = [
            item.model_copy(
                update={
                    "status": new_status,
                    "change_history": [*item.change_history, change],
                }
            )
            if item.category_id == category_id
            else item
            for item in catalog.categories
        ]
        return self._replace_catalog(catalog_index, catalog, categories)

    def merge_categories(
        self,
        taxonomy_type: TaxonomyType,
        *,
        source_category_ids: list[str],
        target_category_id: str,
        target_label: str | None,
        target_description: str | None,
        actor: str,
    ) -> TaxonomyCatalog:
        source_ids = list(dict.fromkeys(source_category_ids))
        if len(source_ids) < 2:
            raise ValueError("At least two source categories are required.")

        catalog_index, catalog = self._catalog(taxonomy_type)
        sources = [self._category(catalog, category_id) for category_id in source_ids]
        for source in sources:
            self._ensure_unlocked(source)

        change = self._change(
            TaxonomyOperation.merge,
            f"Merged {', '.join(source.label for source in sources)} into {target_category_id}.",
            actor,
        )
        merged_terms = sorted({term for source in sources for term in source.terms})
        target = next(
            (category for category in catalog.categories if category.category_id == target_category_id),
            None,
        )
        categories: list[TaxonomyCategory] = []
        target_written = False

        for category in catalog.categories:
            if category.category_id in source_ids:
                if category.category_id == target_category_id:
                    categories.append(
                        category.model_copy(
                            update={
                                "label": target_label or category.label,
                                "description": target_description or category.description,
                                "terms": merged_terms,
                                "change_history": [*category.change_history, change],
                            }
                        )
                    )
                    target_written = True
                else:
                    categories.append(
                        category.model_copy(
                            update={
                                "status": "merged",
                                "parent_id": target_category_id,
                                "change_history": [*category.change_history, change],
                            }
                        )
                    )
            else:
                categories.append(category)

        if target is not None and target.category_id not in source_ids:
            categories = [
                category.model_copy(
                    update={
                        "label": target_label or category.label,
                        "description": target_description or category.description,
                        "terms": sorted({*category.terms, *merged_terms}),
                        "change_history": [*category.change_history, change],
                    }
                )
                if category.category_id == target_category_id
                else category
                for category in categories
            ]
            target_written = True

        if not target_written:
            categories.append(
                TaxonomyCategory(
                    category_id=target_category_id,
                    label=target_label or target_category_id.replace("_", " ").title(),
                    description=target_description or "Merged taxonomy category.",
                    terms=merged_terms,
                    change_history=[change],
                )
            )

        return self._replace_catalog(catalog_index, catalog, categories)

    def split_category(
        self,
        taxonomy_type: TaxonomyType,
        *,
        source_category_id: str,
        categories: list[TaxonomySplitCategoryRequest],
        actor: str,
    ) -> TaxonomyCatalog:
        if len(categories) < 2:
            raise ValueError("At least two split categories are required.")

        catalog_index, catalog = self._catalog(taxonomy_type)
        source = self._category(catalog, source_category_id)
        self._ensure_unlocked(source)
        existing_ids = {category.category_id for category in catalog.categories}
        new_ids = [category.category_id for category in categories]
        if len(new_ids) != len(set(new_ids)):
            raise ValueError("Split category IDs must be unique.")
        if existing_ids.intersection(new_ids):
            raise ValueError("Split category IDs must not already exist.")

        change = self._change(
            TaxonomyOperation.split,
            f"Split {source.label} into {', '.join(category.label for category in categories)}.",
            actor,
        )
        updated_categories = [
            category.model_copy(
                update={
                    "status": "split",
                    "change_history": [*category.change_history, change],
                }
            )
            if category.category_id == source_category_id
            else category
            for category in catalog.categories
        ]
        updated_categories.extend(
            TaxonomyCategory(
                category_id=category.category_id,
                label=category.label,
                description=category.description,
                terms=category.terms,
                parent_id=source_category_id,
                change_history=[change],
            )
            for category in categories
        )
        return self._replace_catalog(
            catalog_index,
            catalog,
            updated_categories,
        )

    def _catalog(self, taxonomy_type: TaxonomyType) -> tuple[int, TaxonomyCatalog]:
        for index, catalog in enumerate(self._catalogs):
            if catalog.taxonomy_type == taxonomy_type:
                return index, catalog
        raise ValueError(f"Unknown taxonomy type: {taxonomy_type.value}.")

    def _category(self, catalog: TaxonomyCatalog, category_id: str) -> TaxonomyCategory:
        for category in catalog.categories:
            if category.category_id == category_id:
                return category
        raise ValueError(f"Unknown taxonomy category: {category_id}.")

    def _ensure_unlocked(self, category: TaxonomyCategory) -> None:
        if category.locked:
            raise ValueError(f"Category is locked: {category.category_id}.")

    def _change(
        self,
        operation: TaxonomyOperation,
        description: str,
        actor: str,
    ) -> TaxonomyChange:
        return TaxonomyChange(
            change_id=f"CHG-{operation.value.upper()}-{self._change_count() + 1:03d}",
            operation=operation,
            description=description,
            actor=actor,
            changed_at=datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        )

    def _change_count(self) -> int:
        return sum(
            len(category.change_history)
            for catalog in self._catalogs
            for category in catalog.categories
        )

    def _replace_catalog(
        self,
        catalog_index: int,
        catalog: TaxonomyCatalog,
        categories: list[TaxonomyCategory],
    ) -> TaxonomyCatalog:
        updated = catalog.model_copy(
            update={
                "version": self._bump_version(catalog.version),
                "categories": categories,
            }
        )
        self._catalogs[catalog_index] = updated
        return updated

    def _bump_version(self, version: str) -> str:
        base, separator, revision = version.partition(".rev")
        if separator and revision.isdigit():
            return f"{base}.rev{int(revision) + 1}"
        return f"{version}.rev1"


def classify_candidate(
    candidate: ProblemCandidate,
    *,
    signals: list[SignalRecord],
    taxonomy_store: TaxonomyStore,
    terminology_store: TerminologyStore,
) -> ProblemCandidate:
    signal_ids = {evidence.signal_id for evidence in candidate.evidence}
    candidate_signals = [signal for signal in signals if signal.signal_id in signal_ids]
    dictionary_entries = terminology_store.list_entries()
    classifications = classify_signals(
        candidate_signals,
        taxonomy_store.list_catalogs(),
        dictionary_entries,
    )
    candidate_dictionary_hits = dictionary_hits(candidate_signals, dictionary_entries)
    limitations = candidate_limitations(candidate, candidate_signals, classifications)
    contradictory_evidence = sorted(
        {
            item
            for classification in classifications
            for item in classification.contradictory_evidence
        }
    )

    updates = {
        "taxonomy_version": taxonomy_store.version_key(),
        "classifications": classifications,
        "terminology_hits": terminology_hits(
            classifications,
            candidate_dictionary_hits,
        ),
        "root_cause_analysis": generate_root_cause_analysis(
            candidate,
            candidate_signals,
            classifications,
            candidate_dictionary_hits,
        ),
        "contradictory_evidence": contradictory_evidence,
        "known_limitations": limitations,
        "evaluation_notes": evaluation_notes(candidate, classifications),
        "emerging_problem_score": emerging_problem_score(candidate, classifications),
    }
    return candidate.model_copy(update=updates)


def classify_signals(
    signals: list[SignalRecord],
    catalogs: list[TaxonomyCatalog],
    dictionary_entries: list[TerminologyDictionaryEntry],
) -> list[TaxonomyClassification]:
    if not signals:
        return []

    signal_text = {
        signal.signal_id: searchable_text(signal)
        for signal in signals
    }
    languages = sorted({signal.language.lower() for signal in signals if signal.language})
    classifications: list[TaxonomyClassification] = []

    for catalog in catalogs:
        scored = []
        for category in catalog.categories:
            # Skip retired categories — merged/split ones are superseded and must not
            # win classification. (Locking uses a separate flag, so locked categories
            # keep status "active" and still classify.) Proposed categories must not
            # classify until a human accepts them; rejected ones never do.
            if category.status in ("merged", "split", "proposed", "rejected"):
                continue
            matched_signal_ids: set[str] = set()
            matched_terms: set[str] = set()
            for term in terms_for_category(catalog, category, dictionary_entries):
                normalized_term = normalize(term)
                if not normalized_term:
                    continue
                for signal_id, text in signal_text.items():
                    if normalized_term in text:
                        matched_signal_ids.add(signal_id)
                        matched_terms.add(term)

            if not matched_signal_ids:
                continue

            coverage = len(matched_signal_ids) / len(signals)
            term_strength = min(len(matched_terms) * 0.06, 0.24)
            language_strength = 0.04 if len(languages) > 1 else 0.0
            confidence = min(0.96, 0.52 + (coverage * 0.24) + term_strength + language_strength)
            scored.append(
                TaxonomyClassification(
                    taxonomy_type=catalog.taxonomy_type,
                    category_id=category.category_id,
                    label=category.label,
                    confidence=round(confidence, 2),
                    evidence_signal_ids=sorted(matched_signal_ids),
                    matched_terms=sorted(matched_terms),
                    language_notes=language_notes(languages, catalog.locale_support),
                    limitations=list(catalog.known_limitations),
                )
            )

        if not scored:
            continue

        scored = sorted(scored, key=lambda item: item.confidence, reverse=True)
        top = scored[0]
        contradictions = [
            f"{other.label} also matched {len(other.evidence_signal_ids)} signal(s)"
            for other in scored[1:]
            if top.confidence - other.confidence <= 0.12
        ]
        classifications.append(top.model_copy(update={"contradictory_evidence": contradictions}))

    return classifications


def journey_stage_inventory(taxonomy_store: "TaxonomyStore") -> list[str]:
    """Active journey-catalog category ids — the closed-set routing inventory (R3).

    Proposed/rejected/merged categories are excluded for the same reason they
    do not classify: the model must not route to a stage no human accepted.
    """
    stages: list[str] = []
    for catalog in taxonomy_store.list_catalogs():
        if catalog.taxonomy_type.value != "journey":
            continue
        for category in catalog.categories:
            if category.status in ("merged", "split", "proposed", "rejected"):
                continue
            stages.append(category.category_id)
    return sorted(set(stages))


def searchable_text(signal: SignalRecord) -> str:
    parts = [
        signal.journey,
        signal.journey_stage,
        signal.feedback_text,
        *signal.campaign_exposure,
        *signal.product_events,
    ]
    return normalize(" ".join(parts))


def terms_for_category(
    catalog: TaxonomyCatalog,
    category: TaxonomyCategory,
    dictionary_entries: list[TerminologyDictionaryEntry],
) -> list[str]:
    terms = list(category.terms)
    for entry in dictionary_entries:
        if entry.taxonomy_type != catalog.taxonomy_type:
            continue
        if category.category_id not in entry.category_ids:
            continue
        terms.extend([entry.canonical_term, *entry.aliases])
    return sorted(set(terms))


def normalize(value: str) -> str:
    return (
        value.casefold()
        .replace("_", " ")
        .replace("-", " ")
        .replace("ö", "oe")
        .replace("ü", "ue")
        .replace("ä", "ae")
        .replace("ß", "ss")
    )


def language_notes(languages: list[str], supported_locales: list[str]) -> list[str]:
    notes: list[str] = []
    unsupported = sorted(set(languages) - set(supported_locales))
    if len(languages) > 1:
        notes.append("Matched across multiple source languages.")
    if unsupported:
        notes.append(f"Unsupported source languages present: {', '.join(unsupported)}.")
    return notes


def dictionary_hits(
    signals: list[SignalRecord],
    dictionary_entries: list[TerminologyDictionaryEntry],
) -> list[str]:
    if not signals:
        return []

    corpus = " ".join(searchable_text(signal) for signal in signals)
    hits: list[str] = []
    for entry in dictionary_entries:
        entry_terms = [entry.canonical_term, *entry.aliases]
        if any(normalize(term) in corpus for term in entry_terms):
            hits.append(entry.canonical_term)
    return sorted(set(hits))


def terminology_hits(
    classifications: list[TaxonomyClassification],
    dictionary_terms: list[str],
) -> list[str]:
    hits = []
    for classification in classifications:
        hits.extend(classification.matched_terms[:3])
    hits.extend(dictionary_terms)
    return sorted(set(hits))


def generate_root_cause_analysis(
    candidate: ProblemCandidate,
    signals: list[SignalRecord],
    classifications: list[TaxonomyClassification],
    dictionary_terms: list[str],
) -> RootCauseAnalysis:
    factors: list[RootCauseEvidenceFactor] = []
    signal_ids = sorted({signal.signal_id for signal in signals})
    top_classifications = sorted(
        classifications,
        key=lambda classification: classification.confidence,
        reverse=True,
    )[:3]

    for classification in top_classifications:
        factors.append(
            RootCauseEvidenceFactor(
                factor_type=f"taxonomy:{classification.taxonomy_type.value}",
                label=classification.label,
                confidence=classification.confidence,
                signal_ids=classification.evidence_signal_ids,
                explanation=(
                    f"{classification.label} matched {len(classification.evidence_signal_ids)} "
                    f"signal(s) through {', '.join(classification.matched_terms[:4])}."
                ),
            )
        )

    if dictionary_terms:
        factors.append(
            RootCauseEvidenceFactor(
                factor_type="terminology",
                label="Terminology dictionary",
                confidence=min(0.95, 0.58 + (len(dictionary_terms) * 0.07)),
                signal_ids=signal_ids,
                explanation=(
                    "Canonical terms matched: "
                    f"{', '.join(dictionary_terms[:5])}."
                ),
            )
        )

    factors.append(
        RootCauseEvidenceFactor(
            factor_type="journey_stage",
            label=candidate.journey_stage,
            confidence=min(0.92, 0.48 + (candidate.signal_count * 0.07)),
            signal_ids=signal_ids,
            explanation=(
                f"{candidate.signal_count} signal(s) cluster in "
                f"{candidate.journey} / {candidate.journey_stage}."
            ),
        )
    )

    confidence = root_cause_confidence(candidate.confidence, factors)
    primary_factor = factors[0] if factors else None
    terminology_clause = ""
    if dictionary_terms:
        terminology_clause = f" involving {', '.join(dictionary_terms[:3])}"

    if primary_factor is not None and primary_factor.factor_type != "journey_stage":
        hypothesis = (
            f"{candidate.journey_stage} friction is likely driven by "
            f"{primary_factor.label.lower()}{terminology_clause}, based on "
            f"{candidate.signal_count} related signal(s)."
        )
    elif primary_factor is not None:
        # Only the journey-stage factor exists (no taxonomy or terminology match):
        # naming the stage as its own driver is a tautology ("General friction is
        # likely driven by general") — abstain honestly instead.
        hypothesis = (
            f"Insufficient evidence to name a likely driver for {candidate.journey_stage} "
            f"friction: {candidate.signal_count} related signal(s) have no taxonomy or "
            "terminology match yet. Review the signals or refine the taxonomy to sharpen this."
        )
    else:
        hypothesis = candidate.root_cause_hypothesis

    alternatives = [
        f"Signals may reflect a broader {candidate.journey} journey design issue.",
        f"Signals may be amplified by source-specific collection bias from {', '.join(candidate.sources[:3])}.",
    ]
    if len(classifications) > 1:
        alternatives.insert(
            0,
            f"{classifications[1].label} is a secondary taxonomy match to validate.",
        )

    validation_questions = [
        f"Do recent {candidate.journey_stage} drop-off events increase for the same customers?",
        "Do support transcripts mention the same canonical terms outside this sample?",
        "Can owners reproduce the issue from the affected customer path?",
    ]

    return RootCauseAnalysis(
        hypothesis=hypothesis,
        confidence=confidence,
        factors=factors,
        alternative_hypotheses=alternatives[:3],
        validation_questions=validation_questions,
    )


def root_cause_confidence(
    candidate_confidence: float,
    factors: list[RootCauseEvidenceFactor],
) -> float:
    if not factors:
        return round(candidate_confidence, 2)
    average_factor_confidence = sum(factor.confidence for factor in factors) / len(factors)
    return round(min(0.97, (candidate_confidence * 0.45) + (average_factor_confidence * 0.55)), 2)


def candidate_limitations(
    candidate: ProblemCandidate,
    signals: list[SignalRecord],
    classifications: list[TaxonomyClassification],
) -> list[str]:
    limitations: list[str] = []
    if candidate.signal_count < 5:
        limitations.append("Small evaluation set; classification confidence should be reviewed.")
    if not classifications:
        limitations.append("No taxonomy category matched the current evidence.")
    if "de" not in {signal.language.lower() for signal in signals}:
        limitations.append("No German-language evidence in this candidate.")
    if any(classification.confidence < 0.7 for classification in classifications):
        limitations.append("At least one taxonomy match is below the trusted-confidence threshold.")
    return limitations


def evaluation_notes(
    candidate: ProblemCandidate,
    classifications: list[TaxonomyClassification],
) -> list[str]:
    notes = [
        f"Candidate generated from {candidate.signal_count} signal(s) across {len(candidate.sources)} source(s)."
    ]
    if classifications:
        notes.append(
            f"{len(classifications)} taxonomy dimension(s) classified for routing evaluation."
        )
    if len(candidate.languages) > 1:
        notes.append("Routing evaluation includes multilingual German/English handling.")
    return notes


def emerging_problem_score(
    candidate: ProblemCandidate,
    classifications: list[TaxonomyClassification],
) -> float:
    source_factor = min(len(candidate.sources) * 0.08, 0.24)
    volume_factor = min(candidate.signal_count * 0.08, 0.4)
    confidence_factor = 0.0
    if classifications:
        confidence_factor = sum(item.confidence for item in classifications) / len(classifications) * 0.24
    novelty_factor = 0.12 if candidate.review_status.value == "pending" else 0.0
    return round(min(1.0, source_factor + volume_factor + confidence_factor + novelty_factor), 2)
