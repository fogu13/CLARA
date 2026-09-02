from __future__ import annotations

import csv
import hashlib
import io
import json
import re
import sqlite3
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

from app.domain.models import (
    ActionProposal,
    AffectedCohort,
    AudienceReadiness,
    CandidateDecisionRecord,
    CandidateDecisionStatus,
    Evidence,
    GovernanceCheck,
    InterventionBrief,
    OutcomeContract,
    ProblemCandidate,
    ProblemRecord,
    SignalImportResult,
    SignalRecord,
    SignalValidationIssue,
    SignalValidationReport,
)
from app.domain.models import redact_common_pii
from app.domain.scoring import approval_pressure, impact_band, normalized_impact_score
from app.services.measurement_scheduler import THEME_JOURNEY
from app.services.common import (  # re-exported for existing importers, SerializedConnection
    SerializedConnection,
    normalize_timestamp,
    utc_now,
)
from app.services.language import detect_language


# Fallback identifiers written when an import row carries no customer/account id
# (web CSV wizard uses "unknown", the API fallback uses "unknown_customer"/"_account").
UNKNOWN_IDENTITY_VALUES = {"", "unknown", "unknown_customer", "unknown_account"}

# --------------------------------------------------------------------------- #
# Near-duplicate detection (external-review item 11, fuzzy tier).
#
# Token-set Jaccard against the recent corpus at import time. Matches are
# ANNOTATED (metadata["near_duplicate_of"]) and still imported — silently
# dropping a signal is the dishonest failure mode this replaces; the feed
# shows a "possible duplicate" badge instead.
# ponytail: O(new × corpus) set intersection, corpus capped at the most recent
# 2000 signals — MinHash or the embedding infra is the upgrade path at scale.
# --------------------------------------------------------------------------- #
NEAR_DUP_JACCARD = 0.85
NEAR_DUP_MIN_TOKENS = 5
_NEAR_DUP_CORPUS_CAP = 2000
_DUP_TOKEN = re.compile(r"[a-zà-ÿäöüß0-9']+")


def _dup_tokens(text: str) -> frozenset[str]:
    return frozenset(t for t in _DUP_TOKEN.findall(text.casefold()) if len(t) > 1)


def annotate_near_duplicates(
    new_records: list[SignalRecord], existing: list[SignalRecord]
) -> int:
    """Stamp metadata['near_duplicate_of'] on records that near-match an
    existing (or same-batch) signal's text. Returns how many were annotated."""
    corpus: list[tuple[str, frozenset[str]]] = [
        (signal.signal_id, _dup_tokens(signal.feedback_text))
        for signal in existing[-_NEAR_DUP_CORPUS_CAP:]
    ]
    annotated = 0
    for record in new_records:
        tokens = _dup_tokens(record.feedback_text)
        if len(tokens) >= NEAR_DUP_MIN_TOKENS:
            for signal_id, other in corpus:
                if not other:
                    continue
                union = len(tokens | other)
                if union and len(tokens & other) / union >= NEAR_DUP_JACCARD:
                    record.metadata["near_duplicate_of"] = signal_id
                    annotated += 1
                    break
        corpus.append((record.signal_id, tokens))
    return annotated


def normalize_label(value: str) -> str:
    return value.replace("_", " ").strip().title()


_CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_TAG_RE = re.compile(r"<[^>]{1,200}>")
_SPACE_RUNS = re.compile(r"[ \t\f\v]+")
_BLANK_LINES = re.compile(r"\n{3,}")


def clean_feedback_text(text: str) -> str:
    """Normalize customer text once, at the door.

    HTML entities are decoded and tags stripped (review sites and ticket systems
    deliver both), control characters removed, Unicode NFC-normalised, and
    whitespace collapsed while single blank lines are kept. The pitch's
    "cleans, normalizes and standardizes" starts here; the model and the
    clustering see the same string whatever channel it arrived on.
    """
    import html
    import unicodedata

    if not text:
        return ""
    value = html.unescape(str(text))
    value = _TAG_RE.sub(" ", value)
    value = _CONTROL_CHARS.sub("", value)
    value = unicodedata.normalize("NFC", value)
    value = value.replace("\r\n", "\n").replace("\r", "\n")
    value = _SPACE_RUNS.sub(" ", value)
    value = "\n".join(line.strip() for line in value.split("\n"))
    value = _BLANK_LINES.sub("\n\n", value)
    return value.strip()


def _csv_reader(csv_text: str) -> csv.DictReader:
    """DictReader that copes with what spreadsheets actually export.

    Excel (German locale) writes semicolon-separated files with a UTF-8 BOM;
    both used to surface as "Missing required column: feedback_text". The BOM
    is stripped and the delimiter sniffed from the header line (comma,
    semicolon or tab), falling back to the comma dialect.
    """
    text = csv_text.lstrip("\ufeff").strip()
    header = text.split("\n", 1)[0]
    counts = {",": header.count(","), ";": header.count(";"), "\t": header.count("\t")}
    delimiter = max(counts, key=counts.get) if any(counts.values()) else ","
    return csv.DictReader(io.StringIO(text), delimiter=delimiter)


def normalize_incoming_signal(record: SignalRecord) -> SignalRecord:
    """Apply the CSV/webhook door rules to a SignalRecord posted as JSON.

    POST /signals/import used to store records verbatim: unparseable
    timestamps, missing language and raw text slipped past the checks every
    other import path runs. Timestamp defaults are flagged in metadata so a
    substituted time stays auditable.
    """
    metadata = dict(record.metadata)
    timestamp, defaulted = normalize_timestamp(record.timestamp)
    if defaulted:
        metadata["timestamp_defaulted"] = "true"
    text = clean_feedback_text(record.feedback_text)
    language = record.language
    if not language or language == "unknown":
        language = detect_language(text)
    return record.model_copy(
        update={
            "feedback_text": text,
            "timestamp": timestamp,
            "language": language,
            "metadata": metadata,
        }
    )


def candidate_id_for(journey: str, journey_stage: str) -> str:
    token = f"{journey}-{journey_stage}".upper().replace("_", "-")
    return f"CAND-{token}"


def owner_for_stage(journey_stage: str) -> str:
    if "verification" in journey_stage:
        return "onboarding_product"
    if "cancellation" in journey_stage:
        return "lifecycle_marketing"
    if "payment" in journey_stage:
        return "payments_product"
    return "cx_operations"


