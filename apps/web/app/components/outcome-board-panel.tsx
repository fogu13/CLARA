"use client";

import { useEffect, useState } from "react";
import { getOutcomeBoard } from "../../lib/client-api";
import type { OutcomeBoard, OutcomeBoardItem } from "../../lib/types";
import { StateNotice } from "./state-notice";
import { formatMetric, percent } from "@/lib/format";
import { useI18n } from "@/lib/i18n";

type BoardState = {
  status: "loading" | "ready" | "error";
  message: string;
  board?: OutcomeBoard;
};

function outcomeLabels(t: ReturnType<typeof useI18n>["t"]): Record<OutcomeBoardItem["outcome_status"], string> {
  return {
    not_measured: t.outcomeBoard.notMeasured,
    target_met: t.outcomeBoard.targetMet,
    improving: t.outcomeBoard.improving,
    not_improved: t.outcomeBoard.notImproved
  };
}



function directionLabel(direction: OutcomeBoardItem["improvement_direction"], t: ReturnType<typeof useI18n>["t"]): string {
  return direction === "increase" ? t.outcomeBoard.higherBetter : t.outcomeBoard.lowerBetter;
}

function learningLabel(status: OutcomeBoardItem["latest_learning_status"], t: ReturnType<typeof useI18n>["t"]): string {
  return status ? status.replaceAll("_", " ") : t.outcomeBoard.notReviewed;
}

export function OutcomeBoardPanel() {
  const { t } = useI18n();
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

    window.addEventListener("clara:outcome-recorded", loadBoard);
    return () => window.removeEventListener("clara:outcome-recorded", loadBoard);
  }, []);

  const board = state.board;

  return (
    <section className="outcome-board" aria-live="polite">
      <header className="outcome-board-header">
        <div>
          <p className="eyebrow">Outcome Learning</p>
          <h2>{t.outcomeBoard.title}</h2>
        </div>
        <div className="outcome-board-actions">
          <p className={`outcome-board-message outcome-board-message-${state.status}`}>{state.message}</p>
          <button type="button" onClick={loadBoard} disabled={state.status === "loading"}>
            Refresh
          </button>
        </div>
      </header>

      {state.status === "loading" && !board ? (
        <StateNotice tone="loading" title={t.outcomeBoard.loading}>
          Reading the latest outcome contracts and measurements from the API.
        </StateNotice>
      ) : null}

      {state.status === "error" ? (
        <StateNotice tone="error" title={t.outcomeBoard.unavailable}>
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
                  {outcomeLabels(t)[item.outcome_status]}
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
                  <dt>{t.outcomeBoard.impact}</dt>
                  <dd>
                    {percent(item.impact_score)} {item.impact_band}
                  </dd>
                </div>
                <div>
                  <dt>{t.outcomeBoard.metric}</dt>
                  <dd>{item.metric}</dd>
                </div>
                <div>
                  <dt>{t.outcomeBoard.latest}</dt>
                  <dd>
                    {formatMetric(item.latest_value)}
                    {item.measurement_source === "manual" && item.latest_value != null ? (
                      <span className="outcome-board-manual-note"> · {t.outcomeBoard.manualValue}</span>
                    ) : null}
                  </dd>
                </div>
                <div>
                  <dt>{t.outcomeBoard.target}</dt>
                  <dd>{formatMetric(item.success_threshold)}</dd>
                </div>
                <div>
                  <dt>{t.outcomeBoard.direction}</dt>
                  <dd>{directionLabel(item.improvement_direction, t)}</dd>
                </div>
                {item.evidence_grade ? (
                  <div>
                    <dt title={t.outcomeBoard.gradeTooltip} style={{ cursor: "help" }}>
                      {t.outcomeBoard.grade}
                    </dt>
                    <dd>{item.evidence_grade}</dd>
                  </div>
                ) : null}
                <div>
                  <dt>{t.common.owner}</dt>
                  <dd>{item.responsible_owner}</dd>
                </div>
                <div>
                  <dt>{t.outcomeBoard.learning}</dt>
                  <dd>{learningLabel(item.latest_learning_status, t)}</dd>
                </div>
              </dl>
            </li>
          ))}
        </ul>
      ) : state.status === "ready" ? (
        <StateNotice tone="empty" title={t.outcomeBoard.empty}>
          Create or import problems with outcome contracts before using the outcome board.
        </StateNotice>
      ) : null}
    </section>
  );
}
