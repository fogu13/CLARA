"use client";

import { useEffect, useMemo, useState } from "react";
import sampleContext from "../../../../data/sample_customer_context.json";
import {
  getCustomerContext,
  getCustomerContextCompleteness,
  importCustomerContext,
  importCustomerContextCsv,
  validateCustomerContextCsv
} from "../../lib/client-api";
import type {
  CustomerContextCompletenessReport,
  CustomerContextRecord,
  CustomerContextValidationReport
} from "../../lib/types";
import { StateNotice } from "./state-notice";

type ContextState = {
  status: "loading" | "ready" | "saving" | "error";
  message: string;
  records: CustomerContextRecord[];
  completeness?: CustomerContextCompletenessReport;
};

type ValidationState = {
  report: CustomerContextValidationReport;
};

const defaultContextCsv =
  "customer_id,account_id,account_name,parent_account_id,parent_account_name,segment,lifecycle_stage,plan_tier,contact_role,account_value,renewal_date,consent_status,health_score,owner,region\n";

function formatCurrency(value: number): string {
  return new Intl.NumberFormat("en", {
    maximumFractionDigits: 0,
    style: "currency",
    currency: "USD"
  }).format(value);
}

function contextStats(records: CustomerContextRecord[]) {
  const accountValues = new Map<string, number>();
  let consentGranted = 0;

  for (const record of records) {
    accountValues.set(
      record.account_id,
      Math.max(accountValues.get(record.account_id) ?? 0, record.account_value)
    );
    if (record.consent_status === "granted") {
      consentGranted += 1;
    }
  }

  return {
    accounts: accountValues.size,
    accountValue: [...accountValues.values()].reduce((total, value) => total + value, 0),
    consentCoverage: records.length ? consentGranted / records.length : 0
  };
}

function percent(value: number): string {
  return `${Math.round(value * 100)}%`;
}

function readinessLabel(value: string): string {
  return value.replaceAll("_", " ");
}

