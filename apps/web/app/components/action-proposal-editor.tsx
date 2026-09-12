"use client";

import { useEffect, useState } from "react";
import { getWorkflowState, updateActionProposal } from "../../lib/client-api";
import { useI18n } from "../../lib/i18n";
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
  const { t } = useI18n();
  const [proposal, setProposal] = useState(action.proposal);
  const [owner, setOwner] = useState(action.owner);
  const [destination, setDestination] = useState(action.destination);
  const [riskLevel, setRiskLevel] = useState<RiskLevel>(action.risk_level);
  const [approvalState, setApprovalState] = useState(action.approval_state);
  const [briefChannel, setBriefChannel] = useState(action.intervention_brief?.recommended_channel ?? "");
  const [briefContent, setBriefContent] = useState(action.intervention_brief?.content_brief ?? "");
  const [editorState, setEditorState] = useState<EditorState>({
    status: "idle",
    message: "Action proposal can be refined before approval."
  });
  // An approval signs one revision of the action; the API refuses edits while
  // the latest decision is `approved` (409). Mirror that here so the editor is
  // not offered at all — the decision panel is where a rejection is recorded.
  const [approvedLatest, setApprovedLatest] = useState(false);

  useEffect(() => {
    let cancelled = false;
    getWorkflowState(problemId)
      .then((workflow) => {
        if (cancelled) return;
        const latest = workflow.approvals
          .filter((approval) => approval.action_id === action.action_id)
          .slice(-1)[0];
        setApprovedLatest(latest?.decision === "approved");
      })
      .catch(() => {
        // Unknown state: leave the editor available; the API still enforces the lock.
      });
    return () => {
      cancelled = true;
    };
  }, [problemId, action.action_id]);

  if (!problemId.startsWith("PRB-DRAFT-")) {
    return null;
  }

  if (approvedLatest) {
    return (
      <p className="action-editor-message action-editor-idle" aria-label={`Edit ${action.action_id}`}>
        {t.detail.actionEditorLocked}
      </p>
    );
  }

  async function saveAction() {
    setEditorState({ status: "saving", message: "Saving action proposal..." });

    try {
      await updateActionProposal(problemId, action.action_id, {
        proposal,
        owner,
        destination,
        risk_level: riskLevel,
        approval_state: approvalState,
        intervention_brief: action.intervention_brief
          ? {
              ...action.intervention_brief,
              recommended_channel: briefChannel,
              content_brief: briefContent
            }
          : undefined
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
      {action.intervention_brief ? (
        <div className="action-editor-grid">
          <label>
            Intervention channel
            <input value={briefChannel} onChange={(event) => setBriefChannel(event.target.value)} />
          </label>
          <label>
            Content brief
            <textarea value={briefContent} rows={3} onChange={(event) => setBriefContent(event.target.value)} />
          </label>
        </div>
      ) : null}
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
