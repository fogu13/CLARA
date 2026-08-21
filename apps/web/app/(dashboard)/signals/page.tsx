"use client";

import { useEffect, useRef, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { MessageSquare, Upload, Sparkles, Trash2 } from "lucide-react";
import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip as ChartTooltip, XAxis, YAxis } from "recharts";
import { signalTrendSeries, withRollingAverage } from "@/lib/signal-trend";
import { cn } from "@/lib/utils";
import { apiBaseUrl, apiHeaders, backfillAuthenticity, deleteSignals, getSignals, importSignalCsv, validateSignalCsv } from "@/lib/client-api";
import {
  essentialSignalCsvField,
  inferColumnMapping,
  parseCsv,
  signalCsvFields,
  toCanonicalSignalCsvWithDefaults
} from "@/lib/csv";
import type { ColumnMapping } from "@/lib/csv";
import { useI18n } from "@/lib/i18n";

type Status = { tone: "idle" | "busy" | "ok" | "error"; message: string };
type FileCsv = { fileName: string; headers: string[]; rows: Record<string, string>[]; mapping: ColumnMapping };

const fieldLabels: Record<string, string> = {
  feedback_text: "Feedback text",
  signal_id: "Signal ID",
  customer_id: "Customer ID",
  account_id: "Account ID",
  source: "Source",
  journey: "Journey",
  journey_stage: "Journey stage",
  campaign_exposure: "Campaign exposure",
  product_events: "Product events",
  language: "Language",
  timestamp: "Timestamp"
};

const FEED_PAGE_SIZE = 25;

