"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Lightbulb, AlertCircle } from "lucide-react";
import { getProblems } from "@/lib/client-api";

export default function InsightsPage() {
  const [problems, setProblems] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      try {
        // getProblems() sends the auth headers and throws on a non-2xx response, so a
        // failure surfaces as an error instead of being masked as "No insights yet".
        setProblems(await getProblems());
      } catch (e) {
        setError(e instanceof Error ? e.message : "Failed to load insights");
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  if (loading) return <div className="text-muted-foreground">Loading insights...</div>;

  if (error) {
    return (
      <Card>
        <CardContent className="text-center py-12">
          <AlertCircle className="h-8 w-8 text-destructive mx-auto mb-3" />
          <p className="text-sm text-muted-foreground">Failed to load insights: {error}</p>
        </CardContent>
      </Card>
    );
  }

  const columns = [
    { key: "validation_required", label: "Validation", statuses: ["validation_required"] },
    { key: "approval_needed", label: "Needs Approval", statuses: ["approval_needed"] },
    { key: "in_progress", label: "In Progress", statuses: ["in_progress", "blocked_by_policy"] },
    { key: "resolved", label: "Resolved", statuses: ["resolved"] },
  ];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Insights</h1>
        <p className="text-sm text-muted-foreground mt-1">AI-synthesized problem insights from customer signals</p>
      </div>

      {problems.length === 0 ? (
        <Card>
          <CardContent className="text-center py-12">
            <Lightbulb className="h-8 w-8 text-muted-foreground mx-auto mb-3" />
            <p className="text-sm text-muted-foreground">
              No insights yet. Run the triage pipeline on signals to generate insights.
            </p>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          {columns.map(col => {
            const items = problems.filter(p => col.statuses.includes(p.status));
            return (
              <div key={col.key} className="space-y-3">
                <div className="flex items-center justify-between">
                  <h3 className="text-sm font-semibold">{col.label}</h3>
                  <Badge variant="secondary">{items.length}</Badge>
                </div>
                {items.map(p => (
                  <Link key={p.problem_id} href={`/insights/${p.problem_id}`} className="block">
                    <Card className="cursor-pointer hover:shadow-md transition-shadow">
                      <CardContent className="p-4">
                        <p className="text-sm font-medium line-clamp-2">{p.title}</p>
                        <div className="flex items-center gap-2 mt-2">
                          <Badge variant="secondary" className="text-xs">{p.journey}</Badge>
                          {p.status === "blocked_by_policy" && (
                            <Badge variant="destructive" className="text-xs">
                              <AlertCircle className="h-3 w-3 mr-1" />
                              Blocked
                            </Badge>
                          )}
                        </div>
                        {p.impact_score !== undefined && (
                          <div className="mt-2 text-xs text-muted-foreground">
                            Impact: {Math.round(p.impact_score * 100)}%
                          </div>
                        )}
                      </CardContent>
                    </Card>
                  </Link>
                ))}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
