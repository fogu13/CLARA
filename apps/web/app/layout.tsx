import type { Metadata } from "next";
import type { ReactNode } from "react";
import { cookies } from "next/headers";
import localFont from "next/font/local";
import { Analytics } from "@vercel/analytics/react";
import { I18nProvider } from "@/lib/i18n";
import "./globals.css";

// The Inter files have shipped in /public/fonts all along but were never
// loaded, so every user saw their OS fallback. next/font self-hosts with
// zero layout shift; 600 covers headings (700 renders synthetically).
const inter = localFont({
  src: [
    { path: "../public/fonts/inter-400.woff2", weight: "400", style: "normal" },
    { path: "../public/fonts/inter-500.woff2", weight: "500", style: "normal" },
    { path: "../public/fonts/inter-600.woff2", weight: "600", style: "normal" },
  ],
  variable: "--font-inter",
  display: "swap",
});

// One tagline canon everywhere: "the European feedback-to-outcome platform"
// (the app pages that don't set their own metadata inherit this).
export const metadata: Metadata = {
  metadataBase: new URL("https://clara.odradekai.com"),
  title: "CLARA | The European feedback-to-outcome platform",
  description:
    "Turn customer signals into governed action, then measure whether it worked. Evidence-backed problems, policy-gated decisions, measured outcomes — EU-resident by design.",
  icons: { icon: "/icon.svg" },
  other: { "theme-color": "#08171a" },
};

export default async function RootLayout({ children }: Readonly<{ children: ReactNode }>) {
  // Reading the locale cookie server-side means German users get German HTML
  // on the first byte (and makes rendering dynamic, which this authenticated,
  // client-fetched dashboard doesn't mind).
  const stored = (await cookies()).get("clara_locale")?.value;
  const locale = stored === "de" ? "de" : "en";
  return (
    <html lang={locale}>
      <body className={inter.variable}>
        <I18nProvider initialLocale={locale}>{children}</I18nProvider>
        <Analytics />
      </body>
    </html>
  );
}
