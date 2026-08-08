# CLARA — Science, Statistics & ML Review

**Date:** 8 August 2026
**Reviewer stance:** market-research / voice-of-customer methodology, statistics, and applied ML. The review targets what the system and thesis actually do (every claim cites a file), credits what is already disclosed rather than re-raising it, and proposes concrete strengthenings ranked by payoff.
**Scope reviewed:** the full ML core (`apps/api/app/services/`, `apps/api/app/agents/`, `apps/api/app/evals/`), the strategy and product docs (`docs/`, `business-ops/`), and both thesis evidence streams (`thesis/manuscript/`, `thesis/evaluation/`).

---

## 1. Summary verdict

CLARA's scientific posture is unusually honest for a VoC product: the deliberate separation of deterministic scoring from LLM judgement, the paired in-run McNemar design, the held-out golden split, the refuse-to-fit rule in the ITS engine, the A–E evidence grading, and the documented retraction of a confounded fairness claim are practices most commercial tools in this category do not have and most published papers would accept. The critique below is therefore not "the methodology is naive" — it is that **several load-bearing numerical components were never calibrated to the thing they now run on**, that **the statistics of detection and outcome attribution still permit self-flattering readings the honesty machinery doesn't catch**, and that **one eval finding (closed-set routing) has not yet been fed back into the product although it is the single largest measured accuracy lever**.

The three findings I would fix first: the embedding-threshold miscalibration introduced by this week's provider swap (F1), the absence of any inter-annotator agreement number behind the golden labels (F2), and shipping the closed-set routing condition to production (F9).

---

## 2. What is genuinely strong (credited, not re-argued)

These are design decisions that align with current best evidence, several of them ahead of the published state of practice:

- **Deterministic severity outside the LLM** (`synthesis.py:53`, DP3) — the LLM is instructed not to set severity, and the 8-factor score decomposes exactly into contestable drivers (`domain/scoring.py:82-119`). This sidesteps the well-documented unreliability of LLM-as-judge scoring (position and verbosity biases, Zheng et al. 2023; overconfident self-reports, Xiong et al. 2024).
- **The in-run paired A/B with exact McNemar** (`evals/run_live.py`, `harness.py:268`) as the designed inference, because GLM-5.2 is non-deterministic at temperature 0 — this is the correct test for small paired samples, and the decision to report the p-value trajectory (p≈1.0 at n=60 → 0.219 at n=80 → 0.039 at n=100) rather than only the endpoint is a disclosure most papers skip.
- **The ITS engine's honesty rules** (`outcome_engine.py:395-474`): refuse-to-fit under 10 pre / 5 post buckets, execution-day exclusion, complete-UTC-days-only with a Monte-Carlo justification (spurious negative effects in ~66% of mid-day reads), no fabricated pre-history, and a labelled plain delta instead of a dressed-up CI. The `detectability_note` MDE heuristic (`outcome_engine.py:44-67`) — warning approvers when a window cannot detect anything — is something I have not seen in any commercial VoC tool.
- **Evidence grades A–E grading the design, not the result** (`outcome_engine.py:70-90`), with grade B (controlled quasi-experiment) honestly reserved rather than claimed.
- **Refusal-based grounded Q&A** (`ask.py`): minimum-match refusal, confidence = min(model, retrieval), no chat memory — the right counter-design to hallucinating chat analytics.
- **Corroboration floors on emerging problems** (`emerging.py:17-18`) so a single-source burst cannot page anyone.
- **Annotate-don't-drop near-duplicate handling** (Jaccard 0.85, `signals.py:53`) — surfacing the inflation-vs-deletion trade to the human instead of silently resolving it.
- **The retraction discipline**: the confounded cross-language accuracy claim was retracted in writing (`05_evaluation_results.md` §5A.5, commit d3059c9) and replaced with the defensible equal-opportunity escalation-recall claim, with the 8-signal German stratum's ~47–100% interval stated. Kiritchenko & Mohammad (2018) and Hardt et al. (2016) are the right anchors and are already cited.
- **Train/test hygiene**: exemplars deliberately disjoint from the golden set; a held-out split the loop may not optimize against; "never weaken a golden label" as a written rule (`LOOP_PROMPT.md`).

