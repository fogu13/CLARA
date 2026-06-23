import type { SignalSourceConfig } from "@/lib/types";
import { cn } from "@/lib/utils";
import { formatDistanceToNow } from "date-fns";

const sourceIcons: Record<string, string> = {
  typeform: "📝",
  google_analytics: "📊",
  zendesk: "🎧",
  api_poll: "📱",
  webhook: "🔗",
  csv_upload: "📄",
  mautic: "📧",
  hubspot: "🟠",
  intercom: "💬",
};

export function SourceHealthGrid({ sources }: { sources: SignalSourceConfig[] }) {
  return (
    <div className="rounded-lg border bg-card shadow-sm">
      <div className="px-6 py-4 border-b">
        <h3 className="text-sm font-semibold">Source Health</h3>
      </div>
      <div className="p-4 grid grid-cols-1 gap-3">
        {sources.slice(0, 5).map((source) => (
          <div key={source.id} className="flex items-center gap-3 rounded-lg bg-secondary/50 px-4 py-3">
            <span className="text-lg">{sourceIcons[source.source_type] || "📡"}</span>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium truncate">{source.name}</p>
              <p className="text-xs text-muted-foreground">
                {source.last_synced_at
                  ? `Synced ${formatDistanceToNow(new Date(source.last_synced_at), { addSuffix: true })}`
                  : "Never synced"}
              </p>
            </div>
            <div className={cn(
              "h-2.5 w-2.5 rounded-full",
              source.sync_status === "error" ? "bg-destructive" :
              !source.enabled ? "bg-muted-foreground" :
              "bg-success"
            )} />
          </div>
        ))}
      </div>
    </div>
  );
}
