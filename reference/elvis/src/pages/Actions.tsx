import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { supabase } from "@/integrations/supabase/client";
import { useWorkspaceId } from "@/hooks/use-workspace";
import { useAuth } from "@/contexts/AuthContext";
import { AppLayout } from "@/components/layout/AppLayout";
import { StatusBadge } from "@/components/shared/Badges";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";
import { Check, X } from "lucide-react";
import { formatDistanceToNow } from "date-fns";
import { toast } from "sonner";
import { logEvent } from "@/lib/events";
import type { ActionLog } from "@/lib/types";

function normalizeAction(row: Record<string, unknown>): ActionLog {
  return {
    ...row,
    action_params: (row.action_params as Record<string, unknown>) ?? {},
    action_result: (row.action_result as Record<string, unknown>) ?? undefined,
  } as ActionLog;
}

const ActionsPage = () => {
  const workspaceId = useWorkspaceId();
  const { user } = useAuth();
  const qc = useQueryClient();

  const decide = useMutation({
    mutationFn: async ({ id, decision }: { id: number; decision: "approve" | "reject" }) => {
      const update =
        decision === "approve"
          ? { status: "completed", executed_by: `user:${user?.id ?? ""}`.slice(0, 50) }
          : { status: "rejected", error_message: "Rejected by reviewer" };
      const { error } = await supabase
        .from("actions_log")
        .update(update)
        .eq("id", id)
        .eq("workspace_id", workspaceId!);
      if (error) throw error;
    },
    onSuccess: (_d, { id, decision }) => {
      toast.success(decision === "approve" ? "Action approved" : "Action rejected");
      logEvent(workspaceId!, decision === "approve" ? "action_approved" : "action_rejected", {
        entity: "action", entity_id: id, user_id: user?.id,
      });
      qc.invalidateQueries({ queryKey: ["actions", workspaceId] });
    },
    onError: (e) => toast.error(e instanceof Error ? e.message : "Failed to update action"),
  });

  const { data: actions = [], isLoading } = useQuery({
    queryKey: ["actions", workspaceId],
    queryFn: async () => {
      const { data, error } = await supabase
        .from("actions_log")
        .select("*")
        .eq("workspace_id", workspaceId!)
        .order("executed_at", { ascending: false });
      if (error) throw error;
      return (data as Record<string, unknown>[]).map(normalizeAction);
    },
    enabled: !!workspaceId,
  });

  const pending = actions.filter((a) => a.status === "pending_approval");
  const completed = actions.filter((a) => a.status !== "pending_approval");

  return (
    <AppLayout title="Actions">
      {/* Pending approvals */}
      {pending.length > 0 && (
        <div className="mb-8">
          <h2 className="text-sm font-semibold mb-4 flex items-center gap-2">
            Pending Approvals
            <span className="bg-warning/15 text-warning text-xs rounded-full px-2 py-0.5">{pending.length}</span>
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {pending.map((action) => (
              <div key={action.id} className="rounded-lg border bg-card p-5 shadow-sm border-warning/30">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm font-semibold capitalize">{action.action_type.replace(/_/g, " ")}</span>
                  <StatusBadge status={action.status} />
                </div>
                <p className="text-xs text-muted-foreground mb-1">Insight #{action.insight_id}</p>
                <p className="text-xs text-muted-foreground mb-4">
                  {Object.entries(action.action_params).map(([k, v]) => `${k}: ${String(v)}`).join(" • ")}
                </p>
                <div className="flex gap-2">
                  <Button size="sm" className="flex-1" disabled={decide.isPending}
                    onClick={() => decide.mutate({ id: action.id, decision: "approve" })}>
                    <Check className="h-3 w-3 mr-1" />Approve
                  </Button>
                  <Button size="sm" variant="outline" disabled={decide.isPending}
                    onClick={() => decide.mutate({ id: action.id, decision: "reject" })}>
                    <X className="h-3 w-3 mr-1" />Reject
                  </Button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Action log */}
      <div>
        <h2 className="text-sm font-semibold mb-4">Action History</h2>
        <div className="rounded-lg border bg-card shadow-sm overflow-hidden">
          <table className="w-full">
            <thead>
              <tr className="border-b bg-secondary/50">
                <th className="text-left text-xs font-semibold text-muted-foreground px-4 py-3">Type</th>
                <th className="text-left text-xs font-semibold text-muted-foreground px-4 py-3">Insight</th>
                <th className="text-left text-xs font-semibold text-muted-foreground px-4 py-3">Executed By</th>
                <th className="text-left text-xs font-semibold text-muted-foreground px-4 py-3">Status</th>
                <th className="text-left text-xs font-semibold text-muted-foreground px-4 py-3">Result</th>
                <th className="text-left text-xs font-semibold text-muted-foreground px-4 py-3">Time</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {isLoading ? (
                Array.from({ length: 5 }).map((_, i) => (
                  <tr key={i}><td colSpan={6} className="px-4 py-3"><Skeleton className="h-5 w-full" /></td></tr>
                ))
              ) : completed.length === 0 ? (
                <tr><td colSpan={6} className="px-4 py-8 text-center text-sm text-muted-foreground">No actions recorded yet</td></tr>
              ) : (
                completed.map((action) => (
                  <tr key={action.id} className="hover:bg-secondary/30 transition-colors">
                    <td className="px-4 py-3 text-sm font-medium capitalize">{action.action_type.replace(/_/g, " ")}</td>
                    <td className="px-4 py-3 text-sm text-muted-foreground">#{action.insight_id}</td>
                    <td className="px-4 py-3 text-xs text-muted-foreground">{action.executed_by}</td>
                    <td className="px-4 py-3"><StatusBadge status={action.status} /></td>
                    <td className="px-4 py-3 text-xs text-muted-foreground max-w-[200px] truncate">
                      {action.action_result ? Object.entries(action.action_result).map(([k, v]) => `${k}: ${String(v)}`).join(", ") : "—"}
                    </td>
                    <td className="px-4 py-3 text-xs text-muted-foreground">{formatDistanceToNow(new Date(action.executed_at), { addSuffix: true })}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </AppLayout>
  );
};

export default ActionsPage;
