# CLARA — Feature Catalog & Design Rationale

_A complete inventory of what the platform does, why each piece is built the way it is (versus the
alternatives), and where it should go next. Verified against the codebase on main, 18 Jul 2026._

CLARA closes the **Signal → Insight → Action → Learning** loop for customer feedback, with
Responsible-AI governance built into the loop rather than bolted on. Everything below serves one of
those four stages or the trust layer around them.

---

## A · Signal: getting feedback in, safely

### 1. Multi-source signal ingestion
Ingests customer feedback as normalized "signals" from CSV upload, REST API, and pull/push
connectors, with language detection (EN/DE) and workspace scoping on every row.
**Why this approach:** a single normalized signal schema (id, text, source, language, metadata)
means every downstream stage — enrichment, clustering, severity, export — is source-agnostic; new
sources are a connector, not a schema migration. The alternative (per-source pipelines, as many
listening tools do) multiplies every later feature by the number of sources. Costs accepted:
source-specific richness (e.g. star ratings) lives in metadata rather than first-class columns.

### 2. Connector suite (Trustpilot, Zendesk, Jira, Slack, App Store, Google Play, Google Business)
Pull-connectors fetch the customer's own feedback (reviews, tickets) on schedule; push-connectors
(Jira, Slack) execute approved actions. All are configured per-workspace through a connector config
store.
**Why this approach:** strictly **"own-presence listening"** — the Trustpilot connector uses the
customer's own API key and pseudonymizes reviewer names at ingestion; the product never scrapes.
The alternative — scrape-everything social listening — is what most competitors do and is exactly
what a GDPR/ToS-conscious EU mid-market buyer cannot sign off. This stance costs coverage (you see
only what the customer owns or what platforms serve publicly) and is also a sales asset: the
documented legitimate-interest basis is part of the compliance pack.

### 3. Encrypted connector secrets (Fernet, `enc:v1:`)
Connector API keys are sealed with a workspace-level Fernet key before storage and fail loudly if
the encryption key is absent.
**Why:** secrets in plaintext jsonb are the default failure mode of "config in the DB" designs; a
marker-prefixed envelope (`enc:v1:`) makes encrypted-vs-legacy rows distinguishable and migration
auditable. A full KMS/HSM was rejected as premature for the deployment size — the upgrade path
(swap the key provider) is preserved.

### 4. PII redaction and data minimisation
Feedback text is capped for LLM context; PII is redacted from stored learning conclusions;
reviewer identities are pseudonymized (sha256) at the connector boundary.
**Why:** CLARA analyzes **themes, never people**. Redacting at write-time (rather than at
display-time) means a DB dump is already minimized — the alternative, masking in the UI only,
fails the first subject-access request. Cost: irreversibility; accepted deliberately.

## B · Insight: from raw text to defensible findings

### 5. LLM enrichment (sentiment, urgency, tags) with few-shot exemplar store
Every signal gets sentiment, urgency, and snake_case theme tags from an LLM call, steered by a
curated, coverage-balanced exemplar set (7 EN + 2 DE) that teaches the tag vocabulary and urgency
rubric.
**Why this approach:** plain prompt-text exemplars work with *any* OpenAI-compatible model —
cloud or self-hosted — and need no embeddings endpoint (some gateways are chat-only). The
alternatives were fine-tuning (locks you to one model, needs training infra, kills the
"self-hostable" promise) and embedding-retrieved exemplars (better at scale, but requires an
embeddings provider — kept as the documented upgrade path). Measured honestly: the exemplar
intervention lifts exact-tag-set agreement 8.75%→28.75% (in-run paired McNemar p = 0.001, n = 80);
the urgency lift (81.25%→86.25%, p = 0.219) is directionally positive but unproven, and we say so.

### 6. Provider-agnostic AI layer (cloud or EU-resident/self-hosted)
One AI service speaks the OpenAI chat protocol to any backend: hosted models, EU gateways, or
local Ollama/vLLM.
**Why:** EU data-sovereignty is CLARA's commercial wedge — regulated buyers cannot send feedback
to US-hosted LLMs. Abstracting at the protocol level (not per-vendor SDKs) keeps the switch to a
sovereign deployment a config change. Cost: lowest-common-denominator features (no vendor-specific
tool-calling exotica), which the pipeline is designed around anyway.

