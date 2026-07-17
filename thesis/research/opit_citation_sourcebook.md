# OPIT Coursework → Thesis Citation Sourcebook

*Compiled 12 Jul 2026 from a full sweep of `/Users/olamakri/Documents/OPIT` (11 courses, syllabi, readings, lecture decks, and your own graded submissions), cross-checked against `thesis/references.md`.*

**How to read this document.** Every source carries a status and a priority:
- ✅ **IN THESIS** — already in `references.md`; revision = reread so you can defend it in the viva.
- ➕ **ADD** — not yet in the thesis; a candidate to cite (chapter/claim given).
- 📝 **OWN WORK** — your own graded submission or blog post; reusable prose/method, self-citable with care.
- **P1/P2/P3** — revision priority (P1 = you will almost certainly be asked about it or must cite it).

The biggest finding first: **your DATA-8004 research proposal was a pre-registered sub-study of this very thesis** — its reference list is your Chapter 2 skeleton, already learned. And your RAI-8001 (RAG) and RAI-7005 (sentiment classification) reports are near-1:1 methodological precedents for Chapters 4–5. Revise your own three reports before anything else.

---

## Part 1 · The revision plan (ordered)

| # | Session (~1–2h each) | What to reread | Why |
|---|---|---|---|
| 1 | **Your own three reports** | `DATA-8004/05_Assessments/Graded/Part1_ResearchProposal_ElvisShehi.md` · `RAI-8001/05_Assessments/Graded/Assessment_2/RAI8001_Assessment_2_Report_ElvisShehi.pdf` · `RAI-7005/05_Assessments/Final/Shehi_Elvis_Report.pdf` | Your thesis pre-study, your RAG pilot, your sentiment-classification pilot. You wrote them — fastest re-learning, richest reusable citations. |
| 2 | **DSR + methods core** | Hevner 2004, Peffers 2007 (papers via proposal), plus `DATA-8004/01_Lectures/` Weeks 4–8 decks (methodologies, data collection, data analysis) and the *Qualitative SE Research — Reflections and Guidelines* PDF | Ch3 is built on these; the examiner will probe DSR fluency. |
| 3 | **HITL / automation backbone** | Shneiderman 2020 (+2022 book), Amershi 2019, Parasuraman 2000 & Parasuraman–Riley 1997, Bradshaw 2013, Skitka 1999 — all in `RAI-7003/03_Readings` + `06_Resources` | The approval-gate defense rests on this lineage; you cited most in your own assignments. |
| 4 | **Governance / EU AI Act** | `RAI-7001/03_Readings/` — the AI Act & GDPR texts, Floridi 2018, Jobin 2019, Model Cards, Raji 2020, Hagendorff 2020, plus your EU-AI-Act essay | Ch2 §2.15/Ch6 §6.2; your own essay prose is reusable. |
| 5 | **NLP foundations** | Vaswani, Mikolov, GloVe, Salton & Buckley (PDFs on disk in `RAI-8001`), plus Lewis RAG / Sentence-BERT / RAGAS from your RAG report | Ch2 NLP + Ch4 pipeline justification. |
| 6 | **Business frame** | Iansiti & Lakhani, Porter, Blank, Rogers (all in `RAI-8005`), your Assessment 1 | Ch1/Ch6 positioning; also your investor narrative. |

---

## Part 2 · Citation map, by thesis chapter

### Chapter 1 — Introduction (problem & market relevance)

| Status | Source | What it says | Cite for | Revise at |
|---|---|---|---|---|
| ✅ P1 | Bone et al. (2017), *JMR* | <30% of firms close the loop; structural barriers | §1.1 headline gap stat | Your DATA-8004 proposal (already cited there) |
| ✅ P1 | Lemon & Verhoef (2016), *J. Marketing* | CX as continuous journey capability | §1.1 always-on VoC framing | same |
| ✅ P1 | Halperin et al. (2022), *Economic J.* | Recovery actions can backfire (Uber, n≈1.5M) | §1.2 why closure must be measured | already in thesis §1.2 |
| ➕ P2 | **Iansiti & Lakhani (2020), *Competing in the Age of AI*, HBS Press** | AI-native firms scale on data/learning loops | §1.1/Ch6 — the learning loop as moat | `RAI-8005/06_Resources/Competing in the Age of AI.txt` |
| ➕ P2 | **Blank (2013), "Why the Lean Start-Up Changes Everything", *HBR*** | Build–measure–learn as method | §1.4/Ch6 — the loop is itself build-measure-learn | `RAI-8005/01_Lectures/Why the Lean Start-Up Changes Everything.pdf` |
| ➕ P3 | McKinsey (2025), *State of AI* | Enterprise AI adoption & value data | §1.1 market context (vendor-report caveat) | `RAI-8005/01_Lectures/The State of AI...pdf` |

