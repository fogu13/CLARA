import {
  getActionQueueProblems,
  getEmergingProblems,
  getTerminologyDictionary,
  getTaxonomies
} from "../lib/api";
import { ActionDecisionPanel } from "./components/action-decision-panel";
import { ActionProposalEditor } from "./components/action-proposal-editor";
import { AffectedContextPanel } from "./components/affected-context-panel";
import { CustomerContextPanel } from "./components/customer-context-panel";
import { DraftProblemEditor } from "./components/draft-problem-editor";
import { EvidencePanel } from "./components/evidence-panel";
import { OutcomeBoardPanel } from "./components/outcome-board-panel";
import { OutcomeMeasurementPanel } from "./components/outcome-measurement-panel";
import { PolicyRulesPanel } from "./components/policy-rules-panel";
import { ProblemLifecyclePanel } from "./components/problem-lifecycle-panel";
import { SignalIntakePanel } from "./components/signal-intake-panel";
import { StateNotice } from "./components/state-notice";
import type {
  ActionProposal,
  ContextImpactSummary,
  EmergingProblemReport,
  GovernanceCheck,
  ProblemRecord,
  TerminologyDictionaryEntry,
  TaxonomyCatalog
} from "../lib/types";

const statusLabels: Record<string, string> = {
  approval_needed: "Approval needed",
  blocked_by_policy: "Blocked by policy",
  validation_required: "Validation required",
  in_progress: "In progress",
  resolved: "Resolved"
};

function percent(value: number): string {
  return `${Math.round(value * 100)}%`;
}

function formatMetric(value: number): string {
  if (value < 1) return percent(value);
  return String(value);
}

function formatNumber(value: number): string {
  return new Intl.NumberFormat("en-US", { maximumFractionDigits: 0 }).format(value);
}

function actionLabel(action: ActionProposal): string {
  return action.class.replaceAll("_", " ");
}

function checkLabel(check: GovernanceCheck): string {
  return check.status.replaceAll("_", " ");
}

function QueueStats({ problems }: { problems: ProblemRecord[] }) {
  const blocked = problems.filter((problem) => problem.approval_pressure === "blocked").length;
  const affectedCustomers = problems.reduce(
    (total, problem) => total + problem.affected_cohort.customers,
    0
  );
  const actions = problems.reduce((total, problem) => total + problem.action_proposals.length, 0);

  return (
    <section className="stats" aria-label="Queue summary">
      <div>
        <span className="stat-label">Open problems</span>
        <strong>{problems.length}</strong>
      </div>
      <div>
        <span className="stat-label">Affected customers</span>
        <strong>{affectedCustomers}</strong>
      </div>
      <div>
        <span className="stat-label">Proposed actions</span>
        <strong>{actions}</strong>
      </div>
      <div>
        <span className="stat-label">Policy blocked</span>
        <strong>{blocked}</strong>
      </div>
    </section>
  );
}

function ContextImpactPanel({ contextImpact }: { contextImpact?: ContextImpactSummary | null }) {
  if (!contextImpact) {
    return (
      <StateNotice tone="empty" title="No linked context yet">
        Import customer context rows that match the evidence customer or account IDs.
      </StateNotice>
    );
  }

  return (
    <section>
      <h3>Context Impact</h3>
      <dl className="compact-list">
        <div>
          <dt>Matched customers</dt>
          <dd>{contextImpact.matched_customers}</dd>
        </div>
        <div>
          <dt>Matched accounts</dt>
          <dd>{contextImpact.matched_accounts}</dd>
        </div>
        <div>
          <dt>High-value accounts</dt>
          <dd>{contextImpact.high_value_accounts}</dd>
        </div>
        <div>
          <dt>Account value</dt>
          <dd>{formatNumber(contextImpact.total_account_value)}</dd>
        </div>
        <div>
          <dt>Avg. health</dt>
          <dd>
            {contextImpact.average_health_score === null ||
            contextImpact.average_health_score === undefined
              ? "Unknown"
              : percent(contextImpact.average_health_score)}
          </dd>
        </div>
        <div>
          <dt>Consent risk</dt>
          <dd>{contextImpact.consent_risk_customers}</dd>
        </div>
        <div>
          <dt>Score lift</dt>
          <dd>+{percent(contextImpact.score_delta)}</dd>
        </div>
        <div>
          <dt>Drivers</dt>
          <dd>{contextImpact.drivers.length ? contextImpact.drivers.join(", ") : "covered"}</dd>
        </div>
      </dl>
      <small>
        {contextImpact.owners.length ? contextImpact.owners.join(", ") : "No owner"} /{" "}
        {contextImpact.product_owners.length
          ? contextImpact.product_owners.join(", ")
          : "No product owner"} /{" "}
        {contextImpact.regions.length ? contextImpact.regions.join(", ") : "No region"}
      </small>
    </section>
  );
}

