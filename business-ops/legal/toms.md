# CLARA — Technical & Organisational Measures (TOMs)

_Annex to the Data Processing Agreement (Auftragsverarbeitungsvertrag / AVV) describing the technical and organisational measures CLARA implements as a **processor** pursuant to Art. 32 GDPR._

> **DRAFT — have a German Fachanwalt (IT-Recht/Datenschutz) review before use.**

---

## 0. About this document

| Field | Value |
|---|---|
| Document | Technical & Organisational Measures (TOMs) — Annex to the AVV |
| Provider (processor) | {{LEGAL_ENTITY_NAME}}, {{ADDRESS}}, {{COUNTRY}} |
| Product | CLARA — AI customer-feedback triage (SaaS) |
| Contact for security matters | {{SECURITY_CONTACT_NAME}} / {{SECURITY_CONTACT_EMAIL}} |
| Data protection contact | {{DPO_OR_DP_CONTACT}} |
| Version | {{VERSION}} |
| Effective date | {{EFFECTIVE_DATE}} |
| Last reviewed | {{LAST_REVIEW_DATE}} |
| Governs | Personal data contained in **customer feedback text** (app-store reviews, support tickets, survey responses, etc.) ingested into CLARA by the **customer (controller)** |

**Legal basis.** These measures are implemented and maintained pursuant to **Art. 32 GDPR (Security of processing)**, which requires the controller and processor to implement appropriate technical and organisational measures to ensure a level of security appropriate to the risk, "taking into account the state of the art, the costs of implementation and the nature, scope, context and purposes of processing as well as the risk of varying likelihood and severity for the rights and freedoms of natural persons." Art. 32 expressly names *pseudonymisation and encryption*, *ongoing confidentiality, integrity, availability and resilience*, *timely restoration of availability*, and *a process for regularly testing, assessing and evaluating* the effectiveness of the measures (Art. 32(1)(a)–(d)). ([Art. 32 GDPR – gdpr-info.eu](https://gdpr-info.eu/art-32-gdpr/))

**Scope note — controller vs. processor.** CLARA is a **processor** for personal data contained in ingested customer feedback (the customer is the **controller**). CLARA is an independent **controller** for its own website, marketing, and billing data; those processing activities are covered by CLARA's Datenschutzerklärung and are **out of scope** for this TOMs annex except where infrastructure is shared. This document describes the measures protecting **controller (customer) data processed on the controller's behalf**.

**"State of the art" is dynamic.** The measures below reflect current technology available on the market and are reviewed and updated over time; the concept of "state of the art" in Art. 32 cannot be fixed at a single point in time and must be re-assessed against technological progress. ([Art. 32 GDPR – gdpr-info.eu](https://gdpr-info.eu/art-32-gdpr/))

**How to use this template.** Replace every `{{PLACEHOLDER}}` with CLARA's actual details. Where a measure is *planned but not yet implemented* (e.g., "moving to EU hosting"), mark it clearly as a roadmap item with a target date rather than describing it as an existing control — misdescribing controls is itself a compliance and misrepresentation risk. Delete measures that do not apply and add any that are missing.

---

## 1. Overview of CLARA's processing environment

| Layer | Description (verify & complete) |
|---|---|
| Hosting / IaaS | {{CLOUD_PROVIDER, e.g. Hetzner / AWS eu-central-1 / OVHcloud}}, region **{{EU_REGION}}** (EU/EEA) |
| Application hosting / PaaS | {{APP_PLATFORM, e.g. Vercel (region), Fly.io, self-managed}} |
| Primary database | {{DB, e.g. Supabase Postgres / managed Postgres}}, region **{{DB_REGION}}** (EU/EEA) |
| Object / file storage | {{STORAGE, e.g. Supabase Storage / S3 eu-central-1}} |
| Multi-tenancy model | Logical isolation per **workspace/tenant**, enforced by Postgres **Row-Level Security (RLS)** |
| LLM inference | {{LLM_PROVIDER + API, e.g. Anthropic / OpenAI / Mistral}} via API, **no fine-tuning**, {{EU_ENDPOINT / zero-retention flag}} |
| Auth | {{AUTH, e.g. Supabase Auth / Clerk}}, {{MFA status}} |
| Secrets management | {{e.g. platform env vars / Vault / cloud KMS}} |
| Logging & audit | {{LOGGING_STACK}}, append-only audit log per workspace |
| Backups | {{BACKUP_MECHANISM}}, retention {{N}} days, region **{{BACKUP_REGION}}** (EU/EEA) |

> **Data-minimisation posture.** CLARA processes only the feedback text and metadata the customer chooses to ingest. The customer (controller) is responsible for the lawfulness of ingestion and for minimising direct identifiers before/at ingestion where feasible. CLARA supports {{PII_REDACTION_FEATURE?}} to reduce identifiers in transit to the LLM (see §2.5).

---

## 2. Confidentiality (Art. 32(1)(b))

### 2.1 Physical access control (Zutrittskontrolle)

CLARA operates **no own data centres**; physical security is provided by the sub-processor cloud/hosting providers under their certified controls.

| Measure | Implementation |
|---|---|
| Certified data centres | Hosting in {{CLOUD_PROVIDER}} facilities certified to {{ISO 27001 / SOC 2 / C5}}; certificates on file (§7.4) |
| Physical access | Managed by the hosting sub-processor: 24/7 security, access badges/biometrics, CCTV, visitor logs — per provider's TOMs/certifications |
| Provider TOMs on file | Sub-processor security documentation retained and reviewed at onboarding and {{annually}} |
| Founder workstation | Full-disk encryption ({{FileVault / LUKS}}), auto-lock, no controller data stored locally except transiently for support with customer authorisation |

> Because CLARA is cloud-native, physical access control is largely **inherited** from sub-processors. Reference their certifications rather than re-describing their measures.

### 2.2 System / logical access control (Zugangskontrol​le)

Controls preventing unauthorised persons from using CLARA's systems.

| Measure | Implementation |
|---|---|
| Authentication | {{Auth provider}}; passwords stored only as salted hashes ({{bcrypt/argon2}}); SSO/OIDC available for {{plan}} |
| Multi-factor authentication (MFA) | {{Enforced / available}} for CLARA staff (admin) and offered to customer users; **required** for all administrative/infrastructure access |
| Administrative access | Access to production infrastructure limited to {{named individuals — currently the founder}}; protected by MFA + {{hardware key / SSH keys}} |
| Session management | Short-lived tokens, secure/HttpOnly/SameSite cookies, idle timeout {{N}} min, forced re-auth for sensitive actions |
| Secrets & keys | Stored in {{secrets manager / KMS}}, never in source control; rotation policy {{cadence}}; `.env` files excluded via `.gitignore` |
| Network exposure | Databases and internal services not publicly exposed; access via {{private networking / allowlisted IPs / bastion}} |
| Endpoint security | Admin workstation: disk encryption, screen lock, OS auto-updates, {{EDR/AV}} |

### 2.3 Data access control (Zugriffskontrolle) & multi-tenant separation (Trennungskontrolle)

Controls ensuring users and staff can access only the data they are authorised for, and that tenants' data is kept strictly separate.

| Measure | Implementation |
|---|---|
| Per-workspace isolation | Every row of controller data carries a `workspace_id`; **Postgres Row-Level Security (RLS)** policies restrict every query to the authenticated workspace — enforced at the database layer, not only in application code |
| Role-based access control (RBAC) | Roles ({{owner / admin / member / viewer}}) scoped **within** a workspace; least-privilege by default |
| Tenant separation model | {{Shared schema with RLS / schema-per-tenant / DB-per-tenant}} — logical separation with defence-in-depth so one customer can never read another customer's feedback |
| Staff access to controller data | Minimised and role-gated; production data access by CLARA staff only for {{support/debugging}} with {{customer authorisation / break-glass}} procedure and is **logged** (§3.3) |
| Audit logging | Append-only audit trail of security-relevant events (logins, permission changes, exports, data access, deletions) per workspace, retained {{N}} days |
| Separation of environments | Production, staging and development are separated; **no real controller personal data in non-production environments** (synthetic/anonymised test data only) |
| Data export & deletion | Controller can export/delete its workspace data; deletion propagates to backups within the backup-retention window (§4) |

> **RLS is the primary tenant-isolation control.** Where feasible, RLS policies should be covered by automated tests that assert cross-tenant reads fail. Note the test approach in {{TESTING_REF}}.

### 2.4 Encryption (Verschlüsselung)

Encryption is an explicitly named measure under Art. 32(1)(a). ([Art. 32 GDPR – gdpr-info.eu](https://gdpr-info.eu/art-32-gdpr/))

| Data state | Measure |
|---|---|
| In transit — external | **TLS {{1.2+/1.3}}** for all connections (browser↔app, app↔DB, app↔LLM API, app↔sub-processors); HTTPS enforced (HSTS), no plaintext HTTP |
| In transit — internal | {{TLS / provider-managed encryption}} between application and database/storage |
| At rest — database | {{AES-256 at-rest encryption via managed DB / disk-level encryption}} |
| At rest — object storage | {{Provider-managed encryption at rest}} |
| At rest — backups | Backups encrypted at rest ({{mechanism}}) |
| Key management | Keys managed by {{provider KMS / managed service}}; application secrets in {{secrets manager}}; rotation {{cadence}} |
| Passwords/secrets | Never stored in plaintext; salted-hashed ({{argon2/bcrypt}}) |

### 2.5 Pseudonymisation & LLM-API data handling (Pseudonymisierung)

Pseudonymisation is expressly named in Art. 32(1)(a). Because feedback text may contain PII and is sent to a **third-party LLM API**, this is a focus area.

| Measure | Implementation |
|---|---|
| LLM provider role | CLARA is a downstream **AI-system deployer/provider using a frontier model via API without fine-tuning** — CLARA is **not** a GPAI provider. The LLM vendor acts as a **sub-processor** for feedback text sent for inference (§7) |
| No training on customer data | Contractual **no-training / zero-retention** terms with the LLM provider ({{Anthropic/OpenAI/Mistral — enterprise/API zero-retention tier}}); ingested feedback is **not** used to train or fine-tune any model. Verify and cite the exact contractual clause: {{DPA_REF}} |
| Data residency for inference | {{EU/regional inference endpoint if available}}; where inference occurs outside the EEA, an Art. 46 transfer mechanism applies (§6) |
| Minimisation before inference | Only the text needed for triage is sent; {{system prompts avoid echoing PII}}; {{no unnecessary metadata}} |
| Optional PII redaction | {{Automated detection/redaction or masking of direct identifiers (emails, phone numbers, names) before text is sent to the LLM — feature status: implemented/roadmap}} |
| Pseudonymisation in storage | {{Where feasible, identifiers stored separately from feedback content / referenced by internal IDs}} |
| Prompt/response logging | LLM request/response logging {{disabled / minimised / scrubbed}}; retention {{N}} days; access restricted per §2.3 |

> **Verify before use:** confirm the LLM provider's current data-handling tier, retention default, and whether an EU/regional endpoint is contracted. Retention and training defaults differ by provider and by API tier and change over time.

---

## 3. Integrity (Art. 32(1)(b))

### 3.1 Transfer control (Weitergabekontrolle)

Ensuring data cannot be read, copied, altered or removed without authorisation during transmission or transport.

| Measure | Implementation |
|---|---|
| Encrypted transmission | All data-in-transit encrypted via TLS (§2.4) |
| Controlled interfaces | Data leaves CLARA only via defined, authenticated interfaces: {{API, LLM sub-processor, export functions}} |
| Sub-processor transfers | Governed by Art. 28 DPAs and, where relevant, Art. 46 transfer mechanisms (§6, §7) |
| No uncontrolled media | No transfer of controller data to removable media; downloads/exports restricted and logged |
| Data-flow documentation | Data flows (ingestion → storage → LLM inference → results) documented in the Record of Processing / architecture doc {{REF}} |

### 3.2 Input control (Eingabekontrolle)

Ensuring it can be checked and established **whether and by whom** personal data has been entered, altered or removed.

| Measure | Implementation |
|---|---|
| Audit logging | Append-only logs record who created/modified/deleted/exported data, with timestamp and actor identity, per workspace |
| Immutability | Audit logs are {{append-only / tamper-evident}}; separate from application data |
| Retention | Audit logs retained {{N}} days, then rotated/deleted |
| Attribution | All write actions tied to an authenticated user or service identity (no shared accounts for staff) |
| Change management | Application changes via version control (git) with reviewed commits and deployment history |

### 3.3 Data-integrity & staff-access accountability

| Measure | Implementation |
|---|---|
| Referential integrity | Database constraints and application validation prevent corruption/cross-tenant references |
| Break-glass access | Staff access to production controller data uses a documented, logged {{break-glass}} procedure with justification |
| Input validation | Server-side validation and output encoding to mitigate injection/XSS; parameterised queries |

---

## 4. Availability & Resilience (Art. 32(1)(b), (c))

Art. 32 requires the ability to ensure ongoing **availability and resilience** and to **restore availability and access** to personal data in a timely manner after an incident. ([Art. 32 GDPR – gdpr-info.eu](https://gdpr-info.eu/art-32-gdpr/))

| Measure | Implementation |
|---|---|
| Backups | Automated backups of the database {{frequency, e.g. daily + PITR}}; retention {{N}} days; stored encrypted in **EU/EEA** region |
| Backup testing | Restores tested {{cadence, e.g. quarterly}}; results recorded |
| Point-in-time recovery | {{PITR window, e.g. 7 days}} via {{managed DB feature}} |
| Redundancy | {{Managed DB HA / multi-AZ / provider redundancy}}; application {{horizontally scalable / stateless}} |
| Recovery objectives | **RTO {{e.g. 24h}}**, **RPO {{e.g. 24h / near-zero with PITR}}** — verify against actual capability |
| Disaster recovery (DR) | Documented DR/runbook {{REF}}; recovery steps for loss of primary region/provider |
| Monitoring & alerting | Uptime and error monitoring ({{tool}}); alerts to on-call ({{founder}}) |
| Protection against loss | Managed infrastructure with provider-level durability guarantees; DDoS/edge protection via {{CDN/platform}} |
| Patch management | OS/dependencies kept current; security updates applied {{cadence}}; dependency scanning ({{Dependabot/etc.}}) |
| Capacity | {{Autoscaling / resource monitoring}} to maintain availability under load |

> **Solo-founder note.** Document a realistic on-call/escalation plan and, ideally, a documented recovery runbook a third party could follow, given single-operator risk. Consider a designated deputy/emergency contact {{NAME}}.

---

## 5. Procedures for regular review, evaluation & assessment (Art. 32(1)(d))

Art. 32(1)(d) requires **a process for regularly testing, assessing and evaluating** the effectiveness of technical and organisational measures. ([Art. 32 GDPR – gdpr-info.eu](https://gdpr-info.eu/art-32-gdpr/))

| Measure | Implementation |
|---|---|
| TOMs review cycle | These TOMs reviewed at least **{{annually}}** and upon material changes to systems, sub-processors, or risk |
| Risk assessment | Risk-based approach per Art. 32; {{DPIA where applicable — controller-led; CLARA supports per Art. 28(3)(f)}} |
| Security testing | {{Dependency/SAST scanning; periodic penetration test / vulnerability scan — status & cadence}} |
| Access reviews | Periodic review of who has access to production and admin systems ({{cadence}}) |
| Restore tests | Backup restores tested per §4 |
| Change control | Code review + version control + deployment logs (§3.2) |
| Vendor/sub-processor review | Sub-processor certifications and DPAs reviewed at onboarding and {{annually}} (§7) |
| Documentation | Findings and remediation tracked in {{issue tracker / security log}} |

> Consider whether an information-security framework (e.g. **BSI IT-Grundschutz**, **ISO/IEC 27001**, or **BSI C5**) is proportionate as CLARA grows — many DACH enterprise buyers expect it. Not legally mandatory for Art. 32 but strong evidence of "state of the art."

---

## 6. International data transfers (Art. 44–49)

| Measure | Implementation |
|---|---|
| Primary hosting | EU/EEA region(s): {{regions}} — no transfer for core storage/processing |
| Sub-processors outside EEA | Where any sub-processor (notably {{LLM_PROVIDER}}) processes data outside the EEA, transfers are covered by {{EU Standard Contractual Clauses (2021/914) / EU–US Data Privacy Framework certification}} plus, where needed, supplementary measures |
| LLM inference residency | {{EU/regional endpoint used where available; otherwise SCCs + supplementary measures + transfer impact assessment (TIA)}} |
| Transfer documentation | Transfer mechanisms and TIAs recorded {{REF}} |

> **Verify before use:** confirm each sub-processor's current transfer mechanism (SCC module, DPF certification status) and whether an EU endpoint removes the transfer entirely. DPF certification status per vendor must be checked, not assumed.

---

## 7. Sub-processor management (Art. 28)

Engagement of sub-processors is governed by **Art. 28(2) and (4) GDPR** (prior authorisation and flow-down of equivalent data-protection obligations).

| Measure | Implementation |
|---|---|
| Authorisation | Customer authorises listed sub-processors via the AVV; CLARA gives {{N}} days' notice of additions/changes and the customer may object ({{general written authorisation}} model) |
| Flow-down obligations | Each sub-processor bound by a written DPA imposing data-protection obligations **equivalent** to CLARA's under Art. 28 |
| Due diligence | Security posture, certifications, DPA and transfer mechanism reviewed before onboarding and {{annually}} |
| Register | Up-to-date list maintained and made available to the customer (see §7.1) |

### 7.1 Current sub-processors (complete & verify)

| Sub-processor | Purpose | Data processed | Location / region | Transfer mechanism | DPA on file |
|---|---|---|---|---|---|
| {{Hosting/IaaS provider}} | Infrastructure / hosting | All controller data (hosting) | {{EU region}} | EEA — n/a | {{link}} |
| {{Managed DB provider}} | Database / storage | Feedback text + metadata | {{EU region}} | EEA — n/a | {{link}} |
| {{LLM provider}} | AI inference / triage | Feedback text sent for analysis | {{region / EU endpoint}} | {{SCCs / DPF / EU endpoint}} | {{link}} |
| {{Auth provider}} | Authentication | Account identifiers | {{region}} | {{mechanism}} | {{link}} |
| {{Email/transactional}} | Notifications | Contact email + metadata | {{region}} | {{mechanism}} | {{link}} |
| {{Error/observability}} | Monitoring | {{scrubbed logs / metadata}} | {{region}} | {{mechanism}} | {{link}} |

> Keep this table synchronised with the AVV sub-processor annex and with CLARA's public sub-processor list, if maintained.

---

## 8. Incident & data-breach response (Art. 33 support)

As a **processor**, CLARA's core duty on a personal data breach is to **notify the controller without undue delay** after becoming aware of it (Art. 33(2) GDPR); the controller then assesses its own 72-hour notification duty to the supervisory authority (Art. 33(1)). ([Art. 33 GDPR – gdpr-info.eu](https://gdpr-info.eu/art-33-gdpr/))

| Measure | Implementation |
|---|---|
| Detection | Monitoring/alerting (§4); log review; sub-processor breach notifications |
| Notification to controller | CLARA notifies the affected controller **without undue delay** (target: within **{{24–48 hours}}** of becoming aware), via {{documented channel}} |
| Notification content | Nature of the breach, categories/approx. number of data subjects and records affected, likely consequences, and measures taken/proposed — to the extent known, in phases if necessary |
| Assistance to controller | CLARA assists the controller in meeting its Art. 33/34 obligations, per Art. 28(3)(f) |
| Documentation | All incidents documented (facts, effects, remedial action) to enable controller/authority verification (Art. 33(5)) |
| Response plan | Incident-response runbook {{REF}}: triage → contain → eradicate → recover → notify → post-mortem |
| Point of contact | Security contact: {{SECURITY_CONTACT_EMAIL}} |
| Review | Post-incident review to improve controls (feeds §5) |

> **Verify before use:** align the concrete notification timeline (e.g. "within 24 hours") with the wording in the signed AVV — the AVV's Art. 28(3)(f) clause governs, and the number here must match it.

---

## 9. Data return & deletion (Art. 28(3)(g))

| Measure | Implementation |
|---|---|
| During the term | Controller can export its workspace data ({{formats}}) and delete records/workspaces via the product |
| On termination | At the controller's choice, CLARA returns and/or deletes all controller personal data, and deletes existing copies, unless EU/Member-State law requires storage |
| Backup expiry | Deleted data purged from backups within the backup-retention window ({{N}} days); no indefinite retention |
| LLM provider | No controller data retained by the LLM sub-processor beyond {{zero-retention / N-day}} window (§2.5) |
| Confirmation | Deletion confirmed to the controller on request |

---

## 10. Organisational measures

| Measure | Implementation |
|---|---|
| Confidentiality obligations | All persons authorised to process controller data (currently {{the founder}}; future staff/contractors) bound by written confidentiality obligations (Art. 28(3)(b), 29, 32(4)) |
| Awareness/training | {{Security & data-protection awareness for staff/contractors}} |
| Policies | {{Information-security policy, access policy, backup policy, incident-response plan}} — {{status}} |
| Data protection by design & default | Privacy considered in feature design (Art. 25); RLS-by-default, minimisation, no real data in test |
| Records of processing | Art. 30(2) processor record maintained {{REF}} |
| Instruction-bound processing | Controller data processed only on documented instructions of the controller (Art. 28(3)(a)); AVV governs |

---

## 11. Change log

| Date | Version | Change | Author |
|---|---|---|---|
| {{DATE}} | {{VERSION}} | Initial draft | {{AUTHOR}} |

---

### Legal & drafting notes (delete before issuing)

- **Draft template only.** Have a German **Fachanwalt für IT-Recht / Datenschutzrecht** review before attaching to any AVV or sending to a customer. Misdescribing a control you do not actually have is both a data-protection and a misrepresentation risk.
- **Match the AVV.** §7 (sub-processors), §8 (breach timeline), §9 (deletion) must mirror the executed AVV (Art. 28 GDPR) exactly. This TOMs annex is subordinate to and referenced by that AVV.
- **Verify each control.** Every row marked "implemented" must reflect reality today; mark not-yet-built controls as roadmap items with target dates.
- **Language.** English primary is fine for cross-border EU B2B and for the AVV/TOMs. Note that some **CLARA-as-controller** documents have German-language requirements for German-facing use: **Impressum** (§5 DDG — note TMG was repealed 14 May 2024 and replaced by the DDG), **Datenschutzerklärung**, cookie consent (§25 TDDDG), and **AGB** for German customers. The TOMs itself has no statutory language requirement, but a German customer may request a German version.
- **State of the art evolves.** Re-review at least annually and on material change (Art. 32(1)(d)).
- **Frameworks.** Consider ISO/IEC 27001 or BSI C5 attestation as CLARA scales — frequently expected by DACH enterprise buyers and strong Art. 32 evidence, though not legally mandatory.

**Key sources:** [Art. 32 GDPR (Security of processing) – gdpr-info.eu](https://gdpr-info.eu/art-32-gdpr/) · [Art. 33 GDPR (Breach notification) – gdpr-info.eu](https://gdpr-info.eu/art-33-gdpr/) · [Art. 28 GDPR (Processor) – gdpr-info.eu](https://gdpr-info.eu/art-28-gdpr/)
