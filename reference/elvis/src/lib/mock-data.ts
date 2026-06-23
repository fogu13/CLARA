import type {
  Signal, Insight, FeedbackRule, ActionLog, AbLearning, SignalSourceConfig,
  DashboardSummary, SignalTrendPoint, ThemeData, FunnelStage, TeamRouting,
} from "./types";

// ====== Dashboard ======

export const mockDashboardSummary: DashboardSummary = {
  total_signals_7d: 342,
  signals_change_pct: 12,
  open_insights: 8,
  critical_insights: 3,
  high_insights: 5,
  actions_taken_7d: 14,
  auto_executed_pct: 85,
  resolution_rate: 72,
  resolution_change_pct: 8,
};

export const mockSignalTrend: SignalTrendPoint[] = Array.from({ length: 30 }, (_, i) => {
  const d = new Date();
  d.setDate(d.getDate() - (29 - i));
  return {
    date: d.toISOString().slice(0, 10),
    qualitative: Math.floor(Math.random() * 15) + 5,
    quantitative: Math.floor(Math.random() * 10) + 3,
  };
});

export const mockThemes: ThemeData[] = [
  { name: "Pricing Confusion", count: 28, sentiment: "negative" },
  { name: "Onboarding Friction", count: 22, sentiment: "negative" },
  { name: "Feature Requests", count: 18, sentiment: "neutral" },
  { name: "Support Quality", count: 15, sentiment: "positive" },
  { name: "Performance Issues", count: 12, sentiment: "negative" },
  { name: "Billing Problems", count: 8, sentiment: "negative" },
];

export const mockFunnel: FunnelStage[] = [
  { stage: "new", count: 12, label: "New" },
  { stage: "reviewing", count: 8, label: "Reviewing" },
  { stage: "action_taken", count: 5, label: "Action Taken" },
  { stage: "resolved", count: 18, label: "Resolved" },
];

export const mockTeamRouting: TeamRouting[] = [
  { team: "marketing", count: 12 },
  { team: "product", count: 8 },
  { team: "cx", count: 6 },
  { team: "sales", count: 4 },
  { team: "engineering", count: 3 },
];

// ====== Signals ======

