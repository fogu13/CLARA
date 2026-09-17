// MSc thesis progress deck, OPIT RAI-9001. Rebuilt 21 Aug 2026 for the 22 Aug advisor review.
// 16 slides in the main line, ending on the asks, with backup slides behind them.
// House style: navy 1E2761 with ice CADCFC support, Cambria heads, Calibri body.
//
// Writing rules for this file, matching the 20 Aug manuscript line edit:
//   - no em dashes anywhere in slide text or speaker notes; en dashes only inside numeric ranges
//   - plain declarative sentences, first person in the notes, no rhetorical "not X but Y" framing
//   - nothing on a slide that is decoration rather than argument
const path = require("path");
const pptxgen = require("pptxgenjs");
const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE"; // 13.3 x 7.5

const NAVY = "1E2761", ICE = "CADCFC", WHITE = "FFFFFF", INK = "1A1A2E",
      MUTE = "5A6478", GOOD = "2C5F2D", WARN = "990011", ACCENT = "02C39A",
      PANEL = "F4F7FC", ALERT = "FDF3F3";
const T = path.join(__dirname, "..");                                        // thesis/
const W = path.join(__dirname, "..", "..", "apps", "web", "public", "images"); // product screenshots
const HEAD = { fontFace: "Cambria", color: INK }, BODY = { fontFace: "Calibri", color: INK };

let page = 0;
function slide(dark) {
  const s = pres.addSlide();
  if (dark) s.background = { color: NAVY };
  page += 1;
  if (!dark) s.addText(String(page), { ...BODY, x: 12.5, y: 6.98, w: 0.5, h: 0.28, fontSize: 11, color: MUTE, align: "right", margin: 0 });
  return s;
}
function title(s, txt, sub) {
  s.addText(txt, { ...HEAD, x: 0.6, y: 0.32, w: 12.1, h: 0.76, fontSize: 30, bold: true });
  if (sub) s.addText(sub, { ...BODY, x: 0.6, y: 1.0, w: 12.1, h: 0.4, fontSize: 15, color: MUTE });
}
function card(s, x, y, w, h, hd, body, opts = {}) {
  s.addShape("roundRect", { x, y, w, h, rectRadius: 0.06, fill: { color: opts.fill || PANEL }, line: { color: opts.line || ICE, width: 1 } });
  s.addText(hd, { ...BODY, x: x + 0.18, y: y + 0.1, w: w - 0.36, h: 0.3, fontSize: 14.5, bold: true, color: opts.headColor || NAVY, margin: 0 });
  s.addText(body, { ...BODY, x: x + 0.18, y: y + 0.42, w: w - 0.36, h: h - 0.54, fontSize: opts.size || 12, color: opts.bodyColor || INK, margin: 0 });
}
function panel(s, x, y, w, h, hd, body, opts = {}) { // dark emphasis block, one per slide at most
  s.addShape("roundRect", { x, y, w, h, rectRadius: 0.06, fill: { color: opts.fill || NAVY } });
  if (hd) s.addText(hd, { fontFace: "Calibri", x: x + 0.22, y: y + 0.12, w: w - 0.44, h: 0.3, fontSize: 14, bold: true, color: ICE, margin: 0 });
  s.addText(body, { fontFace: "Calibri", x: x + 0.22, y: y + (hd ? 0.46 : 0.18), w: w - 0.44, h: h - (hd ? 0.58 : 0.3), fontSize: opts.size || 13.5, color: WHITE, margin: 0 });
}
function stat(s, x, y, w, big, label, color) {
  s.addText(big, { ...HEAD, x, y, w, h: 0.8, fontSize: 46, bold: true, color: color || NAVY, align: "center", margin: 0 });
  s.addText(label, { ...BODY, x, y: y + 0.84, w, h: 0.98, fontSize: 13, color: MUTE, align: "center", margin: 0 });
}
function bullets(s, items, opts) {
  s.addText(items.map((t, i) => ({ text: t, options: { bullet: true, breakLine: i < items.length - 1 } })),
    { ...BODY, fontSize: 13.5, paraSpaceAfter: 7, ...opts });
}
function sub(s, txt, x, y, w, color) {
  s.addText(txt, { ...HEAD, x, y, w, h: 0.34, fontSize: 17, bold: true, color: color || NAVY });
}
function table(s, rows, opts) {
  const header = rows[0].map(c => ({ text: c, options: { bold: true, color: WHITE, fill: NAVY } }));
  s.addTable([header, ...rows.slice(1)], {
    fontFace: "Calibri", fontSize: 14, border: { color: ICE, pt: 1 }, rowH: 0.5, valign: "middle", ...opts,
  });
}
// Colour key for the architecture diagram. The colour convention carries the
// architectural claim, so it gets a key rather than a sentence.
function legend(s, x, y, entries) {
  let cx = x;
  entries.forEach(([fill, stroke, label]) => {
    s.addShape("roundRect", { x: cx, y: y + 0.04, w: 0.2, h: 0.2, rectRadius: 0.03, fill: { color: fill }, line: { color: stroke, width: 1.25 } });
    s.addText(label, { ...BODY, x: cx + 0.28, y, w: label.length * 0.096 + 0.25, h: 0.3, fontSize: 12.5, color: INK, margin: 0, valign: "middle" });
    cx += label.length * 0.096 + 0.62;
  });
}

// ---------- 1. Title ----------
let s = slide(true);
s.addText("Closing the Loop, Building the Memory", { fontFace: "Cambria", color: WHITE, x: 0.9, y: 1.8, w: 12.0, h: 1.45, fontSize: 44, bold: true });
s.addText("A design science study of a governed platform that turns customer feedback into\nmeasured action and reusable organisational learning",
  { fontFace: "Calibri", color: ICE, x: 0.9, y: 3.3, w: 11.8, h: 0.95, fontSize: 21 });
["Signal", "Insight", "Action", "Learning"].forEach((l, i) => {
  s.addShape("ellipse", { x: 0.95 + i * 1.95, y: 4.5, w: 0.46, h: 0.46, fill: { color: i === 3 ? ACCENT : ICE } });
  s.addText(String(i + 1), { x: 0.95 + i * 1.95, y: 4.49, w: 0.46, h: 0.48, align: "center", fontSize: 19, bold: true, fontFace: "Calibri", color: NAVY, margin: 0 });
  s.addText(l, { x: 1.48 + i * 1.95, y: 4.55, w: 1.4, h: 0.38, fontSize: 17, fontFace: "Calibri", color: WHITE, margin: 0 });
});
s.addText("Elvis Shehi  ·  MSc Responsible Artificial Intelligence  ·  OPIT  ·  Supervisor: Prof. Zorina Alliata",
  { fontFace: "Calibri", color: ICE, x: 0.9, y: 6.35, w: 11.5, h: 0.35, fontSize: 14.5 });
