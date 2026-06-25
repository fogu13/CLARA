from __future__ import annotations

import csv
import io
import json
import sqlite3
from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path

from app.domain.models import (
    ActionProposal,
    AffectedCohort,
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
from app.domain.scoring import approval_pressure, impact_band, normalized_impact_score


def utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def normalize_label(value: str) -> str:
    return value.replace("_", " ").strip().title()


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


def split_multi_value(value: str | None) -> list[str]:
    if not value:
        return []

    return [item.strip() for item in value.replace("|", ";").split(";") if item.strip()]


REQUIRED_SIGNAL_FIELDS = [
    "signal_id",
    "customer_id",
    "account_id",
    "source",
    "journey",
    "journey_stage",
    "feedback_text",
    "language",
    "timestamp",
]

RECOMMENDED_SIGNAL_FIELDS = ["campaign_exposure", "product_events"]


def read_signal_csv_rows(csv_text: str) -> tuple[list[str], list[dict[str, str]]]:
    reader = csv.DictReader(io.StringIO(csv_text.strip()))
    headers = reader.fieldnames or []
    rows = [{key: value or "" for key, value in row.items() if key is not None} for row in reader]
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

    for field in [*REQUIRED_SIGNAL_FIELDS, *RECOMMENDED_SIGNAL_FIELDS]:
        if field not in headers:
            errors.append(
                SignalValidationIssue(
                    severity="error",
                    field=field,
                    message=f"Missing required column: {field}.",
                )
            )

    for row_index, row in enumerate(rows, start=2):
        signal_id = row.get("signal_id", "").strip()
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


def parse_signal_csv(csv_text: str) -> list[SignalRecord]:
    reader = csv.DictReader(io.StringIO(csv_text.strip()))
    signals: list[SignalRecord] = []

    for index, row in enumerate(reader, start=1):
        signals.append(
            SignalRecord(
                signal_id=row.get("signal_id") or f"CSV-{index:04d}",
                customer_id=row.get("customer_id") or "unknown_customer",
                account_id=row.get("account_id") or "unknown_account",
                source=row.get("source") or "csv_upload",
                journey=row.get("journey") or "unknown_journey",
                journey_stage=row.get("journey_stage") or "unknown_stage",
                campaign_exposure=split_multi_value(row.get("campaign_exposure")),
                product_events=split_multi_value(row.get("product_events")),
                feedback_text=row.get("feedback_text") or "",
                language=row.get("language") or "unknown",
                timestamp=row.get("timestamp") or "1970-01-01T00:00:00Z",
            )
        )

    return signals


def build_candidates(signals: list[SignalRecord]) -> list[ProblemCandidate]:
    grouped: dict[tuple[str, str], list[SignalRecord]] = defaultdict(list)
    for signal in signals:
        grouped[(signal.journey, signal.journey_stage)].append(signal)

    candidates: list[ProblemCandidate] = []
    for (journey, journey_stage), group in grouped.items():
        sorted_group = sorted(group, key=lambda signal: signal.timestamp)
        customers = {signal.customer_id for signal in group}
        accounts = {signal.account_id for signal in group}
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


def intervention_brief_for_candidate(candidate: ProblemCandidate, *, channel: str) -> InterventionBrief:
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
    )


def promote_candidate(candidate: ProblemCandidate) -> ProblemRecord:
    journey_token = candidate.journey.upper().replace(" ", "-")
    stage_token = candidate.journey_stage.upper().replace(" ", "-")
    problem_id = f"PRB-DRAFT-{journey_token}-{stage_token}"
    reach = min(1.0, candidate.customer_count / 250)
    recurrence = min(1.0, candidate.signal_count / 25)
    impact_factors = {
        "customer_reach": max(0.2, reach),
        "severity": 0.55,
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
        statement=(
            f"{candidate.signal_count} imported signals indicate recurring friction in "
            f"{candidate.journey_stage}."
        ),
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
        known_limitations=[
            "Generated from imported signals only; behavioural comparison is not attached yet.",
            "Customer value and consent metadata are not available for this draft.",
        ],
        evidence=candidate.evidence,
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
            primary_metric=f"{candidate.journey_stage.lower().replace(' ', '_')}_completion_7d",
            baseline=0.0,
            success_threshold=0.1,
            measurement_window_days=28,
            comparison_method="baseline_required",
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

    def list_signals(self) -> list[SignalRecord]:
        return sorted(self._signals.values(), key=lambda signal: signal.timestamp)

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

    def candidates(self) -> list[ProblemCandidate]:
        return build_candidates(self.list_signals())

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
        self._connection = sqlite3.connect(self.path, check_same_thread=False)
        self._connection.row_factory = sqlite3.Row
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
                timestamp TEXT NOT NULL
            )
            """
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
        self._connection.commit()

    def list_signals(self) -> list[SignalRecord]:
        rows = self._connection.execute("SELECT * FROM signals ORDER BY timestamp").fetchall()
        return [self._signal_from_row(row) for row in rows]

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
                        timestamp
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
        return build_candidates(self.list_signals())

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
