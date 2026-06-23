from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ProblemStatus(str, Enum):
    approval_needed = "approval_needed"
    blocked_by_policy = "blocked_by_policy"
    validation_required = "validation_required"
    in_progress = "in_progress"
    resolved = "resolved"


class TaxonomyType(str, Enum):
    product = "product"
    journey = "journey"
    contact_reason = "contact_reason"
    marketing = "marketing"
    compliance = "compliance"


class TaxonomyOperation(str, Enum):
    merge = "merge"
    split = "split"
    rename = "rename"
    lock = "lock"


class TaxonomyChange(BaseModel):
    change_id: str
    operation: TaxonomyOperation
    description: str
    actor: str
    changed_at: str


class TaxonomyCategory(BaseModel):
    category_id: str
    label: str
    description: str
    terms: list[str] = Field(default_factory=list)
    parent_id: str | None = None
    locked: bool = False
    status: str = "active"
    change_history: list[TaxonomyChange] = Field(default_factory=list)


class TaxonomyCatalog(BaseModel):
    taxonomy_type: TaxonomyType
    version: str
    locale_support: list[str]
    categories: list[TaxonomyCategory]
    known_limitations: list[str] = Field(default_factory=list)


class TaxonomyClassification(BaseModel):
    taxonomy_type: TaxonomyType
    category_id: str
    label: str
    confidence: float = Field(ge=0.0, le=1.0)
    evidence_signal_ids: list[str] = Field(default_factory=list)
    matched_terms: list[str] = Field(default_factory=list)
    language_notes: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    contradictory_evidence: list[str] = Field(default_factory=list)


class TerminologyDictionaryEntry(BaseModel):
    term_id: str
    canonical_term: str
    aliases: list[str] = Field(default_factory=list)
    languages: list[str] = Field(default_factory=list)
    taxonomy_type: TaxonomyType
    category_ids: list[str] = Field(default_factory=list)
    definition: str
    usage_notes: list[str] = Field(default_factory=list)


class RootCauseEvidenceFactor(BaseModel):
    factor_type: str
    label: str
    confidence: float = Field(ge=0.0, le=1.0)
    signal_ids: list[str] = Field(default_factory=list)
    explanation: str


class RootCauseAnalysis(BaseModel):
    hypothesis: str
    confidence: float = Field(ge=0.0, le=1.0)
    factors: list[RootCauseEvidenceFactor] = Field(default_factory=list)
    alternative_hypotheses: list[str] = Field(default_factory=list)
    validation_questions: list[str] = Field(default_factory=list)


class TaxonomyRenameRequest(BaseModel):
    category_id: str
    label: str = Field(min_length=1)
    description: str | None = None
    actor: str = "taxonomy_owner"


class TaxonomyLockRequest(BaseModel):
    category_id: str
    actor: str = "taxonomy_owner"


class TaxonomyMergeRequest(BaseModel):
    source_category_ids: list[str] = Field(min_length=2)
    target_category_id: str
    target_label: str | None = None
    target_description: str | None = None
    actor: str = "taxonomy_owner"


class TaxonomySplitCategoryRequest(BaseModel):
    category_id: str
    label: str = Field(min_length=1)
    description: str = Field(min_length=1)
    terms: list[str] = Field(default_factory=list)


class TaxonomySplitRequest(BaseModel):
    source_category_id: str
    categories: list[TaxonomySplitCategoryRequest] = Field(min_length=2)
    actor: str = "taxonomy_owner"


class ActionClass(str, Enum):
    structural = "structural"
    customer_recovery = "customer_recovery"
    journey_intervention = "journey_intervention"
    research = "research"
    governance = "governance"


