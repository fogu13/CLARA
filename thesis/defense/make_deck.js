// MSc thesis defense deck — 15–20 min, OPIT RAI-9001.
// Palette "Midnight Executive": navy 1E2761 dominant, ice CADCFC support, white accent.
// Motif: the loop stages as small navy circles with white numerals; Cambria heads + Calibri body.
const path = require("path");
const pptxgen = require("pptxgenjs");
const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE"; // 13.3 x 7.5

const NAVY = "1E2761", ICE = "CADCFC", WHITE = "FFFFFF", INK = "1A1A2E", MUTE = "5A6478", GOOD = "2C5F2D", WARN = "990011";
const T = path.join(__dirname, ".."); // repo thesis/ dir (was the pre-unification Thesis_writing folder)
const HEAD = { fontFace: "Cambria", color: INK }, BODY = { fontFace: "Calibri", color: INK };

function title(s, txt, sub) {
  s.addText(txt, { ...HEAD, x: 0.6, y: 0.35, w: 12.1, h: 0.85, fontSize: 32, bold: true });
  if (sub) s.addText(sub, { ...BODY, x: 0.6, y: 1.08, w: 12.1, h: 0.4, fontSize: 14, italic: true, color: MUTE });
}
function loopMotif(s, x, y, active) { // 4 mini circles S-I-A-L
  const labels = ["S", "I", "A", "L"];
  labels.forEach((l, i) => {
    s.addShape("ellipse", { x: x + i * 0.42, y, w: 0.32, h: 0.32, fill: { color: i === active ? NAVY : ICE } });
    s.addText(l, { x: x + i * 0.42, y: y - 0.017, w: 0.32, h: 0.34, align: "center", fontSize: 11, bold: true,
      fontFace: "Calibri", color: i === active ? WHITE : NAVY, margin: 0 });
  });
}
function card(s, x, y, w, h, head, body, opts = {}) {
  s.addShape("roundRect", { x, y, w, h, rectRadius: 0.06, fill: { color: opts.fill || "F4F7FC" }, line: { color: ICE, width: 1 } });
  s.addText(head, { ...BODY, x: x + 0.15, y: y + 0.1, w: w - 0.3, h: 0.32, fontSize: 13.5, bold: true, color: opts.headColor || NAVY, margin: 0 });
  s.addText(body, { ...BODY, x: x + 0.15, y: y + 0.42, w: w - 0.3, h: h - 0.52, fontSize: 11.5, color: opts.bodyColor || INK, margin: 0 });
}
function stat(s, x, y, w, big, label, color) {
  s.addText(big, { ...HEAD, x, y, w, h: 0.9, fontSize: 54, bold: true, color: color || NAVY, align: "center", margin: 0 });
  s.addText(label, { ...BODY, x, y: y + 0.92, w, h: 0.65, fontSize: 12.5, color: MUTE, align: "center", margin: 0 });
}

// ---------- 1 · Title (dark) ----------
let s = pres.addSlide(); s.background = { color: NAVY };
s.addText("Closing the Loop, Building the Memory", { fontFace: "Cambria", color: WHITE, x: 0.9, y: 2.0, w: 11.5, h: 1.2, fontSize: 44, bold: true });
s.addText("A design-science study of a governed platform for turning customer feedback\ninto measured action and reusable organisational learning",
  { fontFace: "Calibri", color: ICE, x: 0.9, y: 3.25, w: 11.5, h: 0.9, fontSize: 20 });
["Signal", "Insight", "Action", "Learning"].forEach((l, i) => {
  s.addShape("ellipse", { x: 0.95 + i * 1.95, y: 4.65, w: 0.5, h: 0.5, fill: { color: i === 3 ? "02C39A" : ICE } });
  s.addText(String(i + 1), { x: 0.95 + i * 1.95, y: 4.63, w: 0.5, h: 0.53, align: "center", fontSize: 18, bold: true, fontFace: "Calibri", color: NAVY, margin: 0 });
  s.addText(l, { x: 1.5 + i * 1.95, y: 4.7, w: 1.35, h: 0.4, fontSize: 15, fontFace: "Calibri", color: WHITE, margin: 0 });
  if (i < 3) s.addText("→", { x: 1.5 + i * 1.95 + 0.85, y: 4.7, w: 0.4, h: 0.4, fontSize: 15, fontFace: "Calibri", color: ICE, margin: 0 });
});
s.addText("Elvis Shehi  ·  MSc Responsible Artificial Intelligence  ·  OPIT  ·  Supervisor: Prof. Zorina Alliata  ·  September 2026",
  { fontFace: "Calibri", color: ICE, x: 0.9, y: 6.55, w: 11.5, h: 0.4, fontSize: 13 });
s.addText("Progress review · 8 August 2026 — the evaluation is complete: all three predictors, one gold standard",
  { fontFace: "Calibri", color: "02C39A", x: 0.9, y: 6.95, w: 11.5, h: 0.35, fontSize: 12, italic: true });
s.addNotes("60–90s. Frame in one breath: organisations collect more feedback than ever, yet fewer than a third systematically close the loop. This thesis designs, builds and evaluates a platform where the loop is not just closed but GOVERNED and MEASURED — and where what worked becomes organisational memory. One system, studied through Design Science Research. TODAY: progress review, not the defense. The headline is that the LLM row of the results table is no longer pending — it ran on 4 August, and it changed two things: RQ3 split into accuracy (RQ3a) and equity (RQ3b), and one fairness claim had to be retracted. Lead with the 'since your last look' section, then the three results slides.");

