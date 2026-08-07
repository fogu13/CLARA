# Advisor brief — meeting with Prof. Zorina, 8 Aug 2026

Prepared 7 Aug. Two parts: a ready-to-send email (send ahead of the call, or use it as the update itself), and a call agenda with the numbered asks.

**Context she needs in one line:** the 1 Aug meeting did not happen, so nothing since the 17 July check-in has been in front of her — including the completed evaluation run, which is the reason this update is worth reading.

**Attachments:** `defense/defense_deck.pptx` (20 slides, rebuilt 7 Aug) and, if she wants the manuscript, `build/thesis.docx` (rebuilt 7 Aug — first rebuild since 13 Jul).

---

## Email draft

**Subject:** The evaluation is complete — all three predictors on one gold standard, and one claim retracted

Dear Prof. Zorina,

Apologies for the gap since our 17 July call — the intended 1 August check-in slipped, and rather than wait I kept working on the evidence that needed nobody's permission. That turned out to be the right call, because the biggest open item on my list has closed.

**1. The LLM evaluation finally ran — and it had been silently broken, not simply un-run**

Since April the results table in Chapter 5 has carried a row marked *pending*: the artifact's own enrichment path scored against this thesis's 188-signal seed-labelled corpus. I had believed it was merely unrun for want of a keyed execution. It was in fact **broken in a way that reported success**: the model gateway rejects Python-urllib's default User-Agent with a 403, and the prediction script exited with status 0 after writing an empty results file. A green exit code on an empty result, for weeks.

I mention this not as an anecdote but because it is the same failure mode this thesis argues about elsewhere — *declared controls are not enforced controls until adversarially verified* — and it happened inside my own evaluation harness. The fix was a User-Agent header plus a loud failure on an empty result set.

The run completed on 4 August, enriching 188 of 188 signals. All three predictors now sit on one gold standard:

| Predictor | Sentiment accuracy (n=153) | Risk macro-F1 (n=106) |
|---|---|---|
| Rule-based lexicon / keyword floor | 0.37 | 0.26 |
| TF-IDF + Logistic Regression (5-fold CV) | 0.78 | 0.65 |
| **LLM enrichment path** | **0.86** | **0.68** |

The shape of that gain is more interesting than its size. Contextual reasoning buys a great deal on sentiment (macro-F1 0.52 → 0.67) and very little on severity (0.65 → 0.68) — severity in this corpus is carried by lexical markers that character n-grams already learn once they are *learned* rather than hand-listed. So the loop's precondition is satisfiable by more than one method, and the choice among them is a genuine design trade-off — cost, latency, model sovereignty — rather than a foregone conclusion. That is a more useful result for a design-science thesis than a single dominant number would have been.

**2. The equity result, which I think is the real finding**

The sharpest consequence is not accuracy but **who gets escalated**. Measuring equal opportunity — recall on the signals whose gold label warrants escalation, which conditions on the gold label and so is not distorted by very different base rates:

| Escalation recall | n | Keyword floor | LLM path |
|---|---:|---:|---:|
| German | 8 | **0.0%** | 87.5% |
| English | 41 | 19.5% | 87.8% |

The keyword floor escalates **not one** of the eight genuinely critical German signals, while catching a fifth of the English ones. The contextual path reaches near-exact parity. An uneven triage layer does not merely score worse — it means some customers' problems are systematically less likely to reach a human at all. That is a fairness property of the *loop*, not of a classifier, and it is the strongest Responsible-AI finding the thesis has.

It is bounded, and I state the bounds rather than let them be found: the German gold-escalate stratum is eight signals, and language is confounded with sector in this corpus.

**3. What I retracted**

That confound cost me a claim I had already written. Language is not independent of sector here — the B2B stratum is almost entirely German, fintech overwhelmingly English — so an aggregate "German versus English accuracy" comparison would largely restate the sector composition. I had a narrowing-cross-language-gap claim in the draft. I **removed it** rather than defend it, and §5A.5 now says explicitly that no such claim is made and why. Only escalation recall survives, because it conditions on the gold label.

This is the same discipline as the urgency result, which I withheld at n=80 (McNemar p = 0.219) and now claim at n=100 (p = 0.039, three consecutive runs). Both directions of that discipline are in the text.

**4. Consequences for the structure**

RQ3 was doing two jobs, so it is now **RQ3a (accuracy)** and **RQ3b (equity)** — the equity question earned its own place rather than living as a sub-clause. Journey stage and recommended owner, described in every prior draft as "labelled but not scored", are **now scored** under a supplied closed inventory: journey 0.59 against a 0.20 majority-class floor over 27 classes, owner 0.40 against 0.15 over 51. Both clear their floors by a wide margin and **neither is anywhere near good enough to route autonomously** — which I have written up as evidence *for* the mandatory approval gate. An owner assignment correct two times in five would, as unattended automation, misroute the majority of problems. The gate is not friction added to a reliable pipeline; it is the control that makes a pipeline of this accuracy deployable at all.

**5. Manuscript state, honestly**

The new results forced a currency problem I have now repaired. Chapter 5's own §5A.7, plus Chapters 3, 4, 6, 7 and Appendices B and D, were still telling the pre-run story — §6.4 listed the completed run as "remains pending", and Appendix B published a superseded accuracy snapshot as the EU AI Act accuracy evidence. All of that is propagated and the prose that reasoned from the old state has been rewritten, not merely renumbered.

