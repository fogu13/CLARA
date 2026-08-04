# CLARA — Business Ops

The business/commercial side of CLARA (the AI customer-feedback triage engine): how to
set up cleanly in Berlin, stay compliant, and go to market fast in DACH/EU B2B.

_Compiled 2026-07-01 from live web research (5 research agents → source-cited drafts).
Founder context assumed: solo technical founder, Berlin, currently **Freiberufler + USt-IdNr**,
taking CLARA to market as a B2B SaaS. Correct any assumption and I'll revise._

> ⚠️ **Not legal, tax, or financial advice.** These are research-backed operational documents,
> not professional advice, and create no advisor relationship. German Freiberufler-vs-Gewerbe
> classification, GDPR/AI-Act specifics, and figures/deadlines are fact-specific and change —
> confirm with a **Steuerberater** and an **IT-/Datenschutz-Rechtsanwalt** before you rely on
> anything here, ideally **before you issue the first CLARA invoice or sign the first contract.**

---

## The documents

| # | Doc | What it gives you |
|---|-----|-------------------|
| 00 | [Business & Tax Setup (Berlin)](00-business-setup-berlin.md) | The Freiberufler-vs-**Gewerbe** decision, registrations, VAT, e-invoicing, entity choice, a Done/To-do checklist |
| 01 | [Compliance: GDPR + EU AI Act](01-compliance-gdpr-eu-ai-act.md) | Processor role, the AVV/DPA + TOMs + subprocessor pack, AI-Act classification & obligations, required legal pages |
| 02 | [Go-To-Market Strategy](02-gtm-strategy.md) | Positioning, ICPs, competitive wedge, messaging, channels, sales motion |
| 03 | [Business Requirements (BRD)](03-business-requirements.md) | Business model, KPIs, personas, PMF hypotheses, revenue roadmap, risks |
| 04 | [90-Day Go-To-Market Plan](04-90-day-go-to-market-plan.md) | Week-by-week execution to first paying customers; the pilot/design-partner offer |
| 05 | [Pricing & Financial Model](05-pricing-and-financial-model.md) | Hybrid tiers with DACH price points, EU-VAT billing, unit economics incl. LLM cost, runway |
| 06 | [Business Plan](06-business-plan.md) | Investor/bank-grade full plan: market sizing, financials, funding ask, roadmap, risks |
| 07 | [Marketing Plan](07-marketing-plan.md) | 12-month plan: messaging house, personas, channels, content calendar, KPIs |

### Pitch & fundraising — `pitch/`

The customer- and investor-facing kit. Start with the deck + executive summary; keep the FAQ and
data-room checklist ready for investor conversations, and the sales one-pager + outbound sequence
for customer pitching.

| Artifact | For |
|----------|-----|
| [pitch-deck.pptx](pitch/pitch-deck.pptx) · [.md](pitch/pitch-deck.md) | **14-slide deck** (editable PowerPoint + markdown source with speaker notes) |
| [executive-summary.md](pitch/executive-summary.md) | One-page teaser (investor + customer) |
| [sales-one-pager.md](pitch/sales-one-pager.md) | Customer-facing leave-behind |
| [investor-faq.md](pitch/investor-faq.md) | Hard-question objection handling + return thesis |
| [outbound-sequence.md](pitch/outbound-sequence.md) | Cold email (DE + EN) + LinkedIn + discovery script |
| [data-room-checklist.md](pitch/data-room-checklist.md) | Due-diligence prep, marked Ready / To-prepare |
| [target-accounts.md](pitch/target-accounts.md) · [.csv](pitch/target-accounts.csv) | **75 researched prospect companies** (DACH-first), ranked by fit, with observable pain + approach + contacts |
| [outreach-playbook.md](pitch/outreach-playbook.md) | How to find + reach decision-makers **compliantly** (UWG §7-aware); per-segment angles + trigger signals |

### Working tools & templates

| Artifact | What it is |
|----------|-----------|
| [legal/](legal/) | **Legal pack** — ready-to-fill draft templates (AVV/DPA, TOMs, subprocessor list, Impressum, Datenschutzerklärung, AGB) to hand to a lawyer |
| [pricing-financial-model.xlsx](pricing-financial-model.xlsx) | **Live financial model** — edit the yellow input cells; unit economics + 24-month MRR/ARR/cash projection recalculate automatically |
| [90-day-tracker.csv](90-day-tracker.csv) · [.md](90-day-tracker.md) | **Execution tracker** — 41 tasks across 12 weeks (CSV imports to Sheets/Notion; the `.md` is a checklist) |

---

## Start here — highest-leverage actions

**This week (setup — before any SaaS revenue):**
1. **Book a Steuerberater consultation.** Frame it exactly: _"I'm a registered Freiberufler with a
   USt-IdNr and want to launch a productised AI SaaS — how do I handle the **Gewerbe** classification
   and avoid **Abfärbung** on my existing freelance income?"_ This is the single most important action —
   selling standardised SaaS is almost certainly Gewerbe, and mixing it into your freelance activity
   without clean separation can retroactively make **all** your income trade-taxable. (See doc 00.)
2. **Ring-fence the two activities** — separate bookkeeping + a separate business bank account now;
   plan a **UG/GmbH** for the SaaS on concrete triggers (customer PII at scale, first investor,
   co-founder, or an enterprise buyer demanding limited liability).

**Next 2–4 weeks (be sellable):**
3. **Assemble the compliance pack** — it *is* sales collateral for DACH buyers: a customer AVV/DPA with
   TOMs annex, a published subprocessor list, a DPIA support pack, an EU-hosting statement. (Doc 01.)
4. **Publish the legal pages** — Impressum (§5 DDG, include your USt-IdNr), Datenschutzerklärung, B2B
   AGB, and a §25 TDDDG cookie banner if you run non-essential cookies. Add the Art. 50 AI-transparency
   line (mandatory 2 Aug 2026). (Doc 01.)

**Weeks 1–12 (go to market):**
5. **Run the 90-day pilot plan** (doc 04): a paid design-partner offer to ~3 regulated/privacy-first
   DACH targets, founder-led outbound + thesis-backed content, converting pilots to paid by week 12.
   Price with the hybrid base-plus-usage tiers in doc 05.

---

## Positioning in one line

> **The EU-sovereign, governed, auditable customer-feedback engine** — turns raw feedback into
> prioritised, action-ready insight that improves from measured outcomes, adaptable to any industry
> without fine-tuning, and built GDPR + EU-AI-Act-first. *Compliance and data residency are the wedge,
> not overhead.*

## Notes
- These docs **are committed to git**, including pricing, strategy and financials. Treat the repo as
  the place they live, and keep that in mind before sharing the repository.
- `legal/` is not just reference: `impressum.md`, `datenschutzerklaerung.md` and `agb-b2b.md` are read
  by the website at build time (`apps/web/app/legal/[slug]/page.tsx`). Renaming or moving them breaks
  the web build.
- Figures, thresholds, and deadlines were current at research time; re-verify the moving ones (Kleinunternehmer
  limits, e-invoicing rollout, AI-Act/Digital-Omnibus dates) against official sources before acting.
