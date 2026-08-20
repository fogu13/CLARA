# Chapter 5: Evaluation and Results

This chapter reports the two evaluation streams introduced in Chapter 3. Section 5A presents the **quantitative gold-set evaluation** of the artifact's enrichment and routing pipeline against human-assigned labels on real customer feedback (RQ3a accuracy, RQ3b equity). Section 5B presents the **qualitative practitioner study** (RQ4): its protocol, instruments, and analysis plan, with results sections held open for the interview data being collected. All §5A numbers are computed by the reproducible harness in `evaluation/` and read from `evaluation/results/`; none are hand-entered.

---

## 5A. Quantitative Gold-Set Evaluation (RQ3a, RQ3b)

### 5A.1 The corpus

The evaluation corpus is **188 real, publicly-sourced, paraphrased and de-identified customer signals** drawn from three sectors and labelled independently of the artifact (Chapter 3, §3.7):

| Sector | Dataset | Signals | Dominant language |
|---|---|---:|---|
| Food delivery | Lieferando | 82 | DE / EN |
| Fintech / brokerage | Trade Republic | 67 | EN |
| B2B industrial | Henkel (adhesives) | 39 | DE |
| **Total** | | **188** | EN 102 · DE 84 · other 2 |

Signals originate from Trustpilot (70), the Apple App Store (38), Reddit (33), Amazon (26), Google Play (10), and DIY retailers Hornbach and OBI (11). Gold labels are present as follows. **Scored in this thesis:** a 1–5 **star rating** on 153 signals (the independent sentiment reference) and a closed-set **risk/severity** label on 106 signals (Trade Republic and Henkel). **Scored separately, under a supplied taxonomy (§5A.4.1):** **journey stage** (27 distinct values) and **recommended owner** (51). **Present but not scored:** **theme** (176 distinct values) and **recommended action** (184), each labelled on all 188 signals. (Coverage and cardinality are stated separately here deliberately: journey stage, for instance, has complete coverage over only 27 values, so it is closed-set in practice despite being authored free-form.) Theme and recommended action are not scored because the semantic-agreement procedure designed for open-vocabulary fields (Chapter 3, §3.5.2) was not executed. Extending the evaluation to them is future work (§6.5), and §5A makes no accuracy claim about either.

### 5A.2 Method recap

![Figure 5.1: Real-data gold-set evaluation harness: three real datasets and their human seed labels feed three predictors (rule-based, classical ML, and the LLM path), scored against the same gold labels.](../diagrams/rendered/07_evaluation_pipeline.png)

Three predictors are compared on the same gold labels, forming a deliberate progression from no learning to full contextual reasoning:

1. **Rule-based floor.** A bilingual (EN/DE) lexicon sentiment classifier and a keyword severity classifier (the pre-LLM tradition; Taboada et al., 2011). No training, fully transparent.
2. **Classical ML.** TF-IDF character n-grams + Logistic Regression, evaluated by stratified 5-fold cross-validation with out-of-fold predictions (no train/test leakage), class-balanced to handle the skew toward negative feedback.
3. **LLM enrichment path.** The artifact's own enrichment reasoning, mirroring the platform's production prompt, so the gold set scores the same reasoning the product uses. It was run against this harness's 188-signal seed-label corpus on 4 August 2026 (`evaluation/predict_llm.py`, model GLM-5.2 at temperature 0), enriching **188 of 188** signals; the scored results appear in the tables below. One disclosure attaches to the run's provenance. An earlier execution attempt had failed *silently*: the model gateway rejected the client library's default User-Agent header with an HTTP 403, and the script exited with status 0 after writing an empty results file, so a green exit code stood in for a run that had produced nothing. The defect was treated as a finding about the harness rather than quietly rerun. The fix (a User-Agent header, and a hard failure on an empty result set) is committed alongside the results, and the episode is reported here because a harness that can report success on no output is exactly the failure mode §4.9 warns against: declared checks are not enforced checks until they fail loudly. Separately, the artifact carries its own **committed, live LLM evaluation**, a curated bilingual golden set (§5A.7), whose results are reported as convergent evidence in §5A.7 rather than merged into these tables, because the gold standards differ.

Sentiment is scored against the star-rating gold (1–2 → negative, 3 → neutral, 4–5 → positive), a non-circular reference because it is independent of the text the classifier reads.

### 5A.3 Sentiment results

| Predictor | n | Accuracy | Macro-F1 | Weighted-F1 |
|---|---:|---:|---:|---:|
| Rule-based lexicon (floor) | 153 | 0.37 | 0.37 | 0.48 |
| TF-IDF + Logistic Regression (5-fold CV) | 153 | 0.78 | 0.52 | 0.76 |
| LLM enrichment path | 153 | **0.86** | **0.67** | **0.86** |

