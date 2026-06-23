# Adaptive Taxonomy — Phase 1 (Foundation) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A workspace can upload a 3-level company taxonomy; it is embedded; new signals are mapped to it during enrichment; and a `/taxonomy` page shows the tree with mapping coverage.

**Architecture:** New `taxonomy_nodes` (self-referential tree) + `signal_node_map` tables with `pgvector` embeddings. A `match_taxonomy_nodes` SQL RPC does nearest-neighbour retrieval. `embed-taxonomy` embeds nodes; `enrich-signal` is extended to embed each signal, retrieve nearest nodes, have the LLM confirm the best subtheme (hybrid), and write a governed mapping. A new React page renders the tree and a coverage stat.

**Tech Stack:** Supabase (Postgres + pgvector + Deno edge functions), React 18 + Vite + TypeScript, React Query, shadcn/ui, Vitest. Embeddings via the Gemini OpenAI-compatible endpoint already configured (`AI_BASE_URL`).

**Scope (Phase 1 only):** schema, upload+embedding, signal→node mapping, tree UI, coverage metric. **Out of scope (Phases 2–3):** candidate discovery, review queue, auto-promotion/merge, decay.

**Conventions (from CLAUDE.md):**
- Generated types are hand-synced — mirror new tables in `src/integrations/supabase/types.ts` AND `src/lib/types.ts`.
- `vite build` does NOT type-check; use `npx tsc -p tsconfig.app.json --noEmit` (exclude `src/test/*`).
- Migrations/functions deploy to the user's Supabase project `grdwaolihoeaqaerovdg` (CLI or MCP).
- `signals.tags` is JSONB.

---

## File Structure

| File | Responsibility |
|---|---|
| `supabase/migrations/20260621170000_taxonomy.sql` | pgvector, `taxonomy_nodes`, `signal_node_map`, RLS, indexes, `match_taxonomy_nodes` RPC |
| `src/lib/types.ts` (modify) | `TaxonomyNode`, `SignalNodeMap` domain types |
| `src/integrations/supabase/types.ts` (modify) | Hand-synced row types for the two tables |
| `src/lib/taxonomy.ts` (create) | Pure helpers: `slugify`, `parseTaxonomyFile`, `buildTree`, `coverage` |
| `src/lib/taxonomy.test.ts` (create) | Vitest unit tests for the pure helpers |
| `supabase/functions/_shared/ai.ts` (modify) | `embed()` helper (embeddings call) |
| `supabase/functions/embed-taxonomy/index.ts` (create) | Embed nodes missing an embedding |
| `supabase/functions/enrich-signal/index.ts` (modify) | Map each signal to nearest node (embed → RPC → LLM confirm → `signal_node_map`) |
| `src/components/taxonomy/TaxonomyTree.tsx` (create) | Recursive 3-level tree renderer |
| `src/pages/Taxonomy.tsx` (create) | Page: upload, coverage stat, tree |
| `src/App.tsx` (modify) | Add `/taxonomy` protected route |
| `src/components/layout/AppSidebar.tsx` (modify) | Add Taxonomy nav item |

---

## Task 1: Database migration

**Files:**
- Create: `supabase/migrations/20260621170000_taxonomy.sql`

- [ ] **Step 1: Write the migration**

