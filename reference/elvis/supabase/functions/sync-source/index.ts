import { serve } from "https://deno.land/std@0.168.0/http/server.ts";
import { createClient } from "https://esm.sh/@supabase/supabase-js@2.49.1";

const corsHeaders = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type",
};

const REQUIRED_CONFIG: Record<string, string[]> = {
  zendesk: ["subdomain", "email", "api_token"],
  typeform: ["form_id", "api_token"],
  hubspot: ["api_key"],
  intercom: ["access_token"],
  google_analytics: ["property_id", "credentials"],
  api_poll: ["endpoint"],
};

function getByPath(obj: unknown, path: string): unknown {
  if (!path) return obj;
  return path.split(".").reduce<unknown>(
    (acc, k) => (acc && typeof acc === "object" ? (acc as Record<string, unknown>)[k] : undefined),
    obj,
  );
}

function parseCsv(text: string): Record<string, string>[] {
  const lines = text.split(/\r?\n/).filter((l) => l.trim());
  if (lines.length < 2) return [];
  const split = (line: string) => {
    const out: string[] = [];
    let cur = "", q = false;
    for (let i = 0; i < line.length; i++) {
      const c = line[i];
      if (c === '"') { if (q && line[i + 1] === '"') { cur += '"'; i++; } else q = !q; }
      else if (c === "," && !q) { out.push(cur); cur = ""; } else cur += c;
    }
    out.push(cur);
    return out.map((s) => s.trim());
  };
  const headers = split(lines[0]);
  return lines.slice(1).map((line) => {
    const cells = split(line);
    const row: Record<string, string> = {};
    headers.forEach((h, i) => (row[h] = cells[i] ?? ""));
    return row;
  });
}

