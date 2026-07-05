export type ProblemStatus =
  | "approval_needed"
  | "blocked_by_policy"
  | "validation_required"
  | "in_progress"
  | "resolved";

export type ActionClass =
  | "structural"
  | "customer_recovery"
  | "journey_intervention"
  | "research"
  | "governance";

export type RiskLevel = "low" | "medium" | "high" | "critical";

export type GovernanceStatus = "pass" | "fail" | "review_required";

export type ApprovalDecisionStatus = "approved" | "rejected" | "needs_more_evidence";

export type TaxonomyType = "product" | "journey" | "contact_reason" | "marketing" | "compliance";

export type TaxonomyOperation = "merge" | "split" | "rename" | "lock";

export type TaxonomyChange = {
  change_id: string;
  operation: TaxonomyOperation;
  description: string;
  actor: string;
  changed_at: string;
};

export type TaxonomyCategory = {
  category_id: string;
  label: string;
  description: string;
  terms: string[];
  parent_id?: string | null;
  locked: boolean;
  status: string;
  change_history: TaxonomyChange[];
  confidence?: number | null;
  evidence_count?: number | null;
};

export type TaxonomyBootstrapReport = {
  scanned: number;
  clusters: number;
  proposed: number;
  skipped: number;
  proposals: {
    category_id: string;
    label: string;
    description: string;
    confidence: number;
    evidence_count: number;
    signal_ids: string[];
    samples: string[];
  }[];
};

export type TaxonomyCatalog = {
  taxonomy_type: TaxonomyType;
  version: string;
  locale_support: string[];
  categories: TaxonomyCategory[];
  known_limitations: string[];
};

export type TaxonomyClassification = {
  taxonomy_type: TaxonomyType;
  category_id: string;
  label: string;
  confidence: number;
  evidence_signal_ids: string[];
  matched_terms: string[];
  language_notes: string[];
  limitations: string[];
  contradictory_evidence: string[];
};

export type ImpactFactors = {
  customer_reach: number;
  severity: number;
  recurrence: number;
  journey_criticality: number;
  account_exposure: number;
  financial_exposure: number;
  regulatory_risk: number;
  evidence_confidence: number;
};

export type TerminologyDictionaryEntry = {
  term_id: string;
  canonical_term: string;
  aliases: string[];
  languages: string[];
  taxonomy_type: TaxonomyType;
  category_ids: string[];
  definition: string;
  usage_notes: string[];
};

export type LanguageQualityRow = {
  language: string;
  signal_count: number;
  terminology_entries: number;
  original_language_evidence: number;
  readiness: "ready" | "needs_attention" | string;
};

export type LanguageQualityReport = {
  total_signals: number;
  languages: LanguageQualityRow[];
  german_english_ready: boolean;
};

export type EmergingProblemSignal = {
  candidate_id: string;
  title: string;
  journey: string;
  journey_stage: string;
  emerging_score: number;
  trend_label: "watch" | "action" | string;
  signal_count: number;
  source_count: number;
  customer_count: number;
  account_count: number;
  first_seen: string;
  last_seen: string;
  taxonomy_labels: string[];
  drivers: string[];
  recommended_next_step: string;
};

export type EmergingProblemReport = {
  generated_at: string;
  candidate_count: number;
  watch_count: number;
  action_count: number;
  signals: EmergingProblemSignal[];
};

export type RootCauseEvidenceFactor = {
  factor_type: string;
  label: string;
  confidence: number;
  signal_ids: string[];
  explanation: string;
};

export type RootCauseAnalysis = {
  hypothesis: string;
  confidence: number;
  factors: RootCauseEvidenceFactor[];
  alternative_hypotheses: string[];
  validation_questions: string[];
};

export type Evidence = {
  signal_id: string;
  source: string;
  language: string;
  excerpt: string;
  customer_id: string;
  account_id: string;
  timestamp: string;
};

export type AffectedCohort = {
  customers: number;
  accounts: number;
  high_value_accounts: number;
  date_range: string;
};

export type JourneyEventRecord = {
  event_id: string;
  customer_id: string;
  account_id: string;
  journey: string;
  journey_stage: string;
  event_name: string;
  event_type: string;
  timestamp: string;
  success?: boolean | null;
  duration_seconds?: number | null;
  metadata: Record<string, string>;
};

export type JourneyEventImportResult = {
  imported: number;
  skipped_duplicates: number;
  total_events: number;
};

export type JourneyImpactSummary = {
  matched_events: number;
  matched_customers: number;
  matched_accounts: number;
  friction_events: number;
  deviation_score: number;
  top_event_names: string[];
  drivers: string[];
};

