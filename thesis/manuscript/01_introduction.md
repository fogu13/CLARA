# Chapter 1: Introduction

## 1.1 Background and Motivation

Organisations collect customer feedback continuously; the Voice of the Customer (Griffin and Hauser, 1993) is an always-on capability across the customer journey (Lemon and Verhoef, 2016). The binding constraint is no longer collection but operationalisation. Forrester's 2025 survey finds that most programmes still struggle to get stakeholders to act on insights (Forrester, 2025b), and its close-the-loop report finds the practice promising but less effective than it could be, with slow communication of feedback and unclear ownership among the reasons (Fazio et al., 2025). Bone et al. (2017) show that soliciting feedback changes subsequent purchasing behaviour, so the act of asking is itself an intervention.

Large language models (LLMs) have made enrichment of unstructured feedback cheap and multilingual, and the same capability raises a governance question: if software can recommend and execute responses, human oversight, auditability and EU AI Act (Regulation 2024/1689) and GDPR compliance become design requirements.

## 1.2 Problem Statement

Four deficiencies constitute the feedback-to-action gap.

1. Signal fragmentation. Signals arrive across disconnected sources and are rarely unified into one prioritised view (Neslin et al., 2006; Verhoef, Kannan and Inman, 2015).
2. The insight-action gap. Organisations lack governed mechanisms to decide what action a problem warrants, route it to an owner and execute it through the systems they already use (Forrester, 2025b; Fazio et al., 2025; Homburg and Fürst, 2005; Wirtz et al., 2010).
3. Unmeasured closure. Actions are seldom tied to an explicit outcome contract, so an organisation cannot tell whether an action resolved the problem or merely produced a ticket, and acting is not automatically value-creating: apologies after service failures did not restore future spending unless paired with material compensation (Halperin, Ho, List and Muir, 2022).
4. Lost organisational memory. What worked, and where, is rarely codified, so lessons depreciate and are relearned (Walsh and Ungson, 1991; Argote, 2013).

Within the literature and product documentation reviewed for this thesis (§2.7; §6.3), no evaluated system was identified that combines governed execution, a measured outcome and a reusable learning in one chain. The thesis treats loop closure as a workflow-and-governance problem and designs around two primitives: a measured outcome contract and a perishable learning memory.

## 1.3 Research Aim and Questions

The aim is to design, build and evaluate a software artifact that operationalises the loop (Signal → Insight → Action → Learning) under Responsible-AI governance, and to derive design principles from doing so.

| Question | Focus | Answered by |
|---|---|---|
| RQ1 (core) | How can a software artifact operationalise the loop so that actions are governed, executed and measured for closure, with reusable learning captured? | Design and demonstration (Chapter 4); principle synthesis (Chapter 6) |
| RQ2 (governance) | What design principles enable governed action-taking (draft-plus-approval, authority graduated by consequence class, an audit trail) aligned with the EU AI Act and GDPR, and how do practitioners experience the friction? | Specified and tested controls (Chapter 4); regulatory interpretation (Appendix B); friction clause not conducted |
| RQ3a (agreement) | How closely does the enrichment pipeline agree with reference sentiment, risk, journey-stage and owner labels on paraphrased public reviews, and how does agreement vary by task and predictor? | Quantitative evaluation (Chapter 5, §5A) |
| RQ3b (equity) | Does the choice of triage method change whose problems are escalated, measured as recall of escalation-worthy signals across source-language strata? | Descriptive stratum comparison (§5A.5) |
| RQ4 (practitioner) | How do practitioners assess the artifact's usefulness, usability and trustworthiness? | Protocol and instruments (Appendix A; §5B); not conducted |

RQ3a and RQ3b are answered through a quantitative evaluation on real customer feedback (paraphrased and de-identified) scored against reference labels that were drafted by a language-model assistant and used as delivered, with the customers' own star rating as the only human-origin reference (§3.7; Chapter 5, §5A): RQ3a by per-field agreement, RQ3b by escalation recall stratified by source language (§5A.5). Neither gold standard is human-labelled. Theme and action carry labels but are not scored because their semantic-agreement procedure (§3.5.2) was not executed; journey stage and owner are scored under a supplied inventory, a constrained task distinct from production free-form routing (§5A.4.1). Eight early working hypotheses (H1 to H8) are carried in Appendix D with their evidence status and as coding labels in the instruments.

The central claim follows. This thesis develops and examines CLARA, a governed workflow that links customer feedback to approved actions, recorded outcome measurements and reusable learning records. The evaluation establishes selected technical properties and bounded enrichment performance on one corpus. Whether these mechanisms improve practitioner decisions and customer outcomes remains to be established.

## 1.4 The Artifact in Brief

CLARA is a web platform (Chapter 4) whose current build implements the Signal → Insight → Action → Learning cycle as bounded stages: signals are ingested, enriched by a language model, synthesised into insights, accepted by a person as problems, proposed as actions that a person approves before anything leaves the system, measured against an outcome contract, and codified as a learning whose retrieval weight decays with age. Governance is a property of the loop: human approval of every action, policy checks that can withhold it, an audit trail with a hashed evidence pack, a published model card, and a fail-closed residency gate that refuses model providers it cannot place in the EU or on the deployer's host (§4.4). The outcome-contract, loop-verdict and learning-memory mechanisms are implemented and regression-tested but not deployed at the time of writing (§4.1).

## 1.5 Research Approach