### 7. Semantic taxonomy with bootstrap and hygiene
An adaptive taxonomy service classifies and canonicalizes themes semantically (replacing the
legacy substring/term-matching), with bootstrap (seed a workspace's taxonomy from its own data)
and hygiene (merge/rename drift) routines.
**Why:** free LLM tagging invents vocabulary (`checkout_crash` vs `checkout_failure`), which
fragments clustering; a rigid hand-built taxonomy (the enterprise-CX default) costs weeks of
consulting before day one. The middle path — model proposes, taxonomy canonicalizes, hygiene
consolidates — keeps zero-config onboarding *and* stable theme keys. Cost: canonicalization is
itself model-assisted and needs the hygiene loop to stay clean.

### 8. Cross-signal severity with time-decayed frequency
Problem severity is computed deterministically from the corroborating **set** of signals (urgency
mix, volume, sentiment) with a time-decayed frequency component and trend detection, not from the
loudest single signal — and severity is explicitly labelled "deterministic" in the UI.
**Why:** putting severity in deterministic code (not the LLM) makes prioritization auditable and
stable across model swaps — an examiner or works council can read the formula. Time decay replaces
raw counts so old storms don't outrank new fires. Known cost, stated in the thesis: a set-based
metric can bury the rare catastrophic single signal — an override exists for that.

### 9. Problem clustering & the problems board
Signals cluster into named problems (theme-keyed), each carrying its evidence, severity, status
lifecycle, and downstream actions/outcomes — the operational home screen.
**Why:** the alternative unit of work — dashboards of charts — is where feedback goes to die (the
market's own analysts declared insight commoditised). Making the *problem* the first-class object
means everything hangs off something ownable and closeable.

### 10. Insight synthesis with learnings injection
For a cluster, the LLM synthesizes an insight card: summary, severity assessment, recommended
action, confidence — with retrieved past learnings injected into the prompt so remedies that
measurably worked are preferred (Reflexion grounded in outcomes).
**Why:** synthesis is bounded to a named pipeline stage with full audit metadata
(model/source/limitations on every card), versus an open-ended agent that "does analysis". The
learnings injection is the loop's payoff — measured: remedy adoption 21%→71% when retrieval is on.
Honest boundary: whether the adopted remedy is *better* still awaits live outcome data.

### 11. Emerging-theme detection
Surfaces themes that are new or accelerating before they are big, from the same tag stream.
**Why:** volume-ranked boards structurally hide the new thing; a simple recency/growth heuristic
on canonical tags is cheap, explainable, and needs no anomaly-detection service. Cost: heuristic
sensitivity — tuned conservatively to avoid alert fatigue.

### 12. Contexts, journeys, and context-impact
Business contexts (products, segments, journey stages — CSV-importable) map onto signals, and a
context-impact service quantifies which contexts drive which problems over time.
**Why:** mid-market teams think in "checkout", "onboarding", "DACH", not in tag clouds; letting
them import their own context model beats both hard-coded journey stages (wrong for someone) and
full CDP integration (too heavy for the segment).

### 13. Ask CLARA — scoped Q&A with receipts
Natural-language questions over the workspace's own signals, where every answer cites the signals
it used.
**Why:** the deliberate counter-design to a free-roaming chat assistant: scope-limited retrieval +
mandatory receipts means answers are checkable and hallucination has nowhere to hide. The
alternative — a general RAG chatbot — demos better and audits worse; for a governance-first
product the receipts are the feature.

## C · Action: doing something, governedly

### 14. Policy rules with explicit conflict resolution
Declarative policy rules (seeded templates included) route insights to actions; conflicts resolve
by priority → specificity → action-type dedupe, and superseded rules are logged.
**Why:** the routing logic must be *inspectable* — an LLM deciding "what happens next" is exactly
what EU AI Act reviewers (and works councils) will not accept. Deterministic rules with a
documented conflict ladder cost config debt (a wrong rule is enforced as faithfully as a right
one — stated in the thesis) but make governance a property, not a promise.

### 15. Human-in-the-loop approval workflow (LangGraph interrupt)
Every consequential action pauses at an approval node: the graph interrupts, a human sees
evidence, confidence and limitations, and approves or rejects; rejection routes to END.
**Why:** approval is implemented as a *workflow interrupt*, not a UI convention — there is no code
path to an external effect that bypasses the gate (`auto_execute=false` default). Designed beyond
Art. 14 minimums (friction + evidence shown + per-decision attribution) because awareness alone
does not de-bias overseers. Alternative rejected: configurable autonomy levels — explicitly
declined in the external-review response because it reopens the ungoverned path the product exists
to close.

### 16. Four-eyes approvals & JWT-bound reviewer identity
An opt-in workspace flag requires two distinct approvers (self-confirmation rejected, first
approval holds execution, rejection resets the tally); the approving identity is derived from the
verified login, not from a client-supplied field.
**Why:** the earlier self-asserted request-body identity was a real finding from the review-then-
harden cycle — approval provenance must be as trustworthy as the approval itself. Shared
resolution logic (`resolve_approval_state`) keeps board/API/UI consistent by construction.

### 17. Real action push with append-only audit
Approved actions fire the real destination connector (Jira ticket, Slack notification); every
execution is logged (rule, params, executor, result) in append-only records.
**Why:** "closing the loop" without external effects is a demo. Push-on-approval with audit
records makes the loop end-to-end real while keeping the blast radius enumerable — the points
where the system can act are finite, named, and individually auditable.

### 18. Evidence packs with content hashing
One export tells the audit-ready story of a problem: signals → classification → proposed actions →
policy trail → human approvals → outcomes; the pack's canonical sha256 is stamped onto the
ApprovalRecord at decision time.
**Why:** the hash makes it *provable* whether the evidence an approver saw has since changed —
tamper-evidence for the cheapest possible price (one hash column), versus the heavyweight
alternative (WORM storage/blockchain notarization) nobody in this segment needs. Stable across
re-exports of unchanged records by construction.

### 19. Works-council mode (§87(1) Nr. 6 BetrVG)
A German-market mode that constrains the system against employee-performance monitoring: no
per-agent metrics, aggregation floors, and a code-verifiable feature matrix + attestation
documents for the Betriebsrat.
**Why:** German works councils co-determine any system objectively *capable* of monitoring
employees — the standard killer of CX-tooling rollouts in DACH. Making non-monitorability a
verifiable product property (with annexes that cite code) turns the deployment blocker into a
differentiator. Alternative (policy PDF promising good behavior) is what everyone else does and
what councils have learned to distrust.

## D · Learning & measurement: does the fix work, and is it remembered

### 20. Outcome contracts with scheduled re-measurement
Approving an action can bind it to an outcome contract: metric, trailing baseline window, 30-day
measurement window with a T+7 early read, proposed automatically at approval time; pg_cron
schedules the re-measurements.
**Why:** action-taken ≠ problem-solved (the Uber apology experiment is the thesis's anchor
citation). A *contract* (agreed metric + window, fixed before the action) prevents post-hoc metric
shopping — the alternative, ad-hoc "did it help?" dashboards, invites exactly that. Cost: honest
contracts sometimes say "not measurable" — see detectability notes.

### 21. Interrupted-time-series estimator with evidence grading (A–E)
Outcome effects are estimated by segmented regression with CIs (complete UTC days, pre-window
truncation, execution-day exclusion), and every readout carries an A–E grade of its measurement
*design* (A randomized holdout … C ITS … E manual assertion), plus instrumented-vs-manual
provenance that clients cannot spoof.
**Why:** mid-market reality is one time series, not an RCT; ITS is the strongest honest design
available there, and grading the design (rather than pretending everything is causal) is the
credibility play. Regression-tested for exact recovery and bias. Upgrade path: synthetic
difference-in-differences once multi-workspace panels accumulate.

### 22. Guardrail measurement & detectability notes
Non-inferiority guardrails (e.g. repeat_signal_rate vs a 28-day pre-window; breach = >20% relative
worsening) are measured at every checkpoint — informative, never blocking; unmeasurable guardrails
surface an explicit "no data source" marker. Contract proposals include a Poisson
normal-approximation MDE note ("at this volume, a smaller effect than X is undetectable in W
days"), labelled a heuristic.
**Why:** the alternative — silent guardrails and unpowered windows — produces confident nonsense;
the honest markers are cheap and teach users what their data can and cannot show. The Trade
Republic public-data teardown (p ≈ 0.66 on a real intervention) is this feature's sales pitch.

### 23. Perishable learning memory with confidence decay
Measured outcomes distill into learning conclusions whose confidence decays
(base × 0.5^(age/half-life)); decayed-confidence retrieval feeds future synthesis; learnings carry
retention windows (730-day default) and PII redaction.
**Why:** organisational memory depreciates (Argote) — a remedy that worked in 2024 should not
steer 2027 with full force. Prior art (MemoryBank) decays *chat* memory; CLARA decays
**action-outcome evidence**, which is the novel, defensible bit. Cost, stated plainly: the
half-life is a guess until enough real outcome data exists to fit it.

### 24. Eval harness with published, honest metrics
An in-repo evaluation harness runs the live pipeline against an 80-case bilingual golden set
(60 EN / 20 authored DE, adversarially verified), computes bootstrap CIs, runs in-run paired A/B
(McNemar) as the designed inference, and — only via an explicit `--publish` — commits a metrics
snapshot served at `GET /model-card/metrics` and rendered in the product's model card.
**Why:** the numbers users see are the committed evaluation outputs, not marketing copy; every
published figure traces to a dated run. In-run pairing exists because the model is
non-deterministic even at temperature 0 — cross-run deltas are noise. Disclosed limits: authored
German stratum; hallucination heuristic is EN-scope only by construction (excluded, not
misreported).

## E · Platform & trust surface

### 25. Multi-tenant isolation: RLS + JWT + workspace scoping
Every table carries workspace scoping enforced by Postgres row-level security; identity flows from
Supabase-issued JWTs; a JWT-derived pseudonym (not an email) lands in audit records.
**Why:** RLS puts tenant isolation in the database, where an application bug cannot bypass it —
the alternative (WHERE-clause discipline in app code) fails exactly once, catastrophically.
Honest boundary: not warranted as hardened multi-tenant for adversarial co-tenants; pilots run
single-workspace.

### 26. Session security: HttpOnly cookies, TOTP MFA, AAL2 enforcement flag
Production auth stores tokens in HttpOnly SameSite=Lax cookies (the api being a subdomain of the
web host makes this same-site — no BFF needed); GoTrue TOTP MFA with an optional
`CLARA_REQUIRE_AAL2` gate; Vercel previews intentionally keep the legacy flow (cross-site).
**Why:** localStorage tokens are XSS-stealable; the cookie flag was chosen over a
backend-for-frontend because the deployment topology already made cookies same-site — the cheapest
correct fix. Flagged rollout because breaking previews would break the dev loop.

### 27. Triple-store persistence (SQLite / in-memory / Postgres jsonb)
The same store interface runs on SQLite (dev), in-memory (tests), and Postgres (prod) with
domain objects serialized as jsonb payloads plus promoted columns added via `_ensure_column`.
**Why:** jsonb payloads make model evolution migration-free (new fields ship without ALTER
ceremonies) while promoted columns keep hot queries indexed; the triple backend keeps tests
hermetic and dev friction near zero. Cost: cross-payload queries need promotion first — accepted.

### 28. API keys for machine-to-machine access
`clara_sk_` keys (only the SHA-256 stored) let scripts and integrations hit the API without
borrowing a browser session.
**Why:** the alternative people actually do — copying a user JWT into a cron job — breaks on
expiry and audits as a human. Hash-only storage is table stakes done properly.

### 29. MCP server (read-only, 8 tools)
An MCP endpoint exposes read-only workspace intelligence (problems, outcomes, signals search,
model card…) to LLM clients (Claude, IDEs) under X-Api-Key auth.
**Why:** the buyer's own AI assistants become consumers of CLARA's governed data instead of
re-analyzing raw exports; read-only + API-key keeps it inside the governance story. Write tools
were deliberately excluded — actions only through the approval gate.

### 30. Alerts & digests (Slack / email)
Threshold alerts and scheduled digest summaries go to Slack and/or SMTP email — stdlib SMTP, no
provider dependency.
**Why:** the external reviews called this missing; it existed — the lesson (unsurfaced capability
reads as absent) is now part of the pitch. Stdlib SMTP keeps self-hosted deployments free of a
SaaS mail dependency.

### 31. BI exports
Flat CSV exports (signals, problems, outcomes, telemetry) for the customer's own warehouse — the
data gets out, deliberately.
**Why:** mid-market buyers fear lock-in more than they fear churn; making export a feature
(instead of an enterprise "talk to sales" concession) is cheap trust. Warehouse *ingestion* was
rejected: CLARA is not an ETL product.

### 32. Product telemetry (pilot metrics)
Append-only product events power the pilot/VC metrics that matter: time-to-first-insight,
approval-cycle time, action/outcome throughput.
**Why:** the pilot motion needs evidence the same way outcomes do; instrumenting from day one
beats reconstructing usage from logs later. Append-only mirrors the audit posture.

### 33. Industry profiles (adaptation by configuration)
Per-sector weight overlays (fintech, food delivery, B2B industrial…) adapt severity and vocabulary
without retraining, validated by the cross-industry real-data run (~90% star-proxy sentiment
across three sectors, zero fine-tuning).
**Why:** per-industry fine-tunes are the alternative — expensive, model-locked, and opaque.
Authored config priors are inspectable (the safeguard against encoded stereotypes, stated in the
thesis) and swap per workspace.

### 34. AI-literacy module (EU AI Act Art. 4) — EN + DE
An in-product module explains the system's capabilities and limits (including that the "model
score" is an uncalibrated heuristic), records a workspace-level pack-delivery attestation, and
deliberately does **not** track per-user completion.
**Why:** it *supports* the deployer's Art. 4 program rather than claiming to discharge it — the
copy was corrected from "discharges" after review, and no per-user tracking keeps it out of
works-council scope. Alternative (LMS-style tracking) creates the monitoring problem the
works-council mode exists to avoid.

### 35. Compliance & trust surface
EU AI Act article-by-article mapping (App B of the thesis doubles as a commercial artifact), DPIA
template, Betriebsrat pack, model card with published metrics, security page, legal pages
(Impressum/Datenschutz/AGB/AVV) and pricing behind a launch flag with double fail-closed guards
(DRAFT/placeholder content refuses to render).
**Why:** in the target segment the compliance pack *is* product surface — procurement reads it
before anyone logs in. Fail-closed legal pages exist because shipping a DRAFT Impressum is a
worse outcome than a 404.

---

## Improvement areas (proposed, prioritized)

1. **One live outcome contract on real data** — the single most important open step (thesis §6.5
   and the traceability matrix agree): every learning-loop claim is mechanism-proven but
   benefit-pending until a real action's contract completes on non-simulated data. The pilot
   motion should be designed around producing exactly this artifact.
2. **Tag canonicalization at enrichment time** — fuzzy tag F1 is 80.2% while exact-string is
   55.5%; the gap is vocabulary drift the semantic taxonomy already knows how to close. Wiring
   canonicalization into the enrichment path (not just post-hoc hygiene) would move exact-match
   metrics and clustering quality together. Cheap, high-leverage.
3. **Urgency significance + calibration** — the exemplar lift on urgency is unproven (p = 0.219 at
   n = 80). Grow the golden set (more DE, plus the eval-077-style "churn musing vs urgent" boundary
   cases) until the A/B is powered, and add a calibration exemplar for the critical-vs-high rule.
4. **Model-score calibration** — the displayed score is honestly labelled an uncalibrated
   heuristic; with eval data accumulating, fit an isotonic/Platt mapping and publish calibration
   curves in the model card. Turns a disclosed weakness into a measurable strength.
5. **Embedding-based exemplar selection and clustering (Set-BSR)** — the documented Phase-B+
   upgrade: per-workspace exemplar stores with coverage-based selection once an embeddings
   provider is configured; would also upgrade clustering beyond tag-keying.
6. **App-store connector hardening** — today's teardown surfaced the real-world quirks (DE
   storefront serves no RSS entries; feeds are flaky and need retries; pagination caps). The
   existing `app_store.py` connector should encode these (multi-storefront fallback, retry
   policy) before a pilot relies on it.
7. **Entity-level attribution** — the GetYourGuide run showed complaints map to *suppliers*; the
   same applies to marketplaces generally (and to CHECK24's verticals). A lightweight entity
   dimension on signals (supplier/product/branch) would unlock per-entity outcome contracts —
   repeat-offender scorecards — without a CDP.
8. **Churn-intent routing** — churn_risk is already a native tag and appeared organically in all
   three teardowns; a policy-rule template routing churn-tagged criticals to a save-desk action
   would be a demo-able, sales-relevant loop instance.
9. **SDID estimator** — as multi-workspace outcome panels accumulate, add synthetic
   difference-in-differences beside ITS (Arkhangelsky et al., 2021), upgrading achievable evidence
   grades from C toward B.
10. **Broader language support** — DE is measured (95%/85%); the hallucination heuristic is
    EN-scope by construction. Multilingual grounding (translate-then-ground or multilingual
    vocabulary) plus FR/ES/IT golden strata would widen the EU story with the same honesty
    discipline.
11. **Operational hardening for pilots** — uptime monitoring (still pending from the review
    response), API rate limiting, and the AAL2 flip once all users are MFA-enrolled; none are
    features, all are pilot-readiness.
12. **Self-serve entry tier** — the thesis targets 10–500-employee teams but onboarding still
    assumes a guided setup; a constrained self-serve Starter (CSV + one connector + read-only
    board) would let the GTM's volume motion run without founder time per seat.

---

_Related reading: `thesis/manuscript/04_artifact.md` (design decisions with costs),
`appendices/D_traceability_matrix.md` (claim-by-claim evidence status),
`business-ops/competitive/` (market positioning), `docs/mcp.md`, `DEPLOY.md`._
