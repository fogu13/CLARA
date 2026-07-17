# Deep-Research Source Log

All sources accessed **2026-06-26**. Vendor/analyst publications are supporting market evidence (figures vary by analyst — cite as reported, with date); academic claims are anchored to peer-reviewed or arXiv preprints. Load-bearing stats verified across ≥2 sources where possible.

## 1. The feedback-to-action gap — current industry evidence

- **Forrester, 2025 Global CX Index Rankings** — 21% of brands declined, 6% improved, 73% unchanged (global); in the US, for the 2nd consecutive year, **25% of brands' CX rankings declined vs only 7% improved**. https://www.forrester.com/press-newsroom/forrester-global-customer-experience-index-2025-rankings/
- **Forrester, 2025 VoC & CX Measurement Survey ("Six Gaps")** — most CX teams still **don't get stakeholders to act** on insights or earn stakeholder confidence; **only 27%** communicate insights in a timely way; only ~half link CX metrics to business outcomes. https://www.forrester.com/blogs/feedback-and-cx-measurement-programs-must-boost-their-impact-according-to-forresters-2025-survey/
- **CX Dive** — US customer experience quality hits an all-time low (Forrester). https://www.customerexperiencedive.com/news/us-customer-experience-quality-all-time-low-forrester/751787/
- *Use:* Ch 1 (problem urgency), Ch 2 §2.16. **Directly corroborates Bone et al. (2017): the gap is operationalisation/action, not collection.**

## 2. Market structure & competitive landscape (2026)

- **Gartner Magic Quadrant for VoC Platforms 2026** — 12 providers evaluated; **Qualtrics a Leader for the 5th consecutive year**, with Medallia and Sprinklr also Leaders; Alchemer the sole Challenger; Visionaries quadrant empty. Gartner frames **"AI Experience Agents"** (agents autonomously assessing customer records and executing personalised actions) as the next wave. https://www.cxtoday.com/customer-analytics-intelligence/gartner-magic-quadrant-voc-platforms-2026/ · https://www.prnewswire.com/news-releases/qualtrics-named-a-leader-in-2026-gartner-magic-quadrant-for-voice-of-the-customer-platforms-302712691.html
- **Enterpret — "first agentic customer feedback platform"** (27 Oct 2025): ingests 50+ channels; **Customer Knowledge Graph** maps feedback to accounts/features/opportunities; **Action Agents** detect emerging bugs and escalate at-risk premium accounts **in real time**; customers include Perplexity, Notion, Canva, Fanatics. https://www.businesswire.com/news/home/20251027487140/en/ · https://siliconangle.com/2025/10/27/exclusive-enterpret-adds-agents-customer-feedback-analysis-platform/
- *Use:* Ch 6 §6.3 (positioning — Enterpret detects/routes/notifies; does not bind actions to an outcome contract or ship a decaying learning memory). Ch 1, Ch 2 §2.16.

## 3. VoC / feedback-analytics market size

- Estimates vary by analyst: **~USD 9.5B (2025) → ~USD 22.5B (2034), ~15% CAGR** (Custom Market Insights); QKS Group **16.66% CAGR** through 2030; ~**64%** of VoC tools now use AI-based sentiment analysis; ~**68%** of enterprises prioritise VoC analytics. https://www.custommarketinsights.com/report/voice-of-customer-voc-platform-market/ · https://www.globenewswire.com/news-release/2025/04/15/3061798/0/en/Voice-of-Customer-VoC-Market-Disruptions-Riding-a-High-Growth-Wave-Through-2030-at-CAGR-16-66.html
- *Use:* Ch 1 (market relevance), cited as a **range** with the analyst named — not a single point estimate.

## 4. EU AI Act — current regulatory state (CORRECTION to existing docs)

- **Digital Omnibus / simplification package** (Council–Parliament agreement, **7 May 2026**): **Annex III high-risk** obligations postponed **2 Aug 2026 → 2 Dec 2027**. **Article 50 transparency obligations remain on the 2 Aug 2026 schedule (unchanged)**; the only deferral is a **4-month grace period to 2 Dec 2026 for the Article 50(2) machine-readable "watermarking"** obligation on systems placed on the market before 2 Aug 2026. https://www.consilium.europa.eu/en/press/press-releases/2026/05/07/artificial-intelligence-council-and-parliament-agree-to-simplify-and-streamline-rules/ · https://www.gibsondunn.com/eu-ai-act-omnibus-agreement-postponed-high-risk-deadlines-and-other-key-changes/ · https://www.lw.com/en/insights/ai-act-update-eu-resolves-to-change-rules-and-extend-deadlines
- **Article 50 reference** + Commission draft transparency guidance (May 2026). https://artificialintelligenceact.eu/article/50/ · https://www.globalpolicywatch.com/2026/05/10-takeaways-european-commission-draft-guidelines-on-ai-transparency-under-the-eu-ai-act/
- *Correction:* the existing artifact docs stated "Article 50 transparency moved to 2 December 2026." That conflates Art 50 transparency (unchanged) with the Art 50(2) watermarking grace period. Manuscript corrected in Ch 4 §4.4 and Appendix B.

## 5. Recent academic literature (2023–2026) to modernise Ch 2

- **LLM-based human–agent collaboration & interaction — survey.** arXiv:2505.00753 (2025). Interactive instruction editing, mid-task refinement, online intervention, post-task skill archiving. → grounds the artifact's bounded-model + human-checkpoint design.
- **Human-in-the-loop software-development agents (HULA).** arXiv:2411.12924 (2024); deployed in Atlassian Jira; engineers report reduced effort on straightforward tasks with human steering. → industrial precedent for governed, human-checkpointed agentic workflows.
- **LLM agent survey** (CoLing 2025): paradigms — tool use incl. RAG, planning, feedback learning. https://github.com/xinzhel/LLM-Agent-Survey
- **LLM-as-a-Judge — survey** (Gu et al., 2025). arXiv:2411.15594. Documents verbosity, position, and self-enhancement bias; multi-judge panels and calibration as mitigations. → cited in Ch 3 §3.5.4 as the justification for the independent star-rating cross-check and human adjudication of borderline theme matches (avoiding naïve LLM-judges-LLM circularity).
- **From Generation to Judgment: opportunities & challenges of LLM-as-a-judge.** arXiv:2411.16594 (2024).

## 6. Integration map

| Finding | Manuscript location |
|---|---|
| Forrester 2025 action gap; CX all-time low | Ch 1 §1.1; Ch 2 §2.16 |
| Gartner MQ VoC 2026; AI Experience Agents | Ch 1 §1.1; Ch 2 §2.16; Ch 6 §6.3 |
| Enterpret agentic launch (detect/route, no measured closure) | Ch 6 §6.3 |
| VoC market size (range) | Ch 1 §1.1 |
| EU AI Act omnibus correction | Ch 4 §4.4; Appendix B; Ch 2 §2.15 |
| LLM agents / HITL precedent | Ch 2 §2.16; Ch 4 §4.2; Ch 6 DP5 |
| LLM-as-judge bias | Ch 3 §3.5.4; Ch 5 §5A |
