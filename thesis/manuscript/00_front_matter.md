# Closing the Loop, Building the Memory

### A Design-Science Study of a Governed Platform for Turning Customer Feedback into Measured Action and Reusable Organisational Learning

---

**Author:** Elvis Shehi
**Programme:** MSc Responsible Artificial Intelligence
**Institution:** Open Institute of Technology (OPIT)
**Capstone:** RAI-9001 (30 ECTS)
**Supervisor:** Prof. Zorina Alliata
**Submission:** Autumn 2026 *(target)*

> **Artifact note.** The artifact of this thesis is **CLARA** (*Capture, Listen, Analyze, Respond, Adapt*): a Next.js front end on a FastAPI/LangGraph backend, in production since July 2026 (Chapter 4). The design was first instantiated on a different stack — a React/Vite single-page application on Supabase Edge Functions — which served as the first design-cycle iteration and is superseded by the build documented here (§4.7). Build-agnostic discussion refers to "the platform" or "the artifact".

---

## Abstract

Organisations collect more customer feedback than ever, yet fewer than a third systematically close the loop on it: feedback is gathered but rarely translated into governed, executed, and *measured* action, and what is learned is rarely retained (Bone et al., 2017). This thesis applies Design Science Research to design, build, and evaluate a platform that operationalises the full **Signal → Insight → Action → Learning** cycle, with Responsible-AI governance — human-in-the-loop approval, audit trails, and EU AI Act / GDPR controls — embedded throughout rather than added on. The contribution is articulated through five non-trivial design decisions (rule conflict resolution, confidence decay in learnings, cross-signal severity scoring, relevant past-learnings retrieval, and per-industry scoring profiles) and is evaluated along two complementary axes: a quantitative gold-set evaluation of the AI enrichment and routing pipeline against human-curated labels on **188 real, multilingual customer signals** across three sectors, and a qualitative practitioner study (semi-structured interviews and task-based prototype sessions with SUS and TAM instruments). The quantitative evaluation shows that triage accuracy is strongly method-dependent — a rule-based lexicon floor is inadequate on paraphrased operational feedback (sentiment accuracy 0.37), a lightweight learned model reaches usable accuracy (0.78), and the artifact's contextual path is strongest (0.86) — establishing that the loop's precondition is satisfiable, by more than one method. The choice among them proves to be an equity decision as much as an accuracy one: the lexicon floor escalates none of the genuinely critical German signals in the corpus, while the contextual path escalates German and English at near-identical rates. The thesis's central claim is that closing the feedback loop is a workflow-and-governance problem whose missing primitives are a measured outcome contract and a perishable learning memory, not a better dashboard. **‹Headline qualitative findings are inserted once the practitioner study is complete.›**

**Keywords:** customer feedback; voice of the customer; feedback-to-action gap; design science research; human-in-the-loop; governed automation; EU AI Act; responsible AI; organisational learning; large language models.

---

## Acknowledgements

*‹To be completed.›* The author thanks the thesis supervisor, Prof. Zorina Alliata, for guidance on scope and method; the practitioners who gave their time to the evaluation interviews; and OPIT faculty for feedback at the proposal and draft stages.

---

## Declaration of Authorship

I declare that this thesis is my own work and that all sources used have been acknowledged. Vendor and analyst publications are cited as supporting market evidence with access dates; load-bearing empirical claims are anchored to peer-reviewed academic sources. *(Sign before submission.)*

## Use of Generative AI

Generative-AI tools were used as an assistant during this project — for drafting and editing prose, for code scaffolding of the artifact and the evaluation harness, and for literature and market discovery (with every load-bearing claim independently verified against primary sources). All research design, analysis, interpretation, and conclusions are the author's own, and the author takes full responsibility for the content. This disclosure follows OPIT's expectations on AI use in assessed work.

## Conflict of Interest

The artifact studied here is also the basis of a commercial venture in which the author has an interest. This is a potential conflict relevant to the evaluation of the artifact and is mitigated by externally-labelled evaluation data, standardised instruments, and a reproducible analysis pipeline (see Chapter 3, §3.10, for the full positionality statement).

## Reproducibility and Data Availability

The quantitative evaluation is fully reproducible: the harness (`evaluation/`) runs from the public datasets and writes every reported number from data (`evaluation/results/`). The datasets used are public, paraphrased, and de-identified. The artifact source, the evaluation code, and the diagram sources are maintained in the project repository. *‹Add repository URL / DOI before submission.›*

---

## List of Abbreviations

| Abbr. | Term |
|---|---|
| ABSA | Aspect-Based Sentiment Analysis |
| CES | Customer Effort Score |
| CSAT | Customer Satisfaction (score) |
| CX | Customer Experience |
| DSR / DSRM | Design Science Research / DSR Methodology |
| GDPR | General Data Protection Regulation |
| HITL | Human-in-the-Loop |
| LLM | Large Language Model |
| NPS | Net Promoter Score |
| PEOU / PU | Perceived Ease of Use / Perceived Usefulness (TAM) |
| RAI | Responsible AI |
| RLS | Row-Level Security |
| SUS | System Usability Scale |
| TAM | Technology Acceptance Model |
| VoC | Voice of the Customer |

---

## Table of Contents · List of Figures · List of Tables

*(Generated on compilation to `.docx`.)*

1. Introduction
2. Literature Review
3. Methodology
4. The Artifact
5. Evaluation and Results
6. Discussion
7. Conclusion
- References
- Appendices A–E
