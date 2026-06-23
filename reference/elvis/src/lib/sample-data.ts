import { supabase } from "@/integrations/supabase/client";

export interface SampleSignalRow {
  workspace_id: number;
  signal_type: "qualitative";
  source: string;
  category: string;
  text_content: string;
  urgency: string;
  tags: string[];
  metadata: Record<string, unknown>;
  recorded_at: string;
}

const SAMPLES: { source: string; text: string; tags: string[] }[] = [
  { source: "nps_survey", text: "Checkout failed three times on the payment step before it went through.", tags: ["checkout_failure", "payment"] },
  { source: "support_ticket", text: "Could not pay with my card at checkout — it kept erroring.", tags: ["checkout_failure", "payment"] },
  { source: "app_review", text: "Delivery status never updated; I had no idea where my order was.", tags: ["late_delivery", "tracking"] },
  { source: "open_feedback", text: "Order arrived late and the tracking was wrong the whole time.", tags: ["late_delivery", "tracking"] },
  { source: "nps_survey", text: "Onboarding was confusing — I couldn't figure out how to connect a source.", tags: ["onboarding_friction"] },
  { source: "csat_survey", text: "The pricing page is unclear about what's included in each tier.", tags: ["pricing_unclear"] },
  { source: "social_mention", text: "Love the new dashboard — so much faster than before!", tags: ["positive_dashboard"] },
];

/** Pure: build sample signal rows for a workspace (last 7 days). */
export function sampleSignals(workspaceId: number): SampleSignalRow[] {
  const now = Date.now();
  return SAMPLES.map((s, i) => ({
    workspace_id: workspaceId,
    signal_type: "qualitative",
    source: s.source,
    category: "feedback",
    text_content: s.text,
    urgency: "medium",
    tags: s.tags,
    metadata: { sample: true },
    recorded_at: new Date(now - (i + 1) * 86400000).toISOString(),
  }));
}

/** Insert the sample signals into the user's workspace (RLS allows own-workspace insert). */
export async function loadSampleData(workspaceId: number): Promise<number> {
  const rows = sampleSignals(workspaceId);
  const { error } = await supabase.from("signals").insert(rows as never);
  if (error) throw error;
  return rows.length;
}
