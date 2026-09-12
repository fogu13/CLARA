"use client";

import { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  getContractProposal,
  getOutcomeSnapshot,
  updateOutcomeContract
} from "@/lib/client-api";
import { useI18n } from "@/lib/i18n";
import type {
  ItsResult,
  LoopVerdict,
  MeasurementOrigin,
  OutcomeContractProposalPreview,
  ProblemRecord
} from "@/lib/types";

export function measurementOriginLabel(
  origin: MeasurementOrigin | null | undefined,
  t: ReturnType<typeof useI18n>["t"]
): string | null {
  if (origin === "dispatch") return t.contract.originDispatch;
  if (origin === "implementation") return t.contract.originImplementation;
  if (origin === "approval") return t.contract.originApproval;
  return null;
}

export function loopVerdictLabel(verdict: LoopVerdict | null | undefined, t: ReturnType<typeof useI18n>["t"]): string {
  switch (verdict) {
    case "loop_closed":
      return t.outcomeBoard.verdictLoopClosed;
    case "fix_did_not_land":
      return t.outcomeBoard.verdictFixDidNotLand;
    case "on_track":
      return t.outcomeBoard.verdictOnTrack;
    case "manual_required":
      return t.outcomeBoard.verdictManual;
    case "measuring":
      return t.outcomeBoard.verdictMeasuring;
    default:
      return t.outcomeBoard.verdictNotMeasured;
  }
}

export function loopVerdictTone(verdict: LoopVerdict | null | undefined): string {
  if (verdict === "loop_closed") return "text-emerald-600";
  if (verdict === "fix_did_not_land") return "text-destructive";
  if (verdict === "on_track") return "text-emerald-600";
  return "text-muted-foreground";
}

export function OutcomeContractCard({ problem }: { problem: ProblemRecord }) {
  const { t } = useI18n();
  const [proposal, setProposal] = useState<OutcomeContractProposalPreview | null>(null);
  const [its, setIts] = useState<ItsResult | null>(null);
  const [loop, setLoop] = useState<{
    verdict: LoopVerdict | null;
    note: string | null;
    origin: MeasurementOrigin | null;
    originAt: string | null;
    amendedAfterMeasurement: boolean;
    measuredUnderRevision: number | null;
  } | null>(null);
  const [applyState, setApplyState] = useState<"idle" | "saving" | "error">("idle");
  const [editing, setEditing] = useState(false);
  const [editWindow, setEditWindow] = useState(
    String(problem.outcome_contract.measurement_window_days)
  );
  const [editThreshold, setEditThreshold] = useState(
    String(problem.outcome_contract.success_threshold)
  );

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
        if (cancelled) return;
        setIts(snapshot.its ?? null);
        setLoop({
          verdict: snapshot.loop_verdict ?? null,
          note: snapshot.loop_note ?? null,
          origin: snapshot.measurement_origin ?? null,
          originAt: snapshot.measurement_origin_at ?? null,
          amendedAfterMeasurement: snapshot.contract_amended_after_measurement ?? false,
          measuredUnderRevision: snapshot.measured_under_revision ?? null
        });
      })
      .catch(() => {
        if (cancelled) return;
        setIts(null);
        setLoop(null);
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
      // Same PATCH + reload pattern as ActionProposalEditor. Send only the
      // machine-derived fields: under works-council mode the GET response
      // redacts responsible_owner to a role label, and echoing it back would
      // overwrite the real owner with the literal label.
      await updateOutcomeContract(problem.problem_id, {
        baseline: proposed.baseline,
        success_threshold: proposed.success_threshold,
        measurement_window_days: proposed.measurement_window_days,
        comparison_method: proposed.comparison_method,
        guardrail_metrics: proposed.guardrail_metrics
      });
      window.location.reload();
    } catch {
      setApplyState("error");
    }
  }

  async function saveEdit() {
    const windowDays = Number(editWindow);
    const threshold = Number(editThreshold);
    if (!Number.isFinite(windowDays) || windowDays <= 0 || !Number.isFinite(threshold)) return;
    setApplyState("saving");
    try {
      await updateOutcomeContract(problem.problem_id, {
        measurement_window_days: Math.round(windowDays),
        success_threshold: threshold
      });
      window.location.reload();
    } catch {
      setApplyState("error");
    }
  }

  return (
    <Card id="contract" className="scroll-mt-14">
      <CardHeader className="pb-2">
        <CardTitle className="text-sm text-muted-foreground">{t.detail.outcomeContract}</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="text-sm font-semibold">{problem.outcome_contract.primary_metric}</div>
        <p className="mt-1 text-xs text-muted-foreground">
          {problem.outcome_contract.comparison_method} /{" "}
          {problem.outcome_contract.measurement_window_days} {t.detail.days} ·{" "}
          <span
            title={
              problem.outcome_contract.revised_at
                ? `${problem.outcome_contract.revised_at.slice(0, 10)}${problem.outcome_contract.revision_note ? ` — ${problem.outcome_contract.revision_note}` : ""}`
                : undefined
            }
          >
            {t.contract.revision.replace("{n}", String(problem.outcome_contract.revision ?? 1))}
          </span>
        </p>
        {loop ? (
          <p className={`mt-2 text-xs ${loopVerdictTone(loop.verdict)}`} title={loop.note ?? undefined}>
            <span className="font-semibold">{t.detail.loopVerdict}:</span> {loopVerdictLabel(loop.verdict, t)}
            {measurementOriginLabel(loop.origin, t) ? (
              <span className="text-muted-foreground">
                {" "}· {measurementOriginLabel(loop.origin, t)}
                {loop.originAt ? ` ${loop.originAt.slice(0, 10)}` : ""}
              </span>
            ) : null}
            {loop.note ? <span className="text-muted-foreground"> — {loop.note}</span> : null}
          </p>
        ) : null}
        {loop?.amendedAfterMeasurement ? (
          <p className="mt-1 text-xs text-amber-700">
            {t.contract.amendedAfterMeasurement.replace(
              "{n}",
              String(loop.measuredUnderRevision ?? "")
            )}
          </p>
        ) : null}
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
        {editing ? (
          <div className="mt-2 space-y-1 text-xs">
            <label className="block">
              {t.contract.editWindowLabel}
              <input
                type="number"
                min={1}
                value={editWindow}
                onChange={(event) => setEditWindow(event.target.value)}
                className="ml-2 w-20 rounded-md border bg-background px-2 py-1"
              />
            </label>
            <label className="block">
              {t.contract.editThresholdLabel}
              <input
                type="number"
                step="0.0001"
                value={editThreshold}
                onChange={(event) => setEditThreshold(event.target.value)}
                className="ml-2 w-24 rounded-md border bg-background px-2 py-1"
              />
            </label>
            <div className="flex gap-2 pt-1">
              <button
                type="button"
                disabled={applyState === "saving"}
                onClick={saveEdit}
                className="inline-flex items-center rounded-md border px-2 py-1 font-medium hover:bg-muted"
              >
                {t.common.save}
              </button>
              <button
                type="button"
                onClick={() => setEditing(false)}
                className="inline-flex items-center rounded-md px-2 py-1 text-muted-foreground hover:bg-muted"
              >
                {t.common.cancel}
              </button>
            </div>
            {applyState === "error" ? (
              <p className="text-destructive">{t.contract.applyFailed}</p>
            ) : null}
          </div>
        ) : (
          <button
            type="button"
            onClick={() => setEditing(true)}
            className="mt-2 text-xs text-muted-foreground underline-offset-2 hover:underline"
          >
            {t.contract.editContract}
          </button>
        )}
      </CardContent>
    </Card>
  );
}
