import type { Metadata } from "next";
import type { ReactNode } from "react";
import { cookies } from "next/headers";
import { I18nProvider } from "@/lib/i18n";
import "./globals.css";

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
      <body>
        <I18nProvider initialLocale={locale}>{children}</I18nProvider>
      </body>
    </html>
  );
}
