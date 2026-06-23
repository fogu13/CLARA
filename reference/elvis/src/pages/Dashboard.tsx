import { useQuery } from "@tanstack/react-query";
import { supabase } from "@/integrations/supabase/client";
import { useWorkspaceId } from "@/hooks/use-workspace";
import { AppLayout } from "@/components/layout/AppLayout";
import { KpiCards } from "@/components/dashboard/KpiCards";
import { SignalTrendChart } from "@/components/dashboard/SignalTrendChart";
import { TopThemesChart } from "@/components/dashboard/TopThemesChart";
import { InsightFunnel } from "@/components/dashboard/InsightFunnel";
import { TeamRoutingPie } from "@/components/dashboard/TeamRoutingPie";
import { RecentInsights } from "@/components/dashboard/RecentInsights";
import { SourceHealthGrid } from "@/components/dashboard/SourceHealthGrid";
import { Skeleton } from "@/components/ui/skeleton";
import type { DashboardSummary, SignalTrendPoint, ThemeData, FunnelStage, TeamRouting, Insight, SignalSourceConfig } from "@/lib/types";
import { subDays, format, startOfDay } from "date-fns";

const Dashboard = () => {
  const workspaceId = useWorkspaceId();

  // ── Signals (last 7d for KPIs + last 30d for trend) ──────────────────────
  const { data: signals30d = [] } = useQuery({
    queryKey: ["signals-30d", workspaceId],
    queryFn: async () => {
      const since = subDays(new Date(), 30).toISOString();
      const { data, error } = await supabase
        .from("signals")
        .select("recorded_at,signal_type,ingested_at")
        .eq("workspace_id", workspaceId!)
        .gte("recorded_at", since)
        .order("recorded_at", { ascending: true });
      if (error) throw error;
      return data as { recorded_at: string; signal_type: string; ingested_at: string }[];
    },
    enabled: !!workspaceId,
  });

  const { data: signals14d = [] } = useQuery({
    queryKey: ["signals-14d", workspaceId],
    queryFn: async () => {
      const since = subDays(new Date(), 14).toISOString();
      const { data, error } = await supabase
        .from("signals")
        .select("recorded_at,signal_type")
        .eq("workspace_id", workspaceId!)
        .gte("recorded_at", since);
      if (error) throw error;
      return data as { recorded_at: string; signal_type: string }[];
    },
    enabled: !!workspaceId,
  });

  // ── Insights ──────────────────────────────────────────────────────────────
  const { data: insights = [], isLoading: insightsLoading } = useQuery({
    queryKey: ["insights-dash", workspaceId],
    queryFn: async () => {
      const { data, error } = await supabase
        .from("insights")
        .select("*")
        .eq("workspace_id", workspaceId!)
        .order("detected_at", { ascending: false });
      if (error) throw error;
      return (data as Record<string, unknown>[]).map((row) => ({
        ...row,
        suggested_actions: Array.isArray(row.suggested_actions) ? row.suggested_actions : [],
        actions_taken: Array.isArray(row.actions_taken) ? row.actions_taken : [],
        signal_ids: Array.isArray(row.signal_ids) ? row.signal_ids : [],
      })) as Insight[];
    },
    enabled: !!workspaceId,
  });

  // ── Actions (last 7d) ─────────────────────────────────────────────────────
  const { data: actions7d = [] } = useQuery({
    queryKey: ["actions-7d", workspaceId],
    queryFn: async () => {
      const since = subDays(new Date(), 7).toISOString();
      const { data, error } = await supabase
        .from("actions_log")
        .select("status,executed_by")
        .eq("workspace_id", workspaceId!)
        .gte("executed_at", since);
      if (error) throw error;
      return data as { status: string; executed_by: string }[];
    },
    enabled: !!workspaceId,
  });

  // ── Sources ───────────────────────────────────────────────────────────────
  const { data: sources = [] } = useQuery({
    queryKey: ["sources-dash", workspaceId],
    queryFn: async () => {
      const { data, error } = await supabase
        .from("signal_sources")
        .select("*")
        .eq("workspace_id", workspaceId!)
        .order("created_at", { ascending: false });
      if (error) throw error;
      return (data as Record<string, unknown>[]).map((row) => ({
        ...row,
        config: (row.config as Record<string, unknown>) ?? {},
        enabled: row.enabled ?? true,
        sync_status: row.sync_status ?? "idle",
      })) as SignalSourceConfig[];
    },
    enabled: !!workspaceId,
  });

  // ── Derived KPIs ──────────────────────────────────────────────────────────
  const now = new Date();
  const signals7d = signals14d.filter((s) => new Date(s.recorded_at) >= subDays(now, 7));
  const signalsPrev7d = signals14d.filter((s) => {
    const d = new Date(s.recorded_at);
    return d >= subDays(now, 14) && d < subDays(now, 7);
  });
  const signalsChangePct = signalsPrev7d.length > 0
    ? Math.round(((signals7d.length - signalsPrev7d.length) / signalsPrev7d.length) * 100)
    : 0;

  const openInsights = insights.filter((i) => !["resolved", "dismissed"].includes(i.status));
  const criticalInsights = openInsights.filter((i) => i.severity === "critical").length;
  const highInsights = openInsights.filter((i) => i.severity === "high").length;

  const resolvedInsights = insights.filter((i) => i.status === "resolved").length;
  const resolutionRate = insights.length > 0 ? Math.round((resolvedInsights / insights.length) * 100) : 0;

  const autoActions = actions7d.filter((a) => a.executed_by === "system_auto").length;
  const autoPct = actions7d.length > 0 ? Math.round((autoActions / actions7d.length) * 100) : 0;

  const summary: DashboardSummary = {
    total_signals_7d: signals7d.length,
    signals_change_pct: signalsChangePct,
    open_insights: openInsights.length,
    critical_insights: criticalInsights,
    high_insights: highInsights,
    actions_taken_7d: actions7d.length,
    auto_executed_pct: autoPct,
    resolution_rate: resolutionRate,
    resolution_change_pct: 0,
  };

  // ── Signal trend (30d grouped by day) ─────────────────────────────────────
  const trendMap = new Map<string, { qualitative: number; quantitative: number }>();
  for (let i = 29; i >= 0; i--) {
    const day = format(startOfDay(subDays(now, i)), "yyyy-MM-dd");
    trendMap.set(day, { qualitative: 0, quantitative: 0 });
  }
  for (const s of signals30d) {
    const day = format(startOfDay(new Date(s.recorded_at)), "yyyy-MM-dd");
    const entry = trendMap.get(day);
    if (entry) {
      if (s.signal_type === "qualitative") entry.qualitative++;
      else entry.quantitative++;
    }
  }
  const trendData: SignalTrendPoint[] = Array.from(trendMap.entries()).map(([date, counts]) => ({ date, ...counts }));

  // ── Insight funnel ────────────────────────────────────────────────────────
  const funnelData: FunnelStage[] = [
    { stage: "new", count: insights.filter((i) => i.status === "new").length, label: "New" },
    { stage: "reviewing", count: insights.filter((i) => i.status === "reviewing").length, label: "Reviewing" },
    { stage: "action_taken", count: insights.filter((i) => i.status === "action_taken" || i.status === "action_planned").length, label: "Action Taken" },
    { stage: "resolved", count: resolvedInsights, label: "Resolved" },
  ];

  // ── Team routing ──────────────────────────────────────────────────────────
  const teamCounts: Record<string, number> = {};
  for (const ins of insights) {
    teamCounts[ins.target_team] = (teamCounts[ins.target_team] ?? 0) + 1;
  }
  const teamRouting: TeamRouting[] = Object.entries(teamCounts).map(([team, count]) => ({
    team: team as TeamRouting["team"],
    count,
  }));

  // ── Top themes from tags ──────────────────────────────────────────────────
  // We'll derive from insight categories as themes
  const categoryLabels: Record<string, string> = {
    content_clarity: "Content Clarity",
    product_issue: "Product Issue",
    churn_risk: "Churn Risk",
    campaign_performance: "Campaign Performance",
    ux_friction: "UX Friction",
    sentiment_shift: "Sentiment Shift",
    engagement_drop: "Engagement Drop",
    positive_trend: "Positive Trend",
    compliance_concern: "Compliance Concern",
  };
  const categoryCounts: Record<string, { count: number; sentiment: "positive" | "negative" | "neutral" | "mixed" }> = {};
  for (const ins of insights) {
    if (!categoryCounts[ins.category]) {
      const isPositive = ins.category === "positive_trend";
      const isNegative = ["churn_risk", "ux_friction", "engagement_drop", "compliance_concern"].includes(ins.category);
      categoryCounts[ins.category] = {
        count: 0,
        sentiment: isPositive ? "positive" : isNegative ? "negative" : "neutral",
      };
    }
    categoryCounts[ins.category].count++;
  }
  const themesData: ThemeData[] = Object.entries(categoryCounts)
    .map(([cat, { count, sentiment }]) => ({ name: categoryLabels[cat] ?? cat, count, sentiment }))
    .sort((a, b) => b.count - a.count)
    .slice(0, 6);

  const isLoading = !workspaceId || insightsLoading;

  return (
    <AppLayout title="Dashboard">
      <div className="space-y-6">
        {isLoading ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            {Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} className="h-32 rounded-lg" />)}
          </div>
        ) : (
          <KpiCards data={summary} />
        )}

        {isLoading ? (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} className="h-64 rounded-lg" />)}
          </div>
        ) : (
          <>
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <SignalTrendChart data={trendData} />
              <TopThemesChart data={themesData} />
              <InsightFunnel data={funnelData} />
              <TeamRoutingPie data={teamRouting} />
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              <div className="lg:col-span-2">
                <RecentInsights insights={insights.slice(0, 5)} />
              </div>
              <SourceHealthGrid sources={sources} />
            </div>
          </>
        )}
      </div>
    </AppLayout>
  );
};

export default Dashboard;