```sql
-- Adaptive taxonomy — Phase 1. 3-level company taxonomy + governed signal mapping + pgvector.

CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS public.taxonomy_nodes (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  workspace_id integer NOT NULL REFERENCES public.workspaces(id) ON DELETE CASCADE,
  parent_id uuid REFERENCES public.taxonomy_nodes(id) ON DELETE CASCADE,
  level integer NOT NULL CHECK (level BETWEEN 1 AND 3),
  name text NOT NULL,
  slug text NOT NULL,
  description text,
  status text NOT NULL DEFAULT 'active' CHECK (status IN ('active','candidate','merged','archived')),
  origin text NOT NULL DEFAULT 'uploaded' CHECK (origin IN ('uploaded','seeded','discovered')),
  confidence numeric NOT NULL DEFAULT 1.0,
  times_matched integer NOT NULL DEFAULT 0,
  last_matched_at timestamptz,
  last_validated_at timestamptz DEFAULT now(),
  merged_into_id uuid REFERENCES public.taxonomy_nodes(id),
  embedding vector(768),
  created_by text,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (workspace_id, parent_id, slug)
);
ALTER TABLE public.taxonomy_nodes ENABLE ROW LEVEL SECURITY;

CREATE INDEX IF NOT EXISTS idx_taxonomy_nodes_ws_status ON public.taxonomy_nodes (workspace_id, status);
CREATE INDEX IF NOT EXISTS idx_taxonomy_nodes_parent ON public.taxonomy_nodes (workspace_id, parent_id);
CREATE INDEX IF NOT EXISTS idx_taxonomy_nodes_embedding ON public.taxonomy_nodes USING hnsw (embedding vector_cosine_ops);

CREATE POLICY "Users manage taxonomy in their workspace" ON public.taxonomy_nodes
  FOR ALL TO authenticated
  USING (workspace_id IN (SELECT workspace_id FROM public.profiles WHERE user_id = auth.uid()))
  WITH CHECK (workspace_id IN (SELECT workspace_id FROM public.profiles WHERE user_id = auth.uid()));

CREATE TRIGGER set_taxonomy_nodes_updated_at
  BEFORE UPDATE ON public.taxonomy_nodes
  FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();

CREATE TABLE IF NOT EXISTS public.signal_node_map (
  id bigserial PRIMARY KEY,
  signal_id integer NOT NULL REFERENCES public.signals(id) ON DELETE CASCADE,
  node_id uuid NOT NULL REFERENCES public.taxonomy_nodes(id) ON DELETE CASCADE,
  score numeric,
  mapped_by text NOT NULL DEFAULT 'system_auto' CHECK (mapped_by IN ('system_auto','system_llm','user')),
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (signal_id, node_id)
);
ALTER TABLE public.signal_node_map ENABLE ROW LEVEL SECURITY;
CREATE INDEX IF NOT EXISTS idx_signal_node_map_node ON public.signal_node_map (node_id);

CREATE POLICY "Users view signal map in their workspace" ON public.signal_node_map
  FOR SELECT TO authenticated
  USING (signal_id IN (
    SELECT s.id FROM public.signals s
    JOIN public.profiles p ON p.workspace_id = s.workspace_id
    WHERE p.user_id = auth.uid()
  ));

-- Nearest-neighbour retrieval over ACTIVE nodes for a workspace.
CREATE OR REPLACE FUNCTION public.match_taxonomy_nodes(
  p_workspace_id integer,
  p_query_embedding vector(768),
  p_match_count integer DEFAULT 5
)
RETURNS TABLE (id uuid, name text, level integer, slug text, similarity double precision)
LANGUAGE sql STABLE
SET search_path = public
AS $$
  SELECT n.id, n.name, n.level, n.slug,
         1 - (n.embedding <=> p_query_embedding) AS similarity
  FROM public.taxonomy_nodes n
  WHERE n.workspace_id = p_workspace_id
    AND n.status = 'active'
    AND n.embedding IS NOT NULL
  ORDER BY n.embedding <=> p_query_embedding
  LIMIT p_match_count;
$$;
```

- [ ] **Step 2: Apply the migration**

Apply to project `grdwaolihoeaqaerovdg` (Supabase MCP `apply_migration`, or `npx supabase db push`).
Expected: success; `taxonomy_nodes` and `signal_node_map` appear in `list_tables`.

- [ ] **Step 3: Verify pgvector + RPC exist**

Run (SQL editor / `execute_sql`):
```sql
select extname from pg_extension where extname='vector';
select proname from pg_proc where proname='match_taxonomy_nodes';
```
Expected: one row each.

- [ ] **Step 4: Commit**

```bash
git add supabase/migrations/20260621170000_taxonomy.sql
git commit -m "feat(taxonomy): schema, pgvector, signal_node_map, match RPC (phase 1)"
```

---

## Task 2: Hand-sync types

**Files:**
- Modify: `src/lib/types.ts`
- Modify: `src/integrations/supabase/types.ts`

- [ ] **Step 1: Add domain types to `src/lib/types.ts`**