export type ContextImpactSummary = {
  matched_customers: number;
  matched_accounts: number;
  high_value_accounts: number;
  total_account_value: number;
  average_health_score?: number | null;
  consent_risk_customers: number;
  renewal_risk_accounts: number;
  priority_lifecycle_accounts: number;
  at_risk_lifecycle_accounts: number;
  owners: string[];
  product_owners: string[];
  regions: string[];
  score_delta: number;
  drivers: string[];
};

export type AudienceReadiness = {
  estimated_audience_size: number;
  eligible_customers: number;
  excluded_customers: number;
  consent_ready_customers: number;
  suppression_excluded_customers: number;
  over_contact_risk: "low" | "medium" | "high";
  readiness_status: "ready_for_review" | "needs_consent_review" | "blocked_by_policy";
  readiness_reasons: string[];
  export_destination: string;
  export_format: string;
  export_fields: string[];
  activation_constraints: string[];
};

export type InterventionBrief = {
  audience_summary: string;
  inclusion_criteria: string[];
  exclusion_criteria: string[];
  trigger: string;
  recommended_channel: string;
  content_brief: string;
  personalization_variables: string[];
  control_group: string;
  primary_success_metric: string;
  guardrail_metrics: string[];
  consent_notes: string[];
  governance_notes: string[];
  audience_readiness?: AudienceReadiness | null;
};

export type ActionProposalSnapshot = {
  action_id: string;
  class: ActionClass;
  owner: string;
  destination: string;
  proposal: string;
  risk_level: RiskLevel;
  approval_state: string;
  depends_on: string[];
  intervention_brief?: InterventionBrief | null;
};

export type ActionProposalChange = {
  field: string;
  before: string;
  after: string;
};

export type ActionProposal = {
  action_id: string;
  class: ActionClass;
  owner: string;
  destination: string;
  proposal: string;
  risk_level: RiskLevel;
  approval_state: string;
  depends_on?: string[];
  intervention_brief?: InterventionBrief | null;
  original_snapshot?: ActionProposalSnapshot | null;
};

export type GovernanceCheck = {
  check_id: string;
  rule: string;
  policy_rule_id?: string | null;
  status: GovernanceStatus;
  reason: string;
  blocking: boolean;
};

export type PolicyRule = {
  rule_id: string;
  title: string;
  description: string;
  category: string;
  severity: RiskLevel;
  applies_to_action_classes: ActionClass[];
  applies_to_destinations: string[];
  required_evidence: string[];
  default_blocking: boolean;
  owner: string;
  version: string;
  status: string;
};

export type OutcomeContract = {
  primary_metric: string;
  baseline: number;
  success_threshold: number;
  measurement_window_days: number;
  comparison_method: string;
  guardrail_metrics: string[];
  responsible_owner: string;
};

export type ProblemRecord = {
  problem_id: string;
  title: string;
  statement: string;
  journey: string;
  journey_stage: string;
  owner: string;
  status: ProblemStatus;
  impact_factors: ImpactFactors;
  evidence_confidence: number;
  affected_cohort: AffectedCohort;
  root_cause_hypothesis: string;
  known_limitations: string[];
  evidence: Evidence[];
  action_proposals: ActionProposal[];
  governance_checks: GovernanceCheck[];
  outcome_contract: OutcomeContract;
  impact_score?: number;
  impact_band?: string;
  approval_pressure?: string;
  context_impact?: ContextImpactSummary | null;
  journey_impact?: JourneyImpactSummary | null;
};

export type ProblemSummary = {
  problem_id: string;
  title: string;
  journey: string;
  journey_stage: string;
  owner: string;
  status: ProblemStatus;
  impact_score: number;
  impact_band: string;
  evidence_confidence: number;
  affected_customers: number;
  affected_accounts: number;
  approval_pressure: string;
  top_action_classes: ActionClass[];
  context_impact?: ContextImpactSummary | null;
  journey_impact?: JourneyImpactSummary | null;
};

export type ProblemUpdateRequest = {
  title?: string;
  statement?: string;
  owner?: string;
  root_cause_hypothesis?: string;
};

export type ActionProposalUpdateRequest = {
  owner?: string;
  destination?: string;
  proposal?: string;
  risk_level?: RiskLevel;
  approval_state?: string;
  intervention_brief?: InterventionBrief | null;
};

export type ProblemTransitionRequest = {
  target_status: ProblemStatus;
  actor: string;
  note?: string;
};

export type ProblemTransitionRecord = {
  transition_id: string;
  problem_id: string;
  from_status: ProblemStatus;
  to_status: ProblemStatus;
  actor: string;
  note?: string | null;
  created_at: string;
};

