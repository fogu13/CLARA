# Closing the Loop, Building the Memory — short working draft

For the 8 Aug meeting with Prof. Zorina. Condensed from the full manuscript (~35,000 words, 12 figures, appendices A–E); the §-numbers point into the real chapters. Working document, rough by design — not a chapter.

*Supersedes `short-draft-2026-08-01.md`, written for the meeting that did not happen. What changed in the week between them is §5 — the whole reason this version exists.*

## Where things stand (7 Aug)

- **The evaluation is complete.** The LLM path ran against this thesis's own 188-signal harness on 4 Aug, closing a `pending` row that had been open since April. It had not been merely unrun: it was **silently broken** — the gateway 403s Python-urllib's default User-Agent, and the script exited 0 after writing an empty file. A green exit code on an empty result. The fix was a User-Agent header and a loud failure on empty output.
- **Two new findings, one retraction, one restructure.** Escalation equity is the substantive Responsible-AI result (§5A.5). Journey stage and owner are scored for the first time (§5A.4.1). An aggregate cross-language accuracy claim was **retracted** — language is confounded with sector. RQ3 is now RQ3a (accuracy) / RQ3b (equity).
- **The manuscript has been re-synced.** Chapter 5's own §5A.7, plus Ch 3, 4, 6, 7 and Appendices B and D, were still telling the pre-run story; §6.4 listed the completed run as "remains pending" and Appendix B published a superseded accuracy snapshot as EU-AI-Act accuracy evidence. Propagated, and the prose that reasoned from the old state rewritten rather than renumbered.
- CLARA is live and healthy: 17/17 live smoke checks verified green 7 Aug.
- **Unchanged and honest: interviews not started (the critical path). Outcome data still simulated.**

## 1 Introduction (Ch 1)

Fewer than 30% of firms systematically close the loop on customer feedback (Bone et al. 2017), and the 2025/26 industry picture got worse, not better. Four deficiencies: signal fragmentation, the insight–action gap, unmeasured closure, lost organisational memory. The claim the whole thesis hangs on: **closing the feedback loop is a workflow-and-governance problem, and the two missing primitives are a measured outcome contract and a perishable learning memory — not a better dashboard.**

RQs, compressed: RQ1 (core) can an artifact make actions governed, executed and *verified closed*, with reusable learning captured; RQ2 what design principles let governed autonomy align with the EU AI Act/GDPR without slowing practitioners; **RQ3a** how accurately does the enrichment/routing pipeline reproduce human labels; **RQ3b** is that reliability *equal* across languages — whose problems reach a human; RQ4 how do practitioners judge usefulness, usability, trust.

## 2 Literature (Ch 2)

Eleven thematic strands → industry corroboration → DSR methodology → RAI and the EU AI Act (incl. the 2026 Digital Omnibus timeline shifts) → 2023–26 developments. The gap it lands on (§2.17): **no design-science artifact instantiates the complete governed loop — signal → insight → governed action → measured closure → perishable, retrievable learning — as one system.** The contribution is the integration, not a new algorithm.

Framing moves worth knowing: the novelty claim is self-narrowed against MemoryBank (decayed *evidence confidence over action-outcome learnings, retrieved under governance*); Halperin et al. 2022 (the 1.5M-customer Uber field experiment — apologies can *reduce* future spending) as the strongest case for measuring closure; Laux & Ruschemeier 2025 on why Art 14 awareness-oversight won't de-bias on its own.

**Fixed 7 Aug.** Ch 2 carried 65 trailing "the platform does X" clauses bolted onto prior-work paragraphs — a chapter arguing *for* the artifact while claiming to survey the field, which is what an examiner reads as motivated reasoning. All are now cut or restated as impersonal design implications, with forward references to the chapters that make artifact-specific claims. Two concrete defects went with them: **30 sentence-initial lowercase "the platform"** (leftovers from the Odradek find-replace, visible on nearly every page) and internal class names in the literature chapter (`ActionLog`, `FeedbackRule`, `AbLearning`, `InsightStatus`, `workspace_id`, `auto_execute`). *Correction to my own note: the chapter is **~11k words, not 75k** — that figure was the file's byte size. Length was never the problem; the framing was.*

## 3 Methodology (Ch 3)

