// MSc thesis defense deck — 15–20 min, OPIT RAI-9001.
// Palette "Midnight Executive": navy 1E2761 dominant, ice CADCFC support, white accent.
// Motif: the loop stages as small navy circles with white numerals; Cambria heads + Calibri body.
const pptxgen = require("pptxgenjs");
const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE"; // 13.3 x 7.5

const NAVY = "1E2761", ICE = "CADCFC", WHITE = "FFFFFF", INK = "1A1A2E", MUTE = "5A6478", GOOD = "2C5F2D", WARN = "990011";
const T = "/Users/olamakri/Documents/Thesis_writing";
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
s.addNotes("60–90s. Frame in one breath: organisations collect more feedback than ever, yet fewer than a third systematically close the loop. This thesis designs, builds and evaluates a platform where the loop is not just closed but GOVERNED and MEASURED — and where what worked becomes organisational memory. One system, studied through Design Science Research.");

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
  ["RQ3 · Quantitative", "How accurately does AI enrichment/routing reproduce human labels on real feedback, across sectors & languages?"],
  ["RQ4 · Qualitative", "How do practitioners judge usefulness, usability, trustworthiness? (interviews + SUS/TAM — in progress)"],
];
rqs.forEach((r, i) => card(s, 0.6 + (i % 2) * 6.15, 1.75 + Math.floor(i / 2) * 1.85, 5.95, 1.65, r[0], r[1]));
s.addShape("roundRect", { x: 0.6, y: 5.6, w: 12.1, h: 1.25, rectRadius: 0.06, fill: { color: "F4F7FC" }, line: { color: ICE, width: 1 } });
s.addText("Method: problem-centred DSRM — problem → objectives → design & build → demonstrate → evaluate → communicate. Mixed-methods evaluation: a quantitative gold-set on 188 real, multilingual signals + a practitioner study (12–15 interviews, task sessions, SUS/TAM). Design-validity claims, not statistical effects.",
  { ...BODY, x: 0.85, y: 5.75, w: 11.6, h: 1.0, fontSize: 13.5, margin: 0 });
s.addNotes("90s. Say why DSR: the question is 'what works by design', not 'what is'. Note H1–H8 map under these four RQs. Flag honestly that RQ4 data collection is in progress — protocol and instruments are complete and in the appendix.");

// ---------- 4 · The artifact ----------
s = pres.addSlide();
title(s, "The artifact: a governed loop, end to end", "CLARA — Capture, Listen, Analyze, Respond, Adapt");
loopMotif(s, 11.4, 0.45, 2);
s.addImage({ path: `${T}/diagrams/rendered/01_architecture_logical.png`, x: 0.6, y: 1.7, w: 12.1, h: 4.25 });
s.addText("Deterministic code owns validation, conflict resolution, execution, audit. Language-model reasoning is confined to named, bounded stages. The points where the system can act are finite, named, individually auditable — that is what makes it governable.",
  { ...BODY, x: 0.6, y: 6.15, w: 12.1, h: 0.85, fontSize: 14, color: MUTE, italic: true });
s.addNotes("2 min. Walk the diagram left to right: sources → ingestion → enrich → synthesize → rules → the approval diamond → execute → measure → learn, with governance cross-cutting. Emphasise the architectural principle: bounded model, deterministic loop. Mention it exists in two builds; the evaluated build is CLARA (FastAPI + LangGraph).");

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

// ---------- 7 · Evaluation design ----------
s = pres.addSlide();
title(s, "Evaluation: two independent streams", "Objective accuracy × practitioner judgement — neither alone suffices");
loopMotif(s, 11.4, 0.45, 3);
s.addImage({ path: `${T}/diagrams/rendered/07_evaluation_pipeline.png`, x: 0.6, y: 1.75, w: 10.4, h: 4.05 });
s.addText("188 real, public, paraphrased signals · 3 sectors (fintech / food delivery / B2B industrial) · EN+DE · human seed labels, authored independently of the artifact. Plus: the artifact's own committed in-repo evaluation (60-case golden set, live LLM) as convergent evidence.",
  { ...BODY, x: 0.6, y: 6.0, w: 12.1, h: 0.85, fontSize: 13.5, color: MUTE });
s.addNotes("90s. Stress the honesty features: real data only (synthetic excluded), star ratings as a NON-CIRCULAR sentiment gold, seed labels external to the artifact, every number written by a reproducible harness — no hand-typed metrics.");

// ---------- 8 · Quantitative results ----------
s = pres.addSlide();
title(s, "Result 1: triage accuracy is method-dependent", "Naive methods fail on real multilingual feedback; learned models are necessary");
loopMotif(s, 11.4, 0.45, 3);
const rows = [
  [{ text: "Predictor", options: { bold: true, color: WHITE, fill: NAVY } }, { text: "Sentiment acc (n=153)", options: { bold: true, color: WHITE, fill: NAVY } }, { text: "Risk macro-F1 (n=106)", options: { bold: true, color: WHITE, fill: NAVY } }],
  ["Lexicon / keyword floor", "0.37", "0.26"],
  ["TF-IDF + LogReg (5-fold CV)", "0.78", "0.65"],
  ["LLM path (in-repo, 60-case golden set)", "0.97 (sentiment)", "0.82 (urgency)"],
];
s.addTable(rows, { x: 0.6, y: 1.8, w: 7.3, colW: [3.4, 1.95, 1.95], fontFace: "Calibri", fontSize: 13, border: { color: ICE, pt: 1 }, rowH: 0.5, valign: "middle" });
s.addText("Why the floor fails: paraphrased operational complaints (\"transaction history cannot be exported…\") carry no sentiment words — 58 of 94 negatives misread as neutral. Substantive finding, not a strawman.",
  { ...BODY, x: 0.6, y: 4.15, w: 7.3, h: 1.1, fontSize: 13 });
