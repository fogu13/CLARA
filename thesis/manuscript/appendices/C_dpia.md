# Data Protection Impact Assessment: provider-prepared material for a deployer's assessment

### C.1 What this document is and is not

A data protection impact assessment under GDPR Article 35 is the controller's assessment: the controller describes the processing it intends to carry out, judges its necessity and proportionality, assesses the risks to data subjects, decides the measures, and signs. This document is not that assessment. It is the provider's preparation of the material a controller needs: a description of the processing the platform performs, the technical safeguards the artifact implements (each of them present in the repository; Chapter 4), the risks the author identifies, a possible lawful basis, and a blank sign-off. A deployer processing real customer data must run its own assessment against its configuration, model provider, tracing and retention choices, complete the balancing test, consult its data protection officer, and sign. Nothing here has been signed by a controller or reviewed by a data protection officer, and no prior consultation with a supervisory authority (Article 36) has been sought.

For the thesis's own evaluation the position is narrower. The corpus is 188 English paraphrases of public reviews, de-identified in an assistant-led session, with seed labels authored in the same session (§3.7; Appendix G.1); no identified or identifiable customer is processed. The practitioner study was not conducted at the time of writing, so no participant data were processed; if sessions run before submission, participation is processed on the basis of consent (Article 6(1)(a); the consent form and the survey's ethics note in Appendix A, which record consent as the lawful basis). This is the author's reading of the evaluation's position, not a completed assessment.

File paths in section C.6 refer to the CLARA implementation.

### C.2 Possible lawful basis (GDPR Article 6)

The lawful basis is the controller's determination. For a production deployment, the basis a controller is likely to consider for processing customer feedback is legitimate interest (Article 6(1)(f)) in improving products and service, which requires the controller's own three-part test (a legitimate interest, necessity of the processing for it, and a balance against the interests and fundamental rights of the data subjects) documented in its assessment; the safeguards of section C.6 are inputs to that balance, not a substitute for it. A controller may instead rely on a contractual or other basis its own analysis supports. No special-category data (Article 9) is sought or required, and the product does not ask for any.

### C.3 Description of the processing

System: the CLARA platform, a governed customer feedback-to-action workflow.

Processing: ingestion; model-assisted enrichment (sentiment, urgency, tag extraction, insight synthesis); approval-gated action routing; outcome measurement; and organisational learning records derived from customer feedback signals.

Data subjects:

- Customers whose feedback is ingested (support tickets, surveys, reviews, app-store comments).
- Employees of the deploying organisation who use the system: approvers, editors and admins. Their pseudonymous identities (a JWT-derived pseudonym) and their decisions are recorded on approval, execution and learning records. Because such records can be read as monitoring, the product ships a works-council pack with a no-individual-performance-monitoring attestation; the designated admin role still sees identities.

Data categories:

- Customer feedback text (may contain personal data: names, e-mail addresses, phone numbers).
- Customer identifiers (customer and account identifiers; pseudonymised in storage).
- Metadata: source, timestamp, journey stage, tags.
- Model-generated metadata: sentiment, urgency, severity, category, with a model score and stated limitations.
- Action records: connector push results (Jira issue keys, Slack message identifiers).
- Learning conclusions: reviewer-authored summaries with direct identifiers redacted.

### C.4 Necessity and proportionality (author's reading)

The table records the author's reading of why each purpose needs the processing and what bounds it. The controller's assessment must re-judge each row for its own purposes.

| Purpose | Necessity | Proportionality |
|---|---|---|
| Feedback triage | Needed to sort feedback for product improvement | The model processes text only; no profiling of individuals |
| Action routing | Needed to turn a theme into an owned, approved action | Human approval required for every action that leaves the system; the gate controls what leaves the system, not what the enrichment fails to surface (C.5) |
| Outcome measurement | Needed to check whether an approved action was followed by a change in the signal | Metrics are aggregate (signal rates over fixed intervals), not per individual |
| Learning | Needed to reuse conclusions across cycles | Conclusions carry redacted identifiers; reviewers appear by pseudonym |

### C.5 Risks to data subjects (author's identification)

Likelihood and impact are the author's estimates for a typical deployment and are to be re-rated by the controller.

| Risk | Likelihood | Impact | Mitigation in the product |
|---|---|---|---|
| Personal data in feedback text reaches the model provider | Medium (if a hosted model is used) | High | Pattern-based redaction of direct identifiers before any text reaches the model (enrichment and synthesis); a personal name in running text is not caught; a self-hosted or EU-resident model with the residency gate is recommended |
| Incorrect sentiment or urgency classification | Medium | Low (a person reviews before any action) | Model score (an uncalibrated heuristic) and limitations on every AI output. The approval gate controls wrong or harmful actions reaching an external system; it does not recover escalation-worthy signals the enrichment ranks too low (22 of 50 under the seed labels on the production rubric; Appendix B, Article 14 note) |
| Unauthorised access to feedback data | Low | High | Verified-login sessions with row-level security; workspace isolation; JWT verification |
| Feedback data retained beyond necessity | Low | Medium | A fixed 730-day expiry (`LEARNING_RETENTION_DAYS`) recorded on workflow records and learning conclusions at write time; no scheduled deletion is implemented, so deletion at expiry is the deployer's process |
| Model-generated insights misrepresent customer views | Medium | Medium | Human approval before action; evidence paraphrases attached to every insight |

