# Draft — supervisor update (manuscript + literature + evaluation status)

**To:** Prof. Zorina Alliata
**Subject:** Thesis update: full manuscript draft, sharpened novelty claim, and the evaluation plan for the pilots

Dear Zorina,

Ahead of our next meeting, a status update in three parts. The short version: the full manuscript
now exists end to end (≈35,000 words, 13 figures, appendices A–E), and I have deliberately
*narrowed* one of my novelty claims after finding prior art myself — I'd rather we surface that now
than an examiner later.

**1. Manuscript status**

All chapters are drafted: introduction, literature review, methodology, artifact, evaluation,
discussion, conclusion, plus appendices (instruments, EU-AI-Act mapping, completed DPIA, a
traceability matrix that states per claim whether it is measured / demonstrated / pending, and the
data-model DDL). The quantitative chapter reports the real-data gold-set results (188 public,
multilingual signals across three sectors) alongside the platform's committed in-repo evaluation as
convergent evidence, with the caveats we discussed stated in the text (the exemplar A/B is not
significant at n=60; outcome data is still simulated). The qualitative section is a complete
protocol with results scaffolding — nothing simulated, slots waiting for the interview data.

**2. Literature: four additions that change the framing**

- *Novelty boundary (the important one).* MemoryBank (Zhong et al., AAAI 2024) already implements
  Ebbinghaus-style decaying memory in LLM systems. My decaying-learning claim is therefore restated
  precisely: the contribution is not decay-based memory per se, but decayed **evidence confidence
  over organisational action-outcomes**, retrieved under governance into future action decisions —
  versus conversational recall. The thesis now cites the prior art itself.
- *Motivation strengthened.* The Uber apology field experiment (Halperin, Ho, List & Muir,
  Economic Journal 2022; ~1.5M customers) shows recovery actions can have null or *negative*
  effects — the strongest empirical case for measuring closure rather than assuming it.
- *Oversight framing modernised.* I now ground the approval gate in meaningful-human-control
  properties (Siebert et al. 2023) and engage Laux & Ruschemeier (2025), who argue Art 14's
  awareness-based oversight won't de-bias humans by itself — which is exactly why the gate adds
  friction, evidence display, and per-decision attribution beyond the Act's minimum.
- *Outcome measurement method.* For the pilot outcome contracts (where RCTs are infeasible) the
  evaluation design is now explicit: interrupted time series at the action date, moving to synthetic
  difference-in-differences (Arkhangelsky et al., AER 2021) as panel data accumulates; naive
  before/after only as a labelled fallback.

**3. The category moved toward the thesis — and the discussion chapter now says so**

Forrester retired its feedback-management Wave in Q1 2026, declaring the *insight* half
commoditised and naming autonomous action and trust as the new axes; Gartner predicts >40% of
agentic-AI projects will be cancelled by 2027 for unclear business value and inadequate risk
controls — the two failure modes outcome contracts and the policy gate address. The competitive
section was rewritten accordingly: no single differentiator survives (Amplitude, Medallia+Ada,
Sprinklr, Dovetail each hold a fragment), so the contribution is stated as the *combination*, and
the same verification standard is applied to my own artifact (outcomes still simulated — said
plainly in §6.4).

**For our meeting, three things I'd value your view on:**
1. The narrowed novelty formulation in §4.3.2 — is the boundary drawn tightly enough?
2. Interview progress and whether the ethics/consent materials need any OPIT-side step I've missed.
3. Whether to grow the golden set to ~100 before the defense so the significance tests are powered,
   or to report n=60 with the McNemar caveat as-is.

A first draft of the defense deck (13 slides, 15–20 min, speaker notes) is attached for whenever
it's useful — no need to review before the meeting.

Best regards,
Elvis
