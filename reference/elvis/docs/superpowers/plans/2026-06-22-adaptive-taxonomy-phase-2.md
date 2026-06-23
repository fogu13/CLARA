# Adaptive Taxonomy — Phase 2 (Discovery + Review Queue) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Automatically discover candidate themes by clustering unmapped signals, propose them as `candidate` taxonomy nodes with evidence, and give a human a review queue to **Approve / Edit / Reject / Merge** — every change audited. This is the governed (human-in-the-loop) half of the adaptive taxonomy.

**Architecture:** A new `evolve-taxonomy` edge function embeds the workspace's unmapped signals, greedily clusters them by cosine similarity, names each cluster with the LLM, places it under the nearest existing active node (by embedding), and inserts it as `status='candidate'` with evidence. The `/taxonomy` page gains a **review queue** that promotes/edits/rejects/merges candidates, writing audit rows to `events`. A `merge_taxonomy_node` SQL RPC remaps `signal_node_map` safely.

**Tech Stack:** Supabase (Postgres + pgvector + Deno), React 18 + Vite + TS, React Query, shadcn/ui, Vitest. Builds on Phase 1 (`taxonomy_nodes`, `signal_node_map`, `match_taxonomy_nodes`, `unmapped_signals`, `embed()`/`toVectorLiteral` in `_shared/ai.ts`).

