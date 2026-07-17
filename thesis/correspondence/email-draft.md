Subject: CLARA thesis — progress update + latest evaluation results

Dear Prof. Zorina,

Hope you are doing well. Since you weren't able to join today, I thought of sending an update
on my progress, and the results of the evaluation I ran this morning. I've also attached four
screenshots of the working system.

I've now named the solution CLARA (Capture, Listen, Analyze, Respond, Adapt): a governed,
local-first customer-feedback triage engine that turns raw feedback into prioritised,
action-ready insight, improves itself from measured outcomes, and adapts across industries
without fine-tuning — and is built GDPR / EU-AI-Act-first.

How the loop actually works (for now)
Feedback goes through a pipeline, one stage at a time:
  1. Ingest: pull in raw feedback (CSV now, Zendesk, etc. later) and normalise it into "signals".
  2. Enrich: an LLM tags each signal with sentiment, urgency, and themes, mapped onto a
     per-workspace taxonomy that grows with the data (this is what would make it work across
     industries without retraining).
  3. Cluster: group related signals into candidate problems by theme.
  4. Synthesise: turn each cluster into a structured insight: a problem statement, the
     evidence (with the actual customer quotes), the affected customers/accounts and the
     revenue at risk (if the use case allows), and a set of proposed actions (product fix,
     customer recovery, journey intervention, or research).
  5. Govern: check every proposed action against policy rules (consent, privacy review,
     no sensitive-attribute inference); actions that fail are blocked pending review.
  6. Approve: a human approves or rejects each action. The pipeline pauses here on purpose:
     nothing customer-facing happens without a person in the loop.
  7. Measure & learn: once an action runs, CLARA measures the outcome against a success metric
     and turns the result into a "learning" that feeds back into future recommendations, so it
     prefers what worked and avoids what didn't.

Screenshot 3 shows one problem all the way through this pipeline.

What I improved this week:
The focus was making the evaluation honest and closing the learning loop. A few changes
looked like big wins at first, but when I tested them properly they turned out to be noise
from small sample sizes. So I rebuilt the evaluation to compare the two versions inside the
same run and test for statistical significance, instead of comparing separate runs. I also:
  • grew the labelled test set to 60 cases
  • connected the outcome→learning loop so past results actually feed back into new
    recommendations, and found and fixed a bug where that loop wasn't running in the live
    product at all
  • validated the whole thing on three real publicly available datasets from different
    industries (Henkel (where I work, chemical manufacturing), Lieferando (food delivery),
    Trade Republic (neobank)).
  • fixed the clustering so it groups themes by meaning rather than exact wording, which made
    the insights noticeably more useful.

Latest evaluation results (run today, using GLM-5.2, 60 labelled test cases)
  • Sentiment accuracy:            96.7%
  • Urgency accuracy:              81.7%
  • Theme matching:                80.8% (by meaning) / 45.8% (exact string)
  • Hallucination rate:            6.7%
  • Learning loop (adoption): feeding past learnings back in raised how much of the learning's
    remedy shows up in the recommendation from 21% → 71% (67% adoption), measured against a
    baseline that absorbs the model's jitter. This is solid evidence the loop is connected and
    genuinely steers recommendations — the mechanism works. (Whether the remedy is actually
    better needs real outcomes — see caveat.)

One caveat: the retrieval feature helps theme-matching and urgency, but the urgency gain
(80.0% → 81.7%) is not statistically significant at 60 cases (McNemar p≈1.0). It's a
small-sample limitation, not a null result. I'll grow the labelled set to fix it (below).
The outcome data is also still simulated for now; the loop adopts past remedies, but proving a
remedy is better will need measured outcomes.

On the model (and next week's experiment)
One thing I noticed: GLM-5.2, the cloud model I'm using, despite being very good, isn't fully
deterministic — the same input can give slightly different output across runs, even with
temperature = 0. Even though this is normal, it matters for us because two eval runs can differ
a little on their own, which can look like an improvement when it isn't.
I will handle it two ways: first, the evaluation now compares both versions within the same run
and tests for significance, so that run-to-run noise cancels out. Second (will do next week
after I fix my server), I'll benchmark some local models against the cloud one on the same
labelled set, testing if they are fully reproducible. So rather than assuming one model is
"right", I'll compare local vs cloud and document the trade-off in accuracy, reproducibility,
cost, and privacy.

Cross-industry validation (three real datasets: Henkel, Lieferando, Trade Republic)
  • ~90% sentiment accuracy against the star rating as a proxy ground truth.
  • Urgency rises consistently as star rating falls, across all three industries.
  • Industry-specific vocabularies generated with zero fine-tuning or config. This is the
    "adaptable to any industry" claim, now shown rather than asserted.

Attached screenshots
  1. clara-01-dashboard.png: leadership overview: highest-impact problems, governance
     blockers, pending decisions, outcomes.
  2. clara-02-insights.png: the insight board (problems by lifecycle stage).
  3. clara-03-insight-detail.png: one problem end to end: evidence, affected customers,
     proposed actions, per-action approval gates, and the governance / consent checks.
  4. clara-04-learnings.png: the outcome→learning loop (the self-improvement part).

What I'll work on in the next week (I'll be on holiday from the 10th till the 26th, but happy
to check in in 2 weeks, if you'll be available)
  • Grow the labelled set toward 100+ to improve the significance tests
  • Benchmark local vs cloud models on the same set (accuracy, reproducibility, cost,
    data-residency)
  • I'd value your view on whether a per-industry evaluation chapter, built on the three real
    datasets, fits the thesis structure.
  • Wire in real outcome measurement to close the loop empirically (simulated → measured)
  • Conduct interviews on Reddit + Linkedin
  • Work on the platform (Claude Fable is amazing on finding my bugs :))

Please let me know your feedback.

Best,
Elvis

P.S. sorry for the long update
