# Data Protection Impact Assessment (completed): the platform

> File paths in §4 refer to the CLARA implementation. Completed for the thesis evaluation context (public, paraphrased, de-identified data); a deployment processing real customer data must re-run this DPIA against its actual configuration.

### 0. Lawful basis (GDPR Article 6)

For the **thesis evaluation**, the data is public, paraphrased, and de-identified, and interview participation is processed on the basis of **consent** (Article 6(1)(a); Appendix A). For a **production deployment**, the controller's lawful basis for processing customer feedback is **legitimate interest** (Article 6(1)(f)) in improving products and service, balanced against data-subject interests via the safeguards below; where AI-generated content reaches customers, Article 50 transparency applies. No special-category data (Article 9) is sought or required.

### 1. Description of the processing

**System:** the platform, a governed customer feedback-to-action platform

**Processing:** Ingestion, AI-powered triage (sentiment/urgency/tag extraction,
insight synthesis), governance-gated action routing, outcome measurement, and
organizational learning from customer feedback signals.

**Data subjects:** Customers whose feedback is ingested (support tickets,
surveys, reviews, app store comments).

**Data categories:**
- Customer feedback text (may contain PII: names, emails, phone numbers)
- Customer identifiers (customer_id, account_id; pseudonymized)
- Metadata: source, timestamp, journey stage, tags
- AI-generated metadata: sentiment, urgency, severity, category
- Action records: connector push results (Jira issue keys, Slack message IDs)
- Learning conclusions: reviewer-authored summaries (PII-redacted)

### 2. Necessity and proportionality

| Purpose | Necessity | Proportionality |
|---|---|---|
| Feedback triage | Necessary for product improvement | LLM processes text only; no profiling of individuals |
| Action routing | Necessary for closing the feedback loop | Human approval required for all consequential actions |
| Outcome measurement | Necessary for verifying action effectiveness | Metrics are aggregate (recurrence counts), not individual |
| Learning | Necessary for organizational improvement | Conclusions are PII-redacted; pseudonymized reviewer IDs |

### 3. Risks to data subjects

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| PII in feedback text reaches LLM API | Medium (if API model used) | High | PII redaction regex on ingestion; local-first LLM recommended |
| Incorrect sentiment/urgency classification | Medium | Low (human reviews before action) | Confidence scores + limitations on every AI output |
| Unauthorized access to feedback data | Low | High | Supabase Auth + RLS; workspace isolation; JWT verification |
| Feedback data retained beyond necessity | Low | Medium | Configurable retention (730 days default); scheduled cleanup |
| AI-generated insights misrepresent customer views | Medium | Medium | Human-in-the-loop approval; evidence excerpts included |

### 4. Risk mitigation measures

1. **Local-first LLM processing.** Ollama/vLLM support eliminates data
   transfer to third-party LLM providers. This is the primary mitigation.

2. **PII redaction.** `redact_common_pii()` in `apps/api/app/domain/models.py`
   redacts email, phone, IP, address patterns from learning conclusions.

3. **Human-in-the-loop.** No consequential action (ticket, notification,
   segment) is executed without explicit human approval via the LangGraph
   approval interrupt.

4. **Data minimisation.** Feedback text is capped at 2000 characters for
   LLM context. Only pseudonymized identifiers are stored.

5. **Access control.** Row-Level Security on all database tables; workspace
   isolation; JWT-based auth with workspace_id scoping.

6. **Audit trail.** Every AI output carries audit metadata (model, source,
   limitations). Every action is logged with connector type and result.

7. **Retention limits.** Learning conclusions have `retention_expires_at`.
   Configurable per workspace.

### 5. Data-subject rights (GDPR Chapter III)

| Right | How it is supported |
|---|---|
| Access / portability (Arts 15, 20) | Signals and derived records are workspace-scoped and queryable by subject identifier; export to CSV/JSON. |
| Rectification (Art 16) | Enrichment labels are editable; corrections feed back to the classifier. |
| Erasure (Art 17) | Per-subject delete cascades across signals, insights, and audit references; learning conclusions are PII-redacted at creation. |
| Restriction / objection (Arts 18, 21) | Processing can be suspended per workspace; legitimate-interest objection honoured. |
| Automated-decision safeguards (Art 22) | No solely-automated decision with legal/significant effect on an individual; consequential actions require human approval. |
| Transparency (Arts 13–14, AI Act Art 50) | AI-generated outputs are labelled; provenance metadata recorded. |

### 6. Conclusion and residual risk

With the mitigations in §4 applied (model sovereignty via a self-hostable LLM, PII redaction, mandatory human approval for consequential actions, workspace-scoped RLS, retention limits, and a full audit trail), the residual risk to data subjects is assessed as **low and acceptable**, and the processing may proceed. Two residual risks are explicitly carried forward (Chapter 6): behavioural automation bias at the approval gate, and the attack surface of public ingestion endpoints. A production deployment must re-assess against its actual model provider, connectors, and retention configuration, and consult its DPO. No prior consultation with a supervisory authority (Article 36) is indicated for the assessed (non-high-risk) processing.

### 7. Sign-off

| Role | Name | Date |
|---|---|---|
| DPO | _________________ | _______ |
| Controller representative | _________________ | _______ |
| Thesis supervisor | _________________ | _______ |
