import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { supabase } from "@/integrations/supabase/client";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { toast } from "sonner";
import { Check, X, GitMerge } from "lucide-react";
import { logEvent } from "@/lib/events";
import type { TaxonomyNode } from "@/lib/types";

interface Props { workspaceId: number; candidates: TaxonomyNode[]; activeNodes: TaxonomyNode[]; }

export function ReviewQueue({ workspaceId, candidates, activeNodes }: Props) {
  const qc = useQueryClient();
  const [edit, setEdit] = useState<Record<string, string>>({});
  const [mergeTarget, setMergeTarget] = useState<Record<string, string>>({});
  const refresh = () => qc.invalidateQueries({ queryKey: ["taxonomy", workspaceId] });

  const act = useMutation({
    mutationFn: async (p: { node: TaxonomyNode; action: "approve" | "reject" | "merge" }) => {
      const { node, action } = p;
      if (action === "approve") {
        const name = edit[node.id] ?? node.name;
        const { error } = await supabase.from("taxonomy_nodes")
          .update({ status: "active", origin: "uploaded", name }).eq("id", node.id);
        if (error) throw error;
        await logEvent(workspaceId, "taxonomy_node_promoted", { entity: "taxonomy_node", entity_id: node.id, metadata: { name } });
      } else if (action === "reject") {
        const { error } = await supabase.from("taxonomy_nodes").update({ status: "archived" }).eq("id", node.id);
        if (error) throw error;
        await logEvent(workspaceId, "taxonomy_node_rejected", { entity: "taxonomy_node", entity_id: node.id });
      } else {
        const into = mergeTarget[node.id];
        if (!into) throw new Error("Pick a node to merge into.");
        const { error } = await supabase.rpc("merge_taxonomy_node", { p_from: node.id, p_into: into });
        if (error) throw error;
        await logEvent(workspaceId, "taxonomy_node_merged", { entity: "taxonomy_node", entity_id: node.id, metadata: { into } });
      }
    },
    onSuccess: () => { refresh(); toast.success("Taxonomy updated"); },
    onError: (e) => toast.error("Action failed", { description: e instanceof Error ? e.message : undefined }),
  });

  if (!candidates.length) return null;

  return (
    <div className="rounded-lg border border-border p-4 mb-6">
      <div className="flex items-center gap-2 mb-3">
        <h2 className="text-sm font-semibold">Review queue</h2>
        <Badge variant="outline" className="text-[10px]">{candidates.length} candidate(s)</Badge>
      </div>
      <div className="space-y-4">
        {candidates.map((c) => (
          <div key={c.id} className="border-b border-border/50 pb-3">
            <div className="flex items-center gap-2 mb-1">
              <Input className="h-7 w-56 text-sm" defaultValue={c.name} onChange={(e) => setEdit((s) => ({ ...s, [c.id]: e.target.value }))} />
              <span className="text-xs text-muted-foreground">conf {Math.round((c.confidence ?? 0) * 100)}% · {c.evidence?.size ?? 0} signals</span>
            </div>
            {c.evidence?.samples?.length ? (
              <ul className="text-xs text-muted-foreground list-disc ml-5 mb-2">
                {c.evidence.samples.slice(0, 3).map((s, i) => <li key={i} className="truncate">{s}</li>)}
              </ul>
            ) : null}
            <div className="flex items-center gap-2">
              <Button size="sm" variant="outline" disabled={act.isPending} onClick={() => act.mutate({ node: c, action: "approve" })}>
                <Check className="h-3.5 w-3.5 mr-1" />Approve
              </Button>
              <Button size="sm" variant="outline" disabled={act.isPending} onClick={() => act.mutate({ node: c, action: "reject" })}>
                <X className="h-3.5 w-3.5 mr-1" />Reject
              </Button>
              <select className="h-8 rounded-md border border-input bg-background px-2 text-xs"
                value={mergeTarget[c.id] ?? ""} onChange={(e) => setMergeTarget((s) => ({ ...s, [c.id]: e.target.value }))}>
                <option value="">merge into…</option>
                {activeNodes.map((n) => <option key={n.id} value={n.id}>{n.name}</option>)}
              </select>
              <Button size="sm" variant="outline" disabled={act.isPending || !mergeTarget[c.id]} onClick={() => act.mutate({ node: c, action: "merge" })}>
                <GitMerge className="h-3.5 w-3.5 mr-1" />Merge
              </Button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
