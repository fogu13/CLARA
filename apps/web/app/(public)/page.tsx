import type { Metadata } from "next";
import { LandingPage } from "./landing";

export const metadata: Metadata = {
  title: "CLARA | Turn customer signals into governed action",
  description:
    "CLARA is the European feedback-to-outcome platform. It connects what customers say with what they do, finds the problems that matter, recommends coordinated action, enforces your policies before anything ships, and measures whether it worked.",
  alternates: { canonical: "/" },
  openGraph: {
    type: "website",
    url: "https://clara.odradekai.com/",
    title: "CLARA | Turn customer signals into governed action",
    description:
      "The European feedback-to-outcome platform: evidence-backed insights, policy-gated action, measured results.",
    images: [{ url: "/og.jpg", width: 1424, height: 737 }],
  },
  twitter: {
    card: "summary_large_image",
    title: "CLARA | Turn customer signals into governed action",
    description:
      "Evidence-backed insights, policy-gated action, measured results. EU-resident by design.",
    images: ["/og.jpg"],
  },
};

export default function Page() {
  return <LandingPage />;
}
