# Chapter 5: Evaluation and Results

This chapter reports the two evaluation streams introduced in Chapter 3. Section 5A presents the **quantitative gold-set evaluation** of the artifact's enrichment and routing pipeline against human-assigned labels on real customer feedback (RQ3a accuracy, RQ3b equity). Section 5B presents the **qualitative practitioner study** (RQ4): its protocol, instruments, analysis plan and the reporting rule fixed in advance for whatever sample the study reaches (§5B.1), with results sections held open for the interview data. Every metric in the §5A tables is computed by the reproducible harness in `evaluation/` and read from `evaluation/results/`; the few prose figures assembled from those tables (the composition counts of §5A.5) are marked as such where they appear.

---

## 5A. Quantitative Gold-Set Evaluation (RQ3a, RQ3b)

### 5A.1 The corpus

The evaluation corpus is **188 real, publicly-sourced, paraphrased and de-identified customer signals** drawn from three sectors and labelled independently of the artifact (Chapter 3, §3.7):

| Sector | Dataset | Signals | Dominant source language |
|---|---|---:|---|
| Food delivery | Lieferando | 82 | DE / EN |
| Fintech / brokerage | Trade Republic | 67 | EN |
| B2B industrial | Henkel (adhesives) | 39 | DE |
| **Total** | | **188** | EN 102 · DE 84 · other 2 |

Signals originate from Trustpilot (70), the Apple App Store (38), Reddit (33), Amazon (26), Google Play (10), and DIY retailers Hornbach and OBI (11). The `language` field records the **source review's** language; the paraphrased texts themselves are English throughout (§3.7), so per-language figures in this chapter are **source-language strata**, not text-language results. Gold labels are present as follows. **Scored in this thesis:** a 1–5 **star rating** on 153 signals (the independent sentiment reference) and a closed-set **risk/severity** label on 106 signals (Trade Republic and Henkel). **Scored separately, under a supplied taxonomy (§5A.4.1):** **journey stage** (27 distinct values) and **recommended owner** (51). **Present but not scored:** **theme** (176 distinct values) and **recommended action** (184), each labelled on all 188 signals. (Coverage and cardinality are stated separately here deliberately: journey stage, for instance, has complete coverage over only 27 values, so it is closed-set in practice despite being authored free-form.) Theme and recommended action are not scored because the semantic-agreement procedure designed for open-vocabulary fields (Chapter 3, §3.5.2) was not executed. Extending the evaluation to them is future work (§6.5), and §5A makes no accuracy claim about either.

### 5A.2 Method recap

![Figure 5.1: Real-data gold-set evaluation harness: three real datasets and their human seed labels feed three predictors (rule-based, classical ML, and the LLM path), scored against the same gold labels.](../diagrams/rendered/07_evaluation_pipeline.png)

Three predictors are compared on the same gold labels, forming a deliberate progression from no learning to full contextual reasoning:

1. **Rule-based floor.** A bilingual (EN/DE) lexicon sentiment classifier and a keyword severity classifier (the pre-LLM tradition; Taboada et al., 2011). No training, fully transparent. Its German entries are largely idle on this corpus, whose texts are English paraphrases (§5A.5).
2. **Classical ML.** TF-IDF character n-grams + Logistic Regression, evaluated by stratified 5-fold cross-validation with out-of-fold predictions (no train/test leakage), class-balanced to handle the skew toward negative feedback.
3. **Contextual LLM path.** A zero-shot triage prompt on the same model the artifact uses (`evaluation/predict_llm.py`, GLM-5.2 at temperature 0), asking for three-class sentiment, a four-level risk label, a theme, a journey stage and an owner per signal. It was run against this harness's 188-signal seed-label corpus on 4 August 2026, enriching **188 of 188** signals; the scored results appear in the tables below. It must be read for what it is: a contextual predictor on the artifact's model, **not the artifact's enrichment stage**. The production stage (`services/enrichment.py`) differs in at least four ways that each move the number: its prompt asks for four-class sentiment including *mixed* and for an urgency rubric rather than *risk*; it prepends curated few-shot exemplars; it batches items and passes every response through a sanitiser; and it scores against a different gold standard in the in-repo evaluation (§5A.7). A second script, `predict_llm_production.py`, runs the corpus through `enrich_signals` itself under pre-registered scoring rules (a `mixed` prediction maps to *neutral* for the three-class star gold, with a drop-*mixed* sensitivity reported beside it; urgency is scored as risk unchanged), and the harness scores it under separate keys. ‹Its results are inserted here once the production-path run has been executed; until then every LLM figure in §5A.3–5A.5 is the generic-prompt predictor.› One disclosure attaches to the run's provenance. An earlier execution attempt had failed *silently*: the model gateway rejected the client library's default User-Agent header with an HTTP 403, and the script exited with status 0 after writing an empty results file, so a green exit code stood in for a run that had produced nothing. The defect was treated as a finding about the harness rather than quietly rerun. The fix (a User-Agent header, and a hard failure on an empty result set) is committed alongside the results, and the episode is reported here because a harness that can report success on no output is exactly the failure mode §4.9 warns against: declared checks are not enforced checks until they fail loudly. Separately, the artifact carries its own **committed, live LLM evaluation**, a curated bilingual golden set (§5A.7), whose results are reported as convergent evidence in §5A.7 rather than merged into these tables, because the gold standards differ.