s.addText("Convergent in-repo run (CLARA, GLM-5.2, 3 Jul 2026): sentiment 96.7% · urgency 81.7% · theme 80.8% by meaning vs 45.8% exact — semantic scoring vindicated. Real-data star-proxy: ≈90% across all three sectors, zero fine-tuning.",
  { ...BODY, x: 0.6, y: 5.3, w: 7.3, h: 1.35, fontSize: 13, color: NAVY });
s.addImage({ path: `${T}/evaluation/results/risk_confusion.png`, x: 8.35, y: 1.8, w: 4.3, h: 3.82 });
s.addText("Keyword floor collapses risk to \"low\" — 19 of 27 critical signals missed.", { ...BODY, x: 8.35, y: 5.75, w: 4.3, h: 0.8, fontSize: 11.5, color: MUTE, italic: true });
s.addNotes("2 min. The three-rung story. Be precise about gold standards: the 0.37/0.78 rows are the thesis harness (188 seed-labelled signals); the LLM numbers are the artifact's committed in-repo eval on a DIFFERENT 60-case golden set — convergent evidence, not the same table. If probed: exemplar A/B lift was NOT significant at n=60 (McNemar p≈1.0) — we report that ourselves.");

// ---------- 9 · Learning loop measured ----------
s = pres.addSlide();
title(s, "Result 2: the memory steers, honestly bounded", "The perishable-learning mechanism, instrumented");
loopMotif(s, 11.4, 0.45, 3);
stat(s, 0.8, 2.2, 3.6, "21% → 71%", "share of a past remedy appearing in the new recommendation when retrieval is ON (66.7% adoption)");
stat(s, 4.85, 2.2, 3.6, "0.503", "alignment lift vs a same-run noise floor that absorbs model jitter", GOOD);
stat(s, 8.9, 2.2, 3.6, "0 / 6.7%", "PII leaks across ledger / hallucination rate, latest run");
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
  ["Triage quality (H3, RQ3)", "MEASURED", "two independent gold standards (§5A + in-repo)"],
  ["DP2 memory influence", "PARTIALLY MEASURED", "adoption 21→71%; outcomes simulated"],
  ["DP1 outcome contracts", "DEMONSTRATED", "designed + instrumented; live contract pending"],
  ["Loop end-to-end in production", "DEMONSTRATED", "real Jira/Slack push; interrupt fix verified"],
  ["Practitioner value (RQ4)", "PENDING", "instruments ready; interviews in progress"],
];
s.addTable(tm, { x: 0.6, y: 1.8, w: 12.1, colW: [4.4, 2.8, 4.9], fontFace: "Calibri", fontSize: 13.5, border: { color: ICE, pt: 1 }, rowH: 0.55, valign: "middle" });
s.addText("A claim's status is stated once, in one place, and the chapters must agree with it. This is the discipline that keeps a design-science thesis honest when the artifact is also a company.",
  { ...BODY, x: 0.6, y: 5.5, w: 12.1, h: 0.8, fontSize: 14, italic: true, color: MUTE });
s.addNotes("90s. Pre-empt the researcher-as-founder question here: externally-labelled gold sets, standardised instruments, reproducible harness, and this matrix. Conflict of interest is declared in the front matter and managed by method, not denial.");

// ---------- 11 · Positioning ----------
s = pres.addSlide();
title(s, "Where this sits (July 2026)", "No single differentiator survives — the contribution is the combination");
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
  { text: "Qualitative study small-N, design-validity — no causal effect claims", options: { bullet: true, breakLine: true } },
  { text: "Researcher-as-designer-and-founder — managed by external labels, standard instruments, reproducibility", options: { bullet: true, breakLine: true } },
  { text: "Security review found 10 HIGH findings → hardened; not warranted multi-tenant", options: { bullet: true, breakLine: true } },
  { text: "Distinctive claims demonstrated + partially measured, not field-proven", options: { bullet: true } },
], { ...BODY, x: 0.8, y: 2.2, w: 5.8, h: 3.4, fontSize: 13, paraSpaceAfter: 8 });
s.addText("Future work", { ...HEAD, x: 7.0, y: 1.7, w: 5.7, h: 0.4, fontSize: 17, bold: true, color: NAVY });
s.addText([
  { text: "① One LIVE outcome contract on real data — scored by interrupted time series; then synthetic difference-in-differences as panels accumulate (Arkhangelsky et al., 2021)", options: { bullet: true, breakLine: true } },
  { text: "② Unify the two LLM evidence streams on one gold standard; grow the golden set past significance", options: { bullet: true, breakLine: true } },
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
  ["A real-data evaluation", "188 multilingual signals, two independent gold standards; triage is method-dependent and the loop's precondition is satisfiable"],
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

pres.writeFile({ fileName: "/Users/olamakri/Documents/Thesis_writing/defense/defense_deck.pptx" }).then(() => console.log("written"));
