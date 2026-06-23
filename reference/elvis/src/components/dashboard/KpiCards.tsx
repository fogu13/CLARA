import { cn } from "@/lib/utils";
import type { DashboardSummary } from "@/lib/types";
import { TrendingUp, TrendingDown, Lightbulb, Zap, Target } from "lucide-react";

interface KpiCardProps {
  label: string;
  value: string | number;
  subtitle: string;
  trend?: number;
  icon: React.ReactNode;
  accentClass?: string;
}

function KpiCard({ label, value, subtitle, trend, icon, accentClass }: KpiCardProps) {
  const isPositive = trend !== undefined && trend > 0;
  const isZero = trend !== undefined && trend === 0;
  return (
    <div className="rounded-lg border bg-card p-6 shadow-sm animate-fade-in">
      <div className="flex items-center justify-between mb-3">
        <span className="text-sm font-medium text-muted-foreground">{label}</span>
        <div className={cn("h-9 w-9 rounded-lg flex items-center justify-center", accentClass || "bg-primary/10")}>
          {icon}
        </div>
      </div>
      <div className="text-3xl font-bold font-mono tracking-tight mb-1">{value}</div>
      <div className="flex items-center gap-1.5 text-xs">
        {trend !== undefined && (
          <span className={cn("flex items-center gap-0.5 font-medium", isZero ? "text-muted-foreground" : isPositive ? "text-success" : "text-destructive")}>
            {!isZero && (isPositive ? <TrendingUp className="h-3 w-3" /> : <TrendingDown className="h-3 w-3" />)}
            {isPositive ? "+" : ""}{trend}%
          </span>
        )}
        <span className="text-muted-foreground">{subtitle}</span>
      </div>
    </div>
  );
}

export function KpiCards({ data }: { data: DashboardSummary }) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
      <KpiCard
        label="Signals (7d)"
        value={data.total_signals_7d}
        subtitle="vs last week"
        trend={data.signals_change_pct}
        icon={<Zap className="h-4 w-4 text-primary" />}
        accentClass="bg-primary/10"
      />
      <KpiCard
        label="Open Insights"
        value={data.open_insights}
        subtitle={`${data.critical_insights} critical, ${data.high_insights} high`}
        icon={<Lightbulb className="h-4 w-4 text-warning" />}
        accentClass="bg-warning/10"
      />
      <KpiCard
        label="Actions Taken (7d)"
        value={data.actions_taken_7d}
        subtitle={`${data.auto_executed_pct}% auto-executed`}
        icon={<Zap className="h-4 w-4 text-success" />}
        accentClass="bg-success/10"
      />
      <KpiCard
        label="Resolution Rate"
        value={`${data.resolution_rate}%`}
        subtitle="vs last month"
        trend={data.resolution_change_pct}
        icon={<Target className="h-4 w-4 text-success" />}
        accentClass="bg-success/10"
      />
    </div>
  );
}
