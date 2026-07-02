"use client";

import { useEffect, useState } from "react";
import { getAffectedContext } from "../../lib/client-api";
import type { AffectedContextExplorer, CustomerContextRecord } from "../../lib/types";
import { StateNotice } from "./state-notice";
import { percent } from "@/lib/format";

type ExplorerState = {
  status: "loading" | "ready" | "error";
  message: string;
  explorer?: AffectedContextExplorer;
};

function formatCurrency(value: number): string {
  return new Intl.NumberFormat("en", {
    maximumFractionDigits: 0,
    style: "currency",
    currency: "USD"
  }).format(value);
}


function joinOrDash(values: string[]): string {
  return values.length ? values.join(", ") : "-";
}

function customerLabel(customer: CustomerContextRecord): string {
  return customer.account_name
    ? `${customer.customer_id} / ${customer.account_name}`
    : customer.customer_id;
}

export function AffectedContextPanel({ problemId }: { problemId: string }) {
  const [state, setState] = useState<ExplorerState>({
    status: "loading",
    message: "Loading affected account context..."
  });

  useEffect(() => {
    getAffectedContext(problemId)
      .then((explorer) => {
        setState({
          status: "ready",
          message: "Affected context loaded.",
          explorer
        });
      })
      .catch(() => {
        setState({
          status: "error",
          message: "API is not connected. Start the backend to inspect affected accounts."
        });
      });
  }, [problemId]);

  const explorer = state.explorer;

  return (
    <section className="affected-context-panel" aria-label="Affected customers and accounts">
      <div className="affected-context-header">
        <h3>Affected Context</h3>
        {explorer ? <span>{explorer.customers.length} matched customers</span> : null}
      </div>

      {state.status === "loading" ? (
        <StateNotice tone="loading" title="Loading affected context">
          Matching evidence customer and account IDs to imported context.
        </StateNotice>
      ) : null}

      {state.status === "error" ? (
        <StateNotice tone="error" title="Affected context unavailable">
          {state.message}
        </StateNotice>
      ) : null}

      {state.status === "ready" && explorer && explorer.customers.length === 0 ? (
        <StateNotice tone="empty" title="No affected context rows">
          Import context rows for the evidence customer or account IDs to unlock account rollups.
        </StateNotice>
      ) : null}

      {explorer && explorer.accounts.length > 0 ? (
        <ul className="affected-account-list">
          {explorer.accounts.map((account) => (
            <li key={account.account_id}>
              <div>
                <strong>{account.account_name ?? account.account_id}</strong>
                <span>
                  {account.account_id}
                  {account.parent_account_name
                    ? ` / ${account.parent_account_name}`
                    : ""}
                </span>
              </div>
              <dl>
                <div>
                  <dt>Customers</dt>
                  <dd>{account.customer_count}</dd>
                </div>
                <div>
                  <dt>Value</dt>
                  <dd>{formatCurrency(account.account_value)}</dd>
                </div>
                <div>
                  <dt>Health</dt>
                  <dd>
                    {account.average_health_score === null ||
                    account.average_health_score === undefined
                      ? "-"
                      : percent(account.average_health_score)}
                  </dd>
                </div>
                <div>
                  <dt>Consent risk</dt>
                  <dd>{account.consent_risk_customers}</dd>
                </div>
                <div>
                  <dt>Roles</dt>
                  <dd>{joinOrDash(account.contact_roles)}</dd>
                </div>
                <div>
                  <dt>Lifecycle</dt>
                  <dd>{joinOrDash(account.lifecycle_stages)}</dd>
                </div>
                <div>
                  <dt>Owner</dt>
                  <dd>{joinOrDash(account.owners)}</dd>
                </div>
                <div>
                  <dt>Product owner</dt>
                  <dd>{joinOrDash(account.product_owners)}</dd>
                </div>
              </dl>
            </li>
          ))}
        </ul>
      ) : null}

      {explorer && explorer.routing_recommendations.length > 0 ? (
        <div className="routing-recommendations">
          <strong>Routing</strong>
          <ul>
            {explorer.routing_recommendations.map((recommendation) => (
              <li key={recommendation.owner}>
                <span className={`routing-priority routing-${recommendation.priority}`}>
                  {recommendation.priority}
                </span>
                <div>
                  <strong>{recommendation.owner}</strong>
                  <p>{recommendation.reason}</p>
                  <small>
                    {recommendation.account_ids.join(", ")} /{" "}
                    {joinOrDash(recommendation.contact_roles)}
                  </small>
                </div>
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      {explorer && explorer.warnings.length > 0 ? (
        <ul className="context-warning-list">
          {explorer.warnings.map((warning) => (
            <li key={warning.warning_id}>
              <strong>{warning.field}</strong>
              <span>{warning.message}</span>
            </li>
          ))}
        </ul>
      ) : null}

      {explorer && explorer.customers.length > 0 ? (
        <div className="affected-customer-list">
          {explorer.customers.slice(0, 6).map((customer) => (
            <div key={customer.customer_id}>
              <strong>{customerLabel(customer)}</strong>
              <span>{customer.contact_role ?? "Unknown role"}</span>
              <span>{customer.plan_tier ?? "Unknown tier"}</span>
              <span>{customer.product_owner ?? "No product owner"}</span>
              <span>{customer.consent_status}</span>
              <span>
                {customer.health_score === null || customer.health_score === undefined
                  ? "No health"
                  : percent(customer.health_score)}
              </span>
            </div>
          ))}
        </div>
      ) : null}
    </section>
  );
}
