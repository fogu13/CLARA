# Connectors — Generic API/CSV Poller Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development. Steps use checkbox (`- [ ]`) syntax.

**Goal:** A workspace can add a **generic poller** source pointing at any HTTP endpoint that returns JSON or CSV feedback, with a field mapping, and pull it into `signals` (on demand via "Sync now", or on a schedule). The existing enrich → map (taxonomy) → synthesize pipeline then takes over. Provider-agnostic; the reusable framework makes named connectors (Zendesk/Typeform/…) cheap to add later.

**Architecture:** Implement the real `api_poll` branch in the existing `sync-source` edge function: fetch the endpoint (optional `Authorization` header) → parse JSON (navigate an `items_path`) or CSV → map each item to a signal via a configurable field map → **dedupe** by a per-source `external_id` → insert. The existing `Sources` page already lists sources, toggles enable, and has "Sync now" wired to `sync-source`; we add an `api_poll` config form to its "Add source" dialog. Dedupe state lives in `signals.metadata` (`{ source_id, external_id }`) — no schema change needed.

**Tech Stack:** Supabase Deno edge function, React 18 + Vite + TS + shadcn/ui, React Query. No migration required.

**Conventions (CLAUDE.md):** `signals.tags` is JSONB (insert a JS array via supabase-js — PostgREST maps it to a JSON array, which is correct here); `vite build` doesn't type-check; deploy `sync-source` to `grdwaolihoeaqaerovdg`.

**Config shape stored in `signal_sources.config` for `api_poll`:**
```jsonc
{
  "endpoint": "https://…",          // required
  "format": "json" | "csv",          // default json
  "auth_header": "Bearer xxx",       // optional; sent as Authorization
  "items_path": "data",              // JSON: dot-path to the array (empty = root array)
  "map": {                            // field names within each item
    "text": "comment", "metric_name": "", "metric_value": "",
    "tags": "labels", "recorded_at": "created_at", "external_id": "id"
  }
}
```

---

## File Structure

| File | Responsibility |
|---|---|
| `supabase/functions/sync-source/index.ts` (modify) | real `api_poll` pull: fetch → parse → map → dedupe → insert |
| `src/pages/Sources.tsx` (modify) | `api_poll` option + config form in the Add-source dialog |

---

## Task 1: Real `api_poll` pull in `sync-source`

**Files:** Modify `supabase/functions/sync-source/index.ts` (replace the whole file with the version below — it preserves the pull-free + credential-scaffold branches and adds the real poller + helpers).

- [ ] **Step 1: Replace the file contents**

```ts
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

    // Pull-free sources.
    if (["webhook", "custom_webhook", "csv_upload"].includes(type)) {
      await db.from("signal_sources").update({ last_synced_at: now, sync_status: "idle", sync_error: null }).eq("id", source_id);
      return new Response(JSON.stringify({ synced: 0, note: `${type} ingests via webhook/CSV, not pull.` }), {
        headers: { ...corsHeaders, "Content-Type": "application/json" },
      });
    }

    // Generic API/CSV poller.
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

        // Dedupe against previously-imported items from this source.
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

    // Other API connectors: credential check + structured stub (unchanged scaffold).
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
```

- [ ] **Step 2: Commit** `git add supabase/functions/sync-source/index.ts && git commit -m "feat(connectors): real api_poll pull (fetch -> map -> dedupe -> signals) in sync-source"`

- [ ] **Step 3: (controller) Deploy** `sync-source` (verify_jwt = true) to `grdwaolihoeaqaerovdg`.

- [ ] **Step 4: (controller) Live test** — create an `api_poll` source via SQL pointing at a public JSON API (e.g. JSONPlaceholder comments: `https://jsonplaceholder.typicode.com/comments`, mapping `text→body`, `external_id→id`), invoke `sync-source`, confirm signals inserted; invoke again, confirm `skipped` (dedupe). Clean up.