s.addText("Progress review, 22 August 2026", { fontFace: "Calibri", color: ACCENT, x: 0.9, y: 6.74, w: 11.5, h: 0.35, fontSize: 14.5, bold: true });
s.addNotes("40 seconds. Thanks for the time. Frame it in one line: organisations collect more feedback than ever and rarely verify that acting on it resolved anything, and this thesis builds and evaluates a platform where the loop is governed and measured and where what worked is kept. Then say straight away that today is a progress review and that the second slide is the whole meeting, so she can steer from there.");

// ---------- 2. Executive summary ----------
s = slide();
title(s, "Executive summary", "Where the thesis stands, what moved in the last two weeks, and what I need from you");
card(s, 0.6, 1.55, 5.95, 1.5, "Built and running", "The artifact runs the whole loop in production. Signal in, insight, approved action out to Jira and Slack, outcome measured against a contract, learning kept and retrieved on the next decision.");
card(s, 6.75, 1.55, 5.95, 1.5, "Measured", "The quantitative evaluation is complete on 188 real seed-labelled signals. Three predictors now sit on one gold standard, with paired significance tests between all three.");
card(s, 0.6, 3.2, 5.95, 1.5, "The result that matters", "Triage accuracy depends on the method, and the method can change whose problems reach a human. On eight German-source signals whose label warrants escalation: floor none, learned model five, contextual path seven (descriptive; no predictor ranking).");
card(s, 6.75, 3.2, 5.95, 1.5, "What has not moved", "The practitioner study is still at zero interviews, and the outcome data behind the learning loop is still simulated. Both sit on the critical path to submission.", { headColor: WARN });
panel(s, 0.6, 4.95, 12.1, 1.8, "What I need from you today",
  "1. The ethics step. The consent form still says to check with you, and the manuscript already says the study runs under confirmed OPIT expectations. One of those has to change.\n2. Help reaching practitioners, so that twelve to fifteen sessions in September is realistic.\n3. Scope. Of the evidence still outstanding, which do you consider required for submission and which is honest future work.", { size: 14.5 });
s.addNotes("90 seconds, and this slide is the meeting. One line per box, then stop on the three asks and say that the rest of the deck is the evidence behind them. If she wants to go straight into a question, let her. The results slides work as backup just as well as in sequence.");

// ---------- 3. Research questions and method ----------
s = slide();
title(s, "Research questions and method", "Design science research, so the artifact is the research output (Hevner, 2004; Peffers et al., 2007)");
const rqs = [
  ["RQ1. Core", "How can an artifact make actions governed, executed and verified to have closed, and turn what worked into learning that is reused?"],
  ["RQ2. Governance", "What design lets automated action meet the EU AI Act and GDPR without slowing practitioners more than the risk warrants?"],
  ["RQ3a. Accuracy", "How accurately does AI enrichment and routing reproduce reference labels on real feedback, across sectors? Answered: three predictors on one gold standard."],
  ["RQ3b. Equity", "Is triage reliability equal across language strata, defined here by the source review's language? Answered, and tightly bounded."],
];
rqs.forEach((r, i) => card(s, 0.6 + (i % 2) * 6.15, 1.55 + Math.floor(i / 2) * 1.42, 5.95, 1.28, r[0], r[1], { size: 13 }));
card(s, 0.6, 4.42, 12.1, 1.05, "RQ4. Practitioner value",
  "How do practitioners judge usefulness, usability and trust? Twelve to fifteen interviews and task sessions with SUS and TAM, plus an anonymous survey for breadth. Not started, and it is the critical path.", { headColor: WARN, size: 13 });
s.addShape("roundRect", { x: 0.6, y: 5.65, w: 12.1, h: 1.15, rectRadius: 0.06, fill: { color: PANEL }, line: { color: ICE, width: 1 } });
s.addText("Method: problem-centred DSRM. Problem, objectives, design and build, demonstrate, evaluate, communicate. The quantitative stream scores 188 real customer signals from English-language and German-language sources, held as English paraphrases. The qualitative stream is the practitioner study. The claims are about design validity, not about statistical effect sizes.",
  { ...BODY, x: 0.85, y: 5.78, w: 11.6, h: 0.95, fontSize: 14, margin: 0 });
s.addNotes("60 seconds. Why design science in one line: the question is what works by design, not what is. Then the change I need her view on. RQ3 became RQ3a and RQ3b after the August run, because the equity answer turned out to be the more important one and it was sitting inside RQ3 as a sub-clause. For a Responsible AI thesis that felt wrong. Say plainly that RQ4 has not started and that ask one and ask two are about unblocking it.");

// ---------- 4. The artifact ----------
s = slide();
title(s, "The artifact: one governed loop, end to end", "CLARA. The model advises at two named stages. Everything that acts on the outside world is ordinary code.");
s.addImage({ path: `${__dirname}/01_architecture_colour.png`, x: 0.6, y: 1.5, w: 12.1, h: 4.21 });
legend(s, 0.75, 5.85, [
  ["e2ecfd", "3b6ea5", "Model reasoning, only here"],
  ["ffffff", "5a6478", "Deterministic code"],
  ["fde2e2", "c0392b", "Governance control point"],
  ["eef0f4", "98a0ae", "Integrated external system"],
]);
s.addText("Two stages are model-driven. Everything that validates, resolves conflicts, executes and audits is testable code, so every point where the system can act is one you can name, test and audit. Execution targets shown are the design-level set; what ships today writes to Jira and Slack, and Zendesk is ingest only.",
  { ...BODY, x: 0.6, y: 6.22, w: 12.1, h: 0.76, fontSize: 13.5, color: MUTE });
s.addNotes("90 seconds. Walk it left to right once: sources, ingestion, enrichment, synthesis, rules, the approval diamond, execution, measurement, learning, with governance cutting across. Use the key deliberately, because the colours are the argument. Blue appears exactly twice and everything downstream of it is white. The sentence I want her to be able to check against the picture is that the model advises and never acts. The red diamond is a LangGraph interrupt node, not a UI confirmation, so there is no code path to an external effect that goes around it.");

// ---------- 5. The product surface ----------
s = slide();
title(s, "The same loop, as the running product", "Rebuilt on 13 August around one question: what needs a decision today");
s.addImage({ path: `${W}/product-loop-bar.jpg`, x: 0.6, y: 1.55, w: 5.95, h: 3.08 });
s.addImage({ path: `${W}/product-decision-queue.jpg`, x: 6.75, y: 1.55, w: 5.95, h: 3.08 });
s.addText("The loop bar. Signals, problems, decisions, actions, outcomes, each one clickable.",
  { ...BODY, x: 0.6, y: 4.68, w: 5.95, h: 0.52, fontSize: 13, color: MUTE });
s.addText("The decision queue. What is waiting on a human, with the evidence behind it.",
  { ...BODY, x: 6.75, y: 4.68, w: 5.95, h: 0.52, fontSize: 13, color: MUTE });
