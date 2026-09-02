"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { useI18n } from "@/lib/i18n";
import { Badge } from "@/components/ui/badge";
import { ActionDecisionPanel } from "@/app/components/action-decision-panel";
import { WorksCouncilBanner } from "@/app/components/works-council-banner";
import { getExecutions, getProblem, getProblems, wrongOriginHint } from "@/lib/client-api";
import type { ActionProposal, ExecutionRecord, ProblemRecord } from "@/lib/types";
import { CheckCircle, XCircle, Clock, ArrowRight, AlertCircle } from "lucide-react";

type ActionQueueItem = {
  problem: ProblemRecord;
  action: ActionProposal;
};

function label(value: string): string {
  return value.replaceAll("_", " ");
}

function readinessBadge(status: string): "success" | "warning" | "destructive" | "outline" {
  if (status === "ready_for_review") return "success";
  if (status === "blocked_by_policy") return "destructive";
  if (status === "needs_consent_review") return "warning";
  return "outline";
}

export default function ActionsPage() {
  const { t } = useI18n();
  const searchParams = useSearchParams();
  // Per-team queue ("every team sees what it can act on"): /actions?owner=<team>.
  const owner = searchParams.get("owner") ?? "";
  const [overdueOnly, setOverdueOnly] = useState(searchParams.get("overdue") === "true");
  const [items, setItems] = useState<ActionQueueItem[]>([]);
  const [executions, setExecutions] = useState<ExecutionRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [reloadKey, setReloadKey] = useState(0);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      setLoading(true);
      try {
        const [summaries, executionRecords] = await Promise.all([
          getProblems({ owner: owner || undefined, overdue: overdueOnly ? true : undefined }),
          getExecutions()
        ]);
        const problems = await Promise.all(summaries.map((problem) => getProblem(problem.problem_id)));
        if (cancelled) return;
        setItems(
          problems.flatMap((problem) =>
            problem.action_proposals.map((action) => ({ problem, action }))
          )
        );
        setExecutions(executionRecords);
        setLoadError(null);
      } catch (error) {
        if (cancelled) return;
        // Never substitute sample data here: fake proposals next to live
        // Approve buttons is exactly the trust hazard the dashboard avoids.
        const message = error instanceof Error ? error.message : "";
        setLoadError(
          message.startsWith("Failed to fetch") || message.includes("NetworkError") || !message
            ? `${t.dashboard.apiUnreachable}${wrongOriginHint()}`
            : message
        );
        setItems([]);
        setExecutions([]);
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    void load();
    return () => {
      cancelled = true;
    };
  }, [owner, overdueOnly, reloadKey, t.dashboard.apiUnreachable]);

  if (loading) return <div className="text-muted-foreground">Loading actions...</div>;

  if (loadError) {
    return (
      <Card className="mx-auto max-w-xl">
        <CardContent className="flex flex-col items-center gap-4 py-12 text-center">
          <AlertCircle className="h-8 w-8 text-destructive" aria-hidden="true" />
          <div>
            <h1 className="text-lg font-semibold">{t.actionsPage.loadFailed}</h1>
            <p className="mt-2 text-sm text-muted-foreground">{loadError}</p>
          </div>
          <Button size="sm" onClick={() => setReloadKey((key) => key + 1)}>
            {t.common.retry}
          </Button>
        </CardContent>
      </Card>
    );
  }

  const blockedActions = items.filter((item) =>
    item.problem.governance_checks.some((check) => check.blocking && check.status !== "pass")
  ).length;
  const destinations = new Set(items.map((item) => item.action.destination).filter(Boolean));
  const problemTitleById = new Map(items.map(({ problem }) => [problem.problem_id, problem.title]));
  const interventionItems = items.filter((item) => item.action.intervention_brief?.audience_readiness);
  const readyInterventions = interventionItems.filter(
    (item) => item.action.intervention_brief?.audience_readiness?.readiness_status === "ready_for_review"
  ).length;
  const consentReviewInterventions = interventionItems.filter(
    (item) => item.action.intervention_brief?.audience_readiness?.readiness_status === "needs_consent_review"
  ).length;
  const blockedInterventions = interventionItems.filter(
    (item) => item.action.intervention_brief?.audience_readiness?.readiness_status === "blocked_by_policy"
  ).length;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">{t.actionsPage.title}</h1>
        <p className="text-sm text-muted-foreground mt-1">
          {t.actionsPage.subtitle}
        </p>
      </div>

      <div className="flex flex-wrap items-center gap-3 text-sm text-muted-foreground">
        <span>
          {t.actionsPage.teamFilterNote}{" "}
          <strong className="text-foreground">{owner ? label(owner) : t.actionsPage.allTeams}</strong>
          {owner ? (
            <>
              {" · "}
              <Link href="/actions" className="text-primary hover:underline">
                {t.actionsPage.allTeams}
              </Link>
            </>
          ) : null}
        </span>
        <label className="inline-flex items-center gap-2">
          <input
            type="checkbox"
            checked={overdueOnly}
            onChange={(event) => setOverdueOnly(event.target.checked)}
          />
          {t.actionsPage.overdueOnly}
        </label>
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardHeader className="pb-2"><CardTitle className="text-sm text-muted-foreground">Action Proposals</CardTitle></CardHeader>
          <CardContent><div className="text-2xl font-bold">{items.length}</div></CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2"><CardTitle className="text-sm text-muted-foreground">Held by policy checks</CardTitle></CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{blockedActions}</div>
            <p className="mt-1 text-xs text-muted-foreground">Awaiting evidence or approval — nothing ships outside policy.</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2"><CardTitle className="text-sm text-muted-foreground">Destinations</CardTitle></CardHeader>
          <CardContent><div className="text-2xl font-bold">{destinations.size}</div></CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>{t.actionsPage.audienceReadiness}</CardTitle>
        </CardHeader>
        <CardContent>
          {interventionItems.length === 0 ? (
            <p className="text-sm text-muted-foreground">No audience-ready intervention drafts yet.</p>
          ) : (
            <div className="space-y-4">
              <div className="grid gap-3 md:grid-cols-4">
                <div className="rounded-lg border p-3">
                  <p className="text-xs text-muted-foreground">Drafts</p>
                  <p className="mt-1 text-2xl font-bold">{interventionItems.length}</p>
                </div>
                <div className="rounded-lg border p-3">
                  <p className="text-xs text-muted-foreground">Ready for review</p>
                  <p className="mt-1 text-2xl font-bold text-emerald-600">{readyInterventions}</p>
                </div>
                <div className="rounded-lg border p-3">
                  <p className="text-xs text-muted-foreground">Consent review</p>
                  <p className="mt-1 text-2xl font-bold text-amber-600">{consentReviewInterventions}</p>
                </div>
                <div className="rounded-lg border p-3">
                  <p className="text-xs text-muted-foreground">Blocked</p>
                  <p className="mt-1 text-2xl font-bold text-destructive">{blockedInterventions}</p>
                </div>
              </div>
              <div className="grid gap-3 lg:grid-cols-2">
                {interventionItems.map(({ problem, action }) => {
                  const readiness = action.intervention_brief?.audience_readiness;
                  if (!readiness) return null;

                  return (
                    <Link
                      key={`${problem.problem_id}-${action.action_id}-readiness`}
                      href={`/insights/${problem.problem_id}`}
                      className="rounded-lg border p-4 transition-colors hover:bg-muted/50"
                    >
                      <div className="flex flex-col gap-2 md:flex-row md:items-start md:justify-between">
                        <div>
                          <p className="text-sm font-semibold">{problem.title}</p>
                          <p className="mt-1 text-xs text-muted-foreground">
                            {readiness.export_destination} / {readiness.export_format}
                          </p>
                        </div>
                        <Badge variant={readinessBadge(readiness.readiness_status)}>
                          {label(readiness.readiness_status)}
                        </Badge>
                      </div>
                      <div className="mt-3 grid grid-cols-4 gap-2 text-xs">
                        <div><p className="text-muted-foreground">Est.</p><p className="font-semibold">{readiness.estimated_audience_size}</p></div>
                        <div><p className="text-muted-foreground">Eligible</p><p className="font-semibold">{readiness.eligible_customers}</p></div>
                        <div><p className="text-muted-foreground">Excluded</p><p className="font-semibold">{readiness.excluded_customers}</p></div>
                        <div><p className="text-muted-foreground">Risk</p><p className="font-semibold">{readiness.over_contact_risk}</p></div>
                      </div>
                    </Link>
                  );
                })}
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>{t.actionsPage.actionProposals}</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <WorksCouncilBanner />
          {items.length === 0 ? (
            <div className="text-center py-8">
              <CheckCircle className="h-8 w-8 text-muted-foreground mx-auto mb-3" />
              <p className="text-sm text-muted-foreground">No action proposals yet.</p>
            </div>
          ) : (
            <div className="space-y-4">
              {items.map(({ problem, action }) => (
                <div key={`${problem.problem_id}-${action.action_id}`} className="rounded-lg border p-4">
                  <div className="flex flex-col gap-2 md:flex-row md:items-start md:justify-between">
                    <div>
                      <Link href={`/insights/${problem.problem_id}`} className="text-sm font-semibold hover:underline">
                        {problem.title}
                      </Link>
                      <p className="mt-1 text-sm text-muted-foreground">{action.proposal}</p>
                    </div>
                    <div className="flex flex-wrap gap-2">
                      <Badge variant="secondary">{label(action.class)}</Badge>
                      <Badge variant="outline">{action.destination}</Badge>
                      <Badge variant={action.risk_level === "critical" ? "destructive" : "secondary"}>
                        {action.risk_level}
                      </Badge>
                      <Badge variant="outline">{label(action.owner)}</Badge>
                      {problem.due_at ? (
                        (() => {
                          const due = new Date(problem.due_at);
                          const overdue = problem.status !== "resolved" && due.getTime() < Date.now();
                          return (
                            <Badge variant={overdue ? "destructive" : "outline"} title={problem.due_at}>
                              {overdue ? t.dashboard.overdueChip : `${t.dashboard.dueLabel} ${due.toLocaleDateString()}`}
                            </Badge>
                          );
                        })()
                      ) : null}
                    </div>
                  </div>
                  <ActionDecisionPanel problemId={problem.problem_id} action={action} />
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader><CardTitle>{t.actionsPage.executionHistory}</CardTitle></CardHeader>
        <CardContent>
          {executions.length === 0 ? (
            <p className="text-sm text-muted-foreground">No executions yet.</p>
          ) : (
            <div className="space-y-3">
              {executions.slice(0, 20).map((execution) => (
                <div key={execution.execution_id} className="flex items-center justify-between border-b pb-3">
                  <div className="flex items-center gap-3">
                    {execution.status === "completed" || execution.status === "pushed" ? (
                      <CheckCircle className="h-4 w-4 text-emerald-500" />
                    ) : execution.status === "blocked" || execution.status === "push_failed" ? (
                      <XCircle className="h-4 w-4 text-destructive" />
                    ) : (
                      <Clock className="h-4 w-4 text-muted-foreground" />
                    )}
                    <div>
                      <a href={`/insights/${execution.problem_id}`} className="text-sm font-medium hover:underline">
                        {problemTitleById.get(execution.problem_id) ?? execution.problem_id}
                      </a>
                      <p className="text-[11px] text-muted-foreground">{execution.problem_id}</p>
                      <p className="text-xs text-muted-foreground">
                        Destination: {execution.destination}
                        {execution.external_ref ? ` · ${t.actionsPage.externalRef}: ${execution.external_ref}` : ""}
                      </p>
                      {execution.status === "push_failed" && execution.detail ? (
                        <p className="text-xs text-destructive">{execution.detail}</p>
                      ) : null}
                    </div>
                  </div>
                  <Badge
                    variant={
                      execution.status === "completed" || execution.status === "pushed"
                        ? "success"
                        : execution.status === "blocked" || execution.status === "push_failed"
                          ? "destructive"
                          : "secondary"
                    }
                  >
                    {label(execution.status)}
                  </Badge>
                </div>
              ))}
              {executions.length > 20 ? (
                <p className="pt-2 text-xs text-muted-foreground">{t.common.showingOf.replace("{n}", "20").replace("{total}", String(executions.length))}</p>
              ) : null}
            </div>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader><CardTitle>{t.actionsPage.connectorPipeline}</CardTitle></CardHeader>
        <CardContent>
          <div className="flex items-center gap-2 text-sm flex-wrap">
            <Badge variant="secondary">Zendesk in</Badge>
            <ArrowRight className="h-3 w-3 text-muted-foreground" />
            <Badge variant="secondary">{t.actionsPage.triage}</Badge>
            <ArrowRight className="h-3 w-3 text-muted-foreground" />
            <Badge variant="secondary">{t.actionsPage.governance}</Badge>
            <ArrowRight className="h-3 w-3 text-muted-foreground" />
            <Badge variant="secondary">{t.actionsPage.humanApproval}</Badge>
            <ArrowRight className="h-3 w-3 text-muted-foreground" />
            <Badge variant="success">Jira / Slack drafts</Badge>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
