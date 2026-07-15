# Enterpret — Feature Inventory (for CLARA feature-by-feature comparison)

> **Method:** multi-agent deep research — 6 search angles, 24 sources fetched, 114 claims
> extracted, 25 adversarially verified (3-vote; need 2/3 refutes to kill). **21 confirmed,
> 4 refuted.** Confidence tags: **[H]** high (multi-source, survived verification),
> **[M]** medium (single-source or partial), **[U]** surfaced but *not* verified this run.
> **Source caveat:** most evidence is Enterpret's own material (product pages, help center,
> the Enterpret 2.0 blog, the Oct 27 2025 BusinessWire launch) — authoritative for *what
> Enterpret claims*, **not independently benchmarked**. Treat all metrics as "Enterpret states…".
> **Snapshot:** post-"Enterpret 2.0" (launched ~Oct 27 2025), as of July 2026. Claude model
> versions cited (Sonnet 4.6 / Opus 4.6) will drift.

---

## 0 · Positioning & architecture
- **"Enterpret 2.0 — the first agentic customer feedback platform."** Relaunched ~**Oct 27 2025**. [H]
- Category: **AI customer/product feedback intelligence** (VoC + product-feedback analytics).
- Architecture = one continuous loop across **three pillars: Unify → Understand → Act.** [H]
- 11+ named modules mapped to pillars: **Unify** (Feedback Integrations, Adaptive Taxonomy, Customer Context / Knowledge Graph, Data Enrichment); **Understand** (Dashboard, AI Insights/Wisdom, MCP Server, Sales Intelligence); **Act** (AI Agents, Close the Loop, Workflow Integrations). [H]

