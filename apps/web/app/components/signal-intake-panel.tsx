"use client";

import { useEffect, useState } from "react";
import sampleSignals from "../../../../data/sample_signals.json";
import {
  acceptProblemCandidate,
  getDemoDatasets,
  getProblemCandidates,
  getSignals,
  importDemoDataset,
  importSignalCsv,
  rejectProblemCandidate,
  validateSignalCsv
} from "../../lib/client-api";
import {
  inferColumnMapping,
  parseCsv,
  signalCsvFields,
  toCanonicalSignalCsv,
  unmappedRequiredFields
} from "../../lib/csv";
import type { ColumnMapping } from "../../lib/csv";
import type {
  DemoDatasetSummary,
  ProblemCandidate,
  SignalRecord,
  SignalValidationReport
} from "../../lib/types";
import { StateNotice } from "./state-notice";
import { useI18n } from "@/lib/i18n";
import { currentUserEmail } from "../../lib/auth-client";
import { percent } from "@/lib/format";

type IntakeState = {
  status: "loading" | "ready" | "saving" | "error";
  message: string;
  signals: SignalRecord[];
  candidates: ProblemCandidate[];
  demoDatasets: DemoDatasetSummary[];
};

type FileCsvState = {
  fileName: string;
  headers: string[];
  rows: Record<string, string>[];
  mapping: ColumnMapping;
};

type ValidationState = {
  source: "pasted" | "mapped";
  report: SignalValidationReport;
};


function candidateStatusLabels(t: ReturnType<typeof useI18n>["t"]): Record<ProblemCandidate["review_status"], string> {
  return {
    pending: t.intake.statusPending,
    duplicate: t.intake.statusDuplicate,
    accepted: t.intake.statusAccepted,
    rejected: t.intake.statusRejected
  };
}

function CandidateIntelligence({ candidate }: { candidate: ProblemCandidate }) {
  const classifications = candidate.classifications ?? [];
  const limitations = candidate.known_limitations ?? [];
  const contradictions = candidate.contradictory_evidence ?? [];
  const rootCauseAnalysis = candidate.root_cause_analysis;

  if (!rootCauseAnalysis && !classifications.length && !limitations.length && !contradictions.length) {
    return null;
  }

  return (
    <div className="candidate-intelligence">
      <div className="classification-row">
        <span>Trusted intelligence</span>
        <strong>{percent(candidate.emerging_problem_score ?? 0)} emerging score</strong>
      </div>
      {rootCauseAnalysis ? (
        <div className="root-cause-analysis">
          <div className="classification-row">
            <span>Root cause</span>
            <strong>{percent(rootCauseAnalysis.confidence)}</strong>
          </div>
          <p>{rootCauseAnalysis.hypothesis}</p>
          {rootCauseAnalysis.factors[0] ? (
            <small className="classification-meta">
              {rootCauseAnalysis.factors[0].explanation}
            </small>
          ) : null}
          {rootCauseAnalysis.validation_questions[0] ? (
            <small className="classification-meta">
              Validate: {rootCauseAnalysis.validation_questions[0]}
            </small>
          ) : null}
        </div>
      ) : null}
      {classifications.length ? (
        <ul className="classification-list">
          {classifications.map((classification) => (
            <li key={`${classification.taxonomy_type}-${classification.category_id}`}>
              <div className="classification-row">
                <strong>{classification.label}</strong>
                <span>{percent(classification.confidence)}</span>
              </div>
              <small className="classification-meta">
                {classification.taxonomy_type.replaceAll("_", " ")} /{" "}
                {classification.matched_terms.slice(0, 4).join(", ")}
              </small>
              {classification.language_notes[0] ? (
                <small className="classification-meta">{classification.language_notes[0]}</small>
              ) : null}
            </li>
          ))}
        </ul>
      ) : null}
      {contradictions[0] ? <p className="candidate-duplicate">{contradictions[0]}</p> : null}
      {limitations[0] ? <p className="candidate-review-note">Limit: {limitations[0]}</p> : null}
    </div>
  );
}

async function loadIntakeState(): Promise<
  Pick<IntakeState, "signals" | "candidates" | "demoDatasets">
> {
  const [signals, candidates, demoDatasets] = await Promise.all([
    getSignals(),
    getProblemCandidates(),
    getDemoDatasets()
  ]);
  return { signals, candidates, demoDatasets };
}

