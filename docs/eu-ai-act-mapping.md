# EU AI Act Compliance Mapping

## Document purpose

This document maps the Odradek Hybrid_GLM platform's features against the
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

## Article-by-article mapping

### Article 14 — Human Oversight

| Requirement | Platform implementation | Status |
|---|---|---|
| AI system shall be designed to allow human oversight | LangGraph `interrupt()` at the approval node — graph pauses, human reviews and approves/rejects | **Compliant** |
| Natural person shall have the technical capability to oversee | All consequential actions (Jira tickets, Slack notifications) require explicit approval via the UI | **Compliant** |
| Human shall be able to disregard or override output | Human can reject any proposed action; rejection routes to END, no action executed | **Compliant** |
| Human shall be able to interrupt or stop the system | The graph can be stopped at the approval interrupt; no auto-execution without approval | **Compliant** |

### Article 50 — Transparency

| Requirement | Platform implementation | Status |
|---|---|---|
| AI-generated content shall be labelled | Every AI output carries `audit: {model, source, limitations}` — enriched signals, synthesized insights, and learnings all have provenance metadata | **Compliant** |
| Users shall be informed when they interact with AI | The UI displays which insights are "LLM-synthesized" via audit metadata; severity is explicitly labelled "deterministic" | **Compliant** |
| AI system's output shall be distinguishable from human output | AI outputs carry `source: "llm_enrichment"` or `source: "llm_synthesis"`; human conclusions carry `reviewer: <id>` | **Compliant** |

### Article 15 — Robustness, Accuracy, and Cybersecurity

| Requirement | Platform implementation | Status |
|---|---|---|
| AI system shall achieve appropriate level of accuracy | Eval harness measures classification precision/recall/F1 against a golden set; results documented in the thesis | **Implemented** |
| AI system shall be resilient to errors, faults, inconsistencies | Enrichment batch failures are logged and skipped (graceful degradation); connector failures are non-fatal | **Compliant** |
| Model output is treated as untrusted | `AGENTS.md` rule: "treat model output as untrusted"; evidence/confidence/limitations on every AI claim | **Compliant** |

### Article 12 — Logging

| Requirement | Platform implementation | Status |
|---|---|---|
| AI system shall enable automatic logging of events | `events` table (migration 005) + `action_logs` table; Langfuse traces all LLM calls | **Compliant** |
| Logs shall be kept for a period appropriate to the system's purpose | Learning conclusions have `retention_expires_at` (730 days default) | **Compliant** |

### Article 13 — Quality Management

| Requirement | Platform implementation | Status |
|---|---|---|
| Quality management system shall be established | Eval harness + golden set + CI (npm run check); tests cover the full pipeline | **Implemented** |
| Quality management shall include risk management | Governance gate (PolicyRule) blocks compliance_concern actions; PII redaction in learning conclusions | **Compliant** |

## GDPR compliance

### Article 5 — Principles relating to processing

| Principle | Implementation |
|---|---|
| Lawfulness, fairness, transparency | AI outputs are labelled with audit metadata; human oversight is mandatory |
| Purpose limitation | Signals are processed for feedback analysis only; no secondary use |
| Data minimisation | Feedback text capped at 2000 chars for LLM context; PII redaction in learning conclusions |
| Accuracy | Confidence scores + limitations on every AI claim; human validation encouraged |
| Storage limitation | Learning conclusions have `retention_expires_at` (730 days); configurable |
| Integrity and confidentiality | RLS policies on all tables; workspace isolation; JWT auth |

### Article 22 — Automated individual decision-making

The platform does **not** make solely automated decisions with legal or
similar significant effects on individuals. All consequential actions
(creating tickets, sending notifications, building segments) require
explicit human approval via the LangGraph approval interrupt.

## DPIA summary

A Data Protection Impact Assessment is recommended because:
1. The platform processes personal data (customer feedback may contain PII)
2. The platform uses AI/LLM technology for analysis
3. When using API-based LLMs (OpenAI, Anthropic), data may be processed
   outside the EU — local-first (Ollama/vLLM) is the recommended mitigation

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
