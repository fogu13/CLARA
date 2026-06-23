import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { supabase } from "@/integrations/supabase/client";
import { useWorkspaceId } from "@/hooks/use-workspace";
import { AppLayout } from "@/components/layout/AppLayout";
import type { Insight, InsightStatus } from "@/lib/types";
import { SeverityBadge, TeamBadge, StatusBadge } from "@/components/shared/Badges";
import { Skeleton } from "@/components/ui/skeleton";
import { formatDistanceToNow } from "date-fns";
import { useNavigate } from "react-router-dom";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Textarea } from "@/components/ui/textarea";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { toast } from "@/hooks/use-toast";
import { List, LayoutGrid, Ban, RefreshCw, X } from "lucide-react";

function normalizeInsight(row: Record<string, unknown>): Insight {
  return {
    ...row,
    suggested_actions: Array.isArray(row.suggested_actions) ? row.suggested_actions : [],
    actions_taken: Array.isArray(row.actions_taken) ? row.actions_taken : [],
    signal_ids: Array.isArray(row.signal_ids) ? row.signal_ids : [],
  } as Insight;
}

const STATUS_COLUMNS: { status: InsightStatus; label: string; colorClass: string }[] = [
  { status: "new", label: "New", colorClass: "bg-muted-foreground" },
  { status: "reviewing", label: "Reviewing", colorClass: "bg-info" },
  { status: "action_taken", label: "Action Taken", colorClass: "bg-warning" },
  { status: "resolved", label: "Resolved", colorClass: "bg-success" },
];

const STATUS_OPTIONS: { value: InsightStatus; label: string }[] = [
  { value: "new", label: "New" },
  { value: "reviewing", label: "Reviewing" },
  { value: "action_taken", label: "Action Taken" },
  { value: "resolved", label: "Resolved" },
];

/* ─── InsightCard ─────────────────────────────────────────── */
function InsightCard({
  insight,
  selected,
  onSelect,
  onClick,
}: {
  insight: Insight;
  selected: boolean;
  onSelect: (checked: boolean) => void;
  onClick: () => void;
}) {
  return (
    <div
      className={cn(
        "relative w-full text-left rounded-lg border bg-card p-4 shadow-sm hover:shadow-md transition-all animate-fade-in",
        selected && "border-primary ring-1 ring-primary"
      )}
    >
      {/* Checkbox overlay — stop propagation so clicking it doesn't open detail */}
      <div
        className="absolute top-3 left-3 z-10"
        onClick={(e) => e.stopPropagation()}
      >
        <Checkbox
          checked={selected}
          onCheckedChange={(v) => onSelect(!!v)}
          className="shadow"
        />
      </div>

      {/* Clickable body */}
      <button onClick={onClick} className="w-full text-left pl-6">
        <div className="flex items-center justify-between mb-2">
          <SeverityBadge severity={insight.severity} />
          <span className="text-xs text-muted-foreground">
            {formatDistanceToNow(new Date(insight.detected_at), { addSuffix: true })}
          </span>
        </div>
        <h4 className="text-sm font-semibold leading-snug mb-2 line-clamp-2">{insight.title}</h4>
        <div className="flex items-center gap-3 text-xs text-muted-foreground mb-3">
          <span className="font-mono">Impact: {insight.impact_score}/10</span>
          <span className="font-mono">Conf: {(insight.confidence * 100).toFixed(0)}%</span>
        </div>
        <div className="flex items-center justify-between">
          <TeamBadge team={insight.target_team} />
          <span className="text-xs text-muted-foreground">{insight.affected_contacts} contacts</span>
        </div>
        {insight.suggested_actions.length > 0 && (
          <div className="mt-2 text-xs text-muted-foreground">
            {insight.suggested_actions.length} suggested actions
          </div>
        )}
      </button>
    </div>
  );
}

