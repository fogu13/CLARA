# EU AI Act and GDPR Mapping

## Document purpose and how to read the status column

This appendix maps the CLARA platform's design against the EU AI Act (Regulation (EU) 2024/1689, as amended by Regulation (EU) 2026/1744) and the GDPR. It is the author's reading, prepared as documentation for the thesis and as a starting point for a deployer's own assessment; it is not legal advice, and the product contains no automated legal assessment. Where the thesis says that the regulatory interpretation is documented (§1.7, Chapter 7), this appendix is that document.

The status column distinguishes three things:

- **Applicable**: an obligation that binds this artifact or its deployer on the classification below (Article 4, Article 5, Article 50(2) where engaged, and the GDPR).
- **Voluntarily aligned**: a Chapter III requirement written for high-risk systems (Articles 8 to 15 bind providers of high-risk systems through Article 16; Article 17 likewise). This artifact is not high-risk, so these articles do not bind it. The design adopts their substance as commitments, in the spirit of the codes of conduct the Act invites for other systems (Article 95). "Voluntarily aligned" therefore records a design fact, not a compliance claim.
- **Manual process**: a right or safeguard the deployer can honour, but which the product does not automate.

Rows describe the build at the cited commits (§4.1; Appendix G.8). Several mechanisms, including identifier redaction at the model boundary, loop verdicts and the binding of dispatch to reviewed outbound content, were implemented and regression-tested in September 2026 and were not deployed at the time of writing, so a row records what the build contains, not what the running service enforced on that date.

## Risk classification

### Not Annex III high-risk, on the author's reading

The platform is a customer-feedback triage and action-routing tool. Annex III covers biometric identification and categorisation, critical infrastructure, education and vocational training, employment and worker management, access to essential private and public services, law enforcement, migration and the administration of justice. The platform's outputs are internal operational routing (a backlog item, an owner, a priority) with a human approval before any action leaves the system; it makes no decision about an identified individual's access to anything. The classification should be re-examined if a deployer uses it in an employment or worker-management context (approval records name their reviewer by pseudonym and can be read as monitoring; a works agreement may be needed; §4.4), in an essential-service context, or to make automated decisions with significant effects on individuals.

### Sentiment analysis is not "emotion recognition" under the Act

An "emotion recognition system" is defined (Article 3(39)) as one that identifies or infers emotions or intentions of natural persons on the basis of their biometric data. Text-based sentiment analysis of customer feedback processes no biometric data, so it sits outside both the Article 5(1)(f) prohibition (workplace and education contexts) and the Annex III entry. This reading should be re-examined if the platform ever ingests voice or video feedback, where the biometric qualifier could be met.

### Article 50, paragraph by paragraph

Article 50 is the transparency article most often cited for systems like this one, and it has to be read by paragraph rather than as a whole. Each paragraph binds a different role (provider or deployer) and is engaged by a different kind of output, so the question for each is which role CLARA or its deployer plays and what output the paragraph is about, not whether the deployer publishes anything.

