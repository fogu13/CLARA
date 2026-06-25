"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { ActionDecisionPanel } from "@/app/components/action-decision-panel";
import { getExecutions, getProblem, getProblems } from "@/lib/client-api";
import { fallbackProblems } from "@/lib/sample-data";
import type { ActionProposal, ExecutionRecord, ProblemRecord } from "@/lib/types";
import { CheckCircle, XCircle, Clock, ArrowRight } from "lucide-react";

type ActionQueueItem = {
  problem: ProblemRecord;
  action: ActionProposal;
};

function label(value: string): string {
  return value.replaceAll("_", " ");
}

export default function ActionsPage() {
  const [items, setItems] = useState<ActionQueueItem[]>([]);
  const [executions, setExecutions] = useState<ExecutionRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [usingFallback, setUsingFallback] = useState(false);

  useEffect(() => {
    async function load() {
      try {
        const [summaries, executionRecords] = await Promise.all([getProblems(), getExecutions()]);
        const problems = await Promise.all(summaries.map((problem) => getProblem(problem.problem_id)));
        setItems(
          problems.flatMap((problem) =>
            problem.action_proposals.map((action) => ({ problem, action }))
          )
        );
        setExecutions(executionRecords);
      } catch {
        setItems(
          fallbackProblems.flatMap((problem) =>
            problem.action_proposals.map((action) => ({ problem, action }))
          )
        );
        setExecutions([]);
        setUsingFallback(true);
      } finally {
        setLoading(false);
      }
    }

    void load();
  }, []);

  if (loading) return <div className="text-muted-foreground">Loading actions...</div>;

  const blockedActions = items.filter((item) =>
    item.problem.governance_checks.some((check) => check.blocking && check.status !== "pass")
  ).length;
  const destinations = new Set(items.map((item) => item.action.destination).filter(Boolean));

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Actions</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Review proposed actions, record decisions and inspect execution history.
        </p>
      </div>

      {usingFallback ? (
        <div className="rounded-md border border-dashed border-yellow-500/50 bg-yellow-500/5 p-3 text-sm text-yellow-700 dark:text-yellow-400">
          API unreachable — showing sample action proposals.
        </div>
      ) : null}

      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardHeader className="pb-2"><CardTitle className="text-sm text-muted-foreground">Action Proposals</CardTitle></CardHeader>
          <CardContent><div className="text-2xl font-bold">{items.length}</div></CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2"><CardTitle className="text-sm text-muted-foreground">Policy Blocked</CardTitle></CardHeader>
          <CardContent><div className="text-2xl font-bold">{blockedActions}</div></CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2"><CardTitle className="text-sm text-muted-foreground">Destinations</CardTitle></CardHeader>
          <CardContent><div className="text-2xl font-bold">{destinations.size}</div></CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Action Proposals</CardTitle>
        </CardHeader>
        <CardContent>
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
        <CardHeader><CardTitle>Execution History</CardTitle></CardHeader>
        <CardContent>
          {executions.length === 0 ? (
            <p className="text-sm text-muted-foreground">No executions yet.</p>
          ) : (
            <div className="space-y-3">
              {executions.slice(0, 20).map((execution) => (
                <div key={execution.execution_id} className="flex items-center justify-between border-b pb-3">
                  <div className="flex items-center gap-3">
                    {execution.status === "completed" ? (
                      <CheckCircle className="h-4 w-4 text-emerald-500" />
                    ) : execution.status === "blocked" ? (
                      <XCircle className="h-4 w-4 text-destructive" />
                    ) : (
                      <Clock className="h-4 w-4 text-muted-foreground" />
                    )}
                    <div>
                      <p className="text-sm font-medium">{execution.problem_id}</p>
                      <p className="text-xs text-muted-foreground">Destination: {execution.destination}</p>
                    </div>
                  </div>
                  <Badge variant={execution.status === "completed" ? "success" : execution.status === "blocked" ? "destructive" : "secondary"}>
                    {label(execution.status)}
                  </Badge>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader><CardTitle>Connector Pipeline</CardTitle></CardHeader>
        <CardContent>
          <div className="flex items-center gap-2 text-sm flex-wrap">
            <Badge variant="secondary">Zendesk in</Badge>
            <ArrowRight className="h-3 w-3 text-muted-foreground" />
            <Badge variant="secondary">Triage</Badge>
            <ArrowRight className="h-3 w-3 text-muted-foreground" />
            <Badge variant="secondary">Governance</Badge>
            <ArrowRight className="h-3 w-3 text-muted-foreground" />
            <Badge variant="secondary">Human approval</Badge>
            <ArrowRight className="h-3 w-3 text-muted-foreground" />
            <Badge variant="success">Jira / Slack drafts</Badge>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
