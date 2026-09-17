# Independent review of the CLARA thesis and Claude's revision (ChatGPT, 17 September 2026)

Verbatim text of the review the owner received on 17 September 2026, kept so that the revision contract (`thesis/revisions/2026-09-17-revision-contract.md`) can be checked against its source. The disposition table at the end maps each numbered section of the review to the contract sections that answer it. Local links in the review point at the reviewer's own snapshot and are reproduced as received.

---

**Assessment: a substantial engineering artifact and a promising design-science thesis, but not yet a submission-ready research argument.** Claude improved disclosure and repaired several contradictions. The manuscript still needs a substantive revision that narrows its claims, evaluates its distinctive design more directly, and removes repeated explanation. Another sentence-level polish will not be enough.

Reviewed on 17 September 2026. I read the front matter, Chapters 1–7, the relevant appendices and instruments, the claim ledger, and selected evaluation and measurement code. The manuscript is the revision at commit `2f426f4298a81905f7bd3d8833d1bee93ad77ee7` on `claude/relaxed-babbage-of6lum`. The branch was one commit ahead when retrieved, but that later commit changed only `CLAUDE.md` and `docs/product/core-problems.md`. Source links below point to the local review snapshot. I checked selected important references against primary sources and reproduced all 24 committed Holm-adjustment rows from the input CSVs. I did not run new model experiments, verify all bibliography entries, inspect the private raw datasets, or assess the rendered Word document's pagination. The manuscript itself has not been edited.

**1. What is already good, and what Claude's reply gets right**

The thesis has a worthwhile central problem: recording an action is insufficient evidence that a customer problem improved. Making outcome definitions, measurement provenance, human authority and reusable conclusions explicit is a coherent design contribution. The implementation is considerably more developed than a conceptual prototype, and the separation between deterministic controls and model-generated suggestions is clearly explained.

Other strengths deserve preserving: reporting negative results; retaining the production model's weak severity results; distinguishing the production pipeline from a generic prompt; acknowledging that the German evaluation texts are constructed or translated paraphrases; recording the exposed validation split; and acknowledging the author's commercial interest. These are valuable research practices. They should become a small number of clear statements rather than recurring arguments for the thesis's honesty.

Claude was right to prioritise practitioner evidence and human labels, to qualify the unadjusted sentiment result, and to move revision history out of the chapters. It also correctly distinguished completed work from scripts for studies that still require data or people. The new scripts are preparation, not additional research evidence.

Several parts of its advice need qualification:

| Claude's position | My assessment |
|---|---|
| The evaluation currently says "nothing" about the artifact's purpose | Too strong. Demonstration and analytical or regression checks can support DSR claims about implementability and enforced properties. They do not establish practitioner utility, better decisions, or business outcomes. |
| After a 3% cut, the remaining length is content | Unconvincing. Much of the remaining content duplicates other sections, describes obsolete versions, or supplies background that does little work in the argument. |
| TF-IDF plus logistic regression is a weak baseline | It is a legitimate, useful baseline. Add embeddings only if this tests a retained research claim; adding models should not displace evaluation of closure and memory. |
| Roughly 400 signals, or 50–100 German reviews, will solve the sample problem | These are planning suggestions, not justified sample-size requirements. Precision depends on class prevalence, paired disagreements, clustering and the intended claim. The relevant fairness denominator is escalation-worthy cases in each comparable stratum. |
| Annotation takes two to three hours per rater | Do not plan around this without a pilot. There are five fields, 51 owner labels, construct ambiguities and adjudication. Time a small blind pilot first. |
| A retrospective event study is a natural experiment | A dated event alone does not establish a natural experiment. It can provide a useful retrospective observational demonstration; causal interpretation requires a defensible intervention assignment and counterfactual. |
| A matched 2×2 rerun is ready | The script still batches the generic condition at 1 and production at the requested size, normally 25. It cannot isolate a prompt-only effect as currently described. |

**2. The most important revision: make the research claim match the evidence**

Locations: [§1.3–1.7](/home/fogu/Documents/ChatGPT/CLARA/review-sources/thesis-2026-09-17/thesis/manuscript/01_introduction.md:26), [§3.3](/home/fogu/Documents/ChatGPT/CLARA/review-sources/thesis-2026-09-17/thesis/manuscript/03_methodology.md:30), [§5A.6](/home/fogu/Documents/ChatGPT/CLARA/review-sources/thesis-2026-09-17/thesis/manuscript/05_evaluation_results.md:137), [Chapter 7](/home/fogu/Documents/ChatGPT/CLARA/review-sources/thesis-2026-09-17/thesis/manuscript/07_conclusion.md:5).

The opening says the artifact closes the loop, the evaluation establishes its precondition, and the conclusion demonstrates usefulness. Yet there is no live outcome contract, no practitioner study, no measured benefit of memory decay, and no justified operational accuracy threshold. These are different claims and require different evidence.

