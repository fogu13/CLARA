# Advisor brief — check-in with Prof. Zorina, 17 Jul 2026

Prepared 16 Jul. Two parts: a ready-to-send email (send ahead of the call or use as the update itself), and a call agenda with the numbered asks. Absorbs the unsent 12-Jul manuscript draft (`email-draft-2026-07-manuscript.md`) — don't send both.

**Before attaching anything:** `build/thesis.docx` and `defense/defense_deck.pptx` are stale (pre-streamline). Rebuild first — see Author TODOs in `thesis/README.md`.

---

## Email draft

**Subject:** Two-week check-in: full manuscript draft, outcome measurement shipped, and CLARA live in production

Dear Prof. Zorina,

Hope you are doing well. As promised on 3 July, here is the two-week check-in ahead of our call. A lot has landed — the short version: **the full thesis manuscript now exists end to end, the outcome-measurement design is no longer a plan but shipped code (and a methodology section), and CLARA is live in production on an EU-sovereign stack.** Below is what happened to each item from my last email, what's new, and the points where I need your guidance.

**1. The manuscript (the headline)**

All chapters are drafted — introduction, literature review, methodology, artifact, evaluation, discussion, conclusion, plus appendices: the study instruments, an EU-AI-Act/GDPR mapping, a completed DPIA, the data-model DDL, and a traceability matrix that states per claim whether it is *measured, demonstrated, perception-tested, or pending*. Roughly 35,000 words and 12 figures. Three things I'd flag about how it's written:

- **I narrowed one of my own novelty claims after finding prior art myself.** MemoryBank (Zhong et al., AAAI 2024) already applies Ebbinghaus-style decay to LLM conversational memory. My decaying-learning contribution is therefore restated precisely: decayed *evidence confidence over organisational action-outcome learnings, retrieved under governance into future action decisions* — not decay-based memory per se. The thesis cites the prior art itself; I'd rather we surface this than an examiner.
- **The evaluation chapter separates the two evidence streams honestly**: the 188-signal external gold-set results (rule floor 0.37 sentiment vs learned model 0.78 — the "triage must be learned" finding) and the platform's committed in-repo evaluation (the numbers from my 3-July email) as *convergent evidence*, never merged into one table, because the gold standards differ. The caveats we discussed are in the text: the exemplar A/B is not significant at n=60, and outcome data is still simulated.
- **The qualitative section (§5B) is a complete protocol with results scaffolding** — instruments, survey, codebook, analysis scripts — with every result cell explicitly awaiting interview data. Nothing is simulated.

**2. Outcome measurement: from "next week I'll wire it in" to shipped**

This was the biggest item on my 3-July list, and it landed deeper than planned. Because a randomised experiment is infeasible in production (the fix goes to everyone at once), CLARA now scores outcomes with an **interrupted-time-series design (segmented regression at the action date)** — implemented dependency-free in the platform, with bias controls I validated by simulation (complete UTC days only, execution-day exclusion, no fabricated history) and honesty rules: below minimum data, it refuses to fit and reports a labelled plain delta with *no* confidence interval. Outcome contracts are now proposed automatically at approval time (trailing-rate baseline, 30-day window, T+7 early read — editable and declinable), and re-measurement runs on a schedule. The same design is written up as methodology §3.5.5, so the thesis chapter and the shipped estimator are one and the same design — with its limitations stated (approximate OLS intervals pending HAC errors; synthetic difference-in-differences as the panel-data upgrade). *The remaining gap is unchanged and honest: the data flowing through it is still simulated until real usage accumulates.*

**3. CLARA is live in production**

The "fix my server" item became a full deployment: the API runs in Docker on an EU VPS behind TLS, the frontend at https://clara.odradekai.com, database in Supabase Frankfurt, nightly encrypted backups. Two thesis-relevant consequences: the **EU-sovereignty / data-residency claim is now a deployed fact rather than a design intention**, and the practitioner interviews can use a real URL instead of a localhost demo. Alongside it, tenant isolation was hardened (enforced row-level security, JWT-bound identity) following the adversarial review I mentioned — the review-then-harden account is §4.9 of the manuscript.

**4. Governance features with German-market relevance**

Three additions since 3 July, all in production: a **works-council mode** (aggregate-only views with role-redacted reasoning — designed with §87 BetrVG consultation in mind), an **AI-literacy onboarding module** (the Art 4 deployer duty), and an **Article 50(4) editorial-review flow** for AI-drafted customer-facing text. These strengthen the "Responsible AI as integral design" chapter with concrete, shipped examples.