// ---------- 2 · The problem ----------
s = pres.addSlide();
title(s, "The problem: feedback is collected, not converted", "The feedback-to-action gap, and why acting without measuring is not enough");
loopMotif(s, 11.4, 0.45, 0);
card(s, 0.6, 1.7, 6.0, 1.55, "Fewer than 30% of firms close the loop", "Structural barriers — silos, unclear ownership, no workflow from feedback to responsible team (Bone et al., 2017). Forrester 2025: most CX teams still can't get stakeholders to act; only 27% communicate insights in time.");
card(s, 0.6, 3.45, 6.0, 1.55, "Even acting can backfire", "Field experiment, ~1.5M Uber customers: apologies alone didn't restore spending — repeated apologies REDUCED it (Halperin et al., 2022). Action taken ≠ problem solved. Closure must be measured.");
card(s, 0.6, 5.2, 6.0, 1.55, "What is learned is forgotten", "Organisational memory depreciates (Argote 2013; Walsh & Ungson 1991). Teams re-learn the same lessons; no system retains which remedies actually worked.");
s.addText("Four deficiencies", { ...HEAD, x: 7.0, y: 1.75, w: 5.6, h: 0.4, fontSize: 17, bold: true, color: NAVY });
s.addText([
  { text: "Signal fragmentation — 13+ sources, no unified priority", options: { bullet: true, breakLine: true } },
  { text: "Insight–action gap — no governed path to execution", options: { bullet: true, breakLine: true } },
  { text: "Unmeasured closure — tickets created, outcomes unknown", options: { bullet: true, breakLine: true } },
  { text: "Lost memory — what worked isn't retained or retrieved", options: { bullet: true } },
], { ...BODY, x: 7.2, y: 2.25, w: 5.4, h: 2.1, fontSize: 14, paraSpaceAfter: 8 });
s.addShape("roundRect", { x: 7.0, y: 4.65, w: 5.7, h: 2.1, rectRadius: 0.06, fill: { color: NAVY } });
s.addText("Central claim", { fontFace: "Calibri", x: 7.25, y: 4.8, w: 5.2, h: 0.35, fontSize: 13, bold: true, color: ICE, margin: 0 });
s.addText("Closing the loop is a workflow-and-governance problem. The missing primitives are a measured outcome contract and a perishable learning memory — not a better dashboard.",
  { fontFace: "Calibri", x: 7.25, y: 5.15, w: 5.2, h: 1.5, fontSize: 14.5, color: WHITE, margin: 0 });
s.addNotes("90s. Anchor the gap in Bone et al., then the Uber experiment — the strongest evidence that acting without measuring can make things worse. End on the central claim; everything after is those two primitives.");

// ---------- 3 · RQs + method ----------
s = pres.addSlide();
title(s, "Research questions and method", "Design Science Research (Hevner 2004; Peffers 2007) — the artifact is the research output");
loopMotif(s, 11.4, 0.45, 1);
const rqs = [
  ["RQ1 · Core", "How can an artifact make actions governed, executed and VERIFIED to have closed — with reusable learning?"],
  ["RQ2 · Governance", "What design lets autonomous action align with EU AI Act & GDPR without unduly slowing practitioners?"],
  ["RQ3a · Accuracy", "How accurately does AI enrichment/routing reproduce human labels on real feedback, across sectors? (answered — three predictors, one gold standard)"],
  ["RQ3b · Equity", "Is triage reliability EQUAL across languages — whose problems reach a human? (split out from RQ3 after the August run made it answerable)"],
  ["RQ4 · Qualitative", "How do practitioners judge usefulness, usability, trustworthiness? (interviews + SUS/TAM — not yet started; the critical path)"],
];
// Five RQs since the August split of RQ3 — 2 columns x 3 rows, the last card spanning.
rqs.forEach((r, i) => {
  const last = i === rqs.length - 1;
  card(s, 0.6 + (last ? 0 : (i % 2) * 6.15), 1.7 + Math.floor(i / 2) * 1.3,
       last ? 12.1 : 5.95, 1.18, r[0], r[1]);
});
s.addShape("roundRect", { x: 0.6, y: 5.72, w: 12.1, h: 1.2, rectRadius: 0.06, fill: { color: "F4F7FC" }, line: { color: ICE, width: 1 } });
s.addText("Method: problem-centred DSRM — problem → objectives → design & build → demonstrate → evaluate → communicate. Mixed-methods evaluation: a quantitative gold-set on 188 real, multilingual signals + a practitioner study (12–15 interviews, task sessions, SUS/TAM). Design-validity claims, not statistical effects.",
  { ...BODY, x: 0.85, y: 5.85, w: 11.6, h: 0.95, fontSize: 13, margin: 0 });
s.addNotes("90s. Say why DSR: the question is 'what works by design', not 'what is'. The change since you last saw this: RQ3 has become RQ3a (accuracy) and RQ3b (equity). That is not cosmetic — the August run showed the equity result is the substantive one for a Responsible-AI thesis, and it needed its own question rather than living as a sub-clause. H1–H8 map under these five. Flag honestly that RQ4 has not started: it is the critical path and it is ask #2 today.");

// ---------- 4 · The artifact ----------
s = pres.addSlide();
title(s, "The artifact: a governed loop, end to end", "CLARA — Capture, Listen, Analyze, Respond, Adapt");
loopMotif(s, 11.4, 0.45, 2);
s.addImage({ path: `${T}/diagrams/rendered/01_architecture_logical.png`, x: 0.6, y: 1.7, w: 12.1, h: 4.25 });
s.addText("Deterministic code owns validation, conflict resolution, execution, audit. Language-model reasoning is confined to named, bounded stages. The points where the system can act are finite, named, individually auditable — that is what makes it governable.",
  { ...BODY, x: 0.6, y: 6.15, w: 12.1, h: 0.85, fontSize: 14, color: MUTE, italic: true });
s.addNotes("2 min. Walk the diagram left to right: sources → ingestion → enrich → synthesize → rules → the approval diamond → execute → measure → learn, with governance cross-cutting. Emphasise the architectural principle: bounded model, deterministic loop. Single build: CLARA (FastAPI + LangGraph), in production — the earlier prototype is acknowledged once as the first design cycle and archived.");

// ---------- 4b · System architecture (the CLARA build) ----------
s = pres.addSlide();
title(s, "Inside the build: CLARA system architecture", "Next.js (Vercel) → FastAPI + LangGraph (Docker on a Hetzner EU VPS, behind Caddy) → Supabase Postgres");
loopMotif(s, 11.4, 0.45, 2);
s.addImage({ path: `${T}/diagrams/rendered/03_architecture_clara.png`, x: 0.6, y: 1.55, w: 6.22, h: 5.2 });
card(s, 7.05, 1.6, 5.65, 1.62, "LangGraph runtime", "One typed graph: enrich → synthesize → evaluate-rules → interrupt (human approval) → execute → measure → learn. The interrupt IS the Art 14 gate — there is no code path to an external effect that bypasses it.");
card(s, 7.05, 3.37, 5.65, 1.62, "Deployment (production)", "API in Docker on a Hetzner EU VPS behind Caddy · frontend on Vercel · Supabase Postgres + pgvector, RLS tenant isolation · uptime: GitHub Actions re-runs the 17-check live smoke every 30 min.");
card(s, 7.05, 5.14, 5.65, 1.62, "Model & observability", "Provider-agnostic LLM layer speaking the OpenAI protocol — hosted, EU gateway, or self-hosted (Ollama/vLLM). Langfuse tracing on the LLM stages; severity stays deterministic code.");
s.addNotes("90s. New slide for this meeting. Walk top-down: UI → FastAPI (~43 REST endpoints) → the LangGraph nodes; approval is a graph interrupt, not a UI convention. Deployment reality matches the diagram: Docker on a Hetzner EU VPS behind Caddy, Vercel frontend, Supabase Postgres with RLS. The provider-agnostic model layer is the EU-sovereignty wedge.");