The classical-ML baseline improves accuracy by **41 points** and macro-F1 by **15 points** over the lexicon floor. The per-class and confusion analysis explains why the floor is weak: of 94 gold-negative signals the lexicon labels **58 as neutral**, because the *paraphrased, operational* phrasing of real feedback ("Transaction history cannot be exported to CSV") carries few overt sentiment words. Lexicon precision on the negative class is high (0.94) but recall is low (0.34). When an explicit negative word appears the call is reliable, but most real complaints are stated descriptively. This is a substantive finding, not merely a baseline artefact: **surface-lexicon sentiment is inadequate for operational customer feedback, which motivates contextual models.** The neutral class is small (9 of 153) and noisy, and it depresses macro-F1 for all three methods.

The LLM path extends the progression rather than merely matching it. Accuracy rises from 0.78 to **0.86** and macro-F1 from 0.52 to **0.67** over the classical baseline, a further 8-point accuracy gain on top of the 41-point gain the learned model already delivered. The macro-F1 improvement is the more informative of the two, since it is not inflated by the dominant negative class: the contextual model recovers minority-class signal that the character n-grams do not. The ordering floor → learned → contextual is therefore monotone on both metrics, which is the result the loop's precondition argument requires.

![Figure 5.2: Sentiment confusion matrix, lexicon floor vs star-rating gold (n = 153). Gold-negative signals are frequently mislabelled neutral.](../evaluation/results/sentiment_confusion.png)

### 5A.4 Risk / severity results

Risk is scored on the 106 signals (Trade Republic + Henkel) carrying a closed-set `risk_seed` label {low, medium, high, critical}.

| Predictor | n | Accuracy | Macro-F1 | Weighted-F1 |
|---|---:|---:|---:|---:|
| Keyword severity (floor) | 106 | 0.41 | 0.26 | 0.30 |
| TF-IDF + Logistic Regression (5-fold CV) | 106 | 0.68 | 0.65 | 0.67 |
| LLM enrichment path | 106 | **0.72** | **0.68** | **0.71** |

The keyword floor collapses almost everything to "low": it correctly tags all 36 low-risk signals but mislabels 18 of 23 high and 19 of 27 critical signals as low, because severity in paraphrased text is rarely signalled by a fixed keyword. Its one strength is precision on "critical" (1.00). When an unambiguous critical term ("blocked", "fraud") fires, it is right, but recall is only 0.15. Collapsed to a binary **escalate (high+critical) vs routine** decision, the floor reaches 0.59 accuracy and 0.50 macro-F1, still weak. The classical-ML model recovers most of the lost signal (macro-F1 0.26 → **0.65**), learning sector-specific severity cues from character n-grams across both languages.

The LLM path leads on risk as well (accuracy 0.72, macro-F1 0.68), but its margin over the classical baseline is **markedly slimmer than on sentiment**: three macro-F1 points here against fifteen there. This asymmetry is worth stating rather than smoothing over, and it qualifies the case for contextual triage. Severity in this corpus is carried substantially by lexical markers that character n-grams already capture once they are *learned* rather than hand-listed, so the additional benefit of contextual reasoning is small. Sentiment, by contrast, depends on reading descriptively-phrased dissatisfaction that has no reliable surface form. For a deployment weighing cost, latency and model sovereignty (§4.4), the defensible reading is that a learned local model is close to sufficient for severity routing, while the contextual path earns its cost on sentiment. The corpus is modest (n = 106) and the two models' intervals are not separated by a significance test, so this is reported as an observed ordering, not a demonstrated superiority.

![Figure 5.3: Risk/severity confusion matrix, keyword floor vs risk_seed gold (n = 106). The floor collapses most signals to "low".](../evaluation/results/risk_confusion.png)

#### 5A.4.1 Routing fields: journey stage and recommended owner

The two *routing* fields are evaluated separately, under a different configuration, and the difference must be stated before the numbers. Journey stage and owner are open-vocabulary in the production prompt, and the model's free-form vocabulary barely intersects the corpus gold: roughly fifteen percent of journey values and one percent of owner values match by exact string. Scored that way, the result would measure wording, not routing. They are therefore scored from a **constrained run** (`predict_llm.py --constrained`) in which the corpus taxonomy is supplied as a closed inventory and the model must select from it. This is the closed-set treatment §3.5.2 designed for exactly these two fields, and it mirrors the deployed condition: a real workspace configures its owner list and journey taxonomy rather than inventing labels per signal. It is nevertheless a *different configuration* from the production-config run behind §5A.3–5A.4, so it is reported separately and never merged with those tables. The model obeyed the inventory completely (the in-vocabulary rate is 100% for both fields), so the comparison is valid on its own terms.

