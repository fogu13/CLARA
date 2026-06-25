"use client";

import { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { MessageSquare, Lightbulb, CheckCircle, TrendingUp, Plug, AlertCircle } from "lucide-react";
import { apiBaseUrl } from "@/lib/client-api";
import { fallbackProblems } from "@/lib/sample-data";
import type { ProblemSummary } from "@/lib/types";

type ConnectorSummary = { connector_type: string; is_active: boolean };

interface DashboardData {
  problems: ProblemSummary[];
  connectors: ConnectorSummary[];
  usingFallback: boolean;
}

export default function DashboardPage() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      const baseUrl = apiBaseUrl();
      try {
        const [problemsRes, connectorsRes] = await Promise.all([
          fetch(`${baseUrl}/problems`).then(r => r.ok ? r.json() : []),
          fetch(`${baseUrl}/connectors`).then(r => r.ok ? r.json() : []),
        ]);
        setData({
          problems: problemsRes || [],
          connectors: connectorsRes || [],
          usingFallback: false
        });
      } catch {
        setData({
          problems: fallbackProblems.map((problem) => ({
            problem_id: problem.problem_id,
            title: problem.title,
            journey: problem.journey,
            journey_stage: problem.journey_stage,
            owner: problem.owner,
            status: problem.status,
            impact_score: problem.impact_score ?? 0,
            impact_band: problem.impact_band ?? "unknown",
            evidence_confidence: problem.evidence_confidence,
            affected_customers: problem.affected_cohort.customers,
            affected_accounts: problem.affected_cohort.accounts,
            approval_pressure: problem.approval_pressure ?? "ready",
            top_action_classes: problem.action_proposals.map((action) => action.class)
          })),
          connectors: [],
          usingFallback: true
        });
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  if (loading) return <div className="text-muted-foreground">Loading dashboard...</div>;

  const problems = data?.problems || [];
  const connectors = data?.connectors || [];
  const openProblems = problems.filter((p: any) => p.status === "approval_needed" || p.status === "open").length;
  const blockedProblems = problems.filter((p: any) => p.status === "blocked_by_policy").length;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-foreground">Dashboard</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Feedback-to-Action Platform — governed AI triage with real connectors
        </p>
      </div>

      {data?.usingFallback ? (
        <div className="rounded-md border border-dashed border-yellow-500/50 bg-yellow-500/5 p-3 text-sm text-yellow-700 dark:text-yellow-400">
          API unreachable at {apiBaseUrl()} — showing sample data.
        </div>
      ) : null}

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Open Problems</CardTitle>
            <MessageSquare className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{openProblems}</div>
            <p className="text-xs text-muted-foreground mt-1">
              {problems.length} total in queue
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Policy Blocked</CardTitle>
            <AlertCircle className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{blockedProblems}</div>
            <p className="text-xs text-muted-foreground mt-1">
              Governance gate active
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Connectors</CardTitle>
            <Plug className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{connectors.length}</div>
            <p className="text-xs text-muted-foreground mt-1">
              {connectors.filter((c: any) => c.is_active).length} active
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Resolution Rate</CardTitle>
            <TrendingUp className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {problems.length > 0
                ? Math.round((problems.filter((p: any) => p.status === "resolved").length / problems.length) * 100)
                : 0}%
            </div>
            <p className="text-xs text-muted-foreground mt-1">
              Problems resolved
            </p>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Recent Problems</CardTitle>
          </CardHeader>
          <CardContent>
            {problems.length === 0 ? (
              <p className="text-sm text-muted-foreground">No problems in the queue yet.</p>
            ) : (
              <div className="space-y-3">
                {problems.slice(0, 5).map((p: any) => (
                  <div key={p.problem_id} className="flex items-center justify-between">
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium truncate">{p.title}</p>
                      <p className="text-xs text-muted-foreground">{p.journey} / {p.journey_stage}</p>
                    </div>
                    <Badge variant={p.status === "resolved" ? "success" : p.status === "blocked_by_policy" ? "destructive" : "secondary"}>
                      {p.status?.replace(/_/g, " ")}
                    </Badge>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Connector Status</CardTitle>
          </CardHeader>
          <CardContent>
            {connectors.length === 0 ? (
              <div className="space-y-2">
                <p className="text-sm text-muted-foreground">No connectors configured.</p>
                <Button variant="outline" size="sm" onClick={() => window.location.href = "/integrations"}>
                  Configure Connectors
                </Button>
              </div>
            ) : (
              <div className="space-y-3">
                {connectors.map((c: any) => (
                  <div key={c.connector_type} className="flex items-center justify-between">
                    <span className="text-sm font-medium capitalize">{c.connector_type}</span>
                    <Badge variant={c.is_active ? "success" : "secondary"}>
                      {c.is_active ? "Active" : "Inactive"}
                    </Badge>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Platform Architecture</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid gap-3 text-sm md:grid-cols-2 lg:grid-cols-4">
            <div className="flex items-center gap-2">
              <CheckCircle className="h-4 w-4 text-emerald-500" />
              <span>LangGraph triage engine</span>
            </div>
            <div className="flex items-center gap-2">
              <CheckCircle className="h-4 w-4 text-emerald-500" />
              <span>Provider-agnostic AI (Ollama/vLLM)</span>
            </div>
            <div className="flex items-center gap-2">
              <CheckCircle className="h-4 w-4 text-emerald-500" />
              <span>Zendesk / Jira / Slack connectors</span>
            </div>
            <div className="flex items-center gap-2">
              <CheckCircle className="h-4 w-4 text-emerald-500" />
              <span>Human-in-the-loop approval</span>
            </div>
            <div className="flex items-center gap-2">
              <CheckCircle className="h-4 w-4 text-emerald-500" />
              <span>Outcome measurement + resolution score</span>
            </div>
            <div className="flex items-center gap-2">
              <CheckCircle className="h-4 w-4 text-emerald-500" />
              <span>Confidence-decay learnings</span>
            </div>
            <div className="flex items-center gap-2">
              <CheckCircle className="h-4 w-4 text-emerald-500" />
              <span>pgvector semantic taxonomy</span>
            </div>
            <div className="flex items-center gap-2">
              <CheckCircle className="h-4 w-4 text-emerald-500" />
              <span>EU AI Act governance gate</span>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