card(s, 0.6, 5.25, 12.1, 1.5, "The design argument, one layer up from the thesis",
  "Every count on this page comes from one shared status function, so the numbers reconcile by construction rather than by discipline. That is the same commitment the thesis makes about closure: an outcome contract is a foreign key at creation, not a status flag someone remembers to set. The Chapter 4 diagrams were re-rendered in September from the deployed build; the screenshots are from the 16 July build, before this redesign landed on 13 August.", { size: 13.5 });
s.addNotes("45 seconds. This is the first time the deck shows the artifact rather than a diagram of it, and the loop bar renders the thesis's five stages as software you can click. If she asks to see it live I can, but flag first that the Chapter 4 screenshots are the July build.");

// ---------- 6. Governance ----------
s = slide();
title(s, "Responsible AI as a property of the loop", "The loop itself is the control surface, so governance is not a separate module");
const gov = [
  ["Human approval, Article 14 and past it", "Every consequential action is a draft until a person approves it: the graph's approval node is a LangGraph interrupt, and no code path reaches an external effect without a recorded approval. Authority is graduated by consequence class, from draft to single approval to four-eyes. Designed past the Article requirement, because awareness alone does not de-bias an overseer (Laux and Ruschemeier, 2025; Siebert et al., 2023)."],
  ["Audit trail, Article 12", "Every action records the rule, the parameters, the executor and the result. The evidence pack is hashed at decision time, so evidence that changed afterwards is provable rather than arguable. Four-eyes approval is available for consequential actions."],
  ["Transparency, Article 50", "AI output carries its provenance, and human editorial review is the exemption mechanism, which makes the approval gate itself the compliance artefact. The 2026 Digital Omnibus moved the Annex III high-risk duties to December 2027 and left Article 50 on its August 2026 schedule."],
  ["Sovereignty and GDPR", "The model layer is provider agnostic, so it runs hosted, behind an EU gateway, or self-hosted. Direct identifiers are redacted before any text reaches a model; retention limits and workspace isolation are enforced in Postgres below the application. Sentiment on text is not emotion recognition under Article 3(39), which is biometric."],
];
gov.forEach((g, i) => card(s, 0.6 + (i % 2) * 6.15, 1.55 + Math.floor(i / 2) * 2.28, 5.95, 2.08, g[0], g[1], { size: 13 }));
s.addText("Closure has three levels. The ticket is done, the reporter is told, the metric moved. Closed means the third.",
  { ...BODY, x: 0.6, y: 6.25, w: 12.1, h: 0.45, fontSize: 15, color: NAVY, bold: true });
s.addNotes("2 minutes. This is the heart of the Responsible AI argument. Two lines matter most. The gate goes past Article 14 on purpose, because the legal literature says awareness measures alone do not de-bias overseers. And the audit instrumentation is what found the platform's own unenforced controls in July, which is governance working rather than governance claimed. Finish on the three levels of closure, because the results slides measure the first two and not yet the third.");

// ---------- 7. Since 8 August ----------
s = slide();
title(s, "What changed since we last spoke", "Two weeks of method work, a methodology review, and three new datasets");
sub(s, "Evaluation and method", 0.6, 1.5, 6.0);
bullets(s, [
  "Paired McNemar tests between all three predictors on identical items. The contextual path leads the learned model on sentiment (p = 0.029) and does not separate from it on severity (p = 0.644).",
  "The learned model joined the escalation equity table: 62.5% against 95.1% across the two strata, a 32.6-point gap on eight German-source items; descriptive, no ranking.",
  "Three more datasets collected and run on 21 August, held outside the frozen 188-signal corpus: Vodafone Germany, Delivery Hero across eight EU markets, German consumer banks.",
  "An AI-verbatim detector measured on 6,740 real texts and then refused, because it flags 15% of genuine reviews and 3x more in some languages than others.",
], { x: 0.8, y: 1.95, w: 5.8, h: 3.5 });
sub(s, "Manuscript and platform", 6.9, 1.5, 5.8);
bullets(s, [
  "A truth audit of the manuscript against the codebase. Three claims did not survive and were corrected in the thesis.",
  "A full line edit for plain voice. Every em dash is gone from the compiled document, and no claim or number changed.",
  "A conflict of interest disclosure that participants read before consent, plus a standing separation between the research and any commercial follow-up.",
  "Dashboard rebuilt around the decision queue on 13 August, public site replatformed on 14 August, and the public claims audited against shipped capability on 21 August.",
], { x: 7.1, y: 1.95, w: 5.6, h: 3.6 });
panel(s, 0.6, 5.55, 12.1, 1.2, null,
  "One thing did not move. RQ4 is still at zero interviews, zero survey responses and no ethics sign-off, and that is what I most need from this meeting.", { size: 15.5 });
s.addNotes("2 minutes, and I should not read the slide. The two items she will care about are the paired tests and the truth audit, and both are on the next slide in more detail. The point of the dark box is to be honest early rather than let it surface at the end: everything I could do without permission has moved, and the one thing that needs her has not.");

// ---------- 8. Two reviews ----------
s = slide();
title(s, "Two reviews, and what they cost", "One of the method by an outside reviewer, one of my own claims by me");
sub(s, "Methodology review, 8 August", 0.6, 1.5, 6.0);
card(s, 0.6, 1.92, 5.95, 2.2, "The finding that mattered most",
  "An embedding provider swap on 6 August silently invalidated every cosine similarity threshold in the system. Under the new model, wrong-category pairs sit between 0.73 and 0.88, so the inherited 0.55 mapping floor admitted everything and the 0.30 refusal floor could never refuse on similarity. Nothing had failed, and nothing had warned.", { size: 13 });
card(s, 0.6, 4.22, 5.95, 2.0, "What shipped, stated honestly",
  "11 findings, 10 recommendations, all ten implemented and merged. Two produced measured numbers, five shipped mechanism that only unit tests cover, and two are still open. Thresholds are now derived from a stated quantile rule and stored per embedder with the model name beside them.", { size: 13 });
sub(s, "Truth audit of my own manuscript, 20 August", 6.75, 1.5, 5.95);
card(s, 6.75, 1.92, 5.95, 2.2, "Three claims did not survive",
  "The evaluation run ledger was described as a committed record. It is excluded from version control, so it is not inspectable, and the thesis now discloses that as a reproducibility boundary.\n\nThe connector text was wrong in both directions. Five official API pull sources exist, and three named integrations do not.\n\n\"Up to thirteen source types\" was a design taxonomy presented as a capability.", { size: 11.5 });
card(s, 6.75, 4.22, 5.95, 2.0, "What I did about it",
  "I corrected the thesis rather than softening the wording, and the same audit ran over the public site the next day. Seven claims were corrected there, and three of them are now checks that run against production every 30 minutes and fail if the old wording comes back.", { size: 13 });
s.addText("The same lesson three times. A declared control is not an enforced control until somebody checks it. The platform in July, the method in August, my own writing last week.",
  { ...BODY, x: 0.6, y: 6.4, w: 12.1, h: 0.5, fontSize: 14.5, color: NAVY, bold: true });
