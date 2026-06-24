"use client";

import { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { CheckCircle, XCircle, Clock, ArrowRight } from "lucide-react";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function ActionsPage() {
  const [approvals, setApprovals] = useState<any[]>([]);
  const [executions, setExecutions] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      try {
        const [aRes, eRes] = await Promise.all([
          fetch(`${API_URL}/approvals`).then(r => r.ok ? r.json() : []),
          fetch(`${API_URL}/executions`).then(r => r.ok ? r.json() : []),
        ]);
        setApprovals(aRes || []);
        setExecutions(eRes || []);
      } catch { /* API not running */ }
      finally { setLoading(false); }
    }
    load();
  }, []);

  if (loading) return <div className="text-muted-foreground">Loading actions...</div>;

  const pendingApprovals = approvals.filter(a => a.decision === "approved" && !a.executed);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Actions</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Pending approvals and executed actions — governed by human-in-the-loop oversight
        </p>
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardHeader className="pb-2"><CardTitle className="text-sm text-muted-foreground">Pending Approvals</CardTitle></CardHeader>
          <CardContent><div className="text-2xl font-bold">{pendingApprovals.length}</div></CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2"><CardTitle className="text-sm text-muted-foreground">Executed Actions</CardTitle></CardHeader>
          <CardContent><div className="text-2xl font-bold">{executions.length}</div></CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2"><CardTitle className="text-sm text-muted-foreground">Connectors Active</CardTitle></CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {new Set(executions.filter(e => e.status === "completed").map(e => e.destination)).size}
            </div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Pending Approvals</CardTitle>
        </CardHeader>
        <CardContent>
          {pendingApprovals.length === 0 ? (
            <div className="text-center py-8">
              <CheckCircle className="h-8 w-8 text-muted-foreground mx-auto mb-3" />
              <p className="text-sm text-muted-foreground">No pending approvals.</p>
            </div>
          ) : (
            <div className="space-y-3">
              {pendingApprovals.map(a => (
                <div key={a.approval_id} className="flex items-center justify-between border-b pb-3">
                  <div className="flex-1">
                    <p className="text-sm font-medium">{a.problem_id}</p>
                    <p className="text-xs text-muted-foreground">Actor: {a.actor}</p>
                  </div>
                  <div className="flex gap-2">
                    <Button size="sm" variant="default">
                      <CheckCircle className="h-3 w-3 mr-1" />
                      Approve
                    </Button>
                    <Button size="sm" variant="outline">
                      <XCircle className="h-3 w-3 mr-1" />
                      Reject
                    </Button>
                  </div>
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
              {executions.slice(0, 20).map(e => (
                <div key={e.execution_id} className="flex items-center justify-between border-b pb-3">
                  <div className="flex items-center gap-3">
                    {e.status === "completed" ? (
                      <CheckCircle className="h-4 w-4 text-emerald-500" />
                    ) : e.status === "blocked" ? (
                      <XCircle className="h-4 w-4 text-destructive" />
                    ) : (
                      <Clock className="h-4 w-4 text-muted-foreground" />
                    )}
                    <div>
                      <p className="text-sm font-medium">{e.problem_id}</p>
                      <p className="text-xs text-muted-foreground">
                        Destination: {e.destination || "N/A"}
                      </p>
                    </div>
                  </div>
                  <Badge variant={e.status === "completed" ? "success" : e.status === "blocked" ? "destructive" : "secondary"}>
                    {e.status}
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
            <Badge variant="secondary">Zendesk (in)</Badge>
            <ArrowRight className="h-3 w-3 text-muted-foreground" />
            <Badge variant="secondary">LLM Triage</Badge>
            <ArrowRight className="h-3 w-3 text-muted-foreground" />
            <Badge variant="secondary">Governance Gate</Badge>
            <ArrowRight className="h-3 w-3 text-muted-foreground" />
            <Badge variant="secondary">Human Approval</Badge>
            <ArrowRight className="h-3 w-3 text-muted-foreground" />
            <Badge variant="success">Jira + Slack (out)</Badge>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