# --- AI themes as problem candidates --------------------------------------
# POST /triage/run sorts signals into themes (LLM enrichment + deterministic
# clustering + synthesis). Until these helpers existed the resulting insights
# were returned in the HTTP response and dropped: the AI triage never reached
# the Action Queue, which only knew the deterministic journey/stage grouping.
# Themes are now persisted (stores' save_theme_insights) and surfaced as
# ProblemCandidates with origin="ai_theme", so the same human accept -> promote
# -> approve -> measure path applies to what the model found.

THEME_TITLE_MAX = 160
THEME_SUMMARY_MAX = 1000
THEME_EVIDENCE_ROWS = 5
# A theme belongs to one journey when that journey carries at least this share
# of its signals; otherwise it is reported as cross-journey.
THEME_JOURNEY_MAJORITY = 0.6
CROSS_JOURNEY_LABEL = "Cross Journey"


def slugify_owner(value: str | None) -> str:
    token = re.sub(r"[^a-z0-9]+", "_", (value or "").strip().lower()).strip("_")
    return token


def theme_candidate_id(tag: str) -> str:
    return f"CAND-THEME-{tag.upper().replace('_', '-').replace(' ', '-')}"


def _clip01(value: object) -> float:
    try:
        number = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return 0.0
    return max(0.0, min(1.0, number))


def _safe_text(value: object, limit: int) -> str:
    if value is None:
        return ""
    return (redact_common_pii(str(value)) or "")[:limit]


def prepare_theme_insight(insight: dict, *, run_id: str) -> dict | None:
    """Reduce a synthesis insight to the persisted theme record.

    Model output is untrusted: only known fields are kept, free text is PII-
    redacted and length-capped, numbers are clipped to [0, 1]. Returns None for
    an insight without a theme tag (nothing to key on).
    """
    tag = str(insight.get("tag") or "").strip().lower().replace(" ", "_")
    if not tag:
        return None
    audit = insight.get("audit") if isinstance(insight.get("audit"), dict) else {}
    actions = []
    for action in insight.get("suggested_actions") or []:
        if not isinstance(action, dict):
            continue
        actions.append(
            {
                "type": _safe_text(action.get("type"), 40),
                "title": _safe_text(action.get("title"), THEME_TITLE_MAX),
                "description": _safe_text(action.get("description"), 300),
            }
        )
        if len(actions) >= 5:
            break
    return {
        "tag": tag,
        "title": _safe_text(insight.get("title"), THEME_TITLE_MAX),
        "summary": _safe_text(insight.get("summary"), THEME_SUMMARY_MAX),
        "category": _safe_text(insight.get("category"), 80),
        "target_team": _safe_text(insight.get("target_team"), 80),
        "confidence": _clip01(insight.get("confidence")),
        "severity": _safe_text(insight.get("severity"), 20),
        "severity_score": _clip01(
            insight.get("severity_score", insight.get("impact_score"))
        ),
        "max_urgency": _safe_text(insight.get("max_urgency"), 20),
        "signal_ids": [str(item) for item in (insight.get("signal_ids") or [])][:5000],
        "suggested_actions": actions,
        "audit": {
            "model": _safe_text(audit.get("model"), 80),
            "source": _safe_text(audit.get("source"), 40),
            "limitations": [_safe_text(item, 200) for item in (audit.get("limitations") or [])][:6],
            "applied_learnings": [
                _safe_text(item, 80) for item in (audit.get("applied_learnings") or [])
            ][:6],
        },
        "triage_run_id": run_id,
        "saved_at": utc_now(),
    }


def theme_candidates(insights: list[dict], signals: list[SignalRecord]) -> list[ProblemCandidate]:
    """ProblemCandidates (origin=ai_theme) from persisted triage themes.

    Counts are recomputed from the signals that still exist, so a deleted import
    batch shrinks or removes the theme instead of leaving stale numbers.
    """
    by_id = {signal.signal_id: signal for signal in signals}
    candidates: list[ProblemCandidate] = []
    for insight in insights:
        tag = str(insight.get("tag") or "").strip()
        if not tag:
            continue
        group = [by_id[sid] for sid in insight.get("signal_ids") or [] if sid in by_id]
        if not group:
            continue
        sorted_group = sorted(group, key=lambda signal: signal.timestamp)
        customers = {
            signal.customer_id for signal in group if signal.customer_id not in UNKNOWN_IDENTITY_VALUES
        }
        accounts = {
            signal.account_id for signal in group if signal.account_id not in UNKNOWN_IDENTITY_VALUES
        }
        journeys = Counter(signal.journey for signal in group if signal.journey != "unknown_journey")
        journey = CROSS_JOURNEY_LABEL
        if journeys:
            top_journey, top_count = journeys.most_common(1)[0]
            if top_count >= THEME_JOURNEY_MAJORITY * len(group):
                journey = normalize_label(top_journey)
        stage_label = normalize_label(tag)
        raw_confidence = _clip01(insight.get("confidence"))
        confidence = round(min(0.95, max(0.3, raw_confidence or 0.5)), 2)
        summary = str(insight.get("summary") or "").strip()
        audit = insight.get("audit") if isinstance(insight.get("audit"), dict) else {}
        actions = insight.get("suggested_actions") or []
        first_action = actions[0] if actions and isinstance(actions[0], dict) else None
        if first_action and (first_action.get("title") or first_action.get("description")):
            suggested_action = ": ".join(
                part for part in (first_action.get("title"), first_action.get("description")) if part
            )
        else:
            suggested_action = (
                f"Review the {stage_label} theme with its evidence, confirm the owning team, "
                "then create a structural fix plus customer recovery action."
            )
        limitations = [
            "AI-sorted theme (LLM synthesis); not human-validated until a reviewer accepts it.",
            *[str(item) for item in (audit.get("limitations") or []) if item],
        ]
        if journey == CROSS_JOURNEY_LABEL:
            limitations.append(
                "Signals span several journeys; the theme, not a journey stage, is the unit of ownership."
            )
        evaluation_notes = []
        if audit.get("model"):
            evaluation_notes.append(f"Synthesized by {audit['model']} ({audit.get('source') or 'llm'}).")
        if insight.get("severity"):
            evaluation_notes.append(
                f"Deterministic cross-signal severity: {insight['severity']} "
                f"({round(_clip01(insight.get('severity_score')) * 100)}%)."
            )
        if audit.get("applied_learnings"):
            evaluation_notes.append(
                "Past learnings applied: " + ", ".join(str(x) for x in audit["applied_learnings"])
            )
        candidates.append(
            ProblemCandidate(
                candidate_id=theme_candidate_id(tag),
                title=str(insight.get("title") or "").strip() or f"Theme: {stage_label}",
                journey=journey,
                journey_stage=stage_label,
                signal_count=len(group),
                customer_count=len(customers),
                account_count=len(accounts),
                sources=sorted({signal.source for signal in group}),
                languages=sorted({signal.language for signal in group}),
                first_seen=sorted_group[0].timestamp,
                last_seen=sorted_group[-1].timestamp,
                confidence=confidence,
                evidence=[
                    Evidence(
                        signal_id=signal.signal_id,
                        source=signal.source,
                        language=signal.language,
                        excerpt=signal.feedback_text[:220],
                        customer_id=signal.customer_id,
                        account_id=signal.account_id,
                        timestamp=signal.timestamp,
                    )
                    for signal in sorted_group[:THEME_EVIDENCE_ROWS]
                ],
                root_cause_hypothesis=(
                    f"{summary} This is an AI-sorted theme, not a confirmed root cause."
                    if summary
                    else f"Signals were sorted into the theme {stage_label}. "
                    "This is an AI-sorted theme, not a confirmed root cause."
                ),
                suggested_owner=slugify_owner(insight.get("target_team")) or owner_for_stage(tag),
                suggested_action=suggested_action,
                known_limitations=limitations,
                evaluation_notes=evaluation_notes,
                origin="ai_theme",
                theme_tag=tag,
                theme_summary=summary or None,
                triage_impact_score=_clip01(insight.get("severity_score")) or None,
                triage_urgency=str(insight.get("max_urgency") or "") or None,
                triage_run_id=str(insight.get("triage_run_id") or "") or None,
            )
        )
    return sorted(candidates, key=lambda candidate: candidate.signal_count, reverse=True)


