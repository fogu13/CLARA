"use client";

import { useEffect, useState } from "react";
import { getWorkflowState, submitApproval } from "../../lib/client-api";
import type { ActionProposal, ActionProposalChange, ApprovalDecisionStatus, WorkflowState } from "../../lib/types";

type DecisionState = {
  state: "loading" | "idle" | "saving" | "saved" | "error";
  message: string;
  workflow?: WorkflowState;
};

const decisionLabels: Record<ApprovalDecisionStatus, string> = {
  approved: "Approve",
  rejected: "Reject",
  needs_more_evidence: "Need evidence"
};

function latestApproval(workflow: WorkflowState | undefined, actionId: string) {
  return workflow?.approvals.filter((approval) => approval.action_id === actionId).slice(-1)[0];
}

function approvalMessage(approval: NonNullable<ReturnType<typeof latestApproval>>): string {
  return `${approval.decision.replaceAll("_", " ")} recorded by ${approval.reviewer}.`;
}

function diffValue(value: unknown): string {
  if (value && typeof value === "object") return JSON.stringify(value);
  return String(value ?? "");
}

function pendingChanges(action: ActionProposal): ActionProposalChange[] {
  if (!action.original_snapshot) return [];

  return (["owner", "destination", "proposal", "risk_level", "approval_state", "intervention_brief"] as const).flatMap(
    (field) => {
      const before = diffValue(action.original_snapshot?.[field]);
      const after = diffValue(action[field]);
      return before === after ? [] : [{ field, before, after }];
    }
  );
}

function ActionDiff({ title, changes }: { title: string; changes: ActionProposalChange[] }) {
  if (changes.length === 0) return null;

  return (
    <div className="action-diff">
      <p className="action-diff-title">{title}</p>
      <ul>
        {changes.map((change) => (
          <li key={change.field}>
            <strong>{change.field.replaceAll("_", " ")}:</strong> {change.before}{" -> "}{change.after}
          </li>
        ))}
      </ul>
    </div>
  );
}

export function ActionDecisionPanel({
  problemId,
  action
}: {
  problemId: string;
  action: ActionProposal;
}) {
  const [decisionState, setDecisionState] = useState<DecisionState>({
    state: "loading",
    message: "Loading previous decisions..."
  });

  useEffect(() => {
    let cancelled = false;

    getWorkflowState(problemId)
      .then((workflow) => {
        if (cancelled) return;
        const approval = latestApproval(workflow, action.action_id);
        setDecisionState({
          state: approval ? "saved" : "idle",
          message: approval ? approvalMessage(approval) : "No decision recorded.",
          workflow
        });
      })
      .catch((error) => {
        if (cancelled) return;
        setDecisionState({
          state: "error",
          message: error instanceof Error ? error.message : "Could not load previous decisions."
        });
      });

    return () => {
      cancelled = true;
    };
  }, [problemId, action.action_id]);

  async function decide(decision: ApprovalDecisionStatus) {
    setDecisionState((current) => ({ ...current, state: "saving", message: "Recording decision..." }));

    try {
      const currentWorkflow = await getWorkflowState(problemId);
      const existingApproval = latestApproval(currentWorkflow, action.action_id);
      if (existingApproval) {
        setDecisionState({
          state: "saved",
          message: approvalMessage(existingApproval),
          workflow: currentWorkflow
        });
        return;
      }

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
      setDecisionState((current) => ({
        ...current,
        state: "error",
        message: error instanceof Error ? error.message : "Could not record the decision."
      }));
    }
  }

  const matchingApproval = latestApproval(decisionState.workflow, action.action_id);
  const matchingExecution = decisionState.workflow?.executions.find(
    (execution) => execution.action_id === action.action_id
  );
  const matchingJiraDraft = decisionState.workflow?.jira_issue_drafts.find(
    (draft) => draft.action_id === action.action_id
  );
  const changes = matchingApproval?.action_diff ?? pendingChanges(action);

  return (
    <div className="decision-panel" aria-live="polite">
      {!matchingApproval && decisionState.state !== "loading" ? (
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
      ) : null}
      <p className={`decision-message decision-${decisionState.state}`}>{decisionState.message}</p>
      <ActionDiff title={matchingApproval ? "Approved action diff" : "Pending approval diff"} changes={changes} />
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
