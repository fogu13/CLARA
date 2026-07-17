"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { BookOpen, CheckCircle2, Circle } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import {
  apiBaseUrl,
  apiHeaders,
  getApprovals,
  getMeasurements,
  getProblemCandidates,
  getSignals,
} from "@/lib/client-api";
import { useI18n } from "@/lib/i18n";

type Progress = {
  sourceConnected: boolean;
  signalsImported: boolean;
  candidateReviewed: boolean;
  actionApproved: boolean;
  measurementScheduled: boolean;
};

const EMPTY: Progress = {
  sourceConnected: false,
  signalsImported: false,
  candidateReviewed: false,
  actionApproved: false,
  measurementScheduled: false,
};

export default function OnboardingPage() {
  const { t } = useI18n();
  const [progress, setProgress] = useState<Progress>(EMPTY);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      // Each probe is independent; a failing one just leaves its step open.
      const [connectors, signals, candidates, approvals, plans] = await Promise.all([
        fetch(`${apiBaseUrl()}/connectors`, { credentials: "include", headers: apiHeaders() })
          .then((r) => (r.ok ? r.json() : []))
          .catch(() => []),
        getSignals().catch(() => []),
        getProblemCandidates().catch(() => []),
        getApprovals().catch(() => []),
        getMeasurements().catch(() => []),
      ]);
      if (cancelled) return;
      setProgress({
        sourceConnected:
          connectors.some((c: { is_active?: boolean }) => c.is_active) || signals.length > 0,
        signalsImported: signals.length > 0,
        candidateReviewed: candidates.some((c) => c.review_status !== "pending"),
        actionApproved: approvals.length > 0,
        measurementScheduled: plans.length > 0,
      });
      setLoading(false);
    }
    void load();
    return () => {
      cancelled = true;
    };
  }, []);

  const steps = [
    { done: progress.sourceConnected, title: t.onboarding.step1Title, desc: t.onboarding.step1Desc, cta: t.onboarding.step1Cta, href: "/integrations" },
    { done: progress.signalsImported, title: t.onboarding.step2Title, desc: t.onboarding.step2Desc, cta: t.onboarding.step2Cta, href: "/sources" },
    { done: progress.candidateReviewed, title: t.onboarding.step3Title, desc: t.onboarding.step3Desc, cta: t.onboarding.step3Cta, href: "/sources" },
    { done: progress.actionApproved, title: t.onboarding.step4Title, desc: t.onboarding.step4Desc, cta: t.onboarding.step4Cta, href: "/insights" },
    { done: progress.measurementScheduled, title: t.onboarding.step5Title, desc: t.onboarding.step5Desc, cta: t.onboarding.step5Cta, href: "/learnings" },
  ];
  const doneCount = steps.filter((s) => s.done).length;
  const firstOpen = steps.findIndex((s) => !s.done);

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <div>
        <h1 className="text-2xl font-bold">{t.onboarding.title}</h1>
        <p className="mt-1 text-sm text-muted-foreground">{t.onboarding.subtitle}</p>
      </div>

      <div className="flex items-center gap-3" role="status" aria-live="polite">
        <div className="h-2 flex-1 overflow-hidden rounded-full bg-muted">
          <div
            className="h-full rounded-full bg-primary transition-all"
            style={{ width: `${(doneCount / steps.length) * 100}%` }}
          />
        </div>
        <span className="whitespace-nowrap text-sm text-muted-foreground">
          {t.onboarding.progress.replace("{n}", String(doneCount))}
        </span>
      </div>

      {doneCount === steps.length && !loading ? (
        <div className="rounded-md border border-emerald-300 bg-emerald-50 px-4 py-3 text-sm text-emerald-800">
          {t.onboarding.allDone}
        </div>
      ) : null}

      <div className="space-y-3">
        {steps.map((step, index) => (
          <Card
            key={step.title}
            className={step.done ? "opacity-70" : index === firstOpen ? "border-primary/50" : ""}
          >
            <CardContent className="flex items-start gap-4 py-4">
              {step.done ? (
                <CheckCircle2 className="mt-0.5 h-6 w-6 shrink-0 text-emerald-500" aria-hidden="true" />
              ) : (
                <Circle className="mt-0.5 h-6 w-6 shrink-0 text-muted-foreground/40" aria-hidden="true" />
              )}
              <div className="min-w-0 flex-1">
                <p className={`text-sm font-semibold ${step.done ? "line-through decoration-emerald-500/50" : ""}`}>
                  {index + 1}. {step.title}
                </p>
                <p className="mt-1 text-sm text-muted-foreground">{step.desc}</p>
              </div>
              {step.done ? (
                <span className="mt-1 shrink-0 text-xs font-medium text-emerald-600">{t.onboarding.done}</span>
              ) : (
                <Link
                  href={step.href}
                  className="mt-0.5 shrink-0 rounded-md border px-3 py-1.5 text-xs font-medium hover:bg-muted"
                >
                  {step.cta}
                </Link>
              )}
            </CardContent>
          </Card>
        ))}
      </div>

      {/* W3: Art. 4 AI-literacy module — a standing pointer, not a tracked
          step: completion is deliberately never recorded per user. */}
      <Card className="border-primary/30">
        <CardContent className="flex items-start gap-4 py-4">
          <BookOpen className="mt-0.5 h-6 w-6 shrink-0 text-primary" aria-hidden="true" />
          <div className="min-w-0 flex-1">
            <p className="text-sm font-semibold">{t.aiLiteracy.onboardingTitle}</p>
            <p className="mt-1 text-sm text-muted-foreground">{t.aiLiteracy.onboardingDesc}</p>
          </div>
          <Link
            href="/ai-literacy"
            className="mt-0.5 shrink-0 rounded-md border px-3 py-1.5 text-xs font-medium hover:bg-muted"
          >
            {t.aiLiteracy.onboardingCta}
          </Link>
        </CardContent>
      </Card>
    </div>
  );
}
