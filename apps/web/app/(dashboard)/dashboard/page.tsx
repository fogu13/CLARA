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
import { apiBaseUrl, apiHeaders, getApprovals, getExecutions, getOutcomeBoard, getProblems } from "@/lib/client-api";
import { fallbackProblems } from "@/lib/sample-data";
import type { ActionClass, ApprovalRecord, ExecutionRecord, OutcomeBoard, OutcomeBoardItem, ProblemSummary } from "@/lib/types";
import { percent } from "@/lib/format";

type ConnectorSummary = { connector_type: string; is_active: boolean };

type DashboardData = {
  problems: ProblemSummary[];
  outcomeBoard: OutcomeBoard;
  approvals: ApprovalRecord[];
  executions: ExecutionRecord[];
  connectors: ConnectorSummary[];
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

const actionClassLabels: Record<ActionClass, string> = {
  structural: "Product fix",
  customer_recovery: "Customer recovery",
  journey_intervention: "Intervention",
  research: "Research",
  governance: "Governance"
};

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

function leadershipHeadline(problems: ProblemSummary[], outcomeBoard: OutcomeBoard): string {
  const top = [...problems].sort((a, b) => impact(b) - impact(a))[0];
  if (!top) return "No open problems right now.";

  const blocked = problems.filter((problem) => blockingChecks(problem) > 0).length;
  const improving = outcomeBoard.improving + outcomeBoard.target_met;
  if (blocked > 0) return `${blocked} ${blocked === 1 ? "problem needs" : "problems need"} a decision before work can start.`;
  if (improving > 0) return `${improving} ${improving === 1 ? "outcome is" : "outcomes are"} improving or on target.`;
  return `${top.title} is the highest-impact problem right now.`;
}

function attentionItems(problems: ProblemSummary[]): AttentionItem[] {
  return [...problems]
    .filter((problem) => !isResolved(problem))
    .map((problem) => {
      const blocked = blockingChecks(problem);
      if (blocked > 0) return { problem, reason: "Blocking governance gate", severity: "blocked" as const };
      if (needsReview(problem)) return { problem, reason: "Approval or owner review needed", severity: "review" as const };
      return { problem, reason: `${compact(problem.affected_customers)} customers represented`, severity: "watch" as const };
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

async function getConnectors(): Promise<ConnectorSummary[]> {
  const response = await fetch(`${apiBaseUrl()}/connectors`, { headers: apiHeaders() });
  if (!response.ok) return [];
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
  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      try {
        const [problems, outcomeBoard] = await Promise.all([getProblems(), getOutcomeBoard()]);
        const partialSources: string[] = [];
        const [approvals, executions, connectors] = await Promise.all([
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
          })
        ]);
        setData({ problems, outcomeBoard, approvals, executions, connectors, usingFallback: false, partialSources });
      } catch {
        setData({
          problems: fallbackSummaries(),
          outcomeBoard: fallbackOutcomeBoard(),
          approvals: [],
          executions: [],
          connectors: [],
          usingFallback: true,
          partialSources: []
        });
      } finally {
        setLoading(false);
      }
    }

    void load();
  }, []);

  if (loading) return <div className="text-muted-foreground">Loading leadership dashboard...</div>;

  const problems = data?.problems ?? [];
  const outcomeBoard = data?.outcomeBoard ?? fallbackOutcomeBoard();
  const approvals = data?.approvals ?? [];
  const executions = data?.executions ?? [];
  const connectors = data?.connectors ?? [];
  const actionClassCount = problems.reduce((total, problem) => total + problem.top_action_classes.length, 0);
  const approvedActions = approvedActionIds(approvals);
  const blockedProblems = problems.filter((problem) => blockingChecks(problem) > 0);
  const highImpactProblems = problems.filter((problem) => impact(problem) >= 0.7 || problem.impact_band === "high");
  const representedCustomers = problems.reduce((total, problem) => total + problem.affected_customers, 0);
  const interventionReady = problems.filter((problem) => problem.top_action_classes.includes("journey_intervention"));
  const measuredOutcomes = outcomeBoard.total - outcomeBoard.not_measured;
  const improvingOutcomes = outcomeBoard.improving + outcomeBoard.target_met;
  const activeConnectors = connectors.filter((connector) => connector.is_active).length;
  const pendingDecisionProblems = problems.filter((problem) => !isResolved(problem) && needsReview(problem));
  const attention = attentionItems(problems);
  const loads = ownerLoads(problems);
  const mix = actionMix(problems);
  const maxMix = Math.max(...mix.map((item) => item.count), 1);
  const measuredRate = outcomeBoard.total > 0 ? measuredOutcomes / outcomeBoard.total : 0;

  return (
    <div className="space-y-6">
      <div className="rounded-2xl border bg-card p-8 shadow-sm">
        <div className="flex flex-col gap-6 lg:flex-row lg:items-end lg:justify-between">
          <div className="max-w-3xl">
            <p className="text-xs font-semibold uppercase tracking-[0.2em] text-primary">Overview</p>
            <h1 className="mt-3 text-3xl font-bold tracking-tight text-foreground">
              {leadershipHeadline(problems, outcomeBoard)}
            </h1>
            <p className="mt-3 text-sm text-muted-foreground">
              The highest-impact customer problems, the actions proposed for them, and whether those actions worked.
            </p>
          </div>
          <div className="flex shrink-0 gap-8">
            <div>
              <p className="text-xs uppercase tracking-wide text-muted-foreground">Customers affected</p>
              <p className="mt-1 text-3xl font-semibold tabular-nums">{compact(representedCustomers)}</p>
            </div>
            <div className="border-l pl-8">
              <p className="text-xs uppercase tracking-wide text-muted-foreground">Outcomes measured</p>
              <p className="mt-1 text-3xl font-semibold tabular-nums">{percent(measuredRate)}</p>
            </div>
          </div>
        </div>
      </div>

      {data?.usingFallback ? (
        <div className="rounded-md border border-dashed border-yellow-500/50 bg-yellow-500/5 p-3 text-sm text-yellow-700 dark:text-yellow-400">
          Showing sample data — couldn&apos;t reach the API.
        </div>
      ) : null}

      {!data?.usingFallback && data?.partialSources.length ? (
        <div className="rounded-md border border-dashed border-amber-500/50 bg-amber-500/5 p-3 text-sm text-amber-700 dark:text-amber-400">
          Some data is unavailable ({data.partialSources.join(", ")}); a few counts may be low.
        </div>
      ) : null}

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-5">
        <MetricCard title="High-Impact Problems" value={highImpactProblems.length} detail={`${problems.length} total problems in queue`} tone={highImpactProblems.length > 0 ? "warn" : "good"} />
        <MetricCard title="Governance Blockers" value={blockedProblems.length} detail="Require policy or privacy decision" tone={blockedProblems.length > 0 ? "bad" : "good"} />
        <MetricCard title="Pending Decisions" value={pendingDecisionProblems.length} detail={`${approvals.length} approval decisions recorded`} tone={pendingDecisionProblems.length > 0 ? "warn" : "good"} />
        <MetricCard title="Outcomes improving" value={`${improvingOutcomes}/${outcomeBoard.total}`} detail={`${measuredOutcomes} measured, ${outcomeBoard.not_measured} pending`} tone={improvingOutcomes > 0 ? "good" : "neutral"} />
        <MetricCard title="Connectors" value={`${activeConnectors}/${connectors.length}`} detail="Active integrations" tone={activeConnectors > 0 ? "good" : "neutral"} />
      </div>

      <div className="grid gap-4 xl:grid-cols-[1.4fr_0.8fr]">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle className="flex items-center gap-2 text-lg"><ShieldAlert className="h-5 w-5 text-amber-500" /> Needs attention</CardTitle>
            <Link className="text-sm text-primary hover:underline" href="/insights">Open insights</Link>
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
                        <Badge variant={severity === "blocked" ? "destructive" : severity === "review" ? "warning" : "secondary"}>{severity}</Badge>
                        <Badge variant="outline">impact {percent(impact(problem))}</Badge>
                        <Badge variant="outline">{compact(problem.affected_customers)} customers</Badge>
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
            <CardTitle className="flex items-center gap-2 text-lg"><Gauge className="h-5 w-5 text-primary" /> Actions</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-2 gap-3 text-sm">
              <div className="rounded-lg border p-3"><p className="text-muted-foreground">Action types</p><p className="mt-1 text-2xl font-bold">{actionClassCount}</p></div>
              <div className="rounded-lg border p-3"><p className="text-muted-foreground">Approved</p><p className="mt-1 text-2xl font-bold">{approvedActions.size}</p></div>
              <div className="rounded-lg border p-3"><p className="text-muted-foreground">Draft executions</p><p className="mt-1 text-2xl font-bold">{executions.length}</p></div>
              <div className="rounded-lg border p-3"><p className="text-muted-foreground">Interventions ready</p><p className="mt-1 text-2xl font-bold">{interventionReady.length}</p></div>
            </div>
            <div className="space-y-3">
              {mix.map((item) => (
                <div key={item.actionClass}>
                  <div className="mb-1 flex items-center justify-between text-sm"><span>{actionClassLabels[item.actionClass]}</span><span className="text-muted-foreground">{item.count}</span></div>
                  <div className="h-2 overflow-hidden rounded-full bg-muted"><div className="h-full rounded-full bg-primary" style={{ width: `${(item.count / maxMix) * 100}%` }} /></div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-4 xl:grid-cols-3">
        <Card>
          <CardHeader><CardTitle className="flex items-center gap-2 text-lg"><Target className="h-5 w-5 text-emerald-500" /> Outcomes</CardTitle></CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-2 gap-3 text-sm">
              <div className="rounded-lg border p-3"><p className="text-muted-foreground">Target met</p><p className="mt-1 text-2xl font-bold text-emerald-600">{outcomeBoard.target_met}</p></div>
              <div className="rounded-lg border p-3"><p className="text-muted-foreground">Improving</p><p className="mt-1 text-2xl font-bold text-emerald-600">{outcomeBoard.improving}</p></div>
              <div className="rounded-lg border p-3"><p className="text-muted-foreground">Not improved</p><p className="mt-1 text-2xl font-bold text-amber-600">{outcomeBoard.not_improved}</p></div>
              <div className="rounded-lg border p-3"><p className="text-muted-foreground">Not measured</p><p className="mt-1 text-2xl font-bold">{outcomeBoard.not_measured}</p></div>
            </div>
            <div className="space-y-2">
              {outcomeBoard.items.slice(0, 3).map((item) => (
                <Link key={item.problem_id} className="flex items-center justify-between rounded-lg border p-3 text-sm hover:bg-muted/50" href={`/insights/${item.problem_id}`}>
                  <span className="truncate pr-3">{item.title}</span>
                  <Badge variant={item.outcome_status === "target_met" || item.outcome_status === "improving" ? "success" : "outline"}>{label(item.outcome_status)}</Badge>
                </Link>
              ))}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader><CardTitle className="flex items-center gap-2 text-lg"><Users className="h-5 w-5 text-primary" /> Workload by owner</CardTitle></CardHeader>
          <CardContent className="space-y-3">
            {loads.length === 0 ? (
              <p className="text-sm text-muted-foreground">No active owner load.</p>
            ) : (
              loads.map((load) => (
                <div key={load.owner} className="rounded-lg border p-3">
                  <div className="flex items-start justify-between gap-3">
                    <div><p className="font-medium">{label(load.owner)}</p><p className="mt-1 text-xs text-muted-foreground">Top issue: {load.topProblem.title}</p></div>
                    <Badge variant={load.blocked > 0 ? "destructive" : "secondary"}>{load.problems} issues</Badge>
                  </div>
                  <p className="mt-2 text-xs text-muted-foreground">{compact(load.affectedCustomers)} affected customers / {load.blocked} blocked</p>
                </div>
              ))
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader><CardTitle className="flex items-center gap-2 text-lg"><Sparkles className="h-5 w-5 text-amber-500" /> Readiness</CardTitle></CardHeader>
          <CardContent className="space-y-3 text-sm">
            <div className="flex items-center justify-between rounded-lg border p-3"><span className="flex items-center gap-2"><ClipboardCheck className="h-4 w-4" /> Interventions</span><Badge variant={interventionReady.length > 0 ? "success" : "secondary"}>{interventionReady.length}</Badge></div>
            <div className="flex items-center justify-between rounded-lg border p-3"><span className="flex items-center gap-2"><TrendingUp className="h-4 w-4" /> Learning records</span><Badge variant="outline">{outcomeBoard.learning_worked + outcomeBoard.learning_partially_worked + outcomeBoard.learning_did_not_work}</Badge></div>
            <div className="flex items-center justify-between rounded-lg border p-3"><span className="flex items-center gap-2"><Plug className="h-4 w-4" /> Active connectors</span><Badge variant={activeConnectors > 0 ? "success" : "secondary"}>{activeConnectors}</Badge></div>
            <div className="flex items-center justify-between rounded-lg border p-3"><span className="flex items-center gap-2"><CheckCircle className="h-4 w-4" /> Human approvals</span><Badge variant={approvals.length > 0 ? "success" : "outline"}>{approvals.length}</Badge></div>
            <Link className="inline-flex items-center gap-2 text-primary hover:underline" href="/actions">Review action portfolio <ArrowRight className="h-3 w-3" /></Link>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
