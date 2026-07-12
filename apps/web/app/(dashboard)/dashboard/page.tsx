"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  ArrowRight,
  CheckCircle,
  ClipboardCheck,
  Gauge,
  Plug,
  ShieldAlert,
  Sparkles,
  Target,
  TrendingUp,
  Users
} from "lucide-react";
import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import {
  apiBaseUrl,
  apiHeaders,
  getApprovals,
  getEmergingProblems,
  getExecutions,
  getOutcomeBoard,
  getProblems,
  getSignals
} from "@/lib/client-api";
import { AiLiteracyBanner } from "@/app/components/ai-literacy-banner";
import { WorksCouncilBanner } from "@/app/components/works-council-banner";
import { percent } from "@/lib/format";
import { useI18n } from "@/lib/i18n";
import { fallbackProblems } from "@/lib/sample-data";
import type {
  ActionClass,
  ApprovalRecord,
  EmergingProblemReport,
  ExecutionRecord,
  OutcomeBoard,
  OutcomeBoardItem,
  ProblemSummary,
  SignalRecord
} from "@/lib/types";

type ConnectorSummary = { connector_type: string; is_active: boolean };

type DashboardData = {
  problems: ProblemSummary[];
  outcomeBoard: OutcomeBoard;
  approvals: ApprovalRecord[];
  executions: ExecutionRecord[];
  connectors: ConnectorSummary[];
  signals: SignalRecord[];
  emerging: EmergingProblemReport | null;
  usingFallback: boolean;
  partialSources: string[];
};

type AttentionItem = {
  problem: ProblemSummary;
  reason: string;
  severity: "blocked" | "review" | "watch";
};

type OwnerLoad = {
  owner: string;
  problems: number;
  affectedCustomers: number;
  blocked: number;
  topProblem: ProblemSummary;
};

function actionClassLabels(td: ReturnType<typeof useI18n>["t"]["dashboard"]): Record<ActionClass, string> {
  return {
    structural: td.classStructural,
    customer_recovery: td.classRecovery,
    journey_intervention: td.classIntervention,
    research: td.classResearch,
    governance: td.classGovernance
  };
}

function outcomeStatusLabel(status: string, t: ReturnType<typeof useI18n>["t"]): string {
  const map: Record<string, string> = {
    not_measured: t.outcomeBoard.notMeasured,
    target_met: t.outcomeBoard.targetMet,
    improving: t.outcomeBoard.improving,
    not_improved: t.outcomeBoard.notImproved,
  };
  return map[status] ?? status.replaceAll("_", " ");
}

function label(value: string): string {
  return value.replaceAll("_", " ");
}


function compact(value: number): string {
  return new Intl.NumberFormat("en", { notation: "compact" }).format(value);
}

