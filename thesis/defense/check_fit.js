// Overflow check for the deck. Larger fonts in fixed-height boxes is exactly how a
// deck breaks between "looks fine in the build log" and "clipped on the projector",
// so this estimates, per text box, how many lines the string needs at its font size
// and flags boxes whose estimated height exceeds the box.
//
// Run: node thesis/defense/check_fit.js
// Heuristic, not a renderer: Calibri/Cambria average glyph advance is ~0.50 em, line
// height ~1.22 em. It is tuned to be slightly pessimistic, so a WARN is worth a look
// rather than proof of clipping.
const path = require("path");
const pptxgen = require(path.join(__dirname, "..", "..", "node_modules", "pptxgenjs"));

const AVG_ADVANCE = 0.5;   // em per character
const LINE_HEIGHT = 1.22;  // em per line
const findings = [];
let slideNo = 0;

function estimate(text, opts, kind) {
  if (!opts || typeof opts.w !== "number" || typeof opts.h !== "number") return;
  const size = opts.fontSize || 12;
  const inset = 0.2; // pptxgenjs default text inset, both sides
  const usableW = Math.max(opts.w - inset, 0.3);
  const charsPerLine = Math.max(Math.floor((usableW * 72) / (AVG_ADVANCE * size)), 8);

  const raw = Array.isArray(text)
    ? text.map(t => (typeof t === "string" ? t : t.text || "")).join("\n")
    : String(text ?? "");
  // count wrapped lines per explicit paragraph, plus bullet indent cost
  const bulletPad = opts.bullet ? 3 : 0;
  const lines = raw.split("\n").reduce((n, para) => {
    const len = para.length + bulletPad;
    return n + Math.max(Math.ceil(len / charsPerLine), 1);
  }, 0);
  const spacing = (opts.paraSpaceAfter || 0) / 72;
  const needed = (lines * LINE_HEIGHT * size) / 72 + spacing * raw.split("\n").length;
  const ratio = needed / opts.h;
  if (ratio > 1.0) {
    findings.push({
      slide: slideNo, kind, size, ratio: +ratio.toFixed(2),
      box: `${opts.w.toFixed(2)}x${opts.h.toFixed(2)}in`,
      needed: +needed.toFixed(2), lines,
      text: raw.replace(/\s+/g, " ").slice(0, 68),
    });
  }
}

const origAddSlide = pptxgen.prototype.addSlide;
pptxgen.prototype.addSlide = function (...args) {
  const s = origAddSlide.apply(this, args);
  slideNo += 1;
  const myNo = slideNo;
  const origText = s.addText.bind(s);
  s.addText = (t, o) => { const keep = slideNo; slideNo = myNo; estimate(t, o, "text"); slideNo = keep; return origText(t, o); };
  const origTable = s.addTable.bind(s);
  s.addTable = (rows, o) => {
    // a table row that needs two lines at its font size is the usual table failure
    const size = (o && o.fontSize) || 12;
    const rowH = (o && o.rowH) || 0.4;
    (rows || []).forEach((row, ri) => {
      (row || []).forEach((cell, ci) => {
        const colW = o && o.colW ? o.colW[ci] : (o && o.w ? o.w / row.length : 2);
        const txt = typeof cell === "string" ? cell : (cell && cell.text) || "";
        estimate(txt, { w: colW, h: rowH, fontSize: size }, `table r${ri}c${ci}`);
      });
    });
    return origTable(rows, o);
  };
  return s;
};

require(path.join(__dirname, "make_deck.js"));

setTimeout(() => {
  if (!findings.length) {
    console.log("FIT OK: no text box is estimated to overflow.");
    process.exit(0);
  }
  console.log(`${findings.length} box(es) estimated to overflow:\n`);
  findings.sort((a, b) => b.ratio - a.ratio).forEach(f => {
    console.log(`  slide ${String(f.slide).padStart(2)}  ${String(f.ratio).padStart(5)}x  ${f.kind.padEnd(12)} ${String(f.size).padStart(4)}pt  ${f.box.padEnd(12)} "${f.text}"`);
  });
  process.exit(1);
}, 1500);
