# DPIA Template — CLARA CLARA Platform

## Data Protection Impact Assessment

### 1. Description of the processing

**System:** CLARA CLARA — governed customer feedback-to-action platform

**Processing:** Ingestion, AI-powered triage (sentiment/urgency/tag extraction,
insight synthesis), governance-gated action routing, outcome measurement, and
organizational learning from customer feedback signals.

**Data subjects:** Customers whose feedback is ingested (support tickets,
surveys, reviews, app store comments).

**Data categories:**
- Customer feedback text (may contain PII: names, emails, phone numbers)
- Customer identifiers (customer_id, account_id — pseudonymized)
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

1. **Local-first LLM processing** — Ollama/vLLM support eliminates data
   transfer to third-party LLM providers. This is the primary mitigation.

2. **PII redaction** — `redact_common_pii()` in `apps/api/app/domain/models.py`
   redacts email, phone, IP, address patterns from learning conclusions.

3. **Human-in-the-loop** — No consequential action (ticket, notification,
   segment) is executed without explicit human approval via the LangGraph
   approval interrupt.

4. **Data minimisation** — Feedback text is capped at 2000 characters for
   LLM context. Only pseudonymized identifiers are stored.

5. **Access control** — Row-Level Security on all database tables; workspace
   isolation; JWT-based auth with workspace_id scoping.

6. **Audit trail** — Every AI output carries audit metadata (model, source,
   limitations). Every action is logged with connector type and result.

7. **Retention limits** — Learning conclusions have `retention_expires_at`.
   Configurable per workspace.

### 5. Signature

| Role | Name | Date |
|---|---|---|
| DPO | _________________ | _______ |
| CTO | _________________ | _______ |
| Thesis supervisor | _________________ | _______ |
