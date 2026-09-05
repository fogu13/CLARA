# Closing the Loop, Building the Memory

### A Design-Science Study of a Governed Platform for Turning Customer Feedback into Measured Action and Reusable Organisational Learning

---

**Author:** Elvis Shehi
**Programme:** MSc Responsible Artificial Intelligence
**Institution:** Open Institute of Technology (OPIT)
**Capstone:** RAI-9001 (30 ECTS)
**Supervisor:** Prof. Zorina Alliata
**Submission:** Autumn 2026 *(target)*

> **Artifact note.** The artifact of this thesis is **CLARA** (*Capture, Listen, Analyze, Respond, Adapt*): a Next.js front end on a FastAPI/LangGraph backend, in production since July 2026 (Chapter 4). The design was first instantiated on a different stack, a React/Vite single-page application on Supabase Edge Functions, which served as the first design-cycle iteration and is superseded by the build documented here (§4.7). Build-agnostic discussion refers to "the platform" or "the artifact".

---

## Abstract

Organisations collect more customer feedback than ever, yet closing the loop on it remains the weakest practice in feedback management: feedback is gathered, but it is rarely turned into governed, executed and *measured* action, and what is learned along the way is rarely retained (Forrester, 2025b). This thesis applies Design Science Research to design, build and evaluate CLARA, a platform that operationalises the full **Signal → Insight → Action → Learning** cycle with Responsible-AI governance built into the loop rather than added on top: every action is a draft until a person approves it, approvals are recorded against a hashed evidence pack, outcomes are measured against a contract by an estimator that grades its own evidence and refuses when the data cannot carry a result, and what a reviewer concludes enters a memory whose confidence decays. The artifact runs in production. It is evaluated along two axes: a quantitative gold-set evaluation of the AI triage pipeline on **188 real customer signals** from three sectors, drawn from English- and German-language sources and scored as English paraphrases, and an exploratory practitioner study using interviews, task-based sessions and the SUS and TAM instruments. Two results carry the quantitative chapter. Triage accuracy depends strongly on method: a rule-based lexicon floor fails on real operational feedback, a lightweight learned model reaches usable accuracy, and a contextual language-model path is strongest, with the gain large on sentiment and slim on severity. And the choice of method is an equity decision as well as an accuracy one: on the corpus's German-source stratum the learned model escalates genuinely critical signals at a significantly lower rate than on the English-source stratum, while the contextual path shows no detectable difference; the stratum is small and the finding is indicative. The contribution is five design principles, each stated with its cost: closure as a contracted, graded measurement that refuses when underpowered; organisational memory as perishable; authority graduated by consequence class; a bounded model inside a deterministic loop; and the rule that a capability whose errors fall unevenly on the people served is measured, published and not shipped. The central claim is that closing the feedback loop is a workflow and governance problem, and that the two primitives the market lacks are a measured outcome contract and a perishable learning memory, not a better dashboard.

**Keywords:** customer feedback; voice of the customer; feedback-to-action gap; design science research; human-in-the-loop; governed automation; EU AI Act; responsible AI; organisational learning; large language models.

---

## Acknowledgements

*‹To be completed.›* I thank my supervisor, Prof. Zorina Alliata, for guidance on scope and method, the practitioners who gave their time to the evaluation interviews, and the OPIT faculty for feedback at the proposal and draft stages.

## Declaration of Authorship

I declare that this thesis is my own work and that all sources used have been acknowledged. Vendor and analyst publications are cited as supporting market evidence with access dates; load-bearing empirical claims are anchored to peer-reviewed academic sources. *(Sign before submission.)*

## Use of Generative AI

I used generative-AI tools as an assistant during this project: for drafting and editing prose, for code scaffolding of the artifact and the evaluation harness, and for literature and market discovery, with every load-bearing claim verified independently against primary sources. All research design, analysis, interpretation and conclusions are my own, and I take full responsibility for the content. This disclosure follows OPIT's expectations on AI use in assessed work.

## Conflict of Interest

The artifact studied here is also the basis of a commercial venture in which I have an interest. This is a potential conflict relevant to the evaluation of the artifact. It is mitigated by externally-labelled evaluation data, standardised instruments, and a reproducible analysis pipeline (see Chapter 3, §3.10, for the full positionality statement).

## Reproducibility and Data Availability

The quantitative evaluation is reproducible: the harness (`evaluation/`) runs from the public datasets and writes every metric in the results tables from data (`evaluation/results/`); the few prose figures assembled from those tables are marked where they appear. The datasets used are public, paraphrased, and de-identified. The artifact source, the evaluation code, and the diagram sources are maintained in the project repository. *‹Add repository URL / DOI before submission.›*

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

*(The table of contents is generated on compilation to `.docx`; the lists of figures and tables are inserted in Word from the captions before submission.)*

1. Introduction
2. Literature Review
3. Methodology
4. The Artifact
5. Evaluation and Results
6. Discussion
7. Conclusion
- References
- Appendices A–E
