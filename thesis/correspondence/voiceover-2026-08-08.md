# Voice-over script — 8 Aug 2026 progress review

Spoken script for the 20-slide deck. Written to be **said**, not read off the screen. Plain language; the emphasis is on *why* each choice was made, because a choice you can justify is a contribution and a choice you can only describe is a feature list.

**[CORE]** = the 11-slide spine (~15 min). **[RESERVE]** = only if the conversation goes there.
Timings assume you talk at a normal pace and don't read the bullets aloud.

---

## Slide 1 — Title **[CORE · 20s]**

> "Thanks for making the time, and sorry about the gap — the August first slot slipped and I didn't want to lose three weeks waiting, so I kept working on the parts that didn't need anyone's permission.
>
> That turned out well, because the biggest open item on my list closed. The evaluation is finished. That's the story today."

---

## Slide 2 — The problem **[RESERVE · 45s]**

*Skip unless she wants the framing again. If you do show it:*

> "Three facts set this up. Fewer than a third of companies actually close the loop on feedback they collect. Acting isn't the same as solving — there's a field experiment with about one and a half million Uber customers where apologies alone didn't restore spending, and repeated apologies actually reduced it. And what teams do learn, they forget, so they solve the same problem again next year.
>
> So my claim is: this is not an analytics problem. Companies don't lack insight, they lack a governed path from insight to action, and a memory of what worked. Those are the two missing pieces."

---

## Slide 3 — Research questions **[CORE · 1 min]**

> "One change here I need your view on. RQ3 used to be a single question — how accurately does the pipeline reproduce human labels. After the August run I split it into two.
>
> RQ3a is accuracy: how well does it label. RQ3b is equity: is that accuracy *the same for everyone*, or are some customers' problems less likely to be picked up.
>
> I split it because the equity answer turned out to be the more important one, and it was hiding inside RQ3 as a sub-clause. For a Responsible AI thesis that felt wrong.
>
> RQ4 — the practitioner study — has not started. That's the critical path and it's my second ask today."

---

## Slide 4 — The artifact, end to end **[RESERVE · 1.5 min]**

> "This is the whole loop in one picture. Signal comes in, gets enriched, gets grouped into insights, rules propose an action, a human approves, we execute, we measure whether it worked, and we write down what we learned so it can be retrieved next time.
>
> The line I'd draw your attention to is the split between the blue and the white. **Deterministic code owns validation, conflict resolution, execution and audit. The language model only runs at named stages.**
>
> That's the central architectural commitment, and it's worth saying why."

**→ If she engages here, go to slide 5. This is the WHY block she'd most enjoy.**

---

## Slide 5 — System architecture **[RESERVE, but your strongest reserve · 2 min]**

*She's an AI architecture professor and has never seen this slide. If the conversation turns architectural at all, this is where to go.*

> "Four choices here, and I'd rather explain the reasoning than the boxes.
>
> **First — why the model is boxed in.** If a model can decide anything at any point, you can't say in advance what the system will do. If it only runs at named stages — read this text and label it; group these labelled items; draft this recommendation — then every point where it can influence an outcome is a point I can name, test and audit. Everything between those points is ordinary code with unit tests. The cost is real: the ceiling is lower, because the system can't be cleverer than the stages I designed. I think that's the right trade when the output creates tickets and messages that reach actual customers.
>
> **Second — why approval is a graph interrupt, not a screen.** If approval lives in the UI, someone can call the API directly and go around it. Because it's an interrupt node in the LangGraph, there is no code path from an insight to an external effect that doesn't stop there. The gate is in the machinery, not in the manners. That's what lets me call it an Article 14 control rather than a convention.
>
> **Third — why severity is deterministic code, not a model judgement.** Severity decides what gets escalated. If a model scores it, then severity changes silently whenever the model changes. Computing it from named factors means I can show an auditor exactly why something ranked urgent, and it doesn't drift under me.
>
> **Fourth — why the model layer is provider-agnostic.** Two reasons. Research: my evaluation harness can benchmark any model with zero code change, which is how I know the model isn't my bottleneck. Practical: if a German company says the data can't leave the EU, that's a configuration change rather than a rewrite. In August I made that properly true — embeddings can now point at a different provider from chat, so you can put the embedding model in the EU independently."

**If she asks about the database:** "Tenant isolation is enforced by Postgres row-level security, underneath the application. I moved it there because a review found the isolation was declared but not actually enforced — one forgotten WHERE clause is a leak. Below the app, an app bug can't bypass it."

