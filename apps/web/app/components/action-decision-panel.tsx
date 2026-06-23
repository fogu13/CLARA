"use client";

import { useState } from "react";
import { getWorkflowState, submitApproval } from "../../lib/client-api";
import type { ActionProposal, ApprovalDecisionStatus, WorkflowState } from "../../lib/types";

type DecisionState = {
  state: "idle" | "saving" | "saved" | "error";
  message: string;
  workflow?: WorkflowState;
};

const decisionLabels: Record<ApprovalDecisionStatus, string> = {
  approved: "Approve",
  rejected: "Reject",
  needs_more_evidence: "Need evidence"
};

export function ActionDecisionPanel({
  problemId,
  action
}: {
  problemId: string;
  action: ActionProposal;
}) {
  const [decisionState, setDecisionState] = useState<DecisionState>({
    state: "idle",
    message: "No decision recorded in this session."
  });

  async function decide(decision: ApprovalDecisionStatus) {
    setDecisionState({ state: "saving", message: "Recording decision..." });

    try {
      const record = await submitApproval(problemId, {
        action_id: action.action_id,
        decision,
        reviewer: "demo_reviewer",
        note:
          decision === "approved"
            ? "Approved from the Action Queue."
            : "Decision recorded from the Action Queue."
      });
      const workflow = await getWorkflowState(problemId);

      setDecisionState({
        state: "saved",
        message: `${record.decision.replaceAll("_", " ")} recorded by ${record.reviewer}.`,
        workflow
      });
    } catch (error) {
      setDecisionState({
        state: "error",
        message: error instanceof Error ? error.message : "Could not record the decision."
      });
    }
  }

  const matchingExecution = decisionState.workflow?.executions.find(
    (execution) => execution.action_id === action.action_id
  );
  const matchingJiraDraft = decisionState.workflow?.jira_issue_drafts.find(
    (draft) => draft.action_id === action.action_id
  );

  return (
    <div className="decision-panel" aria-live="polite">
      <div className="decision-buttons">
        {(Object.keys(decisionLabels) as ApprovalDecisionStatus[]).map((decision) => (
          <button
            key={decision}
            type="button"
            disabled={decisionState.state === "saving"}
            onClick={() => decide(decision)}
          >
            {decisionLabels[decision]}
          </button>
        ))}
      </div>
      <p className={`decision-message decision-${decisionState.state}`}>{decisionState.message}</p>
      {matchingExecution ? (
        <p className="execution-message">
          Execution: {matchingExecution.status.replaceAll("_", " ")} in{" "}
          {matchingExecution.destination}
        </p>
      ) : null}
      {matchingJiraDraft ? (
        <p className="jira-draft-message">
          Jira draft: {matchingJiraDraft.draft_id} / {matchingJiraDraft.project_key}{" "}
          {matchingJiraDraft.issue_type} / {matchingJiraDraft.assignee}
        </p>
      ) : null}
    </div>
  );
}
