# CLARA — spoken brief

Narration script for text-to-speech. Written to be *heard*, not read: short sentences, no tables, no symbols, numbers spelled out, and spoken signposts instead of headings. Regenerate the audio with `thesis/make_audio.sh`.

---

Part one. What this is.

This is a full explanation of CLARA — the problem it addresses, the idea behind it, how it is built, how it is governed, and what has actually been measured. It runs about twenty minutes. There are nine parts, and I will announce each one as it begins.

CLARA is a governed customer-feedback intelligence platform. It takes customer feedback from many sources, works out what the underlying problems are, proposes actions, routes those actions through a mandatory human approval step, executes the approved ones in the tools a company already uses, measures whether the problem actually got better, and finally stores what was learned so it can inform the next decision. It is in production, on European infrastructure. It is also the artifact of a master's thesis in Responsible Artificial Intelligence, which is why almost every claim it makes is accompanied by an explicit statement of how strong the evidence is.

Part two. The problem.

Organisations have never collected more customer feedback. They run satisfaction surveys, net promoter score surveys, and customer effort surveys. They accumulate support tickets, app store reviews, social media mentions, sales call transcripts, and product analytics. The idea of the voice of the customer was formalised three decades ago, and it has grown from occasional market research into an always-on capability.

And yet. Research by Bone and colleagues, published in twenty seventeen, found that fewer than thirty percent of firms systematically close the loop on the feedback they gather. What is striking is the reason. The barriers they identified were not analytical. Companies were not failing because they could not understand what customers were saying. They were failing because of departmental silos, unclear ownership, and the simple absence of any workflow that routes a problem to the person responsible for fixing it.

Industry evidence has since made this worse, not better. Forrester's twenty twenty-five Customer Experience Index recorded customer experience quality at an all-time low. Their voice-of-the-customer survey found that most customer experience teams still cannot get stakeholders to act on the insights they produce. Only about a quarter communicate those insights in a timely way. The diagnosis that keeps recurring in the industry is that customer experience programmes have an action problem. Insight is cheap. Execution is what is missing.

The thesis breaks this into four specific deficiencies.

The first is signal fragmentation. Customer signals arrive across many disconnected sources and are rarely unified into a single prioritised view. So it is genuinely hard to know which problem matters most this week.

The second is the insight-to-action gap. Even when a problem is clearly identified, organisations lack a structured, governed mechanism to decide what action is warranted, route it to the right owner, and execute it in the systems they already use.

The third is unmeasured closure. When action is taken, it is seldom tied to an explicit outcome. So organisations cannot tell whether the loop actually closed — whether the customer's problem was resolved, as opposed to merely whether a ticket was created. This matters more than it sounds. There is a natural field experiment by Halperin, Ho, List and Muir, published in the Economic Journal in twenty twenty-two, covering roughly one and a half million customers. It found that apologies after service failures did not restore future spending on their own. Repeated or promise-laden apologies actually reduced it. In other words, acting on feedback without measuring the outcome can make things worse. Not neutral. Worse.

The fourth deficiency is lost organisational memory. What worked, in which context, is rarely written down. Hard-won lessons depreciate and are forgotten, so organisations relearn the same things repeatedly.

Part three. The idea.

The central claim of this work can be stated in one sentence. Closing the feedback loop is a workflow and governance problem, and the two primitives the market is missing are a measured outcome contract and a perishable learning memory — not a better dashboard.

Let me unpack both of those, because everything else follows from them.

A measured outcome contract means that when an action is approved, it is bound at that moment to a specific metric, a baseline, a time window, and a threshold that would count as success. The contract is proposed automatically when someone approves the action, and it can be edited or declined. The point is that the system commits, in advance, to what "this worked" would look like. Afterwards it goes and measures. If the data is insufficient, it says so rather than guessing.

A perishable learning memory means that when the loop completes, the lesson is stored with a confidence value that decays over time. Something learned about customer behaviour three years ago should not carry the same weight as something learned last month. The decay is deliberate. Organisational knowledge has a half-life, and pretending otherwise is how companies end up confidently acting on stale evidence.

There is an honesty point attached to that second idea that is worth stating. The author found prior art against his own novelty claim and narrowed it himself. A system called MemoryBank, published at the AAAI conference in twenty twenty-four, already applies forgetting-curve-style decay to conversational memory in language models. So the contribution here is stated more precisely: it is not decay-based memory in general, but decayed evidence confidence over organisational action-outcome learnings, retrieved under governance into future action decisions. The thesis cites the prior art itself rather than waiting for an examiner to find it.

Part four. What CLARA deliberately is not.

Scope discipline is a design contribution in its own right, so this is worth stating plainly. CLARA is not a survey collection tool. It is not a customer data platform. It is not a campaign delivery engine. It is not a product management suite. And it is not a chat-first analytics product. Those are all treated as systems to integrate with, not systems to rebuild.