def split_multi_value(value: str | None) -> list[str]:
    if not value:
        return []

    return [item.strip() for item in value.replace("|", ";").split(";") if item.strip()]


# Only feedback_text is required. The rest are "recommended": if a column is present but a
# row leaves it empty we warn (quality hint), but a missing column is fine — it gets a default.
REQUIRED_SIGNAL_FIELDS = ["feedback_text"]

RECOMMENDED_SIGNAL_FIELDS = [
    "customer_id",
    "account_id",
    "source",
    "journey",
    "journey_stage",
    "language",
    "timestamp",
]

# Canonical columns mapped onto SignalRecord fields; any other CSV column is kept in metadata.
KNOWN_SIGNAL_COLUMNS = frozenset(
    {
        "signal_id",
        "customer_id",
        "account_id",
        "source",
        "journey",
        "journey_stage",
        "campaign_exposure",
        "product_events",
        "feedback_text",
        "language",
        "timestamp",
    }
)


def read_signal_csv_rows(csv_text: str) -> tuple[list[str], list[dict[str, str]]]:
    reader = _csv_reader(csv_text)
    headers = [header.strip() for header in (reader.fieldnames or [])]
    rows = [
        {key.strip(): value or "" for key, value in row.items() if key is not None}
        for row in reader
    ]
    return headers, rows


def validate_signal_csv(
    csv_text: str,
    *,
    existing_signal_ids: set[str] | None = None,
) -> SignalValidationReport:
    headers, rows = read_signal_csv_rows(csv_text)
    existing_signal_ids = existing_signal_ids or set()
    errors: list[SignalValidationIssue] = []
    warnings: list[SignalValidationIssue] = []
    rows_with_errors: set[int] = set()
    rows_skipped_as_existing: set[int] = set()
    seen_signal_ids: dict[str, int] = {}

    if not headers:
        errors.append(
            SignalValidationIssue(
                severity="error",
                message="CSV must include a header row.",
            )
        )

    for field in REQUIRED_SIGNAL_FIELDS:
        if field not in headers:
            errors.append(
                SignalValidationIssue(
                    severity="error",
                    field=field,
                    message=f"Missing required column: {field}.",
                )
            )

    for row_index, row in enumerate(rows, start=2):
        # Use the same content-hash fallback the importer uses, so the preview's
        # duplicate detection matches what import will actually do for no-id rows.
        signal_id = row.get("signal_id", "").strip() or _fallback_signal_id(row)
        row_has_error = False

        for field in REQUIRED_SIGNAL_FIELDS:
            if not row.get(field, "").strip():
                errors.append(
                    SignalValidationIssue(
                        severity="error",
                        row_number=row_index,
                        field=field,
                        message=f"Row {row_index} is missing {field}.",
                    )
                )
                row_has_error = True

        for field in RECOMMENDED_SIGNAL_FIELDS:
            if field in headers and not row.get(field, "").strip():
                warnings.append(
                    SignalValidationIssue(
                        severity="warning",
                        row_number=row_index,
                        field=field,
                        message=f"Row {row_index} has no {field}; candidate quality may be lower.",
                    )
                )

        # A non-ISO timestamp ("23.06.2026 10:00", "6/23/2026") is not an
        # error — import still works — but it is silently replaced by the
        # import time, which drops the row out of every trend window. Say so
        # in the preview instead of letting the substitution pass unseen.
        raw_timestamp = row.get("timestamp", "").strip()
        if "timestamp" in headers and raw_timestamp and normalize_timestamp(raw_timestamp)[1]:
            warnings.append(
                SignalValidationIssue(
                    severity="warning",
                    row_number=row_index,
                    field="timestamp",
                    message=(
                        f"Row {row_index} timestamp '{raw_timestamp[:40]}' is not ISO 8601 and will"
                        " be set to the import time (flagged in metadata)."
                    ),
                )
            )

        if signal_id:
            first_seen_row = seen_signal_ids.get(signal_id)
            if first_seen_row is not None:
                errors.append(
                    SignalValidationIssue(
                        severity="error",
                        row_number=row_index,
                        field="signal_id",
                        message=(
                            f"Duplicate signal_id {signal_id} also appears on row {first_seen_row}."
                        ),
                    )
                )
                row_has_error = True
            else:
                seen_signal_ids[signal_id] = row_index

            if signal_id in existing_signal_ids:
                warnings.append(
                    SignalValidationIssue(
                        severity="warning",
                        row_number=row_index,
                        field="signal_id",
                        message=f"Signal {signal_id} already exists and will be skipped.",
                    )
                )
                rows_skipped_as_existing.add(row_index)

        if row_has_error:
            rows_with_errors.add(row_index)

    importable_rows = max(0, len(rows) - len(rows_with_errors) - len(rows_skipped_as_existing))

    return SignalValidationReport(
        valid=not errors,
        total_rows=len(rows),
        importable_rows=importable_rows,
        errors=errors,
        warnings=warnings,
    )


