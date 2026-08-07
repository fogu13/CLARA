# Meeting card — Prof. Zorina Alliata, 8 Aug 2026 (30 min)

Budget: ~15 min slides, ~15 min the asks. One line per slide; say it, don't read it.

## The spine — 12 slides

| # | Slide | Time | The one line |
|---|---|---|---|
| 1 | Title | 15s | "Since we last spoke the evaluation completed — that's today's story." |
| 3 | Research questions | 1m | RQ3 split into RQ3a accuracy / RQ3b equity — the run forced it; needs your sign-off. |
| 10 | Since your last look 1/2 | 1.5m | July hardening + August sovereignty work — all merged, hashes in notes. |
| 11 | Since your last look 2/2 | 2m | **The run was silently broken, not un-run** — 403 on the User-Agent, exit 0 on an empty file. Fixed, 188/188, three consequences. |
| 12 | Two streams | 30s | Two gold standards, never merged — sets up why 0.86 and 0.97 coexist. |
| 13 | Result 1: accuracy | 2m | 0.37 → 0.78 → 0.86; the *shape* is the finding — big gain on sentiment, slim on severity. |
| 14 | Result 2: equity | 2m | **0 of 8 critical German signals escalated by the floor; LLM 87.5 vs 87.8 parity.** Say it slowly, then the bounds unprompted: n=8, language×sector confound, aggregate claim retracted. |
| 15 | Result 3: routing | 1.5m | 0.59 / 0.40 clears the floors, nowhere near autonomous — **the numbers that justify the gate**. |
| 16 | Result 4: memory | 1m | 21% → 71% remedy adoption — mechanism measured, benefit pending; outcomes still simulated. |
| 17 | Proven / pending | 1.5m | The honesty map; three rows changed status in August. Leads into the asks. |
| 19 | Limitations & next | 1.5m | Future-work #2 landed; #1 (live outcome) is ask 3. Stop here, talk. |

Don't close on slide 20 — end on the asks.

## Reserve slides (only if summoned)

- **5 System architecture** ← anything architectural (she's an architecture prof; she hasn't seen it)
- **8 Design decisions** ← MemoryBank / novelty probing
- **9 RAI controls** ← governance beyond the equity finding
- **18 Positioning** ← commercial questions
- Pair **5 + 15** if "why not an agent?" comes up.

## The asks — top 3 verbatim

1. **Evidence triage for the rest of August.** "The 188-run is done. Of what remains — 12–15 interviews, one live outcome measurement, a local-vs-cloud benchmark, semantic scoring of the two unscored fields — which are *required* for September, which are nice-to-have? And your realistic review turnaround on a compiled draft?"
2. **Interviews / ethics.** "Any OPIT-side step beyond your confirmation before I start recruiting? August is the window — if 12–15 looks unrealistic, is leaning on the breadth survey an acceptable fallback?"
3. **Simulated outcomes.** "Is September defensible with outcomes simulated — DP1 by demonstration + perception only — or do we force one small live ITS measurement into August at the cost of interview time?"

Remaining, one line each: **4** RQ3b as escalation-equity-only — right call given the confound? · **5** supplied-inventory routing — fair to report? · **6** DP5-vs-agents comparison in Ch 6 — worth adding or scope creep? · **7** MemoryBank boundary tight enough? Abstract still lacks the boundary sentence. · **8** per-industry treatment: distributed or consolidated? · **9** episode now single-sourced in §5A.8 — does it land, or appendix? · **10** IP letter (due 31 Aug), defense window, deck ahead of time?

## Verified facts (all from repo files, none from memory)

- **Corpus/run**: 188 signals (67 TR / 39 Henkel / 82 Lieferando; EN 102 / DE 84 / other 2); run 4 Aug; 6 lost to endpoint errors on routing (n=182 there).
- **Accuracy**: sentiment 0.37 / 0.78 / **0.86** (macro-F1 0.37 / 0.52 / **0.67**); risk macro-F1 0.26 / 0.65 / **0.68**.
- **Equity**: gold-escalate recall DE 0.0 → **87.5%** (7 of 8), EN 19.5 → **87.8%**; base rates DE 17.8% / EN 69.5%.
- **Routing**: journey **0.59** vs 0.20 floor (27 classes), owner **0.40** vs 0.15 (51); supported-classes macro-F1 0.28 / 0.18; upper bound (inventory supplied).
- **In-repo golden set** (18 Jul, n=100, 72/28): sentiment **97%** (CI 93–100), urgency **90%** (CI 84–95), tag-F1 **82.7%**; urgency exemplar p=**0.039** (3rd consecutive run; was 0.219 at n=80, withheld). Quote **0.86**, not 0.97.
- **Learning loop**: remedy presence 21% → **71%** (adoption 66.7%).
- **Ops**: production 17/17 live checks green (7–8 Aug, twice); uptime cron recovered; CI green on main (mcp<2 ceiling, PR #134); full check 745 passed.

## Likely questions — one-line answers

- **"Routing is only 40% accurate?"** — Over 51 classes vs a 15% floor, under a supplied inventory (upper bound) — and that's the argument *for* the approval gate, not against the pipeline.
- **"Why not an agent?"** — DP5: bounded model, deterministic loop; the routing numbers are the empirical case — a free-roaming agent routing at 0.40 fails quietly. (Ask 6 = should Ch 6 say this explicitly?)
- **"Is 0.86 or 0.97 the real number?"** — Different gold standards; curated sets select for label clarity; the conservative 0.86 is the one the thesis quotes.
- **"MemoryBank already did decay."** — Cited ourselves; boundary: decayed *evidence confidence over action-outcome learnings retrieved under governance*, not chat-memory decay.
- **"Outcomes are simulated — so what's proven?"** — Mechanism (adoption 21→71%) measured; benefit awaits one live contract — ask 3 is exactly this trade-off.
- **"You authored the German data."** — Disclosed everywhere it appears; adversarially verified 19/20; natural German is named the highest-value corpus work (§6.5).
- **"You're the founder."** — Declared COI + four safeguards: external labels, standard instruments, double-coding, reproducible harness; plus the traceability matrix.
- **"Can you finish by September?"** — Yes if interviews start now — which is asks 1–2; everything else is bounded.

## Morning checklist

- [x] `python3 scripts/live_smoke.py` → 17/17
- [x] Uptime workflow dispatched → green, cron recovered
- [ ] Laptop: deck open in presenter view (notes carry hashes + trajectories); this card printed or on phone
- [ ] If tech fails: the verified-facts box above is the whole talk
