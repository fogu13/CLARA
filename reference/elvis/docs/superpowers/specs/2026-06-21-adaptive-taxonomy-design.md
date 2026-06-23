# Adaptive Company Taxonomy — Design Spec

**Date:** 2026-06-21
**Status:** Approved (design); pending implementation plan
**Owner:** Elvis Shehi (Odradek, MSc Responsible AI thesis)

## 1. Motivation

Odradek today has **no governed taxonomy**. `enrich-signal` asks the LLM for free-form
snake_case theme tags (open vocabulary — the same issue surfaces as `checkout_failure`,
`payment_failure`, `checkout_error` on different runs), and `synthesize-insights` assigns a
**hardcoded** `category` enum. Nothing reconciles tags, and a company cannot bring its own
vocabulary.

This spec adds a **company-owned, 3-level, self-improving taxonomy** — the capability that is
Enterpret's core moat ("adaptive taxonomy"). For the thesis it is positioned as a **5th
non-trivial design decision**: *governed taxonomy evolution* (graduated authority + auditable,
reversible promotion/merge), strengthening the "Building the Memory" contribution.

## 2. Locked decisions (from brainstorming)

| Fork | Decision |
|---|---|
| Scope | Full adaptive taxonomy (upload + self-improvement), all 3 phases |
| Structure | 3-level: **category → theme → subtheme** |
| Self-improvement | **Graduated authority**: auto-promote/merge above threshold (logged, reversible); queue lower-confidence for human approval |
| Matching | **Hybrid**: embeddings (pgvector) for retrieval + synonym/merge detection; LLM for final assignment + naming new nodes |
| Embeddings provider | Gemini embedding endpoint (same OpenAI-compatible base already configured); `text-embedding-004` → `vector(768)` (dimension is model-configurable) |

## 3. Data model

Enable the `vector` (pgvector) extension.

### `taxonomy_nodes`
Self-referential tree.
- `id uuid pk`
- `workspace_id int → workspaces(id)`
- `parent_id uuid → taxonomy_nodes(id)` (null at level 1)
- `level int` (1=category, 2=theme, 3=subtheme; enforce `level = parent.level + 1`)
- `name text`, `slug text`, `description text`
- `status text` (`active | candidate | merged | archived`)
- `origin text` (`uploaded | seeded | discovered`)
- `confidence numeric` (0–1), `times_matched int default 0`, `last_matched_at timestamptz`
- `last_validated_at timestamptz` (decay reference), `merged_into_id uuid → taxonomy_nodes(id)`
- `embedding vector(768)`
- `created_by text`, `created_at`, `updated_at`
- Indexes: `(workspace_id, status)`, `(workspace_id, parent_id)`, ivfflat/hnsw on `embedding`.
- RLS: workspace-scoped (mirror existing policies).

### `signal_node_map`
Governed mapping layer (multi-label, with provenance). Raw `signals.tags` are kept as the
*unreconciled* LLM input; nodes are the governed truth.
- `id bigserial pk`, `signal_id int → signals(id)`, `node_id uuid → taxonomy_nodes(id)`
- `score numeric` (match similarity/confidence), `mapped_by text` (`system_auto | system_llm | user`)
- `created_at`; unique `(signal_id, node_id)`. RLS workspace-scoped via signal.

### Audit
Reuse `events` (`event_type` in `taxonomy_node_promoted | _merged | _rejected | _auto_promoted |
_mapped`), with actor, confidence, and evidence in `metadata`. Every change is reversible.

> **Type-sync (CLAUDE.md gotcha):** new tables/columns must be mirrored by hand in
> `src/integrations/supabase/types.ts` AND domain types in `src/lib/types.ts`.

## 4. Pipeline & functions

1. **Upload** — `/taxonomy` accepts CSV/JSON (`category,theme,subtheme,description`). Parser builds
   the 3-level tree, inserts nodes (`status=active`, `origin=uploaded`), then a function
   **`embed-taxonomy`** generates embeddings for each node (`name + description`).