---

## Task 2: `api_poll` config form in the Add-source dialog

**Files:** Modify `src/pages/Sources.tsx`

READ the file first. It has `useState` for `name` + a `type` select, an `addSource` mutation that inserts `{ workspace_id, name, source_type: type, config: {} }`, and a Dialog.

- [ ] **Step 1: Add `api_poll` to the source-type options** in the dialog's type `<select>` (label e.g. "API / CSV poll", value `api_poll`). Follow the existing option list.

- [ ] **Step 2: Add config state** near the other dialog `useState`s:
```tsx
  const [poll, setPoll] = useState({ endpoint: "", format: "json", auth_header: "", items_path: "", text: "", tags: "", external_id: "", recorded_at: "" });
```

- [ ] **Step 3: Conditionally render config fields** when `type === "api_poll"` inside the Dialog body (use the existing `Input`/label styling; a native `<select>` for format json/csv). Fields: endpoint (required), format, auth_header, items_path, and map fields text/tags/external_id/recorded_at. Each bound to `poll` via `setPoll`.

- [ ] **Step 4: Include config in `addSource`** — change the insert's `config: {}` so that when `type === "api_poll"` it is:
```tsx
        config: type === "api_poll" ? {
          endpoint: poll.endpoint.trim(),
          format: poll.format,
          auth_header: poll.auth_header.trim() || undefined,
          items_path: poll.items_path.trim() || undefined,
          map: { text: poll.text.trim() || undefined, tags: poll.tags.trim() || undefined, external_id: poll.external_id.trim() || undefined, recorded_at: poll.recorded_at.trim() || undefined },
        } : {},
```
Also disable the "Add source" button when `type === "api_poll" && !poll.endpoint.trim()`.

- [ ] **Step 5: Verify** `npx tsc -p tsconfig.app.json --noEmit 2>&1 | grep -v "src/test/"` → clean; `npm run build` → `✓ built`.

- [ ] **Step 6: Commit** `git add src/pages/Sources.tsx && git commit -m "feat(connectors): api_poll config form in Add-source dialog"`

---

## Task 3: End-to-end verification + PR

- [ ] **Step 1:** `npm run build` → `✓ built`.
- [ ] **Step 2 (manual UI):** Sources → Add source → "API / CSV poll", endpoint `https://jsonplaceholder.typicode.com/comments`, map `text=body`, `external_id=id` → Add → "Sync now". Expect a toast "Synced N signal(s)"; Signals page fills. Click "Sync now" again → 0 new (deduped).
- [ ] **Step 3 (controller SQL):** confirm `select count(*) from signals where metadata->>'source_id' is not null;` increased, and re-sync added 0.
- [ ] **Step 4: PR**
```bash
git push -u origin feat/connectors-api-poll
gh pr create --base main --head feat/connectors-api-poll --title "Connectors: generic API/CSV poller" --body "Real api_poll ingestion in sync-source (fetch -> field-map -> dedupe -> signals) + config form on the Sources page. Reusable framework for named connectors next. Plan: docs/superpowers/plans/2026-06-22-connectors-api-poll.md"
```

---

## Self-review (completed)

- **Coverage:** real pull (Task 1), config UI (Task 2), dedupe (Task 1 `external_id`/`metadata`), verification (Task 3). No migration needed (dedupe via `signals.metadata`).
- **Placeholders:** none — full edge-function code; UI changes specified against the existing dialog with the exact config shape + mutation change.
- **Consistency:** the `config.map` keys written by the dialog (Task 2) match what `sync-source` reads (Task 1: `map.text/tags/external_id/recorded_at/metric_name/metric_value`). Signals shape matches the `valid_signal` constraint (skip rows with neither text nor metric_name).
- **Caveat:** scheduled auto-sync (pg_cron → `sync-source`) needs a stored service key; v1 is on-demand "Sync now" (fully working). Note as a follow-up.