export const mockSignals: Signal[] = [
  {
    id: 1, workspace_id: 1, signal_type: "qualitative", source: "nps_survey",
    category: "feedback", text_content: "The pricing page is really confusing. I can't tell the difference between the plans.",
    original_language: "en", is_anomaly: false, contact_count: 1,
    sentiment: "negative", sentiment_score: 0.2, urgency: "high",
    tags: ["pricing", "ux"], metadata: { nps_score: 3 },
    entity_type: "page", entity_name: "Pricing Page",
    recorded_at: new Date(Date.now() - 2 * 3600000).toISOString(),
    ingested_at: new Date(Date.now() - 2 * 3600000).toISOString(),
  },
  {
    id: 2, workspace_id: 1, signal_type: "quantitative", source: "page_analytics",
    category: "performance", metric_name: "bounce_rate", metric_value: 65.2,
    metric_baseline: 42.1, metric_delta: 23.1, metric_delta_pct: 54.9,
    is_anomaly: true, contact_count: 1200,
    urgency: "critical", tags: ["pricing"], metadata: {},
    entity_type: "page", entity_name: "Pricing Page",
    recorded_at: new Date(Date.now() - 3 * 3600000).toISOString(),
    ingested_at: new Date(Date.now() - 3 * 3600000).toISOString(),
  },
  {
    id: 3, workspace_id: 1, signal_type: "qualitative", source: "support_ticket",
    category: "feedback", text_content: "I've been trying to upgrade my plan for 20 minutes. Too many options, just want something simple.",
    original_language: "en", is_anomaly: false, contact_count: 1,
    sentiment: "negative", sentiment_score: 0.15, urgency: "high",
    tags: ["pricing", "onboarding", "ux"], metadata: { ticket_id: "TK-1234" },
    entity_type: "product", entity_name: "Plan Upgrade Flow",
    recorded_at: new Date(Date.now() - 5 * 3600000).toISOString(),
    ingested_at: new Date(Date.now() - 5 * 3600000).toISOString(),
  },
  {
    id: 4, workspace_id: 1, signal_type: "qualitative", source: "nps_survey",
    category: "feedback", text_content: "Love the new chat support! Got my issue resolved in under 2 minutes.",
    original_language: "en", is_anomaly: false, contact_count: 1,
    sentiment: "positive", sentiment_score: 0.95, urgency: "low",
    tags: ["support"], metadata: { nps_score: 10 },
    entity_type: "product", entity_name: "Chat Support",
    recorded_at: new Date(Date.now() - 8 * 3600000).toISOString(),
    ingested_at: new Date(Date.now() - 8 * 3600000).toISOString(),
  },
  {
    id: 5, workspace_id: 1, signal_type: "quantitative", source: "email_engagement",
    category: "behavior", metric_name: "open_rate", metric_value: 12.3,
    metric_baseline: 24.5, metric_delta: -12.2, metric_delta_pct: -49.8,
    is_anomaly: true, contact_count: 5000,
    urgency: "high", tags: ["email", "engagement"], metadata: { campaign: "Weekly Newsletter #42" },
    entity_type: "email", entity_name: "Weekly Newsletter #42",
    recorded_at: new Date(Date.now() - 12 * 3600000).toISOString(),
    ingested_at: new Date(Date.now() - 12 * 3600000).toISOString(),
  },
  {
    id: 6, workspace_id: 1, signal_type: "qualitative", source: "app_review",
    category: "feedback", text_content: "Step 3 of onboarding is broken on mobile. Had to switch to desktop to finish.",
    original_language: "en", is_anomaly: false, contact_count: 1,
    sentiment: "negative", sentiment_score: 0.1, urgency: "high",
    tags: ["onboarding", "bug"], metadata: { store: "App Store", rating: 2 },
    entity_type: "product", entity_name: "Onboarding Flow",
    recorded_at: new Date(Date.now() - 18 * 3600000).toISOString(),
    ingested_at: new Date(Date.now() - 18 * 3600000).toISOString(),
  },
  {
    id: 7, workspace_id: 1, signal_type: "quantitative", source: "page_analytics",
    category: "performance", metric_name: "time_on_page", metric_value: 8.2,
    metric_baseline: 45.0, metric_delta: -36.8, metric_delta_pct: -81.8,
    is_anomaly: true, contact_count: 340,
    urgency: "critical", tags: ["onboarding"], metadata: {},
    entity_type: "page", entity_name: "Onboarding Step 3",
    recorded_at: new Date(Date.now() - 20 * 3600000).toISOString(),
    ingested_at: new Date(Date.now() - 20 * 3600000).toISOString(),
  },
  {
    id: 8, workspace_id: 1, signal_type: "qualitative", source: "social_mention",
    category: "sentiment", text_content: "Just switched to @product — onboarding was rough but the product itself is great once you get past the setup.",
    original_language: "en", is_anomaly: false, contact_count: 1,
    sentiment: "mixed", sentiment_score: 0.55, urgency: "medium",
    tags: ["onboarding", "value"], metadata: { platform: "twitter" },
    recorded_at: new Date(Date.now() - 24 * 3600000).toISOString(),
    ingested_at: new Date(Date.now() - 24 * 3600000).toISOString(),
  },
  {
    id: 9, workspace_id: 1, signal_type: "quantitative", source: "ab_test_result",
    category: "performance", metric_name: "click_rate", metric_value: 4.8,
    metric_baseline: 3.2, metric_delta: 1.6, metric_delta_pct: 50.0,
    is_anomaly: false, contact_count: 2500,
    urgency: "low", tags: ["cta", "email"], metadata: { test_name: "CTA Button Color Test", variant: "B" },
    entity_type: "email", entity_name: "CTA Button Color Test",
    recorded_at: new Date(Date.now() - 48 * 3600000).toISOString(),
    ingested_at: new Date(Date.now() - 48 * 3600000).toISOString(),
  },
  {
    id: 10, workspace_id: 1, signal_type: "qualitative", source: "csat_survey",
    category: "feedback", text_content: "Your emails are way too frequent. I'm getting 3-4 per week and it's annoying.",
    original_language: "en", is_anomaly: false, contact_count: 1,
    sentiment: "negative", sentiment_score: 0.1, urgency: "medium",
    tags: ["email", "communication"], metadata: { csat_score: 2 },
    recorded_at: new Date(Date.now() - 36 * 3600000).toISOString(),
    ingested_at: new Date(Date.now() - 36 * 3600000).toISOString(),
  },
];

