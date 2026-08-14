import type { Metadata } from "next";
import { SecurityPage } from "./security-client";

export const metadata: Metadata = {
  title: "Security & Trust · CLARA",
  description:
    "How CLARA handles customer feedback data: EU residency, security measures, data-subject rights, AI transparency and the certification roadmap.",
  alternates: { canonical: "/security" },
  openGraph: {
    type: "website",
    url: "https://clara.odradekai.com/security",
    title: "Security & Trust · CLARA",
    description:
      "EU residency, security measures, data-subject rights, AI transparency and the certification roadmap. Evidence-scoped, no superlatives.",
    images: [{ url: "/og.jpg", width: 1424, height: 737 }],
  },
};

export default function Page() {
  return <SecurityPage />;
}
