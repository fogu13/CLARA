import type { Metadata } from "next";
import { AboutPage } from "./about-client";

export const metadata: Metadata = {
  title: "About · CLARA",
  description:
    "Why CLARA exists: feedback intelligence European teams can defend. Born from Responsible-AI research, built in Berlin, led by 15+ years of enterprise Voice-of-Customer practice.",
  alternates: { canonical: "/about" },
  openGraph: {
    type: "website",
    url: "https://clara.odradekai.com/about",
    title: "About · CLARA",
    description:
      "Born from research, validated across three industries, built in Berlin. Every claim on this site is machine-checked against the live product.",
    images: [{ url: "/og.jpg", width: 1424, height: 737 }],
  },
};

export default function Page() {
  return <AboutPage />;
}