DSR (Hevner's three cycles, Peffers' DSRM, contribution level "improvement"). Convergent mixed methods where the **qualitative stream is primary** for design validity and the quantitative gold set is supporting evidence that the triage precondition holds.

Quantitative design (§3.5): 188 real public signals (Trade Republic 67, Henkel 39, Lieferando 82; EN 102 / DE 84 / other 2), labelled independently of the artifact. *(The §3.7 table used to sum to 191 against the harness's 188 — reconciled this week.)* Closed-set fields scored with macro-F1 and confusion matrices; the hallucination check is deliberately EN-only rather than mis-scoring German. Exemplar effects tested with in-run paired McNemar because GLM-5.2 is non-deterministic even at temperature 0.

§3.5.5 — outcome scoring as interrupted time series: segmented regression at the action date, ~60 dependency-free lines; honesty rules: below 10 pre / 5 post daily buckets it refuses to fit and reports a labelled plain delta with no CI.

## 4 The artifact (Ch 4)

Next.js front end; FastAPI backend (~43 endpoints); LangGraph orchestration; Postgres + pgvector with enforced RLS and JWT-bound identity; Langfuse tracing; provider-agnostic model routing. Production: Vercel + Docker on an EU VPS behind Caddy + Supabase Frankfurt.

The architecture stance: **deterministic logic in testable code, LLM reasoning bounded behind one interface at named pipeline stages** — Ingestion → Enrichment → Synthesis → Action → Approval → Measurement → Learning, governance cross-cutting. The human approval gate is literally a LangGraph *interrupt* node (DP5).

Five design decisions (§4.3): graduated rule-conflict resolution; confidence decay on learnings; cross-signal severity with a corroboration floor; past-learnings retrieval; per-industry scoring profiles.

RAI controls (§4.4): approval gate beyond the Art 14 minimum; Art 12 audit trail; Art 50 transparency labels; works-council mode; model-sovereignty option — which August made real rather than declared: embeddings can now point at a different provider than chat, so an EU embedding provider is a config change.

## 5 Evaluation (Ch 5) — **this is what changed**

§5A — three predictors, **one gold standard**, all rows now filled:

| | sentiment (n=153) acc / macro-F1 | risk (n=106) acc / macro-F1 |
|---|---|---|
| lexicon floor | 0.37 / 0.37 | 0.41 / 0.26 |
| TF-IDF + LogReg | 0.78 / 0.52 | 0.68 / 0.65 |
| **LLM path** | **0.86 / 0.67** | **0.72 / 0.68** |

Reading: triage accuracy is strongly method-dependent, and **the shape of the gain is the finding** — contextual reasoning buys a lot on sentiment (macro-F1 0.52 → 0.67) and little on severity (0.65 → 0.68). The precondition is satisfiable by more than one method; the choice is a deployer's trade-off, not a foregone conclusion.

§5A.4.1 — **routing fields, scored for the first time** under a supplied closed inventory: journey stage 0.59 against a 0.20 majority-class floor (27 classes); owner 0.40 against 0.15 (51 classes). Both clear their floors by a wide margin; **neither is remotely autonomous-capable**. Written up as evidence *for* the approval gate: a system routing on these numbers unattended would fail quietly and often. Bounds stated: supplied inventory is an upper bound, n=182 (six lost to endpoint errors), macro-F1 on classes with ≥5 support falls to 0.28 / 0.18.

§5A.5 — **the equity result (RQ3b)**, equal opportunity on gold-escalate signals:

| Escalation recall | n | keyword floor | LLM path |
|---|---:|---:|---:|
| German | 8 | **0.0%** | 87.5% |
| English | 41 | 19.5% | 87.8% |

The floor escalates **none** of the eight genuinely critical German signals. An uneven triage layer doesn't merely score worse — some customers' problems are systematically less likely to reach a human at all. A fairness property of the *loop*, not of a classifier. Bounds: n=8, and language is confounded with sector.

**What was retracted.** That confound cost a claim already in the draft: an aggregate DE-vs-EN accuracy comparison would largely restate sector composition (B2B is almost entirely German, fintech overwhelmingly English). Removed rather than defended. Only equal-opportunity escalation recall survives, because it conditions on the gold label. → question 4.

§5A.7 — the convergent in-repo stream (different gold, deliberately never merged): **n = 100 (72 EN / 28 DE)**: sentiment 97%, urgency 90%, tag-F1 (fuzzy) 0.83; urgency exemplar lift significant at p = 0.039, third consecutive run — **withheld at n=80 (p = 0.219) and claimed only once the sample carried it**. Learning loop: remedy presence in recommendations 21% → 71%. That the same path scores 0.86 against the star proxy and 0.97 against curated labels is itself instructive; **0.86 is the figure the thesis quotes**.

§5B: complete protocol, instruments, analysis plan; SUS/TAM ready; every result cell an explicit ‹placeholder›; nothing simulated. **Zero interviews conducted.** This is the critical path, and it is 7 August.

## 6 Discussion (Ch 6)

Six design principles, each with its cost stated. Positioning (§6.3): Forrester retired its feedback-management Wave in Q1 2026 — the insight half is commoditised; the defensible position is the combination (outcome contracts + verified resolution + approval gate and audit + decaying memory + EU-sovereign + SMB price point).

§6.4 now carries the limitations the run *created*: the language/sector confound behind the retraction; the eight-signal DE escalate stratum; routing as a supplied-inventory upper bound; six signals lost to endpoint errors; theme and recommended action **still unscored** (2 of 6 gold fields). The uncomfortable symmetry stands: my own outcome data is still simulated — limitation six of six, and the single most important open item.

## 7 Conclusion (Ch 7)

The loop can be closed by design, and governed while closing. RQ3a's honest answer: 0.37 floor → 0.78 learned → 0.86 contextual, with the gain concentrated in sentiment. RQ3b's: method choice determines whose problems reach a human. RQ4 awaits data. The closing motif: the verify-before-believe discipline the artifact imposes on its own actions got applied to the artifact itself — and this month, to its own evaluation harness.

## Text debts remaining

- Theme and recommended action remain unscored; the semantic-agreement procedure in §3.5.2 has not been executed. This is the only *evidence* debt left — the rest below are done.
- Routing fields need scoring in the free-form production condition, not only under the supplied inventory.
- Citation verification pass; repository URL / DOI in front matter; sign the declaration.

*(Cleared this week: the n=80 → n=100 propagation, the 191-vs-188 dataset table, the "remains pending" 188-run references, Appendix B's superseded published snapshot, the H4/H5 "not scored" rows, and the stale `build/thesis.docx` — rebuilt 7 Aug, display math verified.)*

## What I want from the 30 minutes

If we only get through three: 1, 2, 3.

1. **Evidence triage for the rest of August.** The 188-run is done — that ask is closed. Of what remains — 12–15 interviews, one *live* outcome measurement, a local-vs-cloud benchmark, semantic scoring of the two unscored fields — which are required for September and which are nice-to-have? And your realistic review turnaround on a compiled draft?
2. **Interviews / ethics.** Any OPIT-side step beyond your confirmation before I start recruiting? Recruitment hasn't started and August is the window — if 12–15 looks unrealistic, is leaning harder on the breadth survey an acceptable fallback?
3. **Simulated outcomes.** Is the thesis defensible in September if outcomes are still simulated (DP1 evidenced by demonstration + perception only), or do we force one small live ITS measurement into August at the cost of interview time?
4. **Is escalation-equity-only the right RQ3b claim,** given that I retracted the aggregate cross-language comparison? Or does RQ3b need natural German data before September?
5. **Routing fields under a supplied taxonomy** — fair to report, or does an examiner read it as scoring an easier task than the one deployed?
6. **DP5 vs free-roaming agents:** should Ch 6 add an explicit comparison to pre-empt "why not an agent?" — or is that scope creep? (The routing result is now my best empirical answer to it.)
7. **MemoryBank boundary** — tight enough as stated in §4.3.2/§6.1? The abstract still mentions decay without the boundary sentence.
8. **Per-industry placement** — does the distributed treatment (§5A.5 + §5A.7 + §4.3.5) suffice, or does it need one consolidated section? *(The Ch 2 half of this ask is withdrawn — the artifact-referential prose is fixed, and the chapter is ~11k words, so there is no length problem to solve.)*
9. **The external-review episode** — I compressed it from four full retellings to one canonical account in §5A.8, with §4.9, §6.4 and Ch 7 now carrying only their own consequence and a cross-reference. Does that read right, or would you still rather it moved to an appendix?
10. Logistics: the IP-letter process (due 31 Aug), the defense window, and whether you want the deck ahead of time.