// ---------- 4c · The loop in motion (pipeline + HITL sequence) ----------
s = pres.addSlide();
title(s, "The loop in motion: pipeline and approval sequence", "Bounded LLM stages (blue) inside deterministic gates; governance touchpoints in red");
loopMotif(s, 11.4, 0.45, 2);
s.addImage({ path: `${T}/diagrams/rendered/04_pipeline_flow.png`, x: 0.7, y: 1.6, w: 2.05, h: 5.15 });
s.addImage({ path: `${T}/diagrams/rendered/05_sequence_hitl.png`, x: 3.05, y: 1.75, w: 9.55, h: 4.14 });
s.addText("Left: the pipeline as implemented — risk gate (auto_execute), approval queue, audit write, outcome measurement, decayed-confidence retrieval feeding rule matching. Right: the same lifecycle as a sequence — approval interrupt, audit record, outcome contract set BEFORE measurement, re-measure after the window, codify learning, retrieve on the next similar decision.",
  { ...BODY, x: 3.05, y: 6.0, w: 9.55, h: 1.0, fontSize: 11.5, color: MUTE });
s.addNotes("90s. Two views of one loop. Left: stress the two red governance nodes (approval queue, audit write) and the retrieval back-edge — the memory sits IN the control flow, not in a side store. Right: the contract is fixed before the action executes, so there is no post-hoc metric shopping.");

// ---------- 4d · Data model ----------
s = pres.addSlide();
title(s, "Data model: the loop is a schema, not a convention", "ER view (runnable DDL in diagrams/schema.sql) — contracts and learnings are first-class tables");
loopMotif(s, 11.4, 0.45, 2);
s.addImage({ path: `${T}/diagrams/rendered/06_data_model_er.png`, x: 0.75, y: 1.5, w: 2.56, h: 5.35 });
card(s, 3.75, 1.7, 8.9, 1.5, "Closure as referential integrity", "actions_log binds 1:1 to outcome_contracts AT CREATION; outcome_measurements grade closure (operational → customer → outcome). \"Closed\" is a row with evidence, not a status flag.");
card(s, 3.75, 3.35, 8.9, 1.5, "Memory as data", "ab_learnings carry base_confidence + half_life_days — decay is computed from columns, auditable by query. Taxonomy nodes carry the same decay fields for theme drift.");
card(s, 3.75, 5.0, 8.9, 1.5, "Tenancy & evolution", "Every table workspace-scoped, enforced by Postgres RLS below the app layer. Domain objects as jsonb payloads + promoted columns — one store contract across SQLite (dev), in-memory (tests), Postgres (prod).");
s.addNotes("60–90s. For an architecture audience the schema is the argument: the thesis's two primitives (outcome contract, perishable learning) are tables with foreign keys, not prose. RLS puts tenant isolation in the database where an application bug cannot bypass it — honest boundary: not warranted for adversarial co-tenants; pilots run single-workspace.");

// ---------- 5 · Design decisions ----------
s = pres.addSlide();
title(s, "Five design decisions the literature doesn't resolve", "Each implemented, grounded, and stated with its cost");
loopMotif(s, 11.4, 0.45, 2);
const dds = [
  ["1 · Rule conflict resolution", "Priority → specificity → action-type dedupe; superseded rules logged. Cost: config debt — entrenches a wrong rule as faithfully as a right one."],
  ["2 · Confidence decay in learnings", "Memory as perishable: base × 0.5^(age/half-life). Prior art bounded: MemoryBank decays chat memory; ours decays ACTION-OUTCOME evidence. Cost: the half-life is a guess."],
  ["3 · Cross-signal severity", "Severity from the corroborating SET (urgency, volume, sentiment), not the loudest voice. Cost: can bury the rare catastrophic single signal — needs an override."],
  ["4 · Past-learnings retrieval", "Decayed-confidence retrieval into new decisions (CBR lineage). Cost: retrieval quality gates usefulness."],
  ["5 · Per-industry profiles", "Adaptation by configuration, not fine-tuning: weight overlays per sector. Cost: authored priors can encode stereotypes; inspectability is the safeguard."],
];
dds.forEach((d, i) => {
  const col = i % 3, row = Math.floor(i / 3);
  card(s, 0.6 + col * 4.13, 1.75 + row * 2.35, 3.93, 2.15, d[0], d[1]);
});
s.addShape("roundRect", { x: 8.86, y: 4.1, w: 3.87, h: 2.15, rectRadius: 0.06, fill: { color: NAVY } });
s.addText("Why costs?", { fontFace: "Calibri", x: 9.05, y: 4.25, w: 3.5, h: 0.35, fontSize: 13, bold: true, color: ICE, margin: 0 });
s.addText("A design principle that buys something for nothing is a platitude. Stating the cost is what makes each decision defensible.",
  { fontFace: "Calibri", x: 9.05, y: 4.62, w: 3.5, h: 1.5, fontSize: 12.5, color: WHITE, margin: 0 });
s.addNotes("2 min. One sentence each; slow down on decay (the novelty boundary vs MemoryBank — examiners may probe novelty; we cite the prior art ourselves and position precisely) and on industry profiles (adaptation without retraining, demonstrated on three real sectors).");

// ---------- 6 · Governance ----------
s = pres.addSlide();
title(s, "Responsible AI as a property of the loop", "Not a compliance module — the loop itself is the control surface");
loopMotif(s, 11.4, 0.45, 2);
const gov = [
  ["Human approval · Art 14+", "auto_execute=false ⇒ pending approval. Designed BEYOND Art 14: friction, evidence & confidence shown, per-decision attribution (meaningful human control — Siebert 2023; automation-bias critique — Laux & Ruschemeier 2025)."],
  ["Audit trail · Art 12", "Every action: rule, params, executor, result. Review-then-harden finding: declared controls ≠ enforced controls until adversarially verified."],
  ["Transparency · Art 50", "AI outputs labelled with provenance. Human editorial review = the Art 50(4) exemption mechanism — the approval gate IS the compliance artifact."],
  ["Sovereignty & GDPR", "Provider-agnostic LLM — self-hostable, EU-resident. PII masking, retention limits, workspace RLS. Sentiment on text is NOT 'emotion recognition' (Art 3(39): biometric only)."],
];
gov.forEach((g, i) => card(s, 0.6 + (i % 2) * 6.15, 1.75 + Math.floor(i / 2) * 2.35, 5.95, 2.15, g[0], g[1]));
s.addText("Measured closure has three levels: operational (ticket done) → customer (reporter notified) → outcome (metric moved). \"Closed\" means the third.",
  { ...BODY, x: 0.6, y: 6.45, w: 12.1, h: 0.6, fontSize: 13.5, italic: true, color: MUTE });
