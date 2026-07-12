"use client";

import { useEffect, useState } from "react";
import { ShieldCheck } from "lucide-react";
import { getWorkspace } from "../../lib/client-api";
import { useI18n } from "../../lib/i18n";

/**
 * W1 Betriebsrat-Modus: shown on panels whose person columns collapse to role
 * labels while works_council_mode is on. Renders nothing when the flag is off
 * (or workspace settings can't be loaded) — purely informational.
 */
export function WorksCouncilBanner() {
  const { t } = useI18n();
  const [active, setActive] = useState(false);

  useEffect(() => {
    let cancelled = false;
    getWorkspace()
      .then((workspace) => {
        if (!cancelled) setActive(Boolean(workspace.works_council_mode));
      })
      .catch(() => {
        // informational only; stay hidden if settings can't load
      });
    return () => {
      cancelled = true;
    };
  }, []);

  if (!active) return null;

  return (
    <p
      role="status"
      className="flex items-center gap-2 rounded-md border border-sky-500/40 bg-sky-500/5 px-3 py-2 text-xs text-sky-700 dark:text-sky-400"
    >
      <ShieldCheck className="h-3.5 w-3.5 shrink-0" aria-hidden="true" />
      {t.worksCouncil.banner}
    </p>
  );
}