def _fallback_signal_id(row: dict) -> str:
    """Deterministic content-based id for rows with no signal_id.

    The old positional id (``CSV-{index}``) collided across different files, so a
    second no-signal_id import silently deduped to zero rows (data loss). Hashing
    the row content instead lets different files coexist while re-importing the SAME
    file stays idempotent.
    """
    basis = "|".join(
        # Casefold + collapse whitespace so trivial variants of the same row
        # ("Great app" vs "great  app ") hash identically and dedupe on import.
        " ".join((row.get(field) or "").split()).casefold()
        for field in ("feedback_text", "customer_id", "timestamp", "source", "journey_stage")
    )
    return "CSV-" + hashlib.sha256(basis.encode("utf-8")).hexdigest()[:12]


def signal_from_row(row: dict[str, str], *, default_source: str = "csv_upload") -> SignalRecord:
    """Build a SignalRecord from a flat field mapping (CSV row or webhook payload).

    Unknown keys are preserved as metadata; missing fields get the same defaults
    everywhere so CSV and webhook ingestion behave identically.
    """
    metadata = {
        key: (value or "").strip()
        for key, value in row.items()
        if key and key not in KNOWN_SIGNAL_COLUMNS and (value or "").strip()
    }
    timestamp, timestamp_defaulted = normalize_timestamp(row.get("timestamp"))
    if timestamp_defaulted:
        metadata["timestamp_defaulted"] = "true"
    return SignalRecord(
        signal_id=row.get("signal_id") or _fallback_signal_id(row),
        customer_id=row.get("customer_id") or "unknown_customer",
        account_id=row.get("account_id") or "unknown_account",
        source=row.get("source") or default_source,
        journey=row.get("journey") or "unknown_journey",
        journey_stage=row.get("journey_stage") or "unknown_stage",
        campaign_exposure=split_multi_value(row.get("campaign_exposure")),
        product_events=split_multi_value(row.get("product_events")),
        feedback_text=clean_feedback_text(row.get("feedback_text") or ""),
        # No language field -> detect from the text (DE/EN heuristic), so
        # German handling fires on real imports instead of "unknown".
        language=row.get("language") or detect_language(row.get("feedback_text") or ""),
        timestamp=timestamp,
        metadata=metadata,
    )


def parse_signal_csv(csv_text: str) -> list[SignalRecord]:
    _headers, rows = read_signal_csv_rows(csv_text)
    return [signal_from_row(row) for row in rows]


def build_candidates(signals: list[SignalRecord]) -> list[ProblemCandidate]:
    grouped: dict[tuple[str, str], list[SignalRecord]] = defaultdict(list)
    for signal in signals:
        journey_stage = signal.journey_stage
        if signal.journey == "unknown_journey" and journey_stage == "unknown_stage":
            # Connector/CSV feedback (app stores, review sites) carries no journey
            # metadata; one mega-candidate titled "Unknown Stage" is useless. Fall
            # back to per-source grouping so each channel gets a readable candidate
            # ("Repeated friction in Trustpilot Feedback").
            journey_stage = f"{signal.source}_feedback"
        # Group case-insensitively: candidate ids are upper-cased, so
        # "Checkout/Payment" and "checkout/payment" rows would otherwise form two
        # candidates with the same id and a baseline that disagrees with the
        # (normalised) measurement scope.
        grouped[(signal.journey.strip().lower(), journey_stage.strip().lower())].append(signal)

    candidates: list[ProblemCandidate] = []
    for (journey, journey_stage), group in grouped.items():
        sorted_group = sorted(group, key=lambda signal: signal.timestamp)
        # Fallback ids ("unknown", "unknown_customer") are identity gaps, not a
        # real customer: counting them let 153 identifier-less signals reconcile
        # to "1 customer / 1 account" on the problem detail.
        customers = {
            signal.customer_id
            for signal in group
            if signal.customer_id not in UNKNOWN_IDENTITY_VALUES
        }
        accounts = {
            signal.account_id
            for signal in group
            if signal.account_id not in UNKNOWN_IDENTITY_VALUES
        }
        sources = sorted({signal.source for signal in group})
        languages = sorted({signal.language for signal in group})
        product_events = Counter(event for signal in group for event in signal.product_events)
        campaigns = Counter(campaign for signal in group for campaign in signal.campaign_exposure)

        top_event = product_events.most_common(1)[0][0] if product_events else "unknown event"
        top_campaign = campaigns.most_common(1)[0][0] if campaigns else "no dominant campaign"
        confidence = min(0.95, 0.5 + (len(group) * 0.08) + (len(sources) * 0.04))
        owner = owner_for_stage(journey_stage)

        evidence = [
            Evidence(
                signal_id=signal.signal_id,
                source=signal.source,
                language=signal.language,
                excerpt=signal.feedback_text[:220],
                customer_id=signal.customer_id,
                account_id=signal.account_id,
                timestamp=signal.timestamp,
            )
            for signal in sorted_group[:3]
        ]

        candidates.append(
            ProblemCandidate(
                candidate_id=candidate_id_for(journey, journey_stage),
                title=f"Repeated friction in {normalize_label(journey_stage)}",
                journey=normalize_label(journey),
                journey_stage=normalize_label(journey_stage),
                signal_count=len(group),
                customer_count=len(customers),
                account_count=len(accounts),
                sources=sources,
                languages=languages,
                first_seen=sorted_group[0].timestamp,
                last_seen=sorted_group[-1].timestamp,
                confidence=round(confidence, 2),
                evidence=evidence,
                root_cause_hypothesis=(
                    f"Signals cluster around {top_event} with campaign context {top_campaign}. "
                    "This is a candidate, not a confirmed root cause."
                ),
                suggested_owner=owner,
                suggested_action=(
                    f"Review affected {normalize_label(journey_stage)} signals, validate the "
                    "event path, then create a structural fix plus customer recovery action."
                ),
            )
        )

    return sorted(candidates, key=lambda candidate: candidate.signal_count, reverse=True)