**5. Honest status of the rest of the 3-July list**

- *Grow the labelled set toward 100+* — *not done yet* (still 60, adversarially verified). I prioritised the manuscript and the outcome engine; see ask #4.
- *Local vs cloud model benchmark* — *not run yet.* The harness is model-agnostic and ready; I'll run it once we agree where it sits in the thesis (see ask #4).
- *LLM path against the 188-signal harness* — wired and reproducible, still pending an execution run; §5A reports its cells as pending.
- *Interviews* — not started (holiday); instruments and a breadth survey with its analysis script are ready to go. This is now my critical path — see ask #3.
- *Per-industry evaluation chapter* (I asked your view on 3 July) — meanwhile implemented inside the existing structure: sector/language breakdowns (§5A.5), the cross-industry real-data run (§5A.7), and per-industry scoring profiles as the fifth design decision (§4.3.5). See ask #5.

**Where I need your guidance (numbered so it's easy to respond):**

1. **Manuscript review order and turnaround.** I'll send the compiled draft after this call. If your time is limited, the highest-leverage chapters for feedback are Ch 3 (especially the new §3.5.5) and Ch 6, plus the abstract. What review turnaround is realistic on your side so a September submission holds?
2. **The narrowed novelty formulation** (§4.3.2 / §6.1 DP2): is the boundary against MemoryBank drawn tightly enough?
3. **Interviews — ethics and start.** Consent, recruitment materials, SUS/TAM and the survey are in Appendix A. Is there any OPIT-side ethics step beyond your confirmation before I start recruiting (Reddit/LinkedIn + referrals)? I'm back on the 26th and want interviews running through August.
4. **Evidence priorities for the remaining ~6 weeks.** Candidates: (a) the 12–15 interviews (§5B — I assume must-have), (b) the LLM run on the 188-signal harness, (c) growing the golden set to ~100 so the significance tests are powered, (d) the local-vs-cloud benchmark (accuracy / reproducibility / cost / residency), (e) one small *live* outcome measurement so the ITS engine reports a real, non-simulated number. I can't do all five well — which are required for the thesis, and which are nice-to-have?
5. **Per-industry evaluation**: does the current placement (§5A.5 + §5A.7 + §4.3.5) suffice, or would you promote it to its own chapter/section?
6. **The thesis–IP letter (needed by 31 Aug).** The artifact underpins a commercial venture (declared in the front matter's conflict-of-interest statement, with the mitigations in §3.12). What is the OPIT process for the IP confirmation letter, and is the current declaration sufficient in your view?

A first draft of the defense deck (13 slides, speaker notes) is ready too — no need to look before the call; I'll bring it when we discuss the defense window.

Please let me know your feedback — and thank you!

Best,
Elvis

---

## Call agenda (if it's a live call, ~10 min update + discussion)

1. **Since 3 July in one line each:** full manuscript drafted (35k words, appendices A–E, traceability matrix) · outcome measurement shipped as code + §3.5.5 (ITS, honesty rules, approval-time contracts) · CLARA live in production, EU stack (clara.odradekai.com — offer a 2-minute live walkthrough) · tenant isolation hardened after adversarial review · works-council mode / AI-literacy / Art 50(4) flows shipped · novelty claim self-narrowed against MemoryBank · competitive chapter now verification-based (Enterpret: 114 claims extracted, 25 survived adversarial verification, outcome measurement unverifiable).
2. **Unchanged honest gaps:** outcome data simulated; exemplar A/B underpowered at n=60; LLM-on-188 run pending; interviews not started.
3. **Decisions needed:** the six numbered asks above — priority on #3 (ethics green light) and #4 (evidence triage), since they set the August plan.
4. **Logistics:** draft delivery date, her review turnaround, defense window, IP-letter process.

## Prep checklist (before sending / attaching)

- [ ] Rebuild `build/thesis.docx` (chapters changed 16 Jul; §3.5.5 has display math — check it renders) and re-render `03_architecture_clara` + `08_dsr_method` diagrams (`python3 diagrams/render.py`)
- [ ] Rebuild `defense/defense_deck.pptx` via `make_deck.js` (built deck still carries a removed subtitle)
- [ ] Attach: rebuilt docx (+ deck only if asked)
- [ ] Optional: have https://clara.odradekai.com open and logged in for a live demo
