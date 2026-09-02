"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Lightbulb, AlertCircle } from "lucide-react";
import { getProblems } from "@/lib/client-api";
import type { ProblemSummary } from "@/lib/types";
import { AskClaraPanel } from "../../components/ask-clara-panel";
import { useI18n } from "@/lib/i18n";

export default function InsightsPage() {
  const { t } = useI18n();
  const searchParams = useSearchParams();
  const owner = searchParams.get("owner") ?? "";
  const [problems, setProblems] = useState<ProblemSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      try {
        // getProblems() sends the auth headers and throws on a non-2xx response, so a
        // failure surfaces as an error instead of being masked as "No insights yet".
        setProblems(await getProblems({ owner: owner || undefined }));
      } catch (e) {
        setError(e instanceof Error ? e.message : "Failed to load insights");
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [owner]);

  if (loading) return <div className="text-muted-foreground">{t.common.loading}</div>;

  if (error) {
    return (
      <Card>
        <CardContent className="text-center py-12">
          <AlertCircle className="h-8 w-8 text-destructive mx-auto mb-3" />
          <p className="text-sm text-muted-foreground">{t.insights.loadFailed}: {error}</p>
        </CardContent>
      </Card>
    );
  }

  const columns = [
    { key: "validation_required", label: t.insights.validation, statuses: ["validation_required"] },
    { key: "approval_needed", label: t.insights.needsApproval, statuses: ["approval_needed"] },
    { key: "in_progress", label: t.insights.inProgress, statuses: ["in_progress", "blocked_by_policy"] },
    { key: "resolved", label: t.insights.resolved, statuses: ["resolved"] },
  ];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">{t.insights.title}</h1>
        <p className="text-sm text-muted-foreground mt-1">{t.insights.subtitle}</p>
      </div>

      <AskClaraPanel />

      {problems.length === 0 ? (
        <Card>
          <CardContent className="text-center py-12">
            <Lightbulb className="h-8 w-8 text-muted-foreground mx-auto mb-3" />
            <p className="text-sm text-muted-foreground">
              {t.insights.empty}
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
                        <div className="flex flex-wrap items-center gap-2 mt-2">
                          <Badge variant="secondary" className="text-xs">{p.journey}</Badge>
                          {p.overdue ? (
                            <Badge variant="destructive" className="text-xs" title={p.due_at ?? undefined}>
                              {t.dashboard.overdueChip}
                            </Badge>
                          ) : p.due_at ? (
                            <Badge variant="outline" className="text-xs" title={p.due_at}>
                              {t.dashboard.dueLabel} {p.due_at.slice(0, 10)}
                            </Badge>
                          ) : null}
                          {p.status === "blocked_by_policy" && (
                            <Badge variant="destructive" className="text-xs">
                              <AlertCircle className="h-3 w-3 mr-1" />
                              {t.insights.blocked}
                            </Badge>
                          )}
                        </div>
                        {p.impact_score !== undefined && (
                          <div className="mt-2 text-xs text-muted-foreground">
                            {t.insights.impact}: {Math.round(p.impact_score * 100)}%
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