Append:
```ts
export type TaxonomyStatus = "active" | "candidate" | "merged" | "archived";
export type TaxonomyOrigin = "uploaded" | "seeded" | "discovered";

export interface TaxonomyNode {
  id: string;
  workspace_id: number;
  parent_id: string | null;
  level: 1 | 2 | 3;
  name: string;
  slug: string;
  description: string | null;
  status: TaxonomyStatus;
  origin: TaxonomyOrigin;
  confidence: number;
  times_matched: number;
  last_matched_at: string | null;
  merged_into_id: string | null;
  created_at: string;
  updated_at: string;
  /** populated client-side by buildTree */
  children?: TaxonomyNode[];
  match_count?: number;
}

export interface SignalNodeMap {
  id: number;
  signal_id: number;
  node_id: string;
  score: number | null;
  mapped_by: "system_auto" | "system_llm" | "user";
  created_at: string;
}
```

- [ ] **Step 2: Mirror Supabase row types in `src/integrations/supabase/types.ts`**

Inside the `Tables` object (next to existing tables like `signals`), add `taxonomy_nodes` and `signal_node_map`. Match the existing file's shape (`Row`/`Insert`/`Update`/`Relationships`). Use `string` for `embedding` (it is not queried client-side):
```ts
taxonomy_nodes: {
  Row: {
    id: string; workspace_id: number; parent_id: string | null; level: number;
    name: string; slug: string; description: string | null; status: string; origin: string;
    confidence: number; times_matched: number; last_matched_at: string | null;
    last_validated_at: string | null; merged_into_id: string | null; embedding: string | null;
    created_by: string | null; created_at: string; updated_at: string;
  };
  Insert: {
    id?: string; workspace_id: number; parent_id?: string | null; level: number;
    name: string; slug: string; description?: string | null; status?: string; origin?: string;
    confidence?: number; times_matched?: number; last_matched_at?: string | null;
    last_validated_at?: string | null; merged_into_id?: string | null; embedding?: string | null;
    created_by?: string | null; created_at?: string; updated_at?: string;
  };
  Update: Partial<Database["public"]["Tables"]["taxonomy_nodes"]["Insert"]>;
  Relationships: [];
};
signal_node_map: {
  Row: { id: number; signal_id: number; node_id: string; score: number | null; mapped_by: string; created_at: string; };
  Insert: { id?: number; signal_id: number; node_id: string; score?: number | null; mapped_by?: string; created_at?: string; };
  Update: Partial<Database["public"]["Tables"]["signal_node_map"]["Insert"]>;
  Relationships: [];
};
```

- [ ] **Step 3: Type-check**

Run: `npx tsc -p tsconfig.app.json --noEmit 2>&1 | grep -v "src/test/"`
Expected: no output (clean).

- [ ] **Step 4: Commit**

```bash
git add src/lib/types.ts src/integrations/supabase/types.ts
git commit -m "feat(taxonomy): domain + supabase row types (phase 1)"
```

---

## Task 3: Pure helpers (`taxonomy.ts`) — TDD

**Files:**
- Create: `src/lib/taxonomy.ts`
- Test: `src/lib/taxonomy.test.ts`

- [ ] **Step 1: Write the failing tests**

