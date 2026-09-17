"use client";

// Published pricing — one displayed anchor per tier (the "from €490 /
// typically €690" double number confused more than it converted; the floor
// stays a negotiation position, not a public promise). Numbers per the
// August 2026 pricing benchmark (private repository). No named competitor
// comparisons here: comparative advertising is pending the Fachanwalt review.

import { useI18n } from "@/lib/i18n";
import { CONTACT_EMAIL, demoHref, useReveal } from "../site-shell";

function Check() {
  return <i aria-hidden="true">✓</i>;
}

export function PricingPage() {
  const { t } = useI18n();
  const s = t.site;
  useReveal();

  const tiers = [
    {
      name: s.pT1N,
      price: "€690",
      note: s.pT1Note,
      flagship: false,
      features: [s.pT1F1, s.pT1F2, s.pT1F3, s.pT1F4, s.pT1F5],
    },
    {
      name: s.pT2N,
      price: "€1,990",
      note: s.pT2Note,
      flagship: true,
      features: [s.pT2F1, s.pT2F2, s.pT2F3, s.pT2F4, s.pT2F5],
    },
    {
      name: s.pT3N,
      price: s.pT3Price,
      note: s.pT3Note,
      flagship: false,
      features: [s.pT3F1, s.pT3F2, s.pT3F3, s.pT3F4, s.pT3F5],
    },
  ];

  return (
    <main className="page-main">
      <div className="page-head">
        <div className="wrap">
          <span className="eyebrow on-dark"><span className="dot" />{s.pEyebrow}</span>
          <h1>{s.pH1}</h1>
          <p className="lede">{s.pLede}</p>
        </div>
      </div>

      <section>
        <div className="wrap">
          <div className="tiers">
            {tiers.map((tier) => (
              <div key={tier.name} className={`tier-card reveal${tier.flagship ? " flagship" : ""}`}>
                {tier.flagship ? <span className="pop">{s.pPopular}</span> : null}
                <h3>{tier.name}</h3>
                <div className="price">
                  {tier.price}
                  <small> {s.pPerMonth}</small>
                </div>
                <p className="p-note">{tier.note}</p>
                <ul>
                  {tier.features.map((feature) => (
                    <li key={feature}><Check /> {feature}</li>
                  ))}
                </ul>
              </div>
            ))}
          </div>

          <div className="pilot-card reveal">
            <div>
              <h3>{s.pPilotT}</h3>
              <p>{s.pPilotB}</p>
            </div>
            <a className="btn btn-primary" href={demoHref()}>
              {s.pPilotCta} <span className="arrow" aria-hidden="true">→</span>
            </a>
          </div>

          <div className="price-notes reveal">
            <p>{s.pNote1}</p>
            <p>{s.pNote2}</p>
            <p>{s.pNote3}</p>
            <p>
              {s.pContact} <a href={`mailto:${CONTACT_EMAIL}?subject=CLARA%20pricing`}>{CONTACT_EMAIL}</a>
            </p>
          </div>
        </div>
      </section>
    </main>
  );
}