function fallbackSummaries(): ProblemSummary[] {
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

function fallbackOutcomeBoard(): OutcomeBoard {
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

function impact(problem: ProblemSummary): number {
  return problem.impact_score ?? 0;
}

function blockingChecks(problem: ProblemSummary): number {
  return problem.status === "blocked_by_policy" || problem.approval_pressure === "blocked" ? 1 : 0;
}

function needsReview(problem: ProblemSummary): boolean {
  return problem.status === "approval_needed" || problem.status === "validation_required" || problem.approval_pressure === "needs_review";
}

function isResolved(problem: ProblemSummary): boolean {
  return problem.status === "resolved";
}

function leadershipHeadline(
  problems: ProblemSummary[],
  outcomeBoard: OutcomeBoard,
  td: ReturnType<typeof useI18n>["t"]["dashboard"]
): string {
  const top = [...problems].sort((a, b) => impact(b) - impact(a))[0];
  if (!top) return td.headlineNone;

  const blocked = problems.filter((problem) => blockingChecks(problem) > 0).length;
  const improving = outcomeBoard.improving + outcomeBoard.target_met;
  if (blocked > 0) return `${blocked} ${blocked === 1 ? td.headlineBlockedOne : td.headlineBlockedMany}`;
  if (improving > 0) return `${improving} ${improving === 1 ? td.headlineImprovingOne : td.headlineImprovingMany}`;
  return `${top.title} ${td.headlineTop}`;
}

function attentionItems(problems: ProblemSummary[], td: ReturnType<typeof useI18n>["t"]["dashboard"]): AttentionItem[] {
  return [...problems]
    .filter((problem) => !isResolved(problem))
    .map((problem) => {
      const blocked = blockingChecks(problem);
      if (blocked > 0) return { problem, reason: td.reasonBlocked, severity: "blocked" as const };
      if (needsReview(problem)) return { problem, reason: td.reasonReview, severity: "review" as const };
      return { problem, reason: `${compact(problem.affected_customers)} ${td.reasonWatch}`, severity: "watch" as const };
    })
    .sort((a, b) => {
      const severity = { blocked: 3, review: 2, watch: 1 };
      return severity[b.severity] - severity[a.severity] || impact(b.problem) - impact(a.problem);
    })
    .slice(0, 5);
}

function ownerLoads(problems: ProblemSummary[]): OwnerLoad[] {
  const byOwner = new Map<string, ProblemSummary[]>();
  for (const problem of problems.filter((item) => !isResolved(item))) {
    byOwner.set(problem.owner, [...(byOwner.get(problem.owner) ?? []), problem]);
  }

  return [...byOwner.entries()]
    .map(([owner, items]) => {
      const sorted = [...items].sort((a, b) => impact(b) - impact(a));
      return {
        owner,
        problems: items.length,
        affectedCustomers: items.reduce((total, problem) => total + problem.affected_customers, 0),
        blocked: items.filter((problem) => blockingChecks(problem) > 0).length,
        topProblem: sorted[0]
      };
    })
    .sort((a, b) => b.blocked - a.blocked || b.affectedCustomers - a.affectedCustomers)
    .slice(0, 4);
}

function actionMix(problems: ProblemSummary[]): { actionClass: ActionClass; count: number }[] {
  const counts = new Map<ActionClass, number>();
  for (const actionClass of problems.flatMap((problem) => problem.top_action_classes)) {
    counts.set(actionClass, (counts.get(actionClass) ?? 0) + 1);
  }

  return [...counts.entries()]
    .map(([actionClass, count]) => ({ actionClass, count }))
    .sort((a, b) => b.count - a.count);
}

function approvedActionIds(approvals: ApprovalRecord[]): Set<string> {
  return new Set(approvals.filter((approval) => approval.decision === "approved").map((approval) => approval.action_id));
}

// Signals per day over the trailing window; the dashboard's time axis.
function signalTrendSeries(signals: SignalRecord[], days = 30): { day: string; count: number }[] {
  const now = Date.now();
  const dayMs = 86_400_000;
  const buckets = new Map<string, number>();
  for (let offset = days - 1; offset >= 0; offset -= 1) {
    buckets.set(new Date(now - offset * dayMs).toISOString().slice(0, 10), 0);
  }
  for (const signal of signals) {
    const day = (signal.timestamp || "").slice(0, 10);
    if (buckets.has(day)) buckets.set(day, (buckets.get(day) ?? 0) + 1);
  }
  return [...buckets.entries()].map(([day, count]) => ({ day: day.slice(5), count }));
}

async function getConnectors(): Promise<ConnectorSummary[]> {
  const response = await fetch(`${apiBaseUrl()}/connectors`, { headers: apiHeaders() });
  // Throw on a non-ok status so the caller's .catch records it as a partial source;
  // returning [] here silently hid connector HTTP errors from the "partial data" notice.
  if (!response.ok) throw new Error(`connectors request failed (${response.status})`);
  return response.json() as Promise<ConnectorSummary[]>;
}

function MetricCard({
  title,
  value,
  detail,
  tone = "neutral"
}: {
  title: string;
  value: string | number;
  detail: string;
  tone?: "neutral" | "good" | "warn" | "bad";
}) {
  const toneClass = {
    neutral: "text-foreground",
    good: "text-emerald-600",
    warn: "text-amber-600",
    bad: "text-destructive"
  }[tone];

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-sm font-medium text-muted-foreground">{title}</CardTitle>
      </CardHeader>
      <CardContent>
        <div className={`text-3xl font-bold ${toneClass}`}>{value}</div>
        <p className="mt-1 text-xs text-muted-foreground">{detail}</p>
      </CardContent>
    </Card>
  );
}

export default function DashboardPage() {
  const { t } = useI18n();
  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [reloadKey, setReloadKey] = useState(0);

  useEffect(() => {
    async function load() {
      try {
        const [problems, outcomeBoard] = await Promise.all([getProblems(), getOutcomeBoard()]);
        const partialSources: string[] = [];
        const [approvals, executions, connectors, signals, emerging] = await Promise.all([
          getApprovals().catch(() => {
            partialSources.push("approvals");
            return [];
          }),
          getExecutions().catch(() => {
            partialSources.push("executions");
            return [];
          }),
          getConnectors().catch(() => {
            partialSources.push("connectors");
            return [];
          }),
          getSignals().catch(() => {
            partialSources.push("signals");
            return [] as SignalRecord[];
          }),
          getEmergingProblems().catch(() => {
            partialSources.push("emerging problems");
            return null;
          })
        ]);
        setData({ problems, outcomeBoard, approvals, executions, connectors, signals, emerging, usingFallback: false, partialSources });
      } catch {
        setData({
          problems: fallbackSummaries(),
          outcomeBoard: fallbackOutcomeBoard(),
          approvals: [],
          executions: [],
          connectors: [],
          signals: [],
          emerging: null,
          usingFallback: true,
          partialSources: []
        });
      } finally {
        setLoading(false);
      }
    }

    void load();
  }, [reloadKey]);

  if (loading) return <div role="status" aria-live="polite" className="text-muted-foreground">Loading leadership dashboard...</div>;

  const problems = data?.problems ?? [];
  const outcomeBoard = data?.outcomeBoard ?? fallbackOutcomeBoard();
  const approvals = data?.approvals ?? [];
  const executions = data?.executions ?? [];
  const connectors = data?.connectors ?? [];
  const signals = data?.signals ?? [];
  const emerging = data?.emerging ?? null;
  const trendSeries = signalTrendSeries(signals);
  const actionClassCount = new Set(problems.flatMap((problem) => problem.top_action_classes)).size;
  const approvedActions = approvedActionIds(approvals);
  const blockedProblems = problems.filter((problem) => blockingChecks(problem) > 0);
  const highImpactProblems = problems.filter((problem) => impact(problem) >= 0.7 || problem.impact_band === "high");
  const representedCustomers = problems.reduce((total, problem) => total + problem.affected_customers, 0);
  const interventionReady = problems.filter((problem) => problem.top_action_classes.includes("journey_intervention"));
  const measuredOutcomes = outcomeBoard.total - outcomeBoard.not_measured;
  const improvingOutcomes = outcomeBoard.improving + outcomeBoard.target_met;
  const activeConnectors = connectors.filter((connector) => connector.is_active).length;
  const pendingDecisionProblems = problems.filter((problem) => !isResolved(problem) && needsReview(problem));
  const attention = attentionItems(problems, t.dashboard);
  const loads = ownerLoads(problems);
  const mix = actionMix(problems);
  const maxMix = Math.max(...mix.map((item) => item.count), 1);
  const measuredRate = outcomeBoard.total > 0 ? measuredOutcomes / outcomeBoard.total : 0;

  return (
    <div className="space-y-6">
      <AiLiteracyBanner />
      <div className="rounded-2xl border bg-card p-8 shadow-sm">
        <div className="flex flex-col gap-6 lg:flex-row lg:items-end lg:justify-between">
          <div className="max-w-3xl">
            <p className="text-xs font-semibold uppercase tracking-[0.2em] text-primary">{t.dashboard.overview}</p>
            <h1 className="mt-3 text-3xl font-bold tracking-tight text-foreground">
              {leadershipHeadline(problems, outcomeBoard, t.dashboard)}
            </h1>
            <p className="mt-3 text-sm text-muted-foreground">
              {t.dashboard.subtitle}
            </p>
          </div>
          <div className="flex shrink-0 gap-8">
            <div>
              <p className="text-xs uppercase tracking-wide text-muted-foreground">{t.dashboard.customersAffected}</p>
              <p className="mt-1 text-3xl font-semibold tabular-nums">{compact(representedCustomers)}</p>
            </div>
            <div className="border-l pl-8">
              <p className="text-xs uppercase tracking-wide text-muted-foreground">{t.dashboard.outcomesMeasured}</p>
              <p className="mt-1 text-3xl font-semibold tabular-nums">{percent(measuredRate)}</p>
            </div>
          </div>
        </div>
      </div>

      {data?.usingFallback ? (
        <div role="alert" className="flex items-center justify-between gap-3 rounded-md border border-dashed border-yellow-500/50 bg-yellow-500/5 p-3 text-sm text-yellow-700 dark:text-yellow-400">
          <span>{t.dashboard.sampleBanner}</span>
          <button type="button" onClick={() => setReloadKey((k) => k + 1)} className="shrink-0 rounded-md border px-2 py-1 text-xs font-medium hover:bg-yellow-500/10">
            {t.common.retry}
          </button>
        </div>
      ) : null}

      {!data?.usingFallback && data?.partialSources.length ? (
        <div role="alert" className="flex items-center justify-between gap-3 rounded-md border border-dashed border-amber-500/50 bg-amber-500/5 p-3 text-sm text-amber-700 dark:text-amber-400">
          <span>{t.dashboard.partialBanner} ({data.partialSources.join(", ")})</span>
          <button type="button" onClick={() => setReloadKey((k) => k + 1)} className="shrink-0 rounded-md border px-2 py-1 text-xs font-medium hover:bg-amber-500/10">
            {t.common.retry}
          </button>
        </div>
      ) : null}

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-5">
        <MetricCard title={t.dashboard.highImpact} value={highImpactProblems.length} detail={`${problems.length} ${t.dashboard.highImpactDetail}`} tone={highImpactProblems.length > 0 ? "warn" : "good"} />
        <MetricCard title={t.dashboard.governanceBlockers} value={blockedProblems.length} detail={t.dashboard.governanceBlockersDetail} tone={blockedProblems.length > 0 ? "bad" : "good"} />
        <MetricCard title={t.dashboard.pendingDecisions} value={pendingDecisionProblems.length} detail={`${approvals.length} ${t.dashboard.pendingDecisionsDetail}`} tone={pendingDecisionProblems.length > 0 ? "warn" : "good"} />
        <MetricCard title={t.dashboard.outcomesImproving} value={`${improvingOutcomes}/${outcomeBoard.total}`} detail={`${measuredOutcomes} ${t.dashboard.measuredPending.replace("{pending}", String(outcomeBoard.not_measured))}`} tone={improvingOutcomes > 0 ? "good" : "neutral"} />
        <MetricCard title={t.dashboard.connectors} value={`${activeConnectors}/${connectors.length}`} detail={t.dashboard.connectorsDetail} tone={activeConnectors > 0 ? "good" : "neutral"} />
      </div>

      <div className="grid gap-4 xl:grid-cols-[1.4fr_0.8fr]">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-lg">
              <TrendingUp className="h-5 w-5 text-primary" /> {t.dashboard.signalVolume}
            </CardTitle>
          </CardHeader>
          <CardContent>
            {signals.length === 0 ? (
              <p className="text-sm text-muted-foreground">{t.dashboard.signalVolumeEmpty}</p>
            ) : (
              <div className="h-56">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={trendSeries} margin={{ top: 4, right: 8, bottom: 0, left: -20 }}>
                    <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                    <XAxis dataKey="day" tick={{ fontSize: 11 }} interval="preserveStartEnd" minTickGap={24} />
                    <YAxis tick={{ fontSize: 11 }} allowDecimals={false} />
                    <Tooltip formatter={(value) => [`${value} signals`, "Volume"]} labelFormatter={(day) => `Day ${day}`} />
                    <Area type="monotone" dataKey="count" stroke="hsl(173 58% 39%)" fill="hsl(173 58% 39% / 0.15)" strokeWidth={2} />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-lg">
              <Sparkles className="h-5 w-5 text-amber-500" /> {t.dashboard.emergingProblems}
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {!emerging || emerging.signals.length === 0 ? (
              <p className="text-sm text-muted-foreground">{t.dashboard.emergingEmpty}</p>
            ) : (
              emerging.signals.slice(0, 5).map((item) => (
                <div key={item.candidate_id} className="rounded-md border p-3">
                  <div className="flex items-start justify-between gap-2">
                    <p className="text-sm font-medium leading-tight">{item.title}</p>
                    <Badge variant={item.trend_label === "action" ? "destructive" : "warning"}>
                      {item.trend_label === "action" ? t.dashboard.trendAction : t.dashboard.severityWatch}
                    </Badge>
                  </div>
                  <p className="mt-1 text-xs text-muted-foreground">
                    {label(item.journey)} / {label(item.journey_stage)} · {t.dashboard.score} {Math.round(item.emerging_score * 100)}%
                  </p>
                  <p className="mt-1 text-xs text-muted-foreground">
                    {t.common.signals}: {item.signal_count} · {t.common.customers}: {item.customer_count} · {t.common.sources}: {item.source_count}
                  </p>
                </div>
              ))
            )}
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-4 xl:grid-cols-[1.4fr_0.8fr]">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle className="flex items-center gap-2 text-lg"><ShieldAlert className="h-5 w-5 text-amber-500" /> {t.dashboard.needsAttention}</CardTitle>
            <Link className="text-sm text-primary hover:underline" href="/insights">{t.dashboard.openInsights}</Link>
          </CardHeader>
          <CardContent>
            {attention.length === 0 ? (
              <p className="text-sm text-muted-foreground">No leadership attention needed right now.</p>
            ) : (
              <div className="space-y-3">
                {attention.map(({ problem, reason, severity }, index) => (
                  <Link key={problem.problem_id} className="block rounded-xl border p-4 transition-colors hover:bg-muted/50" href={`/insights/${problem.problem_id}`}>
                    <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="flex h-7 w-7 items-center justify-center rounded-full bg-muted text-xs font-semibold">{index + 1}</span>
                          <h2 className="font-semibold">{problem.title}</h2>
                        </div>
                        <p className="mt-2 text-sm text-muted-foreground">{problem.journey} / {problem.journey_stage}</p>
                        <p className="mt-1 text-sm">{reason}</p>
                      </div>
                      <div className="flex flex-wrap gap-2 md:justify-end">
                        <Badge variant={severity === "blocked" ? "destructive" : severity === "review" ? "warning" : "secondary"}>{severity === "blocked" ? t.dashboard.severityBlocked : severity === "review" ? t.dashboard.severityReview : t.dashboard.severityWatch}</Badge>
                        <Badge variant="outline">{t.insights.impact} {percent(impact(problem))}</Badge>
                        <Badge variant="outline">{compact(problem.affected_customers)} {t.common.customers}</Badge>
                      </div>
                    </div>
                  </Link>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-lg"><Gauge className="h-5 w-5 text-primary" /> {t.nav.actions}</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-2 gap-3 text-sm">
              <div className="rounded-lg border p-3"><p className="text-muted-foreground">{t.dashboard.actionTypes}</p><p className="mt-1 text-2xl font-bold">{actionClassCount}</p></div>
              <div className="rounded-lg border p-3"><p className="text-muted-foreground">{t.dashboard.approved}</p><p className="mt-1 text-2xl font-bold">{approvedActions.size}</p></div>
              <div className="rounded-lg border p-3"><p className="text-muted-foreground">{t.dashboard.draftExecutions}</p><p className="mt-1 text-2xl font-bold">{executions.filter((e) => e.status === "draft_created").length}</p></div>
              <div className="rounded-lg border p-3"><p className="text-muted-foreground">{t.dashboard.interventionsReady}</p><p className="mt-1 text-2xl font-bold">{interventionReady.length}</p></div>
            </div>
            <div className="space-y-3">
              {mix.map((item) => (
                <div key={item.actionClass}>
                  <div className="mb-1 flex items-center justify-between text-sm"><span>{actionClassLabels(t.dashboard)[item.actionClass]}</span><span className="text-muted-foreground">{item.count}</span></div>
                  <div className="h-2 overflow-hidden rounded-full bg-muted"><div className="h-full rounded-full bg-primary" style={{ width: `${(item.count / maxMix) * 100}%` }} /></div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-4 xl:grid-cols-3">
        <Card>
          <CardHeader><CardTitle className="flex items-center gap-2 text-lg"><Target className="h-5 w-5 text-emerald-500" /> {t.dashboard.outcomes}</CardTitle></CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-2 gap-3 text-sm">
              <div className="rounded-lg border p-3"><p className="text-muted-foreground">{t.dashboard.targetMet}</p><p className="mt-1 text-2xl font-bold text-emerald-600">{outcomeBoard.target_met}</p></div>
              <div className="rounded-lg border p-3"><p className="text-muted-foreground">{t.dashboard.improving}</p><p className="mt-1 text-2xl font-bold text-emerald-600">{outcomeBoard.improving}</p></div>
              <div className="rounded-lg border p-3"><p className="text-muted-foreground">{t.dashboard.notImproved}</p><p className="mt-1 text-2xl font-bold text-amber-600">{outcomeBoard.not_improved}</p></div>
              <div className="rounded-lg border p-3"><p className="text-muted-foreground">{t.dashboard.notMeasured}</p><p className="mt-1 text-2xl font-bold">{outcomeBoard.not_measured}</p></div>
            </div>
            <div className="space-y-2">
              {outcomeBoard.items.slice(0, 3).map((item) => (
                <Link key={item.problem_id} className="flex items-center justify-between rounded-lg border p-3 text-sm hover:bg-muted/50" href={`/insights/${item.problem_id}`}>
                  <span className="truncate pr-3">{item.title}</span>
                  <Badge variant={item.outcome_status === "target_met" || item.outcome_status === "improving" ? "success" : "outline"}>{outcomeStatusLabel(item.outcome_status, t)}</Badge>
                </Link>
              ))}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader><CardTitle className="flex items-center gap-2 text-lg"><Users className="h-5 w-5 text-primary" /> {t.dashboard.workload}</CardTitle></CardHeader>
          <CardContent className="space-y-3">
            <WorksCouncilBanner />
            {loads.length === 0 ? (
              <p className="text-sm text-muted-foreground">No active owner load.</p>
            ) : (
              loads.map((load) => (
                <div key={load.owner} className="rounded-lg border p-3">
                  <div className="flex items-start justify-between gap-3">
                    <div><p className="font-medium">{label(load.owner)}</p><p className="mt-1 text-xs text-muted-foreground">{t.dashboard.topIssue}: {load.topProblem.title}</p></div>
                    <Badge variant={load.blocked > 0 ? "destructive" : "secondary"}>{t.dashboard.issues}: {load.problems}</Badge>
                  </div>
                  <p className="mt-2 text-xs text-muted-foreground">{compact(load.affectedCustomers)} affected customers / {load.blocked} blocked</p>
                </div>
              ))
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader><CardTitle className="flex items-center gap-2 text-lg"><Sparkles className="h-5 w-5 text-amber-500" /> {t.dashboard.readiness}</CardTitle></CardHeader>
          <CardContent className="space-y-3 text-sm">
            <div className="flex items-center justify-between rounded-lg border p-3"><span className="flex items-center gap-2"><ClipboardCheck className="h-4 w-4" /> Interventions</span><Badge variant={interventionReady.length > 0 ? "success" : "secondary"}>{interventionReady.length}</Badge></div>
            <div className="flex items-center justify-between rounded-lg border p-3"><span className="flex items-center gap-2"><TrendingUp className="h-4 w-4" /> {t.dashboard.learningRecords}</span><Badge variant="outline">{outcomeBoard.learning_worked + outcomeBoard.learning_partially_worked + outcomeBoard.learning_did_not_work}</Badge></div>
            <div className="flex items-center justify-between rounded-lg border p-3"><span className="flex items-center gap-2"><Plug className="h-4 w-4" /> {t.dashboard.activeConnectors}</span><Badge variant={activeConnectors > 0 ? "success" : "secondary"}>{activeConnectors}</Badge></div>
            <div className="flex items-center justify-between rounded-lg border p-3"><span className="flex items-center gap-2"><CheckCircle className="h-4 w-4" /> {t.dashboard.humanApprovals}</span><Badge variant={approvals.length > 0 ? "success" : "outline"}>{approvals.length}</Badge></div>
            <Link className="inline-flex items-center gap-2 text-primary hover:underline" href="/actions">{t.dashboard.reviewPortfolio} <ArrowRight className="h-3 w-3" /></Link>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
