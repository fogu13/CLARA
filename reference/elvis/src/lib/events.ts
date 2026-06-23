import { supabase } from "@/integrations/supabase/client";

export type AppEventType =
  | "rule_created"
  | "rule_updated"
  | "action_approved"
  | "action_rejected"
  | "action_executed"
  | "insight_status_advanced"
  | "outcome_measured"
  | "learnings_shown"
  | "taxonomy_node_promoted"
  | "taxonomy_node_rejected"
  | "taxonomy_node_merged"
  | "taxonomy_node_auto_promoted"
  | "taxonomy_node_auto_merged"
  | "taxonomy_node_decayed";

interface EventOpts {
  entity?: string;
  entity_id?: string | number;
  user_id?: string;
  duration_ms?: number;
  metadata?: Record<string, unknown>;
}

/**
 * Fire-and-forget evaluation telemetry (Phase F1). Never throws — instrumentation
 * must not break the user action it measures. Consumed by thesis/evaluation/prototype_metrics.py.
 */
export async function logEvent(workspaceId: number, eventType: AppEventType, opts: EventOpts = {}) {
  try {
    await supabase.from("events").insert({
      workspace_id: workspaceId,
      event_type: eventType,
      entity: opts.entity ?? null,
      entity_id: opts.entity_id != null ? String(opts.entity_id) : null,
      user_id: opts.user_id ?? null,
      duration_ms: opts.duration_ms ?? null,
      metadata: (opts.metadata ?? {}) as never,
    });
  } catch {
    /* telemetry is best-effort */
  }
}
