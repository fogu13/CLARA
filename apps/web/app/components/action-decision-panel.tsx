"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { hasRole } from "../../lib/auth-client";
import { getContractProposal, getOutboundPreview, getWorkflowState, submitApproval,
  recordImplementation,
  retryExecution
} from "../../lib/client-api";
import { currentUserEmail } from "../../lib/auth-client";
import { useI18n } from "../../lib/i18n";
import type {
  ActionProposal,
  ActionProposalChange,
  ApprovalDecisionStatus,
  ExecutionRecord,
  OutboundPreview,
  OutcomeContractProposalPreview,
  WorkflowState
} from "../../lib/types";

// Executions whose fix can be attested: the record left CLARA (pushed) or the
// draft itself is the deliverable. A failed push has nothing to implement.
const IMPLEMENTABLE: ReadonlySet<ExecutionRecord["status"]> = new Set(["pushed", "draft_created", "completed"]);

function localDateTimeValue(date: Date): string {
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`;
}

// Parse the datetime-local value into an ISO instant; null when it is not a
// valid instant or lies in the future (the API refuses both as well).
export function implementationInstant(value: string, now: Date = new Date()): string | null {
  if (!value) return null;
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return null;
  if (parsed.getTime() > now.getTime() + 5 * 60 * 1000) return null;
  return parsed.toISOString();
}

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
  const { t } = useI18n();
  const [decisionState, setDecisionState] = useState<DecisionState>({
    state: "loading",
    message: "Loading previous decisions..."
  });
  const [contractProposal, setContractProposal] = useState<OutcomeContractProposalPreview | null>(null);
  // Cosmetic role gate (server stays authoritative); resolved in an effect so
  // the SSR render (no localStorage) matches the first client render.
  const [canDecide, setCanDecide] = useState(true);
  useEffect(() => {
    setCanDecide(hasRole("editor"));
  }, []);
  const [acceptContract, setAcceptContract] = useState(true);
  const [retrying, setRetrying] = useState(false);
  // The outbound content the reviewer is looking at: its hash travels with
  // the decision so the API refuses to sign text that changed in between.
  const [preview, setPreview] = useState<OutboundPreview | null>(null);
  const [implementing, setImplementing] = useState(false);
  const [implementedAtInput, setImplementedAtInput] = useState(() => localDateTimeValue(new Date()));
  const [implementationNote, setImplementationNote] = useState("");
  const [implementationState, setImplementationState] = useState<{ state: "idle" | "saving" | "saved" | "error"; message: string }>({
    state: "idle",
    message: ""
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
      .catch(() => {
        if (cancelled) return;
        setDecisionState({
          state: "error",
          message: "Couldn't load previous decisions."
        });
      });

    // Preview of the outcome contract an approval would apply (W4). Optional:
    // panel works unchanged when the endpoint is unavailable.
    getContractProposal(problemId)
      .then((preview) => {
        if (!cancelled) setContractProposal(preview);
      })
      .catch(() => {
        if (!cancelled) setContractProposal(null);
      });

    getOutboundPreview(problemId, action.action_id)
      .then((shown) => {
        if (!cancelled) setPreview(shown);
      })
      .catch(() => {
        if (!cancelled) setPreview(null);
      });

    return () => {
      cancelled = true;
    };
  }, [problemId, action.action_id]);

  async function decide(decision: ApprovalDecisionStatus) {
    // Governance decisions are permanent: one native dialog doubles as the
    // confirmation step and the rationale field. Cancel aborts.
    const note = window.prompt(
      `Record "${decision.replaceAll("_", " ")}" for this action? This is permanent and audited.\nOptional note:`,
      ""
    );
    if (note === null) return;
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
        reviewer: currentUserEmail() ?? "local-user",
        note: note.trim() || `Decision recorded in the app (${decision.replaceAll("_", " ")}).`,
        accept_proposed_contract: acceptContract,
        expected_outbound_sha256: preview?.sha256 ?? null
      });
      const workflow = await getWorkflowState(problemId);

      setDecisionState({
        state: "saved",
        message: `${record.decision.replaceAll("_", " ")} recorded by ${record.reviewer}.`,
        workflow
      });
    } catch (error) {
      const message = error instanceof Error ? error.message : "Could not record the decision.";
      const contentChanged = /changed since it was displayed/i.test(message);
      if (contentChanged) {
        // Refresh what the reviewer is looking at; the next decision signs
        // the current text.
        getOutboundPreview(problemId, action.action_id).then(setPreview).catch(() => setPreview(null));
      }
      setDecisionState((current) => ({
        ...current,
        state: "error",
        message: contentChanged ? t.actionsPage.decisionContentChanged : message
      }));
    }
  }

  async function saveImplementation(execution: ExecutionRecord) {
    const instant = implementationInstant(implementedAtInput);
    if (instant === null) {
      setImplementationState({ state: "error", message: t.actionsPage.implementationInvalid });
      return;
    }
    setImplementationState({ state: "saving", message: "" });
    try {
      const updated = await recordImplementation(problemId, execution.execution_id, {
        implemented_at: instant,
        note: implementationNote.trim() || null
      });
      const workflow = await getWorkflowState(problemId);
      setDecisionState((current) => ({ ...current, workflow }));
      setImplementing(false);
      setImplementationState({
        state: "saved",
        message: t.actionsPage.implementationRecorded.replace("{at}", (updated.implemented_at ?? instant).slice(0, 16).replace("T", " "))
      });
    } catch (error) {
      setImplementationState({
        state: "error",
        message: error instanceof Error ? error.message : "Could not record the implementation."
      });
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

  const proposedContract =
    !matchingApproval && contractProposal?.is_promotion_default
      ? contractProposal.proposed
      : null;

  return (
    <div className="decision-panel" aria-live="polite">
      {proposedContract ? (
        <div className="rounded-md border p-2 text-xs text-muted-foreground">
          <p className="font-semibold text-foreground">{t.contract.title}</p>
          <p className="mt-1">
            {proposedContract.primary_metric}: {t.contract.baseline}{" "}
            {contractProposal?.current.baseline}
            {" -> "}
            {proposedContract.baseline} ({t.contract.trailing28d}) /{" "}
            {t.contract.windowDays.replace(
              "{n}",
              String(proposedContract.measurement_window_days)
            )}{" "}
            / {t.contract.itsMethod}
          </p>
          {contractProposal?.detectability_note ? (
            <p className="mt-1 italic">{contractProposal.detectability_note}</p>
          ) : null}
          <label className="mt-1 flex items-center gap-2">
            <input
              type="checkbox"
              checked={acceptContract}
              onChange={(event) => setAcceptContract(event.target.checked)}
            />
            {t.contract.acceptProposed}
          </label>
          <Link
            href={`/insights/${problemId}#contract`}
            className="mt-1 inline-block text-primary hover:underline"
          >
            {t.contract.editOnInsight}
          </Link>
        </div>
      ) : null}
      {!matchingApproval && decisionState.state !== "loading" ? (
        canDecide ? (
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
        ) : (
          <p className="decision-message">
            Deciding requires the editor role — you have read-only access.
          </p>
        )
      ) : null}
      <p className={`decision-message decision-${decisionState.state}`}>{decisionState.message}</p>
      <ActionDiff title={matchingApproval ? "Approved action diff" : "Pending approval diff"} changes={changes} />
      {matchingExecution ? (
        <div className="execution-message">
          <p>
            Execution: {matchingExecution.status.replaceAll("_", " ")} in{" "}
            {matchingExecution.destination}
            {matchingExecution.external_ref ? ` · ${t.actionsPage.externalRef}: ${matchingExecution.external_ref}` : ""}
            {matchingExecution.dispatched_at ? ` · ${t.actionsPage.dispatchedOn} ${matchingExecution.dispatched_at.slice(0, 16).replace("T", " ")}` : ""}
            {matchingExecution.implemented_at ? ` · ${t.actionsPage.implementedOn} ${matchingExecution.implemented_at.slice(0, 16).replace("T", " ")}` : ""}
            {matchingExecution.dispatch_claimed_at ? ` · ${t.actionsPage.beingDispatched}` : ""}
          </p>
          {matchingExecution.implementation_note ? (
            <p className="text-xs text-muted-foreground">{matchingExecution.implementation_note}</p>
          ) : null}
          {canDecide && IMPLEMENTABLE.has(matchingExecution.status) ? (
            <div className="mt-1 text-xs">
              {implementing ? (
                <form
                  className="space-y-1"
                  onSubmit={(event) => {
                    event.preventDefault();
                    void saveImplementation(matchingExecution);
                  }}
                >
                  <p className="text-muted-foreground">{t.actionsPage.implementationHint}</p>
                  <label className="block">
                    {t.actionsPage.implementedAt}
                    <input
                      type="datetime-local"
                      required
                      max={localDateTimeValue(new Date())}
                      value={implementedAtInput}
                      onChange={(event) => setImplementedAtInput(event.target.value)}
                      className="ml-2 rounded-md border bg-background px-2 py-1"
                    />
                  </label>
                  <label className="block">
                    {t.actionsPage.implementationNote}
                    <input
                      type="text"
                      maxLength={300}
                      value={implementationNote}
                      onChange={(event) => setImplementationNote(event.target.value)}
                      className="ml-2 w-64 rounded-md border bg-background px-2 py-1"
                    />
                  </label>
                  <div className="flex gap-2 pt-1">
                    <button type="submit" disabled={implementationState.state === "saving"}>
                      {implementationState.state === "saving" ? t.actionsPage.savingImplementation : t.actionsPage.saveImplementation}
                    </button>
                    <button type="button" onClick={() => setImplementing(false)}>
                      {t.common.cancel}
                    </button>
                  </div>
                </form>
              ) : matchingExecution.implemented_at ? null : (
                <button type="button" onClick={() => setImplementing(true)}>
                  {t.actionsPage.recordImplementation}
                </button>
              )}
              {implementationState.message ? (
                <p className={implementationState.state === "error" ? "text-destructive" : "text-muted-foreground"}>
                  {implementationState.message}
                </p>
              ) : null}
            </div>
          ) : null}
          {matchingExecution.status === "push_failed" ? (
            <div className="mt-1 flex flex-wrap items-center gap-2">
              {matchingExecution.detail ? (
                <span className="text-destructive">{matchingExecution.detail}</span>
              ) : null}
              {canDecide ? (
                <button
                  type="button"
                  disabled={retrying}
                  onClick={async () => {
                    setRetrying(true);
                    try {
                      await retryExecution(problemId, matchingExecution.execution_id);
                      const workflow = await getWorkflowState(problemId);
                      setDecisionState((current) => ({ ...current, workflow }));
                    } catch (error) {
                      setDecisionState((current) => ({
                        ...current,
                        state: "error",
                        message: error instanceof Error ? error.message : "Retry failed."
                      }));
                    } finally {
                      setRetrying(false);
                    }
                  }}
                >
                  {retrying ? t.actionsPage.retrying : t.actionsPage.retryPush}
                </button>
              ) : null}
            </div>
          ) : null}
        </div>
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
