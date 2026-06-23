import { serve } from "https://deno.land/std@0.168.0/http/server.ts";
import { createClient } from "https://esm.sh/@supabase/supabase-js@2.49.1";
import { embed, toVectorLiteral } from "../_shared/ai.ts";

const corsHeaders = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type",
};

// Map signals to taxonomy nodes using embeddings only (no LLM enrichment), so this works
// even when the chat model is rate-limited. Tunable via the MAP_THRESHOLD secret.
const MAP_THRESHOLD = Number(Deno.env.get("MAP_THRESHOLD") ?? "0.55");

serve(async (req) => {
  if (req.method === "OPTIONS") return new Response(null, { headers: corsHeaders });
  try {
    const { workspace_id, limit } = await req.json();
    if (!workspace_id) {
      return new Response(JSON.stringify({ error: "workspace_id is required" }), {
        status: 400, headers: { ...corsHeaders, "Content-Type": "application/json" },
      });
    }
    const db = createClient(Deno.env.get("SUPABASE_URL")!, Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!);

    const { data: rows, error } = await db.rpc("unmapped_signals", {
      p_workspace_id: workspace_id,
      p_limit: limit ?? 100,
    });
    if (error) throw error;
    const sigs = (rows ?? []) as { id: number; text_content: string }[];
    if (!sigs.length) {
      return new Response(JSON.stringify({ scanned: 0, mapped: 0, threshold: MAP_THRESHOLD }), {
        headers: { ...corsHeaders, "Content-Type": "application/json" },
      });
    }

    const vectors = await embed(sigs.map((s) => s.text_content));

    const upserts: { signal_id: number; node_id: string; score: number; mapped_by: string }[] = [];
    const nodeBump = new Map<string, number>();
    const sample: { signal_id: number; node: string; sim: number }[] = [];

    for (let i = 0; i < sigs.length; i++) {
      const { data: matches } = await db.rpc("match_taxonomy_nodes", {
        p_workspace_id: workspace_id,
        p_query_embedding: toVectorLiteral(vectors[i]),
        p_match_count: 3,
      });
      const top = (matches as { id: string; name: string; similarity: number }[] | null)?.[0];
      if (!top) continue;
      if (sample.length < 8) sample.push({ signal_id: sigs[i].id, node: top.name, sim: Number(top.similarity.toFixed(3)) });
      if (top.similarity >= MAP_THRESHOLD) {
        upserts.push({ signal_id: sigs[i].id, node_id: top.id, score: top.similarity, mapped_by: "system_auto" });
        nodeBump.set(top.id, (nodeBump.get(top.id) ?? 0) + 1);
      }
    }

    if (upserts.length) {
      const { error: upErr } = await db.from("signal_node_map").upsert(upserts, { onConflict: "signal_id,node_id" });
      if (upErr) throw upErr;
      const now = new Date().toISOString();
      for (const [nodeId, n] of nodeBump) {
        const { data: node } = await db.from("taxonomy_nodes").select("times_matched").eq("id", nodeId).single();
        await db.from("taxonomy_nodes")
          .update({ times_matched: ((node?.times_matched as number) ?? 0) + n, last_matched_at: now })
          .eq("id", nodeId);
      }
    }

    return new Response(JSON.stringify({ scanned: sigs.length, mapped: upserts.length, threshold: MAP_THRESHOLD, sample }), {
      headers: { ...corsHeaders, "Content-Type": "application/json" },
    });
  } catch (e) {
    console.error("backfill-mappings error:", e);
    const status = (e as { status?: number })?.status ?? 500;
    return new Response(JSON.stringify({ error: e instanceof Error ? e.message : "Unknown error" }), {
      status, headers: { ...corsHeaders, "Content-Type": "application/json" },
    });
  }
});