2. **Map** — extend **`enrich-signal`**: after producing raw tags, embed the signal → pgvector
   nearest-K nodes → LLM confirms the best node (subtheme) or returns "unmapped" (the hybrid step)
   → write `signal_node_map` with `score`. Low-score/unmapped signals are flagged for evolution.
3. **Evolve** — new function **`evolve-taxonomy`** (on-demand button + scheduled `pg_cron`):
   cluster unmapped/low-confidence signals by embedding similarity → for clusters above a frequency
   threshold, LLM names a **candidate** node and proposes placement (category/theme/subtheme) with
   example-signal evidence → insert as `status=candidate` with a confidence score.
4. **Graduated authority** —
   - Promote: candidate `confidence × frequency ≥ auto_threshold` → `status=active` automatically
     (audited, reversible). Else → human **review queue**.
   - Merge: a node whose `embedding` is within `ε` of an existing `active` node → propose merge;
     auto-merge above `merge_threshold` (`merged_into_id` set, `signal_node_map` remapped), else queue.
   - All thresholds live in `workspaces.settings`.
5. **Decay** — node `confidence` erodes from `last_validated_at`/`last_matched_at` (reuse the
   learnings-decay logic in `src/lib/learnings.ts`); stale nodes flagged for archive/review.

## 5. UI

New protected route **`/taxonomy`** (+ sidebar entry):
- **Tree view** (3 levels): status badge (`active`/`candidate`), match count, confidence, stale flag.
- **Upload** (CSV/JSON) with format help + a downloadable template.
- **Review queue**: candidate nodes and proposed merges, each with example-signal evidence and
  **Approve / Edit / Reject / Merge**. Auto-applied changes show an "auto" badge + **Undo**.
- **Node detail**: linked signals, change history (from `events`).

Follow existing patterns (React Query mutations, Sonner toasts, `useWorkspaceId()`, shadcn dialogs).

## 6. Governance & thesis framing

- **Graduated authority** made concrete: risk-tiered automation with auditable, reversible changes —
  the thesis's "white-box advantage / graduated authority" lens applied to taxonomy.
- **Evaluation hooks** (feed `evaluation/prototype_metrics.py`):
  - **Coverage %** — mapped vs unmapped signals over time.
  - **Consistency** — synonym collisions / duplicate-node rate over time.
  - **Human-correction rate** — share of auto-promotions/merges later overridden.
  - **Time-to-stabilize** — iterations until coverage plateaus.
- These metrics are what make this a *defensible* design decision, not just a feature.

## 7. Phasing (each phase independently shippable)

- **Phase 1 — Foundation:** pgvector + schema + types-sync; upload + `embed-taxonomy`; `/taxonomy`
  tree UI; mapping in `enrich-signal` (`signal_node_map`); coverage metric.
- **Phase 2 — Discovery + governance:** `evolve-taxonomy` candidate detection; human review queue
  (approve/edit/reject/merge); audit events.
- **Phase 3 — Graduated autonomy:** auto-promote + auto-merge above thresholds (logged, undoable);
  confidence decay + stale archival; scheduled `pg_cron` evolution.

## 8. Non-goals (YAGNI)

- No taxonomy versioning/rollback beyond per-change Undo.
- No multi-workspace shared/global taxonomies.
- No manual drag-and-drop tree re-parenting in v1 (edit name/description/placement via form only).
- No real-time taxonomy updates; mapping runs in the existing enrich pass + scheduled evolution.

## 9. Risks / open questions

- **Embedding cost/latency** at signal volume — mitigate with batch embedding + only embedding
  qualitative signals; cache node embeddings.
- **pgvector index choice** (ivfflat vs hnsw) — pick hnsw for recall if Postgres version supports it.
- **Threshold tuning** for graduated authority — start conservative (high auto-threshold) and expose
  in settings; the human-correction-rate metric guides tuning.
- **Prompt size** when passing candidate context to the LLM — bounded by nearest-K retrieval.
