"use client";

// The about page answers the buyer's real question out loud: you'd be
// trusting one person, so here is exactly who, with claims that stay inside
// what his own public profile states. No stock-photo team, no invented
// advisors, the solo reality framed as what it is: short paths and no
// handoffs, checked by the same claims discipline as the rest of the site.

import Link from "next/link";
import { useI18n } from "@/lib/i18n";
import { demoHref, useReveal } from "../site-shell";

export function AboutPage() {
  const { t } = useI18n();
  const s = t.site;
  useReveal();

  const cards = [
    { mark: "15y", title: s.aC1T, body: s.aC1B },
    { mark: "AIGP", title: s.aC2T, body: s.aC2B },
    { mark: "EU", title: s.aC3T, body: s.aC3B },
    { mark: "1:1", title: s.aC4T, body: s.aC4B },
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

      <section>
        <div className="wrap">
          <div className="usp-grid" style={{ marginTop: 0 }}>
            {cards.map((card) => (
              <div key={card.mark} className="usp reveal">
                <span className="num">{card.mark}</span>
                <div>
                  <h3>{card.title}</h3>
                  <p>{card.body}</p>
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
            {s.aAltPre} <Link href="/research">{s.aAltLink}</Link>. {s.aMore}{" "}
            <a href="https://elvis.odradekai.com" target="_blank" rel="noreferrer">elvis.odradekai.com</a>.
          </p>
        </div>
      </section>
    </main>
  );
}
