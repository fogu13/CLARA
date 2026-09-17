"use client";

import { useCallback, useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { CalendarClock, Play } from "lucide-react";
import { getMeasurements, runDueMeasurements, type MeasurementPlan } from "@/lib/client-api";
import { useI18n } from "@/lib/i18n";

function statusVariant(status: string): "success" | "warning" | "secondary" | "outline" {
  if (status === "done") return "success";
  if (status === "manual_required") return "warning";
  if (status === "pending") return "secondary";
  return "outline";
}

function originLabel(origin: MeasurementPlan["origin"], t: ReturnType<typeof useI18n>["t"]): string {
  if (origin === "dispatch") return t.learnings.originDispatch;
  if (origin === "implementation") return t.learnings.originImplementation;
  return t.learnings.originApproval;
}

export function MeasurementCheckpointsPanel() {
  const { t } = useI18n();
  const [plans, setPlans] = useState<MeasurementPlan[]>([]);
  const [message, setMessage] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const [loadFailed, setLoadFailed] = useState(false);
  const [loaded, setLoaded] = useState(false);

  const load = useCallback(() => {
    getMeasurements()
      .then((data) => {
        setPlans(data);
        setLoadFailed(false);
        setLoaded(true);
      })
      .catch(() => {
        // A fetch failure must not masquerade as "no checkpoints yet".
        setPlans([]);
        setLoadFailed(true);
      });
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  async function runDue() {
    setBusy(true);
    setMessage(null);
    try {
      const result = await runDueMeasurements();
      setMessage(
        `Measured ${result.measured} outcome${result.measured === 1 ? "" : "s"} from real signal data` +
          (result.manual_required > 0 ? `; ${result.manual_required} need a human-recorded value.` : ".")
      );
      load();
      window.dispatchEvent(new Event("clara:outcome-recorded"));
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Run failed.");
    } finally {
      setBusy(false);
    }
  }

  const pending = plans.filter((plan) => plan.status === "pending");
  const manual = plans.filter((plan) => plan.status === "manual_required");

  return (
    <Card>
      <CardHeader className="flex flex-row items-start justify-between space-y-0">
        <div>
          <CardTitle className="flex items-center gap-2 text-base">
            <CalendarClock className="h-4 w-4" /> {t.learnings.checkpoints}
          </CardTitle>
          <CardDescription>
            {t.learnings.checkpointsSubtitle}
          </CardDescription>
        </div>
        <Button size="sm" disabled={busy} onClick={() => void runDue()}>
          <Play className="mr-1 h-3 w-3" /> {busy ? t.learnings.running : t.learnings.runDue}
        </Button>
      </CardHeader>
      <CardContent className="space-y-3">
        {message ? <p className="text-sm text-muted-foreground">{message}</p> : null}
        {loadFailed ? (
          <p className="text-sm text-destructive">{t.common.error}</p>
        ) : !loaded ? (
          <p role="status" className="text-sm text-muted-foreground">{t.common.loading}</p>
        ) : plans.length === 0 ? (
          <p className="text-sm text-muted-foreground">
            {t.learnings.noCheckpoints}
          </p>
        ) : (
          <>
            {manual.length > 0 ? (
              <p className="text-xs text-amber-700">
                {manual.length} {t.learnings.manualNote}
              </p>
            ) : null}
            <div className="space-y-2">
              {plans.slice(0, 12).map((plan) => (
                <div key={plan.id} className="flex items-start justify-between gap-2 rounded-md border p-2 text-sm">
                  <div>
                    <span className="font-medium">{plan.problem_id}</span>
                    <span className="ml-2 text-xs text-muted-foreground">
                      {plan.kind === "t7" ? t.learnings.t7Check : plan.kind === "followup" ? t.learnings.followUp : t.learnings.windowClose} · {t.learnings.due} {plan.due_at.slice(0, 10)}
                    </span>
                    <span
                      className="ml-2 rounded-full border px-1.5 py-0.5 text-[10px] text-muted-foreground"
                      title={plan.executed_at.slice(0, 10)}
                    >
                      {originLabel(plan.origin, t)}
                    </span>
                    {plan.observation_start && plan.observation_end ? (
                      <span className="ml-2 text-[10px] text-muted-foreground">
                        {t.learnings.reads
                          .replace("{start}", plan.observation_start.slice(0, 10))
                          .replace("{end}", plan.observation_end.slice(0, 10))}
                        {plan.contract_snapshot && typeof plan.contract_snapshot.revision === "number"
                          ? ` · ${t.learnings.contractRevision.replace("{n}", String(plan.contract_snapshot.revision))}`
                          : ""}
                      </span>
                    ) : null}
                    {plan.note ? (
                      <p className="mt-0.5 text-xs text-muted-foreground">{plan.note}</p>
                    ) : null}
                  </div>
                  <Badge variant={statusVariant(plan.status)}>
                    {plan.status === "superseded" ? t.learnings.statusSuperseded : plan.status.replaceAll("_", " ")}
                  </Badge>
                </div>
              ))}
            </div>
            {pending.length > 0 ? (
              <p className="text-xs text-muted-foreground">
                {pending.length} {t.learnings.pendingNote}
              </p>
            ) : null}
          </>
        )}
      </CardContent>
    </Card>
  );
}
