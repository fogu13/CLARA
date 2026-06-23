import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { supabase } from "@/integrations/supabase/client";
import { useWorkspaceId } from "@/hooks/use-workspace";
import { AppLayout } from "@/components/layout/AppLayout";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { Sparkles, Search, Loader2 } from "lucide-react";
import { toast } from "sonner";
import { decayedConfidence, isStale, rankLearnings } from "@/lib/learnings";
import type { AbLearning } from "@/lib/types";

const topicIcons: Record<string, string> = {
  subject_lines: "✉️",
  cta_text: "🔘",
  send_time: "🕐",
  layout: "📐",
  personalization: "👤",
  imagery: "🖼️",
};

function normalizeEvidence(raw: unknown): AbLearning["evidence"] {
  const e = (raw as Record<string, unknown>) ?? {};
  return {
    tests_count: (e.tests_count as number) ?? 0,
    avg_lift_pct: (e.avg_lift_pct as number) ?? 0,
    confidence: (e.confidence as number) ?? 0,
    sample_size: (e.sample_size as number) ?? 0,
    winning_examples: Array.isArray(e.winning_examples) ? (e.winning_examples as string[]) : [],
    losing_examples: Array.isArray(e.losing_examples) ? (e.losing_examples as string[]) : [],
  };
}

const LearningsPage = () => {
  const workspaceId = useWorkspaceId();
  const qc = useQueryClient();
  const [query, setQuery] = useState("");

  const { data: learnings = [], isLoading } = useQuery({
    queryKey: ["learnings", workspaceId],
    queryFn: async () => {
      const { data, error } = await supabase
        .from("ab_learnings")
        .select("*")
        .eq("workspace_id", workspaceId!)
        .order("created_at", { ascending: false });
      if (error) throw error;
      return (data as Record<string, unknown>[]).map((row) => ({
        ...row,
        evidence: normalizeEvidence(row.evidence),
        test_ids: Array.isArray(row.test_ids) ? row.test_ids : [],
        is_validated: row.is_validated ?? false,
      })) as AbLearning[];
    },
    enabled: !!workspaceId,
  });

  const extract = useMutation({
    mutationFn: async () => {
      const { data, error } = await supabase.functions.invoke("extract-learnings", {
        body: { workspace_id: workspaceId },
      });
      if (error) throw error;
      if (data?.error) throw new Error(data.error);
      return data as { created: number };
    },
    onSuccess: (d) => {
      toast.success(d?.created ? `Extracted ${d.created} learning(s)` : "No new learnings found");
      qc.invalidateQueries({ queryKey: ["learnings", workspaceId] });
    },
    onError: (e) => toast.error(e instanceof Error ? e.message : "Extraction failed"),
  });

  // D2 retrieval: free-text search ranks by relevance × decayed confidence.
  const visible = query.trim() ? rankLearnings(learnings, query, 100) : learnings;

  const grouped = visible.reduce<Record<string, AbLearning[]>>((acc, l) => {
    (acc[l.topic] ||= []).push(l);
    return acc;
  }, {});

  return (
    <AppLayout title="A/B Learnings">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-6">
        <p className="text-sm text-muted-foreground">Accumulated learnings from A/B tests across all campaigns.</p>
        <div className="flex items-center gap-2">
          <div className="relative">
            <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground" />
            <Input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search learnings…"
              className="pl-8 h-9 w-56"
            />
          </div>
          <Button size="sm" disabled={extract.isPending || !workspaceId} onClick={() => extract.mutate()}>
            {extract.isPending ? <><Loader2 className="h-3.5 w-3.5 mr-1.5 animate-spin" />Extracting…</> : <><Sparkles className="h-3.5 w-3.5 mr-1.5" />Extract Learnings</>}
          </Button>
        </div>
      </div>

      {isLoading ? (
        <div className="space-y-8">
          {Array.from({ length: 2 }).map((_, i) => (
            <div key={i} className="space-y-4">
              <Skeleton className="h-5 w-32" />
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <Skeleton className="h-52 w-full rounded-lg" />
                <Skeleton className="h-52 w-full rounded-lg" />
              </div>
            </div>
          ))}
        </div>
      ) : Object.keys(grouped).length === 0 ? (
        <p className="text-sm text-muted-foreground text-center py-12">
          {query.trim() ? `No learnings match "${query}".` : "No A/B learnings yet."}
        </p>
      ) : (
        <div className="space-y-8">
          {Object.entries(grouped).map(([topic, topicLearnings]) => (
            <div key={topic}>
              <h2 className="text-sm font-semibold mb-4 flex items-center gap-2 capitalize">
                <span>{topicIcons[topic] || "📊"}</span>
                {topic.replace(/_/g, " ")}
              </h2>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {topicLearnings.map((learning) => {
                  const decayed = decayedConfidence(learning);
                  const stale = isStale(learning);
                  return (
                  <div key={learning.id} className="rounded-lg border bg-card p-6 shadow-sm animate-fade-in">
                    <div className="flex items-center gap-2 mb-3">
                      {learning.is_validated ? (
                        <span className="text-xs bg-success/15 text-success px-2.5 py-0.5 rounded-full font-semibold">✅ VALIDATED ({learning.evidence.tests_count} tests)</span>
                      ) : (
                        <span className="text-xs bg-warning/15 text-warning px-2.5 py-0.5 rounded-full font-semibold">🔄 EMERGING ({learning.evidence.tests_count} tests)</span>
                      )}
                      {stale && (
                        <span className="text-xs bg-muted text-muted-foreground px-2.5 py-0.5 rounded-full font-semibold">⏳ STALE</span>
                      )}
                    </div>

                    <p className="text-sm font-semibold mb-4 leading-relaxed">"{learning.pattern}"</p>

                    <div className="flex gap-6 mb-4 text-xs text-muted-foreground">
                      <span>Avg lift: <strong className="text-success font-mono">+{learning.evidence.avg_lift_pct}%</strong></span>
                      <span>
                        Confidence: <strong className="font-mono">{(decayed * 100).toFixed(0)}%</strong>
                        <span className="text-muted-foreground/60"> (was {(learning.evidence.confidence * 100).toFixed(0)}%)</span>
                      </span>
                      <span>Sample: <strong className="font-mono">{learning.evidence.sample_size.toLocaleString()}</strong></span>
                    </div>

                    <div className="space-y-2">
                      <div>
                        <span className="text-xs text-success font-semibold">Winners:</span>
                        {learning.evidence.winning_examples.map((ex, i) => (
                          <p key={i} className="text-xs text-muted-foreground ml-3 italic">"{ex}"</p>
                        ))}
                      </div>
                      <div>
                        <span className="text-xs text-destructive font-semibold">Losers:</span>
                        {learning.evidence.losing_examples.map((ex, i) => (
                          <p key={i} className="text-xs text-muted-foreground ml-3 italic">"{ex}"</p>
                        ))}
                      </div>
                    </div>
                  </div>
                  );
                })}
              </div>
            </div>
          ))}
        </div>
      )}
    </AppLayout>
  );
};

export default LearningsPage;
