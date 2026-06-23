import { useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { supabase } from "@/integrations/supabase/client";
import { useWorkspaceId } from "@/hooks/use-workspace";
import { useAuth } from "@/contexts/AuthContext";

import { AppLayout } from "@/components/layout/AppLayout";
import { SeverityBadge, TeamBadge, StatusBadge } from "@/components/shared/Badges";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Textarea } from "@/components/ui/textarea";
import { Input } from "@/components/ui/input";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog";
import { toast } from "sonner";
import { ArrowLeft, Play, X, ChevronRight, Ban, Zap, Loader2, Gauge, CheckCircle2 } from "lucide-react";
import { formatDistanceToNow } from "date-fns";
import { cn } from "@/lib/utils";
import { logEvent } from "@/lib/events";
import type { Insight, Signal, SuggestedAction, ActionTaken, InsightStatus } from "@/lib/types";

function normalizeInsight(row: Record<string, unknown>): Insight {
  return {
    ...row,
    suggested_actions: Array.isArray(row.suggested_actions) ? (row.suggested_actions as SuggestedAction[]) : [],
    actions_taken: Array.isArray(row.actions_taken) ? (row.actions_taken as ActionTaken[]) : [],
    signal_ids: Array.isArray(row.signal_ids) ? (row.signal_ids as number[]) : [],
  } as Insight;
}

function normalizeSignal(row: Record<string, unknown>): Signal {
  return {
    ...row,
    tags: Array.isArray(row.tags) ? (row.tags as string[]) : [],
    metadata: (row.metadata as Record<string, unknown>) ?? {},
    is_anomaly: row.is_anomaly ?? false,
    contact_count: (row.contact_count as number) ?? 1,
  } as Signal;
}

