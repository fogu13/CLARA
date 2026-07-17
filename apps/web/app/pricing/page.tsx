import Link from "next/link";
import { notFound } from "next/navigation";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Pricing — CLARA",
  description:
    "Transparent EUR pricing for the governed feedback-to-outcome platform. Entry tier published — DACH procurement should never have to guess.",
};

// Public pricing (external-review item 31, user-approved tiers from
// business-ops/05-pricing-and-financial-model.md). Gated behind the same
// launch flag as the legal pages: pricing goes public together with the
// Impressum, not before it.
export const dynamic = "force-static";

const ENABLED = process.env.NEXT_PUBLIC_LEGAL_PAGES === "1";

const tiers = [
  {
    name: "Starter",
    price: "from €490/mo",
    anchor: "typically €690/mo, billed annually",
    bullets: [
      "Up to ~5,000 feedback signals / month",
      "1–2 connected sources",
      "Sentiment, urgency and adaptive theming — no taxonomy to build",
      "Governed insight synthesis and the full loop, standard depth",
      "EU data residency",
    ],
  },
  {
    name: "Growth",
    price: "from €1,500/mo",
    anchor: "typically €1,990/mo, billed annually",
    flagship: true,
    bullets: [
      "Up to ~50,000 signals / month, 5+ sources",
      "Everything in Starter, plus audit log on synthesis",
      "Automated loop closure: Signal → Insight → Action → Learning",
      "GDPR / EU AI Act reporting and API access",
      "Unlimited seats",
    ],
  },
  {
    name: "Enterprise",
    price: "custom",
    anchor: "from ~€5,000/mo",
    bullets: [
      "High-volume / unlimited signals and sources",
      "Outcome-grounded self-improving loop with full audit trail",
      "On-prem / local-model deployment option",
      "SSO, DPA, SLA — works-council pack included",
      "Regulated-industry onboarding (fintech, insurance)",
    ],
  },
];

export default function PricingPage() {
  if (!ENABLED) notFound();
  return (
    <main style={{ maxWidth: 900, margin: "0 auto", padding: "48px 20px", lineHeight: 1.6 }}>
      <p style={{ fontSize: 13, letterSpacing: 1, textTransform: "uppercase", opacity: 0.6 }}>
        CLARA · Pricing
      </p>
      <h1 style={{ fontSize: 32, margin: "8px 0 12px" }}>Transparent, in EUR, VAT-clear.</h1>
      <p style={{ opacity: 0.8, maxWidth: 640 }}>
        Published entry pricing because DACH procurement should never have to guess. Annual billing
        with a monthly option; annual prepay earns roughly two months free. Six-week governed
        pilots are available at €3–5k with pre-negotiated conversion.
      </p>
      <div style={{ display: "grid", gap: 16, gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))", marginTop: 28 }}>
        {tiers.map((tier) => (
          <section
            key={tier.name}
            style={{
              border: tier.flagship ? "2px solid #016f60" : "1px solid rgba(128,128,128,.35)",
              borderRadius: 12,
              padding: 20,
            }}
          >
            <h2 style={{ fontSize: 20, marginBottom: 2 }}>{tier.name}</h2>
            <p style={{ fontSize: 22, fontWeight: 700 }}>{tier.price}</p>
            <p style={{ fontSize: 13, opacity: 0.65, marginBottom: 10 }}>{tier.anchor}</p>
            <ul style={{ paddingLeft: 18, fontSize: 14 }}>
              {tier.bullets.map((bullet) => (
                <li key={bullet} style={{ marginBottom: 6 }}>
                  {bullet}
                </li>
              ))}
            </ul>
          </section>
        ))}
      </div>
      <p style={{ marginTop: 24, fontSize: 14, opacity: 0.8 }}>
        Signal overage is metered per 1,000 signals; heavy usage upgrades a tier instead of
        surprising you. No aggressive auto-renewal clauses.
      </p>
      <p style={{ marginTop: 24, fontSize: 14 }}>
        <a href="mailto:hello@odradekai.com?subject=CLARA%20pilot" style={{ textDecoration: "underline" }}>
          Start with a governed pilot →
        </a>
      </p>
      <p style={{ marginTop: 40, fontSize: 13, opacity: 0.6 }}>
        <Link href="/" style={{ textDecoration: "underline" }}>clara.odradekai.com</Link> ·{" "}
        <Link href="/security" style={{ textDecoration: "underline" }}>Security &amp; Trust</Link>
      </p>
    </main>
  );
}
