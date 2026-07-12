"use client";

// W3 (EU AI Act Art. 4): shared content for the AI-literacy module and the
// printable AI-Literacy Pack. The five screens are pure i18n copy; the eval
// numbers are a CITED SNAPSHOT of the versioned eval report (apps/api/app/
// evals/reports/report_20260703T110119Z.json) — deliberately not live values,
// so the pack a customer files stays reproducible against that report.

import { useI18n } from "@/lib/i18n";

type Dict = ReturnType<typeof useI18n>["t"];

// First-login flag. localStorage ONLY: per-user completion tracking would be
// an employee-monitoring feature (works-council trap, see W1), so the server
// never learns who viewed the module.
export const AI_LITERACY_SEEN_KEY = "clara_ai_literacy_seen";

export function todayIso(): string {
  return new Date().toISOString().slice(0, 10);
}

export type LiteracyScreen = {
  title: string;
  bullets: string[];
  /** Render the eval-snapshot block after the bullets. */
  showEval?: boolean;
  /** Significance caveat rendered after the eval block. */
  caveat?: string;
  /** Closing bullets rendered after the eval block + caveat. */
  tail?: string[];
};

export function buildScreens(t: Dict): LiteracyScreen[] {
  const a = t.aiLiteracy;
  return [
    { title: a.s1Title, bullets: [a.s1B1, a.s1B2, a.s1B3, a.s1B4] },
    { title: a.s2Title, bullets: [a.s2B1], showEval: true, caveat: a.evalCaveat, tail: [a.s2B2] },
    { title: a.s3Title, bullets: [a.s3B1, a.s3B2, a.s3B3, a.s3B4] },
    { title: a.s4Title, bullets: [a.s4B1, a.s4B2, a.s4B3] },
    { title: a.s5Title, bullets: [a.s5B1, a.s5B2, a.s5B3, a.s5B4] },
  ];
}

/** Eval-report citation block: metric snapshot + source line (never live). */
export function EvalBlock({ t }: { t: Dict }) {
  const a = t.aiLiteracy;
  const rows: [string, string][] = [
    [a.evalSentiment, "96.7%"],
    [a.evalUrgency, "81.7%"],
    [a.evalTagF1, "0.81"],
    [a.evalHallucination, "6.7%"],
    [a.evalPii, "0"],
  ];
  return (
    <div className="print-avoid-break rounded-md border p-3">
      <p className="text-sm font-medium">{a.evalHeading}</p>
      <dl className="mt-2 grid grid-cols-2 gap-x-4 gap-y-2 text-sm sm:grid-cols-5">
        {rows.map(([label, value]) => (
          <div key={label}>
            <dt className="text-xs text-muted-foreground">{label}</dt>
            <dd className="font-semibold tabular-nums">{value}</dd>
          </div>
        ))}
      </dl>
      <p className="mt-2 text-xs text-muted-foreground">{a.evalCitation}</p>
    </div>
  );
}
