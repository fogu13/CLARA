import { serve } from "https://deno.land/std@0.168.0/http/server.ts";
import { createClient } from "https://esm.sh/@supabase/supabase-js@2.49.1";

const corsHeaders = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type",
};

// Phase E1 — public webhook ingestion. External systems POST feedback items here.
// Body: { source_id?, workspace_id?, token?, items: [{ type, source, text, metric_name, metric_value, tags }] }
// If the source has a token configured (config.token), it must match.
serve(async (req) => {
  if (req.method === "OPTIONS") return new Response(null, { headers: corsHeaders });

  try {
    const { source_id, workspace_id, token, items } = await req.json();
    if (!Array.isArray(items) || items.length === 0) {
      return new Response(JSON.stringify({ error: "items[] is required" }), {
        status: 400, headers: { ...corsHeaders, "Content-Type": "application/json" },
      });
    }

    const db = createClient(Deno.env.get("SUPABASE_URL")!, Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!);

    let wsId = workspace_id as number | undefined;
    let sourceType = "custom_webhook";
    if (source_id) {
      const { data: src, error } = await db.from("signal_sources").select("*").eq("id", source_id).single();
      if (error || !src) {
        return new Response(JSON.stringify({ error: "Source not found" }), {
          status: 404, headers: { ...corsHeaders, "Content-Type": "application/json" },
        });
      }
      const cfgToken = (src.config as Record<string, unknown>)?.token;
      if (cfgToken && cfgToken !== token) {
        return new Response(JSON.stringify({ error: "Invalid token" }), {
          status: 401, headers: { ...corsHeaders, "Content-Type": "application/json" },
        });
      }
      wsId = src.workspace_id;
      sourceType = src.source_type;
    }

    if (!wsId) {
      return new Response(JSON.stringify({ error: "workspace_id or source_id is required" }), {
        status: 400, headers: { ...corsHeaders, "Content-Type": "application/json" },
      });
    }

    const rows = items.map((it: Record<string, unknown>) => {
      const isQuant = String(it.type ?? "").toLowerCase() === "quantitative" || (!it.text && !!it.metric_name);
      return {
        workspace_id: wsId,
        signal_type: isQuant ? "quantitative" : "qualitative",
        source: (it.source as string) || sourceType,
        category: "feedback",
        text_content: (it.text as string) ?? null,
        metric_name: (it.metric_name as string) ?? null,
        metric_value: it.metric_value != null ? Number(it.metric_value) : null,
        urgency: "low",
        is_anomaly: false,
        contact_count: 1,
        tags: Array.isArray(it.tags) ? it.tags : typeof it.tags === "string" ? (it.tags as string).split(";").map((t) => t.trim()).filter(Boolean) : [],
        metadata: { ingested: true },
        recorded_at: (it.recorded_at as string) || new Date().toISOString(),
      };
    });

    const { error: insErr } = await db.from("signals").insert(rows);
    if (insErr) throw insErr;

    if (source_id) {
      await db.from("signal_sources")
        .update({ last_synced_at: new Date().toISOString(), sync_status: "idle", sync_error: null })
        .eq("id", source_id);
    }

    return new Response(JSON.stringify({ ingested: rows.length }), {
      headers: { ...corsHeaders, "Content-Type": "application/json" },
    });
  } catch (e) {
    console.error("ingest-webhook error:", e);
    return new Response(JSON.stringify({ error: e instanceof Error ? e.message : "Unknown error" }), {
      status: 500, headers: { ...corsHeaders, "Content-Type": "application/json" },
    });
  }
});
