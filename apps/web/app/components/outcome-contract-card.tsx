"use client";

import { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  getContractProposal,
  getOutcomeSnapshot,
  updateOutcomeContract
} from "@/lib/client-api";
import { useI18n } from "@/lib/i18n";
import type { ItsResult, OutcomeContractProposalPreview, ProblemRecord } from "@/lib/types";

export function OutcomeContractCard({ problem }: { problem: ProblemRecord }) {
  const { t } = useI18n();
  const [proposal, setProposal] = useState<OutcomeContractProposalPreview | null>(null);
  const [its, setIts] = useState<ItsResult | null>(null);
  const [applyState, setApplyState] = useState<"idle" | "saving" | "error">("idle");

  useEffect(() => {
    let cancelled = false;

    getContractProposal(problem.problem_id)
      .then((preview) => {
        if (!cancelled) setProposal(preview);
      })
      .catch(() => {
        if (!cancelled) setProposal(null);
      });

    getOutcomeSnapshot(problem.problem_id)
      .then((snapshot) => {
        if (!cancelled) setIts(snapshot.its ?? null);
      })
      .catch(() => {
        if (!cancelled) setIts(null);
      });

    return () => {
      cancelled = true;
    };
  }, [problem.problem_id]);

  const proposed = proposal?.is_promotion_default ? proposal.proposed : null;

  async function applyProposal() {
    if (!proposed) return;
    setApplyState("saving");
    try {
      // Same PATCH + reload pattern as ActionProposalEditor.
      await updateOutcomeContract(problem.problem_id, proposed);
      window.location.reload();
    } catch {
      setApplyState("error");
    }
  }

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-sm text-muted-foreground">{t.detail.outcomeContract}</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="text-sm font-semibold">{problem.outcome_contract.primary_metric}</div>
        <p className="mt-1 text-xs text-muted-foreground">
          {problem.outcome_contract.comparison_method} /{" "}
          {problem.outcome_contract.measurement_window_days} {t.detail.days}
        </p>
        {proposed ? (
          <div className="mt-2 rounded-md border p-2 text-xs text-muted-foreground">
            <p>
              {t.contract.baseline} {proposal?.current.baseline}
              {" -> "}
              {proposed.baseline} ({t.contract.trailing28d}) /{" "}
              {t.contract.windowDays.replace("{n}", String(proposed.measurement_window_days))} /{" "}
              {t.contract.itsMethod}
            </p>
            <button
              type="button"
              disabled={applyState === "saving"}
              onClick={applyProposal}
              className="mt-1 inline-flex items-center rounded-md border px-2 py-1 text-xs font-medium hover:bg-muted"
            >
              {applyState === "saving" ? t.contract.applying : t.contract.applyProposal}
            </button>
            {applyState === "error" ? (
              <p className="mt-1 text-destructive">{t.contract.applyFailed}</p>
            ) : null}
          </div>
        ) : null}
        {its ? (
          <p className="mt-2 text-xs">
            {its.method === "its"
              ? `${t.contract.itsEffect}: ${its.effect} (${t.contract.itsCi} ${its.ci_low} … ${its.ci_high})`
              : `${t.contract.itsInsufficient} — ${t.contract.itsDelta}: ${its.delta}`}
            {" · "}
            {t.contract.itsBuckets
              .replace("{pre}", String(its.n_pre))
              .replace("{post}", String(its.n_post))}
          </p>
        ) : null}
      </CardContent>
    </Card>
  );
}