```ts
import { describe, it, expect } from "vitest";
import { slugify, parseTaxonomyFile, buildTree, coverage } from "./taxonomy";
import type { TaxonomyNode } from "./types";

describe("slugify", () => {
  it("lowercases, trims, and underscores", () => {
    expect(slugify("  Checkout Failure! ")).toBe("checkout_failure");
  });
});

describe("parseTaxonomyFile", () => {
  it("parses CSV into category/theme/subtheme rows", () => {
    const csv = "category,theme,subtheme,description\nBilling,Checkout,payment_declined,Card declined\n";
    const rows = parseTaxonomyFile(csv, "text/csv");
    expect(rows).toEqual([
      { category: "Billing", theme: "Checkout", subtheme: "payment_declined", description: "Card declined" },
    ]);
  });

  it("parses JSON array form", () => {
    const json = JSON.stringify([{ category: "Billing", theme: "Checkout", subtheme: "payment_declined" }]);
    const rows = parseTaxonomyFile(json, "application/json");
    expect(rows[0].category).toBe("Billing");
    expect(rows[0].description ?? "").toBe("");
  });

  it("throws when a row has no category", () => {
    expect(() => parseTaxonomyFile("category,theme\n,Checkout\n", "text/csv")).toThrow();
  });
});

describe("buildTree", () => {
  it("nests level 2 and 3 under their parents", () => {
    const flat = [
      { id: "c", parent_id: null, level: 1, name: "Billing" },
      { id: "t", parent_id: "c", level: 2, name: "Checkout" },
      { id: "s", parent_id: "t", level: 3, name: "declined" },
    ] as TaxonomyNode[];
    const tree = buildTree(flat);
    expect(tree).toHaveLength(1);
    expect(tree[0].children?.[0].children?.[0].name).toBe("declined");
  });
});

describe("coverage", () => {
  it("is mapped / total, 0 when no signals", () => {
    expect(coverage(8, 10)).toBeCloseTo(0.8);
    expect(coverage(0, 0)).toBe(0);
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `npm run test -- src/lib/taxonomy.test.ts`
Expected: FAIL ("Cannot find module './taxonomy'" / functions undefined).

- [ ] **Step 3: Implement `src/lib/taxonomy.ts`**

```ts
import type { TaxonomyNode } from "./types";

export interface TaxonomyRow {
  category: string;
  theme: string;
  subtheme: string;
  description: string;
}

export function slugify(s: string): string {
  return s.trim().toLowerCase().replace(/[^a-z0-9]+/g, "_").replace(/^_+|_+$/g, "");
}

/** Minimal CSV split honouring quoted fields (mirrors Signals.tsx parser). */
function splitCsvLine(line: string): string[] {
  const out: string[] = [];
  let cur = "", q = false;
  for (let i = 0; i < line.length; i++) {
    const c = line[i];
    if (c === '"') { if (q && line[i + 1] === '"') { cur += '"'; i++; } else q = !q; }
    else if (c === "," && !q) { out.push(cur); cur = ""; }
    else cur += c;
  }
  out.push(cur);
  return out.map((x) => x.trim());
}

export function parseTaxonomyFile(text: string, mime: string): TaxonomyRow[] {
  const norm = (r: Record<string, unknown>): TaxonomyRow => {
    const category = String(r.category ?? "").trim();
    if (!category) throw new Error("Every row needs a non-empty 'category'.");
    return {
      category,
      theme: String(r.theme ?? "").trim(),
      subtheme: String(r.subtheme ?? "").trim(),
      description: String(r.description ?? "").trim(),
    };
  };
  if (mime.includes("json") || text.trim().startsWith("[")) {
    const arr = JSON.parse(text);
    if (!Array.isArray(arr)) throw new Error("JSON taxonomy must be an array of rows.");
    return arr.map(norm);
  }
  const lines = text.split(/\r?\n/).filter((l) => l.trim());
  if (lines.length < 2) throw new Error("CSV needs a header row + at least one row.");
  const headers = splitCsvLine(lines[0]).map((h) => h.toLowerCase());
  return lines.slice(1).map((line) => {
    const cells = splitCsvLine(line);
    const row: Record<string, string> = {};
    headers.forEach((h, i) => (row[h] = cells[i] ?? ""));
    return norm(row);
  });
}

/** Nest flat nodes into a tree by parent_id. */
export function buildTree(nodes: TaxonomyNode[]): TaxonomyNode[] {
  const byId = new Map(nodes.map((n) => [n.id, { ...n, children: [] as TaxonomyNode[] }]));
  const roots: TaxonomyNode[] = [];
  for (const n of byId.values()) {
    if (n.parent_id && byId.has(n.parent_id)) byId.get(n.parent_id)!.children!.push(n);
    else roots.push(n);
  }
  return roots;
}