### Chapter 2 — Literature Review

**§2.1 VoC / feedback loops** — all ✅ and already yours: Griffin & Hauser 1993, Wirtz 2010, Bone 2017 (revise via your proposal, P1).

**§2.2 NLP / sentiment / embeddings**

| Status | Source | Cite for | Revise at |
|---|---|---|---|
| ✅ P1 | Vaswani et al. (2017) | transformers | PDF: `RAI-8001/01_Lectures/Attention is All You Need.pdf` |
| ✅ P2 | Pang & Lee (2008); Wilson et al. (2005); Liu (2012) | sentiment foundations | via your proposal |
| ➕ P1 | **Mikolov et al. (2013), word2vec** | §2.2 embeddings lineage | `RAI-8001/01_Lectures/Efficient Estimation of Word Representations...pdf` |
| ➕ P2 | **Pennington et al. (2014), GloVe, EMNLP** | §2.2 embeddings | `RAI-8001/01_Lectures/GloVe...pdf` |
| ➕ P2 | **Salton & Buckley (1988), term weighting** | §2.2/Ch4 — the canonical TF-IDF citation (you cite Salton & McGill 1983; add this for the weighting scheme itself) | `RAI-8001/03_Readings/Term-Weighting Approaches...pdf` |
| ➕ P2 | **Reimers & Gurevych (2019), Sentence-BERT, EMNLP** | §2.2/Ch4 — semantic-retrieval component (pgvector) | via your RAG report |
| ➕ P2 | **Lewis et al. (2020), RAG, NeurIPS** | §2.16/Ch4 — grounding LLM outputs in retrieved evidence | via your RAG report |
| ➕ P3 | Robertson & Zaragoza (2009), BM25; Turney & Pantel (2010); Harris (1954); Manning et al., *IIR* | IR/distributional lineage, only if §2.2 is expanded | `RAI-8001/03_Readings/` |

**§2.15–2.16 Responsible AI / HITL / governance**

| Status | Source | Cite for | Revise at |
|---|---|---|---|
| ✅ P1 | Shneiderman (2020) *(just restored to references.md)* | high-automation + high-control framework | `RAI-7003/03_Readings/Reading - Human-Centered Artificial Intelligence.pdf` |
| ✅ P1 | Amershi et al. (2019) *(restored)* | 18 HAI guidelines → approval-UI design | `RAI-7003` readings; your Assignment 1 |
| ✅ P1 | Parasuraman et al. (2000); Lee & See (2004) | automation levels; trust calibration | `RAI-7003` decks |
| ✅ P1 | Floridi et al. (2018); Jobin et al. (2019) *(restored)* | RAI principle convergence | `RAI-7001/03_Readings/Luciano Floridi...pdf` |
| ✅ P1 | Mehrabi et al. (2021); Guo et al. (2017) | bias survey; calibration/overconfidence | via your proposal |
| ✅ P2 | Siebert et al. (2023); Laux & Ruschemeier (2025) | meaningful human control; Art-14 critique | already in thesis §2.16 |
| ➕ P1 | **Parasuraman & Riley (1997), "Use, Misuse, Disuse, Abuse", *Human Factors*** | §2.16/§6.2 — the reliance-failure taxonomy behind your automation-bias monitoring | `RAI-7003` readings; your Assignment 2 |
| ➕ P1 | **Mitchell et al. (2019), Model Cards, FAT*** | Ch4 §4.4 — the transparency/documentation artifact your compliance pack ships | `RAI-7001/03_Readings/...Model Cards for Model Reporting.pdf` |
| ➕ P2 | **Raji et al. (2020), Closing the AI Accountability Gap, FAT*** | Ch4 §4.9 — internal-audit framing of your review-then-harden story | `RAI-7001/03_Readings/`; your Assessment 1 |
| ➕ P2 | **Hagendorff (2020), The Ethics of AI Ethics, *Minds & Machines*** | §6.2 — principles rarely reach practice; your artifact operationalises them | `RAI-7001/03_Readings/` |
| ➕ P2 | **Bradshaw et al. (2013), Seven Deadly Myths of Autonomy, *IEEE IS*** | §2.16/§6.2 — why the loop stays human-governed | `RAI-7003`; your Assignment 1 |
| ➕ P2 | **Skitka et al. (1999), automation bias, *IJHCS*** | §6.2/§4.9 — the empirical automation-bias base under Laux & Ruschemeier | `RAI-7003`; your Assignment 1 |
| ➕ P2 | **Bender et al. (2021), Stochastic Parrots, FAccT** | §2.15 — training-data bias for the LLM enrichment layer | via your proposal |
| ➕ P3 | Lipton (2016); Schmager et al. (2023); Capel & Brereton (2023); Wischnewski et al. (2023); Okamura & Yamada (2020) | interpretability desiderata; HCAI definitions; trust measurement | `RAI-7003/06_Resources/Reading Text N` files |

