# Closing the Loop, Building the Memory

### A Design-Science Study of a Governed Platform for Turning Customer Feedback into Measured Action and Reusable Organisational Learning

---

**Author:** Elvis Shehi
**Programme:** MSc Responsible Artificial Intelligence
**Institution:** Open Institute of Technology (OPIT)
**Capstone:** RAI-9001 (30 ECTS)
**Supervisor:** Prof. Zorina Alliata
**Submission:** Autumn 2026 (target)

> **Artifact note.** The artifact of this thesis is CLARA (Capture, Listen, Analyze, Respond, Adapt): a Next.js front end on a FastAPI/LangGraph backend, in production since July 2026 (§4.1 dates the deployed build; §4.7 the earlier first-cycle instantiation). Build-agnostic discussion refers to "the platform" or "the artifact".

---

## Abstract

Customer-feedback systems can record that an action was taken without establishing whether the underlying problem improved. This design-science study develops CLARA, a workflow linking customer signals to human-approved actions, outcome contracts and reusable learning records. The design combines versioned measurement terms, explicit evidence grades and confidence-weighted retrieval of past conclusions.

Evaluation examines technical controls and feedback enrichment on 188 English paraphrases of public reviews from three sectors. Against star-rating proxies on 153 items, the production configurations achieved sentiment agreement of 0.83–0.84, compared with 0.78 for a TF-IDF classifier, a difference not distinguishable on this corpus after correction for multiple comparisons; a generic prompt on the same model family reached 0.86, a lead that is stable across repeated runs and not significant after the retrospective correction. Against assistant-authored risk labels on 106 items, production agreement was 0.50–0.59; the disagreement may reflect differences between the risk and urgency constructs. Source-stratum escalation comparisons are exploratory because language and sector are confounded and one positive stratum contains only eight cases.

The artifact demonstrates an implementable approach to governed workflow execution and explicit outcome provenance. Practitioner usefulness, benefit from memory decay and improvement in real customer outcomes have not been established. The contribution is the integrated design and a set of provisional design principles, together with evidence about the limits of the enrichment and measurement components.

**Keywords:** customer feedback; voice of the customer; feedback-to-action gap; design science research; human-in-the-loop; governed automation; EU AI Act; responsible AI; organisational learning; large language models.

---

## Acknowledgements

I thank my supervisor, Prof. Zorina Alliata, for guidance on scope and method, and the OPIT faculty for feedback at the proposal and draft stages.

## Declaration of Authorship

This thesis is my own work and all sources used are acknowledged. Vendor and analyst publications are cited with access dates and their commercial interest stated; the problem motivation rests on peer-reviewed process research and analyst surveys together (§2.1).

## Use of Generative AI

Generative-AI tools took part at points that bear on the evidence. The evaluation corpus came from an assistant-led research session on 21 June 2026: the collection of the public review pages, the English paraphrases, the de-identification and the seed labels were used as delivered (§3.7; Appendix G.1). Neither the seed labels nor the in-repo golden set is human-labelled; the golden set was authored with an AI coding assistant; AI reviewer agents audited its German and boundary strata, and its English items have no recorded audit (Appendix G.2). AI coding assistants contributed to the artifact's code and the evaluation harness, and AI tools assisted the drafting, editing and review of this manuscript. Verification is claimed only for work that was completed: the literature claims the September 2026 reviews identified as load-bearing were re-checked against their sources and corrected where they over-read them, the Chapter 5 figures derived from committed prediction files are harness-regenerated (Reproducibility, below), and the artifact's mechanisms are covered by regression tests. Independent human adjudication of the corpus labels is not claimed. Research design, analysis, interpretation and conclusions are my own, and the content is my responsibility.

## Conflict of Interest

The artifact is also the basis of a commercial venture in which I have an interest, a potential conflict relevant to its evaluation, addressed by reference labels of stated provenance, a reproducible pipeline and standardised instruments; the practitioner instruments had not been used at the time of writing (§5B.1; positionality statement in §3.10).

## Reproducibility and Data Availability

The harness (`evaluation/`) regenerates the accuracy, agreement and paired-test figures of §5A.3–5A.6 from the committed prediction files (`evaluation/results/`, `evaluation/results_mistral-small-2603/`). The §5A.7 golden-set figures rest on the published snapshot or, for the production default, the exemplar effects and the learning-retrieval probe, on a contemporaneous record with no preserved per-item record; no harness regenerates them and they are cited as such (Appendix G.2, G.4). The artifact, evaluation code and diagram sources are in the private repository (`github.com/fogu13/CLARA`). Examination read access and an examiner package (the paraphrased corpus, the seed labels of §3.8 and the in-repo golden set, the immutable prediction files of every harness-scored run, the run metadata and file hashes; runs cited as contemporaneous record have no prediction file) are available on request.

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

(Generated on compilation.)

1. Introduction
2. Literature Review
3. Methodology
4. The Artifact
5. Evaluation and Results
6. Discussion
7. Conclusion
- References
- Appendix A: Study Instruments
- Appendix B: EU AI Act and GDPR Mapping
- Appendix C: Data Protection Impact Assessment
- Appendix D: Traceability Matrix
- Appendix E: Data Model DDL
- Appendix F: External-Review Episode
- Appendix G: Provenance and Revision Log