Sentiment is scored against the star-rating gold (1–2 → negative, 3 → neutral, 4–5 → positive), a non-circular reference because it is independent of the text the classifier reads.

### 5A.3 Sentiment results

| Predictor | n | Accuracy | Macro-F1 | Weighted-F1 |
|---|---:|---:|---:|---:|
| Rule-based lexicon (floor) | 153 | 0.37 | 0.37 | 0.48 |
| TF-IDF + Logistic Regression (5-fold CV) | 153 | 0.78 | 0.52 | 0.76 |
| LLM enrichment path | 153 | **0.86** | **0.67** | **0.86** |

The classical-ML baseline improves accuracy by **41 points** and macro-F1 by **15 points** over the lexicon floor. The per-class and confusion analysis explains why the floor is weak: of 94 gold-negative signals the lexicon labels **58 as neutral**, because the *paraphrased, operational* phrasing of real feedback ("Transaction history cannot be exported to CSV") carries few overt sentiment words. Lexicon precision on the negative class is high (0.94) but recall is low (0.34). When an explicit negative word appears the call is reliable, but most real complaints are stated descriptively. This is a substantive finding, not merely a baseline artefact: **surface-lexicon sentiment is inadequate for operational customer feedback, which motivates contextual models.** The neutral class is small (9 of 153) and noisy, and it depresses macro-F1 for all three methods.

The LLM path extends the progression rather than merely matching it. Accuracy rises from 0.78 to **0.86** and macro-F1 from 0.52 to **0.67** over the classical baseline, a further 8-point accuracy gain on top of the 41-point gain the learned model already delivered. The macro-F1 improvement is the more informative of the two, since it is not inflated by the dominant negative class: the contextual model recovers minority-class signal that the character n-grams do not. The ordering floor → learned → contextual is therefore monotone on both metrics, which is the result the loop's precondition argument requires.

The pairwise gaps are tested, not eyeballed. On identical items, an exact McNemar test (the same convention as the in-repo harness, §5A.7) separates the contextual path from the learned model on sentiment: the two disagree on 26 signals, with the contextual path right and the learned model wrong on 19 and the reverse on 7 (n = 153, p = 0.029). Both learned and contextual paths separate from the lexicon floor at p < 0.0001. The 8-point sentiment lead is therefore a statistically significant paired difference on this corpus, not sampling noise. The tests are written by the harness to `evaluation/results/summary.json` (`mcnemar_paired`).

![Figure 5.2: Sentiment confusion matrix, lexicon floor vs star-rating gold (n = 153). Gold-negative signals are frequently mislabelled neutral.](../evaluation/results/sentiment_confusion.png)

### 5A.4 Risk / severity results

Risk is scored on the 106 signals (Trade Republic + Henkel) carrying a closed-set `risk_seed` label {low, medium, high, critical}.

| Predictor | n | Accuracy | Macro-F1 | Weighted-F1 |
|---|---:|---:|---:|---:|
| Keyword severity (floor) | 106 | 0.41 | 0.26 | 0.30 |
| TF-IDF + Logistic Regression (5-fold CV) | 106 | 0.68 | 0.65 | 0.67 |
| LLM enrichment path | 106 | **0.72** | **0.68** | **0.71** |