serve(async (req) => {
  if (req.method === "OPTIONS") return new Response(null, { headers: corsHeaders });

  try {
    const { source_id } = await req.json();
    if (!source_id) {
      return new Response(JSON.stringify({ error: "source_id is required" }), {
        status: 400, headers: { ...corsHeaders, "Content-Type": "application/json" },
      });
    }

    const db = createClient(Deno.env.get("SUPABASE_URL")!, Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!);
    const { data: src, error } = await db.from("signal_sources").select("*").eq("id", source_id).single();
    if (error || !src) {
      return new Response(JSON.stringify({ error: "Source not found" }), {
        status: 404, headers: { ...corsHeaders, "Content-Type": "application/json" },
      });
    }

    const type = src.source_type as string;
    const config = (src.config as Record<string, unknown>) ?? {};
    const now = new Date().toISOString();

    if (["webhook", "custom_webhook", "csv_upload"].includes(type)) {
      await db.from("signal_sources").update({ last_synced_at: now, sync_status: "idle", sync_error: null }).eq("id", source_id);
      return new Response(JSON.stringify({ synced: 0, note: `${type} ingests via webhook/CSV, not pull.` }), {
        headers: { ...corsHeaders, "Content-Type": "application/json" },
      });
    }

    if (type === "api_poll") {
      const endpoint = config.endpoint as string;
      if (!endpoint) {
        await db.from("signal_sources").update({ sync_status: "error", sync_error: "Missing endpoint", last_synced_at: now }).eq("id", source_id);
        return new Response(JSON.stringify({ synced: 0, error: "Missing endpoint" }), {
          headers: { ...corsHeaders, "Content-Type": "application/json" },
        });
      }
      try {
        const headers: Record<string, string> = { "Accept": "application/json, text/csv, */*" };
        if (config.auth_header) headers["Authorization"] = String(config.auth_header);
        const resp = await fetch(endpoint, { headers });
        if (!resp.ok) throw new Error(`Endpoint returned ${resp.status}`);

        const format = (config.format as string) || "json";
        let items: Record<string, unknown>[] = [];
        if (format === "csv") {
          items = parseCsv(await resp.text());
        } else {
          const json = await resp.json();
          const arr = getByPath(json, (config.items_path as string) || "");
          items = Array.isArray(arr) ? (arr as Record<string, unknown>[]) : (Array.isArray(json) ? json : []);
        }

        const map = (config.map as Record<string, string>) ?? {};

        const { data: ex } = await db.from("signals").select("metadata")
          .eq("workspace_id", src.workspace_id).contains("metadata", { source_id });
        const seen = new Set(
          (ex ?? [])
            .map((r: { metadata: Record<string, unknown> | null }) => r.metadata?.external_id)
            .filter((v) => v != null).map(String),
        );

        const rows: Record<string, unknown>[] = [];
        let skipped = 0;
        for (const it of items) {
          const text = map.text && it[map.text] != null ? String(it[map.text]) : "";
          const metricName = map.metric_name && it[map.metric_name] != null ? String(it[map.metric_name]) : "";
          if (!text && !metricName) { skipped++; continue; }
          const extId = map.external_id && it[map.external_id] != null ? String(it[map.external_id]) : undefined;
          if (extId && seen.has(extId)) { skipped++; continue; }

          const tagsRaw = map.tags ? it[map.tags] : undefined;
          const tags = Array.isArray(tagsRaw)
            ? tagsRaw
            : (typeof tagsRaw === "string" ? tagsRaw.split(/[;,]/).map((t) => t.trim()).filter(Boolean) : []);

          rows.push({
            workspace_id: src.workspace_id,
            signal_type: metricName && !text ? "quantitative" : "qualitative",
            source: (src.name as string) || "api_poll",
            category: "feedback",
            text_content: text || null,
            metric_name: metricName || null,
            metric_value: map.metric_value && it[map.metric_value] != null ? Number(it[map.metric_value]) : null,
            urgency: "low",
            is_anomaly: false,
            contact_count: 1,
            tags,
            metadata: { source_id, external_id: extId ?? null, imported: true },
            recorded_at: map.recorded_at && it[map.recorded_at] ? String(it[map.recorded_at]) : now,
          });
          if (extId) seen.add(extId);
        }

        if (rows.length) {
          const { error: insErr } = await db.from("signals").insert(rows);
          if (insErr) throw insErr;
        }
        await db.from("signal_sources").update({ last_synced_at: now, sync_status: "idle", sync_error: null }).eq("id", source_id);
        return new Response(JSON.stringify({ synced: rows.length, skipped }), {
          headers: { ...corsHeaders, "Content-Type": "application/json" },
        });
      } catch (e) {
        const msg = e instanceof Error ? e.message : "Sync error";
        await db.from("signal_sources").update({ sync_status: "error", sync_error: msg, last_synced_at: now }).eq("id", source_id);
        return new Response(JSON.stringify({ synced: 0, error: msg }), {
          headers: { ...corsHeaders, "Content-Type": "application/json" },
        });
      }
    }

    const required = REQUIRED_CONFIG[type] ?? [];
    const missing = required.filter((k) => !config[k]);
    if (missing.length) {
      await db.from("signal_sources").update({ sync_status: "error", sync_error: `Missing credentials: ${missing.join(", ")}`, last_synced_at: now }).eq("id", source_id);
      return new Response(JSON.stringify({ synced: 0, error: `Missing credentials: ${missing.join(", ")}` }), {
        headers: { ...corsHeaders, "Content-Type": "application/json" },
      });
    }
    await db.from("signal_sources").update({ sync_status: "idle", sync_error: null, last_synced_at: now }).eq("id", source_id);
    return new Response(JSON.stringify({ synced: 0, note: `${type} credentials present; live pull is scaffolded but not enabled in this build.` }), {
      headers: { ...corsHeaders, "Content-Type": "application/json" },
    });
  } catch (e) {
    console.error("sync-source error:", e);
    return new Response(JSON.stringify({ error: e instanceof Error ? e.message : "Unknown error" }), {
      status: 500, headers: { ...corsHeaders, "Content-Type": "application/json" },
    });
  }
});
