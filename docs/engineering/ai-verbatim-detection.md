# Detecting AI-generated verbatims at ingestion: what we measured and what we shipped

**Status:** implemented (`apps/api/app/services/authenticity.py`), 2026-08-21
**Question asked:** "Can CLARA pinpoint which verbatim comments are AI-generated, and
flag them so I can weed them out before they are triaged and combined into insights?"

## Short answer

Per-comment AI-authorship attribution on customer verbatims cannot be done honestly,
and we measured that rather than assuming it. CLARA therefore ships an **ingestion
authenticity review** that reports provenance, duplication, coordination and volume
evidence, abstains loudly when a comment is too short to assess, and leaves the
exclusion decision to a human. It never removes anything on its own, and it never
tells a user that a particular person's complaint was written by a machine.

## What we measured

Corpus: 6,740 texts. 6,154 are real reviews published on Apple's App Store,
Trustpilot and Reddit, collected via official feeds (the closest available stand-in
for "human-written customer feedback"; an unknown fraction of real reviews are
themselves AI-assisted, so measured false-positive rates are an **upper bound**).
586 are texts we know a language model produced: the English paraphrases in CLARA's
six evaluation datasets plus the authored German golden-set items. Language is
confounded with class, so everything is read per stratum. Scripts and corpus:
`scratchpad/authenticity/` (build_eval_corpus.py, feature_probe.py,
naive_filter_harm.py, equity_probe.py, binoculars_probe.py, ppl_mechanism.py).

### 1. The obvious stylometric detector is a complaint filter

Built the detector any team would ship first (no emoji, no typo runs, even sentence
lengths, ends with punctuation, impersonal register) and tuned it to catch 81.2% of
the known machine text on the English stratum (607 platform / 558 LLM):

| | value |
|---|---|
| True-positive rate | 81.2% |
| False-positive rate on real reviews | **15.0%** |
| Precision at 1% AI base rate | 5% — 95 of every 100 flags is a real customer |
| Precision at 5% AI base rate | 22% — 78 of every 100 flags is a real customer |
| Mean stars, falsely flagged | **2.21** |
| Mean stars, not flagged | 2.70 |

The filter preferentially flags *angrier, longer, more careful* complaints. For a
feedback-intelligence product this is the worst possible failure direction: it
silences the customers whose problems most need to reach a human.

### 2. It flags some languages 3x more than others

Per-language flag rate on genuine reviews at the same threshold:

| Greek | Hungarian | Czech | Spanish | Swedish | German | Norwegian | English | Polish |
|---|---|---|---|---|---|---|---|---|
| 44.4% | 41.7% | 32.8% | 32.1% | 20.9% | 19.8% | 19.7% | 15.0% | 14.8% |

A 3.0x spread. The mechanism is worth stating plainly because it is how this bias
enters real systems: our feature lexicon encoded English and German first-person
markers and not Greek or Czech ones, so languages the builder did not think about
were penalised automatically. This is the same failure the thesis measures in
§5A.5 — a triage layer that decides *whose* problems get escalated.

### 3. The state-of-the-art model-based detector performs worse than chance

Binoculars-style cross-perplexity (Hans et al. 2024) with a Qwen2.5-0.5B observer
and Qwen2.5-1.5B performer:

| stratum | platform n | llm n | AUROC |
|---|---|---|---|
| EN, all | 576 | 558 | **0.326** |
| EN, 10–24 words | 170 | 430 | 0.329 |
| EN, 25–49 words | 153 | 112 | 0.256 |
| DE, all | 394 | 28 | 0.512 |

0.5 is a coin flip; below 0.5 is systematically inverted. At an 80%-recall operating
point it flagged **89.8%** of real reviews.

The mechanism is structural, not a model-size artefact. Mean log-perplexity under
Qwen2.5-1.5B:

| | real customer text | LLM text |
|---|---|---|
| English | 4.52 | 4.87 |
| German | 3.82 | 3.48 |

Genuine complaint text is formulaic and highly predictable, so in English it sits at
the low-perplexity end *where these methods expect machine text*. Worse, **the sign
flips by language**: a single global threshold is necessarily wrong in one of them.
Every perplexity-family detector (DetectGPT, Fast-DetectGPT, Binoculars) inherits
this, because they all assume machine text is the more predictable text.

### 4. Most verbatims are too short to assess at all

23% of the corpus is under 10 words. At the ~50-word floor the literature associates
with reliable detection, **82% of a real feedback corpus is unassessable**.

### 5. What the "AI-likeness" features were actually detecting

On the English stratum, the strongest separators were sentence-length variance
(0.00 for LLM text) and first-person voice (0.00 for LLM text) — both artefacts of
*our own paraphrasing house style* (single-sentence, third-person summaries). On the
German golden-set items, which were authored to *imitate* customer register, the
first-person signal **flips direction** (0.79 LLM vs 0.43 platform) and the
sentence-variance signal vanishes entirely (0.30 vs 0.31). Stylometry detects
register, not authorship. An adversary who prompts "write like an angry customer,
keep it short" defeats it — which is precisely the adversary that matters.

## What the market does