| Paragraph | Who it binds | Engaged by this artifact? |
|---|---|---|
| 50(1): systems intended to interact directly with natural persons must make that apparent | Providers | Not engaged. The system's users are workspace staff who know they are using an AI-assisted tool; it does not converse with customers. |
| 50(2): systems, including general-purpose systems, that generate synthetic audio, image, video or text must have their outputs marked in a machine-readable format and detectable as artificially generated or manipulated | Providers | Potentially engaged. This is a provider-side marking duty on synthetic text output. It is assessed by the output the system generates and by the role of the party that places the system on the market, not by whether the deployer later publishes the text. CLARA drafts text (insight summaries, ticket and message drafts), so CLARA as the provider of a system that drafts text is potentially engaged. The duty is subject to the Act's own exceptions in the same paragraph (an assistive function for standard editing, output that does not substantially alter the deployer's input data or its semantics, and uses authorised by law for criminal offences); the author does not assume that a ticket or message drafted from an insight summary falls within the assistive-editing exception, so the exception is not relied on. In the product, the audit block on every AI output records provenance (model, source, stated limitations); machine-readable marking of exported drafts, in the sense the paragraph requires, is the open item. The Omnibus grace period for this paragraph (below) applies only to systems already on the market before 2 August 2026. The platform has been in production since July 2026 (§4.1), so on the author's reading the grace period to 2 December 2026 applies to it and the open item is dated accordingly; a deployer's own assessment decides whether its use of the platform falls within that reading. |
| 50(3): emotion recognition and biometric categorisation systems must inform the persons exposed | Deployers | Not engaged (see above: no biometric data). |
| 50(4): deployers of deep fakes must disclose them; deployers of systems that generate or manipulate text published with the purpose of informing the public on matters of public interest must disclose that the text is artificially generated or manipulated (subject to the paragraph's exceptions for human review and editorial responsibility) | Deployers | Not engaged. This is the deployer-side disclosure for public-interest text. An internal ticket, a backlog item or a Slack message to a team channel is not text published to inform the public on a matter of public interest, and the platform generates no image, audio or video content. A deployer that took a CLARA draft and published it for that purpose would engage the paragraph on its own account. |

### The Digital Omnibus (Regulation (EU) 2026/1744)

The Commission's Digital Omnibus on AI, agreed politically on 7 May 2026, was adopted as Regulation (EU) 2026/1744, published in the Official Journal on 24 July 2026 (European Parliament and Council of the European Union, 2026). It postponed the Annex III high-risk obligations from 2 August 2026 to 2 December 2027 and the Annex I product-safety obligations to 2 August 2028; the Article 50 transparency obligations stayed on their 2 August 2026 schedule, with a short grace period, to 2 December 2026, for the Article 50(2) marking duty on systems already on the market (Council of the European Union, 2026, for the agreement; the dates are those of the enacted text, European Parliament and Council of the European Union, 2026, as the earlier readings of Gibson Dunn, 2026, and Latham & Watkins, 2026, anticipated). It also softened Article 4: the duty on providers and deployers changed from ensuring, to their best extent, a sufficient level of AI literacy to "taking measures to support the development of AI literacy", and the new Article 4(1) adds that the obligation "does not require providers or deployers to guarantee any specific level of AI literacy of any individual", an obligation of effort rather than of result. None of the postponed obligations bound this artifact (it is not high-risk); the amended Article 4 and Article 50(2) are the provisions that matter here.

## EU AI Act, article by article

### Article 4: AI literacy (applicable)

| Requirement | Platform implementation | Status |
|---|---|---|
| Providers and deployers shall take measures to support the development of AI literacy among their staff and other persons dealing with the system on their behalf (as amended by Regulation (EU) 2026/1744) | An in-product AI-literacy module (EN and DE) explains the system's capabilities and limits, including that the displayed model score is an uncalibrated heuristic blending a model self-report with volume and source counts, not a validated probability. The product copy says that the module supports the deployer's Article 4 programme, not that it discharges the duty: the module records only a workspace-level pack-delivery attestation and no per-user completion tracking, so it supports, and does not discharge, the deployer's own obligation | Applicable; implemented as a support |

### Article 5: prohibited practices (applicable)

| Requirement | Platform implementation | Status |
|---|---|---|
| No subliminal, manipulative or deceptive techniques that materially distort behaviour (5(1)(a)); no exploitation of vulnerabilities due to age, disability or a specific social or economic situation (5(1)(b)) | The action layer proposes internal operational actions and drafts; customer-facing action classes carry a blocking policy check, and every action requires a human approval. A churn-risk segment is not a vulnerability group under 5(1)(b), but the house policy is stricter than the prohibition: no manipulative or exploitative outreach at all (§4.9) | Applicable; design constraint |

### Article 14: human oversight (voluntarily aligned; binds high-risk systems)

| Requirement | Platform implementation | Status |
|---|---|---|
| Designed to allow human oversight | A LangGraph `interrupt()` at the approval node: the graph pauses; a person reviews and approves or rejects | Voluntarily aligned |
| A natural person has the technical capability to oversee | Every action (Jira tickets, Slack messages) requires explicit approval in the UI; the reviewer's identity is bound to the verified login (a JWT-derived pseudonym); an opt-in, admin-only four-eyes workspace flag requires two distinct approvers, holds execution after the first approval, rejects self-confirmation and resets on rejection | Voluntarily aligned |
| The person can disregard or override the output | Any proposed action can be rejected; rejection routes to END and nothing executes | Voluntarily aligned |
| The person can interrupt or stop the system | The graph stops at the approval interrupt; there is no path to an external effect without an approval record | Voluntarily aligned |

The approval gate controls false positives, that is, wrong or harmful actions reaching an external system. It cannot recover escalation-worthy signals that the enrichment ranks too low (22 of 50 under the seed labels on the production rubric, §5A.4.2); a signal the pipeline never surfaces as a candidate is never placed before an approver. Oversight of the action layer is therefore not oversight of the enrichment layer, and the Article 14 rows above should be read with that limit.

### Article 12: record-keeping (voluntarily aligned)

| Requirement | Platform implementation | Status |
|---|---|---|
| Automatic recording of events over the system's lifetime | A telemetry stream of typed events (candidate acceptance, approval decisions, executions, measurement checkpoints, loop verdicts; no person identifier on any row); Langfuse traces every model call; approval decisions are append-only workflow records carrying the reviewer's pseudonym and the canonical sha256 hash of the evidence pack as it stood before the decision, stable across re-exports, so whether the pack an approver saw has since changed is provable, except where a per-subject erasure has since scrubbed evidence in place, after which earlier hashes for the affected problems no longer verify and the erasure endpoint reports this to the operator (Appendix C.7); audit records export to CSV | Voluntarily aligned |
| Logs kept for a period appropriate to the purpose | Workflow records and learning conclusions carry `retention_expires_at`, set at write time to 730 days after the record (a fixed code default, `LEARNING_RETENTION_DAYS`); no per-workspace setting and no scheduled deletion are implemented, so the expiry is recorded, not enforced | Voluntarily aligned; expiry recorded, enforcement is a manual process |

### Article 15: accuracy, robustness and cybersecurity (voluntarily aligned)

| Requirement | Platform implementation | Status |
|---|---|---|
| An appropriate level of accuracy, declared | An evaluation harness scores classification against a 100-item bilingual golden set that is a development and validation benchmark co-developed with the artifact, not independent confirmation (provenance in Appendix G.2; disclosed in the model card). The published snapshot (6 September 2026, GLM-5.2, n = 100) reports sentiment 99% (0.95–1.00) and urgency 91% (0.84–0.95). The thesis's own 188-signal harness scores the production stage on both models against star-rating and seed-label references; neither gold standard is human-labelled, and the figures, including the production stage's shift relative to the seed risk labels, are in §5A.4.2 and §5A.7. Metrics are committed only through an explicit `--publish` step, served at `GET /model-card/metrics` and rendered in the product's model card; the hallucination heuristic is English-scope only by construction and says so | Voluntarily aligned |
| Resilience to errors, faults and inconsistencies | Enrichment batch failures are logged and skipped (partial enrichment rather than none); connector failures are recorded on the execution and never fail the approval; the ITS estimator refuses to fit below its minimum data requirements (10 pre-days, 5 post-days) rather than report an unsupported interval | Voluntarily aligned |
| Model output treated as untrusted | Every model response passes a sanitiser that coerces enums, clips scores and drops items naming ids outside the batch; an injection guard keeps customer text in the data lane; evidence, model score and limitations accompany every AI claim | Voluntarily aligned |

### Article 17: quality management (voluntarily aligned)

| Requirement | Platform implementation | Status |
|---|---|---|
| A quality management system | Evaluation harness, golden set and CI (`npm run check`); tests cover the pipeline end to end, including a walker test that calls every read endpoint as a non-admin and fails if a person-capable field leaks | Voluntarily aligned |
| Risk management | Policy rules whose blocking checks withhold approval; identifier redaction before model calls and in learning conclusions; the threat model of §4.9 | Voluntarily aligned |

## GDPR

### Article 5: principles relating to processing

| Principle | Implementation | Status |
|---|---|---|
| Lawfulness, fairness, transparency | AI outputs carry audit metadata; every action needs a human approval; the model score is labelled a heuristic. The lawful basis itself is the controller's determination (Appendix C) | Applicable; implemented on the product side |
| Purpose limitation | Signals are processed for feedback triage and action routing; no secondary use, no profiling of individuals | Applicable; implemented |
| Data minimisation | Direct identifiers (e-mail addresses, phone numbers, IP addresses, account identifiers, street addresses) are redacted from feedback text before it reaches the model in enrichment and synthesis, and from learning conclusions; the redaction is pattern-based, not named-entity recognition, so a personal name in running text is not caught | Applicable; implemented (pattern-based) |
| Accuracy | Model score and limitations on every AI claim; human approval before any action leaves the system; enrichment labels are not editable in the product, so a wrong label is corrected by re-import (Appendix C) | Applicable; implemented with a manual correction path |
| Storage limitation | Workflow records and learning conclusions carry `retention_expires_at`, set at write time to 730 days after the record (a fixed code default, `LEARNING_RETENTION_DAYS`); no per-workspace setting and no scheduled deletion are implemented, so deletion at expiry is the deployer's process | Applicable; expiry recorded, enforcement is a manual process |
| Integrity and confidentiality | Row-level security enabled and forced on every table, tenant-first keys, workspace isolation, verified-login sessions, encrypted connector secrets | Applicable; implemented |

### Articles 13 to 15 and 22: information rights and automated decisions

The platform makes no decision producing legal or similarly significant effects on an individual, so Article 22 is not engaged; the approval interrupt keeps it that way by construction. The information rights (Articles 13 to 15) fall to the deployer as controller; the audit records and exports give the deployer the material to answer them. Article 22 carries no "explainability" requirement of its own, and none is claimed from it.

### Data transfers and the model hop

A deployment's data-protection position depends on where the model runs and where the traces go. CLARA is hosted software (API on a European VPS, database in an EU region, front end on Vercel), so customer feedback leaves the customer's own infrastructure whichever model is chosen; a self-hosted model (Ollama or vLLM) removes the model-provider hop, and the fail-closed residency gate (`CLARA_AI_REQUIRE_EU=1`) refuses a provider the classifier cannot place in the EU or on the deployer's host. Langfuse tracing is itself a processor relationship that the deployer's DPIA must cover. None of this eliminates transfer questions; it scopes them to the hosting, tracing and model-provider arrangements a deployer chooses and documents (Appendix C).