export function CustomerContextPanel() {
  const [csvText, setCsvText] = useState(defaultContextCsv);
  const [validation, setValidation] = useState<ValidationState | null>(null);
  const [state, setState] = useState<ContextState>({
    status: "loading",
    message: "Loading customer context...",
    records: []
  });

  useEffect(() => {
    Promise.all([getCustomerContext(), getCustomerContextCompleteness()])
      .then(([records, completeness]) => {
        setState({
          status: "ready",
          message: "Customer context is connected to the API.",
          records,
          completeness
        });
      })
      .catch(() => {
        setState({
          status: "error",
          message: "API is not connected. Start the backend to import account context.",
          records: sampleContext as CustomerContextRecord[],
          completeness: undefined
        });
      });
  }, []);

  const stats = useMemo(() => contextStats(state.records), [state.records]);

  async function refreshContext(message: string) {
    const [records, completeness] = await Promise.all([
      getCustomerContext(),
      getCustomerContextCompleteness()
    ]);
    setState({
      status: "ready",
      message,
      records,
      completeness
    });
  }

  async function importSampleContext() {
    setState((current) => ({ ...current, status: "saving", message: "Importing sample context..." }));

    try {
      const result = await importCustomerContext(sampleContext as CustomerContextRecord[]);
      await refreshContext(
        `Imported ${result.imported}; updated ${result.updated} customer context records.`
      );
    } catch (error) {
      setState((current) => ({
        ...current,
        status: "error",
        message: error instanceof Error ? error.message : "Could not import sample context."
      }));
    }
  }

  async function validateCsv() {
    setState((current) => ({ ...current, status: "saving", message: "Validating context CSV..." }));

    try {
      const report = await validateCustomerContextCsv(csvText);
      setValidation({ report });
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
        message: error instanceof Error ? error.message : "Could not validate context CSV."
      }));
    }
  }

  async function importCsv() {
    setState((current) => ({ ...current, status: "saving", message: "Importing context CSV..." }));

    try {
      const report = await validateCustomerContextCsv(csvText);
      setValidation({ report });
      if (!report.valid) {
        setState((current) => ({
          ...current,
          status: "error",
          message: "Fix context CSV validation errors before import."
        }));
        return;
      }

      const result = await importCustomerContextCsv(csvText);
      await refreshContext(
        `Context CSV imported ${result.imported}; updated ${result.updated} records.`
      );
    } catch (error) {
      setState((current) => ({
        ...current,
        status: "error",
        message: error instanceof Error ? error.message : "Could not import context CSV."
      }));
    }
  }

  return (
    <section className="signal-intake context-intake" aria-label="Customer and account context import">
      <div className="signal-intake-header">
        <div>
          <p className="eyebrow">Customer Context</p>
          <h2>Import customer and account context</h2>
        </div>
        <button type="button" disabled={state.status === "saving"} onClick={importSampleContext}>
          Import sample context
        </button>
      </div>

      <div className="signal-intake-grid">
        <div>
          <span className="stat-label">Context records</span>
          <strong>{state.records.length}</strong>
          <p>{state.message}</p>
        </div>
        <div>
          <span className="stat-label">Accounts</span>
          <strong>{stats.accounts}</strong>
          <p>{formatCurrency(stats.accountValue)} represented by imported context.</p>
        </div>
        <div>
          <span className="stat-label">Consent coverage</span>
          <strong>{percent(stats.consentCoverage)}</strong>
          <p>Available for governance checks before customer-facing recovery.</p>
        </div>
      </div>

      {state.completeness ? (
        <div className="context-completeness">
          <div className="context-completeness-header">
            <div>
              <span className={`readiness readiness-${state.completeness.readiness_level}`}>
                {readinessLabel(state.completeness.readiness_level)}
              </span>
              <strong>{percent(state.completeness.readiness_score)}</strong>
            </div>
            <p>
              {state.completeness.complete_records}/{state.completeness.total_records} rows include
              core scoring, routing and governance fields.
            </p>
          </div>
          <div className="context-completeness-grid">
            {state.completeness.metrics
              .filter((metric) =>
                [
                  "account_value",
                  "consent_status",
                  "health_score",
                  "owner",
                  "contact_role",
                  "lifecycle_stage"
                ].includes(metric.field)
              )
              .map((metric) => (
                <div key={metric.field}>
                  <span>{metric.label}</span>
                  <strong>{percent(metric.coverage)}</strong>
                </div>
              ))}
          </div>
          {state.completeness.warnings.length > 0 ? (
            <ul className="context-completeness-warnings">
              {state.completeness.warnings.slice(0, 3).map((warning) => (
                <li key={`${warning.field}-${warning.message}`}>{warning.message}</li>
              ))}
            </ul>
          ) : null}
        </div>
      ) : null}

      {state.status === "loading" ? (
        <StateNotice tone="loading" title="Loading customer context">
          Connecting to the API and reading account metadata.
        </StateNotice>
      ) : null}

      {state.status === "saving" ? (
        <StateNotice tone="info" title="Context import in progress">
          {state.message}
        </StateNotice>
      ) : null}

      {state.status === "error" ? (
        <StateNotice tone="error" title="Customer context API unavailable">
          {state.message}
        </StateNotice>
      ) : null}

      {state.status === "ready" && state.records.length === 0 ? (
        <StateNotice tone="empty" title="No customer context loaded">
          Import a demo dataset, sample context, or customer context CSV to enrich candidate review.
        </StateNotice>
      ) : null}

      <div className="csv-import">
        <label htmlFor="context-csv">Paste customer context CSV</label>
        <textarea
          id="context-csv"
          value={csvText}
          rows={4}
          onChange={(event) => setCsvText(event.target.value)}
        />
        <button type="button" disabled={state.status === "saving"} onClick={importCsv}>
          Import context CSV
        </button>
        <button type="button" disabled={state.status === "saving"} onClick={validateCsv}>
          Validate context CSV
        </button>
      </div>

      {validation ? (
        <div className={`validation-report validation-${validation.report.valid ? "valid" : "invalid"}`}>
          <div className="validation-summary">
            <strong>
              {validation.report.valid ? "Validation passed" : "Validation needs attention"}
            </strong>
            <span>
              {validation.report.importable_rows}/{validation.report.total_rows} importable context rows
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