s.addNotes("2 min. This is the RAI thesis heart. Two lines matter most: (1) the gate deliberately EXCEEDS Art 14 because awareness alone doesn't de-bias overseers; (2) the code review found declared-but-unenforced controls — and the governance instrumentation is what made that visible. Honesty as methodology.");

// ---------- 6b · Progress since mid-July (1/2) ----------
s = pres.addSlide();
title(s, "Since your last look (1/2): platform, security, governance", "17 Jul → 7 Aug — none of this has been in front of you; all merged to main, commit hashes in the notes");
loopMotif(s, 11.4, 0.45, 2);
s.addText("Security & sessions", { ...HEAD, x: 0.6, y: 1.55, w: 6.0, h: 0.38, fontSize: 16, bold: true, color: NAVY });
s.addText([
  { text: "TOTP MFA + HttpOnly cookie sessions — login challenge on the cookie-auth routes; tokens out of localStorage; AAL2 enforcement flag ready", options: { bullet: true, breakLine: true } },
  { text: "Opt-in per-client rate limiting, hardened after two adversarial audits — keyed on network address behind the trusted proxy (client headers can't mint fresh buckets); memory-bounded; auth dependency now fails closed by default", options: { bullet: true, breakLine: true } },
  { text: "Connector secrets encrypted at rest — Fernet envelope (enc:v1), loud failure if the key is absent", options: { bullet: true, breakLine: true } },
  { text: "Founder-owner bootstrap fix — the operator can no longer be locked out of their own workspace", options: { bullet: true, breakLine: true } },
  { text: "Scheduled uptime monitor — GitHub Actions re-runs the 17-check live smoke on a schedule; two consecutive failures open an issue, auto-closed on recovery", options: { bullet: true } },
], { ...BODY, x: 0.8, y: 1.98, w: 5.8, h: 3.5, fontSize: 11.5, paraSpaceAfter: 6 });
s.addText("Governance & audit", { ...HEAD, x: 7.0, y: 1.55, w: 5.7, h: 0.38, fontSize: 16, bold: true, color: NAVY });
s.addText([
  { text: "Four-eyes approvals (opt-in) — two distinct approvers, self-confirmation rejected; reviewer identity JWT-bound, never client-supplied", options: { bullet: true, breakLine: true } },
  { text: "Evidence-pack tamper evidence — canonical sha256 stamped onto the ApprovalRecord at decision time; changed evidence is provable", options: { bullet: true, breakLine: true } },
  { text: "Guardrail measurement — declared guardrails are now measured at every checkpoint; unmeasurable ones surface an explicit 'no data source' marker", options: { bullet: true, breakLine: true } },
  { text: "Public trust surface — Security & Trust page live; /pricing + legal pages staged behind fail-closed launch flags", options: { bullet: true } },
], { ...BODY, x: 7.2, y: 1.98, w: 5.5, h: 3.5, fontSize: 11.5, paraSpaceAfter: 6 });
s.addShape("roundRect", { x: 0.6, y: 5.55, w: 12.1, h: 1.45, rectRadius: 0.06, fill: { color: NAVY } });
s.addText("August: making model sovereignty real, not just declared", { fontFace: "Calibri", x: 0.85, y: 5.65, w: 11.6, h: 0.3, fontSize: 12.5, bold: true, color: "02C39A", margin: 0 });
s.addText("Embeddings can now point at a different provider than chat (migration 012 retargets taxonomy embeddings to vector(1024)) — so an EU embedding provider is a config change, not a rewrite. Provider errors now name the knob that actually failed instead of guessing from host equality. App Store connector reports an empty feed instead of a contented zero.  ·  Pattern throughout: review-then-harden — declared controls are not enforced controls until verified.",
  { fontFace: "Calibri", x: 0.85, y: 5.95, w: 11.6, h: 1.0, fontSize: 11.5, color: WHITE, margin: 0 });
s.addNotes("90s. One line per item, do not read the slide. July hashes: MFA 4200672 · cookie sessions a012298 · rate limiting 9b75195, hardened + auth fail-closed 350dc37 · secrets-at-rest & four-eyes eb15bcc · JWT-bound reviewer 967c7d1 · founder-owner bootstrap 1b0ab07 · uptime monitor 49013f8 · tamper evidence b065e4a · guardrail measurement e13105d · trust page 405a630 · pricing ec6bba6. August hashes: App Store empty-feed 9c87bd9 · AI failure names the knob 9f35374 · migration 012 embeddings vector(1024) 03f9120 · split embed provider f73f5ad · dashboard stale-bearer 401 bb6ce59/353c519. If she asks about uptime: production was verified 17/17 green by hand on 7 Aug; GitHub's scheduler dropped the cron for about a day on 6-7 Aug, which is a monitoring gap, not an outage — and worth saying plainly rather than letting the slide imply unbroken coverage.");

