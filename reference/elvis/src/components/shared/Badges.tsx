import { cn } from "@/lib/utils";
import type { Severity, Sentiment, TargetTeam, Urgency } from "@/lib/types";

// ====== Severity Badge ======
const severityStyles: Record<Severity, string> = {
  low: "bg-severity-low/15 text-severity-low",
  medium: "bg-severity-medium/15 text-severity-medium",
  high: "bg-severity-high/15 text-severity-high",
  critical: "bg-severity-critical/15 text-severity-critical",
};

export function SeverityBadge({ severity, className }: { severity: Severity; className?: string }) {
  return (
    <span className={cn("inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold uppercase tracking-wide", severityStyles[severity], className)}>
      {severity === "critical" && "🔴 "}{severity}
    </span>
  );
}

// ====== Sentiment Indicator ======
const sentimentStyles: Record<Sentiment, string> = {
  positive: "bg-sentiment-positive",
  neutral: "bg-sentiment-neutral",
  negative: "bg-sentiment-negative",
  mixed: "bg-sentiment-mixed",
};

export function SentimentIndicator({ sentiment, showLabel = true, className }: { sentiment: Sentiment; showLabel?: boolean; className?: string }) {
  return (
    <span className={cn("inline-flex items-center gap-1.5 text-xs", className)}>
      <span className={cn("h-2 w-2 rounded-full", sentimentStyles[sentiment])} />
      {showLabel && <span className="capitalize text-muted-foreground">{sentiment}</span>}
    </span>
  );
}

// ====== Team Badge ======
const teamStyles: Record<TargetTeam, string> = {
  marketing: "bg-team-marketing/15 text-team-marketing",
  product: "bg-team-product/15 text-team-product",
  cx: "bg-team-cx/15 text-team-cx",
  sales: "bg-team-sales/15 text-team-sales",
  engineering: "bg-team-engineering/15 text-team-engineering",
};

const teamIcons: Record<TargetTeam, string> = {
  marketing: "📣",
  product: "🧪",
  cx: "💬",
  sales: "💰",
  engineering: "⚙️",
};

export function TeamBadge({ team, className }: { team: TargetTeam; className?: string }) {
  return (
    <span className={cn("inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-medium capitalize", teamStyles[team], className)}>
      {teamIcons[team]} {team === "cx" ? "CX" : team}
    </span>
  );
}

// ====== Tag Badge ======
export function TagBadge({ tag, className }: { tag: string; className?: string }) {
  return (
    <span className={cn("inline-flex items-center rounded-md bg-secondary px-2 py-0.5 text-xs font-medium text-secondary-foreground", className)}>
      {tag}
    </span>
  );
}

// ====== Anomaly Badge ======
export function AnomalyBadge({ className }: { className?: string }) {
  return (
    <span className={cn("inline-flex items-center rounded-full bg-destructive/15 px-2.5 py-0.5 text-xs font-semibold text-destructive", className)}>
      Anomaly
    </span>
  );
}

// ====== Status Badge ======
const statusStyles: Record<string, string> = {
  new: "bg-muted text-muted-foreground",
  reviewing: "bg-info/15 text-info",
  action_planned: "bg-warning/15 text-warning",
  action_taken: "bg-warning/15 text-warning",
  measuring: "bg-info/15 text-info",
  resolved: "bg-success/15 text-success",
  dismissed: "bg-muted text-muted-foreground",
  escalated: "bg-destructive/15 text-destructive",
  pending_approval: "bg-warning/15 text-warning",
  completed: "bg-success/15 text-success",
  failed: "bg-destructive/15 text-destructive",
  rejected: "bg-destructive/15 text-destructive",
};

export function StatusBadge({ status, className }: { status: string; className?: string }) {
  const label = status.replace(/_/g, " ");
  return (
    <span className={cn("inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium capitalize", statusStyles[status] || statusStyles.new, className)}>
      {label}
    </span>
  );
}

// ====== Urgency Badge (alias for Severity in many contexts) ======
export function UrgencyBadge({ urgency, className }: { urgency: Urgency; className?: string }) {
  return <SeverityBadge severity={urgency} className={className} />;
}
