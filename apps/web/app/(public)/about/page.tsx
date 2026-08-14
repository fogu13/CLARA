import type { Metadata } from "next";
import { AboutPage } from "./about-client";

export const metadata: Metadata = {
  title: "About · CLARA",
  description:
    "Who builds CLARA and why you can check every claim: 15+ years of B2B Voice of Customer from the inside, certified AI governance, EU-first by habit.",
  alternates: { canonical: "/about" },
  openGraph: {
    type: "website",
    url: "https://clara.odradekai.com/about",
    title: "About · CLARA",
    description:
      "One founder, 15+ years of B2B Voice of Customer, certified AI governance. Every claim on this site is machine-checked against the live product.",
    images: [{ url: "/og.jpg", width: 1424, height: 737 }],
  },
};

export default function Page() {
  return <AboutPage />;
}
