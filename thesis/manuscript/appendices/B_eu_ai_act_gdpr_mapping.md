# EU AI Act and GDPR Mapping

## Document purpose and how to read the status column

This appendix maps the CLARA platform's design against the EU AI Act (Regulation (EU) 2024/1689, as amended by Regulation (EU) 2026/1744) and the GDPR. It is the author's reading, prepared as documentation for the thesis and as a starting point for a deployer's own assessment; it is not legal advice and the product contains no automated legal assessment (§4.4).

The status column distinguishes three things that the earlier draft of this appendix ran together:

- **Applicable**: an obligation that binds this artifact or its deployer on the classification below (Article 4, Article 5, Article 50(2) where engaged, and the GDPR).
- **Voluntarily aligned**: a Chapter III requirement written for *high-risk* systems (Articles 8–15 bind providers of high-risk systems through Article 16; Article 17 likewise). This artifact is not high-risk, so these articles do not bind it. The design adopts their substance as commitments, in the spirit of the codes of conduct the Act invites for other systems (Article 95). "Voluntarily aligned" therefore records a design fact, not a compliance claim.
- **Manual process**: a right or safeguard the deployer can honour, but which the product does not automate.

## Risk classification

### Not Annex III high-risk, on the author's reading

The platform is a customer-feedback triage and action-routing tool. Annex III covers biometric identification and categorisation, critical infrastructure, education and vocational training, employment and worker management, access to essential private and public services, law enforcement, migration and the administration of justice. The platform's outputs are internal operational routing (a backlog item, an owner, a priority) with a human approval before any action leaves the system; it makes no decision about an identified individual's access to anything. The classification should be re-examined if a deployer uses it in an employment or worker-management context (the works-council pack of §4.4 exists because approval records can be read as monitoring, §87(1) Nr. 6 BetrVG), in an essential-service context, or to make automated decisions with significant effects on individuals.

### Sentiment analysis is not "emotion recognition" under the Act

An "emotion recognition system" is defined (Article 3(39)) as one that identifies or infers emotions or intentions of natural persons **on the basis of their biometric data**. Text-based sentiment analysis of customer feedback processes no biometric data, so it sits outside both the Article 5(1)(f) prohibition (workplace and education contexts) and the Annex III entry. This reading should be re-verified if the platform ever ingests voice or video feedback, where the biometric qualifier could be met.

### Article 50, paragraph by paragraph

Article 50 is the transparency article most often cited for systems like this one, and it has to be read by paragraph rather than as a whole:

| Paragraph | Who it binds | Engaged by this artifact? |
|---|---|---|
| 50(1): systems intended to interact directly with natural persons must make that apparent | Providers | **Not engaged.** The system's users are workspace staff who know they are using an AI-assisted tool; it does not converse with customers. |
| 50(2): systems generating synthetic audio, image, video or text must mark outputs as artificially generated in a machine-readable, detectable way | Providers | **Potentially engaged.** The system drafts text (insight summaries, ticket and message drafts). Where a deployer publishes such text, the provider-side marking duty applies; the audit block on every AI output records provenance, and machine-readable marking of exported drafts is the open item. The Omnibus grace period for this paragraph (below) applies only to systems already on the market before 2 August 2026. |
| 50(3): emotion recognition and biometric categorisation systems must inform the persons exposed | Deployers | **Not engaged** (see above: no biometric data). |
| 50(4): deep fakes; and text published with the purpose of informing the public on matters of public interest must be disclosed as AI-generated | Deployers | **Not engaged.** An internal ticket, a backlog item or a Slack message is not text published to inform the public on a matter of public interest. |

### The Digital Omnibus (Regulation (EU) 2026/1744)

