"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import {
  AlertTriangle,
  ArrowRight,
  ChevronRight,
  Info,
  RefreshCw,
  ShieldCheck,
  Sparkles,
  Target
} from "lucide-react";
import { Area, AreaChart, ResponsiveContainer } from "recharts";
import { Badge } from "@/components/ui/badge";
import { Button, buttonVariants } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";
import {
  apiBaseUrl,
  apiHeaders,
  getApprovals,
  getEmergingProblems,
  getExecutions,
  getOutcomeBoard,
  getProblems,
  getSignals,
  getWorkspace,
  wrongOriginHint
} from "@/lib/client-api";
import { formatMetric, percent } from "@/lib/format";
import { useI18n } from "@/lib/i18n";
import { fallbackProblems } from "@/lib/sample-data";
import { countInWindow, signalTrendSeries, withRollingAverage } from "@/lib/signal-trend";
import { cn } from "@/lib/utils";
import type {
  ApprovalRecord,
  EmergingProblemReport,
  EmergingProblemSignal,
  ExecutionRecord,
  OutcomeBoard,
  OutcomeBoardItem,
  ProblemSummary,
  SignalRecord,
  WorkspaceSettings
} from "@/lib/types";

type ConnectorSummary = { connector_type: string; is_active: boolean };

type SecondarySource = "approvals" | "executions" | "connectors" | "signals" | "emerging";

type DashboardData = {
  problems: ProblemSummary[];
  outcomeBoard: OutcomeBoard;
  approvals: ApprovalRecord[];
  executions: ExecutionRecord[];
  connectors: ConnectorSummary[];
  signals: SignalRecord[];
  emerging: EmergingProblemReport | null;
  workspace: WorkspaceSettings | null;
  failedSources: SecondarySource[];
  fetchedAt: number;
};

type QueueStatus = "blocked" | "review" | "watch";

type Band = "high" | "medium" | "low";

// ---------------------------------------------------------------------------
// One definition of "what state is this problem in", used by every module on
// the page — the queue, the counts, and the headline all derive from it, so
// the numbers reconcile by construction.
// ---------------------------------------------------------------------------

function statusOf(problem: ProblemSummary): QueueStatus {
  if (problem.status === "blocked_by_policy" || problem.approval_pressure === "blocked") return "blocked";
  if (
    problem.status === "approval_needed" ||
    problem.status === "validation_required" ||
    problem.approval_pressure === "needs_review"
  ) {
    return "review";
  }
  return "watch";
}

function isOpen(problem: ProblemSummary): boolean {
  return problem.status !== "resolved";
}

function impact(problem: ProblemSummary): number {
  return problem.impact_score ?? 0;
}

function band(value: number): Band {
  if (value >= 0.7) return "high";
  if (value >= 0.4) return "medium";
  return "low";
}

function impactBand(problem: ProblemSummary): Band {
  const declared = problem.impact_band?.toLowerCase();
  if (declared === "high" || declared === "medium" || declared === "low") return declared;
  return band(impact(problem));
}

const ACRONYMS = new Set(["cx", "ai", "api", "csv", "id", "qa", "sla"]);

// Owners and journeys arrive as machine identifiers ("cx_operations"); show
// them as names, not internals.
function humanize(value: string): string {
  return value
    .split(/[_\s]+/)
    .filter(Boolean)
    .map((word) => (ACRONYMS.has(word.toLowerCase()) ? word.toUpperCase() : word.charAt(0).toUpperCase() + word.slice(1)))
    .join(" ");
}

// Metric ids can carry a scope suffix after a colon
// ("signal_rate_per_day:purchase/checkout"); show the scope as a
// parenthetical instead of gluing it to the humanized name.
function metricLabel(metric: string): string {
  const colon = metric.indexOf(":");
  if (colon === -1) return humanize(metric);
  return `${humanize(metric.slice(0, colon))} (${metric.slice(colon + 1)})`;
}

function compact(value: number): string {
  return new Intl.NumberFormat("en", { notation: "compact" }).format(value);
}

