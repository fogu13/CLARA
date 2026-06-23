import { useRef, useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { supabase } from "@/integrations/supabase/client";
import { useWorkspaceId } from "@/hooks/use-workspace";
import { AppLayout } from "@/components/layout/AppLayout";
import type { Signal, SignalType, Sentiment } from "@/lib/types";
import { SeverityBadge, SentimentIndicator, TagBadge, AnomalyBadge } from "@/components/shared/Badges";
import { EmptyState } from "@/components/shared/EmptyState";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Switch } from "@/components/ui/switch";
import { Checkbox } from "@/components/ui/checkbox";
import { Skeleton } from "@/components/ui/skeleton";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { toast } from "sonner";
import { formatDistanceToNow } from "date-fns";
import { Upload, Sparkles, Search, MessageSquare, BarChart3, Loader2, Trash2 } from "lucide-react";
import { Sheet, SheetContent, SheetHeader, SheetTitle } from "@/components/ui/sheet";

function normalizeSignal(row: Record<string, unknown>): Signal {
  return {
    ...row,
    tags: Array.isArray(row.tags) ? (row.tags as string[]) : [],
    metadata: (row.metadata as Record<string, unknown>) ?? {},
    is_anomaly: row.is_anomaly ?? false,
    contact_count: (row.contact_count as number) ?? 1,
  } as Signal;
}

/** Minimal CSV parser (handles quoted fields). Returns rows keyed by lowercased header. */
function parseCsv(text: string): Record<string, string>[] {
  const lines = text.split(/\r?\n/).filter((l) => l.trim());
  if (lines.length < 2) return [];
  const split = (line: string) => {
    const out: string[] = [];
    let cur = "";
    let q = false;
    for (let i = 0; i < line.length; i++) {
      const c = line[i];
      if (c === '"') {
        if (q && line[i + 1] === '"') { cur += '"'; i++; } else q = !q;
      } else if (c === "," && !q) { out.push(cur); cur = ""; } else cur += c;
    }
    out.push(cur);
    return out.map((s) => s.trim());
  };
  const headers = split(lines[0]).map((h) => h.toLowerCase());
  return lines.slice(1).map((line) => {
    const cells = split(line);
    const row: Record<string, string> = {};
    headers.forEach((h, i) => (row[h] = cells[i] ?? ""));
    return row;
  });
}

