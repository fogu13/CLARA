# Adaptive Taxonomy — Phase 3 (Graduated Authority) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Close the adaptive loop with *graduated authority*: automatically **promote** high-confidence, well-evidenced candidate themes; conservatively **auto-merge** near-identical discovered nodes; and **decay/archive** stale auto-discovered nodes — all on a daily schedule, all audited and reversible. Uploaded company taxonomy is never auto-archived or auto-merged away.

**Architecture:** One in-database SQL routine `apply_taxonomy_governance(workspace, …thresholds)` does promote + merge + decay (no LLM needed — it reuses stored `confidence`, `evidence.size`, and pgvector embeddings). It writes audit rows to `events` and tags auto-actions with `taxonomy_nodes.auto_promoted`. `pg_cron` runs it daily; a "Run governance" button runs it on demand for demos. The UI badges auto-promoted nodes and offers **Undo** (revert to `candidate` → back into the Phase-2 review queue).

**Tech Stack:** Supabase Postgres (pg_cron + pgvector), React 18 + Vite + TS, React Query, shadcn/ui. Builds on Phase 2 (`taxonomy_nodes.evidence`, `merge_taxonomy_node`, candidate review queue) and Phase 1.

**Conventions (CLAUDE.md):** hand-sync types; deploy migrations to `grdwaolihoeaqaerovdg`; `npx tsc -p tsconfig.app.json --noEmit` (exclude `src/test/*`).

**Thresholds (defaults, env/arg-tunable):** auto-promote `confidence ≥ 0.80` AND `evidence.size ≥ 5`; auto-merge cosine `≥ 0.95`; decay/archive discovered nodes unmatched `> 90 days`.

---

## File Structure

| File | Responsibility |
|---|---|
| `supabase/migrations/20260622140000_taxonomy_governance.sql` | `auto_promoted` column; `apply_taxonomy_governance` routine; pg_cron daily job |
| `src/lib/types.ts` (modify) | `auto_promoted` on `TaxonomyNode` |
| `src/integrations/supabase/types.ts` (modify) | `auto_promoted` row field + `apply_taxonomy_governance` Functions type |
| `src/lib/events.ts` (modify) | add `taxonomy_node_auto_promoted` / `_auto_merged` / `_decayed` to `AppEventType` |
| `src/components/taxonomy/TaxonomyTree.tsx` (modify) | "auto" badge + optional Undo button |
| `src/pages/Taxonomy.tsx` (modify) | "Run governance" button + Undo mutation wiring |

---

## Task 1: Migration — governance routine + cron

**Files:** Create `supabase/migrations/20260622140000_taxonomy_governance.sql`

- [ ] **Step 1: Write the migration**