s.addNotes("2 minutes, and this is the slide I would spend extra time on if she engages. The embedding story is the portable architecture lesson: cosine thresholds are not comparable across embedding models, so a provider swap that looks like a config change silently rewrites the behaviour of every semantic feature. Be honest about the residual, which is that the calibrated values live in the deployment environment and the in-code defaults are still the old ones. If she asks what is still open from the review: the one agreement number is the 40-item second risk rating (kappa 0.55 unweighted, 0.70 weighted); its independent human provenance is unverified (the owner attests a second person, the files identify no rater, and the 13 September review reports an AI-assistant task record with identical labels), so it is second-rating agreement and not a human check; there is none behind the in-repo golden set, and that remains the most attackable gap.");

// ---------- 9. Result 1: accuracy ----------
s = slide();
title(s, "Triage accuracy depends on the method", "Three predictors, one gold standard, paired tests on identical items");
table(s, [
  ["Predictor", "Sentiment accuracy (n = 153)", "Severity macro-F1 (n = 106)"],
  ["Keyword and lexicon floor", "0.37", "0.26"],
  ["TF-IDF and logistic regression", "0.78", "0.65"],
  [{ text: "Contextual model path (generic prompt)", options: { bold: true } }, { text: "0.86", options: { bold: true } }, { text: "0.68", options: { bold: true } }],
  ["Production enrichment stage, same model", "0.83", "0.41"],
  ["Production enrichment stage, production default", "0.84", "0.53"],
], { x: 0.6, y: 1.6, w: 7.4, colW: [3.4, 2.0, 2.0] });
card(s, 0.6, 3.62, 7.4, 1.3, "Paired McNemar on the same items, testing accuracy",
  "Both learned methods beat the floor (p < 0.0001). The contextual path leads the learned model on sentiment in all four runs (p = 0.02–0.03; 0.09 Holm-corrected, so exploratory) and ties it on severity. The production stage is within three points on sentiment (p = 0.23), one severity level below the seeds, and compares configurations, not the model alone.", { size: 10.5 });
s.addText("Contextual reasoning buys a great deal on sentiment and nothing demonstrable on severity, which lexical markers already carry. The production stage's severity shift is partly the seed labels' own calibration: a second rating, of unverified independent provenance, put seven of ten seed-critical items at high (kappa 0.55, weighted 0.70). The precondition can be met by more than one method; a deployer has a choice, not an instruction.",
  { ...BODY, x: 0.6, y: 5.1, w: 7.4, h: 1.5, fontSize: 14 });
s.addImage({ path: `${T}/evaluation/results/risk_confusion.png`, x: 8.35, y: 1.6, w: 4.3, h: 3.82 });
card(s, 8.35, 5.42, 4.3, 1.5, "How this is scored",
  "188 real public signals, paraphrased and de-identified; seed labels drafted by a language-model assistant, used as delivered. Sentiment is scored against the star rating, the one human-origin reference.", { size: 11 });
s.addNotes("2 minutes. Walk the three rungs, then go to the paired tests, which are new since she last saw this. The honest headline is that the contextual path is not measurably better than a TF-IDF model on severity at this sample size. The confusion matrix shows how the floor fails: it calls 19 of the 27 critical signals low and gets only 4 of them right, a recall of 0.15. Two caveats to have ready. The severity numbers come from Trade Republic and Henkel only, because Lieferando ships no risk label, so food delivery is absent from every n = 106 figure. And the learned model is five-fold cross-validated while the contextual path was run once at temperature 0. If she asks whether 0.86 or the 0.97 on the in-repo set is the real number: different gold standards, curated sets select for label clarity, and the thesis quotes the star-proxy figures (0.86 for the prompt, 0.83 and 0.84 for the production stage). New since August: the production stage was run on the corpus on both models, the generic prompt four times, and the production default is close to deterministic at temperature 0.");

// ---------- 10. Result 2: equity ----------
s = slide();
title(s, "Whose problems reach a human at all", "Equal opportunity, meaning recall on the signals whose gold label warrants escalation");
table(s, [
  ["Escalation recall", "n", "Keyword floor", "TF-IDF and LR", "Contextual path", "Production stage"],
  ["German-source", "8", { text: "0.0%", options: { bold: true, color: WARN } }, { text: "62.5%", options: { color: WARN } }, "87.5%", "62.5%"],
  ["English-source", "41", "19.5%", "95.1%", "87.8%", "53.7%"],
], { x: 0.6, y: 1.6, w: 7.7, colW: [2.2, 0.5, 1.4, 1.4, 1.2, 1.0] });
s.addText("On the eight German-source signals whose reference label warrants escalation: the floor escalates none, the learned model five, the contextual path seven. The learned model ties the contextual path on severity accuracy; its stratum recalls differ by 32.6 points, the contextual path's by 0.3, descriptive figures on eight items. One significant test beside a non-significant one does not compare the two gaps.",
  { ...BODY, x: 0.6, y: 3.2, w: 7.7, h: 1.3, fontSize: 13 });
card(s, 8.6, 1.6, 4.1, 3.5, "What bounds this",
  "The German-source escalate stratum is eight signals. A 95% interval on 7 of 8 runs from roughly 47% to 100%, on 5 of 8 from 25% to 92%.\nLanguage is confounded with sector on this corpus.\nThe texts are English paraphrases, so the mechanism cannot be German-language processing; what differs is what German-language customers wrote about, and how.\nThe aggregate cross-language accuracy comparison was retracted for the same reason.\nThe Fisher tests are within-predictor; no test on the difference between predictors' gaps has been run (Gelman and Stern, 2006).", { size: 11 });
panel(s, 0.6, 5.15, 12.1, 1.6, "The substantive Responsible AI finding",
  "An uneven triage layer does not only score worse. It means some customers' problems are systematically less likely to reach a human at all. That is a fairness property of the loop rather than of a classifier, and the choice of triage method largely determines it.", { size: 15.5 });
s.addNotes("2 minutes, and for a Responsible AI thesis this is the most important results slide. Read the zero out loud and then pause. Then make the new point: the middle column was added on 20 August and it shows that a respectable learned model has an observed gap of its own, so this is not only about a weak baseline. Say plainly, before she does, that the learned model's significant within-predictor test beside the contextual path's non-significant one does not rank the two predictors (Gelman and Stern, 2006): the eight-item stratum cannot carry a ranking, and the thesis reports the gaps descriptively and recommends per-stratum monitoring rather than a predictor. Volunteer the bounds before she asks. Be precise if she pushes: the supported claim is the paired one on the same eight signals, not a cross-stratum claim that German is handled worse than English, which this corpus cannot establish. If she asks whether it generalises, the answer is no, the thesis says so, and the claim is about method choice on this corpus. One more honest caveat if she presses on the zero: across the three new datasets the same floor escalates German-source signals at 0.36 and 0.40, so the zero here is the low end of what a keyword floor does, not a fixed property of it.");