The findings below assume all of this as the baseline.

---

## 3. Findings

Ordered by how much they matter, not by pipeline stage. None of these repeats a limitation the thesis already states.

### F1 — Every cosine threshold in the system was calibrated under a different embedding model (most urgent)

The pipeline contains at least seven load-bearing cosine thresholds:

| Threshold | Value | Site |
|---|---|---|
| Ask retrieval floor | 0.30 | `ask.py:32` |
| Taxonomy mapping floor | 0.55 | `semantic_taxonomy.py:25` |
| Theme-discovery clustering | 0.70 | `semantic_taxonomy.py:26` |
| Synthesis semantic fallback | 0.70 | `synthesis.py:35` |
| Hygiene duplicate detection | 0.86 | `taxonomy_hygiene.py:32` |
| Governance auto-merge | 0.95 | `semantic_taxonomy.py:299` |
| Learning retrieval (planned pgvector path) | — | `learning_engine.py` |

All of these were set under the previous embedding geometry (the Elvis-era defaults, latterly `gemini-embedding-001` at 768 dims). On 6–7 August the embedding provider moved to `mistral-embed` (1024 dims). **Cosine similarity distributions are not comparable across embedding models** — different models occupy different regions of the similarity range, with different means and variances for both related and unrelated pairs; a floor of 0.55 can be conservative under one model and near-vacuous under another. Nothing recalibrated. Concretely: `MAP_THRESHOLD=0.55` may now over- or under-map signals to taxonomy nodes; `merge_eps=0.95` may stop catching duplicates or start merging distinct themes; `MIN_SIMILARITY=0.30` changes what `/ask` refuses; and `retrieval_strength` (the mean cosine that caps user-facing confidence, `ask.py:148-156`) now sits on a different scale than the one implicitly validated during development.

**Fix (R1):** a one-time calibration script. Build a small labelled pair set from data already in the repo — golden-set items sharing a gold tag = positive pairs, items from different categories = negative pairs; taxonomy category descriptions vs their own terms = positive mapping pairs. For each threshold, sweep the operating point under the live embedder and pick the value matching the previous operating characteristics (e.g. the FPR the old threshold achieved). Persist as env-configurable per-embedder values with the embedder name recorded next to them, so the next provider swap forces the question. This also converts the thresholds from folklore constants to measured quantities — worth a paragraph in the thesis.

### F2 — No inter-annotator agreement exists anywhere behind the accuracy claims

Both evidence streams rest on single-annotator gold labels. Stream A's seeds are "human-curated … labelled independently of the artifact" with no annotator count; §3.11 promises IAA "where available" and it is never reported. Stream B's German items were adversarially audited by LLM skeptic agents (19/20 confirmed) — which is a real check, but it is model-against-model agreement, not human-human agreement, and an examiner will distinguish the two. Urgency is the weakest point: it is the most judgement-laden field, it carries the headline p=0.039 claim, and it is scored as nominal accuracy although it is ordinal — a medium↔high confusion counts the same as a low↔critical one.

**Fix (R2):** have one additional human independently label a stratified subsample (~30 items: both languages, all four urgency levels), then report Cohen's κ per field and **quadratic-weighted κ for urgency** (Artstein & Poesio 2008 is the standard reference). Two days of work; it either validates the gold standard or reveals that some "model errors" are label ambiguity — both outcomes strengthen the thesis. Where disagreement concentrates, adjudicate and document. This directly addresses LLM-annotation validation norms (Gilardi et al. 2023 showed LLM annotation can beat crowdworkers; Pangakis et al. 2023 showed you must still validate per task).