The keyword floor collapses almost everything to "low": it correctly tags all 36 low-risk signals but mislabels 18 of 23 high and 19 of 27 critical signals as low, because severity in paraphrased text is rarely signalled by a fixed keyword. Its one strength is precision on "critical" (1.00). When an unambiguous critical term ("blocked", "fraud") fires, it is right, but recall is only 0.15. Collapsed to a binary **escalate (high+critical) vs routine** decision, the floor reaches 0.59 accuracy and 0.50 macro-F1, still weak. The classical-ML model recovers most of the lost signal (macro-F1 0.26 → **0.65**), learning sector-specific severity cues from character n-grams across both languages.

The LLM path leads on risk as well (accuracy 0.72, macro-F1 0.68), but its margin over the classical baseline is **markedly slimmer than on sentiment**: three macro-F1 points here against fifteen there. This asymmetry is worth stating rather than smoothing over, and it qualifies the case for contextual triage. Severity in this corpus is carried substantially by lexical markers that character n-grams already capture once they are *learned* rather than hand-listed, so the additional benefit of contextual reasoning is small. Sentiment, by contrast, depends on reading descriptively-phrased dissatisfaction that has no reliable surface form. For a deployment weighing cost, latency and model sovereignty (§4.4), the defensible reading is that a learned local model is close to sufficient for severity routing, while the contextual path earns its cost on sentiment. The corpus is modest (n = 106), and the paired test confirms the caution: on identical items the contextual and learned models disagree on 42 signals almost symmetrically (23 to 19 in the contextual path's favour), McNemar p = 0.644. The contextual path's lead on risk is therefore **not statistically separable** from the learned model on this corpus. The sentiment lead is (p = 0.029, §5A.3); the risk lead remains an observed ordering, which strengthens the deployment reading above: for severity routing, a learned local model is statistically indistinguishable from the contextual path here.

![Figure 5.3: Risk/severity confusion matrix, keyword floor vs risk_seed gold (n = 106). The floor collapses most signals to "low".](../evaluation/results/risk_confusion.png)

#### 5A.4.1 Routing fields: journey stage and recommended owner

The two *routing* fields are evaluated separately, under a different configuration, and the difference must be stated before the numbers. Journey stage and owner are open-vocabulary in the production prompt, and the model's free-form vocabulary barely intersects the corpus gold: roughly fifteen percent of journey values and one percent of owner values match by exact string. Scored that way, the result would measure wording, not routing. They are therefore scored from a **constrained run** (`predict_llm.py --constrained`) in which the corpus taxonomy is supplied as a closed inventory and the model must select from it. This is the closed-set treatment §3.5.2 designed for exactly these two fields, and it mirrors the deployed condition: a real workspace configures its owner list and journey taxonomy rather than inventing labels per signal. It is nevertheless a *different configuration* from the production-config run behind §5A.3–5A.4, so it is reported separately and never merged with those tables. The model obeyed the inventory completely (the in-vocabulary rate is 100% for both fields), so the comparison is valid on its own terms.

A majority-class floor is reported alongside, because accuracy over 27 or 51 classes is uninterpretable without one:

| Field | Classes | Majority-class floor | LLM (inventory supplied) | Macro-F1 |
|---|---:|---:|---:|---:|
| Journey stage | 27 | 0.20 | **0.59** | 0.50 |
| Recommended owner | 51 | 0.15 | **0.40** | 0.32 |

Both clear their floor by a wide margin, journey stage by roughly three times and owner by about two and a half, so the pipeline is extracting real routing signal rather than guessing the modal class. **Neither is accurate enough to route autonomously.** An owner assignment that is correct two times in five would, as unattended automation, misroute the majority of problems. The plain reading is that these fields are useful as a *draft* a human accepts or corrects, and useless as an unattended decision. That is not a convenient interpretation; it is the one the numbers force. It also independently supports the artifact's central design commitment (§4.4, DP4): the mandatory approval gate is not friction added to an otherwise-reliable pipeline, it is the control that makes a pipeline of this accuracy safe to deploy at all. A system that routed on these numbers without review would fail quietly and often.

Three limits. Six of the 188 signals were lost to endpoint errors during the run, so n is 182. The macro-F1 figures are computed across all classes and are inflated by rare labels that happen to be predicted correctly; restricted to the items whose gold label is one of the classes with at least five examples (nine journey stages covering 78% of items; eight owners covering 58%), macro-F1 over those classes is 0.55 for journey stage and 0.42 for owner, with accuracy 0.58 and 0.44 on the same items (`f1_macro_on_supported`, `accuracy_on_supported` in `summary.json`). (An earlier draft reported 0.28 and 0.18 for these figures; that was an averaging artefact of the harness, which admitted every out-of-set prediction on the restricted items as a phantom class with F1 = 0, and it is corrected in the harness.) The genuinely conservative fact is where the misses concentrate: three supported owner classes (`cx_insights`, n = 20; `cx_policy`, n = 6; `mobile_product`, n = 6) and one journey stage (`onboarding`, n = 5) score F1 = 0, so the model never routed a single one of their signals correctly. And the supplied-inventory condition makes the task easier than production free-form generation, so these numbers are an *upper* bound on the production pipeline's routing accuracy, not an estimate of it.

### 5A.5 Generalisation across sectors and languages

Lexicon sentiment macro-F1 varies by slice: B2B industrial 0.45, food delivery 0.34, fintech 0.28; German-source 0.42, English-source 0.27. This confirms that a fixed lexicon transfers poorly and unevenly across domains and languages (relevant to H3 and to the fairness concern that some languages are triaged less reliably; Mehrabi et al., 2021). The classical-ML model, trained across the pooled multilingual corpus with character n-grams, is more uniform. Sliced by *source* (the review platform or channel, which is what H3 literally asks), the floor's accuracy runs from 0.29 on the Apple App Store (n = 38) and 0.34 on Trustpilot (n = 68) to 0.50 on Amazon (n = 26), while the contextual path runs from 0.73 on Amazon to 0.94 on Trustpilot; the two retail sources carry five and six signals and are not read. Source and sector are themselves confounded on this corpus (Amazon and the two retailers are the B2B stratum; the app stores are fintech), so this is reported as descriptive support for H3, not as a source effect. The per-slice tables are written to `evaluation/results/sentiment_by_sector.csv`, `sentiment_by_language.csv` and `sentiment_by_source.csv`.

The LLM path was scored on the same slices, with the same minimum of five signals per slice. It improves **every** sector slice, and it improves the weakest most: fintech, the floor's worst, roughly doubles (macro-F1 0.28 → 0.58).

**Per-language comparison on this corpus is confounded twice over, and is not made here.** First, these are source-language strata: the `language` field records the original review's language, the paraphrased texts are all English (§3.7), so no slice measures German-text processing, and the lexicon's German entries go largely unexercised. Second, language is not independent of sector: the B2B industrial stratum is almost entirely German-source (38 of 39 signals in the full corpus; 37 of 37 among the star-rated ones), fintech is overwhelmingly English-source (58 of 67; 36 of 45 star-rated), and only food delivery carries both strata in comparable numbers (37 German-source / 34 English-source among the star-rated). These counts are read from the composition tables the harness writes (`composition.csv`; `summary.json`). An aggregate "German versus English" figure would therefore largely restate the sector composition. The two metrics also disagree in direction. Aggregated, German leads on macro-F1 (0.67 vs 0.61) while English leads on accuracy (0.91 vs 0.81), which is what one expects when macro-F1 is computed over slices with sparse minority classes. Within the one sector that supports a like-for-like comparison, food delivery, LLM accuracy is near parity (German 0.919, English 0.941) while the macro-F1 gap is wide and unstable (0.840 vs 0.328) on roughly thirty signals per cell. **Accuracy is therefore the metric reported for language, and no claim of a narrowing or widening cross-language classification gap is made.** The composition table and both metrics are written to `evaluation/results/summary.json`, so the confound is inspectable rather than asserted.

What *can* be claimed, and matters more for the loop, concerns **escalation** rather than classification. The relevant fairness criterion is equal opportunity, the recall on signals whose gold label warrants escalation (high or critical), because it conditions on the gold label and is therefore not distorted by the very different base rates across strata (German-source 17.8%, English-source 69.5%):

| Escalation recall (gold-escalate signals) | n | Keyword floor | TF-IDF + LR | LLM path |
|---|---:|---:|---:|---:|
| German-source | 8 | **0.0%** | 62.5% | 87.5% |
| English-source | 41 | 19.5% | 95.1% | 87.8% |

Each recall carries a 95% Wilson interval, and each stratum pair a two-sided Fisher exact test on hits and misses. The keyword floor escalates none of the eight gold-escalate German-source signals (0 of 8; interval 0–32%) against a fifth of the English-source ones (8 of 41; 10–34%), a difference eight signals cannot distinguish from chance (p = 0.32). The learned model, close to sufficient on aggregate risk accuracy (§5A.4), carries a stratum gap that *is* significant: 62.5% (31–86%) against 95.1% (84–99%), p = 0.026. The contextual path's stratum difference is not detectable: 87.5% (53–98%) against 87.8% (74–95%), p = 1.0; and on the German-source stratum the contextual path's 7 of 8 against the learned model's 5 of 8 is p = 0.57. What the table supports is therefore precise: the learned model's escalation gap is significant, and the contextual path's is not detectable on this corpus. The middle column is what makes the finding matter: the gap is not an artefact of the deliberately weak floor, because a respectable learned model shows it, and the method that is statistically indistinguishable from the contextual path on aggregate risk accuracy (p = 0.644, §5A.4) differs from it in whom it escalates. A rival explanation is named rather than dismissed: the learned model is trained by cross-validation on this corpus, in which German-source escalation cases are eight of forty-nine and almost all B2B vocabulary, so any in-domain classifier inherits that composition, and the zero-shot contextual model does not; an English-only training ablation would separate "method choice" from "in-domain training on an imbalanced corpus" and has not been run. An uneven triage layer does not merely score worse; it means some customers' problems are systematically less likely to reach a human at all. That is a fairness property of the *loop*, not of a classifier (§6.2), and one that the choice of triage method largely determines. Three limits bound it. The German-source gold-escalate stratum is only eight signals, so its recall estimates are imprecise (the Wilson intervals above; the exact intervals are wider still). Language remains confounded with dataset on this subset too, German-source being largely the B2B stratum and English-source largely fintech. And because the texts are English paraphrases, the mechanism cannot be German-language processing; what differs across strata is the content and register of what German-language customers wrote about, such as B2B product issues phrased without alarm keywords. The claim is therefore that method choice governs escalation equity across source strata on this corpus, not a German-text finding, and not that parity is established in general. The hallucination heuristic also remains English-scope by construction (§3.5.2). The full table, including the learned model, is written to `evaluation/results/escalation_recall_by_language.csv`.

![Figure 5.4: Baseline sentiment macro-F1 by sector, showing uneven transfer of a fixed lexicon across domains.](../evaluation/results/f1_breakdown.png) *(The figure shows the lexicon floor; the LLM path's per-slice values are tabulated above.)*

### 5A.6 Interpretation and threats

The results support a clear, defensible claim for RQ3a: **the accuracy of the loop's automated triage is strongly method-dependent, and a learned model is necessary.** Naive lexical methods fail on real, paraphrased operational feedback, while even a lightweight learned model reaches usable accuracy (sentiment 0.78, risk 0.68), and the contextual LLM path (a generic prompt on the artifact's model, §5A.2) is the strongest predictor on both tasks (sentiment 0.86, risk 0.72).

The gain is not uniform, and the shape of it is itself the finding. Contextual reasoning buys a great deal on sentiment (macro-F1 0.52 → 0.67; the paired accuracy lead is significant, McNemar p = 0.029, but it rests on 26 discordant pairs, and the p-value moves to 0.043, 0.052 or 0.076 if a single item's correctness changes, depending on which item, so it sits at the significance line rather than comfortably past it) and comparatively little on severity (0.65 → 0.68; not significant, p = 0.644), while changing escalation equity: the keyword floor escalates none of the eight critical German-source signals, the learned model's stratum gap (62.5% against 95.1%) is statistically significant (Fisher exact p = 0.026), and the contextual path's difference between strata is not detectable (87.5% against 87.8%, p = 1.0; §5A.5). Read together, these say that the loop's precondition is satisfied by more than one method, and that the choice among them is a design trade-off (cost, latency and model sovereignty against a measurable accuracy margin) rather than a foregone conclusion. That is a more useful result for a design-science thesis than a single dominant number would have been, because it hands a deployer an actual decision rather than an instruction.

Two limits on the comparison should be stated. The three predictors are scored on identical gold labels, but only the classical model is cross-validated. The lexicon requires no training, and the LLM path was run once, at temperature 0, without repetition, so run-to-run variation for the contextual path is uncharacterised here (the in-repo evaluation, which does test this, observes a 96–99% sentiment band across same-day runs, §5A.7). And the LLM path scores 0.86 on this corpus against 0.97 on the artifact's own curated golden set. The divergence is expected, and it is why the two streams are never merged: this harness scores against an independent star-rating proxy, the in-repo set against curated labels. The lower number here is the more conservative estimate and the one that should be quoted.

What §5A tests, and what it does not, should be stated plainly. It evaluates a **precondition** of the contribution, namely that the enrichment feeding the loop is good enough to act on, not the contribution itself. The thesis's distinctive claims (DP1 measured closure; DP2 perishable learning memory; §1.2) are evaluated by *design demonstration* (Chapter 4) and *practitioner perception* (§5B), not by these numbers. That an outcome contract or a decaying memory improves real decisions is argued and demonstrated, not yet measured. The reading of §5A is therefore narrow but firm: the triage layer the loop depends on clears the bar a learned model can reach, and would otherwise fail. The threats of Chapter 3, §3.5.4 further bound these claims: the gold labels are defensible human judgements rather than an oracle, and the corpus is modest (188 signals) and balanced rather than population-representative. A scope limit must also be stated plainly: **this harness scores sentiment and risk/severity in the production configuration, and journey stage and owner only under a supplied taxonomy (§5A.4.1).** The `theme_seed` and `recommended_action_seed` fields carry gold labels for the full corpus but are not scored at all. The semantic-agreement procedure designed for open-vocabulary fields in §3.5.2 has not been executed and remains future work (§6.5). Claims about the pipeline's accuracy extend no further than those four fields. The headline numbers characterise the pipeline *on this corpus* and are not population estimates.

### 5A.7 Convergent evidence from the artifact's in-repo evaluation

The artifact carries its own evaluation infrastructure, committed in its repository (`apps/api/app/evals/`: a curated golden set, a live runner with within-run A/B testing, a real-data evaluator and a published metrics snapshot), with a local run ledger the repository deliberately excludes. Its results are reported here as **convergent evidence**, not as entries in the §5A.3–5A.4 tables, because the gold standards differ: the in-repo set is hand-authored in the repository (both strata; the German stratum's authorship and adversarial verification are documented in the model card, and the English items' authorship should be stated the same way), whereas this chapter's harness scores 188 externally seed-labelled signals. Unlike the §5A predictor, the in-repo runner exercises the **production enrichment stage** itself (prompt, exemplars, batching, sanitiser), on the same model (GLM-5.2 at temperature 0). The numbers are read from the dated run records; none are re-computed here.

The set grew from 60 to 100 items during July 2026, and the trajectory is reported rather than only the endpoint, because the intermediate stages contain a negative result that was not re-rolled:

| Run (2026) | n (EN/DE) | Sentiment | Urgency | Tag F1 (fuzzy) | Exemplar A/B, exact tag set | Exemplar A/B, urgency |
|---|---:|---:|---:|---:|---|---|
| 3 July | 60 (60/0) | 96.7% | 81.7% | 80.8% by meaning (45.8% exact) | p ≈ 1.0 (underpowered) | p ≈ 1.0 (underpowered) |
| 17 July, 07:24 UTC (20 authored DE items added, 19/20 confirmed by two skeptic agents) | 80 (60/20) | 97.5% | 85.0% | 74.2% | 7.5% → 17.5%, p = 0.039 | 82.5% → 85.0%, p = 0.727 |
| 17 July, 15:22 UTC (two German exemplars added) | 80 (60/20) | 97.5% | 86.3% | 80.2% | 8.75% → 28.75%, **p = 0.001** | 81.3% → 86.3%, p = 0.219 (not claimed) |
| 18 July, published snapshot | 100 (72/28) | 97% (Wilson 0.92–0.99) | 90% (0.83–0.94) | 82.7% | (not re-tested) | 83% → 90%, **p = 0.039**, in three same-day re-runs |

The one eval-improve iteration the table contains is the German gap: the 17 July baseline scored 0% German exact-tag-set agreement because the seven few-shot exemplars were English-only, so the urgency rubric and the praise-tag convention never transferred; two German exemplars, written fresh rather than drawn from golden-set texts, lifted the exact-tag-set agreement to a significant in-run effect and narrowed the DE/EN urgency gap from 6.7 to 1.7 points without regressing English. The published run (18 July; `published_metrics.json`, served at `GET /model-card/metrics`) reports per-language DE (n = 28) 96.4% sentiment / 89.3% urgency and EN (n = 72) 97.2% / 90.3%. Its intervals are quoted as Wilson intervals; the ledger's percentile-bootstrap intervals (93–100%, 84–95%) overstate the precision of a proportion at the boundary. Both halves of the golden set are pooled in these figures: the set declares an optimisation half (49 EN / 21 DE) on which the exemplar interventions were tuned and a held-out half (23 EN / 7 DE) never optimised against, and the harness now reports the held-out half separately (`by_split`); ‹the held-out figures are inserted here once the runner has been re-executed›.

Five disclosures travel with these numbers. (i) The German tag metrics at n = 100 improve partly by construction: the rubric completion added tags the model was already predicting against under-labelled gold, so tag figures are not comparable across that boundary. (ii) The urgency effect at n = 100 was first significant after a churn-musing calibration exemplar was added between the n = 80 and n = 100 runs, and its "three runs" are same-day re-runs of identical items that bound model noise (GLM-5.2 is non-deterministic even at temperature 0), not replication over items; the p-value trajectory across n = 60/80/100 is sequential testing without alpha spending, so the urgency claim is held as exploratory and the held-out split is the confirmatory read (§3.5.3). (iii) The hallucination heuristic is English-scope only by construction: it token-grounds predicted tags against the English vocabulary, which would mis-flag correct German tags, so non-English items are excluded from that metric rather than misreported. (iv) The cross-industry real-data run over the same three public datasets reaches about 90% sentiment accuracy against the star rating, but under a lenient rule in which a *mixed* prediction counts as correct for one-to-three-star items, so it is not comparable to the strict 0.86 of §5A.3, and its n and date are not in the committed outputs (‹author to add from the local ledger or drop the figure›); what it does show is urgency rising consistently as star ratings fall in all three sectors and sector vocabularies emerging with no per-sector configuration, the premise behind §4.3.5. (v) The learning-loop probe: feeding stored learnings back into synthesis raised the share of a past learning's remedy appearing in the new recommendation from **21% to 71%** (66.7% adoption; alignment lift 0.503 against a same-run noise floor). This is evidence that retrieval steers recommendations rather than decorating them, and no more: the probe varied whether a learning was retrieved, not its age, so perishability (DP2) is unmeasured; it ran on simulation-authored learnings, which were retrieval-eligible at the time, whereas since 8 August 2026 only human-recorded conclusions pass the retrieval gate; and the outcome data behind the learnings is simulated, so whether the steered remedy is *better* requires a live outcome contract on real data (§6.5).

Taken with §5A.3–5A.6, the two evidence streams converge from different gold standards on the same conclusion: contextual LLM triage clears the accuracy bar the loop requires, while the loop's *outcome* claim remains to be earned on real data. What the streams do not yet share is the predictor: the production stage's score on this chapter's 188-signal corpus is the pending re-run of §5A.2.

### 5A.8 An external-review episode, in brief

A third, unplanned evaluation input arose during the write-up window (16–17 July 2026): two independent LLM-based strategic reviews of the deployed artifact, whose factual claims were adversarially verified against the codebase and the live deployment before any were acted on, and whose surviving findings drove the trust-and-credibility hardening reported in §4.4. The episode is reported in full, with its claim-by-claim tally and what it does and does not license as evidence, in Appendix F; its one methodological lesson is carried into §6.4: an external evaluation of an artifact evaluates what the artifact *shows*, so it understates capability that is built but unexposed.

---

## 5B. Qualitative Practitioner Study (RQ4)

### 5B.0 Two evidence sources: in-depth interviews and a breadth survey

RQ4 is addressed by two complementary instruments. The **in-depth interviews and task sessions** (12–15 participants; §5B.2) are the *primary* evidence: they carry the prototype-reaction and task-metric findings that only observation can provide. A short, anonymous **supplementary survey** (instrument in Appendix A; distributed via practitioner communities on Reddit and LinkedIn) adds *breadth*, confirming the current-practice and attitude hypotheses (H1, H2, H4, H5, H6, H7, H8) across a larger, shallower sample. The survey is deliberately minimal: a single Likert matrix in which each row is a hypothesis, plus a source-count and a closure-frequency item. It is analysed by a reproducible script (`evaluation/survey_analysis.py`) that reports top-2-box agreement with a 95% Wilson interval and a descriptive support level per hypothesis (supported / mixed-refine / not supported, with no verdict below n = 10 and the corroborating item required for H2 and H8), matching §3.6.4. The survey's limits are explicit and bound its weight: it is self-report and attitudinal, its sample is a convenience sample skewed to those platforms, and H6/H7 are measured there as *hypothetical* comfort rather than observed trust, so on those two the interviews remain the stronger test. Survey verdicts are reported below alongside the interview themes and folded into the hypothesis table (§5B.5) and the traceability matrix (Appendix D).

> **‹PLACEHOLDER: survey results: n, response source split (Reddit/LinkedIn), and the per-hypothesis verdict table from `evaluation/results/survey_verdicts.csv`.›**

### 5B.1 Status and fallback protocol

The practitioner study was planned as the primary validation of the design with practitioners; as the evidence stands (Chapter 3, §3.3) it is the **exploratory** stream, and it is reported as such. No session had been run at the time of writing, and **no interview findings are reported until the data are collected; nothing here is simulated.** So that the reporting rule does not depend on the sample the study reaches, it is fixed here in advance. With **12 or more interviews** the protocol below is executed as designed, the SUS and TAM figures are reported with their intervals, and the survey is folded in. With **six to eleven interviews**, the same instruments are reported, the SUS and TAM figures are given as descriptive ranges rather than means with intervals, the task metrics are reported per participant rather than aggregated, and every finding is labelled *exploratory (n = …)*. With **fewer than six interviews**, or a survey below n = 40, no theme is reported as a finding: the section states the number reached, reports the sessions as a design walkthrough with verbatim reactions attributed by role, and the hypotheses the study was to test are marked *not evaluated* in Appendix D. In every case an empty result cell is deleted and its absence stated in a sentence, never left as a placeholder in the submitted document.

### 5B.2 Protocol (as designed; no session had been run at the time of writing)

Twelve to fifteen practitioners (marketing / product / CX, 2+ years, companies of ~10–500 staff that actively collect feedback) are recruited purposively with role and company-size variation (recruitment materials, Appendix A). Each ~25–30 minute online session has two parts: a semi-structured discussion of current practice (eliciting H1, H2, H5, H8) and a task-based prototype encounter (triage, govern a rule, approve a queued action, inspect a closed-loop measurement), with think-aloud. Sessions are recorded with consent and transcribed. Task success and time-to-action are captured by the facilitator and the platform's `events` telemetry. Participants then complete the SUS and the TAM + trust battery (Appendix A). The full interview and task guide is in Appendix A.

### 5B.3 Analysis plan

Transcripts are analysed by thematic analysis (Braun & Clarke, 2006), following the reflexive approach (Braun & Clarke, 2019), against the codebook in Appendix A, with a double-coded subset and an inter-rater reliability check. SUS is scored 0–100; TAM/trust subscales are summarised descriptively. Findings are mapped to the research questions, with the hypothesis codes of Appendix D used as coding labels.

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

The per-hypothesis outcomes (supported / mixed-refine / not supported / insufficient n, from the survey script; and the interview evidence per code) are recorded in the traceability matrix (Appendix D) once the data are in, so that the evidence status of every claim is stated in one place. ‹Survey verdicts from `evaluation/results/survey_verdicts.csv` and the interview-based outcomes are inserted into Appendix D when analysis is complete.›
