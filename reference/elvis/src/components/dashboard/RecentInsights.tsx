import type { Insight } from "@/lib/types";
import { SeverityBadge, TeamBadge, StatusBadge } from "@/components/shared/Badges";
import { formatDistanceToNow } from "date-fns";
import { useNavigate } from "react-router-dom";

export function RecentInsights({ insights }: { insights: Insight[] }) {
  const navigate = useNavigate();

  return (
    <div className="rounded-lg border bg-card shadow-sm">
      <div className="px-6 py-4 border-b">
        <h3 className="text-sm font-semibold">Recent Insights</h3>
      </div>
      <div className="divide-y">
        {insights.slice(0, 5).map((insight) => (
          <button
            key={insight.id}
            onClick={() => navigate(`/insights/${insight.id}`)}
            className="w-full flex items-center gap-3 px-6 py-3.5 text-left hover:bg-secondary/50 transition-colors"
          >
            <SeverityBadge severity={insight.severity} />
            <span className="flex-1 text-sm font-medium truncate">{insight.title}</span>
            <TeamBadge team={insight.target_team} />
            <span className="text-xs text-muted-foreground whitespace-nowrap">
              {formatDistanceToNow(new Date(insight.detected_at), { addSuffix: true })}
            </span>
            <StatusBadge status={insight.status} />
          </button>
        ))}
      </div>
    </div>
  );
}
