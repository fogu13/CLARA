"use client";

// Security & trust. Content policy (unchanged from the original page): every
// claim below is verifiable in the codebase or deployment — evidence-scoped,
// no superlatives. Bilingual via in-file content maps (the page is long-form
// prose, better kept together than scattered across 60 dictionary keys); the
// German version is a draft pending native-speaker review.

import { useI18n } from "@/lib/i18n";
import { CONTACT_EMAIL, useReveal } from "../site-shell";

type SecurityContent = {
  eyebrow: string;
  h1: string;
  intro: string;
  sections: { title: string; items: string[] }[];
  contact: string;
};

const EN: SecurityContent = {
  eyebrow: "CLARA · Security & Trust",
  h1: "Evidence-scoped, EU-resident by design.",
  intro:
    "This page states what is implemented today — verifiable in the product — not aspirations. Legal pages (Impressum, Datenschutzerklärung, AGB) ship after legal review; until then, request our DPA or ask anything at " +
    CONTACT_EMAIL +
    ".",
  sections: [
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
        "Audit records are append-only; evidence packs carry a content hash so what an approver signed off on is verifiable later.",
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
  ],
  contact: `Questions, security reports or DPA requests: ${CONTACT_EMAIL}`,
};

const DE: SecurityContent = {
  eyebrow: "CLARA · Sicherheit & Vertrauen",
  h1: "Evidenzbasiert, EU-resident by design.",
  intro:
    "Diese Seite beschreibt, was heute implementiert ist — im Produkt überprüfbar — keine Absichtserklärungen. Die Rechtsseiten (Impressum, Datenschutzerklärung, AGB) erscheinen nach juristischer Prüfung; bis dahin: AVV anfordern oder alles fragen unter " +
    CONTACT_EMAIL +
    ".",
  sections: [
    {
      title: "Hosting & Datenresidenz",
      items: [
        "CLARA-API und Anwendungsdaten laufen auf EU-Infrastruktur: dedizierter Server in Deutschland (Hetzner) und Postgres in einer EU-Region (Supabase).",
        "Marketing-Seite und Dashboard-Frontend werden über Vercels CDN ausgeliefert; Kundensignal-Daten verarbeitet ausschließlich die EU-gehostete API, nicht das CDN.",
        "Self-Hosting wird unterstützt: die API ist ein Standard-Docker-Deployment, und der KI-Endpunkt ist pro Workspace auf EU-gehostete oder vollständig lokale Modelle konfigurierbar.",
      ],
    },
    {
      title: "Sicherheitsmaßnahmen",
      items: [
        "Durchgehend TLS mit HSTS; Security-Header (CSP, X-Frame-Options, X-Content-Type-Options, Referrer-Policy) auf Web- und API-Antworten.",
        "Zeilenbasierte Mandantentrennung (Postgres RLS, gebunden an das verifizierte JWT), rollenbasierte Zugriffskontrolle serverseitig durchgesetzt.",
        "Webhook-Ingestion erfordert HMAC-SHA256-Signaturen; API-Schlüssel werden als Hashes gespeichert und genau einmal angezeigt.",
        "Freigabeentscheidungen protokollieren die verifizierte Identität aus dem JWT — die Prüferidentität kann nicht vom Request behauptet werden.",
        "Audit-Einträge sind append-only; Evidenzpakete tragen einen Content-Hash, sodass später überprüfbar ist, was freigegeben wurde.",
      ],
    },
    {
      title: "Betroffenenrechte & Governance",
      items: [
        "DSGVO Art. 17 (Löschung) und Art. 20 (Export) sind Produkt-Endpunkte, keine Ticket-Warteschlangen.",
        "Betriebsrats-Modus (§87 BetrVG): unterhalb der Admin-Rolle ersetzen Rollenbezeichnungen alle personenbeziehbaren Felder — keine Leistungskennzahl pro Mitarbeiter:in ableitbar.",
        "EU-KI-Verordnung Art. 50: nicht menschlich geprüfte ausgehende Texte tragen eine automatische KI-Kennzeichnung; menschlich freigegebene Inhalte protokollieren die prüfende Person.",
        "Eine Live-Model-Card im Produkt zeigt Modell, Endpunkt und gemessene Evaluationsqualität (Genauigkeit pro Sprache mit Nennern und Datensatz-Datum).",
      ],
    },
    {
      title: "KI-Transparenz",
      items: [
        "Provider-agnostisch: jeder OpenAI-kompatible Endpunkt, einschließlich EU-gehosteter und selbst gehosteter lokaler Modelle. Kein Fine-Tuning auf Kundendaten.",
        "Modell-Ausgaben tragen einen Modell-Score (eine unkalibrierte Heuristik — als solche gekennzeichnet), Evidenz-Links und benannte Limitationen; dünne Evidenz führt zu einer Ablehnung, nicht zu einer Vermutung.",
        "Outcome-Auswertungen werden nach Messdesign mit A–E bewertet; manuelle Einträge sind als „unverifizierte manuelle Beobachtung“ gekennzeichnet und werden nie mit instrumentierten Messungen vermischt.",
      ],
    },
    {
      title: "Zertifizierungen & Roadmap",
      items: [
        "ISO 27001: auf der Roadmap — DACH-Shortlists filtern danach; wird mit wachsendem Umsatz und PII-Volumen verfolgt.",
        "BSI C5 (Typ 1 → Typ 2): nach ISO 27001 sequenziert; dient zugleich als NIS2-/DORA-Lieferketten-Nachweis.",
        "DORA-ICT-Annex und NIS2-Lieferketten-Dokumentation liegen für regulierte Pilotprojekte bereit; eine unterschriebene AVV ist auf Anfrage verfügbar.",
      ],
    },
  ],
  contact: `Fragen, Sicherheitsmeldungen oder AVV-Anfragen: ${CONTACT_EMAIL}`,
};

export function SecurityPage() {
  const { locale } = useI18n();
  const c = locale === "de" ? DE : EN;
  useReveal();

  return (
    <main className="page-main">
      <div className="page-head">
        <div className="wrap">
          <span className="eyebrow on-dark"><span className="dot" />{c.eyebrow}</span>
          <h1>{c.h1}</h1>
          <p className="lede">{c.intro}</p>
        </div>
      </div>
      <section>
        <div className="wrap">
          <div className="prose" style={{ maxWidth: 780 }}>
            {c.sections.map((section) => (
              <div key={section.title} className="reveal">
                <h2>{section.title}</h2>
                <ul>
                  {section.items.map((item) => (
                    <li key={item}>{item}</li>
                  ))}
                </ul>
              </div>
            ))}
            <p style={{ marginTop: 36, color: "var(--muted)" }}>{c.contact}</p>
          </div>
        </div>
      </section>
    </main>
  );
}