### C.6 Technical safeguards implemented

1. Model placement. Self-hosted model support (Ollama, vLLM) removes the model-provider hop, and the fail-closed residency gate (`CLARA_AI_REQUIRE_EU=1`) refuses a provider the classifier cannot place in the EU or on the deployer's host. CLARA is hosted software, so feedback still leaves the customer's own infrastructure whichever model is chosen (Appendix B, data transfers).

2. Identifier redaction. `redact_common_pii()` in `apps/api/app/domain/models.py` redacts e-mail, phone, IP, account-identifier and street-address patterns from feedback text before it reaches the model (`services/enrichment.py`, `services/synthesis.py`) and from learning conclusions. The stored signal is unchanged; only the provider payload is minimised. It is pattern-based, not named-entity recognition.

3. Human-in-the-loop approval. No action that leaves the system (ticket, notification, segment) is executed without explicit human approval at the LangGraph approval interrupt; the dispatched payload is bound to the approved revision.

4. Data minimisation at the model boundary. Only the signal id and the redacted text are sent to the model; customer and account identifiers are pseudonymous in storage and never reach the model. Observability traces (Langfuse) carry the redacted prompt and are a processor relationship the deployer must cover.

5. Access control. Row-level security on all database tables; workspace isolation; JWT-based authentication with workspace scoping.

6. Audit trail. Every AI output carries audit metadata (model, source, limitations). Every approval and execution is an append-only workflow record with the connector type and result.

7. Retention limits. Workflow records and learning conclusions carry `retention_expires_at`, set at write time to 730 days after the record (a fixed code default, `LEARNING_RETENTION_DAYS` in `apps/api/app/domain/models.py`). No per-workspace setting and no scheduled deletion are implemented: the expiry is recorded, not enforced.

These are implemented controls; the approval and provenance controls among them are regression-tested (Chapter 4). They describe the build at the cited commits (§4.1; Appendix G.8): several of them, including identifier redaction at the model boundary, loop verdicts and the binding of dispatch to reviewed outbound content, were implemented and regression-tested in September 2026 and were not deployed at the time of writing. Whether they are sufficient for a given deployment is the conclusion of the controller's assessment, not of this document.

### C.7 Data-subject rights (GDPR Chapter III)

| Right | How the product supports it |
|---|---|
| Access and portability (Articles 15, 20) | Signals and derived records are workspace-scoped and queryable by subject identifier; export to CSV or JSON. |
| Rectification (Article 16) | Manual process: signals can be corrected by re-import; enrichment labels are not editable in the product and no correction feeds back to the classifier. |
| Erasure (Article 17) | Per-subject erasure deletes signals, journey events and context records and scrubs evidence excerpts inside draft problems and connector drafts in place; earlier evidence-pack hashes for affected problems no longer verify, and the endpoint reports this to the operator. Learning conclusions carry redacted identifiers from creation. |
| Restriction and objection (Articles 18, 21) | Manual process: there is no per-workspace processing-suspension switch; the deployer honours a restriction or objection by pausing ingestion and deleting the subject's records. |
| Automated-decision safeguards (Article 22) | No solely automated decision with legal or similarly significant effect on an individual; every action that leaves the system requires human approval. |
| Transparency (Articles 13 and 14; AI Act Article 50) | Model-generated outputs carry provenance metadata inside the product; machine-readable marking of exported drafts under Article 50(2) is the open item (Appendix B). |

### C.8 Residual risk: what the provider can and cannot conclude

The provider can state that the safeguards of section C.6 are implemented, that the redaction is pattern-based and misses names in running text, that hosted operation means feedback leaves the customer's infrastructure whichever model is chosen, and that tracing adds a processor. The provider cannot conclude that the residual risk to data subjects in a production deployment is low or acceptable; that conclusion is the controller's, reached against its actual model provider, connectors and retention configuration. Two design-level risks remain open on the author's reading: automation bias at the approval gate, which awareness alone is unlikely to counter (Laux & Ruschemeier, 2025; §6.2), and the exposure of the ingestion endpoints to machine-generated or coordinated feedback, which the threat model of §4.9 carries under the authenticity review with its residual risk stated. On the author's reading the assessed processing is not high-risk under the EU AI Act (Appendix B), which bears on the controller's judgement of whether Article 36 consultation is indicated but does not make it.

### C.9 Sign-off (for the deployer)

| Role | Name | Date |
|---|---|---|
| Data protection officer | _________________ | _______ |
| Controller representative | _________________ | _______ |