- Independent 2026 benchmarks put detector false positives at 1.6–12% on native
  speakers and **as high as 61% on non-native English writers**; short texts under
  200 words add roughly 8 percentage points of false positives. Vendors themselves
  advise never using a single detector score as proof.
  ([GradPilot 2026 comparison](https://gradpilot.com/news/ai-detector-false-positive-rates-compared),
  [AIBusted false-positive tests](https://blog.aibusted.com/how-often-do-ai-detectors-get-it-wrong/))
- OpenAI withdrew its own AI Text Classifier in July 2023 for low accuracy.
- The platforms that actually do this at scale lead with **behaviour, not text**.
  Trustpilot removed 4.5M fake reviews in 2024 with ~90% caught automatically, using
  IP addresses, device fingerprints, geolocation, timestamps, account history and
  posting velocity alongside content checks; Amazon uses graph neural networks over
  reviewer–product relationships. Practitioner analysis is explicit that behavioural
  signals beat text classifiers, and that general-purpose AI detectors have high
  false-positive rates on exactly the short conversational text reviews consist of.
  ([Amazon](https://www.aboutamazon.com/news/policy-news-views/how-ai-spots-fake-reviews-amazon),
  [Trustpilot method summary](https://wiserreview.com/blog/trustpilot-fake-reviews/))
- **CLARA cannot use most of those signals.** IP, device fingerprint and account
  history belong to the platform; CLARA receives text second-hand through connectors.
  The right conclusion is not to reinvent them badly but to treat the platform's own
  enforcement as part of a channel's trust level.

## The regulatory target is fakeness, not machine authorship

The FTC Rule on the Use of Consumer Reviews and Testimonials (16 CFR Part 465,
effective 21 October 2024) bans creating, buying or disseminating fake reviews
"whether generated by humans or artificial intelligence", with civil penalties up to
$51,744 per violation
([FTC](https://www.ftc.gov/news-events/news/press-releases/2024/08/federal-trade-commission-announces-final-rule-banning-fake-reviews-testimonials),
[eCFR](https://www.ecfr.gov/current/title-16/chapter-I/subchapter-D/part-465)).

The regulated harm is **fabrication and undisclosed incentivisation** — a review from
someone with no genuine experience — not machine assistance. A real customer who used
ChatGPT to tidy up a genuine complaint has not produced a fake review. A human who
invents a review has. A detector aimed at "AI-generated" is therefore aimed at the
wrong target, and would systematically mistake polished genuine feedback for the
violation while missing hand-written fabrications.

Two further constraints: labelling a natural person's text as machine-generated is an
inference about that person, which carries GDPR contestability expectations; and
sending EU customer feedback to a US detection API would contradict the EU
data-residency posture CLARA sells.

## What we shipped

Three tiers, in `services/authenticity.py`:

**Tier 1 — known facts.** Self-declared AI authorship (model boilerplate such as
"as an AI language model", or an explicit self-reference like "this review was
AI-generated"), and exact duplicates. The naive keyword version of the declaration
check is a trap in this domain: run against 6,154 real reviews it produced one false
positive, a long careful complaint containing *"I don't know if the reply to my review
was generated by AI or written by real person"* — the customer was criticising the
vendor's chatbot. The shipped check therefore requires a self-referential declaration
and disqualifies matches near reply/support/bot/chat context.

**Tier 2 — structural, cohort-level.** Volume bursts against a source's own trailing
median, batch uniformity of length and structure, channel trust, and a low-information
note. Two rules make these safe: batch findings **never** change an individual
signal's band (a cohort question must not become a verdict on a comment), and burst
wording is explicitly a question, because the measured corpus contains genuine 21x
launch-day spikes.

**Tier 3 — refused.** Per-comment authorship attribution from writing style. Not
shipped. `test_articulate_customer_is_never_flagged` and `test_no_signal_is_ever_dropped`
exist to stop it being added later.

**Equity guardrail.** The review computes its own flag rate per language stratum and
warns *inside the review queue* when the top stratum exceeds the bottom by 2x
(minimum 50 signals and 5 flags per stratum, so it does not cry wolf). A filter that
monitors its own disparate impact is the direct product analogue of the thesis's
escalation-equity measurement.

**Abstention.** Under 10 words the state is `insufficient_text`, surfaced as "too
short to assess". This mirrors `outcome_engine`'s refusal to fit an ITS it cannot
support.

### Behaviour on the real corpus

| scenario | result |
|---|---|
| 6,154 real reviews via a platform connector | **0.86% review-suggested** (all genuine exact duplicates), 25.1% honestly abstained, no false AI accusations, no spurious disparity warning |
| 5 duplicates + 1 self-declared AI text planted in 200 real reviews | 6/6 caught |
| 100 varied machine-written texts pasted as one CSV | **not caught** — reported below, not hidden |

The last row is the honest limit. A competently varied batch of AI-written text with
no duplication and normal length variance is not detectable by this gate, and by our
measurements not detectable by the alternatives either.

## Why the insight layer is already defended

The user's underlying worry is that junk verbatims distort insights. Independently of
this gate, `services/emerging.py` already requires corroboration before anything can
grade "act now": `MIN_ACTION_SOURCES = 2` **or** `MIN_ACTION_CUSTOMERS = 3`, plus
burst confirmation. A flood of injected reviews arriving through a single source with
no identified customers is held at "watch" with a stated reason. Cross-signal severity
(DP3) fuses corroborating evidence rather than trusting the loudest member. The loop
was already structurally resistant to this attack; the gate makes the suspicion
visible and the exclusion decision explicit and auditable.

## The sentence we put in the UI

> CLARA flags signals whose provenance or structure is unusual, and says so when a
> comment is too short to assess. It does not claim to know whether a person or a
> language model wrote any individual comment, and it never removes anything on its own.

## Open work

- Cohort exclusion UX: reversible, audited "exclude from insights" on a reason group,
  written to the approval-style audit record. The gate annotates today; the bulk
  action is not built.
- Publish flag rate and abstention rate per language into `published_metrics.json`
  and the model card, the same way triage accuracy is published.
- Cross-batch template-family detection (near-duplicate currently runs within the
  recent corpus window).
- Watermark/provenance ingestion (C2PA, SynthID-Text) if and when connectors expose
  it: that is the only route to an honest per-comment determination, and EU AI Act
  Article 50(2) machine-readable marking makes it more likely over time.
