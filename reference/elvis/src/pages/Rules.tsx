import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { supabase } from "@/integrations/supabase/client";
import { useWorkspaceId } from "@/hooks/use-workspace";
import { AppLayout } from "@/components/layout/AppLayout";
import { Button } from "@/components/ui/button";
import { Switch } from "@/components/ui/switch";
import { Skeleton } from "@/components/ui/skeleton";
import { Plus, Pencil } from "lucide-react";
import { formatDistanceToNow } from "date-fns";
import { toast } from "sonner";
import type { FeedbackRule } from "@/lib/types";
import { RuleBuilderDialog } from "@/components/rules/RuleBuilderDialog";

const RulesPage = () => {
  const workspaceId = useWorkspaceId();
  const queryClient = useQueryClient();
  const [builderOpen, setBuilderOpen] = useState(false);
  const [editingRule, setEditingRule] = useState<FeedbackRule | null>(null);

  const openCreate = () => { setEditingRule(null); setBuilderOpen(true); };
  const openEdit = (rule: FeedbackRule) => { setEditingRule(rule); setBuilderOpen(true); };

  const { data: rules = [], isLoading } = useQuery({
    queryKey: ["rules", workspaceId],
    queryFn: async () => {
      const { data, error } = await supabase
        .from("feedback_rules")
        .select("*")
        .eq("workspace_id", workspaceId!)
        .order("created_at", { ascending: false });
      if (error) throw error;
      return data as unknown as FeedbackRule[];
    },
    enabled: !!workspaceId,
  });

  const toggleRule = useMutation({
    mutationFn: async ({ id, enabled }: { id: number; enabled: boolean }) => {
      const { error } = await supabase
        .from("feedback_rules")
        .update({ enabled })
        .eq("id", id)
        .eq("workspace_id", workspaceId!);
      if (error) throw error;
    },
    onMutate: async ({ id, enabled }) => {
      await queryClient.cancelQueries({ queryKey: ["rules", workspaceId] });
      const previous = queryClient.getQueryData<FeedbackRule[]>(["rules", workspaceId]);
      queryClient.setQueryData<FeedbackRule[]>(["rules", workspaceId], (old) =>
        old?.map((r) => (r.id === id ? { ...r, enabled } : r))
      );
      return { previous };
    },
    onError: (_err, _vars, context) => {
      queryClient.setQueryData(["rules", workspaceId], context?.previous);
      toast.error("Failed to update rule");
    },
  });

  return (
    <AppLayout title="Automation Rules">
      <div className="flex items-center justify-between mb-6">
        <p className="text-sm text-muted-foreground">Configure automated responses to insights.</p>
        <Button size="sm" onClick={openCreate}><Plus className="h-3.5 w-3.5 mr-1.5" />Create Rule</Button>
      </div>

      <div className="rounded-lg border bg-card shadow-sm overflow-hidden">
        <table className="w-full">
          <thead>
            <tr className="border-b bg-secondary/50">
              <th className="text-left text-xs font-semibold text-muted-foreground px-4 py-3 w-16">Active</th>
              <th className="text-left text-xs font-semibold text-muted-foreground px-4 py-3">Name</th>
              <th className="text-left text-xs font-semibold text-muted-foreground px-4 py-3">Conditions</th>
              <th className="text-left text-xs font-semibold text-muted-foreground px-4 py-3">Actions</th>
              <th className="text-left text-xs font-semibold text-muted-foreground px-4 py-3 w-20">Auto</th>
              <th className="text-left text-xs font-semibold text-muted-foreground px-4 py-3 w-24">Triggered</th>
              <th className="text-left text-xs font-semibold text-muted-foreground px-4 py-3 w-28">Last Trigger</th>
              <th className="px-4 py-3 w-12"></th>
            </tr>
          </thead>
          <tbody className="divide-y">
            {isLoading ? (
              Array.from({ length: 4 }).map((_, i) => (
                <tr key={i}><td colSpan={8} className="px-4 py-3"><Skeleton className="h-5 w-full" /></td></tr>
              ))
            ) : rules.length === 0 ? (
              <tr><td colSpan={8} className="px-4 py-8 text-center text-sm text-muted-foreground">No rules configured</td></tr>
            ) : (
              rules.map((rule) => {
                const conditions = rule.conditions as Record<string, unknown>;
                const condSummary = Object.entries(conditions)
                  .map(([k, v]) => `${k.replace(/_/g, " ")}: ${Array.isArray(v) ? (v as string[]).join(", ") : String(v)}`)
                  .join("; ");
                const actionsSummary = (rule.actions as Record<string, unknown>[])
                  .map((a) => String(a.type || "").replace(/_/g, " "))
                  .join(", ");

                return (
                  <tr key={rule.id} className="hover:bg-secondary/30 transition-colors">
                    <td className="px-4 py-3"><Switch checked={rule.enabled} onCheckedChange={(checked) => toggleRule.mutate({ id: rule.id, enabled: checked })} /></td>
                    <td className="px-4 py-3">
                      <div className="text-sm font-medium">{rule.name}</div>
                      {rule.description && <div className="text-xs text-muted-foreground line-clamp-1">{rule.description}</div>}
                    </td>
                    <td className="px-4 py-3 text-xs text-muted-foreground max-w-[200px] truncate">{condSummary}</td>
                    <td className="px-4 py-3 text-xs text-muted-foreground capitalize">{actionsSummary}</td>
                    <td className="px-4 py-3">
                      {rule.auto_execute
                        ? <span className="text-xs bg-success/15 text-success px-2 py-0.5 rounded-full font-medium">Auto</span>
                        : <span className="text-xs bg-secondary text-muted-foreground px-2 py-0.5 rounded-full">Manual</span>
                      }
                    </td>
                    <td className="px-4 py-3 font-mono text-sm">{rule.times_triggered}</td>
                    <td className="px-4 py-3 text-xs text-muted-foreground">
                      {rule.last_triggered_at ? formatDistanceToNow(new Date(rule.last_triggered_at), { addSuffix: true }) : "Never"}
                    </td>
                    <td className="px-4 py-3">
                      <Button size="icon" variant="ghost" className="h-8 w-8" onClick={() => openEdit(rule)} aria-label="Edit rule">
                        <Pencil className="h-3.5 w-3.5" />
                      </Button>
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>

      {workspaceId != null && (
        <RuleBuilderDialog
          open={builderOpen}
          onOpenChange={setBuilderOpen}
          rule={editingRule}
          workspaceId={workspaceId}
        />
      )}
    </AppLayout>
  );
};

export default RulesPage;
