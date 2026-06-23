import { serve } from "https://deno.land/std@0.168.0/http/server.ts";
import { createClient } from "https://esm.sh/@supabase/supabase-js@2.49.1";
import { callTool, embed, toVectorLiteral } from "../_shared/ai.ts";

const corsHeaders = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type",
};

const SYSTEM_PROMPT = `You are a customer-feedback analyst. For each feedback item you receive, extract:
- sentiment: one of positive | neutral | negative | mixed
- sentiment_score: number from -1 (very negative) to 1 (very positive)
- urgency: one of low | medium | high | critical
- tags: 1-3 short snake_case theme tags (e.g. checkout_failure, late_delivery, onboarding_friction, pricing_unclear)
Return one enrichment per input item, preserving its id.`;

const MAP_THRESHOLD = Number(Deno.env.get("MAP_THRESHOLD") ?? "0.55"); // cosine floor; tunable

async function mapSignalToNode(
  db: ReturnType<typeof createClient>,
  workspaceId: number,
  signalId: number,
  text: string,
) {
  if (!text) return;
  const [vec] = await embed(text);
  const { data: matches, error } = await db.rpc("match_taxonomy_nodes", {
    p_workspace_id: workspaceId,
    p_query_embedding: toVectorLiteral(vec),
    p_match_count: 5,
  });
  if (error || !matches?.length) return;
  const top = (matches as { id: string; similarity: number }[])[0];
  if (top.similarity < MAP_THRESHOLD) return; // unmapped → left for Phase 2 discovery
  await db.from("signal_node_map").upsert(
    { signal_id: signalId, node_id: top.id, score: top.similarity, mapped_by: "system_auto" },
    { onConflict: "signal_id,node_id" },
  );
  const { data: node } = await db.from("taxonomy_nodes").select("times_matched").eq("id", top.id).single();
  await db.from("taxonomy_nodes")
    .update({ times_matched: ((node?.times_matched as number) ?? 0) + 1, last_matched_at: new Date().toISOString() })
    .eq("id", top.id);
}

serve(async (req) => {
  if (req.method === "OPTIONS") return new Response(null, { headers: corsHeaders });

  try {
    const { workspace_id, signal_id, limit } = await req.json();
    const db = createClient(Deno.env.get("SUPABASE_URL")!, Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!);

    // Target qualitative signals that haven't been enriched yet.
    let q = db
      .from("signals")
      .select("id, text_content, metadata, workspace_id")
      .eq("signal_type", "qualitative")
      .not("text_content", "is", null)
      .limit(limit ?? 25);
    if (signal_id) q = q.eq("id", signal_id);
    else q = q.eq("workspace_id", workspace_id).is("sentiment", null);

    const { data: signals, error } = await q;
    if (error) throw error;
    if (!signals?.length) {
      return new Response(JSON.stringify({ enriched: 0, reason: "Nothing to enrich" }), {
        headers: { ...corsHeaders, "Content-Type": "application/json" },
      });
    }

    const items = signals.map((s: { id: number; text_content: string }) => ({ id: s.id, text: s.text_content }));

    const tools = [{
      type: "function",
      function: {
        name: "submit_enrichments",
        description: "Submit per-item feedback enrichments",
        parameters: {
          type: "object",
          properties: {
            enrichments: {
              type: "array",
              items: {
                type: "object",
                properties: {
                  id: { type: "integer" },
                  sentiment: { type: "string", enum: ["positive", "neutral", "negative", "mixed"] },
                  sentiment_score: { type: "number" },
                  urgency: { type: "string", enum: ["low", "medium", "high", "critical"] },
                  tags: { type: "array", items: { type: "string" } },
                },
                required: ["id", "sentiment", "sentiment_score", "urgency", "tags"],
              },
            },
          },
          required: ["enrichments"],
        },
      },
    }];

    const result = await callTool({
      system: SYSTEM_PROMPT,
      user: "Enrich these feedback items:\n\n" + JSON.stringify(items, null, 2),
      tool: tools[0],
      toolName: "submit_enrichments",
    });
    const { enrichments } = result as {
      enrichments: { id: number; sentiment: string; sentiment_score: number; urgency: string; tags: string[] }[];
    };

    const metaById = new Map(signals.map((s: { id: number; metadata: Record<string, unknown> | null }) => [s.id, s.metadata ?? {}]));
    let enriched = 0;
    for (const e of enrichments ?? []) {
      const { error: upErr } = await db
        .from("signals")
        .update({
          sentiment: e.sentiment,
          sentiment_score: e.sentiment_score,
          urgency: e.urgency,
          tags: e.tags,
          metadata: { ...(metaById.get(e.id) as Record<string, unknown>), enriched: true },
        })
        .eq("id", e.id);
      if (!upErr) {
        enriched++;
        try {
          const sig = signals.find((s: { id: number }) => s.id === e.id) as
            { id: number; text_content: string; workspace_id: number } | undefined;
          if (sig?.text_content) await mapSignalToNode(db, sig.workspace_id, sig.id, sig.text_content);
        } catch (mapErr) { console.error("map skip", e.id, mapErr); }
      }
    }

    return new Response(JSON.stringify({ enriched }), {
      headers: { ...corsHeaders, "Content-Type": "application/json" },
    });
  } catch (e) {
    console.error("enrich-signal error:", e);
    const status = (e as { status?: number })?.status ?? 500;
    return new Response(JSON.stringify({ error: e instanceof Error ? e.message : "Unknown error" }), {
      status, headers: { ...corsHeaders, "Content-Type": "application/json" },
    });
  }
});