```sql
-- Adaptive taxonomy — Phase 3 (graduated authority). Auto-promote / auto-merge / decay,
-- audited to events, reversible. Never auto-archives or auto-merges uploaded taxonomy.

ALTER TABLE public.taxonomy_nodes
  ADD COLUMN IF NOT EXISTS auto_promoted boolean NOT NULL DEFAULT false;

CREATE OR REPLACE FUNCTION public.apply_taxonomy_governance(
  p_workspace_id integer,
  p_auto_promote numeric DEFAULT 0.80,
  p_min_size integer DEFAULT 5,
  p_merge_eps numeric DEFAULT 0.95,
  p_stale_days integer DEFAULT 90
)
RETURNS jsonb
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
  promoted int := 0; archived int := 0; merged int := 0;
  rec record; target uuid;
BEGIN
  -- An authenticated caller may only govern their own workspace; pg_cron (no auth.uid()) is allowed.
  IF auth.uid() IS NOT NULL AND NOT EXISTS (
    SELECT 1 FROM public.profiles WHERE user_id = auth.uid() AND workspace_id = p_workspace_id
  ) THEN
    RAISE EXCEPTION 'not authorized for workspace %', p_workspace_id;
  END IF;

  -- 1) Auto-promote high-confidence, well-evidenced candidates.
  WITH promo AS (
    UPDATE public.taxonomy_nodes
      SET status = 'active', auto_promoted = true, last_validated_at = now(), updated_at = now()
    WHERE workspace_id = p_workspace_id AND status = 'candidate'
      AND confidence >= p_auto_promote
      AND COALESCE((evidence->>'size')::int, 0) >= p_min_size
    RETURNING id
  ) SELECT count(*) INTO promoted FROM promo;
  IF promoted > 0 THEN
    INSERT INTO public.events (workspace_id, event_type, entity, metadata)
    VALUES (p_workspace_id, 'taxonomy_node_auto_promoted', 'taxonomy_node', jsonb_build_object('count', promoted));
  END IF;

  -- 2) Conservatively auto-merge near-identical DISCOVERED active nodes into a >= confident neighbour.
  FOR rec IN
    SELECT id, embedding, confidence FROM public.taxonomy_nodes
    WHERE workspace_id = p_workspace_id AND status = 'active' AND origin = 'discovered' AND embedding IS NOT NULL
  LOOP
    SELECT id INTO target FROM public.taxonomy_nodes
    WHERE workspace_id = p_workspace_id AND status = 'active' AND id <> rec.id AND embedding IS NOT NULL
      AND (1 - (embedding <=> rec.embedding)) >= p_merge_eps
      AND confidence >= rec.confidence
    ORDER BY embedding <=> rec.embedding
    LIMIT 1;
    IF target IS NOT NULL THEN
      PERFORM public.merge_taxonomy_node(rec.id, target);
      merged := merged + 1;
      target := NULL;
    END IF;
  END LOOP;
  IF merged > 0 THEN
    INSERT INTO public.events (workspace_id, event_type, entity, metadata)
    VALUES (p_workspace_id, 'taxonomy_node_auto_merged', 'taxonomy_node', jsonb_build_object('count', merged));
  END IF;

  -- 3) Decay: archive stale auto-discovered nodes (never touches uploaded taxonomy).
  WITH arch AS (
    UPDATE public.taxonomy_nodes
      SET status = 'archived', updated_at = now()
    WHERE workspace_id = p_workspace_id AND status = 'active' AND origin = 'discovered'
      AND COALESCE(last_matched_at, created_at) < now() - make_interval(days => p_stale_days)
    RETURNING id
  ) SELECT count(*) INTO archived FROM arch;
  IF archived > 0 THEN
    INSERT INTO public.events (workspace_id, event_type, entity, metadata)
    VALUES (p_workspace_id, 'taxonomy_node_decayed', 'taxonomy_node', jsonb_build_object('count', archived));
  END IF;

  RETURN jsonb_build_object('promoted', promoted, 'merged', merged, 'archived', archived);
END;
$$;

-- Daily schedule across all workspaces (idempotent re-schedule).
CREATE EXTENSION IF NOT EXISTS pg_cron;
DO $$
BEGIN
  PERFORM cron.unschedule('taxonomy-governance-daily');
EXCEPTION WHEN OTHERS THEN NULL;
END $$;
SELECT cron.schedule('taxonomy-governance-daily', '0 3 * * *',
  $$ SELECT public.apply_taxonomy_governance(id) FROM public.workspaces $$);
```

- [ ] **Step 2: Apply** to `grdwaolihoeaqaerovdg` (MCP `apply_migration` or `supabase db push`).
  - If `CREATE EXTENSION pg_cron` errors (not allowed in-migration on the project), enable pg_cron in the Supabase dashboard (Database → Extensions), then re-run only the `cron.*` block. The column + routine must apply regardless.

- [ ] **Step 3: Verify**
```sql
select column_name from information_schema.columns where table_name='taxonomy_nodes' and column_name='auto_promoted';
select proname from pg_proc where proname='apply_taxonomy_governance';
select jobname,schedule from cron.job where jobname='taxonomy-governance-daily';
```
Expected: a row each (the cron row only if pg_cron is enabled).