const SignalsPage = () => {
  const workspaceId = useWorkspaceId();
  const qc = useQueryClient();
  const fileRef = useRef<HTMLInputElement>(null);
  const [search, setSearch] = useState("");
  const [typeFilter, setTypeFilter] = useState<SignalType | "all">("all");
  const [sentimentFilter, setSentimentFilter] = useState<Sentiment | "all">("all");
  const [anomalyOnly, setAnomalyOnly] = useState(false);
  const [selectedSignal, setSelectedSignal] = useState<Signal | null>(null);
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set());
  // Holds the ids queued for deletion while the confirm dialog is open.
  const [pendingDelete, setPendingDelete] = useState<number[] | null>(null);

  const { data: signals = [], isLoading } = useQuery({
    queryKey: ["signals", workspaceId],
    queryFn: async () => {
      const { data, error } = await supabase
        .from("signals")
        .select("*")
        .eq("workspace_id", workspaceId!)
        .order("recorded_at", { ascending: false })
        .limit(200);
      if (error) throw error;
      return (data as Record<string, unknown>[]).map(normalizeSignal);
    },
    enabled: !!workspaceId,
  });

  // Phase C pipeline: enrich raw signals (sentiment/theme/urgency) then synthesise insights.
  const analyze = useMutation({
    mutationFn: async () => {
      const enrichRes = await supabase.functions.invoke("enrich-signal", { body: { workspace_id: workspaceId } });
      if (enrichRes.error) throw enrichRes.error;
      if (enrichRes.data?.error) throw new Error(enrichRes.data.error);
      const synthRes = await supabase.functions.invoke("synthesize-insights", { body: { workspace_id: workspaceId } });
      if (synthRes.error) throw synthRes.error;
      if (synthRes.data?.error) throw new Error(synthRes.data.error);
      return { enriched: enrichRes.data?.enriched ?? 0, created: synthRes.data?.created ?? 0 };
    },
    onSuccess: (d) => {
      qc.invalidateQueries({ queryKey: ["signals", workspaceId] });
      qc.invalidateQueries({ queryKey: ["insights"] });
      qc.invalidateQueries({ queryKey: ["insights-dash"] });
      toast.success(`Analyzed: ${d.enriched} signal(s) enriched, ${d.created} insight(s) created`);
    },
    onError: (e) => toast.error("Analysis failed", { description: e instanceof Error ? e.message : undefined }),
  });

  // Phase E — CSV import. Columns (header row, case-insensitive): type, source, text, metric_name, metric_value, tags, recorded_at.
  const importCsv = useMutation({
    mutationFn: async (file: File) => {
      const rows = parseCsv(await file.text());
      if (!rows.length) throw new Error("No rows found in CSV (need a header row + at least one row)");
      // DB enforces `valid_signal`: a row must be qualitative WITH text, or quantitative
      // WITH a metric_name. Skip rows that satisfy neither so one bad row doesn't 400 the batch.
      const payload = rows.flatMap((r) => {
        const hasText = !!r.text?.trim();
        const hasMetric = !!r.metric_name?.trim();
        if (!hasText && !hasMetric) return [];
        const isQuant = hasMetric && ((r.type || "").toLowerCase() === "quantitative" || !hasText);
        return [{
          workspace_id: workspaceId!,
          signal_type: isQuant ? "quantitative" : "qualitative",
          source: r.source || "csv_upload",
          category: "feedback",
          text_content: hasText ? r.text : null,
          metric_name: hasMetric ? r.metric_name : null,
          metric_value: r.metric_value ? Number(r.metric_value) : null,
          urgency: "low",
          is_anomaly: false,
          contact_count: 1,
          tags: r.tags ? r.tags.split(";").map((t) => t.trim()).filter(Boolean) : [],
          metadata: { imported: true },
          recorded_at: r.recorded_at || new Date().toISOString(),
        }];
      });
      const skipped = rows.length - payload.length;
      if (!payload.length) {
        throw new Error("No valid rows. Each row needs text (qualitative) or a metric_name (quantitative). Expected columns: type, source, text, metric_name, metric_value, tags, recorded_at.");
      }
      const { error } = await supabase.from("signals").insert(payload as never);
      if (error) throw error;
      return { imported: payload.length, skipped };
    },
    onSuccess: ({ imported, skipped }) => {
      qc.invalidateQueries({ queryKey: ["signals", workspaceId] });
      toast.success(`Imported ${imported} signal(s)${skipped ? `, skipped ${skipped} invalid row(s)` : ""}. Click Analyze to enrich them.`);
    },
    onError: (e) => toast.error("Import failed", { description: e instanceof Error ? e.message : undefined }),
  });

  const deleteSignals = useMutation({
    mutationFn: async (ids: number[]) => {
      const { error } = await supabase
        .from("signals")
        .delete()
        .in("id", ids)
        .eq("workspace_id", workspaceId!);
      if (error) throw error;
      return ids.length;
    },
    onSuccess: (count) => {
      qc.invalidateQueries({ queryKey: ["signals", workspaceId] });
      setSelectedIds(new Set());
      toast.success(`Deleted ${count} signal${count === 1 ? "" : "s"}`);
    },
    onError: (e) => toast.error("Delete failed", { description: e instanceof Error ? e.message : undefined }),
  });

  const filtered = signals.filter((s) => {
    if (typeFilter !== "all" && s.signal_type !== typeFilter) return false;
    if (sentimentFilter !== "all" && s.sentiment !== sentimentFilter) return false;
    if (anomalyOnly && !s.is_anomaly) return false;
    if (search && !s.text_content?.toLowerCase().includes(search.toLowerCase()) && !s.metric_name?.toLowerCase().includes(search.toLowerCase())) return false;
    return true;
  });

  const allSelected = filtered.length > 0 && filtered.every((s) => selectedIds.has(s.id));
  const someSelected = filtered.some((s) => selectedIds.has(s.id));
  const toggleAll = () =>
    setSelectedIds(allSelected ? new Set() : new Set(filtered.map((s) => s.id)));
  const toggleOne = (id: number) =>
    setSelectedIds((prev) => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });

  return (
    <AppLayout title="Signals">
      <div className="flex gap-6">
        {/* Filter sidebar */}
        <div className="w-60 shrink-0 space-y-5">
          <div>
            <label className="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-2 block">Signal Type</label>
            <div className="space-y-1.5">
              {(["all", "qualitative", "quantitative"] as const).map((t) => (
                <button key={t} onClick={() => setTypeFilter(t)} className={`block w-full text-left text-sm px-3 py-1.5 rounded-md transition-colors ${typeFilter === t ? "bg-primary/10 text-primary font-medium" : "text-muted-foreground hover:bg-secondary"}`}>
                  {t === "all" ? "All Types" : t === "qualitative" ? "💬 Qualitative" : "📊 Quantitative"}
                </button>
              ))}
            </div>
          </div>
          <div>
            <label className="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-2 block">Sentiment</label>
            <div className="space-y-1.5">
              {(["all", "positive", "neutral", "negative", "mixed"] as const).map((s) => (
                <button key={s} onClick={() => setSentimentFilter(s)} className={`block w-full text-left text-sm px-3 py-1.5 rounded-md transition-colors ${sentimentFilter === s ? "bg-primary/10 text-primary font-medium" : "text-muted-foreground hover:bg-secondary"}`}>
                  {s === "all" ? "All Sentiments" : <SentimentIndicator sentiment={s} />}
                </button>
              ))}
            </div>
          </div>
          <div className="flex items-center justify-between">
            <label className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">Anomalies Only</label>
            <Switch checked={anomalyOnly} onCheckedChange={setAnomalyOnly} />
          </div>
        </div>

        {/* Main table */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-3 mb-4">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Search signals..." className="pl-9" />
            </div>
            <input
              ref={fileRef}
              type="file"
              accept=".csv"
              className="hidden"
              onChange={(e) => { const f = e.target.files?.[0]; if (f) importCsv.mutate(f); e.target.value = ""; }}
            />
            <Button variant="outline" size="sm" disabled={importCsv.isPending || !workspaceId} onClick={() => fileRef.current?.click()}>
              {importCsv.isPending ? <><Loader2 className="h-3.5 w-3.5 mr-1.5 animate-spin" />Importing…</> : <><Upload className="h-3.5 w-3.5 mr-1.5" />Import</>}
            </Button>
            <Button variant="outline" size="sm" disabled={analyze.isPending || !workspaceId} onClick={() => analyze.mutate()}>
              {analyze.isPending ? <><Loader2 className="h-3.5 w-3.5 mr-1.5 animate-spin" />Analyzing…</> : <><Sparkles className="h-3.5 w-3.5 mr-1.5" />Analyze</>}
            </Button>
          </div>

          {selectedIds.size > 0 && (
            <div className="flex items-center justify-between mb-3 rounded-lg border bg-secondary/50 px-4 py-2">
              <span className="text-sm font-medium">{selectedIds.size} selected</span>
              <div className="flex items-center gap-2">
                <Button variant="ghost" size="sm" onClick={() => setSelectedIds(new Set())}>
                  Clear
                </Button>
                <Button
                  variant="destructive"
                  size="sm"
                  disabled={deleteSignals.isPending}
                  onClick={() => setPendingDelete([...selectedIds])}
                >
                  {deleteSignals.isPending
                    ? <><Loader2 className="h-3.5 w-3.5 mr-1.5 animate-spin" />Deleting…</>
                    : <><Trash2 className="h-3.5 w-3.5 mr-1.5" />Delete selected</>}
                </Button>
              </div>
            </div>
          )}

          {!isLoading && signals.length === 0 ? (
            <EmptyState title="No signals yet" description="Import a CSV, connect a source, or load sample data to get started.">
              <Button variant="outline" size="sm" onClick={() => fileRef.current?.click()}>
                <Upload className="h-3.5 w-3.5 mr-1.5" />Import CSV
              </Button>
            </EmptyState>
          ) : (
            <div className="rounded-lg border bg-card shadow-sm overflow-hidden">
              <table className="w-full">
                <thead>
                  <tr className="border-b bg-secondary/50">
                    <th className="px-4 py-3 w-10">
                      <Checkbox
                        checked={allSelected ? true : someSelected ? "indeterminate" : false}
                        onCheckedChange={toggleAll}
                        aria-label="Select all signals"
                      />
                    </th>
                    <th className="text-left text-xs font-semibold text-muted-foreground px-4 py-3 w-10">Type</th>
                    <th className="text-left text-xs font-semibold text-muted-foreground px-4 py-3 w-28">Source</th>
                    <th className="text-left text-xs font-semibold text-muted-foreground px-4 py-3">Content</th>
                    <th className="text-left text-xs font-semibold text-muted-foreground px-4 py-3 w-24">Sentiment</th>
                    <th className="text-left text-xs font-semibold text-muted-foreground px-4 py-3 w-36">Tags</th>
                    <th className="text-left text-xs font-semibold text-muted-foreground px-4 py-3 w-20">Urgency</th>
                    <th className="text-left text-xs font-semibold text-muted-foreground px-4 py-3 w-20">Anomaly</th>
                    <th className="text-left text-xs font-semibold text-muted-foreground px-4 py-3 w-24">Date</th>
                    <th className="px-4 py-3 w-10"></th>
                  </tr>
                </thead>
                <tbody className="divide-y">
                  {isLoading ? (
                    Array.from({ length: 6 }).map((_, i) => (
                      <tr key={i}><td colSpan={10} className="px-4 py-3"><Skeleton className="h-5 w-full" /></td></tr>
                    ))
                  ) : filtered.length === 0 ? (
                    <tr><td colSpan={10} className="px-4 py-8 text-center text-sm text-muted-foreground">No signals found</td></tr>
                  ) : (
                    filtered.map((signal) => (
                      <tr key={signal.id} onClick={() => setSelectedSignal(signal)} className={`group hover:bg-secondary/30 cursor-pointer transition-colors ${selectedIds.has(signal.id) ? "bg-primary/5" : ""}`}>
                        <td className="px-4 py-3" onClick={(e) => e.stopPropagation()}>
                          <Checkbox
                            checked={selectedIds.has(signal.id)}
                            onCheckedChange={() => toggleOne(signal.id)}
                            aria-label={`Select signal ${signal.id}`}
                          />
                        </td>
                        <td className="px-4 py-3">
                          {signal.signal_type === "qualitative" ? <MessageSquare className="h-4 w-4 text-primary" /> : <BarChart3 className="h-4 w-4 text-sentiment-mixed" />}
                        </td>
                        <td className="px-4 py-3">
                          <span className="text-xs font-medium bg-secondary px-2 py-0.5 rounded">{signal.source.replace(/_/g, " ")}</span>
                        </td>
                        <td className="px-4 py-3 text-sm">
                          {signal.signal_type === "qualitative"
                            ? <span className="line-clamp-1">{signal.text_content}</span>
                            : <span className="font-mono text-xs">{signal.metric_name}: {signal.metric_value}{signal.metric_delta_pct != null && <> <span className={signal.metric_delta_pct > 0 ? "text-destructive" : "text-success"}>({signal.metric_delta_pct > 0 ? "↑" : "↓"}{Math.abs(signal.metric_delta_pct)}%)</span></>}</span>
                          }
                        </td>
                        <td className="px-4 py-3">{signal.sentiment && <SentimentIndicator sentiment={signal.sentiment} />}</td>
                        <td className="px-4 py-3">
                          <div className="flex gap-1 flex-wrap">
                            {signal.tags.slice(0, 2).map((t) => <TagBadge key={t} tag={t} />)}
                            {signal.tags.length > 2 && <span className="text-xs text-muted-foreground">+{signal.tags.length - 2}</span>}
                          </div>
                        </td>
                        <td className="px-4 py-3"><SeverityBadge severity={signal.urgency} /></td>
                        <td className="px-4 py-3">{signal.is_anomaly && <AnomalyBadge />}</td>
                        <td className="px-4 py-3 text-xs text-muted-foreground">{formatDistanceToNow(new Date(signal.recorded_at), { addSuffix: true })}</td>
                        <td className="px-4 py-3" onClick={(e) => e.stopPropagation()}>
                          <Button
                            variant="ghost"
                            size="icon"
                            className="h-7 w-7 text-muted-foreground opacity-0 group-hover:opacity-100 hover:text-destructive transition-opacity"
                            aria-label={`Delete signal ${signal.id}`}
                            onClick={() => setPendingDelete([signal.id])}
                          >
                            <Trash2 className="h-3.5 w-3.5" />
                          </Button>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>

      {/* Delete confirmation */}
      <AlertDialog open={!!pendingDelete} onOpenChange={(open) => !open && setPendingDelete(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>
              Delete {pendingDelete?.length ?? 0} signal{(pendingDelete?.length ?? 0) === 1 ? "" : "s"}?
            </AlertDialogTitle>
            <AlertDialogDescription>
              This permanently removes the selected signal{(pendingDelete?.length ?? 0) === 1 ? "" : "s"} and any taxonomy mappings. This action cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
              onClick={() => {
                if (pendingDelete) deleteSignals.mutate(pendingDelete);
                setPendingDelete(null);
              }}
            >
              Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* Signal detail slide-over */}
      <Sheet open={!!selectedSignal} onOpenChange={() => setSelectedSignal(null)}>
        <SheetContent className="w-[480px] sm:max-w-[480px] overflow-y-auto">
          {selectedSignal && (
            <>
              <SheetHeader>
                <SheetTitle className="flex items-center gap-2">
                  {selectedSignal.signal_type === "qualitative" ? "💬" : "📊"} Signal #{selectedSignal.id}
                </SheetTitle>
              </SheetHeader>
              <div className="mt-6 space-y-5">
                <div className="flex flex-wrap gap-2">
                  <SeverityBadge severity={selectedSignal.urgency} />
                  {selectedSignal.sentiment && <SentimentIndicator sentiment={selectedSignal.sentiment} />}
                  {selectedSignal.is_anomaly && <AnomalyBadge />}
                </div>
                {selectedSignal.text_content && (
                  <div>
                    <h4 className="text-xs font-semibold text-muted-foreground uppercase mb-1">Content</h4>
                    <p className="text-sm bg-secondary/50 rounded-lg p-4 italic">"{selectedSignal.text_content}"</p>
                  </div>
                )}
                {selectedSignal.metric_name && (
                  <div>
                    <h4 className="text-xs font-semibold text-muted-foreground uppercase mb-1">Metric</h4>
                    <div className="bg-secondary/50 rounded-lg p-4">
                      <div className="text-lg font-bold font-mono">{selectedSignal.metric_name}: {selectedSignal.metric_value}</div>
                      <div className="text-sm text-muted-foreground">Baseline: {selectedSignal.metric_baseline} | Delta: {selectedSignal.metric_delta_pct}%</div>
                    </div>
                  </div>
                )}
                <div>
                  <h4 className="text-xs font-semibold text-muted-foreground uppercase mb-1">Source</h4>
                  <p className="text-sm">{selectedSignal.source.replace(/_/g, " ")} — {selectedSignal.entity_name || "Unknown entity"}</p>
                </div>
                <div>
                  <h4 className="text-xs font-semibold text-muted-foreground uppercase mb-1">Tags</h4>
                  <div className="flex flex-wrap gap-1.5">{selectedSignal.tags.map((t) => <TagBadge key={t} tag={t} />)}</div>
                </div>
                <div>
                  <h4 className="text-xs font-semibold text-muted-foreground uppercase mb-1">Recorded</h4>
                  <p className="text-sm text-muted-foreground">{new Date(selectedSignal.recorded_at).toLocaleString()}</p>
                </div>
              </div>
            </>
          )}
        </SheetContent>
      </Sheet>
    </AppLayout>
  );
};

export default SignalsPage;
