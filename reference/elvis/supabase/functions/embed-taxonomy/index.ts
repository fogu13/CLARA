import { serve } from "https://deno.land/std@0.168.0/http/server.ts";
import { createClient } from "https://esm.sh/@supabase/supabase-js@2.49.1";
import { embed, toVectorLiteral } from "../_shared/ai.ts";

const corsHeaders = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type",
};

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

    const { data: nodes, error } = await db
      .from("taxonomy_nodes")
      .select("id, name, description")
      .eq("workspace_id", workspace_id)
      .is("embedding", null)
      .limit(200);
    if (error) throw error;
    if (!nodes?.length) {
      return new Response(JSON.stringify({ embedded: 0 }), { headers: { ...corsHeaders, "Content-Type": "application/json" } });
    }

    const texts = nodes.map((n: { name: string; description: string | null }) =>
      `${n.name}${n.description ? ` — ${n.description}` : ""}`);
    const vectors = await embed(texts);

    let embedded = 0;
    for (let i = 0; i < nodes.length; i++) {
      const { error: upErr } = await db
        .from("taxonomy_nodes")
        .update({ embedding: toVectorLiteral(vectors[i]) })
        .eq("id", (nodes[i] as { id: string }).id);
      if (!upErr) embedded++;
    }
    return new Response(JSON.stringify({ embedded }), { headers: { ...corsHeaders, "Content-Type": "application/json" } });
  } catch (e) {
    console.error("embed-taxonomy error:", e);
    const status = (e as { status?: number })?.status ?? 500;
    return new Response(JSON.stringify({ error: e instanceof Error ? e.message : "Unknown error" }), {
      status, headers: { ...corsHeaders, "Content-Type": "application/json" },
    });
  }
});