// ====== Insights ======

export const mockInsights: Insight[] = [
  {
    id: 1, workspace_id: 1,
    title: "Pricing confusion driving 35% bounce rate spike",
    summary: "Multiple NPS responses and support tickets indicate customers find the pricing page confusing, with too many plan options. This correlates with a 54.9% bounce rate increase on the pricing page over the past 7 days, affecting approximately 1,200 visitors.",
    category: "content_clarity",
    signal_ids: [1, 2, 3], qual_signal_count: 2, quant_signal_count: 1,
    impact_score: 8.4, confidence: 0.87, severity: "critical",
    affected_contacts: 1247, estimated_revenue_impact: 45000,
    urgency: "critical", target_team: "marketing",
    suggested_actions: [
      { type: "create_segment", title: "Pricing-confused visitors", description: "Create a segment of visitors who bounced from the pricing page in the last 7 days for targeted outreach.", params: {}, priority: 1 },
      { type: "draft_email", title: "Pricing clarity campaign", description: "Draft an email explaining the key differences between plans with a comparison table.", params: { template: "clarification" }, priority: 2 },
    ],
    status: "new", actions_taken: [],
    detected_at: new Date(Date.now() - 2 * 3600000).toISOString(),
    created_at: new Date(Date.now() - 2 * 3600000).toISOString(),
    updated_at: new Date(Date.now() - 2 * 3600000).toISOString(),
  },
  {
    id: 2, workspace_id: 1,
    title: "Onboarding drop-off at step 3 on mobile",
    summary: "App reviews and social mentions report that onboarding step 3 is broken on mobile devices. Time on page dropped 81.8% for the onboarding step 3 page, suggesting users are abandoning rather than completing the flow.",
    category: "ux_friction",
    signal_ids: [6, 7, 8], qual_signal_count: 2, quant_signal_count: 1,
    impact_score: 6.2, confidence: 0.79, severity: "high",
    affected_contacts: 340, urgency: "high", target_team: "product",
    suggested_actions: [
      { type: "create_ticket", title: "Fix mobile onboarding step 3", description: "Create an engineering ticket with evidence from user reports and analytics.", params: { project: "PROD", labels: ["mobile", "onboarding"] }, priority: 1 },
      { type: "send_alert", title: "Notify product team", description: "Alert the product team about the mobile onboarding issue.", params: {}, priority: 2 },
    ],
    status: "reviewing", actions_taken: [],
    detected_at: new Date(Date.now() - 18 * 3600000).toISOString(),
    created_at: new Date(Date.now() - 18 * 3600000).toISOString(),
    updated_at: new Date(Date.now() - 12 * 3600000).toISOString(),
  },
  {
    id: 3, workspace_id: 1,
    title: "Positive response to new support chat feature",
    summary: "NPS promoters are specifically calling out the new chat support feature. Response times under 2 minutes are driving satisfaction. This is a positive signal that should be amplified in marketing materials.",
    category: "positive_trend",
    signal_ids: [4], qual_signal_count: 3, quant_signal_count: 1,
    impact_score: 4.0, confidence: 0.72, severity: "low",
    affected_contacts: 89, urgency: "low", target_team: "marketing",
    suggested_actions: [
      { type: "draft_email", title: "Chat support success story", description: "Draft a case study email highlighting the chat support improvements.", params: {}, priority: 1 },
    ],
    status: "action_taken",
    actions_taken: [
      { type: "email_drafted", id: 15, at: new Date(Date.now() - 48 * 3600000).toISOString() },
    ],
    detected_at: new Date(Date.now() - 72 * 3600000).toISOString(),
    created_at: new Date(Date.now() - 72 * 3600000).toISOString(),
    updated_at: new Date(Date.now() - 48 * 3600000).toISOString(),
    measurement_due_at: new Date(Date.now() + 12 * 86400000).toISOString(),
  },
  {
    id: 4, workspace_id: 1,
    title: "Email fatigue in enterprise segment",
    summary: "Enterprise customers report receiving too many emails (3-4/week). Open rates for the weekly newsletter dropped 49.8%, correlating with unsubscribe complaints. Immediate frequency reduction recommended.",
    category: "engagement_drop",
    signal_ids: [5, 10], qual_signal_count: 3, quant_signal_count: 2,
    impact_score: 5.8, confidence: 0.82, severity: "high",
    affected_contacts: 5000, urgency: "high", target_team: "marketing",
    suggested_actions: [
      { type: "create_segment", title: "Over-contacted enterprise users", description: "Segment enterprise users receiving >3 emails/week.", params: {}, priority: 1 },
      { type: "draft_email", title: "Preference center reminder", description: "Send a one-time email letting users adjust their email preferences.", params: {}, priority: 2 },
    ],
    status: "action_planned",
    actions_taken: [],
    detected_at: new Date(Date.now() - 36 * 3600000).toISOString(),
    created_at: new Date(Date.now() - 36 * 3600000).toISOString(),
    updated_at: new Date(Date.now() - 24 * 3600000).toISOString(),
  },
  {
    id: 5, workspace_id: 1,
    title: "Feature request: bulk data export",
    summary: "Four separate feedback submissions from different channels request the ability to export data in bulk. While no quantitative anomaly is directly correlated, the recurring theme suggests growing demand.",
    category: "product_issue",
    signal_ids: [], qual_signal_count: 4, quant_signal_count: 0,
    impact_score: 3.5, confidence: 0.65, severity: "medium",
    affected_contacts: 24, urgency: "medium", target_team: "product",
    suggested_actions: [
      { type: "create_ticket", title: "Evaluate bulk export feature", description: "Create a product ticket to evaluate the feasibility and priority of bulk data export.", params: { project: "PROD" }, priority: 1 },
    ],
    status: "new", actions_taken: [],
    detected_at: new Date(Date.now() - 96 * 3600000).toISOString(),
    created_at: new Date(Date.now() - 96 * 3600000).toISOString(),
    updated_at: new Date(Date.now() - 96 * 3600000).toISOString(),
  },
];

