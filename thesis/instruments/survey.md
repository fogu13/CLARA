# Supplementary Survey — "How feedback becomes action"

A short, anonymous survey that confirms the **current-practice** and **attitude** hypotheses (H1, H2, H4, H5, H6, H7, H8) at breadth, complementing the 12–15 in-depth interviews. Target: **~3 minutes, 8 items**, most of the weight in one matrix. It does **not** replace the interviews/task sessions (those carry the prototype-reaction and task-metric evidence) or the gold set (H3). Self-report attitudinal data confirms *perceived* gaps — consistent with the design-validity stance (Ch 3, §3.10).

> **Design rule applied:** one question = one (or more) hypotheses; no question that doesn't map to a hypothesis. Statements are kept behavioural/concrete to limit acquiescence bias; one frequency item and one count item give non-Likert corroboration; reverse-phrasing is avoided to keep it fast but the acquiescence limitation is reported.

---

## A. The survey (copy-paste ready)

**Intro / consent (shown first, required tick):**
> I'm researching how teams turn customer feedback into action, for an MSc thesis (Responsible AI, OPIT). This is anonymous, ~3 minutes, no sales. I don't collect your name or company. You can stop anytime. Results shared on request. Lawful basis: consent.
> ☐ I'm 18+, this is voluntary, and I consent to my anonymous answers being used in academic research.

**Screener**
- **S1. Your role?** ☐ Marketing ☐ Product ☐ Customer Experience / Support ☐ Founder / GM ☐ Other: ___
- **S2. Company size?** ☐ 1–9 ☐ 10–50 ☐ 51–200 ☐ 201–500 ☐ 500+
- **S3. Do you work with customer feedback (surveys, tickets, reviews, etc.)?** ☐ Yes, regularly ☐ Occasionally ☐ No *(if No → thank-you + end)*

**Q1. How much do you agree? (Strongly disagree · Disagree · Neutral · Agree · Strongly agree)** *— single matrix*

| # | Statement | Hyp. |
|---|-----------|------|
| a | We often understand what customers want but struggle to actually act on it. | **H1** |
| b | Our customer feedback is spread across so many tools that it's hard to see the priorities in one place. | **H2** |
| c | When feedback calls for action, it's often unclear who owns the response. | **H5** |
| d | Where in the customer journey a problem happens changes how much we prioritise it. | **H4** |
| e | I'd be more comfortable letting software act on feedback automatically *if a human approved the riskier actions first*. | **H6** |
| f | I wouldn't trust software to act on feedback unless I could see and audit exactly what it did and why. | **H7** |
| g | Being able to *prove* an action actually resolved the customer's problem would be valuable to me. | **H8** |

**Q2. Roughly how many separate tools/sources does your customer feedback live in?** ☐ 1 ☐ 2–3 ☐ 4–6 ☐ 7+ *(corroborates **H2**)*

**Q3. After your team acts on customer feedback, how often do you measure whether it actually resolved the issue?** ☐ Never ☐ Rarely ☐ Sometimes ☐ Usually ☐ Always *(corroborates **H8** — "rarely practised")*

**Q4. (Optional, one line) Where does customer feedback most often get *stuck* on its way to action?** ____________________ *(rich qualitative; feeds §5B inductive themes)*

**Q5. (Optional) Open to a 20-min follow-up chat? Leave an email — optional.** ____________________ *(the only field that can collect contact; on Reddit, tell people to skip it)*

That's **3 screeners + 1 matrix (7 rows) + 2 quick + 1 open + 1 opt-in**.

---

## B. Hypothesis → confirmation logic

Score Likert as **top-2-box agreement** (Agree + Strongly agree). Rule of thumb: **≥60% = supported**, **40–59% = mixed/refine**, **<40% = not supported**. Report n, %, and median for every item.

