"use client";

import { currentUserEmail } from "@/lib/auth-client";

import { useEffect, useMemo, useState } from "react";
import { getWorkflowState, transitionProblem } from "../../lib/client-api";
import type { ProblemRecord, ProblemStatus, WorkflowState } from "../../lib/types";
import { StateNotice } from "./state-notice";

const lifecycleStatuses: ProblemStatus[] = [
  "validation_required",
  "approval_needed",
  "in_progress",
  "blocked_by_policy",
  "resolved"
];

const defaultNextStatus: Partial<Record<ProblemStatus, ProblemStatus>> = {
  validation_required: "approval_needed",
  approval_needed: "in_progress",
  in_progress: "resolved",
  blocked_by_policy: "approval_needed"
};

type LifecycleState = {
  status: "loading" | "ready" | "saving" | "error";
  message: string;
  workflow?: WorkflowState;
};

function statusLabel(status: ProblemStatus): string {
  return status.replaceAll("_", " ");
}

function formatTimestamp(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;

  return new Intl.DateTimeFormat("en", {
    dateStyle: "medium",
    timeStyle: "short"
  }).format(date);
}

function initialTransitionTarget(status: ProblemStatus): ProblemStatus {
  return defaultNextStatus[status] ?? lifecycleStatuses.find((candidate) => candidate !== status) ?? status;
}

export function ProblemLifecyclePanel({ problem }: { problem: ProblemRecord }) {
  const initialTargetStatus = initialTransitionTarget(problem.status);
  const [targetStatus, setTargetStatus] = useState<ProblemStatus>(initialTargetStatus);
  const [note, setNote] = useState("");
  const [state, setState] = useState<LifecycleState>({
    status: "loading",
    message: "Loading problem timeline..."
  });
  const canTransition = problem.problem_id.startsWith("PRB-DRAFT-");
  const transitionOptions = useMemo(
    () => lifecycleStatuses.filter((status) => status !== problem.status),
    [problem.status]
  );

  useEffect(() => {
    getWorkflowState(problem.problem_id)
      .then((workflow) => {
        setState({ status: "ready", message: "Timeline loaded.", workflow });
      })
      .catch(() => {
        setState({
          status: "error",
          message: "API is not connected. Start the backend to load lifecycle history."
        });
      });
  }, [problem.problem_id]);

  async function moveStatus() {
    if (targetStatus === problem.status) {
      setState((current) => ({
        ...current,
        status: "error",
        message: "Choose a new lifecycle status."
      }));
      return;
    }

    setState((current) => ({ ...current, status: "saving", message: "Recording transition..." }));

    try {
      await transitionProblem(problem.problem_id, {
        target_status: targetStatus,
        // The API replaces this with the verified principal when auth is on;
        // locally it records the signed-in email (or a neutral placeholder).
        actor: currentUserEmail() ?? "local-user",
        note: note || undefined
      });
      const workflow = await getWorkflowState(problem.problem_id);
      setState({
        status: "ready",
        message: "Lifecycle transition recorded. Refreshing queue...",
        workflow
      });
      window.location.reload();
    } catch (error) {
      setState((current) => ({
        ...current,
        status: "error",
        message: error instanceof Error ? error.message : "Could not record lifecycle transition."
      }));
    }
  }

  const timeline = state.workflow?.timeline ?? [];

  return (
    <section className="lifecycle-panel" aria-label="Problem lifecycle and timeline">
      <div className="lifecycle-header">
        <div>
          <h3>Lifecycle</h3>
          <p>Current status: {statusLabel(problem.status)}</p>
        </div>
        {canTransition ? (
          <div className="lifecycle-controls">
            <label>
              Move to
              <select
                value={targetStatus}
                onChange={(event) => setTargetStatus(event.target.value as ProblemStatus)}
              >
                {transitionOptions.map((status) => (
                  <option key={status} value={status}>
                    {statusLabel(status)}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Note
              <input
                placeholder="Why this state changed"
                value={note}
                onChange={(event) => setNote(event.target.value)}
              />
            </label>
            <button type="button" disabled={state.status === "saving"} onClick={moveStatus}>
              Move status
            </button>
          </div>
        ) : (
          <p className="lifecycle-readonly">Seed demo problems are read-only.</p>
        )}
      </div>
      {state.status === "loading" ? (
        <StateNotice tone="loading" title="Loading lifecycle history">
          Reading timeline events, approvals, execution drafts and outcome measurements.
        </StateNotice>
      ) : null}
      {state.status === "saving" ? (
        <StateNotice tone="info" title="Recording lifecycle transition">
          {state.message}
        </StateNotice>
      ) : null}
      {state.status === "error" ? (
        <StateNotice tone="error" title="Lifecycle history unavailable">
          {state.message}
        </StateNotice>
      ) : null}
      {state.status === "ready" && timeline.length > 0 ? (
        <p className={`lifecycle-message lifecycle-${state.status}`}>{state.message}</p>
      ) : null}
      {timeline.length > 0 ? (
        <ol className="timeline-list">
          {timeline.map((event) => (
            <li key={event.event_id}>
              <div>
                <strong>{event.label}</strong>
                <span>{formatTimestamp(event.created_at)}</span>
              </div>
              <p>{event.detail}</p>
              {event.actor ? <small>{event.actor}</small> : null}
            </li>
          ))}
        </ol>
      ) : state.status === "ready" ? (
        <StateNotice tone="empty" title="No timeline events yet">
          Approvals, lifecycle moves, execution drafts and outcome measurements will appear here.
        </StateNotice>
      ) : null}
    </section>
  );
}
