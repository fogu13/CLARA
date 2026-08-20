# EU AI Act Compliance Mapping

## Document purpose

This document maps the CLARA platform's features against the
EU AI Act requirements and GDPR obligations. It serves as both a thesis
chapter contribution and a commercial compliance artifact.

## Risk classification

### Likely NOT Annex III high-risk

The platform is a customer feedback analysis tool, not an AI system listed
in Annex III (which covers biometric identification, critical infrastructure,
education/employment, essential services, law enforcement, migration, and
justice). However, the classification should be reviewed if:

- The platform is used in an essential-service context (banking, healthcare)
- The platform makes automated decisions with significant effects on individuals
- The platform is used for credit scoring or insurance pricing

**Current position:** The platform is a decision-support tool with mandatory
human-in-the-loop approval for all consequential actions. It does not make
automated decisions about individuals without human review.

### Sentiment analysis is not "emotion recognition" under the Act

A recurring classification question is whether the platform's sentiment and
urgency tagging falls under the Act's emotion-recognition provisions: the
Article 5(1)(f) prohibition (workplace and education contexts) or the
corresponding Annex III high-risk category. On the Act's own definitions it
does not: an "emotion recognition system" is defined (Article 3(39)) as one
that identifies or infers emotions or intentions of natural persons **on the
basis of their biometric data**. Text-based sentiment analysis of customer
feedback processes no biometric data, so it sits outside both the prohibition
and the Annex III entry. The platform's triage is therefore minimal/limited
risk, with the Article 50 transparency duties (applying from 2 August 2026) as
the operative obligations. This reading should be re-verified against final
Commission guidance if the platform ever ingests voice or video feedback,
where the biometric qualifier could be met.

## Article-by-article mapping

### Article 14: Human Oversight

| Requirement | Platform implementation | Status |
|---|---|---|
| AI system shall be designed to allow human oversight | LangGraph `interrupt()` at the approval node: graph pauses, human reviews and approves/rejects | **Compliant** |
| Natural person shall have the technical capability to oversee | All consequential actions (Jira tickets, Slack notifications) require explicit approval via the UI; the approving reviewer's identity is bound to the verified login (JWT-derived pseudonym, e.g. `user-3fa2b1c9`), replacing the earlier self-asserted request-body identity; an opt-in, admin-only **four-eyes** workspace flag requires two distinct approvers; the first approval is recorded but holds execution, self-confirmation is rejected, and a rejection resets the tally | **Compliant** |
| Human shall be able to disregard or override output | Human can reject any proposed action; rejection routes to END, no action executed | **Compliant** |
| Human shall be able to interrupt or stop the system | The graph can be stopped at the approval interrupt; no auto-execution without approval | **Compliant** |

### Article 50: Transparency

| Requirement | Platform implementation | Status |
|---|---|---|
| AI-generated content shall be labelled | Every AI output carries `audit: {model, source, limitations}`: enriched signals, synthesized insights, and learnings all have provenance metadata | **Compliant** |
| Users shall be informed when they interact with AI | The UI displays which insights are "LLM-synthesized" via audit metadata; severity is explicitly labelled "deterministic" | **Compliant** |
| AI system's output shall be distinguishable from human output | AI outputs carry `source: "llm_enrichment"` or `source: "llm_synthesis"`; human conclusions carry `reviewer: <id>` | **Compliant** |

### Article 15: Robustness, Accuracy, and Cybersecurity

| Requirement | Platform implementation | Status |
|---|---|---|
| AI system shall achieve appropriate level of accuracy | Eval harness measures classification accuracy/F1 against a 100-item bilingual golden set (72 en / 28 de; the German stratum is **authored**, not naturally occurring; disclosed in the model card). Published snapshot (run 2026-07-18T14:28Z, production config, n=100): sentiment 97% (95% CI 93–100%), urgency 90% (CI 84–95%), tag F1 fuzzy 82.7%; per-language with denominators: EN (n=72) sentiment 97.2% / urgency 90.3%, DE (n=28) 96.4% / 89.3%. Independently, the same enrichment path scores 0.86 sentiment accuracy against the thesis's 188-signal star-rating gold (4 Aug 2026); the more conservative of the two figures. Metrics are committed only via an explicit `--publish` flag (`published_metrics.json`), served at `GET /model-card/metrics`, and rendered in the product's model card; the hallucination heuristic is EN-scope only by construction (non-EN items excluded rather than misreported; disclosed) | **Implemented** |
| AI system shall be resilient to errors, faults, inconsistencies | Enrichment batch failures are logged and skipped (graceful degradation); connector failures are non-fatal | **Compliant** |
| Model output is treated as untrusted | `AGENTS.md` rule: "treat model output as untrusted"; evidence/confidence/limitations on every AI claim | **Compliant** |

