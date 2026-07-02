"use client";

import { useEffect, useState } from "react";
import {
  getOutcomeSnapshot,
  recordLearningConclusion,
  recordOutcomeMeasurement
} from "../../lib/client-api";
import type { LearningStatus, OutcomeContract, OutcomeSnapshot } from "../../lib/types";
import { formatMetric } from "@/lib/format";

type PanelState = {
  status: "loading" | "ready" | "saving" | "error";
  message: string;
  snapshot?: OutcomeSnapshot;
};

const outcomeLabels: Record<OutcomeSnapshot["status"], string> = {
  not_measured: "Not measured",
  target_met: "Target met",
  improving: "Improving",
  not_improved: "Not improved"
};

const learningStatuses: LearningStatus[] = [
  "worked",
  "partially_worked",
  "did_not_work",
  "inconclusive",
  "measurement_invalid"
];


function directionLabel(direction: OutcomeSnapshot["improvement_direction"] | undefined): string {
  if (!direction) return "Direction loading";
  return direction === "increase" ? "Higher is better" : "Lower is better";
}

export function OutcomeMeasurementPanel({
  problemId,
  contract
}: {
  problemId: string;
  contract: OutcomeContract;
}) {
  const [observedValue, setObservedValue] = useState("");
  const [notes, setNotes] = useState("");
  const [learningStatus, setLearningStatus] = useState<LearningStatus>("inconclusive");
  const [summary, setSummary] = useState("");
  const [limitations, setLimitations] = useState("");
  const [nextStep, setNextStep] = useState("");
  const [state, setState] = useState<PanelState>({
    status: "loading",
    message: "Loading outcome status..."
  });

  useEffect(() => {
    getOutcomeSnapshot(problemId)
      .then((snapshot) => {
        setState({ status: "ready", message: "Outcome snapshot loaded.", snapshot });
      })
      .catch(() => {
        setState({
          status: "error",
          message: "API is not connected. Start the backend to record outcomes."
        });
      });
  }, [problemId]);

  async function submitOutcome() {
    const value = Number(observedValue);
    if (!Number.isFinite(value)) {
      setState((current) => ({ ...current, status: "error", message: "Observed value must be numeric." }));
      return;
    }

    setState((current) => ({ ...current, status: "saving", message: "Recording outcome..." }));

    try {
      await recordOutcomeMeasurement(problemId, {
        problem_id: problemId,
        metric: contract.primary_metric,
        observed_value: value,
        measured_at: new Date().toISOString(),
        notes: notes || undefined
      });
      const snapshot = await getOutcomeSnapshot(problemId);
      setState({ status: "ready", message: "Outcome measurement recorded.", snapshot });
      window.dispatchEvent(new CustomEvent("clara:outcome-recorded"));
    } catch (error) {
      setState((current) => ({
        ...current,
        status: "error",
        message: error instanceof Error ? error.message : "Could not record outcome."
      }));
    }
  }

  async function submitLearning() {
    if (!summary.trim() || !limitations.trim()) {
      setState((current) => ({
        ...current,
        status: "error",
        message: "Learning summary and limitations are required."
      }));
      return;
    }

    setState((current) => ({ ...current, status: "saving", message: "Recording learning review..." }));

    try {
      await recordLearningConclusion(problemId, {
        learning_status: learningStatus,
        summary,
        limitations,
        next_step: nextStep || undefined
      });
      setState((current) => ({ ...current, status: "ready", message: "Learning review recorded." }));
      window.dispatchEvent(new CustomEvent("clara:outcome-recorded"));
    } catch (error) {
      setState((current) => ({
        ...current,
        status: "error",
        message: error instanceof Error ? error.message : "Could not record learning review."
      }));
    }
  }

  const snapshot = state.snapshot;
  const status = snapshot?.status ?? "not_measured";

  return (
    <div className="outcome-measurement-panel" aria-live="polite">
      <div className="outcome-status-row">
        <span className={`outcome-status outcome-${status}`}>{outcomeLabels[status]}</span>
        <span>Latest: {formatMetric(snapshot?.latest_value)}</span>
        <span>{directionLabel(snapshot?.improvement_direction)}</span>
      </div>
      <div className="outcome-input-row">
        <label>
          Observed value
          <input
            inputMode="decimal"
            placeholder="0.72"
            value={observedValue}
            onChange={(event) => setObservedValue(event.target.value)}
          />
        </label>
        <label>
          Notes
          <input
            placeholder="Holdout readout, week 4"
            value={notes}
            onChange={(event) => setNotes(event.target.value)}
          />
        </label>
        <button type="button" disabled={state.status === "saving"} onClick={submitOutcome}>
          Record outcome
        </button>
      </div>
      <div className="outcome-input-row">
        <label>
          Learning status
          <select
            value={learningStatus}
            onChange={(event) => setLearningStatus(event.target.value as LearningStatus)}
          >
            {learningStatuses.map((status) => (
              <option key={status} value={status}>
                {status.replaceAll("_", " ")}
              </option>
            ))}
          </select>
        </label>
      </div>
      <div className="outcome-input-row">
        <label>
          Summary
          <input
            placeholder="What did we learn? Do not include personal data."
            value={summary}
            onChange={(event) => setSummary(event.target.value)}
          />
        </label>
        <label>
          Limitations
          <input
            placeholder="Measurement limits, caveats or missing evidence"
            value={limitations}
            onChange={(event) => setLimitations(event.target.value)}
          />
        </label>
        <label>
          Next step
          <input value={nextStep} onChange={(event) => setNextStep(event.target.value)} />
        </label>
        <button type="button" disabled={state.status === "saving"} onClick={submitLearning}>
          Record learning
        </button>
      </div>
      <p className={`outcome-message outcome-message-${state.status}`}>{state.message}</p>
    </div>
  );
}
