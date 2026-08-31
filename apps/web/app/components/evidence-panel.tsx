import type { Evidence } from "../../lib/types";
import { percent } from "@/lib/format";


function formatDate(timestamp: string): string {
  // Missing timestamps are stored as the 1970 epoch sentinel; showing
  // "Jan 1, 1970" reads as corrupt data, so name the gap honestly.
  if (timestamp.startsWith("1970-01-01")) return "no timestamp";
  const date = new Date(timestamp);
  if (Number.isNaN(date.getTime())) return timestamp;

  return new Intl.DateTimeFormat("en", {
    month: "short",
    day: "numeric",
    year: "numeric"
  }).format(date);
}

function uniqueCount(values: string[]): number {
  return new Set(values.filter(Boolean)).size;
}

// Cohort counts live in the page's "Affected cohort" card and the Affected
// Context panel; this summary deliberately doesn't repeat them a third time.
export function EvidencePanel({
  evidence,
  confidence,
  dateRange,
  owner
}: {
  evidence: Evidence[];
  confidence: number;
  dateRange: string;
  owner: string;
}) {
  const sourceCount = uniqueCount(evidence.map((item) => item.source));
  const languageCount = uniqueCount(evidence.map((item) => item.language));

  return (
    <section className="evidence-panel">
      <div className="evidence-panel-header">
        <h3>Evidence</h3>
        <span>{evidence.length} excerpts</span>
      </div>

      <dl className="evidence-summary">
        <div>
          {/* "Model score", not "confidence": the value is an uncalibrated
              heuristic, not a validated probability (external-review item 12). */}
          <dt
            title="Uncalibrated model score: blends signal volume, source count and the model's self-reported certainty. Not a validated probability."
            style={{ cursor: "help" }}
          >
            Model score
          </dt>
          <dd>{percent(confidence)}</dd>
        </div>
        <div>
          <dt>Sources</dt>
          <dd>{sourceCount}</dd>
        </div>
        <div>
          <dt>Languages</dt>
          <dd>{languageCount}</dd>
        </div>
        <div>
          <dt>Date range</dt>
          <dd>{dateRange}</dd>
        </div>
        <div>
          <dt>Owner</dt>
          <dd>{owner}</dd>
        </div>
      </dl>

      {evidence.length > 0 ? (
        <ul className="evidence-list">
          {evidence.map((item) => (
            <li key={item.signal_id}>
              <blockquote>&quot;{item.excerpt}&quot;</blockquote>
              <dl className="evidence-meta">
                <div>
                  <dt>Signal</dt>
                  <dd>{item.signal_id}</dd>
                </div>
                <div>
                  <dt>Source</dt>
                  <dd>{item.source}</dd>
                </div>
                <div>
                  <dt>Customer</dt>
                  <dd>{item.customer_id}</dd>
                </div>
                <div>
                  <dt>Account</dt>
                  <dd>{item.account_id}</dd>
                </div>
                <div>
                  <dt>Language</dt>
                  <dd>{item.language}</dd>
                </div>
                <div>
                  <dt>Seen</dt>
                  <dd>{formatDate(item.timestamp)}</dd>
                </div>
              </dl>
            </li>
          ))}
        </ul>
      ) : (
        <p className="evidence-empty">No evidence excerpts are attached to this problem.</p>
      )}
    </section>
  );
}