There is one more exclusion that matters more than the others. CLARA does not do autonomous customer contact. An earlier design considered configurable autonomy levels, where an administrator could let certain low-risk actions execute without human review. That was explicitly rejected, and the reasoning is worth quoting in spirit: it would reopen the ungoverned path that the product exists to close. The approval gate is not a setting. It is the architecture.

Part five. The loop and the architecture.

The cycle has four stages, and they give the platform its shape: Signal, then Insight, then Action, then Learning.

Underneath that, the pipeline has seven concrete stages. Ingestion, where signals arrive from connectors or file upload. Enrichment, where a language model assigns sentiment, urgency, theme, and other attributes. Synthesis, where many individual signals are clustered into a smaller number of real problems. Action, where a rule engine proposes what should be done. Approval, the human gate. Measurement, where the outcome contract is evaluated. And Learning, where the result is codified and stored with decaying confidence. Governance runs across all seven rather than sitting in one of them.

Now the technical architecture. The front end is Next.js and TypeScript. The back end is FastAPI, in Python, with roughly forty-three REST endpoints. Orchestration uses LangGraph. The database is PostgreSQL with the pgvector extension for similarity search, with row-level security for tenant isolation. Tracing uses Langfuse. Model access goes through a provider-agnostic routing layer, which means the underlying language model can be swapped, including for a self-hosted European model.

In production, the front end runs on Vercel, the API runs in Docker on a European virtual private server behind the Caddy web server, and the database is Postgres hosted in Frankfurt. That last detail matters: the European data residency claim is a deployed fact, not a design intention.

But the architectural decision that actually matters is this one. Deterministic logic lives in ordinary, testable code. That includes validation, rule conflict resolution, the audit trail, action execution, and outcome scoring. Language model reasoning is bounded, behind a single interface, and confined to named stages: enrichment, synthesis, and learning extraction.

The consequence is that the model is a contained component, not the controller. The human approval step is literally an interrupt node in the LangGraph state machine — the graph stops and waits. It cannot be skipped by a model deciding it is confident. When you hear about agentic systems where a language model plans and executes freely, this is the deliberate opposite of that, and the thesis argues the trade-off is worth it. The cost, stated openly, is that this design caps the ceiling: the system will never be cleverer than its bounded stages allow.

Part six. The five design decisions.

The design contribution is articulated through five decisions that the existing literature does not resolve. Each one is a real choice with a real cost.

The first is rule conflict resolution. When two automation rules both match the same problem and disagree, something has to break the tie. CLARA resolves by priority first, then by specificity, then by removing duplicate action types. Superseded rules are logged rather than silently dropped, so a reviewer can see what did not happen and why. The cost is configuration debt: more rules means more conflicts to reason about.

The second is confidence decay in learnings. A learning's confidence is its base value multiplied by one half, raised to the power of its age divided by a half-life. Stale learnings get flagged. The cost is that the half-life is a parameter nobody actually knows the right value for.

The third is cross-signal severity. Severity is computed from the set of related signals, not from the single loudest complaint. It combines the strongest urgency, the volume, and the proportion that are negative. There is a corroboration floor: before something can be marked as act-now, it needs at least two independent sources or at least three identified customers. Near-duplicate signals are annotated rather than deleted, so nothing disappears silently. The cost is real and stated: a set-based view can bury the rare catastrophic single signal.

The fourth is relevant past-learnings retrieval. When a new decision is being made, similar past learnings are retrieved using vector similarity, re-weighted by their decayed confidence, so old lessons surface less strongly. There is an explainable fallback based on token overlap for when embeddings are unavailable.

The fifth is per-industry scoring profiles. Different sectors weigh impact differently, so the platform ships named weight profiles for fintech, food delivery, business-to-business manufacturing, and software. Crucially, this is adaptation by configuration, not by retraining a model. The cost, again stated openly, is that those weights are authored by a human and can embed sector stereotypes as easily as they encode expertise. The safeguard is that they are inspectable.

Part seven. Responsible AI, and how it is built in.

This is a Responsible AI master's thesis, so this part is not decoration.

Human oversight is aligned with Article fourteen of the European Union AI Act, and deliberately goes beyond its minimum. Research by Laux and Ruschemeier argues that awareness-based oversight will not de-bias humans by itself — telling someone to pay attention does not make them pay attention. So the gate adds deliberate friction, displays the underlying evidence, and attributes each decision to a specific identified person, whose identity is bound to their authentication token rather than self-asserted.

The audit trail is aligned with Article twelve. Transparency labelling on AI-generated text is aligned with Article fifty, including an editorial review flow for anything customer-facing.

There is a works council mode, designed with German co-determination law in mind. It shows aggregate-only views with role-redacted reasoning, suppresses small cells below a threshold of five, and there is an automated test in the continuous integration pipeline that walks the output and fails the build if any field capable of identifying an individual leaks through.

There is an artificial-intelligence-literacy onboarding module, addressing the Article four duty on deployers. And there is model sovereignty: the option to run against a self-hosted, European-resident model.

Three honesty mechanisms deserve particular mention, because they came out of criticism.

