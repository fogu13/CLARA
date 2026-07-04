// Shared formatting helpers, consolidated from copies that had drifted
// (formatMetric used `value < 1` in one place, rendering negative metrics as huge
// percentages; the correct check is Math.abs(value) < 1).

export function percent(value: number | null | undefined): string {
  return `${Math.round((value ?? 0) * 100)}%`;
}

export function formatMetric(value: number | null | undefined): string {
  if (value === null || value === undefined) return "None";
  if (Math.abs(value) < 1) return `${Math.round(value * 100)}%`;
  return String(value);
}