## 1 · UNIFY — ingestion, structuring, context
### 1a. Data sources & connector model
- **50+ (up to ~65) native connectors.** [H] ("50+" is a vendor round number.)
- **Inbound sources:** support tickets (Zendesk, Intercom, Front, HubSpot, Kustomer, **Salesforce Service Cloud**), reviews (app stores, G2), **surveys / CSAT / NPS**, **sales calls (Gong)**, social (Reddit, X, Instagram), community, **CRM (Salesforce)**, **product-usage signals**. [H]
- **Ingestion methods (heterogeneous):** native OAuth connectors • **webhook API** (programmatic push) • **data-warehouse / ETL sync** (Snowflake, Census) • **CSV upload**. [H]
### 1b. Adaptive Taxonomy (auto-classification)
- Self-evolving; auto-organizes feedback into a **"5-level" hierarchy** = **L1/L2/L3 keyword tree** (product area → feature → sub-feature) **+ Themes + Sub-themes** (the "why"). A prediction = full L1→L2→L3 path + themes. [H] *(Nuance: it's a 3-deep tag tree + a 2-deep theme tree, not one 5-deep tree.)*
- **Continuous learning** from each launch / language shift; **proactive maintenance = drift detection, duplicate detection, emerging-term detection**; **proposes** changes with **human-in-the-loop** AI-assisted validation. [H]
- Separate **fixed intent Categories** (not adaptive): exactly **4 — Help, Improvement, Complaint, Praise.** [H]
- **⚠ Boundary:** "zero manual maintenance / no drift / fully automatic taxonomy" was **REFUTED (0-3).** It proposes; humans approve. [M]
### 1c. Customer Knowledge Graph + enrichment
- **Entity graph** linking feedback to **Accounts, Users, Opportunities, Products, custom objects** — the layer that ties feedback to business/revenue context. [H]
- **Data Enrichment** module ("enrich & extract deeper insights"). [H]

## 2 · UNDERSTAND — AI insights
- **Wisdom AI** — conversational insights engine. Plain-English Q&A across the **entire corpus** (tickets/surveys/calls/reviews) "in seconds," **multi-turn**, **grounded in the customer's taxonomy**, **one-click citations** back to source conversations. [H] *("verified" citations = self-asserted, not audited.)*
- **Models:** Claude **Sonnet 4.6** (fast, default) / **Opus 4.6** (most capable), chosen via a model switcher per query. [H]
- **MCP Server** — exposes feedback/Wisdom to external AI (**Slack, ChatGPT, Claude, Cursor, Notion, Glean**) via named tools (`get_organization_details`, `get_graph_schema`, `run_graph_query`, `find_user_quote`). [H]
- **Voice-of-Customer AI Agent** — generates narratives with charts & call-outs (explains the "why"). [H]
- **Agent OS** *(New)* — build workflows that **create artifacts & perform work** (Linear tickets, Notion docs, slide decks, HTML dashboards, CSVs) "without needing someone to ask." [H] *(marketed; not benchmarked.)*
- **Dashboard** — "visualize & quantify insights." [H]  • **Sales Intelligence** — "understand every deal to win more." [M]

## 3 · ACT — actioning / workflow
- **Outbound write-actions** into: **Jira** (bi-directional sync: link feedback↔issues, enrich tickets, track resolution) • **Linear** (create/assign issues w/ context) • **Slack** (dashboard snapshots + AI-Agent alerts + Wisdom access) • **Notion** (export insights as docs) • **Canva** (dashboards as decks). *Bi-di sync = Jira only.* [H]
- **True write-back:** create/update tickets, **change priority/owner/SLAs**, **instantly reassign Zendesk tickets**, create high-priority Jira issues; **triggerable automatically.** [H]
- **Close the Loop** module — "detect resolutions and respond." [H]
- Route to **any third-party / internal system** via configurable actions or APIs. [H]

## 4 · Analytics ↔ revenue / CX metrics
- Dashboards **quantify** insights; the Knowledge Graph links feedback to Accounts/Opportunities → enables revenue/deal tying. [M]
- **Gap:** the *precise mechanics* of tying feedback to **churn / NPS / CSAT / adoption / ARR-at-risk** were **not confirmed** in verified sources — under-documented. [M]
- Anomaly detection over unstructured feedback is marketed, but the specific "library agents + anomaly alerts" claim was **REFUTED (1-2).** [M]

## 5 · Governance / security / compliance  ⚠ surfaced, NOT verified this run
- From Enterpret's `/security` page (search-surfaced, not 3-vote verified): **SOC 2 Type 2** (SSAE 18), **ISO/IEC 27001**, **ISO/IEC 42001** (AI management system), **ISO/IEC 27701** (privacy). **[U]**
- **No evidence** on data residency, SSO/RBAC, admin controls, or **EU-specific / EU-AI-Act** governance. **Major gap** for a governed-platform comparison.

## 6 · Personas / use-cases
- **Product, CX, Voice-of-Customer, Support, Sales, Leadership.** [H]

## 7 · Pricing
- **No public pricing**; sales-gated (Vendr marketplace listing exists). [M]

## 8 · Practitioner-reported limitations (independent)
- G2 / Gartner: **steep learning curve, difficult setup, reporting "lacks flexibility," occasional Wisdom load failures/lag, no confidence scores.** [M, secondary]

## 9 · ⭐ Boundary — what Enterpret does NOT verifiably do (do not credit in the comparison)
Three "agentic autonomy" claims were **adversarially refuted**:
1. **Autonomous real-time Action Agents** that act "before accounts churn." (0-3)
2. **Fully automatic taxonomy**, zero manual maintenance / no drift. (0-3)
3. **Prebuilt library agents + anomaly detection** firing governed alerts. (1-2)

→ **Verified actioning ceiling:** detect + understand + **create/route/reassign tickets + fire alerts + PROPOSE taxonomy changes (human-in-loop).**
→ **NOT verified:** autonomous **governed** intervention • **policy-gated** action • **proving an action moved a metric** (outcome measurement).

## 10 · CLARA differentiation surface (framing note for the comparison LLM)
Enterpret is strongest at **Unify + Understand** (aggregation, adaptive taxonomy, conversational insights w/ citations, MCP) and does **Act** as **ticket/alert routing + human-approved proposals.** The absent/unverified zones — **governed action (policy-as-code, approvals), outcome contracts / proof-of-impact, closed-loop measurement & learning, and EU-first governance (EU AI Act, DE/EN, data residency)** — are exactly CLARA's positioning. The honest comparison lives on the **right half of the loop (decide → govern → execute → prove → learn)**, where Enterpret's *verified* capability thins out. On the **left half (ingest → structure → understand)**, Enterpret is deep and mature; do not overstate CLARA there.

---

## Sources
- Enterpret Features Explained (help center) — https://helpcenter.enterpret.com/en/articles/12665465-enterpret-features-explained
- Enterpret 2.0 blog — https://www.enterpret.com/blog/enterpret-2-the-foundation-for-customer-intelligence
- Homepage — https://www.enterpret.com/
- Adaptive Taxonomy — https://www.enterpret.com/platform/adaptive-taxonomy
- What is the Taxonomy (help) — https://helpcenter.enterpret.com/en/articles/12665751-what-is-the-taxonomy
- AI Insights / Wisdom — https://www.enterpret.com/platform/ai-insights
- AI Agents — https://www.enterpret.com/platform/ai-agents
- Workflow Integrations — https://www.enterpret.com/platform/workflow-integrations
- Feedback Integration / connectors — https://www.enterpret.com/platform/customer-feedback-integration • https://www.enterpret.com/integrations
- MCP Server (help) — https://helpcenter.enterpret.com/en/articles/12665166
- Security & Trust — https://www.enterpret.com/security
- BusinessWire launch (Oct 27 2025) — https://www.businesswire.com/news/home/20251027487140/en/Enterpret-Launches-the-First-Agentic-Customer-Feedback-Platform-to-Unify-Understand-and-Act-on-Scattered-Customer-Signals
- SiliconANGLE (independent) — https://siliconangle.com/2025/10/27/exclusive-enterpret-adds-agents-customer-feedback-analysis-platform/
- G2 reviews — https://www.g2.com/products/enterpret-inc-enterpret/reviews
- Vendr (pricing) — https://www.vendr.com/marketplace/enterpret