A majority-class floor is reported alongside, because accuracy over 27 or 51 classes is uninterpretable without one:

| Field | Classes | Majority-class floor | LLM (inventory supplied) | Macro-F1 |
|---|---:|---:|---:|---:|
| Journey stage | 27 | 0.20 | **0.59** | 0.50 |
| Recommended owner | 51 | 0.15 | **0.40** | 0.32 |

Both clear their floor by a wide margin, journey stage by roughly three times and owner by about two and a half, so the pipeline is extracting real routing signal rather than guessing the modal class. **Neither is accurate enough to route autonomously.** An owner assignment that is correct two times in five would, as unattended automation, misroute the majority of problems. The plain reading is that these fields are useful as a *draft* a human accepts or corrects, and useless as an unattended decision. That is not a convenient interpretation; it is the one the numbers force. It also independently supports the artifact's central design commitment (§4.4, DP4): the mandatory approval gate is not friction added to an otherwise-reliable pipeline, it is the control that makes a pipeline of this accuracy safe to deploy at all. A system that routed on these numbers without review would fail quietly and often.

Three limits. Six of the 188 signals were lost to endpoint errors during the run, so n is 182. The macro-F1 figures are computed across all classes and are inflated by rare labels that happen to be predicted correctly; restricted to the classes with at least five gold examples, macro-F1 falls to 0.28 for journey stage and 0.18 for owner, and those are the more conservative figures. And the supplied-inventory condition makes the task easier than production free-form generation, so these numbers are an *upper* bound on the production pipeline's routing accuracy, not an estimate of it.

### 5A.5 Generalisation across sectors and languages

Lexicon sentiment macro-F1 varies by slice: B2B industrial 0.45, food delivery 0.34, fintech 0.28; German 0.42, English 0.27. This confirms that a fixed lexicon transfers poorly and unevenly across domains and languages (relevant to H3 and to the fairness concern that some languages are triaged less reliably; Mehrabi et al., 2021). The classical-ML model, trained across the pooled multilingual corpus with character n-grams, is more uniform. The per-slice tables are written to `evaluation/results/sentiment_by_sector.csv` and `sentiment_by_language.csv`.

The LLM path was scored on the same slices, with the same minimum of five signals per slice. It improves **every** sector slice, and it improves the weakest most: fintech, the floor's worst, roughly doubles (macro-F1 0.28 → 0.58).

**Per-language comparison on this corpus is confounded, and is not made here.** Language is not independent of sector: the B2B industrial stratum is entirely German (37 of 38 signals), fintech is overwhelmingly English (58 of 66), and only food delivery carries both languages in comparable numbers (37 German / 34 English). An aggregate "German versus English" figure would therefore largely restate the sector composition. The two metrics also disagree in direction. Aggregated, German leads on macro-F1 (0.67 vs 0.61) while English leads on accuracy (0.91 vs 0.81), which is what one expects when macro-F1 is computed over slices with sparse minority classes. Within the one sector that supports a like-for-like comparison, food delivery, LLM accuracy is near parity (German 0.919, English 0.941) while the macro-F1 gap is wide and unstable (0.840 vs 0.328) on roughly thirty signals per cell. **Accuracy is therefore the metric reported for language, and no claim of a narrowing or widening cross-language classification gap is made.** The composition table and both metrics are written to `evaluation/results/summary.json`, so the confound is inspectable rather than asserted.

What *can* be claimed, and matters more for the loop, concerns **escalation** rather than classification. The relevant fairness criterion is equal opportunity, the recall on signals whose gold label warrants escalation (high or critical), because it conditions on the gold label and is therefore not distorted by the very different base rates across strata (German 17.8%, English 69.5%):

| Escalation recall (gold-escalate signals) | n | Keyword floor | LLM path |
|---|---:|---:|---:|
| German | 8 | **0.0%** | 87.5% |
| English | 41 | 19.5% | 87.8% |

The keyword floor escalates **not one** of the eight genuinely critical German signals, while catching a fifth of the English ones. The LLM path reaches near-exact parity (87.5% against 87.8%). This is the substantive Responsible-AI finding of §5A. An uneven triage layer does not merely score worse; it means some customers' problems are systematically less likely to reach a human at all. That is a fairness property of the *loop*, not of a classifier (§6.2), and one that the choice of triage method largely determines. Two limits bound it. The German gold-escalate stratum is only eight signals, so its recall estimate is imprecise (a 95% interval on 7 of 8 spans roughly 47–100%). And language remains confounded with dataset on this subset too, German being largely the B2B stratum and English largely fintech. The claim is therefore that method choice governs escalation equity on this corpus, not that parity is established in general. The hallucination heuristic also remains English-scope by construction (§3.5.2).