// ---------- 11. A measured refusal ----------
s = slide();
title(s, "A detector I measured and did not ship", "Asked to flag AI-written verbatims before triage. The measurement decided the design.");
stat(s, 0.8, 1.9, 3.6, "15.0%", "of genuine reviews flagged by a stylometric detector at 81% recall. At 1 to 5% contamination that is 78 to 95 real customers per 100 flags.", WARN);
stat(s, 4.85, 1.9, 3.6, "0.326", "AUROC for a Binoculars cross-perplexity detector, English stratum. Below 0.5 is worse than chance: complaint text is the more predictable text.", WARN);
stat(s, 8.9, 1.9, 3.6, "3.0x", "spread in flag rate across languages, Greek 44.4% against Polish 14.8%, because the lexicon encoded English and German cues only.", WARN);
s.addText("The false flags skewed toward angrier reviews, 2.21 stars against 2.70. A feedback platform that quietly suppresses its most articulate critics has inverted its own purpose.",
  { ...BODY, x: 0.8, y: 3.95, w: 11.7, h: 0.55, fontSize: 14, bold: true, color: NAVY });
panel(s, 0.8, 4.6, 11.7, 2.15, "What shipped instead, and what it refuses",
  "Provenance, exact duplication, volume bursts against a source's own trailing median, and batch-level uniformity, annotated for a human rather than enforced. It abstains below ten words, which is 23% of a real corpus, and it reports its own flag rate per language so an uneven filter is visible before anyone excludes anything.\n\nPer-comment authorship attribution is not implemented. On the same 6,154 genuine reviews the shipped gate flags 0.86%, and every one is a true duplicate.", { size: 13 });
s.addNotes("90 seconds, and this is a Responsible AI slide rather than a feature slide. The story is that I was asked for a capability, built the two candidate detectors, measured them on 6,740 real texts and then declined to ship the capability. Land on the second number, because it is the one that surprises people: the strongest open method is worse than a coin flip in this domain, and the reason is structural rather than a tuning problem. Genuine complaints are formulaic, so they sit at the low-perplexity end where the method expects machines, and the sign of the signal actually flips between English and German. The link back to the previous slide is the 3.0x language spread: the same fairness failure that decides whose problems get escalated also decides whose problems get deleted. If she asks whether this belongs in the thesis, it is in 4.4 and 4.9 as a control and a threat, in 6.2 as a Responsible AI tension, and in Appendix D as a measured negative result, and ask six is partly about whether that is the right home.");

// ---------- 12. Replication outside the corpus ----------
s = slide();
title(s, "Does the pattern hold outside the frozen corpus", "Three datasets collected on 21 August, kept outside the 188 on purpose");
table(s, [
  ["Dataset", "Signals", "Sentiment accuracy, floor to learned", "Severity accuracy, floor to learned"],
  ["Vodafone Germany, telecom", "65", "0.31 to 0.54, p = 0.029", "0.48 to 0.56, p = 0.44"],
  ["Delivery Hero, eight EU markets", "86", "0.38 to 0.65, p = 0.001", "0.52 to 0.53, p = 1.0"],
  ["German consumer banks", "104", "0.41 to 0.62, p = 0.008", "0.43 to 0.52, p = 0.21"],
], { x: 0.6, y: 1.6, w: 12.1, colW: [4.3, 1.4, 3.2, 3.2] });
card(s, 0.6, 3.7, 5.95, 1.65, "What replicates, and what does not",
  "The sentiment result holds on all three. The severity result does not. On none of the three does the learned model separate from the keyword floor on severity, where on the thesis corpus it clearly did. Severity behaviour looks corpus dependent, and the discussion should say so.", { size: 13 });
card(s, 6.75, 3.7, 5.95, 1.65, "The equity gap, once more",
  "Vodafone is the only new set with two source strata large enough to compare: the learned model escalates German-source signals at 50% against 81.8% English-source. Same direction as its observed 32.6-point gap on the thesis corpus; draft labels, descriptive in both cases.", { size: 13 });
card(s, 0.6, 5.5, 12.1, 1.25, "What these are not",
  "They are outside the frozen corpus by design, and none of them changes a single number in the thesis. Their seed labels are drafts pending my review, so they are not gold. The texts are English paraphrases again, so they do not close the authored-German gap. The contextual path has not been run on them yet.", { headColor: WARN, size: 13 });
s.addNotes("90 seconds. Present this as exploratory replication and not as corpus growth, and say the corpus is still 188 in the same breath. The interesting half is the negative one: the severity advantage of a learned model over a keyword floor does not reproduce on any of the three new sets, which is a caution about how much weight the severity numbers can carry. The Vodafone escalation gap is the encouraging half, because it is an independent set in a different sector pointing the same way. Ask five on the last slide is about whether relabelling these to gold standard is required work before submission.");

// ---------- 13. Result 3: routing ----------
s = slide();
title(s, "Routing is good enough for a draft and not for a decision", "Journey stage and owner, scored with the class inventory supplied");
table(s, [
  ["Routing field", "Classes", "Majority class floor", "Model, inventory supplied"],
  ["Journey stage", "27", "0.20", { text: "0.59", options: { bold: true } }],
  ["Recommended owner", "51", "0.15", { text: "0.40", options: { bold: true } }],
], { x: 0.6, y: 1.6, w: 7.6, colW: [2.6, 1.0, 2.0, 2.0] });
s.addText("Both clear their floor by a wide margin, so the pipeline extracts real routing signal rather than guessing the modal class. Neither is close to routing unattended. An owner assignment that is right two times in five would misroute most of the problems it touches.",
  { ...BODY, x: 0.6, y: 3.15, w: 7.6, h: 1.3, fontSize: 14 });
card(s, 8.5, 1.6, 4.2, 2.85, "What bounds this",
  "Supplying the class inventory is easier than the free-form condition production runs, so 0.59 and 0.40 are an upper bound and not an estimate. n = 182, with six signals lost to endpoint errors. Restricted to classes with at least five gold examples, macro-F1 falls to 0.28 and 0.18.", { size: 12.5 });
panel(s, 0.6, 4.62, 12.1, 2.25, "Why this strengthens the design",
  "The approval gate is the control that makes a pipeline of this accuracy safe to deploy. These fields are useful as a draft that a human accepts or corrects, and unsafe as an unattended decision. I did not choose the numbers to make that argument. They are what the run produced, and I report them because they are the strongest available answer to the question of why the agent does not simply route it.\n\nSince the review, journey-stage routing can run the closed-inventory condition in production behind a flag, off by default. Measuring that condition is the next iteration.", { size: 14 });
s.addNotes("90 seconds. This slide is deliberately unflattering to the pipeline. It is the best answer I have to why the agent does not simply route it unattended. Expect the question about 40% accuracy and answer it here rather than at the defense. Yes, over 51 classes against a 15% floor, with the inventory supplied, and that is exactly the argument for human approval. If she probes the flag: journey stage only, owner routing was deliberately not implemented because there is no owner registry and an enum of invented owners would not mean anything.");