function fill(template: string, vars: Record<string, string | number>): string {
  return Object.entries(vars).reduce(
    (result, [key, value]) => result.replaceAll(`{${key}}`, String(value)),
    template
  );
}

async function getConnectors(): Promise<ConnectorSummary[]> {
  const response = await fetch(`${apiBaseUrl()}/connectors`, { credentials: "include", headers: apiHeaders() });
  if (!response.ok) throw new Error(`connectors request failed (${response.status})`);
  return response.json() as Promise<ConnectorSummary[]>;
}

// --- explicit sample mode ---------------------------------------------------
// Sample data is entered deliberately from the error state, never substituted
// silently: fabricated numbers wearing production clothes are a trust hazard.

function sampleSummaries(): ProblemSummary[] {
  return fallbackProblems.map((problem) => ({
    problem_id: problem.problem_id,
    title: problem.title,
    journey: problem.journey,
    journey_stage: problem.journey_stage,
    owner: problem.owner,
    status: problem.status,
    impact_score: problem.impact_score ?? 0,
    impact_band: problem.impact_band ?? "low",
    evidence_confidence: problem.evidence_confidence,
    affected_customers: problem.affected_cohort.customers,
    affected_accounts: problem.affected_cohort.accounts,
    approval_pressure: problem.approval_pressure ?? "ready",
    top_action_classes: problem.action_proposals.slice(0, 3).map((action) => action.class),
    context_impact: problem.context_impact,
    journey_impact: problem.journey_impact
  }));
}

function sampleOutcomeBoard(): OutcomeBoard {
  const items: OutcomeBoardItem[] = fallbackProblems.map((problem) => ({
    problem_id: problem.problem_id,
    title: problem.title,
    owner: problem.owner,
    problem_status: problem.status,
    impact_score: problem.impact_score ?? 0,
    impact_band: problem.impact_band ?? "low",
    metric: problem.outcome_contract.primary_metric,
    baseline: problem.outcome_contract.baseline,
    success_threshold: problem.outcome_contract.success_threshold,
    latest_value: null,
    outcome_status: "not_measured",
    improvement_direction:
      problem.outcome_contract.success_threshold >= problem.outcome_contract.baseline ? "increase" : "decrease",
    latest_learning_status: null,
    latest_learning_reviewed_at: null,
    measurement_window_days: problem.outcome_contract.measurement_window_days,
    comparison_method: problem.outcome_contract.comparison_method,
    responsible_owner: problem.outcome_contract.responsible_owner
  }));

  return {
    total: items.length,
    not_measured: items.length,
    not_improved: 0,
    improving: 0,
    target_met: 0,
    learning_worked: 0,
    learning_partially_worked: 0,
    learning_did_not_work: 0,
    learning_inconclusive: 0,
    learning_measurement_invalid: 0,
    items
  };
}

function sampleData(): DashboardData {
  return {
    problems: sampleSummaries(),
    outcomeBoard: sampleOutcomeBoard(),
    approvals: [],
    executions: [],
    connectors: [],
    signals: [],
    emerging: null,
    workspace: null,
    failedSources: [],
    fetchedAt: Date.now()
  };
}