The Commission's Digital Omnibus on AI, agreed politically on 7 May 2026, was adopted as Regulation (EU) 2026/1744, published in the Official Journal on 24 July 2026 and in force from 27 July 2026. It postponed the Annex III high-risk obligations from 2 August 2026 to 2 December 2027 and the Annex I product-safety obligations to 2 August 2028; the Article 50 transparency obligations stayed on their 2 August 2026 schedule, with a short grace period, to 2 December 2026, for the Article 50(2) marking duty on systems already on the market (Council of the European Union, 2026, for the agreement; the dates are those of the enacted text, whose Article 1, points (39)(b) and (40)(b), insert Article 111(4) and replace Article 113, third paragraph, point (c), of the Act, as the earlier readings of Gibson Dunn, 2026, and Latham & Watkins, 2026, anticipated). It also softened Article 4 (Article 1, point (5)): the duty on providers and deployers changed from ensuring, to their best extent, a sufficient level of AI literacy to **taking measures to support the development of AI literacy**, and the new Article 4(1) adds that the obligation "does not require providers or deployers to guarantee any specific level of AI literacy of any individual", an obligation of effort rather than of result. None of the postponed obligations bound this artifact (it is not high-risk); the amended Article 4 and Article 50(2) are the provisions that matter here.

## EU AI Act, article by article

### Article 4: AI literacy (applicable)

| Requirement | Platform implementation | Status |
|---|---|---|
| Providers and deployers shall take measures to support the development of AI literacy among their staff and other persons dealing with the system on their behalf (as amended by Regulation (EU) 2026/1744) | An in-product AI-literacy module (EN + DE) explains the system's capabilities and limits, including that the displayed "model score" (renamed from "confidence") is an uncalibrated heuristic blending an LLM self-report with volume and source counts, not a validated probability. The product copy was corrected from "discharges your team's AI-literacy duty" to "**supports your Article 4 programme**": the module records only a workspace-level pack-delivery attestation and deliberately no per-user completion tracking, so it supports, and does not discharge, the deployer's own obligation | **Applicable; implemented as a support** |

### Article 5: prohibited practices (applicable)

| Requirement | Platform implementation | Status |
|---|---|---|
| No subliminal, manipulative or deceptive techniques that materially distort behaviour (5(1)(a)); no exploitation of vulnerabilities due to age, disability or a specific social or economic situation (5(1)(b)) | The action layer proposes internal operational actions and drafts; customer-facing action classes carry a blocking policy check, and every action requires a human approval. A churn-risk segment is not a vulnerability group under 5(1)(b), but the house policy is stricter than the prohibition: no manipulative or exploitative outreach at all (§4.9) | **Applicable; design constraint** |

### Article 14: human oversight (voluntarily aligned; binds high-risk systems)

| Requirement | Platform implementation | Status |
|---|---|---|
| Designed to allow human oversight | LangGraph `interrupt()` at the approval node: the graph pauses; a person reviews and approves or rejects | Voluntarily aligned |
| A natural person has the technical capability to oversee | Every action (Jira tickets, Slack messages) requires explicit approval in the UI; the reviewer's identity is bound to the verified login (a JWT-derived pseudonym), replacing the earlier self-asserted request-body identity; an opt-in, admin-only **four-eyes** workspace flag requires two distinct approvers, holds execution after the first approval, rejects self-confirmation and resets on rejection | Voluntarily aligned |
| The person can disregard or override the output | Any proposed action can be rejected; rejection routes to END and nothing executes | Voluntarily aligned |
| The person can interrupt or stop the system | The graph stops at the approval interrupt; there is no path to an external effect without an approval record | Voluntarily aligned |

### Article 12: record-keeping (voluntarily aligned)

| Requirement | Platform implementation | Status |
|---|---|---|
| Automatic recording of events over the system's lifetime | A telemetry stream of about twenty-five event types (candidate acceptance, approval decisions, executions, measurement checkpoints, loop verdicts; no person identifier on any row); Langfuse traces every model call; approval decisions are **append-only** workflow records carrying the reviewer's pseudonym and the canonical sha256 hash of the evidence pack as it stood pre-decision, stable across re-exports, so whether the pack an approver saw has since changed is provable; audit records export to CSV | Voluntarily aligned |
| Logs kept for a period appropriate to the purpose | Workflow records and learning conclusions carry `retention_expires_at` (730 days by default, configurable) | Voluntarily aligned |

