export const signalCsvFields = [
  "signal_id",
  "customer_id",
  "account_id",
  "source",
  "journey",
  "journey_stage",
  "campaign_exposure",
  "product_events",
  "feedback_text",
  "language",
  "timestamp"
] as const;

export type SignalCsvField = (typeof signalCsvFields)[number];
export type ColumnMapping = Record<SignalCsvField, string>;

export type ParsedCsv = {
  headers: string[];
  rows: Record<string, string>[];
};

const aliases: Record<SignalCsvField, string[]> = {
  signal_id: ["signal_id", "id", "ticket_id", "response_id"],
  customer_id: ["customer_id", "contact_id", "user_id", "respondent_id"],
  account_id: ["account_id", "company_id", "organization_id", "org_id"],
  source: ["source", "channel", "system"],
  journey: ["journey", "journey_name", "stage_group"],
  journey_stage: ["journey_stage", "stage", "touchpoint", "step"],
  campaign_exposure: ["campaign_exposure", "campaign", "campaigns", "campaign_name"],
  product_events: ["product_events", "events", "event_names", "behavior"],
  feedback_text: ["feedback_text", "comment", "text", "message", "description"],
  language: ["language", "lang", "locale"],
  timestamp: ["timestamp", "created_at", "date", "submitted_at"]
};

function normalizeHeader(value: string): string {
  return value.trim().toLowerCase().replace(/[\s-]+/g, "_");
}

function parseCsvLine(line: string): string[] {
  const cells: string[] = [];
  let current = "";
  let insideQuote = false;

  for (let index = 0; index < line.length; index += 1) {
    const character = line[index];
    const nextCharacter = line[index + 1];

    if (character === '"' && insideQuote && nextCharacter === '"') {
      current += '"';
      index += 1;
      continue;
    }

    if (character === '"') {
      insideQuote = !insideQuote;
      continue;
    }

    if (character === "," && !insideQuote) {
      cells.push(current);
      current = "";
      continue;
    }

    current += character;
  }

  cells.push(current);
  return cells.map((cell) => cell.trim());
}

export function parseCsv(csvText: string): ParsedCsv {
  const lines = csvText
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean);

  if (lines.length === 0) {
    return { headers: [], rows: [] };
  }

  const headers = parseCsvLine(lines[0]);
  const rows = lines.slice(1).map((line) => {
    const cells = parseCsvLine(line);
    return Object.fromEntries(headers.map((header, index) => [header, cells[index] ?? ""]));
  });

  return { headers, rows };
}

export function inferColumnMapping(headers: string[]): ColumnMapping {
  const normalizedHeaders = new Map(headers.map((header) => [normalizeHeader(header), header]));

  return Object.fromEntries(
    signalCsvFields.map((field) => {
      const match = aliases[field].find((alias) => normalizedHeaders.has(alias));
      return [field, match ? normalizedHeaders.get(match) ?? "" : ""];
    })
  ) as ColumnMapping;
}

function escapeCsvCell(value: string): string {
  if (!/[",\n\r]/.test(value)) return value;
  return `"${value.replaceAll('"', '""')}"`;
}

export function toCanonicalSignalCsv(rows: Record<string, string>[], mapping: ColumnMapping): string {
  const csvRows = [
    signalCsvFields.join(","),
    ...rows.map((row) =>
      signalCsvFields
        .map((field) => {
          const mappedHeader = mapping[field];
          return escapeCsvCell(mappedHeader ? row[mappedHeader] ?? "" : "");
        })
        .join(",")
    )
  ];

  return csvRows.join("\n");
}

export function unmappedRequiredFields(mapping: ColumnMapping): SignalCsvField[] {
  return signalCsvFields.filter((field) => !mapping[field]);
}

// The only column a user must map: the feedback text itself. Everything else is
// auto-filled with a sensible default so arbitrary CSVs import without busywork.
export const essentialSignalCsvField: SignalCsvField = "feedback_text";

function defaultSignalValue(field: SignalCsvField, rowIndex: number, batchId: string, now: string): string {
  switch (field) {
    case "signal_id":
      return `csv-${batchId}-${rowIndex}`;
    case "customer_id":
    case "account_id":
      return "unknown";
    case "source":
      return "csv_import";
    case "journey":
      return "unknown";
    case "journey_stage":
      return "general";
    case "language":
      return "en";
    case "timestamp":
      return now;
    default:
      // feedback_text (required, no default), campaign_exposure, product_events
      return "";
  }
}

// Build the canonical CSV, filling any unmapped/empty field with a default so the
// import only really needs the feedback text mapped.
export function toCanonicalSignalCsvWithDefaults(
  rows: Record<string, string>[],
  mapping: ColumnMapping,
  batchId: string
): string {
  const now = new Date().toISOString();
  const csvRows = [
    signalCsvFields.join(","),
    ...rows.map((row, index) => {
      const rowNumber = index + 1;
      return signalCsvFields
        .map((field) => {
          const mappedHeader = mapping[field];
          const raw = mappedHeader ? (row[mappedHeader] ?? "").trim() : "";
          return escapeCsvCell(raw || defaultSignalValue(field, rowNumber, batchId, now));
        })
        .join(",");
    })
  ];

  return csvRows.join("\n");
}

