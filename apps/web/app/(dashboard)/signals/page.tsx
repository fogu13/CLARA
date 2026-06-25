"use client";

import { useEffect, useRef, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { MessageSquare, Upload, Sparkles } from "lucide-react";
import { cn } from "@/lib/utils";
import { apiBaseUrl, apiHeaders, getSignals, importSignalCsv, validateSignalCsv } from "@/lib/client-api";
import { inferColumnMapping, parseCsv, toCanonicalSignalCsv, unmappedRequiredFields } from "@/lib/csv";

type Status = { tone: "idle" | "busy" | "ok" | "error"; message: string };

export default function SignalsPage() {
  const [signals, setSignals] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [status, setStatus] = useState<Status>({ tone: "idle", message: "" });
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    getSignals()
      .then(setSignals)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  async function refresh() {
    try {
      setSignals(await getSignals());
    } catch {
      /* keep current list */
    }
  }

  async function handleFile(file: File | undefined) {
    if (!file) return;
    setStatus({ tone: "busy", message: `Importing ${file.name}…` });
    try {
      const { headers, rows } = parseCsv(await file.text());
      const mapping = inferColumnMapping(headers);
      const missing = unmappedRequiredFields(mapping);
      if (missing.length > 0) {
        setStatus({
          tone: "error",
          message: `Couldn't match these required columns: ${missing.join(", ")}. Expected headers like signal_id, customer_id, source, journey, journey_stage, feedback_text, timestamp.`
        });
        return;
      }
      const canonical = toCanonicalSignalCsv(rows, mapping);
      const report = await validateSignalCsv(canonical);
      if (!report.valid) {
        const first = report.errors[0];
        setStatus({
          tone: "error",
          message: `CSV has ${report.errors.length} error(s)${first ? `: ${first.message}` : ""}.`
        });
        return;
      }
      const result = await importSignalCsv(canonical);
      await refresh();
      setStatus({
        tone: "ok",
        message: `Imported ${result.imported} signal(s); skipped ${result.skipped_duplicates} duplicate(s).`
      });
    } catch (error) {
      setStatus({ tone: "error", message: error instanceof Error ? error.message : "Couldn't import the CSV." });
    }
  }

  async function runTriage() {
    setStatus({ tone: "busy", message: "Running triage… this can take a moment." });
    try {
      const response = await fetch(`${apiBaseUrl()}/triage/run`, {
        method: "POST",
        headers: apiHeaders(),
        body: JSON.stringify({})
      });
      if (!response.ok) {
        const body = await response.json().catch(() => null);
        throw new Error(body?.detail ?? `Triage failed (${response.status})`);
      }
      const result = await response.json();
      await refresh();
      setStatus({
        tone: "ok",
        message: `Triage ${result.status}: ${result.insights?.length ?? 0} insight(s) generated.`
      });
    } catch (error) {
      setStatus({ tone: "error", message: error instanceof Error ? error.message : "Couldn't run triage." });
    }
  }

  if (loading) return <div className="text-muted-foreground">Loading signals...</div>;

  const busy = status.tone === "busy";

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Signals</h1>
          <p className="text-sm text-muted-foreground mt-1">Customer feedback signals from all sources</p>
        </div>
        <div className="flex gap-2">
          <input
            ref={fileInputRef}
            type="file"
            accept=".csv,text/csv"
            className="hidden"
            onChange={(event) => {
              void handleFile(event.target.files?.[0]);
              event.target.value = "";
            }}
          />
          <Button variant="outline" size="sm" disabled={busy} onClick={() => fileInputRef.current?.click()}>
            <Upload className="h-4 w-4 mr-2" />
            Import CSV
          </Button>
          <Button size="sm" disabled={busy} onClick={runTriage}>
            <Sparkles className="h-4 w-4 mr-2" />
            Run Triage
          </Button>
        </div>
      </div>

      {status.message ? (
        <div
          className={cn(
            "rounded-md border p-3 text-sm",
            status.tone === "error"
              ? "border-destructive/40 bg-destructive/5 text-destructive"
              : status.tone === "ok"
                ? "border-emerald-500/40 bg-emerald-500/5 text-emerald-700 dark:text-emerald-400"
                : "border-border bg-muted text-muted-foreground"
          )}
        >
          {status.message}
        </div>
      ) : null}

      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardHeader className="pb-2"><CardTitle className="text-sm text-muted-foreground">Total Signals</CardTitle></CardHeader>
          <CardContent><div className="text-2xl font-bold">{signals.length}</div></CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2"><CardTitle className="text-sm text-muted-foreground">Sources</CardTitle></CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {new Set(signals.map(s => s.source)).size}
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2"><CardTitle className="text-sm text-muted-foreground">Enriched</CardTitle></CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {signals.filter(s => s.enriched).length}
            </div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader><CardTitle>Signal Feed</CardTitle></CardHeader>
        <CardContent>
          {signals.length === 0 ? (
            <div className="text-center py-12">
              <MessageSquare className="h-8 w-8 text-muted-foreground mx-auto mb-3" />
              <p className="text-sm text-muted-foreground">No signals yet. Import CSV or connect a source.</p>
            </div>
          ) : (
            <div className="space-y-3">
              {signals.slice(0, 20).map(s => (
                <div key={s.signal_id} className="flex items-start gap-3 border-b pb-3">
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium truncate">{s.feedback_text?.slice(0, 200)}</p>
                    <div className="flex items-center gap-2 mt-1">
                      <Badge variant="secondary" className="text-xs">{s.source}</Badge>
                      <span className="text-xs text-muted-foreground">{s.journey} / {s.journey_stage}</span>
                      {s.sentiment && (
                        <Badge variant={s.sentiment === "negative" ? "destructive" : s.sentiment === "positive" ? "success" : "secondary"}>
                          {s.sentiment}
                        </Badge>
                      )}
                      {s.urgency && s.urgency !== "medium" && (
                        <Badge variant={s.urgency === "critical" ? "destructive" : "warning"}>
                          {s.urgency}
                        </Badge>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
