# Closing the Loop, Building the Memory — short working draft

For the 1 Aug meeting with Prof. Zorina. Condensed from the full manuscript (~35,000 words, 12 figures, appendices A–E); the §-numbers point into the real chapters. Working document, rough by design — not a chapter.

## Where things stand (31 Jul)

- Full manuscript exists end to end since mid-July: Ch 1–7 + references + appendices (instruments, EU-AI-Act/GDPR mapping, DPIA, traceability matrix, schema DDL).
- CLARA is live and healthy: scheduled uptime monitor green (15/15 recent runs), 17/17 live smoke checks, production deploy current, no runtime errors in the last 7 days.
- Since the 17 Jul check-in: golden set grown 80 → **100** (ask #4c from last time — done). DE gold completed to the two-tag rubric, and the **urgency exemplar effect is now significant: 83% → 90%, in-run McNemar p = 0.039, third consecutive run** (was p = 0.219 at n = 80). The manuscript text still says n = 80 / "not claimed" — needs a half-day propagation pass, listed under text debts below.
- Also since then, mostly platform work: TOTP MFA, HttpOnly cookie sessions, per-client rate limiting, secret encryption at rest, four-eyes approvals, guardrails now actually measured (not just declared), per-entity attribution rollup, tag canonicalization, App Store connector hardening, scheduled uptime monitoring.
- Still open, unchanged and honest: interviews not started (the critical path), LLM run on the 188-signal harness pending (needs a keyed execution run), outcome data still simulated.

## 1 Introduction (Ch 1)

Fewer than 30% of firms systematically close the loop on customer feedback (Bone et al. 2017), and the 2025/26 industry picture got worse, not better (Forrester's CX Index at an all-time low; "CX has an action problem"). I frame this as four deficiencies: signal fragmentation, the insight–action gap, unmeasured closure, and lost organisational memory. The claim the whole thesis hangs on: **closing the feedback loop is a workflow-and-governance problem, and the two missing primitives are a measured outcome contract and a perishable learning memory — not a better dashboard.**

RQs, compressed: RQ1 (core) can an artifact make actions governed, executed and *verified closed*, with reusable learning captured; RQ2 what design principles let governed autonomy align with the EU AI Act/GDPR without slowing practitioners; RQ3 how accurately does the enrichment/routing pipeline reproduce human labels across sectors and languages; RQ4 how do practitioners judge usefulness, usability, trust.

Contributions: the working artifact; transferable design principles; a real-data evaluation across three sectors and two languages; an account of Responsible AI as integral design rather than bolt-on.

## 2 Literature (Ch 2)

Eleven thematic strands (VoC, sentiment/NLP, BI, anomaly detection, DSS/rules, experimentation, churn, integration, dashboards, workflow, organisational learning) → industry corroboration → DSR methodology → RAI and the EU AI Act (incl. the 2026 Digital Omnibus timeline shifts) → 2023–26 developments (agentic feedback platforms, meaningful human control, MemoryBank, LLMs as qualitative coders). The gap it lands on (§2.17): **no design-science artifact instantiates the complete governed loop — signal → insight → governed action → measured closure → perishable, retrievable learning — as one system.** The contribution is the integration, not a new algorithm.

Framing moves worth knowing about: the novelty claim is self-narrowed against MemoryBank (decayed *evidence confidence over action-outcome learnings, retrieved under governance* — not decay-memory per se); Halperin et al. 2022 (the 1.5M-customer Uber field experiment — apologies can *reduce* future spending) as the strongest case for measuring closure instead of assuming it; Laux & Ruschemeier 2025 on why Art 14 awareness-oversight won't de-bias on its own — which is exactly why the approval gate adds friction, evidence display and per-decision attribution.

[Known issue: Ch 2 is 75k words and §2.1–2.13 still carry artifact-referential prose from an earlier draft ("the platform addresses…"). Prune into a tighter prior-work chapter? → question 8.]

## 3 Methodology (Ch 3)

DSR (Hevner's three cycles, Peffers' DSRM, contribution level = "improvement": instantiation + nascent design theory). Convergent mixed methods where the **qualitative stream is primary** for design validity and the quantitative gold-set is supporting evidence that the triage precondition holds. The old H1–H8 are treated as design propositions, not statistical effects.

Quantitative design (§3.5): 188 real public signals (Trade Republic, Henkel, Lieferando; EN 102 / DE 84), labelled independently of the artifact. Closed-set fields scored with macro-F1 and confusion matrices; open-vocabulary fields via semantic agreement with human adjudication; the hallucination check is deliberately EN-only rather than mis-scoring German. Exemplar effects tested with in-run paired McNemar because GLM-5.2 is non-deterministic even at temperature 0.

§3.5.5 — the July addition, shipped as production code, not just methodology: outcome scoring as interrupted time series. Segmented regression at the action date, ~60 dependency-free lines; bias controls validated by simulation (complete UTC days only, execution day excluded, no fabricated history); honesty rules: below 10 pre / 5 post daily buckets it refuses to fit and reports a labelled plain delta with no CI. Contracts are proposed automatically at approval time (trailing-rate baseline capped at 28 days, 30-day window, T+7 early read), editable and declinable. Known caveats carried in §6.5: HAC errors pending, OLS-on-rates vs a count GLM, earliest-execution attribution.

Ethics (§3.9) and positionality (§3.12): researcher = designer with a commercial interest, declared, with four safeguards (external labels, standardised instruments, double-coding, reproducible harness).

## 4 The artifact (Ch 4)

Stack: Next.js front end; FastAPI backend (~43 endpoints); LangGraph orchestration; Postgres + pgvector with enforced RLS and JWT-bound identity; Langfuse tracing; provider-agnostic model routing. Production: Vercel + Docker on an EU VPS behind Caddy + Supabase Frankfurt — the EU-sovereignty claim is a deployed fact, not an intention.

The architecture stance (the part I most want your read on): **deterministic logic in testable code, LLM reasoning bounded behind one interface at named pipeline stages** — Ingestion → Enrichment → Synthesis → Action (rules) → Approval → Measurement → Learning, with governance cross-cutting. The human approval gate is literally a LangGraph *interrupt* node; the model is a contained component, not the controller (DP5).

The five design decisions (§4.3), one line each: graduated rule-conflict resolution (priority → specificity → action-type dedupe, superseded rules logged); confidence decay on learnings (base × 0.5^(age/half-life), staleness flags); cross-signal severity with a corroboration floor (≥2 sources or ≥3 identified customers before "act now") and near-duplicate annotation that never drops; past-learnings retrieval (pgvector similarity re-weighted by decayed confidence, explainable token-overlap fallback); per-industry scoring profiles (adaptation by configuration, not retraining).

RAI controls (§4.4): approval gate beyond the Art 14 minimum (friction, evidence display, per-decision attribution); Art 12 audit trail; Art 50 transparency labels + an editorial-review flow for AI-drafted customer text; works-council mode (aggregate-only, k = 5 small-cell suppression, a CI test that no person-capable field leaks); AI-literacy onboarding; model-sovereignty option. Out of the July review episode: evidence grades A–E, provenance force-stamping, "confidence" renamed **model score** (it is an uncalibrated heuristic — saying so is the feature), sha256-hashed evidence packs, four-eyes approvals.

§4.9 is the review-then-harden account: a 2 Jul structured review found 58 defects, 10 high (declared-but-not-enforced RLS among them) — lesson kept in the text: *declared controls are not enforced controls*. Then 16–17 Jul: two external LLM reviews, 45 claims adversarially verified (≈27 confirmed / 13 partial / 2 refuted), a 38-item plan, 20 PRs, 17/17 live checks after deploy.

## 5 Evaluation (Ch 5)

§5A — three predictors on the same real-data gold:

| | sentiment (n=153) acc / macro-F1 | risk (n=106) acc / macro-F1 |
|---|---|---|
| lexicon floor | 0.37 / 0.37 | 0.41 / 0.26 |
| TF-IDF + LogReg | 0.78 / 0.52 | 0.68 / 0.65 |
| LLM path | ‹pending — keyed run› | ‹pending› |

Reading: triage accuracy is strongly method-dependent. The floor calls 58 of 94 gold-negatives "neutral"; a learned model is necessary, and sufficient for the loop's precondition. Per-slice lexicon macro-F1 is uneven (DE 0.42 vs EN 0.27) — kept as a fairness observation, not buried.

§5A.7 — the convergent in-repo stream (different gold standard, deliberately never merged into the table above): on the platform's committed golden set, now **n = 100 (72 EN / 28 DE)**: sentiment 97%, urgency 90%, tag-F1 (fuzzy) 0.83; the urgency exemplar lift significant at p = 0.039 for the third consecutive run; the DE tag-gold completion is disclosed as improving metrics partly by construction — that disclosure is the point. Learning loop: remedy presence in recommendations 21% → 71%. [These are the 18 Jul published numbers; the chapter text still carries the 17 Jul n = 80 snapshot.]

§5B: complete protocol, instruments, analysis plan; SUS/TAM ready; every result cell is an explicit ‹placeholder›; nothing simulated. Zero interviews conducted. This is the critical path, and it is 31 July.

## 6 Discussion (Ch 6)

Six design principles, each with its cost stated: closure as contract (gameable metric); perishable memory (half-life is an unknown parameter); severity from the set (can bury the rare catastrophic single signal); graduated authority + explicit conflicts (configuration debt); bounded model, deterministic loop (caps the ceiling); adapt by configuration (authored priors).

Positioning (§6.3): Forrester retired its feedback-management Wave in Q1 2026 — the insight half is commoditised. Enterpret's marketing claims were verified rather than believed: 114 extracted, 25 survived, outcome measurement unverifiable. No single differentiator survives on its own; the defensible position is the combination (outcome contracts + verified resolution + approval gate and audit + decaying memory + EU-sovereign + SMB price point). The uncomfortable symmetry is stated in §6.4: my own outcome data is still simulated — limitation six of six, and the single most important open item (§6.5).

## 7 Conclusion (Ch 7)

The loop can be closed by design, and governed while closing: actions bound to outcome contracts, learnings retained as perishable retrievable memory, autonomy graduated and auditable. RQ3's honest answer: 0.37 floor vs 0.78 learned, LLM row pending, convergent evidence strong. RQ4 awaits data. The closing motif: the verify-before-believe discipline the artifact imposes on its own actions got applied to the artifact itself in the external-review episode, and the claim came out stronger.

## Text debts I already know about

- Propagate n = 100 / p = 0.039 into §5A.7, §6.4, Ch 7 and the abstract (all still say n = 80 / "not claimed").
- Ch 3 §3.7 dataset table sums to 191; §5A.1 says 188 — reconcile the 3-signal discrepancy.
- Ch 2: prune the artifact-referential passages and the stale header.
- Rebuild `build/thesis.docx` (built 13 Jul, pre-streamline; §3.5.5 display math needs a pandoc check).

## What I want from the 30 minutes

If we only get through three: 1, 2, 3.

1. **Evidence triage for August** (was ask #4). Golden-set growth is done (n = 100, significance achieved). Of the rest — 12–15 interviews, the LLM-on-188 run, one *live* outcome measurement, the local-vs-cloud benchmark — which are required for September and which are nice-to-have? And your realistic review turnaround for the compiled draft (was ask #1).
2. **Interviews / ethics** (was ask #3). Any OPIT-side step beyond your confirmation before I start recruiting? Recruitment hasn't started and August is the window — if 12–15 looks unrealistic from here, is leaning harder on the breadth survey an acceptable fallback?
3. **Simulated outcomes.** §6.5 calls one live outcome contract "the single most important next step." Is the thesis defensible in September if outcomes are still simulated (DP1 evidenced by demonstration + perception only), or do we force one small live ITS measurement into August at the cost of interview time?
4. **An architecture question I'd genuinely value your view on:** DP5 confines the model to named stages with a human-approval interrupt node, deterministic code everywhere else. Should Ch 6 add an explicit comparison against free-roaming agent designs (the HULA/agentic literature it already cites) to preempt an examiner's "why not an agent?" — or is that scope creep?
5. **RQ3 shape.** If the LLM-on-188 run can't land in time: does an RQ3 whose strongest predictor row reads "pending" survive the defense, or should the convergent-evidence stream be promoted to primary RQ3 evidence?
6. **MemoryBank boundary** (was ask #2): tight enough as now stated in §4.3.2/§6.1? The abstract still mentions decay without the boundary sentence.
7. **Authored German stratum + EN-only hallucination check:** is disclosure enough for the fairness-across-language observations in §6.2, or should I get natural German data before September?
8. **Ch 2 and per-industry placement** (was ask #5): does the distributed per-industry treatment (§5A.5 + §5A.7 + §4.3.5) suffice, and should the 75k-word Ch 2 be cut to a tighter prior-work chapter that lands faster on the gap table?
9. **The external-review episode appears in four places** (§4.9, §5A.8, §6.4, Ch 7). Does it strengthen the verify-before-believe thread or start to read as inflation? Keep / compress / move to an appendix.
10. Logistics: the IP-letter process (due 31 Aug), the defense window, and whether you want the updated deck ahead of time.
