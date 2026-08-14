import type { Metadata } from "next";
import { ResearchPage } from "./research-client";

export const metadata: Metadata = {
  title: "Research & pilots — CLARA",
  description:
    "Two ways to take part: a no-sales academic interview study on how teams turn customer feedback into action, or a paid design-partner pilot. Clearly separated, never mixed.",
  alternates: { canonical: "/research" },
  openGraph: {
    type: "website",
    url: "https://clara.odradekai.com/research",
    title: "Research & pilots — CLARA",
    description:
      "A no-sales academic interview study on feedback-to-action practice, and a separate paid design-partner pilot track.",
    images: [{ url: "/og.jpg", width: 1424, height: 737 }],
  },
};

export default function Page() {
  return <ResearchPage />;
}
