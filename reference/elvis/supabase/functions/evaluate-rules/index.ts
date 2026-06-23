import { serve } from "https://deno.land/std@0.168.0/http/server.ts";
import { createClient } from "https://esm.sh/@supabase/supabase-js@2.49.1";

const corsHeaders = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers":
    "authorization, x-client-info, apikey, content-type",
};

// ── Types ────────────────────────────────────────────────────────────────────

interface Insight {
  id: number;
  workspace_id: number;
  title: string;
  summary: string;
  category: string;
  impact_score: number;
  confidence: number;
  severity: string;
  urgency: string;
  affected_contacts: number;
  target_team: string;
  status: string;
  actions_taken: unknown[];
}

interface RuleConditions {
  insight_category?: string[];
  min_impact_score?: number;
  min_confidence?: number;
  min_affected_contacts?: number;
  urgency?: string[];
  severity?: string[];
  target_team?: string[];
}

interface RuleAction {
  type: string;
  [key: string]: unknown;
}

interface FeedbackRule {
  id: number;
  workspace_id: number;
  name: string;
  enabled: boolean;
  conditions: RuleConditions;
  actions: RuleAction[];
  auto_execute: boolean;
  priority: number;
  measure_after_days: number;
  times_triggered: number;
}

interface ActionLogInsert {
  workspace_id: number;
  insight_id: number;
  rule_id: number;
  action_type: string;
  action_params: Record<string, unknown>;
  action_result: Record<string, unknown>;
  executed_by: string;
  status: string;
}

// ── Condition matching ───────────────────────────────────────────────────────

function matchesRule(insight: Insight, conditions: RuleConditions): boolean {
  if (conditions.insight_category?.length) {
    if (!conditions.insight_category.includes(insight.category)) return false;
  }
  if (conditions.urgency?.length) {
    if (!conditions.urgency.includes(insight.urgency)) return false;
  }
  if (conditions.severity?.length) {
    if (!conditions.severity.includes(insight.severity)) return false;
  }
  if (conditions.target_team?.length) {
    if (!conditions.target_team.includes(insight.target_team)) return false;
  }
  if (conditions.min_impact_score !== undefined) {
    if (insight.impact_score < conditions.min_impact_score) return false;
  }
  if (conditions.min_confidence !== undefined) {
    if (insight.confidence < conditions.min_confidence) return false;
  }
  if (conditions.min_affected_contacts !== undefined) {
    if (insight.affected_contacts < conditions.min_affected_contacts) return false;
  }
  return true;
}

// ── Action execution (simulated) ─────────────────────────────────────────────
// Each action type returns a simulated result. When real integrations are
// connected, replace these with actual API calls to HubSpot, Slack, etc.

function executeAction(
  action: RuleAction,
  insight: Insight,
): { action_type: string; params: Record<string, unknown>; result: Record<string, unknown> } {
  const interpolate = (tpl: string) =>
    tpl
      .replace("{insight_title}", insight.title)
      .replace("{insight_id}", String(insight.id))
      .replace("{target_team}", insight.target_team);

  switch (action.type) {
    case "create_segment": {
      const name = action.name_template
        ? interpolate(action.name_template as string)
        : `Segment for insight #${insight.id}`;
      return {
        action_type: "segment_created",
        params: { name, insight_id: insight.id },
        result: { segment_id: crypto.randomUUID(), contact_count: insight.affected_contacts },
      };
    }
    case "draft_email": {
      const subject = action.subject
        ? interpolate(action.subject as string)
        : `Re: ${insight.title}`;
      return {
        action_type: "email_drafted",
        params: { template_id: action.template_id, subject, insight_id: insight.id },
        result: { draft_id: crypto.randomUUID() },
      };
    }
    case "create_ticket": {
      const title = `[${insight.severity.toUpperCase()}] ${insight.title}`;
      return {
        action_type: "ticket_created",
        params: {
          project: action.project,
          title,
          labels: action.labels ?? [],
          insight_id: insight.id,
        },
        result: { ticket_id: `${action.project}-${Date.now() % 10000}` },
      };
    }
    case "notify": {
      const message = `Insight "${insight.title}" (${insight.severity} severity, ${insight.urgency} urgency) matched rule. Affected contacts: ${insight.affected_contacts}.`;
      return {
        action_type: "notification_sent",
        params: {
          channels: action.channels,
          recipients: action.recipients,
          message,
        },
        result: { delivered: true },
      };
    }
    default: {
      return {
        action_type: action.type,
        params: { ...action, insight_id: insight.id },
        result: { simulated: true },
      };
    }
  }
}

