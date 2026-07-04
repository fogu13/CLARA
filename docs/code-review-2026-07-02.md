# CLARA — Code Review (2026-07-02)

Adversarially-verified review: 7 specialist finders → skeptic verifier per finding. **58 confirmed** issues (46 confirmed, 12 partially-right after verification), 2 refuted as false positives.

Baseline at review time: 433 tests pass · tsc clean · ruff `--select F` clean.

## Severity counts

| Severity | Count |
|---|---|
| High | 10 |
| Medium | 23 |
| Low | 25 |


## Triage update — 2026-07-04

All 58 findings re-verified against `main` (post PR #82 router split) by 6 parallel read-only
verification agents; per-finding verdicts are inlined under each heading below.

| Status | Count |
|---|---|
| ✅ Fixed | 28 |
| 🟡 Partially fixed | 7 |
| ❌ Still open | 23 |

Still-open findings cluster into three buckets:

- **Gated on the live-DB / multi-tenant workstream** (don't fix until that session):
  #18 #23 #25 #29 #34 (Postgres store parity/scoping) · #30 #31 (tenant identity from client headers).
- **Ungated backend correctness** — all seven fixed in PR #84 (plus the #3 residual):
  #14 (LLM retry) · #35 (approval idempotency) · #36 (outcome direction) · #37 (max_urgency default)
  · #38 (eval hallucination check) · #45 (measured_at ordering) · #46 (nan/inf CSV validation).
- **Frontend / duplication debt** (low severity):
  #21 #26 #48 #50 #54 #56 #57 #58 (+ partials #3 #11 #28 #32 #33 #43 #52).

## HIGH — fix before any multi-tenant / production exposure

### [bug] parse_context_csv silently drops the product_owner column
> **Triage 2026-07-04:** ✅ FIXED — contexts.py:344 parse_context_csv now sets product_owner=parse_optional(row.get("product_owner"))

**`apps/api/app/services/contexts.py:322-345`** · confidence 0.97

**Why:** `product_owner` is a declared recommended CSV column (line 32), a SQLite column, a completeness metric (line 48: ("product_owner", "Product owner", "routing", 1.0)), and a data-quality warning trigger (context_impact.py:351-368). But the CustomerContextRecord constructed in parse_context_csv never sets it, so the pydantic default None is used. Every CSV import via POST /customer-context/import-csv (main.py:712) loses product_owner even when the column is present and valid: the completeness report permanently shows 0% product_owner coverage with a warning the user cannot fix, and every problem gets a spurious 'missing product owners for routing' warning.

**Fix:** Add `product_owner=parse_optional(row.get("product_owner")),` after `owner=parse_optional(row.get("owner")),` in the CustomerContextRecord constructor in parse_context_csv (apps/api/app/services/contexts.py:342), and extend test_customer_context_csv_import to assert imported["product_owner"] == "onboarding_product" so the round-trip is pinned.

> _Verifier:_ Verified in code: parse_context_csv (apps/api/app/services/contexts.py:322-347) sets all 15 other declared CSV fields but omits product_owner, so the pydantic default None (domain/models.py:788) is used and the value is silently dropped on every CSV import via POST /customer-context/import-csv (main.py:712), which the frontend actually calls (apps/web/lib/client-api.ts:322). The column is declared as a recommended CSV field (contexts.py:32), a completeness metric with weight 1.0 (contexts.py:48), part of CORE_COMPLETE_FIELDS (contexts.py:60), and a full SQLite round-trip column (contexts.py:41

### [bug] classify_signals ignores category status, so merged/split (retired) categories keep winning classification
> **Triage 2026-07-04:** ✅ FIXED — taxonomies.py:459 classify_signals skips merged/split/proposed/rejected categories

**`apps/api/app/services/taxonomies.py:378-424 (with merge_categories 162-171, split_category 230-240)`** · confidence 0.85

**Why:** merge_categories/split_category retire source categories by setting status='merged'/'split' but keep them in catalog.categories WITH their original terms. classify_signals iterates all categories with no status filter, so retired categories continue to match. Worst case is split: the split source retains the full term list while each child gets only a subset, so the source matches at least as many signals as any child and stays the top classification forever — the user-facing split operation has no effect on classification, and the retired label keeps appearing in classifications/contradictory_evidence (via main.py:421 classify_candidate). Merged-away categories similarly reappear as contradictions against their own target.

**Fix:** In classify_signals (apps/api/app/services/taxonomies.py ~line 380), skip non-active categories: `for category in catalog.categories:` then `if category.status != "active": continue`. This is the only classification consumer (terms_for_category is only called from classify_signals; classify_candidate in main.py:421 goes through classify_signals), so no other scorer needs the filter. Add a test asserting that after a split/merge the retired source category no longer appears in candidate classifications or contradictory_evidence.

> _Verifier:_ Verified in apps/api/app/services/taxonomies.py: classify_signals (line 380) iterates catalog.categories with no status filter, and the only 'status' writes in the file are merge (line 166, status='merged') and split (line 233, status='split'), both of which retain the retired category with its original full terms list. TaxonomyCategory.status defaults to 'active' (domain/models.py) but no code anywhere in the app filters on it — grep found zero 'active' status checks in services/ or main.py. The sole caller (main.py:421 classify_candidate via taxonomy_store.list_catalogs()) applies no upstrea

### [bug] call_tool parses LLM tool-call arguments without guards; malformed JSON crashes callers that only catch AIProviderError
> **Triage 2026-07-04:** 🟡 PARTIAL — ai.py:218-225 guards malformed JSON/missing keys; empty-choices IndexError at ai.py:211 still unguarded

**`apps/api/app/services/ai.py:181-190`** · confidence 0.85

**Why:** Every caller (enrich_signals enrichment.py:109, synthesize_cluster synthesis.py:422, discover_themes semantic_taxonomy.py:249) deliberately catches AIProviderError to skip a failed batch/cluster and continue. But three failure modes here raise other exception types: (1) json.loads on truncated/malformed `arguments` raises json.JSONDecodeError (common when a model hits max output tokens mid tool call — the HTTP status is still 200), (2) `tool_calls[0]["function"]` / `["arguments"]` raises KeyError on nonstandard local-server responses (Ollama/vLLM compatibility is an explicit requirement), (3) `data.get("choices", [{}])[0]` raises IndexError if `choices` is an empty list. All escape the batch-skip handlers and abort the entire pipeline run instead of skipping one batch.

**Fix:** Wrap extraction: `try: arguments = tool_calls[0]["function"]["arguments"]; parsed = json.loads(arguments) except (KeyError, IndexError, TypeError, json.JSONDecodeError) as exc: raise NoStructuredResponseError(f"Malformed tool call from AI: {exc}") from exc`, and use `(data.get("choices") or [{}])[0]` for the choices access.

> _Verifier:_ All three failure modes verified in /Users/olamakri/Documents/CLARA/apps/api/app/services/ai.py:181-190: (1) json.loads(arguments) at line 190 has no guard and JSONDecodeError does not inherit from AIProviderError; (2) tool_calls[0]["function"]["arguments"] at line 189 can raise KeyError — the line-183 guard only checks tool_calls is non-empty, not its shape; (3) data.get("choices", [{}])[0] at line 182 raises IndexError when choices is an empty list, since the .get default only applies when the key is missing. All five call sites (enrichment.py:109, synthesis.py:422, semantic_taxonomy.py:139/

### [bug] Insight detail page silently substitutes sample data or 404s real problems on any API hiccup
> **Triage 2026-07-04:** ✅ FIXED — insights/[id]/page.tsx now "use client" via client-api with 404/error banners; lib/api.ts sample fallback opt-in

**`apps/web/lib/api.ts:26-37 (plus app/(dashboard)/insights/[id]/page.tsx:340-343)`** · confidence 0.88

**Why:** getActionQueueProblems fetches /problems then EVERY /problems/{id} in a Promise.all; if any single request fails (transient API restart, one bad record, NEXT_PUBLIC_API_URL unset on the server in prod — server components read this env at runtime, not the browser's), the catch returns fallbackProblems (hard-coded sample data). The detail page then does problems.find(id): a real problem_id won't match a sample ID, so notFound() renders a 404 for a problem that exists and is clickable from the /insights list (which fetches client-side and succeeds). Conversely if the route is visited with a sample ID, fabricated data renders with editors/approval panels and NO 'sample data' banner (unlike dashboard/actions pages which set usingFallback). Users will hit this: list works, detail 404s, no error surfaced.

**Fix:** In app/(dashboard)/insights/[id]/page.tsx, fetch `${apiUrl}/problems/${id}` directly (drop the list + N+1 fan-out); call notFound() only on an actual 404 response, and render an error state (or rethrow to an error boundary) on other failures instead of consuming the fallback-capable getActionQueueProblems. If sample-data fallback is kept for list views, return a usingFallback flag from lib/api.ts helpers and render the same banner dashboard/actions already use.

> _Verifier:_ Verified in code. lib/api.ts:26-37 wraps a /problems list fetch plus an N+1 Promise.all fan-out to /problems/{id} in a single bare catch that returns hard-coded fallbackProblems — any one of N+1 no-store requests failing substitutes the entire dataset. insights/[id]/page.tsx:340-343 then does problems.find(id) and notFound(), so a real problem_id 404s during any API hiccup, while the /insights list (a "use client" page fetching /problems in the browser with a single request) keeps working — the list-works/detail-404s divergence is real. Conversely, sample IDs (linked from dashboard/actions pag

### [data-integrity] Jira draft ID counter never resumes after restart: new drafts silently lost / overwritten
> **Triage 2026-07-04:** ✅ FIXED — postgres.py:612 _jira_draft_ids uses "JIRA-DRAFT" prefix so counter resumes

**`apps/api/app/services/postgres.py:500, 571-578`** · confidence 0.9

**Why:** Draft IDs are formatted 'JIRA-DRAFT-%04d' (workflow.py:396) but _next_id is called with prefix 'JIRA', so the regex '^JIRA-(\d+)$' never matches and the counter restarts at 1 after every process restart. The first approval that creates a Jira draft then produces draft_id 'JIRA-DRAFT-0001', which already exists in the in-memory list loaded by _load_records; record_approval's `if draft.draft_id not in before_drafts` check (line 571-578) therefore skips persisting the NEW draft entirely — it is returned to the client but never written to clara_workflow_records, and the in-memory list holds two records with the same ID. Any draft that does get through collides via ON CONFLICT (record_type, record_id) DO UPDATE and overwrites the older audit record. Audit-export data loss on the Postgres/production path.

**Fix:** In /Users/olamakri/Documents/CLARA/apps/api/app/services/postgres.py line 500, change to: self._jira_draft_ids = count(_next_id(jira_drafts, "draft_id", "JIRA-DRAFT") + 1). Optionally add a regression test that constructs PostgresWorkflowStore over existing jira_draft records and asserts the next generated draft_id does not collide. Longer term, switch draft IDs to uuid4 like outcome/closure records to eliminate counter-resumption bugs. (Note: drop the "overwrites older audit record" wording from the finding — colliding drafts are skipped before the upsert, never overwritten.)

> _Verifier:_ Verified in code and by direct regex test. postgres.py:500 passes prefix "JIRA" to _next_id, whose pattern '^JIRA-(\d+)$' (postgres.py:620-627) never matches the actual draft ID format 'JIRA-DRAFT-%04d' (workflow.py:396) — confirmed False via python re test — so the Jira draft counter restarts at 1 on every PostgresWorkflowStore init while DEC/EXE/TRN/CLR counters resume correctly. After a restart with persisted drafts, the next approved Jira action regenerates 'JIRA-DRAFT-0001', which is already in before_drafts (postgres.py:555), so the guard at postgres.py:571-578 skips persisting the NEW d

### [data-integrity] CSV fallback signal IDs are positional, so a second no-signal_id CSV import is silently dropped as duplicates
> **Triage 2026-07-04:** ✅ FIXED — signals.py:213 _fallback_signal_id is content sha256 (parse+validate both use it)

**`apps/api/app/services/signals.py:204-228 (213)`** · confidence 0.85

**Why:** parse_signal_csv assigns IDs CSV-0001, CSV-0002... by row position when the CSV has no signal_id column. Import a first file (rows become CSV-0001..CSV-0050), then import a *different* file also lacking signal_id: every row maps to the same CSV-000N IDs and both stores treat them as duplicates (SQLiteSignalStore catches IntegrityError, PostgresSignalStore skips via existing_ids), silently discarding all new feedback. Worse, validate_signal_csv only checks existing_signal_ids for rows that HAVE an explicit signal_id (line 158 `if signal_id:`), so the pre-import validation reports the file as fully importable — the /signals/import-csv endpoint returns 200 with skipped_duplicates=N and users lose their data without an error.

**Fix:** Make the fallback ID deterministic per-content rather than per-position: e.g. `signal_id=row.get("signal_id") or "CSV-" + sha256(f"{feedback_text}|{customer_id}|{timestamp}".encode()).hexdigest()[:12]`, preserving idempotent re-import of the same file while letting different files coexist. (A uuid4 fallback also fixes the data loss but would create duplicates when the same file is re-imported.) Additionally, make validate_signal_csv compute the same fallback ID for rows without an explicit signal_id and run it through the seen/existing checks, so the pre-import preview and the import agree.

> _Verifier:_ Verified at signals.py:213 — fallback IDs are positional (CSV-0001..N via enumerate), and all three store backends (in-memory SignalStore dict-skip at signals.py:562-567, SQLiteSignalStore IntegrityError-catch at signals.py:693-694, PostgresSignalStore existing_ids + ON CONFLICT DO NOTHING at postgres.py:294-314) dedupe purely on signal_id and silently count collisions as skipped_duplicates. The validation gap is also real: validate_signal_csv only checks existing_signal_ids inside `if signal_id:` (signals.py:158), so rows depending on the fallback are never flagged; a second no-signal_id CSV 

### [data-integrity] Eval harness scores missing enrichments as 100% correct (falls back to golden labels)
> **Triage 2026-07-04:** ✅ FIXED — harness.py:316-321 no golden fallback for missing enrichments

**`apps/api/app/evals/harness.py:311-318`** · confidence 0.92

**Why:** When a real LLM run is scored (enrichments passed by run_live._score_enrichment), any golden item with NO matching enrichment falls back to `golden_enrichment` itself, so it compares the golden labels against themselves and counts as correct for sentiment, urgency, tags, hallucination and PII. enrich_signals() (services/enrichment.py:106-115) silently drops entire failed batches, so a partially-failed run inflates the headline metrics written to report_<ts>.json and history.jsonl — the thesis evidence. Note the paired vectors in run_live.py:99 correctly use `by_id.get(g["id"], {})` (missing = wrong), so the McNemar A/B and the headline accuracies can silently disagree on the same run.

**Fix:** In run_enrichment_eval, branch on mode instead of falling back per item: `if enrichments is None: actual_enrichment = golden_enrichment` (self-compare mode) `else: actual_enrichment = next((e for e in enrichments if e.get("id") == item["id"]), {})` so a missing enrichment scores as wrong, matching run_live's vector logic. Also add a missing_enrichments count to EnrichmentEvalResult, and consider having enrich_signals surface how many batches were dropped (or having run_live compare len(enrichments) to len(golden)) so partial-failure runs are flagged in the report rather than silently averaged.

> _Verifier:_ Verified in code. harness.py run_enrichment_eval (lines 311-318) applies the golden-label fallback per-item, so when run_live._score_enrichment passes real enrichments, any golden item with no matching enrichment is scored golden-vs-golden and counts as correct for sentiment, urgency, tags, hallucination, and PII. enrich_signals (services/enrichment.py:95-115) swallows AIProviderError per batch and returns partial (or empty) results without raising, so a partially failed run silently inflates the headline metrics written to report_<ts>.json and history.jsonl; a fully failed run (all batches dr

### [data-integrity] CSV parser splits quoted multiline fields into separate corrupted rows
> **Triage 2026-07-04:** ✅ FIXED — csv.ts:43-90 single-pass quote-aware tokenizer across newlines

**`apps/web/lib/csv.ts:74-91 (parseCsv), 41-72 (parseCsvLine)`** · confidence 0.92

**Why:** parseCsv does `csvText.split(/\r?\n/)` BEFORE quote-aware parsing, then parses each line independently. A quoted cell containing a newline (extremely common in customer feedback text, and RFC-4180 legal — Zendesk/survey exports produce these routinely) is split mid-cell: the first fragment ends with an unbalanced quote, the remainder becomes one or more bogus extra rows with columns shifted. Because the signals import flow (app/(dashboard)/signals/page.tsx importMapped) only requires feedback_text to be mapped and toCanonicalSignalCsvWithDefaults silently fills every other column with defaults, these shifted fragments pass backend validation and are imported as separate garbage signals that feed candidate generation and triage. escapeCsvCell (line 104-107) correctly quotes newlines on output, so the writer and reader are asymmetric.

**Fix:** As proposed: replace the split-then-parse approach in parseCsv with a single-pass quote-aware tokenizer over the whole csvText (or track an open-quote flag across lines, joining continuation lines with "\n"), treating \r?\n as a row terminator only when not inside quotes. Additionally remove the pre-parse .map(trim).filter(Boolean) on lines (only skip fully empty records after tokenizing) so whitespace and blank lines inside quoted cells are preserved; keep per-cell trim if desired for unquoted cells only.

> _Verifier:_ Verified by executing an exact replica of parseCsv/parseCsvLine from apps/web/lib/csv.ts: a quoted multiline cell splits into corrupted rows with shifted columns because csvText.split(/\r?\n/) (lines 75-78) runs before quote-aware parsing (quote state is local to parseCsvLine). Downstream claim also holds: the signals import flow (app/(dashboard)/signals/page.tsx importMapped) requires only feedback_text to be mapped, toCanonicalSignalCsvWithDefaults fills all other columns with defaults, and backend validation (apps/api/app/services/signals.py, REQUIRED_SIGNAL_FIELDS = ["feedback_text"]) only

### [security] All GET data endpoints have no auth dependency — unauthenticated read of every workspace's problems, signals and customer PII
> **Triage 2026-07-04:** ✅ FIXED — all GET routes carry read_dep (routers/signals.py, problems.py, governance.py)

**`apps/api/app/main.py:553, 646, 672, 684, 723, 954`** · confidence 0.9

**Why:** Auth is enforced only per-route via require_role() on write endpoints; there is no global dependency on the FastAPI app (create_app builds FastAPI() at line 445 with only CORS middleware, no dependencies=[]). Every read route — list_problems (553), list_signals (646), list_journey_events (672), list_customer_context (684), list_policy_rules (723), get_outcome_board (954), list_approvals/executions/jira-drafts — is declared with NO Depends(get_current_user) and NO require_role. Signals and customer-context contain raw feedback_text, customer_id and account_id (PII). Even when AUTH_ENABLED is true (SUPABASE_URL set), an unauthenticated caller with just the API URL can GET /signals and /customer-context and read every tenant's customer data. This is an authorization bypass on the most sensitive data in the system.

**Fix:** Host all data routes on an APIRouter(dependencies=[Depends(get_current_user)]) and include it in create_app, keeping /health (and optionally /system-config) on the bare app; retain require_role on mutating/admin routes. Avoid putting dependencies=[Depends(get_current_user)] directly on FastAPI(...) as suggested, since that would also gate /health and break unauthenticated liveness probes once auth is enabled. Also add the missing auth to the two overlooked POST routes /signals/validate-csv (line 665) and /customer-context/validate-csv (line 714), and add an RBAC test asserting GET /signals and GET /customer-context return 401 without a token when auth is enabled.

> _Verifier:_ Verified in apps/api/app/main.py: create_app (line 445) builds FastAPI with only CORS middleware — no app-level dependencies, no router, no auth middleware. Every cited GET route (553 /problems, 646 /signals, 672 /journey-events, 684 /customer-context, 723 /policy-rules, 954 /outcome-board, plus /approvals 966, /executions 970, /jira-drafts 974, /workspace 993, /rules 1018, and POST validate-csv routes 665/714) has neither dependencies=[Depends(require_role(...))] nor a Depends(get_current_user) parameter — handler signatures take no user at all (e.g. `def list_signals() -> list[SignalRecord]`

### [security] Auth guard is client-only with no middleware; server-rendered pages expose data before the redirect can run
> **Triage 2026-07-04:** ✅ FIXED — dashboard pages all client components + API read auth; residual: no middleware.ts but no data leak

**`apps/web/components/auth/auth-guard.tsx:11-22 (plus app/(dashboard)/layout.tsx:8, lib/api.ts:17-24)`** · confidence 0.8

**Why:** AuthGuard checks localStorage in a useEffect and calls router.replace('/auth') only after hydration. There is no middleware.ts in apps/web (verified) and the token lives in localStorage, so the server can never enforce auth. Crucially, app/(dashboard)/insights/[id]/page.tsx is a SERVER component: getActionQueueProblems()/getPolicyRules() run on the server with no credentials and the fully rendered problem data (titles, evidence excerpts, customer/account IDs, action proposals) is embedded in the initial HTML/RSC flight payload that is served to ANY unauthenticated request for /insights/<id> — the client guard only hides it after the bytes have already been delivered (curl or view-source bypasses it entirely). The backend's dev-fallback is explicitly flagged with a fail-closed guard comment (apps/api/app/auth.py:35-43), but the web tier has no equivalent: with Supabase auth configured, the frontend still leaks all server-rendered content pre-auth.

**Fix:** Two layers are needed, and the API one is the real security boundary. (1) API: add auth to the read endpoints — e.g. a router/app-level `dependencies=[Depends(get_current_user)]` on the FastAPI app in apps/api/app/main.py (excluding /health), or per-route Depends on GET /problems, /problems/{id}, /policy-rules, /taxonomies, /terminology-dictionary, /emerging-problems etc. Without this, middleware on the web tier is cosmetic because the same data is directly curl-able from the API even with Supabase configured. (2) Web: either convert app/(dashboard)/insights/[id]/page.tsx to a client component fetching via lib/client-api.ts (which already attaches the Bearer token, lines 74-75) so no protected data is server-rendered without credentials, or adopt @supabase/ssr cookie sessions plus an apps/web/middleware.ts redirecting unauthenticated /(dashboard) requests to /auth. Note: once the API reads require auth, the current server-side lib/api.ts fetches will 401 and silently render fallback sample data for logged-in users too — so the page must be moved to authenticated client-side fetching (or SSR with the cookie-borne token) as part of the same change.

> _Verifier:_ Verified every link in the chain. (1) AuthGuard (components/auth/auth-guard.tsx:11-22) is a "use client" component gating via localStorage in useEffect — pure client-side UX, renders null only after hydration. (2) No middleware.ts exists anywhere in apps/web. (3) app/(dashboard)/insights/[id]/page.tsx is a server component (no "use client"; line 340 does `await Promise.all([getActionQueueProblems(), getPolicyRules()])`) using lib/api.ts, whose fetchJson (lines 17-24) sends no Authorization header. (4) The leak is real, and worse than framed: in apps/api/app/main.py, GET /problems (:553), GET /


## MEDIUM — real bugs & risks

### [bug] SQLite stores share one connection across FastAPI's threadpool with no lock; interleaved commits can persist partial approval writes
> **Triage 2026-07-04:** 🟡 PARTIAL — SerializedConnection (services/common.py:38-71) fixes cursor corruption; workflow.py record_approval multi-statement atomicity still open

**`apps/api/app/services/workflow.py:644-649, 796-904`** · confidence 0.7

**Why:** Every SQLite store (SQLiteWorkflowStore:648, SQLiteSignalStore signals.py:607, SQLiteProblemStore problems.py:138) opens a single shared connection with check_same_thread=False and no synchronization. FastAPI runs these sync endpoints on a threadpool, so two requests interleave on one connection/transaction. record_approval performs 3 inserts (approval, execution, jira draft) before its commit at line 902; a concurrent request's commit() (e.g. record_transition:789) commits whatever partial statements are pending, and if an exception occurs mid-sequence there is no rollback — the dangling approval row is committed later by an unrelated request, producing approvals without their execution/jira draft, or half-imported signal batches. Autocommit-mode isolation is whatever thread commits first.

**Fix:** Add a threading.Lock per SQLite store and wrap every write method (and multi-statement read-modify-write sequences) in `with self._lock, self._connection:` — the sqlite3 connection context manager commits on success and rolls back on exception, fixing both the interleaved-commit and missing-rollback problems. Apply to all 8 stores that share a connection (workflow, signals, problems, rules, journeys, workspace, contexts, learning_store). Alternative: open a short-lived connection per operation, mirroring the PostgresStore `with self._connect() as conn` pattern in postgres.py.

> _Verifier:_ Verified in code: all SQLite stores (SQLiteWorkflowStore workflow.py:648, SQLiteSignalStore signals.py:607, SQLiteProblemStore problems.py:138, and 5 more) share a single sqlite3 connection opened with check_same_thread=False; grep confirms zero threading.Lock usage and zero `with self._connection` / rollback anywhere in apps/api/app. Endpoints in main.py are sync `def` (e.g. record_approval at main.py:885), so FastAPI executes them concurrently on the anyio threadpool against the shared connection, which is an app-level singleton (main.py:472-473). The connection uses default legacy deferred 

### [bug] trend_label compares a 7-day count against a 30-day count without rate normalization — steady themes are labeled 'falling'
> **Triage 2026-07-04:** ✅ FIXED — frequency.py:155-157 per-day rate normalization before ratio

**`apps/api/app/services/frequency.py:95-154`** · confidence 0.88

**Why:** The windows have different lengths (7 days vs 30 days) but raw counts are compared. A perfectly steady stream (1 signal/day) gives recent=7, baseline=30, ratio 0.23 → 'falling'. To be labeled 'rising' a theme's daily rate must increase ~6.4x (recent 7-day count >= 1.5x the whole prior 30-day count). The docstring itself claims the baseline period is 'the same length' — the code contradicts it. This trend feeds every insight's frequency block (synthesis.py:476) and is shown to users, so rising themes are systematically reported as stable/falling.

**Fix:** In trend_label (apps/api/app/services/frequency.py), normalize counts to per-day rates before comparing: recent_rate = recent_count / recent_window_days; baseline_rate = baseline_count / baseline_window_days; if baseline_rate == 0 keep the existing "new"/"stable" handling; ratio = recent_rate / baseline_rate with the existing 1.5/0.5 thresholds. Keep the "new" branch (lines 145-146) unchanged. Add a test with a steady 1/day stream over ~40 days asserting "stable", and a burst case asserting "rising".

> _Verifier:_ Verified in frequency.py: recent window is 7 days (line 124), baseline is the prior 30 days (line 125), and lines 148-153 compare raw counts (ratio = recent_count / baseline_count) against 1.5/0.5 thresholds with no rate normalization. A steady 1-signal/day stream yields recent=7, baseline=30, ratio 0.23 → "falling"; "rising" requires ~6.4x rate increase. No ponytail marker or comment marks this as deliberate; tests (test_synthesis.py:312, :469) only check the label is in the allowed set or test the "new" branch, so nothing pins the raw-count comparison as intended. Impact scope confirmed: tre

### [bug] frequency_factors min()/max() over mixed naive and aware datetimes raises TypeError
> **Triage 2026-07-04:** ✅ FIXED — frequency.py:38 _parse_timestamp always returns aware UTC

**`apps/api/app/services/frequency.py:187-199`** · confidence 0.8

**Why:** _parse_timestamp returns an aware datetime for '...Z'/offset timestamps and a naive one for offset-less ISO strings. time_decayed_frequency and trend_label defensively `ts.replace(tzinfo=UTC)` per signal, but frequency_factors compares the raw parsed values directly. When a cluster mixes signals from a connector emitting 'Z' timestamps with one emitting naive timestamps (exactly the multi-source situation clustering is built for), `min()`/`max()` raises `TypeError: can't compare offset-naive and offset-aware datetimes`, which aborts synthesize_insights (synthesis.py:476) for the whole run.

**Fix:** In frequency_factors (frequency.py:190-193), normalize before appending, mirroring time_decayed_frequency: `ts = _signal_timestamp(signal); if ts is not None: timestamps.append(ts if ts.tzinfo else ts.replace(tzinfo=UTC))`. Alternatively normalize once inside _parse_timestamp (return aware UTC always), which would also simplify the duplicated per-callsite handling in time_decayed_frequency and trend_label.

> _Verifier:_ The bug is real exactly as described, and slightly easier to trigger than claimed. frequency.py:190-199 appends raw _parse_timestamp results and runs min()/max() without tz normalization, while the sibling functions time_decayed_frequency (lines 83-84) and trend_label (136-137) both defensively apply ts.replace(tzinfo=UTC) per signal — showing the codebase already anticipates naive timestamps. _parse_timestamp yields aware datetimes for 'Z'/offset strings and naive ones for offset-less ISO strings, and Python raises TypeError when ordering mixed naive/aware datetimes. Mixed input is realistic:

### [bug] No retry on rate-limited/transient LLM failures — whole enrichment batches silently dropped
> **Triage 2026-07-04:** ❌ OPEN — ai.py call_tool/embed still single HTTP attempt, no retry/backoff

**`apps/api/app/services/ai.py:117-203 (with enrichment.py 100-114)`** · confidence 0.7

**Why:** call_tool makes exactly one HTTP attempt; a 429 raises RateLimitError immediately. enrich_signals catches it and permanently skips the whole 25-signal batch, and synthesize_cluster drops the whole cluster. Rate limits are the most likely failure under exactly the burst pattern this pipeline generates (sequential batches with no pacing), so a single throttle event silently produces partially-enriched signal sets and missing insights with only a log warning — downstream clustering, severity, and eval metrics quietly degrade with no error surfaced to the caller.

**Fix:** In ai.py, wrap the HTTP call in call_tool and embed with a bounded retry (e.g. 3 attempts, exponential backoff, honor Retry-After when present) for status 429 and >=500 plus httpx.RequestError; keep other 4xx fail-fast. Additionally, fix the dead partial-enrichment check in triage_graph.py enrich_node: count signals where enrichment_map lacked an entry (e.g. `unenriched = sum(1 for it in items if it["id"] not in enrichment_map)`) instead of comparing len(enriched) < len(items), so partial enrichment is actually surfaced in state errors.

> _Verifier:_ Verified in code: call_tool (ai.py:163-179) and embed (ai.py:236-250) make exactly one HTTP attempt; 429 maps straight to RateLimitError (ai.py:109-114) and raises. enrich_signals (enrichment.py:109-113) catches AIProviderError and permanently skips the whole batch; synthesize_cluster (synthesis.py:422-423) drops the whole cluster. Repo-wide grep confirms no retry/backoff/pacing anywhere for AI calls, and batches run sequentially back-to-back. No "# ponytail:" marker covers this. The finding is actually understated in one respect: the enrich node in triage_graph.py (lines 93-111) pads un-enric

### [bug] Journey CSV import: non-numeric duration_seconds raises uncaught ValueError (HTTP 500), no validation pass exists
> **Triage 2026-07-04:** ✅ FIXED — journeys.py:43-50 _parse_duration catches ValueError/TypeError -> None

**`apps/api/app/services/journeys.py:44-61 (called from main.py:682)`** · confidence 0.85

**Why:** Unlike the customer-context CSV flow (which runs validate_context_csv and returns 422 before parsing), POST /journey-events/import-csv (main.py:682) calls parse_journey_event_csv directly. A single row with a non-numeric duration_seconds (e.g. '2.5s', 'n/a', '1,5' from a German locale export) raises ValueError from float(), which bubbles up as an unhandled 500 with no row information — for a user-supplied file upload path where malformed values are routine.

**Fix:** Prefer mirroring the existing pattern: add a validate_journey_event_csv pass (like validate_context_csv/validate_signal_csv) that collects per-row errors and have the endpoint return 422 with the report before calling parse_journey_event_csv. Minimal alternative inside parse_journey_event_csv: try: duration_value = float(duration) if duration else None; except ValueError: duration_value = None — but note this silently drops bad durations, so the 422-report approach is more consistent with the rest of the codebase.

> _Verifier:_ Reproduced directly: parse_journey_event_csv (journeys.py:45,57) calls float(duration) on the raw CSV cell and raises ValueError for non-numeric values like '2.5s'. The endpoint POST /journey-events/import-csv (main.py:680-682) invokes it with no try/except and no validation pass, unlike the sibling /signals/import-csv and /customer-context/import-csv flows which run validate_signal_csv / validate_context_csv and return 422 first. There is no app-level exception handler (no add_exception_handler in main.py; the except ValueError blocks at lines 354/752/etc. are local to other endpoints), so th

### [bug] enrich_node partial-failure detection is dead code and enrichment_count overcounts
> **Triage 2026-07-04:** ✅ FIXED — triage_graph.py:115 partial-failure detected via success < len(items); enrichment_count=success

**`apps/api/app/agents/triage_graph.py:93-118`** · confidence 0.95

**Why:** The else-branch appends a default record for every item without an enrichment, so `enriched` is ALWAYS the same length as `items` — `len(enriched) < len(items)` can never be true. The 'partial' error is unreachable, so when enrich_signals drops whole batches (its documented behaviour on AIProviderError) the pipeline reports zero errors, and `"enrichment_count": len(enriched)` claims every signal was enriched (surfaced as `enriched_count` by /triage/run, main.py:1212). A fully-failed LLM run looks identical to a fully-successful one in the response metadata.

**Fix:** In enrich_node (triage_graph.py): compute `matched = sum(1 for item in items if item["id"] in enrichment_map)`; replace the dead check with `if matched < len(items): errors.append(f"Enriched {matched}/{len(items)} signals (partial)")`; return `"enrichment_count": matched` (keeping enriched_signals as-is so downstream nodes still receive all signals). This matches the documented semantics in state.py:29 and existing tests still pass since their mocks enrich every signal.

> _Verifier:_ Verified at /Users/olamakri/Documents/CLARA/apps/api/app/agents/triage_graph.py:92-118. The for-loop appends a record for every item in both branches (merged enrichment or a default with "enriched": False), so len(enriched) == len(items) is an invariant and the partial-failure check `if len(enriched) < len(items)` at line 110 is unreachable dead code. The failure path is real: enrich_signals (services/enrichment.py:99-115) catches AIProviderError per batch and skips it ("Enrichment batch %d-%d failed, skipping"), returning fewer enrichments than inputs. In that case enrichment_map is missing e

### [bug] Integrations page ignores response.ok on save/delete/pull — failed saves look successful
> **Triage 2026-07-04:** ✅ FIXED — integrations/page.tsx save/delete/pull all check !res.ok and surface errors

**`apps/web/app/(dashboard)/integrations/page.tsx:100-121, 146-158`** · confidence 0.88

**Why:** saveConnector awaits the PUT but never checks response.ok; on a 4xx/5xx (invalid credentials shape, 401 from require_trusted_workflow_identity, validation error) it still closes the editor (setEditingConnector(null)) and reloads the list — the user's API token is silently discarded and the card shows its previous state with no error. deleteConnector likewise ignores failures. pullZendesk does `const data = await res.json(); alert(`Pulled ${data.pulled} signals`)` — on an error response data.pulled is undefined, so the user sees 'Pulled undefined signals from Zendesk' presented as success.

**Fix:** In saveConnector: `const res = await fetch(...); if (!res.ok) { const body = await res.json().catch(() => null); setTestResult(`error: ${body?.detail ?? res.status}`); return; }` before loadConnectors/setEditingConnector(null) (the existing testResult rendering at lines 220-224 will display it). In deleteConnector: wrap in try/catch and check res.ok, surfacing failure (e.g. alert with body.detail) instead of silently reloading. In pullZendesk: `if (!res.ok || typeof data.pulled !== "number") { alert(`Pull failed: ${data?.detail ?? res.status}`); return; }` — note FastAPI error bodies use `detail`, which matches.

> _Verifier:_ All three claims verified in apps/web/app/(dashboard)/integrations/page.tsx. saveConnector (lines 100-116) never checks res.ok and its catch is "// ignore"; on any HTTP error it still runs loadConnectors() and setEditingConnector(null), silently discarding the entered credentials. Error responses are realistic: the backend PUT /connectors/{type} (apps/api/app/main.py:1042) is guarded by require_role(Role.admin), so 401/403 are reachable (the finding names require_trusted_workflow_identity, but the actual guard is require_role(Role.admin) — same failure mode). deleteConnector (lines 118-121) ig

### [contract-drift] PostgresProblemStore drifts from SQLite contract: upsert overwrites existing problems and seed problems are freely editable/transitionable
> **Triage 2026-07-04:** ❌ OPEN — postgres.py upsert_problem ON CONFLICT DO UPDATE overwrites; no seed guard in update paths

**`apps/api/app/services/postgres.py:245-283`** · confidence 0.75

**Why:** SQLiteProblemStore.upsert_problem (problems.py:179-193) returns the existing record without overwriting, and update_problem/update_action_proposal/transition_problem_status return None for seed problems so main.py raises 409 'Only promoted draft problems can be edited' (main.py:585-589, 633-637). PostgresProblemStore has neither guard: upsert_problem clobbers the stored payload, and because seeds are persisted as ordinary rows at __init__ (lines 222-226), PATCH /problems/{seed_id} and POST /problems/{seed_id}/transitions succeed on Postgres while returning 409 on SQLite. Concretely, /problem-candidates/{id}/accept (main.py:858 upsert_problem) can reset a previously edited draft problem back to generated defaults on the Postgres backend (e.g. after the draft's journey/stage was renamed, which disables the duplicate guard), losing operator edits.

**Fix:** Mirror the SQLite semantics: keep the seed problem_id set on the instance and return None from update_problem/update_action_proposal/transition_problem_status for seeded IDs; make upsert_problem use INSERT ... ON CONFLICT DO NOTHING and return the existing record when the insert did not apply (RETURNING + fallback get_problem).

> _Verifier:_ Verified against the code. SQLiteProblemStore (problems.py:179-260) and the in-memory ProblemStore (problems.py:81-130) both make upsert_problem a no-op when the record exists and return None from update/transition for seed IDs, which main.py (585-589, 611-616, 633-637) converts to 409. PostgresProblemStore (postgres.py:245-283) diverges exactly as claimed: upsert uses ON CONFLICT DO UPDATE (overwrites payload) and update_problem/update_action_proposal/transition_problem_status have no seed guard, while seeds are persisted as ordinary rows in __init__ (postgres.py:222-226) — so PATCH/transitio

### [contract-drift] Approval interrupt can never be resumed — action/measure/learn nodes are unreachable in production
> **Triage 2026-07-04:** ✅ FIXED — shared MemorySaver graph + POST /triage/resume (routers/problems.py:617) closes the loop

**`apps/api/app/main.py:1197-1207 (with triage_graph.py:258-276)`** · confidence 0.85

**Why:** /triage/run builds a fresh per-request MemorySaver, invokes, and returns when the graph pauses at approval_node's interrupt() (triage_graph.py:261). The checkpointer is then garbage-collected and there is no endpoint anywhere that calls Command(resume=...) (grep finds zero resume/Command call sites). So whenever insights exist the graph permanently stops at the interrupt: action_node, measure_node and learn_node never run via the API, and the `connector_configs` carefully injected into state (main.py:1181-1184) are dead. Only the /connectors/test endpoint ever calls dest.push(). The endpoint docstring says approval is 'handled separately via the Actions page', but no code path executes approved actions through the connectors, so the documented ingest→…→action→measure→learn loop exists only in tests.

**Fix:** Either (a) persist the checkpointer (module-level or PostgresSaver per triage_graph.py's own docstring), return the thread_id from /triage/run, and add POST /triage/{thread_id}/resume that invokes Command(resume="approved"|"rejected"); or (b) accept the Actions-page workflow (POST /problems/{id}/approvals → ExecutionRecord/JiraIssueDraft) as the approval surface and close the real gap there: add an execution step that calls get_destination_for_action + dest.push() with the stored connector configs when an approval is recorded (turning draft_created into pushed), then remove the unreachable interrupt/action path from the production graph (or gate it behind the resume flow) and drop the dead connector_configs injection in /triage/run. Note the graph's measure/learn logic is partially duplicated by /problems/{id}/outcomes and /learning-conclusions — whichever option is chosen should consolidate rather than leave two half-loops.

> _Verifier:_ Verified in code: /triage/run (main.py:1197-1208) creates a fresh per-request MemorySaver with a one-off timestamp thread_id; when insights exist, approval_node's interrupt() (triage_graph.py:261) pauses the graph and invoke returns, after which the checkpointer is garbage-collected. Grep confirms Command(resume=...) exists ONLY in tests (test_triage_graph.py, test_outcome_learning_graph.py, test_connector_integration.py) — no endpoint can resume, so action_node/measure_node/learn_node are unreachable via the API and the connector_configs injected at main.py:1181-1184 'for the action node' are

### [contract-drift] Insights list fetch bypasses apiHeaders and renders failures as 'No insights yet'
> **Triage 2026-07-04:** ✅ FIXED — insights/page.tsx uses getProblems() with try/catch -> error banner

**`apps/web/app/(dashboard)/insights/page.tsx:18-21, 42-50`** · confidence 0.82

**Why:** Every other client call goes through requestJson/apiHeaders (lib/client-api.ts:65-93) which attaches x-tenant-id, x-actor-id and the Supabase Bearer token; this page does a bare `fetch(`${API_URL}/problems`)`. Today GET /problems happens to be unauthenticated server-side, but the moment read-side tenancy/auth is enforced (the direction the backend auth.py is clearly headed) this page breaks while its sibling pages keep working. Independently, the handler only sets state `if (res.ok)` and the catch swallows everything, so an API outage or 401 renders the 'No insights yet. Run the triage pipeline…' empty-state — actively misleading, and inconsistent with dashboard/actions/taxonomy which all show an 'API unreachable' banner.

**Fix:** In apps/web/app/(dashboard)/insights/page.tsx, replace the bare fetch with the shared client: import { getProblems } from "@/lib/client-api"; add a loadFailed state; in the effect do `getProblems().then(setProblems).catch(() => setLoadFailed(true)).finally(() => setLoading(false))`; and when loadFailed, render an "API unreachable" banner (matching the pattern in actions/page.tsx and taxonomy/page.tsx) instead of the "No insights yet" empty-state card.

> _Verifier:_ All claims verified against actual code. insights/page.tsx:18 is the only dashboard page calling the API without apiHeaders() (no x-tenant-id/x-actor-id/Bearer token); every sibling either uses the shared client-api functions or passes apiHeaders() to raw fetch. Backend GET /problems (main.py:553) currently has no auth dependency while write endpoints do, and auth.py explicitly describes the open state as a "Phase 0 transition" toward enforcement — so the forward-compat drift mechanism is real, not hypothetical hand-waving. The error-handling claim is also accurate: `if (res.ok)` plus a swallo

### [contract-drift] requestJson assumes error.detail is a string, but the backend returns structured objects/lists on 422 — users see "[object Object]"
> **Triage 2026-07-04:** ❌ OPEN — client-api.ts:91 error?.detail assumed string; no coercion for object/array detail

**`apps/api/app/main.py:656-663, 705-712`** · confidence 0.9

**Why:** The frontend error handler does `throw new Error(error?.detail ?? ...)` (apps/web/lib/client-api.ts:87-89), assuming detail is a string. The backend deliberately returns non-string detail: `raise HTTPException(status_code=422, detail=report.model_dump(mode="json"))` for CSV imports (main.py:661 and 710 — a full SignalValidationReport object), and every pydantic request-validation failure returns FastAPI's standard `detail: [{loc, msg, type}...]` list (e.g. draft-problem-editor.tsx:30-35 sends title/statement/owner unconditionally, so clearing a field hits ProblemUpdateRequest min_length=1 at models.py:433-437). `new Error(objectOrArray)` stringifies to "[object Object]", which is exactly what the UI renders via `error.message` in every panel's catch block. The structured validation report the backend goes out of its way to return is discarded.

**Fix:** In requestJson (apps/web/lib/client-api.ts:87-90): coerce detail by type — string as-is; array → detail.map(d => d.msg ?? JSON.stringify(d)).join("; "); other truthy object → JSON.stringify(detail); else fall back to `Request failed with status ${response.status}`. Optionally throw a custom ApiError carrying the raw detail so CSV panels can render the SignalValidationReport if the server-side re-validation race ever fires.

> _Verifier:_ client-api.ts:89 does `throw new Error(error?.detail ?? ...)` with no type check. FastAPI's standard 422 returns detail as a list of {loc,msg,type} objects, and this path is trivially reachable: draft-problem-editor.tsx:30-35 sends title/statement/owner unconditionally, so clearing a field violates ProblemUpdateRequest min_length=1 (models.py:433-437) and the catch block renders error.message = "[object Object]". The CSV mechanism (main.py:661/710 returning a full SignalValidationReport as detail) is also real but is normally pre-empted by the UI, which calls validate-csv first and only import

### [contract-drift] Zendesk "Pull Tickets" reads data.pulled without checking response.ok, and pulled signals are never persisted despite the UI implying ingestion
> **Triage 2026-07-04:** ✅ FIXED — integrations pull checks res.ok; backend persists pulled signals + returns counts

**`apps/api/app/main.py:1073-1101`** · confidence 0.85

**Why:** POST /connectors/zendesk/pull returns `{"pulled": n, "signals": [...]}` on success but `{detail: str}` with 400/502 on missing config or ConnectorError (main.py:1090-1099); it never calls signal_store.import_signals, so pulled tickets don't appear in /signals. The frontend (apps/web/app/(dashboard)/integrations/page.tsx:146-158) does `const data = await res.json(); alert(`Pulled ${data.pulled} signals from Zendesk`)` with no `res.ok` check — on any Zendesk auth/network failure the user sees the success-shaped alert "Pulled undefined signals from Zendesk", and even on success the message implies signals were imported when the API discarded all but a 10-item echo.

**Fix:** Frontend: check `res.ok` and surface `data.detail` on failure. Backend: either persist via `signal_store.import_signals(signals)` and return the SignalImportResult, or rename the response/UI copy to make clear it's a preview (e.g. return {previewed: n, sample: signals[:10]}).

> _Verifier:_ Verified both halves. Backend: apps/api/app/main.py:1073-1101 `pull_zendesk` returns {"pulled": len(signals), "signals": signals[:10]} and never calls signal_store.import_signals (grep confirms import_signals is only called from seed load, /signals/import, CSV import, and demo dataset load), so pulled tickets never reach /signals; errors are HTTPException 400/502 serialized as {"detail": str}. Frontend: apps/web/app/(dashboard)/integrations/page.tsx:146-158 has no res.ok check and fetch doesn't throw on HTTP errors, so on any 400/502 the user gets the success-shaped alert "Pulled undefined sig

### [data-integrity] PostgresWorkflowStore caches all records and ID counters in memory at startup; concurrent workers/replicas silently overwrite each other's audit records
> **Triage 2026-07-04:** ❌ OPEN — PostgresWorkflowStore still snapshots records + ID counters in memory at __init__

**`apps/api/app/services/postgres.py:448-502, 513-541, 553-579`** · confidence 0.8

**Why:** PostgresWorkflowStore loads every workflow record into instance lists once at construction and mints IDs from itertools.count seeded at that moment. With more than one process against the same DATABASE_URL (uvicorn --workers N, horizontal scaling, or even two dev instances), both processes mint the same DEC-000X / EXE-000X / TRN-000X IDs; _save_workflow_record uses ON CONFLICT ... DO UPDATE, so the second writer silently replaces the first writer's approval/execution/transition record — permanent loss of governance audit data with no error. Reads (list_approvals, state_for_problem, latest_learning_conclusion) also serve the stale startup snapshot, so decisions recorded by one worker are invisible to the others (dependency gating in assert_dependencies_satisfied then misfires). The Dockerfile currently runs one worker, so this is latent, but the class is explicitly the production Postgres counterpart.

**Fix:** Implement PostgresWorkflowStore reads as SQL queries per call (mirroring SQLiteWorkflowStore) instead of startup-loaded instance lists, and mint record IDs from a Postgres sequence or uuid4 (as learning conclusions and outcome records already do — note closure records currently do NOT; they use the counter-based CLR- scheme and need migrating too). At minimum, change _save_workflow_record for counter-ID record types (approval, execution, jira_draft, transition, closure) to ON CONFLICT DO NOTHING and raise on rowcount 0 so a cross-process ID collision surfaces as an error instead of silently overwriting audit records.

> _Verifier:_ All three mechanisms verified in code. (1) PostgresWorkflowStore (apps/api/app/services/postgres.py:448-502) loads every workflow record into inherited in-memory lists once at construction and seeds itertools.count ID generators (DEC/EXE/JIRA/TRN/CLR) from the max ID at that instant; the store is a per-process singleton (main.py:472, default_workflow_store at main.py:129-133). (2) Reads are inherited unchanged from WorkflowStore (workflow.py:313-323 return self._approvals etc.), and record_approval derives approved_action_ids from the stale in-memory list (workflow.py:354-360) before assert_de

### [data-integrity] Zendesk pull silently caps at the first page and never persists/consumes last_synced_at *(partial: severity/mechanism adjusted by verifier)*
> **Triage 2026-07-04:** ✅ FIXED — zendesk.py:88-137 paginates (next_page/after_url, MAX_PAGES); last_synced_at persisted via upsert_config

**`apps/api/app/connectors/zendesk.py:64-69, 119-124`** · confidence 0.88

**Why:** pull() issues exactly one GET and never follows `next_page` / `after_cursor` / `end_of_stream`, so any Zendesk workspace with >100 tickets (or >1000 on the incremental path) silently loses everything past page 1 — `pulled: 100` forever with no warning. Worse, the incremental path is unreachable in practice: `_sync_metadata` smuggled into signals[0] is never read anywhere (grep across apps/api/app finds no consumer; main.py:1073-1100 just returns the signals), so `config["last_synced_at"]` is never updated and every pull re-fetches the same first page. If a consumer ever imports these dicts verbatim, `_sync_metadata` also leaks into signal storage as a bogus field.

**Fix:** Paginate in pull(): for tickets.json follow data["next_page"] until null; for the incremental cursor endpoint loop on data["after_cursor"] until data["end_of_stream"] is true. Return sync metadata out-of-band (e.g. change the return to (signals, {"last_synced_at": latest}) or a wrapper dict) instead of injecting _sync_metadata into signals[0], and have POST /connectors/zendesk/pull persist last_synced_at back via connector_config_store.upsert_config when pulling from stored config. Also fix the module docstring, which currently claims last_synced_at is updated. Note this becomes higher priority the moment pulled signals are actually ingested into the signal store — currently the endpoint only returns a count and a 10-item preview.

> _Verifier:_ Every mechanism claim checks out: pull() in apps/api/app/connectors/zendesk.py makes exactly one GET and never follows next_page/after_cursor/end_of_stream (grep across connectors/ confirms zero pagination handling), so both the tickets.json path (100/page) and the incremental cursor path silently cap at page 1. The _sync_metadata dict smuggled into signals[0] (line 123) has no consumer anywhere in apps/api/app — the pull endpoint (main.py:1073-1101) returns {"pulled": N, "signals": signals[:10]} and never persists last_synced_at via upsert_config, so incremental sync is dead despite the docst

### [data-integrity] Postgres stores never filter by workspace_id and never set app.tenant_id — RLS is bypassed, giving cross-tenant data disclosure *(partial: severity/mechanism adjusted by verifier)*
> **Triage 2026-07-04:** ❌ OPEN — postgres reads unscoped by workspace_id; apply_tenant_to_connection has zero callers

**`apps/api/app/services/postgres.py:228-233, 287-292, 401-406, 514`** · confidence 0.85

**Why:** Every read in the Postgres stores is an unscoped 'SELECT payload FROM clara_* ORDER BY id' with no workspace_id predicate (list_problems 228-233, list_signals 287-292, list_context 401-406). The only tenant defense is RLS from migration 004, which relies on current_setting('app.tenant_id'). But auth.apply_tenant_to_connection() (apps/api/app/auth.py:148 — the function that would SET app.tenant_id from the authenticated UserContext) is never called anywhere in the codebase; app.tenant_id is only set inside _save_workflow_record (line 514) from the record's own tenant_id, never on read connections. Worse, migration 007's own header (lines 15-20) states the backend connects as the table OWNER (postgres), which has BYPASSRLS — so RLS never applies to the FastAPI path at all. Net result in a multi-tenant Supabase deployment: authenticated user in workspace A calling GET /problems receives every workspace's rows. The workspace_id extracted in get_current_user is used only for /workspace and rate limiting, never to scope data queries.

**Fix:** Treat as the tenant-isolation milestone plus hygiene fixes, not an emergency patch: (1) When implementing the milestone, thread UserContext.workspace_id into every store read/write (add WHERE workspace_id = %s; columns exist per migrations 004/006) or connect as a non-owner role and actually call apply_tenant_to_connection() per request so RLS engages. (2) Until then, make the single-tenant assumption fail-closed: reject or log JWTs carrying workspace_id != 1 in get_current_user, so a manually-provisioned second workspace cannot silently share data. (3) Fix the misleading auth.py module docstring ('Sets session-level Postgres settings... for RLS enforcement' — it never does) and either delete or wire up the dead apply_tenant_to_connection. (4) Update the stale ponytail at postgres.py:597 (workflow_records HAS tenant_id and RLS since migrations 002/004) so the documented ceiling matches reality. (5) Optionally attach the orphaned handle_new_user() trigger to auth.users only together with the milestone, since enabling per-user workspaces before app-level scoping exists is what would turn this into a real high-severity cross-tenant leak.

> _Verifier:_ Every mechanical claim verifies: Postgres store reads are unscoped (postgres.py ~228/287/401), apply_tenant_to_connection (auth.py:148) has zero callers, app.tenant_id is set only in _save_workflow_record (line 514, default 'legacy'), and migration 007's header confirms the backend connects as table owner so RLS never applies to the FastAPI path. However, the 'high / cross-tenant data disclosure' framing is overstated for two reasons. (1) This is the explicitly documented deferred ceiling: migration 006's header states 'Full per-tenant writes... are the deferred tenant-isolation milestone', an

### [data-integrity] Re-importing the same CSV duplicates every signal: generated signal_id uses a per-import timestamp batch ID
> **Triage 2026-07-04:** ❌ OPEN — signals/page.tsx:94 batchId=Date.now() -> re-import duplicates every signal

**`apps/web/app/(dashboard)/signals/page.tsx:87-88 (plus lib/csv.ts:133-137)`** · confidence 0.85

**Why:** Backend dedupe is keyed solely on signal_id (apps/api/app/services/signals.py:562-566: `if signal.signal_id in self._signals: skipped += 1`). When the user leaves the Signal ID column unmapped (the UI advertises 'only feedback text is required'), defaultSignalValue generates `csv-${batchId}-${rowIndex}` where batchId = Date.now().toString(36) — a fresh value on every import. Importing the same file twice (double-submit after a slow response, or a routine re-upload) therefore inserts a full second copy of every row; the reassuring 'skipped N duplicate(s)' message reports 0 and the duplicated signals inflate candidate counts, affected-customer numbers and triage output with no way to notice.

**Fix:** Derive generated signal_ids deterministically from the RAW source row, not the canonicalized one: the defaulted timestamp is new Date().toISOString() (csv.ts:165), which also varies per import and would defeat a hash of the canonical row. In toCanonicalSignalCsvWithDefaults, compute e.g. signal_id = `csv-${fnv1a(fileName + " " + sourceHeaders.map(h => row[h] ?? "").join(" "))}-${rowIndex}`; keep rowIndex in the ID so legitimately identical rows within one file are not silently collapsed, while a re-import of the same file reproduces the same IDs and the backend signal_id dedupe works as designed. Optionally also disable the Import button while status.tone === "busy" to prevent double-submit.

> _Verifier:_ Verified end to end. Backend dedupe is keyed solely on signal_id in both stores (apps/api/app/services/signals.py:562-567 in-memory check; SQLite signal_id PRIMARY KEY at line 615; validation preview at lines 175-184 also only checks signal_id). The frontend generates signal_id as `csv-${batchId}-${rowIndex}` (lib/csv.ts:136) with batchId = Date.now().toString(36) created fresh per import (signals/page.tsx:87), and this path fires whenever the signal_id column is unmapped OR a mapped cell is blank (csv.ts:179 uses `raw || default`) — and the UI explicitly advertises feedback_text as the only r

### [duplication] Direction-aware outcome_status/outcome_direction logic duplicated in workflow.py and outcome_engine.py
> **Triage 2026-07-04:** ❌ OPEN — workflow.py:188/192 duplicates outcome_engine.py:32/40 direction/status logic

**`apps/api/app/services/workflow.py:workflow.py:196-220; outcome_engine.py:32-70`** · confidence 0.9

**Why:** The core direction-aware outcome evaluation (not_measured/not_improved/improving/target_met) exists twice with identical logic but different keyword names (success_threshold vs target). outcome_engine.py:48 even documents itself as a 'Port of CLARA_2's outcome_status (workflow.py:68-88)'. Both copies are live in production paths: workflow.py's copy feeds the outcome board/snapshots (workflow.py:489), while outcome_engine's copy feeds the LangGraph triage pipeline (agents/triage_graph.py:407) and evals/simulate_outcomes.py. If thresholds or the improving/target_met semantics change in one copy, the outcome board and the triage/learning pipeline will silently disagree on whether an action worked — that discrepancy flows into learning conclusions. Currently in sync, so no live bug yet, but this is the highest-value drift risk found. outcome_engine.py:28 clamp01 also re-implements domain/scoring.py:58 clamp.

**Fix:** Delete outcome_direction/outcome_status from services/workflow.py and import them from services/outcome_engine (or move both into domain/, since they are pure functions with no I/O). Standardize on outcome_engine's keyword names (target, measured) and update ALL workflow.py call sites: 489/494 AND 1037/1042 (the finding cited only 209/489; line 209 is internal to the deleted function, and there is a second external call-site pair at 1037/1042). Replace clamp01 with `from app.domain.scoring import clamp` (defaults already 0.0/1.0), updating test_outcome_engine.py imports accordingly. Existing tests (test_outcome_engine.py, test_outcome_board.py) pin behavior on both sides and should pass unchanged.

> _Verifier:_ Verified: workflow.py:196-220 and outcome_engine.py:32-70 contain identical direction-aware outcome logic (same comparisons, same four statuses: not_measured/not_improved/improving/target_met), differing only in keyword names. outcome_engine.py:35/48 docstrings explicitly say "Port of CLARA_2's outcome_direction/outcome_status (workflow.py)". Both copies are live: workflow.py's copy is called at workflow.py:489/494 AND 1037/1042 (outcome board/snapshots, pinned by test_outcome_board.py); outcome_engine's copy is used by agents/triage_graph.py:407 and evals/simulate_outcomes.py (via measure_out

### [duplication] Legacy server-side API client lib/api.ts duplicates client-api.ts endpoints and has already diverged (no auth/tenant headers, silent sample-data fallback)
> **Triage 2026-07-04:** 🟡 PARTIAL — detail page now uses client-api (bug fixed); lib/api.ts remains as dead duplicate

**`apps/web/lib/api.ts:api.ts:17-77; client-api.ts:81-115, 236-242, 264`** · confidence 0.85

**Why:** lib/api.ts re-implements four endpoints that lib/client-api.ts already provides: getPolicyRules (client-api.ts:236), getTaxonomies (client-api.ts:240), getTerminologyDictionary (client-api.ts:264), and getActionQueueProblems ~= getProblems+getProblem (client-api.ts:109-115). The copies have diverged: api.ts's fetchJson sends no Authorization/x-tenant-id/x-actor-id headers (client-api.ts apiHeaders does, client-api.ts:65-79) and swallows every error by returning bundled sample data. Its only consumer is app/(dashboard)/insights/[id]/page.tsx:13,340 — so the insight detail page silently renders fake sample problems whenever the API errors or (once SUPABASE_JWT_SECRET auth is enforced, per apps/api/app/auth.py:7) always, while every other page shows real authenticated data. That is a real user-visible inconsistency waiting to fire.

**Fix:** Delete lib/api.ts (getTaxonomies/getTerminologyDictionary/getEmergingProblems there are already dead code). Port app/(dashboard)/insights/[id]/page.tsx to client-api's getProblems/getProblem/getPolicyRules and add an explicit page-level error/fallback state following the existing pattern in taxonomy/actions pages (visible "showing sample data" notice or error state). Note the insights page is a server component, so under enforced auth even client-api has no browser token server-side — the explicit error state is required, not optional (or convert the page to the client-side fetch pattern the other dashboard pages use).

> _Verifier:_ All load-bearing claims check out against the code. lib/api.ts:17-77 duplicates four client-api.ts endpoints (getPolicyRules:236, getTaxonomies:240, getTerminologyDictionary:264, getProblems/getProblem:109-115) and has diverged: its fetchJson sends no Authorization/x-tenant-id/x-actor-id headers (client-api's apiHeaders at 65-79 sends all three) and every function swallows errors into bundled sample data. Its only consumer is app/(dashboard)/insights/[id]/page.tsx (lines 13, 340). Three of its five exports (getTaxonomies, getTerminologyDictionary, getEmergingProblems) have zero importers — dea

### [duplication] Postgres import_signals/import_events dedup logic diverged from SQLite/in-memory stores — over-counts imports for in-batch duplicate IDs
> **Triage 2026-07-04:** ❌ OPEN — postgres import_signals/import_events over-count in-batch dupes after ON CONFLICT DO NOTHING

**`apps/api/app/services/postgres.py:postgres.py:294-314, 372-395; signals.py:559-573 (in-memory), 655-700 (SQLite)`** · confidence 0.8

**Why:** The import-with-dedup logic is implemented three times (in-memory SignalStore signals.py:559, SQLiteSignalStore signals.py:655, PostgresSignalStore postgres.py:294) and the Postgres copy has drifted: it snapshots existing_ids once before the loop and increments `imported` unconditionally after an ON CONFLICT DO NOTHING insert. If a CSV batch contains the same signal_id twice (parse_signal_csv at signals.py:200-228 does not dedupe, and auto-generated IDs come straight from the file), Postgres reports imported=2 for one stored row and computes skipped_duplicates=len(signals)-imported, while SQLite correctly reports imported=1/skipped=1 via IntegrityError. Same pattern in PostgresJourneyEventStore.import_events (postgres.py:372-395). Result: SignalImportResult counts shown to the user are wrong on the Postgres backend for in-batch duplicates — a live, if cosmetic, divergence caused by the copy.

**Fix:** In PostgresSignalStore.import_signals and PostgresJourneyEventStore.import_events (apps/api/app/services/postgres.py), count from the database's answer instead of assuming every attempted insert lands: use the cursor returned by conn.execute and add its rowcount (0 on conflict, 1 on insert) to `imported`, e.g. `cur = conn.execute("INSERT ... ON CONFLICT ... DO NOTHING", ...); imported += cur.rowcount`. Then skipped_duplicates = len(records) - imported is correct for both pre-existing and in-batch duplicates, and the loop's existing_ids pre-check becomes an optional optimization. Longer term, collapse the triplicated import-with-dedup semantics into one shared helper used by the in-memory, SQLite, and Postgres stores so the counting contract cannot drift again.

> _Verifier:_ Verified in code. PostgresSignalStore.import_signals (postgres.py:294-314) snapshots existing_signal_ids() once, never updates it during the loop, and increments `imported` unconditionally after INSERT ... ON CONFLICT (signal_id) DO NOTHING; signal_id is a PRIMARY KEY (postgres.py:57-62), so an in-batch duplicate's second insert is silently dropped yet still counted as imported, and skipped_duplicates = len(signals) - imported under-counts. PostgresJourneyEventStore.import_events (postgres.py:372-392) has the identical flaw. The in-memory store (signals.py:559-573, per-iteration dict check) an

### [security] Tenant identity is a verbatim, spoofable client header — cross-tenant read/write of learning conclusions and closure records
> **Triage 2026-07-04:** ❌ OPEN — pseudonymized_identifier returns client value verbatim; trusted headers unbound to JWT

**`apps/api/app/main.py:339-356, 889-901, 911-947`** · confidence 0.6

**Why:** pseudonymized_identifier (models.py:554-560) does NOT hash or verify — it returns the client-supplied string unchanged after a PII-pattern check. Tenant scoping for GET /problems/{id}/workflow, GET /outcome-board, POST closure and POST learning-conclusions is therefore controlled entirely by whatever x-tenant-id the caller sends (the web client hardcodes 'demo_tenant', client-api.ts:50). Any authenticated editor can read another tenant's learning conclusions and closure records, or write records into another tenant's partition, by sending that tenant's identifier; auth (Supabase get_current_user with workspace_id) exists but is never tied to these tenant headers. This is beyond the marked ponytail ceiling, which only defers DB-level RLS, not API-level tenant binding.

**Fix:** Resolve tenant_id server-side from the authenticated principal when AUTH_ENABLED (e.g. map UserContext.workspace_id or a tenant claim from app_metadata in get_current_user) and ignore/reject x-tenant-id in that mode, keeping the header path only for auth-disabled local dev. Additionally, add an auth dependency (at least require_role(Role.viewer) / get_current_user) to GET /problems/{id}/workflow and GET /outcome-board, which currently have no authentication at all, so the read path is not weaker than the write path.

> _Verifier:_ Verified in code: pseudonymized_identifier (domain/models.py:554-560) returns the client-supplied string unchanged after a PII-pattern check — no hashing or verification. require_trusted_workflow_identity (main.py:345-356) and the GET workflow/outcome-board handlers (main.py:889-901, 954+) derive tenant scope solely from the x-tenant-id header; workflow.py filters closure/learning records by that string verbatim. No upstream guard exists: create_app has no global auth dependency, require_role (rbac.py) checks only role, and get_current_user's JWT-derived workspace_id is never compared to the h

### [security] Tenant scoping driven by unauthenticated client-supplied x-tenant-id / x-actor-id headers *(partial: severity/mechanism adjusted by verifier)*
> **Triage 2026-07-04:** ❌ OPEN — trusted workflow identity still from client headers, no JWT binding (routers/problems.py:149-160)

**`apps/api/app/main.py:345-356, 889-901, 954-964`** · confidence 0.82

**Why:** require_trusted_workflow_identity (345-356) and the get_workflow_state (889-901) / get_outcome_board (954-964) handlers derive tenant_id purely from the x-tenant-id request header, not from the verified JWT (UserContext.workspace_id). The frontend sends this from a public build-time env var (apps/web/lib/client-api.ts:48-53, default 'demo_tenant'), so any caller can set x-tenant-id to an arbitrary value. Impact: (a) a user can read another tenant's learning conclusions / closure records by setting a different x-tenant-id on GET /problems/{id}/workflow and /outcome-board (these filter learning/closure records by the header value), and (b) POST /problems/{id}/closure and /learning-conclusions write records tagged with an attacker-chosen tenant_id, corrupting another tenant's audit trail. The 'trusted' naming is misleading — the header is fully client-controlled and unauthenticated.

**Fix:** When the multi-tenancy milestone lands (or now, as hardening): derive tenant and actor from the verified JWT instead of headers — in require_trusted_workflow_identity take user: UserContext = Depends(get_current_user) and use tenant_id = str(user.workspace_id) (matching UserContext.tenant_setting used for RLS) and actor_id = user.user_id/email; apply the same to the tenant filter in get_workflow_state and get_outcome_board; rename the dependency so 'trusted' is not applied to client-supplied headers. Also ensure _save_workflow_record's set_config('app.tenant_id', ...) uses the workspace-derived value so the clara_workflow_records RLS policy is keyed on authenticated identity, not a client string. Keep the x-tenant-id/x-actor-id headers only if needed for service-to-service calls behind a shared secret.

> _Verifier:_ The mechanism is accurately described: require_trusted_workflow_identity (apps/api/app/main.py:345-356) and the GET /problems/{id}/workflow (889-901) and /outcome-board (954-964) handlers take tenant_id straight from the client-controlled x-tenant-id header; pseudonymized_identifier (domain/models.py:554) only validates against PII patterns, it does not bind the value to any authenticated identity; and the frontend sends it from a public build-time env var defaulting to 'demo_tenant' (apps/web/lib/client-api.ts:48-53). The 'trusted' naming is indeed misleading. But 'high' severity assumes a mu

### [security] SSRF via connector base_url / subdomain fetched server-side, with response body reflected to caller
> **Triage 2026-07-04:** 🟡 PARTIAL — SSRF host access blocked (validate_external_url, zendesk subdomain regex); upstream resp.text[:300] still reflected to caller

**`apps/api/app/main.py:1073-1139`** · confidence 0.7

**Why:** POST /connectors/test/{connector_type} (1103) and /connectors/zendesk/pull (1073) pass an arbitrary client-supplied config dict straight to the connector, which builds a URL from it and issues a server-side HTTP request. Jira uses config['base_url'] verbatim: f"{base_url}/rest/api/3/issue" (jira.py:70) — an admin can set base_url to http://169.254.169.254/ or an internal service. Zendesk builds f"https://{subdomain}.zendesk.com/api/v2" (zendesk.py:60); a subdomain like 'internal-host/path?' yields host 'internal-host'. On error the connector raises ConnectorError with resp.text[:200-300] (jira.py:95, zendesk.py:102), and test_connector returns that message to the caller, so internal endpoint responses are exfiltrated. Gated behind require_role(admin), but in AUTH-disabled dev mode every caller is role=owner, and a compromised/over-privileged admin should still not be able to reach the cloud metadata endpoint.

**Fix:** Validate connector hosts before fetching. Jira: require config['base_url'] to have scheme https and a host ending in an allowlisted domain (e.g. .atlassian.net); reject anything else. Zendesk: require subdomain to match ^[a-z0-9][a-z0-9-]*$ (no '/', '?', '.', or '@'), which already blocks the injection since scheme is pinned to https. In both cases resolve the target host and reject private/link-local/loopback ranges (169.254.0.0/16, 10.0.0.0/8, 127.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16, ::1, fc00::/7) to defend against DNS-rebinding/pointed hostnames. Finally, do not echo raw upstream response bodies (resp.text) back to the API caller in ConnectorError — return a generic status/code and log details server-side.

> _Verifier:_ Verified in code. jira.py:70 builds url from fully client-controlled config['base_url'] (scheme included) and issues a server-side request; on non-2xx it raises ConnectorError with resp.text[:300] (jira.py:95). zendesk.py:60 builds the URL from config['subdomain']; a value like 'internal-host/path?' resolves host to 'internal-host', and errors reflect resp.text[:200] (zendesk.py:102). Both test_connector (main.py:1103) and pull_zendesk (main.py:1073) return str(exc) to the caller, so upstream response bodies are exfiltrated. Routes are gated by require_role(Role.admin) (rbac.py:43-66), but aut

### [security] Rate limiter is implemented but never applied to any route — LLM triage endpoint is unthrottled
> **Triage 2026-07-04:** 🟡 PARTIAL — rate_limiter now on /triage/run, /triage/resume, /ask; limit hardcoded to Plan.FREE (rate_limit.py:56)

**`apps/api/app/rate_limit.py:32-59`** · confidence 0.75

**Why:** rate_limiter is defined but a grep of the app shows it is referenced only in its own definition/docstring — it is not wired into any route via Depends. In particular POST /triage/run (main.py:1143), which invokes the full LangGraph LLM pipeline (graph.invoke at 1200) and thus incurs real provider cost/latency, is protected only by require_role(editor) with no rate limit. A single editor (or, in AUTH-disabled mode, anyone) can issue unbounded triage runs, enabling cost-exhaustion / DoS against the LLM provider. Separately, even where it were applied, line 49 hardcodes limit = RATE_LIMITS.get(Plan.FREE.value) so every workspace is capped at the free tier regardless of plan.

**Fix:** As proposed: add Depends(rate_limiter) to expensive routes (at minimum /triage/run, CSV import, connector pull/test), and replace the hardcoded FREE lookup at rate_limit.py:49 with the workspace's actual plan via BillingStore.get_subscription(user.workspace_id).plan. Note additionally that the limiter is in-memory/per-process (acknowledged in its own docstring), so a Redis-backed store is needed if the API is ever run multi-instance.

> _Verifier:_ Verified: rate_limiter (apps/api/app/rate_limit.py:32) is referenced nowhere in production code — only in test_saas.py:185, which constructs a synthetic FastAPI app to unit-test the dependency, not the real app wiring. main.py installs only CORSMiddleware (line 458) and no route uses Depends(rate_limiter). POST /triage/run (main.py:1143) is guarded solely by require_role(Role.editor) and invokes the LangGraph pipeline (graph.invoke at main.py:1200) whose enrich node calls the real LLM provider via httpx (app/services/ai.py), so unbounded requests incur real provider cost. In auth-disabled mode


## LOW — minor bugs, tech debt, duplication

### [bug] PostgresSignalStore.import_signals miscounts duplicates within the same batch
> **Triage 2026-07-04:** ❌ OPEN — PostgresSignalStore.import_signals snapshot ids + unconditional imported+=1 (postgres.py:381,395)

**`apps/api/app/services/postgres.py:294-314`** · confidence 0.8

**Why:** existing_ids is snapshotted once before the loop. If the same signal_id appears twice in one import request (which validate_signal_csv only guards for the CSV route, not POST /signals/import), the second row hits ON CONFLICT DO NOTHING — nothing is stored — yet `imported` is still incremented, so the returned SignalImportResult over-reports imported and under-reports skipped_duplicates. The in-memory and SQLite stores count the same case correctly (dict check / IntegrityError), so results differ per backend.

**Fix:** In PostgresSignalStore.import_signals, either add existing_ids.add(signal.signal_id) immediately after the conn.execute(...) insert, or use the cursor's rowcount (psycopg returns 0 when ON CONFLICT DO NOTHING suppresses the insert) / INSERT ... RETURNING signal_id, and only increment imported when the row was actually inserted.

> _Verifier:_ Verified at postgres.py:294-314: existing_ids is snapshotted once (line 295) and never updated in the loop, so a signal_id appearing twice in one batch passes the membership check on its second occurrence, the INSERT is silently absorbed by ON CONFLICT DO NOTHING, and imported is still incremented (line 309); skipped_duplicates = len(signals) - imported is correspondingly under-reported. The other two backends count this case correctly — in-memory SignalStore (signals.py:559-573) mutates its dict inside the loop, and SQLiteSignalStore (signals.py:653-702) catches sqlite3.IntegrityError per row

### [bug] Approval dependency gate uses cumulative historical approvals; a later rejection of a dependency does not revoke it, and repeat approvals mint duplicate executions
> **Triage 2026-07-04:** ❌ OPEN — record_approval cumulative historical approvals, no latest-per-action, no idempotency (workflow.py:382-414)

**`apps/api/app/services/workflow.py:127-144, 354-366, 802-813`** · confidence 0.55

**Why:** Approvals are append-only and record_approval accepts repeated decisions for the same action. If the governance action (the depends_on target for recovery/journey actions built in promote_candidate, signals.py:435/455) is approved and then a corrective 'rejected' decision is recorded, the approved-set query still contains the earlier approval, so dependent high-risk actions continue to pass assert_dependencies_satisfied against a dependency whose latest decision is rejected. Additionally, re-approving the same action creates a second ExecutionRecord and Jira draft each time (lines 843-900) with no idempotency guard.

**Fix:** Build approved_action_ids from the LATEST decision per action_id (e.g. `SELECT action_id, decision FROM approvals WHERE problem_id = ? ORDER BY id` and keep last, or a window query), and reject a new approval when the latest existing decision for that action is already 'approved'.

> _Verifier:_ Verified in both store implementations. WorkflowStore.record_approval (apps/api/app/services/workflow.py:355-360) and the SQLite store (lines 803-807) build approved_action_ids from ALL historical approvals with decision='approved' (append-only table, query `WHERE decision = ?` with no latest-per-action logic), so a later 'rejected' decision on a dependency never removes it from the approved set and assert_dependencies_satisfied (lines 127-144, called at 186-189) still passes for dependents. ApprovalDecisionStatus includes 'rejected' and 'needs_more_evidence' (domain/models.py:171-174), so the

### [bug] outcome_status ignores the contract's direction and misclassifies zero-baseline decrease metrics *(partial: severity/mechanism adjusted by verifier)*
> **Triage 2026-07-04:** ❌ OPEN — outcome_status ignores contract direction; zero-baseline decrease flips to increase/target_met (outcome_engine.py:37-58)

**`apps/api/app/services/outcome_engine.py:32-37, 58, 196-210`** · confidence 0.65

**Why:** measure_outcome passes the contract's explicit `direction` to resolution_score but outcome_status re-derives direction from baseline/target via `target >= baseline`. build_outcome_contract always sets direction='decrease' with target=0.0 and baseline=qual_signal_count. When baseline is 0 (a tag cluster made up entirely of quantitative signals — qual_signal_count is `sum(signal_type == 'qualitative')`), `target(0) >= baseline(0)` flips the derived direction to 'increase', so ANY recurrence (measured > 0 >= target) is reported as 'target_met' while resolution_score for the same measurement returns 0.5 — a self-contradictory outcome record that then feeds build_learning_from_conclusion confidence.

**Fix:** The reviewer's fix is correct: add `direction: str | None = None` to outcome_status; when provided, use it instead of outcome_direction(baseline, target), keeping derivation as fallback. Pass `direction=direction` from measure_outcome (outcome_engine.py:206-210). Additionally handle the baseline==0/target==0 decrease tie explicitly (measured<=0 → target_met, else not_improved) and add a regression test for a zero-baseline decrease contract asserting status="not_improved" and resolution_score=0.5 agree in polarity.

> _Verifier:_ Mechanism verified as described: outcome_status (outcome_engine.py:40-70) re-derives direction via `target >= baseline` (line 37) instead of using the contract's explicit `direction`, and build_outcome_contract always emits direction="decrease", target=0.0, baseline=qual_signal_count for tag metrics. When baseline==0, `0 >= 0` flips to the "increase" branch and any measured value returns "target_met" while resolution_score (honoring direction="decrease", baseline<=0, measured>0) returns 0.5 — a self-contradictory outcome that then maps to a "worked" conclusion with base_confidence 0.6 in build

### [bug] max_urgency reported as 'low' for signals ranked as 'medium' — inconsistent defaults in key vs read *(partial: severity/mechanism adjusted by verifier)*
> **Triage 2026-07-04:** ❌ OPEN — max_urgency argmax default mismatch medium-vs-low (synthesis.py:493-494)

**`apps/api/app/services/synthesis.py:491-494`** · confidence 0.8

**Why:** The selection key treats a signal missing 'urgency' as medium (rank 2), so such a signal can win the max over genuine 'low'-urgency signals; but the winner's urgency is then read with default 'low'. A cluster of [low, low, <missing>] reports max_urgency='low' even though the ranking treated the missing one as medium — and conversely masks that a medium-equivalent signal was ranked above explicit lows. The reported max_urgency on the insight is wrong whenever the argmax signal lacks the field.

**Fix:** Change the trailing read default to match the key: `max_urgency = max(sigs, key=lambda s: URGENCY_RANK.get(s.get("urgency") or "medium", 2)).get("urgency") or "medium"`. Using `or "medium"` (rather than a .get default) also covers the reachable degraded case where the key is present with value None (merge_enrichment_into_signal sets urgency: enrichment.get("urgency")), which the reviewer's proposed fix would still report as None.

> _Verifier:_ The inconsistency exists in the code text: at synthesis.py:491-494 the argmax key defaults missing 'urgency' to "medium" (rank 2) while the winner's urgency is read with default "low", and the sibling uses at lines 253-254 and 297-298 both use "medium", making line 494 the outlier. BUT the claimed impact is unreachable: every caller guarantees the 'urgency' key is present. The production path (triage_graph.py enrich_node, lines 93-107) either merges enrichment via merge_enrichment_into_signal (enrichment.py:134, always sets the key) or falls back to an explicit '"urgency": "medium"' (triage_gr

### [bug] check_hallucination false-flags tags composed only of short tokens even when literally present in the text
> **Triage 2026-07-04:** ❌ OPEN — check_hallucination only grounds tokens len>3 (evals/harness.py:214-219)

**`apps/api/app/evals/harness.py:207-221`** · confidence 0.75

**Why:** Grounding only counts tokens longer than 3 chars. A predicted tag like "bug", "app_bug" or "ux" has no token passing `len(part) > 3`, so an enrichment whose only tags are short-token tags is counted as a hallucination even when the word appears verbatim in the text (e.g. tags=["bug"] on "there is a bug in checkout"). This inflates hallucination_rate in run_live reports and deflates the `grounded` metric in real_data.py:109, which calls the same function on unconstrained real-world LLM tag output.

**Fix:** In check_hallucination (apps/api/app/evals/harness.py:212-215), ground short tokens via word-boundary match instead of excluding them: for each tag part, treat it as grounded if (len(part) > 3 and part in text_lower) or (len(part) <= 3 and re.search(rf"\b{re.escape(part)}\b", text_lower)). Consider skipping trivial stopword-like parts (e.g. "a", "of") to avoid the opposite failure of grounding everything, and add a test case pinning tags=["bug"] on text containing "bug" as not-hallucination.

> _Verifier:_ Verified by executing the actual function: check_hallucination({'tags': ['bug']}, 'there is a bug in checkout') returns True (flagged hallucination) even though the tag appears verbatim, because the grounding loop at harness.py:212-215 only tests tokens with len(part) > 3, and the fallback at 218-219 then returns True for any non-empty tag list. No refutation holds: tags are unconstrained free-form LLM output ("exactly 2 concise snake_case theme tags" in services/enrichment.py:29, no taxonomy), so short-token tags like "bug"/"ux"/"app_bug" are reachable; there is no upstream guard at either ca

### [bug] enrich_node crashes the whole graph if an LLM enrichment record omits 'id'
> **Triage 2026-07-04:** ✅ FIXED — enrich_node guards missing id (triage_graph.py:92)

**`apps/api/app/agents/triage_graph.py:91`** · confidence 0.65

**Why:** Every other consumer of enrich_signals output defensively uses `e.get("id")` (run_live.py:93, real_data.py:96, simulate_outcomes.py:92) because the LLM's tool output is not guaranteed to honour the JSON-schema `required` list. Only the production graph node uses `e["id"]` — a single malformed enrichment record raises KeyError inside the node, which aborts graph.invoke and turns /triage/run into a 500, killing the entire pipeline run instead of degrading like every other error path in this file.

**Fix:** In /Users/olamakri/Documents/CLARA/apps/api/app/agents/triage_graph.py:91, change to `enrichment_map = {e["id"]: e for e in enrichments if e.get("id")}`. Signals whose enrichment was dropped then automatically fall into the existing "pass through with defaults" branch, and the existing partial-enrichment error message at lines 110-111 already surfaces the degradation.

> _Verifier:_ Every element of the finding checks out. (1) /Users/olamakri/Documents/CLARA/apps/api/app/agents/triage_graph.py:91 is the only place in the codebase that does `e["id"]` on enrich_signals output; the three eval consumers all use `e.get("id")` (run_live.py:93 and :163, real_data.py:96, simulate_outcomes.py:92). (2) No upstream guard exists: enrich_signals (services/enrichment.py:107) just extends `result.get("enrichments", [])`, and call_tool (services/ai.py:190) returns `json.loads(arguments)` with zero schema validation — the tool schema's `required: ["id", ...]` is only a hint to the provide

### [bug] Clearing a numeric settings field silently persists 0 (Number('') === 0) *(partial: severity/mechanism adjusted by verifier)*
> **Triage 2026-07-04:** ✅ FIXED — settings numeric inputs guard empty string before Number() (settings/page.tsx:180-193)

**`apps/web/app/(dashboard)/settings/page.tsx:122, 132 (same pattern rules/page.tsx:142)`** · confidence 0.75

**Why:** The measurement-window and learning-half-life inputs do `update("measurement_window_days", Number(event.target.value))`. While retyping, the field is momentarily empty and Number('') is 0, so the state becomes 0; clicking either of the two Save buttons (both submit the whole settings object) persists measurement_window_days=0 / learning_half_life_days=0 with no validation, corrupting the outcome-measurement defaults workspace-wide. Same pattern on the rule priority input in rules/page.tsx:142.

**Fix:** Minor polish, not urgent: in settings/page.tsx use event.target.valueAsNumber and only commit finite positive values (e.g. `const n = event.target.valueAsNumber; if (Number.isFinite(n) && n > 0) update("measurement_window_days", n)`), or add min={1} plus a save()-time guard. Optionally add `Field(gt=0)` to WorkspaceSettings.measurement_window_days/learning_half_life_days in apps/api/app/domain/models.py for defense in depth. The rules/page.tsx priority input needs no change (0 is its documented default).

> _Verifier:_ The code pattern is real: settings/page.tsx:122,132 do Number(event.target.value), Number('')===0, and PUT /workspace (apps/api/app/main.py:1002) accepts it because WorkspaceSettings (domain/models.py:133-138) has plain `int` fields with no gt=0 constraint — so 0 can indeed be persisted with no validation anywhere. However the finding overstates both the silence and the impact: (1) the inputs are controlled, so clearing immediately re-renders the field showing "0" — the user sees the value before saving, it is not silent; (2) tracing all consumers shows workspace-level measurement_window_days/

### [bug] Dashboard 'partial data' notice never fires for connector HTTP errors
> **Triage 2026-07-04:** ✅ FIXED — getConnectors throws on !response.ok; dashboard records partial source (dashboard/page.tsx:259)

**`apps/web/app/(dashboard)/dashboard/page.tsx:205-209, 260-263`** · confidence 0.85

**Why:** getConnectors already swallows HTTP failures itself (`if (!response.ok) return [];`), so the `.catch(() => { partialSources.push("connectors"); return []; })` in the loader only runs on network-level throws. A 401/500 from /connectors yields an empty connector list with no 'Some data is unavailable (connectors)' banner, and the Connectors metric card confidently shows '0/0 Active integrations' as if none are configured — inconsistent with how approvals/executions failures are reported right next to it.

**Fix:** Route the connectors fetch through the existing requestJson helper by moving getConnectors into lib/client-api.ts (e.g. `export async function getConnectors(): Promise<ConnectorSummary[]> { return requestJson<ConnectorSummary[]>(`${apiBaseUrl()}/connectors`); }`) and importing it in page.tsx. This makes HTTP errors throw, so the existing .catch records "connectors" in partialSources, matching approvals/executions. (The reviewer's inline `throw new Error(String(response.status))` also works but duplicates requestJson.)

> _Verifier:_ Verified in code. getConnectors (page.tsx:205-209) returns [] on !response.ok, so the .catch at lines 260-263 that pushes "connectors" into partialSources only runs on network-level throws. By contrast, getApprovals/getExecutions use requestJson in lib/client-api.ts (lines 81-93), which throws on !response.ok, so their catches DO record HTTP failures. Result: a 401/500 from /connectors silently yields an empty list — no "Some data is unavailable (connectors)" banner (rendered at line 339) and the Connectors metric card shows 0/0 as if none are configured — exactly the inconsistency described. 

### [bug] Malformed access token is treated as an authenticated session
> **Triage 2026-07-04:** ✅ FIXED — isAuthenticated fails closed on malformed token (auth-client.ts:55)

**`apps/web/lib/auth-client.ts:48-56`** · confidence 0.7

**Why:** isAuthenticated returns true when decodeExp fails (`exp === null ? true : ...`): any garbage or truncated value under clara_access_token — e.g. written by an older build, corrupted, or a JWT without exp — passes the guard forever. The user then lands on the dashboard where every API call 401s (once backend auth is on) with no route back to /auth except manual sign-out; the ponytail comment on line 53-54 only covers skipping refresh for VALID expired tokens, not accepting undecodable ones.

**Fix:** Fail closed in isAuthenticated: `return exp !== null && exp * 1000 > Date.now();` — Supabase-issued access tokens always contain a numeric exp when auth is configured, so this rejects only structurally broken/legacy tokens. Optionally call signOut() (clear clara_access_token/clara_refresh_token) when decodeExp returns null so the stale value doesn't linger in localStorage. The finding's alternative of accepting any 3-part token is weaker and unnecessary.

> _Verifier:_ Verified against the actual code. decodeExp (auth-client.ts:37-46) returns null for any undecodable/truncated token, and isAuthenticated line 55 (`return exp === null ? true : exp * 1000 > Date.now()`) fails open on that null, so any garbage under clara_access_token passes AuthGuard (components/auth/auth-guard.tsx:14). The ponytail comment on lines 53-54 only covers skipping auto-refresh for valid expired tokens — it does not sanction accepting undecodable ones. Downstream: lib/client-api.ts forwards the raw localStorage string as Bearer and requestJson has no 401 handling (no auto sign-out/re

### [contract-drift] WorkspaceSettings.industry_profile exists on the backend but is missing from the TS type, DEFAULTS, and Settings UI; a save from defaults silently resets it *(partial: severity/mechanism adjusted by verifier)*
> **Triage 2026-07-04:** 🟡 PARTIAL — save-on-load reset guarded via workspaceLoadFailed; industry_profile still missing from TS type + DEFAULTS

**`apps/api/app/domain/models.py:133-141`** · confidence 0.85

**Why:** Backend WorkspaceSettings has `industry_profile: str = "default"` (models.py:141) and PUT /workspace (main.py:997-1006) stores the WHOLE validated payload (workspace.py put() replaces the JSON blob). The TS mirror `WorkspaceSettings` (apps/web/lib/types.ts:551-557) omits industry_profile entirely, and the Settings page builds a from-scratch `DEFAULTS: WorkspaceSettings` without it (apps/web/app/(dashboard)/settings/page.tsx:11-17) while swallowing GET failures (`getWorkspace().then(setSettings).catch(() => {})`, line 27). If the initial GET fails or the user clicks Save before it resolves, the PUT body lacks industry_profile, pydantic fills "default", and a configured industry profile is silently reset. Even in the happy path the UI can never display or edit the field the backend persists per workspace.

**Fix:** Add industry_profile: string to the TS WorkspaceSettings type (apps/web/lib/types.ts) and to DEFAULTS in apps/web/app/(dashboard)/settings/page.tsx ("default"), and gate the Save button until the initial GET /workspace resolves (this fixes the broader save-before-load bug that would reset ALL workspace settings, not just industry_profile). Rendering an industry-profile selector in the Settings UI is optional until the backend actually consumes the per-workspace value instead of env INDUSTRY_PROFILE.

> _Verifier:_ The drift facts are all accurate: backend WorkspaceSettings has industry_profile (models.py:141), the TS type (types.ts:551-557) and settings-page DEFAULTS omit it, PUT /workspace replaces the whole JSON blob (workspace.py put), and the page swallows GET failures with no save-guard. However, two parts of the mechanism are wrong or overstated. (1) The happy path DOES round-trip the field: TS types don't strip runtime JSON, so getWorkspace() returns industry_profile, setSettings stores it, update() spreads it, and updateWorkspace() serializes the full object — only the GET-failure/save-before-lo

### [contract-drift] Connector save/delete ignore HTTP status: admin-only endpoints fail silently for authenticated non-admin users (default JWT role is "viewer")
> **Triage 2026-07-04:** ✅ FIXED — connector save/delete/load check res.ok and surface detail (integrations/page.tsx:217,236,183)

**`apps/api/app/main.py:1042-1071`** · confidence 0.75

**Why:** PUT/DELETE /connectors/{type} require Role.admin (main.py:1042, 1066), and when Supabase auth is enabled a token without app_metadata.user_role defaults to "viewer" (apps/api/app/auth.py:142), so these calls return 403 `{detail: "Requires role 'admin'..."}`. The frontend saveConnector/deleteConnector (apps/web/app/(dashboard)/integrations/page.tsx:100-121) never check `res.ok` — fetch resolves on 403, the edit form closes, loadConnectors() re-renders the stale state, and the user gets zero feedback that the save was rejected (the catch block only fires on network errors and is an explicit `// ignore`). The connector still shows "Not configured" with no explanation.

**Fix:** In apps/web/app/(dashboard)/integrations/page.tsx, check res.ok in saveConnector and deleteConnector and surface (await res.json()).detail via the existing testResult/status UI instead of silently closing the editor. Note the same silent-403 applies to loadConnectors (GET /connectors is also admin-only): show an "admin role required" notice when the initial list load returns 403, rather than rendering everything as "Not configured". Optionally gate the Save/Delete controls on a role exposed to the client.

> _Verifier:_ Every link in the chain is real: PUT/DELETE /connectors/{type} are admin-gated (main.py, require_role(Role.admin)); rbac.py returns 403 for lower roles; auth.py defaults role to "viewer" when a Supabase JWT lacks app_metadata.user_role; and integrations/page.tsx saveConnector/deleteConnector never check res.ok — fetch resolves on 403, the catch block is an explicit "// ignore", the editor closes, and loadConnectors (which also silently drops its own 403, since GET /connectors is admin-only too) re-renders "Not configured" with no feedback. No frontend role gating exists (grep for role in apps/

### [data-integrity] Outcome upsert ignores measured_at ordering — a stale measurement posted late overwrites the latest value and flips outcome status *(partial: severity/mechanism adjusted by verifier)*
> **Triage 2026-07-04:** ❌ OPEN — record_outcome last-write-wins, no measured_at ordering guard (workflow.py:443,988-992)

**`apps/api/app/services/workflow.py:406-417, 906-934`** · confidence 0.6

**Why:** record_outcome unconditionally replaces the single outcome row/dict entry per problem with whatever the client sends, keyed only by problem_id. If a backfilled or retried measurement with an older measured_at arrives after a newer one (client-supplied timestamps are not validated against the stored row), latest_value regresses and outcome_status/outcome-board counts (target_met vs not_improved) and the learning-conclusion gate in main.py:936 are computed from stale data. Postgres path has the same last-write-wins behavior via _load_records keyed on problem_id ordered by created_at (insert time, not measured_at).

**Fix:** Prefer append-only semantics over a rejection guard: store each measurement as its own row (SQLite: drop the problem_id UNIQUE conflict target, or add a measurements history table; the Postgres workflow_records path already appends), and have outcome_snapshot select the row with max(measured_at) (parsing timestamps rather than comparing TEXT lexicographically). This keeps latest_value monotonic by measurement time while still allowing corrections (a corrected value with the same measured_at supersedes via insertion order tiebreak). If a minimal patch is wanted instead, apply the DO UPDATE ... WHERE excluded.measured_at >= outcomes.measured_at guard plus the dict-side comparison in WorkflowStore.record_outcome, but document that corrections must reuse or advance measured_at; do not claim this protects the learning-conclusion gate at main.py:936, which only checks measured vs not_measured and is unaffected.

> _Verifier:_ Core mechanism confirmed: all three paths are unconditional last-write-wins keyed on problem_id with client-supplied measured_at never validated — workflow.py:416 (dict assignment), workflow.py:915-932 (SQLite ON CONFLICT upsert), and postgres.py:581-593 + _load_records (454-495, reload ordered by created_at insert time, so last-inserted wins). No ponytail comment covers this, and no test pins out-of-order/overwrite behavior (test_workflow_api.py:266 posts a single measurement). A stale late-arriving measurement really can regress latest_value and flip outcome-board target_met/not_improved cou

### [data-integrity] CSV numeric validation accepts 'nan'/'inf' for account_value, poisoning financial-exposure sums *(partial: severity/mechanism adjusted by verifier)*
> **Triage 2026-07-04:** ❌ OPEN — validate_context_csv accepts nan/inf (no isfinite; contexts.py:277,291)

**`apps/api/app/services/contexts.py:270-298`** · confidence 0.7

**Why:** float('nan') and float('inf') parse successfully; `nan < 0` is False and `inf < 0` is False, so a row with account_value='nan' or 'inf' passes validate_context_csv, and pydantic's ge=0.0 accepts both (nan comparisons are skipped, inf >= 0 is True). Once imported, context_impact.summarize_context_impact's `sum(account_values.values())` becomes nan/inf, which propagates into total_account_value, the financial_exposure factor (nan comparisons make max()/min() unstable), and the impact score for every problem touching that account.

**Fix:** In validate_context_csv (contexts.py, after the float() parse at line 276), reject non-finite values: `if not math.isfinite(parsed_value): errors.append(SignalValidationIssue(severity="error", row_number=row_index, field=field, message=f"Row {row_index} has a non-numeric {field}."))` — applying it to both fields in the loop is harmless, but only account_value strictly needs it (the health_score 0..1 range check already rejects nan/inf). This closes both the 'inf' import (which saturates financial_exposure to 1.0 and inflates total_account_value/high_value_accounts) and the 'nan' inconsistency where validate-csv reports valid=True but import-csv then 500s on pydantic's ge=0.0 rejection.

> _Verifier:_ The validation gap is real: validate_context_csv (contexts.py:270-298) accepts account_value='nan'/'inf' because float() parses them and `parsed_value < 0` is False for both (health_score is NOT affected — `not 0 <= v <= 1` already rejects nan and inf). But the claimed downstream mechanism is wrong on two counts, verified empirically against the repo's pydantic 2.13.4: (1) Field(default=0.0, ge=0.0) on CustomerContextRecord.account_value (models.py:783) REJECTS nan (and -inf), so 'nan' never reaches the store or the sums — instead /customer-context/import-csv returns a confusing 500 (unhandled

### [data-integrity] Triage learnings load hardcodes workspace_id=1, leaking/using default-tenant learnings for every caller
> **Triage 2026-07-04:** ✅ FIXED — triage learnings load uses user.workspace_id via get_current_user (routers/problems.py:530,573)

**`apps/api/app/main.py:1192-1195`** · confidence 0.7

**Why:** run_triage_pipeline loads past learnings with default_learning_store().load(workspace_id=1) regardless of the authenticated user's workspace. In a multi-tenant deployment every tenant's triage run is seeded with workspace 1's learning conclusions (which feed synthesis/prompts), mixing one tenant's outcome data into another tenant's LLM context. Low severity because it degrades gracefully and only affects synthesis quality, but it is a real cross-tenant leak of learned content into prompts.

**Fix:** Add user: UserContext = Depends(get_current_user) to run_triage_pipeline and call default_learning_store().load(workspace_id=user.workspace_id). While there, note the same endpoint's signal_store.list_signals() and connector_config_store.list_configs() calls are also tenant-unscoped and should be workspace-filtered in the same pass.

> _Verifier:_ The code at apps/api/app/main.py:1193 does hardcode default_learning_store().load(workspace_id=1), and run_triage_pipeline never resolves the caller's workspace (only require_role(Role.editor), no get_current_user dependency). The nearby "# ponytail:" comment (lines 1189-1191) only marks the try/except graceful-degradation as deliberate, not the tenancy hardcode, so this is not a documented ceiling. Multi-tenancy is genuinely supported elsewhere (auth.py reads workspace_id from JWT app_metadata; SQLiteLearningStore is keyed by (workspace_id, conclusion_id); main.py:995/1006 use user.workspace_

### [data-integrity] Taxonomy rename/lock requests never send `actor`, so every governance change_history entry is attributed to the backend default "taxonomy_owner"
> **Triage 2026-07-04:** ❌ OPEN — taxonomy rename/lock actor still defaults to taxonomy_owner; client omits actor

**`apps/api/app/domain/models.py:100-109`** · confidence 0.8

**Why:** TaxonomyRenameRequest and TaxonomyLockRequest both default `actor: str = "taxonomy_owner"` (models.py:104, 109) and the endpoints pass it into change history (main.py:739-767). The frontend client (apps/web/lib/client-api.ts:244-262) sends only {category_id, label, description} / {category_id} — the TS body type doesn't even allow actor — while the app otherwise identifies the actor (x-actor-id header in trustedHeaders(), client-api.ts:48-53). Result: the taxonomy audit trail rendered on the taxonomy page (taxonomy/page.tsx:268-271) records the same placeholder actor for all edits, defeating the change-attribution purpose of change_history in a governance-oriented product.

**Fix:** Have the taxonomy rename/lock (and merge/split) endpoints take identity: TrustedWorkflowIdentity = Depends(require_trusted_workflow_identity) and pass actor=identity.actor_id to taxonomy_store, ignoring/removing the body actor field and its "taxonomy_owner" default in models.py — matching the existing pattern in record_closure (main.py:911-924) and record_outcome_learning (main.py:926-947). Update test_signal_api.py:165 accordingly.

> _Verifier:_ Verified end-to-end: models.py:104/109 default actor="taxonomy_owner"; main.py rename/lock endpoints pass request.actor into taxonomies.py _change() (lines 274-286) which stamps TaxonomyChange.actor; client-api.ts:245-262 body types omit actor and the taxonomy page call sites never pass it, so every UI-driven rename/lock is attributed to the placeholder. The backend already has the correct pattern — TrustedWorkflowIdentity from x-actor-id (main.py:340-356), used by closure (main.py:922) and learning-conclusion (main.py:946) endpoints — but taxonomy endpoints skip it even though the client send

### [duplication] formatMetric renders negative metric values as huge percentages (drifted copy of the fixed board version)
> **Triage 2026-07-04:** ✅ FIXED — single shared formatMetric with Math.abs(value)<1 (web lib/format.ts:11)

**`apps/web/app/components/outcome-measurement-panel.tsx:32-36`** · confidence 0.8

**Why:** This formatMetric uses `if (value < 1)` to decide percent formatting, so any negative observed value or threshold (e.g. a delta metric of -5, or -0.5 meaning '-0.5 days') renders as '-500%'/'-50%'. The same function in outcome-board-panel.tsx:21-25 was already corrected to `Math.abs(value) < 1`, so the two copies of this helper have diverged and the detail panel shows a different (wrong) number than the Learnings board for the same snapshot value.

**Fix:** Extract a single shared formatMetric (e.g. in apps/web/lib) using the `Math.abs(value) < 1` check and import it in both outcome-measurement-panel.tsx and outcome-board-panel.tsx; at minimum, change `value < 1` to `Math.abs(value) < 1` in outcome-measurement-panel.tsx:34.

> _Verifier:_ Verified: outcome-measurement-panel.tsx:32-36 uses `if (value < 1)` while outcome-board-panel.tsx:21-25 uses `Math.abs(value) < 1`. Negative values with |value| >= 1 (e.g. -5) render as "-500%" in the measurement panel but "-5" on the board. The path is reachable: formatMetric is called with snapshot?.latest_value (line 140), which comes from user-entered observed values checked only with Number.isFinite, so negatives are accepted. No ponytail marker or upstream guard exists. Minor nit: the finding's "-0.5 → -50%" example is not a divergence (both versions render that identically since Math.ab

### [duplication] Impact weights, band thresholds, and approval_pressure duplicated in frontend lib/scoring.ts + sample-data.ts — approval_pressure copy has already diverged *(partial: severity/mechanism adjusted by verifier)*
> **Triage 2026-07-04:** ❌ OPEN — lib/scoring.ts duplicates weights/bands; sample-data.ts approval_pressure mapping diverges

**`apps/web/lib/scoring.ts:scoring.ts:3-32; sample-data.ts:23-29; apps/api/app/domain/scoring.py:6-15, 84-100`** · confidence 0.85

**Why:** lib/scoring.ts copies the backend's _DEFAULT_WEIGHTS (domain/scoring.py:6-15) and impact_band thresholds 0.78/0.58/0.38 (scoring.py:84-91). The backend has since grown industry-profile and SCORING_WEIGHT_* env overrides (scoring.py:22-40), which the static TS copy can never reflect, so fallback-rendered scores/bands diverge from server-computed ones whenever a profile is active. Worse, sample-data.ts:23-29 re-implements approval_pressure (scoring.py:95-100) and is ALREADY wrong: the backend maps validation_required and review_required to "needs_review", the frontend copy maps them to "ready". Any sample problem in validation_required status renders with the wrong pressure badge in fallback mode. This only affects sample/fallback data paths, which caps the severity.

**Fix:** Align sample-data.ts approval_pressure with scoring.py:94-99 (treat approval_needed, review_required, and validation_required as needs_review). Better: precompute impact_score, impact_band, and approval_pressure into data/sample_problems.json (e.g. via the API's own serialization in a small script) and delete lib/scoring.ts plus the recompute in sample-data.ts, so the frontend never re-derives domain scoring.

> _Verifier:_ The duplication is real and unmarked (no ponytail comment): lib/scoring.ts copies _DEFAULT_WEIGHTS and the 0.78/0.58/0.38 band thresholds from domain/scoring.py, and the static TS copy cannot see the backend's industry-profile/SCORING_WEIGHT_* overrides (scoring.py:22-40). The approval_pressure re-implementation in sample-data.ts:24-29 has also genuinely drifted in logic: backend maps review_required and validation_required to needs_review (scoring.py:97), the TS copy maps them to ready. BUT the finding's concrete impact claim is overstated: data/sample_problems.json contains only two problems

### [duplication] API base URL fallback literal duplicated 9 times across web app; two pages bypass the shared client entirely
> **Triage 2026-07-04:** ✅ FIXED — API base URL single-sourced in client-api.ts:47 apiBaseUrl(); all pages route through it

**`apps/web/lib/client-api.ts:client-api.ts:44-46; api.ts:27,40,50,60,70; app/(dashboard)/insights/page.tsx:9,18; app/(dashboard)/integrations/page.tsx:13`** · confidence 0.9

**Why:** `process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"` is written out in 9 places despite client-api.ts:44 exporting apiBaseUrl(). Drift has already started: insights/page.tsx:18 fetches /problems with a raw fetch and NO apiHeaders(), so it sends no Authorization/x-tenant-id headers — duplicating getProblems (client-api.ts:109) minus auth. When Supabase auth is enforced this page's list breaks while dashboard/actions pages (which use getProblems) keep working. integrations/page.tsx at least uses apiHeaders but still re-declares the base URL and raw-fetches /connectors, duplicating the dashboard's connector fetch (dashboard/page.tsx:206).

**Fix:** As proposed, with corrected count (8 occurrences, not 9): replace the 7 duplicate literals with apiBaseUrl() from client-api.ts; switch insights/page.tsx to getProblems() from client-api.ts (or at minimum fetch(`${apiBaseUrl()}/problems`, { headers: apiHeaders() })); add getConnectors()/connector mutation helpers to client-api.ts and use them from both integrations/page.tsx and dashboard/page.tsx:206.

> _Verifier:_ All substantive claims verified against the code. The base-URL fallback literal appears in 8 places (finding says 9 — trivial overcount): client-api.ts:45 (canonical apiBaseUrl()), lib/api.ts:27/40/50/60/70, insights/page.tsx:9, integrations/page.tsx:13. insights/page.tsx:18 does raw-fetch /problems with no apiHeaders() (no Authorization/x-tenant-id), duplicating getProblems() minus headers; the finding correctly frames the breakage as conditional on future auth enforcement — today GET /problems in apps/api/app/main.py:553 has no dependencies= (only mutating endpoints use require_trusted_workf

### [duplication] utc_now() timestamp helper defined twice plus one inline copy
> **Triage 2026-07-04:** 🟡 PARTIAL — utc_now consolidated in services/common.py:10; inline Z-suffix copy remains at taxonomies.py:360

**`apps/api/app/services/workflow.py:workflow.py:37-38; signals.py:31-32; taxonomies.py:285`** · confidence 0.95

**Why:** Identical Z-suffixed ISO timestamp helper is defined in services/signals.py:31 and services/workflow.py:37, and the same expression is inlined at taxonomies.py:285 (changed_at=...). main.py:~112 imports utc_now from workflow while postgres.py:339 imports it from signals — two import paths for the same function. All timestamps in the system depend on this exact format ('Z' suffix); if one copy is ever changed (e.g. to keep +00:00 or add microsecond truncation), stored records would carry mixed formats that string-comparison-based ordering and retention logic consume.

**Fix:** Define utc_now() once (e.g. in app/domain/models.py alongside retention_expires_at, which already owns the Z-suffix format convention) and import it in signals.py, workflow.py, taxonomies.py (replacing the inline expression at line 285), postgres.py, emerging.py, and main.py. Delete the duplicate definitions in signals.py and workflow.py.

> _Verifier:_ Verified directly: identical utc_now() defined at services/signals.py:31-32 and services/workflow.py:37-38, and the same expression inlined at taxonomies.py:285. Import split confirmed — main.py:117 imports from workflow, postgres.py:337 (and also emerging.py:9, which the finding missed) import from signals. No '# ponytail:' marker excuses it. domain/models.py:530 round-trips the Z format back, so format drift between copies would indeed matter. Low severity is appropriate; no current runtime bug, just duplication/drift risk.

### [duplication] action_snapshot() defined identically in problems.py and workflow.py
> **Triage 2026-07-04:** ✅ FIXED — action_snapshot() single def in services/common.py:15, imported by workflow.py and problems.py

**`apps/api/app/services/problems.py:problems.py:35-36; workflow.py:93-94`** · confidence 0.9

**Why:** Byte-identical function in two service modules. Both copies are load-bearing: problems.py:55 uses it to capture original_snapshot before an edit, workflow.py:109/376/837 uses it for approval diffs and persisted approval snapshots. If snapshot semantics change (e.g. excluding a field, changing alias handling), updating one copy but not the other would make the approval diff (workflow.py action_diff) compare snapshots produced by different rules — the drift would surface as phantom or missing 'reviewer changed X' entries in the audit trail.

**Fix:** Keep one definition and import it in the other module, e.g. add `from app.services.problems import action_snapshot` to workflow.py and delete workflow.py:93-94 (no import cycle: problems.py only imports app.domain.*). Alternatively, hoist the helper to app/domain/models.py beside ActionProposal/ActionProposalSnapshot, which both services already import from.

> _Verifier:_ Verified byte-identical action_snapshot definitions at problems.py:35-36 and workflow.py:93-94, both load-bearing exactly as cited (problems.py:55 for original_snapshot capture; workflow.py:109/376/837 for approval diffs and persisted snapshots). No cross-import between the two modules exists, so the proposed single-import fix introduces no cycle. No ponytail marker excuses the duplication. The drift risk (diff/audit-trail comparing snapshots produced by divergent rules) is a real but hypothetical future hazard, so low severity is appropriate.

### [duplication] CLARA_DB_PATH / default SQLite path resolution duplicated with different parent-offset arithmetic
> **Triage 2026-07-04:** ❌ OPEN — default_db_path dup: main.py:82 (parents[1]) vs evals/simulate_outcomes.py:66 (parents[2])

**`apps/api/app/main.py:main.py:121-126; evals/simulate_outcomes.py:60-66`** · confidence 0.9

**Why:** Both functions resolve the same env var (CLARA_DB_PATH) and the same target file (apps/api/.data/clara.db) but each hard-codes a different parents[N] offset relative to its own file location. Today both land on apps/api/.data/clara.db, but the duplication is fragile: moving either file, or changing the data-dir name in one place, silently splits the API and the outcome-simulation eval onto two different databases — the eval would then measure/write outcomes against a DB the API never reads, which is exactly the class of bug that is hard to notice (everything 'works', numbers are just wrong).

**Fix:** Move default_db_path() into a shared module (e.g. app/services/db.py or next to database_url() in app/services/postgres.py) anchored once relative to the package root (`Path(__file__).resolve().parents[N]` computed in one file only), and import it from main.py and evals/simulate_outcomes.py. The 8 near-identical default_*_store() wrappers in main.py:128-190 could also collapse into one `pick_store(sqlite_cls, pg_cls, *args)` helper while touching this code.

> _Verifier:_ Verified both cited functions. main.py:121-126 default_db_path() uses parents[1] from apps/api/app/main.py and simulate_outcomes.py:60-66 _default_db_path() uses parents[2] from apps/api/app/evals/simulate_outcomes.py; both read CLARA_DB_PATH and both currently resolve to apps/api/.data/clara.db. These are the only two occurrences in the codebase (grep confirmed). No ponytail marker excuses it — the eval's docstring merely asserts it matches the API path, which is an unenforced implicit contract, and no test pins the two paths to be equal. The eval cannot import from main.py without triggering

### [duplication] percent() formatting helper copy-pasted into 7 components with one already-drifted signature
> **Triage 2026-07-04:** ✅ FIXED — percent() single shared export in web lib/format.ts:5

**`apps/web/app/components/evidence-panel.tsx:evidence-panel.tsx:3; outcome-board-panel.tsx:27; customer-context-panel.tsx:62; signal-intake-panel.tsx:51; affected-context-panel.tsx:22; app/(dashboard)/insights/[id]/page.tsx:24; app/(dashboard)/dashboard/page.tsx:61`** · confidence 0.95

**Why:** The identical percent formatter is declared in 7 files; the insights/[id] copy has already drifted to `(value: number | undefined)` with a `?? 0` default. Cosmetic-only today, but any change to rounding/precision (e.g. one decimal place for impact scores) now requires 7 coordinated edits, and the drifted variant shows how copies mutate independently. lib/utils.ts (6 lines) is the obvious existing home.

**Fix:** Export `export function percent(value: number | null | undefined): string { return `${Math.round((value ?? 0) * 100)}%`; }` from apps/web/lib/utils.ts, import it in all 7 files, and delete the local copies. The widened signature is a superset of both existing variants, so all call sites remain type-safe.

> _Verifier:_ Grep verifies all 7 cited declarations exist exactly as claimed: 6 identical `function percent(value: number): string { return `${Math.round(value * 100)}%`; }` copies (evidence-panel.tsx:3, outcome-board-panel.tsx:27, customer-context-panel.tsx:62, signal-intake-panel.tsx:51, affected-context-panel.tsx:22, dashboard/page.tsx:61) and one drifted variant in app/(dashboard)/insights/[id]/page.tsx:24 taking `number | undefined` with a `?? 0` default — the drift is real and matches the finding's description. apps/web/lib/utils.ts currently contains only the 6-line `cn()` helper, so the proposed co

### [duplication] Outcome status label map and outcome-direction logic re-declared across web components *(partial: severity/mechanism adjusted by verifier)*
> **Triage 2026-07-04:** ❌ OPEN — outcomeLabels maps still duplicated (outcome-board-panel vs outcome-measurement-panel); dashboard re-implements direction rule

**`apps/web/app/components/outcome-board-panel.tsx:outcome-board-panel.tsx:12-18; outcome-measurement-panel.tsx:17-22; app/(dashboard)/dashboard/page.tsx:103`** · confidence 0.85

**Why:** The outcome_status -> display-label map is duplicated in outcome-board-panel.tsx and outcome-measurement-panel.tsx (keyed off two different types, OutcomeBoardItem["outcome_status"] and OutcomeSnapshot["status"], so adding a status on the backend requires finding both). dashboard/page.tsx:103 additionally re-implements the backend's outcome_direction rule (workflow.py:196, outcome_engine.py:32) inside its fallback OutcomeBoard builder — a third copy of that rule across the codebase, in a second language. If the direction rule ever changes server-side (e.g. explicit improvement_direction field takes precedence), the dashboard fallback silently disagrees.

**Fix:** Extract the shared label map once, e.g. `export const outcomeStatusLabels: Record<OutcomeSnapshot["status"], string>` in apps/web/lib/types.ts (or a lib/labels.ts), and import it in both outcome-board-panel.tsx and outcome-measurement-panel.tsx. For the direction rule, add a small helper in apps/web/lib (e.g. `outcomeDirection(baseline: number, successThreshold: number): "increase" | "decrease"` mirroring workflow.py:197) and use it in fallbackOutcomeBoard() at dashboard/page.tsx:103 — do NOT try to read improvement_direction from the API there, since that code path only executes when the API is unreachable and neither OutcomeContract nor the sample data carries the field.

> _Verifier:_ The duplication itself is real: identical outcomeLabels maps exist at outcome-board-panel.tsx:14-19 and outcome-measurement-panel.tsx:17-22, and dashboard/page.tsx:103 re-implements the backend direction rule from workflow.py:197. But two parts of the finding are wrong. (1) The label maps are NOT keyed off two independent types — types.ts:461 defines OutcomeBoardItem["outcome_status"] as OutcomeSnapshot["status"], so both Record maps share one union and adding a backend status triggers compile errors in both files; the "requires finding both" drift mechanism is refuted by TS exhaustiveness. (2

### [duplication] Canonical signal CSV column list duplicated between backend KNOWN_SIGNAL_COLUMNS and frontend signalCsvFields
> **Triage 2026-07-04:** ❌ OPEN — signalCsvFields (web csv.ts:1) and KNOWN_SIGNAL_COLUMNS (api signals.py:75) still independent copies

**`apps/web/lib/csv.ts:csv.ts:1-13; apps/api/app/services/signals.py:76-90`** · confidence 0.7

**Why:** The 11 canonical signal CSV columns exist as independent constants on both sides of the wire. This goes beyond the stated types.ts-mirrors-models convention: the frontend uses signalCsvFields to build/remap the CSV it POSTs to /signals/import-csv (toCanonicalSignalCsv), and the backend uses KNOWN_SIGNAL_COLUMNS to decide which columns become SignalRecord fields vs. metadata (signals.py:209). Currently identical, but adding a canonical column on the backend without updating csv.ts means the frontend mapper demotes it to an unmapped column and the value lands in metadata instead of the typed field — a silent contract break with no error anywhere.

**Fix:** Single-source the list: either generate a small shared JSON (e.g. data/signal_csv_columns.json imported by both signals.py and csv.ts, matching how sample_*.json is already shared), or add a backend test that fetches the frontend list and asserts equality so CI catches desync. At minimum add a cross-reference comment on both constants naming the counterpart file/line.

> _Verifier:_ Verified against actual code: apps/web/lib/csv.ts:1-13 (signalCsvFields) and apps/api/app/services/signals.py:76-90 (KNOWN_SIGNAL_COLUMNS) are two independent, currently-identical 11-name copies of the canonical signal CSV contract, with no ponytail marker, no cross-reference comment, no shared source, and no test on either side pinning them together. Both are load-bearing: the frontend builds the POSTed CSV and mapping UI from its copy (toCanonicalSignalCsv in signal-intake-panel.tsx:312, toCanonicalSignalCsvWithDefaults in signals/page.tsx:88), the backend uses its copy at signals.py:209 to 

### [security] Supabase access + refresh tokens stored in localStorage (XSS-exfiltratable) *(partial: severity/mechanism adjusted by verifier)*
> **Triage 2026-07-04:** ❌ OPEN — auth-client.ts still stores access+refresh tokens in localStorage; refresh token never read

**`apps/web/lib/auth-client.ts:25-28, 50`** · confidence 0.6

**Why:** signIn writes the Supabase access_token and refresh_token to window.localStorage (25-28) and client-api.ts:59 reads the access token from localStorage to attach as the Bearer header. localStorage is readable by any JavaScript running on the origin, so any XSS (including a compromised npm dependency) can exfiltrate both the access token and the long-lived refresh_token, enabling full account takeover that survives page reloads. Refresh tokens in particular should never be JS-readable.

**Fix:** Stop persisting the refresh token entirely: delete the REFRESH_KEY constant and lines 26-28 in apps/web/lib/auth-client.ts (and the corresponding removeItem in signOut). Nothing in the codebase reads it, and the ponytail-documented design already accepts re-authentication when the ~1h access token expires, so this is a zero-cost hardening change. If longer sessions are ever added, implement refresh rotation server-side or via httpOnly cookies at that point rather than pre-storing the token in JS-readable storage.

> _Verifier:_ The code claim is factually accurate: apps/web/lib/auth-client.ts:25-28 stores both access_token and refresh_token in localStorage, and apps/web/lib/client-api.ts:59 reads the access token for the Bearer header. Grep confirms the refresh token is never read anywhere — only written on signIn and removed on signOut — and the "# ponytail:" comment at auth-client.ts:53-54 marks the no-auto-refresh, re-auth-on-expiry session model as deliberate. So the stored refresh token is pure dead risk with zero benefit. However, "medium" overstates severity: (1) localStorage session storage (including refresh


## Refuted (false positives — no action)

- **RLS on clara_workflow_records is either inert (owner role) or breaks _load_records (non-owner), since reads never set app.tenant_id** — The finding assumes the RLS on clara_workflow_records is meant to constrain the backend's own connection and is therefore either inert or breaking. Both prongs fail. (a) "Inert/false assurance": migra
- **discover_themes maps clusters back to the wrong signals when any unmapped signal has empty text** — The claimed trigger condition is unreachable. The only definition of unmapped_signals() (apps/api/migrations/003_pgvector_taxonomy.sql lines 143-163, not redefined in any later migration) filters with
