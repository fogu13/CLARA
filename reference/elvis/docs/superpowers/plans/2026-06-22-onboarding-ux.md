# Onboarding UX Polish — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Give brand-new signups a real first-run experience: a **Welcome wizard** (name your workspace, optionally load sample data) shown once, then helpful **empty-state CTAs** instead of blank screens. Auto-workspace-on-signup already exists; this adds the human-facing layer.

**Architecture:** A `workspaces.onboarded` flag (defaults false for new workspaces; backfilled true for existing). `AppLayout` redirects un-onboarded users to a standalone `/welcome` page. Welcome sets the workspace name + `onboarded=true` and can insert a few demo signals via a pure client helper. The Signals page shows an empty-state with CTAs (Import / Add source / Load sample) when the workspace has no signals.

**Tech Stack:** Supabase (Postgres), React 18 + Vite + TS, React Query, React Router v6, shadcn/ui. Builds on existing `useWorkspaceId()`, `AppLayout`, `ProtectedRoute`, `supabase` client.

**Conventions (CLAUDE.md):** hand-sync types; `npx tsc -p tsconfig.app.json --noEmit` (exclude `src/test/*`); migrations applied to `grdwaolihoeaqaerovdg`; `signals.tags` is JSONB (client array inserts are fine via PostgREST).

---

## File Structure

| File | Responsibility |
|---|---|
| `supabase/migrations/20260622160000_workspace_onboarded.sql` | `workspaces.onboarded` flag (+ backfill existing = true) |
| `src/integrations/supabase/types.ts` (modify) | `onboarded` on `workspaces` Row/Insert/Update |
| `src/lib/sample-data.ts` (create) | pure `sampleSignals(workspaceId)` rows + `loadSampleData()` insert helper |
| `src/lib/sample-data.test.ts` (create) | unit test for `sampleSignals` |
| `src/pages/Welcome.tsx` (create) | first-run wizard (name + optional sample data) |
| `src/components/shared/EmptyState.tsx` (create) | reusable empty-state card |
| `src/components/layout/AppLayout.tsx` (modify) | redirect un-onboarded → `/welcome` |
| `src/pages/Signals.tsx` (modify) | show `<EmptyState>` when no signals |
| `src/App.tsx` (modify) | add protected `/welcome` route |

---

## Task 1: Migration — `onboarded` flag

**Files:** Create `supabase/migrations/20260622160000_workspace_onboarded.sql`

- [ ] **Step 1: Write**
```sql
-- Onboarding: new workspaces start un-onboarded so the app shows the Welcome wizard once.
ALTER TABLE public.workspaces
  ADD COLUMN IF NOT EXISTS onboarded boolean NOT NULL DEFAULT false;

-- Existing workspaces are already in use — don't show them the wizard.
UPDATE public.workspaces SET onboarded = true WHERE created_at < now();
```

- [ ] **Step 2: Apply** to `grdwaolihoeaqaerovdg` (MCP `apply_migration`). Verify:
```sql
select column_name from information_schema.columns where table_name='workspaces' and column_name='onboarded';
select count(*) filter (where onboarded) as onboarded, count(*) as total from public.workspaces;
```
Expected: column exists; all existing workspaces `onboarded=true`.

- [ ] **Step 3: Commit**
```bash
git add supabase/migrations/20260622160000_workspace_onboarded.sql
git commit -m "feat(onboarding): workspaces.onboarded flag (+ backfill existing)"
```

---

## Task 2: Hand-sync types

**Files:** Modify `src/integrations/supabase/types.ts`