---

## Slide 6 — Pipeline and approval sequence **[RESERVE · 1.5 min]**

> "Same loop, two views. What I'd want to justify is why each stage exists — because each one is there because the previous one isn't enough on its own.
>
> **Enrichment** alone gives you neatly labelled complaints. That's a better inbox, not a better company.
>
> **Synthesis** exists because one angry customer isn't a signal — a pattern is. Severity comes from the corroborating set, not the loudest voice.
>
> **Rules** exist because 'who should own this' is company policy, not a model's opinion. That belongs in something a manager can read and edit.
>
> **Approval** exists because — and I'll show you the number later — the pipeline is not accurate enough to route on its own.
>
> **Measurement** exists because of the Uber result: acting is not solving.
>
> **Learning** exists because otherwise you rediscover the same fix every quarter.
>
> The one detail I'd point out: the outcome contract is fixed *before* the action executes. That's deliberate — it means nobody can go looking for a metric that happens to have moved afterwards."

---

## Slide 7 — Data model **[RESERVE · 1 min]**

> "The short version: my two claimed contributions are tables, not prose. An action is bound to an outcome contract at the moment it's created — one to one, in the schema. So 'closed' is a row with evidence attached, not a status someone set. And learnings carry their own confidence and half-life as columns, so the decay is computed from data and you can audit it with a query."

---

## Slide 8 — Five design decisions **[RESERVE · 2 min]**

> "Five decisions the literature doesn't settle. Each one has a cost, and I state it — a design principle that buys something for nothing is a platitude.
>
> **Rule conflicts.** Eventually two rules fire on the same insight. If the resolution is implicit, nobody can explain the result. So: priority, then specificity, then deduplicate by action type — and log which rule lost. The cost is that it entrenches a *wrong* high-priority rule just as faithfully as a right one.
>
> **Decaying learnings.** A fix that worked eighteen months ago may not apply now, but nobody ever goes back and deletes old lessons. Decay means old evidence loses weight automatically instead of relying on someone's discipline. The cost is that the half-life is genuinely a guess — I picked it, I didn't derive it.
>
> **Severity from the set.** The loudest customer isn't the biggest problem. I require corroboration before something can be marked act-now. The cost is real: this can bury the rare catastrophic single report, so it needs an override.
>
> **Retrieving past learnings.** A memory that isn't retrieved at the moment of decision is just a log file. So retrieval is wired into the decision path. The cost is that retrieval quality gates the entire benefit.
>
> **Per-industry profiles.** 'Urgent' means something different in fintech than in industrial adhesives. So I adapt by configuration — weight overlays per sector — rather than retraining. The cost is that authored priors can encode a stereotype as easily as expertise; inspectability is the only safeguard.
>
> On the decay one — I want to flag that I narrowed my own novelty claim here. MemoryBank already applies forgetting-curve decay to conversational memory. Mine is decayed *evidence confidence over action-outcome learnings, retrieved under governance*. I cite the prior art myself rather than wait for an examiner to find it."

---

## Slide 9 — Responsible AI **[RESERVE · 1.5 min]**

> "The argument here is that governance isn't a module I bolted on — the loop itself is the control surface.
>
> The approval gate deliberately goes beyond the Article 14 minimum. The reason is in the literature: awareness-based oversight doesn't reliably counter automation bias — people rubber-stamp. So the gate adds friction, shows the evidence and the model score, and attributes the decision to a named person.
>
> One naming decision I'd defend: I renamed 'confidence' to **model score**. It's an uncalibrated heuristic. Calling it confidence implies a probability I haven't earned. Saying so is the feature."

---

## Slide 10 — Since your last look, part 1 **[CORE · 1.5 min]**

> "Everything on this slide is new to you — it's the July hardening plus August.
>
> July: multi-factor auth, cookie sessions, rate limiting, connector secrets encrypted at rest, four-eyes approvals, and guardrails that are now actually measured rather than just declared.
>
> August, and this is the one that matters conceptually: **model sovereignty went from a claim to a fact.** Embeddings can now use a different provider from chat, with a migration to match. So 'you can run this inside the EU' is a config change now, not a promise.
>
> The pattern across all of it is review-then-harden. Two independent adversarial audits of my own July merges produced the rate-limiter and fail-closed fixes. The lesson I keep: declared controls are not enforced controls until someone attacks them."

---

## Slide 11 — Since your last look, part 2 **[CORE · 2 min — the most important slide]**

