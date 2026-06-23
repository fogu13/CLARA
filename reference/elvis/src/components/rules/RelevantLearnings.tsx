import { useEffect } from "react";
import { useQuery } from "@tanstack/react-query";
import { supabase } from "@/integrations/supabase/client";
import type { AbLearning } from "@/lib/types";
import { logEvent } from "@/lib/events";
import { decayedConfidence, isStale, rankLearnings } from "@/lib/learnings";
import { Lightbulb } from "lucide-react";

/**
 * Surfaces past A/B learnings relevant to the categories a user is building a rule for
 * (Phase D2 — "relevant past learnings" retrieval). Keyword overlap for now; a semantic
 * (pgvector) ranking is layered on in Phase D without changing this interface.
 */
export function RelevantLearnings({ workspaceId, categories }: { workspaceId: number; categories: string[] }) {
  const { data: learnings = [] } = useQuery({
    queryKey: ["ab_learnings", workspaceId],
    queryFn: async () => {
      const { data, error } = await supabase
        .from("ab_learnings")
        .select("*")
        .eq("workspace_id", workspaceId);
      if (error) throw error;
      return data as unknown as AbLearning[];
    },
    enabled: !!workspaceId,
  });

  const matches = rankLearnings(learnings, categories.join(" "), 3);

  const shownKey = matches.map((m) => m.id).join(",");
  useEffect(() => {
    if (shownKey) logEvent(workspaceId, "learnings_shown", { entity: "learning", metadata: { count: shownKey.split(",").length } });
  }, [shownKey, workspaceId]);

  if (matches.length === 0) return null;

  return (
    <div className="rounded-lg border border-amber-200 bg-amber-50/60 p-3 space-y-2">
      <div className="flex items-center gap-1.5 text-xs font-semibold text-amber-900">
        <Lightbulb className="h-3.5 w-3.5" />
        Relevant past learnings
      </div>
      {matches.map((l) => (
        <div key={l.id} className="text-xs text-amber-950/80">
          <span className="font-medium">{l.pattern}</span>
          <span className="text-amber-900/60">
            {" "}— {Math.round(decayedConfidence(l) * 100)}% confidence
            {isStale(l) ? " · stale" : l.is_validated ? " · validated" : " · emerging"}
          </span>
        </div>
      ))}
    </div>
  );
}