**§2.16 LLM agents** — ✅ existing agent surveys; ➕ P2 **Yao et al. (2023) ReAct** and **Wang et al. (2024) LLM-agent survey** (confidence-gated execution + HITL fallback as safety pattern — directly supports §4.2) — both via your DATA-8004 proposal.

### Chapter 3 — Methodology

| Status | Source | Cite for | Revise at |
|---|---|---|---|
| ✅ P1 | Hevner 2004; Peffers 2007; Gregor & Hevner 2013; Prat 2015 | the DSR spine | your proposal + `DATA-8004/01_Lectures/` Weeks 4–5 |
| ✅ P1 | Cohen (1988) | effect sizes / practical vs statistical significance (§3.10, §5A) | your Part2 data-analysis submission |
| ✅ P2 | Braun & Clarke (2006); Brooke SUS; Davis TAM | qualitative + instruments (NOT in OPIT folders — external, already in thesis) | thesis Appendix A |
| ➕ P1 | ***Qualitative SE Research — Reflections and Guidelines* (open PDF for exact authors)** | §3.6/§3.11 — trustworthiness criteria for the thematic analysis | `DATA-8004/01_Lectures/Qualitative Software Engineering Research...pdf` |
| ➕ P2 | **Pedregosa et al. (2011), scikit-learn, *JMLR*** | §3.5/Ch4 — tooling citation for the eval harness | via your ML report |
| ➕ P2 | **Hastie, Tibshirani & Friedman, *Elements of Statistical Learning*** | §3.5 — cross-validation methodology (the OPIT "Cross-Validation" note is not citable; the textbook is) | external; topic covered in `RAI-7005/03_Readings/` |
| ➕ P3 | Es et al. (2024) RAGAS; Honovich et al. (2022) TRUE | §3.5/§6.5 — faithfulness metrics if LLM-generated text is evaluated | via your RAG report |

### Chapter 4 — Artifact

| Status | Source | Cite for | Revise at |
|---|---|---|---|
| 📝 P1 | **Your RAI-8003 group assignment: agentic RAG architecture** | §4.2 — your own prior architecture work; maps ~1:1 to the LangGraph design (plan–act–observe + RAG) | `RAI-8003/05_Assessments/Graded/RAI8003_Group3_Revised.docx` |
| ➕ P2 | Lewis 2020 RAG; Reimers & Gurevych 2019; Nogueira & Cho 2019 | retrieval/reranking components | via your RAG report |
| ➕ P2 | Mitchell et al. Model Cards | the model-card artifact in `/compliance` | above |
| ➕ P3 | Hutto & Gilbert (2014) VADER | §5A — a named, citable lexicon baseline (your rule-based floor is VADER-adjacent) | via your ML report |
| ➕ P3 | Kore (2022) *Designing Human-Centric AI Experiences*; Lew & Schumacher (2020) | approval-UX design choices | `RAI-7003`; your Assignments 2–3 |

### Chapter 5 — Evaluation

