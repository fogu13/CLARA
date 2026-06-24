# CLARA Thesis — 3-Month Plan (Jun 9 → Sep 2026)

**Track:** 30 ECTS Capstone (RAI-9001) · **Advisor meeting:** Jun 19 · **Target defense:** Sep 2026
**Regulatory anchors (OPIT regs §6):** complete draft → supervisor approval → Thesis Defense Form → examining committee formed ≥1 month before defense → defense (15–20 min presentation) → final PDF ≤2 weeks after defense. Supervisor meetings every ~2 weeks.

**Critical path: the 12-15 practitioner interviews. Recruitment starts now.**

> **Product roadmap note:** Product phases and remaining build work are tracked only in
> `../docs/roadmap.md`. This file is the thesis calendar, not a second product roadmap.
> Remaining thesis critical path is unchanged: recruit and run the interviews/task sessions.

---

## Month 1 — Consolidate & Recruit (Jun 9 – Jul 5)

### Week 1 (Jun 9–14)
- [ ] Consolidate into ONE master document (merge `Thesis_CLARA_2.docx` + `chapters/ch1`, `ch3`, `literature_review.md`). Archive everything else.
- [ ] Decide scope: H1 (insight-action gap) + H2 (signal fragmentation) as primary; H3–H8 secondary/descriptive.
- [ ] Draft participant consent form + check OPIT ethics requirements (ask advisor Jun 19).
- [ ] Build recruitment list: 25–30 candidate marketers (LinkedIn, communities, alumni, employer network).
- [ ] Prep advisor meeting (summary doc done).

### Week 2 (Jun 15–21)
- [ ] **Jun 19: Advisor meeting** — confirm scope, ethics, committee, defense window. Confirm supervisory agreement form is on Canvas.
- [ ] Send recruitment outreach wave 1 (goal: 15 sessions booked by Jul 4).
- [ ] Platform feature freeze: list remaining must-fix items only (bugs, demo data set, task-metrics logging). No new features.

### Week 3 (Jun 22–28)
- [ ] Pilot interviews ×2 → refine guide and task protocol.
- [x] Instrument platform for evaluation (time-to-action logging, task completion tracking feeding `evaluation/prototype_metrics.py`). **Done** — `logEvent` → `events` table → `prototype_metrics.py`.
- [ ] Write Chapter 4 (Artifact): architecture, Signal→Insight→Action→Learning cycle, rules engine, RAI controls (human-in-the-loop modes, ActionLog audit trail, compliance checker).

### Week 4 (Jun 29 – Jul 5)
- [ ] Interviews 3–6 (record, transcribe, start coding per Braun & Clarke).
- [ ] Chapter 4 complete draft → send to supervisor.

**Month 1 exit:** master doc, Ch4 drafted, 6 interviews done, 15 booked, platform frozen + instrumented.

---

## Month 2 — Evaluate (Jul 6 – Aug 2)

### Weeks 5–6 (Jul 6–19)
- [ ] Interviews + task-based prototype sessions 7–12 (incl. SUS questionnaire after each session).
- [ ] Code transcripts continuously; maintain codebook.

### Week 7 (Jul 20–26)
- [ ] Interviews 13–15 (buffer for no-shows). **Hard stop on data collection Jul 26.**
- [ ] Inter-rater reliability check (`evaluation/inter_rater_reliability.py`) on a transcript subset.

### Week 8 (Jul 27 – Aug 2)
- [ ] Finalize thematic analysis; run SUS + task metrics analysis; generate figures (`evaluation/visualization.py`).
- [ ] Map findings to H1–H8: confirmed / refined / rejected.

**Month 2 exit:** all data collected and analyzed; results tables/figures ready.

---

## Month 3 — Write & Defend (Aug 3 – Sep)

### Weeks 9–10 (Aug 3–16)
- [ ] Chapter 5 (Results) and Chapter 6 (Discussion, design principles, RAI reflections, limitations, future work).
- [ ] Revise Ch1–3 for consistency with findings; write abstract last.

### Week 11 (Aug 17–23)
- [ ] **Aug 21: complete draft to supervisor** for approval (initial submission per §6.6).
- [ ] Confirm 2 examining-committee members; submit MSc Examining Committee Appointment Form (must be ≥1 month before defense).

### Week 12 (Aug 24–30)
- [ ] Apply supervisor revisions; submit Thesis Defense Form on Canvas; agree defense date in a September defense week.

### September
- [ ] Defense deck (15–20 min) + mock defense with supervisor (early Sep).
- [ ] **Defense** (mid–late Sep).
- [ ] Final dissertation PDF, re-approved and signed, submitted ≤2 weeks after defense.

---

## Standing cadence
- Supervisor meeting every 2 weeks (regs §6.4): Jun 19, ~Jul 3, ~Jul 17, ~Jul 31, ~Aug 14, ~Aug 28, mock defense early Sep.
- Friday weekly review: interviews done vs. booked, words written, blockers.

## Top risks
| Risk | Mitigation |
|---|---|
| Interview recruitment shortfall (the #1 risk) | Start outreach Jun 15; overbook to 18–20; ask advisor for OPIT network access; incentives if allowed |
| Scope creep on platform | Feature freeze Week 2; build only what evaluation needs |
| RQ2 overclaim ("significantly reduce time-to-action") | Reframe with advisor as design validity / perceived utility, not statistical effect |
| Analyst sources (Gartner/Forrester/Qualtrics 2025–26) hard to cite | Anchor each claim to academic sources; keep vendor reports as supporting evidence with access dates |
| September defense logistics | Committee form by Aug 21; confirm defense-week dates on Jun 19 |