// ── Main handler ─────────────────────────────────────────────────────────────

serve(async (req) => {
  if (req.method === "OPTIONS") {
    return new Response(null, { headers: corsHeaders });
  }

  try {
    const { insight_id } = await req.json();
    if (!insight_id) {
      return new Response(
        JSON.stringify({ error: "insight_id is required" }),
        { status: 400, headers: { ...corsHeaders, "Content-Type": "application/json" } },
      );
    }

    // Use service role to bypass RLS — this function runs server-side
    const supabaseUrl = Deno.env.get("SUPABASE_URL")!;
    const serviceKey = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!;
    const db = createClient(supabaseUrl, serviceKey);

    // 1. Fetch the insight
    const { data: insight, error: insightErr } = await db
      .from("insights")
      .select("*")
      .eq("id", insight_id)
      .single();

    if (insightErr || !insight) {
      return new Response(
        JSON.stringify({ error: `Insight ${insight_id} not found` }),
        { status: 404, headers: { ...corsHeaders, "Content-Type": "application/json" } },
      );
    }

    // Skip dismissed/resolved insights
    if (["dismissed", "resolved"].includes(insight.status)) {
      return new Response(
        JSON.stringify({ matched: 0, actions: 0, skipped: true, reason: `Insight status is "${insight.status}"` }),
        { headers: { ...corsHeaders, "Content-Type": "application/json" } },
      );
    }

    // 2. Fetch all enabled rules for this workspace
    const { data: rules, error: rulesErr } = await db
      .from("feedback_rules")
      .select("*")
      .eq("workspace_id", insight.workspace_id)
      .eq("enabled", true);

    if (rulesErr) throw rulesErr;
    if (!rules?.length) {
      return new Response(
        JSON.stringify({ matched: 0, actions: 0, reason: "No enabled rules" }),
        { headers: { ...corsHeaders, "Content-Type": "application/json" } },
      );
    }

    // 3. Evaluate each rule against the insight
    const matched = (rules as FeedbackRule[]).filter((rule) =>
      matchesRule(insight as Insight, rule.conditions),
    );

    if (!matched.length) {
      return new Response(
        JSON.stringify({ matched: 0, actions: 0, reason: "No rules matched" }),
        { headers: { ...corsHeaders, "Content-Type": "application/json" } },
      );
    }

    // 3b. Conflict resolution. When several rules match the same insight, higher
    // `priority` wins; ties break by specificity (number of conditions), then id.
    // Each action type fires at most once — the highest-ranked rule claiming it wins;
    // a lower rule whose action types are all already claimed is recorded as superseded.
    const specificity = (r: FeedbackRule) => Object.keys(r.conditions ?? {}).length;
    const ranked = [...matched].sort(
      (a, b) =>
        (b.priority ?? 0) - (a.priority ?? 0) ||
        specificity(b) - specificity(a) ||
        a.id - b.id,
    );

    const claimed = new Set<string>();
    const firedRules: { rule: FeedbackRule; actions: RuleAction[] }[] = [];
    const superseded: { id: number; name: string }[] = [];

    for (const rule of ranked) {
      const keptActions = rule.actions.filter((a) => !claimed.has(a.type));
      if (keptActions.length === 0) {
        superseded.push({ id: rule.id, name: rule.name });
        continue;
      }
      keptActions.forEach((a) => claimed.add(a.type));
      firedRules.push({ rule, actions: keptActions });
    }

    if (firedRules.length === 0) {
      return new Response(
        JSON.stringify({ matched: matched.length, fired: 0, actions: 0, superseded, reason: "Matched rules had no executable actions" }),
        { headers: { ...corsHeaders, "Content-Type": "application/json" } },
      );
    }

    // 4. Execute the surviving actions
    const now = () => new Date().toISOString();
    const actionLogs: ActionLogInsert[] = [];
    const actionsTakenUpdate: { type: string; id?: string; at: string }[] = [
      ...(insight.actions_taken ?? []) as { type: string; id?: string; at: string }[],
    ];

    for (const { rule, actions } of firedRules) {
      for (const action of actions) {
        const { action_type, params, result } = executeAction(action, insight as Insight);
        const status = rule.auto_execute ? "completed" : "pending_approval";

        actionLogs.push({
          workspace_id: insight.workspace_id,
          insight_id: insight.id,
          rule_id: rule.id,
          action_type,
          action_params: params,
          action_result: result,
          executed_by: rule.auto_execute ? "system_auto" : "system_pending",
          status,
        });

        actionsTakenUpdate.push({ type: action_type, at: now() });
      }

      // 5. Update rule trigger stats (only rules that actually fired)
      await db
        .from("feedback_rules")
        .update({
          times_triggered: rule.times_triggered + 1,
          last_triggered_at: now(),
        })
        .eq("id", rule.id);
    }

    // 6. Insert action logs
    const { error: logErr } = await db.from("actions_log").insert(actionLogs);
    if (logErr) throw logErr;

    // 7. Advance insight status
    const firedRuleList = firedRules.map((f) => f.rule);
    const hasAutoExecuted = firedRuleList.some((r) => r.auto_execute);
    const newStatus = hasAutoExecuted ? "action_taken" : "action_planned";

    // Calculate measurement_due_at from the shortest measure_after_days
    const minMeasureDays = Math.min(...firedRuleList.map((r) => r.measure_after_days));
    const measurementDue = new Date();
    measurementDue.setDate(measurementDue.getDate() + minMeasureDays);

    // Outcome contract: capture WHAT to measure and the baseline at action time.
    // Default to affected_contacts; prefer recurrence of the insight's dominant signal tag.
    let outcomeMetric = "affected_contacts";
    let outcomeBaseline: number = insight.affected_contacts ?? 0;
    if (Array.isArray(insight.signal_ids) && insight.signal_ids.length) {
      const { data: sigs } = await db
        .from("signals")
        .select("tags")
        .in("id", insight.signal_ids);
      const counts: Record<string, number> = {};
      for (const s of (sigs ?? []) as { tags: string[] | null }[]) {
        for (const t of s.tags ?? []) counts[t] = (counts[t] ?? 0) + 1;
      }
      const top = Object.entries(counts).sort((a, b) => b[1] - a[1])[0];
      if (top) {
        outcomeMetric = `tag:${top[0]}`;
        outcomeBaseline = top[1];
      }
    }

    // Only advance status forward (don't regress)
    const statusOrder = ["new", "reviewing", "action_planned", "action_taken", "measuring", "resolved"];
    const currentIdx = statusOrder.indexOf(insight.status);
    const newIdx = statusOrder.indexOf(newStatus);
    const shouldAdvance = newIdx > currentIdx;

    if (shouldAdvance) {
      await db
        .from("insights")
        .update({
          status: newStatus,
          status_changed_at: new Date().toISOString(),
          actions_taken: actionsTakenUpdate,
          measurement_due_at: measurementDue.toISOString(),
          outcome_metric: outcomeMetric,
          outcome_baseline: outcomeBaseline,
          measurement_window_days: minMeasureDays,
        })
        .eq("id", insight.id);
    } else {
      // Still update actions_taken even if status doesn't advance
      await db
        .from("insights")
        .update({ actions_taken: actionsTakenUpdate })
        .eq("id", insight.id);
    }

    const response = {
      matched: matched.length,
      fired: firedRules.length,
      superseded,
      actions: actionLogs.length,
      auto_executed: actionLogs.filter((a) => a.status === "completed").length,
      pending_approval: actionLogs.filter((a) => a.status === "pending_approval").length,
      status_advanced: shouldAdvance ? newStatus : null,
      measurement_due: shouldAdvance ? measurementDue.toISOString() : null,
      rules: firedRuleList.map((r) => ({ id: r.id, name: r.name, auto_execute: r.auto_execute })),
    };

    return new Response(JSON.stringify(response), {
      headers: { ...corsHeaders, "Content-Type": "application/json" },
    });
  } catch (e) {
    console.error("evaluate-rules error:", e);
    return new Response(
      JSON.stringify({ error: e instanceof Error ? e.message : "Unknown error" }),
      { status: 500, headers: { ...corsHeaders, "Content-Type": "application/json" } },
    );
  }
});