// ---------- 6c · Progress since mid-July (2/2) ----------
s = pres.addSlide();
title(s, "Since your last look (2/2): the evaluation finally completed", "The LLM row of the results table stopped saying \"pending\" on 4 August — and changed three things");
loopMotif(s, 11.4, 0.45, 3);
s.addText("The in-repo golden set", { ...HEAD, x: 0.6, y: 1.55, w: 6.0, h: 0.38, fontSize: 16, bold: true, color: NAVY });
s.addText([
  { text: "Golden set 80 → 100 bilingual (72 EN / 28 DE); DE gold completed to the two-tag rubric; the n=100 run published to the model card", options: { bullet: true, breakLine: true } },
  { text: "Published: sentiment 97% (CI 93–100) · urgency 90% (CI 84–95) · tag F1 by meaning 82.7%; DE within ~1pp of EN on urgency (89.3 vs 90.3)", options: { bullet: true, breakLine: true } },
  { text: "Urgency exemplar effect now significant — 83%→90%, in-run paired McNemar p=0.039 (was p=0.219 at n=80), after a churn-musing calibration exemplar", options: { bullet: true, breakLine: true } },
  { text: "German few-shot exemplars (leakage-free) + lexical tag canonicalization at enrichment — measured: 2/80 items touched, both toward gold, zero regressions", options: { bullet: true, breakLine: true } },
  { text: "Per-item eval persistence — full per-item predictions kept per run, so future model-score calibration can pool dated runs", options: { bullet: true } },
], { ...BODY, x: 0.8, y: 1.98, w: 5.8, h: 3.9, fontSize: 11.5, paraSpaceAfter: 6 });
s.addText("The 188-signal run — completed 4 Aug", { ...HEAD, x: 7.0, y: 1.55, w: 5.7, h: 0.38, fontSize: 16, bold: true, color: WARN });
s.addText([
  { text: "It had never been un-run — it had been SILENTLY BROKEN. The gateway 403s Python-urllib's default User-Agent, and the script exited 0 after writing an empty file. A green exit code on an empty result, for weeks", options: { bullet: true, breakLine: true } },
  { text: "Now: 188/188 signals enriched — the pending cells in §5A.3–5A.5 are closed and all three predictors sit on ONE gold standard", options: { bullet: true, breakLine: true } },
  { text: "Changed #1 — RQ3 split into RQ3a (accuracy) and RQ3b (equity): the equity result turned out to be the substantive one", options: { bullet: true, breakLine: true } },
  { text: "Changed #2 — journey stage + owner now scored under a supplied inventory (§5A.4.1); they were \"labelled but not scored\" in every prior draft", options: { bullet: true, breakLine: true } },
  { text: "Changed #3 — a cross-language fairness claim was RETRACTED: language is confounded with sector here, so the aggregate DE-vs-EN comparison would restate sector composition", options: { bullet: true } },
], { ...BODY, x: 7.2, y: 1.98, w: 5.5, h: 4.0, fontSize: 11, paraSpaceAfter: 5 });
s.addShape("roundRect", { x: 0.6, y: 6.15, w: 6.4, h: 0.85, rectRadius: 0.06, fill: { color: "F4F7FC" }, line: { color: ICE, width: 1 } });
s.addText("Method note: each evaluation change ships as one measured iteration — gap → root cause → intervention → in-run paired A/B — with the negative result (p=0.219 at n=80) reported, not re-rolled.",
  { ...BODY, x: 0.8, y: 6.24, w: 6.0, h: 0.7, fontSize: 10.5, margin: 0 });
s.addNotes("2 min — this is the slide that earns the meeting. Do not soften the right-hand failure story: a script that exits 0 on an empty output is exactly the failure mode this thesis warns about elsewhere (declared controls are not enforced controls), and it happened in my own harness. The fix was a User-Agent header plus a loud failure on an empty result set. Then land the three consequences in order — the third matters most methodologically, because retracting a claim I had already written is the same discipline as withholding the urgency claim at n=80. Hashes: golden set 80→100 + churn-musing exemplar 58504f3 · two-tag DE rubric + published n=100 run 5d250fb · per-language metrics + model card 8a258f8 · German exemplars e454898 · tag canonicalization e8af0e5 (claim revised to measured reality in c43062e) · per-item persistence + entity rollup 6412810. August: unblock the LLM path 26bf75d · first completed run e032d16 · results into Ch5 eeebbad · retract the confounded fairness claim d3059c9 · RQ3a/RQ3b restatement 79b80ab · journey+owner scoring b75ed6b.");

// ---------- 7 · Evaluation design ----------
s = pres.addSlide();
title(s, "Evaluation: two independent streams", "Objective accuracy × practitioner judgement — neither alone suffices");
loopMotif(s, 11.4, 0.45, 3);
s.addImage({ path: `${T}/diagrams/rendered/07_evaluation_pipeline.png`, x: 0.6, y: 1.75, w: 10.4, h: 4.05 });
s.addText("188 real, public, paraphrased signals · 3 sectors (fintech / food delivery / B2B industrial) · EN+DE · human seed labels, authored independently of the artifact. All three predictors — lexicon floor, classical ML, LLM path — have now been scored against this gold (the LLM row completed 4 Aug). Separately: the artifact's own committed in-repo evaluation (100-case bilingual golden set — 72 EN / 28 DE, live LLM, published metrics) as convergent evidence on a different gold.",
  { ...BODY, x: 0.6, y: 5.95, w: 12.1, h: 0.95, fontSize: 13, color: MUTE });
s.addNotes("90s. Stress the honesty features: real data only (synthetic excluded), star ratings as a NON-CIRCULAR sentiment gold, seed labels external to the artifact, every number written by a reproducible harness — no hand-typed metrics. New since you last saw this: the third predictor row is filled in, so the next three slides compare like with like.");

// ---------- 8 · Quantitative results ----------
s = pres.addSlide();
title(s, "Result 1: triage accuracy is method-dependent", "Naive methods fail on real multilingual feedback; learned models are necessary");
loopMotif(s, 11.4, 0.45, 3);
const rows = [
  [{ text: "Predictor", options: { bold: true, color: WHITE, fill: NAVY } }, { text: "Sentiment acc (n=153)", options: { bold: true, color: WHITE, fill: NAVY } }, { text: "Risk macro-F1 (n=106)", options: { bold: true, color: WHITE, fill: NAVY } }],
  ["Lexicon / keyword floor", "0.37", "0.26"],
  ["TF-IDF + LogReg (5-fold CV)", "0.78", "0.65"],
  [{ text: "LLM enrichment path", options: { bold: true } }, { text: "0.86", options: { bold: true } }, { text: "0.68", options: { bold: true } }],
];
s.addTable(rows, { x: 0.6, y: 1.8, w: 7.3, colW: [3.4, 1.95, 1.95], fontFace: "Calibri", fontSize: 13, border: { color: ICE, pt: 1 }, rowH: 0.5, valign: "middle" });
s.addText("One gold standard, all three rows — the 188 externally seed-labelled signals. Sentiment is scored against the 1–5 star rating, which is independent of the text the classifier reads.",
  { ...BODY, x: 0.6, y: 3.85, w: 7.3, h: 0.5, fontSize: 11.5, italic: true, color: MUTE });
s.addText("The gain is NOT uniform — and the shape is the finding. Contextual reasoning buys a lot on sentiment (macro-F1 0.52 → 0.67) and little on severity (0.65 → 0.68): severity is carried by lexical markers that n-grams already learn. So the loop's precondition is satisfiable by more than one method, and a deployer weighing cost, latency and sovereignty gets a real decision rather than an instruction.",
  { ...BODY, x: 0.6, y: 4.4, w: 7.3, h: 1.3, fontSize: 12.5 });
s.addShape("roundRect", { x: 0.6, y: 5.72, w: 7.3, h: 1.2, rectRadius: 0.06, fill: { color: "F4F7FC" }, line: { color: ICE, width: 1 } });
s.addText("Convergent — a DIFFERENT gold standard, never merged into the table: on the artifact's own curated 100-case set (18 Jul, 72 EN / 28 DE) the same path scores 0.97 sentiment / 0.90 urgency. The divergence from 0.86 is expected — curated sets select for label clarity — and 0.86 is the figure the thesis quotes.",
  { ...BODY, x: 0.8, y: 5.82, w: 6.9, h: 1.05, fontSize: 11.5, color: NAVY, margin: 0 });
