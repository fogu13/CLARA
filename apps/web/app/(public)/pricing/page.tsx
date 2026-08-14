import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { PricingPage } from "./pricing-client";

export const metadata: Metadata = {
  title: "Pricing — CLARA",
  description:
    "Transparent EUR pricing for the governed feedback-to-outcome platform. Published tiers — DACH procurement should never have to guess.",
  alternates: { canonical: "/pricing" },
  openGraph: {
    type: "website",
    url: "https://clara.odradekai.com/pricing",
    title: "Pricing — CLARA",
    description: "Transparent EUR pricing, published. Starter €690 · Growth €1,990 · Enterprise custom.",
    images: [{ url: "/og.jpg", width: 1424, height: 737 }],
  },
};

// Gated with the launch surface: pricing goes public together with the legal
// pages (NEXT_PUBLIC_LEGAL_PAGES=1 at build time), not before.
const ENABLED = process.env.NEXT_PUBLIC_LEGAL_PAGES === "1";

export default function Page() {
  if (!ENABLED) notFound();
  return <PricingPage />;
}
