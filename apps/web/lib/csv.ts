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

// Single-pass tokenizer that tracks quote state across newlines, so a quoted field
// containing a newline (valid RFC-4180 CSV) is kept intact instead of being split
// into corrupt rows. Returns rows of raw (untrimmed) cells.
function tokenizeCsv(text: string): string[][] {
  const rows: string[][] = [];
  let cell = "";
  let row: string[] = [];
  let insideQuote = false;

  for (let index = 0; index < text.length; index += 1) {
    const character = text[index];
    const nextCharacter = text[index + 1];

    if (character === '"') {
      if (insideQuote && nextCharacter === '"') {
        cell += '"';
        index += 1; // escaped quote
      } else {
        insideQuote = !insideQuote;
      }
      continue;
    }

    if (character === "," && !insideQuote) {
      row.push(cell);
      cell = "";
      continue;
    }

    if ((character === "\n" || character === "\r") && !insideQuote) {
      if (character === "\r" && nextCharacter === "\n") {
        index += 1; // treat CRLF as one break
      }
      row.push(cell);
      rows.push(row);
      cell = "";
      row = [];
      continue;
    }

    cell += character;
  }

  // Flush a trailing cell/row (unless the text ended exactly on a row break).
  if (cell !== "" || row.length > 0) {
    row.push(cell);
    rows.push(row);
  }

  return rows;
}

export function parseCsv(csvText: string): ParsedCsv {
  const trimmed = tokenizeCsv(csvText)
    .map((cells) => cells.map((cell) => cell.trim()))
    .filter((cells) => cells.some((cell) => cell !== "")); // drop fully-empty rows

  if (trimmed.length === 0) {
    return { headers: [], rows: [] };
  }

  const headers = trimmed[0];
  const rows = trimmed.slice(1).map((cells) =>
    Object.fromEntries(headers.map((header, index) => [header, cells[index] ?? ""]))
  );

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

// Only the signal id gets a client-side default (a stable batch label so a
// mis-mapped import can be removed as one batch). Every other unmapped field is
// left EMPTY so the backend applies its own defaults and detection: language is
// detected from the text (a German review used to be stamped "en"), the
// timestamp falls back to import time WITH an audit flag, and journey/stage/
// source take the canonical unknown values the candidate grouping understands.
function defaultSignalValue(field: SignalCsvField, rowIndex: number, batchId: string, _now: string): string {
  switch (field) {
    case "signal_id":
      return `csv-${batchId}-${rowIndex}`;
    default:
      return "";
  }
}

// Build the canonical CSV: map columns to canonical fields (filling unmapped ones with
// defaults), and carry any other source column through under its own header so the backend
// keeps it as signal metadata. Only the feedback text really needs mapping.
export function toCanonicalSignalCsvWithDefaults(
  rows: Record<string, string>[],
  mapping: ColumnMapping,
  batchId: string,
  sourceHeaders: string[] = []
): string {
  const now = new Date().toISOString();
  const usedHeaders = new Set(Object.values(mapping).filter(Boolean));
  const knownFields = new Set<string>(signalCsvFields);
  // Columns the user didn't map and that don't collide with a canonical name -> metadata.
  const extraHeaders = sourceHeaders.filter(
    (header) => !usedHeaders.has(header) && !knownFields.has(header)
  );

  const headerRow = [...signalCsvFields, ...extraHeaders].map(escapeCsvCell).join(",");
  const dataRows = rows.map((row, index) => {
    const rowNumber = index + 1;
    const canonical = signalCsvFields.map((field) => {
      const mappedHeader = mapping[field];
      const raw = mappedHeader ? (row[mappedHeader] ?? "").trim() : "";
      return escapeCsvCell(raw || defaultSignalValue(field, rowNumber, batchId, now));
    });
    const extras = extraHeaders.map((header) => escapeCsvCell((row[header] ?? "").trim()));
    return [...canonical, ...extras].join(",");
  });

  return [headerRow, ...dataRows].join("\n");
}