### Article 15: accuracy, robustness and cybersecurity (voluntarily aligned)

| Requirement | Platform implementation | Status |
|---|---|---|
| An appropriate level of accuracy, declared | An evaluation harness scores classification against a 100-item bilingual golden set (72 EN / 28 DE; both strata authored in the repository, the German stratum adversarially verified; disclosed in the model card). Published snapshot (6 September 2026, production prompt configuration, model GLM-5.2, n = 100): sentiment 99% (95% Wilson interval 0.95–1.00), urgency 91% (0.84–0.95), tag F1 fuzzy 78.7%; held-out half (n = 30) 96.7% / 93.3%, accuracies of the same exemplars-on configuration on a validation split that has been scored on every run (§5A.7); per language: EN (n = 72) 100% / 93.1%, DE (n = 28) 96.4% / 85.7%; the 18 July snapshot it replaces read 97% / 90% / 82.7%. The configured production model scores 95% / 82% on the same set (not published). The thesis's own 188-signal harness scores a *generic* triage prompt on the same model at 0.86 sentiment accuracy against a star-rating gold (§5A), and the production enrichment stage itself at 0.83 (GLM-5.2) and 0.84 (the configured production default, Mistral Small 4) on sentiment and 0.50 and 0.59 on four-level risk, where the production urgency rubric labels one level below the seed risk labels; the uneven capability is published, not smoothed (§5A.4.2). Metrics are committed only through an explicit `--publish` step, served at `GET /model-card/metrics` and rendered in the product's model card; the hallucination heuristic is English-scope only by construction and says so | Voluntarily aligned; the published figures are GLM-5.2's, and the configured production model has been run on both gold sets (§5A.4.2, §5A.7, §6.4) |
| Resilience to errors, faults and inconsistencies | Enrichment batch failures are logged and skipped (partial enrichment rather than none); connector failures are recorded on the execution and never fail the approval; the ITS estimator refuses to fit rather than report an unsupported interval | Voluntarily aligned |
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
| Lawfulness, fairness, transparency | AI outputs carry audit metadata; every action needs a human approval; the model score is labelled a heuristic | Applicable; implemented |
| Purpose limitation | Signals are processed for feedback triage and action routing; no secondary use, no profiling of individuals | Applicable; implemented |
| Data minimisation | Direct identifiers (e-mail addresses, phone numbers, IP addresses, account identifiers, street addresses) are redacted from feedback text before it reaches the model in enrichment and synthesis, and from learning conclusions; the redaction is pattern-based, not named-entity recognition, so a personal name in running text is not caught | Applicable; implemented (pattern-based) |
| Accuracy | Model score and limitations on every AI claim; human validation before action | Applicable; implemented |
| Storage limitation | Retention dates on workflow records and learning conclusions (730 days by default, configurable) | Applicable; implemented |
| Integrity and confidentiality | Row-level security enabled and forced on every table, tenant-first keys, workspace isolation, verified-login sessions, encrypted connector secrets | Applicable; implemented |

### Articles 13–15 and 22: information rights and automated decisions

The platform makes no decision producing legal or similarly significant effects on an individual, so Article 22 is not engaged; the approval interrupt keeps it that way by construction. The information rights (Articles 13–15) fall to the deployer as controller; the audit records and exports give the deployer the material to answer them. Article 22 carries no "explainability" requirement of its own, and none is claimed from it.

### Data transfers and the model hop

A deployment's data-protection position depends on where the model runs and where the traces go. CLARA is hosted software (API on a European VPS, database in an EU region, front end on Vercel), so customer feedback leaves the customer's own infrastructure whichever model is chosen; a self-hosted model (Ollama/vLLM) removes the *model-provider* hop, and the fail-closed residency gate (`CLARA_AI_REQUIRE_EU=1`) refuses a provider the classifier cannot place in the EU or on the deployer's host. Langfuse tracing is itself a processor relationship that the deployer's DPIA must cover. None of this "eliminates" transfer questions; it scopes them to the hosting, tracing and model-provider arrangements a deployer chooses and documents (Appendix C).