// ====== Rules ======

export const mockRules: FeedbackRule[] = [
  {
    id: 1, workspace_id: 1,
    name: "Auto-respond to content clarity issues",
    description: "When a content clarity insight is detected with high impact, automatically create a segment and draft an email.",
    enabled: true,
    conditions: { insight_category: ["content_clarity", "ux_friction"], min_impact_score: 7.0, min_confidence: 0.7, min_affected_contacts: 10, urgency: ["high", "critical"] },
    actions: [
      { type: "create_segment", name_template: "Auto: {insight_title}" },
      { type: "draft_email", template_id: "clarification" },
    ],
    auto_execute: true, priority: 5, measure_after_days: 14,
    times_triggered: 4, last_triggered_at: new Date(Date.now() - 2 * 3600000).toISOString(),
    created_at: new Date(Date.now() - 30 * 86400000).toISOString(),
    updated_at: new Date(Date.now() - 2 * 3600000).toISOString(),
  },
  {
    id: 2, workspace_id: 1,
    name: "Route product issues to engineering",
    description: "Automatically create a ticket and notify engineering when product issues are detected.",
    enabled: true,
    conditions: { insight_category: ["product_issue"] },
    actions: [
      { type: "create_ticket", project: "PROD", labels: ["customer-feedback"] },
      { type: "notify", channels: ["slack"], recipients: ["eng-team"] },
    ],
    auto_execute: false, priority: 0, measure_after_days: 14,
    times_triggered: 7, last_triggered_at: new Date(Date.now() - 96 * 3600000).toISOString(),
    created_at: new Date(Date.now() - 30 * 86400000).toISOString(),
    updated_at: new Date(Date.now() - 96 * 3600000).toISOString(),
  },
  {
    id: 3, workspace_id: 1,
    name: "Alert on churn risk",
    description: "Notify CX team and create segment when critical churn risk is detected.",
    enabled: true,
    conditions: { insight_category: ["churn_risk"], urgency: ["critical"] },
    actions: [
      { type: "notify", channels: ["email", "slack"], recipients: ["cx-lead"] },
      { type: "create_segment", name_template: "Churn risk: {insight_title}" },
    ],
    auto_execute: true, priority: 10, measure_after_days: 7,
    times_triggered: 2, last_triggered_at: new Date(Date.now() - 168 * 3600000).toISOString(),
    created_at: new Date(Date.now() - 30 * 86400000).toISOString(),
    updated_at: new Date(Date.now() - 168 * 3600000).toISOString(),
  },
];

