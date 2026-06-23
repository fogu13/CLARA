"use client";

import { useState } from "react";
import { updateActionProposal } from "../../lib/client-api";
import type { ActionProposal, RiskLevel } from "../../lib/types";

type EditorState = {
  status: "idle" | "saving" | "saved" | "error";
  message: string;
};

const riskLevels: RiskLevel[] = ["low", "medium", "high", "critical"];

export function ActionProposalEditor({
  problemId,
  action
}: {
  problemId: string;
  action: ActionProposal;
}) {
  const [proposal, setProposal] = useState(action.proposal);
  const [owner, setOwner] = useState(action.owner);
  const [destination, setDestination] = useState(action.destination);
  const [riskLevel, setRiskLevel] = useState<RiskLevel>(action.risk_level);
  const [approvalState, setApprovalState] = useState(action.approval_state);
  const [editorState, setEditorState] = useState<EditorState>({
    status: "idle",
    message: "Action proposal can be refined before approval."
  });

  if (!problemId.startsWith("PRB-DRAFT-")) {
    return null;
  }

  async function saveAction() {
    setEditorState({ status: "saving", message: "Saving action proposal..." });

    try {
      await updateActionProposal(problemId, action.action_id, {
        proposal,
        owner,
        destination,
        risk_level: riskLevel,
        approval_state: approvalState
      });
      setEditorState({
        status: "saved",
        message: "Action proposal saved. Refreshing queue..."
      });
      window.location.reload();
    } catch (error) {
      setEditorState({
        status: "error",
        message: error instanceof Error ? error.message : "Could not save action proposal."
      });
    }
  }

  return (
    <div className="action-editor" aria-label={`Edit ${action.action_id}`}>
      <div className="action-editor-grid">
        <label>
          Owner
          <input value={owner} onChange={(event) => setOwner(event.target.value)} />
        </label>
        <label>
          Destination
          <input value={destination} onChange={(event) => setDestination(event.target.value)} />
        </label>
        <label>
          Risk
          <select
            value={riskLevel}
            onChange={(event) => setRiskLevel(event.target.value as RiskLevel)}
          >
            {riskLevels.map((level) => (
              <option key={level} value={level}>
                {level}
              </option>
            ))}
          </select>
        </label>
        <label>
          Approval state
          <input value={approvalState} onChange={(event) => setApprovalState(event.target.value)} />
        </label>
      </div>
      <label>
        Proposal
        <textarea value={proposal} rows={3} onChange={(event) => setProposal(event.target.value)} />
      </label>
      <div className="action-editor-actions">
        <button type="button" disabled={editorState.status === "saving"} onClick={saveAction}>
          Save action
        </button>
        <p className={`action-editor-message action-editor-${editorState.status}`}>
          {editorState.message}
        </p>
      </div>
    </div>
  );
}
