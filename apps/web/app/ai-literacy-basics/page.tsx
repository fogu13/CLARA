import Link from "next/link";
import { notFound } from "next/navigation";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "AI literacy for feedback triage (EU AI Act Art. 4) — CLARA",
  description:
    "A free five-part primer for teams operating AI-assisted customer-feedback triage: how it works, where it fails, when to override, what human oversight means, where the audit trail lives.",
};

// Public Art. 4 lead magnet (external-review item 35): the in-product
// AI-literacy module's five screens, published as a free primer. Gated behind
// the launch flag — it goes public together with the Impressum, not before.
export const dynamic = "force-static";

const ENABLED = process.env.NEXT_PUBLIC_LEGAL_PAGES === "1";

const screens: Array<{ title: string; bullets: string[] }> = [
  {
    title: "1 · How AI triage works",
    bullets: [
      "The system reads incoming feedback signals and clusters them into problem themes — each backed by the exact customer quotes it came from.",
      "Every theme carries a model score blending signal volume, source count and the model's self-reported certainty. It is an uncalibrated heuristic, never a validated probability.",
      "A low model score means thin evidence: treat those themes as hypotheses to verify, not as facts.",
      "Nothing should execute on its own. Every consequential action belongs behind a human approval gate.",
    ],
  },
  {
    title: "2 · Known limitations",
    bullets: [
      "LLMs are non-deterministic: the same input can produce differently worded — occasionally differently classified — output on another run.",
      "Models hallucinate: a small share of outputs contains claims the evidence does not support. A measured, non-zero error rate is exactly why human review exists.",
      "Quality must be measured, not assumed: insist on published evaluation metrics with denominators, dataset dates and per-language breakdowns.",
    ],
  },
  {
    title: "3 · When and how to override",
    bullets: [
      "You are the editor-in-chief. Approving an AI proposal makes it your editorial decision (EU AI Act Art. 50(4)) — override whenever your judgement disagrees.",
      "Reject a proposal when the evidence does not support it. A rejection is a recorded decision, not a failure.",
      "Say \"needs more evidence\" when you cannot decide yet — keep the question open instead of forcing a call.",
      "Edit proposals before approving: the edited text is what ships, and your name stands behind it, not the model's.",
    ],
  },
  {
    title: "4 · What human oversight means (Art. 14)",
    bullets: [
      "No consequential action runs without an explicit human decision — that is the substance of meaningful oversight.",
      "Every decision should be stamped with reviewer and timestamp and stay permanently attached to the action.",
      "Human-reviewed content needs no AI label (Art. 50(4)); anything auto-published must carry an AI disclosure.",
    ],
  },
  {
    title: "5 · Where the audit trail lives",
    bullets: [
      "The full decision history — proposals, overrides, approvals — must be reviewable per case, with reviewer and timestamp.",
      "Every claim should link back to the underlying customer evidence.",
      "Works councils and auditors need exports; routine views should show role labels, not names, so no per-employee metric can be derived.",
    ],
  },
];

export default function AiLiteracyBasicsPage() {
  if (!ENABLED) notFound();
  return (
    <main style={{ maxWidth: 760, margin: "0 auto", padding: "48px 20px", lineHeight: 1.65 }}>
      <p style={{ fontSize: 13, letterSpacing: 1, textTransform: "uppercase", opacity: 0.6 }}>
        CLARA · Free primer
      </p>
      <h1 style={{ fontSize: 30, margin: "8px 0 12px" }}>
        AI literacy for customer-feedback triage
      </h1>
      <p style={{ opacity: 0.8 }}>
        Since 2 February 2025, Art. 4 of the EU AI Act obliges every deployer to ensure a
        sufficient level of AI literacy in the staff who operate AI systems. This five-part primer
        supports that duty for teams running AI-assisted feedback triage — any vendor&apos;s, not
        just ours. It is education, not legal advice, and reading it alone does not discharge the
        Art. 4 duty: pair it with role-specific training on your actual system.
      </p>
      {screens.map((screen) => (
        <section key={screen.title} style={{ marginTop: 28 }}>
          <h2 style={{ fontSize: 20, marginBottom: 8 }}>{screen.title}</h2>
          <ul style={{ paddingLeft: 20 }}>
            {screen.bullets.map((bullet) => (
              <li key={bullet} style={{ marginBottom: 6 }}>
                {bullet}
              </li>
            ))}
          </ul>
        </section>
      ))}
      <p style={{ marginTop: 32, fontSize: 14, opacity: 0.85 }}>
        CLARA ships this module in-product with a workspace-level delivery attestation — and
        deliberately no per-user completion tracking (that would itself be an employee-monitoring
        feature). Questions:{" "}
        <a href="mailto:hello@odradekai.com?subject=AI%20literacy" style={{ textDecoration: "underline" }}>
          hello@odradekai.com
        </a>
      </p>
      <p style={{ marginTop: 40, fontSize: 13, opacity: 0.6 }}>
        <Link href="/" style={{ textDecoration: "underline" }}>clara.odradekai.com</Link> ·{" "}
        <Link href="/security" style={{ textDecoration: "underline" }}>Security &amp; Trust</Link>
      </p>
    </main>
  );
}