function TrustedIntelligencePanel({
  taxonomies,
  terminology
}: {
  taxonomies: TaxonomyCatalog[];
  terminology: TerminologyDictionaryEntry[];
}) {
  const categoryCount = taxonomies.reduce(
    (total, taxonomy) => total + taxonomy.categories.length,
    0
  );
  const lockedCount = taxonomies.reduce(
    (total, taxonomy) =>
      total + taxonomy.categories.filter((category) => category.locked).length,
    0
  );
  const limitations = Array.from(
    new Set(taxonomies.flatMap((taxonomy) => taxonomy.known_limitations))
  );
  const dictionaryLanguages = Array.from(
    new Set(terminology.flatMap((entry) => entry.languages))
  ).sort();
  const dictionaryTerms = terminology
    .slice(0, 4)
    .map((entry) => entry.canonical_term)
    .join(", ");

  return (
    <section className="taxonomy-panel">
      <header>
        <div>
          <p className="eyebrow">Phase 3</p>
          <h2>Trusted Intelligence Engine</h2>
        </div>
        <dl className="taxonomy-stats">
          <div>
            <dt>Taxonomies</dt>
            <dd>{taxonomies.length}</dd>
          </div>
          <div>
            <dt>Categories</dt>
            <dd>{categoryCount}</dd>
          </div>
          <div>
            <dt>Locked</dt>
            <dd>{lockedCount}</dd>
          </div>
          <div>
            <dt>Terms</dt>
            <dd>{terminology.length}</dd>
          </div>
        </dl>
      </header>
      <div className="taxonomy-grid">
        {taxonomies.map((taxonomy) => (
          <article key={taxonomy.taxonomy_type}>
            <span>{taxonomy.taxonomy_type.replaceAll("_", " ")}</span>
            <strong>{taxonomy.version}</strong>
            <small>{taxonomy.locale_support.join(" / ")}</small>
            <p>
              {taxonomy.categories
                .slice(0, 3)
                .map((category) => category.label)
                .join(", ")}
            </p>
          </article>
        ))}
      </div>
      {dictionaryTerms ? (
        <p className="limitation">
          Dictionary: {dictionaryTerms}. Languages: {dictionaryLanguages.join(" / ")}
        </p>
      ) : null}
      {limitations[0] ? <p className="limitation">Limit: {limitations[0]}</p> : null}
    </section>
  );
}

function EmergingProblemsPanel({ report }: { report: EmergingProblemReport }) {
  const visibleSignals = report.signals.slice(0, 3);

  return (
    <section className="emerging-panel">
      <header className="emerging-panel-header">
        <div>
          <p className="eyebrow">Phase 3</p>
          <h2>Emerging Problem Radar</h2>
        </div>
        <dl className="emerging-stats">
          <div>
            <dt>Candidates</dt>
            <dd>{report.candidate_count}</dd>
          </div>
          <div>
            <dt>Watch</dt>
            <dd>{report.watch_count}</dd>
          </div>
          <div>
            <dt>Action</dt>
            <dd>{report.action_count}</dd>
          </div>
        </dl>
      </header>

      {visibleSignals.length > 0 ? (
        <ol className="emerging-list">
          {visibleSignals.map((signal) => (
            <li key={signal.candidate_id}>
              <div className="emerging-list-header">
                <div>
                  <span className={`trend trend-${signal.trend_label}`}>
                    {signal.trend_label}
                  </span>
                  <strong>{signal.title}</strong>
                  <small>
                    {signal.journey} / {signal.journey_stage}
                  </small>
                </div>
                <div className="emerging-score">
                  <strong>{percent(signal.emerging_score)}</strong>
                  <span>emerging score</span>
                </div>
              </div>

              <dl className="emerging-metrics">
                <div>
                  <dt>Signals</dt>
                  <dd>{signal.signal_count}</dd>
                </div>
                <div>
                  <dt>Sources</dt>
                  <dd>{signal.source_count}</dd>
                </div>
                <div>
                  <dt>Customers</dt>
                  <dd>{signal.customer_count}</dd>
                </div>
                <div>
                  <dt>Accounts</dt>
                  <dd>{signal.account_count}</dd>
                </div>
              </dl>

              {signal.taxonomy_labels.length > 0 ? (
                <p className="emerging-taxonomy">
                  Taxonomy: {signal.taxonomy_labels.join(", ")}
                </p>
              ) : null}
              {signal.drivers[0] ? <p className="emerging-driver">{signal.drivers[0]}</p> : null}
              <p className="emerging-next-step">{signal.recommended_next_step}</p>
            </li>
          ))}
        </ol>
      ) : (
        <p className="emerging-empty">No candidate has crossed the watch threshold yet.</p>
      )}
    </section>
  );
}