### F3 — Sequential testing without alpha control, and a ledger gap

The urgency significance narrative is: tested at n=60 (p≈1.0), n=80 (p=0.727), n=80 again (p=0.219, "not claimed"), then three same-day runs at n=100 with "first significant at 2026-07-18T12:25Z" (`published_metrics.json` notes). Reporting the trajectory is honest and unusual — but formally this is **repeated significance testing on an accumulating sample with no alpha spending**, and "first significant at" is the signature of optional stopping. The three consecutive significant runs at n=100 are better read as replication (which is genuinely stronger than one p-value), but the thesis should name the issue rather than let an examiner name it first.

Separately, **the committed eval ledger stops on 3 July** (`history.jsonl`, 9 rows) while the thesis cites 17/18 July runs; those survive only in `published_metrics.json` and prose. The commits exist, but the reproducibility artefact the methodology chapter describes is incomplete.

**Fix (R4):** (a) state the sequential-testing caveat in §3.5.3 and frame the n=100 claim on the replication (3/3 runs p<0.05), not the first crossing; (b) for future confirmatory claims, fix n in advance — the accept gate already exists, add "n is frozen for the claim"; (c) regenerate and commit the missing ledger rows and reports so `history.jsonl` matches the thesis; (d) report the number of loop iterations attempted alongside accepted, since the accept gate's per-comparison p<0.05 accumulates family-wise risk over a long loop (the held-out split is the existing mitigation — say so explicitly).

### F4 — Self-selection bias enters the product's arithmetic, not just the eval's