*Don't soften this. Volunteering it is what makes it rigour instead of sloppiness.*

> "This is the one I most want to tell you about.
>
> Since April my results table had a row marked 'pending' — my own pipeline scored against my own 188-signal corpus. I believed it simply hadn't been run.
>
> It had been running. It was **silently broken**. The model gateway rejects the default user-agent header with a 403, and my script exited with status zero after writing an empty file. A green exit code on an empty result, for weeks.
>
> I'm telling you this rather than quietly rerunning it, for two reasons. One, it's exactly the failure mode this thesis warns about elsewhere — a declared check that was never an enforced check. It happened inside my own evaluation harness. Two, it's now written into the chapter as a disclosure, and the fix fails loudly on empty output.
>
> The run completed on the 4th, 188 out of 188. And it changed three things: RQ3 split into accuracy and equity; journey stage and owner got scored for the first time; and I had to **retract** a fairness claim I'd already written, because language turns out to be confounded with sector in my corpus."

---

## Slide 12 — Two evidence streams **[CORE · 30s]**

> "One thing to hold in mind for the next three slides: there are two different gold standards and I never merge them.
>
> This chapter's harness scores 188 signals labelled independently, using the star rating as the reference — which is honest because it's independent of the text the classifier reads. Separately, the product has its own curated 100-case set. Different standards, so different numbers, reported separately. When they disagree I quote the lower one."

---

## Slide 13 — Result 1: accuracy **[CORE · 2 min]**

> "Three ways to read customer feedback, from crudest to most sophisticated, all scored on identical data.
>
> A word-list method — the pre-AI approach — gets sentiment right **37%** of the time. A simple trained model, TF-IDF and logistic regression, gets **78%**. My LLM pipeline gets **86%**.
>
> Why does the word list fail so badly? Because real complaints don't contain angry words. 'Transaction history cannot be exported to CSV' is a furious customer with no negative vocabulary. It reads 58 of 94 genuine complaints as neutral. That's a finding, not a strawman.
>
> Now the part I find more interesting. On *severity* — how bad is this — the sophisticated model barely beats the simple one: 0.65 to 0.68. Big gain on sentiment, almost nothing on severity.
>
> Why? Severity in this data is carried by words a trained model already picks up — 'blocked', 'fraud', 'refund'. Sentiment isn't, because it's implied rather than stated.
>
> So the conclusion isn't 'use the biggest model'. It's that a deployer has a genuine choice: a cheap local model may be sufficient for severity routing, while the contextual model earns its cost on sentiment. I think that's more useful for a design thesis than one dominant number."

---

## Slide 14 — Result 2: equity **[CORE · 2 min — say the number slowly]**

> "This is the result I think matters most.
>
> Take only the complaints that genuinely deserved escalation — where the human label says this needs a person, now.
>
> The word-list method caught about one in five of the English ones. And **zero of the eight German ones. None.**
>
> My pipeline catches roughly seven of eight in both languages — 87.5 and 87.8. Near parity.
>
> Here's why that's different from an accuracy difference. A worse classifier doesn't just score lower on a chart. It means some customers' problems are systematically less likely to ever reach a human being. That's a property of the *loop*, not of a classifier. And it's determined almost entirely by which triage method you chose.
>
> Now the limits, before you ask for them. The German escalate group is **eight signals** — that's a wide interval, and I say so. And language is confounded with sector here: my German data is mostly the industrial set, my English is mostly fintech. So the claim I make is that *method choice governs escalation equity on this corpus* — not that parity is established in general.
>
> That confound is also what forced the retraction I mentioned. I had written a cross-language accuracy comparison. It would largely have restated which industry each language came from. I took it out rather than defend it. Only escalation recall survives, because it conditions on the human label."

---

## Slide 15 — Result 3: routing **[CORE · 1.5 min]**

> "I also asked it to pick which stage of the customer journey each item belongs to, and which team should own it.
>
> Journey stage: **59% correct** across 27 possible values. If you always guessed the most common one you'd get 20%. Owner: **40% correct** across 51 teams, against a 15% floor.
>
> So it's finding real signal — roughly three times better than guessing. And I want to be blunt: **40% is nowhere near good enough to route automatically.** An owner assignment that's right two times in five would misroute the majority of problems.
>
> That's an unflattering number and I'm putting it on a slide on purpose, because it's the strongest argument for my own design. The approval gate is not friction added to an otherwise reliable pipeline — **it is the control that makes a pipeline of this accuracy safe to deploy at all.** These fields are useful as a draft a human corrects. They're useless as an unattended decision. The numbers force that reading; I didn't choose it.
>
> One caveat: I scored these with the list of valid options supplied. That's easier than the production condition, so 59 and 40 are an upper bound, not an estimate."