s.addImage({ path: `${T}/evaluation/results/risk_confusion.png`, x: 8.35, y: 1.8, w: 4.3, h: 3.82 });
s.addText("Keyword floor collapses risk to \"low\" — 19 of 27 critical signals missed. On sentiment the floor fails the same way: paraphrased operational complaints (\"transaction history cannot be exported…\") carry no sentiment words, so 58 of 94 negatives are misread as neutral. A substantive finding, not a strawman.",
  { ...BODY, x: 8.35, y: 5.72, w: 4.3, h: 1.2, fontSize: 11, color: MUTE, italic: true });
s.addNotes("2 min. The three-rung story — and note what changed since you last saw this slide: the bottom row used to be borrowed from a different gold standard because the LLM had never run on this harness. It has now, so the table is finally like-for-like, and the borrowed numbers moved down into the grey box where they are labelled as a separate standard. If probed on exemplars: at n=60 the A/B was not significant (p≈1.0); at n=80, after adding German exemplars, the exact-tag-set lift became significant (8.75%→28.75%, in-run paired McNemar p=0.001) while urgency stayed underpowered (81.25%→86.25%, p=0.219); at n=100, after the churn-musing calibration exemplar, urgency is significant too (83%→90%, p=0.039, third consecutive run) — the whole trajectory is reported, including the stages where nothing could be claimed. Tag metrics at n=100 are not comparable to the n=80 snapshot (new adversarial items + completed two-tag DE gold — disclosed, and it improves DE tags partly by construction). The in-run paired A/B is the designed inference; the model is non-deterministic even at temperature 0.");

// ---------- 8b · NEW: escalation equity (RQ3b) ----------
s = pres.addSlide();
title(s, "Result 2: whose problems reach a human at all", "RQ3b — equal opportunity: recall on the signals whose gold label warrants escalation");
loopMotif(s, 11.4, 0.45, 3);
stat(s, 0.8, 1.8, 3.6, "0 of 8", "critical German signals escalated by the keyword floor — none", WARN);
stat(s, 4.85, 1.8, 3.6, "87.5 / 87.8", "German / English escalation recall on the LLM path — near-parity", GOOD);
card(s, 8.9, 1.8, 3.8, 3.3, "What bounds this", "The German gold-escalate stratum is EIGHT signals — a 95% interval on 7 of 8 spans roughly 47–100%. Language is also confounded with sector here. So the claim is that METHOD CHOICE GOVERNS ESCALATION EQUITY ON THIS CORPUS — not that parity is established in general.\n\nEqual opportunity is the right criterion precisely because it conditions on the gold label, so it is not distorted by very different base rates (DE 17.8%, EN 69.5%).");
const eq = [
  [{ text: "Escalation recall (gold-escalate signals)", options: { bold: true, color: WHITE, fill: NAVY } }, { text: "n", options: { bold: true, color: WHITE, fill: NAVY } }, { text: "Keyword floor", options: { bold: true, color: WHITE, fill: NAVY } }, { text: "LLM path", options: { bold: true, color: WHITE, fill: NAVY } }],
  ["German", "8", { text: "0.0%", options: { bold: true, color: WARN } }, "87.5%"],
  ["English", "41", "19.5%", "87.8%"],
];
s.addTable(eq, { x: 0.8, y: 3.55, w: 7.6, colW: [3.4, 0.7, 1.75, 1.75], fontFace: "Calibri", fontSize: 13, border: { color: ICE, pt: 1 }, rowH: 0.5, valign: "middle" });
s.addShape("roundRect", { x: 0.8, y: 5.35, w: 11.9, h: 1.5, rectRadius: 0.06, fill: { color: NAVY } });
s.addText("The substantive Responsible-AI finding", { fontFace: "Calibri", x: 1.05, y: 5.47, w: 11.4, h: 0.32, fontSize: 13, bold: true, color: ICE, margin: 0 });
s.addText("An uneven triage layer does not merely score worse — it means some customers' problems are systematically less likely to reach a human at all. That is a fairness property of the LOOP, not of a classifier, and the choice of triage method largely determines it.",
  { fontFace: "Calibri", x: 1.05, y: 5.82, w: 11.4, h: 0.95, fontSize: 14, color: WHITE, margin: 0 });
s.addNotes("2 min — for an RAI thesis this is the most important results slide, and it did not exist before August. Say the 0-of-8 slowly and let it sit. The argument: everywhere else in this deck fairness is a design commitment; here it is a measured consequence of an engineering choice. Then volunteer the bounds before she asks — eight signals is a small stratum and language is confounded with sector, which is exactly why the aggregate 'German vs English accuracy' comparison was RETRACTED rather than defended (§5A.5). Equal opportunity survives that retraction because it conditions on the gold label. If she pushes on whether this generalises: it does not, and the thesis says so — it is a claim about this corpus and about method choice, which is still the actionable claim for a deployer.");

// ---------- 8c · NEW: routing fields and the gate ----------
s = pres.addSlide();
title(s, "Result 3: the numbers that justify the approval gate", "Journey stage and owner, scored under a supplied inventory — clears the floor, nowhere near autonomous");
loopMotif(s, 11.4, 0.45, 2);
const rt = [
  [{ text: "Routing field", options: { bold: true, color: WHITE, fill: NAVY } }, { text: "Classes", options: { bold: true, color: WHITE, fill: NAVY } }, { text: "Majority-class floor", options: { bold: true, color: WHITE, fill: NAVY } }, { text: "LLM (inventory supplied)", options: { bold: true, color: WHITE, fill: NAVY } }],
  ["Journey stage", "27", "0.20", { text: "0.59", options: { bold: true } }],
  ["Recommended owner", "51", "0.15", { text: "0.40", options: { bold: true } }],
];
s.addTable(rt, { x: 0.6, y: 1.8, w: 7.5, colW: [2.5, 1.0, 2.0, 2.0], fontFace: "Calibri", fontSize: 13, border: { color: ICE, pt: 1 }, rowH: 0.5, valign: "middle" });
s.addText("Both clear their floor by a wide margin — journey by ~3×, owner by ~2.5× — so the pipeline extracts real routing signal rather than guessing the modal class. And neither is remotely good enough to route unattended: an owner assignment correct two times in five would misroute the majority of problems.",
  { ...BODY, x: 0.6, y: 3.5, w: 7.5, h: 1.4, fontSize: 12.5 });