### Article 12: Logging

| Requirement | Platform implementation | Status |
|---|---|---|
| AI system shall enable automatic logging of events | `events` table (migration 005) + `action_logs` table; Langfuse traces all LLM calls; approval decisions are recorded on an **append-only** approval record carrying the reviewer's JWT-derived pseudonym and the canonical sha256 content hash of the evidence pack as it stood pre-decision; the hash is stable across re-exports of unchanged records, so whether the pack an approver saw has since changed is provable | **Compliant** |
| Logs shall be kept for a period appropriate to the system's purpose | Learning conclusions have `retention_expires_at` (730 days default) | **Compliant** |

### Article 17: Quality Management

| Requirement | Platform implementation | Status |
|---|---|---|
| Quality management system shall be established | Eval harness + golden set + CI (npm run check); tests cover the full pipeline | **Implemented** |
| Quality management shall include risk management | Governance gate (PolicyRule) blocks compliance_concern actions; PII redaction in learning conclusions | **Compliant** |

### Article 4: AI Literacy

| Requirement | Platform implementation | Status |
|---|---|---|
| Providers and deployers shall take measures to ensure a sufficient level of AI literacy of their staff | An in-product AI-literacy module (EN + DE) explains the system's capabilities and limits; including that the displayed "model score" (renamed from "confidence") is an uncalibrated heuristic blending LLM self-report with volume/source counts, not a validated probability. The product copy was corrected from "discharges your team's AI-literacy duty" to "**supports your Art. 4 program**" (EN + DE): the module records only a workspace-level pack-delivery attestation and deliberately no per-user completion tracking, so it *supports*; and does not discharge; the deployer's own Art. 4 obligation | **Implemented** |

## GDPR compliance

### Article 5: Principles relating to processing

| Principle | Implementation |
|---|---|
| Lawfulness, fairness, transparency | AI outputs are labelled with audit metadata; human oversight is mandatory |
| Purpose limitation | Signals are processed for feedback analysis only; no secondary use |
| Data minimisation | Feedback text capped at 2000 chars for LLM context; PII redaction in learning conclusions |
| Accuracy | Model score (renamed from "confidence"; explained in the UI as an uncalibrated heuristic, not a validated probability) + limitations on every AI claim; human validation encouraged |
| Storage limitation | Learning conclusions have `retention_expires_at` (730 days); configurable |
| Integrity and confidentiality | RLS policies on all tables; workspace isolation; JWT auth |

### Article 22: Automated individual decision-making

The platform does **not** make solely automated decisions with legal or
similar significant effects on individuals. All consequential actions
(creating tickets, sending notifications, building segments) require
explicit human approval via the LangGraph approval interrupt.

## DPIA summary

A Data Protection Impact Assessment is recommended because:
1. The platform processes personal data (customer feedback may contain PII)
2. The platform uses AI/LLM technology for analysis
3. When using API-based LLMs (OpenAI, Anthropic), data may be processed
   outside the EU; local-first (Ollama/vLLM) is the recommended mitigation

**DPIA template location:** `docs/dpia-template.md`

## Local-first as compliance mitigation

The provider-agnostic AI layer (`apps/api/app/services/ai.py`) supports
Ollama and vLLM for on-premise processing. When configured with a local
LLM server:

- No customer feedback data leaves the organisation's infrastructure
- No API-based LLM provider processes the data
- GDPR data transfer concerns are eliminated
- EU data residency is guaranteed

This is the platform's primary commercial moat for the EU market.
