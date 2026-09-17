# What's in this repository

A guide to every folder in `CLARA/`: what it is, why it exists, and what is safe to change.

The confusing thing about this repo is that it holds **three unrelated kinds of material** in one place — a production product, frozen history, and tool exhaust (the MSc thesis and the commercial kit moved to a private repository on 17 September 2026). Once you see which bucket a folder belongs to, the rest follows.

The other useful fact: the repo is roughly **900 MB on disk but only ~12 MB of real content** across 589 tracked files. Almost everything large is regenerable.

## The map

```
CLARA/
│
├── ① THE PRODUCT — code that runs in production
│   ├── apps/api/               FastAPI backend · 185 files · 84 endpoints
│   │   ├── app/routers/          the 8 URL surfaces the frontend calls
│   │   ├── app/services/         the brain — 41 files, all in use
│   │   ├── app/agents/           LangGraph loop; approval = interrupt node
│   │   ├── app/connectors/       pull: Zendesk/Trustpilot/App Store · push: Jira/Slack
│   │   ├── app/domain/           the shared vocabulary (models.py = 1110 lines)
│   │   ├── app/evals/            100-item golden set + published metrics  ← thesis evidence
│   │   ├── app/tests/            101 test files — the safety net
│   │   └── migrations/           001→011 SQL, run in order to build the DB
│   ├── apps/web/               Next.js frontend · 95 files
│   │   ├── app/(dashboard)/      13 product screens (signals→insights→actions→learnings)
│   │   ├── app/(auth)/           sign-in + MFA
│   │   ├── app/legal|pricing|security|ai-literacy-basics/   public pages, flag-gated
│   │   ├── content/legal/        the three reviewed legal pages the build renders
│   │   ├── public/home.html      the marketing landing page (hand-written, not React)
│   │   └── lib/                  API client, i18n (EN/DE), types
│   ├── data/                   ⚠ NOT documentation — seed JSON imported by 3 app files
│   ├── infra/                  docker-compose for local Postgres + Langfuse
│   ├── scripts/live_smoke.py   the 17-check production smoke test
│   └── .github/workflows/      ci.yml (every PR) · uptime.yml (every 30 min)
│
├── ② THE THESIS and ③ THE BUSINESS — moved to a private repository on 17 Sep 2026
│
├── ④ HISTORY — frozen, nothing depends on it
│   ├── reference/elvis/          snapshot of the predecessor codebase (port reference)
│   ├── docs/archive/             dated one-off snapshots (code review, E2E runs, demos)
│   └── docs/reviews/             the two external LLM platform audits (17 Jul 2026)
│
└── ⑤ TOOL EXHAUST — regenerable, most of the disk
    ├── node_modules/ · apps/web/.next/ · apps/api/.venv/     (rebuild on demand)
    ├── .claude/ .serena/ .firecrawl/ .playwright-mcp/ .understand-anything/
    ├── .pytest_cache/ .ruff_cache/ __pycache__/
    └── .git/                     the repository history itself
```

## ① The product

| Folder | What it is | Safe to change? |
|---|---|---|
| `apps/api/app/routers/` | The 8 groups of URLs the frontend calls (problems, signals, system, taxonomy, governance, connectors, measurement). Thin — they delegate to services. | Yes, with tests |
| `apps/api/app/services/` | Where the actual product logic lives: triage, synthesis, outcome measurement, exports, persistence. All 41 files are imported by something. | Yes, with tests |
| `apps/api/app/agents/` | The LangGraph state machine that walks a signal through the loop. The human-approval step is an *interrupt* node — this is the governance design, not just plumbing. | Carefully |
| `apps/api/app/evals/` | `golden_set.json` (100 hand-labelled items) and `published_metrics.json` are **hand-curated data, not build output**, even though they look generated. They are the evidence behind the thesis numbers and the in-product model card. | Only deliberately |
| `apps/api/migrations/` | Numbered SQL, run in order, to build the database. `011` enforces tenant row-level security. | Never edit a shipped one |
| `apps/api/app/tests/` | 101 test files. `conftest.py` forces a throwaway SQLite DB so tests can never touch real data. | Yes — add freely |
| `apps/web/app/(dashboard)/` | The 13 screens behind login. Biggest: `taxonomy` (719 lines), `dashboard` (599), `insights/[id]` (542). | Yes |
| `apps/web/public/home.html` | The marketing landing page. Hand-written HTML, **not** React — that's why it isn't in the app folder. Served at `/` by a rewrite in `next.config.mjs`. | Yes |
| `apps/web/lib/` | Shared plumbing: `client-api.ts` (the API client), `i18n.tsx` (EN/DE, 1290 lines), `types.ts` (mirrors the backend models). | Yes |
| `data/` | **Not documentation.** Seed JSON imported directly by `apps/web/lib/sample-data.ts`, `signal-intake-panel.tsx`, and served by `apps/api/app/routers/signals.py`. Deleting it breaks the build. | No |
| `infra/` | Two docker-compose files so you can run Postgres and Langfuse locally, plus the SQL that enables `vector`/`pg_cron`/`pg_net`. | Yes |
| `scripts/live_smoke.py` | The 17-check production smoke test. Run by `.github/workflows/uptime.yml` every 30 minutes; opens a GitHub issue on a second consecutive failure. | Yes |