The thesis correctly says the corpus is "not population-representative." But the *product* also treats feedback counts as population quantities: `customer_reach = min(1, customers/250)`, `recurrence = decayed_frequency/25`, `evidence_confidence = sources·0.04 + volume·0.02` (`synthesis.py:311-326`) all scale with raw self-selected volume. Public reviews are the canonical J-shaped, extremes-oversampled channel (Hu, Pavlou & Zhang 2009; Anderson & Simester 2014 found many reviewers hadn't even purchased); support tickets oversample engaged customers; the silent majority appears nowhere. Two consequences: (a) cross-source composition shifts masquerade as problem-severity shifts — adding a new connector inflates every factor; (b) `affected_contacts = Σ contact_count` (`synthesis.py:490`) and customer reach **double-count identities across sources**, because pseudonyms are per-source (`as-de-…` review authors can never merge with CRM customer IDs) and no identity resolution exists. The same person complaining on Trustpilot and in a ticket is two customers.

**Fix (R9/R10):** this is not fully solvable (public-review identity resolution is inherently impossible and shouldn't be attempted) — so make the numbers honest about what they are. Label reach as "signal-weighted, not unique customers" wherever it renders; add a source-mix line to every insight (n per source) so an approver sees when evidence is one-channel; consider a near-duplicate *cross-source* collapse (embedding similarity + same-day window) before counting, which catches cross-posted complaints without claiming identity. Longer term, per-source prevalence normalization (each source contributes rates relative to its own baseline volume) removes the connector-addition artefact. Do not attempt MRP-style population weighting — there is no frame to weight to; disclosure is the defensible move.

### F5 — Emerging-problem detection is a hand-weighted score, not a detection statistic

`emerging_problem_score = min(sources·0.08, 0.24) + min(volume·0.08, 0.4) + avg_confidence·0.24 + pending·0.12` with action/watch thresholds 0.68/0.48 (`taxonomies.py:729-739`, `emerging.py:11-13`). Three statistical problems: it has **no baseline** — a theme that always produces 5 signals/week scores identically to a genuinely new spike (the score measures presence, not emergence); `trend_label` compares a 7-day to a 30-day window with a 1.5× ratio and **no variance treatment**, so 3-vs-2 counts flip labels on noise (`frequency.py:99-163`); and the report tests every candidate every time it is built, which is a **multiplicity problem** — with dozens of candidates, some cross 0.68 by chance weekly, and the corroboration floor (good) bounds only the single-source failure mode.

**Fix (R5):** keep the corroboration floor, replace the emergence arithmetic with a rate statistic: per taxonomy node (or candidate theme), model the daily count against its own trailing baseline — a Poisson/negative-binomial exceedance or an EWMA control limit is enough (Kleinberg's burst detection is the heavier canonical option); normalize per source so connector volume shifts don't fire alarms; and control the family-wise error across candidates with Benjamini–Hochberg on the exceedance p-values. This turns "emerging" from a styling decision into a claim with a false-alarm rate — which is exactly the kind of number the governance posture elsewhere in CLARA already prefers.

### F6 — Outcome readouts are exposed to regression-to-the-mean, and the volume confound

Actions are approved when a theme is at peak salience — that is selection on an extreme. Under pure noise, a series selected at its peak declines afterwards; an ITS level-change estimated at that point is biased toward "improvement" (the classic RTM trap; Barnett, van der Pols & Dobson 2005). The ITS design controls trend but not selection-on-peak; the thesis already flags HAC errors and the count-GLM upgrade, but not RTM. Additionally, `resolution_score = 1 − measured/baseline` (`outcome_engine.py:149-179`) is **unnormalized by total inflow** — if overall feedback volume drops 40% (seasonality, a connector outage, the App Store feed going dark as it did this week), every open contract "improves." Daily-bucket ITS with no day-of-week terms also leaves weekly seasonality in the residuals.

**Fix (R6):** three cheap upgrades, all consistent with machinery already present. (a) **Control series**: score the contract metric *as a share of total signal inflow* (or alongside a matched non-targeted journey/stage as comparison) — this simultaneously kills the volume confound and the bulk of RTM, and it is precisely the reserved evidence-grade B design; SDID is already cited as the roadmap. (b) **Placebo checks**: run the same ITS at two pseudo-intervention dates in the pre-window; a "significant effect" at a placebo date flags a series too noisy to attribute. (c) Add day-of-week dummies or aggregate to weekly buckets when the window allows. Each of these is a stronger examiner answer than a caveat paragraph.

### F7 — The learning loop can launder unvalidated causal claims into future prompts

`learn_node` auto-derives a conclusion from the outcome status when no human conclusion exists — `target_met → "worked"`, reviewer `"system"` (`triage_graph.py:489-514`) — and `build_learning_from_conclusion` assigns it base confidence ≥ 0.6 (`learning_engine.py:177-181`). Retrieved learnings are then injected into synthesis prompts to steer future recommendations (`synthesis.py:405-411`). Combined with F6, the failure mode is a closed confirmation loop: a peak-selected, volume-confounded "improvement" auto-becomes a high-confidence "worked" learning that biases the next recommendation toward the same action. The docs describe learning conclusions as human-authored (`docs/data-model.md`), and the influence probe (21%→71% remedy adoption) shows the injection genuinely steers output — which is exactly why the input needs the gate.

**Fix (R7):** one rule — only human-validated conclusions (`reviewer != "system"`) are eligible for retrieval into prompts; auto-derived ones remain visible as *pending* learnings but never steer synthesis. This is a small filter in the retrieval path and it converts DP2 from "memory with decay" into "memory with provenance," which is the version the thesis can defend.

### F8 — Clustering has no stability story, and cohesion is doing validity's job

Two separate clustering mechanisms share the weakness. `cluster_by_threshold` (`semantic_taxonomy.py:62-86`) is greedy single-pass star clustering: the first unused vector anchors a cluster, so **results depend on input order**, and no run-to-run stability is ever measured. The synthesis path's union-find over token-Jaccard (`synthesis.py:186-224`) is transitive: A~B and B~C merge A and C even when they share nothing — single-link chaining, mitigated only by a hand-curated English stop-token list. Upstream LLM tag nondeterminism compounds both. Meanwhile taxonomy auto-promotion uses **cohesion (mean pairwise cosine) as `confidence`** with a 0.80 promote threshold (`semantic_taxonomy.py:257`, `apply_governance`): cohesion measures tightness, not validity — a burst of near-duplicate complaints from one incident is maximally cohesive and would auto-promote a taxonomy node that is an event, not a theme. No separation-from-existing-nodes criterion is applied at promotion time.

**Fix (R8):** (a) swap greedy star clustering for average-linkage agglomerative at the same cosine threshold — deterministic given inputs, no new dependency, drop-in; (b) add a bootstrap stability check to the eval loop (resample signals, re-cluster, report adjusted Rand index; Hennig 2007) and put the number in the model card; (c) at auto-promotion, require separation as well as cohesion (e.g. centroid distance to nearest active node below the merge threshold blocks promotion — the data for this is already computed in `discover_themes`). Recent LLM-clustering work (ClusterLLM, Zhang et al. 2023; LLooM, Lam et al. 2024) is the comparative frame the thesis can cite.

### F9 — The eval's biggest measured lever has not been shipped: production routing still runs the free-form condition

The constrained run (§5A.4.1) exists precisely because free-form generation barely intersects the gold vocabulary — **~15% for journey, ~1% for owner** — while the closed-inventory condition reaches 0.59 / 0.40 (≈3× and ≈2.5× the majority floors). The thesis honestly labels the constrained numbers an upper bound on production behaviour. But the striking product fact is the reverse reading: **production is running the condition the eval showed is drastically worse, while the workspace taxonomy needed for the better condition already exists in the product.** The synthesis prompt's `target_team` enum and category enum are closed sets, but journey/stage/owner assignment in the candidate path is not prompt-constrained against the workspace's own taxonomy.

**Fix (R3):** ship the constrained condition: inject the workspace's journey/stage/owner inventories into the enrichment/synthesis prompts (they are small), require the model to choose from them or abstain, and route abstentions to the existing human review queue. This aligns with the strongest recent system precedent — TnT-LLM (Wan et al. 2024) generates a taxonomy with an LLM, then *classifies against it as a closed set* (and distills to a cheap classifier for scale, which is CLARA's natural cost-reduction path later). It also upgrades the thesis narrative: the upper bound becomes the operating point, measured before/after with the existing paired harness.

### F10 — /ask's trust surface is principled but unvalidated

Three gaps in an otherwise excellent design. (a) The user-facing confidence (min of model self-report and mean retrieval cosine) has **never been validated against answer correctness** — and LLM verbalized confidence is systematically miscalibrated (Xiong et al. 2024; Tian et al. 2023; the thesis already cites Guo 2017 and renamed "confidence" to "model score" elsewhere — `/ask` should inherit that discipline). The per-item predictions are already persisted for exactly this purpose (`run_live.py:96-98`). (b) **Citation entailment is unchecked**: nothing verifies that a cited excerpt actually supports the sentence citing it; the enrichment-stage hallucination heuristic does not run here. (c) **The recency window is undisclosed**: answers draw on the most recent 500 signals (`ask.py:29,106`), so on a busy workspace "no complaints about X" silently means "none recently" — the refusal/answer text never says so.

**Fix (R9):** build a small labelled set of (question, answer, correct?) from demo workspaces; plot the **selective-prediction curve** (coverage vs accuracy as the confidence threshold sweeps) — this is the standard way to validate a refusal system and would be a genuinely novel model-card entry for a VoC product. Spot-audit citation entailment on the same set (an NLI model or an LLM-judge with the RAG-faithfulness caveats). One-line fix for (c): append the evidence window to every answer ("based on the 500 most recent signals, ending YYYY-MM-DD").

### F11 — Smaller findings, quickly

- **Batch-annotation effects:** enrichment labels 25 items per LLM call (`enrichment.py:156`); items in a batch can influence each other (context contamination, position effects). Cheap test: score the golden set at batch size 1 vs 25 once; if metrics move, it is a measured artefact of the production configuration and belongs in the model card.
- **Two impact numbers coexist:** the LLM emits `impact_score` 0–10 and `confidence` in synthesis (`synthesis.py:66-67`) alongside the deterministic 8-factor severity. The problem path ranks on the deterministic score, but the LLM's number survives on insight cards — either drop it from the tool schema or label it as the model's opinion, otherwise the "severity is deterministic" story has a leak.
- **PII scope:** the eval's PII check covers email/IP/phone regexes (`harness.py:178-182`); names and IBANs inside `feedback_text` are untouched (reviewer *author* names are pseudonymized, in-text names are not). Fine for the current claims, but the DPIA should say "regex-scope" explicitly; an NER pass is the upgrade if a pilot demands it.
- **Two duplicate thresholds:** hygiene flags duplicates at 0.86 while governance auto-merges at 0.95 (`taxonomy_hygiene.py:32` vs `semantic_taxonomy.py:299`) — defensible (flag earlier than you merge) but undocumented, and both are F1-affected.
- **Internal inconsistencies to fix before submission:** endpoint count (≈43 in `04_artifact.md` §4.1 vs 84 in `docs/repo-map.md`); learning half-life (180d in code, 365d in the §4.8 worked example); `06_discussion.md` §6.2 still makes a per-language lexicon-reliability claim of the same *form* the §5A.5 retraction declines — align the wording.
- **1970 default timestamps:** `SignalRecord.timestamp` defaults to `1970-01-01` (`domain/models.py:830`), which silently classifies un-timestamped CSV rows as 56 years old — excluded from trends and decayed frequency, and poisoning `first_seen`. Prefer ingest-time now() plus the existing `timestamp_defaulted` marker.

---

## 4. Ranked recommendations

| # | Action | Fixes | Effort | Why this rank |
|---|---|---|---|---|
| R1 | Recalibrate all cosine thresholds for `mistral-embed`; persist per-embedder with provenance | F1 | 1–2 days | Every semantic feature currently runs on constants calibrated to a model no longer in use; affects prod behaviour *today* |
| R2 | Second annotator on ~30-item stratified subsample; report κ per field + quadratic-weighted κ for urgency | F2 | 2 days | The cheapest large upgrade to claim credibility; urgency carries the headline p-value |
| R3 | Ship closed-set routing (workspace taxonomy as inventory + abstention) and re-measure with the paired harness | F9 | ~1 week | Largest measured accuracy lever in the whole eval (free-form ~15%/~1% overlap vs 0.59/0.40 constrained); turns an eval caveat into the product's operating point |
| R4 | Sequential-testing caveat + frozen-n rule for confirmatory claims; commit the missing ledger rows | F3 | ½ day | Removes the most attackable statistical surface before the defense |
| R5 | Rate-based emerging detection (per-source-normalized baseline + control limits + BH-FDR across candidates) | F5 | ~1 week | Converts "emerging" into a claim with a false-alarm rate |
| R6 | Share-of-inflow outcome metric (or matched control series), placebo-date checks, DOW terms | F6 | ~1 week | Addresses RTM + volume confound; produces the reserved evidence-grade B |
| R7 | Retrieval-eligible learnings require human validation (`reviewer != "system"`) | F7 | hours | Closes the confirmation loop; tiny diff |
| R8 | Deterministic agglomerative clustering + bootstrap-ARI stability in the model card + separation criterion at auto-promotion | F8 | 2–3 days | Makes the taxonomy's evolution defensible as measurement, not behaviour |
| R9 | /ask selective-prediction curve + citation-entailment spot audit + evidence-window disclosure line | F10 | 2–3 days | Validates the product's signature trust feature |
| R10 | Reach honesty: "signal-weighted" labelling, per-insight source mix, cross-source near-dup collapse before counting | F4 | 2–3 days | Cheapest honest answer to self-selection; disclosure over false precision |

If only three happen before the next milestone: **R1, R2, R3.**

---

## 5. Positioning against the literature

Where CLARA sits relative to the published state of the art, for the discussion chapter:

- **Taxonomy generation + use.** The closest published system is **TnT-LLM** (Wan et al., 2024): LLM-generated taxonomy, then closed-set LLM labelling, then distillation to a lightweight classifier for scale. CLARA independently converges on the first two stages (bootstrap → proposals → human accept; semantic mapping) but has not taken the closed-set step in production (F9/R3) nor the distillation step (a future cost lever: at pilot volumes irrelevant, at scale it stabilizes labels and cuts inference cost). **ClusterLLM** (Zhang et al., 2023) and **LLooM** (Lam et al., 2024) are the right citations for LLM-guided concept induction and its stability questions (F8).
- **LLM annotation.** Gilardi et al. (2023) and Pangakis et al. (2023) frame the field's norm: LLM annotation is viable but must be validated per task against human agreement — which is exactly what F2 supplies. Prompt-sensitivity work (Sclar et al., 2024) motivates keeping the published metrics pinned to an exact prompt+model configuration, which `published_metrics.json` already does well.
- **Confidence and trust.** Guo et al. (2017) — already cited — plus Xiong et al. (2024) and Tian et al. (2023) on verbalized-confidence miscalibration justify both the "model score" rename and the selective-prediction validation of `/ask` (F10). Parasuraman & Riley's automation-bias lineage (already engaged via Laux & Ruschemeier) supports the human-validation gate on learnings (F7).
- **Feedback sampling.** Hu, Pavlou & Zhang (2009) on J-shaped review distributions and Anderson & Simester (2014) on reviewers-without-purchases ground F4: public feedback is a biased sample *by construction*, so the defensible design is disclosure and per-source normalization, not population claims.
- **Detection and attribution.** Kleinberg (2003) for burst detection and Benjamini–Hochberg (1995) for multiplicity ground F5; Barnett et al. (2005) on regression to the mean, plus the ITS canon the thesis already cites (Bernal et al. 2017; Wagner et al. 2002) and its own SDID roadmap (Arkhangelsky et al. 2021), ground F6. CLARA's refuse-to-fit and MDE-disclosure practices are *ahead* of typical applied ITS use; the missing pieces are control series and placebo checks.
- **Agreement.** Artstein & Poesio (2008) for IAA norms; weighted κ for ordinal scales (F2).

---

## 6. Questions for the author

1. **Which claim is the thesis's single confirmatory endpoint?** The urgency exemplar effect (p=0.039, n=100) currently reads as the headline. If so, freezing that as the pre-specified primary claim — and framing everything else as exploratory — is the cleanest defense against the multiplicity/sequential-testing critique (F3).
2. **Is the golden-set author also the seed-label author for Stream A?** The answer decides how much weight R2's second annotator must carry (one shared annotator across both streams is a stronger reason to do it).
3. **What is the intended production behaviour when closed-set routing abstains** (R3) — human queue, or fall back to free-form? The abstention path determines whether the 0.59/0.40 upper bound translates into precision (route fewer, route right) or coverage (route all, accept errors).
4. **At pilot scale, which matters more to the pitch: emerging-problem sensitivity or false-alarm rate?** R5 can be tuned either way, but the control-limit design needs the answer before thresholds are set.

---

## 7. Closing

The honest-measurement culture in this codebase is its scientific moat — it is more differentiating than any single model choice, and it is rare in this product category. The findings above are the places where that culture has not yet reached: constants that outlived the model they were tuned on, a gold standard with one pair of eyes, detection and attribution statistics that still allow flattering noise, and one eval insight waiting to become a product feature. All ten recommendations are incremental; none requires abandoning an existing design decision, because the designs are mostly right.