def audience_readiness_for_candidate(candidate: ProblemCandidate, *, destination: str) -> AudienceReadiness:
    estimated_size = candidate.customer_count
    return AudienceReadiness(
        estimated_audience_size=estimated_size,
        eligible_customers=0,
        excluded_customers=estimated_size,
        consent_ready_customers=0,
        suppression_excluded_customers=0,
        over_contact_risk="medium" if estimated_size >= 25 else "low",
        readiness_status="needs_consent_review",
        readiness_reasons=[
            "Audience is estimated from evidence-linked customers only.",
            "Consent, lawful basis and suppression metadata must be verified before export.",
        ],
        export_destination=destination,
        export_format=f"{destination}_draft_csv",
        export_fields=[
            "customer_id",
            "account_id",
            "journey",
            "journey_stage",
            "trigger_reason",
            "recommended_channel",
            "control_group_flag",
        ],
        activation_constraints=[
            "Export is a draft for human review; CLARA does not activate campaigns.",
            "Remove customers without valid consent or with legal/fraud/vulnerability holds.",
            "Apply current suppression and over-contact rules in the destination system.",
        ],
    )


def intervention_brief_for_candidate(candidate: ProblemCandidate, *, channel: str, destination: str) -> InterventionBrief:
    stage_token = candidate.journey_stage.lower().replace(" ", "_")
    return InterventionBrief(
        audience_summary=(
            f"Customers represented by {candidate.signal_count} signals in {candidate.journey} / "
            f"{candidate.journey_stage}; draft only until consent and suppression checks pass."
        ),
        inclusion_criteria=[
            f"Evidence references {candidate.customer_count} affected customers",
            f"Journey is {candidate.journey}",
            f"Journey stage is {candidate.journey_stage}",
        ],
        exclusion_criteria=[
            "Customers without valid communication consent",
            "Customers under active complaint, fraud, legal or vulnerability review",
            "Customers already contacted for this issue in the current suppression window",
        ],
        trigger=f"New signal or journey event shows unresolved {candidate.journey_stage} friction",
        recommended_channel=channel,
        content_brief=(
            "Explain the known issue, give a low-friction recovery path, avoid promises beyond verified "
            "resolution facts, and route unresolved cases to the accountable owner."
        ),
        personalization_variables=["customer_id", "account_id", "journey_stage", "owner"],
        control_group="Hold back a small eligible sample where policy and account rules allow measurement.",
        primary_success_metric=f"{stage_token}_completion_7d",
        guardrail_metrics=["repeat_signal_rate", "support_contact_rate", "unsubscribe_or_opt_out_rate"],
        consent_notes=[
            "Consent metadata is not available in imported signals.",
            "Activation requires a consent check in the destination system before customer contact.",
        ],
        governance_notes=[
            "Draft intervention only; CLARA does not send customer messages autonomously.",
            "Privacy review must approve audience criteria before export or execution.",
        ],
        audience_readiness=audience_readiness_for_candidate(candidate, destination=destination),
    )


def _signal_rate_baseline(candidate: ProblemCandidate) -> float:
    """Signals per day over the candidate's observed window (auto-captured baseline)."""
    try:
        first = datetime.fromisoformat(candidate.first_seen.replace("Z", "+00:00"))
        last = datetime.fromisoformat(candidate.last_seen.replace("Z", "+00:00"))
        observed_days = max((last - first).total_seconds() / 86_400, 1.0)
    except (ValueError, AttributeError):
        observed_days = 1.0
    return round(candidate.signal_count / observed_days, 4)


