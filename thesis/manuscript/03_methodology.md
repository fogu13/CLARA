# Chapter 3: Methodology

## 3.1 Research Paradigm: Design Science Research

This thesis adopts **Design Science Research** (DSR), the information-systems research paradigm whose unit of analysis is a purposeful *artifact* built to address a relevant organisational problem and whose contribution is judged by the artifact's utility and by the design knowledge it yields (Hevner, March, Park, & Ram, 2004). DSR is the appropriate paradigm here because the research aim — to operationalise the feedback-to-action loop — is inherently constructive: the central question is not "what is?" but "what works, and why?" The problem (the feedback-to-action gap) is well documented in the behavioural literature (Bone et al., 2017); the open question is *how to design* a system that closes it under governance, which is a design problem.

The work is organised around Hevner's (2007) **three-cycle view**. The *relevance cycle* connects the artifact to its environment: the practitioner problem (Chapter 1), the requirements distilled from VoC practice and the EU regulatory context, and the field evaluation through practitioner interviews. The *rigour cycle* grounds the design in the knowledge base: the literature of Chapter 2 and the DSR and Responsible-AI methodological foundations. The *design cycle* iterates build-and-evaluate internally, refining the artifact across versions until it is fit for evaluation.

![Figure 3.1 — Design Science Research: Hevner's three cycles and the DSRM activities, instantiated for this thesis.](../diagrams/rendered/08_dsr_method.png)

The research activities follow Peffers, Tuunanen, Rothenberger, and Chatterjee's (2007) **Design Science Research Methodology** (DSRM), a problem-centred entry point with six activities, mapped to this thesis as follows:

| DSRM activity | Instantiation in this thesis |
|---|---|
| 1. Problem identification and motivation | The feedback-to-action gap (Ch 1, Ch 2): collection without operationalisation, unmeasured closure, lost memory. |
| 2. Objectives of a solution | A governed Signal → Insight → Action → Learning loop; measured closure; perishable, retrievable organisational memory; EU AI Act / GDPR-aligned oversight (Ch 1, §1.3; Ch 4). |
| 3. Design and development | The artifact and its five non-trivial design decisions (Ch 4). |
| 4. Demonstration | The artifact run end-to-end on real customer feedback; the gold-set pipeline run (Ch 5, §5A). |
| 5. Evaluation | Quantitative accuracy against human labels (§5A) and a qualitative practitioner study with SUS/TAM (§5B). |
| 6. Communication | This thesis and the defence. |

Following Gregor and Hevner (2013), the intended contribution sits at the level of an *improvement* (a better solution to a known problem) and yields both an instantiation (the platform) and nascent design theory (the design principles synthesised in Chapter 6). The artifact was developed as a *search process* (Hevner et al., 2004, Guideline 6): several scope boundaries are themselves findings about what a loop-closure system does and does not need (Ch 4, §4.6).

## 3.2 Research Questions and Hypothesis Mapping

The four research questions (Chapter 1, §1.3) subsume the project's eight working hypotheses. The mapping makes explicit which evidence base addresses each claim:

| Hypothesis | Statement (abbreviated) | Research question | Evidence |
|---|---|---|---|
| H1 (primary) | Teams have insights but struggle to act — the insight-action gap | RQ1, RQ4 | Interviews; artifact demonstration |
| H2 (primary) | Signals are fragmented across sources; unified prioritisation is rare | RQ1, RQ4 | Interviews; artifact design |
| H3 | Signal type affects how reliably feedback can be classified and routed | RQ3 | Gold-set evaluation |
| H4 | Journey stage materially shapes prioritisation | RQ3, RQ4 | Gold-set evaluation; interviews |
| H5 | Routing to the right owner is a recurring failure point | RQ1, RQ3 | Gold-set evaluation (owner field) |
| H6 | Clear ownership and approval improve perceived trust | RQ2, RQ4 | Interviews; task sessions |
| H7 | Stakeholders distrust action they cannot audit | RQ2, RQ4 | Interviews; SUS/TAM |
| H8 | Outcome measurement (closure) is rarely practised and valued when offered | RQ1, RQ4 | Interviews |

Each hypothesis is reported in Chapter 5 as **confirmed**, **refined**, or **rejected** against the evidence. Consistent with the methodological stance below, hypotheses are treated as design propositions to be assessed for plausibility and utility, not as statistical effects to be tested for significance.

## 3.3 Research Design Overview: Mixed Methods

The artifact is evaluated through a **convergent mixed-methods** design that triangulates two independent evidence streams:

- a **quantitative** gold-set evaluation that measures how well the artifact's AI enrichment and routing reproduce human-curated labels on real feedback (objective accuracy; RQ3); and
- a **qualitative** practitioner study — semi-structured interviews and task-based prototype sessions — that captures perceived usefulness, usability, and trust (RQ4), supplemented by standardised SUS and TAM instruments.

The qualitative stream is the *primary* evidence for the design's validity with practitioners; the quantitative stream provides *supporting* evidence that the automated triage underpinning the loop is good enough to be useful. Neither stream alone is sufficient: accuracy without practitioner trust does not close the gap, and practitioner enthusiasm without demonstrated accuracy is not credible. Their convergence (or divergence) is the object of analysis.

## 3.4 Artifact Development Method

The artifact was built in iterative build–evaluate cycles. Deterministic responsibilities (schema validation, rule conflict resolution, audit logging, action execution, outcome scoring) were implemented in code; bounded language-model reasoning (enrichment, synthesis, learning extraction) was confined behind a single provider-agnostic interface, so that model behaviour is isolated, swappable, and testable. Ahead of evaluation the platform was placed under a **feature freeze**: only fixes required by the evaluation (bug fixes, demonstration data, task-metric instrumentation) were permitted, to hold the artifact stable across participants. The platform records an `events` telemetry stream (rule creation, approvals, status advances carrying time-to-action, measurement, learning retrieval), which feeds the task-metric analysis in §5B.

## 3.5 Quantitative Evaluation Design (RQ3)

### 3.5.1 Gold-set construction

The quantitative evaluation treats the artifact's enrichment and routing pipeline as a multi-field classifier and measures agreement with **human-curated reference labels** ("seeds") attached to a corpus of real customer feedback. The corpus is drawn from three publicly-sourced, paraphrased, de-identified datasets (described in §3.7), each shipping a *detailed research table* with the following gold fields per signal: `theme_seed`, `journey_stage_seed`, `recommended_owner_seed`, `recommended_action_seed`, and `risk_seed`, together with `star_rating_1_5`, `language`, and `source`.

A second, complementary reference set lives *inside* the artifact: the curated **golden set** driving the in-repo live evaluation harness, whose results are reported as convergent evidence in Chapter 5 (§5A.7). Initially 60 English cases, it was grown in July 2026 to **80 bilingual items** through 20 German additions (ids `eval-061`–`080`), authored to supply registers absent from the English cases — formal *Sie* and informal *du* address, irony, compound nouns — under the set's documented labelling rules. Because authored items risk encoding the author's own labelling bias, the new stratum passed an explicit **adversarial verification protocol**: two independent skeptic agents re-examined every label against the rules, confirming 19 of 20 and raising exactly one dispute, which was reconciled and accepted (`eval-078`, urgency low → medium). The 20 items follow a **14 optimisation / 6 held-out** split, and a per-item language field now records the set's composition (60 en / 20 de). One provenance fact is disclosed wherever these items' numbers are reported — in the artifact's model card and throughout this thesis: **the German stratum is authored, not naturally occurring**. The three public datasets' texts turned out to be English paraphrases, and no natural German customer texts were locally available, so the German figures characterise performance on constructed, adversarially-verified German, not on field German.

### 3.5.2 Metrics

The five predicted fields differ in cardinality, which dictates the metric:

- **Categorical fields** — journey stage, recommended owner, and risk/severity have small, closed label sets. These are scored with **precision, recall, and macro/micro F1**, with per-class **confusion matrices** to expose systematic mis-routing (e.g., conflating "billing" with "account management").
- **Open-vocabulary fields** — `theme_seed` (and to a degree `recommended_action_seed`) are free-text and high-cardinality, so exact-match accuracy is an unfairly strict metric. These are evaluated by **semantic agreement**: predicted and gold labels are embedded and compared by cosine similarity against a threshold, complemented by a **clustering-agreement** measure (the degree to which signals the artifact groups under one theme share a gold theme). A small human adjudication of borderline cases is used to calibrate the threshold. This open-vocabulary caveat is reported explicitly so that theme-level numbers are not over-interpreted.
- **Sentiment** is cross-checked against the `star_rating_1_5` signal where present (low ratings should not be classified as positive sentiment), giving an independent, non-circular validity check.

One metric is deliberately scope-limited as a **measurement-validity decision**: the in-repo harness's hallucination heuristic token-grounds predicted tags against the *English* tag vocabulary, so applied to German text it would falsely flag correct tags as hallucinated. The metric therefore simply **omits** non-English items — a narrower honest measure is preferred to a broader invalid one — and the artifact's model card discloses the restriction.

### 3.5.3 Breakdowns and baselines

Results are reported **per sector** (fintech, B2B industrial, food delivery) and **per language** (English, German) to assess generalisation and multilingual robustness — a direct test of H3 and a probe of the fairness concern that feedback in some languages or channels may be triaged less reliably (Mehrabi et al., 2021). Per-language results are always reported **stratified, with their denominators** (on the golden set: EN n = 60, DE n = 20) rather than as a blended average, so a small stratum can neither be hidden inside a headline figure nor over-read as a precise estimate. The artifact commits the same discipline in production: an explicit `--publish` flag writes a committed metrics snapshot (`published_metrics.json`, carrying the sample size, each language's accuracy with its denominator, confidence intervals, dataset date, and provenance notes), which the API serves (`GET /model-card/metrics`) and the product's model card renders — so the numbers users see are the numbers the harness wrote. Where feasible, the LLM pipeline is compared against a **simple baseline** (e.g., a keyword/lexicon classifier for journey stage and a majority-class baseline for risk) so that the value added by the language model is quantified rather than assumed. The evaluation is implemented as a reproducible harness (`evaluation/`) that writes all metrics and figures from data, so that no number in §5A is hand-entered.

For the effect of the few-shot exemplar store (Chapter 4), the designed inference is an **in-run paired A/B**: within a single evaluation run, every item is scored with exemplars off and with exemplars on, and the paired difference is tested with **McNemar's test** on the discordant items. This choice is forced by an observed property of the model: it is **non-deterministic even at temperature 0**, so *cross-run* comparisons confound any intervention with model noise — they are reported only with that caveat attached, never as the basis of a significance claim. The resulting tests — including those that remain underpowered at n = 80 and are therefore not claimed — are reported in §5A.7.

### 3.5.4 Threats to validity

The reference labels are themselves human judgements and were authored alongside the datasets, so they are a *defensible* but not an *oracle* ground truth; inter-annotator disagreement on open themes is acknowledged. Looking past this thesis's window, the outcome contracts themselves (Chapter 4) will require **quasi-experimental** evaluation once run on live data — randomisation is infeasible in single-organisation pilots, so interrupted-time-series (segmented regression at the action date) is the minimum credible design, with synthetic difference-in-differences (Arkhangelsky et al., 2021) as the stronger panel-data option; the platform's shipped measurement design implements exactly this (§3.5.5), and naive before/after deltas are explicitly not sufficient (Chapter 6, §6.5). The corpus is modest in size (≈190 labelled qualitative signals) and was assembled to be balanced rather than statistically representative of any population, so accuracy figures characterise the pipeline on this corpus, not a population estimate. Using a language model both to *predict* and (for theme similarity) to *judge* risks a degree of circularity; this is mitigated by the independent star-rating cross-check and by human adjudication of borderline theme matches.

### 3.5.5 Quasi-experimental outcome scoring: interrupted time series

Whether a remediation action *worked* cannot, in a production feedback system, be established by a randomised experiment: the action is applied to every affected customer at once, and withholding a fix from a control group is neither ethical nor commercially acceptable. Naïve before/after deltas, however, are weak evidence — they confound the intervention with trends and seasonality, and field evidence shows well-intentioned recovery actions can have null or even negative effects (Halperin et al., 2022), which is precisely why measurement must be default-on rather than opt-in. The platform therefore scores outcomes with an **interrupted time series (ITS) design using segmented regression** (Wagner, Soumerai, Zhang, & Ross-Degnan, 2002; Bernal, Cummins, & Gasparrini, 2017) — the standard quasi-experimental design when an intervention has a known onset date and no concurrent control is available.

**Model.** For a problem theme with journey/stage-scoped daily signal counts $y_t$ (signals per complete UTC day), with the action executed at day $t_0$:

$$y_t = \beta_0 + \beta_1 t + \beta_2\,\text{post}_t + \beta_3\,(t - t_0)\,\text{post}_t + \varepsilon_t$$

where $\text{post}_t = \mathbb{1}[t \ge t_0]$. $\beta_2$ estimates the immediate **level change**, $\beta_3$ the **slope change**. The reported effect is the model-implied difference at the end of the observation window between the fitted post-intervention trend and the pre-intervention counterfactual, $\hat\Delta = \beta_2 + h\beta_3$ with $h$ the horizon in days, with a 95% confidence interval from $\widehat{\text{Var}}(\beta_2 + h\beta_3) = \sigma^2\!\left[(X'X)^{-1}_{22} + h^2 (X'X)^{-1}_{33} + 2h (X'X)^{-1}_{23}\right]$ and Student-$t$ critical values at $n-4$ degrees of freedom. The estimator is closed-form OLS (normal equations, Gauss–Jordan with partial pivoting), implemented dependency-free in ~60 lines.

**Series construction (bias controls).** Three deliberate rules, each of which measurably biased the estimate when omitted:

1. **Complete UTC days only.** The bucket for the read-time day is a partial observation; entering it at full-day scale drags the endpoint of the fit — Monte-Carlo simulation on a no-effect series (Poisson(10) noise) showed a spurious negative point effect in ~66% of mid-day reads and false CI exclusion of zero in 5–7.5% of reads versus the nominal 2.5%.
2. **The execution day is excluded** from the fit: it mixes pre- and post-intervention exposure, and assigning it to the post segment understates $\beta_2$ and manufactures a spurious $\beta_3$.
3. **No fabricated history.** The pre-window (up to 28 days before execution) is truncated at the first observed signal; days before data existed are not counted as zeros.

**Honesty rules.** With fewer than 10 pre-intervention or 5 post-intervention daily buckets, the system refuses to fit and reports a labelled plain difference of means ("insufficient data for ITS") with **no confidence interval** — an underpowered regression dressed up with a CI would be less honest than a labelled delta. Simulated data is structurally quarantined: outcome series derive exclusively from raw ingested signals, and the simulation harness cannot write measurements.

**Outcome contracts.** The measurement is contracted *before* acting: at approval time the system proposes — applied by default, editable, declinable — a contract with baseline = the trailing signal rate over the observed span (capped at 28 days; dividing by a fixed window would dilute young workspaces' baselines by up to 4×), a 30-day measurement window with a T+7 early read, and a success threshold of a 50% rate reduction. Scheduled re-measurement runs via pg_cron (or an in-process fallback loop) over due checkpoints.

**Grading and bounding the measurement itself.** Three further design elements, added in the July 2026 design cycle, make the *quality* of each measurement legible rather than leaving all readouts to carry equal apparent weight. First, every outcome readout is stamped with an **evidence grade (A–E)** that grades the measurement *design*, not the result: **A** randomised holdout; **B** controlled quasi-experiment (a grade reserved in the taxonomy but not yet produced by the platform); **C** interrupted time series; **D** uncontrolled before/after; **E** manual assertion or unmeasured. The grade is computed from the comparison method together with the **measurement provenance** — every measurement is either *instrumented* (scheduler-computed from signals) or *manual*, manual values are labelled "unverified manual observation" in the UI, and the API route force-stamps manual provenance so it cannot be spoofed by clients — and is rendered identically on the outcome board and the problem detail, so a naive before/after delta can never masquerade as quasi-experimental evidence. Second, declared **guardrail metrics** are actually measured at every checkpoint rather than merely declared: the repeat-signal guardrail — the daily rate of post-execution theme signals from customers already observed in the 28-day pre-window, omitting identity-less signals since they cannot evidence a repeat complainer — is checked for **non-inferiority** against that pre-window baseline; a breach (a relative worsening of more than 20%) informs but never blocks, and a guardrail without a data source surfaces an explicit "no data source" marker instead of silence. Third, at contract proposal time a **detectability note** applies a two-sample Poisson normal-approximation **minimum-detectable-effect heuristic at 80% power**, flagging measurement windows too small to detect the contracted effect *before* approval; it is explicitly labelled a heuristic, not a formal power analysis (Cohen, 1988).

The estimator's known caveats — approximate OLS confidence intervals pending heteroskedasticity-and-autocorrelation-consistent errors, OLS on rates rather than a count GLM, and earliest-execution attribution when actions on one theme overlap — are carried into Chapter 6 (§6.5). The design-to-code mapping is given in Appendix D.

## 3.6 Qualitative Evaluation Design (RQ4)

### 3.6.1 Participants and sampling

The target population is marketing, product, and customer-experience practitioners with **2+ years' experience at companies of roughly 10–500 staff that actively collect customer feedback** — the artifact's intended users. Purposive sampling seeks variation across the three roles and across company size. The recruitment target is **12–15 completed interviews**, over-booked to ~18 to absorb no-shows, recruited via LinkedIn, practitioner communities, and referral chaining (each interviewee is asked for one or two introductions). Recruitment materials are reproduced in Appendix A.

### 3.6.2 Procedure

Each session is a ~20–30 minute online, semi-structured interview in two parts: (i) the participant's *current* practice — how their organisation acts on feedback today and where it stalls (eliciting evidence on H1, H2, H5, H8); and (ii) a *task-based* encounter with the prototype, in which the participant attempts a small set of realistic tasks (e.g., triage a batch of signals, create a governed rule, approve a queued action, inspect a closed-loop measurement). With consent, sessions are audio-recorded and transcribed automatically; recordings are deleted after transcription. Task completion and time-to-action are captured both by facilitator observation and by the platform's `events` telemetry.

### 3.6.3 Instruments

After the task portion, participants complete the **System Usability Scale** (Brooke's ten-item SUS) and a short **Technology Acceptance Model** battery measuring perceived usefulness and perceived ease of use (Davis, 1989), plus targeted trust items addressing auditability and human oversight (H6, H7). The instruments are reproduced in Appendix A.

### 3.6.4 Analysis

Transcripts are analysed by **reflexive thematic analysis** (Braun & Clarke, 2006): familiarisation, open coding, theme construction, review, and definition, maintaining a living codebook (Appendix A). To guard against single-coder bias, a subset of transcripts is double-coded and **inter-rater reliability** computed; disagreements are reconciled and the codebook refined. Themes are then mapped back to H1–H8 and to the research questions. SUS is scored conventionally (0–100) and reported with the standard adjective-rating interpretation; TAM items are summarised descriptively. Given the sample size, all quantitative summaries of the qualitative data are reported as descriptive, not inferential.

## 3.7 Datasets

The evaluation uses **only real, publicly-sourced** customer-feedback datasets; synthetic datasets available in the project were deliberately excluded so that accuracy claims rest on genuine customer language. Three datasets are used, chosen for sector and language diversity:

| Dataset | Sector | Qual. signals | Languages | Gold labels |
|---|---|---|---|---|
| Trade Republic | Fintech / digital brokerage | 68 | EN | theme, journey stage, owner, action, risk |
| Henkel (adhesives) | B2B industrial / consumer goods | 40 | EN, DE | theme, journey stage, owner, action, risk |
| Lieferando | Food delivery | 83 | DE, EN | theme, journey stage, owner, action, risk, response pattern |

Each dataset was assembled from public review and discussion sources (Trustpilot, Google Play, the Apple App Store, Amazon, Reddit). The text is **paraphrased rather than verbatim** and **de-identified** (names, usernames, order numbers, and direct personal details removed), with source URLs and collection dates retained for provenance. Each signal carries human-authored seed labels and, where available, a 1–5 star rating. Crucially for this evaluation, the datasets were labelled **independently of the artifact**, so they function as an external reference rather than a self-graded test.

Their limitations are explicit: public pages expose only sampled, paginated subsets; the corpora are intentionally balanced across positive and negative feedback rather than statistically representative; financial and product claims are unverified customer reports; and B2B industrial feedback is sparse in public sources, so the Henkel set leans on consumer-grade product reviews. These constraints bound the external validity of the quantitative results and are carried into the discussion of limitations (Chapter 6).

## 3.8 Evaluation Criteria

Following Prat, Comyn-Wattiau, and Akoka's (2015) taxonomy of IS-artifact evaluation, the artifact is assessed against a small set of criteria appropriate to its goals: **efficacy and accuracy** (does the enrichment/routing reproduce expert labels? — §5A); **usefulness and ease of use** (do practitioners find it valuable and usable? — §5B, SUS/TAM); **fidelity to the problem** (does it address the documented gap end-to-end? — interviews and demonstration); and **Responsible-AI properties** — human oversight, auditability, and regulatory alignment (assessed by design walkthrough against EU AI Act / GDPR requirements, Appendix B, and by participants' trust ratings). This criterion set operationalises the DSR maxim that an artifact is evaluated by its utility in context, not by novelty alone.

## 3.9 Research Ethics

The qualitative study involves human participants and personal data and is conducted under the OPIT ethics expectations confirmed with the supervisor. Participation is **voluntary**, with the right to skip questions, stop at any time, and withdraw data within a stated window. **Informed consent** (Appendix A) is GDPR-aware: it states the purpose, the recording and automated-transcription procedure, the anonymisation of all reported data and quotes, secure storage, the retention period and deletion, and the lawful basis (consent), and it provides a route to access or erasure. No special-category data is sought. The evaluation datasets are public, paraphrased, and de-identified, and are processed only for academic research. The thesis itself models the Responsible-AI commitments it studies: transparency about method and limitations, and honest reporting of where the artifact underperforms.

## 3.10 Methodological Limitations

Three limitations are intrinsic to the design and stated up front. First, this is a **design-validity** study, not a controlled field experiment: it does not and cannot claim a statistically significant reduction in time-to-action or a causal retention effect, and the early phrasing of RQ-style claims as "significantly reduce time-to-action" was reframed accordingly. Second, the **sample is small** on both axes — ≈190 labelled signals and 12–15 interviews — so findings are characterised as plausible and transferable design knowledge, not population estimates. Third, the researcher is also the artifact's designer, introducing potential **confirmation bias**; this is mitigated by standardised instruments (SUS/TAM), double-coding with inter-rater reliability, an externally-labelled gold set, and a reproducible evaluation harness. These limitations are revisited in Chapter 6.

## 3.11 Threats to Validity

The threats are consolidated here along the four standard dimensions.

- **Construct validity** — the risk that the measures do not capture the constructs. SUS and TAM measure *perceived* usability and usefulness, not whether the loop demonstrably closes faster; this gap between the measured proxy and the claimed effect is acknowledged and is the reason RQ4 is framed as design validity. Sentiment is measured against an *independent* star-rating gold rather than self-graded, reducing construct circularity; the open-vocabulary fields are the weakest point and are reported with explicit caution.
- **Internal validity** — the risk that observed effects have another cause. Because no causal claim is made, the main internal threat is the gold labels themselves: they are human judgements authored alongside the datasets, not an oracle, so agreement figures partly reflect labeller choices. Inter-annotator agreement on the seeds is therefore reported where available, and borderline cases are adjudicated.
- **External validity** — generalisation. The corpus is three sectors and two languages, modest in size and deliberately balanced rather than population-representative; the interview sample is purposive and small. Results transfer as design knowledge, not as population estimates, and the sector/language breakdowns make the limits of transfer explicit.
- **Conclusion validity / reliability** — repeatability. The quantitative pipeline is fully scripted and writes every number from data, so it is exactly reproducible; the qualitative analysis uses a documented codebook, double-coding, and an inter-rater reliability check to make the thematic conclusions auditable rather than idiosyncratic.

## 3.12 Positionality and Reflexivity

The researcher is not a neutral observer: I designed the artifact and have a commercial interest in the venture it underpins (see the Conflict of Interest statement in the front matter). This dual role is the study's most significant bias risk — it could shape which features are tested, how interview questions are framed, and how ambiguous evidence is read. Four standing safeguards address it: (1) the quantitative evaluation uses an **externally-labelled** gold set the researcher did not author; (2) practitioner judgement is captured through **standardised, third-party instruments** (SUS, TAM) rather than bespoke favourable questions; (3) thematic coding is **double-coded with an inter-rater check**, and disconfirming evidence is sought and reported — including the §5A finding that the artifact's triage layer fails without a learned model; and (4) the analysis is **reproducible**, so claims can be re-derived independently. Negative and null findings are reported as first-class results, and where an interpretation is contestable the alternative reading is stated.
