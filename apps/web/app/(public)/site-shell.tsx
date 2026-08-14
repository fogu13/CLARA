"use client";

// Shared chrome for the public marketing surface: header, footer, the
// scroll-reveal effect, and the booking-link helpers. Every (public) page
// renders inside this shell so the trust pages wear the same brand as the
// landing (website audit W-C4).

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { usePathname } from "next/navigation";
import { useI18n } from "@/lib/i18n";

export const CONTACT_EMAIL = "hello@odradekai.com";
export const RESEARCH_EMAIL = "elvisshehi@gmail.com";

// Booking links are env-configured so the site works before the Cal.com
// account exists: unset → an improved mailto that half-writes the email.
export function demoHref(): string {
  return (
    process.env.NEXT_PUBLIC_BOOKING_URL ??
    `mailto:${CONTACT_EMAIL}?subject=${encodeURIComponent("CLARA pilot scoping call")}&body=${encodeURIComponent(
      "Hi Elvis,\n\nI'd like a 30-minute pilot scoping call.\n\nFeedback source I'd bring: \nThe one question I most want answered: \n\nA few times that work for me: "
    )}`
  );
}

export function researchBookingHref(): string {
  return (
    process.env.NEXT_PUBLIC_RESEARCH_BOOKING_URL ??
    `mailto:${RESEARCH_EMAIL}?subject=${encodeURIComponent("Research interview (CLARA study)")}&body=${encodeURIComponent(
      "Hi Elvis,\n\nI'd like to take part in the research interview.\n\nMy role / team: \nCompany size: \nA few times that work for me: "
    )}`
  );
}

export function surveyHref(): string | null {
  return process.env.NEXT_PUBLIC_SURVEY_URL ?? null;
}

export const PRICING_ENABLED = process.env.NEXT_PUBLIC_LEGAL_PAGES === "1";

// Attach the reveal-on-scroll behavior to every .reveal element below `root`.
export function useReveal() {
  useEffect(() => {
    const elements = Array.from(document.querySelectorAll<HTMLElement>(".reveal"));
    if (elements.length === 0) return;
    const io = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add("in");
            io.unobserve(entry.target);
          }
        });
      },
      { threshold: 0.08, rootMargin: "0px 0px -4% 0px" }
    );
    elements.forEach((el, index) => {
      el.style.transitionDelay = `${Math.min(index % 5, 4) * 40}ms`;
      io.observe(el);
    });
    return () => io.disconnect();
  }, []);
}

function BrandMark({ size = 27 }: { size?: number }) {
  return (
    <span className="mark" aria-hidden="true">
      <svg width={size} height={size} viewBox="0 0 100 100" fill="none">
        <g stroke="currentColor" strokeWidth="10">
          <path d="M70.07 27.71 A30 30 0 0 0 46.86 20.16" />
          <path d="M43.76 20.66 A30 30 0 0 0 24.02 35.00" />
          <path d="M22.59 37.80 A30 30 0 0 0 22.59 62.20" />
          <path d="M24.02 65.00 A30 30 0 0 0 43.76 79.34" />
          <path d="M46.86 79.84 A30 30 0 0 0 70.07 72.29" />
        </g>
        <path d="M74.27 32.37 A30 30 0 0 1 74.27 67.63" stroke="#e0a24a" strokeWidth="10" strokeLinecap="round" />
      </svg>
    </span>
  );
}

function LangSwitch() {
  const { locale, setLocale } = useI18n();
  return (
    <span className="lang" role="group" aria-label="Language">
      <button type="button" aria-pressed={locale === "en"} onClick={() => setLocale("en")}>
        EN
      </button>
      <button type="button" aria-pressed={locale === "de"} onClick={() => setLocale("de")}>
        DE
      </button>
    </span>
  );
}