---

## Slide 16 — Result 4: the memory **[CORE · 1 min]**

> "When I feed stored learnings back into the recommendation step, the share of recommendations that contain the previously-successful remedy goes from **21% to 71%**. So the memory demonstrably steers decisions rather than just decorating them.
>
> And here's the boundary, which is the sixth of my six limitations. The outcomes those learnings came from are still **simulated**. So I've shown the mechanism works. I have not shown it makes decisions *better*. I'm claiming mechanism, not benefit — and that gap is my third ask."

---

## Slide 17 — Proven, demonstrated, pending **[CORE · 1.5 min]**

> "This is my honesty map — every claim with its status, stated once, and the chapters have to agree with it.
>
> Triage accuracy: measured, two independent gold standards. Escalation equity: measured but bounded. Routing: measured but bounded. The memory's influence: partially measured — mechanism yes, benefit no. Outcome contracts: demonstrated and instrumented, not measured. Practitioner value: pending, and interviews have not started.
>
> One honest note about this table: three of these rows changed status in August, which meant six places in my manuscript disagreed with it until this week. I've fixed that. The discipline only works if you actually re-run it when the evidence moves."

---

## Slide 18 — Positioning **[RESERVE · 1 min]**

> "Briefly, because it's context rather than contribution. Forrester retired their feedback-management ranking this year — the analysis half is considered solved. Everyone is now competing on autonomous action and trust. Each competitor holds a piece; nobody verifiably holds the combination of measured closure, approval gates, decaying memory and EU deployment. And I applied my own verification standard to their claims rather than believing their marketing."

---

## Slide 19 — Limitations and next **[CORE · 1.5 min → hand into the asks]**

> "The limitations, stated rather than buried: a modest corpus, small-N qualitative work, and I'm both the researcher and the founder — which I manage with external labels, standard instruments and a reproducible harness, but can't eliminate.
>
> New this month, from the completed run: the language-sector confound, the eight-signal German group, routing as an upper bound, and two fields still unscored.
>
> On future work — item two, unifying the two evidence streams, is **done**. What's left is one live outcome contract, and that's where I need your steer. So let me stop there and ask you three things."

---

## The asks — say these out loud, they are not on any slide

*This is the gap: the asks live in the brief and the meeting card, but nothing on screen prompts you. Say them from here.*

> **"First — evidence triage. The 188-run is done, so that ask is closed. Of what's left — twelve to fifteen interviews, one live outcome measurement, a local-versus-cloud model benchmark, and scoring the two remaining fields — which are actually required for September, and which are nice-to-have? And realistically, what's your turnaround on a full draft?"**
>
> **"Second — interviews and ethics. Recruitment hasn't started and August is the window. Is there any OPIT step beyond your confirmation before I approach practitioners? And if twelve to fifteen looks unrealistic from here, is leaning harder on the survey an acceptable fallback?"**
>
> **"Third — simulated outcomes. Is this defensible in September with outcomes still simulated — where DP1 rests on demonstration and perception — or do we force one small live measurement into August, knowing it costs interview time?"**

*If time remains:* equity-only as the RQ3b claim (4) · supplied-inventory routing, fair to report? (5) · should Chapter 6 compare against agent designs? (6) · MemoryBank boundary tight enough? (7) · per-industry placement (8) · the review episode, now compressed — does it land? (9) · IP letter due 31 Aug, defense window, deck ahead of time (10).

---

## Slide 20 — Contributions **[RESERVE — skip in a progress review]**

End on the asks, not on this. Only use it if she asks you to summarise the contribution.

> "A working artifact running the full governed loop in production; six design principles each stated with its cost; a real-data evaluation across three sectors and two languages showing that method choice is an equity decision, not only an accuracy one; and Responsible AI as integral design rather than a bolt-on."

---

## If you only remember four sentences

1. The model is boxed into named stages so that every point it can affect the outcome is one I can name, test and audit.
2. The word-list method escalated none of the eight critical German complaints — method choice decides whose problems reach a human.
3. Routing is 40% accurate, which is exactly why the approval gate has to exist.
4. The memory steers decisions; whether it improves them needs one live outcome contract, and that's my third ask.
