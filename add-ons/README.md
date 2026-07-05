# CLARA add-ons

Optional, decoupled features that are **not** part of the core CLARA platform — each is
self-contained so it can ship as a paid upsell, run as a standalone app, or later be folded
into `apps/api`. Nothing here is imported by the main app.

## compliance-checker

EU AI Act (Reg. 2024/1689) + GDPR (Reg. 2016/679) compliance assessor for a marketing
campaign or AI use case. Ported from the Elvis/Supabase `check-compliance` edge function.
Returns an overall + per-regulation score, article-level findings, required actions, and
prohibited-practice (Art. 5) detection. The regulatory knowledge base is current to the
mid-2026 Digital Omnibus and DACH-aware.

**Why it's an add-on, not core:** the locked strategy (`business/STRATEGY_SYNTHESIS.md` §6)
puts compliance as "an added layer, not the headline." This keeps it a differentiator/upsell
without diluting the feedback-loop USP.

```bash
cd add-ons/compliance-checker
pip install -r requirements.txt
python -m pytest test_compliance.py          # offline test (mocked LLM)
AI_BASE_URL=... AI_API_KEY=... AI_MODEL=... uvicorn app:app --reload
# POST /compliance/check  { "title", "campaign_description", "additional_documents": [] }
```

**Folding into CLARA later:** it already speaks CLARA's AI contract. Delete
`compliance._call_tool`, import `app.services.ai.call_tool` (identical
`system/user/tool/tool_name` signature, plus retry + Langfuse tracing), and mount the
`app.py` route under CLARA's API. Gate it behind a plan/entitlement (`app/billing.py`).
