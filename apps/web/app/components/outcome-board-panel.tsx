"use client";

import { useEffect, useState } from "react";
import { getOutcomeBoard } from "../../lib/client-api";
import type { OutcomeBoard, OutcomeBoardItem } from "../../lib/types";
import { StateNotice } from "./state-notice";

type BoardState = {
  status: "loading" | "ready" | "error";
  message: string;
  board?: OutcomeBoard;
};

const outcomeLabels: Record<OutcomeBoardItem["outcome_status"], string> = {
  not_measured: "Not measured",
  target_met: "Target met",
  improving: "Improving",
  not_improved: "Not improved"
};

function formatMetric(value: number | null | undefined): string {
  if (value === null || value === undefined) return "None";
  if (Math.abs(value) < 1) return `${Math.round(value * 100)}%`;
  return String(value);
}

function percent(value: number): string {
  return `${Math.round(value * 100)}%`;
}

function directionLabel(direction: OutcomeBoardItem["improvement_direction"]): string {
  return direction === "increase" ? "Higher is better" : "Lower is better";
}

function learningLabel(status: OutcomeBoardItem["latest_learning_status"]): string {
  return status ? status.replaceAll("_", " ") : "Not reviewed";
}

export function OutcomeBoardPanel() {
  const [state, setState] = useState<BoardState>({
    status: "loading",
    message: "Loading outcome board..."
  });

  async function loadBoard() {
    setState((current) => ({
      ...current,
      status: current.board ? "ready" : "loading",
      message: current.board ? "Refreshing outcome board..." : "Loading outcome board..."
    }));

    try {
      const board = await getOutcomeBoard();
      setState({ status: "ready", message: "Outcome board loaded.", board });
    } catch {
      setState({
        status: "error",
        message: "API is not connected. Start the backend to view outcome learning."
      });
    }
  }

  useEffect(() => {
    void loadBoard();

    window.addEventListener("odradek:outcome-recorded", loadBoard);
    return () => window.removeEventListener("odradek:outcome-recorded", loadBoard);
  }, []);

  const board = state.board;

  return (
    <section className="outcome-board" aria-live="polite">
      <header className="outcome-board-header">
        <div>
          <p className="eyebrow">Outcome Learning</p>
          <h2>Outcome Board</h2>
        </div>
        <div className="outcome-board-actions">
          <p className={`outcome-board-message outcome-board-message-${state.status}`}>{state.message}</p>
          <button type="button" onClick={loadBoard} disabled={state.status === "loading"}>
            Refresh
          </button>
        </div>
      </header>

      {state.status === "loading" && !board ? (
        <StateNotice tone="loading" title="Loading outcome board">
          Reading the latest outcome contracts and measurements from the API.
        </StateNotice>
      ) : null}

      {state.status === "error" ? (
        <StateNotice tone="error" title="Outcome board unavailable">
          {state.message}
        </StateNotice>
      ) : null}

      <div className="outcome-board-stats" aria-label="Outcome summary">
        <div>
          <span className="stat-label">Problems tracked</span>
          <strong>{board?.total ?? 0}</strong>
        </div>
        <div>
          <span className="stat-label">Target met</span>
          <strong>{board?.target_met ?? 0}</strong>
        </div>
        <div>
          <span className="stat-label">Improving</span>
          <strong>{board?.improving ?? 0}</strong>
        </div>
        <div>
          <span className="stat-label">Not measured</span>
          <strong>{board?.not_measured ?? 0}</strong>
        </div>
        <div>
          <span className="stat-label">Learning reviewed</span>
          <strong>
            {(board?.learning_worked ?? 0) +
              (board?.learning_partially_worked ?? 0) +
              (board?.learning_did_not_work ?? 0) +
              (board?.learning_inconclusive ?? 0) +
              (board?.learning_measurement_invalid ?? 0)}
          </strong>
        </div>
      </div>

      {board?.items.length ? (
        <ul className="outcome-board-list">
          {board.items.map((item) => (
            <li key={item.problem_id}>
              <div className="outcome-board-item-main">
                <span className={`outcome-status outcome-${item.outcome_status}`}>
                  {outcomeLabels[item.outcome_status]}
                </span>
                <div>
                  <strong>{item.title}</strong>
                  <small>
                    {item.problem_id} / {item.owner} / {item.problem_status.replaceAll("_", " ")}
                  </small>
                </div>
              </div>
              <dl className="outcome-board-metrics">
                <div>
                  <dt>Impact</dt>
                  <dd>
                    {percent(item.impact_score)} {item.impact_band}
                  </dd>
                </div>
                <div>
                  <dt>Metric</dt>
                  <dd>{item.metric}</dd>
                </div>
                <div>
                  <dt>Latest</dt>
                  <dd>{formatMetric(item.latest_value)}</dd>
                </div>
                <div>
                  <dt>Target</dt>
                  <dd>{formatMetric(item.success_threshold)}</dd>
                </div>
                <div>
                  <dt>Direction</dt>
                  <dd>{directionLabel(item.improvement_direction)}</dd>
                </div>
                <div>
                  <dt>Owner</dt>
                  <dd>{item.responsible_owner}</dd>
                </div>
                <div>
                  <dt>Learning</dt>
                  <dd>{learningLabel(item.latest_learning_status)}</dd>
                </div>
              </dl>
            </li>
          ))}
        </ul>
      ) : state.status === "ready" ? (
        <StateNotice tone="empty" title="No outcome contracts available">
          Create or import problems with outcome contracts before using the outcome board.
        </StateNotice>
      ) : null}
    </section>
  );
}
