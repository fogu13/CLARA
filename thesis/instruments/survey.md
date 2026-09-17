# Supplementary Survey: "How feedback becomes action"

A short, anonymous survey that tests the current-practice and attitude hypotheses (H1, H2, H4, H5, H6, H7, H8) at breadth, complementing the 12–15 planned in-depth interviews. Target: about 3 minutes, 7 items, most of the weight in one matrix. It does not replace the interviews and task sessions (those carry the prototype-reaction and task-metric evidence) or the gold-set evaluation (H3). Self-report attitudinal data can show *perceived* gaps only, consistent with the design-validity stance of Chapter 3 (§3.10).

Status: not administered at the time of writing (§5B.1). Distribution notes are kept outside the thesis in `thesis/instruments/survey_distribution.md`.

> Design rule applied: one question = one (or more) hypotheses; no question that does not map to a hypothesis. Statements are kept behavioural and concrete to limit acquiescence bias; one frequency item and one count item give non-Likert corroboration; reverse-phrasing is avoided to keep it fast, and the acquiescence limitation is reported.

---

## A. The survey (copy-paste ready)

**Intro / consent (shown first, required tick):**
> I'm researching how teams turn customer feedback into action, for an MSc thesis (Responsible AI, OPIT). This is anonymous, about 3 minutes, no sales. I don't collect your name, email or company. You can stop anytime. Results shared on request. Lawful basis: consent.
> ☐ I'm 18+, this is voluntary, and I consent to my anonymous answers being used in academic research.

**Screener**
- **S1. Your role?** ☐ Marketing ☐ Product ☐ Customer Experience / Support ☐ Founder / GM ☐ Other: ___
- **S2. Company size?** ☐ 1–9 ☐ 10–50 ☐ 51–200 ☐ 201–500 ☐ 500+
- **S3. Do you work with customer feedback (surveys, tickets, reviews, etc.)?** ☐ Yes, regularly ☐ Occasionally ☐ No *(if No → thank-you + end)*

**Q1. How much do you agree? (Strongly disagree · Disagree · Neutral · Agree · Strongly agree)** *(single matrix)*

| # | Statement | Hyp. |
|---|-----------|------|
| a | We often understand what customers want but struggle to actually act on it. | H1 |
| b | Our customer feedback is spread across so many tools that it's hard to see the priorities in one place. | H2 |
| c | When feedback calls for action, it's often unclear who owns the response. | H5 |
| d | Where in the customer journey a problem happens changes how much we prioritise it. | H4 |
| e | I'd be more comfortable letting software act on feedback automatically if a person approved each action before it was sent. | H6 |
| f | I wouldn't trust software to act on feedback unless I could see and audit exactly what it did and why. | H7 |
| g | Being able to prove an action actually resolved the customer's problem would be valuable to me. | H8 |

**Q2. Roughly how many separate tools/sources does your customer feedback live in?** ☐ 1 ☐ 2–3 ☐ 4–6 ☐ 7+ *(corroborates H2)*

**Q3. After your team acts on customer feedback, how often do you measure whether it actually resolved the issue?** ☐ Never ☐ Rarely ☐ Sometimes ☐ Usually ☐ Always *(corroborates H8, "rarely practised")*

**Q4. (Optional, one line) Where does customer feedback most often get stuck on its way to action?** ____________________ *(qualitative; feeds the inductive themes of §5B)*

**Closing note (no field).** The survey itself collects no contact details. Anyone willing to have a 25–30-minute follow-up conversation is pointed to a separate, unlinked form (`thesis/instruments/followup_optin.md`) whose responses cannot be joined to survey answers.

That is 3 screeners + 1 matrix (7 rows) + 2 quick items + 1 open item, and no contact field.

---

## B. Hypothesis → support logic

Score Likert as top-2-box agreement (Agree + Strongly agree). Support levels are descriptive, pre-registered in `evaluation/survey_analysis.py` before any data: ≥60% = supported in this sample, 40–59% = mixed/refine, <40% = not supported, and no verdict below n = 40 on a hypothesis's usable denominator (descriptive counts and intervals only from n = 10 to 39; the number of responses alone below n = 10; §5B.3). The script's CONFIRMED label is reported as "supported in this sample" (§5B.3). For H2 and H8 the corroborating item must hold as well (below); a Likert bar that is met without its corroboration is reported as mixed/refine. Report n, %, a 95% Wilson interval and the median for every item; a verdict whose interval straddles its threshold is marked fragile.

| Hyp. | Evidence in survey | "Supported in this sample" when |
|------|--------------------|------------------|
| H1 insight-action gap | Q1a | ≥60% agree |
| H2 fragmentation | Q1b and Q2 | Q1b ≥60% agree and ≥50% report 4+ sources |
| H4 journey-stage | Q1d | ≥60% agree |
| H5 ownership | Q1c | ≥60% agree |
| H6 approval→comfort | Q1e | ≥60% agree |
| H7 audit→trust | Q1f | ≥60% agree |
| H8 closure rare + valued | Q3 and Q1g | ≥50% answer Never/Rarely (rare) and Q1g ≥60% agree (valued) |
| H3 signal-type classifiability | *not in survey* | covered by the gold-set evaluation (§5A) |

Where a verdict is issued, it enters Chapter 5 §5B as a separate line of evidence beside the interview themes, and the traceability matrix (Appendix D) status column.

---

## C. Distribution

Moved to `thesis/instruments/survey_distribution.md` (working material, not bound into the thesis).

---

## D. Collection and analysis

1. Responses auto-collect in the form host's export. Aim for n ≈ 40–80 (a survey complements, not replaces, the interviews).
2. Export CSV. Run `evaluation/survey_analysis.py` → per-hypothesis top-2-box % with Wilson intervals and a supported / mixed-refine / not-supported / descriptive-only / insufficient-n verdict, written to `evaluation/results/survey_verdicts.csv`.
3. Enter the verdicts, at the tier the n permits, into §5B and Appendix D; quote a few Q4 free-text lines (anonymised) as inductive themes.

**Ethics fit:** anonymous, voluntary, consented, no special-category data, GDPR lawful basis = consent (matches Appendix C). The survey collects no identifier. Follow-up contact is collected on the separate form of `thesis/instruments/followup_optin.md`, stored apart from survey answers, used solely to invite interviews, and deleted after recruitment.

**Limitations to state in the thesis:** self-report and attitudinal (not observed behaviour); convenience sample skewed to the audiences of the channels used; single-statement-per-construct and no reverse-coding, so acquiescence bias is possible; H6 and H7 measure *hypothetical* comfort, not observed trust; the interviews and task sessions remain the stronger test for those.
