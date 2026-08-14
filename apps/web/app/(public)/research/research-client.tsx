"use client";

// The research & pilots page. Two tracks, deliberately kept apart (the
// customer-discovery spec's never-blend rule): Track A is the academic
// interview study for the MSc thesis — consented, anonymized, no sales;
// Track B is the openly commercial design-partner pilot. Each has its own
// CTA and its own contact address.

import { useI18n } from "@/lib/i18n";
import {
  CONTACT_EMAIL,
  RESEARCH_EMAIL,
  demoHref,
  researchBookingHref,
  surveyHref,
  useReveal,
} from "../site-shell";

function Check() {
  return <i aria-hidden="true">✓</i>;
}

export function ResearchPage() {
  const { t } = useI18n();
  const s = t.site;
  useReveal();
  const survey = surveyHref();

  return (
    <main className="page-main">
      <div className="page-head">
        <div className="wrap">
          <span className="eyebrow on-dark"><span className="dot" />{s.rEyebrow}</span>
          <h1>{s.rH1}</h1>
          <p className="lede">{s.rLede}</p>
        </div>
      </div>

      <section>
        <div className="wrap">
          <div className="tracks">
            {/* Track A — academic, no sales */}
            <div className="track academic reveal" id="study">
              <span className="t-tag">{s.rATag}</span>
              <h2>{s.rAH2}</h2>
              <p className="t-body">{s.rABody}</p>
              <ul>
                <li><Check /> {s.rALi1}</li>
                <li><Check /> {s.rALi2}</li>
                <li><Check /> {s.rALi3}</li>
                <li><Check /> {s.rALi4}</li>
              </ul>
              <p className="t-body" style={{ marginTop: 18 }}>{s.rAWho}</p>
              <div className="t-cta">
                <a className="btn btn-primary" href={researchBookingHref()}>
                  {s.rACta} <span className="arrow" aria-hidden="true">→</span>
                </a>
                {survey ? (
                  <a className="btn btn-ghost" href={survey} target="_blank" rel="noreferrer">
                    {s.rASurvey}
                  </a>
                ) : null}
                <p className="t-note">
                  {s.rANote} <b>{RESEARCH_EMAIL}</b>
                </p>
              </div>
            </div>

            {/* Track B — openly commercial */}
            <div className="track commercial reveal" id="pilot">
              <span className="t-tag">{s.rBTag}</span>
              <h2>{s.rBH2}</h2>
              <p className="t-body">{s.rBBody}</p>
              <ul>
                <li><Check /> {s.rBLi1}</li>
                <li><Check /> {s.rBLi2}</li>
                <li><Check /> {s.rBLi3}</li>
              </ul>
              <div className="t-cta" style={{ marginTop: "auto", paddingTop: 26 }}>
                <a className="btn btn-primary" href={demoHref()}>
                  {s.rBCta} <span className="arrow" aria-hidden="true">→</span>
                </a>
                <p className="t-note">
                  {s.rBNote} <b>{CONTACT_EMAIL}</b>
                </p>
              </div>
            </div>
          </div>

          <p className="divider-note reveal">{s.rDivider}</p>
        </div>
      </section>
    </main>
  );
}