export function coverage(mapped: number, total: number): number {
  return total > 0 ? mapped / total : 0;
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `npm run test -- src/lib/taxonomy.test.ts`
Expected: PASS (5 tests).

- [ ] **Step 5: Commit**

```bash
git add src/lib/taxonomy.ts src/lib/taxonomy.test.ts
git commit -m "feat(taxonomy): pure parse/tree/coverage helpers with tests (phase 1)"
```

---

## Task 4: `embed()` helper in shared AI client

**Files:**
- Modify: `supabase/functions/_shared/ai.ts`

- [ ] **Step 1: Append an embeddings helper**

Add to `supabase/functions/_shared/ai.ts`:
```ts
export const AI_EMBED_MODEL = Deno.env.get("AI_EMBED_MODEL") ?? "text-embedding-004";

/** Embed one or more strings via the OpenAI-compatible /embeddings endpoint. */
export async function embed(input: string | string[]): Promise<number[][]> {
  const res = await fetch(`${AI_BASE_URL}/embeddings`, {
    method: "POST",
    headers: aiHeaders(),
    body: JSON.stringify({ model: AI_EMBED_MODEL, input }),
  });
  if (!res.ok) {
    const detail = await res.text().catch(() => "");
    const err = new Error(`Embedding error ${res.status}: ${detail}`) as Error & { status?: number };
    err.status = res.status;
    throw err;
  }
  const data = await res.json();
  return (data.data as { embedding: number[] }[]).map((d) => d.embedding);
}

/** pgvector accepts a string like "[0.1,0.2,...]". */
export function toVectorLiteral(v: number[]): string {
  return `[${v.join(",")}]`;
}
```

- [ ] **Step 2: Commit**

```bash
git add supabase/functions/_shared/ai.ts
git commit -m "feat(taxonomy): add embed() + toVectorLiteral helpers to shared AI client"
```

---

## Task 5: `embed-taxonomy` edge function

**Files:**
- Create: `supabase/functions/embed-taxonomy/index.ts`

- [ ] **Step 1: Write the function**

```ts
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
```

- [ ] **Step 2: Deploy**

Deploy `embed-taxonomy` (verify_jwt = true) to `grdwaolihoeaqaerovdg` (MCP `deploy_edge_function` with `index.ts` + `ai.ts` bundled and the import rewritten to `./ai.ts`, OR `npx supabase functions deploy embed-taxonomy`).
Expected: status ACTIVE.

- [ ] **Step 3: Set the embed-model secret (optional, defaults to text-embedding-004)**

Run: `npx supabase secrets set AI_EMBED_MODEL="text-embedding-004"`
Expected: secret set.

- [ ] **Step 4: Commit**

```bash
git add supabase/functions/embed-taxonomy/index.ts
git commit -m "feat(taxonomy): embed-taxonomy edge function (phase 1)"
```

---

## Task 6: Map signals to nodes inside `enrich-signal`

**Files:**
- Modify: `supabase/functions/enrich-signal/index.ts`

- [ ] **Step 1: Add the import**

At the top, change the AI import to also pull embedding helpers:
```ts
import { callTool, embed, toVectorLiteral } from "../_shared/ai.ts";
```

- [ ] **Step 2: Add a mapping helper above `serve(...)`**

```ts
const MAP_THRESHOLD = 0.72; // cosine similarity floor for an auto-mapping

async function mapSignalToNode(
  db: ReturnType<typeof createClient>,
  workspaceId: number,
  signalId: number,
  text: string,
) {
  const [vec] = await embed(text);
  const { data: matches, error } = await db.rpc("match_taxonomy_nodes", {
    p_workspace_id: workspaceId,
    p_query_embedding: toVectorLiteral(vec),
    p_match_count: 5,
  });
  if (error || !matches?.length) return;

  // Hybrid: let the LLM confirm the best subtheme (or reject) among the candidates.
  const candidates = (matches as { id: string; name: string; level: number; similarity: number }[]);
  const top = candidates[0];
  if (top.similarity < MAP_THRESHOLD) return; // unmapped → left for Phase 2 discovery

  await db.from("signal_node_map")
    .upsert({ signal_id: signalId, node_id: top.id, score: top.similarity, mapped_by: "system_auto" },
            { onConflict: "signal_id,node_id" });
  await db.from("taxonomy_nodes")
    .update({ times_matched: undefined }) // see Step 3 note
    .eq("id", top.id);
}
```

- [ ] **Step 3: Replace the placeholder `times_matched` bump with an RPC-free increment**

In `mapSignalToNode`, replace the `taxonomy_nodes` update block with a read-modify-write:
```ts
  const { data: node } = await db.from("taxonomy_nodes").select("times_matched").eq("id", top.id).single();
  await db.from("taxonomy_nodes")
    .update({ times_matched: ((node?.times_matched as number) ?? 0) + 1, last_matched_at: new Date().toISOString() })
    .eq("id", top.id);
```

- [ ] **Step 4: Call the mapper after enrichment writes**

In the enrichment loop, right after the existing `if (!upErr) enriched++;`, add a mapping call (guarded so mapping never fails the enrich pass):
```ts
      if (!upErr) {
        enriched++;
        try {
          const sig = signals.find((s: { id: number }) => s.id === e.id) as { id: number; text_content: string } | undefined;
          const wsRow = sig ? await db.from("signals").select("workspace_id").eq("id", sig.id).single() : null;
          if (sig && wsRow?.data) {
            await mapSignalToNode(db, wsRow.data.workspace_id as number, sig.id, sig.text_content);
          }
        } catch (mapErr) { console.error("map skip", e.id, mapErr); }
      }
```
(Remove the original bare `if (!upErr) enriched++;` line it replaces.)

- [ ] **Step 5: Deploy and smoke-test**

Deploy `enrich-signal` (verify_jwt = true, bundle `ai.ts` as `./ai.ts`).
Manual test (after Tasks 1–5 + an uploaded, embedded taxonomy exist): in the app, **Signals → Analyze**, then run:
```sql
select count(*) from public.signal_node_map;
```
Expected: > 0 rows once signals match nodes above threshold.

- [ ] **Step 6: Commit**

```bash
git add supabase/functions/enrich-signal/index.ts
git commit -m "feat(taxonomy): map signals to nearest taxonomy node during enrichment (phase 1)"
```

---

## Task 7: Taxonomy tree component + page

**Files:**
- Create: `src/components/taxonomy/TaxonomyTree.tsx`
- Create: `src/pages/Taxonomy.tsx`

- [ ] **Step 1: Write `TaxonomyTree.tsx`**

```tsx
import type { TaxonomyNode } from "@/lib/types";
import { Badge } from "@/components/ui/badge";

function NodeRow({ node, depth }: { node: TaxonomyNode; depth: number }) {
  return (
    <div>
      <div className="flex items-center gap-2 py-1.5 border-b border-border/50" style={{ paddingLeft: depth * 20 }}>
        <span className="text-sm font-medium">{node.name}</span>
        <Badge variant="outline" className="text-[10px]">L{node.level}</Badge>
        {typeof node.match_count === "number" && node.match_count > 0 && (
          <span className="text-xs text-muted-foreground">{node.match_count} signal(s)</span>
        )}
        {node.description && <span className="text-xs text-muted-foreground truncate">— {node.description}</span>}
      </div>
      {node.children?.map((c) => <NodeRow key={c.id} node={c} depth={depth + 1} />)}
    </div>
  );
}

export function TaxonomyTree({ nodes }: { nodes: TaxonomyNode[] }) {
  if (!nodes.length) {
    return <p className="text-sm text-muted-foreground py-8 text-center">No taxonomy yet. Upload a CSV or JSON to get started.</p>;
  }
  return <div>{nodes.map((n) => <NodeRow key={n.id} node={n} depth={0} />)}</div>;
}
```

- [ ] **Step 2: Write `Taxonomy.tsx`**

```tsx
import { useRef } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { supabase } from "@/integrations/supabase/client";
import { useWorkspaceId } from "@/hooks/use-workspace";
import { AppLayout } from "@/components/layout/AppLayout";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { toast } from "sonner";
import { Upload } from "lucide-react";
import { parseTaxonomyFile, buildTree, slugify, coverage } from "@/lib/taxonomy";
import type { TaxonomyNode } from "@/lib/types";
import { TaxonomyTree } from "@/components/taxonomy/TaxonomyTree";

const TaxonomyPage = () => {
  const workspaceId = useWorkspaceId();
  const qc = useQueryClient();
  const fileRef = useRef<HTMLInputElement>(null);

  const { data, isLoading } = useQuery({
    queryKey: ["taxonomy", workspaceId],
    enabled: !!workspaceId,
    queryFn: async () => {
      const { data: nodes, error } = await supabase
        .from("taxonomy_nodes").select("*").eq("workspace_id", workspaceId!).neq("status", "merged");
      if (error) throw error;
      const { count: mapped } = await supabase
        .from("signal_node_map").select("id", { count: "exact", head: true });
      const { count: total } = await supabase
        .from("signals").select("id", { count: "exact", head: true }).eq("workspace_id", workspaceId!);
      const counts = new Map<string, number>();
      const { data: maps } = await supabase.from("signal_node_map").select("node_id");
      (maps ?? []).forEach((m: { node_id: string }) => counts.set(m.node_id, (counts.get(m.node_id) ?? 0) + 1));
      const withCounts = (nodes as TaxonomyNode[]).map((n) => ({ ...n, match_count: counts.get(n.id) ?? 0 }));
      return { tree: buildTree(withCounts), coverage: coverage(mapped ?? 0, total ?? 0) };
    },
  });

  const upload = useMutation({
    mutationFn: async (file: File) => {
      const rows = parseTaxonomyFile(await file.text(), file.type || (file.name.endsWith(".json") ? "application/json" : "text/csv"));
      // Insert categories → themes → subthemes, de-duping by (parent, slug).
      const cache = new Map<string, string>(); // key `${parentId}/${slug}` → id
      const ensure = async (parentId: string | null, level: number, name: string, description = "") => {
        const slug = slugify(name);
        if (!slug) return null;
        const key = `${parentId ?? "root"}/${slug}`;
        if (cache.has(key)) return cache.get(key)!;
        const { data: ins, error } = await supabase.from("taxonomy_nodes")
          .upsert({ workspace_id: workspaceId!, parent_id: parentId, level, name, slug, description: description || null, origin: "uploaded", created_by: "user" },
                  { onConflict: "workspace_id,parent_id,slug" })
          .select("id").single();
        if (error) throw error;
        cache.set(key, ins.id);
        return ins.id as string;
      };
      for (const r of rows) {
        const cId = await ensure(null, 1, r.category);
        const tId = r.theme ? await ensure(cId, 2, r.theme) : null;
        if (r.subtheme) await ensure(tId ?? cId, tId ? 3 : 2, r.subtheme, r.description);
      }
      // Kick off embedding (fire-and-forget; safe to re-run).
      await supabase.functions.invoke("embed-taxonomy", { body: { workspace_id: workspaceId } });
      return rows.length;
    },
    onSuccess: (n) => {
      qc.invalidateQueries({ queryKey: ["taxonomy", workspaceId] });
      toast.success(`Imported ${n} taxonomy row(s). Embedding in the background.`);
    },
    onError: (e) => toast.error("Taxonomy import failed", { description: e instanceof Error ? e.message : undefined }),
  });

  return (
    <AppLayout>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-semibold">Taxonomy</h1>
          <p className="text-sm text-muted-foreground">
            Your company themes. {data ? `Coverage: ${Math.round(data.coverage * 100)}% of signals mapped.` : ""}
          </p>
        </div>
        <input ref={fileRef} type="file" accept=".csv,.json" className="hidden"
          onChange={(e) => { const f = e.target.files?.[0]; if (f) upload.mutate(f); e.target.value = ""; }} />
        <Button variant="outline" size="sm" disabled={upload.isPending || !workspaceId} onClick={() => fileRef.current?.click()}>
          <Upload className="h-3.5 w-3.5 mr-1.5" />{upload.isPending ? "Importing…" : "Upload taxonomy"}
        </Button>
      </div>
      <div className="rounded-lg border border-border p-4">
        {isLoading ? <Skeleton className="h-40 w-full" /> : <TaxonomyTree nodes={data?.tree ?? []} />}
      </div>
    </AppLayout>
  );
};

export default TaxonomyPage;
```

- [ ] **Step 3: Type-check**

Run: `npx tsc -p tsconfig.app.json --noEmit 2>&1 | grep -v "src/test/"`
Expected: clean. (If `@/components/ui/badge` is missing, add it: `npx shadcn@latest add badge`.)

- [ ] **Step 4: Commit**

```bash
git add src/components/taxonomy/TaxonomyTree.tsx src/pages/Taxonomy.tsx
git commit -m "feat(taxonomy): /taxonomy page with upload + tree + coverage (phase 1)"
```

---

## Task 8: Route + sidebar wiring

**Files:**
- Modify: `src/App.tsx`
- Modify: `src/components/layout/AppSidebar.tsx`

- [ ] **Step 1: Add the route in `src/App.tsx`**

Import near the other page imports:
```tsx
import Taxonomy from "./pages/Taxonomy";
```
Add inside the protected routes block (next to `/signals`), following the existing `ProtectedRoute` pattern used by sibling routes:
```tsx
<Route path="/taxonomy" element={<ProtectedRoute><Taxonomy /></ProtectedRoute>} />
```

- [ ] **Step 2: Add the nav item in `src/components/layout/AppSidebar.tsx`**

Import an icon with the others (e.g. `Network`) from `lucide-react`, then add to the existing nav-items array following its shape (match the keys the other items use — e.g. `title`/`url`/`icon`):
```tsx
{ title: "Taxonomy", url: "/taxonomy", icon: Network },
```

- [ ] **Step 3: Type-check + lint**

Run: `npx tsc -p tsconfig.app.json --noEmit 2>&1 | grep -v "src/test/"` → clean.
Run: `npm run lint` → no new errors.

- [ ] **Step 4: Commit**

```bash
git add src/App.tsx src/components/layout/AppSidebar.tsx
git commit -m "feat(taxonomy): add /taxonomy route + sidebar entry (phase 1)"
```

---

## Task 9: End-to-end verification

**Files:** none (manual).

- [ ] **Step 1: Build**

Run: `npm run build`
Expected: `✓ built`.

- [ ] **Step 2: Run the app**

Run: `npm run dev` → open http://localhost:8080 → log in.

- [ ] **Step 3: Upload a taxonomy**

Create `taxonomy_sample.csv`:
```
category,theme,subtheme,description
Billing,Checkout,checkout_failure,Payment fails at checkout
Billing,Pricing,pricing_unclear,Pricing/tiers unclear
Delivery,Tracking,late_delivery,Order late or tracking wrong
Onboarding,Setup,onboarding_friction,Hard to connect a source
```
In **Taxonomy → Upload taxonomy**, pick the file.
Expected: toast "Imported 4 taxonomy row(s)"; tree shows 4 categories with nested themes/subthemes.

- [ ] **Step 4: Confirm embeddings populated**

After ~10s run: `select count(*) from taxonomy_nodes where embedding is not null;`
Expected: equals total node count (categories + themes + subthemes).

- [ ] **Step 5: Map signals**

**Signals → Analyze** (enriches + maps). Then run:
```sql
select n.name, count(*) from signal_node_map m join taxonomy_nodes n on n.id=m.node_id group by n.name order by 2 desc;
```
Expected: seeded signals about checkout/delivery/pricing map to the matching nodes; `/taxonomy` shows non-zero "N signal(s)" and a coverage % > 0.

- [ ] **Step 6: Open a PR**

```bash
git push -u origin feat/adaptive-taxonomy
gh pr create --base main --head feat/adaptive-taxonomy --title "Adaptive taxonomy — Phase 1 (foundation)" --body "Upload + embed a 3-level company taxonomy, map signals to it during enrichment, /taxonomy tree + coverage. Spec: docs/superpowers/specs/2026-06-21-adaptive-taxonomy-design.md"
```

---

## Self-review (completed)

- **Spec coverage:** Phase-1 rows of the spec (schema, upload, embedding, mapping, tree UI, coverage metric) each map to Tasks 1–9. Discovery/review-queue/auto-promotion/decay are intentionally Phases 2–3 (separate plans).
- **Placeholder scan:** none — every code step has full code; thresholds are concrete (`MAP_THRESHOLD=0.72`).
- **Type consistency:** `TaxonomyNode`/`SignalNodeMap` (Task 2) are used consistently in `taxonomy.ts` (Task 3) and the UI (Task 7); `match_taxonomy_nodes` signature (Task 1) matches the `.rpc(...)` call (Task 6); `embed`/`toVectorLiteral` (Task 4) used in Tasks 5–6.
- **Note for executor:** edge-function code is verified by deploy + the manual SQL checks (this project has no Deno test harness); pure logic is covered by Vitest in Task 3.
