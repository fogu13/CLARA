import { serve } from "https://deno.land/std@0.168.0/http/server.ts";
import { createClient } from "https://esm.sh/@supabase/supabase-js@2.49.1";
import { callTool, embed, toVectorLiteral } from "../_shared/ai.ts";

const corsHeaders = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type",
};

const CLUSTER_EPS = Number(Deno.env.get("CLUSTER_EPS") ?? "0.70");
const MIN_CLUSTER = Number(Deno.env.get("MIN_CLUSTER") ?? "3");

function cosineSim(a: number[], b: number[]): number {
  let dot = 0, na = 0, nb = 0;
  for (let i = 0; i < a.length; i++) { dot += a[i] * b[i]; na += a[i] * a[i]; nb += b[i] * b[i]; }
  const denom = Math.sqrt(na) * Math.sqrt(nb);
  return denom === 0 ? 0 : dot / denom;
}
function clusterByThreshold(vectors: number[][], threshold: number, minSize: number): number[][] {
  const used = new Array(vectors.length).fill(false);
  const clusters: number[][] = [];
  for (let i = 0; i < vectors.length; i++) {
    if (used[i]) continue;
    const group = [i]; used[i] = true;
    for (let j = i + 1; j < vectors.length; j++) {
      if (!used[j] && cosineSim(vectors[i], vectors[j]) >= threshold) { group.push(j); used[j] = true; }
    }
    if (group.length >= minSize) clusters.push(group);
  }
  return clusters;
}
function centroid(vectors: number[][]): number[] {
  const out = new Array(vectors[0].length).fill(0);
  for (const v of vectors) for (let i = 0; i < v.length; i++) out[i] += v[i];
  return out.map((x) => x / vectors.length);
}
function avgCohesion(vectors: number[][]): number {
  let sum = 0, n = 0;
  for (let i = 0; i < vectors.length; i++) for (let j = i + 1; j < vectors.length; j++) { sum += cosineSim(vectors[i], vectors[j]); n++; }
  return n === 0 ? 1 : sum / n;
}
function slugify(s: string): string {
  return s.trim().toLowerCase().replace(/[^a-z0-9]+/g, "_").replace(/^_+|_+$/g, "");
}

const NAME_TOOL = {
  type: "function",
  function: {
    name: "name_theme",
    description: "Name a cluster of related customer feedback as a single theme",
    parameters: {
      type: "object",
      properties: {
        name: { type: "string", description: "short snake_case theme name, e.g. refund_delay" },
        description: { type: "string", description: "one sentence describing the theme" },
      },
      required: ["name", "description"],
    },
  },
};

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

    const { data: rows, error } = await db.rpc("unmapped_signals", { p_workspace_id: workspace_id, p_limit: limit ?? 200 });
    if (error) throw error;
    const sigs = (rows ?? []) as { id: number; text_content: string }[];
    if (sigs.length < MIN_CLUSTER) {
      return new Response(JSON.stringify({ candidates: 0, reason: "Not enough unmapped signals" }), {
        headers: { ...corsHeaders, "Content-Type": "application/json" },
      });
    }

    const vectors = await embed(sigs.map((s) => s.text_content));
    const clusters = clusterByThreshold(vectors, CLUSTER_EPS, MIN_CLUSTER);

    let candidates = 0;
    for (const idxs of clusters) {
      const clusterVecs = idxs.map((i) => vectors[i]);
      const clusterSigs = idxs.map((i) => sigs[i]);
      const c = centroid(clusterVecs);

      const { data: near } = await db.rpc("match_taxonomy_nodes", {
        p_workspace_id: workspace_id, p_query_embedding: toVectorLiteral(c), p_match_count: 1,
      });
      const parent = (near as { id: string; level: number }[] | null)?.[0] ?? null;
      const level = parent ? Math.min(parent.level + 1, 3) : 1;

      let named: { name: string; description: string };
      try {
        named = await callTool({
          system: "You name clusters of related customer feedback as one concise theme.",
          user: "Feedback in this cluster:\n" + clusterSigs.map((s) => `- ${s.text_content}`).join("\n"),
          tool: NAME_TOOL, toolName: "name_theme",
        }) as { name: string; description: string };
      } catch (e) {
        // Naming is best-effort: if the chat model is unavailable/rate-limited, still create the
        // candidate with a provisional name (the human renames it in the review queue).
        console.error("name fallback", e);
        const lead = (clusterSigs[0].text_content || "theme").split(/\s+/).slice(0, 4).join(" ");
        named = { name: lead, description: "Auto-discovered theme — rename in review." };
      }

      const slug = slugify(named.name);
      if (!slug) continue;
      const cohesion = avgCohesion(clusterVecs);

      const { error: insErr } = await db.from("taxonomy_nodes").upsert({
        workspace_id, parent_id: parent?.id ?? null, level,
        name: named.name, slug, description: named.description,
        status: "candidate", origin: "discovered", confidence: cohesion,
        embedding: toVectorLiteral(c),
        evidence: { signal_ids: clusterSigs.map((s) => s.id), samples: clusterSigs.slice(0, 5).map((s) => s.text_content), size: clusterSigs.length, cohesion },
      }, { onConflict: "workspace_id,parent_id,slug", ignoreDuplicates: true });
      if (insErr) console.error("candidate insert error", insErr);
      else candidates++;
    }

    return new Response(JSON.stringify({ scanned: sigs.length, clusters: clusters.length, candidates }), {
      headers: { ...corsHeaders, "Content-Type": "application/json" },
    });
  } catch (e) {
    console.error("evolve-taxonomy error:", e);
    const status = (e as { status?: number })?.status ?? 500;
    return new Response(JSON.stringify({ error: e instanceof Error ? e.message : "Unknown error" }), {
      status, headers: { ...corsHeaders, "Content-Type": "application/json" },
    });
  }
});