The first is that what used to be called a confidence score is now called a model score. It is an uncalibrated heuristic, and calling it confidence implied a statistical property it does not have. Renaming it was the fix. Actually calibrating it is still open work.

The second is evidence grading, on a scale from A to E, so that a claim backed by an instrumented measurement is never visually confused with a claim backed by someone typing a number into a box. Manual entries are force-stamped as unverified manual observations.

The third is that guardrails are measured rather than merely declared. This one has a history, which brings us to the next part.

Part eight. Verification, and the lesson that shaped the work.

In July twenty twenty-six, two independent language-model-based strategic reviews were run against the platform. They were harsh. One scored the scientific validity of the evaluation at two out of ten and security at three out of ten.

The response is the interesting part. Rather than accepting or dismissing the criticism, forty-five specific claims were extracted and verified one at a time by nine independent read-only agents. Roughly twenty-seven were confirmed, thirteen partially, two were refuted, and one was unverifiable. That produced a thirty-eight item plan, which produced twenty pull requests, which were then confirmed in production by seventeen live checks.

An earlier structured code review had found fifty-eight defects, ten of them high severity. Among them: read endpoints with no authentication, an authentication guard enforced only in the browser, and row-level security that was declared but not actually enforced, because the application connected to the database as the table owner.

That last one produced the sentence that became the thesis's methodological spine: declared controls are not enforced controls. And it is worth noting that this exact class of problem was found again during this work — the database role in production still has the bypass privilege that overrides row-level security, which the platform's own smoke test detects and reports honestly rather than hiding. The lesson keeps proving itself.

Part nine. What has actually been measured, and what has not.

There are two independent evaluation streams, and they are deliberately never merged, because they use different gold standards.

The first stream is a corpus of one hundred and eighty-eight real, publicly-sourced, paraphrased and de-identified customer signals, across three sectors — a German fintech, a business-to-business industrial adhesives manufacturer, and a food delivery service — in English and German. Three predictors are compared on identical labels.

On sentiment, the rule-based lexicon floor gets thirty-seven percent accuracy. A lightweight classical machine learning model gets seventy-eight percent. The platform's language model path gets eighty-six percent.

On risk severity, the keyword floor gets forty-one percent, the classical model sixty-eight percent, and the language model path seventy-two percent.

Two findings there are more interesting than the headline. First, the gain from contextual reasoning is large on sentiment but slim on severity — three points of macro F-one against fifteen. So a cheap local model is close to sufficient for severity routing, which is a genuine design trade-off for anyone weighing cost, latency and data sovereignty. Second, and this one only emerged from the evaluation rather than being predicted: the choice of method turns out to be an equity decision. Measuring escalation recall — that is, of the signals that genuinely warranted escalation, how many were actually escalated — the keyword floor escalated zero out of eight critical German signals, while catching about a fifth of the English ones. The language model path escalated German and English at near-identical rates, eighty-seven and a half percent against eighty-seven point eight. In plain terms: with a naive triage layer, German-speaking customers with serious problems would simply not have reached a human. That is a fairness property of the whole loop, not of a classifier.

That finding carries two disclosures. The German stratum is only eight signals, so the estimate is imprecise. And language is confounded with sector in this corpus, because the German signals are largely the industrial dataset. Both are stated in the text rather than buried.

The second evaluation stream is the platform's own committed golden set — one hundred hand-labelled cases, seventy-two English and twenty-eight German — which the platform re-runs against itself. It reports ninety-seven percent sentiment accuracy and ninety percent urgency accuracy, with confidence intervals, and a statistically significant improvement from few-shot examples. Its limits are disclosed in the published model card: the German cases are authored rather than naturally occurring, and the hallucination check covers English items only, by construction, because applying it to German would falsely flag correct answers.

Now the honest gaps, because they matter as much as the results.

The outcome data is still simulated. The measurement machinery is real, tested, and shipped — it uses an interrupted time series design, which is a segmented regression at the moment the action was taken, with genuine honesty rules: below ten days of prior data or five days of subsequent data it refuses to fit a model and reports a plainly labelled simple difference with no confidence interval. But no real action has yet completed a full measurement window on live data. That is the single most important open item, and the work to start it is underway.

The practitioner study has not started. The protocol, interview guide, consent forms, and the usability and technology-acceptance instruments are all complete and waiting. Twelve to fifteen practitioner sessions are planned. Nothing has been simulated in their place; the results sections sit empty.

And the enrichment pipeline's theme, journey stage, owner, and recommended action fields carry labels in the corpus but are not yet scored — the semantic agreement procedure designed for them has not been executed. The thesis says so explicitly rather than implying coverage it does not have.

Closing.

The broader argument is that an action-taking artificial intelligence system in customer operations can be both useful and responsible by design — that closing the loop and governing the closing are not opposing goals, but two halves of the same well-designed workflow.

What makes that argument credible is not the feature list. It is that the same verify-before-believe discipline the platform imposes on its own actions was turned on the platform itself, repeatedly, and the claims that survived are the ones being made. The claims that did not survive were narrowed, retracted, or moved to future work.

That is CLARA.