// ---------- 14. Result 4: memory ----------
s = slide();
title(s, "The memory steers the recommendation", "The mechanism is measured. The benefit is not.");
stat(s, 0.8, 1.95, 3.6, "21% to 71%", "share of a past remedy appearing in the new recommendation once retrieval is on, at 66.7% adoption");
stat(s, 4.85, 1.95, 3.6, "0.503", "alignment lift against a same-run noise floor that absorbs model jitter", GOOD);
stat(s, 8.9, 1.95, 3.6, "0 and 2.5%", "PII leaks across the local run ledger, and the hallucination rate at the 17 July run, English scope by construction");
s.addShape("roundRect", { x: 0.8, y: 4.4, w: 11.7, h: 1.85, rectRadius: 0.06, fill: { color: ALERT }, line: { color: WARN, width: 1 } });
s.addText("The boundary", { ...BODY, x: 1.05, y: 4.55, w: 11.2, h: 0.3, fontSize: 15, bold: true, color: WARN, margin: 0 });
s.addText("The outcome data behind these learnings is simulated. Adoption shows that the loop steers recommendations. Whether the steered remedy is better needs a live outcome contract on real data, which is the single most important open step in the thesis.",
  { ...BODY, x: 1.05, y: 4.9, w: 11.2, h: 1.25, fontSize: 15, margin: 0 });
s.addNotes("90 seconds. Lead with the number and land on the boundary. The distinction between a mechanism that is measured and a benefit that is not is the one an examiner rewards, and it is written into the traceability matrix on the next slide rather than only said out loud here. Ask four is exactly this trade-off.");

// ---------- 15. Traceability ----------
s = slide();
title(s, "What is proven, what is demonstrated, what is pending", "The traceability matrix, Appendix D");
table(s, [
  ["Claim", "Status", "Evidence"],
  ["Triage accuracy (RQ3a)", "Measured", "three predictors on one gold standard, with pairwise McNemar tests"],
  ["Escalation equity (RQ3b)", "Measured, bounded", "floor 0.0, learned 62.5, contextual 87.5 vs 87.8, production 62.5 vs 53.7; n = 8"],
  ["Routing fields", "Measured, bounded", "scored with the inventory supplied, which is an upper bound"],
  ["Perishable memory (DP2)", "Partially measured", "remedy adoption 21% to 71%; replicated on GLM-5.2, not on the production default; simulated outcomes"],
  ["Outcome contracts (DP1)", "Demonstrated", "designed, built and instrumented; one live contract still pending"],
  ["Method hardening", "Shipped, partly measured", "calibration and the refusal harness measured; the rest covered by unit tests"],
  ["Second-rating agreement", "Measured once, provenance unverified", "kappa 0.55 (0.70 weighted), 40 risk items; independent human provenance unverified, so no human check; none on golden set"],
  ["AI-verbatim detection", "Measured, refused", "0.86% flagged on 6,154 genuine reviews; per-comment authorship deliberately not implemented"],
  ["Practitioner value (RQ4)", "Pending", "instruments ready; interviews not started"],
], { x: 0.6, y: 1.55, w: 12.1, colW: [3.3, 2.6, 6.2], rowH: 0.5 });
s.addText("A claim's status is stated once, in one place, and every chapter has to agree with it. That is what the truth audit tested on 20 August. Where a chapter disagreed with this table, I changed the chapter.",
  { ...BODY, x: 0.6, y: 6.28, w: 12.1, h: 0.62, fontSize: 13, color: MUTE });
s.addNotes("90 seconds. Use this to pre-empt the founder question: externally authored labels, standard instruments, a reproducible harness, a declared conflict of interest, and this table. Since 20 August participants are told before consent that the interviewer built the prototype and has a commercial interest, there is a fourth consent checkbox, and there is a standing rule of no sales content in sessions and no commercial follow-up for six months. Be honest that the manuscript's method chapter does not yet cite that policy. The pending RQ4 row and the once-measured agreement row are what the asks are about.");

// ---------- 16. Limitations and next ----------
s = slide();
title(s, "Limitations and what comes next", "The bounds I state myself, and the one experiment that matters most");
sub(s, "Limitations", 0.6, 1.5, 6.0);
bullets(s, [
  "A modest, balanced corpus of 188 signals. It characterises the pipeline, not a population.",
  "Language is confounded with sector and the texts are English paraphrases, so every per-language result is a source-language stratum; one cross-language claim was retracted rather than defended.",
  "The German-source escalate stratum is eight signals.",
  "Routing is scored only with the inventory supplied, and two of the six gold fields are not scored at all.",
  "One agreement number: kappa 0.55 on 40 risk items, human provenance unverified, so no human check; none on golden set.",
  "Urgency exemplar effect tested at n = 60, 80, 100 without alpha spending; same-item re-runs bound model noise and do not replace alpha control, so the claim is exploratory.",
  "Outcome data behind the learning loop is simulated, so the distinctive claim is demonstrated and not field-proven.",
  "I am the designer, the founder and the researcher, managed by external labels, standard instruments and a reproducible harness.",
], { x: 0.8, y: 1.92, w: 5.8, h: 4.7, fontSize: 12.5 });
sub(s, "Next, in order of value", 6.9, 1.5, 5.8);
bullets(s, [
  "One live outcome contract on real data, scored by interrupted time series at the action date, then synthetic difference in differences as panels accumulate (Arkhangelsky et al., 2021). The estimator is already built and tested.",
  "The practitioner study. Twelve to fifteen interviews and task sessions, with the survey for breadth.",
  "A human rating with recorded provenance on a new sample of the risk seeds, and a first one on the golden set, with rater role, dates and AI access recorded: the existing kappa's independent human provenance is unverified, and repeats on the same forty items would not be replication.",
  "Score theme and recommended action by the semantic agreement procedure, closing the last two of six gold fields.",
  "Score routing in the free-form production condition, so the numbers describe the deployed system.",
  "Relabel the new multi-market data to gold standard, which would break the language and sector confound.",
], { x: 7.1, y: 1.92, w: 5.6, h: 4.7, fontSize: 12.5 });
s.addNotes("90 seconds. Say the first item slowly, because it is the single most important next artifact. One real action, one real metric, one contract, one window, one verdict. Everything else on the right is bounded work with a known method. Stop here and move to the asks.");

