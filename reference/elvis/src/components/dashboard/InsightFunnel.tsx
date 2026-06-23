import type { FunnelStage } from "@/lib/types";
import { cn } from "@/lib/utils";

const stageColors = ["bg-muted", "bg-info/20", "bg-warning/20", "bg-success/20"];
const stageTextColors = ["text-muted-foreground", "text-info", "text-warning", "text-success"];

export function InsightFunnel({ data }: { data: FunnelStage[] }) {
  const maxCount = Math.max(...data.map((d) => d.count), 1);

  return (
    <div className="rounded-lg border bg-card p-6 shadow-sm">
      <h3 className="text-sm font-semibold mb-4">Insight Funnel</h3>
      <div className="space-y-3">
        {data.map((stage, i) => (
          <div key={stage.stage} className="flex items-center gap-3">
            <span className={cn("text-xs font-medium w-24 text-right", stageTextColors[i])}>{stage.label}</span>
            <div className="flex-1 h-8 bg-secondary rounded-lg overflow-hidden">
              <div
                className={cn("h-full rounded-lg flex items-center px-3 transition-all", stageColors[i])}
                style={{ width: `${Math.max((stage.count / maxCount) * 100, 15)}%` }}
              >
                <span className={cn("text-xs font-bold", stageTextColors[i])}>{stage.count}</span>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
