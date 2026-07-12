"use client";

// W3: the AI-Literacy Pack as a print route (no PDF dependency). Renders all
// five module screens plus the live model-card snapshot and the eval-report
// citation, stamped with workspace name + date in header and footer; the
// button opens the browser print dialog (save as PDF) — labelled honestly.

import { useEffect, useState } from "react";
import Link from "next/link";
import { ArrowLeft, Printer } from "lucide-react";
import { Button } from "@/components/ui/button";
import { getSystemConfig, getWorkspace } from "@/lib/client-api";
import type { SystemConfig, WorkspaceSettings } from "@/lib/types";
import { buildScreens, EvalBlock, todayIso } from "@/lib/ai-literacy";
import { useI18n } from "@/lib/i18n";

export default function AiLiteracyPackPage() {
  const { t } = useI18n();
  const a = t.aiLiteracy;
  const screens = buildScreens(t);
  const [workspace, setWorkspace] = useState<WorkspaceSettings | null>(null);
  const [config, setConfig] = useState<SystemConfig | null>(null);
  const [today, setToday] = useState("");

  useEffect(() => {
    getWorkspace().then(setWorkspace).catch(() => {});
    getSystemConfig().then(setConfig).catch(() => {});
    // Stamped client-side after mount so the statically prerendered HTML
    // can't disagree with the client date (hydration safety).
    setToday(todayIso());
  }, []);

  const workspaceName = workspace?.name ?? "—";

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <div className="print-hidden flex flex-wrap items-start justify-between gap-3">
        <Link
          href="/ai-literacy"
          className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground"
        >
          <ArrowLeft className="h-4 w-4" aria-hidden="true" /> {a.packBack}
        </Link>
        <div className="flex flex-col items-end gap-1">
          <Button onClick={() => window.print()}>
            <Printer className="mr-1 h-4 w-4" aria-hidden="true" /> {a.packPrint}
          </Button>
          <p className="text-xs text-muted-foreground">{a.packPrintNote}</p>
        </div>
      </div>

      <header className="pack-header border-b pb-4">
        <p className="text-xs font-semibold uppercase tracking-[0.2em] text-primary">CLARA</p>
        <h1 className="mt-2 text-2xl font-bold">{a.packTitle}</h1>
        <p className="mt-1 text-sm text-muted-foreground">{a.packSubtitle}</p>
        <div className="mt-3 flex flex-wrap gap-x-8 gap-y-1 text-sm">
          <span>
            <span className="text-muted-foreground">{a.packWorkspace}: </span>
            <span className="font-medium">{workspaceName}</span>
          </span>
          <span>
            <span className="text-muted-foreground">{a.packDate}: </span>
            <span className="font-medium">{today}</span>
          </span>
        </div>
      </header>

      {screens.map((screen, i) => (
        <section key={screen.title} className="print-avoid-break space-y-3 text-sm">
          <h2 className="text-lg font-semibold">
            {i + 1}. {screen.title}
          </h2>
          <ul className="ml-4 list-disc space-y-2">
            {screen.bullets.map((bullet) => (
              <li key={bullet}>{bullet}</li>
            ))}
          </ul>
          {screen.showEval ? <EvalBlock t={t} /> : null}
          {screen.caveat ? (
            <p className="rounded-md border border-amber-500/40 bg-amber-500/5 px-3 py-2 text-xs text-amber-700 dark:text-amber-400">
              {screen.caveat}
            </p>
          ) : null}
          {screen.tail?.length ? (
            <ul className="ml-4 list-disc space-y-2">
              {screen.tail.map((bullet) => (
                <li key={bullet}>{bullet}</li>
              ))}
            </ul>
          ) : null}
        </section>
      ))}

      <section className="print-avoid-break space-y-3 text-sm">
        <h2 className="text-lg font-semibold">{a.packModelCard}</h2>
        {config ? (
          <dl className="space-y-1">
            <div className="flex justify-between gap-4">
              <dt className="text-muted-foreground">{t.compliance.model}</dt>
              <dd>
                <code className="rounded bg-muted px-2 py-0.5">{config.ai_model}</code>
              </dd>
            </div>
            <div className="flex justify-between gap-4">
              <dt className="text-muted-foreground">{t.compliance.endpoint}</dt>
              <dd>
                <code className="rounded bg-muted px-2 py-0.5">{config.ai_base_url}</code>
              </dd>
            </div>
            <div className="flex justify-between gap-4">
              <dt className="text-muted-foreground">{t.compliance.apiAuth}</dt>
              <dd className="font-medium">
                {config.auth_enabled ? t.compliance.enabled : t.compliance.disabledDev}
              </dd>
            </div>
          </dl>
        ) : (
          <p className="text-muted-foreground">{t.compliance.configUnavailable}</p>
        )}
        <p className="text-xs text-muted-foreground">{a.packModelCardNote}</p>
      </section>

      <section className="print-avoid-break space-y-2 text-sm">
        <h2 className="text-lg font-semibold">{a.packAttestation}</h2>
        <p>
          {workspace?.ai_literacy_pack_delivered_at
            ? a.attestedOn.replace("{date}", workspace.ai_literacy_pack_delivered_at)
            : a.notAttested}
        </p>
        <p className="text-xs text-muted-foreground">{a.attestNote}</p>
      </section>

      <footer className="border-t pt-3 text-xs text-muted-foreground">
        {a.packFooter} · {workspaceName} · {today}
      </footer>
    </div>
  );
}