def promote_candidate(candidate: ProblemCandidate) -> ProblemRecord:
    is_theme = candidate.origin == "ai_theme" and bool(candidate.theme_tag)
    if is_theme:
        theme_tag = str(candidate.theme_tag)
        problem_id = f"PRB-DRAFT-THEME-{theme_tag.upper().replace('_', '-')}"
        # Theme contracts are measured by tag, whatever journey the signals came
        # from (measurement_scheduler.signal_matches_scope).
        primary_metric = f"signal_rate_per_day:{THEME_JOURNEY}/{theme_tag}"
        statement = candidate.theme_summary or (
            f"{candidate.signal_count} imported signals were sorted into the theme "
            f"{candidate.journey_stage}."
        )
        severity_factor = (
            candidate.triage_impact_score if candidate.triage_impact_score is not None else 0.55
        )
        limitations = [
            "AI-sorted theme: the grouping and summary are model output, accepted by a reviewer;"
            " the root cause is not confirmed.",
            "Customer value and consent metadata are not available for this draft.",
        ]
    else:
        journey_token = candidate.journey.upper().replace(" ", "-")
        stage_token = candidate.journey_stage.upper().replace(" ", "-")
        problem_id = f"PRB-DRAFT-{journey_token}-{stage_token}"
        primary_metric = (
            f"signal_rate_per_day:{candidate.journey.lower().replace(' ', '_')}"
            f"/{candidate.journey_stage.lower().replace(' ', '_')}"
        )
        statement = (
            f"{candidate.signal_count} imported signals indicate recurring friction in "
            f"{candidate.journey_stage}."
        )
        severity_factor = 0.55
        limitations = [
            "Generated from imported signals only; behavioural comparison is not attached yet.",
            "Customer value and consent metadata are not available for this draft.",
        ]
    reach = min(1.0, candidate.customer_count / 250)
    recurrence = min(1.0, candidate.signal_count / 25)
    impact_factors = {
        "customer_reach": max(0.2, reach),
        "severity": max(0.2, severity_factor),
        "recurrence": max(0.25, recurrence),
        "journey_criticality": 0.7,
        "account_exposure": min(1.0, candidate.account_count / 100),
        "financial_exposure": 0.3,
        "regulatory_risk": 0.2,
        "evidence_confidence": candidate.confidence,
    }
    score = normalized_impact_score(impact_factors)

    return ProblemRecord(
        problem_id=problem_id,
        title=candidate.title,
        statement=statement,
        journey=candidate.journey,
        journey_stage=candidate.journey_stage,
        owner=candidate.suggested_owner,
        status="validation_required",
        impact_factors=impact_factors,
        evidence_confidence=candidate.confidence,
        affected_cohort=AffectedCohort(
            customers=candidate.customer_count,
            accounts=candidate.account_count,
            high_value_accounts=0,
            date_range=f"{candidate.first_seen} to {candidate.last_seen}",
        ),
        root_cause_hypothesis=candidate.root_cause_hypothesis,
        known_limitations=limitations,
        evidence=candidate.evidence,
        origin=candidate.origin,
        theme_tag=candidate.theme_tag,
        action_proposals=[
            ActionProposal.model_validate(
                {
                    "action_id": f"ACT-{problem_id}-STRUCTURAL",
                    "class": "structural",
                    "owner": candidate.suggested_owner,
                    "destination": "jira",
                    "proposal": (
                        f"Create a Jira investigation for {candidate.journey_stage} friction "
                        "with attached evidence excerpts."
                    ),
                    "risk_level": "medium",
                    "approval_state": "needs_owner_approval",
                }
            ),
            ActionProposal.model_validate(
                {
                    "action_id": f"ACT-{problem_id}-RECOVERY",
                    "class": "customer_recovery",
                    "owner": "cx_operations",
                    "destination": "zendesk",
                    "proposal": (
                        "Draft a recovery task for customers represented in the imported signals."
                    ),
                    "risk_level": "medium",
                    "approval_state": "needs_cx_approval",
                    "depends_on": [f"ACT-{problem_id}-GOVERNANCE"],
                    "intervention_brief": intervention_brief_for_candidate(
                        candidate,
                        channel="zendesk recovery task",
                        destination="zendesk",
                    ),
                }
            ),
            ActionProposal.model_validate(
                {
                    "action_id": f"ACT-{problem_id}-JOURNEY",
                    "class": "journey_intervention",
                    "owner": "lifecycle_marketing",
                    "destination": "hubspot",
                    "proposal": (
                        f"Draft a governed intervention for customers stuck in {candidate.journey_stage} "
                        "after consent and suppression checks are confirmed."
                    ),
                    "risk_level": "high",
                    "approval_state": "needs_privacy_review",
                    "depends_on": [f"ACT-{problem_id}-GOVERNANCE"],
                    "intervention_brief": intervention_brief_for_candidate(
                        candidate,
                        channel="hubspot workflow draft",
                        destination="hubspot",
                    ),
                }
            ),
            ActionProposal.model_validate(
                {
                    "action_id": f"ACT-{problem_id}-RESEARCH",
                    "class": "research",
                    "owner": "ux_research",
                    "destination": "research_panel",
                    "proposal": "Validate the candidate root-cause hypothesis with affected customers.",
                    "risk_level": "low",
                    "approval_state": "ready_to_create",
                }
            ),
            ActionProposal.model_validate(
                {
                    "action_id": f"ACT-{problem_id}-GOVERNANCE",
                    "class": "governance",
                    "owner": "privacy_ops",
                    "destination": "policy_review",
                    "proposal": "Review evidence confidence, consent gaps and policy blockers before execution.",
                    "risk_level": "medium",
                    "approval_state": "needs_governance_review",
                }
            ),
        ],
        governance_checks=[
            GovernanceCheck(
                check_id=f"GOV-{problem_id}-EVIDENCE",
                rule="candidate_promotion_requires_evidence",
                policy_rule_id="candidate_promotion_requires_evidence",
                status="pass" if candidate.confidence >= 0.7 else "review_required",
                reason="Candidate includes evidence excerpts from imported customer signals.",
                blocking=False,
            ),
            GovernanceCheck(
                check_id=f"GOV-{problem_id}-CONTACT",
                rule="customer_contact_requires_consent_review",
                policy_rule_id="customer_contact_requires_consent_review",
                status="review_required",
                reason="Consent metadata is not available in imported signals.",
                blocking=True,
            ),
            GovernanceCheck(
                check_id=f"GOV-{problem_id}-VALID-CONSENT",
                rule="customer_contact_requires_valid_consent",
                policy_rule_id="customer_contact_requires_valid_consent",
                status="review_required",
                reason="Valid consent, lawful basis and suppression status are not attached yet.",
                blocking=True,
            ),
            GovernanceCheck(
                check_id=f"GOV-{problem_id}-AUDIENCE-PRIVACY",
                rule="audience_activation_requires_privacy_review",
                policy_rule_id="audience_activation_requires_privacy_review",
                status="review_required",
                reason="Journey interventions require privacy review before downstream activation.",
                blocking=True,
            ),
            GovernanceCheck(
                check_id=f"GOV-{problem_id}-SENSITIVE-DATA",
                rule="sensitive_attribute_inference_prohibited",
                policy_rule_id="sensitive_attribute_inference_prohibited",
                status="pass",
                reason="Generated actions do not use sensitive-category targeting criteria.",
                blocking=True,
            ),
            GovernanceCheck(
                check_id=f"GOV-{problem_id}-MARKETING-PRIVACY",
                rule="high_risk_marketing_change_requires_privacy_review",
                policy_rule_id="high_risk_marketing_change_requires_privacy_review",
                status="review_required",
                reason="High-risk lifecycle intervention changes need privacy review before approval.",
                blocking=True,
            ),
        ],
        outcome_contract=OutcomeContract(
            # Signal-derived metric with an AUTO-CAPTURED baseline: complaint inflow
            # per day for this journey/stage, computed from the candidate's own
            # signals. CLARA can re-measure this itself after the action executes
            # (scheduled T+7/T+window), so promoted problems get real, non-simulated
            # outcome data. Success = halving the complaint rate.
            primary_metric=primary_metric,
            baseline=_signal_rate_baseline(candidate),
            success_threshold=round(_signal_rate_baseline(candidate) * 0.5, 4),
            measurement_window_days=28,
            comparison_method="pre_post_signal_rate",
            guardrail_metrics=["repeat_signal_rate", "support_contact_rate"],
            responsible_owner=candidate.suggested_owner,
        ),
        impact_score=score,
        impact_band=impact_band(score),
        approval_pressure=approval_pressure("validation_required", 0),
    )


