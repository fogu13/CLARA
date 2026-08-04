# P1 demo recording — script (loop closure on real data)

Target: ~4 minutes, one take, screen + voice. Proves the P1 proof-arc position:
**the governed feedback→outcome loop running on real data.** Record against
http://localhost:3000 (the workspace already contains the Lieferando signals and
the walkthrough problems — visually rich without further setup).

Pre-flight (2 min before recording):
- API + web running (`uvicorn app.main:app --port 8000`, `next dev`), dashboard loads.
- Language toggle set to EN (or DE for a German-audience cut).
- Close the Next.js devtools bubble; hide bookmarks bar.

## Beats

1. **Dashboard (30s).** "This is CLARA — every customer signal from app stores,
   support, surveys in one governed loop." Point at: customers affected, the
   30-day signal-volume chart, the emerging-problems radar ("act now" badges).

2. **Signals → import story (40s).** Open Signals. "Feedback comes in via CSV,
   webhooks, or store connectors — 240+ signals here, German and English mixed."
   Show the Import batches card: "and a mis-mapped import is one click to undo."

3. **Run Triage (40s).** Click Run Triage. While it runs (~90s — cut or narrate
   over): "Local-first AI — here it's Mistral, an EU provider, swappable in
   Settings for any OpenAI-compatible endpoint including on-prem." Show Settings
   → AI endpoint card briefly, then back.

4. **Insights (45s).** Open Insights. Pick the checkout/refund insight:
   bilingual evidence excerpts with signal IDs, severity, trend badge,
   affected cohort, proposed actions. "Every claim is grounded — click any
   citation to the raw signal."

5. **Governance + action (45s).** Open the checkout problem. Point at the
   proposed outcome contract above the decision buttons: "before anything
   executes, CLARA proposes the measurement contract — trailing-28-day
   baseline, 30-day window, interrupted-time-series scoring. Zero input:
   the checkbox is on by default." Approve the action: "consequential actions
   stop at a human decision — approving stamps the reviewer (that stamp IS
   the Article 50(4) exemption) and schedules the T+7 and T+30 measurements
   automatically." Show the execution + Jira draft + measurement checkpoints.
   Mention the 409 on double-approval if asked.

6. **Outcome + learning (30s).** Outcome board: the target-met problem.
   "After the measurement window, CLARA re-measures recurrence and records
   whether the action actually worked — with a segmented-regression effect
   estimate and confidence interval, or an honest 'insufficient data' label,
   never a fake number. That learning feeds the next proposal."

7. **Ask CLARA close (20s).** Ask: "What are customers complaining about most?"
   Show the cited, confidence-scored answer. "Grounded Q&A, no chat theater —
   and if the evidence is thin, it refuses."

8. **Works-council switch (20s, DACH audiences).** "And for your works council,
   this switch…" — Settings → flip the «Betriebsrat-Modus» toggle. Back on the
   dashboard, the workload card now carries the "Aggregated under works-council
   mode" banner and role buckets instead of names; open an evidence-pack export:
   the reviewer column reads "approver". "§87 (1) Nr. 6 BetrVG — any system
   capable of monitoring employee performance is co-determined, intent doesn't
   matter. One switch: routine views can't be tied to a person, the audit chain
   stays intact, and the named admin keeps the full export the works-council
   agreement requires. Plus a ready-made Betriebsrat-Information one-pager for
   the co-determination file."

9. **Compliance close (25s, procurement audiences).** Open /compliance: "your
   security questionnaire, pre-answered." Point at the Article 50 status card
   ("every outbound text: human-reviewed and exempt under 50(4), or
   AI-disclosed — exportable"), the audit-log export, and the AI-literacy card:
   "Art 4 says you must train the staff who operate this — the training module
   ships in-product, with a stamped pack for your compliance folder."

## One-liners to land
- "Enterpret tells you what customers said. CLARA proves what you did about it worked."
- "Our approval gate is your Article 50 compliance."
- "EU-resident by default: Supabase EU, Mistral EU, or fully local with Ollama."
- "Every step you saw is in the audit export — approvals, executions, outcomes, learnings."
- "No US tool engineers for §87 BetrVG — CLARA ships works-council mode out of the box."

## Don'ts
- Don't open the seed problems' detail if asked about real data — stay on the
  checkout/refund story (real + synthetic-realistic).
- Don't run taxonomy bootstrap live (8s of silence); mention it exists.