card(s, 8.4, 1.8, 4.3, 3.05, "What bounds this", "Supplied-inventory scoring is EASIER than production free-form generation, so 0.59 / 0.40 are an UPPER bound, not an estimate. n = 182 (six signals lost to endpoint errors). Macro-F1 across all classes is inflated by rare labels predicted correctly; restricted to classes with ≥5 gold examples it falls to 0.28 and 0.18 — the more conservative figures.");
s.addShape("roundRect", { x: 0.6, y: 5.05, w: 12.1, h: 1.8, rectRadius: 0.06, fill: { color: NAVY } });
s.addText("Why this strengthens the design rather than weakening it", { fontFace: "Calibri", x: 0.85, y: 5.18, w: 11.6, h: 0.32, fontSize: 13, bold: true, color: ICE, margin: 0 });
s.addText("The mandatory approval gate (DP4) is not friction added to an otherwise-reliable pipeline — it is the control that makes a pipeline of THIS accuracy safe to deploy at all. A system that routed on these numbers unattended would fail quietly and often. The honest reading: these fields are useful as a draft a human accepts or corrects, and useless as an unattended decision. The numbers force that reading; they were not chosen to support it.",
  { fontFace: "Calibri", x: 0.85, y: 5.52, w: 11.6, h: 1.25, fontSize: 13.5, color: WHITE, margin: 0 });
s.addNotes("90s. This slide is deliberately unflattering to the pipeline and that is the point — it is the strongest available answer to 'why not just let the agent route it?'. Expect the examiner question 'so your routing is only 40% accurate?' and answer it here rather than in the defense: yes, over 51 classes against a 15% floor, under a supplied inventory, and that is precisely the argument for human approval. Note this configuration mirrors deployment — a real workspace configures its owner list rather than inventing labels per signal — but it is still reported separately from the production-config numbers on the previous slides, never merged.");

// ---------- 9 · Learning loop measured ----------
s = pres.addSlide();
title(s, "Result 4: the memory steers, honestly bounded", "The perishable-learning mechanism, instrumented");
loopMotif(s, 11.4, 0.45, 3);
stat(s, 0.8, 2.2, 3.6, "21% → 71%", "share of a past remedy appearing in the new recommendation when retrieval is ON (66.7% adoption)");
stat(s, 4.85, 2.2, 3.6, "0.503", "alignment lift vs a same-run noise floor that absorbs model jitter", GOOD);
stat(s, 8.9, 2.2, 3.6, "0 / 2.5%", "PII leaks across the whole ledger / hallucination rate at the 17-Jul run (EN-scope check by construction)");
s.addShape("roundRect", { x: 0.8, y: 4.6, w: 11.7, h: 2.0, rectRadius: 0.06, fill: { color: "FDF3F3" }, line: { color: WARN, width: 1 } });
s.addText("The honest boundary", { ...BODY, x: 1.05, y: 4.75, w: 11.2, h: 0.35, fontSize: 14, bold: true, color: WARN, margin: 0 });
s.addText("Outcome data behind these learnings is still SIMULATED. Adoption shows the loop steers recommendations; whether the steered remedy is BETTER requires a live outcome contract on real data — the single most important open step. We claim mechanism, not benefit.",
  { ...BODY, x: 1.05, y: 5.12, w: 11.2, h: 1.35, fontSize: 14, margin: 0 });
s.addNotes("90s. This slide wins or loses trust. Lead with the number, land on the boundary: mechanism measured, benefit pending. Examiners reward the distinction — it's also written into the traceability matrix (next slide).");

// ---------- 10 · Proven vs pending ----------
s = pres.addSlide();
title(s, "What is proven, demonstrated, and pending", "The traceability matrix — the thesis's honesty map (Appendix D)");
loopMotif(s, 11.4, 0.45, 3);
const tm = [
  [{ text: "Claim", options: { bold: true, color: WHITE, fill: NAVY } }, { text: "Status", options: { bold: true, color: WHITE, fill: NAVY } }, { text: "Evidence", options: { bold: true, color: WHITE, fill: NAVY } }],
  ["Triage accuracy (H3, RQ3a)", "MEASURED", "three predictors, one gold standard (§5A.3–5A.4)"],
  ["Escalation equity (RQ3b)", "MEASURED (bounded)", "equal-opportunity recall; DE stratum n=8 (§5A.5)"],
  ["Routing fields (H4, H5)", "MEASURED (bounded)", "supplied inventory = upper bound (§5A.4.1)"],
  ["DP2 memory influence", "PARTIALLY MEASURED", "adoption 21→71%; outcomes simulated"],
  ["DP1 outcome contracts", "DEMONSTRATED", "designed + instrumented; live contract pending"],
  ["Practitioner value (RQ4)", "PENDING", "instruments ready; interviews NOT started"],
];
s.addTable(tm, { x: 0.6, y: 1.8, w: 12.1, colW: [4.4, 2.8, 4.9], fontFace: "Calibri", fontSize: 13, border: { color: ICE, pt: 1 }, rowH: 0.5, valign: "middle" });
s.addText("A claim's status is stated once, in one place, and the chapters must agree with it. This is the discipline that keeps a design-science thesis honest when the artifact is also a company — and it is exactly what the August run broke and I had to repair: three rows above changed status, so six locations in the manuscript disagreed with this matrix until this week.",
  { ...BODY, x: 0.6, y: 5.45, w: 12.1, h: 1.1, fontSize: 13, italic: true, color: MUTE });
s.addNotes("90s. Pre-empt the researcher-as-founder question here: externally-labelled gold sets, standardised instruments, reproducible harness, and this matrix. Conflict of interest is declared in the front matter and managed by method, not denial. If asked about the July external reviews (§5A.8): two independent LLM strategic reviews, 45 claims adversarially verified (27 confirmed / 13 partial / 2 refuted), 20 hardening PRs, 17/17 live production checks — and the refuted claims are themselves a finding: unsurfaced capability reads as absent.");

// ---------- 11 · Positioning ----------
s = pres.addSlide();
title(s, "Where this sits (August 2026)", "No single differentiator survives — the contribution is the combination");
loopMotif(s, 11.4, 0.45, 2);
const comp = [
  ["Amplitude", "ties feedback to behavioural/revenue data it owns — recommends, doesn't contract closure"],
  ["Medallia + Ada", "executes policy-aware workflows from insight — enterprise scale, published gains"],
  ["Sprinklr", "audit trails & agent evaluation — governance artefacts at enterprise level"],
  ["Dovetail / Enterpret", "SMB agents \"trigger real work\" / MCP breadth — no approval gates, no outcome measurement (verified)"],
];
comp.forEach((c, i) => card(s, 0.6, 1.75 + i * 1.22, 6.6, 1.08, c[0], c[1]));
s.addShape("roundRect", { x: 7.5, y: 1.75, w: 5.2, h: 3.4, rectRadius: 0.06, fill: { color: NAVY } });
s.addText("The unclaimed combination", { fontFace: "Calibri", x: 7.75, y: 1.95, w: 4.7, h: 0.4, fontSize: 15, bold: true, color: ICE, margin: 0 });
s.addText("Outcome contracts (verified closure)\n+ approval-gated cross-system action\n+ decaying learning memory\n+ EU-sovereign deployment\n+ accessible to 10–500-employee firms",
  { fontFace: "Calibri", x: 7.75, y: 2.4, w: 4.7, h: 2.6, fontSize: 14.5, color: WHITE, margin: 0 });