Use one evidence map throughout:

| Question or claim | What is currently supported | What remains open |
|---|---|---|
| RQ1: governed feedback-to-action architecture | Implemented architecture, worked demonstration and tested mechanisms | Whether it improves decisions or resolves customer problems in practice |
| RQ2: governance | Specified and tested approval/provenance controls; a documented regulatory interpretation | Whether people understand the controls, catch errors and accept their cost |
| RQ3a: enrichment | Agreement with star-rating proxies and assistant-authored references on the particular corpus | Agreement with independent expert judgement and performance on natural deployment data |
| RQ3b: escalation disparities | Descriptive differences across source strata, with an eight-case German-source positive stratum | A language effect, comparative fairness ranking, or evidence of parity |
| RQ4: practitioner experience | Protocol and instruments | All empirical answers: no study has run |
| DP2: perishable memory | Implemented decay; limited, model-dependent evidence that retrieval changes output | Whether decay changes retrieval appropriately or improves recommendations |

"Exploratory" describes how collected evidence is analysed. At zero participants the status is **not conducted**, and RQ4 is **unanswered**. The conclusion must not call the qualitative study a small-N study that "establishes design validity." Appendix D's statement that H1 and H8 are "perception-tested" also needs removal.

There is a second problem with the traceability matrix: implementing a unified platform does not demonstrate the population claim that organisations suffer fragmentation; classifying journey stages does not test whether journey stage materially changes prioritisation; and a classifier ablation does not compare bounded workflows with autonomous agents. Mark these as literature-supported motivation, implementation evidence, or pending empirical propositions as appropriate. Preserve the distinction between a **problem claim** and evidence that its proposed solution exists.

Suggested central claim:

> This thesis develops and examines CLARA, a governed workflow that links customer feedback to approved actions, recorded outcome measurements and reusable learning records. The evaluation establishes selected technical properties and bounded enrichment performance. Whether these mechanisms improve practitioner decisions and customer outcomes remains to be established.

That is a credible research claim. It can be strengthened when the outstanding studies are completed.

**3. Closure currently combines three different meanings**

Locations: [§3.5.5](/home/fogu/Documents/ChatGPT/CLARA/review-sources/thesis-2026-09-17/thesis/manuscript/03_methodology.md:73), [§4.8](/home/fogu/Documents/ChatGPT/CLARA/review-sources/thesis-2026-09-17/thesis/manuscript/04_artifact.md:116), [§4.9](/home/fogu/Documents/ChatGPT/CLARA/review-sources/thesis-2026-09-17/thesis/manuscript/04_artifact.md:149).

Separate **delivery of an action**, **observed target attainment**, and **evidence that the action caused improvement**. The code itself makes a useful distinction: an instrumented closing checkpoint can return `loop_closed` on target attainment while explicitly saying attribution is not established. That is the behaviour the thesis should explain. See [the verdict implementation](/home/fogu/Documents/ChatGPT/CLARA/review-sources/thesis-2026-09-17/apps/api/app/services/outcome_engine.py:725).

The worked example creates a Jira backlog item, starts measuring, and later records "adding CSV export reduced reporting complaints." Creating the ticket does not implement CSV export. For that example, the substantive intervention is the verified release of the feature. Dispatch is an appropriate intervention time only when dispatch itself delivers the hypothesised remedy.

Rewrite the example to show: ticket dispatch → verified implementation date → fixed observation window → observed recurrence result → qualified reviewer conclusion. If no implementation date is available, report what was observed after dispatch without attributing it to an unverified fix. The example must also say which steps were actually executed and which are illustrative.

The statistic needs similar precision. The scheduled checkpoint compares a rate over a frozen interval with its baseline; §3.5.5 explicitly grades that D. The detail view separately computes a cumulative ITS estimate. §4.4 and §4.8 still describe checkpoint measurement as ITS scoring. Show these as two rows in one table, with their estimand, time window, grade and role in closure. Explain why the contract's observed-rate threshold and the ITS counterfactual effect are different quantities.

The refusal claim is too broad. Having at least 10 pre-days and 5 post-days is an implementation minimum, not proof of statistical power or trustworthy uncertainty. The thesis acknowledges plain OLS errors, autocorrelation, sparse counts and a detectability heuristic that materially understates the actual estimator's requirement. Say "refuses below its minimum data requirements," rather than claiming it generally refuses whenever underpowered. A fitted model alone is not a validated causal design. The cited [Bernal, Cummins and Gasparrini tutorial](https://academic.oup.com/ije/article/46/1/348/2622842) discusses seasonality, autocorrelation and time-varying confounding; these belong in the model's interpretation, not only a later limitations paragraph.