- [ ] **Step 1:** In the `workspaces` table type: add `onboarded: boolean;` to `Row`, and `onboarded?: boolean;` to `Insert` and `Update` (match the file's existing style for `workspaces`).
- [ ] **Step 2:** `npx tsc -p tsconfig.app.json --noEmit 2>&1 | grep -v "src/test/"` → clean.
- [ ] **Step 3:** Commit `git add src/integrations/supabase/types.ts && git commit -m "feat(onboarding): onboarded on workspaces types"`

---

## Task 3: Sample-data helper (TDD)

**Files:** Create `src/lib/sample-data.ts`, `src/lib/sample-data.test.ts`

- [ ] **Step 1: Failing test `src/lib/sample-data.test.ts`**
```ts
import { describe, it, expect } from "vitest";
import { sampleSignals } from "./sample-data";

describe("sampleSignals", () => {
  it("returns workspace-scoped qualitative rows with tags + recorded_at", () => {
    const rows = sampleSignals(7);
    expect(rows.length).toBeGreaterThanOrEqual(5);
    for (const r of rows) {
      expect(r.workspace_id).toBe(7);
      expect(r.signal_type).toBe("qualitative");
      expect(typeof r.text_content).toBe("string");
      expect(Array.isArray(r.tags)).toBe(true);
      expect(typeof r.recorded_at).toBe("string");
    }
  });
});
```

- [ ] **Step 2: Run → FAIL** (`npm run test -- src/lib/sample-data.test.ts`).

- [ ] **Step 3: Implement `src/lib/sample-data.ts`**
```ts
import { supabase } from "@/integrations/supabase/client";

export interface SampleSignalRow {
  workspace_id: number;
  signal_type: "qualitative";
  source: string;
  category: string;
  text_content: string;
  urgency: string;
  tags: string[];
  metadata: Record<string, unknown>;
  recorded_at: string;
}

const SAMPLES: { source: string; text: string; tags: string[] }[] = [
  { source: "nps_survey", text: "Checkout failed three times on the payment step before it went through.", tags: ["checkout_failure", "payment"] },
  { source: "support_ticket", text: "Could not pay with my card at checkout — it kept erroring.", tags: ["checkout_failure", "payment"] },
  { source: "app_review", text: "Delivery status never updated; I had no idea where my order was.", tags: ["late_delivery", "tracking"] },
  { source: "open_feedback", text: "Order arrived late and the tracking was wrong the whole time.", tags: ["late_delivery", "tracking"] },
  { source: "nps_survey", text: "Onboarding was confusing — I couldn't figure out how to connect a source.", tags: ["onboarding_friction"] },
  { source: "csat_survey", text: "The pricing page is unclear about what's included in each tier.", tags: ["pricing_unclear"] },
  { source: "social_mention", text: "Love the new dashboard — so much faster than before!", tags: ["positive_dashboard"] },
];

/** Pure: build sample signal rows for a workspace (last 7 days). */
export function sampleSignals(workspaceId: number): SampleSignalRow[] {
  const now = Date.now();
  return SAMPLES.map((s, i) => ({
    workspace_id: workspaceId,
    signal_type: "qualitative",
    source: s.source,
    category: "feedback",
    text_content: s.text,
    urgency: "medium",
    tags: s.tags,
    metadata: { sample: true },
    recorded_at: new Date(now - (i + 1) * 86400000).toISOString(),
  }));
}

/** Insert the sample signals into the user's workspace (RLS allows own-workspace insert). */
export async function loadSampleData(workspaceId: number): Promise<number> {
  const rows = sampleSignals(workspaceId);
  const { error } = await supabase.from("signals").insert(rows as never);
  if (error) throw error;
  return rows.length;
}
```

- [ ] **Step 4: Run → PASS.**
- [ ] **Step 5: Commit** `git add src/lib/sample-data.ts src/lib/sample-data.test.ts && git commit -m "feat(onboarding): sample-data helper with test"`

---

## Task 4: Welcome wizard + empty state + guard + route

**Files:** Create `src/pages/Welcome.tsx`, `src/components/shared/EmptyState.tsx`; modify `src/components/layout/AppLayout.tsx`, `src/pages/Signals.tsx`, `src/App.tsx`

- [ ] **Step 1: `src/components/shared/EmptyState.tsx`**
```tsx
import type { ReactNode } from "react";

export function EmptyState({ title, description, children }: { title: string; description?: string; children?: ReactNode }) {
  return (
    <div className="flex flex-col items-center justify-center rounded-lg border border-dashed border-border py-16 text-center">
      <h3 className="text-sm font-semibold">{title}</h3>
      {description && <p className="mt-1 text-sm text-muted-foreground max-w-md">{description}</p>}
      {children && <div className="mt-4 flex flex-wrap items-center justify-center gap-2">{children}</div>}
    </div>
  );
}
```

- [ ] **Step 2: `src/pages/Welcome.tsx`** (standalone — does NOT use AppLayout)
```tsx
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useQueryClient } from "@tanstack/react-query";
import { supabase } from "@/integrations/supabase/client";
import { useWorkspaceId } from "@/hooks/use-workspace";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { toast } from "sonner";
import { loadSampleData } from "@/lib/sample-data";

const WelcomePage = () => {
  const workspaceId = useWorkspaceId();
  const navigate = useNavigate();
  const qc = useQueryClient();
  const [name, setName] = useState("");
  const [withSample, setWithSample] = useState(true);
  const [busy, setBusy] = useState(false);

  const finish = async () => {
    if (!workspaceId) return;
    setBusy(true);
    try {
      const update: { onboarded: boolean; name?: string } = { onboarded: true };
      if (name.trim()) update.name = name.trim();
      const { error } = await supabase.from("workspaces").update(update).eq("id", workspaceId);
      if (error) throw error;
      if (withSample) {
        const n = await loadSampleData(workspaceId);
        toast.success(`Loaded ${n} sample signals.`);
      }
      qc.invalidateQueries();
      navigate("/app");
    } catch (e) {
      toast.error("Could not finish setup", { description: e instanceof Error ? e.message : undefined });
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-background p-4">
      <div className="w-full max-w-md rounded-xl border border-border p-6">
        <h1 className="text-xl font-semibold">Welcome to Odradek</h1>
        <p className="mt-1 text-sm text-muted-foreground">Let's set up your workspace. Takes 10 seconds.</p>
        <div className="mt-6 space-y-4">
          <div className="space-y-1.5">
            <Label htmlFor="ws">Workspace name</Label>
            <Input id="ws" placeholder="e.g. Acme Inc" value={name} onChange={(e) => setName(e.target.value)} />
          </div>
          <div className="flex items-center justify-between">
            <div>
              <Label htmlFor="sample">Load sample data</Label>
              <p className="text-xs text-muted-foreground">A few example signals so you can explore right away.</p>
            </div>
            <Switch id="sample" checked={withSample} onCheckedChange={setWithSample} />
          </div>
        </div>
        <Button className="mt-6 w-full" disabled={busy || !workspaceId} onClick={finish}>
          {busy ? "Setting up…" : "Get started"}
        </Button>
      </div>
    </div>
  );
};

export default WelcomePage;
```

- [ ] **Step 3: Guard in `src/components/layout/AppLayout.tsx`**
READ the file. Add imports (`useQuery` from `@tanstack/react-query`, `supabase`, `useWorkspaceId`, `Navigate` from `react-router-dom`). At the top of the component body, before the normal render, add a check:
```tsx
  const workspaceId = useWorkspaceId();
  const { data: onboarded, isLoading } = useQuery({
    queryKey: ["onboarded", workspaceId],
    enabled: !!workspaceId,
    queryFn: async () => {
      const { data } = await supabase.from("workspaces").select("onboarded").eq("id", workspaceId!).single();
      return data?.onboarded ?? true; // fail-open: never trap a user out of the app
    },
  });
  if (workspaceId && !isLoading && onboarded === false) {
    return <Navigate to="/welcome" replace />;
  }
```
(Place this after existing hooks in `AppLayout`; do not change the rest of the layout. If `AppLayout` already calls `useWorkspaceId`, reuse it rather than duplicating.)

- [ ] **Step 4: `src/App.tsx`** — add the protected route (NOT wrapped in AppLayout — Welcome is standalone). Import `Welcome` and add next to the other protected routes:
```tsx
<Route path="/welcome" element={<ProtectedRoute><Welcome /></ProtectedRoute>} />
```

- [ ] **Step 5: Signals empty-state in `src/pages/Signals.tsx`**
READ the file. Import `EmptyState`. In the render, when not loading and `signals.length === 0` (and no active search/filter), render an empty state instead of the empty table, e.g. just above the table block:
```tsx
{!isLoading && signals.length === 0 ? (
  <EmptyState title="No signals yet" description="Import a CSV, connect a source, or load sample data to get started.">
    <Button variant="outline" size="sm" onClick={() => fileRef.current?.click()}><Upload className="h-3.5 w-3.5 mr-1.5" />Import CSV</Button>
  </EmptyState>
) : (
  /* existing table JSX */
)}
```
Wire it minimally — keep the existing table for the non-empty case. (The hidden file input + `importCsv` already exist on this page.)

- [ ] **Step 6: Verify**
`npx tsc -p tsconfig.app.json --noEmit 2>&1 | grep -v "src/test/"` → clean.
`npm run build` → `✓ built`. (Add shadcn `label`/`switch` via `npx shadcn@latest add label switch` only if missing — they likely exist.)

- [ ] **Step 7: Commit**
```bash
git add src/pages/Welcome.tsx src/components/shared/EmptyState.tsx src/components/layout/AppLayout.tsx src/pages/Signals.tsx src/App.tsx
git commit -m "feat(onboarding): welcome wizard + onboarding guard + signals empty-state"
```

---

## Task 5: Verify + PR

- [ ] **Step 1:** `npm run build` → `✓ built`; `npm run test` → taxonomy + sample-data tests pass.
- [ ] **Step 2 (manual, needs a fresh signup):** sign up a new account → lands on `/welcome` → name workspace + keep "load sample data" → **Get started** → dashboard shows the sample signals; the wizard does not appear again on next login. An empty workspace (sample off) shows the Signals empty-state.
- [ ] **Step 3: PR**
```bash
git push -u origin feat/self-serve-onboarding
gh pr create --base main --head feat/self-serve-onboarding --title "Onboarding UX (welcome wizard + empty states)" --body "First-run welcome wizard (name workspace + optional sample data), onboarding guard redirecting un-onboarded workspaces to /welcome, and a Signals empty-state. workspaces.onboarded flag backfilled true for existing workspaces."
```

---

## Self-review (completed)
- **Coverage:** welcome wizard (name + sample data), onboarded flag + guard, empty-state CTAs — all mapped.
- **No placeholders:** full code throughout; sample data is concrete.
- **Type consistency:** `workspaces.onboarded` (Task 2) read in AppLayout guard + set in Welcome (Task 4); `sampleSignals`/`loadSampleData` (Task 3) used by Welcome.
- **Safety:** the guard is **fail-open** (defaults `onboarded=true` on query miss) so a query hiccup never locks a user out; existing workspaces are backfilled `onboarded=true` so current users never see the wizard.
- **Note:** the redirect/wizard flow needs a real fresh signup to fully verify (controller verifies migration + build + unit test; live signup is the manual step).