function ProblemCard({ problem }: { problem: ProblemRecord }) {
  const outcome = problem.outcome_contract;

  return (
    <article className="problem-card">
      <header className="problem-header">
        <div>
          <div className="meta-line">
            <span>{problem.problem_id}</span>
            <span>{problem.journey}</span>
            <span>{problem.journey_stage}</span>
          </div>
          <h2>{problem.title}</h2>
          <p>{problem.statement}</p>
        </div>
        <div className="score-block">
          <span className={`status status-${problem.status}`}>
            {statusLabels[problem.status] ?? problem.status}
          </span>
          <strong>{percent(problem.impact_score ?? 0)}</strong>
          <span>{problem.impact_band ?? "unscored"} impact</span>
        </div>
      </header>

      <div className="problem-grid">
        <DraftProblemEditor problem={problem} />
        <ProblemLifecyclePanel problem={problem} />

        <EvidencePanel
          evidence={problem.evidence}
          confidence={problem.evidence_confidence}
          affectedCohort={problem.affected_cohort}
          owner={problem.owner}
        />

        <ContextImpactPanel contextImpact={problem.context_impact} />

        <AffectedContextPanel problemId={problem.problem_id} />

        <section>
          <h3>Root-Cause Hypothesis</h3>
          <p>{problem.root_cause_hypothesis}</p>
          {problem.known_limitations.length > 0 ? (
            <p className="limitation">Limit: {problem.known_limitations[0]}</p>
          ) : null}
        </section>

        <section>
          <h3>Action Portfolio</h3>
          <ul className="action-list">
            {problem.action_proposals.map((action) => (
              <li key={action.action_id}>
                <span className={`risk risk-${action.risk_level}`}>{action.risk_level}</span>
                <div>
                  <strong>{actionLabel(action)}</strong>
                  <p>{action.proposal}</p>
                  <small>
                    {action.destination} / {action.owner}
                  </small>
                  <ActionProposalEditor problemId={problem.problem_id} action={action} />
                  <ActionDecisionPanel problemId={problem.problem_id} action={action} />
                </div>
              </li>
            ))}
          </ul>
        </section>

        <section>
          <h3>Governance</h3>
          <ul className="check-list">
            {problem.governance_checks.map((check) => (
              <li key={check.check_id} className={`check check-${check.status}`}>
                <strong>{checkLabel(check)}</strong>
                <small>{check.policy_rule_id ?? check.rule}</small>
                <span>{check.reason}</span>
              </li>
            ))}
          </ul>
        </section>

        <section className="outcome-section">
          <h3>Outcome Contract</h3>
          <dl className="compact-list">
            <div>
              <dt>Metric</dt>
              <dd>{outcome.primary_metric}</dd>
            </div>
            <div>
              <dt>Baseline</dt>
              <dd>{formatMetric(outcome.baseline)}</dd>
            </div>
            <div>
              <dt>Target</dt>
              <dd>{formatMetric(outcome.success_threshold)}</dd>
            </div>
            <div>
              <dt>Window</dt>
              <dd>{outcome.measurement_window_days} days</dd>
            </div>
          </dl>
          <OutcomeMeasurementPanel problemId={problem.problem_id} contract={outcome} />
        </section>
      </div>
    </article>
  );
}

export default async function Home() {
  const [problems, taxonomies, terminology, emergingProblems] = await Promise.all([
    getActionQueueProblems(),
    getTaxonomies(),
    getTerminologyDictionary(),
    getEmergingProblems()
  ]);

  return (
    <main className="page-shell">
      <section className="page-heading">
        <div>
          <p className="eyebrow">Feedback-to-Outcome</p>
          <h1>Action Queue</h1>
        </div>
        <p>
          Review evidence-backed customer problems, approve coordinated actions, and define how each
          intervention will be measured.
        </p>
      </section>

      <QueueStats problems={problems} />

      <TrustedIntelligencePanel taxonomies={taxonomies} terminology={terminology} />

      <EmergingProblemsPanel report={emergingProblems} />

      <OutcomeBoardPanel />

      <CustomerContextPanel />

      <PolicyRulesPanel />

      <SignalIntakePanel />

      {problems.length > 0 ? (
        <section className="queue" aria-label="Problems requiring action">
          {problems.map((problem) => (
            <ProblemCard key={problem.problem_id} problem={problem} />
          ))}
        </section>
      ) : (
        <StateNotice tone="empty" title="No problems in the Action Queue">
          Import a demo dataset or CSV signals, then accept a candidate to create a draft problem.
        </StateNotice>
      )}
    </main>
  );
}
