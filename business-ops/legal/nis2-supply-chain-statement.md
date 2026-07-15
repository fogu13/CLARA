# CLARA — NIS2 / BSIG Supply-Chain Security Statement

_A vendor-side security-measures statement for customers that are in scope of NIS2 (Directive (EU) 2022/2555) as implemented in Germany by the amended **BSIG** (NIS2-Umsetzungsgesetz, in force since **6 December 2025**, bringing roughly 29,000 German entities into scope). In-scope customers must manage **supply-chain security** and will flow that duty down to SaaS vendors like CLARA via security questionnaires and contract clauses — this statement pre-answers them by mapping each expectation to CLARA's existing, documented measures._

> **DRAFT — have a German Fachanwalt (IT-Recht/Datenschutz) review before use.**
> This is a founder-drafted template, not legal advice, and creates no lawyer–client relationship. Review it in the **same Fachanwalt pass as the AVV/TOMs trust pack**. Every statement below must reflect controls that actually exist (see the "verify each control" rule in [toms.md](toms.md)) — overstating a measure to pass a questionnaire is a misrepresentation risk. Fill every `{{PLACEHOLDER}}` and re-verify the BSIG section numbering against the promulgated text before sending to a customer.

---

## 1. About this statement

CLARA (`{{LEGAL_ENTITY_NAME}}`, `{{ADDRESS}}`, Germany) provides an AI-assisted customer-feedback triage service (SaaS), hosted and operated in the EU/EEA. Customers that are **besonders wichtige** or **wichtige Einrichtungen** under **§ 28 BSIG** must implement risk-management measures under **§ 30 BSIG** — including **security of the supply chain** (§ 30 Abs. 2 Nr. 4 BSIG, mirroring Art. 21(2)(d) NIS2) — and therefore need documented assurance from their ICT suppliers.

This statement:

1. maps each § 30 Abs. 2 BSIG measure area to CLARA's **Technical & Organisational Measures** ([toms.md](toms.md)) rather than restating them — the TOMs remain the single source of truth;
2. states CLARA's **incident-notification SLA** with a concrete contact path and clock, aligned with the AVV so the two never contradict;
3. confirms the **audit-trail/export capability**, **EU data residency**, and **subprocessor change-notification** mechanics the questionnaires ask about.

