"use client";

import { useEffect, useMemo, useState } from "react";
import { getPolicyRules } from "../../lib/client-api";
import type { PolicyRule } from "../../lib/types";
import { StateNotice } from "./state-notice";

type PolicyState = {
  status: "loading" | "ready" | "error";
  message: string;
  rules: PolicyRule[];
};

function formatLabel(value: string): string {
  return value.replaceAll("_", " ");
}

function policyStats(rules: PolicyRule[]) {
  return {
    active: rules.filter((rule) => rule.status === "active").length,
    blocking: rules.filter((rule) => rule.default_blocking).length,
    critical: rules.filter((rule) => rule.severity === "critical").length
  };
}

export function PolicyRulesPanel() {
  const [state, setState] = useState<PolicyState>({
    status: "loading",
    message: "Loading policy rules...",
    rules: []
  });

  useEffect(() => {
    getPolicyRules()
      .then((rules) => {
        setState({
          status: "ready",
          message: "Policy catalog is connected to the API.",
          rules
        });
      })
      .catch(() => {
        setState({
          status: "error",
          message: "API is not connected. Start the backend to load policy rules.",
          rules: []
        });
      });
  }, []);

  const stats = useMemo(() => policyStats(state.rules), [state.rules]);

  return (
    <section className="policy-panel" aria-label="Policy rules">
      <div className="policy-panel-header">
        <div>
          <p className="eyebrow">Policy Rules</p>
          <h2>Reusable governance catalog</h2>
        </div>
        <p>Reusable checks that gate approvals and customer-facing execution.</p>
      </div>

      {state.status === "loading" ? (
        <StateNotice tone="loading" title="Loading policy rules">
          Connecting to the API and reading the governance catalog.
        </StateNotice>
      ) : null}

      {state.status === "error" ? (
        <StateNotice tone="error" title="Policy catalog unavailable">
          {state.message}
        </StateNotice>
      ) : null}

      <div className="policy-stats">
        <div>
          <span className="stat-label">Active rules</span>
          <strong>{stats.active}</strong>
        </div>
        <div>
          <span className="stat-label">Blocking defaults</span>
          <strong>{stats.blocking}</strong>
        </div>
        <div>
          <span className="stat-label">Critical rules</span>
          <strong>{stats.critical}</strong>
        </div>
      </div>

      {state.rules.length > 0 ? (
        <ul className="policy-list">
          {state.rules.slice(0, 4).map((rule) => (
            <li key={rule.rule_id}>
              <div>
                <strong>{rule.title}</strong>
                <span className={`risk risk-${rule.severity}`}>{rule.severity}</span>
              </div>
              <p>{rule.description}</p>
              <small>
                {rule.rule_id} / {formatLabel(rule.category)} / owner {rule.owner}
              </small>
            </li>
          ))}
        </ul>
      ) : state.status === "ready" ? (
        <StateNotice tone="empty" title="No policy rules loaded">
          Import or seed policy rules before approving governed actions.
        </StateNotice>
      ) : null}
    </section>
  );
}