For a real-data demonstration, report observed counts, collection coverage, a justified denominator, intervention timing, competing events, residual diagnostics and sensitivity to window choice. The implementation already has a volume-adjusted share diagnostic and placebo refit; show and discuss them. A decline in complaints can reflect fewer users, a failed connector, changed solicitation, changed theme assignment, or regression to the mean. "No observations" must remain distinguishable from "complete observation with zero complaints."

Do not state that randomisation is impossible or unethical for all remediation actions. Restrict that rationale to the deployments and interventions considered. Do not call a percentage-worsening guardrail a statistical non-inferiority test unless such a test has actually been implemented.

**4. Validate the reference data before expanding it**

Locations: [§3.7](/home/fogu/Documents/ChatGPT/CLARA/review-sources/thesis-2026-09-17/thesis/manuscript/03_methodology.md:115), [§5A.1](/home/fogu/Documents/ChatGPT/CLARA/review-sources/thesis-2026-09-17/thesis/manuscript/05_evaluation_results.md:9).

Claude's recommendation for human annotation is sound, but it should begin with provenance and construct checks. The collection, paraphrasing, de-identification and seed labelling all came from an assistant-led research session and were used as delivered. Labelling those paraphrases more carefully will improve reference reliability; it will not establish that every source was faithfully collected or that the transformation preserved sentiment and severity.

Recommended sequence:

1. Audit a stratified sample against source material: original text, stable source identifier, date, original language, star rating, paraphrase and transformation record. Expand the audit if discrepancies appear. Preserve provenance without publishing unnecessary personal data.
2. Define sentiment, risk and urgency separately. A star rating measures overall reported satisfaction; mixed textual sentiment and urgent operational risk are different constructs. Call stars a human-origin proxy, not a reference statistically independent of the text.
3. Pilot the annotation rubric and owner inventory with independent human raters. Record their role, instructions, model exposure and timing. Permit "ambiguous," "multiple valid owners," or "insufficient context" where justified.
4. Freeze the rubric, label independently, report agreement before adjudication, and preserve adjudication reasons. Report risk and urgency separately before considering any mapping.
5. Rescore saved model predictions to assess agreement with the new labels. If comparing **human-trained** supervised baselines, also retrain the classical model within each training fold. Its saved predictions were trained against the old seed labels; rescoring alone evaluates a seed-trained model against humans.

The 51-owner inventory over 188 cases particularly needs conceptual cleanup. Several teams may reasonably own an issue, and public reviews may not identify a company's internal accountability structure. Low exact agreement can reflect ambiguity in the reference as well as bad routing. For the actual deployment condition, measure valid-destination rate, acceptable-owner agreement, abstention and correction burden.

Do not call the supplied-inventory score a proven upper bound on free-form production performance. It is a different, constrained task that may be easier; no formal bound or matched semantic comparison has been established.

Additional German data is worthwhile only if German-language performance remains a central claim. Collect natural text with comparable sectors, sources and severity strata in both languages. Simply adding German reviews from a new sector perpetuates the confound. The number of escalation-positive cases, not total reviews, determines recall precision.

**5. The statistical narrative still needs one consistent interpretation**

Locations: [§5A.3–5A.4.2](/home/fogu/Documents/ChatGPT/CLARA/review-sources/thesis-2026-09-17/thesis/manuscript/05_evaluation_results.md:48), [adjustment results](/home/fogu/Documents/ChatGPT/CLARA/review-sources/thesis-2026-09-17/thesis/evaluation/results/paired_tests_holm.csv).

The Holm arithmetic reproduces. The unresolved issue is which family supports each claim. The same learned-model versus GLM-production risk comparison is adjusted to **0.038** in the "ordering" family and **0.053** in the "configuration" family. The generic-versus-learned sentiment comparison is **0.087** in one and **0.174** in the other. Both calculations can be mathematically correct, but a reader needs a reason for the family choice and one consistent conclusion.

As a sensitivity check, combining the nine unique comparisons reported across the two families within each task gives approximately **0.174** for the sentiment comparison and **0.064** for the learned-versus-GLM-production risk comparison, recalculated from the discordant counts. This is an illustrative alternative family, not a claim that it is the uniquely required correction. It demonstrates why the research question must determine the family, rather than the CSV location.

Treat the historical comparisons as exploratory, describe the retrospective adjustment as retrospective, and report effect sizes and paired uncertainty. A primary hypothesis cannot be pre-declared after seeing its results. For a future confirmatory study, specify the primary contrast, sample, mapping and correction policy before examining the new outcomes. The fairness tests and adaptively developed exemplar comparisons also need to be explicitly outside any claim that the new Holm correction makes the whole evaluation confirmatory.

Specific wording to change:

