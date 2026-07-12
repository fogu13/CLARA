"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { BookOpen, X } from "lucide-react";
import { AI_LITERACY_SEEN_KEY } from "../../lib/ai-literacy";
import { useI18n } from "../../lib/i18n";

/**
 * W3 Art. 4 first-login pointer: shown on the dashboard until the user
 * finishes or dismisses the AI-literacy module. The flag lives in
 * localStorage ONLY — per-user completion is never tracked server-side
 * (works-council trap, see W1).
 */
export function AiLiteracyBanner() {
  const { t } = useI18n();
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    try {
      setVisible(window.localStorage.getItem(AI_LITERACY_SEEN_KEY) !== "1");
    } catch {
      // storage unavailable: stay hidden rather than nag on every load
    }
  }, []);

  function dismiss() {
    setVisible(false);
    try {
      window.localStorage.setItem(AI_LITERACY_SEEN_KEY, "1");
    } catch {
      // non-fatal
    }
  }

  if (!visible) return null;

  return (
    <div
      role="status"
      className="flex items-center justify-between gap-3 rounded-md border border-primary/40 bg-primary/5 px-3 py-2 text-sm"
    >
      <span className="flex items-center gap-2">
        <BookOpen className="h-4 w-4 shrink-0 text-primary" aria-hidden="true" />
        {t.aiLiteracy.bannerText}
      </span>
      <span className="flex shrink-0 items-center gap-2">
        <Link
          href="/ai-literacy"
          className="rounded-md border px-2 py-1 text-xs font-medium hover:bg-primary/10"
        >
          {t.aiLiteracy.bannerCta}
        </Link>
        <button
          type="button"
          aria-label={t.aiLiteracy.bannerDismiss}
          onClick={dismiss}
          className="rounded-md p-1 text-muted-foreground hover:bg-accent hover:text-foreground"
        >
          <X className="h-4 w-4" aria-hidden="true" />
        </button>
      </span>
    </div>
  );
}