- [ ] **Step 4: Commit**
```bash
git add supabase/migrations/20260622140000_taxonomy_governance.sql
git commit -m "feat(taxonomy): apply_taxonomy_governance (auto-promote/merge/decay) + daily cron (phase 3)"
```

---

## Task 2: Hand-sync types

**Files:** Modify `src/lib/types.ts`, `src/integrations/supabase/types.ts`, `src/lib/events.ts`

- [ ] **Step 1: `src/lib/types.ts`** — in `TaxonomyNode`, after `merged_into_id`, add:
```ts
  auto_promoted?: boolean;
```

- [ ] **Step 2: `src/integrations/supabase/types.ts`**
  - In `taxonomy_nodes` `Row` add `auto_promoted: boolean;`, `Insert` add `auto_promoted?: boolean;`, `Update` add `auto_promoted?: boolean;`.
  - In the `Functions` object (where `merge_taxonomy_node`/`match_taxonomy_nodes` are), add:
```ts
      apply_taxonomy_governance: {
        Args: { p_workspace_id: number; p_auto_promote?: number; p_min_size?: number; p_merge_eps?: number; p_stale_days?: number };
        Returns: Json;
      };
```
(Match the file's existing `Functions` formatting; `Json` is already defined.)

- [ ] **Step 3: `src/lib/events.ts`** — add to the `AppEventType` union: `"taxonomy_node_auto_promoted"`, `"taxonomy_node_auto_merged"`, `"taxonomy_node_decayed"`.

- [ ] **Step 4: Type-check** `npx tsc -p tsconfig.app.json --noEmit 2>&1 | grep -v "src/test/"` → clean.

- [ ] **Step 5: Commit**
```bash
git add src/lib/types.ts src/integrations/supabase/types.ts src/lib/events.ts
git commit -m "feat(taxonomy): auto_promoted + apply_taxonomy_governance + governance event types (phase 3)"
```

---

## Task 3: UI — auto badge, Undo, Run governance

**Files:** Modify `src/components/taxonomy/TaxonomyTree.tsx`, `src/pages/Taxonomy.tsx`

- [ ] **Step 1: `TaxonomyTree.tsx`** — accept an optional `onUndo` and badge auto nodes.
Change the component signature/props to:
```tsx
export function TaxonomyTree({ nodes, onUndo }: { nodes: TaxonomyNode[]; onUndo?: (id: string) => void }) {
```
Thread `onUndo` into `NodeRow` (add it to `NodeRow`'s props and pass it in the recursive call). In `NodeRow`, after the existing description span, add:
```tsx
        {node.auto_promoted && (
          <>
            <Badge variant="outline" className="text-[10px]">auto</Badge>
            {onUndo && (
              <button className="text-[10px] text-muted-foreground underline" onClick={() => onUndo(node.id)}>undo</button>
            )}
          </>
        )}
```
And in the recursive children render, pass `onUndo`: `<NodeRow key={c.id} node={c} depth={depth + 1} onUndo={onUndo} />`. The top-level `nodes.map` also passes `onUndo`.

- [ ] **Step 2: `Taxonomy.tsx`** — add a governance mutation + an undo mutation + a "Run governance" button.
2a. After the `discover` mutation, add:
```tsx
  const governance = useMutation({
    mutationFn: async () => {
      const { data, error } = await supabase.rpc("apply_taxonomy_governance", { p_workspace_id: workspaceId! });
      if (error) throw error;
      return data as { promoted: number; merged: number; archived: number };
    },
    onSuccess: (d) => { qc.invalidateQueries({ queryKey: ["taxonomy", workspaceId] }); toast.success(`Governance: ${d.promoted} promoted, ${d.merged} merged, ${d.archived} archived.`); },
    onError: (e) => toast.error("Governance failed", { description: e instanceof Error ? e.message : undefined }),
  });

  const undo = useMutation({
    mutationFn: async (id: string) => {
      const { error } = await supabase.from("taxonomy_nodes").update({ status: "candidate", auto_promoted: false }).eq("id", id);
      if (error) throw error;
    },
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["taxonomy", workspaceId] }); toast.success("Reverted to candidate"); },
    onError: (e) => toast.error("Undo failed", { description: e instanceof Error ? e.message : undefined }),
  });
```
2b. In the button group, add (after "Discover themes"):
```tsx
          <Button variant="outline" size="sm" disabled={governance.isPending || !workspaceId} onClick={() => governance.mutate()}>
            <ShieldCheck className="h-3.5 w-3.5 mr-1.5" />{governance.isPending ? "Running…" : "Run governance"}
          </Button>
```
2c. Import `ShieldCheck` from `lucide-react` (add to the existing lucide import).
2d. Pass `onUndo` to the tree: change `<TaxonomyTree nodes={data?.tree ?? []} />` to `<TaxonomyTree nodes={data?.tree ?? []} onUndo={(id) => undo.mutate(id)} />`.

- [ ] **Step 3: Verify** `npx tsc -p tsconfig.app.json --noEmit 2>&1 | grep -v "src/test/"` → clean; `npm run build` → `✓ built`.

- [ ] **Step 4: Commit**
```bash
git add src/components/taxonomy/TaxonomyTree.tsx src/pages/Taxonomy.tsx
git commit -m "feat(taxonomy): auto badge + Undo + Run governance button (phase 3)"
```

---

## Task 4: End-to-end verification + PR

- [ ] **Step 1:** `npm run build` → `✓ built`.
- [ ] **Step 2: Backend verify** (SQL, controller): create a synthetic high-confidence candidate, run governance, confirm promotion + audit:
```sql
-- seed a candidate that meets the auto-promote bar
insert into public.taxonomy_nodes (workspace_id, level, name, slug, status, origin, confidence, evidence)
values (1, 1, 'governance_test', 'governance_test', 'candidate', 'discovered', 0.9,
        '{"size":6,"samples":["x"],"signal_ids":[]}'::jsonb);
select public.apply_taxonomy_governance(1);            -- expect promoted >= 1
select status, auto_promoted from public.taxonomy_nodes where slug='governance_test';  -- active, true
select event_type, metadata from public.events where event_type like 'taxonomy_node_auto%' order by created_at desc limit 3;
-- cleanup
delete from public.taxonomy_nodes where slug='governance_test';
```
- [ ] **Step 3: UI smoke** (manual): on `/taxonomy`, "Run governance" toasts the counts; an auto-promoted node shows an **auto** badge + **undo**; clicking undo returns it to the review queue.
- [ ] **Step 4: PR**
```bash
git push -u origin feat/taxonomy-phase-3
gh pr create --base main --head feat/taxonomy-phase-3 --title "Adaptive taxonomy — Phase 3 (graduated authority)" --body "apply_taxonomy_governance auto-promotes/merges/decays candidates (audited + reversible), daily via pg_cron; UI auto badge + Undo + Run governance. Stacked on PR #8. Spec: docs/superpowers/specs/2026-06-21-adaptive-taxonomy-design.md"
```

---

## Self-review (completed)

- **Spec coverage:** Phase-3 items — graduated auto-promotion (threshold on confidence×size), conservative auto-merge (pgvector), decay/archival of stale discovered nodes, scheduled (pg_cron), audited (`events`), reversible (`auto_promoted` + Undo). All mapped. Uploaded taxonomy is explicitly protected from auto-archive/merge.
- **Placeholder scan:** none — full SQL + UI in every step; thresholds concrete and arg-tunable.
- **Type consistency:** `auto_promoted` (Task 2) read in `TaxonomyTree` (Task 3) and set by the routine (Task 1) + Undo (Task 3); `apply_taxonomy_governance` signature (Task 1) matches the `.rpc(...)` Args type (Task 2) and call (Task 3).
- **Risk:** pg_cron may need dashboard enablement (Step 2 fallback noted). The auto-merge loop is O(n) nearest-neighbour per discovered node — fine at taxonomy scale (tens–hundreds of nodes).