export type ApprovalDecision = {
  action_id: string;
  decision: ApprovalDecisionStatus;
  reviewer: string;
  note?: string;
};

export type ApprovalRecord = ApprovalDecision & {
  decision_id: string;
  problem_id: string;
  created_at: string;
  action_snapshot?: ActionProposalSnapshot | null;
  action_diff: ActionProposalChange[];
};

export type ExecutionRecord = {
  execution_id: string;
  problem_id: string;
  action_id: string;
  destination: string;
  status: "draft_created" | "blocked" | "not_started" | "completed";
  owner: string;
  summary: string;
  created_at: string;
};

export type ClosureRecordRequest = {
  operational_status: "not_started" | "draft_created" | "in_progress" | "released" | "verified";
  customer_status: "not_started" | "not_eligible" | "draft_ready" | "contacted" | "unresolved";
  owner: string;
  verified_resolution_facts: string[];
  unresolved_customers: number;
  follow_up_channel: string;
  response_draft?: string | null;
  limitations: string[];
};

export type ClosureRecord = ClosureRecordRequest & {
  closure_id: string;
  problem_id: string;
  tenant_id: string;
  actor: string;
  customer_closure_eligible: boolean;
  response_draft?: string | null;
  created_at: string;
};

export type JiraIssueDraft = {
  draft_id: string;
  problem_id: string;
  action_id: string;
  execution_id: string;
  project_key: string;
  issue_type: string;
  summary: string;
  description: string;
  labels: string[];
  assignee: string;
  status: string;
  created_at: string;
};

export type OutcomeSnapshot = {
  problem_id: string;
  metric: string;
  baseline: number;
  success_threshold: number;
  latest_value?: number | null;
  status: "not_measured" | "target_met" | "improving" | "not_improved";
  improvement_direction: "increase" | "decrease";
  measurement_window_days: number;
  comparison_method: string;
};

export type OutcomeBoardItem = {
  problem_id: string;
  title: string;
  owner: string;
  problem_status: ProblemStatus;
  impact_score: number;
  impact_band: string;
  metric: string;
  baseline: number;
  success_threshold: number;
  latest_value?: number | null;
  outcome_status: OutcomeSnapshot["status"];
  improvement_direction: OutcomeSnapshot["improvement_direction"];
  latest_learning_status?: LearningStatus | null;
  latest_learning_reviewed_at?: string | null;
  measurement_window_days: number;
  comparison_method: string;
  responsible_owner: string;
};

export type LearningStatus =
  | "worked"
  | "partially_worked"
  | "did_not_work"
  | "inconclusive"
  | "measurement_invalid";

export type OutcomeBoard = {
  total: number;
  not_measured: number;
  not_improved: number;
  improving: number;
  target_met: number;
  learning_worked: number;
  learning_partially_worked: number;
  learning_did_not_work: number;
  learning_inconclusive: number;
  learning_measurement_invalid: number;
  items: OutcomeBoardItem[];
};

export type OutcomeMeasurement = {
  problem_id: string;
  metric: string;
  observed_value: number;
  measured_at: string;
  notes?: string;
};

export type LearningConclusionRequest = {
  learning_status: LearningStatus;
  summary: string;
  limitations: string;
  next_step?: string;
};

export type LearningConclusionRecord = LearningConclusionRequest & {
  conclusion_id: string;
  problem_id: string;
  tenant_id: string;
  reviewer: string;
  reviewed_at: string;
  retention_expires_at: string;
};

export type TimelineEvent = {
  event_id: string;
  problem_id: string;
  event_type: "status_changed" | "approval_recorded" | "execution_created" | "outcome_measured" | string;
  label: string;
  detail: string;
  actor?: string | null;
  created_at: string;
};

export type WorkflowState = {
  problem_id: string;
  approvals: ApprovalRecord[];
  executions: ExecutionRecord[];
  jira_issue_drafts: JiraIssueDraft[];
  outcome: OutcomeSnapshot;
  learning_conclusions: LearningConclusionRecord[];
  closure_records: ClosureRecord[];
  timeline: TimelineEvent[];
};

export type SignalRecord = {
  signal_id: string;
  customer_id: string;
  account_id: string;
  source: string;
  journey: string;
  journey_stage: string;
  campaign_exposure: string[];
  product_events: string[];
  feedback_text: string;
  language: string;
  timestamp: string;
  metadata?: Record<string, string>;
};

export type WorkspaceSettings = {
  name: string;
  slug: string;
  notification_email: string;
  measurement_window_days: number;
  learning_half_life_days: number;
};

