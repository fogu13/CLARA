import type { SignalRecord } from "./types";

export type TrendPoint = { day: string; count: number };

// Signals per day over the trailing window; day label is MM-DD.
export function signalTrendSeries(signals: SignalRecord[], days = 30): TrendPoint[] {
  const now = Date.now();
  const dayMs = 86_400_000;
  const buckets = new Map<string, number>();
  for (let offset = days - 1; offset >= 0; offset -= 1) {
    buckets.set(new Date(now - offset * dayMs).toISOString().slice(0, 10), 0);
  }
  for (const signal of signals) {
    const day = (signal.timestamp || "").slice(0, 10);
    if (buckets.has(day)) buckets.set(day, (buckets.get(day) ?? 0) + 1);
  }
  return [...buckets.entries()].map(([day, count]) => ({ day: day.slice(5), count }));
}

// Trailing mean over up to `window` days. Bulk-import days (one CSV upload
// stamping hundreds of signals on a single date) otherwise set the y-axis and
// flatten the organic trend to the floor.
export function withRollingAverage(
  series: TrendPoint[],
  window = 7
): (TrendPoint & { avg: number })[] {
  return series.map((point, index) => {
    const start = Math.max(0, index - window + 1);
    const slice = series.slice(start, index + 1);
    const avg = slice.reduce((total, item) => total + item.count, 0) / slice.length;
    return { ...point, avg: Math.round(avg * 10) / 10 };
  });
}

// Count of signals in the trailing `days` ending at `endOffsetDays` before now.
export function countInWindow(signals: SignalRecord[], days: number, endOffsetDays = 0): number {
  const dayMs = 86_400_000;
  const end = Date.now() - endOffsetDays * dayMs;
  const start = end - days * dayMs;
  return signals.filter((signal) => {
    const stamp = Date.parse(signal.timestamp || "");
    return Number.isFinite(stamp) && stamp > start && stamp <= end;
  }).length;
}
