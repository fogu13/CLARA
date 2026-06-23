import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { supabase } from "@/integrations/supabase/client";
import { useWorkspaceId } from "@/hooks/use-workspace";
import { AppLayout } from "@/components/layout/AppLayout";
import { Button } from "@/components/ui/button";
import { Switch } from "@/components/ui/switch";
import { Skeleton } from "@/components/ui/skeleton";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Plus, RefreshCw, Loader2 } from "lucide-react";
import { formatDistanceToNow } from "date-fns";
import { toast } from "sonner";
import { cn } from "@/lib/utils";
import type { SignalSourceConfig } from "@/lib/types";

const sourceIcons: Record<string, string> = {
  typeform: "📝", google_analytics: "📊", zendesk: "🎧",
  api_poll: "📱", webhook: "🔗", csv_upload: "📄",
  mautic: "📧", hubspot: "🟠", intercom: "💬",
};

const SOURCE_TYPES = ["webhook", "csv_upload", "typeform", "zendesk", "hubspot", "intercom", "google_analytics", "api_poll"];
const WEBHOOK_URL = `${import.meta.env.VITE_SUPABASE_URL}/functions/v1/ingest-webhook`;

const SourcesPage = () => {
  const workspaceId = useWorkspaceId();
  const qc = useQueryClient();
  const [addOpen, setAddOpen] = useState(false);
  const [name, setName] = useState("");
  const [type, setType] = useState("webhook");
  const [poll, setPoll] = useState({ endpoint: "", format: "json", auth_header: "", items_path: "", text: "", tags: "", external_id: "", recorded_at: "" });

  const { data: sources = [], isLoading } = useQuery({
    queryKey: ["sources", workspaceId],
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

  const addSource = useMutation({
    mutationFn: async () => {
      const { error } = await supabase.from("signal_sources").insert({
        workspace_id: workspaceId!,
        name: name.trim(),
        source_type: type,
        config: type === "api_poll" ? {
          endpoint: poll.endpoint.trim(),
          format: poll.format,
          auth_header: poll.auth_header.trim() || undefined,
          items_path: poll.items_path.trim() || undefined,
          map: {
            text: poll.text.trim() || undefined,
            tags: poll.tags.trim() || undefined,
            external_id: poll.external_id.trim() || undefined,
            recorded_at: poll.recorded_at.trim() || undefined,
          },
        } : {},
        enabled: true,
        sync_status: "idle",
      } as never);
      if (error) throw error;
    },
    onSuccess: () => {
      toast.success("Source added");
      qc.invalidateQueries({ queryKey: ["sources", workspaceId] });
      setAddOpen(false);
      setName("");
      setType("webhook");
      setPoll({ endpoint: "", format: "json", auth_header: "", items_path: "", text: "", tags: "", external_id: "", recorded_at: "" });
    },
    onError: (e) => toast.error(e instanceof Error ? e.message : "Failed to add source"),
  });

  const toggleSource = useMutation({
    mutationFn: async ({ id, enabled }: { id: number; enabled: boolean }) => {
      const { error } = await supabase.from("signal_sources").update({ enabled }).eq("id", id).eq("workspace_id", workspaceId!);
      if (error) throw error;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["sources", workspaceId] }),
    onError: (e) => toast.error(e instanceof Error ? e.message : "Failed to update source"),
  });

  const refreshSource = useMutation({
    mutationFn: async (id: number) => {
      const { data, error } = await supabase.functions.invoke("sync-source", { body: { source_id: id } });
      if (error) throw error;
      if (data?.error) throw new Error(data.error);
      return data as { synced: number; note?: string };
    },
    onSuccess: (d) => {
      qc.invalidateQueries({ queryKey: ["sources", workspaceId] });
      qc.invalidateQueries({ queryKey: ["signals", workspaceId] });
      toast.success(d.synced ? `Synced ${d.synced} signal(s)` : d.note || "Sync complete");
    },
    onError: (e) => toast.error("Sync failed", { description: e instanceof Error ? e.message : undefined }),
  });

  return (
    <AppLayout title="Signal Sources">
      <div className="flex items-center justify-between mb-6">
        <p className="text-sm text-muted-foreground">Manage your data source connections.</p>
        <Button size="sm" onClick={() => setAddOpen(true)}><Plus className="h-3.5 w-3.5 mr-1.5" />Add Source</Button>
      </div>

      {isLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} className="h-44 w-full rounded-lg" />)}
        </div>
      ) : sources.length === 0 ? (
        <p className="text-sm text-muted-foreground text-center py-12">No signal sources configured yet.</p>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {sources.map((source) => (
            <div key={source.id} className={cn("rounded-lg border bg-card p-6 shadow-sm", source.sync_status === "error" && "border-destructive/30")}>
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-3">
                  <span className="text-2xl">{sourceIcons[source.source_type] || "📡"}</span>
                  <div>
                    <h3 className="text-sm font-semibold">{source.name}</h3>
                    <p className="text-xs text-muted-foreground capitalize">{source.source_type.replace(/_/g, " ")}</p>
                  </div>
                </div>
                <Switch checked={source.enabled} onCheckedChange={(enabled) => toggleSource.mutate({ id: source.id, enabled })} />
              </div>

              <div className="flex items-center gap-2 mb-3">
                <div className={cn(
                  "h-2 w-2 rounded-full",
                  source.sync_status === "error" ? "bg-destructive" :
                  !source.enabled ? "bg-muted-foreground" :
                  source.sync_status === "syncing" ? "bg-warning animate-pulse" :
                  "bg-success"
                )} />
                <span className="text-xs text-muted-foreground capitalize">
                  {source.sync_status === "error" ? "Error" :
                   !source.enabled ? "Disabled" :
                   source.sync_status === "syncing" ? "Syncing..." :
                   "Connected"}
                </span>
              </div>

              {source.sync_error && (
                <p className="text-xs text-destructive mb-3 bg-destructive/5 rounded p-2">{source.sync_error}</p>
              )}

              {source.source_type === "webhook" && (
                <p className="text-[11px] text-muted-foreground mb-3 bg-secondary/50 rounded p-2 break-all">
                  POST to <span className="font-mono">{WEBHOOK_URL}</span> with <span className="font-mono">{`{ source_id: ${source.id}, items: [...] }`}</span>
                </p>
              )}

              <div className="flex items-center justify-between">
                <span className="text-xs text-muted-foreground">
                  {source.last_synced_at
                    ? `Last sync: ${formatDistanceToNow(new Date(source.last_synced_at), { addSuffix: true })}`
                    : "Never synced"}
                </span>
                <Button variant="ghost" size="sm" disabled={!source.enabled || refreshSource.isPending} onClick={() => refreshSource.mutate(source.id)}>
                  {refreshSource.isPending ? <Loader2 className="h-3 w-3 animate-spin" /> : <RefreshCw className="h-3 w-3" />}
                </Button>
              </div>
            </div>
          ))}
        </div>
      )}

      <Dialog open={addOpen} onOpenChange={setAddOpen}>
        <DialogContent>
          <DialogHeader><DialogTitle>Add signal source</DialogTitle></DialogHeader>
          <div className="space-y-4 py-2">
            <div className="space-y-1.5">
              <Label htmlFor="src-name">Name</Label>
              <Input id="src-name" value={name} onChange={(e) => setName(e.target.value)} placeholder="e.g. Support inbox" />
            </div>
            <div className="space-y-1.5">
              <Label>Type</Label>
              <Select value={type} onValueChange={setType}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  {SOURCE_TYPES.map((t) => <SelectItem key={t} value={t}>{t.replace(/_/g, " ")}</SelectItem>)}
                </SelectContent>
              </Select>
              <p className="text-xs text-muted-foreground">
                {type === "webhook" ? "Receives feedback via a POST endpoint (shown after creation)." :
                 type === "csv_upload" ? "Import rows from the Signals page." :
                 type === "api_poll" ? "Poll any JSON/CSV endpoint on demand (configure below)." :
                 "API connector — add credentials, then use Refresh to sync."}
              </p>
            </div>
            {type === "api_poll" && (
              <div className="space-y-2 rounded-md border border-border p-3">
                <p className="text-xs text-muted-foreground">Map your endpoint's fields to signals. Text is required for qualitative feedback.</p>
                <div className="space-y-1.5">
                  <Label htmlFor="poll-endpoint">Endpoint URL</Label>
                  <Input id="poll-endpoint" value={poll.endpoint} onChange={(e) => setPoll((p) => ({ ...p, endpoint: e.target.value }))} placeholder="https://api.example.com/feedback" />
                </div>
                <div className="grid grid-cols-2 gap-2">
                  <div className="space-y-1.5">
                    <Label>Format</Label>
                    <Select value={poll.format} onValueChange={(v) => setPoll((p) => ({ ...p, format: v }))}>
                      <SelectTrigger><SelectValue /></SelectTrigger>
                      <SelectContent>
                        <SelectItem value="json">JSON</SelectItem>
                        <SelectItem value="csv">CSV</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="space-y-1.5">
                    <Label htmlFor="poll-items">Items path (JSON)</Label>
                    <Input id="poll-items" value={poll.items_path} onChange={(e) => setPoll((p) => ({ ...p, items_path: e.target.value }))} placeholder="e.g. data" />
                  </div>
                </div>
                <div className="space-y-1.5">
                  <Label htmlFor="poll-auth">Auth header (optional)</Label>
                  <Input id="poll-auth" value={poll.auth_header} onChange={(e) => setPoll((p) => ({ ...p, auth_header: e.target.value }))} placeholder="Bearer …" />
                </div>
                <div className="grid grid-cols-2 gap-2">
                  <div className="space-y-1.5">
                    <Label htmlFor="poll-text">Text field</Label>
                    <Input id="poll-text" value={poll.text} onChange={(e) => setPoll((p) => ({ ...p, text: e.target.value }))} placeholder="e.g. body" />
                  </div>
                  <div className="space-y-1.5">
                    <Label htmlFor="poll-extid">External ID field</Label>
                    <Input id="poll-extid" value={poll.external_id} onChange={(e) => setPoll((p) => ({ ...p, external_id: e.target.value }))} placeholder="e.g. id" />
                  </div>
                  <div className="space-y-1.5">
                    <Label htmlFor="poll-tags">Tags field</Label>
                    <Input id="poll-tags" value={poll.tags} onChange={(e) => setPoll((p) => ({ ...p, tags: e.target.value }))} placeholder="optional" />
                  </div>
                  <div className="space-y-1.5">
                    <Label htmlFor="poll-recorded">Recorded-at field</Label>
                    <Input id="poll-recorded" value={poll.recorded_at} onChange={(e) => setPoll((p) => ({ ...p, recorded_at: e.target.value }))} placeholder="optional" />
                  </div>
                </div>
              </div>
            )}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setAddOpen(false)}>Cancel</Button>
            <Button disabled={!name.trim() || (type === "api_poll" && !poll.endpoint.trim()) || addSource.isPending} onClick={() => addSource.mutate()}>
              {addSource.isPending ? "Adding…" : "Add source"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </AppLayout>
  );
};

export default SourcesPage;