export default function SignalsPage() {
  const { t } = useI18n();
  const [signals, setSignals] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [status, setStatus] = useState<Status>({ tone: "idle", message: "" });
  const [fileCsv, setFileCsv] = useState<FileCsv | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [query, setQuery] = useState("");
  const [sourceFilter, setSourceFilter] = useState("all");
  const [languageFilter, setLanguageFilter] = useState("all");
  const [visibleCount, setVisibleCount] = useState(FEED_PAGE_SIZE);

  const [loadFailed, setLoadFailed] = useState(false);

  useEffect(() => {
    getSignals()
      .then((data) => {
        setSignals(data);
        setLoadFailed(false);
      })
      .catch(() => setLoadFailed(true))
      .finally(() => setLoading(false));
  }, []);

  async function refresh() {
    try {
      setSignals(await getSignals());
    } catch {
      /* keep current list */
    }
  }

  // Raw daily counts plus a 7-day trailing average: bulk-import days would
  // otherwise set the y-axis and flatten the organic trend to the floor.
  const trend = withRollingAverage(signalTrendSeries(signals, 30));

  const filteredSignals = signals.filter((s) => {
    if (sourceFilter !== "all" && s.source !== sourceFilter) return false;
    if (languageFilter !== "all" && s.language !== languageFilter) return false;
    if (query && !(s.feedback_text ?? "").toLowerCase().includes(query.toLowerCase())) return false;
    return true;
  });

  // Ingestion authenticity review, summarised from what the API stamped on each
  // signal. Computed here rather than fetched so the card reflects exactly what
  // the feed below shows. Per-language flag rates are compared so the filter's
  // own disparate impact is visible before anyone excludes anything: strata need
  // 50+ signals and 5+ flags before a warning, matching services/authenticity.py.
  const review = (() => {
    const assessed = signals.filter((s) => s.metadata?.authenticity_state);
    const flagged = assessed.filter((s) => s.metadata.authenticity_band === "review_suggested");
    const abstained = assessed.filter((s) => s.metadata.authenticity_state === "insufficient_text");
    const counts: Record<string, number> = {};
    for (const s of assessed) {
      for (const code of String(s.metadata.authenticity_reasons ?? "").split(",").filter(Boolean)) {
        counts[code] = (counts[code] ?? 0) + 1;
      }
    }
    const byLang: Record<string, { n: number; f: number }> = {};
    for (const s of assessed) {
      const lang = (s.language || "unknown").toLowerCase();
      byLang[lang] ??= { n: 0, f: 0 };
      byLang[lang].n += 1;
      if (s.metadata.authenticity_band === "review_suggested") byLang[lang].f += 1;
    }
    const rates = Object.entries(byLang)
      .filter(([, v]) => v.n >= 50)
      .map(([lang, v]) => ({ lang, rate: v.f / v.n, f: v.f }));
    let disparity: { hi: string; hiRate: number; lo: string; loRate: number } | null = null;
    if (rates.length >= 2) {
      const hi = rates.reduce((a, b) => (b.rate > a.rate ? b : a));
      const lo = rates.reduce((a, b) => (b.rate < a.rate ? b : a));
      if (hi.f >= 5 && hi.rate > 0 && (lo.rate === 0 || hi.rate / lo.rate >= 2)) {
        disparity = { hi: hi.lang, hiRate: hi.rate, lo: lo.lang, loRate: lo.rate };
      }
    }
    return {
      total: assessed.length,
      flagged: flagged.length,
      abstained: abstained.length,
      reasons: Object.entries(counts).sort((a, b) => b[1] - a[1]) as [string, number][],
      disparity,
    };
  })();

  // CSV imports carry their batch in the signal id (csv-<batch>-<row>), so a
  // mis-mapped import can be undone as a unit.
  const importBatches = Object.entries(
    signals.reduce<Record<string, string[]>>((acc, s) => {
      const match = /^csv-(.+)-\d+$/.exec(s.signal_id ?? "");
      if (match) (acc[match[1]] ??= []).push(s.signal_id);
      return acc;
    }, {})
  ).map(([batch, ids]) => ({ batch, ids }));

  async function removeBatch(batch: string, ids: string[]) {
    if (!window.confirm(`Remove all ${ids.length} signal(s) from import batch ${batch}? This cannot be undone.`)) return;
    setStatus({ tone: "busy", message: "Removing import batch..." });
    try {
      const result = await deleteSignals(ids);
      await refresh();
      setStatus({ tone: "ok", message: `Removed ${result.deleted} signal(s). Re-run triage to refresh insights.` });
    } catch (error) {
      setStatus({ tone: "error", message: error instanceof Error ? error.message : t.common.error });
    }
  }

  async function handleFile(file: File | undefined) {
    if (!file) return;
    try {
      const { headers, rows } = parseCsv(await file.text());
      if (rows.length === 0) {
        setStatus({ tone: "error", message: "That file has no data rows." });
        return;
      }
      setFileCsv({ fileName: file.name, headers, rows, mapping: inferColumnMapping(headers) });
      setStatus({ tone: "idle", message: `Loaded ${rows.length} row(s) from ${file.name}. Map your columns and import.` });
    } catch {
      setStatus({ tone: "error", message: "Couldn't read that file as CSV." });
    }
  }

  function updateMapping(field: string, header: string) {
    setFileCsv((current) =>
      current ? { ...current, mapping: { ...current.mapping, [field]: header } } : current
    );
  }

  async function importMapped() {
    if (!fileCsv) return;
    if (!fileCsv.mapping[essentialSignalCsvField]) {
      setStatus({ tone: "error", message: "Map the column that holds the feedback text. It's the only required field." });
      return;
    }
    setStatus({ tone: "busy", message: `Importing ${fileCsv.rows.length} row(s)…` });
    try {
      // Batch label = filename slug + timestamp, embedded in each signal_id
      // (csv-<batch>-<row>), so the Import batches card shows "checkout-feedback-
      // mr6u0z1m" instead of a bare machine code and survives reloads.
      const fileSlug = fileCsv.fileName
        .toLowerCase()
        .replace(/\.[^.]+$/, "")
        .replace(/[^a-z0-9]+/g, "-")
        .replace(/^-+|-+$/g, "")
        .slice(0, 32);
      const batchId = `${fileSlug ? `${fileSlug}-` : ""}${Date.now().toString(36)}`;
      const canonical = toCanonicalSignalCsvWithDefaults(fileCsv.rows, fileCsv.mapping, batchId, fileCsv.headers);
      const report = await validateSignalCsv(canonical);
      if (!report.valid) {
        const first = report.errors[0];
        setStatus({ tone: "error", message: `Couldn't import: ${first ? first.message : `${report.errors.length} validation error(s)`}` });
        return;
      }
      const result = await importSignalCsv(canonical);
      setFileCsv(null);
      await refresh();
      setStatus({ tone: "ok", message: `Imported ${result.imported} signal(s); skipped ${result.skipped_duplicates} duplicate(s).` });
    } catch (error) {
      setStatus({ tone: "error", message: error instanceof Error ? error.message : "Couldn't import the CSV." });
    }
  }

  async function assessExisting() {
    setStatus({ tone: "busy", message: t.authenticity.assessing });
    try {
      const result = await backfillAuthenticity();
      await refresh();
      setStatus({ tone: "ok", message: `${result.updated} / ${result.scanned}` });
    } catch (error) {
      setStatus({ tone: "error", message: error instanceof Error ? error.message : t.common.error });
    }
  }

  async function runTriage() {
    setStatus({ tone: "busy", message: "Running triage… this can take a moment." });
    try {
      const response = await fetch(`${apiBaseUrl()}/triage/run`, {
        method: "POST",
        credentials: "include", headers: apiHeaders(),
        body: JSON.stringify({})
      });
      if (!response.ok) {
        const body = await response.json().catch(() => null);
        throw new Error(body?.detail ?? `Triage failed (${response.status})`);
      }
      const result = await response.json();
      await refresh();
      setStatus({ tone: "ok", message: `Triage ${result.status}: ${result.insights?.length ?? 0} insight(s) generated.` });
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

      {fileCsv ? (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Map columns: {fileCsv.fileName}</CardTitle>
            <p className="text-sm text-muted-foreground">
              Match your columns to CLARA&apos;s fields. Only <strong>Feedback text</strong> is required;
              unmapped canonical fields use a default, and any other column in your file is kept as metadata.
            </p>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
              {signalCsvFields.map((field) => {
                const required = field === essentialSignalCsvField;
                return (
                  <label key={field} className="flex flex-col gap-1 text-sm">
                    <span className="font-medium">
                      {fieldLabels[field] ?? field}
                      {required ? <span className="text-destructive"> *</span> : null}
                    </span>
                    <select
                      className="h-9 rounded-md border bg-background px-2 text-sm"
                      value={fileCsv.mapping[field] ?? ""}
                      onChange={(event) => updateMapping(field, event.target.value)}
                    >
                      <option value="">Not mapped</option>
                      {fileCsv.headers.map((header) => (
                        <option key={header} value={header}>{header}</option>
                      ))}
                    </select>
                  </label>
                );
              })}
            </div>
            <div className="flex gap-2">
              <Button size="sm" disabled={busy} onClick={importMapped}>
                Import {fileCsv.rows.length} row(s)
              </Button>
              <Button variant="ghost" size="sm" disabled={busy} onClick={() => { setFileCsv(null); setStatus({ tone: "idle", message: "" }); }}>
                Cancel
              </Button>
            </div>
          </CardContent>
        </Card>
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

      {signals.length > 0 && (
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-base">{t.authenticity.cardTitle}</CardTitle>
            <p className="text-xs text-muted-foreground">{t.authenticity.whatThisIs}</p>
          </CardHeader>
          <CardContent className="space-y-3">
            {review.total === 0 ? (
              <div className="flex flex-wrap items-center justify-between gap-3">
                <p className="text-sm text-muted-foreground">{t.authenticity.notAssessedYet}</p>
                <Button variant="outline" size="sm" onClick={assessExisting} disabled={busy}>
                  {t.authenticity.assessExisting}
                </Button>
              </div>
            ) : (
            <>
            <div className="grid gap-4 sm:grid-cols-3">
              <div>
                <div className="text-2xl font-bold tabular-nums">{review.flagged}</div>
                <p className="text-xs text-muted-foreground">{t.authenticity.needsReview}</p>
              </div>
              <div>
                <div className="text-2xl font-bold tabular-nums text-muted-foreground">{review.abstained}</div>
                <p className="text-xs text-muted-foreground">{t.authenticity.tooShortToAssess}</p>
              </div>
              <div>
                <div className="text-2xl font-bold tabular-nums">{review.total - review.flagged - review.abstained}</div>
                <p className="text-xs text-muted-foreground">{t.authenticity.routine}</p>
              </div>
            </div>
            {review.reasons.length > 0 && (
              <div className="flex flex-wrap gap-2">
                {review.reasons.map(([code, n]) => (
                  <Badge key={code} variant="outline" title={t.authenticity.reasonHints[code] ?? code}>
                    {(t.authenticity.reasonLabels[code] ?? code)} · {n}
                  </Badge>
                ))}
              </div>
            )}
            {/* The filter reports its own disparate impact before anyone acts on it.
                A review queue that flags one language far more than another is a
                finding about the filter, not about those customers. */}
            {review.disparity && (
              <p className="rounded-md border border-amber-500/40 bg-amber-500/10 px-3 py-2 text-xs">
                <strong>{t.authenticity.disparityWarning}.</strong>{" "}
                {t.authenticity.disparityBody
                  .replace("{hi}", review.disparity.hi)
                  .replace("{hiRate}", `${Math.round(review.disparity.hiRate * 100)}%`)
                  .replace("{lo}", review.disparity.lo)
                  .replace("{loRate}", `${Math.round(review.disparity.loRate * 100)}%`)}
              </p>
            )}
            {review.total < signals.length && (
              <div className="flex flex-wrap items-center justify-between gap-3 border-t pt-3">
                <p className="text-xs text-muted-foreground">
                  {t.authenticity.someUnassessed.replace("{n}", String(signals.length - review.total))}
                </p>
                <Button variant="outline" size="sm" onClick={assessExisting} disabled={busy}>
                  {t.authenticity.assessExisting}
                </Button>
              </div>
            )}
            </>
            )}
          </CardContent>
        </Card>
      )}

      <Card>
        <CardHeader className="pb-2"><CardTitle className="text-base">{t.dashboard.signalVolume}</CardTitle></CardHeader>
        <CardContent>
          {trend.every((point) => point.count === 0) ? (
            <p className="text-sm text-muted-foreground">{t.dashboard.signalVolumeEmpty}</p>
          ) : (
            <div className="h-48">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={trend} margin={{ top: 4, right: 8, bottom: 0, left: -20 }}>
                  <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                  <XAxis dataKey="day" tick={{ fontSize: 11 }} interval="preserveStartEnd" minTickGap={24} />
                  <YAxis tick={{ fontSize: 11 }} allowDecimals={false} />
                  <ChartTooltip
                    formatter={(value, name) => [
                      `${value} ${t.common.signals}`,
                      name === "avg" ? t.dashboard.chartAvg : t.dashboard.chartRaw
                    ]}
                  />
                  <Area type="monotone" dataKey="count" name="count" stroke="hsl(var(--primary) / 0.35)" fill="hsl(var(--primary) / 0.08)" strokeWidth={1} isAnimationActive={false} />
                  <Area type="monotone" dataKey="avg" name="avg" stroke="hsl(var(--primary))" fill="transparent" strokeWidth={2} isAnimationActive={false} />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          )}
        </CardContent>
      </Card>

      {importBatches.length > 0 ? (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Import batches</CardTitle>
            <p className="text-sm text-muted-foreground">
              Each CSV import is one batch. Remove a batch to undo a mis-mapped import, then re-import and re-run triage.
            </p>
          </CardHeader>
          <CardContent className="space-y-2">
            {importBatches.map(({ batch, ids }) => (
              <div key={batch} className="flex items-center justify-between rounded-md border px-3 py-2 text-sm">
                <span>
                  <code className="rounded bg-muted px-1.5 py-0.5">{batch}</code>
                  {" · "}
                  {ids.length} signal(s)
                </span>
                <Button variant="ghost" size="sm" disabled={busy} onClick={() => removeBatch(batch, ids)}>
                  <Trash2 className="h-4 w-4 mr-1" />
                  Remove
                </Button>
              </div>
            ))}
          </CardContent>
        </Card>
      ) : null}

      <Card>
        <CardHeader><CardTitle>Signal Feed</CardTitle></CardHeader>
        <CardContent>
          {loadFailed ? (
              <p className="text-sm text-destructive">{t.common.error}</p>
            ) : signals.length === 0 ? (
            <div className="text-center py-12">
              <MessageSquare className="h-8 w-8 text-muted-foreground mx-auto mb-3" />
              <p className="text-sm text-muted-foreground">No signals yet. Import CSV or connect a source.</p>
            </div>
          ) : (
            <div className="space-y-3">
              <div className="flex flex-wrap items-center gap-2">
                <input
                  type="search"
                  placeholder="Search feedback text…"
                  className="h-8 flex-1 min-w-48 rounded-md border bg-background px-2 text-sm"
                  value={query}
                  onChange={(e) => { setQuery(e.target.value); setVisibleCount(FEED_PAGE_SIZE); }}
                />
                <select
                  className="h-8 rounded-md border bg-background px-2 text-sm"
                  value={sourceFilter}
                  aria-label="Filter by source"
                  onChange={(e) => { setSourceFilter(e.target.value); setVisibleCount(FEED_PAGE_SIZE); }}
                >
                  <option value="all">All sources</option>
                  {[...new Set(signals.map((s) => s.source).filter(Boolean))].sort().map((source) => (
                    <option key={source} value={source}>{source}</option>
                  ))}
                </select>
                <select
                  className="h-8 rounded-md border bg-background px-2 text-sm"
                  value={languageFilter}
                  aria-label="Filter by language"
                  onChange={(e) => { setLanguageFilter(e.target.value); setVisibleCount(FEED_PAGE_SIZE); }}
                >
                  <option value="all">All languages</option>
                  {[...new Set(signals.map((s) => s.language).filter(Boolean))].sort().map((lang) => (
                    <option key={lang} value={lang}>{lang}</option>
                  ))}
                </select>
              </div>
              {filteredSignals.slice(0, visibleCount).map(s => (
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
                      {s.metadata?.near_duplicate_of && (
                        <Badge variant="outline" title={`Similar to ${s.metadata.near_duplicate_of}`}>
                          possible duplicate
                        </Badge>
                      )}
                      {/* Authenticity review. Deliberately never says "AI-written":
                          the band reflects provenance and duplication evidence, and
                          the tooltip carries the reason so nobody acts on a bare badge. */}
                      {s.metadata?.authenticity_band === "review_suggested" && (
                        <Badge variant="warning" title={s.metadata?.authenticity_note || t.authenticity.reviewSuggestedHint}>
                          {t.authenticity.reviewSuggested}
                        </Badge>
                      )}
                      {s.metadata?.authenticity_state === "insufficient_text" && (
                        <Badge variant="outline" title={t.authenticity.tooShortHint}>
                          {t.authenticity.tooShortToAssess}
                        </Badge>
                      )}
                    </div>
                  </div>
                </div>
              ))}
              <div className="flex items-center justify-between pt-2">
                <p className="text-xs text-muted-foreground">
                  {t.common.showingOf
                    .replace("{n}", String(Math.min(visibleCount, filteredSignals.length)))
                    .replace("{total}", String(filteredSignals.length))}
                  {filteredSignals.length !== signals.length ? ` (of ${signals.length} unfiltered)` : ""}
                </p>
                {filteredSignals.length > visibleCount ? (
                  <Button size="sm" variant="outline" onClick={() => setVisibleCount((n) => n + FEED_PAGE_SIZE)}>
                    Show more
                  </Button>
                ) : null}
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