const InsightDetail = () => {
  const { id } = useParams();
  const workspaceId = useWorkspaceId();
  const { user } = useAuth();
  const [dismissOpen, setDismissOpen] = useState(false);
  const [dismissReason, setDismissReason] = useState("");
  const [measureManualOpen, setMeasureManualOpen] = useState(false);
  const [manualScore, setManualScore] = useState("70");
  const [manualSummary, setManualSummary] = useState("");
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const { data: insight, isLoading: insightLoading } = useQuery({
    queryKey: ["insight", id, workspaceId],
    queryFn: async () => {
      const { data, error } = await supabase
        .from("insights")
        .select("*")
        .eq("id", Number(id))
        .eq("workspace_id", workspaceId!)
        .maybeSingle();
      if (error) throw error;
      return data ? normalizeInsight(data as Record<string, unknown>) : null;
    },
    enabled: !!id && !!workspaceId,
  });

  const { data: relatedSignals = [] } = useQuery({
    queryKey: ["insight-signals", insight?.signal_ids],
    queryFn: async () => {
      if (!insight?.signal_ids?.length) return [];
      const { data, error } = await supabase
        .from("signals")
        .select("*")
        .in("id", insight.signal_ids);
      if (error) throw error;
      return (data as Record<string, unknown>[]).map(normalizeSignal);
    },
    enabled: !!insight?.signal_ids?.length,
  });

  const statusMutation = useMutation({
    mutationFn: async (newStatus: InsightStatus) => {
      const { error } = await supabase
        .from("insights")
        .update({ status: newStatus, status_changed_at: new Date().toISOString() })
        .eq("id", Number(id))
        .eq("workspace_id", workspaceId!);
      if (error) throw error;
    },
    onSuccess: (_data, newStatus) => {
      queryClient.invalidateQueries({ queryKey: ["insight", id] });
      queryClient.invalidateQueries({ queryKey: ["insights"] });
      queryClient.invalidateQueries({ queryKey: ["insights-dash"] });
      if (workspaceId && insight?.detected_at) {
        logEvent(workspaceId, "insight_status_advanced", {
          entity: "insight",
          entity_id: id,
          duration_ms: Date.now() - new Date(insight.detected_at).getTime(),
          metadata: { to: newStatus },
        });
      }
      toast.success(`Status updated to "${newStatus.replace(/_/g, " ")}"`);
    },
    onError: (err: Error) => {
      toast.error("Failed to update status", { description: err.message });
    },
  });

  const dismissMutation = useMutation({
    mutationFn: async (reason: string) => {
      const { error } = await supabase
        .from("insights")
        .update({ status: "dismissed", dismissed_reason: reason, status_changed_at: new Date().toISOString() })
        .eq("id", Number(id))
        .eq("workspace_id", workspaceId!);
      if (error) throw error;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["insight", id] });
      queryClient.invalidateQueries({ queryKey: ["insights"] });
      queryClient.invalidateQueries({ queryKey: ["insights-dash"] });
      setDismissOpen(false);
      setDismissReason("");
      toast.success("Insight dismissed");
    },
    onError: (err: Error) => {
      toast.error("Failed to dismiss insight", { description: err.message });
    },
  });

  const evaluateRulesMutation = useMutation({
    mutationFn: async () => {
      const { data, error } = await supabase.functions.invoke("evaluate-rules", {
        body: { insight_id: Number(id) },
      });
      if (error) throw error;
      if (data?.error) throw new Error(data.error);
      return data as {
        matched: number;
        actions: number;
        auto_executed: number;
        pending_approval: number;
        status_advanced: string | null;
        rules: { id: number; name: string; auto_execute: boolean }[];
      };
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ["insight", id] });
      queryClient.invalidateQueries({ queryKey: ["insights"] });
      queryClient.invalidateQueries({ queryKey: ["actions"] });
      if (data.matched === 0) {
        toast("No rules matched this insight");
      } else {
        const names = data.rules.map((r) => r.name).join(", ");
        toast.success(
          `${data.matched} rule(s) matched, ${data.actions} action(s) created`,
          { description: names },
        );
      }
    },
    onError: (err: Error) => {
      toast.error("Rule evaluation failed", { description: err.message });
    },
  });

  const measureMutation = useMutation({
    mutationFn: async () => {
      const { data, error } = await supabase.functions.invoke("measure-outcomes", {
        body: { insight_id: Number(id) },
      });
      if (error) throw error;
      if (data?.error) throw new Error(data.error);
      return data as { measured: number; results: { resolution_score: number; summary: string }[] };
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ["insight", id] });
      queryClient.invalidateQueries({ queryKey: ["insights"] });
      queryClient.invalidateQueries({ queryKey: ["insights-dash"] });
      const r = data.results?.[0];
      if (workspaceId) logEvent(workspaceId, "outcome_measured", { entity: "insight", entity_id: id, metadata: { mode: "auto", resolution_score: r?.resolution_score } });
      toast.success(r ? `Outcome measured — ${(r.resolution_score * 100).toFixed(0)}% resolution` : "Measurement complete");
    },
    onError: (err: Error) => toast.error("Measurement failed", { description: err.message }),
  });

  const manualResolveMutation = useMutation({
    mutationFn: async () => {
      const score = Math.max(0, Math.min(100, Number(manualScore) || 0)) / 100;
      const now = new Date().toISOString();
      const { error } = await supabase
        .from("insights")
        .update({
          resolution_score: score,
          resolution_summary: manualSummary.trim() || "Outcome recorded manually.",
          measured_at: now,
          status: "resolved",
          status_changed_at: now,
          resolved_at: now,
        })
        .eq("id", Number(id))
        .eq("workspace_id", workspaceId!);
      if (error) throw error;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["insight", id] });
      queryClient.invalidateQueries({ queryKey: ["insights"] });
      queryClient.invalidateQueries({ queryKey: ["insights-dash"] });
      setMeasureManualOpen(false);
      if (workspaceId) logEvent(workspaceId, "outcome_measured", { entity: "insight", entity_id: id, metadata: { mode: "manual" } });
      toast.success("Outcome recorded");
    },
    onError: (err: Error) => toast.error("Failed to record outcome", { description: err.message }),
  });

  const ACTION_TYPE_MAP: Record<string, string> = {
    create_ticket: "ticket_created",
    notify: "notification_sent",
    draft_email: "email_drafted",
    create_segment: "segment_created",
  };

  const executeSuggested = useMutation({
    mutationFn: async (action: SuggestedAction) => {
      const actionType = ACTION_TYPE_MAP[action.type] ?? action.type;
      const { error: e1 } = await supabase.from("actions_log").insert({
        workspace_id: workspaceId!,
        insight_id: Number(id),
        action_type: actionType,
        action_params: (action.params ?? {}) as never,
        action_result: { manual: true } as never,
        executed_by: `user:${user?.id ?? ""}`.slice(0, 50),
        status: "completed",
      });
      if (e1) throw e1;
      const newTaken = [...(insight?.actions_taken ?? []), { type: actionType, at: new Date().toISOString() }];
      const newSuggested = (insight?.suggested_actions ?? []).filter((a) => a !== action);
      const { error: e2 } = await supabase
        .from("insights")
        .update({ actions_taken: newTaken as never, suggested_actions: newSuggested as never })
        .eq("id", Number(id))
        .eq("workspace_id", workspaceId!);
      if (e2) throw e2;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["insight", id] });
      queryClient.invalidateQueries({ queryKey: ["actions"] });
      if (workspaceId) logEvent(workspaceId, "action_executed", { entity: "insight", entity_id: id, user_id: user?.id });
      toast.success("Action executed and logged");
    },
    onError: (err: Error) => toast.error("Failed to execute action", { description: err.message }),
  });

  const dismissSuggested = useMutation({
    mutationFn: async (action: SuggestedAction) => {
      const newSuggested = (insight?.suggested_actions ?? []).filter((a) => a !== action);
      const { error } = await supabase
        .from("insights")
        .update({ suggested_actions: newSuggested as never })
        .eq("id", Number(id))
        .eq("workspace_id", workspaceId!);
      if (error) throw error;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["insight", id] });
      toast("Suggestion dismissed");
    },
    onError: (err: Error) => toast.error("Failed to dismiss", { description: err.message }),
  });

  const qualSignals = relatedSignals.filter((s) => s.signal_type === "qualitative");
  const quantSignals = relatedSignals.filter((s) => s.signal_type === "quantitative");

  if (insightLoading) {
    return (
      <AppLayout title="Insight Detail">
        <Skeleton className="h-5 w-32 mb-4" />
        <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
          <div className="lg:col-span-3 space-y-6">
            <Skeleton className="h-48 w-full rounded-lg" />
            <Skeleton className="h-40 w-full rounded-lg" />
          </div>
          <div className="lg:col-span-2 space-y-6">
            <Skeleton className="h-64 w-full rounded-lg" />
          </div>
        </div>
      </AppLayout>
    );
  }

  if (!insight) {
    return (
      <AppLayout title="Insight Not Found">
        <div className="text-center py-20">
          <p className="text-muted-foreground mb-2">No insight found with ID #{id}.</p>
          <p className="text-sm text-muted-foreground">It may have been deleted or you may not have access.</p>
          <Button variant="outline" onClick={() => navigate("/insights")} className="mt-4">Back to Insights</Button>
        </div>
      </AppLayout>
    );
  }

  const statusSteps: { status: InsightStatus; label: string }[] = [
    { status: "new", label: "New" },
    { status: "reviewing", label: "Reviewing" },
    { status: "action_taken", label: "Action Taken" },
    { status: "resolved", label: "Resolved" },
  ];

  const currentStepIndex = statusSteps.findIndex(
    (s) => s.status === insight.status || (s.status === "action_taken" && insight.status === "action_planned")
  );

  return (
    <AppLayout title="Insight Detail">
      <button onClick={() => navigate("/insights")} className="flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground mb-4 transition-colors">
        <ArrowLeft className="h-4 w-4" /> Back to Insights
      </button>

      {/* Status stepper */}
      <div className="rounded-lg border bg-card p-4 shadow-sm mb-6 flex items-center gap-2 overflow-x-auto">
        {statusSteps.map((step, i) => {
          const isPast = i < currentStepIndex;
          const isCurrent = i === currentStepIndex;
          const isNext = i === currentStepIndex + 1;
          const isDisabled = statusMutation.isPending || (!isNext && !isCurrent);
          return (
            <div key={step.status} className="flex items-center gap-2 shrink-0">
              <button
                onClick={() => !isDisabled && statusMutation.mutate(step.status)}
                disabled={isDisabled}
                className={cn(
                  "flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all border",
                  isCurrent && "bg-primary text-primary-foreground border-primary",
                  isPast && "bg-success/10 text-success border-success/30 cursor-default",
                  isNext && "border-primary/40 text-primary hover:bg-primary/10 cursor-pointer",
                  !isCurrent && !isPast && !isNext && "border-border text-muted-foreground cursor-not-allowed opacity-50",
                )}
              >
                {isPast && <span className="text-success">✓</span>}
                {step.label}
              </button>
              {i < statusSteps.length - 1 && <ChevronRight className="h-4 w-4 text-muted-foreground shrink-0" />}
            </div>
          );
        })}
        {["dismissed", "escalated", "measuring"].includes(insight.status) ? (
          <span className="ml-auto text-xs text-muted-foreground capitalize italic">{insight.status}</span>
        ) : (
          <button
            onClick={() => setDismissOpen(true)}
            disabled={statusMutation.isPending || dismissMutation.isPending}
            className="ml-auto flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium border border-destructive/30 text-destructive hover:bg-destructive/10 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <Ban className="h-3.5 w-3.5" /> Dismiss
          </button>
        )}
      </div>

      {/* Dismiss dialog */}
      <Dialog open={dismissOpen} onOpenChange={setDismissOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Dismiss Insight</DialogTitle>
          </DialogHeader>
          <p className="text-sm text-muted-foreground">Provide a reason for dismissing this insight. This will be recorded for future reference.</p>
          <Textarea
            placeholder="e.g. Already addressed by another initiative, duplicate signal, out of scope…"
            value={dismissReason}
            onChange={(e) => setDismissReason(e.target.value)}
            className="min-h-[100px]"
          />
          <DialogFooter>
            <Button variant="outline" onClick={() => setDismissOpen(false)}>Cancel</Button>
            <Button
              variant="destructive"
              disabled={!dismissReason.trim() || dismissMutation.isPending}
              onClick={() => dismissMutation.mutate(dismissReason.trim())}
            >
              {dismissMutation.isPending ? "Dismissing…" : "Dismiss Insight"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Record outcome manually */}
      <Dialog open={measureManualOpen} onOpenChange={setMeasureManualOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Record outcome</DialogTitle>
          </DialogHeader>
          <p className="text-sm text-muted-foreground">Manually record the measured outcome and close the loop.</p>
          <div className="space-y-1.5">
            <label htmlFor="manual-score" className="text-xs font-medium">Resolution score (0–100)</label>
            <Input id="manual-score" type="number" min={0} max={100} value={manualScore} onChange={(e) => setManualScore(e.target.value)} />
          </div>
          <Textarea
            placeholder="What changed? e.g. complaint volume dropped 60% after the fix."
            value={manualSummary}
            onChange={(e) => setManualSummary(e.target.value)}
            className="min-h-[90px]"
          />
          <DialogFooter>
            <Button variant="outline" onClick={() => setMeasureManualOpen(false)}>Cancel</Button>
            <Button disabled={manualResolveMutation.isPending} onClick={() => manualResolveMutation.mutate()}>
              {manualResolveMutation.isPending ? "Saving…" : "Record outcome"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
        {/* Left column - 60% */}
        <div className="lg:col-span-3 space-y-6">
          {/* Header */}
          <div>
            <div className="flex items-center gap-2 mb-3">
              <SeverityBadge severity={insight.severity} />
              <TeamBadge team={insight.target_team} />
              <StatusBadge status={insight.status} />
            </div>
            <h2 className="text-2xl font-bold mb-3">{insight.title}</h2>
            <blockquote className="border-l-4 border-primary bg-primary/5 rounded-r-lg px-5 py-4 text-sm text-foreground leading-relaxed">
              {insight.summary}
            </blockquote>
            {insight.status === "dismissed" && insight.dismissed_reason && (
              <div className="mt-3 flex items-start gap-2 rounded-lg border border-destructive/20 bg-destructive/5 px-4 py-3 text-sm text-destructive">
                <Ban className="h-4 w-4 mt-0.5 shrink-0" />
                <span><span className="font-semibold">Dismissed:</span> {insight.dismissed_reason}</span>
              </div>
            )}
          </div>

          {/* Scores */}
          <div className="flex gap-6">
            <div className="text-center">
              <div className="text-2xl font-bold font-mono">{insight.impact_score}</div>
              <div className="text-xs text-muted-foreground">Impact</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold font-mono">{(insight.confidence * 100).toFixed(0)}%</div>
              <div className="text-xs text-muted-foreground">Confidence</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold font-mono">{insight.affected_contacts}</div>
              <div className="text-xs text-muted-foreground">Contacts</div>
            </div>
            {insight.estimated_revenue_impact && (
              <div className="text-center">
                <div className="text-2xl font-bold font-mono text-destructive">${(insight.estimated_revenue_impact / 1000).toFixed(0)}K</div>
                <div className="text-xs text-muted-foreground">Revenue Impact</div>
              </div>
            )}
          </div>

          {/* Correlated Signals */}
          <div className="rounded-lg border bg-card p-6 shadow-sm">
            <h3 className="text-sm font-semibold mb-4">Correlated Signals</h3>
            <div className="grid grid-cols-2 gap-6">
              <div className="space-y-3">
                <h4 className="text-xs font-semibold text-muted-foreground uppercase">Qualitative</h4>
                {qualSignals.length === 0 ? (
                  <p className="text-xs text-muted-foreground italic">No qualitative signals</p>
                ) : (
                  qualSignals.map((s) => (
                    <div key={s.id} className="rounded-lg bg-primary/5 border border-primary/20 p-3">
                      <div className="flex items-center gap-1.5 mb-1">
                        <span>💬</span>
                        <span className="text-xs text-muted-foreground">{s.source.replace(/_/g, " ")}</span>
                        <span className="text-xs text-muted-foreground ml-auto">{formatDistanceToNow(new Date(s.recorded_at), { addSuffix: true })}</span>
                      </div>
                      <p className="text-sm italic">"{s.text_content}"</p>
                    </div>
                  ))
                )}
              </div>
              <div className="space-y-3">
                <h4 className="text-xs font-semibold text-muted-foreground uppercase">Quantitative</h4>
                {quantSignals.length === 0 ? (
                  <p className="text-xs text-muted-foreground italic">No quantitative signals</p>
                ) : (
                  quantSignals.map((s) => (
                    <div key={s.id} className="rounded-lg bg-sentiment-mixed/5 border border-sentiment-mixed/20 p-3">
                      <div className="flex items-center gap-1.5 mb-1">
                        <span>📊</span>
                        <span className="text-xs text-muted-foreground">{s.entity_name}</span>
                      </div>
                      <div className="text-sm font-mono font-bold">
                        {s.metric_name}: {s.metric_value}
                        {s.metric_delta_pct !== undefined && s.metric_delta_pct !== null && (
                          <span className={s.metric_delta_pct > 0 ? " text-destructive" : " text-success"}>
                            {" "}({s.metric_delta_pct > 0 ? "↑" : "↓"}{Math.abs(s.metric_delta_pct)}%)
                          </span>
                        )}
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>
            <div className="mt-4 flex items-center gap-2">
              <span className="text-xs text-muted-foreground">Confidence:</span>
              <div className="flex-1 h-2 bg-secondary rounded-full overflow-hidden">
                <div className="h-full bg-primary rounded-full transition-all" style={{ width: `${insight.confidence * 100}%` }} />
              </div>
              <span className="text-xs font-mono font-bold">{(insight.confidence * 100).toFixed(0)}%</span>
            </div>
          </div>

          {/* Timeline */}
          <div className="rounded-lg border bg-card p-6 shadow-sm">
            <h3 className="text-sm font-semibold mb-4">Timeline</h3>
            <div className="space-y-0">
              <TimelineItem
                dot="filled"
                title="Detected"
                time={new Date(insight.detected_at).toLocaleString()}
                description={`${insight.qual_signal_count} qualitative + ${insight.quant_signal_count} quantitative signals correlated`}
              />
              <TimelineItem
                dot="filled"
                title={`Routed to ${insight.target_team}`}
                time={new Date(new Date(insight.detected_at).getTime() + 60000).toLocaleString()}
              />
              {insight.actions_taken.map((a, i) => (
                <TimelineItem
                  key={i}
                  dot="filled"
                  title={a.type.replace(/_/g, " ")}
                  time={new Date(a.at).toLocaleString()}
                />
              ))}
              {insight.measurement_due_at && !insight.resolution_score && (
                <TimelineItem
                  dot="empty"
                  title="Impact measurement due"
                  time={new Date(insight.measurement_due_at).toLocaleString()}
                />
              )}
              {insight.resolved_at && (
                <TimelineItem
                  dot="filled"
                  title="Resolved"
                  time={new Date(insight.resolved_at).toLocaleString()}
                />
              )}
            </div>
          </div>
        </div>

        {/* Right column - Actions */}
        <div className="lg:col-span-2 space-y-6">
          {/* Run Rules */}
          {!["dismissed", "resolved"].includes(insight.status) && (
            <Button
              className="w-full"
              variant="outline"
              disabled={evaluateRulesMutation.isPending}
              onClick={() => evaluateRulesMutation.mutate()}
            >
              {evaluateRulesMutation.isPending ? (
                <><Loader2 className="h-4 w-4 animate-spin mr-2" /> Evaluating rules...</>
              ) : (
                <><Zap className="h-4 w-4 mr-2" /> Run Rules</>
              )}
            </Button>
          )}

          {/* Suggested Actions */}
          <div className="rounded-lg border bg-card p-6 shadow-sm">
            <h3 className="text-sm font-semibold mb-4">Suggested Actions</h3>
            {insight.suggested_actions.length === 0 ? (
              <p className="text-xs text-muted-foreground italic">No suggested actions</p>
            ) : (
              <div className="space-y-3">
                {insight.suggested_actions.map((action, i) => (
                  <div key={i} className="rounded-lg border p-4">
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-sm font-semibold">{action.title}</span>
                      <span className="text-xs bg-secondary rounded-full px-2 py-0.5">P{action.priority}</span>
                    </div>
                    <p className="text-xs text-muted-foreground mb-3">{action.description}</p>
                    <div className="flex gap-2">
                      <Button size="sm" className="flex-1" disabled={executeSuggested.isPending}
                        onClick={() => executeSuggested.mutate(action)}>
                        <Play className="h-3 w-3 mr-1" />Execute
                      </Button>
                      <Button size="sm" variant="ghost" disabled={dismissSuggested.isPending}
                        onClick={() => dismissSuggested.mutate(action)}>
                        <X className="h-3 w-3" />
                      </Button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Actions Taken */}
          {insight.actions_taken.length > 0 && (
            <div className="rounded-lg border bg-card p-6 shadow-sm">
              <h3 className="text-sm font-semibold mb-4">Actions Taken</h3>
              <div className="space-y-3">
                {insight.actions_taken.map((a, i) => (
                  <div key={i} className="flex items-center gap-3 text-sm">
                    <span className="text-success">✅</span>
                    <span className="capitalize">{a.type.replace(/_/g, " ")}</span>
                    <span className="text-xs text-muted-foreground ml-auto">{formatDistanceToNow(new Date(a.at), { addSuffix: true })}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Close the loop — measurement pending */}
          {insight.measurement_due_at &&
            (insight.resolution_score === undefined || insight.resolution_score === null) &&
            insight.status !== "dismissed" && (
            <div className="rounded-lg border bg-card p-6 shadow-sm">
              <h3 className="text-sm font-semibold mb-3 flex items-center gap-1.5"><Gauge className="h-4 w-4" /> Close the loop</h3>
              <div className="space-y-1.5 text-xs text-muted-foreground mb-4">
                <div>Measuring: <span className="font-medium text-foreground">{insight.outcome_metric ?? "—"}</span></div>
                <div>Baseline: <span className="font-mono text-foreground">{insight.outcome_baseline ?? "—"}</span></div>
                <div>Due: <span className="text-foreground">{new Date(insight.measurement_due_at).toLocaleDateString()}</span></div>
              </div>
              <div className="flex gap-2">
                <Button size="sm" className="flex-1" disabled={measureMutation.isPending} onClick={() => measureMutation.mutate()}>
                  {measureMutation.isPending ? <><Loader2 className="h-3 w-3 mr-1 animate-spin" />Measuring…</> : <><Gauge className="h-3 w-3 mr-1" />Measure now</>}
                </Button>
                <Button size="sm" variant="outline" onClick={() => setMeasureManualOpen(true)}>Record manually</Button>
              </div>
            </div>
          )}

          {/* Impact Measurement (after measuring) */}
          {insight.resolution_score !== undefined && insight.resolution_score !== null && (
            <div className="rounded-lg border bg-success/5 border-success/20 p-6 shadow-sm">
              <h3 className="text-sm font-semibold mb-4">Impact Measurement</h3>
              <div className="space-y-2">
                <div className="flex items-center gap-2">
                  <span className="text-xs text-muted-foreground">Resolution:</span>
                  <div className="flex-1 h-2 bg-secondary rounded-full overflow-hidden">
                    <div className="h-full bg-success rounded-full" style={{ width: `${insight.resolution_score * 100}%` }} />
                  </div>
                  <span className="text-xs font-mono font-bold">{(insight.resolution_score * 100).toFixed(0)}%</span>
                </div>
                {insight.outcome_baseline !== undefined && insight.outcome_baseline !== null && (
                  <div className="text-xs text-muted-foreground">
                    {insight.outcome_metric}: baseline <span className="font-mono">{insight.outcome_baseline}</span> → measured{" "}
                    <span className="font-mono">{insight.outcome_measured ?? "—"}</span>
                  </div>
                )}
                {insight.resolution_summary && (
                  <p className="text-xs text-muted-foreground mt-2">{insight.resolution_summary}</p>
                )}
                <div className="flex flex-wrap gap-2 pt-2">
                  <ClosureChip label="Operational" done={insight.actions_taken.length > 0} />
                  <ClosureChip label="Customer" done={insight.actions_taken.some((a) => a.type.includes("email") || a.type.includes("notification"))} />
                  <ClosureChip label="Outcome" done={insight.resolution_score >= 0.5} />
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </AppLayout>
  );
};

function ClosureChip({ label, done }: { label: string; done: boolean }) {
  return (
    <span className={cn("inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs", done ? "bg-success/15 text-success" : "bg-secondary text-muted-foreground")}>
      {done ? <CheckCircle2 className="h-3 w-3" /> : <span className="h-3 w-3 rounded-full border border-current inline-block" />}
      {label}
    </span>
  );
}

function TimelineItem({ dot, title, time, description }: { dot: "filled" | "empty"; title: string; time: string; description?: string }) {
  return (
    <div className="flex gap-3 pb-4">
      <div className="flex flex-col items-center">
        <div className={`h-3 w-3 rounded-full border-2 ${dot === "filled" ? "bg-primary border-primary" : "bg-card border-muted-foreground"}`} />
        <div className="w-0.5 flex-1 bg-border mt-1" />
      </div>
      <div className="pb-2">
        <div className="text-sm font-medium">{title}</div>
        <div className="text-xs text-muted-foreground">{time}</div>
        {description && <div className="text-xs text-muted-foreground mt-0.5">{description}</div>}
      </div>
    </div>
  );
}

export default InsightDetail;