export function SignalIntakePanel() {
  const { t } = useI18n();
  const [csvText, setCsvText] = useState(
    "signal_id,customer_id,account_id,source,journey,journey_stage,campaign_exposure,product_events,feedback_text,language,timestamp\n"
  );
  const [fileCsv, setFileCsv] = useState<FileCsvState | null>(null);
  const [validation, setValidation] = useState<ValidationState | null>(null);
  const [selectedDemoDatasetId, setSelectedDemoDatasetId] = useState("");
  const [state, setState] = useState<IntakeState>({
    status: "loading",
    message: "Loading signal intake...",
    signals: [],
    candidates: [],
    demoDatasets: []
  });

  useEffect(() => {
    loadIntakeState()
      .then(({ signals, candidates, demoDatasets }) => {
        setState({
          status: "ready",
          message: "Signal intake is connected to the API.",
          signals,
          candidates,
          demoDatasets
        });
        setSelectedDemoDatasetId((current) => current || demoDatasets[0]?.dataset_id || "");
      })
      .catch(() => {
        setState({
          status: "error",
          message: "API is not connected. Start the backend to import and persist signals.",
          signals: sampleSignals as SignalRecord[],
          candidates: [],
          demoDatasets: []
        });
      });
  }, []);

  async function importSelectedDemoDataset() {
    const datasetId = selectedDemoDatasetId || state.demoDatasets[0]?.dataset_id;
    if (!datasetId) return;

    setState((current) => ({ ...current, status: "saving", message: "Importing demo dataset..." }));

    try {
      const result = await importDemoDataset(datasetId);
      const { signals, candidates, demoDatasets } = await loadIntakeState();
      setState({
        status: "ready",
        message: (
          `Imported ${result.title}: ${result.signals.imported} signals, ` +
          `${result.signals.skipped_duplicates} signal duplicates, ` +
          `${result.customer_context.imported} context rows.`
        ),
        signals,
        candidates,
        demoDatasets
      });
    } catch (error) {
      setState((current) => ({
        ...current,
        status: "error",
        message: error instanceof Error ? error.message : "Could not import demo dataset."
      }));
    }
  }

  async function importCsvText() {
    setState((current) => ({ ...current, status: "saving", message: "Importing CSV..." }));

    try {
      const report = await validateSignalCsv(csvText);
      setValidation({ source: "pasted", report });
      if (!report.valid) {
        setState((current) => ({
          ...current,
          status: "error",
          message: "Fix CSV validation errors before import."
        }));
        return;
      }

      const result = await importSignalCsv(csvText);
      const { signals, candidates, demoDatasets } = await loadIntakeState();
      setState({
        status: "ready",
        message: `CSV import added ${result.imported}; skipped ${result.skipped_duplicates} duplicates.`,
        signals,
        candidates,
        demoDatasets
      });
    } catch (error) {
      setState((current) => ({
        ...current,
        status: "error",
        message: error instanceof Error ? error.message : "Could not import CSV."
      }));
    }
  }

  async function validatePastedCsv() {
    setState((current) => ({ ...current, status: "saving", message: "Validating pasted CSV..." }));

    try {
      const report = await validateSignalCsv(csvText);
      setValidation({ source: "pasted", report });
      setState((current) => ({
        ...current,
        status: report.valid ? "ready" : "error",
        message: report.valid
          ? `Validation passed for ${report.importable_rows} importable rows.`
          : `Validation found ${report.errors.length} errors.`
      }));
    } catch (error) {
      setState((current) => ({
        ...current,
        status: "error",
        message: error instanceof Error ? error.message : "Could not validate CSV."
      }));
    }
  }

  async function handleCsvFile(file: File | undefined) {
    if (!file) return;

    try {
      const text = await file.text();
      const parsedCsv = parseCsv(text);
      setFileCsv({
        fileName: file.name,
        headers: parsedCsv.headers,
        rows: parsedCsv.rows,
        mapping: inferColumnMapping(parsedCsv.headers)
      });
      setValidation(null);
      setState((current) => ({
        ...current,
        status: "ready",
        message: `Loaded ${parsedCsv.rows.length} rows from ${file.name}. Review the column mapping before import.`
      }));
    } catch {
      setState((current) => ({
        ...current,
        status: "error",
        message: "Could not read the CSV file."
      }));
    }
  }

  function updateMapping(field: keyof ColumnMapping, header: string) {
    setFileCsv((current) => {
      if (!current) return current;

      return {
        ...current,
        mapping: {
          ...current.mapping,
          [field]: header
        }
      };
    });
  }

  async function importMappedCsv() {
    if (!fileCsv) return;

    const missingFields = unmappedRequiredFields(fileCsv.mapping);
    if (missingFields.length > 0) {
      setState((current) => ({
        ...current,
        status: "error",
        message: `Map all required fields before import. Missing: ${missingFields.join(", ")}.`
      }));
      return;
    }

    setState((current) => ({ ...current, status: "saving", message: "Importing mapped CSV..." }));

    try {
      const canonicalCsv = toCanonicalSignalCsv(fileCsv.rows, fileCsv.mapping);
      const report = await validateSignalCsv(canonicalCsv);
      setValidation({ source: "mapped", report });
      if (!report.valid) {
        setState((current) => ({
          ...current,
          status: "error",
          message: "Fix mapped CSV validation errors before import."
        }));
        return;
      }

      const result = await importSignalCsv(canonicalCsv);
      const { signals, candidates, demoDatasets } = await loadIntakeState();
      setState({
        status: "ready",
        message: `Mapped CSV imported ${result.imported}; skipped ${result.skipped_duplicates} duplicates.`,
        signals,
        candidates,
        demoDatasets
      });
    } catch (error) {
      setState((current) => ({
        ...current,
        status: "error",
        message: error instanceof Error ? error.message : "Could not import mapped CSV."
      }));
    }
  }

  async function validateMappedCsv() {
    if (!fileCsv) return;

    const missingFields = unmappedRequiredFields(fileCsv.mapping);
    if (missingFields.length > 0) {
      setState((current) => ({
        ...current,
        status: "error",
        message: `Map all required fields before validation. Missing: ${missingFields.join(", ")}.`
      }));
      return;
    }

    setState((current) => ({ ...current, status: "saving", message: "Validating mapped CSV..." }));

    try {
      const report = await validateSignalCsv(toCanonicalSignalCsv(fileCsv.rows, fileCsv.mapping));
      setValidation({ source: "mapped", report });
      setState((current) => ({
        ...current,
        status: report.valid ? "ready" : "error",
        message: report.valid
          ? `Validation passed for ${report.importable_rows} importable rows.`
          : `Validation found ${report.errors.length} errors.`
      }));
    } catch (error) {
      setState((current) => ({
        ...current,
        status: "error",
        message: error instanceof Error ? error.message : "Could not validate mapped CSV."
      }));
    }
  }

  async function acceptCandidate(candidate: ProblemCandidate) {
    if (candidate.review_status !== "pending") return;

    setState((current) => ({ ...current, status: "saving", message: "Creating draft problem..." }));

    try {
      const problem = await acceptProblemCandidate(candidate.candidate_id, {
        reviewer: currentUserEmail() ?? "local-user",
        note: "Accepted from Signal Intake."
      });
      const { signals, candidates, demoDatasets } = await loadIntakeState();
      setState((current) => ({
        ...current,
        status: "ready",
        message: `Created draft problem ${problem.problem_id}.`,
        signals,
        candidates,
        demoDatasets
      }));
    } catch (error) {
      setState((current) => ({
        ...current,
        status: "error",
        message: error instanceof Error ? error.message : "Could not promote candidate."
      }));
    }
  }

  async function rejectCandidate(candidate: ProblemCandidate) {
    if (candidate.review_status === "accepted" || candidate.review_status === "rejected") return;

    setState((current) => ({ ...current, status: "saving", message: "Rejecting candidate..." }));

    try {
      await rejectProblemCandidate(candidate.candidate_id, {
        reviewer: currentUserEmail() ?? "local-user",
        note:
          candidate.review_status === "duplicate"
            ? `Duplicate of ${candidate.duplicate_problem_id}.`
            : "Rejected from Signal Intake."
      });
      const { signals, candidates, demoDatasets } = await loadIntakeState();
      setState({
        status: "ready",
        message: `Rejected candidate ${candidate.candidate_id}.`,
        signals,
        candidates,
        demoDatasets
      });
    } catch (error) {
      setState((current) => ({
        ...current,
        status: "error",
        message: error instanceof Error ? error.message : "Could not reject candidate."
      }));
    }
  }

  const topCandidate = state.candidates[0];
  const duplicateCandidates = state.candidates.filter(
    (candidate) => candidate.review_status === "duplicate"
  ).length;
  const pendingCandidates = state.candidates.filter(
    (candidate) => candidate.review_status === "pending"
  ).length;
  const selectedDemoDataset =
    state.demoDatasets.find((dataset) => dataset.dataset_id === selectedDemoDatasetId) ??
    state.demoDatasets[0];

  return (
    <section className="signal-intake" aria-label="Signal intake">
      <div className="signal-intake-header">
        <div>
          <p className="eyebrow">{t.intake.eyebrow}</p>
          <h2>{t.intake.title}</h2>
        </div>
      </div>

      <div className="signal-intake-grid">
        <div>
          <span className="stat-label">{t.intake.persistedSignals}</span>
          <strong>{state.signals.length}</strong>
          <p>{state.message}</p>
        </div>
        <div>
          <span className="stat-label">{t.intake.problemCandidates}</span>
          <strong>{state.candidates.length}</strong>
          <p>
            {pendingCandidates} {t.intake.pendingReview} {duplicateCandidates} {t.intake.duplicateMatches}
          </p>
        </div>
        <div className="candidate-preview">
          <span className="stat-label">{t.intake.topCandidate}</span>
          {topCandidate ? (
            <>
              <strong>{topCandidate.title}</strong>
              <p>
                {topCandidate.signal_count} signals, {percent(topCandidate.confidence)} confidence,
                {candidateStatusLabels(t)[topCandidate.review_status].toLowerCase()}
              </p>
            </>
          ) : (
            <>
              <strong>{t.intake.noCandidate}</strong>
              <p>{t.intake.noCandidateHint}</p>
            </>
          )}
        </div>
      </div>

      {state.status === "loading" ? (
        <StateNotice tone="loading" title={t.intake.loadingIntake}>
          Connecting to the API, demo datasets, imported signals and generated candidates.
        </StateNotice>
      ) : null}

      {state.status === "saving" ? (
        <StateNotice tone="info" title={t.intake.actionInProgress}>
          {state.message}
        </StateNotice>
      ) : null}

      {state.status === "error" ? (
        <StateNotice tone="error" title={t.intake.apiUnavailable}>
          {state.message}
        </StateNotice>
      ) : null}

      <div className="demo-dataset-picker">
        <div>
          <label htmlFor="demo-dataset">{t.intake.demoDataset}</label>
          <p>
            Import packaged demo signals and customer context for a repeatable design-partner walkthrough.
          </p>
        </div>
        <select
          id="demo-dataset"
          value={selectedDemoDataset?.dataset_id ?? ""}
          onChange={(event) => setSelectedDemoDatasetId(event.target.value)}
        >
          {state.demoDatasets.map((dataset) => (
            <option key={dataset.dataset_id} value={dataset.dataset_id}>
              {dataset.title}
            </option>
          ))}
        </select>
        <div className="demo-dataset-summary">
          {selectedDemoDataset ? (
            <>
              <strong>{selectedDemoDataset.industry}</strong>
              <span>
                {selectedDemoDataset.signal_count} signals / {selectedDemoDataset.context_count} context rows
              </span>
              <p>{selectedDemoDataset.description}</p>
            </>
          ) : (
            <p>No demo datasets are available while the API is disconnected.</p>
          )}
        </div>
        <button
          type="button"
          disabled={state.status === "saving" || !selectedDemoDataset}
          onClick={importSelectedDemoDataset}
        >
          {t.intake.importDemo}
        </button>
      </div>

      <div className="candidate-review">
        <div className="candidate-review-header">
          <div>
            <h3>{t.intake.candidateReview}</h3>
            <p>{t.intake.candidateReviewHint}</p>
          </div>
          <span>{pendingCandidates} {t.intake.pending}</span>
        </div>

        {state.status === "loading" ? (
          <StateNotice tone="loading" title={t.intake.loadingCandidates}>
            Candidate groups will appear after the API returns imported signals.
          </StateNotice>
        ) : state.candidates.length > 0 ? (
          <ul className="candidate-list">
            {state.candidates.map((candidate) => (
              <li key={candidate.candidate_id} className={`candidate candidate-${candidate.review_status}`}>
                <div className="candidate-list-header">
                  <div>
                    <span className={`candidate-status candidate-status-${candidate.review_status}`}>
                      {candidateStatusLabels(t)[candidate.review_status]}
                    </span>
                    <strong>{candidate.title}</strong>
                    <small>
                      {candidate.candidate_id} / {candidate.journey} / {candidate.journey_stage}
                    </small>
                  </div>
                  <div className="candidate-score">
                    <strong>{percent(candidate.confidence)}</strong>
                    <span>{candidate.signal_count} signals</span>
                  </div>
                </div>
                <dl className="candidate-meta">
                  <div>
                    <dt>Customers</dt>
                    <dd>{candidate.customer_count}</dd>
                  </div>
                  <div>
                    <dt>Accounts</dt>
                    <dd>{candidate.account_count}</dd>
                  </div>
                  <div>
                    <dt>Sources</dt>
                    <dd>{candidate.sources.join(", ")}</dd>
                  </div>
                  <div>
                    <dt>Owner</dt>
                    <dd>{candidate.suggested_owner}</dd>
                  </div>
                </dl>
                {candidate.duplicate_problem_id ? (
                  <p className="candidate-duplicate">
                    Duplicate match: {candidate.duplicate_problem_id}. {candidate.duplicate_reason}
                  </p>
                ) : null}
                <p>{candidate.root_cause_hypothesis}</p>
                {candidate.evidence[0] ? (
                  <blockquote>&quot;{candidate.evidence[0].excerpt}&quot;</blockquote>
                ) : null}
                <CandidateIntelligence candidate={candidate} />
                {candidate.review_note ? (
                  <p className="candidate-review-note">
                    Reviewed by {candidate.reviewer}: {candidate.review_note}
                  </p>
                ) : null}
                <div className="candidate-actions">
                  <button
                    type="button"
                    disabled={state.status === "saving" || candidate.review_status !== "pending"}
                    onClick={() => acceptCandidate(candidate)}
                  >
                    {t.intake.acceptIntoQueue}
                  </button>
                  <button
                    type="button"
                    disabled={
                      state.status === "saving" ||
                      candidate.review_status === "accepted" ||
                      candidate.review_status === "rejected"
                    }
                    onClick={() => rejectCandidate(candidate)}
                  >
                    {t.common.reject}
                  </button>
                </div>
              </li>
            ))}
          </ul>
        ) : (
          <StateNotice tone="empty" title={t.intake.noCandidates}>
            Import a demo dataset, pasted CSV, or mapped CSV to generate review items.
          </StateNotice>
        )}
      </div>

      <div className="csv-import">
        <label htmlFor="signal-csv">{t.intake.pasteCsv}</label>
        <textarea
          id="signal-csv"
          value={csvText}
          rows={5}
          onChange={(event) => setCsvText(event.target.value)}
        />
        <button type="button" disabled={state.status === "saving"} onClick={importCsvText}>
          {t.intake.importPasted}
        </button>
        <button type="button" disabled={state.status === "saving"} onClick={validatePastedCsv}>
          {t.intake.validatePasted}
        </button>
      </div>

      <div className="csv-file-import">
        <div className="csv-file-header">
          <div>
            <label htmlFor="signal-csv-file">{t.intake.uploadCsv}</label>
            <p>{t.intake.uploadHint}</p>
          </div>
          <input
            id="signal-csv-file"
            type="file"
            accept=".csv,text/csv"
            onChange={(event) => handleCsvFile(event.target.files?.[0])}
          />
        </div>

        {fileCsv ? (
          <div className="csv-mapping">
            <div className="csv-mapping-summary">
              <strong>{fileCsv.fileName}</strong>
              <span>
                {fileCsv.rows.length} rows / {fileCsv.headers.length} source columns
              </span>
            </div>
            <div className="mapping-grid">
              {signalCsvFields.map((field) => (
                <label key={field}>
                  {field}
                  <select
                    value={fileCsv.mapping[field]}
                    onChange={(event) => updateMapping(field, event.target.value)}
                  >
                    <option value="">Select column</option>
                    {fileCsv.headers.map((header) => (
                      <option key={header} value={header}>
                        {header}
                      </option>
                    ))}
                  </select>
                </label>
              ))}
            </div>
            <div className="mapping-actions">
              <button type="button" disabled={state.status === "saving"} onClick={validateMappedCsv}>
                {t.intake.validateMapped}
              </button>
              <button type="button" disabled={state.status === "saving"} onClick={importMappedCsv}>
                {t.intake.importMapped}
              </button>
            </div>
          </div>
        ) : null}
      </div>

      {validation ? (
        <div className={`validation-report validation-${validation.report.valid ? "valid" : "invalid"}`}>
          <div className="validation-summary">
            <strong>
              {validation.report.valid ? "Validation passed" : "Validation needs attention"}
            </strong>
            <span>
              {validation.report.importable_rows}/{validation.report.total_rows} importable rows from{" "}
              {validation.source} CSV
            </span>
          </div>
          {validation.report.errors.length > 0 ? (
            <ul>
              {validation.report.errors.slice(0, 4).map((issue) => (
                <li key={`${issue.row_number}-${issue.field}-${issue.message}`}>
                  Error{issue.row_number ? ` row ${issue.row_number}` : ""}: {issue.message}
                </li>
              ))}
            </ul>
          ) : null}
          {validation.report.warnings.length > 0 ? (
            <ul>
              {validation.report.warnings.slice(0, 4).map((issue) => (
                <li key={`${issue.row_number}-${issue.field}-${issue.message}`}>
                  Warning{issue.row_number ? ` row ${issue.row_number}` : ""}: {issue.message}
                </li>
              ))}
            </ul>
          ) : null}
        </div>
      ) : null}
    </section>
  );
}