| Status | Source | Cite for | Revise at |
|---|---|---|---|
| 📝 P1 | **Your RAI-7005 sentiment report** | ready-made precedent: stratified 5-fold CV, confusion-matrix reading, class imbalance → macro-F1 justification | `RAI-7005/05_Assessments/Final/Shehi_Elvis_Report.pdf` |
| 📝 P1 | **Your DATA-8004 Part 2 (data analysis)** | worked statistical-vs-practical-significance prose (Cohen's d, Mann-Whitney) | `DATA-8004/05_Assessments/Graded/Part2_DataAnalysis_ElvisShehi.md` |
| ➕ P2 | Liang et al. (2022) HELM | §5A.6 — caution against single-number "LLM accuracy" | via your proposal |
| ➕ P3 | Wolpert (1992) stacking; Chen & Guestrin (2016) XGBoost | only if you add ensemble baselines | via your ML report |

### Chapter 6 — Discussion

| Status | Source | Cite for | Revise at |
|---|---|---|---|
| ➕ P2 | **Iansiti & Lakhani (2020)** | §6.3/§6.6 — learning loop as compounding moat | `RAI-8005/06_Resources/` |
| ➕ P2 | **Porter (1980) five forces** (+ digital-disruption reading) | §6.3 competitive structure | `RAI-8005/06_Resources/How Digital Business Disrupts...txt`; your Assessment 1 |
| ➕ P2 | **Rogers (2003) *Diffusion of Innovations***; Moore (1991) *Crossing the Chasm* | §6.6 adoption path for DACH mid-market | `RAI-8005`; your Assessment 1 |
| ➕ P2 | Hagendorff (2020) | §6.2 — governance-in-practice gap | above |
| ➕ P3 | Kim & Mauborgne Blue Ocean; MITRE AI Maturity; McKinsey (2019) responsible-AI | positioning / org-adoption color | `RAI-8005`, `RAI-7003/03_Readings/` |

---

## Part 3 · Your own reusable work (📝 highest revision leverage)

| Work | Where | Reuse |
|---|---|---|
| **DATA-8004 Research Proposal** (pre-study of this thesis) | `DATA-8004/05_Assessments/Graded/Part1_ResearchProposal_ElvisShehi.md` | Ch2 skeleton + all P1 citations above; check consistency with the final RQ framing |
| **RAG pipeline report** (VoC-framed, HotpotQA) | `RAI-8001/.../RAI8001_Assessment_2_Report_ElvisShehi.pdf` | Ch4 retrieval design + Ch5 faithfulness metrics; its 8 references |
| **Sentiment classification report** (TF-IDF/LogReg/SVM, 5-fold CV) | `RAI-7005/05_Assessments/Final/Shehi_Elvis_Report.pdf` | Ch3/Ch5 method prose (CV, confusion matrices, imbalance → macro-F1) |
| **Agentic-RAG architecture assignment** | `RAI-8003/05_Assessments/Graded/RAI8003_Group3_Revised.docx` | Ch4 architecture lineage (group work — attribute accordingly) |
| **EU AI Act essay + Assessment 4** | `RAI-7001/05_Assessments/Graded/EU_AI_Act_Essay_user_style_latestdraft.docx` | Ch2 governance narrative prose |
| **Statistics analysis (Part 2)** | `DATA-8004/.../Part2_DataAnalysis_ElvisShehi.md` | Ch5 statistical-reporting prose |
| **Blog: EU AI Act / Agentic AI & context engineering** | `Blog_Articles/01_navigating_eu_ai_act.md`, `12_agentic_ai_context_engineering.md` | drafting material — trace claims back to primary sources rather than self-citing a blog |

*Self-citation etiquette: coursework can be cited as unpublished prior work ("Shehi, 2026, unpublished MSc coursework") or, cleaner, reused as method/prose with its underlying primary sources cited. For the group assignment, attribute the group. Check OPIT's self-plagiarism policy before verbatim reuse of assessed text.*

---

## Part 4 · Gaps & cautions

1. **Not in any OPIT folder — source externally** (already in thesis, but no local PDF to revise from): Braun & Clarke (2006), Brooke's SUS, Davis's TAM, Tufte/Munzner (viz canon — the RAI-7002 storytelling decks teach their principles without naming them; add **Wilkinson, *Grammar of Graphics*** and **Knaflic, *Storytelling with Data*** only if Ch2's viz section grows).
2. **OPIT-authored lecture notes are not citable** ("Cross-Validation_Machine Learning.pdf" etc.) — they're revision material; cite the canonical texts they summarize (ESL, Guo 2017).
3. **Vendor/consulting sources** (McKinsey, WEF, Google, MITRE) — cite as market evidence with access dates, per the thesis's existing convention; never as load-bearing empirical claims.
4. **Fixed during this sweep:** five §2.15 citations (Amershi 2019, Beauchamp & Childress 2001, Floridi et al. 2018, Jobin et al. 2019, Shneiderman 2020) were cited in prose but **missing from references.md** — now restored.
