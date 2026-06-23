# Odradek — Consolidated Strategy Synthesis

> Master strategy document merging the in-folder thesis strategy with four external AI strategy
> sessions (ChatGPT, Gemini 3.1 Pro, Claude). Created 2026-06-19 for the advisor meeting and to
> serve as the single source of truth ("consolidate into ONE document", PLAN_3_MONTHS Week 1).

**Positioning (locked):** The main USP is **automating the closing of the feedback loop** — the full
Signal → Insight → Action → Learning cycle run automatically (with human-in-the-loop where needed).
**EU AI Act / GDPR compliance checks and audit/governance controls are an added layer on top**, not
the headline. Project name: **Odradek**. See §6.

> **Implementation status (built):** The plan in this document has been implemented in the codebase —
> action engine (rule builder + conflict resolution + approvals), close-the-loop outcome measurement,
> the learning repository (confidence decay + relevant-learnings retrieval), real NLP enrichment/
> synthesis with cross-signal severity, multi-source ingestion (CSV/webhook + connector scaffolds),
> and evaluation instrumentation. The four "non-trivial design decisions" (§ thesis) are now coded.
> AI runs through a provider-agnostic, self-hostable layer (any OpenAI-compatible endpoint). Connector *pulls*
> (Zendesk/Jira/HubSpot/Typeform) remain scaffolded pending credentials. See git history on
> `feat/strategy-alignment`.

---

## 1. The two views being merged

| | In-folder strategy | External AI sessions |
|---|---|---|
| **What it is** | A scoped, defensible DSR thesis (MSc Responsible AI, OPIT, 30 ECTS, Sept 2026) | An expansive engineering + SaaS-business blueprint |
| **Artifact** | Odradek — React 18 + Supabase, **already built** | Proposed Python/FastAPI/LangGraph/pgvector/LiteLLM rebuild |
| **Core** | Signal → Insight → Action → **Learning** (incl. Experiment Learning Repository) | Feedback → triage → action → outcome (governed agentic) |
| **Evaluation** | Qualitative: 12–15 interviews + task scenarios + SUS/TAM, Braun & Clarke | Quantitative ladder: gold set, F1/precision/acceptance/cost/latency |
| **Target** | SMB marketing teams (10–500 employees) | B2B SaaS 20–300 employees; DACH-first |

**Conclusion:** these are the same product at two sizes. Keep the in-folder thesis as the spine;
import the external sessions as market context, an RAI mechanism, and post-thesis roadmap.

---

## 2. Cross-source convergence (treat as settled bets)

Points reached independently by 3–4 sources:

| Converged conclusion | ChatGPT | Gemini | Claude | In folder |
|---|:--:|:--:|:--:|:--:|
| "Themes-in-a-dashboard → Jira" is **table stakes**, not a differentiator | ✓ | ✓ | ✓ | partial |
| Wedge = **governed / explainable autonomous action** with approval gates | ✓ (policy engine) | ✓ (white-box + graduated authority) | ✓ (action gate) | ✓ |
| **Hybrid local + API** models (local for PII/volume, API for synthesis) | ✓ | ✓ | ✓ | ✗ |
| **Eval-first** with a gold-labelled set as the thesis instrument | ✓ | – | ✓ | partial |
| **EU/GDPR/AI-Act + data sovereignty** as a feature, esp. DACH | ✓ | ✓ (strongest) | ✓ | ✓ |
| **Scope brutally; SaaS is post-thesis** | ✓ | – | ✓ (loudest) | ✓ |
| **Enterpret** = closest competitive threat | ✓ | ✓ | ✓ (deep dive) | ✗ |
| Don't compete on collection — **integrate** with VoC vendors | ✓ | ✓ | ✓ | ✓ |

---

## 3. What each external source uniquely contributes

