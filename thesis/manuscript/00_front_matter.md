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

Organisations collect more customer feedback than ever, yet closing the loop on it remains the weakest practice in feedback management: feedback is gathered but rarely turned into governed, executed and *measured* action, and what is learned is rarely retained (Forrester, 2025b). This thesis applies Design Science Research to design, build and evaluate CLARA, a production platform that operationalises the **Signal → Insight → Action → Learning** cycle with Responsible-AI governance built into the loop: every action is a draft until a person approves it, outcomes are measured against a contract by an estimator that grades its own evidence and refuses when the data cannot carry a result, and reviewer conclusions enter a memory whose confidence decays. Evaluated on **188 real customer signals** from three sectors and in an exploratory practitioner study, it shows that triage accuracy depends on method: a lexicon floor fails on real operational feedback, a learned model reaches usable accuracy, and a contextual language-model path leads on sentiment across four runs while tying the learned model on severity. The artifact's own enrichment stage matches that path on sentiment and labels severity one level below the reference labels, a calibration difference that a second rating of the labels, whose independent human provenance is unverified, partly shares, reported as an uneven capability rather than adjusted away. Method choice can also change whose problems are escalated: on a stratum of eight German-source signals whose reference label warrants escalation, the learned model's recall is 62.5% against 95.1% for English-source signals, while the contextual path's is 87.5% against 87.8%, descriptive figures that do not rank the predictors and that argue for per-stratum monitoring of escalation. The contribution is five design principles, each stated with its cost: contracted, graded closure that refuses when underpowered; perishable organisational memory; authority graduated by consequence class; a bounded model inside a deterministic loop; and uneven capabilities measured and published, not shipped. Closing the feedback loop is a workflow and governance problem, and what the market lacks is a measured outcome contract and a perishable learning memory, not a better dashboard.

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

The quantitative evaluation is reproducible: the harness (`evaluation/`) runs from the public datasets and writes every metric in the results tables from data (`evaluation/results/`); the few prose figures assembled from those tables are marked where they appear. The datasets used are public, paraphrased, and de-identified. The artifact source, the evaluation code, and the diagram sources are maintained in the project repository (`github.com/fogu13/CLARA`), which is private; read access for examination is granted on request.

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
