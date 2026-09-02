"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { getLearnings } from "@/lib/client-api";
import { useI18n } from "@/lib/i18n";
import type { LearningMemoryItem } from "@/lib/types";
import { StateNotice } from "./state-notice";

function statusVariant(status: LearningMemoryItem["learning_status"]): "success" | "warning" | "destructive" | "secondary" {
  if (status === "worked") return "success";
  if (status === "partially_worked") return "warning";
  if (status === "did_not_work") return "destructive";
  return "secondary";
}

function label(value: string): string {
  return value.replaceAll("_", " ");
}

// The learning memory: what was done for a theme and whether it measurably
// worked. This is the half of "close & learn" the model reads back — only
// human-validated (retrieval_eligible) items ever reach a synthesis prompt.
export function LearningMemoryPanel() {
  const { t } = useI18n();
  const [items, setItems] = useState<LearningMemoryItem[] | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    let cancelled = false;
    function load() {
      getLearnings()
        .then((data) => {
          if (cancelled) return;
          setItems(data);
          setFailed(false);
        })
        .catch(() => {
          if (cancelled) return;
          setItems([]);
          setFailed(true);
        });
    }
    load();
    window.addEventListener("clara:outcome-recorded", load);
    return () => {
      cancelled = true;
      window.removeEventListener("clara:outcome-recorded", load);
    };
  }, []);

  return (
    <Card>
      <CardHeader>
        <CardTitle>{t.learnings.memoryTitle}</CardTitle>
        <CardDescription>{t.learnings.memorySubtitle}</CardDescription>
      </CardHeader>
      <CardContent className="space-y-3">
        {items === null ? (
          <p className="text-sm text-muted-foreground">{t.common.loading}</p>
        ) : failed ? (
          <StateNotice tone="error" title={t.learnings.memoryUnavailable}>
            {t.common.error}
          </StateNotice>
        ) : items.length === 0 ? (
          <p className="text-sm text-muted-foreground">{t.learnings.memoryEmpty}</p>
        ) : (
          items.map((item) => (
            <div key={item.conclusion_id} className="rounded-lg border p-3 text-sm">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div className="flex flex-wrap items-center gap-2">
                  <Badge variant={statusVariant(item.learning_status)}>{label(item.learning_status)}</Badge>
                  {item.topic ? <span className="font-medium">{label(item.topic)}</span> : null}
                  <Badge variant="outline">{item.freshness.toLowerCase()}</Badge>
                </div>
                <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
                  <span>
                    {t.learnings.confidence}: {Math.round(item.decayed_confidence * 100)}%
                  </span>
                  <Badge variant={item.retrieval_eligible ? "success" : "secondary"}>
                    {item.retrieval_eligible ? t.learnings.retrievalEligible : t.learnings.pendingValidation}
                  </Badge>
                </div>
              </div>
              {item.summary ? <p className="mt-2">{item.summary}</p> : null}
              {item.resolution_actions && item.resolution_actions.length > 0 ? (
                <div className="mt-2 text-xs text-muted-foreground">
                  <span className="font-medium text-foreground">{t.learnings.resolution}:</span>
                  <ul className="mt-1 list-disc space-y-0.5 pl-4">
                    {item.resolution_actions.map((action) => (
                      <li key={action}>{action}</li>
                    ))}
                  </ul>
                </div>
              ) : null}
              {item.limitations ? (
                <p className="mt-2 text-xs text-muted-foreground">{item.limitations}</p>
              ) : null}
              {item.problem_id && !item.problem_id.startsWith("TRIAGE-") ? (
                <Link href={`/insights/${item.problem_id}`} className="mt-2 inline-block text-xs text-primary hover:underline">
                  {item.problem_id}
                </Link>
              ) : null}
            </div>
          ))
        )}
      </CardContent>
    </Card>
  );
}