export type SystemConfig = {
  ai_base_url: string;
  ai_model: string;
  ai_embed_model?: string;
  auth_enabled: boolean;
};

export type RuleCondition = {
  field: string;
  operator: string;
  value: string;
};

export type RuleAction = {
  type: string;
  target: string;
};

export type FeedbackRule = {
  rule_id: string;
  name: string;
  conditions: RuleCondition[];
  actions: RuleAction[];
  priority: number;
  is_active: boolean;
};

export type SignalImportResult = {
  imported: number;
  skipped_duplicates: number;
  total_signals: number;
};

export type CustomerContextRecord = {
  customer_id: string;
  account_id: string;
  account_name?: string | null;
  parent_account_id?: string | null;
  parent_account_name?: string | null;
  segment?: string | null;
  lifecycle_stage?: string | null;
  plan_tier?: string | null;
  contact_role?: string | null;
  account_value: number;
  renewal_date?: string | null;
  consent_status: string;
  health_score?: number | null;
  owner?: string | null;
  product_owner?: string | null;
  region?: string | null;
};

export type ContextDataQualityWarning = {
  warning_id: string;
  severity: string;
  field: string;
  message: string;
  customer_ids: string[];
  account_ids: string[];
};

export type ContextRoutingRecommendation = {
  owner: string;
  priority: string;
  reason: string;
  customer_ids: string[];
  account_ids: string[];
  contact_roles: string[];
};

export type AffectedAccountSummary = {
  account_id: string;
  account_name?: string | null;
  parent_account_id?: string | null;
  parent_account_name?: string | null;
  customer_count: number;
  account_value: number;
  high_value: boolean;
  consent_risk_customers: number;
  average_health_score?: number | null;
  contact_roles: string[];
  lifecycle_stages: string[];
  plan_tiers: string[];
  renewal_dates: string[];
  owners: string[];
  product_owners: string[];
  regions: string[];
};

export type AffectedContextExplorer = {
  problem_id: string;
  context_impact?: ContextImpactSummary | null;
  accounts: AffectedAccountSummary[];
  customers: CustomerContextRecord[];
  missing_customer_ids: string[];
  missing_account_ids: string[];
  warnings: ContextDataQualityWarning[];
  routing_recommendations: ContextRoutingRecommendation[];
};

export type CustomerContextImportResult = {
  imported: number;
  updated: number;
  total_context_records: number;
};

export type DemoDatasetSummary = {
  dataset_id: string;
  title: string;
  description: string;
  industry: string;
  signal_count: number;
  context_count: number;
  journeys: string[];
};

export type DemoDatasetImportResult = {
  dataset_id: string;
  title: string;
  signals: SignalImportResult;
  customer_context: CustomerContextImportResult;
};

export type SignalValidationIssue = {
  severity: "error" | "warning";
  row_number?: number | null;
  field?: string | null;
  message: string;
};

export type SignalValidationReport = {
  valid: boolean;
  total_rows: number;
  importable_rows: number;
  errors: SignalValidationIssue[];
  warnings: SignalValidationIssue[];
};

export type CustomerContextValidationReport = SignalValidationReport;

export type ContextCompletenessMetric = {
  field: string;
  label: string;
  populated_records: number;
  total_records: number;
  coverage: number;
  importance: string;
};

export type CustomerContextCompletenessReport = {
  total_records: number;
  total_accounts: number;
  complete_records: number;
  readiness_score: number;
  readiness_level: "ready" | "usable" | "needs_attention" | string;
  metrics: ContextCompletenessMetric[];
  warnings: SignalValidationIssue[];
};

export type ProblemCandidate = {
  candidate_id: string;
  title: string;
  journey: string;
  journey_stage: string;
  signal_count: number;
  customer_count: number;
  account_count: number;
  sources: string[];
  languages: string[];
  first_seen: string;
  last_seen: string;
  confidence: number;
  evidence: Evidence[];
  root_cause_hypothesis: string;
  root_cause_analysis?: RootCauseAnalysis | null;
  suggested_owner: string;
  suggested_action: string;
  taxonomy_version?: string | null;
  classifications: TaxonomyClassification[];
  terminology_hits: string[];
  contradictory_evidence: string[];
  known_limitations: string[];
  evaluation_notes: string[];
  emerging_problem_score: number;
  review_status: "pending" | "duplicate" | "accepted" | "rejected";
  duplicate_problem_id?: string | null;
  duplicate_reason?: string | null;
  reviewer?: string | null;
  review_note?: string | null;
  reviewed_at?: string | null;
};

export type CandidateReviewRequest = {
  reviewer: string;
  note?: string;
};