export default function DashboardPage() {
  const { t } = useI18n();
  const td = t.dashboard;
  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [demo, setDemo] = useState(false);
  const [reloadKey, setReloadKey] = useState(0);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      setLoading(true);
      // All eight requests fire in parallel; each module degrades on its own
      // instead of one slow call gating the whole page.
      const [problems, outcomeBoard, approvals, executions, connectors, signals, emerging, workspace] =
        await Promise.allSettled([
          getProblems(),
          getOutcomeBoard(),
          getApprovals(),
          getExecutions(),
          getConnectors(),
          getSignals(),
          getEmergingProblems(),
          getWorkspace()
        ]);
      if (cancelled) return;

      if (problems.status === "rejected" || outcomeBoard.status === "rejected") {
        const failure = problems.status === "rejected" ? problems.reason : (outcomeBoard as PromiseRejectedResult).reason;
        const message = failure instanceof Error ? failure.message : "";
        // Only a transport failure is actually an unreachable API; an HTTP
        // status already arrives here as a human sentence (client-api.ts).
        setLoadError(
          message.startsWith("Failed to fetch") || message.includes("NetworkError") || !message
            ? `${td.apiUnreachable}${wrongOriginHint()}`
            : message
        );
        setData(null);
        setLoading(false);
        return;
      }

      const failedSources: SecondarySource[] = [];
      if (approvals.status === "rejected") failedSources.push("approvals");
      if (executions.status === "rejected") failedSources.push("executions");
      if (connectors.status === "rejected") failedSources.push("connectors");
      if (signals.status === "rejected") failedSources.push("signals");
      if (emerging.status === "rejected") failedSources.push("emerging");

      setLoadError(null);
      setData({
        problems: problems.value,
        outcomeBoard: outcomeBoard.value,
        approvals: approvals.status === "fulfilled" ? approvals.value : [],
        executions: executions.status === "fulfilled" ? executions.value : [],
        connectors: connectors.status === "fulfilled" ? connectors.value : [],
        signals: signals.status === "fulfilled" ? signals.value : [],
        emerging: emerging.status === "fulfilled" ? emerging.value : null,
        workspace: workspace.status === "fulfilled" ? workspace.value : null,
        failedSources,
        fetchedAt: Date.now()
      });
      setLoading(false);
    }

    void load();
    return () => {
      cancelled = true;
    };
  }, [reloadKey, td.apiUnreachable]);

  if (loading && !demo) {
    return (
      <div role="status" aria-live="polite" className="space-y-6">
        <span className="sr-only">{td.loading}</span>
        <div className="h-5 w-64 animate-pulse rounded bg-muted" />
        {[0, 1, 2].map((block) => (
          <div key={block} className="rounded-lg border bg-card p-6">
            <div className="h-5 w-48 animate-pulse rounded bg-muted" />
            <div className="mt-5 space-y-3">
              <div className="h-14 animate-pulse rounded-lg bg-muted" />
              <div className="h-14 animate-pulse rounded-lg bg-muted" />
            </div>
          </div>
        ))}
      </div>
    );
  }

  if (loadError && !demo) {
    return (
      <Card className="mx-auto max-w-xl">
        <CardContent className="flex flex-col items-center gap-4 py-12 text-center">
          <AlertTriangle className="h-8 w-8 text-destructive" aria-hidden="true" />
          <div>
            <h1 className="text-lg font-semibold">{td.errorTitle}</h1>
            <p className="mt-2 text-sm text-muted-foreground">{loadError}</p>
          </div>
          <div className="flex flex-wrap justify-center gap-2">
            <Button size="sm" onClick={() => setReloadKey((key) => key + 1)}>
              {t.common.retry}
            </Button>
            <Button
              size="sm"
              variant="outline"
              onClick={() => {
                setDemo(true);
                setData(sampleData());
              }}
            >
              {td.exploreSample}
            </Button>
          </div>
        </CardContent>
      </Card>
    );
  }

  const problems = data?.problems ?? [];
  const board = data?.outcomeBoard ?? sampleOutcomeBoard();
  const approvals = data?.approvals ?? [];
  const executions = data?.executions ?? [];
  const connectors = data?.connectors ?? [];
  const signals = data?.signals ?? [];
  const emerging = data?.emerging ?? null;
  const workspace = data?.workspace ?? null;
  const failedSources = data?.failedSources ?? [];

  // --- the shared numbers ---------------------------------------------------
  const open = problems.filter(isOpen);
  const byImpact = (a: ProblemSummary, b: ProblemSummary) => impact(b) - impact(a);
  const blocked = open.filter((problem) => statusOf(problem) === "blocked").sort(byImpact);
  const review = open.filter((problem) => statusOf(problem) === "review").sort(byImpact);
  const watch = open.filter((problem) => statusOf(problem) === "watch").sort(byImpact);
  const highImpact = open.filter((problem) => impact(problem) >= 0.7 || problem.impact_band === "high");
  const drafts = executions.filter((execution) => execution.status === "draft_created");
  const approvedActions = new Set(
    approvals.filter((approval) => approval.decision === "approved").map((approval) => approval.action_id)
  ).size;
  const measured = board.total - board.not_measured;
  const improvingOutcomes = board.improving + board.target_met;
  const activeConnectors = connectors.filter((connector) => connector.is_active).length;
  const thisWeek = countInWindow(signals, 7);
  const spark = withRollingAverage(signalTrendSeries(signals, 30)).map((point) => ({ value: point.avg }));

  const headline = (() => {
    if (open.length === 0) return td.headlineNone;
    if (blocked.length > 0) {
      return `${blocked.length} ${blocked.length === 1 ? td.headlineBlockedOne : td.headlineBlockedMany}`;
    }
    if (review.length > 0) {
      return `${review.length} ${review.length === 1 ? td.headlineReviewOne : td.headlineReviewMany}`;
    }
    if (improvingOutcomes > 0) {
      return `${improvingOutcomes} ${improvingOutcomes === 1 ? td.headlineImprovingOne : td.headlineImprovingMany}`;
    }
    const top = [...open].sort(byImpact)[0];
    return `${top.title} ${td.headlineTop}`;
  })();

  // Fold "Unknown"-journey duplicates into their named sibling; the API emits
  // both while clustering settles (flagged upstream as an API follow-up).
  const emergingItems = (() => {
    if (!emerging) return [] as EmergingProblemSignal[];
    const byTitle = new Map<string, EmergingProblemSignal>();
    for (const item of emerging.signals) {
      const current = byTitle.get(item.title);
      if (!current) {
        byTitle.set(item.title, item);
        continue;
      }
      const currentUnknown = current.journey.toLowerCase() === "unknown";
      const itemUnknown = item.journey.toLowerCase() === "unknown";
      if ((currentUnknown && !itemUnknown) || (currentUnknown === itemUnknown && item.emerging_score > current.emerging_score)) {
        byTitle.set(item.title, item);
      }
    }
    return [...byTitle.values()].sort((a, b) => b.emerging_score - a.emerging_score).slice(0, 4);
  })();

  const firstRun = !demo && open.length === 0 && problems.length === 0 && signals.length === 0 && board.total === 0;

  const sourceLabels: Record<SecondarySource, string> = {
    approvals: td.srcApprovals,
    executions: td.srcExecutions,
    connectors: td.srcConnectors,
    signals: td.srcSignals,
    emerging: td.srcEmerging
  };

  const queueGroups: { status: QueueStatus; label: string; items: ProblemSummary[] }[] = [
    { status: "blocked", label: td.groupBlocked, items: blocked },
    { status: "review", label: td.groupReview, items: review },
    { status: "watch", label: td.groupWatch, items: watch.slice(0, 3) }
  ];

  const verbFor: Record<QueueStatus, string> = { blocked: td.decide, review: td.review, watch: td.open };

  const bandLabel: Record<Band, string> = { high: td.bandHigh, medium: td.bandMedium, low: td.bandLow };

  const updatedTime = data
    ? new Date(data.fetchedAt).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })
    : "";

  const loopStages: {
    href: string;
    label: string;
    value: string;
    sub: string;
    subClass?: string;
    sparkline?: boolean;
  }[] = [
    {
      href: "/signals",
      label: td.loopSignals,
      value: String(thisWeek),
      sub: thisWeek > 0 ? fill(td.weekDelta, { n: thisWeek }) : td.weekDeltaNone,
      sparkline: signals.length > 0
    },
    {
      href: "/insights",
      label: td.loopProblems,
      value: String(open.length),
      sub: fill(td.highImpactCount, { n: highImpact.length })
    },
    {
      href: "/actions",
      label: td.loopDecisions,
      value: String(blocked.length + review.length),
      sub: blocked.length > 0 ? fill(td.blockedCount, { n: blocked.length }) : td.noneBlocked,
      subClass: blocked.length > 0 ? "text-destructive" : undefined
    },
    {
      href: "/actions",
      label: td.loopActions,
      value: String(drafts.length),
      sub: fill(td.approvedCount, { n: approvedActions })
    },
    {
      href: "/learnings",
      label: td.loopOutcomes,
      value: `${improvingOutcomes}/${board.total}`,
      sub:
        board.target_met > 0
          ? fill(td.targetMetCount, { n: board.target_met })
          : fill(td.measuredPending, { measured, pending: board.not_measured }),
      subClass: board.target_met > 0 ? "text-emerald-600" : undefined
    }
  ];

  return (
    <TooltipProvider delayDuration={200}>
      <div className="space-y-6">
        {demo ? (
          <div
            role="status"
            className="flex items-center justify-between gap-3 rounded-md border border-amber-500/50 bg-amber-500/10 p-3 text-sm text-amber-800"
          >
            <span>{td.sampleNotice}</span>
            <Button
              size="sm"
              variant="outline"
              className="shrink-0"
              onClick={() => {
                setDemo(false);
                setReloadKey((key) => key + 1);
              }}
            >
              {td.backToLive}
            </Button>
          </div>
        ) : null}

        {!demo && failedSources.length > 0 ? (
          <div
            role="status"
            className="flex items-center justify-between gap-3 rounded-md border border-dashed border-amber-500/50 bg-amber-500/5 p-3 text-sm text-amber-700"
          >
            <span>
              {td.partialBanner} ({failedSources.map((source) => sourceLabels[source]).join(", ")})
            </span>
            <button
              type="button"
              onClick={() => setReloadKey((key) => key + 1)}
              className="shrink-0 rounded-md border px-2 py-1 text-xs font-medium hover:bg-amber-500/10"
            >
              {t.common.retry}
            </button>
          </div>
        ) : null}

        {/* Context line: whose data, how fresh, is it flowing. */}
        <div className="flex flex-wrap items-center justify-between gap-x-4 gap-y-2 text-sm text-muted-foreground">
          <div className="flex items-center gap-3">
            {workspace?.name ? <span className="font-medium text-foreground">{workspace.name}</span> : null}
            {updatedTime ? <span>{fill(td.updatedAt, { time: updatedTime })}</span> : null}
            <button
              type="button"
              aria-label={td.refresh}
              title={td.refresh}
              onClick={() => setReloadKey((key) => key + 1)}
              className="rounded-md p-1 hover:bg-accent hover:text-foreground"
            >
              <RefreshCw className="h-3.5 w-3.5" aria-hidden="true" />
            </button>
          </div>
          <div className="flex items-center gap-3">
            {demo ? <Badge variant="warning">{td.sampleChip}</Badge> : null}
            <Link href="/integrations" className="inline-flex items-center gap-2 hover:text-foreground">
              <span
                aria-hidden="true"
                className={cn(
                  "h-2 w-2 rounded-full",
                  connectors.length > 0 && activeConnectors === connectors.length ? "bg-emerald-500" : "bg-amber-500"
                )}
              />
              {connectors.length > 0
                ? fill(td.connectorsActive, { active: activeConnectors, total: connectors.length })
                : td.connectorsNone}
            </Link>
          </div>
        </div>

        <div className={cn("space-y-6", demo && "opacity-90 saturate-[0.7]")}>
          {firstRun ? (
            <Card>
              <CardContent className="py-10">
                <div className="mx-auto max-w-xl text-center">
                  <h1 className="text-2xl font-semibold tracking-tight">{td.firstRunTitle}</h1>
                  <p className="mt-3 text-sm text-muted-foreground">{td.firstRunBody}</p>
                  <ol className="mx-auto mt-6 max-w-md space-y-2 text-left text-sm text-muted-foreground">
                    {[
                      t.onboarding.step1Title,
                      t.onboarding.step2Title,
                      t.onboarding.step3Title,
                      t.onboarding.step4Title,
                      t.onboarding.step5Title
                    ].map((step, index) => (
                      <li key={step} className="flex items-start gap-3">
                        <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-primary/10 text-xs font-semibold text-primary">
                          {index + 1}
                        </span>
                        {step}
                      </li>
                    ))}
                  </ol>
                  <Link href="/onboarding" className={cn(buttonVariants({ size: "sm" }), "mt-6 gap-2")}>
                    {td.firstRunCta}
                    <ArrowRight className="h-4 w-4" aria-hidden="true" />
                  </Link>
                </div>
              </CardContent>
            </Card>
          ) : (
            <>
              {/* 1 · Decide: what is waiting on a human. */}
              <Card>
                <CardHeader className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
                  <div className="max-w-2xl">
                    <h1 className="text-xl font-semibold tracking-tight md:text-2xl">{headline}</h1>
                    {open.length > 0 ? (
                      <CardDescription className="mt-1.5 flex items-center gap-2">
                        {fill(td.queueCounts, { blocked: blocked.length, review: review.length, watch: watch.length })}
                        <Tooltip>
                          <TooltipTrigger asChild>
                            <button
                              type="button"
                              aria-label={td.chipHelpLabel}
                              className="rounded-full text-muted-foreground hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                            >
                              <Info className="h-3.5 w-3.5" aria-hidden="true" />
                            </button>
                          </TooltipTrigger>
                          <TooltipContent>
                            <p>
                              <span className="font-semibold">{td.impact}:</span> {td.impactHelp}
                            </p>
                            <p className="mt-1.5">
                              <span className="font-semibold">{td.confidence}:</span> {td.confidenceHelp}
                            </p>
                          </TooltipContent>
                        </Tooltip>
                      </CardDescription>
                    ) : null}
                  </div>
                  <Link href="/actions" className={cn(buttonVariants({ size: "sm" }), "shrink-0 gap-2")}>
                    {td.openQueue}
                    <ArrowRight className="h-4 w-4" aria-hidden="true" />
                  </Link>
                </CardHeader>
                <CardContent className="space-y-5">
                  {workspace?.works_council_mode ? (
                    <p
                      role="status"
                      className="flex items-center gap-2 rounded-md border border-sky-500/40 bg-sky-500/5 px-3 py-2 text-xs text-sky-700"
                    >
                      <ShieldCheck className="h-3.5 w-3.5 shrink-0" aria-hidden="true" />
                      {t.worksCouncil.banner}
                    </p>
                  ) : null}

                  {open.length === 0 ? (
                    <div className="py-6 text-center">
                      <p className="font-medium">{td.queueEmpty}</p>
                      <p className="mt-1 text-sm text-muted-foreground">{td.queueEmptyDetail}</p>
                    </div>
                  ) : (
                    queueGroups
                      .filter((group) => group.items.length > 0)
                      .map((group) => (
                        <section key={group.status} aria-label={group.label}>
                          <h2 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                            {group.label} · {group.status === "watch" ? watch.length : group.items.length}
                          </h2>
                          <div className="mt-2 space-y-2">
                            {group.items.map((problem) => (
                              <Link
                                key={problem.problem_id}
                                href={`/insights/${problem.problem_id}`}
                                className="block rounded-lg border p-4 transition-colors hover:bg-muted/50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                              >
                                <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
                                  <div className="min-w-0">
                                    <p className="font-semibold leading-snug">{problem.title}</p>
                                    <p className="mt-1 text-sm text-muted-foreground">
                                      {humanize(problem.journey)} / {humanize(problem.journey_stage)} · {t.common.owner}:{" "}
                                      {humanize(problem.owner)}
                                    </p>
                                  </div>
                                  <div className="flex shrink-0 flex-wrap items-center gap-2 md:justify-end">
                                    <Badge
                                      variant={
                                        group.status === "blocked"
                                          ? "destructive"
                                          : group.status === "review"
                                            ? "warning"
                                            : "secondary"
                                      }
                                    >
                                      {group.status === "blocked"
                                        ? td.chipBlocked
                                        : group.status === "review"
                                          ? td.groupReview
                                          : td.watching}
                                    </Badge>
                                    <Badge
                                      variant="outline"
                                      title={`${td.impact} ${percent(impact(problem))} — ${td.impactHelp}`}
                                    >
                                      {td.impact} {bandLabel[impactBand(problem)]}
                                    </Badge>
                                    <Badge
                                      variant="outline"
                                      title={`${td.confidence} ${percent(problem.evidence_confidence)} — ${td.confidenceHelp}`}
                                    >
                                      {td.confidence} {bandLabel[band(problem.evidence_confidence ?? 0)]}
                                    </Badge>
                                    <Badge variant="outline">
                                      {compact(problem.affected_customers)} {t.common.customers}
                                    </Badge>
                                    <span className="inline-flex items-center gap-1 text-sm font-medium text-primary">
                                      {verbFor[group.status]}
                                      <ArrowRight className="h-3.5 w-3.5" aria-hidden="true" />
                                    </span>
                                  </div>
                                </div>
                              </Link>
                            ))}
                          </div>
                        </section>
                      ))
                  )}

                  <Link
                    href="/insights"
                    className="inline-flex items-center gap-1.5 text-sm font-medium text-primary hover:underline"
                  >
                    {td.viewAllProblems}
                    <ArrowRight className="h-3.5 w-3.5" aria-hidden="true" />
                  </Link>
                </CardContent>
              </Card>

              {/* 2 · The loop: feedback → problems → decisions → actions → outcomes. */}
              <Card>
                <CardHeader>
                  <CardTitle>{td.loopTitle}</CardTitle>
                  <CardDescription>{td.loopSubtitle}</CardDescription>
                </CardHeader>
                <CardContent>
                  <ol className="flex flex-col gap-2 xl:flex-row xl:items-stretch">
                    {loopStages.map((stage, index) => (
                      <li key={stage.label} className="flex flex-1 items-stretch gap-2">
                        <Link
                          href={stage.href}
                          aria-label={`${stage.label}: ${stage.value} — ${stage.sub}`}
                          className="flex-1 rounded-lg border p-3 transition-colors hover:border-primary/60 hover:bg-muted/40 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                        >
                          <p className="text-xs text-muted-foreground">{stage.label}</p>
                          {stage.sparkline ? (
                            <div className="mt-1 h-8" aria-hidden="true">
                              <ResponsiveContainer width="100%" height="100%">
                                <AreaChart data={spark} margin={{ top: 2, right: 0, bottom: 0, left: 0 }}>
                                  <Area
                                    type="monotone"
                                    dataKey="value"
                                    stroke="hsl(var(--primary))"
                                    strokeWidth={2}
                                    fill="hsl(var(--primary) / 0.12)"
                                    isAnimationActive={false}
                                    dot={false}
                                  />
                                </AreaChart>
                              </ResponsiveContainer>
                            </div>
                          ) : (
                            <p className="mt-1 text-2xl font-semibold tabular-nums">{stage.value}</p>
                          )}
                          <p className={cn("mt-1 text-xs text-muted-foreground", stage.subClass)}>{stage.sub}</p>
                        </Link>
                        {index < loopStages.length - 1 ? (
                          <ChevronRight
                            className="hidden shrink-0 self-center text-muted-foreground/40 xl:block"
                            aria-hidden="true"
                          />
                        ) : null}
                      </li>
                    ))}
                  </ol>
                </CardContent>
              </Card>

              {/* 3 · Watch: what is new or moving, and whether actions worked. */}
              <div className="grid items-start gap-4 xl:grid-cols-2">
                <Card>
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                      <Sparkles className="h-5 w-5 text-amber-500" aria-hidden="true" /> {td.emergingProblems}
                    </CardTitle>
                    <CardDescription>{td.emergingSubtitle}</CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-2">
                    {emergingItems.length === 0 ? (
                      <p className="text-sm text-muted-foreground">{td.emergingEmpty}</p>
                    ) : (
                      emergingItems.map((item) => (
                        <Link
                          key={item.candidate_id}
                          href="/sources"
                          className="block rounded-lg border p-3 transition-colors hover:bg-muted/50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                        >
                          <div className="flex items-start justify-between gap-2">
                            <p className="text-sm font-medium leading-snug">{item.title}</p>
                            <Badge variant={item.trend_label === "action" ? "warning" : "secondary"}>
                              {item.trend_label === "action" ? td.rising : td.watching}
                            </Badge>
                          </div>
                          <p className="mt-1 text-xs text-muted-foreground">
                            {humanize(item.journey)} / {humanize(item.journey_stage)} · {item.signal_count}{" "}
                            {t.common.signals} · {item.customer_count} {t.common.customers} · {item.source_count}{" "}
                            {t.common.sources}
                          </p>
                          {item.drivers[0] || item.recommended_next_step ? (
                            <p className="mt-1 text-xs text-muted-foreground">
                              <span className="font-medium text-foreground">{td.whyFlagged}:</span>{" "}
                              {item.drivers[0] ?? item.recommended_next_step}
                            </p>
                          ) : null}
                        </Link>
                      ))
                    )}
                    <Link
                      href="/sources"
                      className="inline-flex items-center gap-1.5 pt-1 text-sm font-medium text-primary hover:underline"
                    >
                      {td.reviewCandidates}
                      <ArrowRight className="h-3.5 w-3.5" aria-hidden="true" />
                    </Link>
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                      <Target className="h-5 w-5 text-emerald-500" aria-hidden="true" /> {td.outcomes}
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-3">
                    <div className="grid grid-cols-2 gap-2 text-sm sm:grid-cols-4">
                      {[
                        { label: t.outcomeBoard.targetMet, value: board.target_met, className: "text-emerald-600" },
                        { label: t.outcomeBoard.improving, value: board.improving, className: "text-emerald-600" },
                        { label: t.outcomeBoard.notImproved, value: board.not_improved, className: "text-amber-600" },
                        { label: t.outcomeBoard.notMeasured, value: board.not_measured, className: "" }
                      ].map((tile) => (
                        <div key={tile.label} className="rounded-lg border p-2.5">
                          <p className="text-xs text-muted-foreground">{tile.label}</p>
                          <p className={cn("mt-0.5 text-lg font-semibold tabular-nums", tile.className)}>{tile.value}</p>
                        </div>
                      ))}
                    </div>
                    {board.items.length === 0 ? (
                      <p className="text-sm text-muted-foreground">{td.outcomesEmpty}</p>
                    ) : (
                      <div className="space-y-2">
                        {board.items.slice(0, 4).map((item) => (
                          <Link
                            key={item.problem_id}
                            href={`/insights/${item.problem_id}`}
                            className="block rounded-lg border p-3 text-sm transition-colors hover:bg-muted/50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                          >
                            <div className="flex items-center justify-between gap-3">
                              <span className="truncate font-medium" title={item.title}>
                                {item.title}
                              </span>
                              <Badge
                                variant={
                                  item.outcome_status === "target_met" || item.outcome_status === "improving"
                                    ? "success"
                                    : item.outcome_status === "not_improved"
                                      ? "warning"
                                      : "outline"
                                }
                              >
                                {item.outcome_status === "not_measured"
                                  ? t.outcomeBoard.notMeasured
                                  : item.outcome_status === "target_met"
                                    ? t.outcomeBoard.targetMet
                                    : item.outcome_status === "improving"
                                      ? t.outcomeBoard.improving
                                      : t.outcomeBoard.notImproved}
                              </Badge>
                            </div>
                            <p className="mt-1 text-xs text-muted-foreground">
                              {metricLabel(item.metric)}: {formatMetric(item.baseline)} →{" "}
                              {item.latest_value === null || item.latest_value === undefined
                                ? "—"
                                : formatMetric(item.latest_value)}{" "}
                              · {td.target} {formatMetric(item.success_threshold)}
                            </p>
                          </Link>
                        ))}
                      </div>
                    )}
                    <Link
                      href="/learnings"
                      className="inline-flex items-center gap-1.5 pt-1 text-sm font-medium text-primary hover:underline"
                    >
                      {td.openLearnings}
                      <ArrowRight className="h-3.5 w-3.5" aria-hidden="true" />
                    </Link>
                  </CardContent>
                </Card>
              </div>
            </>
          )}
        </div>
      </div>
    </TooltipProvider>
  );
}