// ====== Actions Log ======

export const mockActionsLog: ActionLog[] = [
  {
    id: 1, workspace_id: 1, insight_id: 1, rule_id: 1,
    action_type: "segment_created",
    action_params: { name: "Pricing-confused visitors", criteria: "bounced from pricing page in 7d" },
    action_result: { segment_id: 42, contact_count: 47 },
    executed_by: "system_auto", status: "completed",
    executed_at: new Date(Date.now() - 2 * 3600000).toISOString(),
  },
  {
    id: 2, workspace_id: 1, insight_id: 1, rule_id: 1,
    action_type: "email_drafted",
    action_params: { template: "clarification", subject: "Understanding our plans" },
    action_result: { draft_id: 89, preview_url: "#" },
    executed_by: "system_auto", status: "pending_approval",
    executed_at: new Date(Date.now() - 2 * 3600000).toISOString(),
  },
  {
    id: 3, workspace_id: 1, insight_id: 3,
    action_type: "email_drafted",
    action_params: { subject: "How we improved support response times" },
    action_result: { draft_id: 90 },
    executed_by: "user:1", status: "completed",
    executed_at: new Date(Date.now() - 48 * 3600000).toISOString(),
  },
  {
    id: 4, workspace_id: 1, insight_id: 2, rule_id: 2,
    action_type: "ticket_created",
    action_params: { project: "PROD", title: "Fix mobile onboarding step 3", labels: ["mobile", "onboarding"] },
    action_result: { ticket_id: "PROD-456", url: "#" },
    executed_by: "system_auto", status: "completed",
    executed_at: new Date(Date.now() - 12 * 3600000).toISOString(),
  },
  {
    id: 5, workspace_id: 1, insight_id: 2, rule_id: 2,
    action_type: "notification_sent",
    action_params: { channel: "slack", recipients: ["eng-team"], message: "New product issue detected" },
    action_result: { delivered: true },
    executed_by: "system_auto", status: "completed",
    executed_at: new Date(Date.now() - 12 * 3600000).toISOString(),
  },
];

// ====== A/B Learnings ======

