"use client";

// W3: five-screen AI-literacy module (EU AI Act Art. 4 deployer duty).
// Local stepper state only — completing the flow sets a localStorage flag for
// the dashboard banner; the ONLY thing ever persisted server-side is the
// workspace-level pack-delivery attestation (no per-user tracking, by design).

import { useEffect, useState } from "react";
import Link from "next/link";
import { Download } from "lucide-react";
import { Button, buttonVariants } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { getWorkspace, updateWorkspace } from "@/lib/client-api";
import { AI_LITERACY_SEEN_KEY, buildScreens, EvalBlock, todayIso } from "@/lib/ai-literacy";
import { useI18n } from "@/lib/i18n";

export default function AiLiteracyPage() {
  const { t } = useI18n();
  const a = t.aiLiteracy;
  const screens = buildScreens(t);
  const [index, setIndex] = useState(0);
  const [deliveredAt, setDeliveredAt] = useState<string | null>(null);
  const [attestState, setAttestState] = useState<"idle" | "busy" | "error">("idle");

  const last = index === screens.length - 1;
  const screen = screens[index];

  useEffect(() => {
    getWorkspace()
      .then((workspace) => setDeliveredAt(workspace.ai_literacy_pack_delivered_at))
      .catch(() => {
        // status display only; the attestation button re-fetches before writing
      });
  }, []);

  // Reaching the last screen counts as "seen once" and silences the
  // first-login dashboard banner. localStorage only — never sent anywhere.
  useEffect(() => {
    if (!last) return;
    try {
      window.localStorage.setItem(AI_LITERACY_SEEN_KEY, "1");
    } catch {
      // storage unavailable; the banner will simply show again
    }
  }, [last]);

  async function attest() {
    setAttestState("busy");
    try {
      // Fresh read → spread → write, so a stale page can't clobber settings
      // saved elsewhere since load (same pattern as the settings page).
      const current = await getWorkspace();
      const saved = await updateWorkspace({ ...current, ai_literacy_pack_delivered_at: todayIso() });
      setDeliveredAt(saved.ai_literacy_pack_delivered_at);
      setAttestState("idle");
    } catch {
      setAttestState("error");
    }
  }

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <div>
        <h1 className="text-2xl font-bold">{a.title}</h1>
        <p className="mt-1 text-sm text-muted-foreground">{a.subtitle}</p>
      </div>

      <div className="flex items-center justify-between">
        <span className="text-sm text-muted-foreground" role="status" aria-live="polite">
          {a.screenOf.replace("{n}", String(index + 1)).replace("{total}", String(screens.length))}
        </span>
        <div className="flex items-center gap-2">
          {screens.map((s, i) => (
            <button
              key={s.title}
              type="button"
              aria-label={`${i + 1}. ${s.title}`}
              aria-current={i === index ? "step" : undefined}
              onClick={() => setIndex(i)}
              className={`h-2.5 w-2.5 rounded-full transition-colors ${
                i === index ? "bg-primary" : i < index ? "bg-primary/40" : "bg-muted-foreground/25"
              }`}
            />
          ))}
        </div>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>
            {index + 1}. {screen.title}
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3 text-sm">
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
        </CardContent>
      </Card>

      <div className="flex items-center justify-between">
        <Button
          variant="outline"
          onClick={() => setIndex((i) => Math.max(0, i - 1))}
          disabled={index === 0}
        >
          {a.back}
        </Button>
        {!last ? (
          <Button onClick={() => setIndex((i) => Math.min(screens.length - 1, i + 1))}>
            {a.next}
          </Button>
        ) : null}
      </div>

      {last ? (
        <Card>
          <CardContent className="space-y-3 py-4">
            <div className="flex flex-wrap items-center gap-3">
              <Link href="/ai-literacy/pack" className={buttonVariants({ variant: "default" })}>
                <Download className="mr-1 h-4 w-4" aria-hidden="true" />
                {a.ctaPack}
              </Link>
              <Button variant="outline" onClick={() => void attest()} disabled={attestState === "busy"}>
                {attestState === "busy" ? a.attesting : a.ctaAttest}
              </Button>
              <span className="text-sm">
                {deliveredAt ? (
                  <span className="font-medium text-emerald-600">
                    {a.attestedOn.replace("{date}", deliveredAt)}
                  </span>
                ) : (
                  <span className="text-muted-foreground">{a.notAttested}</span>
                )}
              </span>
            </div>
            {attestState === "error" ? (
              <p role="alert" className="text-xs text-destructive">
                {a.attestFailed}
              </p>
            ) : null}
            <p className="text-xs text-muted-foreground">{a.ctaPackNote}</p>
            <p className="text-xs text-muted-foreground">{a.attestNote}</p>
          </CardContent>
        </Card>
      ) : null}
    </div>
  );
}