- §5A.4 still says "The sentiment lead is" statistically separable and cites the unadjusted 0.029.
- §5A.4.2 still refers to "the significant paired lead" without the correction qualification.
- "Replicated" across the same items should become "stable across repeated model runs on this corpus."
- "Tying," "matches," "at least as good," and "close to sufficient" need care: a non-significant difference does not establish equivalence or deployment adequacy.
- "Earns its cost" is not supported without cost and latency measurement or decision-value evidence.
- Discordant counts are inputs to uncertainty calculations; they are not a replacement for an interval on the paired difference.

Put a single main table near the start of the results: predictor/configuration, task, reference standard, eligible n, answered n, accuracy with interval, macro-F1, and escalation recall. Report routing's six missing outputs in both coverage and end-to-end accuracy. Move detailed pairwise tests and run histories to the appendix. Present the production-default configuration first, with the historical generic experiment as a comparator.

Stratified cross-validation is reasonable for the small supervised baseline. It establishes within-corpus performance, not cross-sector transfer. Check duplicates and source clusters before claiming no leakage; use grouped or leave-sector-out sensitivity only where support is sufficient, and report uncertainty rather than turning three brands into a population claim.

**6. Test whether the controls help people, especially with missed cases**

Locations: [§5A.4.1](/home/fogu/Documents/ChatGPT/CLARA/review-sources/thesis-2026-09-17/thesis/manuscript/05_evaluation_results.md:81), [§3.6](/home/fogu/Documents/ChatGPT/CLARA/review-sources/thesis-2026-09-17/thesis/manuscript/03_methodology.md:97), [interview guide](/home/fogu/Documents/ChatGPT/CLARA/review-sources/thesis-2026-09-17/thesis/instruments/interview_guide.md:18).

The statement that approval makes this pipeline "safe to deploy at all" is not demonstrated. A gate can catch a bad proposed action only if the person sees it and recognises the error. It does not automatically recover serious complaints that the model failed to escalate. Against the current seed labels, production escalates 28 of 50 qualifying cases: 22 do not pass that threshold. The construct caveat matters, but it does not justify assuming the gate resolves this concern.

The practitioner study should test the distinctive design rather than only elicit positive reactions to it. Include cases with a plausible wrong owner, a serious low-ranked complaint, a D-grade target-met result, an inconclusive measurement, and a stale learning that sounds relevant but is inapplicable. Record whether participants identify the problem, correct or reject the recommendation, and distinguish observed improvement from causation. Ask for the evidence that supports their decision.

Where feasible, compare equivalent scenarios using the ordinary ticket workflow and the contract/evidence view; counterbalance order. A small comparison can illuminate mechanisms and trade-offs without supporting a population-level causal claim. Report facilitator assistance and correction burden. Pilot the session: four tasks, current-practice questions, trust discussion, consent and questionnaires are unlikely to fit comfortably into 25–30 minutes without shallow responses.

Keep SUS standard. Call the modified PU/PEOU items TAM-derived rather than treating their validation as automatically inherited. The custom trust items cover different constructs, so report them individually unless there is a defensible reason to aggregate them. A threshold of 12 interviews does not magically turn evidence confirmatory, and 40 convenience-survey responses do not confirm broad organisational hypotheses. Use the existing tiers as reporting conventions, not guarantees of validity. Replace survey "confirmed" with "descriptive support in this sample."

The survey still refers to approving only riskier actions, while the artifact requires approval for every external action. It also offers an email field despite calling the instrument anonymous. Move recruitment contact collection to a separate, unlinked form and keep distribution copy out of the bound thesis appendix.

**7. Memory decay needs its own evaluation, and the negative result needs visibility**

Locations: [§4.3.2](/home/fogu/Documents/ChatGPT/CLARA/review-sources/thesis-2026-09-17/thesis/manuscript/04_artifact.md:43), [§5A.7](/home/fogu/Documents/ChatGPT/CLARA/review-sources/thesis-2026-09-17/thesis/manuscript/05_evaluation_results.md:164), [DP2 in §6.1](/home/fogu/Documents/ChatGPT/CLARA/review-sources/thesis-2026-09-17/thesis/manuscript/06_discussion.md:11).

DP2 repeats the favourable 21%→71% remedy-inclusion result. The more recent production-default probe did not reproduce the benefit: reported coverage fell from 40% to 32%, with one of four themes adopting the remedy. These probes are tiny, and the old item-level record is missing. The appropriate conclusion is **retrieval influence is model-dependent and benefit is unestablished**. It should appear beside the positive result wherever DP2 is assessed.

Retrieving a remedy and causing a model to repeat it can demonstrate influence. It can also demonstrate anchoring on bad advice. Neither result validates decay. Conduct a bounded comparison of no memory, memory without decay, and memory with decay on scenarios containing relevant current evidence, superseded evidence and irrelevant but recent evidence. Use the deployed model and blind human assessments of recommendation appropriateness, unsupported causal assertions and handling of stale evidence. Freeze the scenarios and test several justified half-lives as sensitivity analyses; avoid selecting the most flattering half-life on the final test.

