import type { AffectedCohort, Evidence } from "../../lib/types";

function percent(value: number): string {
  return `${Math.round(value * 100)}%`;
}

function formatDate(timestamp: string): string {
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

export function EvidencePanel({
  evidence,
  confidence,
  affectedCohort,
  owner
}: {
  evidence: Evidence[];
  confidence: number;
  affectedCohort: AffectedCohort;
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
          <dt>Confidence</dt>
          <dd>{percent(confidence)}</dd>
        </div>
        <div>
          <dt>Affected</dt>
          <dd>
            {affectedCohort.customers} customers, {affectedCohort.accounts} accounts
          </dd>
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
          <dd>{affectedCohort.date_range}</dd>
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
