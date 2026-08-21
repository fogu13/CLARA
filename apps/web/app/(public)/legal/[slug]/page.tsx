import { promises as fs } from "fs";
import path from "path";
import { notFound } from "next/navigation";
import { marked } from "marked";
import type { Metadata } from "next";

// Legal pages (Impressum, Datenschutzerklärung, AGB), rendered at BUILD time
// from the reviewed markdown in business-ops/legal/.
//
// Publishing is double-gated, fail-closed:
//  1. NEXT_PUBLIC_LEGAL_PAGES=1 must be set at build time (default: 404).
//  2. A document still carrying the "DRAFT" review banner or unfilled
//     {{PLACEHOLDER}} tokens is NEVER published, flag or no flag — a premature
//     env flip cannot put unreviewed legal text on the public site.
// The Fachanwalt flip is therefore: fill placeholders, remove the DRAFT
// banner, set the env var, redeploy.

export const dynamic = "force-static";

const PAGES: Record<string, { file: string; title: string }> = {
  impressum: { file: "impressum.md", title: "Impressum" },
  datenschutz: { file: "datenschutzerklaerung.md", title: "Datenschutzerklärung" },
  agb: { file: "agb-b2b.md", title: "Allgemeine Geschäftsbedingungen (B2B)" },
};

const ENABLED = process.env.NEXT_PUBLIC_LEGAL_PAGES === "1";

async function loadPublishable(slug: string): Promise<string | null> {
  const page = PAGES[slug];
  if (!ENABLED || !page) return null;
  try {
    // Build-time read from the repo checkout (force-static: no runtime fs).
    const raw = await fs.readFile(
      path.join(process.cwd(), "..", "..", "business-ops", "legal", page.file),
      "utf8"
    );
    if (raw.includes("DRAFT") || raw.includes("{{")) {
      console.warn(
        `[legal-pages] ${page.file} still carries a DRAFT banner or unfilled placeholders — refusing to publish.`
      );
      return null;
    }
    return raw;
  } catch {
    return null;
  }
}

export function generateStaticParams() {
  return Object.keys(PAGES).map((slug) => ({ slug }));
}

export async function generateMetadata({
  params,
}: {
  params: Promise<{ slug: string }>;
}): Promise<Metadata> {
  const { slug } = await params;
  const page = PAGES[slug];
  return { title: page ? `${page.title} — CLARA` : "CLARA" };
}

export default async function LegalPage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  const content = await loadPublishable(slug);
  if (!content) notFound();

  const html = await marked.parse(content, { gfm: true });
  return (
    <main className="page-main">
      <section>
        <div className="wrap">
          <article
            className="prose"
            style={{ maxWidth: 760 }}
            // Content is our own repo-committed, lawyer-reviewed markdown — not
            // user input; marked renders it to static HTML at build time.
            dangerouslySetInnerHTML={{ __html: html }}
          />
        </div>
      </section>
    </main>
  );
}