class SignalStore:
    def __init__(self) -> None:
        self._signals: dict[str, SignalRecord] = {}
        self._candidate_decisions: dict[str, CandidateDecisionRecord] = {}
        self._theme_insights: dict[str, dict] = {}

    def list_signals(self) -> list[SignalRecord]:
        return sorted(self._signals.values(), key=lambda signal: signal.timestamp)

    def update_metadata(self, signal_id: str, metadata: dict[str, str]) -> None:
        """Persist an annotation onto a stored signal. Used by the authenticity
        backfill; the record itself is never otherwise altered."""
        signal = self._signals.get(signal_id)
        if signal is not None:
            signal.metadata = dict(metadata)

    def delete_by_customer(self, customer_id: str) -> int:
        """GDPR Art. 17: remove every signal belonging to a customer."""
        doomed = [sid for sid, s in self._signals.items() if s.customer_id == customer_id]
        for signal_id in doomed:
            del self._signals[signal_id]
        return len(doomed)

    def delete_signals(self, signal_ids: list[str]) -> int:
        """Bulk-remove signals by id — the undo for a mis-mapped import batch."""
        doomed = [sid for sid in signal_ids if sid in self._signals]
        for signal_id in doomed:
            del self._signals[signal_id]
        return len(doomed)

    def import_signals(self, signals: list[SignalRecord]) -> SignalImportResult:
        imported = 0
        skipped = 0
        for signal in signals:
            if signal.signal_id in self._signals:
                skipped += 1
                continue
            self._signals[signal.signal_id] = signal
            imported += 1

        return SignalImportResult(
            imported=imported,
            skipped_duplicates=skipped,
            total_signals=len(self._signals),
        )

    def update_enrichment(
        self,
        signal_id: str,
        *,
        sentiment: str | None,
        urgency: str | None,
        tags: list[str] | None = None,
    ) -> None:
        signal = self._signals.get(signal_id)
        if signal is not None:
            self._signals[signal_id] = signal.model_copy(
                update={
                    "sentiment": sentiment,
                    "urgency": urgency,
                    "tags": list(tags or []),
                    "enriched": True,
                }
            )

    def candidates(self) -> list[ProblemCandidate]:
        signals = self.list_signals()
        return [*build_candidates(signals), *theme_candidates(self.list_theme_insights(), signals)]

    def save_theme_insights(self, insights: list[dict], *, run_id: str) -> int:
        saved = 0
        for insight in insights:
            prepared = prepare_theme_insight(insight, run_id=run_id)
            if prepared is None:
                continue
            self._theme_insights[prepared["tag"]] = prepared
            saved += 1
        return saved

    def list_theme_insights(self) -> list[dict]:
        return [self._theme_insights[tag] for tag in sorted(self._theme_insights)]

    def get_candidate_decision(self, candidate_id: str) -> CandidateDecisionRecord | None:
        return self._candidate_decisions.get(candidate_id)

    def record_candidate_decision(
        self,
        *,
        candidate_id: str,
        decision: CandidateDecisionStatus,
        reviewer: str,
        note: str | None = None,
    ) -> CandidateDecisionRecord:
        record = CandidateDecisionRecord(
            candidate_id=candidate_id,
            decision=decision,
            reviewer=reviewer,
            note=note,
            created_at=utc_now(),
        )
        self._candidate_decisions[candidate_id] = record
        return record

    def existing_signal_ids(self) -> set[str]:
        return set(self._signals.keys())


