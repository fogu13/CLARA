# Jev as a candidate decision model: experiment note and decision rule

Status (19 September 2026): tooling implemented and tested with a fake client. No run against the vendor has happened. The development sandbox cannot reach the vendor's endpoint, so the owner runs the experiment from a laptop with a key from the vendor console. Nothing in this note is a result.

## What Jev is and why it is a candidate

Jev is TypeSafe's "System One" decision model (early access since 15 September 2026). It answers typed questions about a state and returns probabilities, not text: a Choice over a label set, a Score over two to ten ordered levels, a Noul yes/no probability. The vendor reports lower raw accuracy than the best generation models on its own benchmark and better calibration; independent calibration reads on out-of-domain data exist but none on customer feedback in German. Input is priced per token, output is free, latency is in the hundreds of milliseconds.

CLARA's enrichment and routing steps are closed-set decisions: sentiment, risk, escalation, journey stage and owner from a workspace inventory. A calibrated probability per decision is what the approval boundary needs to route low-confidence items to a person instead of acting on them. That is the reason to test it. The reasons not to adopt it without evidence: the model is new, US-hosted only, closed, and its behaviour on short German feedback is unknown.

## Design (fixed before the run)

- Corpus, gold and scorers are the thesis harness's, unchanged: the frozen 188-signal corpus, star-derived sentiment gold (n = 153), seed risk labels (n = 106), the gold routing inventories (27 journey stages, 51 owners), `compare_runs.py` for accuracy and paired exact McNemar tests, `calibration.py` for calibration and abstention.
- One request per signal carrying every question; the state is the feedback text only, the same information the generic prompt runs received. Question texts are module constants in `thesis/evaluation/predict_jev.py` and are copied into the run's meta file.
- Primary labels: the sentiment Choice and the risk Choice. The risk Score and the escalation Noul are calibration reads, not labels. Routing is scored closed-set with the majority floor beside it, as for the constrained GLM run.
- No abstention in the primary run (threshold 0). Abstention is read off the saved distributions afterwards, so one paid run serves every threshold.
- The served model string is recorded per item; a change of model between runs is a different predictor.

## Pre-registered reading

1. Risk, end-to-end accuracy on the 106 labelled items, against the production default (Mistral Small 4 on the production stage, 0.594) and against TF-IDF plus logistic regression (0.679), with the paired discordant counts and the exact two-sided p. These two comparisons are new and sit outside the retrospective Holm family of ten in the manuscript; they are reported raw with the paired-difference interval and described as a pilot comparison.
2. Sentiment, the same two comparisons on the 153 rated items.
3. Routing: accuracy over the inventory with the majority floor, against 0.588 (journey stage) and 0.401 (owner) from the constrained GLM run.
4. Escalation recall by language stratum. The German stratum has eight positives, so only the interval is read.
5. Calibration: ECE, Brier and log loss per task; the reliability bins; the coverage-against-accuracy curve. The operating question is what coverage remains when the covered accuracy on risk reaches 0.80.
6. The product golden set (30 held-out items) as a second, synthetic read of sentiment with the `mixed` class, urgency and category.

## Decision rule for any product use

Design a product adapter only if all three hold on the primary run:

- risk end-to-end accuracy is at least the production default's and the paired test does not favour the production model (the count of items only the production model gets right is not larger than the reverse);
- ECE on risk is at most 0.10, so the confidence could gate approval routing;
- the German escalation recall interval overlaps the English one.

A pass on these does not establish fitness: one run, seed labels as gold, an early-access model. It earns a second run on a different day and a human-adjudicated gold before any adapter ships.

Even then, production use is blocked until the residency question is settled. The endpoint is US-hosted only; the product's EU residency gate (`CLARA_AI_REQUIRE_EU=1`) refuses it by design. Enabling it would need a vendor data-processing agreement with standard contractual clauses, an entry in the DPIA, redaction at the boundary as for every model call, and an explicit per-workspace opt-in. The gate stays fail-closed by default whatever the experiment shows.

## Cost and effort

About 188 requests of roughly a thousand input tokens each: about a cent at the published price and about two minutes of wall time. The golden-set run is smaller. Reading the outputs and writing the disposition takes an hour.