class RiskLevel(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


class GovernanceStatus(str, Enum):
    pass_ = "pass"
    fail = "fail"
    review_required = "review_required"


class ApprovalDecisionStatus(str, Enum):
    approved = "approved"
    rejected = "rejected"
    needs_more_evidence = "needs_more_evidence"


class ExecutionStatus(str, Enum):
    draft_created = "draft_created"
    blocked = "blocked"
    not_started = "not_started"
    completed = "completed"


class LearningStatus(str, Enum):
    worked = "worked"
    partially_worked = "partially_worked"
    did_not_work = "did_not_work"
    inconclusive = "inconclusive"
    measurement_invalid = "measurement_invalid"


class ImpactFactors(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    customer_reach: float = Field(ge=0.0, le=1.0)
    severity: float = Field(ge=0.0, le=1.0)
    recurrence: float = Field(ge=0.0, le=1.0)
    journey_criticality: float = Field(ge=0.0, le=1.0)
    account_exposure: float = Field(ge=0.0, le=1.0)
    financial_exposure: float = Field(ge=0.0, le=1.0)
    regulatory_risk: float = Field(ge=0.0, le=1.0)
    evidence_confidence: float = Field(ge=0.0, le=1.0)


class Evidence(BaseModel):
    signal_id: str
    source: str
    language: str
    excerpt: str
    customer_id: str
    account_id: str
    timestamp: str


class AffectedCohort(BaseModel):
    customers: int = Field(ge=0)
    accounts: int = Field(ge=0)
    high_value_accounts: int = Field(ge=0)
    date_range: str


class ContextImpactSummary(BaseModel):
    matched_customers: int = Field(ge=0)
    matched_accounts: int = Field(ge=0)
    high_value_accounts: int = Field(ge=0)
    total_account_value: float = Field(ge=0.0)
    average_health_score: float | None = Field(default=None, ge=0.0, le=1.0)
    consent_risk_customers: int = Field(ge=0)
    renewal_risk_accounts: int = Field(default=0, ge=0)
    priority_lifecycle_accounts: int = Field(default=0, ge=0)
    at_risk_lifecycle_accounts: int = Field(default=0, ge=0)
    owners: list[str] = Field(default_factory=list)
    product_owners: list[str] = Field(default_factory=list)
    regions: list[str] = Field(default_factory=list)
    score_delta: float = Field(default=0.0, ge=0.0, le=1.0)
    drivers: list[str] = Field(default_factory=list)


class ActionProposal(BaseModel):
    action_id: str
    class_: ActionClass = Field(alias="class")
    owner: str
    destination: str
    proposal: str
    risk_level: RiskLevel
    approval_state: str


class GovernanceCheck(BaseModel):
    check_id: str
    rule: str
    policy_rule_id: str | None = None
    status: GovernanceStatus
    reason: str
    blocking: bool


class PolicyRule(BaseModel):
    rule_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    description: str = Field(min_length=1)
    category: str = Field(min_length=1)
    severity: RiskLevel
    applies_to_action_classes: list[ActionClass] = Field(default_factory=list)
    applies_to_destinations: list[str] = Field(default_factory=list)
    required_evidence: list[str] = Field(default_factory=list)
    default_blocking: bool
    owner: str = Field(min_length=1)
    version: str = Field(min_length=1)
    status: str = "active"


class OutcomeContract(BaseModel):
    primary_metric: str
    baseline: float
    success_threshold: float
    measurement_window_days: int = Field(gt=0)
    comparison_method: str
    guardrail_metrics: list[str]
    responsible_owner: str


class ProblemRecord(BaseModel):
    problem_id: str
    title: str
    statement: str
    journey: str
    journey_stage: str
    owner: str
    status: ProblemStatus
    impact_factors: ImpactFactors
    evidence_confidence: float = Field(ge=0.0, le=1.0)
    affected_cohort: AffectedCohort
    root_cause_hypothesis: str
    known_limitations: list[str]
    evidence: list[Evidence]
    action_proposals: list[ActionProposal]
    governance_checks: list[GovernanceCheck]
    outcome_contract: OutcomeContract
    impact_score: float | None = Field(default=None, ge=0.0, le=1.0)
    impact_band: str | None = None
    approval_pressure: str | None = None
    context_impact: ContextImpactSummary | None = None


class ProblemSummary(BaseModel):
    problem_id: str
    title: str
    journey: str
    journey_stage: str
    owner: str
    status: ProblemStatus
    impact_score: float
    impact_band: str
    evidence_confidence: float
    affected_customers: int
    affected_accounts: int
    approval_pressure: str
    top_action_classes: list[ActionClass]
    context_impact: ContextImpactSummary | None = None


class ProblemUpdateRequest(BaseModel):
    title: str | None = Field(default=None, min_length=1)
    statement: str | None = Field(default=None, min_length=1)
    owner: str | None = Field(default=None, min_length=1)
    root_cause_hypothesis: str | None = Field(default=None, min_length=1)


class ActionProposalUpdateRequest(BaseModel):
    owner: str | None = Field(default=None, min_length=1)
    destination: str | None = Field(default=None, min_length=1)
    proposal: str | None = Field(default=None, min_length=1)
    risk_level: RiskLevel | None = None
    approval_state: str | None = Field(default=None, min_length=1)


class ProblemTransitionRequest(BaseModel):
    target_status: ProblemStatus
    actor: str = Field(min_length=1)
    note: str | None = Field(default=None, min_length=1)


class ProblemTransitionRecord(BaseModel):
    transition_id: str
    problem_id: str
    from_status: ProblemStatus
    to_status: ProblemStatus
    actor: str
    note: str | None = None
    created_at: str


class TimelineEvent(BaseModel):
    event_id: str
    problem_id: str
    event_type: str
    label: str
    detail: str
    actor: str | None = None
    created_at: str


class ApprovalDecision(BaseModel):
    action_id: str
    decision: ApprovalDecisionStatus
    reviewer: str
    note: str | None = None


class ApprovalRecord(ApprovalDecision):
    decision_id: str
    problem_id: str
    created_at: str


class ExecutionRecord(BaseModel):
    execution_id: str
    problem_id: str
    action_id: str
    destination: str
    status: ExecutionStatus
    owner: str
    summary: str
    created_at: str


class JiraIssueDraft(BaseModel):
    draft_id: str
    problem_id: str
    action_id: str
    execution_id: str
    project_key: str
    issue_type: str
    summary: str
    description: str
    labels: list[str]
    assignee: str
    status: str
    created_at: str


class OutcomeMeasurement(BaseModel):
    problem_id: str
    metric: str
    observed_value: float
    measured_at: str
    notes: str | None = None


LEARNING_RETENTION_DAYS = 730


def retention_expires_at(created_at: str, days: int = LEARNING_RETENTION_DAYS) -> str:
    created = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
    expires_at = (created + timedelta(days=days)).astimezone(timezone.utc)
    return expires_at.isoformat().replace("+00:00", "Z")


def redact_common_pii(value: str | None) -> str | None:
    if value is None:
        return None

    redacted = value
    patterns = [
        (r"\b\S+@\S+\b", "[EMAIL REDACTED]"),
        (r"\b(?:\d{1,3}\.){3}\d{1,3}\b", "[IP REDACTED]"),
        (r"(?<!\w)(?:\+?\d[\d .()/-]{7,}\d)(?!\w)", "[PHONE REDACTED]"),
        (r"\b(?:CUST|CUSTOMER|ACC|ACCOUNT)-[A-Za-z0-9_-]+\b", "[ID REDACTED]"),
        (
            r"\b\d{1,6}\s+[A-Za-z0-9 .'-]+\s+"
            r"(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Lane|Ln|Drive|Dr)\b",
            "[ADDRESS REDACTED]",
        ),
    ]
    for pattern, replacement in patterns:
        redacted = re.sub(pattern, replacement, redacted, flags=re.IGNORECASE)
    return redacted.strip()


def pseudonymized_identifier(value: str, field_name: str) -> str:
    redacted = redact_common_pii(value)
    if not redacted:
        raise ValueError(f"{field_name} is required.")
    if redacted != value.strip():
        raise ValueError(f"{field_name} must be a pseudonymized identifier.")
    return redacted


class LearningConclusionRequest(BaseModel):
    learning_status: LearningStatus
    summary: str = Field(min_length=1, max_length=2000)
    limitations: str = Field(min_length=1, max_length=2000)
    next_step: str | None = Field(default=None, max_length=1000)

    @field_validator("summary", "limitations", "next_step")
    @classmethod
    def redact_free_text(cls, value: str | None) -> str | None:
        # ponytail: stdlib heuristics only; dedicated DSR tooling if free text expands.
        redacted = redact_common_pii(value)
        if value is not None and not redacted:
            raise ValueError("Text fields cannot be blank.")
        return redacted


class LearningConclusionRecord(LearningConclusionRequest):
    conclusion_id: str
    problem_id: str
    tenant_id: str
    reviewer: str
    reviewed_at: str
    retention_expires_at: str

    @field_validator("tenant_id", "reviewer")
    @classmethod
    def identifiers_must_be_pseudonymized(cls, value: str) -> str:
        return pseudonymized_identifier(value, "Identifier")


class OutcomeSnapshot(BaseModel):
    problem_id: str
    metric: str
    baseline: float
    success_threshold: float
    latest_value: float | None = None
    status: str
    improvement_direction: Literal["increase", "decrease"]
    measurement_window_days: int
    comparison_method: str


class OutcomeBoardItem(BaseModel):
    problem_id: str
    title: str
    owner: str
    problem_status: ProblemStatus
    impact_score: float
    impact_band: str
    metric: str
    baseline: float
    success_threshold: float
    latest_value: float | None = None
    outcome_status: str
    improvement_direction: Literal["increase", "decrease"]
    latest_learning_status: LearningStatus | None = None
    latest_learning_reviewed_at: str | None = None
    measurement_window_days: int
    comparison_method: str
    responsible_owner: str


class OutcomeBoard(BaseModel):
    total: int
    not_measured: int
    not_improved: int
    improving: int
    target_met: int
    learning_worked: int = 0
    learning_partially_worked: int = 0
    learning_did_not_work: int = 0
    learning_inconclusive: int = 0
    learning_measurement_invalid: int = 0
    items: list[OutcomeBoardItem]


class WorkflowState(BaseModel):
    problem_id: str
    approvals: list[ApprovalRecord]
    executions: list[ExecutionRecord]
    jira_issue_drafts: list[JiraIssueDraft]
    outcome: OutcomeSnapshot
    learning_conclusions: list[LearningConclusionRecord]
    timeline: list[TimelineEvent]


class SignalRecord(BaseModel):
    signal_id: str
    customer_id: str
    account_id: str
    source: str
    journey: str
    journey_stage: str
    campaign_exposure: list[str] = Field(default_factory=list)
    product_events: list[str] = Field(default_factory=list)
    feedback_text: str
    language: str
    timestamp: str


class SignalImportRequest(BaseModel):
    signals: list[SignalRecord]


class SignalCsvImportRequest(BaseModel):
    csv_text: str = Field(min_length=1)


class SignalValidationIssue(BaseModel):
    severity: str
    row_number: int | None = None
    field: str | None = None
    message: str


class SignalValidationReport(BaseModel):
    valid: bool
    total_rows: int
    importable_rows: int
    errors: list[SignalValidationIssue]
    warnings: list[SignalValidationIssue]


class SignalImportResult(BaseModel):
    imported: int
    skipped_duplicates: int
    total_signals: int


class CandidateReviewStatus(str, Enum):
    pending = "pending"
    duplicate = "duplicate"
    accepted = "accepted"
    rejected = "rejected"


class CandidateDecisionStatus(str, Enum):
    accepted = "accepted"
    rejected = "rejected"


class CandidateReviewRequest(BaseModel):
    reviewer: str = Field(min_length=1)
    note: str | None = Field(default=None, min_length=1)


class CandidateDecisionRecord(BaseModel):
    candidate_id: str
    decision: CandidateDecisionStatus
    reviewer: str
    note: str | None = None
    created_at: str


class CustomerContextRecord(BaseModel):
    customer_id: str = Field(min_length=1)
    account_id: str = Field(min_length=1)
    account_name: str | None = None
    parent_account_id: str | None = None
    parent_account_name: str | None = None
    segment: str | None = None
    lifecycle_stage: str | None = None
    plan_tier: str | None = None
    contact_role: str | None = None
    account_value: float = Field(default=0.0, ge=0.0)
    renewal_date: str | None = None
    consent_status: str = "unknown"
    health_score: float | None = Field(default=None, ge=0.0, le=1.0)
    owner: str | None = None
    product_owner: str | None = None
    region: str | None = None


class ContextDataQualityWarning(BaseModel):
    warning_id: str
    severity: str
    field: str
    message: str
    customer_ids: list[str] = Field(default_factory=list)
    account_ids: list[str] = Field(default_factory=list)


class ContextRoutingRecommendation(BaseModel):
    owner: str
    priority: str
    reason: str
    customer_ids: list[str] = Field(default_factory=list)
    account_ids: list[str] = Field(default_factory=list)
    contact_roles: list[str] = Field(default_factory=list)


class AffectedAccountSummary(BaseModel):
    account_id: str
    account_name: str | None = None
    parent_account_id: str | None = None
    parent_account_name: str | None = None
    customer_count: int = Field(ge=0)
    account_value: float = Field(ge=0.0)
    high_value: bool
    consent_risk_customers: int = Field(ge=0)
    average_health_score: float | None = Field(default=None, ge=0.0, le=1.0)
    contact_roles: list[str] = Field(default_factory=list)
    lifecycle_stages: list[str] = Field(default_factory=list)
    plan_tiers: list[str] = Field(default_factory=list)
    renewal_dates: list[str] = Field(default_factory=list)
    owners: list[str] = Field(default_factory=list)
    product_owners: list[str] = Field(default_factory=list)
    regions: list[str] = Field(default_factory=list)


class AffectedContextExplorer(BaseModel):
    problem_id: str
    context_impact: ContextImpactSummary | None = None
    accounts: list[AffectedAccountSummary]
    customers: list[CustomerContextRecord]
    missing_customer_ids: list[str]
    missing_account_ids: list[str]
    warnings: list[ContextDataQualityWarning]
    routing_recommendations: list[ContextRoutingRecommendation]


class CustomerContextImportRequest(BaseModel):
    records: list[CustomerContextRecord]


class CustomerContextCsvImportRequest(BaseModel):
    csv_text: str = Field(min_length=1)


class CustomerContextImportResult(BaseModel):
    imported: int
    updated: int
    total_context_records: int


class CustomerContextValidationReport(BaseModel):
    valid: bool
    total_rows: int
    importable_rows: int
    errors: list[SignalValidationIssue]
    warnings: list[SignalValidationIssue]


class ContextCompletenessMetric(BaseModel):
    field: str
    label: str
    populated_records: int = Field(ge=0)
    total_records: int = Field(ge=0)
    coverage: float = Field(ge=0.0, le=1.0)
    importance: str


class CustomerContextCompletenessReport(BaseModel):
    total_records: int = Field(ge=0)
    total_accounts: int = Field(ge=0)
    complete_records: int = Field(ge=0)
    readiness_score: float = Field(ge=0.0, le=1.0)
    readiness_level: str
    metrics: list[ContextCompletenessMetric]
    warnings: list[SignalValidationIssue]


class DemoDatasetSummary(BaseModel):
    dataset_id: str
    title: str
    description: str
    industry: str
    signal_count: int
    context_count: int
    journeys: list[str]


class DemoDataset(BaseModel):
    dataset_id: str
    title: str
    description: str
    industry: str
    signals: list[SignalRecord]
    customer_context: list[CustomerContextRecord]


class DemoDatasetImportResult(BaseModel):
    dataset_id: str
    title: str
    signals: SignalImportResult
    customer_context: CustomerContextImportResult


class ProblemCandidate(BaseModel):
    candidate_id: str
    title: str
    journey: str
    journey_stage: str
    signal_count: int
    customer_count: int
    account_count: int
    sources: list[str]
    languages: list[str]
    first_seen: str
    last_seen: str
    confidence: float = Field(ge=0.0, le=1.0)
    evidence: list[Evidence]
    root_cause_hypothesis: str
    root_cause_analysis: RootCauseAnalysis | None = None
    suggested_owner: str
    suggested_action: str
    taxonomy_version: str | None = None
    classifications: list[TaxonomyClassification] = Field(default_factory=list)
    terminology_hits: list[str] = Field(default_factory=list)
    contradictory_evidence: list[str] = Field(default_factory=list)
    known_limitations: list[str] = Field(default_factory=list)
    evaluation_notes: list[str] = Field(default_factory=list)
    emerging_problem_score: float = Field(default=0.0, ge=0.0, le=1.0)
    review_status: CandidateReviewStatus = CandidateReviewStatus.pending
    duplicate_problem_id: str | None = None
    duplicate_reason: str | None = None
    reviewer: str | None = None
    review_note: str | None = None
    reviewed_at: str | None = None


class EmergingProblemSignal(BaseModel):
    candidate_id: str
    title: str
    journey: str
    journey_stage: str
    emerging_score: float = Field(ge=0.0, le=1.0)
    trend_label: str
    signal_count: int = Field(ge=0)
    source_count: int = Field(ge=0)
    customer_count: int = Field(ge=0)
    account_count: int = Field(ge=0)
    first_seen: str
    last_seen: str
    taxonomy_labels: list[str] = Field(default_factory=list)
    drivers: list[str] = Field(default_factory=list)
    recommended_next_step: str


class EmergingProblemReport(BaseModel):
    generated_at: str
    candidate_count: int = Field(ge=0)
    watch_count: int = Field(ge=0)
    action_count: int = Field(ge=0)
    signals: list[EmergingProblemSignal] = Field(default_factory=list)