class SQLiteSignalStore:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._connection = SerializedConnection(self.path)
        self._initialize()

    def _initialize(self) -> None:
        self._connection.execute(
            """
            CREATE TABLE IF NOT EXISTS signals (
                signal_id TEXT PRIMARY KEY,
                customer_id TEXT NOT NULL,
                account_id TEXT NOT NULL,
                source TEXT NOT NULL,
                journey TEXT NOT NULL,
                journey_stage TEXT NOT NULL,
                campaign_exposure TEXT NOT NULL,
                product_events TEXT NOT NULL,
                feedback_text TEXT NOT NULL,
                language TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                metadata TEXT NOT NULL DEFAULT '{}',
                sentiment TEXT,
                urgency TEXT,
                tags TEXT NOT NULL DEFAULT '[]',
                enriched INTEGER NOT NULL DEFAULT 0
            )
            """
        )
        # Add columns to databases created before they existed.
        columns = {row["name"] for row in self._connection.execute("PRAGMA table_info(signals)")}
        if "metadata" not in columns:
            self._connection.execute(
                "ALTER TABLE signals ADD COLUMN metadata TEXT NOT NULL DEFAULT '{}'"
            )
        if "enriched" not in columns:
            self._connection.execute("ALTER TABLE signals ADD COLUMN sentiment TEXT")
            self._connection.execute("ALTER TABLE signals ADD COLUMN urgency TEXT")
            self._connection.execute(
                "ALTER TABLE signals ADD COLUMN enriched INTEGER NOT NULL DEFAULT 0"
            )
        if "tags" not in columns:
            self._connection.execute(
                "ALTER TABLE signals ADD COLUMN tags TEXT NOT NULL DEFAULT '[]'"
            )
        self._connection.execute(
            """
            CREATE TABLE IF NOT EXISTS candidate_decisions (
                candidate_id TEXT PRIMARY KEY,
                decision TEXT NOT NULL,
                reviewer TEXT NOT NULL,
                note TEXT,
                created_at TEXT NOT NULL
            )
            """
        )
        self._connection.execute(
            """
            CREATE TABLE IF NOT EXISTS theme_insights (
                theme_tag TEXT PRIMARY KEY,
                payload TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        self._connection.commit()

    def list_signals(self) -> list[SignalRecord]:
        rows = self._connection.execute("SELECT * FROM signals ORDER BY timestamp").fetchall()
        return [self._signal_from_row(row) for row in rows]

    def save_theme_insights(self, insights: list[dict], *, run_id: str) -> int:
        saved = 0
        for insight in insights:
            prepared = prepare_theme_insight(insight, run_id=run_id)
            if prepared is None:
                continue
            self._connection.execute(
                """
                INSERT INTO theme_insights (theme_tag, payload, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(theme_tag) DO UPDATE SET
                    payload = excluded.payload, updated_at = excluded.updated_at
                """,
                (prepared["tag"], json.dumps(prepared), utc_now()),
            )
            saved += 1
        self._connection.commit()
        return saved

    def list_theme_insights(self) -> list[dict]:
        rows = self._connection.execute(
            "SELECT payload FROM theme_insights ORDER BY theme_tag"
        ).fetchall()
        return [json.loads(row["payload"]) for row in rows]

    def update_enrichment(
        self,
        signal_id: str,
        *,
        sentiment: str | None,
        urgency: str | None,
        tags: list[str] | None = None,
    ) -> None:
        self._connection.execute(
            "UPDATE signals SET sentiment = ?, urgency = ?, tags = ?, enriched = 1"
            " WHERE signal_id = ?",
            (sentiment, urgency, json.dumps(list(tags or [])), signal_id),
        )
        self._connection.commit()

    def update_metadata(self, signal_id: str, metadata: dict[str, str]) -> None:
        """Persist an annotation onto a stored signal. Used by the authenticity
        backfill; the record itself is never otherwise altered."""
        self._connection.execute(
            "UPDATE signals SET metadata = ? WHERE signal_id = ?",
            (json.dumps(dict(metadata)), signal_id),
        )
        self._connection.commit()

    def delete_by_customer(self, customer_id: str) -> int:
        """GDPR Art. 17: remove every signal belonging to a customer."""
        cursor = self._connection.execute(
            "DELETE FROM signals WHERE customer_id = ?", (customer_id,)
        )
        self._connection.commit()
        return cursor.rowcount

    def delete_signals(self, signal_ids: list[str]) -> int:
        """Bulk-remove signals by id — the undo for a mis-mapped import batch."""
        if not signal_ids:
            return 0
        placeholders = ",".join("?" for _ in signal_ids)
        cursor = self._connection.execute(
            f"DELETE FROM signals WHERE signal_id IN ({placeholders})",  # noqa: S608 — placeholders only
            signal_ids,
        )
        self._connection.commit()
        return cursor.rowcount

    def import_signals(self, signals: list[SignalRecord]) -> SignalImportResult:
        imported = 0
        skipped = 0

        for signal in signals:
            try:
                self._connection.execute(
                    """
                    INSERT INTO signals (
                        signal_id,
                        customer_id,
                        account_id,
                        source,
                        journey,
                        journey_stage,
                        campaign_exposure,
                        product_events,
                        feedback_text,
                        language,
                        timestamp,
                        metadata,
                        sentiment,
                        urgency,
                        tags,
                        enriched
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        signal.signal_id,
                        signal.customer_id,
                        signal.account_id,
                        signal.source,
                        signal.journey,
                        signal.journey_stage,
                        json.dumps(signal.campaign_exposure),
                        json.dumps(signal.product_events),
                        signal.feedback_text,
                        signal.language,
                        signal.timestamp,
                        json.dumps(signal.metadata),
                        signal.sentiment,
                        signal.urgency,
                        json.dumps(signal.tags),
                        1 if signal.enriched else 0,
                    ),
                )
                imported += 1
            except sqlite3.IntegrityError:
                skipped += 1

        self._connection.commit()
        total = self._connection.execute("SELECT COUNT(*) FROM signals").fetchone()[0]
        return SignalImportResult(
            imported=imported,
            skipped_duplicates=skipped,
            total_signals=total,
        )

    def candidates(self) -> list[ProblemCandidate]:
        signals = self.list_signals()
        return [*build_candidates(signals), *theme_candidates(self.list_theme_insights(), signals)]

    def get_candidate_decision(self, candidate_id: str) -> CandidateDecisionRecord | None:
        row = self._connection.execute(
            "SELECT * FROM candidate_decisions WHERE candidate_id = ?",
            (candidate_id,),
        ).fetchone()
        if row is None:
            return None

        return self._candidate_decision_from_row(row)

    def record_candidate_decision(
        self,
        *,
        candidate_id: str,
        decision: CandidateDecisionStatus,
        reviewer: str,
        note: str | None = None,
    ) -> CandidateDecisionRecord:
        created_at = utc_now()
        self._connection.execute(
            """
            INSERT INTO candidate_decisions (candidate_id, decision, reviewer, note, created_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(candidate_id) DO UPDATE SET
                decision = excluded.decision,
                reviewer = excluded.reviewer,
                note = excluded.note,
                created_at = excluded.created_at
            """,
            (candidate_id, decision.value, reviewer, note, created_at),
        )
        self._connection.commit()
        return CandidateDecisionRecord(
            candidate_id=candidate_id,
            decision=decision,
            reviewer=reviewer,
            note=note,
            created_at=created_at,
        )

    def existing_signal_ids(self) -> set[str]:
        rows = self._connection.execute("SELECT signal_id FROM signals").fetchall()
        return {row["signal_id"] for row in rows}

    @staticmethod
    def _signal_from_row(row: sqlite3.Row) -> SignalRecord:
        return SignalRecord(
            signal_id=row["signal_id"],
            customer_id=row["customer_id"],
            account_id=row["account_id"],
            source=row["source"],
            journey=row["journey"],
            journey_stage=row["journey_stage"],
            campaign_exposure=json.loads(row["campaign_exposure"]),
            product_events=json.loads(row["product_events"]),
            feedback_text=row["feedback_text"],
            language=row["language"],
            timestamp=row["timestamp"],
            metadata=json.loads(row["metadata"]) if "metadata" in row.keys() else {},
            sentiment=row["sentiment"] if "sentiment" in row.keys() else None,
            urgency=row["urgency"] if "urgency" in row.keys() else None,
            tags=json.loads(row["tags"]) if "tags" in row.keys() else [],
            enriched=bool(row["enriched"]) if "enriched" in row.keys() else False,
        )

    @staticmethod
    def _candidate_decision_from_row(row: sqlite3.Row) -> CandidateDecisionRecord:
        return CandidateDecisionRecord(
            candidate_id=row["candidate_id"],
            decision=row["decision"],
            reviewer=row["reviewer"],
            note=row["note"],
            created_at=row["created_at"],
        )