## ② The thesis and ③ the business

Moved to a private repository on 17 September 2026: the manuscript, evaluation harness, instruments, defense deck, strategy, playbooks, legal kit and brand assets. Nothing in the product imports them any more. The one build dependency that existed, the three reviewed legal pages (`impressum.md`, `datenschutzerklaerung.md`, `agb-b2b.md`), now lives in `apps/web/content/legal/` and is read by `apps/web/app/(public)/legal/[slug]/page.tsx` at build time. Publishing is fail-closed: the pages 404 unless `NEXT_PUBLIC_LEGAL_PAGES=1`, and they refuse to render if the markdown still contains `DRAFT` or `{{placeholders}}`.

## ④ History

Nothing here is imported by any code. It exists so you can answer "where did this come from?"

- **`reference/elvis/`** — a frozen snapshot of the predecessor codebase (React/Vite/Supabase) kept as a port reference. `docs/hybrid-architecture.md` is the summary of what was actually carried over.
- **`docs/archive/`** — dated one-off snapshots: the 2 July code review (cited by the thesis at `manuscript/04_artifact.md`), two 5 July test runs, a demo script, a July strategy plan.
- **`docs/reviews/`** — the two independent external LLM audits of the platform from 17 July 2026. Harsh, specific, and the direct cause of the legal pack and the governance-hardening work that followed.

## ⑤ Tool exhaust

Every dot-directory except `.github/` is created by a tool and is gitignored. `.claude/`, `.serena/`, `.firecrawl/`, `.playwright-mcp/` and `.understand-anything/` are all safe to delete at any time — they regenerate or are simply logs. So are `node_modules/`, `apps/web/.next/`, and `apps/api/.venv/`, though you'll pay a reinstall.

`.github/` is the exception: it holds real configuration (the CI and uptime workflows) and is tracked.

## Gotchas worth knowing

1. **`.gitignore` has a bare `build/` rule**, which silently ignores *any* folder named `build` at any depth. Anchoring the rule to `/build/` would change that.
2. **Two component directories in the frontend**: `apps/web/app/components/` (18 feature panels) and `apps/web/components/` (ui / layout / auth). No rule is written down for which goes where.
3. **Two rate limiters**, both live: a per-IP ASGI middleware in `apps/api/app/main.py` and a per-workspace, plan-based dependency in `apps/api/app/rate_limit.py`. They key on different things; neither is dead.
4. **`apps/api/app/billing.py` is a deliberate stub** — it defines plan limits without calling Stripe. No billing routes exist.
5. **Three public pages are built but dark**: `/pricing`, `/legal/*`, `/ai-literacy-basics` are finished and gated behind `NEXT_PUBLIC_LEGAL_PAGES`, pending the legal review. Nothing links to them yet.

## Known dead code (not yet removed)

Verified unreferenced, left in place because removing them touches shipping code:

- `apps/web/lib/api.ts` — superseded by `lib/client-api.ts`; zero importers.
- `apps/web/app/components/customer-context-panel.tsx` — zero importers.
- `apps/web/components/ui/separator.tsx`, `ui/progress.tsx` — never used.
- Five unused `@radix-ui` dependencies in `apps/web/package.json` (dialog, dropdown-menu, select, toast, tooltip).
- `apps/web/app/page.tsx` — redundant with the `beforeFiles` rewrite in `next.config.mjs`.

---

*Written 4 August 2026, after a cleanup that removed a forgotten 816 MB duplicate worktree, a byte-identical duplicate of `thesis-update/`, and ~13 MB of stale tool logs.*