The thesis adopts Design Science Research (DSR), whose primary output is a purposeful artifact (Hevner et al., 2004; Peffers et al., 2007), and pursues its dual contribution: a situated instantiation and prescriptive design knowledge (Gregor and Hevner, 2013). The evaluation conducted is technical and bounded (§1.7). The practitioner study was designed; its protocol, instruments and pre-registered reporting tiers are retained (Appendix A; §5B), but it was not conducted (Chapter 3).

## 1.6 Contributions

1. An artifact that implements the loop from signal to contracted outcome measurement and reusable learning under explicit governance, mechanisms regression-tested and operation demonstrated (Chapter 4).
2. Design principles from decisions the literature reviewed in Chapter 2 does not resolve: closure as a contracted, graded measurement that refuses below its minimum data requirements; perishable memory through confidence decay; authority graduated by consequence class with every action a draft; a bounded model inside a deterministic loop; and the decision not to ship a capability whose errors fall unevenly on the people served. Chapter 6 states each principle (DP1 to DP7) with its evidence status and boundary.
3. A bounded evaluation of LLM-based enrichment and routing against reference labels of stated provenance (§3.7) on 188 English paraphrases of public reviews from three sectors (food delivery, fintech, B2B industrial) (Chapter 5, §5A).
4. An account of how human oversight and auditability are built into an action-taking system as design commitments, with a documented EU AI Act and GDPR interpretation (Chapters 4 and 6; Appendices B and C).

## 1.7 What Is Measured, What Is Demonstrated, and What Is Argued

The table condenses Appendix D in its status vocabulary.

| Claim | Supported now | Open |
|---|---|---|
| RQ1 governed feedback-to-action architecture | Implemented architecture, worked demonstration, regression-tested mechanisms (Chapter 4) | Whether it improves decisions or resolves customer problems in practice |
| RQ2 governance | Specified and tested approval and provenance controls; a documented regulatory interpretation (Appendix B) | Whether people understand the controls, catch errors and accept their cost: not conducted |
| RQ3a enrichment | Measured (bounded): agreement with star-rating proxies on 153 signals and with assistant-authored risk labels on 106 of the 188-signal corpus; routing on 182 (§5A.3 to §5A.4) | Agreement with independent human judgement; performance on natural deployment data |
| RQ3b escalation disparities | Descriptive differences across source strata; the German-source positive stratum has eight cases (§5A.5) | A language effect, a fairness ranking of methods, or evidence of parity |
| RQ4 practitioner experience | Protocol and instruments (Appendix A; §5B) | All empirical answers: not conducted |
| DP1 contracted, graded closure | Implemented; refusal below minimum data requirements tested (§3.5.5, §4.4) | Benefit on live outcome data (the estimator has run on simulated outcome data only) |
| DP2 perishable memory | Implemented decay; retrieval changed recommendations on GLM-5.2 in small probes and did not on the production default; probes on simulation-authored learnings over simulated outcomes (§5A.7) | Whether decay changes retrieval appropriately or improves recommendations: untested hypothesis |

## 1.8 Scope and Delimitations

The scope is governed loop closure; survey collection, customer data platforms, campaign delivery and product management are systems to integrate with. The quantitative evaluation scores the enrichment and routing pipeline against reference labels (§3.7) on one paraphrased corpus and claims neither production-scale benchmarking nor agreement with independent human judgement. The practitioner study was not conducted, and long-run outcomes such as retention lie beyond its timeframe. The platform pushes approved actions to Jira and Slack, pulls feedback through official-API connectors, CSV import and a signed webhook, and drafts CRM (HubSpot) actions locally only (§4.7).

## 1.9 Responsible AI Positioning

Responsible AI is a design dimension, not the headline contribution; it makes governed loop closure defensible. Concretely: human oversight and logging designed against EU AI Act Articles 14 and 12 (voluntarily aligned), the Article 50(2) marking of exported drafts analysed and left as an open item (Appendix B), GDPR data-governance principles (Appendix C), and trust calibration (Lee and See, 2004). The approval gate controls false positives, wrong or harmful actions reaching an external system; it cannot recover escalation-worthy signals that the enrichment ranks too low (22 of 50 under the seed labels on the production rubric). Fairness is evaluated, not enforced: escalation recall is reported descriptively across source strata (§5A.5), routing-fairness enforcement is not built (§6.4), and standing fairness monitoring is on the agenda (§6.5; Mehrabi et al., 2021).

## 1.10 Structure of the Thesis

Chapter 2 reviews the literature: turning feedback into accountable action (§2.1), enriching feedback under imperfect labels (§2.2), interpreting outcome evidence and governing automated action (§2.3), reusing knowledge under changing conditions (§2.4), Design Science Research (§2.5), Responsible AI and EU law (§2.6), and the research gap (§2.7). Chapter 3 sets out the methodology, corpus and outcome-measurement model. Chapter 4 documents the artifact, its deployment status, governance controls and a worked example. Chapter 5 presents the quantitative evaluation (§5A) and the status of the practitioner study (§5B). Chapter 6 states the design principles, compares comparable systems, and sets out limitations and an agenda. Chapter 7 concludes. Appendix A holds the practitioner-study instruments, B the EU AI Act and GDPR mapping, C the provider-prepared material for a deployer's data-protection impact assessment, D the traceability matrix, E the data model, F the external review episode, and G the provenance and revision log.