/* ─── BatchActionBar ──────────────────────────────────────── */
function BatchActionBar({
  count,
  onChangeStatus,
  onDismiss,
  onClear,
  isPending,
}: {
  count: number;
  onChangeStatus: (s: InsightStatus) => void;
  onDismiss: () => void;
  onClear: () => void;
  isPending: boolean;
}) {
  const [pendingStatus, setPendingStatus] = useState<InsightStatus | "">("");

  return (
    <div className="fixed bottom-6 left-1/2 -translate-x-1/2 z-50 flex items-center gap-3 rounded-xl border bg-card px-5 py-3 shadow-2xl animate-fade-in">
      <span className="text-sm font-semibold text-foreground">{count} selected</span>

      <div className="h-4 w-px bg-border" />

      {/* Status change */}
      <div className="flex items-center gap-2">
        <Select
          value={pendingStatus}
          onValueChange={(v) => setPendingStatus(v as InsightStatus)}
          disabled={isPending}
        >
          <SelectTrigger className="h-8 w-40 text-xs">
            <SelectValue placeholder="Change status…" />
          </SelectTrigger>
          <SelectContent>
            {STATUS_OPTIONS.map((o) => (
              <SelectItem key={o.value} value={o.value} className="text-xs">
                {o.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Button
          size="sm"
          disabled={!pendingStatus || isPending}
          onClick={() => {
            if (pendingStatus) {
              onChangeStatus(pendingStatus as InsightStatus);
              setPendingStatus("");
            }
          }}
          className="h-8"
        >
          <RefreshCw className="h-3 w-3 mr-1" />
          Apply
        </Button>
      </div>

      <div className="h-4 w-px bg-border" />

      <Button
        size="sm"
        variant="destructive"
        disabled={isPending}
        onClick={onDismiss}
        className="h-8"
      >
        <Ban className="h-3 w-3 mr-1" />
        Dismiss
      </Button>

      <button
        onClick={onClear}
        className="ml-1 text-muted-foreground hover:text-foreground transition-colors"
        aria-label="Clear selection"
      >
        <X className="h-4 w-4" />
      </button>
    </div>
  );
}

/* ─── Main Page ───────────────────────────────────────────── */
const InsightsPage = () => {
  const workspaceId = useWorkspaceId();
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const [viewMode, setViewMode] = useState<"board" | "list">("board");
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set());
  const [dismissOpen, setDismissOpen] = useState(false);
  const [dismissReason, setDismissReason] = useState("");

  const { data: insights = [], isLoading } = useQuery({
    queryKey: ["insights", workspaceId],
    queryFn: async () => {
      const { data, error } = await supabase
        .from("insights")
        .select("*")
        .eq("workspace_id", workspaceId!)
        .order("detected_at", { ascending: false });
      if (error) throw error;
      return (data as Record<string, unknown>[]).map(normalizeInsight);
    },
    enabled: !!workspaceId,
  });

  /* ── mutations ── */
  const bulkStatusMutation = useMutation({
    mutationFn: async ({ ids, status }: { ids: number[]; status: InsightStatus }) => {
      const { error } = await supabase
        .from("insights")
        .update({ status, status_changed_at: new Date().toISOString() })
        .in("id", ids)
        .eq("workspace_id", workspaceId!);
      if (error) throw error;
    },
    onSuccess: (_d, { ids, status }) => {
      queryClient.invalidateQueries({ queryKey: ["insights"] });
      queryClient.invalidateQueries({ queryKey: ["insights-dash"] });
      toast({ title: `${ids.length} insight(s) updated to "${status.replace(/_/g, " ")}"` });
      setSelectedIds(new Set());
    },
    onError: (err: Error) => toast({ title: "Bulk update failed", description: err.message, variant: "destructive" }),
  });

  const bulkDismissMutation = useMutation({
    mutationFn: async ({ ids, reason }: { ids: number[]; reason: string }) => {
      const { error } = await supabase
        .from("insights")
        .update({ status: "dismissed", dismissed_reason: reason, status_changed_at: new Date().toISOString() })
        .in("id", ids)
        .eq("workspace_id", workspaceId!);
      if (error) throw error;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["insights"] });
      queryClient.invalidateQueries({ queryKey: ["insights-dash"] });
      toast({ title: `${selectedIds.size} insight(s) dismissed` });
      setSelectedIds(new Set());
      setDismissOpen(false);
      setDismissReason("");
    },
    onError: (err: Error) => toast({ title: "Bulk dismiss failed", description: err.message, variant: "destructive" }),
  });

  /* ── helpers ── */
  const toggleSelect = (id: number, checked: boolean) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      checked ? next.add(id) : next.delete(id);
      return next;
    });
  };

  const toggleAll = (list: Insight[]) => {
    const allSelected = list.every((i) => selectedIds.has(i.id));
    setSelectedIds((prev) => {
      const next = new Set(prev);
      list.forEach((i) => (allSelected ? next.delete(i.id) : next.add(i.id)));
      return next;
    });
  };

  const getColumnInsights = (status: InsightStatus) =>
    insights.filter((i) => {
      if (status === "action_taken") return i.status === "action_taken" || i.status === "action_planned";
      return i.status === status;
    });

  const dismissed = insights.filter((i) => i.status === "dismissed");
  const isPending = bulkStatusMutation.isPending || bulkDismissMutation.isPending;
  const selectedArr = Array.from(selectedIds);

  if (isLoading) {
    return (
      <AppLayout title="Insights">
        <div className="grid grid-cols-4 gap-4">
          {STATUS_COLUMNS.map((col) => (
            <div key={col.status} className="space-y-3">
              <Skeleton className="h-6 w-24" />
              {Array.from({ length: 2 }).map((_, i) => (
                <Skeleton key={i} className="h-36 w-full rounded-lg" />
              ))}
            </div>
          ))}
        </div>
      </AppLayout>
    );
  }

  return (
    <AppLayout title="Insights">
      {/* Toolbar */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-2">
          <Button
            variant={viewMode === "board" ? "default" : "outline"}
            size="sm"
            onClick={() => setViewMode("board")}
          >
            <LayoutGrid className="h-3.5 w-3.5 mr-1" />Board
          </Button>
          <Button
            variant={viewMode === "list" ? "default" : "outline"}
            size="sm"
            onClick={() => setViewMode("list")}
          >
            <List className="h-3.5 w-3.5 mr-1" />List
          </Button>
        </div>
        {dismissed.length > 0 && (
          <span className="text-xs text-muted-foreground">{dismissed.length} dismissed</span>
        )}
      </div>

      {/* ── Board view ── */}
      {viewMode === "board" ? (
        <div className="grid grid-cols-4 gap-4">
          {STATUS_COLUMNS.map((col) => {
            const colInsights = getColumnInsights(col.status);
            const allColSelected = colInsights.length > 0 && colInsights.every((i) => selectedIds.has(i.id));
            return (
              <div key={col.status} className="space-y-3">
                <div className="flex items-center gap-2 px-1">
                  <Checkbox
                    checked={allColSelected}
                    onCheckedChange={() => toggleAll(colInsights)}
                    disabled={colInsights.length === 0}
                    className="h-3.5 w-3.5"
                    aria-label={`Select all ${col.label}`}
                  />
                  <div className={cn("h-2.5 w-2.5 rounded-full", col.colorClass)} />
                  <span className="text-sm font-semibold">{col.label}</span>
                  <span className="ml-auto text-xs text-muted-foreground bg-secondary rounded-full px-2 py-0.5">
                    {colInsights.length}
                  </span>
                </div>
                <div className="space-y-3">
                  {colInsights.map((insight) => (
                    <InsightCard
                      key={insight.id}
                      insight={insight}
                      selected={selectedIds.has(insight.id)}
                      onSelect={(checked) => toggleSelect(insight.id, checked)}
                      onClick={() => navigate(`/insights/${insight.id}`)}
                    />
                  ))}
                  {colInsights.length === 0 && (
                    <p className="text-xs text-muted-foreground px-1">No insights</p>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      ) : (
        /* ── List view ── */
        <div className="rounded-lg border bg-card shadow-sm overflow-hidden">
          <table className="w-full">
            <thead>
              <tr className="border-b bg-secondary/50">
                <th className="px-4 py-3 w-10">
                  <Checkbox
                    checked={insights.length > 0 && insights.every((i) => selectedIds.has(i.id))}
                    onCheckedChange={() => toggleAll(insights)}
                    aria-label="Select all"
                  />
                </th>
                <th className="text-left text-xs font-semibold text-muted-foreground px-4 py-3">Severity</th>
                <th className="text-left text-xs font-semibold text-muted-foreground px-4 py-3">Title</th>
                <th className="text-left text-xs font-semibold text-muted-foreground px-4 py-3">Team</th>
                <th className="text-left text-xs font-semibold text-muted-foreground px-4 py-3">Impact</th>
                <th className="text-left text-xs font-semibold text-muted-foreground px-4 py-3">Status</th>
                <th className="text-left text-xs font-semibold text-muted-foreground px-4 py-3">Detected</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {insights.map((insight) => (
                <tr
                  key={insight.id}
                  className={cn(
                    "hover:bg-secondary/30 cursor-pointer transition-colors",
                    selectedIds.has(insight.id) && "bg-primary/5"
                  )}
                >
                  <td className="px-4 py-3" onClick={(e) => e.stopPropagation()}>
                    <Checkbox
                      checked={selectedIds.has(insight.id)}
                      onCheckedChange={(v) => toggleSelect(insight.id, !!v)}
                    />
                  </td>
                  <td className="px-4 py-3" onClick={() => navigate(`/insights/${insight.id}`)}>
                    <SeverityBadge severity={insight.severity} />
                  </td>
                  <td className="px-4 py-3 text-sm font-medium" onClick={() => navigate(`/insights/${insight.id}`)}>
                    {insight.title}
                  </td>
                  <td className="px-4 py-3" onClick={() => navigate(`/insights/${insight.id}`)}>
                    <TeamBadge team={insight.target_team} />
                  </td>
                  <td className="px-4 py-3 font-mono text-sm" onClick={() => navigate(`/insights/${insight.id}`)}>
                    {insight.impact_score}/10
                  </td>
                  <td className="px-4 py-3" onClick={() => navigate(`/insights/${insight.id}`)}>
                    <StatusBadge status={insight.status} />
                  </td>
                  <td className="px-4 py-3 text-xs text-muted-foreground" onClick={() => navigate(`/insights/${insight.id}`)}>
                    {formatDistanceToNow(new Date(insight.detected_at), { addSuffix: true })}
                  </td>
                </tr>
              ))}
              {insights.length === 0 && (
                <tr>
                  <td colSpan={7} className="px-4 py-8 text-center text-sm text-muted-foreground">
                    No insights found
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}

      {/* ── Floating batch action bar ── */}
      {selectedIds.size > 0 && (
        <BatchActionBar
          count={selectedIds.size}
          isPending={isPending}
          onChangeStatus={(status) => bulkStatusMutation.mutate({ ids: selectedArr, status })}
          onDismiss={() => setDismissOpen(true)}
          onClear={() => setSelectedIds(new Set())}
        />
      )}

      {/* ── Dismiss dialog ── */}
      <Dialog open={dismissOpen} onOpenChange={setDismissOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Dismiss {selectedIds.size} insight{selectedIds.size !== 1 ? "s" : ""}</DialogTitle>
          </DialogHeader>
          <p className="text-sm text-muted-foreground">
            Provide a reason for dismissing {selectedIds.size > 1 ? "these insights" : "this insight"}. This will be recorded for future reference.
          </p>
          <Textarea
            placeholder="e.g. Already addressed by another initiative, out of scope…"
            value={dismissReason}
            onChange={(e) => setDismissReason(e.target.value)}
            className="min-h-[100px]"
          />
          <DialogFooter>
            <Button variant="outline" onClick={() => setDismissOpen(false)}>
              Cancel
            </Button>
            <Button
              variant="destructive"
              disabled={!dismissReason.trim() || isPending}
              onClick={() => bulkDismissMutation.mutate({ ids: selectedArr, reason: dismissReason.trim() })}
            >
              {isPending ? "Dismissing…" : `Dismiss ${selectedIds.size > 1 ? "All" : "Insight"}`}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </AppLayout>
  );
};

export default InsightsPage;