### ChatGPT
- 8-layer reference architecture; "LLM proposes → deterministic validation → human approval → write-back → outcome tracking".
- Full **competitor ranking** (June 2026): Dovetail 86, Chattermill 81, Enterpret 80, SentiSum 79, Amplitude 78, Medallia 75, Qualtrics 74, Pendo 71, Productboard 70, Thematic 68, Forsta, InMoment, Sprig, Cycle, Canny, zenloop, Alida, UserVoice.
- **Market gaps:** marketing activation, outcome attribution, cross-functional orchestration, governed autonomy, EU deployment, German-language, B2B account-level.
- Three prototype features: **dual-action recommendation**, **approval-policy engine**, **outcome contract**.
- **USP ranking** (journey detection #1, cross-functional orchestration #2, outcome closure #3) and a clear "do NOT build full campaign execution" boundary (Adobe/Salesforce/Braze territory).

### Gemini 3.1 Pro
- **Desirability triad: relevance, explainability, trustworthiness** — a clean, citable evaluation lens.
- **"White-box advantage" + "graduated authority"** — audit-logged reasoning per action; risk-tiered automation.
- **Data sovereignty as a feature** — local self-hosted models so PII never leaves the client (GDPR/AI-Act wedge).
- New competitors: **Mopinion**, **Feedier** (EU SaaS), **Notch**, **Yellow.ai** (autonomous-action agents).

### Claude
- Sharpest scope realism: **~2 months ≠ SaaS; thesis = narrow slice, business = 12–18-month build after.**
- Names the wedge: **governed autonomous action** — agent drafts; compliance + dark-pattern + PII gate clears it before firing.
- **Reliability math:** 95%/step over 8 steps ≈ 66% end-to-end → keep horizons short, **gate every external write**.
- DSR eval template: **2026 CHI paper comparing LLM-generated themes to human-coded NPS themes**.
- Raised a governance-first framing as an alternative. **Rejected** — see §6: Odradek's headline is
  automated loop closure, with governance/EU AI Act as an added layer, not the spine.

---

## 4. What the in-folder strategy has that NONE of the AIs do

These are your genuine moat — protect them:

1. **The "Building the Memory" half** — the **Experiment Learning Repository** (A/B test pattern capture, confidence decay, "relevant past learnings" retrieval). No AI session and no Gartner MQ vendor addresses this. **This is the blue ocean.**
2. **Academic rigor as contribution** — DSRM (Peffers), FEDS (Venable), Hevner's 7 guidelines, and the **four non-trivial design decisions** (rule-conflict resolution, confidence decay, cross-signal severity scoring, learnings retrieval). The research lives here, not in the CRUD.
3. **Concrete SMB scope and three named gaps** — scope gap (SMB vs enterprise VoC), integration gap (action + learning repository), knowledge gap (A/B learnings repository).

---

## 5. Consolidated competitive landscape

| Group | Players | Role vs Odradek |
|---|---|---|
| **Closest threats (intelligence → action)** | Enterpret, Dovetail, Chattermill, SentiSum, Amplitude, Thematic | Replicate evidence-linking + feedback→ticket; beat on **governed action + learning memory** |
| **Enterprise VoC suites** | Qualtrics, Medallia, Sprinklr, InMoment, Forsta | **Sources/partners, not rivals** — they collect; you operationalize |
| **Product feedback / roadmap** | Pendo, Productboard, Sprig, Cycle, Canny, UserVoice | Strong on "what to build"; weak on service/marketing/outcome |
| **EU / DACH feedback SaaS** | zenloop, Mopinion, Feedier | German-market reference points; data-residency benchmarks |
| **Autonomous-action agents** | Notch, Yellow.ai | Support-deflection focus; governance/product-workflow gap |
| **Journey/marketing (future-work only)** | Adobe AJO, Salesforce MC, Braze, Optimove, Bloomreach, Insider, HubSpot | Do **not** compete; integrate as execution targets |

### 5a. Enterpret — closest threat (reviewed June 2026)

Enterpret has moved *toward* this space: it now markets a **Customer Context Graph** (issues →
churn/expansion/revenue-at-risk), an **MCP server** (query + act from Claude/ChatGPT), and **"Close
the Loop"** (detect resolutions + measure ticket-volume/sentiment/churn shifts). It remains
**product/CX/support-centric, enterprise/high-velocity, US cloud SaaS** (GDPR data-processor, not
self-hostable). Sources: enterpret.com, /security, /guides (accessed June 2026).

> **Correction to earlier framing:** Enterpret now *claims* outcome measurement, so "we close the loop"
> is no longer a safe differentiator. Sharpen the wedge to the mechanism it lacks (below).

**Copy — adapt the pattern, not the UI:** adaptive, self-evolving taxonomy; **account/revenue context**
(link insights to contract value + churn — the B2B gap); transparent **impact quantification**
(volume × value × churn = "revenue at risk"); pervasive evidence/verbatim linking; MCP (later).

**Defensible differences to focus & market — Enterpret does NOT do these:**
1. **Governed action** — approval matrix, risk tiers, rule **conflict resolution**, audit. It opens a ticket; Odradek *governs* what fires.
2. **Cross-functional + marketing activation** — one insight → product *and* marketing/CX (segments, suppression, campaigns). It stops at product/support.
3. **Experiment learning repository** — confidence decay + relevant-learnings retrieval. No VoC vendor ships this — the blue ocean.
4. **European-first** — self-hostable, your-own-model, EU residency, **EU AI Act checks on the actions**.
5. **SMB (10–500), governance-first** — a segment Enterpret doesn't court.

**One-line positioning vs Enterpret:** *Enterpret tells product teams what customers say and opens a
ticket; Odradek governs the action across product and marketing, proves it worked against a contract,
and remembers what worked — in your own EU cloud.*

---

## 6. Positioning: automated loop closure first, governance as a layer

- **The USP is automating the closing of the feedback loop** — Signal → Insight → Action → Learning,
  run automatically with human-in-the-loop where the risk warrants it. This is what every written
  artifact in the folder already commits to; no rewrite needed.
- **EU AI Act / GDPR compliance checks, audit trail, and graduated authority are an added layer on
  top** of the loop, not the headline. They strengthen the Responsible-AI fit (OPIT) and the EU/DACH
  commercial angle, but Odradek is sold and evaluated as *the system that closes the loop*, not as a
  governance gate.
- The **Experiment Learning Repository** ("Building the Memory") is part of loop closure — it is what
  makes the loop *learn* — and remains the contribution no competitor or AI session touches. Keep it.
- A governance-first framing was raised in one external session and **rejected**: leading with
  compliance would bury the differentiator and narrow the thesis. Governance rides on top of the loop.
- **Sharpen vs Enterpret (June 2026):** since Enterpret now also markets "close the loop," don't lead
  with the generic claim — lead with the *mechanism* it lacks: **governed, contract-based closure
  across product *and* marketing, plus the compounding learning memory.** See §5a.
- **Adopt cheaply (from the F2O proposal, §10):** the **dual-action** framing — every problem yields a
  *permanent structural fix* **and** an *immediate action for customers affected today*; reframe the
  existing approval/risk tiers as **"policy-as-code"** (strengthens the RAI story); and lift the
  outcome-oriented category line: *"decide what to do about customer problems, execute safely through
  the systems you already use, and prove whether it worked."*

---

## 7. Action list, mapped to thesis chapters

| Chapter / item | Action | Source |
|---|---|---|
| **Ch. 2 — Competitive** | Add the June-2026 competitor ranking + EU players (Enterpret, Mopinion, Feedier, zenloop). Cite vendor pages as supporting evidence w/ access dates; anchor claims to academic sources. | ChatGPT, Gemini |
| **Ch. 2 — EU/DACH market** | Cite German AI-adoption + trust evidence (Bitkom 2026: ~41% of firms ≥20 staff use AI, 93% would prefer a German AI provider; KfW: SME adoption gap) to ground the EU-first + SMB positioning and the SME-vs-enterprise split. | F2O proposal |
| **Ch. 4 — Artifact** | Lead with **automated loop closure** (auto-execute vs human-approval routing). Layer the **compliance/governance checks on top**: EU AI Act + GDPR + PII + **graduated authority** + audit trail. Add **outcome contract** (metric + window defined at action creation) and **three closure levels** (operational / customer / outcome). | ChatGPT, Gemini, Claude |
| **Ch. 4 — Artifact** | Cite the **reliability math** (gate every external write) as design rationale for human-in-the-loop. | Claude |
| **Ch. 5/6 — Evaluation** | Keep qualitative (SUS/TAM/thematic) as primary. Add **one small gold-set metric** via `evaluation/prototype_metrics.py` as supporting evidence, not a statistical claim. Cite the **CHI-2026 LLM-vs-human-NPS** paper as DSR precedent. | Claude, ChatGPT |
| **Ch. 6 — Future work** | Park journey optimisation, marketing activation, hybrid local models, MCP (both directions), B2B account-level prioritisation, DACH/German-language evaluation, full SaaS multi-tenancy. | All |
| **Framing lens** | Use Gemini's **relevance / explainability / trustworthiness** triad to structure the desirability discussion. | Gemini |

## 8. What NOT to do (explicit non-goals before September)

- ❌ Do **not** rebuild on FastAPI/LangGraph/pgvector — keep React + Supabase (feature freeze, Week 2).
- ❌ Do **not** build full campaign execution (Adobe/Salesforce/Braze territory).
- ❌ Do **not** broaden to autonomous multi-agent swarms — supervisor-routing of scoped steps only.
- ❌ Do **not** let the SaaS/journey ambition bloat the thesis. Narrow slice, rigorously evaluated.

---

## 9. Source index

- In-folder: `Thesis_Proposal_Final.docx`, `Advisor_Status_Update_June2026.docx`, `PLAN_3_MONTHS.md`,
  `chapters/ch1_introduction.md`, `chapters/ch3_methodology.md`, `literature_review.md`.
- ChatGPT session: `.firecrawl/chatgpt-share.md`
- Gemini session: `.firecrawl/gemini-share.md`
- Claude session: `.firecrawl/claude-share.md`

---

## 10. Vision & commercialization roadmap (post-thesis appendix)

> This is the **business north-star and Ch.6 future-work**, distilled from the "Feedback-to-Outcome
> Operating System" proposal. It is **not** thesis scope. See the guardrails at the end.

**North-star.** A European **Feedback-to-Outcome Operating System**: a governed customer-intelligence
and action layer that connects feedback with behavioural and operational data, locates problems in the
customer journey, recommends coordinated product/service/marketing interventions, executes them through
existing systems, and learns whether they actually solved the customer problem.
Category: *feedback-driven journey orchestration.* The full chain — **signal → problem → root cause →
affected customers/accounts → coordinated action → governance approval → execution → customer closure →
outcome measurement → organizational learning** — is what no single competitor owns end-to-end.

**Positioning line (not "we analyse feedback better"):** *"We help organizations decide what to do
about customer problems, execute safely through the systems they already use, and prove whether the
action worked."*

**Nine-module map — what exists vs. future:**

| Module | Status |
|---|---|
| 1 Universal Signal Hub (canonical event model) | partial — CSV/webhook + scaffolds today |
| 2 Customer & Account Context Graph (ARR, hierarchy, churn) | **future** (the B2B gap / Enterpret copy item) |
| 3 Trusted Intelligence (adaptive + editable taxonomy, evidence, multilingual) | partial — synthesis + evidence built; adaptive/editable taxonomy + DE/EN = future |
| 4 Live Journey Intelligence (feedback × behaviour, friction scoring) | **future** (flagship differentiator; needs behavioural data) |
| 5 Coordinated Action Studio (dual structural + customer action portfolio) | partial — governed action engine built; portfolio/dual-action = enhance |
| 6 Audience & Intervention Builder (governed audience drafts → Adobe/Braze) | **future** (marketing-activation wedge) |
| 7 Governance & Approval Engine (risk tiers, policy-as-code, model governance) | partial — approval/audit/compliance built; policy-as-code = formalise |
| 8 Resolution & Customer Closure | partial — measurement + closure levels built |
| 9 Outcome Learning Engine (outcome contract, reusable learnings) | **built** — the moat |

**The moat:** the growing proprietary graph of *which customer problems, in which contexts, were best
solved by which combinations of actions* — i.e. the learning repository, extended.

**Commercialization sequence (§17 of the proposal):** 1) feedback → accountable action → 2) journey
intelligence → 3) marketing/customer intervention → 4) outcome learning → 5) controlled autonomy.
**Editions:** SME (EU-hosted SaaS, no-code, prebuilt taxonomies, 1-week setup) vs. Enterprise
(VPC/on-prem, SSO/SCIM, policy engine, local-model routing, MCP). **Industry packs:** B2B industrial,
SaaS, e-commerce, financial services.

**EU/Germany grounding:** Bitkom 2026 (~41% of firms ≥20 staff use AI; 93% prefer a German AI provider);
KfW (SME adoption gap) → justifies EU-first deployment flexibility + the SME/enterprise split.

**Explicitly out (build via integration, not in-house):** survey collection, full CDP, full
campaign-delivery, full product-management. Integrate Qualtrics/Medallia/zenloop, Adobe/Braze/HubSpot,
Jira/Productboard/Linear.

### Thesis guardrails (do NOT let the vision cross these before September)
- ❌ Do **not** adopt the proposal's stack (FastAPI/LangGraph/Temporal/Kafka) — keep React + Supabase.
- ❌ Do **not** expand the thesis RQ to the journey + behavioural *comparative experiment* (Models A–D);
  it needs behavioural data + a larger study. **Advisor decision** — park as flagship future work.
- ❌ Do **not** add half-built modules; the thesis contribution stays the four design decisions + the
  learning memory, evaluated qualitatively.
- ✅ Take **now, cheaply:** EU/DACH market evidence (Ch.2), the dual-action framing, "policy-as-code"
  language, and the outcome category line (§6).
