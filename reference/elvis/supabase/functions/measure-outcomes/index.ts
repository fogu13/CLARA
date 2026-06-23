import { serve } from "https://deno.land/std@0.168.0/http/server.ts";
import { createClient } from "https://esm.sh/@supabase/supabase-js@2.49.1";

const corsHeaders = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type",
};

const clamp01 = (n: number) => Math.max(0, Math.min(1, n));

// Phase B2 — close the loop. For an insight whose measurement window has elapsed, recompute
// the outcome metric from signals and score how much the issue improved vs. its baseline.
async function measureInsight(
  db: ReturnType<typeof createClient>,
  insight: Record<string, unknown>,
) {
  const wsId = insight.workspace_id as number;
  const metric = (insight.outcome_metric as string) ?? "affected_contacts";
  const baseline = Number(insight.outcome_baseline ?? insight.affected_contacts ?? 0);
  const since = (insight.status_changed_at as string) ?? (insight.detected_at as string);

  let measured = baseline;
  let summary: string;

  if (metric.startsWith("tag:")) {
    const tag = metric.slice(4);
    // New occurrences of the same theme after the action was taken.
    const { count } = await db
      .from("signals")
      .select("id", { count: "exact", head: true })
      .eq("workspace_id", wsId)
      .contains("tags", [tag])
      .gt("recorded_at", since);
    measured = count ?? 0;
    summary = `Recurrence of "${tag}" after action: ${measured} new signal(s) vs baseline of ${baseline}.`;
  } else {
    // No themed baseline available — record a neutral result rather than overclaiming.
    summary = `No themed signal to measure; baseline ${metric} = ${baseline}. Outcome inconclusive — confirm manually.`;
  }

  const score = baseline > 0 ? clamp01(1 - measured / baseline) : measured === 0 ? 1 : 0.5;
  const now = new Date().toISOString();

  await db
    .from("insights")
    .update({
      outcome_measured: measured,
      resolution_score: score,
      resolution_summary: summary,
      measured_at: now,
      status: "resolved",
      status_changed_at: now,
      resolved_at: now,
    })
    .eq("id", insight.id as number);

  return { insight_id: insight.id, metric, baseline, measured, resolution_score: score, summary };
}

serve(async (req) => {
  if (req.method === "OPTIONS") return new Response(null, { headers: corsHeaders });

  try {
    const body = await req.json().catch(() => ({}));
    const supabaseUrl = Deno.env.get("SUPABASE_URL")!;
    const serviceKey = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!;
    const db = createClient(supabaseUrl, serviceKey);

    // Single insight (manual "Measure now") or all due (scheduled pass).
    let targets: Record<string, unknown>[] = [];
    if (body.insight_id) {
      const { data, error } = await db.from("insights").select("*").eq("id", body.insight_id).single();
      if (error || !data) {
        return new Response(JSON.stringify({ error: `Insight ${body.insight_id} not found` }), {
          status: 404, headers: { ...corsHeaders, "Content-Type": "application/json" },
        });
      }
      targets = [data];
    } else {
      const { data, error } = await db
        .from("insights")
        .select("*")
        .is("measured_at", null)
        .lte("measurement_due_at", new Date().toISOString())
        .in("status", ["action_planned", "action_taken", "measuring"]);
      if (error) throw error;
      targets = data ?? [];
    }

    const results = [];
    for (const insight of targets) results.push(await measureInsight(db, insight));

    return new Response(JSON.stringify({ measured: results.length, results }), {
      headers: { ...corsHeaders, "Content-Type": "application/json" },
    });
  } catch (e) {
    console.error("measure-outcomes error:", e);
    return new Response(JSON.stringify({ error: e instanceof Error ? e.message : "Unknown error" }), {
      status: 500, headers: { ...corsHeaders, "Content-Type": "application/json" },
    });
  }
});
