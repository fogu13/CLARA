"use client";

import { useEffect, useState } from "react";
import { getWorkflowState, recordClosure } from "../../lib/client-api";
import type { ClosureRecord, ClosureRecordRequest, ProblemRecord, WorkflowState } from "../../lib/types";
import { StateNotice } from "./state-notice";

type PanelState = {
  status: "loading" | "ready" | "saving" | "error";
  message: string;
  workflow?: WorkflowState;
};

const operationalStatuses: ClosureRecordRequest["operational_status"][] = [
  "not_started",
  "draft_created",
  "in_progress",
  "released",
  "verified"
];

const customerStatuses: ClosureRecordRequest["customer_status"][] = [
  "not_started",
  "not_eligible",
  "draft_ready",
  "contacted",
  "unresolved"
];

function label(value: string): string {
  return value.replaceAll("_", " ");
}

function latestClosure(workflow: WorkflowState | undefined): ClosureRecord | undefined {
  return workflow?.closure_records.slice(-1)[0];
}

export function CustomerClosurePanel({ problem }: { problem: ProblemRecord }) {
  const [state, setState] = useState<PanelState>({
    status: "loading",
    message: "Loading closure state..."
  });
  const [operationalStatus, setOperationalStatus] = useState<ClosureRecordRequest["operational_status"]>(
    "draft_created"
  );
  const [customerStatus, setCustomerStatus] = useState<ClosureRecordRequest["customer_status"]>("unresolved");
  const [unresolvedCustomers, setUnresolvedCustomers] = useState(problem.affected_cohort.customers);
  const [owner, setOwner] = useState(problem.owner);
  const [followUpChannel, setFollowUpChannel] = useState("zendesk closure task");
  const [facts, setFacts] = useState(problem.root_cause_hypothesis);
  const [limitations, setLimitations] = useState(problem.known_limitations.join("\n"));
  const [responseDraft, setResponseDraft] = useState("");

  useEffect(() => {
    getWorkflowState(problem.problem_id)
      .then((workflow) => {
        const closure = latestClosure(workflow);
        if (closure) {
          setOperationalStatus(closure.operational_status);
          setCustomerStatus(closure.customer_status);
          setUnresolvedCustomers(closure.unresolved_customers);
          setOwner(closure.owner);
          setFollowUpChannel(closure.follow_up_channel);
          setFacts(closure.verified_resolution_facts.join("\n"));
          setLimitations(closure.limitations.join("\n"));
          setResponseDraft(closure.response_draft ?? "");
        }
        setState({ status: "ready", message: "Closure state loaded.", workflow });
      })
      .catch(() => {
        setState({
          status: "error",
          message: "API is not connected. Start the backend to manage closure."
        });
      });
  }, [problem.problem_id, problem.root_cause_hypothesis, problem.known_limitations]);

  async function saveClosure() {
    setState((current) => ({ ...current, status: "saving", message: "Recording closure state..." }));

    try {
      await recordClosure(problem.problem_id, {
        operational_status: operationalStatus,
        customer_status: customerStatus,
        owner,
        verified_resolution_facts: facts.split("\n").map((item) => item.trim()).filter(Boolean),
        unresolved_customers: unresolvedCustomers,
        follow_up_channel: followUpChannel,
        response_draft: responseDraft.trim() || undefined,
        limitations: limitations.split("\n").map((item) => item.trim()).filter(Boolean)
      });
      const workflow = await getWorkflowState(problem.problem_id);
      setState({ status: "ready", message: "Closure state recorded.", workflow });
    } catch (error) {
      setState((current) => ({
        ...current,
        status: "error",
        message: error instanceof Error ? error.message : "Could not record closure state."
      }));
    }
  }

  const closure = latestClosure(state.workflow);

  return (
    <section className="rounded-lg border p-4" aria-label="Operational and customer closure">
      <div className="flex flex-col gap-2 md:flex-row md:items-start md:justify-between">
        <div>
          <h3 className="text-sm font-semibold">Closure</h3>
          <p className="mt-1 text-sm text-muted-foreground">
            Track operational closure separately from customer follow-up. Drafts are for human review only.
          </p>
        </div>
        {closure ? (
          <div className="flex flex-wrap gap-2 text-xs">
            <span className="rounded-full border px-2 py-1">Operational: {label(closure.operational_status)}</span>
            <span className="rounded-full border px-2 py-1">Customer: {label(closure.customer_status)}</span>
            <span className="rounded-full border px-2 py-1">
              {closure.customer_closure_eligible ? "Closure eligible" : "Not closure eligible"}
            </span>
          </div>
        ) : null}
      </div>

      {state.status === "loading" ? (
        <StateNotice tone="loading" title="Loading closure">
          Reading closure records and timeline state.
        </StateNotice>
      ) : null}
      {state.status === "error" ? (
        <StateNotice tone="error" title="Closure unavailable">
          {state.message}
        </StateNotice>
      ) : null}
      {state.status === "saving" ? (
        <StateNotice tone="info" title="Saving closure">
          {state.message}
        </StateNotice>
      ) : null}
      {state.status === "ready" ? (
        <p className="mt-3 text-xs text-muted-foreground">{state.message}</p>
      ) : null}

      <div className="mt-4 grid gap-3 md:grid-cols-2">
        <label className="text-sm">
          Operational status
          <select
            className="mt-1 w-full rounded-md border bg-background p-2"
            value={operationalStatus}
            onChange={(event) => setOperationalStatus(event.target.value as ClosureRecordRequest["operational_status"])}
          >
            {operationalStatuses.map((status) => (
              <option key={status} value={status}>{label(status)}</option>
            ))}
          </select>
        </label>
        <label className="text-sm">
          Customer closure status
          <select
            className="mt-1 w-full rounded-md border bg-background p-2"
            value={customerStatus}
            onChange={(event) => setCustomerStatus(event.target.value as ClosureRecordRequest["customer_status"])}
          >
            {customerStatuses.map((status) => (
              <option key={status} value={status}>{label(status)}</option>
            ))}
          </select>
        </label>
        <label className="text-sm">
          Owner
          <input className="mt-1 w-full rounded-md border bg-background p-2" value={owner} onChange={(event) => setOwner(event.target.value)} />
        </label>
        <label className="text-sm">
          Follow-up channel
          <input className="mt-1 w-full rounded-md border bg-background p-2" value={followUpChannel} onChange={(event) => setFollowUpChannel(event.target.value)} />
        </label>
        <label className="text-sm">
          Unresolved customers
          <input
            className="mt-1 w-full rounded-md border bg-background p-2"
            min={0}
            max={problem.affected_cohort.customers}
            type="number"
            value={unresolvedCustomers}
            onChange={(event) => setUnresolvedCustomers(Number(event.target.value))}
          />
        </label>
      </div>
      <label className="mt-3 block text-sm">
        Verified resolution facts
        <textarea className="mt-1 w-full rounded-md border bg-background p-2" rows={3} value={facts} onChange={(event) => setFacts(event.target.value)} />
      </label>
      <label className="mt-3 block text-sm">
        Limitations
        <textarea className="mt-1 w-full rounded-md border bg-background p-2" rows={2} value={limitations} onChange={(event) => setLimitations(event.target.value)} />
      </label>
      <label className="mt-3 block text-sm">
        Optional reviewed response draft
        <textarea
          className="mt-1 w-full rounded-md border bg-background p-2"
          rows={4}
          placeholder="Leave blank to generate a verified-facts-only draft. No message is sent from CLARA."
          value={responseDraft}
          onChange={(event) => setResponseDraft(event.target.value)}
        />
      </label>
      {closure?.response_draft ? (
        <div className="mt-3 rounded-md border bg-muted/20 p-3 text-sm">
          <p className="font-medium">Latest response draft</p>
          <p className="mt-1 text-muted-foreground">{closure.response_draft}</p>
        </div>
      ) : null}
      <button type="button" className="mt-4 rounded-md border px-3 py-2 text-sm" disabled={state.status === "saving"} onClick={saveClosure}>
        Save closure state
      </button>
    </section>
  );
}
