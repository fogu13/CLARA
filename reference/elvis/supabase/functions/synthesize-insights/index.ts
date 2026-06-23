import { serve } from "https://deno.land/std@0.168.0/http/server.ts";
import { createClient } from "https://esm.sh/@supabase/supabase-js@2.49.1";
import { callTool } from "../_shared/ai.ts";

const corsHeaders = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type",
};

interface Sig {
  id: number;
  text_content: string | null;
  metric_name: string | null;
  signal_type: string;
  urgency: string;
  sentiment: string | null;
  contact_count: number | null;
  tags: string[] | null;
  metadata: Record<string, unknown> | null;
}

const URANK: Record<string, number> = { low: 1, medium: 2, high: 3, critical: 4 };

// Design decision #3 — cross-signal severity. Composite of the strongest urgency among
// member signals, the volume of corroborating signals, and how negative the cluster is.
function crossSignalSeverity(sigs: Sig[]): string {
  const maxU = Math.max(...sigs.map((s) => URANK[s.urgency] ?? 1));
  const volume = sigs.length;
  let score = maxU + Math.min(3, Math.floor(volume / 2)); // urgency (1-4) + volume bonus (0-3)
  const negFrac = sigs.filter((s) => s.sentiment === "negative").length / volume;
  if (negFrac >= 0.6) score += 1;
  if (score >= 6) return "critical";
  if (score >= 4) return "high";
  if (score >= 2) return "medium";
  return "low";
}

const SYSTEM_PROMPT = `You are a customer-insight synthesist. Given a cluster of related customer signals (all about the same theme), produce a single actionable insight:
- title: short, specific
- summary: 1-2 sentences citing the evidence
- category: one of content_clarity | product_issue | churn_risk | campaign_performance | ux_friction | sentiment_shift | engagement_drop | positive_trend | compliance_concern
- impact_score: 0-10
- confidence: 0-1
- target_team: one of marketing | product | cx | sales | engineering
- suggested_actions: up to 2 items, each {type (create_ticket|notify|create_segment|draft_email), title, description, priority (1-3)}
Do NOT set severity — it is computed separately.`;

async function synthesizeCluster(tag: string, sigs: Sig[]) {
  const evidence = sigs.map((s) => s.text_content ?? `${s.metric_name}`).filter(Boolean);
  const tool = {
    type: "function",
    function: {
      name: "submit_insight",
      parameters: {
        type: "object",
        properties: {
          title: { type: "string" },
          summary: { type: "string" },
          category: { type: "string" },
          impact_score: { type: "number" },
          confidence: { type: "number" },
          target_team: { type: "string" },
          suggested_actions: {
            type: "array",
            items: {
              type: "object",
              properties: {
                type: { type: "string" },
                title: { type: "string" },
                description: { type: "string" },
                priority: { type: "integer" },
              },
              required: ["type", "title", "description", "priority"],
            },
          },
        },
        required: ["title", "summary", "category", "impact_score", "confidence", "target_team", "suggested_actions"],
      },
    },
  };

  return await callTool({
    system: SYSTEM_PROMPT,
    user: `Theme: ${tag}\nSignals (${sigs.length}):\n` + JSON.stringify(evidence, null, 2),
    tool,
    toolName: "submit_insight",
  });
}

serve(async (req) => {
  if (req.method === "OPTIONS") return new Response(null, { headers: corsHeaders });

  try {
    const { workspace_id } = await req.json();
    if (!workspace_id) {
      return new Response(JSON.stringify({ error: "workspace_id is required" }), {
        status: 400, headers: { ...corsHeaders, "Content-Type": "application/json" },
      });
    }
    const db = createClient(Deno.env.get("SUPABASE_URL")!, Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!);

    // Enriched signals not yet folded into an insight.
    const { data: signals, error } = await db
      .from("signals")
      .select("id, text_content, metric_name, signal_type, urgency, sentiment, contact_count, tags, metadata")
      .eq("workspace_id", workspace_id)
      .not("tags", "is", null)
      .order("recorded_at", { ascending: false })
      .limit(100);
    if (error) throw error;

    const pending = (signals as Sig[]).filter((s) => !(s.metadata?.synthesized));
    if (!pending.length) {
      return new Response(JSON.stringify({ created: 0, reason: "No new signals to synthesize" }), {
        headers: { ...corsHeaders, "Content-Type": "application/json" },
      });
    }

    // Cluster by primary (first) tag.
    const clusters = new Map<string, Sig[]>();
    for (const s of pending) {
      const tag = s.tags?.[0];
      if (!tag) continue;
      (clusters.get(tag) ?? clusters.set(tag, []).get(tag)!).push(s);
    }

    let created = 0;
    for (const [tag, sigs] of clusters) {
      if (sigs.length < 2) continue; // need corroboration to form an insight

      const severity = crossSignalSeverity(sigs);
      let gen;
      try {
        gen = await synthesizeCluster(tag, sigs);
      } catch (e) {
        console.error("cluster synth failed", tag, e);
        continue;
      }

      const qual = sigs.filter((s) => s.signal_type === "qualitative").length;
      const quant = sigs.length - qual;
      const affected = sigs.reduce((n, s) => n + (s.contact_count ?? 1), 0);
      const maxUrgency = sigs.reduce((u, s) => (URANK[s.urgency] > URANK[u] ? s.urgency : u), "low");

      const { error: insErr } = await db.from("insights").insert({
        workspace_id,
        title: gen.title,
        summary: gen.summary,
        category: gen.category,
        signal_ids: sigs.map((s) => s.id),
        qual_signal_count: qual,
        quant_signal_count: quant,
        impact_score: gen.impact_score,
        confidence: gen.confidence,
        severity,
        affected_contacts: affected,
        urgency: maxUrgency,
        target_team: gen.target_team,
        suggested_actions: gen.suggested_actions ?? [],
        status: "new",
      });
      if (insErr) {
        console.error("insight insert failed", insErr);
        continue;
      }
      created++;

      // Mark these signals as synthesized so they aren't re-clustered.
      for (const s of sigs) {
        await db.from("signals").update({ metadata: { ...(s.metadata ?? {}), synthesized: true } }).eq("id", s.id);
      }
    }

    return new Response(JSON.stringify({ created }), {
      headers: { ...corsHeaders, "Content-Type": "application/json" },
    });
  } catch (e) {
    console.error("synthesize-insights error:", e);
    const status = (e as { status?: number })?.status ?? 500;
    return new Response(JSON.stringify({ error: e instanceof Error ? e.message : "Unknown error" }), {
      status, headers: { ...corsHeaders, "Content-Type": "application/json" },
    });
  }
});
