// ====== Enums / Literal Types ======

export type SignalType = "qualitative" | "quantitative";
export type SignalSource =
  | "nps_survey" | "csat_survey" | "ces_survey" | "open_feedback"
  | "support_ticket" | "app_review" | "social_mention"
  | "email_engagement" | "page_analytics" | "ab_test_result"
  | "campaign_metrics" | "segment_movement" | "custom_webhook";

export type SignalCategory = "feedback" | "behavior" | "performance" | "sentiment";
export type Sentiment = "positive" | "neutral" | "negative" | "mixed";
export type Urgency = "low" | "medium" | "high" | "critical";
export type Severity = "low" | "medium" | "high" | "critical";

export type InsightStatus =
  | "new" | "reviewing" | "action_planned" | "action_taken"
  | "measuring" | "resolved" | "dismissed" | "escalated";

export type TargetTeam = "marketing" | "product" | "cx" | "sales" | "engineering";
export type InsightCategory =
  | "content_clarity" | "product_issue" | "churn_risk"
  | "campaign_performance" | "ux_friction" | "sentiment_shift"
  | "engagement_drop" | "positive_trend" | "compliance_concern";

export type ActionType =
  | "segment_created" | "email_drafted" | "campaign_triggered"
  | "ticket_created" | "notification_sent" | "content_updated"
  | "survey_triggered" | "alert_sent";

// ====== Models ======

export interface Signal {
  id: number;
  workspace_id: number;
  signal_type: SignalType;
  source: SignalSource;
  category: SignalCategory;
  text_content?: string;
  original_language?: string;
  metric_name?: string;
  metric_value?: number;
  metric_baseline?: number;
  metric_delta?: number;
  metric_delta_pct?: number;
  is_anomaly: boolean;
  entity_type?: string;
  entity_id?: string;
  entity_name?: string;
  contact_id?: string;
  contact_count: number;
  sentiment?: Sentiment;
  sentiment_score?: number;
  urgency: Urgency;
  tags: string[];
  metadata: Record<string, unknown>;
  source_url?: string;
  recorded_at: string;
  ingested_at: string;
}

export interface SuggestedAction {
  type: string;
  title: string;
  description: string;
  params: Record<string, unknown>;
  priority: number;
}

export interface ActionTaken {
  type: string;
  id: number;
  at: string;
}

export interface Insight {
  id: number;
  workspace_id: number;
  title: string;
  summary: string;
  category: InsightCategory;
  signal_ids: number[];
  qual_signal_count: number;
  quant_signal_count: number;
  impact_score: number;
  confidence: number;
  severity: Severity;
  affected_contacts: number;
  estimated_revenue_impact?: number;
  urgency: Urgency;
  target_team: TargetTeam;
  assigned_to?: number;
  suggested_actions: SuggestedAction[];
  status: InsightStatus;
  status_changed_at?: string;
  dismissed_reason?: string;
  actions_taken: ActionTaken[];
  measurement_due_at?: string;
  /** Outcome contract — what to measure, the baseline at action time, and the result. */
  outcome_metric?: string;
  outcome_baseline?: number;
  outcome_measured?: number;
  outcome_target?: number;
  measurement_window_days?: number;
  measured_at?: string;
  resolution_score?: number;
  resolution_summary?: string;
  detected_at: string;
  resolved_at?: string;
  created_at: string;
  updated_at: string;
}

export interface FeedbackRule {
  id: number;
  workspace_id: number;
  name: string;
  description?: string;
  enabled: boolean;
  conditions: Record<string, unknown>;
  actions: Record<string, unknown>[];
  auto_execute: boolean;
  /** Higher wins when multiple rules match the same insight (conflict resolution). */
  priority: number;
  measure_after_days: number;
  times_triggered: number;
  last_triggered_at?: string;
  created_at: string;
  updated_at: string;
}

export interface ActionLog {
  id: number;
  workspace_id: number;
  insight_id?: number;
  rule_id?: number;
  action_type: ActionType;
  action_params: Record<string, unknown>;
  action_result?: Record<string, unknown>;
  executed_by: string;
  status: "completed" | "failed" | "pending_approval";
  error_message?: string;
  executed_at: string;
}

export interface AbLearning {
  id: number;
  workspace_id: number;
  topic: string;
  pattern: string;
  evidence: {
    tests_count: number;
    avg_lift_pct: number;
    confidence: number;
    sample_size: number;
    winning_examples: string[];
    losing_examples: string[];
  };
  test_ids: string[];
  is_validated: boolean;
  /** Confidence decay (design decision #2): decay is measured from last_validated_at over half_life_days. */
  last_validated_at?: string;
  half_life_days?: number;
  created_at: string;
  updated_at: string;
}

export interface SignalSourceConfig {
  id: number;
  workspace_id: number;
  name: string;
  source_type: string;
  config: Record<string, unknown>;
  enabled: boolean;
  last_synced_at?: string;
  sync_status: "idle" | "syncing" | "error";
  sync_error?: string;
  created_at: string;
}

// ====== Dashboard Types ======

export interface DashboardSummary {
  total_signals_7d: number;
  signals_change_pct: number;
  open_insights: number;
  critical_insights: number;
  high_insights: number;
  actions_taken_7d: number;
  auto_executed_pct: number;
  resolution_rate: number;
  resolution_change_pct: number;
}

export interface SignalTrendPoint {
  date: string;
  qualitative: number;
  quantitative: number;
}

export interface ThemeData {
  name: string;
  count: number;
  sentiment: Sentiment;
}

export interface FunnelStage {
  stage: InsightStatus;
  count: number;
  label: string;
}

export interface TeamRouting {
  team: TargetTeam;
  count: number;
}

// ====== Taxonomy Types ======

export type TaxonomyStatus = "active" | "candidate" | "merged" | "archived";
export type TaxonomyOrigin = "uploaded" | "seeded" | "discovered";

export interface TaxonomyNode {
  id: string;
  workspace_id: number;
  parent_id: string | null;
  level: 1 | 2 | 3;
  name: string;
  slug: string;
  description: string | null;
  status: TaxonomyStatus;
  origin: TaxonomyOrigin;
  confidence: number;
  times_matched: number;
  last_matched_at: string | null;
  merged_into_id: string | null;
  auto_promoted?: boolean;
  evidence?: {
    signal_ids?: number[];
    samples?: string[];
    size?: number;
    cohesion?: number;
  };
  created_at: string;
  updated_at: string;
  /** populated client-side by buildTree */
  children?: TaxonomyNode[];
  match_count?: number;
}

export interface SignalNodeMap {
  id: number;
  signal_id: number;
  node_id: string;
  score: number | null;
  mapped_by: "system_auto" | "system_llm" | "user";
  created_at: string;
}
