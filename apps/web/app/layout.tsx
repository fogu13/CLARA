import type { Metadata } from "next";
import type { ReactNode } from "react";
import { cookies } from "next/headers";
import localFont from "next/font/local";
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

export const metadata: Metadata = {
  title: "CLARA | Feedback-to-Action Platform",
  description: "Governed AI triage with real connectors: Zendesk in, Jira + Slack out"
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
      </body>
    </html>
  );
}