export function SiteHeader() {
  const { t } = useI18n();
  const s = t.site;
  const pathname = usePathname();
  // The landing opens on a dark hero, so its header starts transparent and
  // turns light on scroll; every other public page is light from the start.
  const onLanding = pathname === "/";
  const [scrolled, setScrolled] = useState(!onLanding);
  const [menuOpen, setMenuOpen] = useState(false);

  useEffect(() => {
    if (!onLanding) {
      setScrolled(true);
      return;
    }
    const onScroll = () => setScrolled(window.scrollY > 12);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, [onLanding]);

  const close = useCallback(() => setMenuOpen(false), []);

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") close();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [close]);

  const links = (
    <>
      <Link href="/#loop" onClick={close}>{s.navLoop}</Link>
      <Link href="/#platform" onClick={close}>{s.navPlatform}</Link>
      <Link href="/#governance" onClick={close}>{s.navGovernance}</Link>
      <Link href="/#use-cases" onClick={close}>{s.navUseCases}</Link>
      {PRICING_ENABLED ? <Link href="/pricing" onClick={close}>{s.navPricing}</Link> : null}
      <Link href="/security" onClick={close}>{s.navSecurity}</Link>
      <Link href="/about" onClick={close}>{s.navAbout}</Link>
    </>
  );

  return (
    <header className={`nav${scrolled ? " scrolled" : ""}`}>
      <div className="wrap bar">
        <Link className="brand" href="/" aria-label="CLARA home">
          <BrandMark />
          CLARA
        </Link>
        <nav className="nav-links" aria-label="Primary">
          {links}
        </nav>
        <div className="nav-cta">
          <LangSwitch />
          <Link className="login" href="/auth">{s.signIn}</Link>
          <a className="btn btn-primary" href={demoHref()}>
            {s.ctaPrimary}
          </a>
        </div>
        <button
          className="menu-btn"
          aria-label={menuOpen ? s.closeMenu : s.openMenu}
          aria-expanded={menuOpen}
          aria-controls="mmenu"
          onClick={() => setMenuOpen((open) => !open)}
        >
          {menuOpen ? "✕" : "☰"}
        </button>
      </div>
      <div className={`mobile-menu${menuOpen ? " open" : ""}`} id="mmenu" inert={menuOpen ? undefined : true}>
        <div className="mm-in">
          {links}
          <Link className="mm-signin" href="/auth" onClick={close}>{s.signIn}</Link>
          <a className="btn btn-primary mm-cta" href={demoHref()} onClick={close}>
            {s.ctaPrimary}
          </a>
        </div>
      </div>
    </header>
  );
}

export function SiteFooter() {
  const { t } = useI18n();
  const s = t.site;
  return (
    <footer>
      <div className="wrap">
        <div className="foot-grid">
          <div>
            <Link className="brand" href="/">
              <BrandMark size={25} />
              CLARA
            </Link>
            <p className="blurb">{s.footBlurb}</p>
            <p className="acro">
              <b>{s.footLoop}</b>
            </p>
            <span className="made">&#9733; {s.footMade}</span>
          </div>
          <div className="foot-col">
            <h5>{s.footProduct}</h5>
            <Link href="/#loop">{s.navLoop}</Link>
            <Link href="/#platform">{s.navPlatform}</Link>
            <Link href="/#governance">{s.navGovernance}</Link>
            <Link href="/#use-cases">{s.navUseCases}</Link>
            {PRICING_ENABLED ? <Link href="/pricing">{s.navPricing}</Link> : null}
          </div>
          <div className="foot-col">
            <h5>{s.footCompany}</h5>
            <Link href="/about">{s.navAbout}</Link>
            <Link href="/security">{s.navSecurity}</Link>
            <Link href="/research">{s.navResearch}</Link>
            <a href={`mailto:${CONTACT_EMAIL}`}>{s.footContact}</a>
          </div>
          <div className="foot-col">
            <h5>{s.footCompliance}</h5>
            <Link href="/#governance">GDPR</Link>
            <Link href="/#governance">EU AI Act</Link>
            <Link href="/security">{s.footResidency}</Link>
            <a href={`mailto:${CONTACT_EMAIL}?subject=DPA%20request`}>DPA</a>
          </div>
        </div>
        <div className="foot-bot">
          <span>© 2026 CLARA · Berlin · {CONTACT_EMAIL}</span>
          <span>{s.footLegal}</span>
        </div>
      </div>
    </footer>
  );
}