**Depends on:** Phase 1 merged (PR #4) and the embeddings fix (PR #5: `gemini-embedding-001` @ 768 dims, `MAP_THRESHOLD`).

**Conventions (CLAUDE.md):** hand-sync types in `src/integrations/supabase/types.ts` + `src/lib/types.ts`; `vite build` doesn't type-check (use `npx tsc -p tsconfig.app.json --noEmit`, exclude `src/test/*`); deploy migrations/functions to `grdwaolihoeaqaerovdg`; edge functions import `../_shared/ai.ts` in the repo (the deploy bundles `ai.ts` as `./ai.ts`).

---

## File Structure

| File | Responsibility |
|---|---|
| `supabase/migrations/20260622120000_taxonomy_discovery.sql` | `taxonomy_nodes.evidence jsonb`; `merge_taxonomy_node` RPC |
| `src/lib/types.ts` (modify) | add `evidence` to `TaxonomyNode` |
| `src/integrations/supabase/types.ts` (modify) | add `evidence` to the `taxonomy_nodes` row types |
| `src/lib/taxonomy.ts` (modify) | pure `cosineSim` + `clusterByThreshold` + `candidateEvidence` helpers |
| `src/lib/taxonomy.test.ts` (modify) | tests for the new pure helpers |
| `supabase/functions/evolve-taxonomy/index.ts` (create) | discover candidate nodes from unmapped signals |
| `src/components/taxonomy/ReviewQueue.tsx` (create) | candidate review queue (approve/edit/reject/merge) |
| `src/pages/Taxonomy.tsx` (modify) | "Discover themes" button + render `<ReviewQueue>` |

---

## Task 1: Migration — evidence column + merge RPC

**Files:**
- Create: `supabase/migrations/20260622120000_taxonomy_discovery.sql`

- [ ] **Step 1: Write the migration**

```sql
-- Adaptive taxonomy — Phase 2 (discovery + review). Candidate nodes carry evidence; merging
-- a node remaps its signal mappings onto the target and marks it merged.

ALTER TABLE public.taxonomy_nodes
  ADD COLUMN IF NOT EXISTS evidence jsonb NOT NULL DEFAULT '{}'::jsonb;

COMMENT ON COLUMN public.taxonomy_nodes.evidence IS
  'For discovered candidates: { signal_ids:int[], samples:text[], size:int, cohesion:numeric }.';

-- Merge p_from into p_into: move mappings (dedupe against existing), then mark merged.
CREATE OR REPLACE FUNCTION public.merge_taxonomy_node(p_from uuid, p_into uuid)
RETURNS void
LANGUAGE plpgsql
SET search_path = public
AS $$
BEGIN
  IF p_from = p_into THEN RETURN; END IF;

  UPDATE public.signal_node_map m
    SET node_id = p_into
  WHERE m.node_id = p_from
    AND NOT EXISTS (
      SELECT 1 FROM public.signal_node_map x
      WHERE x.signal_id = m.signal_id AND x.node_id = p_into
    );

  DELETE FROM public.signal_node_map WHERE node_id = p_from; -- leftover duplicates

  UPDATE public.taxonomy_nodes
    SET status = 'merged', merged_into_id = p_into, updated_at = now()
  WHERE id = p_from;
END;
$$;
```

- [ ] **Step 2: Apply** (Supabase MCP `apply_migration` or `supabase db push`) to `grdwaolihoeaqaerovdg`.

Verify:
```sql
select column_name from information_schema.columns where table_name='taxonomy_nodes' and column_name='evidence';
select proname from pg_proc where proname='merge_taxonomy_node';
```
Expected: one row each.

- [ ] **Step 3: Commit**

```bash
git add supabase/migrations/20260622120000_taxonomy_discovery.sql
git commit -m "feat(taxonomy): evidence column + merge_taxonomy_node RPC (phase 2)"
```

---

## Task 2: Hand-sync the `evidence` field

**Files:**
- Modify: `src/lib/types.ts`
- Modify: `src/integrations/supabase/types.ts`

- [ ] **Step 1: Add `evidence` to `TaxonomyNode` in `src/lib/types.ts`**

In the `TaxonomyNode` interface (after `merged_into_id`), add:
```ts
  evidence?: {
    signal_ids?: number[];
    samples?: string[];
    size?: number;
    cohesion?: number;
  };
```

- [ ] **Step 2: Add `evidence` to the supabase row types**

In `src/integrations/supabase/types.ts`, in `taxonomy_nodes` `Row` add `evidence: Json;`, and in `Insert`/`Update` add `evidence?: Json;` (match the `Json` type the file already uses for jsonb columns elsewhere, e.g. `signals.metadata`).

- [ ] **Step 3: Type-check**

Run: `npx tsc -p tsconfig.app.json --noEmit 2>&1 | grep -v "src/test/"` → clean.

- [ ] **Step 4: Commit**

```bash
git add src/lib/types.ts src/integrations/supabase/types.ts
git commit -m "feat(taxonomy): evidence field on TaxonomyNode types (phase 2)"
```

---

## Task 3: Pure clustering helpers (TDD)

**Files:**
- Modify: `src/lib/taxonomy.ts`
- Modify: `src/lib/taxonomy.test.ts`

> These are the canonical, unit-tested versions of the clustering math. The `evolve-taxonomy`
> Deno function (Task 4) contains an inline copy of `cosineSim` + `clusterByThreshold` (Deno can't
> import `src/`). **Keep the two copies in sync** — the algorithm is identical.

- [ ] **Step 1: Add failing tests to `src/lib/taxonomy.test.ts`**

Append:
```ts
import { cosineSim, clusterByThreshold, candidateEvidence } from "./taxonomy";

describe("cosineSim", () => {
  it("is 1 for identical, 0 for orthogonal", () => {
    expect(cosineSim([1, 0], [1, 0])).toBeCloseTo(1);
    expect(cosineSim([1, 0], [0, 1])).toBeCloseTo(0);
  });
});

describe("clusterByThreshold", () => {
  it("groups vectors above the threshold, drops singletons below minSize", () => {
    const vecs = [[1, 0], [0.99, 0.01], [0, 1]]; // first two are near-identical, third alone
    const clusters = clusterByThreshold(vecs, 0.9, 2);
    expect(clusters).toEqual([[0, 1]]); // indices of the one cluster of size >= 2
  });
});

describe("candidateEvidence", () => {
  it("summarises ids + first samples + size", () => {
    const ev = candidateEvidence([3, 4, 5], ["a", "b", "c", "d", "e", "f"], 0.81);
    expect(ev.size).toBe(3);
    expect(ev.signal_ids).toEqual([3, 4, 5]);
    expect(ev.samples.length).toBeLessThanOrEqual(5);
    expect(ev.cohesion).toBeCloseTo(0.81);
  });
});
```

- [ ] **Step 2: Run, confirm FAIL**

Run: `npm run test -- src/lib/taxonomy.test.ts`
Expected: FAIL (functions undefined).

- [ ] **Step 3: Implement in `src/lib/taxonomy.ts`**

Append:
```ts
export function cosineSim(a: number[], b: number[]): number {
  let dot = 0, na = 0, nb = 0;
  for (let i = 0; i < a.length; i++) { dot += a[i] * b[i]; na += a[i] * a[i]; nb += b[i] * b[i]; }
  const denom = Math.sqrt(na) * Math.sqrt(nb);
  return denom === 0 ? 0 : dot / denom;
}

/** Greedy single-pass clustering: each unused vector seeds a cluster of all unused vectors
 *  within `threshold` cosine. Returns clusters (as index arrays) with at least `minSize`. */
export function clusterByThreshold(vectors: number[][], threshold: number, minSize: number): number[][] {
  const used = new Array(vectors.length).fill(false);
  const clusters: number[][] = [];
  for (let i = 0; i < vectors.length; i++) {
    if (used[i]) continue;
    const group = [i];
    used[i] = true;
    for (let j = i + 1; j < vectors.length; j++) {
      if (!used[j] && cosineSim(vectors[i], vectors[j]) >= threshold) { group.push(j); used[j] = true; }
    }
    if (group.length >= minSize) clusters.push(group);
  }
  return clusters;
}

export interface CandidateEvidence {
  signal_ids: number[];
  samples: string[];
  size: number;
  cohesion: number;
}

export function candidateEvidence(signalIds: number[], texts: string[], cohesion: number): CandidateEvidence {
  return { signal_ids: signalIds, samples: texts.slice(0, 5), size: signalIds.length, cohesion };
}
```

- [ ] **Step 4: Run, confirm PASS**

Run: `npm run test -- src/lib/taxonomy.test.ts`
Expected: PASS (9 tests total).

- [ ] **Step 5: Commit**

```bash
git add src/lib/taxonomy.ts src/lib/taxonomy.test.ts
git commit -m "feat(taxonomy): cosineSim + clusterByThreshold + candidateEvidence helpers with tests (phase 2)"
```

---

## Task 4: `evolve-taxonomy` edge function

**Files:**
- Create: `supabase/functions/evolve-taxonomy/index.ts`

- [ ] **Step 1: Write the function**

```ts
import { serve } from "https://deno.land/std@0.168.0/http/server.ts";
import { createClient } from "https://esm.sh/@supabase/supabase-js@2.49.1";
import { callTool, embed, toVectorLiteral } from "../_shared/ai.ts";

const corsHeaders = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type",
};

const CLUSTER_EPS = Number(Deno.env.get("CLUSTER_EPS") ?? "0.78"); // cosine to group signals
const MIN_CLUSTER = Number(Deno.env.get("MIN_CLUSTER") ?? "3");    // min signals to propose a theme

// Inline copies of the canonical helpers in src/lib/taxonomy.ts — keep in sync.
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

      // Place under the nearest existing ACTIVE node (by embedding); fall back to top-level.
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
      } catch (e) { console.error("name skip", e); continue; }

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
      if (!insErr) candidates++;
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
```

- [ ] **Step 2: Deploy** `evolve-taxonomy` (verify_jwt = true) to `grdwaolihoeaqaerovdg` (bundle `ai.ts` as `./ai.ts`, or `supabase functions deploy evolve-taxonomy`). Expected: ACTIVE.

- [ ] **Step 3: Smoke test** (needs ≥ MIN_CLUSTER unmapped signals on a theme not already in the taxonomy). Insert a few synthetic unmapped signals via SQL, invoke the function, then:
```sql
select name, level, status, confidence, evidence->>'size' as size from taxonomy_nodes where status='candidate';
```
Expected: ≥1 candidate row with evidence. (Delete the synthetic signals after.)

- [ ] **Step 4: Commit**

```bash
git add supabase/functions/evolve-taxonomy/index.ts
git commit -m "feat(taxonomy): evolve-taxonomy discovery function (cluster -> name -> candidate) (phase 2)"
```

---

## Task 5: Review queue UI + Discover button

**Files:**
- Create: `src/components/taxonomy/ReviewQueue.tsx`
- Modify: `src/pages/Taxonomy.tsx`

- [ ] **Step 1: Write `src/components/taxonomy/ReviewQueue.tsx`**

```tsx
import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { supabase } from "@/integrations/supabase/client";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { toast } from "sonner";
import { Check, X, GitMerge } from "lucide-react";
import { logEvent } from "@/lib/events";
import type { TaxonomyNode } from "@/lib/types";

interface Props { workspaceId: number; candidates: TaxonomyNode[]; activeNodes: TaxonomyNode[]; }

export function ReviewQueue({ workspaceId, candidates, activeNodes }: Props) {
  const qc = useQueryClient();
  const [edit, setEdit] = useState<Record<string, string>>({});
  const [mergeTarget, setMergeTarget] = useState<Record<string, string>>({});
  const refresh = () => qc.invalidateQueries({ queryKey: ["taxonomy", workspaceId] });

  const act = useMutation({
    mutationFn: async (p: { node: TaxonomyNode; action: "approve" | "reject" | "merge" }) => {
      const { node, action } = p;
      if (action === "approve") {
        const name = edit[node.id] ?? node.name;
        const { error } = await supabase.from("taxonomy_nodes")
          .update({ status: "active", origin: "uploaded", name }).eq("id", node.id);
        if (error) throw error;
        await logEvent(workspaceId, "taxonomy_node_promoted", { entity: "taxonomy_node", entity_id: node.id, metadata: { name } });
      } else if (action === "reject") {
        const { error } = await supabase.from("taxonomy_nodes").update({ status: "archived" }).eq("id", node.id);
        if (error) throw error;
        await logEvent(workspaceId, "taxonomy_node_rejected", { entity: "taxonomy_node", entity_id: node.id });
      } else {
        const into = mergeTarget[node.id];
        if (!into) throw new Error("Pick a node to merge into.");
        const { error } = await supabase.rpc("merge_taxonomy_node", { p_from: node.id, p_into: into });
        if (error) throw error;
        await logEvent(workspaceId, "taxonomy_node_merged", { entity: "taxonomy_node", entity_id: node.id, metadata: { into } });
      }
    },
    onSuccess: () => { refresh(); toast.success("Taxonomy updated"); },
    onError: (e) => toast.error("Action failed", { description: e instanceof Error ? e.message : undefined }),
  });

  if (!candidates.length) return null;

  return (
    <div className="rounded-lg border border-border p-4 mb-6">
      <div className="flex items-center gap-2 mb-3">
        <h2 className="text-sm font-semibold">Review queue</h2>
        <Badge variant="outline" className="text-[10px]">{candidates.length} candidate(s)</Badge>
      </div>
      <div className="space-y-4">
        {candidates.map((c) => (
          <div key={c.id} className="border-b border-border/50 pb-3">
            <div className="flex items-center gap-2 mb-1">
              <Input className="h-7 w-56 text-sm" defaultValue={c.name} onChange={(e) => setEdit((s) => ({ ...s, [c.id]: e.target.value }))} />
              <span className="text-xs text-muted-foreground">conf {Math.round((c.confidence ?? 0) * 100)}% · {c.evidence?.size ?? 0} signals</span>
            </div>
            {c.evidence?.samples?.length ? (
              <ul className="text-xs text-muted-foreground list-disc ml-5 mb-2">
                {c.evidence.samples.slice(0, 3).map((s, i) => <li key={i} className="truncate">{s}</li>)}
              </ul>
            ) : null}
            <div className="flex items-center gap-2">
              <Button size="sm" variant="outline" disabled={act.isPending} onClick={() => act.mutate({ node: c, action: "approve" })}>
                <Check className="h-3.5 w-3.5 mr-1" />Approve
              </Button>
              <Button size="sm" variant="outline" disabled={act.isPending} onClick={() => act.mutate({ node: c, action: "reject" })}>
                <X className="h-3.5 w-3.5 mr-1" />Reject
              </Button>
              <select className="h-8 rounded-md border border-input bg-background px-2 text-xs"
                value={mergeTarget[c.id] ?? ""} onChange={(e) => setMergeTarget((s) => ({ ...s, [c.id]: e.target.value }))}>
                <option value="">merge into…</option>
                {activeNodes.map((n) => <option key={n.id} value={n.id}>{n.name}</option>)}
              </select>
              <Button size="sm" variant="outline" disabled={act.isPending || !mergeTarget[c.id]} onClick={() => act.mutate({ node: c, action: "merge" })}>
                <GitMerge className="h-3.5 w-3.5 mr-1" />Merge
              </Button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Add the audit event types to `src/lib/events.ts`**

In the `AppEventType` union, add `"taxonomy_node_promoted" | "taxonomy_node_rejected" | "taxonomy_node_merged"`.

- [ ] **Step 3: Wire into `src/pages/Taxonomy.tsx`**

3a. Imports:
```tsx
import { Sparkles } from "lucide-react";
import { ReviewQueue } from "@/components/taxonomy/ReviewQueue";
```
3b. Change the taxonomy query to also return the raw nodes (so we can split candidates/active). In the query's return, add the flat list:
```tsx
      return { tree: buildTree(withCounts.filter((n) => n.status !== "candidate")), coverage: coverage(mapped ?? 0, total ?? 0), nodes: withCounts };
```
3c. Add a discover mutation (next to `backfill`):
```tsx
  const discover = useMutation({
    mutationFn: async () => {
      const res = await supabase.functions.invoke("evolve-taxonomy", { body: { workspace_id: workspaceId, limit: 200 } });
      if (res.error) throw res.error;
      if (res.data?.error) throw new Error(res.data.error);
      return res.data as { candidates: number };
    },
    onSuccess: (d) => { qc.invalidateQueries({ queryKey: ["taxonomy", workspaceId] }); toast.success(`Discovered ${d.candidates} candidate theme(s).`); },
    onError: (e) => toast.error("Discovery failed", { description: e instanceof Error ? e.message : undefined }),
  });
```
3d. Add a "Discover themes" button inside the button group (before "Map signals"):
```tsx
          <Button variant="outline" size="sm" disabled={discover.isPending || !workspaceId} onClick={() => discover.mutate()}>
            <Sparkles className="h-3.5 w-3.5 mr-1.5" />{discover.isPending ? "Discovering…" : "Discover themes"}
          </Button>
```
3e. Render the review queue above the tree (inside `<AppLayout>`, before the tree's bordered div):
```tsx
      {data && (
        <ReviewQueue
          workspaceId={workspaceId!}
          candidates={(data.nodes as TaxonomyNode[]).filter((n) => n.status === "candidate")}
          activeNodes={(data.nodes as TaxonomyNode[]).filter((n) => n.status === "active")}
        />
      )}
```

- [ ] **Step 4: Type-check + build**

Run: `npx tsc -p tsconfig.app.json --noEmit 2>&1 | grep -v "src/test/"` → clean.
Run: `npm run build` → `✓ built`. (If `select`/`Input`/`Badge` aren't imported where used, add them.)

- [ ] **Step 5: Commit**

```bash
git add src/components/taxonomy/ReviewQueue.tsx src/pages/Taxonomy.tsx src/lib/events.ts
git commit -m "feat(taxonomy): discovery review queue (approve/edit/reject/merge) + Discover button (phase 2)"
```

---

## Task 6: End-to-end verification

- [ ] **Step 1:** `npm run build` → `✓ built`.
- [ ] **Step 2:** Import a batch of signals on a theme NOT already in the taxonomy (e.g. several "the mobile app keeps crashing" messages). Do not map them.
- [ ] **Step 3:** On `/taxonomy`, click **Discover themes**. Expect a toast "Discovered N candidate theme(s)" and the **Review queue** to list a candidate (e.g. `app_crash`) with sample evidence + confidence.
- [ ] **Step 4:** **Approve** it → it moves into the tree as active; **or Merge** it into an existing node → mappings remap (verify `select status,merged_into_id from taxonomy_nodes where id=…`).
- [ ] **Step 5:** Confirm audit rows: `select event_type,count(*) from events where event_type like 'taxonomy_node_%' group by 1;`
- [ ] **Step 6:** Open a PR:
```bash
git push -u origin feat/taxonomy-phase-2
gh pr create --base main --head feat/taxonomy-phase-2 --title "Adaptive taxonomy — Phase 2 (discovery + review queue)" --body "evolve-taxonomy clusters unmapped signals into candidate themes; /taxonomy review queue to approve/edit/reject/merge, audited to events. Spec: docs/superpowers/specs/2026-06-21-adaptive-taxonomy-design.md"
```

---

## Self-review (completed)

- **Spec coverage:** Phase-2 spec items — candidate discovery (`evolve-taxonomy`, Task 4), human review queue with approve/edit/reject/merge (Task 5), audit via `events` (Task 5 step 2 + `logEvent` calls), evidence on candidates (Tasks 1–2, 4) — all mapped. Graduated *auto*-promotion + decay are intentionally Phase 3.
- **Placeholder scan:** none — full code in every step; thresholds concrete + env-tunable (`CLUSTER_EPS=0.78`, `MIN_CLUSTER=3`).
- **Type consistency:** `TaxonomyNode.evidence` (Task 2) is read in `ReviewQueue` (Task 5) and written by `evolve-taxonomy` (Task 4); `merge_taxonomy_node(p_from,p_into)` (Task 1) matches the `.rpc(...)` call (Task 5); `unmapped_signals`/`match_taxonomy_nodes`/`embed`/`toVectorLiteral` reused from Phase 1.
- **Note for executor:** clustering math is unit-tested in `src/lib/taxonomy.ts` (Task 3); the Deno copy in `evolve-taxonomy` is identical — keep in sync. Edge function + RPC are verified by deploy + the SQL checks (no Deno test harness).
- **Threshold caveat:** `CLUSTER_EPS=0.78` and `MIN_CLUSTER=3` are starting points; tune from the discovery sample once run on real data (same approach that set `MAP_THRESHOLD=0.55` in Phase 1).
```