s.addShape("roundRect", { x: 7.5, y: 5.35, w: 5.2, h: 1.5, rectRadius: 0.06, fill: { color: "F4F7FC" }, line: { color: ICE, width: 1 } });
s.addText("Gartner (2025): >40% of agentic-AI projects cancelled by 2027 — for unclear business value and inadequate risk controls. Exactly the two failure modes this design answers.",
  { ...BODY, x: 7.72, y: 5.5, w: 4.8, h: 1.25, fontSize: 12.5, margin: 0 });
s.addText("Forrester retired its CFM Wave (Q1 2026): insight is commoditised; the new axes are autonomous action and trust.", { ...BODY, x: 0.6, y: 6.75, w: 6.6, h: 0.6, fontSize: 12, italic: true, color: MUTE });
s.addNotes("90s. Category has moved TOWARD the thesis: analysts declared the insight half commoditised. Each rival owns a fragment; nobody verifiably holds the combination — and we apply the same verification standard to ourselves (previous slide).");

// ---------- 12 · Limitations & future ----------
s = pres.addSlide();
title(s, "Limitations and what comes next", "Bounded claims, and the one experiment that matters most");
loopMotif(s, 11.4, 0.45, 3);
s.addText("Limitations (stated, not buried)", { ...HEAD, x: 0.6, y: 1.7, w: 6.0, h: 0.4, fontSize: 17, bold: true, color: NAVY });
s.addText([
  { text: "Modest, balanced corpus — characterises the pipeline, not a population", options: { bullet: true, breakLine: true } },
  { text: "New in August, from the completed run: language confounded with sector (one fairness claim retracted); DE escalate stratum n=8; routing scored only under a supplied inventory = upper bound; theme + action still unscored", options: { bullet: true, breakLine: true } },
  { text: "Qualitative study small-N, design-validity — no causal effect claims", options: { bullet: true, breakLine: true } },
  { text: "Researcher-as-designer-and-founder — managed by external labels, standard instruments, reproducibility", options: { bullet: true, breakLine: true } },
  { text: "Security review found 10 HIGH findings → hardened; not warranted multi-tenant", options: { bullet: true, breakLine: true } },
  { text: "Distinctive claims demonstrated + partially measured, not field-proven", options: { bullet: true } },
], { ...BODY, x: 0.8, y: 2.2, w: 5.8, h: 3.4, fontSize: 13, paraSpaceAfter: 8 });
s.addText("Future work", { ...HEAD, x: 7.0, y: 1.7, w: 5.7, h: 0.4, fontSize: 17, bold: true, color: NAVY });
s.addText([
  { text: "① One LIVE outcome contract on real data — scored by interrupted time series; then synthetic difference-in-differences as panels accumulate (Arkhangelsky et al., 2021)", options: { bullet: true, breakLine: true } },
  { text: "② Complete the evaluation's COVERAGE — unifying the two streams is DONE (4 Aug). What remains: theme + recommended action are still unscored (2 of 6 gold fields), routing needs scoring in the free-form production condition, and natural German data would break the language/sector confound", options: { bullet: true, breakLine: true } },
  { text: "③ Connector parity + broader pulls", options: { bullet: true, breakLine: true } },
  { text: "④ Standing fairness monitoring of routing across segments and languages", options: { bullet: true } },
], { ...BODY, x: 7.2, y: 2.2, w: 5.5, h: 3.4, fontSize: 13, paraSpaceAfter: 8 });
s.addNotes("90s. Say number ① slowly: the single most important next artifact — a real action, a real metric, a contract, a window, a verdict. The method is already specified (ITS, then SDID). Everything else is engineering.");

// ---------- 13 · Contributions (dark close) ----------
s = pres.addSlide(); s.background = { color: NAVY };
s.addText("Contributions", { fontFace: "Cambria", color: WHITE, x: 0.9, y: 0.55, w: 11.5, h: 0.8, fontSize: 36, bold: true });
const contribs = [
  ["A working artifact", "the full governed loop — signal to measured outcome to reusable learning — running end to end, in production, with real external writes"],
  ["Six design principles", "each with its cost: closure as contract, perishable memory, set-based severity, graduated authority, bounded model, adaptation by configuration"],
  ["A real-data evaluation", "188 multilingual signals, two independent gold standards; triage is method-dependent — and the choice of method is an EQUITY decision, not only an accuracy one"],
  ["Integral Responsible AI", "oversight designed beyond Art 14, transparency via Art 50(4), auditability that found its own gaps — governance as durable design commitment"],
];
contribs.forEach((c, i) => {
  const x = 0.9 + (i % 2) * 6.0, y = 1.7 + Math.floor(i / 2) * 2.15;
  s.addShape("roundRect", { x, y, w: 5.7, h: 1.95, rectRadius: 0.06, fill: { color: "2A3575" } });
  s.addText(c[0], { fontFace: "Calibri", x: x + 0.22, y: y + 0.15, w: 5.25, h: 0.4, fontSize: 16, bold: true, color: "02C39A", margin: 0 });
  s.addText(c[1], { fontFace: "Calibri", x: x + 0.22, y: y + 0.58, w: 5.25, h: 1.25, fontSize: 13, color: WHITE, margin: 0 });
});
s.addText("Closing the loop and governing the closing are not in opposition — they are two halves of one well-designed workflow.",
  { fontFace: "Calibri", color: ICE, x: 0.9, y: 6.15, w: 11.5, h: 0.5, fontSize: 16, italic: true });
s.addText("Thank you — questions welcome.", { fontFace: "Cambria", color: WHITE, x: 0.9, y: 6.75, w: 11.5, h: 0.5, fontSize: 18, bold: true });
s.addNotes("60s. Read the four contributions crisply, end on the one-liner, invite questions. Likely probes: novelty vs MemoryBank (answered on slide 5), founder COI (slide 10), simulated outcomes (slide 9), why not RCTs (slide 12 — ITS/SDID).");

pres.writeFile({ fileName: path.join(__dirname, "defense_deck.pptx") }).then(() => console.log("written"));
