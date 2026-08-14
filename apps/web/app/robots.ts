import type { MetadataRoute } from "next";

// Public marketing pages are crawlable; the authenticated app is not.
export default function robots(): MetadataRoute.Robots {
  return {
    rules: [
      {
        userAgent: "*",
        allow: "/",
        disallow: [
          "/dashboard",
          "/signals",
          "/insights",
          "/actions",
          "/learnings",
          "/onboarding",
          "/sources",
          "/integrations",
          "/taxonomy",
          "/rules",
          "/compliance",
          "/ai-literacy",
          "/settings",
          "/auth",
          "/welcome",
          "/reset-password",
        ],
      },
    ],
    sitemap: "https://clara.odradekai.com/sitemap.xml",
  };
}