| Hyp. | Evidence in survey | "Confirmed" when |
|------|--------------------|------------------|
| H1 insight-action gap | Q1a | ≥60% agree |
| H2 fragmentation | Q1b **and** Q2 | Q1b ≥60% agree **and** ≥50% report 4+ sources |
| H4 journey-stage | Q1d | ≥60% agree |
| H5 ownership | Q1c | ≥60% agree |
| H6 approval→comfort | Q1e | ≥60% agree |
| H7 audit→trust | Q1f | ≥60% agree |
| H8 closure rare + valued | Q3 **and** Q1g | ≥50% answer Never/Rarely (rare) **and** Q1g ≥60% agree (valued) |
| H3 signal-type classifiability | *not in survey* | covered by the gold set (§5A) |

These results drop straight into **Ch 5 §5B** as a quantitative complement to the interview themes, and into the **traceability matrix (Appendix D)** status column.

---

## C. Distribution

### Tool
Use **Tally.so** (free, clean on mobile, anonymous by default) or **Google Forms** (turn **Settings → "Collect email addresses" = OFF**). Both give a public link and a CSV export. Avoid a self-hosted form — Reddit users distrust unfamiliar data-collection links; a recognised form host raises completion.

### Reddit (anonymous both ways)
- **Where:** post in subreddits whose rules allow surveys — **r/SampleSize** (the dedicated survey sub; use its title format), and value-first in **r/CustomerSuccess, r/ProductManagement, r/marketing, r/analytics, r/SaaS, r/CustomerExperience**. **Read each sub's rules first** — many require survey flair, a specific weekly thread, or ban links; some require you to be an active contributor.
- **Anonymity:** collect **zero** PII; tell people to skip Q5. Don't ask for company name.
- **Post (r/SampleSize title format):**
  > **[Academic] Marketing/Product/CX professionals — how does your team turn customer feedback into action? (~3 min, anonymous)**
  >
  > MSc (Responsible AI) research on where customer feedback stalls before it becomes action. Anonymous, ~3 min, no email needed, no sales. I'll share the aggregate findings in this thread. [link]
- **Etiquette:** reply to comments, post results back (Reddit rewards reciprocity), don't spam-crosspost the same day.

### LinkedIn (they know you; responders anonymous)
- **Feed post (from your profile):**
  > For my MSc thesis (Responsible AI), I'm researching a problem I keep seeing: teams *collect* tons of customer feedback but struggle to *act* on it — and rarely measure whether the action worked.
  >
  > If you work in marketing, product, or CX, I'd hugely value **3 anonymous minutes**: [link]. No names, no pitch — I'll share what I find. A repost would mean a lot. 🙏
- **Targeted DM (warmer, higher response):**
  > Hi [Name] — doing MSc research on how teams act on customer feedback (and where it stalls). Could I borrow **3 anonymous minutes**? [link]. It's anonymous and I'll send you the findings. No worries if not!
- **Anonymity:** the form itself collects no identity, so even though *you* are known as the sender, *responses* are anonymous. Don't enable LinkedIn-poll or any feature that ties responses to profiles.

> **Tip:** use the **same form** for both channels but **two different links** (Tally lets you duplicate, or append `?src=reddit` / `?src=linkedin`) so you can compare channels and report response source in the thesis.

---

## D. Collection & analysis

1. Responses auto-collect in Tally / the linked Google Sheet. Aim for **n ≈ 40–80** (a survey complements, not replaces, the interviews).
2. Export **CSV**. Run `evaluation/survey_analysis.py` (template) → per-hypothesis top-2-box %, medians, and a confirmed/mixed/not-supported verdict, written to `evaluation/results/survey_*.csv`.
3. Paste the verdicts into §5B and Appendix D; quote a few Q4 free-text lines (anonymised) as inductive themes.

**Ethics fit:** anonymous, voluntary, consented, no special-category data, GDPR lawful basis = consent (matches Appendix C). Q5 (optional email) is the only identifier and is used solely to invite interviews; store it separately from survey answers and delete after recruitment.

**Limitations to state in the thesis:** self-report and attitudinal (not observed behaviour); convenience sample skewed to Reddit/LinkedIn audiences; single-statement-per-construct and no reverse-coding, so acquiescence bias is possible; H6/H7 are *hypothetical* comfort, not observed trust — the interviews/task sessions remain the stronger test for those.