// ---------- 17. Questions ----------
s = slide();
title(s, "Questions for you", "Six decisions I would rather take with you than guess at");
const asks = [
  ["1. The ethics step", "Section 3.9 of my methodology already says the study runs under OPIT ethics expectations confirmed with you. My consent sheet is still headed draft and still tells me to check with you first. One of those has to change. Is there a required OPIT template, or is your confirmation the step, and may I record it as such?"],
  ["2. Recruitment, and what the survey can carry", "Recruitment has not started and nine days of August are left. If twelve to fifteen interviews is not realistic from here, is a survey-led section 5B acceptable with a smaller interview set for depth? And can you open any part of the OPIT network to me?"],
  ["3. Scope for the submission", "Of what is left, interviews, one live outcome measurement, a human rating with recorded provenance on a new sample (the existing kappa's independent human provenance is unverified), semantic scoring of two gold fields and free-form routing, which do you consider required and which is honest future work?"],
  ["4. Simulated outcomes", "Section 6.5 still calls one live outcome contract the most important next step. Is the thesis defensible with the contract demonstrated and perceived but not measured, or do I force one small live measurement in at the cost of interview time?"],
  ["5. Does RQ3b stand on its own", "The learned model shows an observed 32.6-point gap of its own on eight German-source signals, reported descriptively because within-predictor tests do not rank predictors. Is that enough as written, or do I need natural German-language data first? That decides whether relabelling the new corpora is required work."],
  ["6. Where the methodology review belongs", "An independent statistics and ML review produced eleven findings, all ten recommendations shipped, and none of it is written up in the thesis. The same is true of the three new corpora. Section 5A, an appendix, or the repository only?"],
];
asks.forEach((a, i) => card(s, 0.6 + (i % 2) * 6.15, 1.5 + Math.floor(i / 2) * 1.74, 5.95, 1.68, a[0], a[1], { size: 12 }));
s.addText("If we only get through three, they are one, two and three. I also need two dates: your realistic review turnaround on a compiled draft, and the thesis IP letter that is due on 31 August.",
  { ...BODY, x: 0.6, y: 6.78, w: 12.1, h: 0.5, fontSize: 13.5, bold: true, color: NAVY });
s.addNotes("This is where the second half of the meeting should go. Ask one, two and three first and write the answers down, because nothing from the last meeting was recorded and I do not want to re-ask them again in September. Four and five are quick and they shape the next two weeks. Six matters because none of the review work or the new corpora is written up anywhere in the thesis yet. On dates: the IP letter is due 31 August, the examining committee form has to be in at least a month before the defense, and the regulations want a complete draft with her first.");

// ================= Backup =================
s = slide(true);
s.addText("Backup", { fontFace: "Cambria", color: WHITE, x: 0.9, y: 2.9, w: 11.5, h: 0.9, fontSize: 40, bold: true });
s.addText("The problem  ·  Evaluation design  ·  System architecture  ·  The loop in motion  ·  Data model  ·  Design decisions  ·  Where this sits",
  { fontFace: "Calibri", color: ICE, x: 0.9, y: 3.85, w: 11.5, h: 0.8, fontSize: 17 });
s.addNotes("Do not present these. They exist so that any question has a slide behind it.");

// B1. The problem
s = slide();
title(s, "Feedback is collected, and then it stops", "Three failures the design has to answer");
card(s, 0.6, 1.55, 3.93, 2.2, "Closing the loop is the weak link", "Forrester's 2025 feedback-management series finds close-the-loop practice promising but ineffective, and the communication of feedback too slow to drive action (Forrester, 2025). Bone et al. (2017) show that how feedback is solicited changes what customers then spend, so collection is not neutral either.");
card(s, 4.68, 1.55, 3.93, 2.2, "Acting can make it worse", "A field experiment with about 1.5 million Uber customers. Apologies alone did not restore spending, and repeated apologies reduced it (Halperin et al., 2022). Action taken is not the same as problem solved.");
card(s, 8.76, 1.55, 3.94, 2.2, "What is learned is forgotten", "Organisational memory depreciates (Argote, 2013; Walsh and Ungson, 1991). Teams relearn the same lessons because nothing keeps which remedy worked, or how long ago.");
sub(s, "The four deficiencies the artifact targets", 0.6, 3.95, 12.1);
bullets(s, [
  "Signal fragmentation. Buyers describe more than a dozen places feedback arrives, with no single priority list.",
  "The gap from insight to action. No governed path from a finding to an execution.",
  "Unmeasured closure. Tickets get created, outcomes stay unknown.",
  "Lost memory. What worked is not retained, and not retrieved when it is needed again.",
], { x: 0.8, y: 4.35, w: 6.0, h: 2.35 });
panel(s, 6.95, 4.35, 5.75, 2.2, "The claim",
  "Closing the loop is a workflow and governance problem rather than an analytics problem. The two missing primitives are a measured outcome contract and a memory that expires.", { size: 15.5 });
s.addNotes("45 seconds if summoned. Anchor on the Forrester series for the gap, on Bone for why solicitation itself has effects, and on the Uber experiment for why acting without measuring is not enough. The fragmentation line is about the buyer's world, not about what CLARA connects to.");

// B2. Evaluation design
s = slide();
title(s, "How the evaluation is set up", "Two gold standards, deliberately kept apart");
s.addImage({ path: `${T}/diagrams/rendered/07_evaluation_pipeline.png`, x: 0.6, y: 1.6, w: 7.0, h: 2.72 });
card(s, 7.9, 1.55, 4.8, 2.4, "The thesis corpus", "188 real public signals, paraphrased and de-identified. Fintech 67, food delivery 82, B2B industrial 39. Source language English 102, German 84. Seed labels authored independently of the artifact.", { size: 13 });
card(s, 7.9, 4.1, 4.8, 2.4, "The artifact's own set", "100 curated bilingual cases committed in the repository, with published metrics served from the model card. Reported as convergent evidence and never merged into the tables, because the gold standards differ.", { size: 13 });
s.addText("Only real data. Synthetic sets are excluded by design. Sentiment is scored against the 1 to 5 star rating, which is independent of the text the classifier reads. Every number is written by a harness that can be re-run, and no metric in this deck was typed by hand.",
  { ...BODY, x: 0.6, y: 4.6, w: 7.0, h: 1.1, fontSize: 13.5, color: MUTE });
s.addNotes("60 seconds if summoned. The honesty features are the point: real data only, seed labels written before and outside the artifact, a non-circular sentiment reference, and a reproducible harness. Two gold standards exist, they disagree, and the thesis quotes the lower one.");

// B3. System architecture
s = slide();
title(s, "Inside the build", "Next.js on Vercel, FastAPI and LangGraph in Docker on a Hetzner EU VPS behind Caddy, Supabase Postgres");
card(s, 0.6, 1.55, 5.95, 2.1, "The runtime", "One typed LangGraph: enrich, synthesise, evaluate rules, interrupt for human approval, execute, measure, learn. The interrupt is the Article 14 gate, and there is no code path to an external effect that goes around it. About 89 REST endpoints across seven domain routers.");
card(s, 6.75, 1.55, 5.95, 2.1, "Deployment", "API in Docker on a Hetzner EU VPS behind Caddy. Frontend on Vercel. Supabase Postgres with pgvector and row-level tenant isolation. A live smoke test runs against production every 30 minutes and opens an issue after two consecutive failures.");
card(s, 0.6, 3.85, 5.95, 2.1, "Model layer and observability", "A provider-agnostic layer speaking the OpenAI protocol, so the model can be hosted, behind an EU gateway, or self-hosted. Langfuse tracing on the model stages. Severity scoring stays in deterministic code.");
card(s, 6.75, 3.85, 5.95, 2.1, "Connectors, stated precisely", "Five official API pull sources: Zendesk, Trustpilot, Apple App Store, Google Play, Google Business Profile. Two execution targets: Jira and Slack. Zendesk is ingest only. Everything else returns a draft.");
s.addText("Diagrams re-rendered from the September sources, which draw the deployed graph and tables. The numbers above are the verified ones.",
  { ...BODY, x: 0.6, y: 6.15, w: 12.1, h: 0.5, fontSize: 13, color: MUTE });
