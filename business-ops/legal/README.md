# CLARA — Legal & Compliance Pack

Ready-to-use **draft templates** that make CLARA sellable to EU B2B (especially regulated
DACH) buyers. These operationalise `../01-compliance-gdpr-eu-ai-act.md`.

> ⚠️ **DRAFTS — not legal advice.** Each file is a founder-drafted template to hand to a German
> **Fachanwalt für IT-Recht/Datenschutz** for review, not a finished contract. Fill every
> `{{PLACEHOLDER}}` and get counsel to review — especially the AVV international-transfer mechanics
> and the AGB liability clauses (heavily constrained by German law) — **before** you sign a
> customer or publish the website.

## Contents

| File | Purpose | Language needed |
|------|---------|-----------------|
| [avv-dpa.md](avv-dpa.md) | Customer-facing Data Processing Agreement (Art. 28 GDPR) + Annexes | EN ok for cross-border; DE on request |
| [toms.md](toms.md) | Technical & Organisational Measures (Art. 32) — the DPA's security annex | EN |
| [subprocessor-list.md](subprocessor-list.md) | Published subprocessor list + change-notification clause | EN |
| [dora-ict-annex.md](dora-ict-annex.md) | DORA Art. 30 ICT-services annex to the AVV + pre-filled Register-of-Information vendor row (for fintech/financial-entity customers) | EN |
| [nis2-supply-chain-statement.md](nis2-supply-chain-statement.md) | NIS2/BSIG supply-chain security statement mapping § 30 BSIG expectations to the TOMs, with incident-notification SLA | EN |
| [betriebsrat-information.md](betriebsrat-information.md) | One-page works-council information sheet (§ 87 Abs. 1 Nr. 6 BetrVG) describing employee-data categories and the works-council mode — for the customer's co-determination process | **German required** |
| [impressum.md](impressum.md) | Website legal notice (§5 DDG) | **German required** |
| [datenschutzerklaerung.md](datenschutzerklaerung.md) | Website privacy policy (controller-side) | **German required** for DE visitors |
| [agb-b2b.md](agb-b2b.md) | B2B SaaS terms skeleton | **German** for DE customers; lawyer-review essential |

**In-product companions (X6 governance pack):** the `/compliance` page ships the audit-log
export, model card, Article 50 status card, and subprocessor/incident-contact card; the
**AI-Literacy Pack** (`/ai-literacy`, EU AI Act Art. 4 deployer duty) is a 5-screen in-product
module plus a printable pack stamped with workspace name and date — hand it to the customer's
compliance folder alongside this pack, and record the delivery attestation in the product.

## How to use
1. **Fill the `{{PLACEHOLDERS}}`** (your name/address, USt-IdNr, chosen subprocessors, price/term specifics).
2. **Pick real subprocessors** (LLM provider, EU hosting, MoR billing) and complete the subprocessor list + the transfer safeguards in the AVV.
3. **Send to counsel** for one review pass — this is the cheapest legal spend with the highest sales ROI (unblocks procurement/security reviews).
4. **Publish** Impressum + Datenschutzerklärung (German) on the site; keep the AVV + TOMs + subprocessor list in your sales data-room.

**Sequencing tip:** Impressum + Datenschutzerklärung go live with the website; the AVV/TOMs/subprocessor list are needed the moment a pilot moves to signature (weeks 3–6 of the 90-day plan). The DORA annex + NIS2 statement are needed the moment a fintech or NIS2-regulated buyer sends a security questionnaire — review them in the **same** Fachanwalt pass as the AVV/TOMs.