**CLARA's own NIS2 status.** CLARA is currently a micro-enterprise below the size thresholds of § 28 BSIG / Art. 2 NIS2 and is therefore **not itself a registered in-scope entity** — this statement is supply-chain assurance for customers, not a claim of direct regulation. `{{VERIFY_WITH_COUNSEL — re-assess on growth or if the BSI's Betroffenheitsprüfung indicates otherwise}}`

---

## 2. Mapping — § 30 Abs. 2 BSIG expectations → CLARA measures

_Each row cites the governing TOMs section ([toms.md](toms.md)); the TOMs are the contractual security annex of the AVV ([avv-dpa.md](avv-dpa.md))._

| # | § 30 Abs. 2 BSIG measure area (≙ Art. 21(2) NIS2) | CLARA measure | Documented in |
|---|---|---|---|
| 1 | Risk analysis and information-system security policies | Risk-based security approach, information-security policies, TOMs review cycle | TOMs §5, §10 |
| 2 | Incident handling (Bewältigung von Sicherheitsvorfällen) | Incident-response runbook (triage → contain → eradicate → recover → notify → post-mortem), monitoring/alerting | TOMs §8, §4 |
| 3 | Business continuity: backup management, disaster recovery, crisis management | Encrypted EU backups, tested restores, PITR, documented DR runbook, RTO/RPO | TOMs §4 |
| 4 | **Supply-chain security** | Subprocessor due diligence at onboarding and annually, back-to-back Art. 28 contracts, full-liability flow-down, published register | TOMs §7; [subprocessor-list.md](subprocessor-list.md) |
| 5 | Security in acquisition, development and maintenance, incl. vulnerability handling | Version control with reviewed changes, dependency scanning, patch cadence, input validation; vulnerability reports to the security contact in §3 | TOMs §3.2, §4 (patch management), §5 |
| 6 | Assessing effectiveness of risk-management measures | Regular testing, access reviews, restore tests, documented findings/remediation | TOMs §5 |
| 7 | Cyber hygiene and training | Confidentiality obligations, security/data-protection awareness, endpoint security | TOMs §10, §2.2 |
| 8 | Cryptography and encryption | TLS in transit, encryption at rest (DB, storage, backups), key management, hashed credentials | TOMs §2.4 |
| 9 | Personnel security, access control, asset management | Need-to-know/least-privilege RBAC, per-workspace tenant isolation via Postgres RLS, logged staff access with break-glass procedure | TOMs §2.2, §2.3, §3.3 |
| 10 | Multi-factor or continuous authentication; secured communications | MFA required for all administrative/infrastructure access and offered to customer users; TLS-only communications | TOMs §2.2, §2.4 |

> **Drafting note (delete before sending):** the ten-item list above follows the § 30 Abs. 2 BSIG catalogue (which transposes Art. 21(2)(a)–(j) NIS2). Verify the exact statutory wording and numbering against the promulgated BSIG text at legal review, and confirm every cited TOMs row is filled in and true before this statement leaves the building.

---

## 3. Incident notification — SLA, contact path and clock

1. **What CLARA notifies.** Any security incident affecting the confidentiality, integrity or availability of a customer's data processed by CLARA — personal-data breaches (Art. 33(2) GDPR) and security incidents involving non-personal data alike.

2. **Clock.** CLARA notifies the affected customer **without undue delay** after becoming aware — target within **24 hours**, and in any event within the **`{{BREACH_NOTICE_HOURS, e.g. 48}}`-hour** deadline committed in **§8.2 of the AVV** ([avv-dpa.md](avv-dpa.md)) and TOMs §8. _Keep the placeholder value identical in all three documents — a mismatch is a standard audit finding._

3. **Why this matters to the customer.** An in-scope customer has its own reporting clocks to the BSI under **§ 32 BSIG** (early warning within **24 hours**, incident notification within **72 hours**, final report within **one month**). CLARA's prompt vendor notice, with phased follow-up as facts emerge (content per §8.2 of the AVV: nature, affected categories/volumes, likely consequences, measures taken), is designed to feed the customer's 24-hour early warning.

4. **Contact path.** Notifications go to the customer's designated contact via `{{DOCUMENTED_CHANNEL, e.g. email to the customer's security contact + status page}}`. Inbound, customers and researchers reach CLARA's security contact at:

| Role | Contact |
|---|---|
| Security contact (monitored) | `{{SECURITY_CONTACT_NAME}}` — `{{SECURITY_CONTACT_EMAIL}}` (same monitored address as in the [Impressum](impressum.md) / TOMs §0) |
| Escalation phone | `{{PHONE_NUMBER_REACHABLE}}` |
| Data-protection contact | `{{DPO_OR_DP_CONTACT}}` |

---

## 4. Audit trail and export capability

- CLARA keeps an **append-only, per-workspace audit trail** of security-relevant events (logins, permission changes, data access, exports, deletions), separated from application data (TOMs §2.3, §3.2).
- Customers can **export their audit trail and workspace data** self-service, in a structured, machine-readable format (TOMs §9; §11.2 of the AVV) — usable as evidence in the customer's own BSIG documentation and audits.
- Further compliance information (certifications of the hosting subprocessors, TIA documentation, sub-processor terms) is available under §9 of the AVV.

## 5. EU data residency

All processing and storage of customer data — including LLM inference inputs and backups — takes place **within the EU/EEA** (`{{HOSTING_LOCATION_EU_REGION}}`); see TOMs §1 and §6 and §§5.4/10.1 of the AVV. Any exception would appear in the subprocessor list with its Chapter V GDPR safeguard before it happens.

## 6. Subprocessor changes

CLARA gives **at least `{{NOTICE_PERIOD_DAYS}}` days' advance notice** of any new or replacement subprocessor, with a right to object and a termination remedy if an objection cannot be resolved — per **Section 4 of the published subprocessor list** ([subprocessor-list.md](subprocessor-list.md)), incorporated into the AVV. The same notice covers **location changes**, which also serves the DORA location-notice duty for fintech customers ([dora-ict-annex.md](dora-ict-annex.md), §4.2).

---

## 7. Document control

| Field | Value |
|---|---|
| Version | `{{VERSION}}` |
| Effective date | `{{EFFECTIVE_DATE}}` |
| Last updated | `{{LAST_UPDATED_DATE}}` |
| Last legal review | `{{LAST_LEGAL_REVIEW_DATE}}` by `{{REVIEWING_LAWYER}}` |
| Owner / contact | `{{SECURITY_CONTACT_EMAIL}}` |

---

### Sources (verify before sending)

- NIS2 — Directive (EU) 2022/2555, esp. Art. 21(2) (risk-management measures, incl. (d) supply-chain security): <https://eur-lex.europa.eu/eli/dir/2022/2555/oj>
- BSIG as amended by the German NIS2 implementation act (NIS2UmsuCG), in force 6 Dec 2025 — § 28 (entity categories), § 30 (Risikomanagementmaßnahmen, Abs. 2 Nr. 4 Lieferkette), § 32 (Meldepflichten: 24h/72h/1 month): <https://www.gesetze-im-internet.de/bsig/> — **verify section numbering against the promulgated text**
- BSI — NIS-2 information hub and Betroffenheitsprüfung (am-I-in-scope check): <https://www.bsi.bund.de/DE/Themen/Regulierte-Wirtschaft/NIS-2-regulierte-Unternehmen/nis-2-regulierte-unternehmen_node.html>
- Art. 33 GDPR (processor breach notification to the controller): <https://gdpr-info.eu/art-33-gdpr/>

_Cross-references within the CLARA pack: security measures in [toms.md](toms.md) (cited by section above — do not fork the content); breach-notice clock in [avv-dpa.md](avv-dpa.md) §8.2; subprocessor mechanics in [subprocessor-list.md](subprocessor-list.md); provider identity and monitored contact in [impressum.md](impressum.md); the DORA-side counterpart for fintech customers is [dora-ict-annex.md](dora-ict-annex.md)._