![Figure 5.4: Baseline sentiment macro-F1 by sector, showing uneven transfer of a fixed lexicon across domains.](../evaluation/results/f1_breakdown.png) *(The figure shows the lexicon floor; the LLM path's per-slice values are tabulated above.)*

### 5A.6 Interpretation and threats

The results support a clear, defensible claim for RQ3a: **the accuracy of the loop's automated triage is strongly method-dependent, and a learned model is necessary.** Naive lexical methods fail on real, paraphrased, multilingual feedback, while even a lightweight learned model reaches usable accuracy (sentiment 0.78, risk 0.68), and the artifact's contextual LLM path is the strongest predictor on both tasks (sentiment 0.86, risk 0.72).

The gain is not uniform, and the shape of it is itself the finding. Contextual reasoning buys a great deal on sentiment (macro-F1 0.52 → 0.67) and comparatively little on severity (0.65 → 0.68), while changing escalation equity substantially: the keyword floor escalates none of the eight critical German signals, and the LLM path reaches near-parity with English (§5A.5). Read together, these say that the loop's precondition is satisfied by more than one method, and that the choice among them is a design trade-off (cost, latency and model sovereignty against a measurable accuracy margin) rather than a foregone conclusion. That is a more useful result for a design-science thesis than a single dominant number would have been, because it hands a deployer an actual decision rather than an instruction.

Two limits on the comparison should be stated. The three predictors are scored on identical gold labels, but only the classical model is cross-validated. The lexicon requires no training, and the LLM path was run once, at temperature 0, without repetition, so run-to-run variation for the contextual path is uncharacterised here (the in-repo evaluation, which does test this, observes a 96–99% sentiment band across same-day runs, §5A.7). And the LLM path scores 0.86 on this corpus against 0.97 on the artifact's own curated golden set. The divergence is expected, and it is why the two streams are never merged: this harness scores against an independent star-rating proxy, the in-repo set against curated labels. The lower number here is the more conservative estimate and the one that should be quoted.

What §5A tests, and what it does not, should be stated plainly. It evaluates a **precondition** of the contribution, namely that the enrichment feeding the loop is good enough to act on, not the contribution itself. The thesis's distinctive claims (DP1 measured closure; DP2 perishable learning memory; §1.2) are evaluated by *design demonstration* (Chapter 4) and *practitioner perception* (§5B), not by these numbers. That an outcome contract or a decaying memory improves real decisions is argued and demonstrated, not yet measured. The reading of §5A is therefore narrow but firm: the triage layer the loop depends on clears the bar a learned model can reach, and would otherwise fail. The threats of Chapter 3, §3.5.4 further bound these claims: the gold labels are defensible human judgements rather than an oracle, and the corpus is modest (188 signals) and balanced rather than population-representative. A scope limit must also be stated plainly: **this harness scores sentiment and risk/severity in the production configuration, and journey stage and owner only under a supplied taxonomy (§5A.4.1).** The `theme_seed` and `recommended_action_seed` fields carry gold labels for the full corpus but are not scored at all. The semantic-agreement procedure designed for open-vocabulary fields in §3.5.2 has not been executed and remains future work (§6.5). Claims about the pipeline's accuracy extend no further than those four fields. The headline numbers characterise the pipeline *on this corpus* and are not population estimates.

### 5A.7 Convergent evidence from the artifact's in-repo evaluation

This section reports results produced by the artifact's own evaluation infrastructure, committed in its repository (`apps/api/app/evals/`: a curated golden set, initially 60 cases and since grown to a **100-case bilingual set**, a live runner with within-run A/B testing, a real-data evaluator, and a results ledger, `history.jsonl`). They are reported here as **convergent evidence**, not as entries in the §5A.3–5A.4 tables, because the gold standards differ: the in-repo golden set is curated, whereas this chapter's harness scores 188 externally seed-labelled signals. The numbers below are read from the committed ledger (the run of 3 July 2026, the two runs of 17 July 2026, and the published run of 18 July 2026, all on model GLM-5.2 at temperature 0) and the corresponding supervisor reports; none are re-computed here.

The section reports the set's full growth trajectory (60 → 80 → 100 cases) rather than only its endpoint, because the intermediate stages contain a negative result (an underpowered urgency comparison, reported as such at each stage until it cleared significance), and the discipline of not re-rolling that result is itself part of the method (§3.5).

**Golden-set results, 3 July 2026 (n = 60; dated history).** On the original 60-case set the live LLM path achieved **96.7% sentiment accuracy**, **81.7% urgency accuracy**, and **80.8% theme matching by meaning** (45.8% by exact string; the gap between the two quantifies how much theme agreement is semantic rather than lexical, and it directly supports this chapter's decision to score open-vocabulary fields semantically). The reported hallucination rate was **6.7%** in that run (0% in several earlier runs), with zero PII leaks across the ledger.

**Growth to an 80-case bilingual set (July 2026).** Because the corpus behind the golden set turned out to contain no natural German texts (the three public datasets' texts are English paraphrases), the set was extended with **20 authored German items** (ids `eval-061`–`080`), written to cover registers the English items do not (formal *Sie*, informal *du*, irony, and compound nouns) and labelled under the same documented labelling rules. The new items were then **adversarially verified by two independent skeptic agents**: 19 of 20 labels were confirmed, and exactly one dispute was accepted (`eval-078`, urgency low → medium). The German stratum is split 14 optimisation / 6 held-out, and every item in the set now carries a language field (60 en / 20 de). The disclosure, carried in the artifact's model card and repeated here: **the German stratum is authored, not naturally occurring**. This is a deliberate, documented compromise, made because no natural German customer texts were locally available.

**Baseline run, 17 July 2026, 07:24 UTC (n = 80).** With the production configuration (few-shot exemplars on) and bootstrap 95% confidence intervals: sentiment **97.50%** (CI 94–100%), urgency **85.00%** (CI 76–92%), tag F1 (fuzzy) **74.24%**, hallucination **1.25%**, PII leaks **0**. Per language: EN (n = 60) sentiment 98.33%, urgency 86.67%, exact-tag-set 23.33%; DE (n = 20) sentiment 95.00%, urgency 80.00%, exact-tag-set **0%**. The in-run paired A/B (exemplars off vs on, identical items, McNemar) showed exact-tag-set 7.5% → 17.5% (p = 0.039, significant) and urgency 82.5% → 85.0% (p = 0.727, not significant).

**One eval-improve iteration: gap → root cause → intervention.** The baseline exposed a clear German gap, most visibly the 0% German exact-tag-set score. The diagnosis: the few-shot exemplar set was **English-only** (7 exemplars), so the urgency rubric (unrecoverable loss happening *now* = critical) and the `positive_trend` praise-tag convention never transferred to German. The intervention: **two fresh German exemplars**, one unrecoverable-payment-loss critical case and one praise case carrying `positive_trend` + `good_support`, deliberately *not* drawn from golden-set texts, so no train/test leakage is introduced.

**Post-intervention run, 17 July 2026, 15:22 UTC (n = 80).** Sentiment **97.50%** (CI 94–100%), urgency **86.25%** (CI 79–94%), tag F1 (fuzzy) **80.17%**, hallucination **2.50%** (one additional English item; within noise; disclosed), PII **0**. Per language: EN 98.33% / 86.67% / 33.33%; DE 95.00% / 85.00% / 15.00% (sentiment / urgency / exact-tag-set). The **in-run paired A/B is the designed inference**: exact-tag-set off 8.75% → on 28.75%, McNemar **p = 0.001** (significant; 19 items gained, 3 lost); urgency off 81.25% → on 86.25%, p = 0.219, directionally positive but **underpowered at n = 80**, so no urgency gain is claimed. Sentiment is unchanged (p = 1.0). The DE/EN urgency gap narrowed from 6.7 pp to 1.7 pp, with English metrics unregressed. Cross-run comparisons (3 July vs 17 July, baseline vs post-intervention) carry a **model-noise caveat**: GLM-5.2 is non-deterministic even at temperature 0, which is why the significance test is paired *within* a single run.

**Growth to 100 cases and the published run, 18 July 2026 (n = 100; the published snapshot).** The set was extended to **100 items (72 EN / 28 DE)**, and the German stratum was completed to the same two-tag rubric the English items follow: 13 additive second tags and 2 auditor corrections, adversarially audited (11 of 13 confirmed, 2 improved). Under the production configuration this run reports sentiment **97%** (bootstrap 95% CI 93–100%), urgency **90%** (CI 84–95%), and tag F1 (fuzzy) **82.7%**. Per language, DE (n = 28) 96.4% sentiment / 89.3% urgency and EN (n = 72) 97.2% / 90.3%, a DE/EN urgency gap of one percentage point. This is the snapshot published to the model card (`published_metrics.json`) and served at `GET /model-card/metrics`.

Two disclosures travel with it. First, **the urgency exemplar effect reaches significance at this sample size**: the in-run paired A/B moves urgency from 83% to 90%, McNemar **p = 0.039**, the third consecutive run in which the effect is significant, first achieved after adding a churn-musing calibration exemplar. The earlier n = 80 result (p = 0.219) was not a different finding but an underpowered one, and it is retained above rather than replaced. Second, the German tag metrics **improve partly by construction**: several tags added in the rubric completion name themes the model was already predicting correctly against under-labelled gold. That is the fix working as intended, and it means tag metrics at n = 100 are **not comparable** to the n = 80 snapshot; both the improvement and its cause are recorded in the published provenance notes. Sentiment sits in a 96–99% band across three same-day runs, reported as measured and never re-rolled.

**Scope limits of the harness itself.** The hallucination heuristic is **English-scope only by construction**. It token-grounds predicted tags against the English tag vocabulary, which falsely flags correct tags on German text, so non-English items are excluded from that metric rather than reported as a meaningless number. This, like the authored-German provenance, is disclosed in the artifact's model card.

**Published metrics as a mechanism.** An explicit `--publish` flag writes a committed snapshot (`published_metrics.json`: n, per-language accuracies with denominators, confidence intervals, dataset date, and provenance notes) that is served by the API (`GET /model-card/metrics`) and rendered in the product's model card. The numbers users see are the committed evaluation outputs, not marketing copy, and every published figure is traceable to a dated run.

**Cross-industry real-data run.** Run over the *same three public datasets* as this chapter (Trade Republic, Henkel, Lieferando), the pipeline reaches **≈90% sentiment accuracy against the star rating as proxy ground truth** (the same non-circular reference §5A.3 uses), and assigned urgency rises consistently as star ratings fall in all three sectors. Industry-appropriate vocabularies emerge with no fine-tuning or per-sector configuration, which is the empirical basis for the per-industry-profiles design decision (§4.3.5).

**Learning-loop influence, measured.** Feeding stored learnings back into synthesis raised the share of a past learning's remedy appearing in the new recommendation from **21% to 71%** (66.7% adoption; alignment lift 0.503 against a same-run noise floor that absorbs model jitter). This is direct evidence that the perishable-memory mechanism (DP2) steers recommendations rather than decorating them.

**Boundaries, as committed in the repository's own evaluation notes.** (i) The exemplar effect was reported at every sample size, including where it failed to reach significance. At 60 cases the lift was **not statistically significant** (within-run McNemar, p ≈ 1.0 on sentiment, urgency, and exact-tag): an underpowered sample, not a demonstrated gain. After the extension to 80 bilingual cases and the German-exemplar intervention, the exact-tag-set lift became significant (p = 0.001) while the urgency lift stayed underpowered (p = 0.219) and was **not claimed at that stage**. At 100 cases the urgency lift reaches significance as well (83% → 90%, p = 0.039, three consecutive runs). The claim is therefore made now and was withheld before, on the same test, which is the point of reporting the trajectory rather than the endpoint. (ii) The evaluation confronted **model non-determinism**: GLM-5.2 produces slightly different outputs across identical runs even at temperature 0, which is why the harness compares conditions *within* a single run and tests significance rather than comparing across runs. (iii) The German gold stratum is **authored rather than naturally occurring**, and the hallucination metric is **English-scope only** (see above); both are disclosed in the model card. (iv) The p-value trajectory across n = 60/80/100 constitutes **sequential testing without alpha spending**. The urgency claim therefore rests on its replication (three consecutive significant runs at n = 100), not on the first crossing, and future confirmatory claims freeze n in advance (§3.5.3). Relatedly, the committed evaluation ledger (`history.jsonl`) ends at the 3 July run. The 17–18 July runs cited here persisted only their published snapshot (`published_metrics.json`) and provenance notes, a reproducibility gap disclosed rather than repaired retroactively; the loop now commits ledger rows and reports alongside accepted changes. (v) Most importantly, the **outcome data behind the learning loop is still simulated**. Adoption shows the loop steers recommendations, but whether the steered remedy is *better* requires a live outcome contract on real data, the single most important open step (§6.5). Taken together with §5A.3–5A.6, the two evidence streams converge on the same conclusion from different gold standards: contextual LLM triage clears the accuracy bar the loop requires, while the loop's *outcome* claim remains to be earned on real data.

### 5A.8 An external-review episode as a naturalistic ex-post evaluation input

A third, unplanned evaluation input arose during the write-up window (16–17 July 2026): **two independent LLM-based strategic reviews** of the deployed artifact were obtained, one product/market-focused, yielding 17 concrete findings, and one strategy-focused, scoring the artifact on dimensions and rating, i.a., "scientific validity" 2/10 and "security" 3/10. It is reported here modestly, as an additional *naturalistic, ex-post* evaluation input to a further design cycle (in the sense of the evaluation-method taxonomy of Prat et al., 2015, and the iterative design cycles of Hevner, 2007), not as a validated review method, and with no claim of methodological novelty. The reviewers are LLMs, the episode is singular, and it was not part of the registered evaluation plan.

The response followed the same verify-before-believe discipline as the rest of the chapter. **45 of the reviews' factual claims were adversarially verified** against the codebase and the live deployment by nine independent read-only verification agents: approximately **27 confirmed, 13 partially correct, 2 refuted, and 1 unverifiable**. The surviving findings were ranked into a 38-item response plan; **20 pull requests** (17 July) implemented every code-reachable item; and a read-only post-deploy verification script of **17 live checks** confirmed all fixes serving in production (**17/17**, 17 July). Two recommendations were rejected with documented reasons (building survey capture; configurable autonomy levels).

Two observations bound the weight this episode can carry. First, the reviews were **substantially right about the trust and credibility layer**, the critique that motivated much of the measurement-rigor and governance hardening reported elsewhere in this thesis. Second, they were **materially wrong about several "missing" capabilities that in fact existed** (alerting/digests, the MCP server, seeded policy templates, drafted legal documents, and interrupted-time-series estimates with confidence intervals), because the reviewers could only see the *deployed surface*, not the repository behind it. The refuted claims are therefore themselves a finding: an external evaluation of an artifact is an evaluation of what the artifact *shows*, and capabilities that are built but not surfaced are, for evaluative purposes, absent. That asymmetry (genuine gaps confirmed, invisible strengths misjudged) is what makes such a review useful as naturalistic input and unreliable as a verdict.

---

## 5B. Qualitative Practitioner Study (RQ4)

### 5B.0 Two evidence sources: in-depth interviews and a breadth survey

RQ4 is addressed by two complementary instruments. The **in-depth interviews and task sessions** (12–15 participants; §5B.2) are the *primary* evidence: they carry the prototype-reaction and task-metric findings that only observation can provide. A short, anonymous **supplementary survey** (instrument in Appendix A; distributed via practitioner communities on Reddit and LinkedIn) adds *breadth*, confirming the current-practice and attitude hypotheses (H1, H2, H4, H5, H6, H7, H8) across a larger, shallower sample. The survey is deliberately minimal: a single Likert matrix in which each row is a hypothesis, plus a source-count and a closure-frequency item. It is analysed by a reproducible script (`evaluation/survey_analysis.py`) that reports top-2-box agreement and a confirmed / refine / not-supported verdict per hypothesis. The survey's limits are explicit and bound its weight: it is self-report and attitudinal, its sample is a convenience sample skewed to those platforms, and H6/H7 are measured there as *hypothetical* comfort rather than observed trust, so on those two the interviews remain the stronger test. Survey verdicts are reported below alongside the interview themes and folded into the hypothesis table (§5B.5) and the traceability matrix (Appendix D).

> **‹PLACEHOLDER: survey results: n, response source split (Reddit/LinkedIn), and the per-hypothesis verdict table from `evaluation/results/survey_verdicts.csv`.›**

### 5B.1 Status

The qualitative study is the *primary* evidence for the design's validity with practitioners (Chapter 3, §3.3). Data collection runs over the evaluation window; this section documents the executed protocol and holds the results open. **No interview findings are reported until the data are collected; nothing here is simulated.**

### 5B.2 Protocol (as executed)

Twelve to fifteen practitioners (marketing / product / CX, 2+ years, companies of ~10–500 staff that actively collect feedback) are recruited purposively with role and company-size variation (recruitment materials, Appendix A). Each ~25–30 minute online session has two parts: a semi-structured discussion of current practice (eliciting H1, H2, H5, H8) and a task-based prototype encounter (triage, govern a rule, approve a queued action, inspect a closed-loop measurement), with think-aloud. Sessions are recorded with consent and transcribed. Task success and time-to-action are captured by the facilitator and the platform's `events` telemetry. Participants then complete the SUS and the TAM + trust battery (Appendix A). The full interview and task guide is in Appendix A.

### 5B.3 Analysis plan

Transcripts are analysed by reflexive thematic analysis (Braun & Clarke, 2006) against the codebook in Appendix A, with a double-coded subset and an inter-rater reliability check. SUS is scored 0–100; TAM/trust subscales are summarised descriptively. Findings are mapped to H1–H8.

### 5B.4 Results

*This section is a fill-in scaffold: every table cell and quote-slot below is populated from the interview data once collection is complete. Nothing here is simulated. Cells marked "–" await data; quote-slots are tagged with the codebook code (Appendix A) they evidence.*

#### 5B.4.1 Participants

Target N = 12–15; reported anonymised. (`role` ∈ marketing / product / CX; `size` = approx. headcount band.)

| ID | Role | Sector | Company size | Tenure (yrs) | Session mode |
|----|------|--------|--------------|--------------|--------------|
| P01 | – | – | – | – | interview + tasks |
| P02 | – | – | – | – | – |
| … | … | … | … | … | … |
| P15 | – | – | – | – | – |
| **Summary** | ‹role mix› | ‹sector mix› | ‹size range› | ‹median› | – |

#### 5B.4.2 Current-practice gaps (H1, H2, H5, H8)

For each theme: report **prevalence** ("‹k› of ‹N› participants") and one or two anonymised quotes. Themes follow the codebook's `gap.*` codes.

**Theme: the insight-action gap (`gap.insight_action`, H1).** Prevalence: ‹k/N›.
> ‹P, role›: "…"

**Theme: signal fragmentation (`gap.fragmentation`, H2).** Prevalence: ‹k/N›.
> ‹P, role›: "…"

**Theme: unclear ownership (`gap.ownership`, H5).** Prevalence: ‹k/N›.
> ‹P, role›: "…"

**Theme: no measured closure (`gap.no_closure`, H8).** Prevalence: ‹k/N›.
> ‹P, role›: "…"

**Theme: lost memory of what worked (`gap.memory_loss`, H1/H8).** Prevalence: ‹k/N›.
> ‹P, role›: "…"

#### 5B.4.3 Prototype reaction: usefulness, usability, trust (H4, H5, H6, H7; RQ4)

**Prioritisation valued (`value.prioritisation`, H4).** Prevalence: ‹k/N›.
> ‹P, role›: "…"

**Owner routing, valued or distrusted (`value.routing`, H5).** Prevalence: ‹k/N›.
> ‹P, role›: "…"

**Human approval and comfort with automation (`trust.oversight`, H6).** Prevalence: ‹k/N›.
> ‹P, role›: "…"

**Auditability and accountability (`trust.audit`, H7).** Prevalence: ‹k/N›.
> ‹P, role›: "…"

**Wanting to see *why* (`trust.transparency`, H7).** Prevalence: ‹k/N›.
> ‹P, role›: "…"

**Adoption barriers (`barrier.adoption`, RQ4).** Prevalence: ‹k/N›.
> ‹P, role›: "…"

**Usability friction (`usability.friction`, RQ4).** Prevalence: ‹k/N›.
> ‹P, role›: "…"

*‹Add any inductive themes that emerge during coding here, with code, prevalence, and quotes.›*

#### 5B.4.4 Usability and acceptance metrics

**System Usability Scale (0–100).** ‹Insert per-participant scores; report mean, SD, and adjective rating (≈68 = average; >80 = good).›

| Statistic | Value |
|---|---|
| N | – |
| Mean SUS | – |
| SD | – |
| Min / Max | – / – |
| Adjective rating | – |

**Technology Acceptance + Trust (1–7).** ‹Means and SDs per subscale.›

| Subscale | Mean | SD | Items |
|---|---|---|---|
| Perceived Usefulness (PU) | – | – | 1–4 |
| Perceived Ease of Use (PEOU) | – | – | 5–8 |
| Trust / Oversight / Auditability | – | – | 9–12 |

#### 5B.4.5 Task metrics (T1–T4)

From facilitator records and the platform `events` telemetry. Time-to-action reported descriptively (median, range); no significance claim (Chapter 3, §3.10).

| Task | Description | Completion (k/N) | Time-to-action (median; range) |
|------|-------------|------------------|--------------------------------|
| T1 | Triage to most urgent problem | – | – |
| T2 | Create a governed rule (auto vs approval) | – | – |
| T3 | Approve a queued action | – | – |
| T4 | Inspect closure + learning | – | – |

#### 5B.4.6 Inter-rater reliability

‹Report the agreement statistic (e.g., Cohen's κ) on the double-coded subset, the proportion of transcripts double-coded, and how disagreements were reconciled.›

### 5B.5 Hypothesis outcomes

The table below is completed once analysis is done; each hypothesis is marked **confirmed / refined / rejected** with its evidence.

| Hypothesis | Outcome | Evidence |
|---|---|---|
| H1 insight-action gap | ‹pending› | interviews |
| H2 signal fragmentation | ‹pending› | interviews |
| H3 signal-type classifiability | partly addressed by §5A | gold set |
| H4 journey-stage prioritisation | ‹pending› | interviews; gold set |
| H5 owner routing failure | ‹pending› | interviews; gold set |
| H6 ownership/approval → trust | ‹pending› | task sessions; TAM |
| H7 auditability → trust | ‹pending› | task sessions; TAM |
| H8 closure rarely practised, valued when offered | ‹pending› | interviews |