s.addNotes("90 seconds if summoned. She is an architecture director, so this is the strongest reserve slide. The claim to make is that the approval step is a graph interrupt rather than a UI convention, and the provider-agnostic model layer is what makes EU sovereignty a configuration question instead of a rewrite.");

// B4. The loop in motion
s = slide();
title(s, "The loop in motion", "Bounded model stages inside deterministic gates, with the governance touchpoints in red");
s.addImage({ path: `${T}/diagrams/rendered/04_pipeline_flow.png`, x: 0.7, y: 1.55, w: 2.05, h: 5.15 });
s.addImage({ path: `${T}/diagrams/rendered/05_sequence_hitl.png`, x: 3.05, y: 1.7, w: 9.55, h: 4.14 });
s.addText("Left: the pipeline as implemented, with the risk gate, the approval queue, the audit write, outcome measurement, and decayed-confidence retrieval feeding rule matching. Right: the same lifecycle as a sequence. The outcome contract is fixed before the action executes, so there is no choosing a friendly metric afterwards.",
  { ...BODY, x: 3.05, y: 5.95, w: 9.55, h: 0.9, fontSize: 13, color: MUTE });
s.addNotes("60 seconds if summoned. Two views of one loop. The memory sits inside the control flow rather than in a side store, and the contract is set at approval time.");

// B5. Data model
s = slide();
title(s, "The data model", "Contracts and learnings are tables, so closure is referential integrity");
s.addImage({ path: `${T}/diagrams/rendered/06_data_model_er.png`, x: 0.75, y: 1.5, w: 2.56, h: 5.35 });
card(s, 3.75, 1.6, 8.95, 1.5, "Closure", "actions_log binds one to one to outcome_contracts at creation, and outcome_measurements grade closure from operational to customer to outcome. A closed action is a row with evidence behind it.");
card(s, 3.75, 3.25, 8.95, 1.5, "Memory", "ab_learnings carry base_confidence and half_life_days, so decay is computed from columns and can be audited by query. Taxonomy nodes carry the same fields for theme drift.");
card(s, 3.75, 4.9, 8.95, 1.5, "Tenancy", "Every table is workspace-scoped and enforced by Postgres row-level security below the application, so an application bug cannot bypass it. The honest bound: this is not warranted for adversarial co-tenants, and pilots run single-workspace.");
s.addNotes("60 seconds if summoned. For an architecture audience the schema is the argument. The thesis's two primitives are tables with foreign keys rather than prose.");

// B6. Design decisions
s = slide();
title(s, "Five design decisions the literature does not resolve", "Each one implemented, and each one stated with its cost");
const dds = [
  ["1. Authority graduated by consequence class", "Every action is a draft; a person approves it, and consequential actions can require two. The first design cycle resolved rule conflicts by priority, specificity and de-duplication; the deployed build keeps rules as configuration and puts the decision with the reviewer. Cost: throughput is bounded by reviewer attention."],
  ["2. Confidence decay in learnings", "Memory as perishable: base times 0.5 to the power of age over half-life. MemoryBank decays chat memory; this decays action and outcome evidence. Cost: the half-life is a guess."],
  ["3. Cross-signal severity", "Severity comes from the corroborating set, using urgency, volume and sentiment, rather than from the loudest single voice. Cost: it can bury the rare catastrophic single signal, so it needs an override."],
  ["4. Past-learnings retrieval", "Decayed-confidence retrieval into new decisions, in the case-based reasoning lineage. Only human-validated conclusions are retrieval-eligible, so an unvalidated causal claim cannot launder itself into the next recommendation. Cost: retrieval quality gates usefulness."],
  ["5. Per-industry profiles", "Adaptation by configuration rather than fine-tuning, using named weight profiles over one scoring model. Cost: authored priors can encode stereotypes, and inspectability is the safeguard rather than a guarantee."],
];
dds.forEach((d, i) => {
  const col = i % 3, row = Math.floor(i / 3);
  card(s, 0.6 + col * 4.13, 1.6 + row * 2.5, 3.93, 2.3, d[0], d[1], { size: 12 });
});
panel(s, 8.86, 4.1, 3.87, 2.3, "Why each cost is stated",
  "A design principle that buys something for nothing is usually a platitude. The cost is what makes each decision defensible, and it is what a reader can argue with.", { size: 13.5 });
s.addNotes("2 minutes if summoned. Slow down on decay, because that is where an examiner probes novelty, and I cite the prior art myself rather than waiting to be caught. The retrieval gate is new since 8 August and it converts DP2 from memory with decay into memory with provenance.");

// B7. Positioning
s = slide();
title(s, "Where this sits", "No single differentiator survives scrutiny, so the contribution is the combination");
const comp = [
  ["Amplitude", "ties feedback to behavioural and revenue data it already owns. Recommends, does not contract closure."],
  ["Medallia with Ada", "executes policy-aware workflows from insight, at enterprise scale, with published gains."],
  ["Sprinklr", "audit trails and agent evaluation, so governance artefacts exist at enterprise level."],
  ["Dovetail and Enterpret", "SMB agents that trigger real work, and broad connector coverage. No approval gates and no outcome measurement that could be verified."],
];
comp.forEach((c, i) => card(s, 0.6, 1.6 + i * 1.22, 6.6, 1.08, c[0], c[1], { size: 12.5 }));
panel(s, 7.5, 1.6, 5.2, 3.35, "The unclaimed combination",
  "Outcome contracts with verified closure\nApproval-gated cross-system action\nA decaying learning memory\nEU-sovereign deployment\nReachable by companies of 10 to 500 people", { size: 15.5 });
card(s, 7.5, 5.2, 5.2, 1.5, "Two failure modes named by the analysts",
  "Gartner (2025) expects more than 40% of agentic AI projects to be cancelled by 2027, for unclear business value and inadequate risk controls. Those are the two this design answers.", { size: 13 });
s.addText("Forrester retired its customer feedback management Wave in Q1 2026. Insight is being treated as commoditised, and the new axes are autonomous action and trust.",
  { ...BODY, x: 0.6, y: 6.5, w: 7.6, h: 0.72, fontSize: 13, color: MUTE });
s.addNotes("90 seconds if summoned, and only for commercial questions. The category moved toward the thesis. Each rival owns a fragment and nobody verifiably holds the combination, and I apply the same verification standard to my own artifact, which is why the traceability slide says the outcome half is demonstrated rather than proven.");

pres.writeFile({ fileName: path.join(__dirname, "defense_deck.pptx") }).then(() => console.log("written"));