Distinguish **strength of the historical evidence**, **current applicability**, and **retrieval weight**. Multiplying a score by an age penalty changes a heuristic; it does not establish that the score is a calibrated probability that the remedy still works. Keep the original provenance and evidence strength inspectable even when retrieval priority decays.

This experiment tests a core contribution more directly than adding several more model benchmarks.

**8. Narrow the literature review and repair the evidence-to-claim links**

Locations: [§2.1.2](/home/fogu/Documents/ChatGPT/CLARA/review-sources/thesis-2026-09-17/thesis/manuscript/02_literature_review.md:17), [§2.9–2.14](/home/fogu/Documents/ChatGPT/CLARA/review-sources/thesis-2026-09-17/thesis/manuscript/02_literature_review.md:203), [§6.3](/home/fogu/Documents/ChatGPT/CLARA/review-sources/thesis-2026-09-17/thesis/manuscript/06_discussion.md:39).

Chapter 2 reads too often as a catalogue: author, year, journal, contribution, short application to CLARA. Replace this with synthesis around four design problems: turning feedback into accountable action; evaluating enrichment under imperfect labels; interpreting outcome evidence; and reusing knowledge under changing conditions. Integrate governance and human oversight where those problems require them.

The important citation problem is claim fit, not just missing DOIs. Bone et al. is repeatedly used as evidence of an insight-action gap and missing operational mechanisms. Its field experiments examine how feedback solicitation changes purchasing, especially the effect of positively framed questions. That supports the narrower point that collecting feedback can itself affect behaviour; it does not establish that the studied firms lacked routing and execution mechanisms, as §2.1.2 says. Replace those attributions or supply an appropriate source. See [the authors' paper](https://paulfombelle.com/wp-content/uploads/2016/12/jmr.14.0232.pdf).

Hill et al.'s figures are real, but "directly supports" CLARA's taxonomy architecture is too strong. Its deductive-coding comparison used an expert-adjudicated healthcare reference and reported high raw agreement alongside κ≈0.34 in a low-prevalence setting. It supplies an analogy and a reason to verify coding, not validation of CLARA's taxonomy design. See [the original study](https://journals.plos.org/digitalhealth/article?id=10.1371/journal.pdig.0001189).

The universal novelty claims remain: "no single tool," "owned by no one," and "no design-science artifact." A broad narrative review cannot establish universal absence. State the databases and dates searched, search terms, selection criteria, relevant close precedents and the limits of coverage. Then use "we did not identify, within the reviewed literature and documentation, an evaluated system combining…" Keep the claim about the integration and the design knowledge it yields.

The new competitor table improves presentation but retains the old evidential problem. LLM agreement over vendor pages does not verify implementation. Change "verified" to "documented in the sources reviewed," "refuted" to the specific conflicting documentation, and "no" to "not documented" when absence has not been established. Compare named products on dated, directly cited capabilities; avoid assigning universal capabilities to whole market categories. A missing public description is not proof that a competitor lacks a feature.

The industry review also calls the evidence independent and describes sources as having no stake in the academic account. These sources have commercial and sampling interests. Retain a brief, attributed account of practitioner motivation; remove repeated market-size figures, acquisitions and vendor announcements that do not change a design decision.

**9. A specific regulatory argument still needs correction**

Locations: [§4.4 transparency](/home/fogu/Documents/ChatGPT/CLARA/review-sources/thesis-2026-09-17/thesis/manuscript/04_artifact.md:81), [§4.9](/home/fogu/Documents/ChatGPT/CLARA/review-sources/thesis-2026-09-17/thesis/manuscript/04_artifact.md:132), [Appendix B](/home/fogu/Documents/ChatGPT/CLARA/review-sources/thesis-2026-09-17/thesis/manuscript/appendices/B_eu_ai_act_gdpr_mapping.md:25).

The manuscript makes Article 50(2) depend on the deployer publishing the generated text and excludes internal tickets/messages categorically. The Commission distinguishes provider-side machine-readable marking under 50(2) from disclosure for public-interest text under 50(4). Its guidance also describes specific, conditional exclusions, including certain business/industrial uses; "internal" alone is not a sufficient analysis. Assess the precise output, the system's provider/deployer role and any relevant exclusion, rather than importing 50(4)'s publication condition into 50(2). See the [Commission's current Article 50 guidance](https://digital-strategy.ec.europa.eu/en/faqs/transparency-obligations-under-article-50-ai-act).

Keep one dated regulatory analysis in Appendix B. In the main text, describe what the controls do and why the research adopts them. Appendix C should likewise distinguish a possible lawful basis and technical safeguards from a controller's completed assessment. Public availability, pseudonymisation and a human approval step do not by themselves establish all the legal conclusions asserted. This review identifies a problem in the thesis's reasoning; it is not a complete compliance assessment.

**10. Claude's new experimental tooling needs two methodological adjustments**

The [matrix runner](/home/fogu/Documents/ChatGPT/CLARA/review-sources/thesis-2026-09-17/thesis/evaluation/run_matrix.py:51) explicitly uses one item per generic call and the requested batch size for production. I inspected its generated plan without executing model calls: the four cells were 1, 25, 1, 25. Either standardise batching, wrappers, post-processing and item order for a prompt-only experiment, or call the factor **pipeline configuration** and acknowledge its constituent differences. A 2×2 design also requires an analysis of contrasts/interaction if it is meant to explain whether model choice changes the pipeline effect. Four independently scored runs alone do not supply that analysis.

The [annotation rescorer](/home/fogu/Documents/ChatGPT/CLARA/review-sources/thesis-2026-09-17/thesis/evaluation/annotation_kit.py:387) usefully scores saved predictions against new gold. It does not retrain the supervised baseline or transform a repeatedly consulted validation set into an untouched test set. State exactly which question rescoring answers. Audit the scripts' outputs against that question before describing the additional studies as ready to run.

**11. Concrete corrections still needed after Claude's consistency pass**

| Location | Remaining issue | Revision |
|---|---|---|
| Front matter, acknowledgements | Thanks practitioners who gave evaluation interviews, although none have run | Remove that clause until true |
| Front matter, conflict/AI-use declarations | "Externally-labelled" can imply independent human validation; disclosure omits the central use of AI in corpus and label generation | Explicitly disclose assistant collection, paraphrasing, seed labelling and AI review; qualify verification claims to work actually completed |
| Front matter, data availability | Public sources are conflated with accessible, reproducible derived datasets | Supply an examiner package or precise access procedure for derived data, transformations, labels and immutable prediction artifacts |
| §1.7 | Undefined "accuracy bar"; practitioner evidence called exploratory | Remove the operational-adequacy claim; mark practitioner work not conducted |
| §1.10 | Chapter map still includes omitted anomaly/churn/dashboard material | Update after restructuring |
| §2.1 headings | Jumps from 2.1.3 to 2.1.5 | Renumber |
| §2.13 and §3.5.4 | Describe human adjudication as an adopted safeguard, although the semantic scoring was not executed | Use planned status or remove from the completed-methods account |
| §3.8 | "Expert labels" | "Reference labels," with their actual provenance |
| §3.10 | Double-coding is described as an operating safeguard despite no interviews | Describe as planned |
| §4.5 | Says theme assignments are scored | Theme is not scored in this thesis harness; correct the fields and configuration |
| §4.8 | Calls paraphrased evidence "verbatim"; implies theme/action seeds are scored | Label the paraphrase; identify only the evaluated fields |
| §4.8 and §4.4 | Checkpoints described as fitting/scoring ITS | Distinguish scheduled rate comparisons from the detail-view ITS estimate |
| §4.9 | Suggests insufficient ITS data always prevents closure | Reconcile with instrumented target-attainment closure at grade D; define exactly what is refused |
| §5A.4 / §5A.5 | "Across both languages" / "pooled multilingual corpus" | All classifier inputs here are English paraphrases |
| §5A.4.1 | Claims macro-F1 is inflated by rare classes, although the supported-class values are higher | Remove the unsupported direction claim; explain the changed label set and population |
| §5A.7 and Appendix G.2 | Calls the in-repo golden set independent of the artifact despite co-development and label revision | Treat as a development/validation benchmark, not independent confirmation |
| §5B.4.5 | T2 still says "Create a governed rule (auto vs approval)" | Match the updated action-governance task in the interview guide |
| §5B.4.4 | Old SUS shorthand and missing friction items disagree with methods/instruments | Use one scoring/reporting specification; include items 13–14 |
| §6.1 DP2 / §6.4 | Favourable old retrieval number receives prominence without production-default failure | Report the model-dependent result together |
| §6.5 | A single 624-word paragraph combines five work programmes | Replace with an ordered, bounded research agenda |
| Chapter 7 | Calls zero-participant work a study that establishes design validity; calls the artifact useful | State unanswered questions and demonstrated capabilities explicitly |
| Appendix D, concluding "Reading" | H1/H8 called perception-tested; repeats most of Chapter 5 | Correct the status and delete the duplicated results narrative |
| Appendix G.8 versus "deployed" claims | Migration 017 is recorded as not applied to production at the snapshot | Distinguish implemented/tested at commit from verified deployed at date |
| Contents | Lists Appendices A–E despite F and G | Update the complete appendix list |

These are substantive reasons that passing 15 string/consistency checks is insufficient evidence of manuscript readiness.

**12. A concrete plan to make it shorter and less repetitive**

My reproducible whitespace count is **43,023 words for Chapters 1–7**, or **43,951 including front matter**. This counts Markdown/table tokens; it differs from Claude's count and is not a Word submission count. I have not verified an OPIT word limit, so the target below is editorial, not an institutional requirement.

| Chapter | Current words | Suggested target | Main action |
|---|---:|---:|---|
| 1 Introduction | 2,928 | 1,800 | One problem statement, one aim/RQ table, one evidence-status table; merge artifact/contribution/scope repetition |
| 2 Literature | 10,308 | 5,500 | Organise by research problems; compress generic histories and vendor survey; integrate "recent developments" into relevant themes |
| 3 Methodology | 6,331 | 4,700 | One data-provenance account, one completed-methods account; move run history and instrument instructions |
| 4 Artifact | 6,970 | 4,500 | Centre outcome contracts, memory and human authority; move endpoint/schema/security chronology; retain one accurate worked example |
| 5 Results | 10,277 | 7,000 | Production-first tables; move repeated caveats and historical runs; replace blank practitioner scaffold with actual findings or a short not-conducted statement |
| 6 Discussion | 5,245 | 3,700 | Interpret rather than repeat; one principle/evidence/boundary table, one limitations account, short future-work priorities |
| 7 Conclusion | 964 | 700 | Answer RQs directly; no miniature rerun of Chapter 5 |
| **Total** | **43,023** | **27,900** | **About 35% shorter** |

The target leaves room for essential new findings. It is not a quota to meet by hiding necessary methods. In particular, §2.5 on experimentation is only about 103 words and is relevant to the central argument: strengthen its connection to outcome inference rather than cutting it automatically. Claude estimated roughly 3,500 words across §2.3–2.7; the current snapshot contains about 1,669 by the same whitespace measure. The larger savings are elsewhere too.

Give each repeated topic one main home:

| Topic | Main home | Other occurrences |
|---|---|---|
| Feedback-to-action gap | §1.2 and focused literature synthesis | One-sentence reminder only |
| Source data, paraphrases and seed labels | §3.7 | A short table note in results; implications in discussion |
| Disputed second-rater provenance | Appendix G.1 | One sentence in §3.7; do not repeat its full statistics as supportive human evidence |
| Validation-split and sequential-testing history | Appendix G | One clear limitation beside benchmark results |
| Final predictor comparison | Chapter 5 | No full metric lists in introduction, discussion, conclusion and traceability matrix |
| Outcome measurement | §3.5.5 and the core architecture section | A diagram/table and cross-reference |
| Regulatory interpretation | Appendix B | Actual design obligations/commitments summarised in the chapters |
| AI-detector experiment | A compact methods/results subsection or technical appendix | One sentence where it motivates the refusal principle |
| Development reviews and defect chronology | One short DSR iteration table plus repository history | Remove §5A.8; condense §4.7/§4.9; slim Appendix F |

Long paragraphs remain despite the earlier edit: §3.7 has a 601-word paragraph; §5A.7 has 474- and 534-word paragraphs; §6.5 has 624 words; and the main conclusion paragraph has 550. Splitting these alone is insufficient: each contains material with several different purposes. Separate result, interpretation and limitation, then remove what belongs elsewhere.

Replace repeated assertions such as "the honest reading," "the plain reading," "rather than smoothing over," "not a convenient interpretation," and "the only basis…to be believed" with direct statements of evidence. Reduce bold and italic emphasis. Remove most journal names from running literature prose. Use model names and dataset labels consistently. Name new design principles by their mechanism, and present each as context → proposed mechanism → expected consequence → evidence → boundary, rather than declaring transferability as established.

**13. Example replacement passages**

**A shorter abstract, reflecting the evidence now available:**

> Customer-feedback systems can record that an action was taken without establishing whether the underlying problem improved. This design-science study develops CLARA, a workflow linking customer signals to human-approved actions, outcome contracts and reusable learning records. The design combines versioned measurement terms, explicit evidence grades and confidence-weighted retrieval of past conclusions.
>
> Evaluation examines technical controls and feedback enrichment on 188 English paraphrases of public reviews from three sectors. Against star-rating proxies on 153 items, the production configurations achieved sentiment agreement of 0.83–0.84, compared with 0.78 for a TF-IDF classifier. Against assistant-authored risk labels on 106 items, production agreement was 0.50–0.59; disagreement may reflect differences between the risk and urgency constructs. Source-stratum escalation comparisons are exploratory because language and sector are confounded and one positive stratum contains only eight cases.
>
> The artifact demonstrates an implementable approach to governed workflow execution and explicit outcome provenance. Practitioner usefulness, benefit from memory decay and improvement in real customer outcomes have not been established. The contribution is the integrated design and a set of provisional design principles, together with evidence about the limits of the enrichment and measurement components.

**Replace the long second-rating discussion in §3.7 with:**

> The corpus was collected, paraphrased and labelled in an assistant-led research session and has not been independently human-adjudicated. Customer star ratings provide a human-origin sentiment proxy; the remaining seeds are assistant judgements. A second rating of 40 risk-labelled items is available, but its independent human provenance is unresolved, so it is not used as human validation. Appendix G.1 documents the provenance and agreement statistics.

**Replace DP2's current evidential claim with:**

> CLARA reduces a learning's retrieval weight with age using an explicit half-life. Small probes show that retrieval can alter recommendations on GLM-5.2, but this effect did not reproduce on the production-default model. The probes did not vary learning age or assess recommendation quality. Decay is therefore an implemented design hypothesis whose benefit remains untested.

**Replace the worked example's causal ending with:**

> Creating the Jira item records operational delivery. If the feature is subsequently released, a reviewer records its implementation date and the observation window runs from that intervention. A qualifying checkpoint can show that complaint inflow met the contracted target. Without a defensible causal design, the learning records an observed reduction after release and its limitations, rather than asserting that the feature caused the reduction.

**Replace the conclusion's claim about RQ4 with:**

> RQ4 remains unanswered because the practitioner study was not conducted. The current evidence supports the feasibility of the architecture and bounded agreement with reference labels, but does not establish practitioner usefulness or improved customer outcomes.

**14. Recommended order of work**

First, choose a defensible submission scope with the supervisor: either complete a bounded practitioner evaluation or explicitly narrow the thesis to technical design and evaluation. Check the programme handbook and supervisor's expectations for length; ECTS alone does not establish the word limit Claude assumed.

Then correct the evidence map, closure definitions, remaining factual contradictions, statistical interpretation and cited-source overreach. These changes need no new participant data and should happen before circulating another polished draft.

Next, validate the data and perform the independent annotation study. In parallel with recruitment, prepare a small evaluation of closure interpretation and memory decay. A retrospective real series is useful if a defensible event, adequate coverage and interpretable comparison exist; a refused estimate is valid evidence of behaviour, but not proof of usefulness.

Only then decide whether a matched pipeline/model rerun, embeddings baseline or self-hosted-model experiment is necessary for a claim the thesis retains. Freeze a fresh test set and analysis plan before any confirmatory extension. Do not expand the project merely because a script now exists.

Finally, restructure to approximately 28,000–30,000 main-text words, replace placeholders with findings or explicit absence statements, verify important citations, freeze the submitted artifact/version, rebuild Word, and inspect figures, tables, equations, references and pagination. The finished paper should let an examiner understand the contribution and its limits without reconstructing the project's review history.

---

## Disposition (17 September 2026): where each review section is answered

| Review section | Contract section(s) | Disposition |
|---|---|---|
| 1, table of qualifications | 1, 4 (tooling row in 7) | Accepted; the matrix rerun is renamed a configuration × model design; sample-size figures and the annotation time estimate are not repeated in the manuscript. |
| 2, evidence map and central claim | 1, 2, 9 | Adopted verbatim; Appendix D statuses re-labelled; "perception-tested" banned. |
| 3, closure | 3, 9 | Adopted; two-measurement table; refusal wording; worsening-threshold guardrail; narrowed randomisation rationale; worked example rewritten. |
| 4, reference data | 6, 7 (tooling: `--retrain-ml`), Chapter 6 agenda | Adopted as the agenda's first item; stars called a human-origin proxy; supplied-inventory score not an upper bound. |
| 5, statistics | 4, 7 (tooling) | One retrospective family of the ten unique comparisons per task, paired-difference intervals, wording rules; production-first main table. |
| 6, controls and the practitioner study | 6, 7 (instruments), Chapter 6 agenda | Gate framing; survey Q1e and contact form; adversarial stimuli recorded as protocol additions for sessions that run; tiers kept as reporting conventions with "supported in this sample". |
| 7, memory decay | 2, 9, Chapter 6 agenda | DP2 replacement text plus the simulation caveat; bounded decay comparison named in the agenda. |
| 8, literature | 6, 7 (Chapter 2 map) | Chapter 2 reorganised around four design problems; Bone and Hill re-attributed; novelty qualifier; competitor wording. |
| 9, regulatory | 7 (Appendix B and C rows) | Article 50(2)/(4) distinction corrected; Appendix C wording. |
| 10, tooling | 7 (tooling row) | Design string, `--retrain-ml`, docstrings stating the question each script answers. |
| 11, concrete corrections | 6, 7 | Every row assigned to a file owner. |
| 12, length | 7 | Ceilings sum to 28,000 for Chapters 1 to 7; one main home per topic. |
| 13, replacement passages | 9 | Adopted with two amendments (κ figures retained in §3.7 for a pinned test; abstract states that the production-versus-TF-IDF difference is not distinguishable after correction). |
| 14, order of work | 1 | Scope narrowed to technical design and bounded evaluation; sessions that run before submission are reported under the pre-registered tiers. |
