import Link from "next/link";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Security & Trust — CLARA",
  description:
    "How CLARA handles customer feedback data: EU residency, security measures, data-subject rights, AI transparency and the certification roadmap.",
};

// Public trust page (external-review "trust center v1"). Every claim below is
// verifiable in the codebase or deployment — evidence-scoped, no superlatives.
// Legal pages (Impressum, Datenschutzerklärung, AGB) ship with launch after
// legal review; this page covers the technical/security facts buyers ask first.
const sections: Array<{ title: string; items: string[] }> = [
  {
    title: "Hosting & data residency",
    items: [
      "The CLARA API and application data run on EU infrastructure: a dedicated server in Germany (Hetzner) and an EU-region Postgres (Supabase).",
      "The marketing site and dashboard front-end are served via Vercel's CDN; customer signal data is processed by the EU-hosted API, not the CDN.",
      "Self-hosting is supported: the API is a standard Docker deployment, and the AI endpoint is workspace-configurable to EU-hosted or fully local models.",
    ],
  },
  {
    title: "Security measures",
    items: [
      "TLS everywhere with HSTS; security headers (CSP, X-Frame-Options, X-Content-Type-Options, Referrer-Policy) on web and API responses.",
      "Row-level multi-tenancy (Postgres RLS keyed to the verified JWT), role-based access control enforced server-side.",
      "Webhook ingestion requires HMAC-SHA256 signatures; API keys are stored as hashes and shown exactly once.",
      "Approval decisions record the verified signer from the JWT — reviewer identity cannot be asserted by the request.",
      "Audit records are append-only; evidence packs carry a content hash so what an approver signed off on is provable later.",
    ],
  },
  {
    title: "Data subject rights & governance",
    items: [
      "GDPR Art. 17 (erasure) and Art. 20 (export) are product endpoints, not ticket queues.",
      "Works-council mode (§87 BetrVG): below-admin responses replace person-capable fields with role labels — no per-employee performance metric can be derived.",
      "EU AI Act Art. 50: non-human-reviewed outbound text carries an automatic AI disclosure; human-approved content records its reviewer.",
      "A live model card in-product shows the configured model, endpoint and measured evaluation quality (per-language accuracy with denominators and dataset date).",
    ],
  },
  {
    title: "AI transparency",
    items: [
      "Provider-agnostic: any OpenAI-compatible endpoint, including EU-hosted and self-hosted local models. No fine-tuning on customer data.",
      "Model outputs carry a model score (an uncalibrated heuristic — labeled as such), evidence links and stated limitations; thin evidence produces a refusal, not a guess.",
      "Outcome readouts are graded A–E by measurement design; manual entries are labeled 'unverified manual observation' and never conflated with instrumented measurements.",
    ],
  },
  {
    title: "Certifications & roadmap",
    items: [
      "ISO 27001: roadmapped — DACH shortlists filter on it; pursued as revenue and PII volume grow.",
      "BSI C5 (Type 1 → Type 2): sequenced after ISO 27001; doubles as NIS2/DORA supply-chain evidence.",
      "DORA ICT-annex and NIS2 supply-chain documentation are prepared for regulated pilots; a signed DPA (AVV) is available on request.",
    ],
  },
];

export default function SecurityPage() {
  return (
    <main style={{ maxWidth: 760, margin: "0 auto", padding: "48px 20px", lineHeight: 1.6 }}>
      <p style={{ fontSize: 13, letterSpacing: 1, textTransform: "uppercase", opacity: 0.6 }}>
        CLARA · Security &amp; Trust
      </p>
      <h1 style={{ fontSize: 32, margin: "8px 0 12px" }}>Evidence-scoped, EU-resident by design.</h1>
      <p style={{ opacity: 0.8 }}>
        This page states what is implemented today — verifiable in the product — not aspirations.
        Legal pages (Impressum, Datenschutzerklärung, AGB) ship with our launch after legal review;
        until then, request our DPA or ask anything at{" "}
        <a href="mailto:hello@odradekai.com" style={{ textDecoration: "underline" }}>
          hello@odradekai.com
        </a>
        .
      </p>
      {sections.map((section) => (
        <section key={section.title} style={{ marginTop: 32 }}>
          <h2 style={{ fontSize: 20, marginBottom: 8 }}>{section.title}</h2>
          <ul style={{ paddingLeft: 20 }}>
            {section.items.map((item) => (
              <li key={item} style={{ marginBottom: 6 }}>
                {item}
              </li>
            ))}
          </ul>
        </section>
      ))}
      <p style={{ marginTop: 40, fontSize: 13, opacity: 0.6 }}>
        © 2026 CLARA. Questions, security reports or DPA requests:{" "}
        <a href="mailto:hello@odradekai.com" style={{ textDecoration: "underline" }}>
          hello@odradekai.com
        </a>{" "}
        · <Link href="/">Back to clara.odradekai.com</Link>
      </p>
    </main>
  );
}
