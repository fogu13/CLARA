import type { MetadataRoute } from "next";

const BASE = "https://clara.odradekai.com";
const LAUNCH_SURFACE = process.env.NEXT_PUBLIC_LEGAL_PAGES === "1";

export default function sitemap(): MetadataRoute.Sitemap {
  const entries: MetadataRoute.Sitemap = [
    { url: `${BASE}/`, changeFrequency: "weekly", priority: 1 },
    { url: `${BASE}/security`, changeFrequency: "monthly", priority: 0.8 },
    { url: `${BASE}/about`, changeFrequency: "monthly", priority: 0.7 },
    { url: `${BASE}/research`, changeFrequency: "monthly", priority: 0.7 },
  ];
  if (LAUNCH_SURFACE) {
    entries.push(
      { url: `${BASE}/pricing`, changeFrequency: "monthly", priority: 0.9 },
      { url: `${BASE}/ai-literacy-basics`, changeFrequency: "monthly", priority: 0.5 },
      { url: `${BASE}/legal/impressum`, changeFrequency: "yearly", priority: 0.3 },
      { url: `${BASE}/legal/datenschutz`, changeFrequency: "yearly", priority: 0.3 },
      { url: `${BASE}/legal/agb`, changeFrequency: "yearly", priority: 0.3 }
    );
  }
  return entries;
}
