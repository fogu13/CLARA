"use client";

// The landing page, replatformed from the former static public/home.html into
// the app so it shares i18n, fonts, metadata and the public shell. Copy canon:
// the loop is described with the product's five stages (Signals → Problems →
// Decisions → Actions → Outcomes); the C·L·A·R·A acrostic stays as brand
// story, not information architecture. Claims discipline: "measure", never
// "prove"; only shipped integrations named as shipped (guarded by
// scripts/live_smoke.py against production every 30 minutes).

import Link from "next/link";
import { useI18n } from "@/lib/i18n";
import { CONTACT_EMAIL, demoHref, useReveal } from "./site-shell";

function Check() {
  return <i aria-hidden="true">✓</i>;
}

export function LandingPage() {
  const { t } = useI18n();
  const s = t.site;
  useReveal();

  return (
    <main id="top">
      {/* HERO */}
      <section className="hero" id="hero">
        <div className="wrap hero-grid">
          <div className="hero-copy">
            <span className="eyebrow hero-eye">
              <span className="dot" />
              {s.heroEyebrow}
            </span>
            <h1>
              {s.heroH1pre} <span className="accent">{s.heroH1accent}</span>
            </h1>
            <p className="lede">{s.heroLede}</p>
            <div className="cta-row">
              <a className="btn btn-primary" href={demoHref()}>
                {s.ctaPrimary} <span className="arrow" aria-hidden="true">→</span>
              </a>
              <a className="btn btn-ghost on-dark" href="#loop">
                {s.heroCtaSecondary}
              </a>
            </div>
            <div className="trust">
              <span><Check /> {s.trust1}</span>
              <span><Check /> {s.trust2}</span>
              <span><Check /> {s.trust3}</span>
            </div>
          </div>

          <aside className="loop-fig" aria-hidden="true">
            <svg viewBox="0 0 460 460">
              <defs>
                <linearGradient id="ring" x1="0" y1="0" x2="1" y2="1">
                  <stop offset="0" stopColor="#e0a24a" />
                  <stop offset="55%" stopColor="#1bb89e" />
                  <stop offset="100%" stopColor="#4dd0b8" />
                </linearGradient>
              </defs>
              <circle cx="230" cy="230" r="170" fill="none" stroke="rgba(140,200,190,.16)" strokeWidth="1.5" />
              <circle
                cx="230" cy="230" r="170" fill="none" stroke="url(#ring)" strokeWidth="2.5"
                strokeLinecap="round" strokeDasharray="6 12" opacity=".9"
              />
              <g>
                <circle cx="230" cy="60" r="9" fill="#e0a24a" />
                <circle cx="330" cy="92" r="4.5" fill="#2a6f70" />
                <circle cx="392" cy="178" r="8" fill="#c79a55" />
                <circle cx="392" cy="283" r="4.5" fill="#2a6f70" />
                <circle cx="330" cy="368" r="8" fill="#4f9f88" />
                <circle cx="230" cy="400" r="4.5" fill="#2a6f70" />
                <circle cx="130" cy="368" r="8" fill="#2bae97" />
                <circle cx="68" cy="283" r="4.5" fill="#2a6f70" />
                <circle cx="68" cy="178" r="8" fill="#1bb89e" />
                <circle cx="130" cy="92" r="4.5" fill="#2a6f70" />
              </g>
              <g className="orbit" style={{ transformOrigin: "230px 230px" }}>
                <circle cx="230" cy="60" r="5" fill="#fff" />
                <circle cx="230" cy="60" r="11" fill="#1bb89e" opacity=".28" />
              </g>
              {/* the product's five stages — the same words as the app nav */}
              <text x="230" y="40" textAnchor="middle" fill="#f1cd93" fontFamily="IBM Plex Mono,monospace" fontSize="11.5" letterSpacing="1.5">{s.ring1}</text>
              <text x="404" y="176" textAnchor="start" fill="#a7cbc3" fontFamily="IBM Plex Mono,monospace" fontSize="11.5" letterSpacing="1.5">{s.ring2}</text>
              <text x="346" y="389" textAnchor="start" fill="#a7cbc3" fontFamily="IBM Plex Mono,monospace" fontSize="11.5" letterSpacing="1.5">{s.ring3}</text>
              <text x="114" y="389" textAnchor="end" fill="#a7cbc3" fontFamily="IBM Plex Mono,monospace" fontSize="11.5" letterSpacing="1.5">{s.ring4}</text>
              <text x="56" y="176" textAnchor="end" fill="#86ddca" fontFamily="IBM Plex Mono,monospace" fontSize="11.5" letterSpacing="1.5">{s.ring5}</text>
              <text x="230" y="212" textAnchor="middle" fill="#6f928b" fontFamily="IBM Plex Mono,monospace" fontSize="11.5" letterSpacing="2.5">{s.ringCenterTop}</text>
              <text x="230" y="246" textAnchor="middle" fill="#ffffff" fontFamily="Space Grotesk,sans-serif" fontWeight="600" fontSize="25">{s.ringCenterA}</text>
              <text x="230" y="276" textAnchor="middle" fill="#4dd0b8" fontFamily="Space Grotesk,sans-serif" fontWeight="600" fontSize="25">{s.ringCenterB}</text>
            </svg>
          </aside>
        </div>
      </section>

      {/* TRUST STRIP */}
      <div className="strip">
        <div className="wrap row">
          <span className="pill"><i>●</i> <b>{s.pill1b}</b> {s.pill1r}</span>
          <span className="pill"><i>●</i> <b>{s.pill2b}</b> {s.pill2r}</span>
          <span className="pill"><i>●</i> {s.pill3pre} <b>Zendesk · Jira · Slack</b></span>
          <span className="pill"><i>●</i> <b>{s.pill4b}</b> {s.pill4r}</span>
          <span className="pill"><i>●</i> {s.pill5pre} <b>EU</b></span>
        </div>
      </div>

      {/* THE GAP */}
      <section id="gap">
        <div className="wrap">
          <div className="sec-head reveal">
            <span className="eyebrow"><span className="dot" />{s.gapEyebrow}</span>
            <h2>{s.gapH2}</h2>
            <p className="sub">{s.gapSub}</p>
          </div>
          <div className="gap-grid">
            <div className="gap-card stop reveal">
              <span className="tag">{s.stopTag}</span>
              <h3>{s.stopH3}</h3>
              <p>{s.stopBody}</p>
              <ul>
                <li><i>×</i> <span>{s.stopLi1}</span></li>
                <li><i>×</i> <span>{s.stopLi2}</span></li>
                <li><i>×</i> <span>{s.stopLi3}</span></li>
                <li><i>×</i> <span>{s.stopLi4}</span></li>
              </ul>
            </div>
            <div className="gap-card go reveal">
              <span className="tag">{s.goTag}</span>
              <h3>{s.goH3}</h3>
              <p>{s.goBody}</p>
              <ul>
                <li><Check /> {s.goLi1}</li>
                <li><Check /> {s.goLi2}</li>
                <li><Check /> {s.goLi3}</li>
                <li><Check /> {s.goLi4}</li>
              </ul>
            </div>
          </div>
        </div>
      </section>

      {/* THE LOOP — the product's five stages, with the real loop bar */}
      <section id="loop" style={{ background: "var(--paper-2)" }}>
        <div className="wrap">
          <div className="sec-head reveal">
            <span className="eyebrow"><span className="dot" />{s.loopEyebrow}</span>
            <h2>{s.loopH2}</h2>
            <p className="sub">{s.loopSub}</p>
          </div>

          <figure className="shot reveal" style={{ margin: "40px 0 0" }}>
            <img src="/images/product-loop-bar.jpg" alt={s.loopShotAlt} loading="lazy" />
          </figure>
          <p className="shot-cap reveal">{s.loopShotCap}</p>

          <div className="steps">
            <div className="step reveal"><span className="letter" style={{ color: "#e0a24a" }}>1</span><h4>{s.step1T}</h4><p>{s.step1B}</p></div>
            <div className="step reveal"><span className="letter" style={{ color: "#c79a55" }}>2</span><h4>{s.step2T}</h4><p>{s.step2B}</p></div>
            <div className="step reveal"><span className="letter" style={{ color: "#4f9f88" }}>3</span><h4>{s.step3T}</h4><p>{s.step3B}</p></div>
            <div className="step reveal"><span className="letter" style={{ color: "#2bae97" }}>4</span><h4>{s.step4T}</h4><p>{s.step4B}</p></div>
            <div className="step reveal"><span className="letter" style={{ color: "#1bb89e" }}>5</span><h4>{s.step5T}</h4><p>{s.step5B}</p></div>
          </div>
          <div className="loop-note reveal">
            ↻&nbsp;<b style={{ whiteSpace: "nowrap" }}>{s.loopUnder}</b>&nbsp;{s.loopChain}
          </div>
          <div className="loop-note reveal">{s.loopBrand}</div>
        </div>
      </section>

      {/* PLATFORM */}
      <section id="platform">
        <div className="wrap">
          <div className="sec-head reveal">
            <span className="eyebrow"><span className="dot" />{s.platEyebrow}</span>
            <h2>{s.platH2}</h2>
            <p className="sub">{s.platSub}</p>
          </div>
          <div className="feat-grid">
            <div className="feat reveal">
              <div className="ic"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round"><path d="M3 12h4l2.5 6 4-14 2.5 8H21" /></svg></div>
              <h3>{s.feat1T}</h3>
              <p>{s.feat1B}</p>
              <div className="meta">{s.feat1M}</div>
            </div>
            <div className="feat reveal">
              <div className="ic"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round"><path d="M12 3l7 2.5v5.5c0 4-3 6.8-7 8-4-1.2-7-4-7-8V5.5z" /><path d="M9 11.5l2 2 4-4.5" /></svg></div>
              <h3>{s.feat2T}</h3>
              <p>{s.feat2B}</p>
              <div className="meta">{s.feat2M}</div>
            </div>
            <div className="feat reveal">
              <div className="ic"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round"><path d="M3 16l5-5 4 3 6-7" /><path d="M17 7h4v4" /></svg></div>
              <h3>{s.feat3T}</h3>
              <p>{s.feat3B}</p>
              <div className="meta">{s.feat3M}</div>
            </div>
            <div className="feat reveal">
              <div className="ic"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round"><path d="M12 3l9 4.5-9 4.5-9-4.5z" /><path d="M3 12.5l9 4.5 9-4.5" /><path d="M3 17l9 4.5 9-4.5" /></svg></div>
              <h3>{s.feat4T}</h3>
              <p>{s.feat4B}</p>
              <div className="meta">{s.feat4M}</div>
            </div>
            <div className="feat reveal">
              <div className="ic"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round"><rect x="5" y="4" width="14" height="17" rx="2" /><path d="M9 4V3h6v1" /><path d="M8.5 12l2.5 2.5 4.5-4.5" /></svg></div>
              <h3>{s.feat5T}</h3>
              <p>{s.feat5B}</p>
              <div className="meta">{s.feat5M}</div>
            </div>
            <div className="feat reveal">
              <div className="ic"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="8.5" /><circle cx="12" cy="12" r="4.5" /><circle cx="12" cy="12" r="1" /></svg></div>
              <h3>{s.feat6T}</h3>
              <p>{s.feat6B}</p>
              <div className="meta">{s.feat6M}</div>
            </div>
          </div>
        </div>
      </section>

      {/* GOVERNANCE — with the real decision queue, not a fictional panel */}
      <section id="governance" className="dark">
        <div className="wrap">
          <div className="moat-grid">
            <div className="moat-copy reveal">
              <span className="eyebrow on-dark"><span className="dot" />{s.govEyebrow}</span>
              <h2>{s.govH2}</h2>
              <p className="sub">{s.govSub}</p>
              <ul>
                <li><i aria-hidden="true">◆</i><div><b>{s.govLi1T}</b><p>{s.govLi1B}</p></div></li>
                <li><i aria-hidden="true">◆</i><div><b>{s.govLi2T}</b><p>{s.govLi2B}</p></div></li>
                <li><i aria-hidden="true">◆</i><div><b>{s.govLi3T}</b><p>{s.govLi3B}</p></div></li>
              </ul>
            </div>
            <div className="moat-shot reveal">
              <figure className="shot">
                <img src="/images/product-decision-queue.jpg" alt={s.govShotAlt} loading="lazy" />
              </figure>
              <p className="shot-cap">{s.govShotCap}</p>
            </div>
          </div>
        </div>
      </section>

      {/* PROOF — the validation that existed before any customer */}
      <section id="proof">
        <div className="wrap">
          <div className="sec-head reveal">
            <span className="eyebrow"><span className="dot" />{s.proofEyebrow}</span>
            <h2>{s.proofH2}</h2>
            <p className="sub">{s.proofSub}</p>
          </div>
          <div className="proof-grid">
            <div className="proof-stat reveal"><div className="big">{s.proofS1T}</div><p>{s.proofS1B}</p></div>
            <div className="proof-stat reveal"><div className="big">{s.proofS2T}</div><p>{s.proofS2B}</p></div>
            <div className="proof-stat reveal"><div className="big">{s.proofS3T}</div><p>{s.proofS3B}</p></div>
          </div>
          <div className="proof-quotes">
            <div className="proof-quote reveal"><p className="q">{s.proofQ1}</p><p className="src">{s.proofQ1src}</p></div>
            <div className="proof-quote reveal"><p className="q">{s.proofQ2}</p><p className="src">{s.proofQ2src}</p></div>
          </div>
          <p className="proof-foot reveal">{s.proofFoot}</p>
        </div>
      </section>

      {/* WHY CLARA */}
      <section id="why" style={{ background: "var(--paper-2)" }}>
        <div className="wrap">
          <div className="sec-head reveal">
            <span className="eyebrow"><span className="dot" />{s.whyEyebrow}</span>
            <h2>{s.whyH2}</h2>
          </div>
          <div className="usp-grid">
            <div className="usp reveal"><span className="num">01</span><div><h3>{s.usp1T}</h3><p>{s.usp1B}</p></div></div>
            <div className="usp reveal"><span className="num">02</span><div><h3>{s.usp2T}</h3><p>{s.usp2B}</p></div></div>
            <div className="usp reveal"><span className="num">03</span><div><h3>{s.usp3T}</h3><p>{s.usp3B}</p></div></div>
            <div className="usp reveal"><span className="num">04</span><div><h3>{s.usp4T}</h3><p>{s.usp4B}</p></div></div>
          </div>
        </div>
      </section>

      {/* USE CASES */}
      <section id="use-cases">
        <div className="wrap">
          <div className="sec-head reveal">
            <span className="eyebrow"><span className="dot" />{s.ucEyebrow}</span>
            <h2>{s.ucH2}</h2>
            <p className="sub">{s.ucSub}</p>
          </div>
          <div className="uc2-grid">
            <div className="uc2 reveal">
              <div className="uc2-top">
                <span className="ic"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round"><path d="M12 4l9 15.5H3z" /><path d="M12 10v4.5" /><path d="M12 17.5h.01" /></svg></span>
                <span className="who">{s.uc1Who}</span>
              </div>
              <p className="q">{s.uc1Q}</p>
              <p className="ans">{s.uc1A}</p>
              <span className="tag">→ {s.uc1Tag}</span>
            </div>
            <div className="uc2 reveal">
              <div className="uc2-top">
                <span className="ic"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round"><path d="M4 20V4" /><path d="M4 20h16" /><path d="M8 17v-4" /><path d="M12 17V9" /><path d="M16 17v-7" /></svg></span>
                <span className="who">{s.uc2Who}</span>
              </div>
              <p className="q">{s.uc2Q}</p>
              <p className="ans">{s.uc2A}</p>
              <span className="tag">→ {s.uc2Tag}</span>
            </div>
            <div className="uc2 feature reveal">
              <span className="badge">{s.ucBadge}</span>
              <div className="uc2-top">
                <span className="ic"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round"><path d="M12 3l7 2.5v5.5c0 4-3 6.8-7 8-4-1.2-7-4-7-8V5.5z" /><path d="M9 11.5l2 2 4-4.5" /></svg></span>
                <span className="who">{s.uc3Who}</span>
              </div>
              <p className="q">{s.uc3Q}</p>
              <p className="ans">{s.uc3A}</p>
              <span className="tag">→ {s.uc3Tag}</span>
            </div>
            <div className="uc2 reveal">
              <div className="uc2-top">
                <span className="ic"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="8.5" /><circle cx="12" cy="12" r="4.5" /><circle cx="12" cy="12" r="1" /></svg></span>
                <span className="who">{s.uc4Who}</span>
              </div>
              <p className="q">{s.uc4Q}</p>
              <p className="ans">{s.uc4A}</p>
              <span className="tag">→ {s.uc4Tag}</span>
            </div>
            <div className="uc2 reveal">
              <div className="uc2-top">
                <span className="ic"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round"><path d="M12 3l9 4.5-9 4.5-9-4.5z" /><path d="M3 12.5l9 4.5 9-4.5" /><path d="M3 17l9 4.5 9-4.5" /></svg></span>
                <span className="who">{s.uc5Who}</span>
              </div>
              <p className="q">{s.uc5Q}</p>
              <p className="ans">{s.uc5A}</p>
              <span className="tag">→ {s.uc5Tag}</span>
            </div>
            <div className="uc2 reveal">
              <div className="uc2-top">
                <span className="ic"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="8.5" /><path d="M3.5 12h17" /><path d="M12 3.5c2.4 2.6 2.4 12.4 0 17M12 3.5c-2.4 2.6-2.4 12.4 0 17" /></svg></span>
                <span className="who">{s.uc6Who}</span>
              </div>
              <p className="q">{s.uc6Q}</p>
              <p className="ans">{s.uc6A}</p>
              <span className="tag">→ {s.uc6Tag}</span>
            </div>
          </div>
        </div>
      </section>

      {/* STACK */}
      <section id="stack" style={{ background: "var(--paper-2)" }}>
        <div className="wrap stack">
          <div className="stack-copy reveal">
            <span className="eyebrow"><span className="dot" />{s.stackEyebrow}</span>
            <h2>{s.stackH2}</h2>
            <p className="sub">{s.stackSub}</p>
            <div className="cta-row" style={{ marginTop: 28 }}>
              <a className="btn btn-ghost" href="#platform">{s.stackExplore}</a>
            </div>
          </div>
          <div className="flow reveal">
            <div className="lane">
              <div className="chips">
                <div className="col-h">{s.stackIn}</div>
                <div className="chip"><i>●</i> Zendesk · Trustpilot</div>
                <div className="chip"><i>●</i> App Store · Google Play · Google Reviews</div>
                <div className="chip"><i>●</i> CSV · Webhook</div>
              </div>
              <div className="mid"><span aria-hidden="true">→</span></div>
              <div className="core">
                <div className="badge">CLARA</div>
                <div className="cap">{s.stackCore}</div>
              </div>
              <div className="mid"><span aria-hidden="true">→</span></div>
              <div className="chips">
                <div className="col-h">{s.stackOut}</div>
                <div className="chip"><i>●</i> Jira</div>
                <div className="chip"><i>●</i> Slack</div>
                <div className="chip" style={{ opacity: 0.6 }}><i>○</i> {s.stackRoadmap}</div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="cta" id="demo">
        <div className="wrap">
          <h2>{s.ctaH2}</h2>
          <p className="cta-sub">{s.ctaSub}</p>
          <div className="cta-row">
            <a className="btn btn-primary" href={demoHref()}>
              {s.ctaPrimary} <span className="arrow" aria-hidden="true">→</span>
            </a>
            <a className="btn btn-ghost on-dark" href="#loop">{s.ctaRevisit}</a>
          </div>
          <p className="cta-alt">{s.ctaAltPre} <b>{CONTACT_EMAIL}</b></p>
          <p className="cta-research">
            {s.ctaResearch} <Link href="/research">{s.ctaResearchLink} →</Link>
          </p>
        </div>
      </section>
    </main>
  );
}