export const mockLearnings: AbLearning[] = [
  {
    id: 1, workspace_id: 1, topic: "subject_lines",
    pattern: "Questions in subject lines outperform statements by 18% on open rate",
    evidence: {
      tests_count: 5, avg_lift_pct: 18.2, confidence: 0.95,
      sample_size: 12000,
      winning_examples: ["Ready to simplify your pricing?", "What if onboarding took 5 minutes?"],
      losing_examples: ["New pricing update", "Onboarding improvements available"],
    },
    test_ids: ["test-1", "test-2", "test-3", "test-4", "test-5"],
    is_validated: true,
    created_at: new Date(Date.now() - 60 * 86400000).toISOString(),
    updated_at: new Date(Date.now() - 5 * 86400000).toISOString(),
  },
  {
    id: 2, workspace_id: 1, topic: "cta_text",
    pattern: "Single CTA outperforms multiple CTAs by 12% on click-through rate",
    evidence: {
      tests_count: 3, avg_lift_pct: 12.4, confidence: 0.88,
      sample_size: 8500,
      winning_examples: ["Start your free trial", "Get started now"],
      losing_examples: ["Learn more / Sign up / Contact us", "Try free or see pricing"],
    },
    test_ids: ["test-6", "test-7", "test-8"],
    is_validated: true,
    created_at: new Date(Date.now() - 45 * 86400000).toISOString(),
    updated_at: new Date(Date.now() - 10 * 86400000).toISOString(),
  },
  {
    id: 3, workspace_id: 1, topic: "send_time",
    pattern: "Tuesday 10AM sends outperform Friday 3PM sends by 8% on open rate",
    evidence: {
      tests_count: 4, avg_lift_pct: 8.1, confidence: 0.82,
      sample_size: 15000,
      winning_examples: ["Tuesday 10:00 AM EST", "Tuesday 9:30 AM EST"],
      losing_examples: ["Friday 3:00 PM EST", "Friday 4:00 PM EST"],
    },
    test_ids: ["test-9", "test-10", "test-11", "test-12"],
    is_validated: false,
    created_at: new Date(Date.now() - 30 * 86400000).toISOString(),
    updated_at: new Date(Date.now() - 3 * 86400000).toISOString(),
  },
];

// ====== Signal Sources ======

export const mockSources: SignalSourceConfig[] = [
  {
    id: 1, workspace_id: 1, name: "NPS Survey (Typeform)",
    source_type: "typeform", config: { form_id: "abc123" },
    enabled: true, last_synced_at: new Date(Date.now() - 30 * 60000).toISOString(),
    sync_status: "idle", created_at: new Date(Date.now() - 60 * 86400000).toISOString(),
  },
  {
    id: 2, workspace_id: 1, name: "Google Analytics",
    source_type: "google_analytics", config: { property_id: "GA-123456" },
    enabled: true, last_synced_at: new Date(Date.now() - 60 * 60000).toISOString(),
    sync_status: "idle", created_at: new Date(Date.now() - 45 * 86400000).toISOString(),
  },
  {
    id: 3, workspace_id: 1, name: "Zendesk Support",
    source_type: "zendesk", config: { subdomain: "mycompany" },
    enabled: true, last_synced_at: new Date(Date.now() - 15 * 60000).toISOString(),
    sync_status: "idle", created_at: new Date(Date.now() - 30 * 86400000).toISOString(),
  },
  {
    id: 4, workspace_id: 1, name: "App Store Reviews",
    source_type: "api_poll", config: { api_url: "https://api.example.com/reviews" },
    enabled: true, last_synced_at: new Date(Date.now() - 120 * 60000).toISOString(),
    sync_status: "idle", created_at: new Date(Date.now() - 20 * 86400000).toISOString(),
  },
  {
    id: 5, workspace_id: 1, name: "Custom Webhook",
    source_type: "webhook", config: { webhook_url: "/api/sources/webhook/tok_abc123" },
    enabled: false, sync_status: "error", sync_error: "Authentication failed: invalid API key",
    created_at: new Date(Date.now() - 10 * 86400000).toISOString(),
  },
];
