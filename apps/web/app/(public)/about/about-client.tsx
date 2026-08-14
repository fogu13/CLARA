"use client";

// About, credibility-first for a DACH audience: mission, research origin,
// professional leadership bio in third person, operating principles, and a
// facts strip. Company voice throughout. The claims-check line stays: the
// strongest trust signal on the site is that its claims are machine-verified.

import Link from "next/link";
import { useI18n } from "@/lib/i18n";
import { demoHref, useReveal } from "../site-shell";

export function AboutPage() {
  const { t } = useI18n();
  const s = t.site;
  useReveal();

  const principles = [
    { title: s.aPrin1T, body: s.aPrin1B },
    { title: s.aPrin2T, body: s.aPrin2B },
    { title: s.aPrin3T, body: s.aPrin3B },
    { title: s.aPrin4T, body: s.aPrin4B },
  ];

  return (
    <main className="page-main">
      <div className="page-head">
        <div className="wrap">
          <span className="eyebrow on-dark"><span className="dot" />{s.aEyebrow}</span>
          <h1>{s.aH1}</h1>
          <p className="lede">{s.aLede}</p>
        </div>
      </div>

      {/* facts strip, same treatment as the landing trust strip */}
      <div className="strip">
        <div className="wrap row">
          <span className="pill"><i>●</i> {s.aFact1}</span>
          <span className="pill"><i>●</i> {s.aFact2}</span>
          <span className="pill"><i>●</i> {s.aFact3}</span>
          <span className="pill"><i>●</i> {s.aFact4}</span>
        </div>
      </div>

      <section>
        <div className="wrap">
          <div className="tracks" style={{ marginTop: 0 }}>
            <div className="track reveal">
              <span className="t-tag">{s.proofEyebrow}</span>
              <h2 style={{ fontSize: 22 }}>{s.aOriginT}</h2>
              <p className="t-body">{s.aOriginB}</p>
            </div>
            <div className="track commercial reveal">
              <span className="t-tag">{s.aFounderT}</span>
              <h2 style={{ fontSize: 22 }}>
                {s.aFounderName} <span style={{ fontWeight: 400, color: "var(--muted-2)", fontSize: 16 }}>· {s.aFounderRole}</span>
              </h2>
              <p className="t-body">{s.aFounderB}</p>
              <p className="t-note" style={{ marginTop: 16 }}>
                <a href="https://elvis.odradekai.com" target="_blank" rel="noreferrer">{s.aMoreFounder}</a>
              </p>
            </div>
          </div>

          <div className="sec-head reveal" style={{ marginTop: 56 }}>
            <h2 style={{ fontSize: 26 }}>{s.aPrinT}</h2>
          </div>
          <div className="usp-grid" style={{ marginTop: 26 }}>
            {principles.map((principle) => (
              <div key={principle.title} className="usp reveal">
                <div>
                  <h3>{principle.title}</h3>
                  <p>{principle.body}</p>
                </div>
              </div>
            ))}
          </div>
          <p className="proof-foot reveal" style={{ maxWidth: "68ch" }}>{s.aCheck}</p>

          <div className="pilot-card reveal" style={{ marginTop: 34 }}>
            <div>
              <h3>{s.aWorkT}</h3>
              <p>{s.aWorkB}</p>
            </div>
            <a className="btn btn-primary" href={demoHref()}>
              {s.ctaPrimary} <span className="arrow" aria-hidden="true">→</span>
            </a>
          </div>

          <p className="reveal" style={{ marginTop: 26, fontSize: 15, color: "var(--muted)" }}>
            {s.aAltPre} <Link href="/research">{s.aAltLink}</Link>.
          </p>
        </div>
      </section>
    </main>
  );
}