Two debts I had been carrying are also now cleared, and both turned out to be worth doing rather than asking about. Chapter 2 was arguing *for* the artifact while claiming to survey the field — sixty-five paragraphs ended with a clause explaining what the platform does about the literature just reviewed, and several named internal class names. Those are now cut or restated as impersonal design implications. (A correction to my own earlier note: the chapter is about **11,000 words, not 75,000** — I had been quoting the file's byte size. Length was never the problem.) Separately, the external-review episode was being retold in full four times; it now has one canonical account in §5A.8, with the other three sections carrying only their own consequence and a cross-reference.

**6. Unchanged and still the critical path**

Interviews have **not started**. Outcome data is **still simulated**. These are the two items that decide whether September is realistic, and they are the first two things I want your view on.

The platform itself is in good shape: production verified green on 7 August (17 of 17 live checks; API and frontend both responding). July's hardening — MFA, cookie sessions, rate limiting, secrets encrypted at rest, four-eyes approvals, measured guardrails — is all merged, and August added the ability to point embeddings at a different provider than chat, which makes the EU-sovereignty claim a configuration change rather than a rewrite.

I have kept the agenda to ten questions but genuinely only need the first three.

With thanks, and again apologies for the silence,
Elvis

---

## Call agenda — the asks

**If we only get through three: 1, 2, 3.**

1. **Evidence triage for the rest of August.** The 188-run is done, so this narrows. Of what remains — 12–15 interviews, one *live* outcome measurement, a local-vs-cloud model benchmark, semantic scoring of the two unscored fields — which are **required** for September and which are nice-to-have? And what is your realistic review turnaround on a compiled draft?

2. **Interviews and ethics.** Recruitment has not started and August is the window. Is there any OPIT-side step beyond your confirmation before I approach practitioners? If 12–15 looks unrealistic from here, is leaning harder on the breadth survey an acceptable fallback?

3. **Simulated outcomes.** §6.5 still calls one live outcome contract "the single most important next step". Is the thesis defensible in September with outcomes simulated — DP1 evidenced by design demonstration plus perception only — or do we force one small live ITS measurement into August at the cost of interview time?

4. **Is escalation-equity-only the right RQ3b claim?** Given the language/sector confound, I retracted the aggregate cross-language comparison and kept only equal-opportunity escalation recall on an eight-signal German stratum. Is that the right call, or does RQ3b need natural German data before September to stand up?

5. **Routing fields under a supplied taxonomy.** Journey and owner are scored with the corpus taxonomy supplied as a closed inventory — an upper bound, and a different configuration from the production-config numbers. I report it separately and never merge it. Is that a fair thing to report, or does an examiner read it as scoring an easier task than the one deployed?

6. **The architecture question I'd most value your view on.** DP5 confines the model to named stages with a human-approval interrupt node and deterministic code everywhere else. Should Chapter 6 add an explicit comparison against free-roaming agent designs — the HULA/agentic literature it already cites — to pre-empt "why not an agent?", or is that scope creep? The routing result (ask 5) is now my best empirical answer to that question.

7. **MemoryBank novelty boundary** — tight enough as stated in §4.3.2/§6.1? The abstract still mentions decay without the boundary sentence.

8. **Per-industry placement.** Does the distributed per-industry treatment (§5A.5 + §5A.7 + §4.3.5) suffice, or would you rather see it consolidated into one section? *(The Chapter 2 half of this ask is withdrawn — the artifact-referential prose is fixed and there is no length problem: the chapter is ~11k words.)*

9. **The external-review episode.** I have compressed it from four full retellings to a single canonical account in §5A.8; §4.9, §6.4 and Chapter 7 now carry only their own consequence plus a cross-reference. Does that land, or would you still prefer it in an appendix?

10. **Logistics** — the IP-letter process (due 31 Aug), the defense window, and whether you want the deck ahead of time.

---

## If she asks — verified facts to hand

- **Production**: 17/17 live smoke checks green, verified 7 Aug. API `https://api.clara.odradekai.com` 200 in 183 ms; frontend 200 in 228 ms.
- **Monitoring gap, stated rather than hidden**: the scheduled uptime workflow logged two consecutive failures on 6 Aug and then GitHub's scheduler dropped the cron for roughly a day. The workflow is enabled and production was fine throughout — verified by hand. It is a monitoring gap, not an outage.
- **Test suite**: 734 passing on `main`; the six failures plus four errors in `test_ai.py` were a **test-isolation defect** (the fixture let the developer's real local `.env` leak into the test environment). Both this and the CI break below are **fixed on branch `fix/ci-green-mcp-ceiling`**, where the full check suite is green — **745 passed**, lint clean, web build clean. Merging that one branch clears both.
- **CI**: red on `main` since 4 Aug for an unrelated reason — `mcp` was pinned only `>=1.2.0`, and **mcp 2.0.0 removed `mcp.server.fastmcp`** (verified against the real packages: 1.29.0 exports it, 2.0.0 does not), so a clean CI install failed to import where local pinned installs succeeded. The fix branch ceilings it at `<2`; a clean install now resolves 1.29.0 and imports.
- **Numbers**: every figure in this brief is read from `evaluation/results/summary.json` or `apps/api/app/evals/published_metrics.json`; none are typed from memory.
